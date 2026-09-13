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
    # cp -r carries the builder's umask; pseudo only fixes ownership, not mode.
    chmod -R u=rwX,go=rX ${D}${localstatedir}/www/irrigation/html
}

# IRRIGATION_WEB_DIST carries no SRC_URI entry, so removing this block
# does not fail the build — it silently ships whatever bundle sstate
# cached the first time, no matter what npm run build produces later.
python() {
    import os
    dist = d.getVar("IRRIGATION_WEB_DIST")
    checksums = []
    if dist and os.path.isdir(dist):
        for root, _dirs, files in os.walk(dist):
            for name in files:
                checksums.append("%s:True" % os.path.join(root, name))
    d.appendVarFlag("do_install", "file-checksums", " " + " ".join(checksums))
}

FILES:${PN} = "${localstatedir}/www/irrigation/"
