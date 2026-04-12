#!/bin/sh
# Install certbot into a Python venv on first boot.
# Runs once and disables itself.

VENV_DIR="/opt/certbot"

if [ -x "${VENV_DIR}/bin/certbot" ]; then
    echo "certbot-setup: already installed, skipping"
    systemctl disable certbot-setup.service
    exit 0
fi

echo "certbot-setup: creating venv at ${VENV_DIR}"
python3 -m venv "${VENV_DIR}"

echo "certbot-setup: installing certbot and nginx plugin"
"${VENV_DIR}/bin/pip" install --upgrade pip
"${VENV_DIR}/bin/pip" install certbot certbot-nginx

echo "certbot-setup: done, disabling setup service"
systemctl disable certbot-setup.service
