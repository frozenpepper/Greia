# Greia — Standalone Engineering Handover

**Date:** 2026-08-13  
**Version family:** `0.13.x` development  
**Repository:** `frozenpepper/Greia` (private)  
**Integration target:** `main`  
**Active branch:** `r7-direct-graphics`  
**Draft PR:** #4  
**Blocking architecture phase:** **R7 — Direct graphics/session architecture**

## 1. Resume order

Read:

1. `AGENTS.md`;
2. `README.md`;
3. `docs/DOCUMENTATION.md`;
4. `docs/architecture/GREIA_ARCHITECTURE.md`;
5. relevant accepted ADRs, especially ADR 0012–0018;
6. `docs/engineering/ENGINEERING_FOUNDATIONS.md`;
7. relevant `docs/product/*` requirement;
8. `docs/plans/2026-08-08_ARCHITECTURE_REMEDIATION_AND_PLATFORM_COMPLETION.md`;
9. this file;
10. `docs/agents/GREIA_AGENT_OPERATIONS.md`;
11. `skills/greia-activity-authoring/SKILL.md` for Activity work;
12. applicable `docs/testing/*` procedure.

GitHub is canonical. Resolve actual branch HEAD before editing/testing.

## 2. Hosted-execution rule

Do **not** use/query/trigger/rerun GitHub Actions without explicit repository-owner authorization for that specific hosted use. Repository source reads/writes/commits/PR discussion remain expected.

No GitHub Actions execution/query service was used in the 2026-08-13 consolidation.

## 3. Verification boundary

Last complete source gate genuinely executed:

```text
commit: 097f0281888a58f6f26425807ce99d9f35449313
provider-free tests: 232 / 232 PASS
project validation: PASS
bundled Activity validation: PASS
source/shell/footprint gate: PASS
```

Earlier focused evidence:

```text
DisplaySessionCoordinator fixture: 22 / 22 PASS
compositor-package pure logic:     14 / 14 PASS
serial fake-SDL/process:            8 / 8 PASS before later strengthening
```

Everything newer is **UNPROVEN** unless explicitly recorded otherwise. No new PASS is claimed for the UI/creative/consolidation source.

## 4. Repository consolidation completed

The repository now has one discoverable authority chain:

```text
AGENTS.md
  ↓
docs/DOCUMENTATION.md
  ↓
accepted ADRs + docs/engineering/ENGINEERING_FOUNDATIONS.md
  ↓
source/runtime contract owner
  ↓
HANDOVER.md for current evidence/state
```

The active plan now contains the missing 2026-08-13 consolidation progress entry; the former “plan append debt” is closed.

README is now a stable landing page rather than a duplicate handover. The Activity skill is a concise derived manual that points to canonical source/architecture owners instead of repeating broad architecture prose.

## 5. Permanent engineering contract

`AGENTS.md` and `docs/engineering/ENGINEERING_FOUNDATIONS.md` require:

- cohesive OOP domain structure around real concepts/invariants;
- purposeful polymorphism at genuine variation points;
- narrow typed interfaces/ABCs/protocols;
- composition by default; inheritance only for real substitutability;
- explicit dependency direction and lifecycle/resource ownership;
- no god classes or duplicated backend/runtime service stacks;
- bounded caches, histories, queues and transient state;
- low-allocation/hot-path discipline;
- useful public docstrings and discoverable extension points;
- tests at the narrowest meaningful layer;
- simple abstractions justified by real consumers rather than speculative framework growth.

Strong OOP does not mean maximizing class count.

## 6. Lightweight UI foundation — ADR 0018

Normative decision:

```text
docs/adr/0018-lightweight-ui-foundation.md
```

Greia UI vocabulary:

```text
Screen
  └── optional Overlay / Sheet
        └── Panel / Card / Collection
              └── Control
```

A child-visible “folder” is a semantic `Collection`, never a Linux path. Greia does not introduce a conventional desktop/window-manager model.

Renderer-neutral source:

```text
src/greia_platform/ui_core.py
```

Current contracts:

```text
UiEventResult
UiSurface
Screen
Overlay
Control
Collection[T]
GridPage
PagedGrid
BoundedCache[K,V]
InvalidationTracker
SurfaceNavigator
```

`ui_core.py` imports no Pygame.

## 7. Current Pygame helper consolidation

Current single implementation remains:

```text
src/greia_platform/activity_ui.py
```

Platform-wide import name for new shared Pygame consumers:

```text
src/greia_platform/pygame_ui.py
```

`pygame_ui.py` re-exports the existing implementation; there is **no duplicate helper implementation**. Existing Writing/Painting imports therefore remain stable.

After focused/current tests pass, the compatibility direction may be flipped mechanically so `pygame_ui.py` physically owns the renderer implementation and `activity_ui.py` becomes the historical Activity compatibility façade. Do not combine that rename with new framework behavior.

The current icon cache is hard-bounded through `ui_core.BoundedCache`.

## 8. UI regression source

Committed source includes:

```text
tests/test_ui_core.py
tests/test_ui_core_lifecycle.py
tests/test_activity_ui.py
```

Coverage includes polymorphic Screen/Overlay lifecycle/event routing, modal/non-modal behavior, bounded overlay depth, semantic Collection behavior, deterministic paging, bounded LRU caching, cache replacement edge cases, invalidation state, child metrics and color helpers.

These tests are unexecuted in the current evidence boundary.

## 9. Phase-0 Writing and Painting

Mandatory product contract:

```text
docs/product/PHASE0_CORE_CREATION_ACTIVITIES.md
```

Stable IDs:

```text
org.greia.writing
org.greia.painting
```

Both source tranches exist and remain execution/hardware-unproven.

Writing includes large Unicode text, wrapping/caret/navigation, bounded inverse-edit undo, visual gallery and debounced profile-scoped UTF-8 saving.

Painting includes a large raster canvas, fixed cheerful palette, three brush sizes, eraser, bounded stroke undo, visual gallery and debounced profile-scoped PNG saving.

No Linux file-management workflow is exposed.

## 10. Safe UI migration boundary

Existing Shell and installer still contain local/procedural UI code. They were deliberately not big-bang rewritten before the new common tests execute.

After focused/current PASS, migrate incrementally:

1. Shell-local grid paging → `ui_core.PagedGrid`;
2. Shell icon/font caches → explicit bounded cache ownership;
3. installer icon/font caches → same bounded resource model;
4. installer font construction out of per-frame draw path;
5. Shell modes → concrete `Screen` / `Overlay` implementations;
6. static Shell loop → invalidation/event-driven idle rendering, with visual/input/performance acceptance.

Do not rewrite all Shell/installer UI in one tranche.

## 11. R7 remains blocking

Production graphics/session state remains:

```text
installed path:         Xorg + xinit compatibility
status:                 PROVISIONAL
production compositor:  none selected
serial direct DRM:      evidence candidate only
```

Do not make `ActivitySupervisor` DRM owner, grant ordinary Activities raw DRM/input authority, remove current X-compatibility concessions before a replacement is accepted, or select a compositor without evidence.

Relevant evidence protocol:

```text
docs/testing/2026-08-09_R7_EXTERNAL_LINUX_EVIDENCE_EXECUTION.md
```

## 12. Developer remote path

Developer-only profile and client:

```text
build/profiles/modern-amd64-dev.toml
tools/greia_remote.py
```

Trust separation remains:

```text
/opt/greia-os/activities                 BUILT_IN
/var/lib/greia-developer/activities      DEVELOPER_UNSIGNED
```

Developer-remote tests/image/physical behavior remain unexecuted/unproven.

## 13. Exact next source verification

On an owner-controlled current Linux checkout:

```bash
PYTHONPATH=src python3 -m unittest \
  tests.test_ui_core \
  tests.test_ui_core_lifecycle \
  tests.test_activity_ui \
  tests.test_core_creation_activities \
  tests.test_activity_theme_access \
  -v

PYTHONPATH=src python3 tools/validate_activity.py activities/writing
PYTHONPATH=src python3 tools/validate_activity.py activities/painting

PYTHONPATH=src python3 -m unittest discover \
  -s tests \
  -p 'test_developer_remote.py' \
  -v

make verify
```

Stop on first real failure and preserve exact stdout/stderr. Do not weaken tests/contracts to manufacture PASS.

Only after this gate should existing Shell/installer UI behavior migrate onto the common primitives.

## 14. Exact next R7 evidence

On the approved disposable/root-safe Linux environment:

```bash
SOURCE_SHA="$(git rev-parse HEAD)"
RUN_ROOT="/var/tmp/greia-r7-${SOURCE_SHA}"
python3 tools/r7_local_evidence.py --run-root "$RUN_ROOT" --plan-only
sudo -E python3 tools/r7_local_evidence.py --run-root "$RUN_ROOT"
```

Preserve first failure and the complete run root. Do not rerun merely to manufacture PASS.

## 15. Invariants

- no visible Linux UI in normal child operation;
- explicit Greia child profiles;
- Activity remains runtime-neutral;
- progression/rewards remain platform-owned;
- child state remains portable and profile-scoped;
- Acer remains the extreme resource floor;
- ARM is co-equal, not a later port;
- no unauthorized hosted execution;
- no desktop/window-manager architecture;
- no child-facing filesystem paths;
- strong OOP/polymorphic seams with composition-first design;
- explicit bounded resources and cleanup;
- architecture/docs remain understandable without chat history;
- source/VM/physical evidence boundaries remain honest.
