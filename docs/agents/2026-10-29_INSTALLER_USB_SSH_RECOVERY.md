# Implement the installer SSH toggle and patch the existing USB

**Work order, 2026-10-29.** The owner requests both a permanent installer UI
change and an immediate patch to the existing installer USB. Do this on the
Linux host; do not build or run virtual machines on the Mac. The Acer is at a
GRUB prompt and is connected to the Mac by Ethernet. The USB is the LaCie
iamaKey, approximately 8 GB. The owner does not require a USB backup.

1. **Implement the installer change in the repository.** Add an obvious,
   localized on/off SSH toggle to the Wi-Fi page. It controls SSH on the
   **currently running live installer**, immediately, without beginning an
   install or changing the installed OS. Default off; turning it on starts
   ordinary SSH with username `greia` and password `greia`; turning it off
   stops SSH. Show the actual result or an actionable failure, and support both
   mouse and keyboard. Keep the Wi-Fi setup and existing navigation usable.
2. Add the live-installer-only OpenSSH server, required dependencies and
   `greia` account. Use standard password authentication and ordinary
   password-authenticated `sudo`; root SSH stays disabled. Start the service
   only on toggle, generate host keys on the booted machine, and ensure the
   SSH unit's existing `prepare-developer-ssh` drop-in and effective sshd
   configuration really allow the requested login. The live UI is unprivileged:
   use an explicit, narrowly scoped root service operation for start/stop and
   verify the actual service state. Do not grant passwordless generic root or
   alter the installed target's SSH policy.
3. Add focused tests for toggle on/off, failures, unauthorized callers,
   keyboard/mouse operation, localization and live-image composition. Commit
   the source and tests to `main` and push them. Preserve unrelated work. Do not
   call the toggle complete until the patched USB actually runs it.
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
