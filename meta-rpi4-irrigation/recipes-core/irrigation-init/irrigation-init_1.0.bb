DESCRIPTION = "Irrigation controller service unit, default configuration and state directory"
LICENSE = "MIT"
LIC_FILES_CHKSUM = "file://${COMMON_LICENSE_DIR}/MIT;md5=0835ade698e0bcf8506ecda2f7b4f302"

SRC_URI = " \
    file://irrigationd.service \
    file://irrigationd.ini \
"
S = "${UNPACKDIR}"

do_install() {
    install -d ${D}${sysconfdir}
    install -m 0644 ${UNPACKDIR}/irrigationd.ini ${D}${sysconfdir}/irrigationd.ini

    install -d ${D}${systemd_system_unitdir}
    install -m 0644 ${UNPACKDIR}/irrigationd.service ${D}${systemd_system_unitdir}/irrigationd.service

    # var-volatile-lib.service only skips /var/lib because
    # ConditionPathIsReadWrite=!/var/lib is false on a writable rootfs. A
    # read-only-rootfs pass makes this directory tmpfs-backed, and every
    # schedule the user entered is gone at the next reboot.
    install -d -m 0755 ${D}${localstatedir}/lib/irrigationd

    install -d ${D}${libdir}/systemd/system-preset
    printf 'enable irrigationd.service\n' \
        > ${D}${libdir}/systemd/system-preset/90-irrigationd.preset
}

FILES:${PN} = " \
    ${sysconfdir}/irrigationd.ini \
    ${systemd_system_unitdir}/irrigationd.service \
    ${localstatedir}/lib/irrigationd \
    ${libdir}/systemd/system-preset/90-irrigationd.preset \
"

CONFFILES:${PN} = "${sysconfdir}/irrigationd.ini"
