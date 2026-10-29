# Acer A/B install failure: ENOSPC while regenerating initramfs

Date: 2026-10-29 · Evidence class: **physical Acer installer USB log + local
SYSTEM_A reproduction** (not physical install acceptance).

## Recovered log

The installer wrote
`GREIA_EFI/greia-logs/last-install-failure.log` on the LaCie USB. Raw copy:
[`acer/2026-10-29_INSTALLER_USB_FAILURE/last-install-failure.txt`](acer/2026-10-29_INSTALLER_USB_FAILURE/last-install-failure.txt).
The transaction failed in the hardware-support package step:

```text
Processing triggers for initramfs-tools (0.142+deb12u3) ...
update-initramfs: Generating /boot/initrd.img-6.1.0-54-686-pae
zstd: error 70 : Write error : cannot write block : No space left on device
E: mkinitramfs failure zstd -q -9 -T0 70
dpkg: error processing package initramfs-tools (--configure):
 installed initramfs-tools package post-installation script subprocess
 returned error exit status 1
```

The same `apt-get install` successfully unpacked and configured
`iucode-tool`, `intel-microcode`, `firmware-misc-nonfree` and
`firmware-realtek`; only the initramfs trigger failed. This is not a package
source, sandbox or disk-identity failure.

## Capacity arithmetic

The release bundle and the Acer A/B layout were reproduced locally:

| Fact | Value |
|---|---|
| SYSTEM_A slot | 1,744,830,464 bytes (1,664 MiB) |
| Payload ext4 image | 1,429,004,288 bytes |
| Payload used blocks | 348,724 / 348,878 (154 free) |
| Free after expansion | 76,232 blocks = 297.8 MiB total |
| Root-reserved blocks | 21,298 = 83.2 MiB |
| Root-usable free before support | ~202 MiB |
| Hardware support installed | 81.8 MB (plus 27.5 MB apt cache during install) |
| `mkinitramfs` temporary tree peak | 186,020 KiB = 181.7 MiB |
| New compressed initrd | 42 MiB |

The old finalizer ran `apt-get` and `update-initramfs` entirely on the target
slot. `mkinitramfs` therefore needed roughly 182 MiB of transient tree plus
the 42 MiB output, on top of the support packages and apt cache, and hit
ENOSPC. The 64 MiB `FINALIZATION_GROWTH_BYTES` bound covers the final initrd
growth, but was never a bound for `mkinitramfs`'s transient working tree.

Local reproduction on the exact bundle payload and 1,664 MiB slot failed with
the identical zstd ENOSPC. Re-running with the new RAM scratch path succeeded:
the initrd is 42 MiB and the target retained ~102 MiB free.

## Fix

`TargetHardwareSupportInstaller` now mounts a bounded 256 MiB tmpfs at
`/run/greia-installer-scratch` inside the already-mounted target `/run`, and
runs the support `apt-get install` with:

- `TMPDIR=/run/greia-installer-scratch/tmp` (the `mkinitramfs` temporary
  module/firmware tree);
- `Dir::Cache::archives=/run/greia-installer-scratch/apt` (the offline
  `.deb` cache).

Only the final compressed initrd is written to the target slot, within the
existing 64 MiB growth bound. The scratch mount is recorded in the normal
reverse-order cleanup path and disappears with the install transaction.
Regression coverage:
`tests/test_installer_hardware_support_install.py`.

## Evidence boundary

The exact pre-fix failure was reproduced locally and the post-fix path
completed the same package install and initramfs generation. Physical Acer
reinstall and first boot are **still required** before claiming install
acceptance.

## Built media

Installer
`7869b6b59e973ecd016facc3035ad29b7219a65efac394b26094ed32d447daae`
(2,270,167,040 bytes, live media ID
`bd758e75-ca71-4599-83fb-628ce0d1b26a`) was built with the fix, verified in
QEMU to reach the interactive installer language screen, and flashed to the
owner-authorized LaCie `/dev/sdc` (`iamaKey`, serial `eca3505216d7d3`).
The first 2,270,167,040 bytes read back byte-identical, and the flashed
squashfs contains `INSTALL_SCRATCH_REL_PATH = "run/greia-installer-scratch"`,
the 256 MiB tmpfs options, `TMPDIR`, and `Dir::Cache::archives`. Physical
Acer reinstall remains pending.
