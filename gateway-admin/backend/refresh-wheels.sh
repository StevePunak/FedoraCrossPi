#!/usr/bin/env bash
# Download aarch64 wheels for the gateway-admin backend so the image
# can install the venv offline at first boot (no DNS / no internet on
# the appliance at that point — DNS is what gateway-admin will *start*
# once running, so it can't be a prerequisite for it to start).
#
# Wheels are dropped into ./wheels/ and gitignored. The recipe copies
# them into the image; gateway-admin-setup.sh installs from this dir
# with --no-index --find-links.
#
# Run automatically by scripts/build-image.sh for the gateway target.
# Run manually if requirements.txt changes.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WHEELS_DIR="${SCRIPT_DIR}/wheels"
REQ_FILE="${SCRIPT_DIR}/requirements.txt"

# Target Python on the appliance image. Bump in lockstep with the
# python3 package shipped by poky/walnascar (3.13.x at time of writing).
TARGET_PYTHON="3.13"
TARGET_ABI="cp313"

# Multiple manylinux tags so pip can pick the freshest wheel that
# matches the appliance glibc. The actual glibc on the image is
# whatever poky/walnascar ships (currently glibc 2.40-ish), so the
# _2_28 wheels are fine.
PLATFORMS=(
    "manylinux2014_aarch64"
    "manylinux_2_17_aarch64"
    "manylinux_2_28_aarch64"
)

PLATFORM_ARGS=()
for p in "${PLATFORMS[@]}"; do
    PLATFORM_ARGS+=(--platform "$p")
done

rm -rf "${WHEELS_DIR}"
mkdir -p "${WHEELS_DIR}"

echo "refresh-wheels: downloading into ${WHEELS_DIR}"
pip3 download \
    --python-version "${TARGET_PYTHON}" \
    --abi "${TARGET_ABI}" \
    "${PLATFORM_ARGS[@]}" \
    --only-binary=:all: \
    -d "${WHEELS_DIR}" \
    -r "${REQ_FILE}"

echo "refresh-wheels: $(find "${WHEELS_DIR}" -name '*.whl' | wc -l) wheels staged"
