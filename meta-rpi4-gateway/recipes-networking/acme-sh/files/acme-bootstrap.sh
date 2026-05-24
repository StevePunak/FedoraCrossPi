#!/bin/sh
# Stage the image-shipped acme.sh tool into /data/acme/.
#
# acme.sh's design requires its binary, the dnsapi/, deploy/, and notify/
# script subdirs, AND its runtime state (account.conf, <domain>_ecc/, etc.)
# all to live in a single working directory. We ship the tool half at
# /usr/share/acme-sh/ in rootfs (immutable, image-versioned) and copy them
# to /data/acme/ on every boot so the writable working dir lives on the
# persistent partition. Runtime state and credentials are never touched.
set -e

SRC=/usr/share/acme-sh
DST=/data/acme

install -d -m 700 "$DST"
install -m 0755 "$SRC/acme.sh" "$DST/acme.sh"

for d in dnsapi deploy notify; do
    install -d "$DST/$d"
    for f in "$SRC/$d"/*.sh; do
        [ -e "$f" ] || continue
        install -m 0644 "$f" "$DST/$d/$(basename "$f")"
    done
done
