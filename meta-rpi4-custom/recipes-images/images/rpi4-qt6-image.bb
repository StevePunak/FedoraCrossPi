DESCRIPTION = "Qt 6.10 image for Raspberry Pi 4B with EGLFS display support"

require recipes-core/images/core-image-base.bb

# Replace busybox with full GNU utilities
VIRTUAL-RUNTIME_base-utils = "util-linux-base"
VIRTUAL-RUNTIME_login-manager = "shadow"
IMAGE_INSTALL:remove = "busybox busybox-udhcpc busybox-udhcpd"

IMAGE_INSTALL:append = " \
    packagegroup-qt6-essentials \
    qtmultimedia \
    qtsvg \
    qtmqtt \
    qtserialbus \
    qtgraphs \
    qtbase-plugins \
    liberation-fonts \
    fbset \
    net-tools \
    iproute2 \
    coreutils \
    util-linux \
    procps \
    findutils \
    grep \
    gawk \
    sed \
    tar \
    bash \
    shadow \
    rsync \
    dnf \
    systemd-networkd-config \
    wpa-supplicant \
    taglib \
    taglib-dev \
    python3 \
    python3-venv \
    cifs-utils \
    avahi-daemon \
    avahi-libnss-mdns \
    bluez5 \
    bluez5-obex \
    rfkill \
    qtconnectivity \
"

# Include SSH and allow passwordless root login (development image)
IMAGE_FEATURES += "ssh-server-openssh allow-root-login empty-root-password package-management"

# Package manager
PACKAGE_CLASSES = "package_rpm"

# Install root SSH public key
install_root_ssh_key() {
    install -d -m 700 ${IMAGE_ROOTFS}/root/.ssh
    install -m 600 ${THISDIR}/files/authorized_keys ${IMAGE_ROOTFS}/root/.ssh/authorized_keys
}
ROOTFS_POSTPROCESS_COMMAND += "install_root_ssh_key;"

# Generates a Qt 6 cross-compile SDK when running:
#   bitbake -c populate_sdk rpi4-qt6-image
inherit populate_sdk_qt6
