SUMMARY = "Inter font family"
HOMEPAGE = "https://rsms.me/inter/"
LICENSE = "OFL-1.1"
LIC_FILES_CHKSUM = "file://LICENSE.txt;md5=082d8cc7db39783f598b7eda8c911f9d"

SRC_URI = "https://github.com/rsms/inter/releases/download/v${PV}/Inter-${PV}.zip"
SRC_URI[sha256sum] = "9883fdd4a49d4fb66bd8177ba6625ef9a64aa45899767dde3d36aa425756b11e"

S = "${UNPACKDIR}"

INHIBIT_DEFAULT_DEPS = "1"

inherit allarch fontcache

do_install() {
    install -d ${D}${datadir}/fonts/truetype/
    find ${UNPACKDIR} -name '*.ttf' -exec install -m 0644 {} ${D}${datadir}/fonts/truetype/ \;
}

FILES:${PN} = "${datadir}/fonts/truetype/"
