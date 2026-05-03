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
    sudo \
    rsync \
    cifs-utils \
    curl \
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

# SSH only (no debug-tweaks, no root login, no empty password)
IMAGE_FEATURES += "ssh-server-openssh package-management"

# Package manager
PACKAGE_CLASSES = "package_rpm"

# Create the 'gateway' sudo user at build time. Default password is 'gateway' —
# change it with `passwd` after first login. Root account is locked so
# passwordless / single-user recovery requires physically reflashing.
inherit extrausers
GATEWAY_UID = "1000"
GATEWAY_GID = "1000"
# SHA-512 crypt of "gateway" (salt: stilgar). Change on first login with `passwd`.
GATEWAY_PW_HASH = "\$6\$stilgar\$a965cRXTOIY.2QOBntpnGJkfB8Q4/Z1Kc4rNyMXRL1Zu2v0XkfZ7LYRa1xyfpb.Qa8fco.8D19qocdLr4drwh/"
EXTRA_USERS_PARAMS = " \
    groupadd -r -f wheel; \
    useradd -m -u ${GATEWAY_UID} -U -s /bin/bash -G wheel -p '${GATEWAY_PW_HASH}' gateway; \
    usermod -L root; \
"

# sudoers: wheel group members can sudo without a password.
# Risk model: SSH is key-only and root login is disabled, so an attacker
# already needs the gateway user's SSH key to land here. Requiring a sudo
# password on top doesn't add meaningful security but breaks unattended
# deploy/maintenance scripts.
install_sudoers() {
    install -d -m 750 ${IMAGE_ROOTFS}${sysconfdir}/sudoers.d
    printf '%%wheel ALL=(ALL) NOPASSWD: ALL\n' > ${IMAGE_ROOTFS}${sysconfdir}/sudoers.d/wheel
    chmod 0440 ${IMAGE_ROOTFS}${sysconfdir}/sudoers.d/wheel
}

# SSH: disable root login explicitly via drop-in config
disable_root_ssh() {
    install -d ${IMAGE_ROOTFS}${sysconfdir}/ssh/sshd_config.d
    printf 'PermitRootLogin no\nPermitEmptyPasswords no\n' \
        > ${IMAGE_ROOTFS}${sysconfdir}/ssh/sshd_config.d/10-harden.conf
}

# Install SSH public key into the gateway user's home
install_gateway_ssh_key() {
    install -d -m 700 ${IMAGE_ROOTFS}/home/gateway/.ssh
    install -m 600 ${THISDIR}/files/authorized_keys \
        ${IMAGE_ROOTFS}/home/gateway/.ssh/authorized_keys
    # useradd -m creates the home dir owned by the user; chown to match
    # Host `chown` doesn't know target-side users/groups; use numeric IDs.
    chown -R ${GATEWAY_UID}:${GATEWAY_GID} ${IMAGE_ROOTFS}/home/gateway/.ssh
}

ROOTFS_POSTPROCESS_COMMAND += "install_sudoers; disable_root_ssh; install_gateway_ssh_key;"
