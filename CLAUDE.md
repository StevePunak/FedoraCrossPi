# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Goal

Produce a Yocto Linux image for Raspberry Pi 4B or 5 **and** a Qt 6.10.1 cross-compile SDK/toolchain usable from a Fedora 42 host.

## Key Technology Choices

- **Yocto release**: Walnascar (5.2) — the version documented to ship with Qt 6.10.1 (Boot to Qt 5.2.4)
- **Layer manager**: [`kas`](https://kas.readthedocs.io/) — drives all layer fetching and bitbake invocations
- **Display backend**: EGLFS with KMS/DRM (no Wayland/X11 compositor)
- **MACHINE**: `raspberrypi4-64` or `raspberrypi5`

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

Build the image (defaults to rpi4):
```bash
./scripts/build-image.sh          # RPi 4
./scripts/build-image.sh rpi5     # RPi 5
# equivalent: kas build kas/rpi4-qt6.yml
```

Build the Qt 6.10.1 cross-compile SDK:
```bash
./scripts/build-sdk.sh            # RPi 4
./scripts/build-sdk.sh rpi5       # RPi 5
# equivalent: kas shell kas/rpi4-qt6.yml -- bitbake -c populate_sdk rpi4-qt6-image
```

SDK installer output:
```
build/tmp/deploy/sdk/poky-glibc-x86_64-rpi4-qt6-image-cortexa7*-toolchain-*.sh
```

Use the SDK on Fedora 42:
```bash
# Install (run the .sh installer), then per session:
source /opt/poky/<version>/environment-setup-cortexa7*-poky-linux
# Cross-compile a Qt app:
cmake -DCMAKE_TOOLCHAIN_FILE=$OECORE_NATIVE_SYSROOT/usr/share/cmake/OEToolchainConfig.cmake ..
```

Interactive bitbake shell (for custom recipes):
```bash
kas shell kas/rpi4-qt6.yml
kas shell kas/rpi5-qt6.yml
```

## Architecture

```
kas/rpi4-qt6.yml          # Layer manifest + local.conf overrides (RPi 4, Cortex-A72)
kas/rpi5-qt6.yml          # Layer manifest + local.conf overrides (RPi 5, Cortex-A76)
meta-rpi4-custom/
  conf/layer.conf          # Layer registration, depends on qt6-layer + raspberrypi
  recipes-images/images/
    rpi4-qt6-image.bb      # Custom image: core-image-base + Qt 6 + SSH
                           # inherit populate_sdk_qt6 enables SDK generation
scripts/
  build-image.sh           # Wraps: kas build [rpi4|rpi5]
  build-sdk.sh             # Wraps: bitbake -c populate_sdk rpi4-qt6-image [rpi4|rpi5]
```

### Layers pulled by kas

| Layer | Branch | Purpose |
|-------|--------|---------|
| poky | walnascar | OE-core, bitbake, base recipes |
| meta-openembedded | walnascar | meta-oe, meta-multimedia, meta-networking, meta-python |
| meta-raspberrypi | walnascar | RPi 4/5 BSP, kernel, firmware |
| meta-qt6 | 6.10 | Qt 6.10.x recipes, `packagegroup-qt6-essentials`, `populate_sdk_qt6` |
| meta-rpi4-custom | (local) | Custom image recipe |

### Shared caches

Both kas files set `DL_DIR` and `SSTATE_DIR` one level above the build directory (`../downloads`, `../sstate-cache`). These persist across clean builds and are safe to share across machines with the same architecture.

## Known Issues / Gotchas

- **SELinux on Fedora**: Yocto's `pseudo` (fakeroot) can conflict with SELinux in enforcing mode. If builds fail with permission errors, set SELinux to permissive: `sudo setenforce 0`.
- **meta-raspberrypi branch**: Uses `walnascar`. Pin to a specific commit for production.
- **Qt modules**: `packagegroup-qt6-essentials` covers core Qt. Add individual modules (`qtmultimedia`, `qtsvg`, etc.) to `IMAGE_INSTALL:append` in the image recipe as needed.
- **GPU memory**: Set to 128 MB (`GPU_MEM = "128"`) in kas files. Increase for GPU-heavy workloads.
- **Pi4 vs Pi5 SDK**: The SDKs produce different sysroots (cortexa72 vs cortexa76). Use the matching SDK for each target board.
