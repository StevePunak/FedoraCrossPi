DESCRIPTION = "Expand root partition to fill SD card on first boot"
LICENSE = "MIT"
LIC_FILES_CHKSUM = "file://${COMMON_LICENSE_DIR}/MIT;md5=0835ade698e0bcf8506ecda2f7b4f302"

RDEPENDS:${PN} = "parted e2fsprogs-resize2fs util-linux-findmnt util-linux-lsblk"

do_install() {
    install -d ${D}${sbindir}
    install -m 0755 ${THISDIR}/files/expand-rootfs.sh ${D}${sbindir}/expand-rootfs.sh

    install -d ${D}${systemd_system_unitdir}
    install -m 0644 ${THISDIR}/files/expand-rootfs.service ${D}${systemd_system_unitdir}/expand-rootfs.service

    install -d ${D}${libdir}/systemd/system-preset
    printf 'enable expand-rootfs.service\n' \
        > ${D}${libdir}/systemd/system-preset/89-expand-rootfs.preset
}

FILES:${PN} = " \
    ${sbindir}/expand-rootfs.sh \
    ${systemd_system_unitdir}/expand-rootfs.service \
    ${libdir}/systemd/system-preset/89-expand-rootfs.preset \
"
