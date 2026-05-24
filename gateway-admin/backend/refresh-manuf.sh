#!/usr/bin/env bash
# Refresh the bundled Wireshark `manuf` file used by app/services/oui.py
# to map MAC OUI prefixes to manufacturer short names. Run manually when
# you want a newer copy; the file is checked into the source tree so the
# image ships with whatever was last refreshed.
#
# Source: https://www.wireshark.org/download/automated/data/manuf
# Format: <prefix>\t<short>\t<long-name>  (prefix can be /24, /28, /36)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TARGET="${SCRIPT_DIR}/app/oui_data/manuf"
URL="https://www.wireshark.org/download/automated/data/manuf"

mkdir -p "$(dirname "$TARGET")"
echo "Fetching $URL ..."
curl -fsSL "$URL" -o "$TARGET.tmp"

# Sanity check: real manuf files have thousands of OUI lines.
lines=$(grep -cv '^#\|^$' "$TARGET.tmp" || true)
if [ "$lines" -lt 5000 ]; then
    echo "ERROR: fetched file has only $lines non-comment lines; refusing to overwrite." >&2
    rm -f "$TARGET.tmp"
    exit 1
fi

mv "$TARGET.tmp" "$TARGET"
size=$(du -h "$TARGET" | cut -f1)
echo "Wrote $TARGET ($size, $lines entries)"
