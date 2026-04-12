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
    ;;
  rpi5)
    KAS_FILE="${REPO_ROOT}/kas/rpi5-qt6.yml"
    PRIVATE_KAS="${REPO_ROOT}/../meta-rpi4-jukebox/kas/private.yml"
    ;;
  gateway)
    KAS_FILE="${REPO_ROOT}/kas/rpi4-gateway.yml"
    PRIVATE_KAS="${REPO_ROOT}/../meta-rpi4-gateway-private/kas/private.yml"
    ;;
  qemu-gateway)
    KAS_FILE="${REPO_ROOT}/kas/qemu-gateway.yml"
    PRIVATE_KAS=""
    ;;
  *) echo "Usage: $0 [rpi4|rpi5|gateway|qemu-gateway]" >&2; exit 1 ;;
esac

if [ -n "${PRIVATE_KAS:-}" ] && [ -f "${PRIVATE_KAS}" ]; then
    cp "${PRIVATE_KAS}" "${LOCAL_KAS}"
    exec kas build "${KAS_FILE}:${LOCAL_KAS}"
else
    exec kas build "${KAS_FILE}"
fi
