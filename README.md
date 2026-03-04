# FedoraCrossPi

Yocto Walnascar (5.2) image and Qt 6.10 cross-compile SDK for Raspberry Pi 4/5, built from a Fedora 42 host.

## What this produces

- A bootable Linux image for Raspberry Pi 4B or Pi 5 with Qt 6.10, EGLFS/KMS display, SSH access
- A Qt 6.10 cross-compile SDK installable on Fedora 42 for building Qt apps targeting the Pi

## Prerequisites

**Install kas** (layer manager):
```bash
pip install kas
```

**Install Fedora 42 build dependencies:**
```bash
sudo dnf install -y bzip2 ccache chrpath cpio diffstat gawk gcc gcc-c++ git \
  glibc-devel glibc-langpack-en hostname make patch python3 python3-GitPython \
  python3-jinja2 python3-pexpect socat tar texinfo unzip wget xz zstd
```

> **SELinux note:** Yocto's `pseudo` (fakeroot) can conflict with SELinux in enforcing mode.
> If builds fail with permission errors: `sudo setenforce 0`

## Building

### Image

```bash
./scripts/build-image.sh          # Raspberry Pi 4 (default)
./scripts/build-image.sh rpi5     # Raspberry Pi 5
```

Output: `build/tmp/deploy/images/raspberrypi4-64/*.wic.bz2`

Flash to SD card:
```bash
bzcat build/tmp/deploy/images/raspberrypi4-64/*.wic.bz2 | sudo dd of=/dev/sdX bs=4M status=progress
```

### Qt 6.10 Cross-Compile SDK

```bash
./scripts/build-sdk.sh            # Raspberry Pi 4
./scripts/build-sdk.sh rpi5       # Raspberry Pi 5
```

Output: `build/tmp/deploy/sdk/poky-glibc-x86_64-rpi4-qt6-image-cortexa7*-toolchain-*.sh`

Install and use:
```bash
# Run the installer
./poky-glibc-x86_64-...-toolchain-*.sh

# Per session — source the environment
source /opt/poky/<version>/environment-setup-cortexa7*-poky-linux

# Cross-compile a Qt app
cmake -DCMAKE_TOOLCHAIN_FILE=$OECORE_NATIVE_SYSROOT/usr/share/cmake/OEToolchainConfig.cmake ..
make
```

## Image contents

- Qt 6.10: Core, Gui, Widgets, Network, Xml, Svg, Multimedia, Mqtt, SerialBus, SQL (SQLite driver)
- Display: EGLFS with KMS/DRM (no X11/Wayland compositor)
- Init: systemd
- SSH: OpenSSH server, passwordless root login, authorized_keys from `meta-rpi4-custom/recipes-images/images/files/`
- Extras: rsync, coreutils, net-tools, iproute2, liberation-fonts

## SSH key

Place your public key at:
```
meta-rpi4-custom/recipes-images/images/files/authorized_keys
```

It will be installed to `/root/.ssh/authorized_keys` on the image.

## Repository structure

```
kas/
  rpi4-qt6.yml          # Layer manifest for RPi 4 (Cortex-A72)
  rpi5-qt6.yml          # Layer manifest for RPi 5 (Cortex-A76)
meta-rpi4-custom/
  conf/layer.conf
  recipes-images/images/
    rpi4-qt6-image.bb   # Custom image recipe
    files/
      authorized_keys   # SSH public key (not committed — add your own)
  recipes-qt/qt6/
    qtbase_%.bbappend   # Enables SQLite SQL driver
scripts/
  build-image.sh
  build-sdk.sh
```

## Layers

| Layer | Branch | Purpose |
|-------|--------|---------|
| poky | walnascar | OE-core, bitbake, base recipes |
| meta-openembedded | walnascar | meta-oe, meta-multimedia, meta-networking, meta-python |
| meta-raspberrypi | walnascar | RPi 4/5 BSP, kernel, firmware |
| meta-qt6 | 6.10 | Qt 6.10.x recipes and SDK class |

External layers are fetched by kas and are not committed to this repository.
