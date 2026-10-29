# Implement the installer SSH toggle and patch the existing USB

**Work order, 2026-10-29.** The owner requests both a permanent installer UI
change and an immediate patch to the existing installer USB. Do this on the
Linux host; do not build or run virtual machines on the Mac. The Acer is at a
GRUB prompt and is connected to the Mac by Ethernet. The USB is the LaCie
iamaKey, approximately 8 GB. The owner does not require a USB backup.

1. **The installer toggle is now implemented in source.** Use current `main`:
   the Wi-Fi page controls the running installer SSH service, with `greia` /
   `greia`, off by default on ordinary installer images, with keyboard/pointer
   behavior and localized copy. The source includes OpenSSH, sudo, Avahi, the live account and the
   narrowly scoped local service operation. Source/demo tests are not live SSH
   acceptance. Do not reimplement the toggle.
2. Apply all affected installer Python sources, locale tables, live service
   composition and package/account provisioning from current `main` to the
   extracted live root. Ensure the resulting effective SSH policy and host-key
   bootstrap actually work on the live system; do not alter installed Greia.
3. Run the focused installer SSH and layout tests on the Linux host.
4. **Patch the existing USB in place on Linux.** Identify the LaCie device by
   actual USB identity and partition inspection; recheck before writing. It has
   a 64 MiB FAT EFI partition and an ext4 `PIP_INSTALL` partition. Mount the
   installer partition, extract `/live/filesystem.squashfs` to scratch, and
   apply the committed installer code, service, package and account changes to
   that live root. Repack the squashfs on the Linux host and replace only
   `/live/filesystem.squashfs` on the USB. Check space first; flush and unmount.
   No full Greia image build, USB backup, reflash or repartition is requested.
   Preserve any EFI failure logs and leave
   `/payload/greia-release.greiaupdate` byte-identical: it is the installed OS
   payload, not the live installer. Do not touch the Acer internal disk.
5. Boot the Acer from the patched USB **without starting installation**. On
   the Wi-Fi page, turn SSH on and connect from the Mac with `greia` / `greia`.
   Verify an actual SSH login, that off stops access and on restores it, and
   that the installer still operates. Confirm the remote host is the live
   installer before inspecting the installed disk. Inspect installed files
   read-only without journal replay; never format, repair or install over the
   internal disk. Report what was actually tested and any failure.

The installed release uses a **volatile journal**, so a reboot may have removed
its prior Parent-service failure logs. Inspect what is available and report the
exact evidence; do not promise that the old logs exist. The recovery USB is
not a public release artifact. The owner separately requested carrying all
installer-selected settings into A/B installations; the source fixes are
already on `main`, but this USB patch must not overwrite the existing installed
OS bundle or claim that bundle has been rebuilt with those fixes.
