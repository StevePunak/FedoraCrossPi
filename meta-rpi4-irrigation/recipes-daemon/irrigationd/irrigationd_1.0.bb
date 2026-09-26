DESCRIPTION = "Irrigation controller daemon: owns the eight valve outputs and serves the REST API"
LICENSE = "MIT"
LIC_FILES_CHKSUM = "file://${COMMON_LICENSE_DIR}/MIT;md5=0835ade698e0bcf8506ecda2f7b4f302"

DEPENDS = "qtbase qthttpserver libgpiod"

# gitsm, because the Kanoop libraries are submodules consumed through
# add_subdirectory. A git:// fetch configures against empty directories.
# The container has no SSH client, so this and every URL in the
# superproject's .gitmodules must stay https.
SRC_URI = "gitsm://github.com/StevePunak/irrigation.git;protocol=https;branch=feature/superproject"
SRCREV = "a9de02ed2b3c8427873f382238295464901249a3"

S = "${WORKDIR}/git"

inherit qt6-cmake pkgconfig

EXTRA_OECMAKE += " \
    -DIRRIGATION_USE_MOLD=OFF \
    -DBUILD_TESTING=OFF \
"

# irrigation-init owns /usr/lib/systemd/system/irrigationd.service. The
# superproject installs its own copy to the same path; shipping both fails
# do_rootfs with a file conflict between the two packages.
do_install:append() {
    rm ${D}${prefix}/lib/systemd/system/irrigationd.service
    rmdir ${D}${prefix}/lib/systemd/system ${D}${prefix}/lib/systemd

    # The superproject adds the Kanoop libraries EXCLUDE_FROM_ALL, so their
    # own install rules never run. The daemon links them shared.
    install -d ${D}${libdir}
    for lib in KanoopCommonQt KanoopDatabaseQt KanoopPiQt; do
        cp -P ${B}/${lib}/lib${lib}.so.* ${D}${libdir}/
    done
}

# The SQLite driver is a dlopened plugin, so no shared-library scan can
# discover it. Without this the daemon starts and fails its first query.
RDEPENDS:${PN} += "qtbase-plugins"
