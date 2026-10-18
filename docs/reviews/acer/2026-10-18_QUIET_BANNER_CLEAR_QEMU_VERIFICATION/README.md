# Quiet RC: stock Syslinux banner cleared (QEMU visual review)

**Date:** 2026-10-18
**Evidence class:** SIMULATOR VISUAL REVIEW (QEMU) + build/media read-back gates.
No physical Acer re-acceptance yet.

## Context

Owner report after the first fixed RC test: the stock
`SYSLINUX 6.04 EDD … Copyright (C) 1994-2015 H. Peter Anvin et al` line stayed
on screen for the whole quiet kernel/initramfs phase (and again after a reboot
into the stick), making the boot look like it belonged to Syslinux rather than
Greia. Owner decision 2026-10-18: cut the banner on the quiet release-candidate
path. The 2026-08-20 review had rolled back a form-feed `DISPLAY` clear file
together with the fatal `console=null` argument; the two are now separated.

## Change under test

- `build/live-syslinux/clear.msg`: one `0x0c` form-feed byte.
- Quiet template only: `DISPLAY /boot/syslinux/clear.msg`.
- `tools/build-live-usb.sh` copies the byte to quiet media when the selected
  template references it; `tools/verify-live-usb.sh` requires the directive and
  byte-compares the file on read-back.
- Unchanged: `console=tty1`, `panic=0`, hidden `verbose` recovery label,
  diagnostic/dev template and media (verifier refuses any `DISPLAY` there).

## Build and media gates (all executed)

- Source: `529accef` (clean tree).
- Built through `tools/build-and-flash-development-usb.sh` inside
  `unshare --mount --propagation private` (desktop-host rule) with the operator
  public key; written to `/dev/sdc` (LaCie iamaKey `eca3505216d7d3`).
- `Developer installer artifact verification: PASS`
- `Greia live USB read-only verification: PASS`
  (`usb_readback_verification=PASS`, `loop_hygiene_verification=PASS`).
- Image SHA-256 `b92cfd58f2967fa581d88a5c675f6926bbf979869318bb302570b5a416aff2f2`;
  live media id `d60ca3a7-372a-4b48-92fb-55c75077daa9`; target payload
  1,203 MiB (<1,300 gate).
- On-media read-back: `boot/syslinux/clear.msg` is exactly one `0x0c` byte and
  `syslinux.cfg` contains `DISPLAY /boot/syslinux/clear.msg`.

## QEMU boot of the flashed media

`qemu-system-i386 -machine pc,accel=kvm:tcg -cpu n270 -m 768 -smp 1`,
`-drive file=/dev/sdc,format=raw,snapshot=on,if=ide` (snapshot: the stick is
never written), monitor screendumps at the times below.

Observed:

- `01-no-syslinux-banner-at-800ms.png` — screen already black at 0.8 s; the
  cleared screen contains no Syslinux/H. Peter Anvin text.
- `02-no-syslinux-banner-at-1500ms.png` — still black through the quiet kernel.
- `03-installer-language-screen.png` — the Greia installer language screen at
  190 s with `greia-installer.service` active and Xorg `:0` on `vt1`; no shell
  text anywhere.

Frames between 3 s and 150 s are black (quiet kernel/initramfs) until the
Greia framebuffer/session artwork paints; the short `Loading /vmlinuz…` lines
appear only for the kernel-load window and were not observable in the frames.

## Open item

Physical Acer re-acceptance of both the quiet presentation and the hidden
`verbose` recovery path (premortem F2). QEMU input emulation could not confirm
the Shift/Alt prompt reliably, so the recovery procedure is unchanged and
still needs the physical check.
