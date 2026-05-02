"""
Configuration store abstraction.

In production, reads/writes config files on the /data partition.
In development, uses a local temp directory with seed data.
"""

import json
import os
import tempfile
from pathlib import Path

from app.models.schemas import (
    DhcpConfig,
    DnsConfig,
    HostEntry,
    NetworkConfig,
    StaticLease,
)

# Use DATA_DIR env var if set (production: /data), otherwise temp dir
_data_dir: Path | None = None


def _get_data_dir() -> Path:
    global _data_dir
    if _data_dir is not None:
        return _data_dir

    env_dir = os.environ.get("GATEWAY_DATA_DIR")
    if env_dir:
        _data_dir = Path(env_dir)
    else:
        _data_dir = Path(tempfile.mkdtemp(prefix="gateway-config-"))
        _seed_defaults()
        print(f"Dev mode: config stored in {_data_dir}")

    _data_dir.mkdir(parents=True, exist_ok=True)
    return _data_dir


def _seed_defaults():
    """Seed the dev config directory with sample data."""
    d = _data_dir
    d.mkdir(parents=True, exist_ok=True)

    _write_json(d / "network.json", NetworkConfig(
        mode="dhcp",
        hostname="gateway",
    ).model_dump())

    _write_json(d / "dhcp.json", DhcpConfig(
        enabled=False,
        authoritative=True,
        range_start="192.168.0.100",
        range_end="192.168.0.200",
        netmask="255.255.255.0",
        lease_time="24h",
        router="192.168.0.1",
        dns_servers=["192.168.0.51", "8.8.8.8"],
        domain="punak.com",
        domain_search=["punak.com"],
        ntp_servers=["192.168.0.51"],
        mtu=1500,
        tftp_server="",
        boot_filename="",
    ).model_dump())

    _write_json(d / "static_leases.json", [
        StaticLease(mac="DC:A6:32:3C:32:E3", ip="192.168.0.78", hostname="kiosk",
                    comment="Gateway dev Pi", enabled=True).model_dump(),
        StaticLease(mac="00:11:32:D9:79:F9", ip="192.168.0.12", hostname="media-02",
                    comment="NAS", enabled=True).model_dump(),
        StaticLease(mac="C8:21:58:8A:A0:E8", ip="192.168.0.30", hostname="globula",
                    comment="", enabled=True).model_dump(),
    ])

    _write_json(d / "dns.json", DnsConfig(
        upstream_servers=["8.8.8.8", "8.8.4.4"],
        domain="punak.com",
        expand_hosts=True,
    ).model_dump())

    _write_json(d / "hosts.json", [
        HostEntry(ip="192.168.0.11", hostnames=["media.punak.com"]).model_dump(),
        HostEntry(ip="192.168.0.12", hostnames=["media-02.punak.com"]).model_dump(),
        HostEntry(ip="192.168.0.51", hostnames=["feyd.punak.com"]).model_dump(),
    ])


def _read_json(path: Path) -> dict | list:
    if path.exists():
        return json.loads(path.read_text())
    return {}


def _write_json(path: Path, data: dict | list):
    path.write_text(json.dumps(data, indent=2) + "\n")


# --- Network ---

def get_network_config() -> NetworkConfig:
    data = _read_json(_get_data_dir() / "network.json")
    return NetworkConfig(**data) if data else NetworkConfig()


def save_network_config(config: NetworkConfig):
    _write_json(_get_data_dir() / "network.json", config.model_dump())


# --- DHCP ---

def get_dhcp_config() -> DhcpConfig:
    data = _read_json(_get_data_dir() / "dhcp.json")
    return DhcpConfig(**data) if data else DhcpConfig()


def save_dhcp_config(config: DhcpConfig):
    _write_json(_get_data_dir() / "dhcp.json", config.model_dump())


def get_static_leases() -> list[StaticLease]:
    data = _read_json(_get_data_dir() / "static_leases.json")
    return [StaticLease(**entry) for entry in data] if data else []


def save_static_leases(leases: list[StaticLease]):
    _write_json(
        _get_data_dir() / "static_leases.json",
        [l.model_dump() for l in leases],
    )


# --- DNS ---

def get_dns_config() -> DnsConfig:
    data = _read_json(_get_data_dir() / "dns.json")
    return DnsConfig(**data) if data else DnsConfig()


def save_dns_config(config: DnsConfig):
    _write_json(_get_data_dir() / "dns.json", config.model_dump())


def get_host_entries() -> list[HostEntry]:
    data = _read_json(_get_data_dir() / "hosts.json")
    return [HostEntry(**entry) for entry in data] if data else []


def save_host_entries(entries: list[HostEntry]):
    _write_json(
        _get_data_dir() / "hosts.json",
        [e.model_dump() for e in entries],
    )
