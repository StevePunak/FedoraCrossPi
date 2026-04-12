#!/bin/sh
# Wrapper to invoke certbot from its venv
VENV_DIR="/opt/certbot"

if [ ! -x "${VENV_DIR}/bin/certbot" ]; then
    echo "certbot is not installed yet. Run: systemctl start certbot-setup" >&2
    exit 1
fi

exec "${VENV_DIR}/bin/certbot" "$@"
