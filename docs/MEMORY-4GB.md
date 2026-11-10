# STAR OS — 4 GB runtime target

The selected profile is intentionally leaner than the full GNOME metapackage.
It targets a usable GNOME desktop on a 4 GB AMD64 virtual machine.

## Memory-conscious choices
- Explicit GNOME component packages rather than the full GNOME metapackage.
- Lightweight app set; no office suite, creative suite, IDE bundle, or container stack.
- zram-tools with zstd compression, configured to use 25% of RAM.
- Conservative VM swappiness settings.
- Inter and Noto fonts.

## Suggested VM settings
- RAM: 4096 MB minimum; 6144–8192 MB recommended.
- CPU: 2 vCPUs minimum; 4 recommended.
- Disk: 25 GB minimum for an installed system.

zram helps with short memory spikes but is not a replacement for physical RAM.
Do not claim the 4 GB target is validated until the actual ISO is tested interactively.
