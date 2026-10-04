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
  irrigation)
    KAS_FILE="${REPO_ROOT}/kas/rpi4-irrigation.yml:${REPO_ROOT}/kas/irrigation-wifi.yml"
    PRIVATE_KAS=""
    ;;
  *) echo "Usage: $0 [rpi4|rpi5|gateway|qemu-gateway|irrigation]" >&2; exit 1 ;;
esac

# Build the admin UI frontend bundle and download aarch64 backend wheels
# before the gateway image (recipe copies dist/ and wheels/).
if [ "${TARGET}" = "gateway" ] || [ "${TARGET}" = "qemu-gateway" ]; then
    FRONTEND_DIR="${REPO_ROOT}/gateway-admin/frontend"
    if [ -d "${FRONTEND_DIR}" ]; then
        echo "Building admin UI frontend..."
        (cd "${FRONTEND_DIR}" && npm install --silent && npm run build)
    fi
    BACKEND_DIR="${REPO_ROOT}/gateway-admin/backend"
    if [ -x "${BACKEND_DIR}/refresh-wheels.sh" ]; then
        echo "Downloading backend wheels..."
        "${BACKEND_DIR}/refresh-wheels.sh"
    fi
fi

if [ -n "${PRIVATE_KAS:-}" ] && [ -f "${PRIVATE_KAS}" ]; then
    cp "${PRIVATE_KAS}" "${LOCAL_KAS}"
    KAS_FILE="${KAS_FILE}:${LOCAL_KAS}"
fi

# The host's tar calls openat2, which pseudo cannot wrap, so packaging only
# works inside this container. The tree must be mounted at its host path:
# TMPDIR is recorded in build/tmp/saved_tmpdir, and a different mount point
# (kas-container uses /work) breaks every later build.
SRC_ROOT="$(cd "${REPO_ROOT}/.." && pwd)"
exec podman run --rm --userns=keep-id --pids-limit=-1 \
    -v "${SRC_ROOT}:${SRC_ROOT}" -w "$(cd "${REPO_ROOT}" && pwd)" \
    localhost/yocto-walnascar:ubuntu-22.04 \
    bash -lc "kas build '${KAS_FILE}'"
