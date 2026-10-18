# RC installer quiet-boot verification (QEMU visual review)

**Date:** 2026-10-18
**Evidence class:** SIMULATOR VISUAL REVIEW (QEMU), SOURCE build/read-back gates.
No physical Acer install was performed in this review.

## What was verified

The 2026-10-17 RC stick froze on the Syslinux banner because the live entry
carried `console=null`; on the Debian 686 kernel (`CONFIG_NULL_TTY` unset) that
leaves PID 1 with no console, live-boot's `init` dies and `panic=0` halts with
the last framebuffer content. This review verifies the fixed quiet path end to
end on freshly built media.

- Source: `ee7a40d1b29f51f44d9aead53cd08a7e65c7da0b` (clean tree).
- Profile: `legacy-x86-i686-rc` (`boot.console_policy = "quiet"`).
- Built image: `out/greia-os-installer-legacy-x86-i686-rc.img`,
  SHA-256 `07240e27416b9801d8b981e43c383d79425697e545402e61d6964a18127b12ac`.
- Live media id: `22857a5a-9fdb-4d9c-923d-ab659eed38ff`.
- Target payload accounted: 1,203 MiB (below the 1,300 MiB owner gate).
- USB: LaCie iamaKey `/dev/sdc` (serial `eca3505216d7d3`), flashed with
  `tools/build-live-usb.sh` and read-back verified with `tools/verify-live-usb.sh`.

Commands ran inside a private mount namespace as prescribed by
`docs/agents/GREIA_AGENT_OPERATIONS.md` ("build in a private mount namespace on
desktop hosts"):

```
sudo -n unshare --mount --propagation private -- \
  bash tools/build-development-installer.sh legacy-x86-i686-rc ./out \
  --operator-key <operator.pub>
sudo -n unshare --mount --propagation private -- \
  bash tools/build-live-usb.sh out/greia-os-installer-legacy-x86-i686-rc.img /dev/sdc
sudo -n unshare --mount --propagation private -- \
  bash tools/verify-live-usb.sh out/greia-os-installer-legacy-x86-i686-rc.img /dev/sdc
```

Both gates passed: `Developer installer artifact verification: PASS` and
`Greia live USB read-only verification: PASS` (`usb_readback_verification=PASS`,
`live_console_policy=quiet`).

## QEMU boot of the flashed media

```
qemu-system-i386 -machine pc,accel=kvm:tcg -cpu n270 -m 768 -smp 1 \
  -drive file=/dev/sdc,format=raw,snapshot=on,if=ide \
  -device e1000,netdev=net0 -netdev user,id=net0,hostfwd=tcp::2222-:22 \
  -display none -monitor unix:<sock>,server=on,wait=off -no-reboot -boot c
```

Snapshots mean the physical stick was never written by QEMU; the read-only USB
verifier passed again after the run.

Observed sequence:

1. `01-quiet-boot-splash.png` — Syslinux banner passes in two lines, then the
   Greia framebuffer boot artwork owns the screen. No kernel, systemd, login or
   cursor text is visible.
2. `02-installer-language-screen.png` — the Greia installer UI takes over:
   language screen (English/Italiano/Español/Français). `greia-installer.service`
   is `active`, Xorg `:0` runs on `vt1`, no shell is visible.

## Negative control (recorded so it is not repeated)

An earlier run of the same media used `-cpu pentium3`, which has no SSE2.
Debian's i386 NumPy refuses to import and the installer client crashes; the
service restart budget (5 starts/300 s) then trips `start-limit-hit`, and the
`installer-exit-cover` helper repaints the Greia cover, so the screen looks
like a stalled splash rather than a crash. The project's own
`build/verify-image-qemu.sh` selects `n270` for i386 for exactly this reason;
do not derive image defects from a pre-SSE2 CPU model. The reference Acer Atom
N270 has SSE2.

## Open items

- **Physical Acer acceptance not yet run** (this review is QEMU-only): install
  through the graphical installer, first-boot checklist
  `docs/reviews/2026-10-17_RC_IMAGE_PREMORTEM.md` §5, and the hidden verbose
  recovery path (hold Shift/Alt → `verbose`) once.
- The live installer root has SSH but no `greia-devctl` or its sudoers entry,
  while `docs/INSTALLER_IMAGE_CREATION_AND_BOOT.md` §13.5 lists
  `sudo -n /usr/local/sbin/greia-devctl status` as a live-installer remote
  check. Source/docs mismatch; the installed target does ship it.
- The build host has one kernel-pinned loop device (`/dev/loop37`, EBUSY after
  a non-namespaced build leaked its chroot mount into service namespaces); it
  clears on reboot and did not affect the namespaced build.
