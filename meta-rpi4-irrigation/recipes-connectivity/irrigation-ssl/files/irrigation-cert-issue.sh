#!/bin/sh
# Issue the Let's Encrypt certificate for irrigation.punak.com through a
# GoDaddy DNS-01 challenge and install it where nginx reads it. Run once,
# by hand, after /data/acme/godaddy.env holds GD_Key and GD_Secret.
# acme-renew.timer renews it from then on, and the --reloadcmd recorded
# here is what puts each renewal in front of nginx.
set -e

FQDN=irrigation.punak.com
ACME_HOME=/data/acme
ENV_FILE="${ACME_HOME}/godaddy.env"

if [ ! -s "${ENV_FILE}" ]; then
    echo "irrigation-cert-issue: ${ENV_FILE} is missing; copy it from stilgar first" >&2
    exit 1
fi

set -a
. "${ENV_FILE}"
set +a

"${ACME_HOME}/acme.sh" --home "${ACME_HOME}" --server letsencrypt \
    --issue --dns dns_gd -d "${FQDN}" --keylength ec-256

"${ACME_HOME}/acme.sh" --home "${ACME_HOME}" --install-cert -d "${FQDN}" --ecc \
    --key-file /data/ssl/key.pem \
    --fullchain-file /data/ssl/cert.pem \
    --reloadcmd "systemctl reload nginx"
