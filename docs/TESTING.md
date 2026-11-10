# Testing checklist

## Live ISO
The build config requests an amd64 hybrid ISO with Syslinux BIOS and GRUB EFI boot paths.

- [ ] ISO boots in UEFI mode
- [ ] ISO boots in legacy BIOS mode
- [ ] GNOME session starts
- [ ] Network and audio work
- [ ] Included applications launch
- [ ] Shutdown and reboot work

## Installation
Debian Installer live mode is enabled but still requires testing of partitioning,
filesystem mounting, user creation, bootloader installation, and first boot.

The GitHub Actions workflow verifies the ISO checksum and El Torito catalog,
then runs 4 GiB QEMU boot smoke tests for BIOS and UEFI. Smoke tests do not
replace manual desktop and installer validation.
