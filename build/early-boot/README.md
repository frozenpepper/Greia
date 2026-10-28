# Greia early-boot framebuffer cover

This directory contains the Greia-owned renderer intended to replace Plymouth in the **normal target and installer boot path**.

The source is committed here before profile authority is switched so a Linux/local-hardware agent can integrate and prove it without leaving `main` in a knowingly half-built state.

**Acceptance status (2026-10-28):** `greia-early-framebuffer-v1` passed the
QEMU visual acceptance recorded in
`docs/release/2026-10-28_BOOT_COVER_ACCEPTANCE.md`: the installer and the
installed A/B target show the branded white frame/launcher handoff with no
Linux console text. The registered release-safe status applies to the
technical-preview composition; physical Acer visual acceptance remains an
ordinary-family gate. Re-run the acceptance after changing the renderer,
initramfs hooks, GRUB theme or boot arguments.

## Runtime contract

`greia-fb-splash` must remain deliberately boring:

- open the actual framebuffer (`/dev/fb0` by default);
- query `FBIOGET_FSCREENINFO` and `FBIOGET_VSCREENINFO`;
- support ordinary 16/24/32-bit true-colour fbdev layouts through the reported channel offsets/lengths;
- paint the visible area pure white;
- read a P6 PPM at `/etc/greia-boot/boot-logo.ppm`;
- preserve artwork aspect ratio and use the full physical display height whenever width permits;
- return immediately if no supported framebuffer is available;
- print nothing during normal boot;
- contain no sleeps/retry loops, networking, subprocesses, Python, SDL, image-decoder libraries or audio.

A framebuffer miss is **fail-soft**. It must never hold up the real boot just to obtain a splash.

## Build contract

The target-architecture binary must be produced **inside the target root/chroot**, never by assuming that the build host architecture equals the image architecture.

Preferred implementation for Debian-based Greia images:

1. install `libklibc-dev` only as a build dependency inside the chroot;
2. compile with target `klcc`, preferably static and stripped;
3. run a build-time smoke invocation/help/error-code check;
4. install the resulting binary under `/usr/lib/greia-boot/greia-fb-splash`;
5. include that exact binary and `/etc/greia-boot/boot-logo.ppm` in the generated initramfs;
6. remove the development package before the final image package manifest/footprint is recorded;
7. assert that no compiler/development package was accidentally retained merely for the boot cover.

If klibc cannot support a required syscall/header on a declared target architecture, stop and document the exact incompatibility before choosing another libc strategy. Do **not** silently copy a host binary or drag a full interpreter/graphics stack into initramfs.

## Invocation stages

Do not poll for `/dev/fb0` or sleep waiting for it. Install the same idempotent draw attempt at a few naturally later initramfs stages so whichever stage first sees the framebuffer paints it, for example:

- `init-top`;
- one pre-root-mount/local-premount stage supported by the current initramfs-tools version;
- `init-bottom` as a final pre-switch-root reinforcement.

Each attempt is:

```sh
[ -c /dev/fb0 ] || exit 0
/usr/lib/greia-boot/greia-fb-splash >/dev/null 2>&1 || true
```

The exact hooks/scripts and `PREREQ` ordering must be validated against the Debian `initramfs-tools` version used by the target profile.

## Artwork contract

The early renderer intentionally does **not** decode PNG. The local-agent integration must establish one canonical static boot artwork source and derive:

- a PNG suitable for the minimal GRUB graphical first frame;
- a P6 PPM for the initramfs renderer;
- launcher-owned PNG frames for the short animated continuation.

These derivatives must all be generated from the same approved artwork so GRUB → initramfs → launcher feels like one continuous image rather than three unrelated splash systems.

The product requirement is a **white frame with the Greia logo/artwork using effectively the full vertical display size** on the 1024×600 reference display, while preserving aspect ratio on other resolutions.

## What does not belong here

- Plymouth;
- long animations;
- a 7-second fixed-frame sequence;
- sound playback;
- profile UI;
- per-hardware framebuffer dimensions;
- Acer-specific pixel formats.

Animation and the optional boot chime start only after the launcher owns a real graphical surface.