#!/usr/bin/env bash
set -Eeuo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ISO="$ROOT/output/STAR-1.0-amd64.iso"
MODE="${1:-bios}"
[[ -f "$ISO" ]] || { echo "ISO not found: $ISO" >&2; exit 1; }
command -v qemu-system-x86_64 >/dev/null 2>&1 || { echo "Install qemu-system-x86." >&2; exit 1; }
[[ ! -f "$ISO.sha256" ]] || (cd "$ROOT/output" && sha256sum -c "$(basename "$ISO").sha256")
ARGS=(-m 4096 -smp 2 -cdrom "$ISO" -boot d -display gtk)
[[ ! -e /dev/kvm ]] || ARGS+=(-enable-kvm -cpu host)
case "$MODE" in
bios) echo "[STAR] Starting legacy BIOS test (4 GiB RAM)...";;
uefi)
  OVMF_CODE=""
  for candidate in /usr/share/OVMF/OVMF_CODE_4M.fd /usr/share/OVMF/OVMF_CODE.fd /usr/share/edk2/ovmf/OVMF_CODE.fd; do
    [[ ! -f "$candidate" ]] || { OVMF_CODE="$candidate"; break; }
  done
  [[ -n "$OVMF_CODE" ]] || { echo "Install OVMF." >&2; exit 1; }
  ARGS+=(-bios "$OVMF_CODE");;
*) echo "Usage: $0 [bios|uefi]" >&2; exit 2;;
esac
exec qemu-system-x86_64 "${ARGS[@]}"
