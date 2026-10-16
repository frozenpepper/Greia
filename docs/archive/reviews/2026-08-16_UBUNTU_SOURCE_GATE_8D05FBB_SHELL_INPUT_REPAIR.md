# Greia — Ubuntu Source Gate `8d05fbb` Shell-Input Failure and Repair

**Date:** 2026-08-16  
**Host:** owner-controlled Intel Mac mini / Ubuntu 24.04.4 LTS / x86_64  
**Failed tested commit:** `8d05fbb6f36c3623d6df794f6cfc2beabef2f47e`  
**Target installer profile:** `legacy-x86-i686`  
**Result:** aggregate source gate FAIL; image build NOT RUN; SD write NOT RUN

## Preserved execution result

The local operator followed the fail-closed runbook and ran:

```bash
bash tools/run_hardware_enablement_source_gate.sh
```

Results:

```text
focused hardware-enablement suite 1: 77 tests PASS
focused hardware-enablement suite 2: 32 tests PASS
full source suite / make verify: 530 tests
full-suite result: failures=1, errors=2
aggregate gate exit: 2
image build: NOT RUN
SD write: NOT RUN
```

The operator correctly stopped before building physical media.

## Remaining failures

All three remaining problems were confined to `tests/test_shell_input.py` / `ShellInputController`.

### 1. D-pad compatibility test bypassed Greia's compatibility layer

Ubuntu's packaged Pygame 2.5.2 exposes `pygame._sdl2.controller` but does not re-export all SDL2 `CONTROLLER_BUTTON_*` integer constants.

The previous repair correctly changed `greia_platform.pygame_input` to own stable compatibility constants, but `tests/test_shell_input.py` still constructed events with:

```python
sdl_controller.CONTROLLER_BUTTON_DPAD_RIGHT
sdl_controller.CONTROLLER_BUTTON_GUIDE
```

This recreated the distro-specific dependency in the test itself and caused two `AttributeError` errors before the Greia translator was exercised.

**Repair:** Shell input tests now construct controller events with Greia's compatibility constants from `greia_platform.pygame_input` while still skipping only when the SDL2 controller module itself is unavailable.

This keeps consumer-brand/native backend naming inside the backend adapter and tests the actual portability contract.

## 2. Exact analog-repeat boundary had a real floating-point bug

The remaining test expected an analog navigation repeat at the exact configured boundary:

```text
initial: 1.00
repeat delay: 0.30 -> repeat at 1.30
repeat interval: 0.10 -> repeat at 1.40
```

The runtime previously computed:

```python
_next_repeat_at = now + interval
```

After the 1.30 repeat, binary floating-point represented the next deadline as:

```text
1.4000000000000001
```

while the polling timestamp was the representable literal `1.4`. The strict comparison therefore treated the exact configured deadline as early and delayed navigation by one Shell polling cycle.

This is a genuine implementation defect rather than a stale test.

**Repair:** `ShellInputController.poll_analog()` compares the current timestamp against the immediately preceding representable value of the stored deadline using `math.nextafter(deadline, -inf)`. This tolerates exactly the one-ULP representation artifact without introducing a coarse arbitrary timing epsilon and without allowing materially early repeats.

The existing `1.35` negative assertion still protects the bounded-repeat interval.

## Repair commits

```text
29380333dd521c234b9c41ec30df471020076cf0
  fix: honor analog repeat deadlines at float boundaries

bf13b419ed20e20634499cc03b9ef381a3b1b464
  tests: use Greia controller compatibility constants
```

## Evidence boundary

These repairs are source-reviewed but are **UNPROVEN** until the same owner-controlled Ubuntu host pulls exact current `origin/main` and reruns:

```bash
bash tools/run_hardware_enablement_source_gate.sh
```

Do not build or write the SD before that aggregate gate exits zero.

If the rerun passes, proceed through the canonical native build:

```bash
sudo bash build/build-legacy-x86-sd-installer.sh out
```

then image SHA verification, positive SD identity checks, raw write, and physical read-back SHA verification.

If the rerun fails, preserve the first new failure and stop again. Do not edit tests or host dependencies merely to obtain PASS.
