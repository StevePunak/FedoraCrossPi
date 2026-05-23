FILESEXTRAPATHS:prepend := "${THISDIR}/files:"

# http2: enabled in the gateway's TLS server block.
# http-auth-request: required by the per-app reverse-proxy drop-ins generated
# by gateway-admin, which gate each app UI behind
# `auth_request /api/auth/check` against the admin backend.
PACKAGECONFIG:append = " http2 http-auth-request"

# Remove the upstream-shipped `default_server` site — our gateway default.conf
# provides its own `listen 80 default_server` block and nginx refuses to start
# with two server blocks claiming the same port as default.
do_install:append() {
    rm -f ${D}${sysconfdir}/nginx/sites-enabled/default_server
    rm -f ${D}${sysconfdir}/nginx/sites-available/default_server
}
