# Greia — Current Engineering Handover

**Updated:** 2026-08-30  
**Canonical repository:** `frozenpepper/Greia`  
**Canonical branch:** `main`  
**Current documentation head at this handover update:** includes `2f78e5eab03e4c1a31a57d113edca6bc9c647d01`  
**Latest runtime implementation change under review:** `83738f737a41aec7c139b3a4a3363e746ba0f266` — Simulator trusted Home render fix  
**Primary blocking platform phase:** **R7 — direct graphics/session/input architecture**  
**Current R7 subphase:** **R7.3 trusted Home verification/physical acceptance; source changed after the previous Activity-pass evidence**  
**Public-release gate:** `docs/release/GREIA_PUBLIC_RELEASE_READINESS.md`  
**Activity modernization:** **COMPLETE**; do not reopen the catalogue-wide pass merely because the Simulator platform adapter changed  
**Physical R7.2/R7.3 Acer acceptance:** **INCOMPLETE**

This file is intentionally a short continuation contract. Detailed chronology belongs in the active plan, dated reviews and Git history.

Historical long-form root state remains preserved under:

```text
docs/handovers/GREIA_ROOT_HANDOVER_ARCHIVE_2026-08-27.md
```

---

## 1. Resume rules

Before substantive work, read:

```text
AGENTS.md
README.md
docs/DOCUMENTATION.md
docs/architecture/GREIA_ARCHITECTURE.md
docs/plans/2026-08-08_ARCHITECTURE_REMEDIATION_AND_PLATFORM_COMPLETION.md
HANDOVER.md
skills/greia-os-work/SKILL.md
```

For the current R7 work also read:

```text
docs/adr/0014-greia-identity-arm-parity-and-direct-graphics-direction.md
docs/adr/0019-platform-owned-activity-system-navigation.md
docs/adr/0020-runtime-neutral-input-profiles-and-controller-support.md
docs/product/ACTIVITY_SYSTEM_NAVIGATION.md
docs/product/ACTIVITY_INPUT_STANDARDS.md
docs/engineering/ENGINEERING_FOUNDATIONS.md
docs/engineering/GREIA_PERFORMANCE_BEST_PRACTICES.md
docs/reviews/2026-08-29_R7_ACTIVITY_BACKEND_INDEPENDENCE_AND_DISPLAY_SESSION_REVIEW.md
docs/reviews/2026-08-29_R7_R72_LEGACY_X_CONTAINMENT_INVENTORY.md
docs/reviews/2026-08-29_R7_R73_TRUSTED_CHROME_SOURCE_TRANCHE.md
docs/reviews/2026-08-29_R7_R73_ACTIVITY_CHROME_MIGRATION_TRANCHE.md
docs/reviews/2026-08-30_R7_R73_HOME_OVERLAY_POST_MODERNIZATION_CORRECTION.md
docs/testing/2026-08-29_R7_R72_LEGACY_X_CONTAINMENT_SOURCE_AND_ACER_ACCEPTANCE.md
docs/testing/2026-08-29_R7_R73_TRUSTED_SYSTEM_CHROME_SOURCE_AND_ACER_ACCEPTANCE.md
```

Work directly on current `main`, refresh before writes, preserve concurrent work, and do not use GitHub-hosted Actions unless the owner explicitly authorizes that specific execution.

No PASS claim may be generalized beyond the exact source/evidence lane that actually executed.

---

## 2. Release-preparation state

The ordinary-family release target is defined by:

```text
docs/release/GREIA_PUBLIC_RELEASE_READINESS.md
```

It deliberately distinguishes:

```text
Threshold A — public source repository
Threshold B — public technical preview
Threshold C — ordinary-family public release
```

The target is Threshold C: a normal parent/family can install, use, administer, update, back up and recover Greia without Linux/developer knowledge.

Do not mistake source-green development state for release certification. The release gate explicitly depends on closure of the blocking platform spine, including R7 and later architecture/package/backup/parent/update/recovery/certification phases.

Current ordinary-family disposition:

```text
NOT READY
```

The first incomplete blocking work remains R7. Do not jump ahead to release cosmetics or public packaging in a way that bypasses this architecture/evidence gate.

---

## 3. Activity modernization state

The catalogue modernization plan is:

```text
docs/plans/2026-08-29_R7_R73_ACTIVITY_MODERNIZATION.md
```

Its catalogue-wide pass is **COMPLETE**.

Historical closure at `e2b831da19a1ae706a8b675985f4191881a95321` recorded:

```text
Activity system chrome ownership audit: blockers=0
Activity backend-independence audit: blockers=0
make verify: PASS at that exact historical SHA
architecture/performance Activity pass: COMPLETE
```

The pass included real decomposition work and a final composition-root wave. Future Activity refactoring is evidence-driven/per-Activity only.

Do **not** restart a catalogue-wide monolith/refactor sweep merely because a later platform/Simulator source file changed.

Likewise, do not reintroduce Activity-owned Home rendering or hit-testing. Activities draw only their own content and retain renderer-neutral safe/protected geometry.

---

## 4. Current R7.3 Home issue and fix

After the Activity pass, manual Simulator inspection found that at least the Encyclopedia could run without a visibly presented Home control.

That is a platform defect, not intended behavior.

The Encyclopedia follows the desired architecture:

```text
activities/enciclopedia_greia/enciclopedia_app.py
```

- it presents with `pygame.display.flip()`;
- it avoids Greia's protected region for Activity pointer handling;
- it keeps its internal page Back control separate from system Home;
- it does not draw/hit-test the real Home control.

Commit:

```text
83738f737a41aec7c139b3a4a3363e746ba0f266
Simulator: make trusted Home overlay deterministic and fail loud
```

changed:

```text
src/greia_simulator/python_activity.py
```

The Simulator now imports the trusted Pygame chrome renderer explicitly and no longer silently suppresses exceptions while drawing Home after Activity presentation.

Architecture remains:

```text
Activity renders its own surface
        ↓
Greia Simulator trusted compatibility hook
        ↓
Home drawn last above Activity pixels
        ↓
Home input consumed by Greia
        ↓
Activity ends independently of Activity cooperation
```

This is Simulator/developer composition only. Production Legacy-X and final direct/compositor trust still require their own evidence.

---

## 5. Evidence correction after `83738f7`

The Activity modernization evidence at `e2b831da` remains valid for what it proved: the catalogue source migration, architecture audits and source gate at that SHA.

However, **Simulator Home runtime/visual evidence captured before `83738f7` is stale for the current Home presentation path** because the Simulator runtime source changed afterward.

Therefore the current state is:

```text
Activity modernization: COMPLETE
Simulator Home source fix: IMPLEMENTED
Simulator Home visual/runtime acceptance after fix: NOT YET RERUN
R7.3 current-source gate after fix: NOT YET RERUN
Acer physical R7.2/R7.3 acceptance: INCOMPLETE
```

The exact correction record is:

```text
docs/reviews/2026-08-30_R7_R73_HOME_OVERLAY_POST_MODERNIZATION_CORRECTION.md
```

Do not send the owner directly into Acer acceptance using `e2b831da` evidence.

---

## 6. Simulator `display.update(...)` hardening item

The current Simulator patch is correct for full `pygame.display.flip()` presentation, including the Encyclopedia.

A general compatibility hardening item remains in the `pygame.display.update(...)` wrapper:

- Greia draws trusted chrome before forwarding the Activity's update call;
- if the Activity supplies a dirty rectangle/list that excludes the Home corner, that original dirty update may not present the newly drawn Home pixels;
- therefore arbitrary partial-update Pygame presentation is not yet proven to preserve visible Home.

Resolve this in the platform-owned Simulator compatibility adapter, not in Activities.

The preferred behavior is to guarantee that the protected chrome region is included in the actual display update while preserving bounded/cheap presentation. Do not add a source-string test; protect the user-visible behavior at the narrowest meaningful layer if a regression test is warranted.

This issue is **not** the explanation for the Encyclopedia report because the Encyclopedia uses `pygame.display.flip()`.

---

## 7. Exact next step

The next bounded tranche is:

1. harden the Simulator `pygame.display.update(...)` path so partial updates cannot omit trusted Home;
2. run the focused Simulator/bootstrap tests on one exact new SHA;
3. visually exercise through the real Greia Simulator at minimum:
   - Encyclopedia;
   - Writing;
   - Painting;
   - one animated/game Activity;
4. verify Home is visible, Home input exits cleanly, and ordinary Activity interaction still works;
5. rerun the exact R7.3 source protocol on the same SHA:

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

6. only after that current-source gate is green, deploy that exact SHA to the reference Acer and execute:

```text
docs/testing/2026-08-29_R7_R72_LEGACY_X_CONTAINMENT_SOURCE_AND_ACER_ACCEPTANCE.md
docs/testing/2026-08-29_R7_R73_TRUSTED_SYSTEM_CHROME_SOURCE_AND_ACER_ACCEPTANCE.md
```

7. on physical `ACCEPTED`, continue R7.4 controller/system-input ownership and the remaining ADR-0014 direct/compositor evidence; on `INCOMPLETE`, do not bypass the missing lane.

---

## 8. Test-suite direction

The test count is not a success metric.

The owner explicitly wants brittle/redundant tests pruned where they slow refactoring without protecting product behavior. Continue that cleanup opportunistically.

Good candidates for removal/replacement:

```text
source-string/name presence assertions
implementation-shape scans
one test duplicating a stronger AST/project audit
historical tests that freeze file/function layout rather than contract
unrelated cross-subsystem assertions placed in the wrong test module
```

Keep meaningful tests around:

```text
security/trust and privilege boundaries
sandbox/device authority
lifecycle/forced return/cleanup
storage/profile/package/progression semantics
renderer-neutral Home geometry/action routing
backend-independence and ownership audits
real rollback/failure behavior
game/domain rules and important regressions
```

Do not add a test simply because a line was edited. Add or retain a test when it protects a behavior/invariant that would otherwise plausibly regress.

---

## 9. R7 architecture invariants

Preserve all of the following:

- Activity rendering remains backend-independent; ordinary Pygame/SDL is valid.
- Do not invent a Greia drawing API or Python framebuffer proxy.
- `DisplaySessionCoordinator` / `DisplaySessionBackend` remains the display/session polymorphic seam.
- `SystemChromeCoordinator` remains runtime/backend-neutral Home/Back authority.
- installed Home remains outside Activity rendering/input authority.
- protected system input is consumed before Activity delivery.
- ordinary Activities do not get raw `/dev/input` or `/dev/dri` authority.
- controller discovery/normalization remains platform-owned.
- trusted chrome stays tiny, bounded and event/invalidation driven.
- preserve direct high-rate SDL pointer/text paths where safe.
- preserve Activity-side precomposed opaque backdrops, converted surfaces, bounded caches, cached transforms and dirty/invalidation rendering.
- X11 is a migration baseline, not the target architecture.
- final architecture remains DRM/KMS-centered direct/appliance graphics; a minimal compositor is allowed only if measured evidence justifies it.
- exact hardware/performance claims require exact-source physical evidence.

---

## 10. Other current workstreams

### Encyclopedia visual work

E3 remains historically accepted at its recorded exact SHA/evidence lane. E4 is not the current blocking platform task and should not displace R7 verification.

### Voice production

New prerecorded speech remains authoring-time work through the canonical Voice Production Engine; do not grow parallel TTS/Whisper logic inside OS/Activity code.

### Microphone processing

The lightweight Greia-owned microphone route has separate physical acceptance evidence. Do not disturb it during R7 Home work.

---

## 11. Evidence vocabulary

Use exact labels:

```text
SOURCE / UNIT
SIMULATOR
VM / IMAGE
PHYSICAL ACER
PHYSICAL PI
DESKTOP VISUAL REVIEW
SIMULATOR VISUAL REVIEW
PHYSICAL VISUAL REVIEW
INCOMPLETE / NOT RUN
```

Never promote one lane into another.

Especially:

```text
Simulator Home visible != installed trusted sibling window cannot be covered
source tests green != Acer graphics/input accepted
old-SHA runtime evidence != new-SHA runtime acceptance
```

---

## 12. Current disposition

```text
Public ordinary-family release: NOT READY
Blocking phase: R7 OPEN
Activity modernization: COMPLETE
Post-modernization Simulator Home source fix: IMPLEMENTED
Post-fix Simulator visual/runtime gate: PENDING
Post-fix R7.3 source gate: PENDING
R7.2/R7.3 Acer physical gate: INCOMPLETE
Next implementation: harden partial display.update Home presentation
Next execution: current-SHA Simulator + source gate, then same-SHA Acer acceptance
```
