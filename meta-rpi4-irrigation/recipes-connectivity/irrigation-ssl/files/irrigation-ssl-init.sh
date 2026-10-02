#!/bin/sh
# Give nginx a certificate to start with: a self-signed one, written only
# when /data/ssl holds none. Once irrigation-cert-issue.sh has installed a
# Let's Encrypt certificate here this script never touches it again;
# overwriting it would put a browser warning back on a working site.
set -e

SSL_DIR=/data/ssl
CERT="${SSL_DIR}/cert.pem"
KEY="${SSL_DIR}/key.pem"
FQDN=irrigation.punak.com
HOST=$(cat /etc/hostname)

install -d -m 700 "${SSL_DIR}"

if [ -s "${CERT}" ] && [ -s "${KEY}" ]; then
    exit 0
fi

echo "irrigation-ssl-init: no certificate in ${SSL_DIR}, generating a self-signed one for ${FQDN}"

CONF=$(mktemp)
cat > "${CONF}" << EOF
[req]
distinguished_name = dn
prompt = no

[dn]
CN = ${FQDN}

[v3_req]
subjectAltName = DNS:${FQDN},DNS:${HOST},DNS:${HOST}.local,DNS:localhost,IP:127.0.0.1
keyUsage = digitalSignature, keyEncipherment
extendedKeyUsage = serverAuth
basicConstraints = CA:false
EOF

openssl req -x509 -new -nodes -newkey ec -pkeyopt ec_paramgen_curve:prime256v1 \
    -keyout "${KEY}" -out "${CERT}" -days 3650 -sha256 \
    -config "${CONF}" -extensions v3_req 2>/dev/null
rm -f "${CONF}"
chmod 600 "${KEY}"
chmod 644 "${CERT}"
