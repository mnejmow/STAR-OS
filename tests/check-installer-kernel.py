#!/usr/bin/env python3
"""Verify the live kernel matches the kernel embedded in Debian Installer."""
import pathlib
import re
import subprocess
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[1]
ISO = ROOT / "output" / "STAR-1.0-amd64.iso"


def extract(iso_path, destination):
    subprocess.run(
        ["xorriso", "-osirrox", "on", "-indev", str(ISO),
         "-extract", iso_path, str(destination)],
        check=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
    )


def main():
    if not ISO.is_file():
        raise SystemExit(f"ISO not found: {ISO}")

    with tempfile.TemporaryDirectory(prefix="star-installer-check-") as temp:
        temp = pathlib.Path(temp)
        squashfs = temp / "filesystem.squashfs"
        extract("/live/filesystem.squashfs", squashfs)

        live_listing = subprocess.run(
            ["unsquashfs", "-ll", str(squashfs)],
            check=True, capture_output=True, text=True,
        ).stdout
        live_versions = sorted(set(re.findall(
            r"(?:squashfs-root/)?(?:usr/)?lib/modules/([^/\s]+)/?",
            live_listing,
        )))
        if len(live_versions) != 1:
            raise SystemExit(
                "Expected exactly one live kernel module directory; found: "
                + repr(live_versions)
            )

        initrd = temp / "installer-initrd.gz"
        initrd_path = None
        for candidate in ("/install/gtk/initrd.gz", "/install/initrd.gz"):
            try:
                extract(candidate, initrd)
                initrd_path = candidate
                break
            except subprocess.CalledProcessError:
                initrd.unlink(missing_ok=True)
        if initrd_path is None:
            raise SystemExit("Could not extract Debian Installer initrd from ISO")

        gunzip = subprocess.Popen(
            ["gzip", "-dc", str(initrd)], stdout=subprocess.PIPE,
        )
        listing = subprocess.run(
            ["cpio", "-it"], stdin=gunzip.stdout,
            check=True, capture_output=True, text=True,
        ).stdout
        gunzip.stdout.close()
        if gunzip.wait() != 0:
            raise SystemExit("Could not read installer initrd")

        installer_versions = sorted(set(re.findall(
            r"(?:^|\n)(?:\./)?lib/modules/([^/\n]+)(?:/|$)",
            listing,
        )))
        if len(installer_versions) != 1:
            raise SystemExit(
                "Expected exactly one installer kernel module directory; found: "
                + repr(installer_versions)
            )

        live = live_versions[0]
        installer = installer_versions[0]
        print(f"Live kernel:      {live}")
        print(f"Installer kernel: {installer}")
        print(f"Installer initrd: {initrd_path}")
        if live != installer:
            raise SystemExit(
                "KERNEL MISMATCH: Debian Installer Launcher will refuse to start."
            )
        print("PASS: live and installer kernel versions match.")


if __name__ == "__main__":
    main()
