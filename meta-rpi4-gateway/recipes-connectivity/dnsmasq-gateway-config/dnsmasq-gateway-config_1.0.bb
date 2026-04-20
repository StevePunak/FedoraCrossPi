DESCRIPTION = "Enable dnsmasq service for gateway appliance"
LICENSE = "MIT"
LIC_FILES_CHKSUM = "file://${COMMON_LICENSE_DIR}/MIT;md5=0835ade698e0bcf8506ecda2f7b4f302"

RDEPENDS:${PN} = "dnsmasq"

do_install() {
    # Enable dnsmasq service via preset
    install -d ${D}${libdir}/systemd/system-preset
    printf 'disable dnsmasq.service\n' \
        > ${D}${libdir}/systemd/system-preset/91-dnsmasq.preset
}

FILES:${PN} = " \
    ${libdir}/systemd/system-preset/91-dnsmasq.preset \
"
