DESCRIPTION = "Gateway first-boot initialization: partition setup, config persistence"
LICENSE = "MIT"
LIC_FILES_CHKSUM = "file://${COMMON_LICENSE_DIR}/MIT;md5=0835ade698e0bcf8506ecda2f7b4f302"

RDEPENDS:${PN} = "parted e2fsprogs-resize2fs e2fsprogs-e2fsck e2fsprogs-mke2fs \
                   util-linux-findmnt util-linux-lsblk util-linux-blkid \
                   util-linux-partx"

SRC_URI = " \
    file://gateway-init.sh \
    file://gateway-init.service \
    file://data.mount \
"

do_install() {
    install -d ${D}${sbindir}
    install -m 0755 ${UNPACKDIR}/gateway-init.sh ${D}${sbindir}/gateway-init.sh

    install -d ${D}${systemd_system_unitdir}
    install -m 0644 ${UNPACKDIR}/gateway-init.service ${D}${systemd_system_unitdir}/gateway-init.service
    install -m 0644 ${UNPACKDIR}/data.mount ${D}${systemd_system_unitdir}/data.mount

    install -d ${D}${libdir}/systemd/system-preset
    printf 'enable gateway-init.service\nenable data.mount\n' \
        > ${D}${libdir}/systemd/system-preset/89-gateway-init.preset
}

FILES:${PN} = " \
    ${sbindir}/gateway-init.sh \
    ${systemd_system_unitdir}/gateway-init.service \
    ${systemd_system_unitdir}/data.mount \
    ${libdir}/systemd/system-preset/89-gateway-init.preset \
"
