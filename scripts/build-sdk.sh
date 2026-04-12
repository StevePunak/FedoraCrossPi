#!/usr/bin/env bash
set -euo pipefail

TARGET="${1:-rpi4}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="${SCRIPT_DIR}/.."
LOCAL_KAS="${REPO_ROOT}/kas/local.yml"

case "${TARGET}" in
  rpi4)
    KAS_FILE="${REPO_ROOT}/kas/rpi4-qt6.yml"
    PRIVATE_KAS="${REPO_ROOT}/../meta-rpi4-jukebox/kas/private.yml"
    IMAGE="rpi4-qt6-image"
    ;;
  rpi5)
    KAS_FILE="${REPO_ROOT}/kas/rpi5-qt6.yml"
    PRIVATE_KAS="${REPO_ROOT}/../meta-rpi4-jukebox/kas/private.yml"
    IMAGE="rpi4-qt6-image"
    ;;
  gateway)
    KAS_FILE="${REPO_ROOT}/kas/rpi4-gateway.yml"
    PRIVATE_KAS="${REPO_ROOT}/../meta-rpi4-gateway-private/kas/private.yml"
    IMAGE="rpi4-gateway-image"
    ;;
  *) echo "Usage: $0 [rpi4|rpi5|gateway]" >&2; exit 1 ;;
esac

FULL_KAS="${KAS_FILE}"
if [ -f "${PRIVATE_KAS}" ]; then
    cp "${PRIVATE_KAS}" "${LOCAL_KAS}"
    FULL_KAS="${KAS_FILE}:${LOCAL_KAS}"
fi

exec kas shell "${FULL_KAS}" -c "bitbake -c populate_sdk ${IMAGE}"
