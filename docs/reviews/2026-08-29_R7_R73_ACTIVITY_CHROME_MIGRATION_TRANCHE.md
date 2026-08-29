# R7.3 Activity System-Chrome Ownership Migration Tranche

**Date:** 2026-08-29  
**Status:** SOURCE INTEGRATED / EXECUTION PENDING  
**Phase:** R7.3 — trusted Greia Home/Back authority  
**Authority:** subordinate to ADR 0014, ADR 0019, ADR 0020 and `docs/plans/2026-08-08_ARCHITECTURE_REMEDIATION_AND_PLATFORM_COMPLETION.md`  
**Continuation gate:** `docs/testing/2026-08-29_R7_R73_TRUSTED_SYSTEM_CHROME_SOURCE_AND_ACER_ACCEPTANCE.md`

## 1. Purpose

This review records the R7.3 tranche that moves first-party Activity source away from the retired cooperative Home implementation after the trusted launcher/simulator Home boundary was introduced.

The architectural distinction is deliberate:

```text
Activity owns
  drawing/gameplay/text/pointer behavior
  Activity-local navigation
  graceful reaction to activity_stop_requested()
  safe/protected layout geometry

Greia platform owns
  real Home/Back rendering
  protected Home/Back input
  Activity stop/forced-return authority
  display/session backend mechanics
```

The migration does **not** create a Greia drawing API and does **not** proxy Activity pixels. Ordinary SDL/Pygame rendering remains the Activity rendering abstraction.

## 2. Shared canvas authority correction

`src/greia_platform/pygame_canvas.py` previously preserved correct protected-region geometry but also let `PygameReferenceCanvas.present()` draw the nominally trusted Home directly into the Activity target surface.

That rendering responsibility is now removed.

Current contract:

- `ActivitySystemChromeLayout` remains used to reserve the protected region;
- `ActivityViewport` / safe UI geometry remains available to Activity authors;
- normal reference-canvas scaling, clipping and pointer mapping remain unchanged;
- Activity-local pointer rendering remains available;
- `PygameReferenceCanvas.present()` no longer imports or invokes `draw_system_chrome_overlay`;
- the old `system_chrome=` keyword remains temporarily accepted for compatibility, defaults to `False`, and is ignored;
- new Activity code must not use that compatibility keyword.

Commit:

```text
44f92f97273eab57c4d5eaccb6bc39225f4628de
R7: remove trusted chrome rendering from Activity canvas
```

This preserves low-resource direct SDL presentation: no full-screen copy, frame broker, extra Pygame renderer process or high-rate IPC was introduced.

## 3. Simulator compatibility authority

Removing Activity-side Home does not remove Simulator navigation.

`src/greia_simulator/python_activity.py` already implements the Simulator's compatibility Home at the trusted bootstrap layer by:

- wrapping Pygame display presentation so the platform overlay is applied after Activity drawing;
- wrapping event retrieval so pointer events in the protected Home hitbox are consumed before Activity delivery;
- deriving the hitbox from `ActivitySystemChromeLayout`.

Therefore Simulator Home remains outside Activity source even while the Activity's own helper imports/calls disappear.

This Simulator compatibility renderer is not evidence for the physical Legacy-X backend; it only preserves the same authority direction for Simulator acceptance.

## 4. Activity migration waves completed in this tranche

The following representative Activities were migrated without gameplay or presentation redesign:

```text
activities/writing/main.py
activities/painting/main.py
activities/labirinto_magico/maze_app.py
activities/volo_draghetto/dragon_app.py
activities/shape_garden/main.py
activities/storie_della_mia_voce/voice_app.py
```

### Writing

Removed only:

- `draw_system_chrome_overlay` import;
- `is_home_clicked` import;
- Activity-side Home click branch;
- Activity-side Home drawing call.

Preserved:

- `activity_stop_requested()` lifecycle reaction;
- final save/autosave behavior;
- ESC convenience behavior;
- direct Pygame text input;
- `activity_toolbar_button()` / `activity_content_rect()` safe geometry;
- typography, undo, storage and caching behavior.

Commit:

```text
4e0e5a4e3f1a34dd2d5c4f55c1b99384f23b3ee7
R7: remove Activity-owned Home from Writing
```

### Painting

Removed only:

- the same retired Home imports;
- Activity-side Home click handling;
- Activity-side Home draw.

Preserved:

- high-rate Pygame drawing path;
- stroke batching and bounded history;
- cached/scaled UI resources;
- autosave/final save;
- ESC convenience;
- `ChildUiMetrics` safe content/toolbar geometry;
- Activity-local pointer.

Commit:

```text
09f8e47a6375cea0f9bac7df51dfd65106a0776b
R7: remove Activity-owned Home from Painting
```

### Labirinto Magico

Removed only the `is_home_clicked` import and Home branch. Preserved `activity_viewport_for_surface()` protected-region filtering, canvas mapping, movement, completion, storage and renderer behavior.

Commit:

```text
a713bdcf4315d848a3e82e78b0c9b96c77d0c322
R7: remove Activity-owned Home from Labyrinth
```

### Il Volo del Draghetto

Removed only the `is_home_clicked` import and Home branch. Preserved protected-region input filtering, continuous pointer/keyboard behavior, canvas rendering, world update, storage and audio.

Commit:

```text
29680a2b588476b08e191adb7d4bd38341635dbd
R7: remove Activity-owned Home from Dragon Flight
```

### Shape Garden

Removed only the `is_home_clicked` import and Home branch. Preserved safe viewport filtering, scene rendering, particles, actor animation and direct pointer behavior.

Commit:

```text
9083335675aa4d3898ce2afcbef94db49b469167
R7: remove Activity-owned Home from Shape Garden
```

### Storie della Mia Voce

Removed the two retired Home helpers and updated the lifecycle comment so Shell navigation is explicitly Greia-platform-owned.

Preserved:

- `get_audio_capture_device()` / `get_sdl_capture_device()` route consumption;
- recorder lifecycle;
- playback;
- storage/events;
- Activity-internal Back controls;
- microphone fallback semantics;
- platform-stop cleanup.

Commit:

```text
0663c1ced021d44e716c389bad96170148c84133
R7: remove Activity-owned Home from Voice Stories
```

## 5. Patch review result

The GitHub commit patches for Writing, Painting, Labyrinth, Dragon Flight, Shape Garden and Voice Stories were inspected after persistence.

The patches confirm the intended migration shape:

- retired Home imports removed;
- retired Home branches/calls removed;
- no gameplay mechanics rewritten;
- no Activity display backend introduced;
- no raw device authority introduced;
- no new frame/input proxy introduced;
- protected/safe geometry retained where it already existed.

This is a **source patch review**, not executed runtime evidence.

## 6. Catalogue-wide ownership audit

Private GitHub code search is not sufficient to prove catalogue-wide zero debt: the direct search returned `incomplete_results=true`.

A repository-local structured audit now owns that evidence instead:

```text
tools/audit_activity_system_chrome_ownership.py
```

Commit:

```text
646d6eaa7586cce1c866d47878f217b8ad887033
R7: add Activity system chrome ownership audit
```

The audit uses Python AST parsing and reports:

```text
legacy_helper_import
legacy_helper_call
legacy_canvas_chrome_request
```

for:

- `draw_system_chrome_overlay`;
- `is_home_clicked`;
- `PygameReferenceCanvas.present(system_chrome=...)`.

Default mode is inventory-only. R7.3 acceptance now requires:

```bash
PYTHONPATH=src python3 tools/audit_activity_system_chrome_ownership.py --strict
```

with exact required summary:

```text
Activity system chrome ownership audit: blockers=0
```

Unit source for the audit:

```text
tests/test_activity_system_chrome_audit.py
```

Commits:

```text
1c87eee7c4de21971b46e894a139a20fd0f430c1
R7: test Activity system chrome ownership audit

872f402962a68edae124c7fe1a8869f228881573
R7: make chrome audit test import deterministic
```

The second commit registers the dynamically loaded audit module in `sys.modules` before execution so dataclass/postponed-annotation resolution is deterministic and the test does not fail because of the test loader itself.

## 7. Migration regression contract

Current regression source:

```text
tests/test_r7_first_wave_activity_trusted_chrome_migration.py
```

It now pins:

- all six migrated exemplars contain no retired Home helper use;
- all six retain platform-stop reaction;
- Writing/Painting retain safe toolbar/content geometry;
- Labyrinth/Dragon/Shape Garden retain protected-region viewport use;
- `PygameReferenceCanvas` retains protected geometry but does not render Home;
- the Simulator bootstrap still owns its compatibility Home above Activity code.

Relevant commits:

```text
c67a03d21fdbb5d747240b13a7bbce18aa1188b4
349c480815992a6fe42921be97b5cddc940772be
38613a6dd212d4240c7bf279f58012cddc046928
```

## 8. Contributor contract update

`skills/greia-activity-authoring/SKILL.md` now explicitly forbids new Activity code from:

- importing/calling `draw_system_chrome_overlay`;
- importing/calling `is_home_clicked`;
- requesting `PygameReferenceCanvas.present(system_chrome=...)`.

It explicitly permits and encourages renderer-neutral protected/safe geometry such as:

- `ActivitySystemChromeLayout`;
- `ActivityViewport`;
- `activity_safe_rect()`;
- `activity_content_rect()`;
- `activity_toolbar_button()`.

Commit:

```text
721bd6cf98b37ba93fdd8cb29858b6467f009fba
Docs: forbid Activity-owned system chrome helpers
```

## 9. R7.3 acceptance protocol update

`docs/testing/2026-08-29_R7_R73_TRUSTED_SYSTEM_CHROME_SOURCE_AND_ACER_ACCEPTANCE.md` now requires both:

```bash
PYTHONPATH=src python3 tools/audit_activity_backend_independence.py activities
PYTHONPATH=src python3 tools/audit_activity_system_chrome_ownership.py --strict
```

and requires zero blockers from both before `make verify` and physical deployment.

Commit:

```text
8f0d62d425b1ec205e629eb02ee49c69b2debd18
Docs: require zero Activity chrome ownership for R7.3
```

The protocol continues to require exact-SHA physical Acer evidence for:

- Writing typing/edit/save/Home;
- Painting sustained drawing/save/Home;
- hostile full-screen non-cooperative Activity;
- bounded forced return;
- 10/10 hostile launch/Home/return cycles;
- crash cleanup;
- next-launch recovery;
- CPU/RSS/latency/performance sanity;
- no child-visible Linux/Xorg surface.

## 10. Evidence status

### Implemented and persisted

The source changes, tests, scanner, contributor rule, protocol and handover are committed on `main`.

Current continuation handover commit at the end of this migration tranche:

```text
7eb454bc9026224f500c42c9e4937478608b974c
Handover: advance R7.3 Activity chrome migration state
```

### Patch-reviewed

The representative Activity commits were inspected and their diffs are authority-only as described above.

### NOT executed in this connector-only tranche

No claim is made for:

- focused R7.3 unit-suite PASS;
- `tools/audit_activity_backend_independence.py` current-head PASS;
- `tools/audit_activity_system_chrome_ownership.py --strict` current-head PASS;
- `make verify` current-head PASS;
- final Simulator acceptance for the six modified Activities;
- native Legacy-X trusted-window execution;
- current-head Acer Writing/Painting PASS;
- hostile fixture physical PASS;
- 10/10 hostile-cycle PASS;
- physical performance PASS.

Therefore **catalogue-wide zero retired-Home debt is not yet claimed**. The six representative migrations and source scanner are not a substitute for actually executing the strict audit.

## 11. Exact next gate

On an owner-controlled full checkout of current `main`:

```text
1. record exact SHA + clean status
2. run the focused R7.3 suite from the acceptance protocol
3. run Activity backend audit; require blockers=0
4. run Activity system-chrome audit --strict; require blockers=0
5. if strict chrome audit reports callers:
     migrate exactly those callers
     preserve gameplay/rendering/performance/safe geometry
     commit new SHA
     restart from step 1
6. run make verify
7. run final Greia Simulator acceptance for runtime-relevant modified Activities
8. only when source is green, deploy that exact SHA to reference Acer
9. complete R7.2 prerequisite evidence plus R7.3 Writing/Painting/hostile/crash/performance gate
10. return ACCEPTED / REJECTED / INCOMPLETE honestly
```

Do **not** promote the audit rule into the normal Activity validator until step 4 proves zero catalogue callers.

Do **not** delete the temporary `system_chrome` compatibility parameter until the audit proves zero callers.

Do **not** delete the canonical Pygame Home renderer from `activity_ui.py` while the trusted Simulator bootstrap still uses it; if that renderer is later moved/renamed, migrate the trusted Simulator layer first.

## 12. Active-plan synchronization note

The active architecture plan requires append-only progress history. In the current connector-only environment the available GitHub write action replaces an entire file; the plan is large enough that bounded reads do not provide a safe byte-for-byte reconstruction path.

Therefore this tranche deliberately does **not** risk rewriting/truncating the active plan merely to satisfy the append checkbox.

The earlier trusted-chrome source progress entry remains preserved in:

```text
docs/reviews/2026-08-29_R7_R73_TRUSTED_CHROME_SOURCE_TRANCHE.md
```

This review is the exact additional Activity-migration progress record. At the next owner-controlled full checkout, append the material R7.3 progress to the active plan using normal local Git tooling **before further R7 source implementation**, then keep the plan append-only.

This documentation gap does not change runtime authority and must not be hidden as a completed plan update.

## 13. Decision after this tranche

The correct next action is **evidence execution**, not another speculative display abstraction or broad blind Activity rewrite.

If the strict audit is zero and the focused/source gates pass, proceed to physical R7.3 acceptance. If the strict audit returns remaining Activity callers, use its exact file/line findings to finish the catalogue migration first.

Only after R7.3 acceptance should the project:

1. promote zero Activity Home ownership into normal validation;
2. remove the compatibility `system_chrome` canvas argument once zero callers are proven;
3. continue R7.4 platform-owned controller/system-input authority;
4. continue ADR-0014 direct/compositor backend comparison and physical evidence.
