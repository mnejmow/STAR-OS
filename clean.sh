#!/usr/bin/env bash
set -Eeuo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"
[[ "$EUID" -eq 0 ]] || { echo "Please run: sudo ./clean.sh" >&2; exit 1; }
lb clean --purge
echo "[STAR] Build workspace cleaned. output/ is preserved."
