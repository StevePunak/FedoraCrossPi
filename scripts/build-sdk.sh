#!/usr/bin/env bash
set -euo pipefail

TARGET="${1:-rpi4}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

case "${TARGET}" in
  rpi4) KAS_FILE="${SCRIPT_DIR}/../kas/rpi4-qt6.yml" ;;
  rpi5) KAS_FILE="${SCRIPT_DIR}/../kas/rpi5-qt6.yml" ;;
  *) echo "Usage: $0 [rpi4|rpi5]" >&2; exit 1 ;;
esac

# Builds the Qt 6.10.x cross-compile SDK installer
# Output: build/tmp/deploy/sdk/poky-glibc-x86_64-rpi4-qt6-image-cortexa7*-toolchain-*.sh
exec kas shell "${KAS_FILE}" -- bitbake -c populate_sdk rpi4-qt6-image
