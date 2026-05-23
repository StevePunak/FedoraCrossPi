import re

from pydantic import BaseModel, field_validator, model_validator


class NetworkConfig(BaseModel):
    # Defaults match the static config shipped in the gateway image's
    # systemd-networkd-gateway-config recipe so reconcile-on-startup is
    # a no-op on a fresh appliance with no persisted network.json.
    mode: str = "static"  # "dhcp" or "static"
    address: str = "192.168.0.2"
    netmask: str = "255.255.255.0"
    gateway: str = "192.168.0.1"
    dns: list[str] = ["127.0.0.1"]
    # Search domain for systemd-resolved on stilgar itself; bare names get
    # this appended (e.g. `media-02` → `media-02.<domain>`). Independent of
    # DhcpConfig.domain (which dnsmasq sends to LAN clients via DHCP option 15).
    domain: str = ""
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


class ActiveLease(BaseModel):
    # Unix epoch when the lease expires. 0 means a never-expiring (static)
    # lease, per dnsmasq's leasefile format.
    expires_at: int
    mac: str
    ip: str
    hostname: str
    client_id: str


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


_NAS_SLUG_RE = re.compile(r"^[a-z0-9](?:[a-z0-9-]*[a-z0-9])?$")
_DEFAULT_NAS_OPTIONS = "vers=3.0,iocharset=utf8,nofail,_netdev,noperm"


class NasMount(BaseModel):
    # Slug becomes the mount path (/mnt/<id>) and the systemd unit basename.
    id: str
    server: str
    share: str
    username: str = ""
    password: str = ""
    # Extra options appended after the defaults; leave empty for the
    # noperm/nofail/_netdev defaults that suit a home NAS.
    extra_options: str = ""
    enabled: bool = True

    @field_validator("id")
    @classmethod
    def _validate_id(cls, v: str) -> str:
        if not _NAS_SLUG_RE.match(v):
            raise ValueError(
                "id must match [a-z0-9-]+, start and end with alphanumeric"
            )
        return v

    @field_validator("server", "share")
    @classmethod
    def _strip_required(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("must not be empty")
        return v

    @property
    def mount_path(self) -> str:
        return f"/mnt/{self.id}"


class NasConfig(BaseModel):
    mounts: list[NasMount] = []

    @model_validator(mode="after")
    def _unique_ids(self):
        ids = [m.id for m in self.mounts]
        if len(ids) != len(set(ids)):
            raise ValueError("mount ids must be unique")
        return self


class NasMountStatus(BaseModel):
    id: str
    mount_path: str
    enabled: bool
    mounted: bool
    automount_active: bool
    last_error: str = ""


class NasTestResult(BaseModel):
    ok: bool
    message: str


class SystemInfo(BaseModel):
    hostname: str
    uptime: str
    ip_address: str
    kernel: str
    memory_total: str
    memory_used: str
    disk_total: str
    disk_used: str
