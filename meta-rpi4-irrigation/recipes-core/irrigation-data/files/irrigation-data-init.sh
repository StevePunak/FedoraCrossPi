#!/bin/sh
# Carve the persistent /data partition out of the SD card, once per flash:
# grow the rootfs to end at DATA_START_MB and declare p3 from there to the
# end of the card. If p3 already exists with an ext4 filesystem there is
# nothing to do.
#
# /data survives a reflash only because DATA_START_MB never changes: the
# wic image writes just the first ~1 GB of the card, so the bytes from
# DATA_START_MB onward are untouched by dd. The next first boot declares p3
# at the same offset, blkid finds the old ext4 superblock, and the
# filesystem (Tailscale identity, ACME account, certificates) is kept.
# Changing DATA_START_MB wipes /data on every existing card at its next
# reflash.
set -e

DATA_START_MB=4096
MIN_DATA_MB=1024
LABEL=irrigation-data

ROOTDEV=$(findmnt -n -o SOURCE /)
DISK=$(lsblk -n -o PKNAME "${ROOTDEV}" | head -1)
ROOT_PARTNUM=$(echo "${ROOTDEV}" | grep -o '[0-9]*$')

if [ -z "${DISK}" ] || [ -z "${ROOT_PARTNUM}" ]; then
    echo "irrigation-data-init: cannot determine root disk/partition" >&2
    exit 1
fi

DATA_PARTNUM=$((ROOT_PARTNUM + 1))
DISK_DEV="/dev/${DISK}"
if [ -b "${DISK_DEV}p1" ]; then
    DATA_DEV="${DISK_DEV}p${DATA_PARTNUM}"
else
    DATA_DEV="${DISK_DEV}${DATA_PARTNUM}"
fi

if blkid "${DATA_DEV}" 2>/dev/null | grep -q 'TYPE="ext4"'; then
    echo "irrigation-data-init: /data already on ${DATA_DEV}"
    exit 0
fi

DISK_SIZE_MB=$(($(blockdev --getsize64 "${DISK_DEV}") / 1024 / 1024))
if [ "$((DISK_SIZE_MB - DATA_START_MB))" -lt "${MIN_DATA_MB}" ]; then
    echo "irrigation-data-init: ${DISK_SIZE_MB} MB card leaves less than ${MIN_DATA_MB} MB above ${DATA_START_MB} MB for /data" >&2
    exit 1
fi

if parted -s "${DISK_DEV}" print | grep -q "^ ${DATA_PARTNUM} "; then
    parted -s "${DISK_DEV}" rm "${DATA_PARTNUM}"
fi

parted -s "${DISK_DEV}" resizepart "${ROOT_PARTNUM}" "${DATA_START_MB}MB"
resize2fs "${ROOTDEV}"

parted -s "${DISK_DEV}" mkpart primary ext4 "${DATA_START_MB}MB" 100%
partprobe "${DISK_DEV}"
sleep 1

if blkid "${DATA_DEV}" 2>/dev/null | grep -q 'TYPE="ext4"'; then
    echo "irrigation-data-init: kept the /data filesystem found at ${DATA_START_MB} MB"
    e2fsck -p "${DATA_DEV}" || true
else
    echo "irrigation-data-init: formatting a fresh /data on ${DATA_DEV}"
    mkfs.ext4 -q -L "${LABEL}" "${DATA_DEV}"
fi
udevadm trigger --action=add "${DATA_DEV}"
udevadm settle
