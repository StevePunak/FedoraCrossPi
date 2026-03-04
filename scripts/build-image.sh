#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
KAS_FILE="${SCRIPT_DIR}/../kas/rpi4-qt6.yml"

exec kas build "${KAS_FILE}"
