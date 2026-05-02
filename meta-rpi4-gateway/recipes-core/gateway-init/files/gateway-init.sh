#!/bin/sh
# Gateway first-boot initialization:
#   1. If /data already has a valid ext4 fs, preserve it (just mount).
#      Otherwise size rootfs (p2) to 2x its as-flashed size and devote
#      everything past it to /data (p3).
#   2. Mount config partition at /data
#   3. Seed default user-editable configs if /data is empty (first-ever boot)
#   4. Symlink user-editable configs from /data into /etc
#
# Note: nginx config is NOT stored in /data — it lives in /etc from the recipe
# so that recipe updates propagate to the device on reflash. Only
# user-editable configs (network, dnsmasq drop-ins, hostname) are persisted.
#
# Upgrade note: existing devices flashed before this layout (fixed 512MB
# /data) keep their /data partition exactly as-is on reflash — the new
# formula only fires on truly fresh SD cards with no /data filesystem.
# To migrate an existing device to the larger /data layout: download a
# backup via the admin UI, wipe the SD card partition table
# (`wipefs -a /dev/sdX`), reflash, restore the backup.

set -e

# Rootfs partition is sized to (as-flashed-rootfs-size * this factor) on
# fresh SD cards. The remainder of the disk becomes /data. Bump the factor
# to give the rootfs more growth room at the cost of /data space.
ROOTFS_GROWTH_FACTOR=2

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

if blkid "${CONFIG_DEV}" 2>/dev/null | grep -q 'TYPE="ext4"'; then
    # Existing /data on this card — leave the layout alone, just fsck and mount.
    echo "gateway-init: existing /data on ${CONFIG_DEV}, preserving layout"
    e2fsck -y "${CONFIG_DEV}" || true
else
    # Fresh card: double the rootfs partition, give the rest to /data.
    ROOT_SIZE_MB=$(($(blockdev --getsize64 "${ROOTDEV}") / 1024 / 1024))
    ROOT_START_SECTORS=$(cat "/sys/class/block/$(basename "${ROOTDEV}")/start")
    ROOT_START_MB=$((ROOT_START_SECTORS / 2048))
    NEW_ROOT_SIZE_MB=$((ROOT_SIZE_MB * ROOTFS_GROWTH_FACTOR))
    NEW_ROOT_END_MB=$((ROOT_START_MB + NEW_ROOT_SIZE_MB))
    DATA_SIZE_MB=$((DISK_SIZE_MB - NEW_ROOT_END_MB))

    if [ "${DATA_SIZE_MB}" -lt "${MIN_DATA_MB}" ]; then
        echo "gateway-init: SD card too small (${DISK_SIZE_MB}MB) — doubling rootfs to ${NEW_ROOT_SIZE_MB}MB would leave only ${DATA_SIZE_MB}MB for /data (need >=${MIN_DATA_MB}MB)" >&2
        exit 1
    fi

    echo "gateway-init: rootfs ${ROOT_SIZE_MB}MB->${NEW_ROOT_SIZE_MB}MB, /data ${DATA_SIZE_MB}MB"

    # Drop a stale p3 entry if one exists (no valid fs, so nothing to lose).
    if parted -s "${DISK_DEV}" print | grep -q "^ ${CONFIG_PARTNUM} "; then
        parted -s "${DISK_DEV}" rm "${CONFIG_PARTNUM}"
    fi

    parted -s "${DISK_DEV}" resizepart "${ROOT_PARTNUM}" "${NEW_ROOT_END_MB}MB"
    resize2fs "${ROOTDEV}"

    parted -s "${DISK_DEV}" mkpart primary ext4 "${NEW_ROOT_END_MB}MB" 100%
    partprobe "${DISK_DEV}"
    sleep 1

    mkfs.ext4 -L gateway-config -q "${CONFIG_DEV}"
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
