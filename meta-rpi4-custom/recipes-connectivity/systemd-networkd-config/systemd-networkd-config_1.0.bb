DESCRIPTION = "systemd-networkd configuration for wired and wireless ethernet"
LICENSE = "MIT"
LIC_FILES_CHKSUM = "file://${COMMON_LICENSE_DIR}/MIT;md5=0835ade698e0bcf8506ecda2f7b4f302"

do_install() {
    install -d ${D}${sysconfdir}/systemd/network
    install -m 0644 ${THISDIR}/files/10-wired.network ${D}${sysconfdir}/systemd/network/
    install -m 0644 ${THISDIR}/files/20-wireless.network ${D}${sysconfdir}/systemd/network/

    # Enable systemd-networkd and systemd-resolved via preset
    install -d ${D}${libdir}/systemd/system-preset
    printf 'enable systemd-networkd.service\nenable systemd-resolved.service\n' \
        > ${D}${libdir}/systemd/system-preset/90-networkd.preset

    # Point resolv.conf to systemd-resolved
    install -d ${D}${sysconfdir}
    ln -sf ../run/systemd/resolve/stub-resolv.conf ${D}${sysconfdir}/resolv.conf
}

FILES:${PN} = " \
    ${sysconfdir}/systemd/network/ \
    ${sysconfdir}/resolv.conf \
    ${libdir}/systemd/system-preset/90-networkd.preset \
"
