# greia-early-framebuffer-v1 — QEMU visual acceptance

Date: 2026-10-28 · Evidence class: **SOURCE + SIMULATOR VISUAL REVIEW (QEMU)**,
not physical-hardware acceptance.

## Decision

`greia-early-framebuffer-v1` is registered as **release-safe for the
technical-preview composition** after the executed visual acceptance below.
The ordinary-family release still requires the physical Acer review; QEMU
evidence is not a hardware certification.

## Artifacts under test

| Artifact | Identity |
|---|---|
| Runtime/payload source | `8bac176bd3d3b562fcf6785cdf663aecf0dcceec` |
| Installer composition source | `fc2af2103` (adds live-root branding copy) |
| Release bundle | `2572bf0829152c24aaf0e82f897b9ba651f871f30c4c9ad5d4f9349729dab3d0` |
| Bundle bytes | 714,551,308 |
| Installer image | `b81279afe4c8d72bb458670efda95c6a422deddbceef69051a5e6da309c2bd80` |
| Installer bytes | 2,270,167,040 |
| Profile | `acer-aspire-one-i386-ab` |
| QEMU | 8.2.2, KVM, i386, 1024 MiB, one vCPU, `pc`/`n270` |

## What was executed

1. The installer image was booted under QEMU with snapshot-backed media.
   Screendumps were captured before and during the installer start.
2. A disposable 7 GiB A/B target was installed through the shipped graphical
   installer transaction socket using the existing product harness
   (`install-prepare` then `install-execute`). The host-side observation
   closed on default slot **A**, valid MBR PARTUUIDs, layout record and
   PERSIST schema 1.
3. The exact installed target was booted again with snapshot-backed media and
   screenshots captured through first-boot setup.

Evidence root:
`/var/tmp/greia-boot-cover-acceptance-final/`
(`install-report.json` and `product/*serial.log`).
Curated screenshots are committed under
[`docs/reviews/acer/2026-10-28_BOOT_COVER_QEMU/`](../reviews/acer/2026-10-28_BOOT_COVER_QEMU/README.md);
raw screendumps remain in `/tmp/greia-release-prep/boot-cover/final-installer/`
and `/tmp/greia-release-prep/boot-cover/installed-final2/`.

## Observed presentation

- **Installer:** firmware text is visible before GRUB/kernel handoff (legacy
  BIOS behavior). From the first Linux-owned frame onward the screen is the
  canonical white Greia frame with the logo; no kernel, systemd, login or
  shell text is drawn on the product surface. The graphical installer then
  owns the screen.
- **Installed A/B target:** after GRUB, the early framebuffer cover paints the
  white Greia frame (captured at 18 s and 25 s). The launcher intro continues
  the same artwork, then the first-child setup appears. No Linux console text
  was visible on the installed product surface.
- The A/B boot-control menu now carries the same GRUB theme and logo; the
  installer copies `greia-theme.txt` and `greia-boot-logo.png` from the live
  root onto the boot-control volume.
- The initramfs now includes optional `bochs`, `cirrus_qemu` and `virtio_gpu`
  framebuffer modules for QEMU/generic displays, in addition to the reference
  `i915` path.

## Defects fixed by this acceptance

1. A/B `grub.cfg` had no graphical theme (raw GRUB text was the first frame).
2. The initramfs had no generic QEMU framebuffer driver, so `/dev/fb0` was
   absent and the cover stayed fail-soft.
3. Kernel arguments were alphabetically sorted, putting `loglevel=0` before
   `quiet`; the later `quiet` re-enabled console logging. `quiet` is now
   emitted first.
4. The live-installer root did not receive the canonical theme/logo, so the
   A/B installer refused the boot-control branding copy. The live consumer
   now installs both assets.

## Remaining release boundary

- Physical Acer Aspire One flash/install/boot visual review is **not run**.
  It remains required before an ordinary-family release, together with the
  full physical update/rollback matrix.
- Firmware (SeaBIOS) text before the Greia-owned graphical path is not a
  Greia backend failure; the acceptance applies to the noninteractive
  Greia-owned cover and transition.
- Any change to the GRUB theme, cover renderer, initramfs hooks or boot
  arguments must re-run this visual acceptance before the registration is
  relied on again.
