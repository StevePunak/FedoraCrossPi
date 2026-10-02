DESCRIPTION = "TLS certificate for the irrigation web UI: self-signed fallback and Let's Encrypt issuance"
LICENSE = "MIT"
LIC_FILES_CHKSUM = "file://${COMMON_LICENSE_DIR}/MIT;md5=0835ade698e0bcf8506ecda2f7b4f302"

RDEPENDS:${PN} = "openssl-bin acme-sh"

SRC_URI = " \
    file://irrigation-ssl-init.sh \
    file://irrigation-ssl-init.service \
    file://irrigation-cert-issue.sh \
"
S = "${UNPACKDIR}"

do_install() {
    install -d ${D}${sbindir}
    install -m 0755 ${UNPACKDIR}/irrigation-ssl-init.sh ${D}${sbindir}/irrigation-ssl-init.sh
    install -m 0755 ${UNPACKDIR}/irrigation-cert-issue.sh ${D}${sbindir}/irrigation-cert-issue.sh

    install -d ${D}${systemd_system_unitdir}
    install -m 0644 ${UNPACKDIR}/irrigation-ssl-init.service ${D}${systemd_system_unitdir}/irrigation-ssl-init.service

    install -d ${D}${libdir}/systemd/system-preset
    printf 'enable irrigation-ssl-init.service\n' \
        > ${D}${libdir}/systemd/system-preset/91-irrigation-ssl.preset
}

FILES:${PN} = " \
    ${sbindir}/irrigation-ssl-init.sh \
    ${sbindir}/irrigation-cert-issue.sh \
    ${systemd_system_unitdir}/irrigation-ssl-init.service \
    ${libdir}/systemd/system-preset/91-irrigation-ssl.preset \
"
