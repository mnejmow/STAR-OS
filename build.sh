#!/usr/bin/env bash
set -Eeuo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"
if [[ "$EUID" -ne 0 ]]; then echo "Run with: sudo ./build.sh" >&2; exit 1; fi
for cmd in lb xorriso mksquashfs; do command -v "$cmd" >/dev/null 2>&1 || { echo "Missing build dependency: $cmd" >&2; exit 1; }; done
mkdir -p output
echo "[STAR] Configuring Debian 13 GNOME live system..."
lb config
echo "[STAR] Building ISO..."
lb build
ISO="$(find "$ROOT" -maxdepth 1 -type f -name '*.iso' -print -quit)"
[[ -n "$ISO" ]] || { echo "No ISO found after lb build." >&2; exit 1; }
rm -f "$ROOT/output/STAR-1.0-amd64.iso"
mv "$ISO" "$ROOT/output/STAR-1.0-amd64.iso"
chmod 0644 "$ROOT/output/STAR-1.0-amd64.iso"
sha256sum "$ROOT/output/STAR-1.0-amd64.iso" > "$ROOT/output/STAR-1.0-amd64.iso.sha256"
echo "[STAR] ISO created: output/STAR-1.0-amd64.iso"
