# Greia — Current Engineering Handover

**Updated:** 2026-08-31  
**Canonical repository/branch:** `frozenpepper/Greia` / `main`  
**Primary blocking phase:** **R7 — direct graphics/session/input architecture**  
**Current subphase:** **R7.2/R7.3 exact-current source + Simulator re-verification after runtime-integration corrections**  
**Latest runtime source change requiring execution:** `c50b395e44a24512753be7b71eba1c2532444588`  
**Activity modernization:** **COMPLETE**  
**Latest executed source gate:** **PASS at `3944ba74b5d5057b46247526633b06ec0f3dd4ce` — 1507 tests**  
**Latest Simulator verdict:** **INCOMPLETE at `3944ba74` — Encyclopedia + hostile Home failed; corrections committed, rerun pending**  
**R7.2/R7.3 Acer physical acceptance:** **INCOMPLETE**  
**Ordinary-family public release:** **NOT READY**  
**Public-release gate:** `docs/release/GREIA_PUBLIC_RELEASE_READINESS.md`

This file is the short continuation contract. Historical detail belongs in dated reviews, the active plan and Git history.

---

## 1. Mandatory resume set

Read before substantive work:

```text
AGENTS.md
README.md
docs/DOCUMENTATION.md
docs/architecture/GREIA_ARCHITECTURE.md
docs/plans/2026-08-08_ARCHITECTURE_REMEDIATION_AND_PLATFORM_COMPLETION.md
HANDOVER.md
skills/greia-os-work/SKILL.md
```

For the current R7 gate also read:

```text
docs/adr/0014-greia-identity-arm-parity-and-direct-graphics-direction.md
docs/adr/0019-platform-owned-activity-system-navigation.md
docs/adr/0020-runtime-neutral-input-profiles-and-controller-support.md
docs/product/ACTIVITY_SYSTEM_NAVIGATION.md
docs/product/ACTIVITY_INPUT_STANDARDS.md
docs/engineering/ENGINEERING_FOUNDATIONS.md
docs/engineering/GREIA_PERFORMANCE_BEST_PRACTICES.md
docs/reviews/2026-08-31_R7_CURRENT_HEAD_SOURCE_GATE_REJECTION_AND_EARTH_CACHE_FIX.md
docs/reviews/2026-08-31_R7_SECOND_SOURCE_REJECTION_MAGNET_TYPOGRAPHY_FIX.md
docs/reviews/2026-08-31_R7_SIMULATOR_RUNTIME_INTEGRATION_REJECTION_AND_CORRECTION.md
docs/testing/2026-08-29_R7_R72_LEGACY_X_CONTAINMENT_SOURCE_AND_ACER_ACCEPTANCE.md
docs/testing/2026-08-29_R7_R73_TRUSTED_SYSTEM_CHROME_SOURCE_AND_ACER_ACCEPTANCE.md
```

For Encyclopedia runtime work also read:

```text
skills/greia-activity-authoring/SKILL.md
skills/greia-activity-authoring/ENGINEERING.md
skills/greia-activity-authoring/LAUNCH_ACCEPTANCE.md
docs/handovers/GREIA_VISUAL_SYSTEM_RESUME.md
docs/handovers/GREIA_ENCYCLOPEDIA_QUALITY_HANDOVER_2026-08-30.md
```

Work directly on current `main`. Refresh before writes. Preserve concurrent work. Do not use GitHub-hosted Actions unless the owner explicitly authorizes that execution.

---

## 2. Release relationship

`docs/release/GREIA_PUBLIC_RELEASE_READINESS.md` remains the public-release gate.

The intended ordinary-family release is **not ready**. R7 remains the first incomplete blocking platform phase. Source tests and Simulator evidence are necessary but do not substitute for exact physical Acer/backend acceptance.

---

## 3. Activity modernization stays closed

The catalogue-wide R7.3 Activity modernization pass is complete.

Do **not** reopen a catalogue-wide refactor sweep because of the current Encyclopedia or Simulator findings. These were specific runtime/evidence-driven defects.

Continue to preserve:

```text
Activity backend-independence audit blockers=0
Activity system-chrome ownership strict audit blockers=0
no Activity-owned real Home drawing or Home hit-testing
```

---

## 4. Source gate is now green at the latest executed SHA

The third acceptance attempt froze:

```text
3944ba74b5d5057b46247526633b06ec0f3dd4ce
```

Executed results:

```text
working tree before/after source gate: clean
focused discovery gate: PASS (17 patterns / 136 tests)
backend audit: PASS, blockers=0
chrome audit: PASS, blockers=0
make verify: PASS, 1507 tests
project validation: PASS
Activity validation: PASS
shell/source gate: PASS
```

The two earlier Encyclopedia Acer-floor hot-path defects are confirmed closed on this executed SHA:

```text
planet_earth direct image decode/scale: absent
magnet direct pygame font constructor: absent
```

Corresponding fixes remain:

```text
6024240034a20bb8724eaaf548d4ac14061bef43
Encyclopedia: keep Earth asset decode behind VisualLibrary

0828cd35b957203775759f442069b9d51e0caf5a
Encyclopedia: route magnet labels through Greia typography
```

Do not weaken the current hot-path contract merely because its present test is lexical. It has caught two real regressions; replace it only with an equally strong or stronger less-brittle contract later.

---

## 5. Simulator result at `3944ba74`

Executed matrix:

```text
Writing: PASS
Painting: PASS
Volo Draghetto: PASS
Encyclopedia: FAIL — no Activity frame / READY
hostile non-cooperative fixture: FAIL — Home did not return
libpng/bad-adaptive-filter warning: NO
```

This produced two independent root causes.

### 5.1 Encyclopedia script-mode regression

Bisect:

```text
faa46ec4  PASS
51db988a  PASS
ad947269  FIRST BAD
```

`ad947269` split `enciclopedia_presentation.py` into cohesive focus/control/toy/planet modules, but the facade retained package-relative imports only.

Greia executes Activity `main.py` as a script through `runpy.run_path(..., run_name="__main__")`. Encyclopedia already supports this mode throughout its composition graph. The split facade did not, so it failed before `mark_activity_ready()`.

Correction:

```text
3447c36edc2a4858aa3e5f8cbda9a7dabac11866
Encyclopedia: restore script-mode presentation imports
```

The split remains; only explicit package-vs-script import compatibility was restored. No broad `ImportError` fallback was added.

Regression coverage:

```text
d9343bb22eba6d0dbbb0e5be1fb5743877204257
Tests: cover Encyclopedia script-mode import graph
```

### 5.2 Hostile Simulator Home authority regression

The hostile fixture intentionally never calls `pygame.event.get()` and ignores STOP.

The old Simulator remote Home path polled/intercepted Home only inside the Activity bootstrap's monkeypatched `event.get()`. Therefore a hostile Activity could starve Home simply by never calling that function. Extending the headless timeout would not fix the authority defect.

Correction:

```text
8742f28665a9e2740ac346b7e6857c583472b21a
Simulator: route protected Home through trusted lifecycle

c50b395e44a24512753be7b71eba1c2532444588
Simulator: compose trusted system chrome backend
```

New source owner:

```text
src/greia_simulator/system_chrome.py
```

The Simulator now composes the same platform lifecycle seam:

```text
SystemChromeCoordinator
  -> SimulatorSystemChromeBackend
  -> protected remote-input route
  -> TrustedChromeActivitySupervisor
  -> graceful stop
  -> bounded forced stop when Activity ignores STOP
```

Protected-region pointer input is removed before Activity delivery. Ordinary Activity pointer input remains on the existing bounded remote queue. The system queue is bounded to one pending navigation action.

The Greia-owned Python display bootstrap continues to draw the canonical Simulator Home overlay; this correction moves missing input/lifecycle authority to the host/coordinator path and does not create an Activity drawing API or framebuffer proxy.

Regression coverage:

```text
4eac557204b1f857edb30241741f8d049a105e04
Tests: prove Simulator Home is consumed before Activity input
```

Full correction record:

```text
docs/reviews/2026-08-31_R7_SIMULATOR_RUNTIME_INTEGRATION_REJECTION_AND_CORRECTION.md
```

---

## 6. Acer deployment helper

The `3944ba74` physical attempt proved that the reference Atom N270 can exceed 60 seconds while extracting/chowning the current ~110 MB developer deployment bundle.

The operator had to patch the helper locally after freeze. That is no longer necessary.

Canonical correction:

```text
3a2d9290c5d24e749d33534f376b8668c3e83961
Dev tooling: allow Acer-floor deployment extraction time
```

Policy:

```text
ordinary SSH command timeout: 60 s
known deployment extraction/chown timeout: 180 s
```

Future evidence runs must not patch `tools/deploy_to_acer.py` after freezing the candidate SHA.

---

## 7. Partial Acer evidence at `3944ba74`

The reference Acer became reachable in the third attempt.

Executed/green:

```text
exact source deployed: YES
Shell boot/focus after restart: PASS
pointer/touchpad: PASS
child-visible Linux: NO
Activity direct DRM required: NO
Activity raw input required: NO
material performance regression observed: NO
physical libpng warning: NO
logs reviewed: YES
```

Still incomplete:

```text
Writing full launch/input/save/relaunch/Home
Painting sustained draw/save/relaunch/Home
hostile first cycle
hostile 10/10 forced returns
abrupt Activity crash recovery
normal Shell -> Activity -> Shell 20/20 cycles
```

A Writing attempt on the Acer produced a black/Starting-like result. **Do not attribute that automatically to the Encyclopedia bug.** Writing passed headless at the same SHA. On the next physical run, test Writing independently; if it remains black/unusable, record a separate physical R7 failure and diagnose it.

---

## 8. Current honest evidence boundary

Executed evidence:

```text
3944ba74 source gate: PASS, 1507 tests
3944ba74 backend audit: blockers=0
3944ba74 chrome audit: blockers=0
3944ba74 Writing/Painting/animated Simulator: PASS
3944ba74 Encyclopedia Simulator: FAIL
3944ba74 hostile Simulator Home: FAIL
3944ba74 partial Acer Shell/focus/pointer: PASS
3944ba74 full R7.2/R7.3 Acer: INCOMPLETE
```

Post-execution source corrections:

```text
3447c36e  Encyclopedia script-mode facade
8742f286  Simulator protected-input/backend source
c50b395e  Simulator child-shell coordinator composition
d9343bb2  script-mode regression test
4eac5572  Simulator protected-Home behavioral tests
3a2d9290  Acer deployment extraction timeout
```

These post-`3944ba74` changes have **not yet been executed through the exact-current gate** in this connector environment.

---

## 9. Next exact step

On the local execution machine:

1. `git switch main && git pull --ff-only`;
2. require clean worktree and freeze exact SHA;
3. run the focused discovery gate, adding:
   - `test_encyclopedia_script_launch.py`
   - `test_simulator_system_chrome.py`;
4. run both architecture audits, require blockers=0;
5. run `make verify`, require exit 0;
6. run the same exact-SHA real-Shell Simulator matrix:
   - Encyclopedia;
   - Writing;
   - Painting;
   - Volo Draghetto/another continuous animated Activity;
   - hostile non-cooperative fixture;
7. require Encyclopedia first frame + Home return and hostile forced Home return;
8. inspect screenshots/warnings;
9. verify `origin/main` still equals frozen SHA before physical work;
10. deploy exact source using canonical `tools/deploy_to_acer.py` with no local patch;
11. execute complete R7.2/R7.3 physical protocols, treating Writing independently;
12. return exact evidence and verdict.

Do not advance R7.4 until R7.2/R7.3 required physical acceptance is actually green.

---

## 10. Test/evidence discipline

The local machine has a site-packages package named `tests` that shadows this repository's namespace-style `tests/` directory under dotted imports.

Use focused discovery patterns:

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -p 'test_name.py' -v
```

`make verify` already uses discovery.

Do not change the repository test-package structure merely to work around this one machine.

Stop on the first genuine source-gate failure. Simulator failures are evidence, not permission to weaken the fixture. Physical failures are evidence, not permission to broaden `/dev/dri`, `/dev/input`, X11 or Activity authority.

---

## 11. R7 invariants

Preserve:

- Activities remain backend-neutral; ordinary Pygame/SDL is valid.
- No generic Greia drawing API or Python framebuffer proxy.
- `DisplaySessionCoordinator` remains the display/session lifecycle seam.
- `SystemChromeCoordinator` remains mandatory Home/optional Back semantic authority.
- `TrustedChromeActivitySupervisor` binds Home to the real graceful/forced Activity lifecycle.
- Home remains outside Activity rendering/input authority.
- protected system input is consumed before Activity delivery.
- ordinary Activities do not receive raw `/dev/input` or `/dev/dri`.
- controller discovery/normalization remains platform-owned.
- trusted chrome remains tiny, bounded and invalidation/event-driven.
- direct high-rate SDL pointer/text paths remain direct where safe.
- X11 remains migration plumbing, not the target architecture.
- final direction remains DRM/KMS-centered; a tiny compositor requires measured justification.
- Simulator evidence does not prove physical/backend isolation.

---

## 12. Current disposition

```text
Ordinary-family public release: NOT READY
Blocking phase: R7 OPEN
Activity modernization: COMPLETE
Latest executed source gate: PASS at 3944ba74 (1507 tests)
Latest executed Simulator: INCOMPLETE at 3944ba74
Encyclopedia runtime root cause: FIX IMPLEMENTED, RETEST PENDING
Simulator hostile Home root cause: FIX IMPLEMENTED, RETEST PENDING
Acer deployment timeout mutation: CANONICAL FIX IMPLEMENTED
R7.2/R7.3 Acer physical gate: INCOMPLETE
Next action: exact-current source gate -> exact-current Simulator -> same-SHA Acer physical completion
```
