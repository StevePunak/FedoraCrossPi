# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Goal

Produce a Yocto Linux image for Raspberry Pi 4B **and** a Qt 6.10.1 cross-compile SDK/toolchain usable from a Fedora 42 host.

## Key Technology Choices

- **Yocto release**: Walnascar (5.2) — the version documented to ship with Qt 6.10.1 (Boot to Qt 5.2.4)
- **Layer manager**: [`kas`](https://kas.readthedocs.io/) — drives all layer fetching and bitbake invocations
- **Display backend**: EGLFS with KMS/DRM (no Wayland/X11 compositor)
- **MACHINE**: `raspberrypi4-64`

## Build Commands

Install `kas` first:
```bash
pip install kas
```

Install Fedora 42 build prerequisites:
```bash
sudo dnf install -y bzip2 ccache chrpath cpio diffstat gawk gcc gcc-c++ git \
  glibc-devel glibc-langpack-en hostname make patch python3 python3-GitPython \
  python3-jinja2 python3-pexpect socat tar texinfo unzip wget xz zstd
```

Build the image:
```bash
./scripts/build-image.sh
# equivalent: kas build kas/rpi4-qt6.yml
```

Build the Qt 6.10.1 cross-compile SDK:
```bash
./scripts/build-sdk.sh
# equivalent: kas shell kas/rpi4-qt6.yml -- bitbake -c populate_sdk rpi4-qt6-image
```

SDK installer output:
```
build/tmp/deploy/sdk/poky-glibc-x86_64-rpi4-qt6-image-cortexa76-raspberrypi4-64-toolchain-*.sh
```

Use the SDK on Fedora 42:
```bash
# Install (run the .sh installer), then per session:
source /opt/poky/<version>/environment-setup-cortexa76-poky-linux
# Cross-compile a Qt app:
cmake -DCMAKE_TOOLCHAIN_FILE=$OECORE_NATIVE_SYSROOT/usr/share/cmake/OEToolchainConfig.cmake ..
```

Interactive bitbake shell (for custom recipes):
```bash
kas shell kas/rpi4-qt6.yml
```

## Architecture

```
kas/rpi4-qt6.yml          # Layer manifest + local.conf overrides
meta-rpi4-custom/
  conf/layer.conf          # Layer registration, depends on qt6-layer + raspberrypi
  recipes-images/images/
    rpi4-qt6-image.bb      # Custom image: core-image-base + Qt 6 + SSH
                           # inherit populate_sdk_qt6 enables SDK generation
scripts/
  build-image.sh           # Wraps: kas build
  build-sdk.sh             # Wraps: bitbake -c populate_sdk rpi4-qt6-image
```

### Layers pulled by kas

| Layer | Branch | Purpose |
|-------|--------|---------|
| poky | walnascar | OE-core, bitbake, base recipes |
| meta-openembedded | walnascar | meta-oe, meta-multimedia, meta-networking, meta-python |
| meta-raspberrypi | master | RPi 5 BSP, kernel, firmware |
| meta-qt6 | 6.10 | Qt 6.10.x recipes, `packagegroup-qt6-essentials`, `populate_sdk_qt6` |
| meta-rpi4-custom | (local) | Custom image recipe |

### Shared caches

`kas/rpi4-qt6.yml` sets `DL_DIR` and `SSTATE_DIR` one level above the build directory (`../downloads`, `../sstate-cache`). These persist across clean builds and are safe to share across machines with the same architecture.

## Known Issues / Gotchas

- **SELinux on Fedora**: Yocto's `pseudo` (fakeroot) can conflict with SELinux in enforcing mode. If builds fail with permission errors, set SELinux to permissive: `sudo setenforce 0`.
- **meta-raspberrypi branch**: Uses `master` (no walnascar branch exists). This is the standard practice for this BSP layer; pin to a specific commit for production.
- **Qt modules**: `packagegroup-qt6-essentials` covers core Qt. Add individual modules (`qtmultimedia`, `qtsvg`, etc.) to `IMAGE_INSTALL:append` in the image recipe as needed.
- **GPU memory**: Set to 128 MB (`GPU_MEM = "128"`) in `kas/rpi4-qt6.yml`. Increase for GPU-heavy workloads.
