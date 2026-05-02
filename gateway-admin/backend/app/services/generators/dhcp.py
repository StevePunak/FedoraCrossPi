from app.models.schemas import DhcpConfig, StaticLease


def generate_dhcp(config: DhcpConfig) -> str:
    if not config.enabled:
        return "# DHCP server disabled via admin UI\n"

    lines = [
        f"dhcp-range={config.range_start},{config.range_end},"
        f"{config.netmask},{config.lease_time}",
    ]

    if config.authoritative:
        lines.append("dhcp-authoritative")

    if config.router:
        lines.append(f"dhcp-option=option:router,{config.router}")
    if config.dns_servers:
        lines.append(f"dhcp-option=option:dns-server,{','.join(config.dns_servers)}")
    if config.domain:
        lines.append(f"dhcp-option=option:domain-name,{config.domain}")
    if config.domain_search:
        lines.append(
            f"dhcp-option=option:domain-search,{','.join(config.domain_search)}"
        )
    if config.ntp_servers:
        lines.append(f"dhcp-option=option:ntp-server,{','.join(config.ntp_servers)}")
    if config.mtu:
        lines.append(f"dhcp-option=option:mtu,{config.mtu}")
    if config.tftp_server:
        lines.append(f"dhcp-option=option:tftp-server,{config.tftp_server}")
    if config.boot_filename:
        lines.append(f"dhcp-option=option:bootfile-name,{config.boot_filename}")

    return "\n".join(lines) + "\n"


def generate_static_leases(leases: list[StaticLease]) -> str:
    lines = []
    for lease in leases:
        prefix = "" if lease.enabled else "# disabled: "
        comment = f"  # {lease.comment}" if lease.comment else ""
        lines.append(
            f"{prefix}dhcp-host={lease.mac},{lease.ip},{lease.hostname}{comment}"
        )
    if not lines:
        return "# no static leases configured\n"
    return "\n".join(lines) + "\n"
