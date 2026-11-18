# STAR Light — The Quiet Universe

Debian 13 Trixie · XFCE 4.20 · AMD64 · Lightweight profile

## Runtime target
- Target RAM: 3 GB
- CPU: 2 cores
- Architecture: x86_64 / AMD64
- Desktop: XFCE

The practical memory requirement depends on the applications opened and the
hardware. The 3 GB target is intended for a lightweight desktop workload.

## Build
On Debian 13 amd64, install live-build, debootstrap, squashfs-tools, xorriso,
GRUB BIOS/EFI and Syslinux packages, then run:

```bash
sudo ./build.sh
```

The output is `output/STAR-1.0-amd64.iso` and its SHA256 checksum.

## Automated build
GitHub Actions builds the hybrid BIOS/UEFI ISO, verifies its checksum and
boot catalog, and runs graphical QEMU boot smoke tests with 4 GiB RAM.
Open **Actions → Build STAR OS ISO** to inspect the latest run and artifacts.

A successful QEMU boot test confirms that the Live desktop reaches XFCE in
BIOS and UEFI modes. It does **not** prove that installation to a disk works.

## Installation validation
Before calling a release install-ready, test the Debian Installer in a
disposable VM in both BIOS and UEFI modes, complete a full installation,
remove the ISO, and verify that the installed system boots from its virtual
disk. Also check networking, user login, audio, and package management.

## Design
Cosmic identity, deep-space navy, restrained violet/cyan highlights, original
wallpaper and STAR mark, XFCE desktop, dock, and Inter typography.
