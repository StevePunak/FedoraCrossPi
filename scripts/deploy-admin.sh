#!/usr/bin/env bash
# Deploy gateway-admin backend + frontend to a running gateway Pi.
# Usage: ./scripts/deploy-admin.sh [host]   (default: 192.168.0.82)

set -euo pipefail

HOST="${1:-192.168.0.82}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="${SCRIPT_DIR}/.."
KEY="${HOME}/.ssh/rpi4-key"

SSH_OPTS=(
    -o IdentitiesOnly=yes
    -o StrictHostKeyChecking=no
    -o UserKnownHostsFile=/dev/null
    -i "${KEY}"
)

echo "=== Deploying backend to ${HOST} ==="
rsync -az --delete \
    -e "ssh ${SSH_OPTS[*]}" \
    "${REPO_ROOT}/gateway-admin/backend/app/" \
    "root@${HOST}:/opt/gateway-admin/app/"

rsync -az \
    -e "ssh ${SSH_OPTS[*]}" \
    "${REPO_ROOT}/gateway-admin/backend/requirements.txt" \
    "root@${HOST}:/opt/gateway-admin/requirements.txt"

echo "=== Installing any new backend dependencies ==="
ssh "${SSH_OPTS[@]}" "root@${HOST}" \
    "/opt/gateway-admin/.venv/bin/pip install -q -r /opt/gateway-admin/requirements.txt"

echo "=== Building frontend ==="
(cd "${REPO_ROOT}/gateway-admin/frontend" && npm run build)

echo "=== Deploying frontend to ${HOST} ==="
rsync -az --delete \
    -e "ssh ${SSH_OPTS[*]}" \
    "${REPO_ROOT}/gateway-admin/frontend/dist/" \
    "root@${HOST}:/var/www/gateway/html/"

echo "=== Restarting backend ==="
ssh "${SSH_OPTS[@]}" "root@${HOST}" "systemctl restart gateway-admin"

echo "=== Done ==="
