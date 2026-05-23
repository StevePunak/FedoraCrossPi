DESCRIPTION = "Tailscale mesh VPN agent (official static arm64 build)"
HOMEPAGE = "https://tailscale.com"
LICENSE = "BSD-3-Clause"
LIC_FILES_CHKSUM = "file://${COMMON_LICENSE_DIR}/BSD-3-Clause;md5=550794465ba0ec5312d6919e203a55f9"

# Tailscale ships fully static Go binaries — no cross-compile needed, just drop
# them in. arm64 covers both raspberrypi4-64 and raspberrypi5.
COMPATIBLE_MACHINE = "raspberrypi4-64|raspberrypi5"

SRC_URI = " \
    https://pkgs.tailscale.com/stable/tailscale_${PV}_arm64.tgz \
    file://tailscaled.service \
    file://tailscaled.defaults \
"
SRC_URI[sha256sum] = "d26ce4a1a259621fc76d16c7baf3f3a4252f356dfa9d9769484782f766ca1b7f"

S = "${UNPACKDIR}/tailscale_${PV}_arm64"

# Pre-built upstream binaries — don't strip, don't try to extract debug info,
# don't run binary QA passes that assume our toolchain produced these.
INHIBIT_PACKAGE_STRIP = "1"
INHIBIT_PACKAGE_DEBUG_SPLIT = "1"
INHIBIT_SYSROOT_STRIP = "1"
INSANE_SKIP:${PN} = "already-stripped ldflags arch textrel"

do_install() {
    install -d ${D}${sbindir}
    install -m 0755 ${S}/tailscale  ${D}${sbindir}/tailscale
    install -m 0755 ${S}/tailscaled ${D}${sbindir}/tailscaled

    install -d ${D}${systemd_system_unitdir}
    install -m 0644 ${UNPACKDIR}/tailscaled.service \
        ${D}${systemd_system_unitdir}/tailscaled.service

    install -d ${D}${sysconfdir}/default
    install -m 0644 ${UNPACKDIR}/tailscaled.defaults \
        ${D}${sysconfdir}/default/tailscaled

    install -d ${D}${libdir}/systemd/system-preset
    printf 'enable tailscaled.service\n' \
        > ${D}${libdir}/systemd/system-preset/92-tailscale.preset
}

FILES:${PN} = " \
    ${sbindir}/tailscale \
    ${sbindir}/tailscaled \
    ${systemd_system_unitdir}/tailscaled.service \
    ${sysconfdir}/default/tailscaled \
    ${libdir}/systemd/system-preset/92-tailscale.preset \
"

CONFFILES:${PN} = "${sysconfdir}/default/tailscaled"
