# Greia — Current Engineering Handover

**Updated:** 2026-08-31  
**Canonical repository/branch:** `frozenpepper/Greia` / `main`  
**Primary blocking phase:** **R7 — direct graphics/session/input architecture**  
**Current subphase:** **R7.2/R7.3 exact-current source re-verification after Encyclopedia performance correction**  
**Latest runtime source change requiring execution:** `6024240034a20bb8724eaaf548d4ac14061bef43`  
**Activity modernization:** **COMPLETE**  
**R7.2/R7.3 current-source acceptance:** **REJECTED at `9b6b055e`; corrective source committed, retest pending**  
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

The catalogue-wide R7.3 modernization pass is complete. Historical accepted source evidence remains recorded at its exact historical SHAs.

Do **not** reopen another catalogue-wide refactor sweep because of the current failure.

The 2026-08-31 rejection is one evidence-driven Encyclopedia correction, not evidence that all Activities need another modernization round.

Continue to preserve:

```text
Activity backend-independence audit blockers=0
Activity system-chrome ownership strict audit blockers=0
no Activity-owned Home drawing or Home hit-testing
```

---

## 4. Trusted Home Simulator fixes remain implemented

The platform presentation corrections remain:

```text
83738f737a41aec7c139b3a4a3363e746ba0f266
Simulator: make trusted Home overlay deterministic and fail loud

45b185d92bb577a3f40c741552fe247a8f6d0b70
Simulator: preserve trusted Home on partial display updates
```

They fixed the Simulator compatibility presentation path rather than adding Activity-side Home behavior.

Current Simulator Home evidence still must be collected on the new exact post-fix source state before any current-head acceptance claim.

---

## 5. 2026-08-31 exact-current rejection

The local acceptance operator froze:

```text
9b6b055e48681714672869f8800a5f7a7c407165
```

The run was disciplined and stopped at the first aggregate source failure.

Results at that exact SHA:

```text
working tree before/after: clean
focused R7/Simulator/Encyclopedia gate: 136 PASS
Activity backend audit: PASS, blockers=0
Activity system-chrome ownership audit: PASS, blockers=0
make verify: FAIL
reported test count: 1507
failures: 2
Simulator matrix: not run after source failure
Acer: unreachable / not run
verdict: REJECTED
```

Both failures were the same product issue:

```text
activities/enciclopedia_greia/pages/planet_earth.py
```

had reintroduced direct:

```text
pygame.image.load(...)
pygame.transform.smoothscale(...)
```

inside the page draw path.

This violated the established Acer-floor rule that page hot paths must not decode or scale authored assets.

Full record:

```text
docs/reviews/2026-08-31_R7_CURRENT_HEAD_SOURCE_GATE_REJECTION_AND_EARTH_CACHE_FIX.md
```

---

## 6. Corrective source change

Committed:

```text
6024240034a20bb8724eaaf548d4ac14061bef43
Encyclopedia: keep Earth asset decode behind VisualLibrary
```

Root cause:

- `VisualLibrary.planet()` already owned semantic asset lookup, PNG decode, conversion, size-specific scaling and the bounded cache;
- `planet_earth.py` called that owner but then added a second direct filesystem/decode/scale fallback when the owner returned `None`;
- that fallback bypassed the cache and made expensive work per-frame-capable.

Fix:

- remove the direct page-local file/decode/scale path;
- ask the injected visual provider for the prepared planet surface only;
- if no prepared sprite is available, retain the existing procedural Earth renderer.

No test was weakened or added merely because a line changed.

The two lexical hot-path tests are retained for now because this run demonstrated that they caught a real performance-boundary regression. They can be replaced later only by an equally strong or stronger, less-brittle contract.

No Home/system-chrome authority, display backend, sandbox grant, DRM/input authority or Activity lifecycle contract changed in this fix.

---

## 7. Post-fix evidence boundary

Current honest state:

```text
Activity modernization: COMPLETE
trusted Home Simulator source fixes: IMPLEMENTED
9b6b055e focused gate: PASS
9b6b055e backend audit: blockers=0
9b6b055e chrome audit: blockers=0
9b6b055e aggregate gate: REJECTED
Earth VisualLibrary ownership fix: IMPLEMENTED at 6024240
post-6024240 focused source gate: NOT RUN
post-6024240 audits: NOT RUN
post-6024240 make verify: NOT RUN
post-6024240 Simulator Home matrix: NOT RUN
R7.2/R7.3 Acer physical gate: INCOMPLETE
ordinary-family public release: NOT READY
```

Do not infer PASS from the narrow diff.

---

## 8. Focused-test invocation correction

The 2026-08-31 local machine has a regular site-packages package named `tests` that shadows this repository's namespace-style `tests/` directory when commands import `tests.test_*` directly.

Therefore future focused local gates should use `unittest discover` patterns rather than importing `tests.<module>` by dotted name.

Example:

```bash
PYTHONPATH=src python3 -m unittest discover \
  -s tests \
  -p 'test_system_chrome.py' \
  -v
```

The full `make verify` already uses discovery and was not affected by this environment issue.

Do not change the repository test package merely to work around one machine unless a separate engineering review justifies that change.

---

## 9. Next exact step — re-run the source gate on current `main`

On the local execution machine:

```bash
git switch main
git pull --ff-only
git status --short
git rev-parse HEAD
```

Require a clean worktree and freeze the exact resulting SHA. Do not hard-reset to `6024240` if legitimate docs-only or concurrent reviewed commits have advanced `main`.

### A. Focused tests

Run the same intended focused modules using discovery patterns. At minimum cover:

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

A simple shell loop invoking `python3 -m unittest discover -s tests -p '<filename>' -v` once per file is acceptable and avoids the site-packages shadowing seen on the rejected run.

### B. Architecture audits

```bash
PYTHONPATH=src python3 tools/audit_activity_backend_independence.py activities
PYTHONPATH=src python3 tools/audit_activity_system_chrome_ownership.py --strict
```

Required:

```text
backend blockers=0
chrome blockers=0
```

### C. Aggregate gate

```bash
make verify
```

Require exit 0. Record the actual current test count rather than assuming 1507.

Stop at the first genuine failure and preserve it.

---

## 10. Only after a green current source gate

Run the real-Shell Simulator matrix on the same exact SHA:

```text
Encyclopedia
Writing
Painting
one continuously animated Activity
R7 non-cooperative hostile fixture
```

For each require:

```text
first usable frame
normal/meaningful interaction
canonical protected Home visible
Home return to Shell
no Activity-owned duplicate Home
clean teardown
```

For Encyclopedia additionally scan output for:

```text
libpng error
bad adaptive filter
traceback
platform_failure
ready timeout
```

and inspect the current screenshots. A mechanical survival result is not permission to ignore an asset-decode warning.

Simulator acceptance proves developer/runtime semantics only; it does not prove physical/backend isolation.

---

## 11. Physical Acer gate

The reference Acer was unreachable during the 9b6b055e attempt, so no current physical PASS exists.

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

## 12. Test-suite policy

The test count is not a product goal.

Continue pruning tests that merely freeze implementation shape or duplicate stronger audits, especially:

```text
source-string/name-presence assertions with no real invariant
historical function/file-shape scans
duplicate checks already covered by AST/project audits
unrelated cross-subsystem assertions in the wrong test module
```

Keep tests/contracts protecting real behavior and boundaries:

```text
security/trust/privilege boundaries
sandbox/device authority
lifecycle/forced return/cleanup
storage/profile/package/progression semantics
renderer-neutral Home geometry/action routing
backend independence and Home-ownership audits
low-resource hot-path constraints with proven product impact
rollback/failure behavior
game/domain rules and important regressions
```

Do not add a test simply because a line changed.

---

## 13. R7 invariants

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
- preserve bounded visual caches and keep image decode/scale outside page/frame hot paths.
- X11 is migration plumbing, not the target architecture.
- final graphics direction remains DRM/KMS-centered; a minimal compositor requires measured justification.
- Simulator evidence is not physical/backend evidence.

---

## 14. Current disposition

```text
Ordinary-family public release: NOT READY
Blocking phase: R7 OPEN
Activity modernization: COMPLETE
Rejected tested source: 9b6b055e48681714672869f8800a5f7a7c407165
Rejection reason: Encyclopedia Earth page bypassed VisualLibrary cache with direct draw-path decode/scale
Corrective runtime commit: 6024240034a20bb8724eaaf548d4ac14061bef43
Post-fix source verification: PENDING
Post-fix Simulator verification: PENDING
R7.2/R7.3 Acer acceptance: INCOMPLETE
Next action: current-SHA focused discovery gate + audits + make verify; if green, same-SHA Simulator; then same-SHA Acer when reachable
```
