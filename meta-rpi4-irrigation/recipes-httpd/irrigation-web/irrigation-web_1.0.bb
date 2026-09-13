DESCRIPTION = "Irrigation controller web UI (React static bundle)"
LICENSE = "MIT"
LIC_FILES_CHKSUM = "file://${COMMON_LICENSE_DIR}/MIT;md5=0835ade698e0bcf8506ecda2f7b4f302"

# The bundle is built outside Yocto, in the sibling irrigation repository.
# Override in a local.conf when the checkout lives elsewhere.
IRRIGATION_WEB_DIST ?= "${THISDIR}/../../../../irrigation/web/dist"

do_install() {
    if [ ! -d "${IRRIGATION_WEB_DIST}" ]; then
        bbfatal "Web bundle not found at ${IRRIGATION_WEB_DIST}. Run 'npm run build' in the irrigation repository's web/ directory before building the image, or set IRRIGATION_WEB_DIST."
    fi
    if [ ! -f "${IRRIGATION_WEB_DIST}/index.html" ]; then
        bbfatal "No index.html in ${IRRIGATION_WEB_DIST}. The directory exists but holds no bundle."
    fi

    install -d ${D}${localstatedir}/www/irrigation/html
    cp -r ${IRRIGATION_WEB_DIST}/* ${D}${localstatedir}/www/irrigation/html/
    # cp -r carries the builder's umask; pseudo only fixes ownership.
    chmod -R u=rwX,go=rX ${D}${localstatedir}/www/irrigation/html
}

# The :True is what makes bitbake walk this as a directory at TASKHASH
# time, every build, catching additions and deletions as well as content
# changes. Drop it and this silently goes back to tracking nothing, since
# IRRIGATION_WEB_DIST carries no SRC_URI entry of its own.
do_install[file-checksums] += "${IRRIGATION_WEB_DIST}:True"

FILES:${PN} = "${localstatedir}/www/irrigation/"
