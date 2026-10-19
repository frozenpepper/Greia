# Quiet installer shutdown behind the Greia cover (QEMU visual review)

**Date:** 2026-10-18
**Evidence class:** SIMULATOR VISUAL REVIEW (QEMU) + build/media read-back
gates. Physical retest pending.

## Context

Owner report after the completion button was repaired: shutdown worked, but a
terminal transcript appeared, then the Greia splash, then more systemd text was
drawn over the splash with a glitchy look. Two separate sources:

1. the temporary diagnostic visibility raise in the root finish helper
   (`SetShowStatus yes` + kernel loglevel 8), removed after power-off was
   proven;
2. `systemd-shutdown` itself, which inherits PID1's log level and prints
   live-medium/loop teardown warnings at the very end
   (`Failed to unmount /run/live/medium`, `Could not detach loopback
   /dev/loop0`, `Failed to finalize file systems, loop devices, ignoring.`).

`becomes_shutdown()` in systemd passes `--log-level <PID1 max level>` to
`systemd-shutdown`, and the Manager `LogLevel` property is writable at runtime.
The root finish helper therefore sets `LogLevel=emerg` immediately before
`systemctl poweroff`. This is runtime-only: normal boot logging and the journal
are unaffected, kernel emergencies still print, and no new package/daemon is
added.

## Evidence

- `02-before-diagnostic-text-over-splash.png`: the successful-but-ugly
  shutdown with the diagnostic raise active; systemd/kernel text is drawn over
  the Greia splash.
- `01-final-frame-clean-greia-splash.png`: final captured frame of the fixed
  media's shutdown (marker created as the installer's own unprivileged
  `nobody` identity). The Greia splash is the last visible frame; no terminal
  text; the VM then powered off (QEMU exited).

Build under test: `6f3c809c`, image SHA-256
`47ab4ec639175f8b21aa69aec0f3aa1d172eab7d8a4ce24fdc775f92031fb6a0`, live media
`a1d8e713-5090-4570-be68-83db7cfda8c6`, payload 1,203 MiB. Artifact
verification PASS, USB read-back PASS, loop hygiene PASS.

The capture used the real flashed stick with QEMU `snapshot=on` (the stick is
never written), `-cpu n270`, 768 MiB, one vCPU, and screendumps every ~0.12 s
through shutdown.

## Notes

- The physical power button bypasses the finish helper and therefore keeps
  stock shutdown logging; the completion screen's button is the intended,
  silent path.
- A short black gap (on the order of one second) remains between Xorg releasing
  VT1 and the framebuffer cover repaint; it contains no text.
