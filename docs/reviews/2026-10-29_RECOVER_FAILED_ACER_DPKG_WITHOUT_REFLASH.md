# Recover failed Acer installer logs without SSH or reflashing (2026-10-29)

**Current failure:** The 2026-10-29 physical Acer now boots the new A/B GUI
but reports `hardware-support command failed` at the end of installation,
with `dpkg` exit 1. The `debconf`/`apt-utils` text is **not the underlying
error**. The broken install is retained on the internal disk as SYSTEM_A.

**Do not re-run the installer, format the disk, or reflash the USB before
recovering this evidence.** The existing installer USB's GRUB can read the
ext4 SYSTEM_A partition directly, without a functioning installed OS,
SSH, login credentials, or installing a different operating system.

## Option A — GRUB only (no Linux boot, no writes)

1. Boot the *existing* Greia USB, enter its GRUB menu/command line the same way
   used previously to display diagnostic logs (typically `c` at the menu;
   the owner recovery credential may be requested).
2. At the `grub>` prompt type these **separate** commands:

   ```text
   insmod ext2
   set pager=1
   search --label GREIA_SYS_A --set=slot
   echo $slot
   ls ($slot)/var/log/apt/
   cat ($slot)/var/log/apt/term.log
   ```

   GRUB's `search --label` resolves the partition by its actual filesystem
   label; it **does not assume** whether USB or internal disk is `hd0`.
   `cat` displays package output without mounting or modifying the partition.
   Advance the pager with Space/Enter, photograph the **actual dpkg failure**
   and the package named near `Errors were encountered while processing`.
   If the apt term log is absent, try:

   ```text
   cat ($slot)/var/log/dpkg.log
   ```

   GRUB cannot conveniently tail large logs; option B is better for that.
   If `search` finds no `GREIA_SYS_A`, stop and report that; do not
   guess a partition or change it.

## Option B — boot this same USB into a temporary local shell (read only)

This is useful if option A's log is too long. It changes the **current boot
only**, not the image on the USB.

1. At the USB GRUB menu edit the Greia installation entry (`e`). At the end
   of its existing `linux /live/vmlinuz ...` line add
   `init=/bin/bash` and remove `quiet splash loglevel=0` if necessary
   to expose the text console. Boot the edited entry (`Ctrl+X`).
   On Debian live-boot/initramfs-tools this normally starts a root shell
   rather than systemd/Greia. If no shell appears, use option A; do not
   rewrite the image.
2. Once at a root shell, discover by filesystem label and mount **read-only
   without journal replay**:

   ```sh
   blkid
   mkdir -p /mnt/failed-greia
   mount -t ext4 -o ro,noload LABEL=GREIA_SYS_A /mnt/failed-greia
   tail -n 100 /mnt/failed-greia/var/log/apt/term.log
   tail -n 60 /mnt/failed-greia/var/log/dpkg.log
   df -h /mnt/failed-greia
   ```

   No internal disk write is required. If the shell lacks a working
   `/dev` or label lookup, use option A instead of improvising a device
   write. Do not run `fsck -y`, `dpkg --configure -a`, `apt install`,
   `mount -o rw`, `grub-install` or `wipefs` in this recovery session.
3. Photograph/copy the actual failing package lines. Then power off; the
   edit to GRUB's boot command line is not permanent.

## Code tracing: what the failure proves

* `transaction_service.py` accepts an explicitly confirmed local request
  and calls `build_ab_executor` / `execute_fresh_ab_install`.
* `fresh_ab_install.py` creates the DOS table (P1 GREIA_BOOT, P2
  GREIA_SYS_A, P3 GREIA_SYS_B, P4 GREIA_PERSIST), streams the release
  into SYSTEM_A, and finalizes A **before** PERSIST/GRUB.
* `slot_writer.SlotFinalizer.finalize` calls
  `SharedSlotPackageInstaller` to install selected firmware and microcode
  in mounted SYSTEM_A.
* `device_seams.py` selects packages from Acer sysfs + a frozen support
  pool. The selection may differ from QEMU and the legacy single-root
  installer.
* `hardware_support_install.py` bind mounts minimal chroot filesystems
  and the offline apt repository, then executes three `apt-get` commands
  (`update`, `install`, `clean`). The reported failure is in the
  `install` invocation, when `dpkg` returns nonzero.
* `SubprocessHardwareSupportRunner` previously displayed only stderr
  when stderr was non-empty, concealing the real dpkg failure in stdout.
  That diagnostic defect was fixed separately, but the flashed image
  cannot inherit this change.
* The old `greia-install-transaction.service` deliberately stripped
  Linux capabilities and constrained file operations, tasks, and syscalls.
  Its own comments document a succession of Acer installation failures
  caused by those restrictions. The service is an **offline root OS
  installer**; keeping those restrictions was not justified. Source now
  uses ordinary root privileges with the existing local-only socket.
  This removes a strongly suspected failure *class*, but the exact current
  dpkg cause cannot be certified without a log.

**Next engineering step:** use the original failure output to name the actual
package and error. Reproduce its `apt-get install`/maintainer script under
the simplified service in a disposable i386 SYSTEM_A root with the Acer-selected
hardware-support packages. Only after it passes should a new image be built
and tested all the way through UI > fresh A/B install > first boot.

## Owner-authorized rebuild/reflash note (2026-10-29)

The repository owner explicitly requested a fresh installer build and LaCie
reflash after reviewing this recovery guide. Image
`b853330f624d816077c1149aa715e03aa2886e3571bbb834bb3e868d6072a436`
now includes `greia-logs/last-install-failure.log` persistence to the
installer FAT32 partition. This does not recover the existing internal-disk
SYSTEM_A transcript; the read-only recovery options above remain the
preferred evidence path, and any reinstall or internal-disk write remains a
separate destructive action.
