DESCRIPTION = "First-boot creation and mounting of the persistent /data partition"
LICENSE = "MIT"
LIC_FILES_CHKSUM = "file://${COMMON_LICENSE_DIR}/MIT;md5=0835ade698e0bcf8506ecda2f7b4f302"

RDEPENDS:${PN} = "parted e2fsprogs-resize2fs e2fsprogs-e2fsck e2fsprogs-mke2fs \
                  util-linux-findmnt util-linux-lsblk util-linux-blkid \
                  util-linux-blockdev"

SRC_URI = " \
    file://irrigation-data-init.sh \
    file://irrigation-data-init.service \
    file://data.mount \
"
S = "${UNPACKDIR}"

do_install() {
    install -d ${D}${sbindir}
    install -m 0755 ${UNPACKDIR}/irrigation-data-init.sh ${D}${sbindir}/irrigation-data-init.sh

    install -d ${D}${systemd_system_unitdir}
    install -m 0644 ${UNPACKDIR}/irrigation-data-init.service ${D}${systemd_system_unitdir}/irrigation-data-init.service
    install -m 0644 ${UNPACKDIR}/data.mount ${D}${systemd_system_unitdir}/data.mount

    install -d ${D}${libdir}/systemd/system-preset
    printf 'enable irrigation-data-init.service\nenable data.mount\n' \
        > ${D}${libdir}/systemd/system-preset/89-irrigation-data.preset
}

FILES:${PN} = " \
    ${sbindir}/irrigation-data-init.sh \
    ${systemd_system_unitdir}/irrigation-data-init.service \
    ${systemd_system_unitdir}/data.mount \
    ${libdir}/systemd/system-preset/89-irrigation-data.preset \
"
