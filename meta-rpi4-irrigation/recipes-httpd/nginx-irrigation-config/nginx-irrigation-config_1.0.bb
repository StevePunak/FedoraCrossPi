DESCRIPTION = "nginx site configuration for the irrigation controller"
LICENSE = "MIT"
LIC_FILES_CHKSUM = "file://${COMMON_LICENSE_DIR}/MIT;md5=0835ade698e0bcf8506ecda2f7b4f302"

RDEPENDS:${PN} = "nginx"

SRC_URI = "file://sites-available/irrigation.conf"

do_install() {
    install -d ${D}${sysconfdir}/nginx/sites-available
    install -d ${D}${sysconfdir}/nginx/sites-enabled
    install -m 0644 ${UNPACKDIR}/sites-available/irrigation.conf \
        ${D}${sysconfdir}/nginx/sites-available/irrigation.conf
    ln -s ../sites-available/irrigation.conf \
        ${D}${sysconfdir}/nginx/sites-enabled/irrigation.conf

    install -d ${D}${libdir}/systemd/system-preset
    printf 'enable nginx.service\n' \
        > ${D}${libdir}/systemd/system-preset/91-nginx.preset
}

FILES:${PN} = " \
    ${sysconfdir}/nginx/sites-available/ \
    ${sysconfdir}/nginx/sites-enabled/ \
    ${libdir}/systemd/system-preset/91-nginx.preset \
"

CONFFILES:${PN} = "${sysconfdir}/nginx/sites-available/irrigation.conf"
