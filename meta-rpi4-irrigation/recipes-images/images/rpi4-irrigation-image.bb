DESCRIPTION = "Irrigation controller appliance image for Raspberry Pi 4B"

require recipes-core/images/core-image-base.bb

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
    systemd-networkd-irrigation-config \
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

# empty-root-password/allow-empty-password/allow-root-login give root an
# empty password and let it in over SSH (this poky no longer has the old
# debug-tweaks alias; these are the primitives it used to expand to).
# Bring-up-only: it must come out before this image goes anywhere near a
# customer's LAN, or anyone who can reach port 80 owns the box outright.
IMAGE_FEATURES += "ssh-server-openssh package-management empty-root-password allow-empty-password allow-root-login"

# Two sites both claiming default_server on :80 stops nginx from starting at all.
remove_stock_nginx_site() {
    stock_site="${IMAGE_ROOTFS}${sysconfdir}/nginx/sites-enabled/default_server"
    if [ ! -e "$stock_site" ]; then
        bbfatal "expected ${sysconfdir}/nginx/sites-enabled/default_server in the rootfs but it is already gone; meta-webserver's nginx.inc may no longer ship it there, so check before deleting this function"
    fi
    rm -f "$stock_site"
}

ROOTFS_POSTPROCESS_COMMAND += "remove_stock_nginx_site"

# RPI_EXTRA_CONFIG is a plain assignment: a later kas fragment (a private
# overlay, most likely) that also sets it for an unrelated reason silently
# drops every relay hold-down with a clean build and no error anywhere.
# do_image_wic's recursive dependency on rpi-config's do_deploy is what
# currently guarantees config.txt exists by the time this runs; trimming
# wic out of IMAGE_FSTYPES would drop that guarantee out from under it.
do_image_complete[depends] += "rpi-config:do_deploy"
assert_gpio_safety_line() {
    generated="${DEPLOY_DIR_IMAGE}/bootfiles/config.txt"
    if ! grep -q 'gpio=5,6,13,16,19,20,21,26=op,dh' "$generated"; then
        bbfatal "gpio=5,6,13,16,19,20,21,26=op,dh missing from $generated — RPI_EXTRA_CONFIG did not reach the boot partition, and the relay lines come up unheld"
    fi
    if ! grep -q 'gpio=25=ip,pu' "$generated"; then
        bbfatal "gpio=25=ip,pu missing from $generated — the stop button input has no pull-up and reads a floating line"
    fi
}

IMAGE_POSTPROCESS_COMMAND += "assert_gpio_safety_line"
