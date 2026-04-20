#!/bin/sh
# Gateway first-boot initialization:
#   1. Expand rootfs (p2) leaving 512MB at end for config partition
#   2. Create config partition (p3) if missing from partition table
#   3. Format p3 only if it doesn't already have a valid filesystem
#   4. Mount config partition at /data
#   5. Seed default user-editable configs if /data is empty (first-ever boot)
#   6. Symlink user-editable configs from /data into /etc
#
# Note: nginx config is NOT stored in /data — it lives in /etc from the recipe
# so that recipe updates propagate to the device on reflash. Only
# user-editable configs (network, dnsmasq drop-ins, hostname) are persisted.

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
    partprobe "${DISK_DEV}"
    sleep 1
fi

# Step 3: Format only if no valid ext4 filesystem exists
if blkid "${CONFIG_DEV}" | grep -q 'TYPE="ext4"'; then
    echo "gateway-init: existing ext4 filesystem found on ${CONFIG_DEV}, preserving data"
    e2fsck -y "${CONFIG_DEV}" || true
else
    echo "gateway-init: formatting ${CONFIG_DEV} as ext4"
    mkfs.ext4 -L gateway-config -q "${CONFIG_DEV}"
fi

# Step 4: Mount config partition
mkdir -p "${DATA_MOUNT}"
mount "${CONFIG_DEV}" "${DATA_MOUNT}"

# Step 5: Seed default user-editable configs on first-ever boot
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

# Step 6: Activate user-editable configs from /data
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
