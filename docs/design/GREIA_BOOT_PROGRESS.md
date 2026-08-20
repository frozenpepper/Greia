# Greia Boot Progress Contract

**Status:** active implementation contract; physical acceptance still required  
**Date:** 2026-08-20  
**Scope:** installed Greia OS and graphical installer boot handoff

## Product requirement

A child or parent must never have to infer whether Greia is still booting from a frozen Linux console line. On slow hardware the branded boot frame must remain visible and communicate that boot is advancing.

This requirement does **not** make long boot times acceptable. A retry storm or multi-minute launcher startup is a defect even if the progress UI remains responsive.

## Truthful progress only

Greia boot progress is milestone-based, never timer-based.

Forbidden:

- increasing the bar because N seconds elapsed;
- increasing the bar because a service crashed and restarted;
- looping a percentage from 0 to 100 while waiting for an unknown dependency;
- claiming 100% before a real graphical Greia surface is ready.

A retry must repaint the same milestone. If Greia remains on one milestone for a long time, the visual may indicate activity, but the percentage must not advance without a real state transition.

## Initial milestone map

The first implementation intentionally uses a small number of stable ownership boundaries:

| Progress | Owner | Meaning |
|---:|---|---|
| 15% | initramfs `init-top` | Greia acquired a usable framebuffer and early device setup has begun. |
| 30% | initramfs `local-premount` | device discovery/root preparation has advanced to pre-mount. |
| 45% | initramfs `init-bottom` | root handoff is ready; Greia is about to enter userspace. |
| 55% | `greia-first-boot` | installed userspace is alive and one-time persistent Greia state is being prepared. |
| 65% | `greia-first-boot` | one-time persistent state initialization completed. |
| 78% | launcher/installer VT preflight | VT/X preflight passed and the graphical server is being started. Every restart remains 78%. |
| ~92% | first X/Pygame frame | a real graphical surface exists; launcher-owned presentation continues the same boot visual. |
| 100% | launcher/installer UI | represented by replacement of the boot cover with the interactive Greia surface, not by an artificial final delay. |

The live installer omits the installed-system first-boot milestones; it moves from the initramfs milestones to graphical preflight.

Percentages are product presentation values attached to real milestones. They are not estimates of elapsed wall-clock time.

## Volatile runtime-root invariant

`/run` is tmpfs and starts empty on every boot. Therefore Greia runtime directories must never be owned by the one-time first-boot initializer or created/chowned opportunistically by whichever application service happens to start first.

The installed system uses:

```text
/etc/tmpfiles.d/greia-runtime.conf
```

as the recurring authority for:

```text
/run/greia-os
/run/greia-hardware
```

with their final owner/group/mode. Launcher and Parent services are ordered after `systemd-tmpfiles-setup.service`. The launcher preflight verifies the directories exist; it does not race other services by changing shared runtime ownership.

This rule was added after the Acer boot investigation exposed that `/run/greia-hardware` had been created inside a one-time initializer even though the directory disappears on every reboot. Even where that was not proven to be the exact cause of the observed 18 launcher restarts, the lifecycle was structurally invalid and could produce later-boot failures.

## Rendering architecture

### Before X

`build/early-boot/greia-fb-splash.c` remains the single tiny raw-fb renderer. It accepts:

```text
--progress 0..100
```

and draws the canonical full-colour boot canvas plus a simple high-contrast bar.

The renderer remains:

- architecture/display-geometry independent;
- 16/24/32-bit fbdev aware;
- fail-soft when fbdev is unavailable;
- silent on the visible console;
- free of sleeps, polling, Python, SDL and subprocesses.

### During X handoff

The raw framebuffer must remain at the last truthful milestone until a real graphical surface is acquired. `-background none` remains a continuity hint, not proof.

The launcher-side boot presentation redraws the same canonical canvas at the start of its bounded intro path, carries the near-complete 92% progress state, then transitions into the launcher/profile UI.

### After X is available

Richer localized status text may be added only in the launcher/installer presentation layer, where the real Greia typography/localization stack exists. Early boot must not add a separate multilingual font/runtime dependency merely to render prose.

## Slow/recovery behavior

If launcher startup takes a long time:

- the 78% frame stays visible instead of revealing stale VT text;
- service restarts do not move the bar;
- diagnostics remain in journal/developer SSH;
- a future richer graphical recovery state may expose a child-safe activity indicator without displaying Linux errors.

The product goal remains to remove the underlying retry/race. The progress UI is a UX safety net, not permission for a slow boot.

## Acer lesson

On the reference Acer a boot reached the final normal VT1 systemd line and then appeared frozen for roughly 4.5 minutes while `greia-launcher.service` repeatedly restarted. The launcher eventually acquired X and displayed Greia without an on-device edit.

That incident establishes two independent acceptance requirements:

1. no successful boot may leave a static Linux status line as the only visible indication of life;
2. launcher startup must be instrumented and fixed so repeated restarts are not treated as normal boot work.

The current service ordering already places `greia-first-boot.service` before the launcher. Therefore the precise cause of that 18-restart incident must come from captured launcher/X logs; it must not be permanently documented as a first-boot race without evidence.

## Acceptance

A boot-progress implementation is not accepted from source inspection alone. Physical/video acceptance must demonstrate:

1. progress is visible on the reference Acer before X starts;
2. the bar advances at real milestone boundaries;
3. repeated launcher restarts leave the same percentage visible;
4. no stale systemd/UTMP line becomes the apparent boot screen after Greia owns the framebuffer;
5. no black/white interstitial is introduced at the X handoff;
6. successful launcher acquisition replaces the progress frame with the interactive UI;
7. normal boot time is measured separately and retry storms are treated as failures, not as acceptable slow-path behavior;
8. a second boot after installation recreates `/run/greia-os` and `/run/greia-hardware` with the expected ownership before launcher/Parent startup.
