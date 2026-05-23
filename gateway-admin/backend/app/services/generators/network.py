from app.models.schemas import NetworkConfig


def _netmask_to_prefix(netmask: str) -> int:
    parts = netmask.split(".")
    if len(parts) != 4:
        return 24
    bits = 0
    for part in parts:
        bits += bin(int(part)).count("1")
    return bits


def generate_network(config: NetworkConfig) -> str:
    lines = ["[Match]", "Type=ether", "", "[Network]"]

    if config.mode == "dhcp":
        lines.append("DHCP=yes")
        lines.append("MulticastDNS=yes")
        if config.domain:
            lines.append(f"Domains={config.domain}")
    else:
        prefix = _netmask_to_prefix(config.netmask)
        lines.append(f"Address={config.address}/{prefix}")
        for dns in config.dns:
            lines.append(f"DNS={dns}")
        if config.domain:
            lines.append(f"Domains={config.domain}")
        lines.append("MulticastDNS=yes")
        if config.gateway:
            lines += ["", "[Route]", f"Gateway={config.gateway}"]

    return "\n".join(lines) + "\n"
