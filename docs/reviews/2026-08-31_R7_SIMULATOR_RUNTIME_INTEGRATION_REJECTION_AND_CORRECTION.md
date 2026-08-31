# Greia — R7 Simulator Runtime-Integration Rejection and Correction

**Date:** 2026-08-31  
**Repository/branch:** `frozenpepper/Greia` / `main`  
**Rejected tested SHA:** `3944ba74b5d5057b46247526633b06ec0f3dd4ce`  
**Disposition:** **SOURCE + SIMULATOR CORRECTIONS IMPLEMENTED / EXACT-CURRENT EXECUTION REQUIRED**

---

## 1. Executive result

The third current-head R7 acceptance run materially advanced the evidence boundary:

```text
focused source gate: PASS
backend-independence audit: blockers=0
system-chrome ownership audit: blockers=0
make verify: 1507 tests PASS
project validation: PASS
Activity validation: PASS
shell/source gate: PASS
Earth page hot-path violation: absent
Magnet page direct-font violation: absent
```

The run then found two independent Simulator/runtime defects:

1. **Encyclopedia could no longer launch through Greia's real script-mode Activity path.**
2. **The Simulator's protected Home input could be starved by a hostile Activity that never called `pygame.event.get()`.**

Both are real architecture/runtime issues. Neither is fixed by weakening tests, extending timeouts, or reverting the Encyclopedia quality split wholesale.

The reference Acer was reachable and exact source was deployed. Shell boot/focus/pointer checks passed, with no child-visible Linux and no Activity DRM/raw-input requirement. Full R7.2/R7.3 physical acceptance remains incomplete because the Simulator/runtime failures were not yet corrected on the tested SHA and the remaining physical lanes were not completed.

---

## 2. Exact rejected evidence at `3944ba74`

The local agent froze:

```text
3944ba74b5d5057b46247526633b06ec0f3dd4ce
```

with `origin/main` equal at the start and before the Acer lane, no main advancement, and a clean worktree before/after the source gate.

### Source

```text
focused discovery gate: PASS (17 patterns / 136 tests)
backend audit: PASS, blockers=0
chrome audit: PASS, blockers=0
make verify: PASS, 1507 tests
project validation: PASS
Activity validation: PASS
shell/source gate: PASS
```

This closes the two earlier masked hot-path corrections as source-green on this exact SHA:

```text
planet_earth page image decode/scale violation: NO
magnet page direct font constructor: NO
```

### Simulator

```text
Writing: PASS
Painting: PASS
Volo Draghetto: PASS
Encyclopedia: FAIL — never produced Activity frame / READY
hostile non-cooperative fixture: FAIL — Activity frame appeared, protected Home did not return
```

No libpng/bad-adaptive-filter warning appeared.

### Acer partial evidence

```text
Acer reachable: YES
exact tested source deployed: YES
Shell boot/focus: PASS
pointer/touchpad: PASS
child-visible Linux: NO
Activity direct DRM required: NO
Activity raw input required: NO
material performance regression observed: NO
logs reviewed: YES
```

Writing/Painting/hostile/crash/20-cycle physical lanes remain incomplete.

The operator also had to locally extend `tools/deploy_to_acer.py` extraction timeout from 60 to 180 seconds because the reference Atom N270 exceeded the old 60-second bound while extracting/chowning the current ~110 MB developer bundle. That local evidence-time mutation is now corrected in canonical source; future runs must not patch the helper after freezing the candidate SHA.

---

## 3. Encyclopedia runtime failure — bisect and root cause

The operator established a strong runtime bisect:

```text
faa46ec4369adaddf2e720d7bedf54319b3f857f  PASS
51db988a5a79181a26c8e694a59ec44fd424c313  PASS
ad9472696b9aa119646674e0b79389b08745d36f  FIRST BAD
```

First bad commit:

```text
ad9472696b9aa119646674e0b79389b08745d36f
Encyclopedia: split interactive presentation architecture (focus/controls/toy/planet, bounded cache)
```

The split itself is architecturally useful and is **not reverted**.

### 3.1 Greia's actual Activity execution mode

The trusted Simulator Python runtime ultimately executes the validated Activity entrypoint with:

```python
runpy.run_path(str(path), run_name="__main__")
```

The Activity package root is added to `sys.path`. Therefore an Activity entrypoint must support **script mode**, not merely package imports.

The Encyclopedia already encoded that rule deliberately throughout its composition graph:

```python
if __package__:
    from .enciclopedia_app import ...
else:
    from enciclopedia_app import ...
```

and page modules likewise choose package-relative versus top-level imports.

### 3.2 What the split broke

After `ad947269`, `enciclopedia_presentation.py` became a facade over the new cohesive modules but unconditionally imported them relatively:

```python
from .enciclopedia_controls import ...
from .enciclopedia_focus import ...
from .enciclopedia_planet_art import ...
from .enciclopedia_toy_controls import ...
```

In Greia script mode the pages import this facade as top-level:

```python
from enciclopedia_presentation import ...
```

so `enciclopedia_presentation.__package__` is empty. Its relative imports fail before `EncyclopediaApp.run()` can draw a first frame or call `mark_activity_ready()`.

That explains all of the observed facts simultaneously:

- package/source imports pass;
- static validation passes;
- the split commit is the first bad runtime SHA;
- the Shell remains in Activities/Starting state;
- no Encyclopedia Activity frame is produced;
- reverting the Encyclopedia tree to the pre-split state restores runtime launch.

This was a runtime import-mode regression, not an art-cache or R7 display-authority failure.

### 3.3 Correction

Committed:

```text
3447c36edc2a4858aa3e5f8cbda9a7dabac11866
Encyclopedia: restore script-mode presentation imports
```

The facade now explicitly supports both modes:

```python
if __package__:
    from .enciclopedia_controls import ...
    ...
else:
    from enciclopedia_controls import ...
    ...
```

No broad `try/except ImportError` is used. A genuine failure inside a split module must still fail loudly rather than being mistaken for import-mode fallback.

The split modules remain separate and the quality/interactivity work is preserved.

A fresh-process regression probe was added in:

```text
tests/test_encyclopedia_script_launch.py
```

It executes the Encyclopedia `main.py` top-level import graph using `runpy.run_path()` with a non-`__main__` run name so startup side effects are avoided while the real script-mode import semantics are preserved.

---

## 4. Hostile Simulator Home failure — root cause

The hostile fixture is intentionally non-cooperative:

```text
tests/fixtures/activities/r7_noncooperative_chrome/main.py
```

It:

- draws over the full Activity surface;
- publishes READY;
- ignores Activity-local input;
- never checks the graceful STOP marker;
- never calls `pygame.event.get()`;
- only calls `pygame.event.pump()` in an infinite loop.

That is exactly the fixture required to prove Home is **outside Activity cooperation**.

### 4.1 Why the old Simulator path failed

The trusted Python Simulator bootstrap had been polling remote input and intercepting protected Home only inside its monkeypatched `pygame.event.get()`.

Therefore the hostile fixture could starve the Simulator Home path simply by not calling `event.get()`.

The 12-second headless timeout was not the root cause. Extending it would not establish the missing authority boundary.

The old remote Home path also raised `SystemExit(0)` directly inside the Activity process. That gave cooperative Activities a convenient Simulator return path, but it did **not** exercise the real platform lifecycle used by `TrustedChromeActivitySupervisor`:

```text
Home action
  -> SystemChromeCoordinator
  -> SystemChromeNavigationBridge
  -> ActivitySupervisor.request_stop()
  -> 2s graceful-stop deadline
  -> forced stop for a non-cooperative Activity
  -> normal cleanup / Shell return
```

The hostile fixture exposed that semantic gap.

---

## 5. Simulator trusted-input correction

New source:

```text
src/greia_simulator/system_chrome.py
```

Key classes:

```text
SimulatorSystemChromeRemoteBridge
SimulatorSystemChromeBackend
```

Composition commit:

```text
8742f28665a9e2740ac346b7e6857c583472b21a
Simulator: route protected Home through trusted lifecycle

c50b395e44a24512753be7b71eba1c2532444588
Simulator: compose trusted system chrome backend
```

### 5.1 Input ownership

`SimulatorSystemChromeRemoteBridge` subclasses the existing remote bridge rather than creating a second remote-control stack.

While trusted system chrome is visible:

- pointer input inside the complete protected region is consumed before Activity delivery;
- a left-button release/click on canonical Home produces one bounded `SystemNavigationAction.HOME`;
- the system navigation queue is hard-bounded to one pending action;
- repeated releases coalesce;
- pointer events outside the protected region continue through the existing bounded Activity input queue unchanged;
- the protected queue is cleared on activation/deactivation so stale navigation cannot cross Activity generations.

The Activity does not need to call `event.get()`, `event.pump()`, or any Greia helper for Home to work.

### 5.2 Lifecycle ownership

`GreiaSimulatorChildShell._system_chrome_coordinator()` now composes:

```text
SystemChromeCoordinator
  -> SimulatorSystemChromeBackend
  -> SimulatorSystemChromeRemoteBridge protected-input route
```

The existing `GreiaChildShell` runtime-service composition then injects that coordinator into `TrustedChromeActivitySupervisor`.

As a result, remote protected Home no longer depends on Activity event consumption. It enters the same graceful/forced lifecycle semantics used by the platform chrome architecture.

The existing trusted display bootstrap continues to draw the canonical Simulator Home overlay after Activity `flip()` / `update()` presentation. This correction moves the missing **input/lifecycle authority** to the host/coordinator boundary; it does not introduce an Activity drawing API, framebuffer proxy, broad input broker, or new display backend.

### 5.3 Regression test

Added:

```text
tests/test_simulator_system_chrome.py
```

It proves behavior rather than source shape:

1. with chrome visible, a Home click becomes `SystemNavigationAction.HOME`;
2. that Home click does not appear in the ordinary Activity event queue;
3. an ordinary outside click remains in the Activity queue;
4. the Simulator child shell composes the simulator system-chrome coordinator.

The hostile real-Shell headless fixture remains the higher-level acceptance proof and must now be rerun.

---

## 6. Acer deployment helper correction

Canonical source now contains:

```text
3a2d9290c5d24e749d33534f376b8668c3e83961
Dev tooling: allow Acer-floor deployment extraction time
```

Ordinary SSH probes remain bounded at 60 seconds. Only the known slow deployment extraction/chown operation receives the measured 180-second window:

```text
DEFAULT_SSH_TIMEOUT_SECONDS = 60
DEPLOY_EXTRACT_TIMEOUT_SECONDS = 180
```

This is developer/evidence tooling only. It changes no Greia runtime authority and avoids another local post-freeze patch on the reference Atom.

---

## 7. Test policy decision

No earlier hot-path test was weakened.

Two new tests are justified because the latest failures exposed **missing product/runtime contracts**, not implementation-style preferences:

```text
Encyclopedia must import through Greia's real script-mode execution graph.
Simulator protected Home must be consumed before Activity input and must enter platform lifecycle authority.
```

Do not add additional string/name/file-shape tests around these fixes unless another concrete invariant requires them.

---

## 8. Physical Writing note — do not over-attribute

The rejected physical run observed a black/Starting-like result while attempting Writing on the Acer.

Do **not** assume this was caused by the Encyclopedia import bug. Writing passed the same exact-SHA headless Shell path, so the next physical run must test Writing independently after deploying the corrected source.

If Writing remains black/unusable on the Acer, record it as a separate physical R7 failure and diagnose its display/runtime path. Do not mark it resolved merely because Encyclopedia launches again.

---

## 9. Honest evidence boundary after implementation

At the time of this correction, the strongest executed evidence remains the rejected SHA `3944ba74`:

```text
3944ba74 source gate: GREEN (1507 tests)
3944ba74 audits: blockers=0 / blockers=0
3944ba74 Writing/Painting/animated Simulator: PASS
3944ba74 Encyclopedia Simulator: FAIL
3944ba74 hostile Simulator Home: FAIL
3944ba74 partial Acer Shell/focus/pointer: PASS
3944ba74 full Acer R7.2/R7.3: INCOMPLETE
```

Corrections now committed:

```text
3447c36e  Encyclopedia script-mode facade
8742f286  Simulator trusted Home/input backend
c50b395e  Simulator child-shell composition
3a2d9290  Acer deployment extraction bound
```

Regression source added:

```text
d9343bb2  Encyclopedia script-mode runtime-import test
4eac5572  Simulator protected-Home routing tests
```

These post-`3944ba74` changes are **not yet claimed as executed PASS** in this connector environment.

---

## 10. Next exact gate

Freeze fresh current `main` and run:

1. focused R7/Simulator/Encyclopedia discovery tests, now including:
   - `test_encyclopedia_script_launch.py`
   - `test_simulator_system_chrome.py`
2. both Activity architecture audits; require blockers=0;
3. full `make verify`; require exit 0;
4. real-Shell headless Simulator matrix:
   - Encyclopedia — must produce Activity frame and Home return;
   - Writing — Home return;
   - Painting — Home return;
   - animated Activity — Home return;
   - hostile fixture — Home must force return without Activity cooperation;
5. inspect screenshots and warning logs;
6. only after source + Simulator are green, deploy the same frozen source using the now-canonical 180-second extraction bound;
7. execute the complete R7.2/R7.3 Acer protocols, including Writing and Painting independently, hostile 10/10, abrupt crash recovery, normal 20/20 durability, logs and performance.

Do not advance R7.4 until the required R7.2/R7.3 physical verdict is accepted.
