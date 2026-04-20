#!/bin/sh
# Generate a self-signed TLS certificate for the gateway admin UI.
#
# The cert is stored in /data/ssl/ so it persists across reflashing. It's
# regenerated if:
#   - Missing
#   - Expired or within 30 days of expiry
#   - Hostname or IP has changed since last generation
set -e

SSL_DIR="/data/ssl"
CERT="${SSL_DIR}/cert.pem"
KEY="${SSL_DIR}/key.pem"
STATE="${SSL_DIR}/.identity"
DAYS=3650

mkdir -p "${SSL_DIR}"
chmod 700 "${SSL_DIR}"

HOSTNAME_VAL=$(hostname)
IPS=$(ip -4 -o addr show scope global 2>/dev/null | awk '{print $4}' | cut -d/ -f1)
IDENTITY="host=${HOSTNAME_VAL} ips=$(echo ${IPS} | tr ' ' ',')"

# Decide whether to regenerate
REGENERATE=1
if [ -f "${CERT}" ] && [ -f "${KEY}" ] && [ -f "${STATE}" ]; then
    OLD_IDENTITY=$(cat "${STATE}")
    if openssl x509 -checkend $((30*86400)) -noout -in "${CERT}" 2>/dev/null \
        && [ "${OLD_IDENTITY}" = "${IDENTITY}" ]; then
        echo "gateway-ssl-init: existing cert is valid for ${IDENTITY}, keeping it"
        REGENERATE=0
    fi
fi

if [ "${REGENERATE}" -eq 0 ]; then
    exit 0
fi

echo "gateway-ssl-init: generating self-signed cert for ${IDENTITY}"

CONF=$(mktemp)
cat > "${CONF}" << EOF
[req]
distinguished_name = dn
req_extensions = v3_req
prompt = no

[dn]
CN = ${HOSTNAME_VAL}
O  = Gateway Admin

[v3_req]
subjectAltName = @alt_names
keyUsage = digitalSignature, keyEncipherment
extendedKeyUsage = serverAuth
basicConstraints = CA:false

[alt_names]
DNS.1 = ${HOSTNAME_VAL}
DNS.2 = ${HOSTNAME_VAL}.local
DNS.3 = localhost
EOF

i=1
for ip in ${IPS} 127.0.0.1; do
    echo "IP.${i} = ${ip}" >> "${CONF}"
    i=$((i + 1))
done

openssl req -x509 -new -nodes -newkey rsa:2048 \
    -keyout "${KEY}" -out "${CERT}" \
    -days "${DAYS}" -sha256 \
    -config "${CONF}" -extensions v3_req 2>/dev/null

rm -f "${CONF}"
chmod 600 "${KEY}"
chmod 644 "${CERT}"
echo "${IDENTITY}" > "${STATE}"

echo "gateway-ssl-init: cert written to ${CERT}"

# If nginx is running, reload so it picks up the new cert
if systemctl is-active --quiet nginx; then
    systemctl reload-or-restart nginx
fi
