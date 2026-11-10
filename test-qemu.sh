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
    [[ ! -r "$candidate" ]] || { OVMF_CODE="$candidate"; break; }
  done
  if [[ -z "$OVMF_CODE" ]]; then
    OVMF_CODE="$(find /usr/share -type f -iname 'OVMF_CODE*.fd' -print -quit 2>/dev/null || true)"
  fi
  [[ -n "$OVMF_CODE" && -r "$OVMF_CODE" ]] || { echo "Usable OVMF_CODE firmware not found; install the ovmf package." >&2; exit 1; }
  echo "[STAR] Using UEFI firmware: $OVMF_CODE"
  ARGS+=(-bios "$OVMF_CODE");;
*) echo "Usage: $0 [bios|uefi]" >&2; exit 2;;
esac
exec qemu-system-x86_64 "${ARGS[@]}"
