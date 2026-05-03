#!/bin/sh
# Gateway first-boot initialization:
#   1. If /data already has a valid ext4 fs (in the partition table or
#      lurking at the fixed offset from a previous boot), preserve it.
#      Otherwise resize p2 to end at DATA_START_MB and create a fresh
#      /data on p3.
#   2. Mount config partition at /data
#   3. Seed default user-editable configs if /data is empty (first-ever boot)
#   4. Symlink user-editable configs from /data into /etc
#
# Note: nginx config is NOT stored in /data — it lives in /etc from the recipe
# so that recipe updates propagate to the device on reflash. Only
# user-editable configs (network, dnsmasq drop-ins, hostname) are persisted.
#
# /data preservation across reflashes works only because DATA_START_MB is
# constant: the wic image only writes the first ~1GB of the SD card, so
# bytes from DATA_START_MB onward survive the dd. Each reflash declares
# p3 at the same offset, blkid finds the existing ext4 superblock, and
# the filesystem is preserved. Bumping DATA_START_MB across builds breaks
# this — operators with existing devices would have to back up and
# restore. The earlier dynamic-formula version of this script had exactly
# that bug.
#
# Upgrade note: existing devices flashed before this layout (fixed 512MB
# /data, or the broken dynamic 2x-rootfs layout) get their /data wiped on
# the next reflash because the old offset doesn't match DATA_START_MB.
# Backup via the admin UI before reflashing in those cases. After one
# reflash with this script in place, future reflashes preserve.

set -e

# Fixed offset where /data starts. Constant across image builds — that's
# the whole point. Big enough to leave the rootfs comfortable growth room
# (current image is ~1GB so this is 4x headroom). Small enough to leave
# the bulk of any reasonable SD card to /data: 28GB on a 32GB card,
# 60GB on a 64GB card.
DATA_START_MB=4096

# Bail rather than carve out a tiny /data; usually means the SD card is
# too small for this image's persistent-data needs.
MIN_DATA_MB=1024

DATA_MOUNT="/data"

ROOTDEV=$(findmnt -n -o SOURCE /)
DISK=$(lsblk -n -o PKNAME "${ROOTDEV}" | head -1)
ROOT_PARTNUM=$(echo "${ROOTDEV}" | grep -o '[0-9]*$')
CONFIG_PARTNUM=$((ROOT_PARTNUM + 1))
CONFIG_DEV="/dev/${DISK}p${CONFIG_PARTNUM}"

# Handle devices without 'p' separator (e.g. /dev/sda vs /dev/mmcblk0p)
if [ ! -b "/dev/${DISK}p1" ] 2>/dev/null; then
    CONFIG_DEV="/dev/${DISK}${CONFIG_PARTNUM}"
fi

if [ -z "${DISK}" ] || [ -z "${ROOT_PARTNUM}" ]; then
    echo "gateway-init: cannot determine root disk/partition" >&2
    exit 1
fi

DISK_DEV="/dev/${DISK}"
DISK_SIZE_MB=$(($(blockdev --getsize64 "${DISK_DEV}") / 1024 / 1024))

echo "gateway-init: disk=${DISK_DEV} size=${DISK_SIZE_MB}MB rootfs=p${ROOT_PARTNUM} config=p${CONFIG_PARTNUM}"

if [ "$((DISK_SIZE_MB - DATA_START_MB))" -lt "${MIN_DATA_MB}" ]; then
    echo "gateway-init: SD card too small (${DISK_SIZE_MB}MB) — at DATA_START_MB=${DATA_START_MB}MB only $((DISK_SIZE_MB - DATA_START_MB))MB would remain for /data (need >=${MIN_DATA_MB}MB)" >&2
    exit 1
fi

# Case 1: p3 already in the partition table with a valid ext4 fs (e.g. a
# soft reboot that re-runs this service for some reason). Just mount it.
if blkid "${CONFIG_DEV}" 2>/dev/null | grep -q 'TYPE="ext4"'; then
    echo "gateway-init: existing /data on ${CONFIG_DEV}, preserving layout"
    e2fsck -y "${CONFIG_DEV}" || true
else
    # Drop any stale p3 entry; if it had no valid fs there's nothing to lose.
    if parted -s "${DISK_DEV}" print | grep -q "^ ${CONFIG_PARTNUM} "; then
        parted -s "${DISK_DEV}" rm "${CONFIG_PARTNUM}"
    fi

    # Grow rootfs to end at DATA_START_MB, then declare p3 from there to
    # the end of the disk. resize2fs writes ext4 metadata throughout p2's
    # new range — that's fine because anything below DATA_START_MB is
    # rootfs territory.
    parted -s "${DISK_DEV}" resizepart "${ROOT_PARTNUM}" "${DATA_START_MB}MB"
    resize2fs "${ROOTDEV}"

    parted -s "${DISK_DEV}" mkpart primary ext4 "${DATA_START_MB}MB" 100%
    partprobe "${DISK_DEV}"
    sleep 1

    # Case 2 vs 3: now that p3 is declared, blkid can see whether bytes
    # at DATA_START_MB are an existing ext4 fs (reflash that preserved
    # /data) or random (truly fresh card or migration from the old
    # broken layout).
    if blkid "${CONFIG_DEV}" 2>/dev/null | grep -q 'TYPE="ext4"'; then
        echo "gateway-init: existing /data filesystem detected at p3, preserving"
        e2fsck -y "${CONFIG_DEV}" || true
    else
        echo "gateway-init: fresh /data, formatting (rootfs ${DATA_START_MB}MB, /data $((DISK_SIZE_MB - DATA_START_MB))MB)"
        mkfs.ext4 -L gateway-config -q "${CONFIG_DEV}"
    fi
fi

mkdir -p "${DATA_MOUNT}"
mount "${CONFIG_DEV}" "${DATA_MOUNT}"

# Seed default user-editable configs on first-ever boot
if [ ! -f "${DATA_MOUNT}/.initialized" ]; then
    echo "gateway-init: first boot — seeding default configuration"

    mkdir -p "${DATA_MOUNT}/dnsmasq.d"
    mkdir -p "${DATA_MOUNT}/network"
    mkdir -p "${DATA_MOUNT}/ssl"

    # Copy dnsmasq drop-in configs
    for f in /etc/dnsmasq.d/*.conf; do
        [ -f "$f" ] && cp "$f" "${DATA_MOUNT}/dnsmasq.d/"
    done

    # Copy network config
    cp /etc/systemd/network/10-wired-static.network "${DATA_MOUNT}/network/"

    # Hostname
    cat /etc/hostname > "${DATA_MOUNT}/hostname"

    touch "${DATA_MOUNT}/.initialized"
    echo "gateway-init: default config seeded in ${DATA_MOUNT}"
fi

# Ensure SSL dir always exists (may be new on upgraded /data partitions)
mkdir -p "${DATA_MOUNT}/ssl"
chmod 700 "${DATA_MOUNT}/ssl"

# Activate user-editable configs from /data
echo "gateway-init: activating configuration from ${DATA_MOUNT}"

# dnsmasq drop-ins
for f in "${DATA_MOUNT}/dnsmasq.d/"*.conf; do
    [ -f "$f" ] && ln -sf "$f" "/etc/dnsmasq.d/$(basename "$f")"
done

# Network config
if [ -f "${DATA_MOUNT}/network/10-wired-static.network" ]; then
    ln -sf "${DATA_MOUNT}/network/10-wired-static.network" /etc/systemd/network/10-wired-static.network
fi

# Hostname
if [ -f "${DATA_MOUNT}/hostname" ]; then
    cat "${DATA_MOUNT}/hostname" > /etc/hostname
    hostname -F /etc/hostname
fi

echo "gateway-init: done, disabling service"
systemctl disable gateway-init.service
