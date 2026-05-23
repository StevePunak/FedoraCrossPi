DESCRIPTION = "Gateway admin FastAPI backend"
LICENSE = "MIT"
LIC_FILES_CHKSUM = "file://${COMMON_LICENSE_DIR}/MIT;md5=0835ade698e0bcf8506ecda2f7b4f302"

RDEPENDS:${PN} = "python3 python3-venv python3-pip"

SRC_URI = " \
    file://gateway-admin-setup.sh \
    file://gateway-admin-setup.service \
    file://gateway-admin.service \
"

INSTALL_PREFIX = "/opt/gateway-admin"
BACKEND_SRC = "${THISDIR}/../../../gateway-admin/backend"

do_install() {
    # Install app source from repo checkout
    install -d ${D}${INSTALL_PREFIX}
    cp -r ${BACKEND_SRC}/app ${D}${INSTALL_PREFIX}/app
    install -m 0644 ${BACKEND_SRC}/requirements.txt ${D}${INSTALL_PREFIX}/requirements.txt

    # Bundle aarch64 wheels so first-boot venv setup is fully offline.
    # build-image.sh runs gateway-admin/backend/refresh-wheels.sh before
    # kas build to populate ${BACKEND_SRC}/wheels.
    if [ ! -d "${BACKEND_SRC}/wheels" ] || [ -z "$(ls -A ${BACKEND_SRC}/wheels 2>/dev/null)" ]; then
        bbfatal "Backend wheels not found at ${BACKEND_SRC}/wheels. Run gateway-admin/backend/refresh-wheels.sh before building (scripts/build-image.sh does this automatically)."
    fi
    install -d ${D}${INSTALL_PREFIX}/wheels
    cp ${BACKEND_SRC}/wheels/*.whl ${D}${INSTALL_PREFIX}/wheels/

    # Remove any dev artifacts
    rm -rf ${D}${INSTALL_PREFIX}/app/__pycache__ || true
    find ${D}${INSTALL_PREFIX}/app -name __pycache__ -type d -exec rm -rf {} + || true
    find ${D}${INSTALL_PREFIX}/app -name '*.pyc' -delete || true

    # First-boot venv setup script
    install -d ${D}${sbindir}
    install -m 0755 ${UNPACKDIR}/gateway-admin-setup.sh ${D}${sbindir}/gateway-admin-setup.sh

    # Systemd units
    install -d ${D}${systemd_system_unitdir}
    install -m 0644 ${UNPACKDIR}/gateway-admin-setup.service ${D}${systemd_system_unitdir}/
    install -m 0644 ${UNPACKDIR}/gateway-admin.service ${D}${systemd_system_unitdir}/

    # Enable via preset
    install -d ${D}${libdir}/systemd/system-preset
    printf 'enable gateway-admin-setup.service\nenable gateway-admin.service\n' \
        > ${D}${libdir}/systemd/system-preset/92-gateway-admin.preset
}

FILES:${PN} = " \
    ${INSTALL_PREFIX} \
    ${sbindir}/gateway-admin-setup.sh \
    ${systemd_system_unitdir}/gateway-admin-setup.service \
    ${systemd_system_unitdir}/gateway-admin.service \
    ${libdir}/systemd/system-preset/92-gateway-admin.preset \
"
