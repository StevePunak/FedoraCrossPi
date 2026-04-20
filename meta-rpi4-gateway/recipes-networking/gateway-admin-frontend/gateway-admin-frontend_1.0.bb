DESCRIPTION = "Gateway admin web UI (React/TypeScript static bundle)"
LICENSE = "MIT"
LIC_FILES_CHKSUM = "file://${COMMON_LICENSE_DIR}/MIT;md5=0835ade698e0bcf8506ecda2f7b4f302"

# Build must have been run beforehand (scripts/build-image.sh handles this)
FRONTEND_DIST = "${THISDIR}/../../../gateway-admin/frontend/dist"

do_install() {
    if [ ! -d "${FRONTEND_DIST}" ]; then
        bbfatal "Frontend dist not found at ${FRONTEND_DIST}. Run 'npm run build' in gateway-admin/frontend before building the image."
    fi

    install -d ${D}/var/www/gateway/html
    cp -r ${FRONTEND_DIST}/* ${D}/var/www/gateway/html/
}

FILES:${PN} = "/var/www/gateway/"
