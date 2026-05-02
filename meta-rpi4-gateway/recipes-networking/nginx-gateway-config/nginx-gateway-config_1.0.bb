DESCRIPTION = "nginx site configuration for gateway admin UI"
LICENSE = "MIT"
LIC_FILES_CHKSUM = "file://${COMMON_LICENSE_DIR}/MIT;md5=0835ade698e0bcf8506ecda2f7b4f302"

RDEPENDS:${PN} = "nginx"

SRC_URI = " \
    file://sites-available/default.conf \
"

do_install() {
    install -d ${D}${sysconfdir}/nginx/sites-available
    install -d ${D}${sysconfdir}/nginx/sites-enabled
    install -m 0644 ${UNPACKDIR}/sites-available/default.conf \
        ${D}${sysconfdir}/nginx/sites-available/default.conf
    ln -s ../sites-available/default.conf ${D}${sysconfdir}/nginx/sites-enabled/default.conf

    # Drop-ins from the app installer land here. Created empty so nginx's
    # include glob matches at startup even before any app is installed.
    install -d ${D}${sysconfdir}/nginx/locations.d/apps

    install -d ${D}${libdir}/systemd/system-preset
    printf 'enable nginx.service\n' \
        > ${D}${libdir}/systemd/system-preset/91-nginx.preset
}

FILES:${PN} = " \
    ${sysconfdir}/nginx/sites-available/ \
    ${sysconfdir}/nginx/sites-enabled/ \
    ${sysconfdir}/nginx/locations.d/ \
    ${libdir}/systemd/system-preset/91-nginx.preset \
"

CONFFILES:${PN} = " \
    ${sysconfdir}/nginx/sites-available/default.conf \
"
