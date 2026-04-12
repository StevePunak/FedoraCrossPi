DESCRIPTION = "nginx site configuration and web root for gateway admin UI"
LICENSE = "MIT"
LIC_FILES_CHKSUM = "file://${COMMON_LICENSE_DIR}/MIT;md5=0835ade698e0bcf8506ecda2f7b4f302"

RDEPENDS:${PN} = "nginx"

do_install() {
    # Site configs
    install -d ${D}${sysconfdir}/nginx/sites-available
    install -d ${D}${sysconfdir}/nginx/sites-enabled
    install -m 0644 ${THISDIR}/files/sites-available/default.conf \
        ${D}${sysconfdir}/nginx/sites-available/default.conf
    ln -s ../sites-available/default.conf ${D}${sysconfdir}/nginx/sites-enabled/default.conf

    # SSL template — activated after certbot runs
    install -m 0644 ${THISDIR}/files/sites-available/ssl.conf.template \
        ${D}${sysconfdir}/nginx/sites-available/ssl.conf.template

    # Web root with placeholder page
    install -d ${D}/var/www/gateway/html
    install -m 0644 ${THISDIR}/files/index.html ${D}/var/www/gateway/html/index.html

    # Enable nginx service via preset
    install -d ${D}${libdir}/systemd/system-preset
    printf 'enable nginx.service\n' \
        > ${D}${libdir}/systemd/system-preset/91-nginx.preset
}

FILES:${PN} = " \
    ${sysconfdir}/nginx/sites-available/ \
    ${sysconfdir}/nginx/sites-enabled/ \
    /var/www/gateway/ \
    ${libdir}/systemd/system-preset/91-nginx.preset \
"

CONFFILES:${PN} = " \
    ${sysconfdir}/nginx/sites-available/default.conf \
"
