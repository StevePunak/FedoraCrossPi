"""
Config applier: takes JSON configs, generates service config files, reloads
the affected services.

In production (GATEWAY_DATA_DIR set): writes to /data/{network,dnsmasq.d}/
(which gateway-init symlinks into /etc) and calls systemctl to reload.

In dev: returns the generated content without touching the filesystem.
"""

import os
import subprocess
from pathlib import Path

from app.models.schemas import (
    DhcpConfig,
    DnsConfig,
    HostEntry,
    NetworkConfig,
    StaticLease,
)
from app.services.generators import dhcp as dhcp_gen
from app.services.generators import dns as dns_gen
from app.services.generators import network as network_gen


def _is_production() -> bool:
    return bool(os.environ.get("GATEWAY_DATA_DIR"))


def _data_dir() -> Path:
    return Path(os.environ.get("GATEWAY_DATA_DIR", "/data"))


def _write(path: Path, content: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)


def _ensure_symlink(target: Path, link: Path):
    """Ensure `link` is a symlink pointing at `target`. No-op in dev mode."""
    if not _is_production():
        return
    link.parent.mkdir(parents=True, exist_ok=True)
    if link.is_symlink() or link.exists():
        if link.is_symlink() and link.readlink() == target:
            return
        link.unlink()
    link.symlink_to(target)


def _systemctl(*args: str) -> tuple[int, str]:
    try:
        result = subprocess.run(
            ["systemctl", *args],
            capture_output=True, text=True, timeout=30,
        )
        return result.returncode, (result.stdout + result.stderr).strip()
    except Exception as e:
        return 1, str(e)


def apply_network(config: NetworkConfig) -> dict:
    content = network_gen.generate_network(config)
    result = {"generated": content, "applied": False}

    if _is_production():
        path = _data_dir() / "network" / "10-wired-static.network"
        _write(path, content)

        if config.hostname:
            hostname_path = _data_dir() / "hostname"
            hostname_path.write_text(config.hostname + "\n")
            subprocess.run(
                ["hostnamectl", "set-hostname", config.hostname],
                capture_output=True, timeout=10,
            )

        # networkctl reload picks up .network file changes; reconfigure applies to the link.
        _systemctl("reload-or-restart", "systemd-networkd")

        # Regenerate TLS cert so SANs include the new IP/hostname (best-effort)
        try:
            subprocess.Popen(
                ["/usr/sbin/gateway-ssl-init.sh"],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            )
        except FileNotFoundError:
            pass

        result["applied"] = True
        result["path"] = str(path)

    return result


def apply_dhcp(config: DhcpConfig, leases: list[StaticLease]) -> dict:
    dhcp_content = dhcp_gen.generate_dhcp(config)
    leases_content = dhcp_gen.generate_static_leases(leases)
    result = {
        "generated": {
            "dhcp": dhcp_content,
            "static_leases": leases_content,
        },
        "applied": False,
    }

    if _is_production():
        dhcp_path = _data_dir() / "dnsmasq.d" / "02-dhcp.conf"
        leases_path = _data_dir() / "dnsmasq.d" / "03-static-leases.conf"
        _write(dhcp_path, dhcp_content)
        _write(leases_path, leases_content)
        _ensure_symlink(dhcp_path, Path("/etc/dnsmasq.d/02-dhcp.conf"))
        _ensure_symlink(leases_path, Path("/etc/dnsmasq.d/03-static-leases.conf"))

        # Enable/disable the service based on config
        if config.enabled:
            _systemctl("enable", "--now", "dnsmasq")
            _systemctl("restart", "dnsmasq")
        else:
            _systemctl("disable", "--now", "dnsmasq")

        result["applied"] = True
        result["paths"] = [str(dhcp_path), str(leases_path)]

    return result


def apply_dns(config: DnsConfig, entries: list[HostEntry]) -> dict:
    dns_content = dns_gen.generate_dns(config)
    hosts_content = dns_gen.generate_hosts(entries)
    result = {
        "generated": {
            "dns": dns_content,
            "hosts": hosts_content,
        },
        "applied": False,
    }

    if _is_production():
        dns_path = _data_dir() / "dnsmasq.d" / "01-dns.conf"
        hosts_path = _data_dir() / "dnsmasq.d" / "04-hosts.conf"
        _write(dns_path, dns_content)
        _write(hosts_path, hosts_content)
        _ensure_symlink(dns_path, Path("/etc/dnsmasq.d/01-dns.conf"))
        _ensure_symlink(hosts_path, Path("/etc/dnsmasq.d/04-hosts.conf"))

        # Only reload if dnsmasq is running (otherwise no-op)
        is_active, _ = _systemctl("is-active", "dnsmasq")
        if is_active == 0:
            _systemctl("restart", "dnsmasq")

        result["applied"] = True
        result["paths"] = [str(dns_path), str(hosts_path)]

    return result
