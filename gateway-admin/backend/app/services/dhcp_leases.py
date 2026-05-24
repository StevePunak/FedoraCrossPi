"""Read dynamic DHCP leases recorded by dnsmasq.

dnsmasq writes one lease per line to its leasefile in the form:
    <expiry-epoch> <mac> <ip> <hostname-or-*> <client-id-or-*>

Lines beginning with `duid` (an IPv6 server identifier) are skipped.
"""

import os
from pathlib import Path

from app.models.schemas import ActiveLease
from app.services.oui import lookup_vendor


def _leasefile() -> Path:
    return Path(os.environ.get("GATEWAY_DNSMASQ_LEASEFILE", "/var/lib/misc/dnsmasq.leases"))


def get_active_leases() -> list[ActiveLease]:
    path = _leasefile()
    try:
        raw = path.read_text()
    except FileNotFoundError:
        return []
    except PermissionError:
        return []

    leases: list[ActiveLease] = []
    for line in raw.splitlines():
        parts = line.split()
        # Skip the IPv6 DUID header line and any malformed entries.
        if len(parts) < 5 or parts[0] == "duid":
            continue
        try:
            expires_at = int(parts[0])
        except ValueError:
            continue
        hostname = parts[3] if parts[3] != "*" else ""
        client_id = parts[4] if parts[4] != "*" else ""
        leases.append(
            ActiveLease(
                expires_at=expires_at,
                mac=parts[1],
                ip=parts[2],
                hostname=hostname,
                client_id=client_id,
                vendor=lookup_vendor(parts[1]),
            )
        )
    return leases
