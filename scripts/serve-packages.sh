#!/usr/bin/env bash
# Serve the Yocto RPM package feed so the Pi can use dnf to install packages.
# Run this on the build machine before using dnf on the Pi.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RPM_DIR="${SCRIPT_DIR}/../build/tmp/deploy/rpm"
PORT="${1:-8080}"

if [ ! -d "${RPM_DIR}" ]; then
    echo "RPM deploy directory not found: ${RPM_DIR}" >&2
    echo "Run build-image.sh first." >&2
    exit 1
fi

echo "Serving Yocto package feed at http://$(hostname -I | awk '{print $1}'):${PORT}/rpm/"
echo "Press Ctrl+C to stop."

cd "${SCRIPT_DIR}/.."
exec python3 -m http.server "${PORT}" --directory build/tmp/deploy
