#!/bin/sh
# Install admin backend Python dependencies into a venv on first boot.
# All wheels are bundled in the image (built by scripts/build-image.sh
# before kas build, staged into the gateway-admin-backend recipe), so
# this runs entirely offline — first-boot network isn't required.
set -e

VENV_DIR="/opt/gateway-admin/.venv"
REQ_FILE="/opt/gateway-admin/requirements.txt"
WHEELS_DIR="/opt/gateway-admin/wheels"

if [ -x "${VENV_DIR}/bin/uvicorn" ]; then
    echo "gateway-admin-setup: venv already exists, skipping"
    systemctl disable gateway-admin-setup.service
    exit 0
fi

echo "gateway-admin-setup: creating venv at ${VENV_DIR}"
python3 -m venv "${VENV_DIR}"

echo "gateway-admin-setup: installing Python dependencies offline from ${WHEELS_DIR}"
"${VENV_DIR}/bin/pip" install --no-index --find-links="${WHEELS_DIR}" -r "${REQ_FILE}"

echo "gateway-admin-setup: done"
systemctl disable gateway-admin-setup.service
