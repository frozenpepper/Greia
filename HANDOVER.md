# Greia — Current Engineering Handover

**Updated:** 2026-08-31  
**Canonical repository/branch:** `frozenpepper/Greia` / `main`  
**Primary blocking phase:** **R7 — direct graphics/session/input architecture**  
**Current subphase:** **R7.2/R7.3 exact-current source re-verification after two Encyclopedia hot-path corrections**  
**Latest runtime source change requiring execution:** `0828cd35b957203775759f442069b9d51e0caf5a`  
**Activity modernization:** **COMPLETE**  
**R7.2/R7.3 current-source acceptance:** **REJECTED twice; second corrective source committed, retest pending**  
**R7.2/R7.3 Acer physical acceptance:** **INCOMPLETE**  
**Ordinary-family public release:** **NOT READY**  
**Public-release gate:** `docs/release/GREIA_PUBLIC_RELEASE_READINESS.md`

This file is the short continuation contract. Historical detail belongs in dated reviews, active plans and Git history.

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

For the current gate also read:

```text
docs/adr/0014-greia-identity-arm-parity-and-direct-graphics-direction.md
docs/adr/0019-platform-owned-activity-system-navigation.md
docs/adr/0020-runtime-neutral-input-profiles-and-controller-support.md
docs/product/ACTIVITY_SYSTEM_NAVIGATION.md
docs/product/ACTIVITY_INPUT_STANDARDS.md
docs/engineering/ENGINEERING_FOUNDATIONS.md
docs/engineering/GREIA_PERFORMANCE_BEST_PRACTICES.md
docs/reviews/2026-08-30_R7_R73_HOME_OVERLAY_POST_MODERNIZATION_CORRECTION.md
docs/reviews/2026-08-31_R7_CURRENT_HEAD_SOURCE_GATE_REJECTION_AND_EARTH_CACHE_FIX.md
docs/reviews/2026-08-31_R7_SECOND_SOURCE_REJECTION_MAGNET_TYPOGRAPHY_FIX.md
docs/testing/2026-08-29_R7_R72_LEGACY_X_CONTAINMENT_SOURCE_AND_ACER_ACCEPTANCE.md
docs/testing/2026-08-29_R7_R73_TRUSTED_SYSTEM_CHROME_SOURCE_AND_ACER_ACCEPTANCE.md
```

For Encyclopedia runtime changes also read:

```text
skills/greia-activity-authoring/SKILL.md
skills/greia-activity-authoring/ENGINEERING.md
skills/greia-activity-authoring/LAUNCH_ACCEPTANCE.md
skills/greia-visual-authoring/SKILL.md
docs/handovers/GREIA_VISUAL_SYSTEM_RESUME.md
docs/handovers/GREIA_ENCYCLOPEDIA_QUALITY_HANDOVER_2026-08-30.md
```

Work directly on current `main`. Refresh before writes. Preserve concurrent work. Do not use GitHub-hosted Actions unless the owner explicitly authorizes that execution.

---

## 2. Release-preparation relationship

`docs/release/GREIA_PUBLIC_RELEASE_READINESS.md` remains the release gate.

The intended ordinary-family release is not certified by source tests alone. R7 remains the first incomplete blocking platform phase, so release preparation continues through exact-current source evidence, Simulator evidence and physical Acer evidence before later release work can treat R7 as closed.

---

## 3. Activity modernization remains closed

The catalogue-wide R7.3 modernization pass is complete. Do **not** reopen another catalogue-wide refactor sweep because of these Encyclopedia failures.

The two current failures are evidence-driven corrections inside one Activity visual/runtime lane, not evidence that the Activity catalogue needs another modernization pass.

Continue to preserve:

```text
Activity backend-independence audit blockers=0
Activity system-chrome ownership strict audit blockers=0
no Activity-owned Home drawing or Home hit-testing
```

---

## 4. Trusted Home Simulator source fixes remain implemented

The platform presentation corrections remain:

```text
83738f737a41aec7c139b3a4a3363e746ba0f266
Simulator: make trusted Home overlay deterministic and fail loud

45b185d92bb577a3f40c741552fe247a8f6d0b70
Simulator: preserve trusted Home on partial display updates
```

They fix the Simulator compatibility presentation path rather than adding Activity-side Home behavior.

Current Simulator Home evidence still must be collected on the exact source state that finally passes the aggregate source gate.

---

## 5. First current-head rejection — Earth page hot-path decode/scale

The first local acceptance operator froze:

```text
9b6b055e48681714672869f8800a5f7a7c407165
```

Results:

```text
working tree before/after: clean
focused discovery gate: 136 PASS
Activity backend audit: PASS, blockers=0
Activity system-chrome ownership audit: PASS, blockers=0
make verify: FAIL
reported test count: 1507
failures: 2
Simulator: not run after source failure
Acer: unreachable / not run
verdict: REJECTED
```

Both failures traced to:

```text
activities/enciclopedia_greia/pages/planet_earth.py
```

which directly used:

```text
pygame.image.load(...)
pygame.transform.smoothscale(...)
```

inside a frame-draw fallback.

Correction:

```text
6024240034a20bb8724eaaf548d4ac14061bef43
Encyclopedia: keep Earth asset decode behind VisualLibrary
```

`VisualLibrary.planet()` remains the sole authored-Earth package lookup/decode/scale/cache owner. If it cannot provide the sprite, the page uses its existing procedural Earth renderer.

Full record:

```text
docs/reviews/2026-08-31_R7_CURRENT_HEAD_SOURCE_GATE_REJECTION_AND_EARTH_CACHE_FIX.md
```

---

## 6. Second current-head rejection — Magnet page direct SysFont

The next disciplined gate froze:

```text
650ce2ebeb9eaee82efb292745568afabde7cce9
```

The Earth correction was confirmed:

```text
planet_earth direct image decode/scale scan: empty
previous Encyclopedia visual-foundation decode/scale test: PASS
```

The same aggregate contract then exposed the next previously masked violation:

```text
activities/enciclopedia_greia/pages/magnet.py
MagnetPage._draw_bar_magnet()
```

contained:

```python
pygame.font.SysFont(None, 22)
```

inside a helper called from the normal page draw path.

Second-run results:

```text
working tree before/after: clean
focused discovery gate: 136 PASS
Activity backend audit: PASS, blockers=0
Activity system-chrome ownership audit: PASS, blockers=0
make verify: FAIL
reported test count: 1507
failures: 1
Simulator: not run after source failure
Acer: unreachable / not run
verdict: REJECTED
```

Correction:

```text
0828cd35b957203775759f442069b9d51e0caf5a
Encyclopedia: route magnet labels through Greia typography
```

`_draw_bar_magnet()` is now an instance helper and renders its constant `N` / `S` labels through:

```text
self.context.typography.render(...)
FontRole.CONTROL
size 22
```

The real Encyclopedia context uses `CachedEncyclopediaTypography`, which already owns Greia font-family/role selection and a hard-bounded `MAX_TEXT_SURFACES = 160` rendered-line cache. No second page cache or typography subsystem was introduced.

Full record:

```text
docs/reviews/2026-08-31_R7_SECOND_SOURCE_REJECTION_MAGNET_TYPOGRAPHY_FIX.md
```

---

## 7. Test disposition

Do **not** weaken the existing Encyclopedia hot-path test in response to either failure.

Although its current implementation includes lexical forbidden-token checks, these two sequential runs have demonstrated real product value:

```text
masked violation 1: page-level image decode + smoothscale
masked violation 2: page-level font construction
```

Both violate established low-resource and visual-service ownership rules on the Acer floor.

The right correction is to restore the existing service/cache boundaries. A future test-quality pass may replace the lexical mechanism with an equally strong or stronger architectural/behavioral contract if that is less brittle.

No new test was added merely because either line changed.

---

## 8. Current evidence boundary

Honest current state after the second source correction:

```text
Activity modernization: COMPLETE
trusted Home Simulator source fixes: IMPLEMENTED
9b6b055e source gate: REJECTED — Earth decode/scale
6024240 Earth correction: IMPLEMENTED
650ce2eb source gate: REJECTED — Earth confirmed clean; Magnet SysFont exposed
0828cd35 Magnet typography correction: IMPLEMENTED
post-0828cd35 focused gate: NOT RUN
post-0828cd35 backend audit: NOT RUN
post-0828cd35 chrome audit: NOT RUN
post-0828cd35 make verify: NOT RUN
post-0828cd35 Simulator Home matrix: NOT RUN
R7.2/R7.3 Acer physical gate: INCOMPLETE
ordinary-family public release: NOT READY
```

Do not infer PASS from source inspection.

---

## 9. Focused-test invocation correction

The local execution machine has a regular site-packages package named `tests` that shadows this repository's namespace-style `tests/` directory when using dotted imports such as `tests.test_system_chrome`.

Use `unittest discover` patterns instead:

```bash
PYTHONPATH=src python3 -m unittest discover \
  -s tests \
  -p 'test_system_chrome.py' \
  -v
```

The aggregate `make verify` already uses discovery and is unaffected.

Do not change repository test packaging merely to work around this machine unless a separate engineering review justifies it.

---

## 10. Next exact step — repeat the unchanged exact-current source gate

On the local execution machine:

```bash
git switch main
git pull --ff-only
git status --short
git rev-parse HEAD
```

Require a clean worktree and freeze the exact resulting current SHA. Do not hard-reset to `0828cd35` if legitimate reviewed docs or concurrent work has advanced `main`.

Run the same 17 focused files using one `unittest discover -s tests -p '<filename>' -v` invocation per file:

```text
test_activity_backend_policy.py
test_r7_shell_window_composition.py
test_r7_activity_device_authority.py
test_hardware_session.py
test_r7_legacy_x_build_containment.py
test_display_session_legacy_x.py
test_supervisor_display_session.py
test_system_chrome.py
test_system_chrome_legacy_x.py
test_trusted_chrome_supervisor.py
test_r7_child_shell_trusted_chrome_composition.py
test_r7_noncooperative_chrome_fixture.py
test_activity_system_chrome_audit.py
test_greia_simulator.py
test_encyclopedia_interaction.py
test_encyclopedia_focus_treatment.py
test_encyclopedia_authoring_tools.py
```

Then:

```bash
PYTHONPATH=src python3 tools/audit_activity_backend_independence.py activities
PYTHONPATH=src python3 tools/audit_activity_system_chrome_ownership.py --strict
make verify
```

Required:

```text
focused gate: PASS
backend blockers=0
chrome blockers=0
make verify exit 0
```

Stop at the first genuine failure and preserve it. Do not fix-as-you-go during the acceptance run.

The operator's all-pages scan at `650ce2eb` identified `magnet.py` as the remaining direct `pygame.font.SysFont` / `pygame.font.Font` page occurrence after the Earth correction. That scan is useful but does not replace the third aggregate execution.

---

## 11. Only after a green current source gate

Run the real-Shell Simulator matrix on the same exact SHA:

```text
Encyclopedia
Writing
Painting
one continuously animated Activity
R7 non-cooperative hostile fixture
```

For every case require:

```text
first usable frame
normal/meaningful interaction
canonical protected Home visible
Home return to Shell
no Activity-owned duplicate Home
clean teardown
```

For Encyclopedia also scan output for:

```text
libpng error
bad adaptive filter
traceback
platform_failure
ready timeout
```

and inspect the screenshots. A mechanical survival result does not override a real asset/runtime warning.

Simulator evidence proves developer/runtime semantics only; it does not prove physical/backend isolation.

---

## 12. Physical Acer gate

The reference Acer was unreachable during both rejected attempts, so no current physical PASS exists.

Only after current source + Simulator gates are green, deploy that same accepted source state to the reference Acer and execute:

```text
docs/testing/2026-08-29_R7_R72_LEGACY_X_CONTAINMENT_SOURCE_AND_ACER_ACCEPTANCE.md
docs/testing/2026-08-29_R7_R73_TRUSTED_SYSTEM_CHROME_SOURCE_AND_ACER_ACCEPTANCE.md
```

Required physical evidence still includes:

```text
Shell focus/input after restart
Writing typing/save/relaunch/Home without input leakage
Painting sustained drawing/save/relaunch/Home without stray stroke
hostile non-cooperative Activity with trusted Home above hostile content
10/10 hostile forced-return cycles without launcher restart
abrupt Activity crash recovery
20/20 normal launch-return durability cycles
no child-visible Linux/Xorg/terminal surface
no Activity direct DRM/raw-input requirement
bounded log review
Acer-floor performance sanity
```

If the Acer is unreachable or a required physical interaction cannot honestly be executed, return `INCOMPLETE`; do not infer a physical PASS.

---

## 13. Test-suite policy

The test count is not a product goal.

Prune tests that merely freeze implementation shape or duplicate stronger audits, especially unrelated source-string/name-presence checks. Keep tests/contracts that protect real behavior and boundaries, including low-resource hot-path constraints with demonstrated product impact.

Do not add a test simply because a line changed.

---

## 14. R7 invariants

Preserve:

- Activities are backend-neutral; ordinary Pygame/SDL remains valid.
- No generic Greia drawing API or Python framebuffer proxy.
- `DisplaySessionCoordinator` / `DisplaySessionBackend` remains the display/session polymorphic seam.
- `SystemChromeCoordinator` remains platform Home/Back authority.
- Home remains outside Activity rendering/input authority.
- protected system input is consumed before Activity delivery.
- ordinary Activities do not get raw `/dev/input` or `/dev/dri` authority.
- controller discovery/normalization remains platform-owned.
- trusted chrome stays tiny, bounded and event/invalidation driven.
- preserve direct high-rate SDL pointer/text paths where safe.
- preserve bounded visual/text caches and keep decode/scale/font construction outside page/frame hot paths.
- X11 is migration plumbing, not the target architecture.
- final graphics direction remains DRM/KMS-centered; a minimal compositor requires measured justification.
- Simulator evidence is not physical/backend evidence.

---

## 15. Current disposition

```text
Ordinary-family public release: NOT READY
Blocking phase: R7 OPEN
Activity modernization: COMPLETE
First rejected source: 9b6b055e48681714672869f8800a5f7a7c407165
First reason: Encyclopedia Earth draw-path image decode/scale
First correction: 6024240034a20bb8724eaaf548d4ac14061bef43
Second rejected source: 650ce2ebeb9eaee82efb292745568afabde7cce9
Second reason: Encyclopedia Magnet draw-path pygame.font.SysFont
Second correction: 0828cd35b957203775759f442069b9d51e0caf5a
Post-second-fix source verification: PENDING
Post-second-fix Simulator verification: PENDING
R7.2/R7.3 Acer acceptance: INCOMPLETE
Next action: current-SHA focused discovery gate + audits + make verify; if green, same-SHA Simulator; then same-SHA Acer when reachable
```
