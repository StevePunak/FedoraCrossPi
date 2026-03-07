#!/usr/bin/env bash
# Sync Yocto RPM packages to feyd for dnf on-device use.
# Run after each image build.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RPM_DIR="${SCRIPT_DIR}/../build/tmp/deploy/rpm"

if [ ! -d "${RPM_DIR}" ]; then
    echo "RPM deploy directory not found: ${RPM_DIR}" >&2
    echo "Run build-image.sh first." >&2
    exit 1
fi

echo "Syncing packages to feyd..."
rsync -av --delete "${RPM_DIR}/" feyd:/var/www/packages/rpm/
echo "Done. Feed available at http://feyd:880/rpm/"
