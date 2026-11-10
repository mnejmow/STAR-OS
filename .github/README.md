# Remote ISO build

Open **Actions → Build STAR OS ISO** and select **Run workflow**.
A successful run publishes the ISO, SHA256 checksum, and BIOS/UEFI QEMU
smoke-test logs as the artifact `STAR-OS-1.0-amd64-BIOS-UEFI`.

Download and extract the artifact, then verify:
```bash
sha256sum -c STAR-1.0-amd64.iso.sha256
```

The workflow only makes an ISO available after the remote build succeeds.
QEMU smoke tests do not certify full desktop hardware or installer workflows.
