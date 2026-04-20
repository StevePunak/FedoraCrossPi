DESCRIPTION = "Home network gateway appliance for Raspberry Pi 4B (DHCP, DNS, web admin)"

require recipes-core/images/core-image-base.bb

# Replace busybox with full GNU utilities
VIRTUAL-RUNTIME_base-utils = "util-linux-base"
VIRTUAL-RUNTIME_base-utils-hwclock = "util-linux-hwclock"
VIRTUAL-RUNTIME_base-utils-syslog = ""
VIRTUAL-RUNTIME_login-manager = "shadow"
IMAGE_INSTALL:remove = "busybox busybox-udhcpc busybox-udhcpd busybox-hwclock busybox-syslog"

IMAGE_INSTALL:append = " \
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
    python3 \
    python3-venv \
    net-tools \
    iproute2 \
    iptables \
    ethtool \
    tcpdump \
    bind-utils \
    openssl-bin \
    dnsmasq \
    dnsmasq-gateway-config \
    nginx \
    nginx-gateway-config \
    certbot-venv \
    avahi-daemon \
    avahi-libnss-mdns \
    wpa-supplicant \
    systemd-networkd-gateway-config \
    gateway-init \
    gateway-ssl-init \
    gateway-admin-backend \
    gateway-admin-frontend \
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
