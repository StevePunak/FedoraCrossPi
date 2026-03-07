#!/usr/bin/env bash
set -euo pipefail

TARGET="${1:-rpi4}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="${SCRIPT_DIR}/.."
PRIVATE_KAS="${REPO_ROOT}/../meta-rpi4-private/kas/private.yml"
LOCAL_KAS="${REPO_ROOT}/kas/local.yml"

case "${TARGET}" in
  rpi4) KAS_FILE="${REPO_ROOT}/kas/rpi4-qt6.yml" ;;
  rpi5) KAS_FILE="${REPO_ROOT}/kas/rpi5-qt6.yml" ;;
  *) echo "Usage: $0 [rpi4|rpi5]" >&2; exit 1 ;;
esac

FULL_KAS="${KAS_FILE}"
if [ -f "${PRIVATE_KAS}" ]; then
    cp "${PRIVATE_KAS}" "${LOCAL_KAS}"
    FULL_KAS="${KAS_FILE}:${LOCAL_KAS}"
fi

# Builds the Qt 6.10.x cross-compile SDK installer
# Output: build/tmp/deploy/sdk/poky-glibc-x86_64-rpi4-qt6-image-cortexa7*-toolchain-*.sh
exec kas shell "${FULL_KAS}" -c "bitbake -c populate_sdk rpi4-qt6-image"
