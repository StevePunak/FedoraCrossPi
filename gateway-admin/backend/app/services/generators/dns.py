from app.models.schemas import DnsConfig, HostEntry


def generate_dns(config: DnsConfig) -> str:
    lines = []
    for server in config.upstream_servers:
        lines.append(f"server={server}")
    if config.domain:
        lines.append(f"domain={config.domain}")
        # Don't add `local=/{domain}/`: that would make dnsmasq authoritative
        # for the entire zone and refuse to forward queries for names not in
        # our local host entries — including the public apex (e.g.
        # punak.com itself), breaking access to the real website.
    if config.expand_hosts:
        lines.append("expand-hosts")
    if not lines:
        return "# no DNS configuration\n"
    return "\n".join(lines) + "\n"


def generate_hosts(entries: list[HostEntry]) -> str:
    lines = []
    for entry in entries:
        for name in entry.hostnames:
            if name:
                lines.append(f"address=/{name}/{entry.ip}")
    if not lines:
        return "# no custom host entries\n"
    return "\n".join(lines) + "\n"
