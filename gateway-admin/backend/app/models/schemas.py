from pydantic import BaseModel, model_validator


class NetworkConfig(BaseModel):
    mode: str = "dhcp"  # "dhcp" or "static"
    address: str = ""
    netmask: str = "255.255.255.0"
    gateway: str = ""
    dns: list[str] = []
    hostname: str = ""


class DhcpConfig(BaseModel):
    enabled: bool = False
    authoritative: bool = True
    range_start: str = ""
    range_end: str = ""
    netmask: str = "255.255.255.0"
    lease_time: str = "24h"
    router: str = ""
    # First entry is the primary DNS clients use; remaining entries are
    # fallbacks (e.g. 8.8.8.8) tried when the primary is down.
    dns_servers: list[str] = []
    domain: str = ""
    domain_search: list[str] = []
    ntp_servers: list[str] = []
    mtu: int | None = None
    tftp_server: str = ""
    boot_filename: str = ""

    @model_validator(mode="before")
    @classmethod
    def _migrate_dns_server(cls, data):
        # Accept legacy `dns_server` (str) from JSON written by older versions
        if isinstance(data, dict) and "dns_server" in data and "dns_servers" not in data:
            legacy = data.pop("dns_server")
            data["dns_servers"] = [legacy] if legacy else []
        return data


class StaticLease(BaseModel):
    mac: str
    ip: str
    hostname: str
    comment: str = ""
    enabled: bool = True


class DnsConfig(BaseModel):
    upstream_servers: list[str] = []
    domain: str = ""
    expand_hosts: bool = True


class HostEntry(BaseModel):
    ip: str
    hostnames: list[str]


class ServiceStatus(BaseModel):
    name: str
    active: bool
    enabled: bool
    status: str


class SystemInfo(BaseModel):
    hostname: str
    uptime: str
    ip_address: str
    kernel: str
    memory_total: str
    memory_used: str
    disk_total: str
    disk_used: str
