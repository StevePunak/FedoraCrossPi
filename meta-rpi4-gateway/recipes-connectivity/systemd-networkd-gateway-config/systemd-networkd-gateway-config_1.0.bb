DESCRIPTION = "systemd-networkd static IP configuration for gateway appliance"
LICENSE = "MIT"
LIC_FILES_CHKSUM = "file://${COMMON_LICENSE_DIR}/MIT;md5=0835ade698e0bcf8506ecda2f7b4f302"

# Conflicts with the DHCP-based config from meta-rpi4-custom
RCONFLICTS:${PN} = "systemd-networkd-config"

do_install() {
    install -d ${D}${sysconfdir}/systemd/network
    install -m 0644 ${THISDIR}/files/10-wired-static.network ${D}${sysconfdir}/systemd/network/

    # Enable systemd-networkd via preset (no systemd-resolved — dnsmasq handles DNS)
    install -d ${D}${libdir}/systemd/system-preset
    printf 'enable systemd-networkd.service\ndisable systemd-resolved.service\n' \
        > ${D}${libdir}/systemd/system-preset/90-networkd.preset

    # Point resolv.conf to localhost (dnsmasq)
    install -d ${D}${sysconfdir}
    printf 'nameserver 127.0.0.1\n' > ${D}${sysconfdir}/resolv.conf
}

FILES:${PN} = " \
    ${sysconfdir}/systemd/network/ \
    ${sysconfdir}/resolv.conf \
    ${libdir}/systemd/system-preset/90-networkd.preset \
"

CONFFILES:${PN} = "${sysconfdir}/systemd/network/10-wired-static.network"
