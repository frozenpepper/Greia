# Greia Boot Progress Compatibility Contract

**Status:** compatibility/history contract; visible loading bar retired from the current boot presentation  
**Date:** 2026-08-24  
**Scope:** installed Greia OS and graphical installer boot handoff

## Current product decision

The current Greia boot presentation does **not** show a loading/progress bar.

The 2026-08-20 milestone-progress experiment remains useful history because it established several good lifecycle rules, but the visible bar itself was removed during the 2026-08-24 Acer recovery/presentation work. The current raw framebuffer renderer retains the `--progress 0..100` argument and callers still pass the historical milestone values for compatibility, but `draw_progress_bar()` is intentionally a no-op. The launcher handoff likewise does not draw a progress bar.

This compatibility plumbing must not be mistaken for visible product behavior.

A future decision to reintroduce child-visible progress would require a new explicit product/design change, source implementation, tests and physical visual acceptance. Agents must not resurrect the bar merely because milestone calls remain in source.

## Historical milestone map retained for compatibility

The following values still exist in callers and tests as stable handoff labels:

| Progress | Owner | Historical meaning |
|---:|---|---|
| 15% | initramfs `init-top` | framebuffer/early device setup stage |
| 30% | initramfs `local-premount` | root preparation pre-mount stage |
| 45% | initramfs `init-bottom` | root handoff/userspace boundary |
| 55% | `greia-first-boot` | installed userspace / persistent-state preparation |
| 65% | `greia-first-boot` | persistent one-time state initialized |
| 78% | launcher/installer VT preflight | VT/X preflight passed; graphical server startup begins |
| ~92% | first X/Pygame frame | graphical surface acquired / launcher handoff |

These are **compatibility labels**, not currently rendered percentages and not elapsed-time estimates.

Do not use them to fabricate movement, infer boot duration, or add a timer-driven loading UI.

## Volatile runtime-root invariant preserved from the progress investigation

`/run` is tmpfs and starts empty on every boot. Greia runtime directories must never be owned only by a one-time initializer or opportunistically created/chowned by whichever application service starts first.

The installed system uses:

```text
/etc/tmpfiles.d/greia-runtime.conf
```

as the recurring authority for:

```text
/run/greia-os
/run/greia-hardware
```

with their final owner/group/mode. Launcher and Parent services are ordered after `systemd-tmpfiles-setup.service`. The launcher preflight verifies required runtime state; it must not race other services by changing shared `/run` ownership.

This lifecycle lesson remains active even though the visible progress bar was retired.

## Rendering architecture

### Before X

`build/early-boot/greia-fb-splash.c` remains the single tiny raw-fb renderer. It still accepts:

```text
--progress 0..100
```

but the current implementation uses that argument only as a compatibility input. `draw_progress_bar()` intentionally performs no drawing.

The renderer remains:

- architecture/display-geometry independent;
- 16/24/32-bit fbdev aware;
- fail-soft when fbdev is unavailable;
- silent on the visible console;
- free of sleeps, polling, Python, SDL and subprocesses;
- responsible for the static Greia artwork/background, not a visible loading meter.

### During X handoff

The raw framebuffer should remain visually continuous until a real graphical surface is acquired. `-background none` remains a continuity hint, not proof.

The launcher redraws the Greia presentation when X/Pygame acquires the display and proceeds into the explicit launcher-owned sequence:

```text
5 seconds animation
2 seconds final-frame hold
profile picker
```

No progress percentage is drawn in this handoff.

## Slow/recovery behavior

Removing the loading bar does **not** permit invisible failure loops or stale Linux output to become the product experience.

If startup is slow or broken:

- development/test profiles preserve visible diagnostics (`console=tty1`, `panic=0`) while the recovery gate is open;
- developer SSH remains the independent userspace recovery channel;
- persistent journal evidence must be retained;
- launcher/service retry storms are defects to fix, not boot progress;
- normal/release presentation changes require their own physical acceptance and must not delete diagnostics merely to hide them.

The product goal is to remove the underlying stall/retry, not animate around it.

## Acer lesson

On the reference Acer, earlier boot work exposed two separate problems:

1. stale Linux/status output can look like a frozen product even when a later graphical stage may eventually recover;
2. a timed panic reboot can destroy the only useful evidence when the kernel/initramfs cannot mount root.

The accepted development response is not a loading bar. It is a recoverable diagnostic path: visible developer console when needed, `panic=0`, persistent logs, working `greia / greia` developer SSH when userspace is reachable, and artifact-level checks before reboot.

## Acceptance

For current no-bar boot presentation, physical/video acceptance should establish the relevant scope:

1. no loading/progress bar is visible unless explicitly reintroduced by a future product decision;
2. Greia artwork remains visually sane through the boot stages that own it;
3. successful launcher acquisition transitions into the intentional 5-second animation + 2-second final hold;
4. no accidental black/garbled interstitial is introduced by the changed path;
5. developer failures remain diagnosable rather than entering timed reboot loops;
6. normal boot time is measured separately from the intentional seven-second launcher presentation;
7. second and later boots recreate volatile runtime roots correctly and do not fail because one-time initialization was skipped at the unit level.

Source inspection alone is not a physical visual PASS.
