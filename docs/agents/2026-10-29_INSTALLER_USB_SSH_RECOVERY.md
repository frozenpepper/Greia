# Patch the existing Greia installer USB for recovery SSH

**Work order, 2026-10-29.** The owner authorizes a Linux-based agent to patch
the existing installer USB so the Acer can boot the **live installer** and the
agent can connect with ordinary SSH, username `greia`, password `greia`. The
owner does not want builds or virtual machines on the Mac. This is a temporary
recovery USB, not a release image, and is not authorization to install Greia or
write to the Acer's internal disk.

1. Identify the existing **LaCie iamaKey, approximately 8 GB** by actual USB
   device identity and partition inspection. It has a 64 MiB FAT EFI partition
   and an ext4 `PIP_INSTALL` partition. Recheck the device and mount source
   before any write; never guess a device path. Work on a Linux host and use
   scratch space outside the USB. No backup copy of the USB is required.
2. Mount `PIP_INSTALL` and inspect `/live/filesystem.squashfs`,
   `/boot/grub/grub.cfg`, and `/payload/greia-release.greiaupdate`. Extract
   the live squashfs to scratch. The A/B release bundle is the installed-system
   payload: **do not alter it, the partition table, bootloader, firmware, or
   the Acer disk**. Record the bundle hash before and after. The EFI partition
   can contain installer failure logs; preserve them.
3. Patch the **extracted live installer only** to include working Debian
   Bookworm i386 OpenSSH server and `sudo`, with all required dependencies.
   Provision the live account `greia` with password `greia`, ordinary SSH
   password authentication and password-authenticated `sudo`. Allow only
   `greia` for this recovery login; keep root SSH login disabled. Configure
   SSH to start automatically on this recovery USB so the agent can connect
   before any installer interaction. Do not enable SSH or create credentials
   in the A/B release bundle or on the installed target. This emergency patch
   does **not** implement the requested future Wi-Fi-screen toggle.
4. Preserve the installer's existing Wi-Fi, wired networking, graphical UI and
   socket-activated install transaction. Check `ssh.service` and its existing
   `prepare-developer-ssh` drop-in: provision a working host-key bootstrap and
   effective SSH policy rather than assuming that enabling the unit is enough.
   Make sure startup is enabled in the live root and no host keys or private
   credentials are committed to the repository. Generate host keys on the
   booted live machine. Handle chroot mounts and package-service startup safely;
   do not run target package hooks on the Linux host itself.
5. Repack the modified live squashfs on the **Linux host**, validate it and
   replace only `/live/filesystem.squashfs` on the USB. Check available space
   before replacement, flush and unmount cleanly. No complete Greia image build, reflash, repartition or
   write to any other physical disk is needed.
6. Verify the patched squashfs contains `sshd`, the `greia` account, enabled
   SSH and effective password policy; verify the SSH unit can generate keys and
   that the original release bundle hash is unchanged. Then boot the Acer from
   this USB **without starting an installation** and connect via SSH as
   `greia` / `greia`. Confirm the connected host is the live installer before
   inspecting the internal disk, and mount any installed filesystem read-only
   without journal replay. Never run installation, repair, `fsck`, formatting,
   or other internal-disk writes as part of this recovery.

The installed release candidate uses a **volatile journal**. A previous reboot
may have erased the Parent service's failure logs; do not promise that booting
the USB will recover them. Inspect what remains and report exact evidence. Keep
this recovery USB separate from public/release media; its fixed password and
automatic SSH are intentionally owner-authorized for this recovery session.
Report the USB identity, checks and real Acer connection result. Do not call source or squashfs inspection a live SSH success.
