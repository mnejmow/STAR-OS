# STAR OS — The Quiet Universe

Debian 13 Trixie · GNOME · AMD64 · Light profile · 4 GB RAM target

## Runtime target
- Minimum RAM target: 4 GB
- Recommended RAM: 8 GB
- CPU: 2 cores minimum
- Architecture: x86_64 / AMD64

The 4 GB figure is a runtime target, not a build-host requirement. ISO construction is memory- and disk-intensive.

## Build
On Debian 13 amd64, install live-build, debootstrap, squashfs-tools, xorriso,
GRUB BIOS/EFI and Syslinux packages, then run:

```bash
sudo ./build.sh
```

The output is `output/STAR-1.0-amd64.iso` and its SHA256 checksum.

## Automated build
GitHub Actions is configured to build the hybrid ISO and run BIOS/UEFI QEMU
boot smoke tests with 4 GiB RAM. Open **Actions → Build STAR OS ISO**.
A successful run uploads an artifact named
`STAR-OS-1.0-amd64-BIOS-UEFI`.

## Current validation status
The ISO has not yet been built or interactively tested. Automated QEMU smoke
tests, if passed, are not a substitute for checking GNOME, networking, audio,
and the Debian installer in a disposable VM.

## Design
Deep-space navy, restrained violet/cyan highlights, original SVG wallpaper
and logo, dark GNOME defaults, and Inter typography.
