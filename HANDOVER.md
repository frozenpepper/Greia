# Greia — Current Engineering Handover

**Updated:** 2026-09-01  
**Canonical repository/branch:** `frozenpepper/Greia` / `main`  
**Primary blocking phase:** **R7 — direct graphics/session/input architecture**  
**Current subphase:** **R7.2/R7.3 physical after Writing surface fix (d947eb7e)**  
**Latest runtime source change requiring execution:** `d947eb7ef5ad3703cb7293a8bba73bf9db9277e4` (Writing physical-surface fix – verified)  
**Activity modernization:** **COMPLETE**  
**Latest executed source gate:** **PASS at `d947eb7ef5ad3703cb7293a8bba73bf9db9277e4` — 1512 tests (skipped=2)**  
**Latest Simulator verdict:** **PASS at `d947eb7e` — Writing visual PASS (toolbar+editor, not black, 8s survival), Painting presentation PASS on Acer; Encyclopedia/hostile Simulator matrix was green at 83ed5d58 (1510 tests) and remains green via regression tests `test_encyclopedia_script_launch` + `test_simulator_system_chrome` at d947eb7e**  
**R7.2/R7.3 Acer physical acceptance:** **PARTIAL at `d947eb7e` — Writing full lane PASS (Starting→visible, typing>15s, save/autosave, relaunch persistence, protected Escape return, no black, no Linux), Painting presentation PASS (Starting→visible canvas+palette, not black), hostile 10/10 / abrupt crash / 20/20 durability still INCOMPLETE**  
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

The current acceptance freeze is:

```text
d947eb7ef5ad3703cb7293a8bba73bf9db9277e4 (Writing physical-surface fix)
parent 83ed5d58 was green at 83ed5d58 (1510 tests, audits 0/0, Simulator five-case PASS, Shell PASS, Acer diagnostic CLASSIFIED)
```

Executed at **d947eb7e** (`PY=/opt/homebrew/bin/python3.12`):

```text
working tree before/after source gate: clean (HEAD == origin/main == d947eb7e)
focused regression: test_writing_physical_surface_contract PASS (2), test_core_creation_activities PASS (16), test_first_party_activity_readiness PASS (1)
backend audit: PASS, activities=34 blockers=0 (migration_findings=2 non-blocking)
chrome audit --strict: PASS, blockers=0
make verify: PASS, 1512 tests OK (skipped=2) – project validation 34 Activities PASS, per-Activity validation 34 PASS, shell-check/footprint PASS (bundle 110.21 MB)
```

The two earlier Encyclopedia Acer-floor hot-path defects remain closed:

```text
planet_earth direct image decode/scale: absent
magnet direct pygame font constructor: absent
```

Corresponding fixes remain:

```text
6024240034a20bb8724eaaf548d4ac14061bef43 Encyclopedia: keep Earth asset decode behind VisualLibrary
0828cd35b957203775759f442069b9d51e0caf5a Encyclopedia: route magnet labels through Greia typography
```

The additional narrow Writing fix at d947eb7e is:

```text
d947eb7e Writing: stop blanking physical frame with unused reference canvas
  – WritingRenderer keeps responsive physical SDL surface via ChildUiMetrics
  – composition root no longer creates PygameReferenceCanvas, passes canvas=None
  – regression test test_writing_physical_surface_contract prevents recreation
```

Do not weaken the hot-path or Writing regression contracts.

---

## 5. Simulator result at `d947eb7e` (and parent `83ed5d58`)

Executed matrix at **d947eb7e**:

```text
Writing first-frame visual: PASS – toolbar (4 buttons + plus, SALVO, brush) + white editor/page with cursor, not black/blank+pointer, no corruption
Writing post-interaction (8s survival): PASS
Painting: not executed this gate, but visible on Acer at d947eb7e (see §7)
Volo Draghetto: inherited PASS from 83ed5d58 matrix (1510 tests)
Encyclopedia script-mode: PASS via test_encyclopedia_script_launch (d9343bb2)
hostile Home diversion: PASS via test_simulator_system_chrome (4eac5572)
libpng/bad-adaptive-filter warning: NO
overall gate: PASS
```

Historical: at `3944ba74`, Encyclopedia and hostile failed before the two runtime corrections; bisected to `ad947269` (script-mode facade) and old Simulator `event.get()`-only Home. Those were corrected at `3447c36e` + `8742f286/c50b395e` and proven by the two new regression tests. At `83ed5d58`, the full five-case Simulator matrix was PASS (1510 tests, 83ed5d58 source). The Writing black failure was **not** a Simulator failure – Writing passed headless at 83ed5d58; the physical failure was classified separately.

This produced the Writing-specific root cause (see §7).

### 5.1 Encyclopedia script-mode regression (historical)

Bisect `ad947269` etc. – corrected at `3447c36e`, covered by `d9343bb2`.

### 5.2 Hostile Simulator Home authority regression (historical)

Hostile ignored `event.get()` – corrected at `8742f286/c50b395e` via `src/greia_simulator/system_chrome.py`, covered by `4eac5572`. Simulator now composes `SystemChromeCoordinator -> SimulatorSystemChromeBackend -> TrustedChromeActivitySupervisor`.

### 5.3 Writing black/dot regression (new)

Writing alive/READY/mapped/topmost but `PygameReferenceCanvas.present(clear=theme.background)` overwrote the valid physical frame with untouched logical surface. Fixed at `d947eb7e` (see §7). Visual-pixel verification at d947eb7e proves first frame is Writing UI, not black.

Full correction records:
- `docs/reviews/2026-08-31_R7_SIMULATOR_RUNTIME_INTEGRATION_REJECTION_AND_CORRECTION.md`
- `docs/reviews/2026-08-31_R7_ACER_WRITING_BLACK_SURFACE_ROOT_CAUSE_AND_FIX.md`

---

## 6. Acer deployment helper

The `3944ba74` attempt proved Atom N270 can exceed 60s for 110 MB bundle; `3a2d9290` made the bound canonical.

At **d947eb7e**, canonical `tools/deploy_to_acer.py` was used without patch:

```text
bundle 110.21 MB, upload 2.8 MB/s 39s, extraction/chown ok, greia-launcher restart, wait --timeout 180 ready, status active, snapshot captured
proven via sha256sum /opt/greia-os/activities/writing/main.py = e2f69027... matching local d947eb7e (vs 496b45fd at 83ed5d58)
```

Policy remains: ordinary SSH 60s, deployment extraction/chown 180s. Do not patch after freeze.

---

## 7. Acer evidence at `d947eb7e` and `83ed5d58`

**At `83ed5d58` (diagnostic):**

Executed/green:

```text
exact source deployed: YES (plan sha256 9c652a5c..., writing main 496b45fd...)
Shell boot/focus after restart: PASS
pointer/touchpad: PASS
child-visible Linux: NO
Activity DRM/raw-input: NO
material performance regression: NO
physical libpng warning: NO
logs reviewed: YES
```

Failure: Writing launched via child path → `Starting…` then solid black 1024x600 with only pale pointer dot, while process alive, READY exists, DISPLAY=:0, SDL_VIDEODRIVER=x11, window 8388616 1024x600 visible/focused/topmost over Shell 4194311, LVDS1 1024x600@60.04, no platform_failure/traceback. Classified **ACTIVITY_X11_RENDERING_OR_SURFACE_FAILURE** (D). Painting not tested per protocol.

**At `d947eb7e` (fix verification, child path, observation-only except one focus recovery):**

- T+2s `writing-t2.png`: Starting… overlay
- T+7s `writing-t7.png` + `acer-writing-visible/screen.png`: **Writing visible** – beige top bar, toolbar (book/undo/emoji/+ + SALVO/brush), large white editor with `GREIA TESTO DI PROVA` etc., cursor, not black, not blank+pointer, no Linux, no traceback
- Typing/editing `NUOVO TEST 123` + `Seconda riga di prova` for >15s: **PASS** – `writing-after-text.png` shows new lines, cursor responsive, pointer usable
- Autosave 5s wait: **PASS**
- `key Escape` return: **PASS** – immediate CREA 3/3, focus/pointer restored, `snapshot` ok (one recovery via `windowfocus 4194311` after first return due to lost X Focus, observation-only, not the black root cause)
- Relaunch after autosave: **PASS** – after focus recovery, second launch `writing-relaunch2.png` shows editor with persisted `NUOVO TEST 123` + `Seconda riga di prova` plus prior content, proving **save/relaunch persistence PASS**; second `Escape` clean (`writing-final-return.png`)
- Overall Writing lane: launch PASS, input PASS, save/autosave PASS, relaunch persistence PASS, protected return PASS

- Painting independent check:
  - `painting-t2.png` Starting…, `painting-t7.png` + `acer-painting-visible/screen.png` **Painting visible** – white canvas 1024x600, top toolbar, bottom 10-color palette + 3 brush sizes, `SALVO`, not black, not blank+pointer
  - `key Escape` return to CREA 1/3: **PASS**
  - Sustained 20s high-rate draw / tool change / save/relaunch not yet executed via physical high-rate path (remote injection is not a substitute per the acceptance doc) – presentation is proven, durability lanes remain INCOMPLETE

Still incomplete for full R7.2/R7.3:

```text
hostile first cycle + 10/10 forced Home returns
abrupt Activity crash recovery
normal Shell -> Activity -> Shell 20/20 cycles (≥5 Writing/Painting)
performance evidence (idle/busy CPU/RSS, launch/return latency)
final logs
```

The long lanes remain deferred until the presentation path is usable – which it now is at d947eb7e.

---

## 8. Current honest evidence boundary

Executed evidence:

```text
d947eb7e source gate: PASS, 1512 tests (skipped=2)
d947eb7e backend audit: blockers=0
d947eb7e chrome audit: blockers=0
d947eb7e Simulator Writing visual: PASS (toolbar+editor, not black, 8s survival)
d947eb7e Acer Writing: PASS (visible, typing>15s, save, relaunch persistence, protected return)
d947eb7e Acer Painting presentation: PASS (canvas+palette visible, not black)
83ed5d58 Simulator five-case matrix: PASS (1510 tests, Encyclopedia/hostile/Painting etc. at 83ed5d58)
83ed5d58 Acer diagnostic: CLASSIFIED at 83ed5d58 (black D), now FIXED at d947eb7e
83ed5d58 partial Acer Shell/focus/pointer: PASS
d947eb7e full R7.2/R7.3 Acer: PARTIAL (Writing lane green, Painting presentation green, remaining 10/10/crash/20-20 not yet executed)
```

Post-`3944ba74` source corrections now executed at d947eb7e:

```text
3447c36e  Encyclopedia script-mode facade
8742f286  Simulator protected-input/backend
c50b395e  Simulator child-shell coordinator
d9343bb2  script-mode regression test
4eac5572  Simulator protected-Home behavioral tests
3a2d9290  Acer deployment extraction timeout
d947eb7e  Writing physical-surface fix + regression test (e2f69027 vs 496b45fd)
```

The `83ed5d58` diagnostic corrections are now executed and the `d947eb7e` fix is executed.

---

## 9. Next exact step

On the local execution machine (current HEAD is d947eb7e, origin/main same, tree clean):

1. (Done) focused regression (`test_writing_physical_surface_contract`, `test_core_creation_activities`, `test_first_party_activity_readiness`) PASS, audits 0/0, `make verify` 1512 PASS, Simulator Writing visual PASS, candidate frozen, deployed d947eb7e, Writing+Painting presentation PASS on Acer
2. Continue **without redeploy or source/Simulator rerun** (source unchanged):
   - hostile first cycle + 10/10 consecutive forced Home returns via normal child path (deploy fixture already present)
   - abrupt Activity crash recovery
   - normal Shell -> Activity -> Shell 20/20 durability cycles (mix Writing/Painting + lightweight + animated, ≥5 Writing/Painting, no extra successes to hide failures)
   - performance/host logs per `docs/testing/2026-08-29_R7_R72_LEGACY_X_CONTAINMENT_SOURCE_AND_ACER_ACCEPTANCE.md` §§9–14 and `docs/testing/2026-08-29_R7_R73_TRUSTED_SYSTEM_CHROME_SOURCE_AND_ACER_ACCEPTANCE.md` §§7–13
3. Update `docs/plans/...`, `HANDOVER.md`, `docs/reviews/2026-08-31_R7_ACER_WRITING_BLACK_SURFACE_ROOT_CAUSE_AND_FIX.md` with physical verdict, then commit/push documentation
4. Do not advance R7.4 until R7.2/R7.3 `ACCEPTED`

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
Blocking phase: R7 OPEN (R7.2/R7.3 physical)
Activity modernization: COMPLETE
Latest executed source gate: PASS at d947eb7e (1512 tests, skipped=2)
Latest executed Simulator: PASS at d947eb7e (Writing visual toolbar+editor not black, 8s survival, protected return; Painting not in this gate but visible on Acer)
Encyclopedia runtime root cause: FIX VERIFIED at d947eb7e via test_encyclopedia_script_launch (was FAIL at 3944ba74, now PASS at 83ed5d58+ and d947eb7e)
Simulator hostile Home root cause: FIX VERIFIED at d947eb7e via test_simulator_system_chrome (was FAIL at 3944ba74, now PASS at 83ed5d58+ and d947eb7e)
Writing black/dot root cause: CLASSIFIED at 83ed5d58 (D, ACTIVITY_X11_RENDERING_OR_SURFACE_FAILURE) and FIX VERIFIED at d947eb7e (PygameReferenceCanvas removed, canvas=None, regression test PASS, Simulator visual PASS, Acer Writing visible/typing/save/relaunch PASS)
Acer deployment timeout mutation: CANONICAL FIX IMPLEMENTED (3a2d9290, 180s)
R7.2/R7.3 Acer physical gate: PARTIAL at d947eb7e (Writing lane PASS, Painting presentation PASS, hostile 10/10 / crash / 20-20 / performance still INCOMPLETE)
Next action: continue on already-deployed d947eb7e without redeploy – hostile first+10/10, abrupt crash, normal 20/20 durability, performance/logs per R7.2/R7.3 docs §§9–14/§§7–13
```
