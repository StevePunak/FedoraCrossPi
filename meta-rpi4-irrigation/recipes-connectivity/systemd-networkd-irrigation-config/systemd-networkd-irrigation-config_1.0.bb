DESCRIPTION = "systemd-networkd DHCP configuration for the irrigation controller"
LICENSE = "MIT"
LIC_FILES_CHKSUM = "file://${COMMON_LICENSE_DIR}/MIT;md5=0835ade698e0bcf8506ecda2f7b4f302"

RCONFLICTS:${PN} = "systemd-networkd-config systemd-networkd-gateway-config"

SRC_URI = " \
    file://10-wired.network \
    file://20-wireless.network \
"

do_install() {
    install -d ${D}${sysconfdir}/systemd/network
    install -m 0644 ${UNPACKDIR}/10-wired.network ${D}${sysconfdir}/systemd/network/
    install -m 0644 ${UNPACKDIR}/20-wireless.network ${D}${sysconfdir}/systemd/network/

    install -d ${D}${libdir}/systemd/system-preset
    printf 'enable systemd-networkd.service\nenable systemd-resolved.service\n' \
        > ${D}${libdir}/systemd/system-preset/90-networkd.preset

    install -d ${D}${sysconfdir}
    ln -sf ../run/systemd/resolve/stub-resolv.conf ${D}${sysconfdir}/resolv.conf
}

FILES:${PN} = " \
    ${sysconfdir}/systemd/network/ \
    ${sysconfdir}/resolv.conf \
    ${libdir}/systemd/system-preset/90-networkd.preset \
"

CONFFILES:${PN} = " \
    ${sysconfdir}/systemd/network/10-wired.network \
    ${sysconfdir}/systemd/network/20-wireless.network \
"
