# Greia Phase-0 Input and Controller Acceptance

**Date:** 2026-08-15  
**Status:** ACTIVE testing protocol for ADR 0020 / Phase-0 input evidence  
**Scope:** source verification plus owner-controlled physical controller evidence; no GitHub-hosted execution

## Purpose

This protocol proves the parts of Greia's input architecture that source tests cannot establish: real controller discovery, analog behavior, device reconnect, child-facing mapping quality, and protected system-input ownership.

It does not replace R7 display/system-chrome evidence. Controller acceptance and trusted Home/Back acceptance must ultimately pass together on the selected production session/input backend.

## Hard rules

- Do not query, trigger or rerun GitHub Actions for this protocol.
- Run against an exact current Git checkout and record its SHA.
- Stop on the first unexplained failure; preserve stdout/stderr and observations.
- Do not weaken dead zones, mapping rules, sandbox/device isolation or system-input reservations merely to obtain PASS.
- Do not grant an Activity broad `/dev/input` access to make the test easier.
- A source-test PASS is not physical-controller evidence.

## Required equipment

Use at least one controller recognized by the target's supported SDL/Linux input stack. Before final Phase-0 certification, repeat representative checks with more than one controller family/layout when available so one vendor does not accidentally define the platform behavior.

For the Acer floor, perform the final resource/latency acceptance on the physical Acer reference once the selected production input backend exists.

## A. Focused source gate

From repository root:

```bash
SOURCE_SHA="$(git rev-parse HEAD)"
printf 'SOURCE_SHA=%s\n' "$SOURCE_SHA"

PYTHONPATH=src python3 -m unittest \
  tests.test_input_core \
  tests.test_pygame_input \
  tests.test_activity_input_contract \
  tests.test_hal_legacy_x \
  tests.test_system_chrome \
  -v

PYTHONPATH=src python3 tools/validate_activity.py activities/writing
PYTHONPATH=src python3 tools/validate_activity.py activities/painting

make verify
```

Stop on the first real failure. Do not claim later sections passed if this gate failed.

## B. Manifest/input-contract checks

Confirm from the exact checkout:

```text
Writing  → input.profile = text
Painting → input.profile = pointer
```

Confirm that a new test Activity with an unknown `input.profile` is rejected and that an old API 0.1 package without `[input]` remains temporarily compatible as `hybrid`.

Confirm that `controller` is in the runtime capability vocabulary but neither Writing nor Painting requires it merely to receive standard alternative-input behavior.

## C. Trusted Shell controller integration

This section becomes executable once the bounded `PygameControllerSet` / standard navigation mapper is composed into the real Shell loop.

Required behavior:

1. Boot/reach the Greia profile picker with keyboard/mouse still functional.
2. Connect the controller before Shell startup; confirm Greia detects it without a separate input-mode setting.
3. Navigate profile choices with D-pad.
4. Navigate profile choices with left stick.
5. Activate using the south face button.
6. In the Activity collection, navigate and activate with the same learned controls.
7. Confirm keyboard arrows + Space/Enter still work while the controller remains connected.
8. Confirm mouse/pointer operation still works while the controller remains connected.
9. Disconnect the controller; Shell must remain usable with keyboard/pointer.
10. Reconnect it; controller navigation must recover without restarting the OS.

Record any missed presses, duplicate presses, excessive repeat, noisy neutral-stick movement or confusing focus behavior.

## D. Directional/game reference Activity

Use a purpose-built simple reference Activity or an accepted first-party game once available.

Required mapping:

```text
keyboard arrows          movement
keyboard Space           primary action
controller D-pad         movement
controller left stick    movement
controller south face    primary action
```

Where secondary action is used, the east face button may provide the standard secondary semantic; do not require it for a simple one-action Activity.

Verify keyboard and controller can alternate naturally without an input-mode switch.

## E. Pointer-profile reference

Use Painting or another spatial pointer Activity once the production semantic-input bridge is composed.

Verify:

- real mouse/touchpad still controls the pointer normally;
- touch works normally where supported;
- controller left stick moves the Greia virtual pointer rather than changing the Activity into directional/game navigation;
- south face button performs the primary pointer press/click semantics;
- neutral stick does not drift visibly;
- small stick movements allow precise target acquisition;
- full stick allows reasonable traversal of a 1024×600 surface;
- pointer never leaves the Activity surface;
- switching back to mouse/touch requires no mode change.

The controller must not be globally emulated as a Linux mouse for this acceptance.

## F. Text-profile reference

Use Writing.

Verify that ordinary text editing retains normal keyboard semantics:

- Space inserts space;
- Enter/newline behaves as designed;
- arrow keys move the caret/navigation according to Writing's text behavior;
- controller support around the Activity does not steal or reinterpret those keyboard inputs through game mappings.

A controller is not required to provide general text entry.

## G. Reserved system input

Once the production trusted system-input backend is composed with ADR 0019:

1. Run an Activity that logs every Activity-facing semantic input event.
2. Press the controller Guide/system control on hardware that exposes it reliably.
3. Confirm Greia receives/handles the reserved system control as designed.
4. Confirm the Activity log contains no corresponding Guide/system input event.
5. Confirm pointer/touch in the protected Home region is likewise absent from Activity input.
6. Exercise Home against an Activity that cooperates with STOP.
7. Exercise Home against an intentionally unresponsive Activity and confirm bounded forced return.

No fallback controller button chord is accepted by this protocol until a dedicated child accidental-activation trial has selected one.

## H. Sandbox/raw-device negative evidence

For an ordinary installed Activity, prove that controller support did not introduce broad raw device authority.

At minimum verify the selected production sandbox/input design does not grant the Activity unrestricted `/dev/input` merely because a controller is connected.

A test Activity must be unable to bypass Greia semantic/system-input routing by opening arbitrary controller input devices directly.

Exact commands depend on the selected R7 backend and must be added to this protocol when that backend is selected.

## I. Resource and latency evidence

On the Acer floor once the production backend is available, record at minimum:

- additional resident memory/process/FD cost with no controller connected;
- additional cost with one controller connected;
- controller discovery/reconnect latency;
- button-to-visible-response latency by practical measurement;
- neutral-stick drift behavior;
- CPU behavior while controller is idle;
- whether controller handling changes Shell idle-render behavior.

Do not claim a numeric acceptance threshold before measurement/product testing defines one. Preserve the measurements for the R7/R14 decision.

## PASS scope

A complete PASS of this protocol means the tested checkout/backend/controller combination satisfies the Phase-0 input/controller requirements covered here.

It does **not** by itself prove:

- every controller model is supported;
- Pi input support;
- Web runtime support;
- final R7 display architecture;
- final Phase-0 release certification.

Those remain scoped to their corresponding R7/R8/R9/R14 evidence.
