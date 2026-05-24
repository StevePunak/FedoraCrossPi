DESCRIPTION = "ACME shell client for Let's Encrypt certificate issuance and renewal"
HOMEPAGE = "https://github.com/acmesh-official/acme.sh"
LICENSE = "GPL-3.0-or-later"
LIC_FILES_CHKSUM = "file://LICENSE.md;md5=1ebbd3e34237af26da5dc08a4e440464"

# acme.sh is pure shell — no compilation, no arch dependence. Fetched via
# git so Yocto's src-uri-bad QA check stays happy (GitHub archive tarballs
# aren't byte-stable across regenerations; git protocol with an explicit
# commit SHA is the QA-approved pattern). SRCREV is the commit that the
# 3.1.3 release tag points to. Bump PV + SRCREV together when updating.
SRC_URI = " \
    git://github.com/acmesh-official/acme.sh;protocol=https;branch=master \
    file://acme-bootstrap.sh \
    file://acme-bootstrap.service \
    file://acme-renew.service \
    file://acme-renew.timer \
"
SRCREV = "76d1377fc12a0f9408d8917bebb8532e3f24d3ab"

S = "${UNPACKDIR}/git"

# The image stages an immutable copy of acme.sh + its script subdirs under
# /usr/share/acme-sh/. acme-bootstrap.service copies them to /data/acme/
# at boot so the writable working dir lives on the persistent partition (and
# survives reflash) while updates ship via the image. Runtime state
# (account.conf, <domain>_ecc/, godaddy.env) accumulates in /data/acme/
# alongside and is never touched by the bootstrap.
do_install() {
    install -d ${D}${datadir}/acme-sh
    install -m 0755 ${S}/acme.sh ${D}${datadir}/acme-sh/acme.sh
    for d in dnsapi deploy notify; do
        install -d ${D}${datadir}/acme-sh/$d
        for f in ${S}/$d/*.sh; do
            [ -e "$f" ] || continue
            install -m 0644 "$f" ${D}${datadir}/acme-sh/$d/
        done
    done

    install -d ${D}${sbindir}
    install -m 0755 ${UNPACKDIR}/acme-bootstrap.sh ${D}${sbindir}/acme-bootstrap.sh

    install -d ${D}${systemd_system_unitdir}
    install -m 0644 ${UNPACKDIR}/acme-bootstrap.service \
        ${D}${systemd_system_unitdir}/acme-bootstrap.service
    install -m 0644 ${UNPACKDIR}/acme-renew.service \
        ${D}${systemd_system_unitdir}/acme-renew.service
    install -m 0644 ${UNPACKDIR}/acme-renew.timer \
        ${D}${systemd_system_unitdir}/acme-renew.timer

    install -d ${D}${libdir}/systemd/system-preset
    printf 'enable acme-bootstrap.service\nenable acme-renew.timer\n' \
        > ${D}${libdir}/systemd/system-preset/93-acme-renew.preset
}

RDEPENDS:${PN} = "bash curl openssl-bin"

FILES:${PN} = " \
    ${datadir}/acme-sh \
    ${sbindir}/acme-bootstrap.sh \
    ${systemd_system_unitdir}/acme-bootstrap.service \
    ${systemd_system_unitdir}/acme-renew.service \
    ${systemd_system_unitdir}/acme-renew.timer \
    ${libdir}/systemd/system-preset/93-acme-renew.preset \
"
