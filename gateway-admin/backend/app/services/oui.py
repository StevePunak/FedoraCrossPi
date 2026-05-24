"""OUI vendor lookup for MAC addresses.

Uses the Wireshark `manuf` file bundled at app/data/manuf as the source.
Supports the three IEEE assignment sizes (MA-L /24, MA-M /28, MA-S /36),
checking longest-prefix-first so a /36 sub-block wins over the /24 it
sits inside. Refresh the bundled file with backend/refresh-manuf.sh.
"""

import re
from pathlib import Path

_d24: dict[str, str] = {}
_d28: dict[str, str] = {}
_d36: dict[str, str] = {}
_loaded = False


def _data_path() -> Path:
    # Sibling `oui_data/` rather than `data/` so the bundled file isn't
    # caught by the `app/data/` gitignore (which is reserved for dev-time
    # config artifacts).
    return Path(__file__).parent.parent / "oui_data" / "manuf"


def _normalize(mac: str) -> str:
    """Strip everything except hex digits, return uppercase. Tolerates
    colons, dashes, dots, spaces, leading/trailing junk."""
    return re.sub(r"[^0-9A-Fa-f]", "", mac).upper()


def _load() -> None:
    global _loaded
    if _loaded:
        return
    _loaded = True

    path = _data_path()
    if not path.exists():
        return

    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue

        # Format: <prefix>[/length]<whitespace><short>[<whitespace><long>]
        # The file uses tabs but the spacing is irregular; split on any
        # whitespace and take the first two fields.
        parts = re.split(r"\s+", line, maxsplit=2)
        if len(parts) < 2:
            continue

        prefix_field, short = parts[0], parts[1]
        if "/" in prefix_field:
            prefix, length_str = prefix_field.split("/", 1)
            try:
                length_bits = int(length_str)
            except ValueError:
                continue
        else:
            prefix = prefix_field
            length_bits = 24

        hex_str = _normalize(prefix)
        if length_bits == 24:
            _d24[hex_str[:6]] = short
        elif length_bits == 28:
            _d28[hex_str[:7]] = short
        elif length_bits == 36:
            _d36[hex_str[:9]] = short
        # Any other length (none seen in practice): ignored.


def lookup_vendor(mac: str) -> str | None:
    """Return the manufacturer short name for `mac`, or None if unknown
    or the file is missing/empty. Safe to call with any string; bogus
    inputs just return None."""
    if not mac:
        return None
    _load()
    h = _normalize(mac)
    if len(h) < 6:
        return None
    return _d36.get(h[:9]) or _d28.get(h[:7]) or _d24.get(h[:6])
