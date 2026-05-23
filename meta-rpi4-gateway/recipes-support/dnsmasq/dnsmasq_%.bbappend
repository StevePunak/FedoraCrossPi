FILESEXTRAPATHS:prepend := "${THISDIR}/files:"

SRC_URI += " \
    file://dnsmasq-gateway.conf \
    file://01-dns.conf \
    file://02-dhcp.conf \
"

do_install:append() {
    # Replace upstream example config with our gateway config
    install -m 0644 ${UNPACKDIR}/dnsmasq-gateway.conf ${D}${sysconfdir}/dnsmasq.conf

    # Install drop-in config directory
    install -d ${D}${sysconfdir}/dnsmasq.d
    install -m 0644 ${UNPACKDIR}/01-dns.conf ${D}${sysconfdir}/dnsmasq.d/
    install -m 0644 ${UNPACKDIR}/02-dhcp.conf ${D}${sysconfdir}/dnsmasq.d/
}

# Don't auto-enable at boot: dnsmasq is reconciled into the configured
# state by gateway-admin once /data is mounted and the persisted config
# is loaded. Premature startup with the recipe-shipped defaults would
# conflict with an upstream DHCP server on the same LAN.
SYSTEMD_AUTO_ENABLE = "disable"

FILES:${PN} += "${sysconfdir}/dnsmasq.d/"
