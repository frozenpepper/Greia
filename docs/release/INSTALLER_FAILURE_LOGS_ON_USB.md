# Installer failures: logs on the same USB key

**Applies to installer images built after 2026-10-29 with the
`greia-installation-failure` USB logging changes.**
Earlier flashed images do **not** gain this feature by pulling Git commits.

The installer USB image has two partitions: the ext4 live root
(`PIP_INSTALL`) and a 64 MiB FAT32 EFI partition (`GREIA_EFI`).
The image builder now places the same live-media ID on both partitions.

On a failed install, the privileged transaction service:

1. Retains the command argv, non-zero exit code and both the captured
   stdout/stderr streams (including apt/dpkg package maintainer-script output).
2. Adds the Python exception and traceback, and retains the failure in the
   live runtime and the service journal.
3. Mounts the *already-present* USB FAT32 EFI partition **read-only first**,
   verifies that its media ID matches the booted live image, and remounts it
   writable only for the diagnostic file.
4. Atomically replaces `greia-logs/last-install-failure.log`, syncs it
   to the filesystem and unmounts. No partition is created or formatted,
   and no EFI bootloader files are changed.
5. Reports **USB log saved** with its path on the installer error screen,
   or **USB log could not be saved** when the USB is absent, full, read-only
   or identity verification fails. Logging must never hide the original
   installation failure.

**Retrieve after failure:** Leave the installer USB in place while the
error screen reports that the log has been saved. Power off normally,
remove the key, and open the `GREIA_EFI` FAT32 partition on a Windows
or macOS computer:

```text
greia-logs/last-install-failure.log
```

On macOS an EFI partition may not mount automatically. In Terminal use
`diskutil list` to identify the **removable USB** and then
`diskutil mount diskXs1` (replace `diskXs1` with that USB's *actual*
first partition; **do not choose an internal disk**). After reading,
eject the USB normally.

This is a **single most recent failure** file, with a UTC timestamp
and a bounded diagnostic transcript. If the installed SYSTEM_A is not
bootable, the USB log remains usable. If the FAT32 partition cannot be
written, the journal and temporary runtime log are fallback evidence,
but the screen must not falsely claim that USB persistence succeeded.

**Acceptance boundary:** GitHub source tests use mocked mounts; an actual
rebuilt USB image has to be tested once in QEMU for both a deliberately
failed install (file readable after power-off/remount) and an ordinary
successful install before announcing it release-ready.
