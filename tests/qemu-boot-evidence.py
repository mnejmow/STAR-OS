#!/usr/bin/env python3
"""Graphical BIOS/UEFI boot evidence test for STAR OS."""
import os
import pathlib
import socket
import subprocess
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = ROOT / "output"
ISO = OUT / "STAR-1.0-amd64.iso"
EVIDENCE = OUT / "boot-evidence"
EVIDENCE.mkdir(parents=True, exist_ok=True)
TIMEOUT = int(os.environ.get("STAR_BOOT_TIMEOUT", "300"))


def monitor_command(sock, command):
    sock.sendall((command + "\n").encode())
    time.sleep(2)
    try:
        return sock.recv(65536).decode(errors="replace")
    except socket.timeout:
        return ""


def screenshot(sock, path):
    reply = monitor_command(sock, "screendump " + str(path))
    if not path.exists() or path.stat().st_size < 4096:
        raise RuntimeError("QEMU did not produce a usable screenshot: " + reply)


def main():
    if not ISO.is_file():
        raise SystemExit("ISO missing: " + str(ISO))
    subprocess.run(["sha256sum", "-c", str(ISO) + ".sha256"], cwd=OUT, check=True)
    ovmf_code = pathlib.Path("/usr/share/OVMF/OVMF_CODE_4M.fd")
    ovmf_vars_template = pathlib.Path("/usr/share/OVMF/OVMF_VARS_4M.fd")
    if not ovmf_code.is_file() or not ovmf_vars_template.is_file():
        raise SystemExit("Matching OVMF 4M firmware pair not found")

    results = []
    for mode in ("bios", "uefi"):
        sock_path = EVIDENCE / (mode + ".monitor")
        log_path = EVIDENCE / (mode + ".log")
        shot_path = EVIDENCE / (mode + ".ppm")
        vars_path = EVIDENCE / (mode + ".vars.fd")
        for p in (sock_path, shot_path, log_path):
            p.unlink(missing_ok=True)
        if mode == "uefi":
            vars_path.write_bytes(ovmf_vars_template.read_bytes())

        args = [
            "qemu-system-x86_64", "-machine", "q35,accel=tcg",
            "-m", "4096", "-smp", "2", "-vga", "std",
            "-cdrom", str(ISO), "-boot", "order=d",
            "-display", "sdl", "-monitor", "unix:" + str(sock_path) + ",server=on,wait=off",
            "-serial", "file:" + str(EVIDENCE / (mode + ".serial.log")),
            "-no-reboot", "-no-shutdown",
        ]
        if mode == "uefi":
            args += [
                "-drive", "if=pflash,format=raw,unit=0,readonly=on,file=" + str(ovmf_code),
                "-drive", "if=pflash,format=raw,unit=1,file=" + str(vars_path),
            ]

        print("[STAR] Launching " + mode.upper() + " graphical boot, 4 GiB RAM", flush=True)
        with log_path.open("wb") as log:
            proc = subprocess.Popen(args, stdout=log, stderr=subprocess.STDOUT)
            try:
                deadline = time.monotonic() + TIMEOUT
                monitor = None
                while time.monotonic() < deadline and proc.poll() is None:
                    if sock_path.exists():
                        try:
                            monitor = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                            monitor.settimeout(3)
                            monitor.connect(str(sock_path))
                            monitor.recv(4096)
                            break
                        except OSError:
                            if monitor:
                                monitor.close()
                            monitor = None
                    time.sleep(1)
                if monitor is None:
                    raise RuntimeError("Could not connect to QEMU monitor for " + mode)
                monitor.settimeout(4)

                # Preserve evidence of the actual boot menu before selecting
                # the default Live system entry.
                time.sleep(3)
                screenshot(monitor, EVIDENCE / (mode + "-boot-menu.ppm"))
                print("[STAR] Captured " + mode + "-boot-menu.ppm", flush=True)

                # The Debian live image presents an interactive boot menu with
                # no automatic timeout. Inject Enter through the QEMU monitor,
                # then inspect the framebuffer. Some UEFI/OVMF combinations can
                # miss the first short key event, so retry with a held keypad
                # Enter only when the menu is still visibly present.
                from PIL import Image
                menu_ocr = subprocess.run(
                    ["tesseract", str(EVIDENCE / (mode + "-boot-menu.ppm")), "stdout"],
                    capture_output=True, text=True, check=True
                ).stdout.lower()
                monitor_command(monitor, "sendkey ret 500")
                time.sleep(5)
                post_boot = EVIDENCE / (mode + "-post-boot.ppm")
                screenshot(monitor, post_boot)
                post_ocr = subprocess.run(
                    ["tesseract", str(post_boot), "stdout"],
                    capture_output=True, text=True, check=True
                ).stdout.lower()
                menu_markers = ("live system", "start installer", "enter: boot")
                if any(marker in post_ocr for marker in menu_markers):
                    print("[STAR] Menu still visible; retrying with keypad Enter", flush=True)
                    monitor_command(monitor, "sendkey kp_enter 1000")
                    time.sleep(5)
                    screenshot(monitor, post_boot)
                print("[STAR] Sent boot selection for " + mode.upper(), flush=True)
                print("[STAR] Captured " + mode + "-post-boot.ppm", flush=True)

                # Give firmware, bootloader and live system time to render.
                checkpoints = [30, 60, 120, 180, 240, TIMEOUT]
                started = time.monotonic()
                for checkpoint in checkpoints:
                    remaining = checkpoint - (time.monotonic() - started)
                    if remaining > 0:
                        time.sleep(remaining)
                    if proc.poll() is not None:
                        raise RuntimeError(mode + " QEMU exited early with " + str(proc.returncode))
                    target = EVIDENCE / (mode + "-%03d.ppm" % checkpoint)
                    screenshot(monitor, target)
                    print("[STAR] Captured " + str(target.name), flush=True)
                final_image = EVIDENCE / (mode + "-final.ppm")
                screenshot(monitor, final_image)
                # Require a rendered, non-uniform framebuffer, not just a live QEMU process.
                from PIL import Image, ImageStat
                image = Image.open(final_image).convert("RGB")
                stat = ImageStat.Stat(image)
                if image.width < 640 or image.height < 400 or max(stat.stddev) < 3:
                    raise RuntimeError(mode + " framebuffer is blank or invalid")
                ocr = subprocess.run(["tesseract", str(final_image), "stdout"], capture_output=True, text=True, check=True).stdout
                (EVIDENCE / (mode + "-ocr.txt")).write_text(ocr)
                ocr_lower = ocr.lower()
                # GNOME may render "Type to search" instead of the traditional
                # "Activities" label in the overview. Accept either signature.
                desktop_markers = ("activities", "type to search")
                if not any(marker in ocr_lower for marker in desktop_markers):
                    raise RuntimeError(mode + " did not reach the GNOME desktop; OCR evidence: " + repr(ocr[:500]))
                results.append(mode + ": GNOME desktop confirmed (%dx%d)" % image.size)
                monitor.close()
            finally:
                if proc.poll() is None:
                    proc.terminate()
                    try:
                        proc.wait(timeout=10)
                    except subprocess.TimeoutExpired:
                        proc.kill()
                        proc.wait()
    (EVIDENCE / "RESULTS.txt").write_text("\n".join(results) + "\n")
    print("\n".join(results), flush=True)


if __name__ == "__main__":
    main()
