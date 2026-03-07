DESCRIPTION = "systemd-networkd configuration for wired ethernet"
LICENSE = "MIT"
LIC_FILES_CHKSUM = "file://${COMMON_LICENSE_DIR}/MIT;md5=0835ade698e0bcf8506ecda2f7b4f302"

SRC_URI = "file://10-wired.network"

inherit systemd

SYSTEMD_SERVICE:${PN} = "systemd-networkd.service systemd-resolved.service"
SYSTEMD_AUTO_ENABLE = "enable"

do_install() {
    install -d ${D}${sysconfdir}/systemd/network
    install -m 0644 ${WORKDIR}/10-wired.network ${D}${sysconfdir}/systemd/network/

    # Point resolv.conf to systemd-resolved
    install -d ${D}${sysconfdir}
    ln -sf ../run/systemd/resolve/stub-resolv.conf ${D}${sysconfdir}/resolv.conf
}

FILES:${PN} = "${sysconfdir}/systemd/network/ ${sysconfdir}/resolv.conf"
