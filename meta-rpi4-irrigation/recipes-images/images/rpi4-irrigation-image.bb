DESCRIPTION = "Irrigation controller appliance image for Raspberry Pi 4B"

require recipes-core/images/core-image-base.bb

# Replace busybox with full GNU utilities
VIRTUAL-RUNTIME_base-utils = "util-linux-base"
VIRTUAL-RUNTIME_base-utils-hwclock = "util-linux-hwclock"
VIRTUAL-RUNTIME_base-utils-syslog = ""
VIRTUAL-RUNTIME_login-manager = "shadow"
IMAGE_INSTALL:remove = "busybox busybox-udhcpc busybox-udhcpd busybox-hwclock busybox-syslog"

IMAGE_INSTALL:append = " \
    irrigationd \
    irrigation-init \
    irrigation-web \
    nginx \
    nginx-irrigation-config \
    libgpiod \
    libgpiod-tools \
    sqlite3 \
    tzdata \
    avahi-daemon \
    avahi-libnss-mdns \
    wpa-supplicant \
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
    less \
    file \
    strace \
    i2c-tools \
"

IMAGE_FEATURES += "ssh-server-openssh package-management"

PACKAGE_CLASSES = "package_rpm"

# Two sites both claiming default_server on :80 stops nginx from starting at all.
remove_stock_nginx_site() {
    rm -f ${IMAGE_ROOTFS}${sysconfdir}/nginx/sites-enabled/default_server
}

ROOTFS_POSTPROCESS_COMMAND += "remove_stock_nginx_site"
