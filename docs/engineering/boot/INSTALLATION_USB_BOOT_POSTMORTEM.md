# Greia Installer USB Boot — Full Post-Mortem

**Status:** accepted engineering record  
**Date:** 2026-08-18  
**Audience:** install/boot engineers, release engineering, agents  
**Scope:** the complete, blow-by-blow account of how the Greia live installer
finally booted from a USB key on the reference Acer Aspire One (2010-era,
Intel Atom N270, BIOS-only, no UEFI), what was borrowed from the antiX
live-image toolchain, and every dead end that was ruled out along the way.

> This document is intentionally narrative. The durable rules are captured in
> `INSTALLATION_ISSUES_LOG.md`; this file preserves the *why* and the *how* so a
> future engineer does not repeat the exploration.

---

## 1. Context: the boot problem

The Acer Aspire One that Greia targets has:

- a BIOS-only firmware (no UEFI, no Secure Boot, legacy MBR boot only);
- **two** SD card readers that the firmware refuses to boot from at all
  (the BIOS does not enumerate them as boot devices);
- one USB port, and a BIOS F12 boot menu that *does* list USB sticks;
- no CD/DVD drive;
- Wi-Fi only networking (which matters for recovery, see §8).

The Greia installer is a live system: kernel + initramfs + a squashfs
filesystem + a `payload/` squashfs containing the installable target image.
For the installer to run, that whole tree must be presented to a bootloader
that the Acer's BIOS will actually execute.

The repository previously produced a *raw disk image* (`*.img`) whose MBR
contained **GRUB**. The plan was to write that image to a USB key and boot it.
That plan failed in a very specific way, and the workaround taught us the
properties the Acer's firmware actually requires.

---

## 2. Attempt 1 — write the Greia raw disk image (GRUB MBR) to the USB key

**What was done:** `dd` the official `greia-os-installer-*.img` to the USB key,
byte-for-byte, verified by re-reading the device and comparing SHA-256.

**What happened:** the Acer's F12 boot menu listed the stick, selected it, and
then the screen stayed grey/black with no cursor, no GRUB menu, no error — the
machine sat there and then rebooted into the internal disk.

**Analysis:**
- The same image booted *fine* in QEMU (BIOS boot, SeaBIOS): GRUB printed,
  the menu appeared, the live system started. So the image itself was valid.
- The Acer's firmware therefore executed something, or failed to execute the
  MBR and fell through to the next boot device. Either way, **GRUB's MBR boot
  code did not produce a visible result on this firmware with this stick.**

**Key observation:** the *internal disk's* GRUB worked perfectly (it is what
eventually booted the installed Greia OS). So the failure is specific to
**GRUB's MBR written to this particular USB stick, read by this particular
BIOS** — a firmware/media-adapter interaction, not a GRUB defect in general.

---

## 3. Attempt 2 — GRUB with a diagnostic menu (ruling out "it boots but is invisible")

**What was done:** replaced the USB's `grub.cfg` with a minimal menuentry that
only printed `USB BOOTED OK - GRUB IS RUNNING` and slept. No kernel, no
filesystem access, no graphics — just a serial-ish console echo on the VT.

**What happened:** still nothing on screen. No text, no menu, no cursor.

**Conclusion:** the Acer's BIOS was **not executing GRUB's MBR code from this
USB stick at all**. If it had, the `echo` would have printed. This ruled out
"GRUB loads but the framebuffer is blank" and left only "the MBR is not being
executed".

**Relevant hardware facts checked:**
- MBR signature `55 aa` was present on the stick.
- The partition was marked bootable.
- GRUB stage 1 (`boot.img`) was present in the MBR gap.
- The stick itself is a LaCie iamaKey V2 (USB 2.0) — a normal, working device.

---

## 4. Attempt 3 — syslinux with a clean FAT32 partition

**What was done:** built a fresh bootable USB the "textbook" way:

1. wipe the stick;
2. create one **active FAT32 primary partition** (type `c`, bootable);
3. `mkfs.vfat -F 32`;
4. copy `vmlinuz`, `initrd.img`, `filesystem.squashfs` to the partition root;
5. install syslinux to the partition VBR (`syslinux --install`);
6. write the syslinux MBR (`mbr.bin`) to the stick's first 440 bytes;
7. add a `syslinux.cfg` with `DEFAULT live`, `LINUX /vmlinuz`,
   `INITRD /initrd.img`, `APPEND boot=live …`.

**What happened:** this time we saw **SYSLINUX 6.04 print, then
`Loading /vmlinuz... ok` / `Loading /initrd.img...ok`** — the first visible
sign of life from the stick. The kernel then started and immediately hit the
`BOOT FAILED` live-boot error (covered in §6), but the bootloader itself had
worked.

**Why syslinux worked where GRUB did not:** syslinux's MBR is a tiny
self-contained loader that reads the VBR of the active partition directly from
the disk with its own minimal INT 13h code. It does not need to discover
kernel modules, search partitions by UUID, or set up a graphical terminal —
it just loads `ldlinux.sys` from the active partition and hands control to it.
The Acer's BIOS would execute that. GRUB's stage 1 needs to load
`core.img` from the partition, which involves more elaborate disk reads that
this firmware + stick combination would not complete silently.

**Important:** this is exactly the mechanism the antiX live ISO uses (see §7),
which is why the same stick class works with antiX on the same machine.

---

## 5. Dead ends ruled out along the way (so nobody repeats them)

These were all tested and *excluded* as the cause of the USB non-boot:

| Candidate cause | How it was ruled out |
|---|---|
| The USB stick is defective | The same stick read/wrote correctly on the build host; QEMU booted the same image from it. |
| The image is corrupt | SHA-256 of the written device matched the source image exactly. |
| GRUB config is broken | A minimal GRUB config that only echoes printed nothing; QEMU showed the real GRUB menu from the same image. |
| The MBR is missing/invalid | `55 aa` present, partition marked active, GRUB stage 1 present. |
| The firmware needs a different partition type | FAT32 active partition (the most compatible) was used; still nothing with GRUB. |
| The firmware cannot boot USB at all | antiX had been installed on this machine from a USB stick previously, and syslinux on this stick booted (§4). |
| The display is blank during early boot | syslinux text appeared on screen, so the display path works. |
| `isohybrid` ISO written as-is | An isohybrid ISO's MBR is designed for CD/optical fallback and, on this firmware+stick, produced the `attempt to read or write outside of disk hd0` error (see below). |

**The `isohybrid` ISO detour:** trying to follow the "write the ISO as-is"
pattern, an isohybrid image with isolinux was attempted. This produced a
*visible* error — `attempt to read or write outside of disk hd0` — which
proved the MBR *was* being executed, but the hybrid structure's embedded
partition/geometry assumptions did not match the stick. This was a strong
confirmation that the firmware executes simple MBR/VBR loaders but chokes on
layout-dependent ones.

---

## 6. After boot: the `BOOT FAILED` live-boot identity wall

Once syslinux loaded the kernel, `live-boot` mounted the medium, printed
`mounted filesystem with ordered data mode. Quota mode: none.`, unmounted it,
and reported `BOOT FAILED` / "Unable to find a medium containing a live file
system".

**Root cause:** `live-boot`'s `matches_uuid()` requires the initramfs
`/conf/uuid.conf` to match a `.disk/live-uuid` file **on the medium itself**.
The hand-built USB carried the kernel, initramfs and squashfs, but not the
`.disk/` identity marker. live-boot probes the medium, checks identity, fails,
and aborts.

**Fix:** create `.disk/live-uuid` on the medium containing the exact value
from the initramfs `conf/uuid.conf` (which is also `greia.live_media_id` in
the kernel command line). With that one file present, the live system booted
to the installer.

---

## 7. What was taken from the antiX build toolchain

The turning point was reading how antiX (a Debian derivative that boots on
this exact class of old hardware) builds its bootable media. Two repositories
were studied:

- `antiX-Linux/Build-iso` (fork of `BitJam/build-iso`): the live ISO builder.
- `BitJam/build-iso`: the canonical script (3805 lines) behind it.

The relevant facts extracted:

### 7.1 The bootloader for BIOS is **isolinux**, not GRUB

antiX's ISO burn uses:

```
genisoimage/mkisofs/xorriso -b boot/isolinux/isolinux.bin \
  -no-emul-boot -boot-load-size 4 -boot-info-table \
  -c boot/isolinux/isolinux.cat
```

then `isohybrid` to make the ISO writable to a USB. The **BIOS boot path is
isolinux** (the CD variant of SYSLINUX) with the classic El Torito
no-emulation parameters. GRUB only appears as a *menu entry* that chainloads
to GRUB from the SYSLINUX menu (`lnxboot.img` + `core.img`), and as the UEFI
image — not as the BIOS first-stage loader.

**Lesson applied:** for BIOS-only old hardware, the first-stage bootloader
must be SYSLINUX-family (syslinux for direct USB, isolinux for ISO). That is
precisely what made the Acer execute our USB.

### 7.2 The boot layout is `boot/` + payload at known paths

antiX's ISO tree:

```
boot/isolinux/{isolinux.bin,isolinux.cfg,isolinux.cat,readme.msg,gfx-cpio}
boot/syslinux/{syslinux.cfg,...}          # for USB/removable variants
boot/grub/{grub.cfg,efi.img,i386-pc/core.img}
antiX/{vmlinuz,initrd.gz,linuxfs}          # kernel, initrd, squashfs
.disk/info  version
```

The kernel line in `kernel0.cfg`:

```
LABEL live
    KERNEL /antiX/vmlinuz
    APPEND <live boot options>
    INITRD /antiX/initrd.gz
```

**Lesson applied:** keep the live kernel/initrd/squashfs at stable, documented
paths on the medium, and make the syslinux config point at them explicitly
rather than relying on any auto-detection.

### 7.3 `isohybrid --uefi` for dual compatibility, with a caveat

antiX burns a hybrid ISO and runs `isohybrid --uefi` so the same artifact
boots BIOS (isolinux) and UEFI (EFI image). We confirmed the **BIOS** side is
what matters for the Acer; and we confirmed the hybrid layout is *not* enough
by itself on this stick — the plain active-FAT32 + syslinux VBR approach was
more reliable than the ISO-as-is write (§5).

### 7.4 Text-mode fallback for quirky displays

antiX ships a plain-text menu fallback (`readme.msg` + menu listing) so that
if gfxboot's graphical mode fails on old hardware, the menu still works. We
did not need gfxboot; we kept `syslinux.cfg` minimal and text-based.

### 7.5 Nothing Acer-specific in the toolchain

antiX has no Acer-specific code. The compatibility comes from using the most
conservative BIOS boot primitive (isolinux/syslinux + El Torito
no-emulation + FAT32 active partition) plus an i386/486-compatible kernel
flavour. The same principles apply to any old BIOS-only machine.

---

## 8. The recovery feedback loop that made debugging possible

Two environmental facts shaped how the debugging proceeded:

- The Acer has **no serial console** and no way to capture boot output except
  the LCD.
- Once the installed system's Wi-Fi came up, SSH provided a remote shell, so
  diagnostic patches (Xorg logs, journald persistence, launcher
  instrumentation) were applied over the network and observed without
  touching the keyboard.

The USB boot debugging itself was done entirely by *observable bootloader
output*: each attempt either printed something (syslinux, isolinux error,
live-boot panic) or printed nothing (GRUB). That binary signal is what
narrowed the problem to the first-stage MBR.

---

## 9. The final working recipe

Given a bootable USB key on BIOS-only old hardware, the recipe that worked:

1. **Wipe** the key.
2. Create one **active FAT32 primary partition** (`fdisk`/`sfdisk`:
   `type=c`, `bootable`), starting at sector 2048.
3. `mkfs.vfat -F 32`.
4. Copy, at the partition root:
   - `vmlinuz` (the live kernel),
   - `initrd.img` (the live initramfs),
   - `filesystem.squashfs` (the live root),
   - a `payload/` directory containing the installable target
     (`pip-rootfs.squashfs`, `.sha256`, `target-image-profile.json`),
   - `.disk/live-uuid` containing the exact `greia.live_media_id` value.
5. Install syslinux to the partition VBR:
   `syslinux --install --directory boot/syslinux /dev/sdX1`
   (VBR must contain `ldlinux.sys`; put the c32 modules beside it).
6. Write syslinux's MBR:
   `dd if=/usr/lib/syslinux/mbr/mbr.bin of=/dev/sdX bs=440 count=1`
7. `syslinux.cfg`:

   ```
   DEFAULT live
   PROMPT 0
   TIMEOUT 100
   LABEL live
       LINUX /vmlinuz
       INITRD /initrd.img
       APPEND boot=live components live-media-path=/ live-media-timeout=30 \
              nopersistence noeject overlay-size=128M \
              greia.live_media_id=<id> console=tty1
   ```

8. Verify the MBR signature (`55 aa`) and that `ldlinux.sys` exists on the
   partition.

Steps 2–6 are the antiX-style mechanics; step 4 (the `.disk` marker and the
`payload/` directory) is Greia-specific and is what turns a bootable stick
into a *working Greia installer*.

---

## 10. Rules this post-mortem establishes

1. **BIOS-first-stage bootloader compatibility is a firmware property, not a
   code property.** Test on the actual hardware class; QEMU is necessary but
   not sufficient.
2. **When GRUB's MBR will not execute on a given stick, switch to
   syslinux.** The syslinux MBR + VBR pair is the most conservative BIOS USB
   boot path and is what antiX uses for the same reason.
3. **A bootable medium is not an installer medium.** The live kernel/initrd/
   squashfs boot fine, but the installer additionally requires `.disk/live-uuid`
   and `payload/` to be present and identity-consistent.
4. **Prefer a plain active FAT32 partition + explicit syslinux config over
   hybrid ISO layouts on old BIOS firmware.**
5. **Keep bootloader output observable.** A first-stage loader that prints
   nothing is indistinguishable from one that never ran; choose bootloaders
   that print their progress (syslinux does). Owner decision 2026-10-18: the
   quiet release-candidate media clears only the stock SYSLINUX copyright
   banner (`clear.msg`) for child-facing presentation; the diagnostic/dev
   template and media keep this rule unchanged, `console=tty1` + `panic=0`
   still print fatal errors, and the `verbose` recovery label is the
   observable path on quiet media.
