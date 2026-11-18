#!/usr/bin/env python3
"""Install STAR Light on a disposable QEMU disk, then boot that disk without the ISO."""
import os
import pathlib
import shutil
import socket
import subprocess
import tempfile
import time

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = ROOT / "output"
ISO = OUT / "STAR-1.0-amd64.iso"
EVIDENCE = OUT / "install-evidence"
INSTALL_TIMEOUT = int(os.environ.get("STAR_INSTALL_TIMEOUT", "2700"))
BOOT_TIMEOUT = int(os.environ.get("STAR_INSTALLED_BOOT_TIMEOUT", "360"))

# This preseed exists only in a temporary initrd created inside CI. It is never
# added to the published ISO and can only partition the disposable /dev/vda.
PRESEED = r'''# STAR Light CI-only unattended installation
d-i debian-installer/locale string en_US.UTF-8
d-i keyboard-configuration/xkb-keymap select us
d-i netcfg/choose_interface select auto
d-i netcfg/get_hostname string star
d-i netcfg/get_domain string local
d-i clock-setup/utc boolean true
d-i time/zone string Etc/UTC

d-i partman-auto/disk string /dev/vda
d-i partman-auto/method string regular
d-i partman-auto/choose_recipe select atomic
d-i partman-partitioning/confirm_write_new_label boolean true
d-i partman-auto/confirm boolean true
d-i partman/choose_partition select finish
d-i partman/confirm boolean true
d-i partman/confirm_nooverwrite boolean true

d-i passwd/root-login boolean false
d-i passwd/make-user boolean true
d-i passwd/user-fullname string STAR CI Test
d-i passwd/username string star
d-i passwd/user-password-crypted password $6$starci$9wklHXkPgZqyHuHGNhf.yLHr1TdfUqp193Nz/FqzlEVHMNb0JGPVKFuqJzN3rR.Q7Gu0mwnII/2iNV/bWU4Cr0

d-i apt-setup/use_mirror boolean false
d-i pkgsel/run_tasksel boolean false
d-i pkgsel/upgrade select none
d-i popularity-contest/participate boolean false

d-i preseed/late_command string in-target sh -c 'mkdir -p /etc/lightdm/lightdm.conf.d; printf "%s\\n" "[Seat:*]" "autologin-user=star" "autologin-user-timeout=0" > /etc/lightdm/lightdm.conf.d/50-star-ci.conf; echo STAR_INSTALL_TEST_OK > /etc/star-ci-install-test'
d-i grub-installer/only_debian boolean true
d-i grub-installer/bootdev string /dev/vda
d-i finish-install/reboot_in_progress note
d-i debian-installer/exit/poweroff boolean true
'''


def run(args, **kwargs):
    print("[STAR-INSTALL] $ " + " ".join(map(str, args)), flush=True)
    return subprocess.run(args, check=True, **kwargs)


def iso_paths(name):
    result = run(
        ["xorriso", "-indev", str(ISO), "-find", "/", "-type", "f", "-name", name, "-print"],
        capture_output=True, text=True,
    )
    found = []
    for line in result.stdout.splitlines():
        path = line.strip().strip("'").strip('"')
        if path.startswith("/"):
            found.append(path)
    return found


def extract(iso_path, destination):
    run(
        ["xorriso", "-osirrox", "on", "-indev", str(ISO), "-extract", iso_path, str(destination)],
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
    )


def prepare_installer(work):
    kernels = iso_paths("vmlinuz")
    initrds = set(iso_paths("initrd.gz")) | set(iso_paths("initrd"))
    pairs = []
    for kernel in kernels:
        parts = [part.lower() for part in pathlib.PurePosixPath(kernel).parts]
        if not any(part.startswith("install") for part in parts):
            continue
        parent = str(pathlib.PurePosixPath(kernel).parent).rstrip("/")
        for name in ("initrd.gz", "initrd"):
            candidate = parent + "/" + name
            if candidate in initrds:
                pairs.append((kernel, candidate))
    print("[STAR-INSTALL] Installer kernel candidates: " + repr(kernels), flush=True)
    print("[STAR-INSTALL] Installer initrd candidates: " + repr(sorted(initrds)), flush=True)
    if not pairs:
        raise RuntimeError("No matching Debian Installer kernel/initrd pair was found in the ISO")

    kernel_path, initrd_path = pairs[0]
    kernel = work / "installer-vmlinuz"
    original = work / "installer-initrd"
    modified = work / "installer-initrd-ci.gz"
    extract(kernel_path, kernel)
    extract(initrd_path, original)
    if not kernel.is_file() or kernel.stat().st_size < 1024 * 1024:
        raise RuntimeError("Extracted installer kernel is missing or unexpectedly small")

    root = work / "initrd-root"
    root.mkdir()
    gunzip = subprocess.Popen(["gzip", "-dc", str(original)], stdout=subprocess.PIPE)
    with (root / "unpack.log").open("wb") as log:
        cpio = subprocess.run(["cpio", "-id", "--quiet"], cwd=root, stdin=gunzip.stdout,
                              stdout=log, stderr=log)
    gunzip.stdout.close()
    if gunzip.wait() != 0 or cpio.returncode != 0:
        raise RuntimeError("Could not unpack the Debian Installer initrd")
    (root / "preseed.cfg").write_text(PRESEED, encoding="utf-8")

    with modified.open("wb") as output:
        pack = subprocess.Popen(
            "find . -print0 | cpio --null -o -H newc 2>/dev/null | gzip -1",
            cwd=root, shell=True, stdout=output,
        )
        if pack.wait() != 0:
            raise RuntimeError("Could not repack the test-only installer initrd")
    print("[STAR-INSTALL] Selected " + kernel_path + " + " + initrd_path, flush=True)
    return kernel, modified


def install_disk(work, kernel, initrd):
    disk = work / "star-install-test.qcow2"
    log = EVIDENCE / "installer-serial.log"
    run(["qemu-img", "create", "-f", "qcow2", str(disk), "20G"],
        capture_output=True, text=True)
    command = [
        "qemu-system-x86_64", "-machine", "q35,accel=tcg", "-m", "4096", "-smp", "2",
        "-kernel", str(kernel), "-initrd", str(initrd),
        "-append", "auto=true priority=critical preseed/file=/preseed.cfg console=ttyS0,115200n8 ---",
        "-drive", "file=" + str(disk) + ",if=virtio,format=qcow2",
        "-cdrom", str(ISO), "-boot", "order=d",
        "-netdev", "user,id=net0", "-device", "virtio-net-pci,netdev=net0",
        "-display", "none", "-serial", "file:" + str(log), "-monitor", "none", "-no-reboot",
    ]
    print("[STAR-INSTALL] Installing onto a fresh 20 GiB disposable QEMU disk", flush=True)
    try:
        result = subprocess.run(command, timeout=INSTALL_TIMEOUT, check=False)
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError("Installer did not power off within " + str(INSTALL_TIMEOUT) + " seconds") from exc
    if result.returncode != 0:
        raise RuntimeError("Installer QEMU exited with status " + str(result.returncode))
    if not log.is_file() or log.stat().st_size < 1024:
        raise RuntimeError("Installer produced no meaningful serial log")
    print("[STAR-INSTALL] Installer powered off; starting disk-only verification", flush=True)
    return disk


def monitor_connect(path, process, timeout):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline and process.poll() is None:
        if path.exists():
            sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            sock.settimeout(5)
            try:
                sock.connect(str(path))
                sock.recv(4096)
                return sock
            except OSError:
                sock.close()
        time.sleep(1)
    raise RuntimeError("Installed QEMU monitor did not become available")


def monitor_cmd(sock, command):
    sock.sendall((command + "\n").encode())
    time.sleep(1)
    try:
        return sock.recv(65536).decode(errors="replace")
    except socket.timeout:
        return ""


def verify_disk_boot(disk):
    monitor_path = EVIDENCE / "installed.monitor"
    serial = EVIDENCE / "installed-serial.log"
    screenshot = EVIDENCE / "installed-xfce.ppm"
    for path in (monitor_path, serial, screenshot):
        path.unlink(missing_ok=True)

    command = [
        "qemu-system-x86_64", "-machine", "q35,accel=tcg", "-m", "4096", "-smp", "2",
        "-vga", "std", "-drive", "file=" + str(disk) + ",if=virtio,format=qcow2",
        "-boot", "order=c", "-display", "sdl",
        "-monitor", "unix:" + str(monitor_path) + ",server=on,wait=off",
        "-serial", "file:" + str(serial), "-no-reboot",
    ]
    print("[STAR-INSTALL] Booting from the installed disk with NO ISO attached", flush=True)
    with (EVIDENCE / "installed-qemu.log").open("wb") as qlog:
        proc = subprocess.Popen(command, stdout=qlog, stderr=subprocess.STDOUT)
        monitor = None
        last_ocr = ""
        try:
            monitor = monitor_connect(monitor_path, proc, BOOT_TIMEOUT)
            from PIL import Image, ImageStat
            deadline = time.monotonic() + BOOT_TIMEOUT
            while time.monotonic() < deadline and proc.poll() is None:
                time.sleep(8)
                current = EVIDENCE / "installed-current.ppm"
                monitor_cmd(monitor, "screendump " + str(current))
                if not current.is_file() or current.stat().st_size < 4096:
                    continue
                image = Image.open(current).convert("RGB")
                stats = ImageStat.Stat(image)
                if image.width < 640 or image.height < 400 or max(stats.stddev) < 3:
                    continue
                ocr = subprocess.run(["tesseract", str(current), "stdout"],
                                     capture_output=True, text=True, check=True).stdout
                last_ocr = ocr
                low = ocr.lower()
                desktop = ("applications", "whisker menu", "xfce", "places")
                icons = ("home", "file system", "trash")
                if any(word in low for word in desktop) or sum(word in low for word in icons) >= 2:
                    shutil.copy2(current, screenshot)
                    (EVIDENCE / "installed-xfce-ocr.txt").write_text(ocr, encoding="utf-8")
                    print("[STAR-INSTALL] PASS: installed disk reached XFCE", flush=True)
                    return
            raise RuntimeError("Disk-only boot did not reach recognizable XFCE; OCR=" + repr(last_ocr[:600]))
        finally:
            if monitor:
                monitor.close()
            if proc.poll() is None:
                proc.terminate()
                try:
                    proc.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    proc.wait()


def main():
    if not ISO.is_file():
        raise SystemExit("ISO missing: " + str(ISO))
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    for item in EVIDENCE.iterdir():
        if item.is_file():
            item.unlink()
    with tempfile.TemporaryDirectory(prefix="star-install-ci-") as temporary:
        work = pathlib.Path(temporary)
        kernel, initrd = prepare_installer(work)
        disk = install_disk(work, kernel, initrd)
        verify_disk_boot(disk)
    result = (
        "PASS: Debian Installer installed STAR Light to a disposable 20 GiB virtual disk.\n"
        "PASS: The ISO was detached; the installed disk booted independently to XFCE.\n"
    )
    (EVIDENCE / "RESULTS.txt").write_text(result, encoding="utf-8")
    print(result, flush=True)


if __name__ == "__main__":
    main()
