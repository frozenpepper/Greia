# R7 Disposable QEMU KMSDRM Acceptance

**Date:** 2026-08-09  
**Status:** test harness implemented; active VM result not yet accepted  
**Production session policy:** unchanged — Xorg remains the normal Greia launcher path

## Purpose

This test provides an intermediate R7 proof between static/image inspection and physical Acer/Raspberry Pi validation. It answers one narrow question:

> Can the exact Greia amd64 image, with its installed SDL/Pygame stack, become DRM master through SDL `kmsdrm`, create a real display surface, render and flip deterministic frames, and persist evidence when the only graphical device is a QEMU virtio GPU?

A PASS is useful evidence for the direct-graphics architecture. It is **not** physical-hardware acceptance and does not authorize switching normal Greia boot away from Xorg.

## Authority and prerequisites

The production image currently installs Debian Trixie `libsdl2-2.0-0` from source package `libsdl2 2.32.4+dfsg-1`.

Debian's exact source package declares Linux build dependencies on `libdrm-dev` and `libgbm-dev` and its `debian/rules` explicitly uses both:

- `--disable-kmsdrm-shared`
- `--enable-video-kmsdrm`

This is strong package-build evidence that KMSDRM is compiled into Debian's SDL rather than an optional shared backend. It does **not** replace Greia's exact finished-image `SDL_GetNumVideoDrivers()` probe; that installed-image probe remains the first runtime gate.

Authoritative Debian sources:

- https://packages.debian.org/source/stable/libsdl2
- https://sources.debian.org/src/libsdl2/2.32.4%2Bdfsg-1/debian/rules

QEMU's current documentation states that `virtio-gpu` provides a paravirtualized GPU/display controller and requires `CONFIG_DRM_VIRTIO_GPU` in the Linux guest. QEMU also documents `-display none` as suppressing host video output while the guest still sees the emulated graphics card. The test therefore uses a virtio VGA device with no host display window.

Authoritative QEMU sources:

- https://www.qemu.org/docs/master/system/devices/virtio/virtio-gpu.html
- https://www.qemu.org/docs/master/system/qemu-manpage.html

SDL documents that KMSDRM requires DRM master by default to change display state and draw. The active Greia acceptance intentionally leaves that default in force.

Authoritative SDL sources:

- https://wiki.libsdl.org/SDL2/SDL_HINT_KMSDRM_REQUIRE_DRM_MASTER
- https://wiki.libsdl.org/SDL2/FAQUsingSDL

## Safety boundary

`tools/r7_qemu_kmsdrm_acceptance.py` never boots or mounts the source image for mutation. It:

1. hashes the source image;
2. creates a sparse/reflink-capable clone;
3. mounts **only the clone**;
4. verifies that the R7 passive probe and active acceptance service exist;
5. writes a test-only boot runner and systemd unit into the clone;
6. masks `greia-launcher.service` only in the clone;
7. enables the test-only unit only in the clone;
8. unmounts and detaches through Greia's fail-closed loop cleanup helper;
9. boots the clone with QEMU;
10. remounts the clone read-only to validate persisted evidence.

The production build overlay is not modified with the QEMU boot unit or boot runner.

## Guest sequence

The disposable guest test is ordered after `greia-first-boot.service` so it observes an initialized Greia runtime.

The test-only boot runner then:

1. activates `tty1` and verifies it is active;
2. refuses to continue if `Xorg`, `X`, or `xinit` is alive;
3. executes `greia_platform.direct_graphics_probe` without initializing a display;
4. requires the installed SDL to enumerate `kmsdrm`;
5. requires a visible DRM card node and the passive KMSDRM prerequisite assessment to pass;
6. starts the existing `greia-kmsdrm-acceptance.service` directly;
7. requires the service to report actual SDL driver `kmsdrm`;
8. requires rendered frame evidence;
9. writes a bounded summary and powers the guest off on every exit path.

The normal maintenance controller is deliberately not used in this VM mode. Its contract is to stop an already-running X launcher, perform the test, and restore the launcher. The disposable VM instead proves the cleaner condition where X never owns the graphical session.

## QEMU topology

The host harness uses, among other arguments:

```text
-machine pc,accel=tcg
-vga none
-device virtio-vga
-display none
-monitor none
-nic none
-no-reboot
-drive file=<disposable-copy>,format=raw,if=ide,index=0,media=disk,cache=writeback
```

This is intentionally TCG-capable and does not require host KVM or host GPU passthrough. Network is disabled. Disk writes are intentionally persistent because the result must be recovered from the guest filesystem after shutdown.

## Manual invocation

Inspect the non-mutating plan first:

```bash
python3 tools/r7_qemu_kmsdrm_acceptance.py \
  --image /path/to/greia-os-modern-amd64.img \
  --output-dir /tmp/greia-r7-qemu \
  --plan-only
```

Run the active test from a Linux host with QEMU and the Greia build cleanup dependencies installed:

```bash
sudo python3 tools/r7_qemu_kmsdrm_acceptance.py \
  --image /path/to/greia-os-modern-amd64.img \
  --output-dir /tmp/greia-r7-qemu
```

Use `--keep-test-image` only when failure forensics require retaining the large disposable clone.

## PASS contract

The host report must have:

```text
classification = ACTIVE_QEMU_KMSDRM_PASS
ok = true
```

The persisted guest evidence must independently show:

- summary schema `1`, phase `complete`, active VT `tty1`;
- launcher masked in the disposable clone;
- passive probe schema `1` and `kmsdrm_compiled = true`;
- at least one DRM card node;
- `kmsdrm_prerequisites_visible = true`;
- active result schema `1` and `ok = true`;
- requested and actual video driver both exactly `kmsdrm`;
- positive surface width and height;
- at least three rendered frames with valid SHA-256 evidence.

Any missing or malformed item is a failure.

## Failure interpretation

A missing/negative passive KMSDRM result means do not attempt to interpret the failure as a session problem; resolve installed SDL/package closure first.

A passive result with no DRM card indicates the QEMU/kernel device topology is insufficient and is not evidence against Greia's physical KMS path.

A passive PASS followed by active SDL failure is the useful R7 VM result: investigate DRM-master acquisition, connector/mode availability, PAM/VT ownership, GBM/EGL, and the virtual GPU path without changing production boot.

A QEMU PASS still leaves physical acceptance mandatory, especially for legacy Intel/Acer behavior, Raspberry Pi DRM/KMS, real connectors/modes, input ownership, suspend/resume, crash recovery, and the no-shell/no-desktop appliance contract.
