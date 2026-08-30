# Greia — Current Engineering Handover

**Updated:** 2026-08-30  
**Canonical repository/branch:** `frozenpepper/Greia` / `main`  
**Primary blocking phase:** **R7 — direct graphics/session/input architecture**  
**Current subphase:** **R7.3 trusted Home verification + physical acceptance**  
**Latest runtime source change requiring execution:** `45b185d92bb577a3f40c741552fe247a8f6d0b70`  
**Activity modernization:** **COMPLETE**  
**R7.2/R7.3 Acer physical acceptance:** **INCOMPLETE**  
**Ordinary-family public release:** **NOT READY**  
**Public-release gate:** `docs/release/GREIA_PUBLIC_RELEASE_READINESS.md`

This is the short continuation contract. Historical detail belongs in dated reviews, plans and Git history.

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

For current R7.3 work also read:

```text
docs/adr/0014-greia-identity-arm-parity-and-direct-graphics-direction.md
docs/adr/0019-platform-owned-activity-system-navigation.md
docs/adr/0020-runtime-neutral-input-profiles-and-controller-support.md
docs/product/ACTIVITY_SYSTEM_NAVIGATION.md
docs/product/ACTIVITY_INPUT_STANDARDS.md
docs/engineering/ENGINEERING_FOUNDATIONS.md
docs/engineering/GREIA_PERFORMANCE_BEST_PRACTICES.md
docs/reviews/2026-08-29_R7_ACTIVITY_BACKEND_INDEPENDENCE_AND_DISPLAY_SESSION_REVIEW.md
docs/reviews/2026-08-30_R7_R73_HOME_OVERLAY_POST_MODERNIZATION_CORRECTION.md
docs/testing/2026-08-29_R7_R72_LEGACY_X_CONTAINMENT_SOURCE_AND_ACER_ACCEPTANCE.md
docs/testing/2026-08-29_R7_R73_TRUSTED_SYSTEM_CHROME_SOURCE_AND_ACER_ACCEPTANCE.md
```

Work directly on current `main`. Refresh before writes. Preserve concurrent work. Do not use GitHub-hosted Actions unless the owner explicitly authorizes that execution.

---

## 2. Release-preparation relationship

`docs/release/GREIA_PUBLIC_RELEASE_READINESS.md` is the release gate. It distinguishes public source, technical preview and the intended ordinary-family release.

The intended release is not certified merely because source tests pass. The first incomplete blocking platform phase remains R7, so current release preparation must continue through R7 rather than jumping directly to packaging/marketing/publication polish.

---

## 3. Activity modernization remains closed

The catalogue pass under:

```text
docs/plans/2026-08-29_R7_R73_ACTIVITY_MODERNIZATION.md
```

is complete.

Historical exact-SHA evidence at `e2b831da19a1ae706a8b675985f4191881a95321` recorded:

```text
Activity system-chrome ownership audit: blockers=0
Activity backend-independence audit: blockers=0
make verify: PASS at that historical SHA
architecture/performance Activity pass: COMPLETE
```

Do not reopen a catalogue-wide refactor sweep because the later Simulator platform adapter changed. Future Activity refactoring is evidence-driven/per-Activity.

Do not restore Activity-owned Home drawing or hit-testing.

---

## 4. Why Home disappeared in the Simulator

After the Activity migration, manual inspection of the Encyclopedia exposed that the platform Home layer was not visibly present.

The Encyclopedia itself is architecturally correct:

```text
activities/enciclopedia_greia/enciclopedia_app.py
```

- draws only Activity content;
- excludes Greia's protected region from Activity pointer authority;
- uses `pygame.display.flip()`;
- keeps Activity-internal Back distinct from system Home.

The problem was the Simulator compatibility presentation layer.

### First fix

```text
83738f737a41aec7c139b3a4a3363e746ba0f266
Simulator: make trusted Home overlay deterministic and fail loud
```

Removed broad exception swallowing around trusted Home rendering in:

```text
src/greia_simulator/python_activity.py
```

The Simulator now draws trusted Home after Activity frame presentation and does not silently continue if that renderer fails.

### Second fix

Source review then found that an Activity using partial:

```python
pygame.display.update(rect_or_rects)
```

could omit the Home corner from the actual dirty update even though Greia had drawn Home onto the backing surface.

Fixed in:

```text
45b185d92bb577a3f40c741552fe247a8f6d0b70
Simulator: preserve trusted Home on partial display updates
```

The Activity's dirty update remains intact; Greia performs one additional update only for the small protected chrome region when presentation is partial. Full flips/updates do not pay that extra update.

No Activity-side workaround and no full-screen pixel proxy were introduced.

---

## 5. Evidence boundary after the fixes

Historical `e2b831da` evidence is still valid for the catalogue source migration it actually tested.

However, Simulator Home runtime/visual evidence captured before `45b185d9` is stale for the current presentation adapter.

Current exact disposition:

```text
Activity modernization: COMPLETE
Home fail-loud source fix: IMPLEMENTED
partial-update Home hardening: IMPLEMENTED
post-fix Simulator visual/runtime gate: NOT RUN
post-fix R7.3 source gate: NOT RUN
R7.2/R7.3 Acer physical gate: INCOMPLETE
```

Do not infer PASS merely from the small diff.

Full correction record:

```text
docs/reviews/2026-08-30_R7_R73_HOME_OVERLAY_POST_MODERNIZATION_CORRECTION.md
```

---

## 6. Next exact step — execute current source

On one exact current SHA:

### A. Simulator/source evidence

1. Run the focused Simulator/bootstrap tests.
2. Launch through the real Greia Simulator and verify at minimum:
   - Encyclopedia;
   - Writing;
   - Painting;
   - one continuously animated/game Activity.
3. For each:
   - first usable frame;
   - normal child interaction;
   - visible canonical Home;
   - Home input exits cleanly to Shell;
   - no Activity-owned Home appears underneath/alongside it.
4. If an existing safe path already uses partial `pygame.display.update(...)`, verify Home remains visible there too. Do not modify an Activity merely to manufacture evidence.
5. Run the canonical R7.3 source gate:

```bash
PYTHONPATH=src python3 -m unittest \
  tests.test_system_chrome \
  tests.test_system_chrome_legacy_x \
  tests.test_trusted_chrome_supervisor \
  tests.test_r7_child_shell_trusted_chrome_composition \
  tests.test_r7_noncooperative_chrome_fixture \
  tests.test_r7_shell_window_composition \
  tests.test_display_session_legacy_x \
  tests.test_supervisor_display_session \
  tests.test_r7_activity_device_authority \
  tests.test_activity_backend_policy \
  tests.test_activity_system_chrome_audit \
  -v

PYTHONPATH=src python3 tools/audit_activity_backend_independence.py activities
PYTHONPATH=src python3 tools/audit_activity_system_chrome_ownership.py --strict
make verify
```

Required:

```text
Activity backend blockers: 0
Activity system chrome ownership audit: blockers=0
make verify: exit 0
```

### B. Physical evidence

Only after A is green, deploy that exact tested SHA to the reference Acer and execute:

```text
docs/testing/2026-08-29_R7_R72_LEGACY_X_CONTAINMENT_SOURCE_AND_ACER_ACCEPTANCE.md
docs/testing/2026-08-29_R7_R73_TRUSTED_SYSTEM_CHROME_SOURCE_AND_ACER_ACCEPTANCE.md
```

R7.3 physical acceptance requires Writing/Painting, hostile non-cooperative Home/forced-return behavior, 10/10 hostile cycles, crash cleanup, performance sanity and no child-visible Linux/Xorg surface.

On `ACCEPTED`, continue R7.4 controller/system-input ownership and the remaining ADR-0014 direct/compositor evidence. On `INCOMPLETE`, do not bypass the missing lane.

---

## 7. Test-suite policy

The test count is not a product goal.

Continue pruning tests that only freeze implementation shape or duplicate a stronger audit, especially:

```text
source-string/name presence assertions
historical function/file-shape scans
duplicate checks already covered by AST/project audits
unrelated cross-subsystem assertions in the wrong test module
```

Keep tests that protect real behavior/contracts:

```text
security/trust boundaries
sandbox/device authority
lifecycle/forced return/cleanup
storage/profile/package/progression semantics
renderer-neutral Home geometry/action routing
backend-independence and ownership audits
rollback/failure behavior
game/domain rules and important regressions
```

Do not add a test simply because a line changed. Prefer behavioral protection when a regression is genuinely worth keeping.

---

## 8. R7 invariants

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
- preserve Activity precomposed opaque backdrops, converted surfaces, bounded caches and dirty rendering.
- X11 is migration plumbing, not the target architecture.
- final graphics direction remains DRM/KMS-centered; a minimal compositor requires measured justification.
- Simulator evidence is not physical/backend evidence.

---

## 9. Other workstreams

- Encyclopedia E3 remains historically accepted in its own exact evidence lane; do not let E4 displace R7.
- New prerecorded speech uses the canonical authoring-time Voice Production Engine; no parallel TTS/Whisper logic inside the OS.
- The physically accepted lightweight microphone route is a separate platform lane; do not disturb it during Home work.

---

## 10. Current disposition

```text
Ordinary-family public release: NOT READY
Blocking phase: R7 OPEN
Activity modernization: COMPLETE
Current runtime candidate: 45b185d9 + later docs-only commits
Post-fix Simulator/source execution: PENDING
R7.2/R7.3 Acer acceptance: INCOMPLETE
Next action: execute current-SHA Simulator + R7.3 source gate, then same-SHA Acer gate
```
