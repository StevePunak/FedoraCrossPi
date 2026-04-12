#!/bin/sh
# Gateway first-boot initialization:
#   1. Expand rootfs (p2) leaving 512MB at end for config partition
#   2. Create config partition (p3) if missing from partition table
#   3. Format p3 only if it doesn't already have a valid filesystem
#   4. Mount config partition at /data
#   5. Seed default configs if /data is empty (first-ever boot)
#   6. Symlink configs from /data into /etc
#
# On re-flash: dd overwrites the partition table and p1+p2, but p3 data
# at the end of the disk survives. This script recreates the partition
# table entry and mounts the existing filesystem without formatting.

set -e

CONFIG_SIZE_MB=512
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
DISK_SIZE_MB=$(blockdev --getsize64 "${DISK_DEV}" | awk '{printf "%d", $1/1024/1024}')
ROOT_END_MB=$((DISK_SIZE_MB - CONFIG_SIZE_MB))

echo "gateway-init: disk=${DISK_DEV} size=${DISK_SIZE_MB}MB rootfs=p${ROOT_PARTNUM} config=p${CONFIG_PARTNUM}"

# Step 1: Expand rootfs, leaving space for config partition
echo "gateway-init: expanding rootfs to ${ROOT_END_MB}MB"
parted -s "${DISK_DEV}" resizepart "${ROOT_PARTNUM}" "${ROOT_END_MB}MB"
resize2fs "${ROOTDEV}"

# Step 2: Create config partition if not in partition table
if ! parted -s "${DISK_DEV}" print | grep -q "^ ${CONFIG_PARTNUM} "; then
    echo "gateway-init: creating config partition (p${CONFIG_PARTNUM}, ${CONFIG_SIZE_MB}MB)"
    parted -s "${DISK_DEV}" mkpart primary ext4 "${ROOT_END_MB}MB" 100%
    # Inform kernel of new partition
    partprobe "${DISK_DEV}"
    sleep 1
fi

# Step 3: Format only if no valid ext4 filesystem exists
if blkid "${CONFIG_DEV}" | grep -q 'TYPE="ext4"'; then
    echo "gateway-init: existing ext4 filesystem found on ${CONFIG_DEV}, preserving data"
    # Quick fsck to ensure consistency
    e2fsck -y "${CONFIG_DEV}" || true
else
    echo "gateway-init: formatting ${CONFIG_DEV} as ext4"
    mkfs.ext4 -L gateway-config -q "${CONFIG_DEV}"
fi

# Step 4: Mount config partition
mkdir -p "${DATA_MOUNT}"
mount "${CONFIG_DEV}" "${DATA_MOUNT}"

# Step 5: Seed default configs on first-ever boot
if [ ! -f "${DATA_MOUNT}/.initialized" ]; then
    echo "gateway-init: first boot — seeding default configuration"

    mkdir -p "${DATA_MOUNT}/dnsmasq.d"
    mkdir -p "${DATA_MOUNT}/nginx/sites-available"
    mkdir -p "${DATA_MOUNT}/nginx/sites-enabled"
    mkdir -p "${DATA_MOUNT}/network"

    # Copy dnsmasq drop-in configs
    for f in /etc/dnsmasq.d/*.conf; do
        [ -f "$f" ] && cp "$f" "${DATA_MOUNT}/dnsmasq.d/"
    done

    # Copy network config
    cp /etc/systemd/network/10-wired-static.network "${DATA_MOUNT}/network/"

    # Copy nginx site configs
    for f in /etc/nginx/sites-available/*; do
        [ -f "$f" ] && cp "$f" "${DATA_MOUNT}/nginx/sites-available/"
    done

    # Hostname
    cat /etc/hostname > "${DATA_MOUNT}/hostname"

    touch "${DATA_MOUNT}/.initialized"
    echo "gateway-init: default config seeded in ${DATA_MOUNT}"
fi

# Step 6: Activate configs from /data
echo "gateway-init: activating configuration from ${DATA_MOUNT}"

# dnsmasq drop-ins: symlink from /data into /etc
for f in "${DATA_MOUNT}/dnsmasq.d/"*.conf; do
    [ -f "$f" ] && ln -sf "$f" "/etc/dnsmasq.d/$(basename "$f")"
done

# Network config
if [ -f "${DATA_MOUNT}/network/10-wired-static.network" ]; then
    ln -sf "${DATA_MOUNT}/network/10-wired-static.network" /etc/systemd/network/10-wired-static.network
fi

# nginx sites
for f in "${DATA_MOUNT}/nginx/sites-available/"*; do
    [ -f "$f" ] && ln -sf "$f" "/etc/nginx/sites-available/$(basename "$f")"
done
# Re-create sites-enabled symlinks pointing to sites-available
rm -f /etc/nginx/sites-enabled/*
for f in "${DATA_MOUNT}/nginx/sites-enabled/"*; do
    name=$(basename "$f")
    if [ -f "/etc/nginx/sites-available/${name}" ]; then
        ln -sf "../sites-available/${name}" "/etc/nginx/sites-enabled/${name}"
    fi
done

# Hostname
if [ -f "${DATA_MOUNT}/hostname" ]; then
    cat "${DATA_MOUNT}/hostname" > /etc/hostname
    hostname -F /etc/hostname
fi

echo "gateway-init: done, disabling service"
systemctl disable gateway-init.service
