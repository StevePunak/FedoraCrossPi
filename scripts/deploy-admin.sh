#!/usr/bin/env bash
# Deploy gateway-admin backend + frontend to a running gateway Pi.
# Usage: ./scripts/deploy-admin.sh [host] [user]
#   default host: 192.168.0.2
#   default user: gateway (use "root" for pre-hardening images)

set -euo pipefail

HOST="${1:-192.168.0.2}"
USER="${2:-gateway}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="${SCRIPT_DIR}/.."

# Use the SSH_KEY env var to force a specific key; otherwise rely on ssh-agent
# and the user's default identities.
SSH_OPTS=(
    -o StrictHostKeyChecking=no
    -o UserKnownHostsFile=/dev/null
)
if [ -n "${SSH_KEY:-}" ]; then
    SSH_OPTS+=(-o IdentitiesOnly=yes -i "${SSH_KEY}")
fi

# If we're gateway (non-root), remote commands that touch root-owned paths
# need sudo. For SSH key login + passworded sudo to work without prompting,
# sudo needs to be configured NOPASSWD, or the user must pre-auth via SSH
# terminal. We assume password-prompted sudo; use -t for a pty.
SUDO=""
if [ "${USER}" != "root" ]; then
    SUDO="sudo"
fi

REMOTE_RSYNC="${SUDO:+${SUDO} }rsync"

echo "=== Deploying backend to ${USER}@${HOST} ==="
rsync -az --delete \
    -e "ssh ${SSH_OPTS[*]}" \
    --rsync-path="${REMOTE_RSYNC}" \
    "${REPO_ROOT}/gateway-admin/backend/app/" \
    "${USER}@${HOST}:/opt/gateway-admin/app/"

rsync -az \
    -e "ssh ${SSH_OPTS[*]}" \
    --rsync-path="${REMOTE_RSYNC}" \
    "${REPO_ROOT}/gateway-admin/backend/requirements.txt" \
    "${USER}@${HOST}:/opt/gateway-admin/requirements.txt"

echo "=== Installing any new backend dependencies ==="
ssh "${SSH_OPTS[@]}" "${USER}@${HOST}" \
    "${SUDO} /opt/gateway-admin/.venv/bin/pip install -q -r /opt/gateway-admin/requirements.txt"

echo "=== Building frontend ==="
(cd "${REPO_ROOT}/gateway-admin/frontend" && npm run build)

echo "=== Deploying frontend to ${USER}@${HOST} ==="
rsync -az --delete \
    -e "ssh ${SSH_OPTS[*]}" \
    --rsync-path="${REMOTE_RSYNC}" \
    "${REPO_ROOT}/gateway-admin/frontend/dist/" \
    "${USER}@${HOST}:/var/www/gateway/html/"

echo "=== Restarting backend ==="
ssh "${SSH_OPTS[@]}" "${USER}@${HOST}" "${SUDO} systemctl restart gateway-admin"

echo "=== Done ==="
