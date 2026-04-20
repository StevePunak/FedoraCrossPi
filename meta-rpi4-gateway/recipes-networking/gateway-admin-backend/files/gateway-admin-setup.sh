#!/bin/sh
# Install admin backend Python dependencies into a venv on first boot.
set -e

VENV_DIR="/opt/gateway-admin/.venv"
REQ_FILE="/opt/gateway-admin/requirements.txt"

if [ -x "${VENV_DIR}/bin/uvicorn" ]; then
    echo "gateway-admin-setup: venv already exists, skipping"
    systemctl disable gateway-admin-setup.service
    exit 0
fi

echo "gateway-admin-setup: creating venv at ${VENV_DIR}"
python3 -m venv "${VENV_DIR}"

echo "gateway-admin-setup: installing Python dependencies"
"${VENV_DIR}/bin/pip" install --upgrade pip
"${VENV_DIR}/bin/pip" install -r "${REQ_FILE}"

echo "gateway-admin-setup: done"
systemctl disable gateway-admin-setup.service
