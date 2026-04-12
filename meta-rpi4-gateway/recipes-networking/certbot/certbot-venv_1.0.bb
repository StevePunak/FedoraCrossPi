DESCRIPTION = "Install certbot via pip venv on first boot with automatic renewal"
LICENSE = "MIT"
LIC_FILES_CHKSUM = "file://${COMMON_LICENSE_DIR}/MIT;md5=0835ade698e0bcf8506ecda2f7b4f302"

RDEPENDS:${PN} = "python3 python3-venv python3-pip openssl-bin nginx"

do_install() {
    # Setup script — creates venv and pip-installs certbot on first boot
    install -d ${D}${sbindir}
    install -m 0755 ${THISDIR}/files/certbot-setup.sh ${D}${sbindir}/certbot-setup.sh

    # Wrapper so 'certbot' works from PATH after setup completes
    install -m 0755 ${THISDIR}/files/certbot-wrapper.sh ${D}${sbindir}/certbot

    # First-boot setup service
    install -d ${D}${systemd_system_unitdir}
    install -m 0644 ${THISDIR}/files/certbot-setup.service ${D}${systemd_system_unitdir}/

    # Renewal timer and service
    install -m 0644 ${THISDIR}/files/certbot-renew.service ${D}${systemd_system_unitdir}/
    install -m 0644 ${THISDIR}/files/certbot-renew.timer ${D}${systemd_system_unitdir}/

    # Enable via presets
    install -d ${D}${libdir}/systemd/system-preset
    printf 'enable certbot-setup.service\nenable certbot-renew.timer\n' \
        > ${D}${libdir}/systemd/system-preset/91-certbot.preset
}

FILES:${PN} = " \
    ${sbindir}/certbot-setup.sh \
    ${sbindir}/certbot \
    ${systemd_system_unitdir}/certbot-setup.service \
    ${systemd_system_unitdir}/certbot-renew.service \
    ${systemd_system_unitdir}/certbot-renew.timer \
    ${libdir}/systemd/system-preset/91-certbot.preset \
"
