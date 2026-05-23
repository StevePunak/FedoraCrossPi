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
    NasConfig,
    NetworkConfig,
    StaticLease,
)
from app.services.generators import dhcp as dhcp_gen
from app.services.generators import dns as dns_gen
from app.services.generators import nas as nas_gen
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


def _nas_unit_dir() -> Path:
    return _data_dir() / "systemd" / "nas"


def _nas_credentials_dir() -> Path:
    return _data_dir() / "nas" / "credentials"


def _systemd_etc() -> Path:
    return Path("/etc/systemd/system")


def _existing_managed_basenames() -> set[str]:
    """Return basenames of NAS-managed unit files currently on disk."""
    d = _nas_unit_dir()
    if not d.exists():
        return set()
    return {p.name for p in d.iterdir() if p.is_file()}


def _teardown_unit(unit_name: str):
    """Stop+disable a unit and remove its symlink + source file."""
    _systemctl("stop", unit_name)
    _systemctl("disable", unit_name)
    link = _systemd_etc() / unit_name
    if link.is_symlink() or link.exists():
        link.unlink()
    src = _nas_unit_dir() / unit_name
    if src.exists():
        src.unlink()


def apply_nas(config: NasConfig) -> dict:
    """Materialize systemd .mount/.automount units for NAS mounts.

    Source files live under /data/systemd/nas/, symlinked into
    /etc/systemd/system/. Credentials go to /data/nas/credentials/<id>
    (mode 0600). Units removed from the config are torn down. Each
    enabled mount has its .automount started; each disabled mount is
    stopped+disabled but its files are left on disk so flipping enabled
    back on does not need a re-save of credentials.
    """
    desired_units: dict[str, str] = {}  # basename -> content
    desired_creds: dict[str, str] = {}  # path -> content
    desired_mountpoints: list[str] = []
    enabled_automounts: list[str] = []
    disabled_units: list[str] = []

    for mount in config.mounts:
        base = nas_gen.unit_basename(mount)
        mount_unit = f"{base}.mount"
        automount_unit = f"{base}.automount"
        desired_mountpoints.append(mount.mount_path)

        creds_content = nas_gen.credentials_content(mount)
        if creds_content is not None:
            creds_path = _nas_credentials_dir() / mount.id
            desired_creds[str(creds_path)] = creds_content
            creds_path_str = str(creds_path)
        else:
            creds_path_str = None

        desired_units[mount_unit] = nas_gen.generate_mount_unit(mount, creds_path_str)
        desired_units[automount_unit] = nas_gen.generate_automount_unit(mount)

        if mount.enabled:
            enabled_automounts.append(automount_unit)
        else:
            disabled_units.extend([automount_unit, mount_unit])

    result = {
        "generated": {name: content for name, content in desired_units.items()},
        "applied": False,
    }

    if not _is_production():
        return result

    # Tear down units no longer in the config.
    existing = _existing_managed_basenames()
    for stale in existing - desired_units.keys():
        _teardown_unit(stale)

    # Write source files, credentials, and symlink into /etc/systemd/system/.
    _nas_unit_dir().mkdir(parents=True, exist_ok=True)
    creds_dir = _nas_credentials_dir()
    creds_dir.mkdir(parents=True, exist_ok=True)
    try:
        creds_dir.chmod(0o700)
    except OSError:
        pass

    # Remove credentials whose mount was removed.
    if creds_dir.exists():
        kept_ids = {m.id for m in config.mounts if nas_gen.credentials_content(m) is not None}
        for f in creds_dir.iterdir():
            if f.is_file() and f.name not in kept_ids:
                f.unlink()

    for path_str, content in desired_creds.items():
        p = Path(path_str)
        p.write_text(content)
        p.chmod(0o600)

    for unit_name, content in desired_units.items():
        src = _nas_unit_dir() / unit_name
        _write(src, content)
        _ensure_symlink(src, _systemd_etc() / unit_name)

    # Ensure mount points exist (mountpoints, owned by root, 0755).
    for mp in desired_mountpoints:
        Path(mp).mkdir(parents=True, exist_ok=True)

    _systemctl("daemon-reload")

    for unit in disabled_units:
        _systemctl("stop", unit)
        _systemctl("disable", unit)

    for unit in enabled_automounts:
        _systemctl("enable", unit)
        _systemctl("start", unit)

    result["applied"] = True
    result["unit_dir"] = str(_nas_unit_dir())
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
