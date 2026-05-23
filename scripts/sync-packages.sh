#!/usr/bin/env bash
# Sync Yocto RPM packages to a package-feed host for dnf on-device use.
# Configure the destination via the PACKAGE_FEED_HOST environment variable
# (or pass it as the first argument). Run after each image build.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RPM_DIR="${SCRIPT_DIR}/../build/tmp/deploy/rpm"

HOST="${1:-${PACKAGE_FEED_HOST:-}}"
if [ -z "${HOST}" ]; then
    echo "Usage: $0 <user@host:/path>  (or set PACKAGE_FEED_HOST)" >&2
    exit 2
fi

if [ ! -d "${RPM_DIR}" ]; then
    echo "RPM deploy directory not found: ${RPM_DIR}" >&2
    echo "Run build-image.sh first." >&2
    exit 1
fi

echo "Syncing packages to ${HOST}..."
rsync -av --delete "${RPM_DIR}/" "${HOST}/"
echo "Done."
