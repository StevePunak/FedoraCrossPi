#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
KAS_FILE="${SCRIPT_DIR}/../kas/rpi4-qt6.yml"

# Builds the Qt 6.10.1 cross-compile SDK installer for Fedora 42 -> RPi 5
# Output: build/tmp/deploy/sdk/poky-glibc-x86_64-rpi4-qt6-image-cortexa76-raspberrypi4-64-toolchain-*.sh
exec kas shell "${KAS_FILE}" -- bitbake -c populate_sdk rpi4-qt6-image
