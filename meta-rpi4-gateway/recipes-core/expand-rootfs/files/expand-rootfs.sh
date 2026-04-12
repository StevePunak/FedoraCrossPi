#!/bin/sh
# Expand root partition to fill the SD card, then resize the filesystem.
# Runs once at first boot and disables itself.

ROOTDEV=$(findmnt -n -o SOURCE /)
DISK=$(lsblk -n -o PKNAME "${ROOTDEV}" | head -1)
PARTNUM=$(echo "${ROOTDEV}" | grep -o '[0-9]*$')

if [ -z "${DISK}" ] || [ -z "${PARTNUM}" ]; then
    echo "expand-rootfs: cannot determine root disk/partition" >&2
    exit 1
fi

echo "expand-rootfs: growing /dev/${DISK} partition ${PARTNUM} to fill disk"
parted -s "/dev/${DISK}" resizepart "${PARTNUM}" 100%

echo "expand-rootfs: resizing filesystem on ${ROOTDEV}"
resize2fs "${ROOTDEV}"

echo "expand-rootfs: done, disabling service"
systemctl disable expand-rootfs.service
