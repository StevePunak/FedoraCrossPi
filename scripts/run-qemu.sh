#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="${SCRIPT_DIR}/.."
KAS_FILE="${REPO_ROOT}/kas/qemu-gateway.yml"

# runqemu options: nographic for headless, slirp for unprivileged networking
# Use 'kvm' if available for near-native speed
QEMU_OPTS="nographic slirp"
if [ -w /dev/kvm ]; then
    QEMU_OPTS="nographic slirp kvm"
fi

exec kas shell "${KAS_FILE}" -c "runqemu ${QEMU_OPTS}"
