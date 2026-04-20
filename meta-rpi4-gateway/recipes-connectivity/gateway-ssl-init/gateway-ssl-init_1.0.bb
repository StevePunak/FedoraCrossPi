DESCRIPTION = "Generate self-signed TLS cert for gateway admin UI"
LICENSE = "MIT"
LIC_FILES_CHKSUM = "file://${COMMON_LICENSE_DIR}/MIT;md5=0835ade698e0bcf8506ecda2f7b4f302"

RDEPENDS:${PN} = "openssl-bin iproute2"

SRC_URI = " \
    file://gateway-ssl-init.sh \
    file://gateway-ssl-init.service \
"

do_install() {
    install -d ${D}${sbindir}
    install -m 0755 ${UNPACKDIR}/gateway-ssl-init.sh ${D}${sbindir}/gateway-ssl-init.sh

    install -d ${D}${systemd_system_unitdir}
    install -m 0644 ${UNPACKDIR}/gateway-ssl-init.service ${D}${systemd_system_unitdir}/

    install -d ${D}${libdir}/systemd/system-preset
    printf 'enable gateway-ssl-init.service\n' \
        > ${D}${libdir}/systemd/system-preset/90-gateway-ssl-init.preset
}

FILES:${PN} = " \
    ${sbindir}/gateway-ssl-init.sh \
    ${systemd_system_unitdir}/gateway-ssl-init.service \
    ${libdir}/systemd/system-preset/90-gateway-ssl-init.preset \
"
