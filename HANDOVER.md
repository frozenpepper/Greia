# Greia — Standalone Engineering Handover

**Date:** 2026-08-13  
**Version family:** `0.13.x` development  
**Repository:** `frozenpepper/Greia` (private)  
**Integration target:** `main`  
**Active branch:** `r7-direct-graphics`  
**Draft PR:** #4 — `R7: direct graphics/session migration and KMSDRM evidence path`  
**Blocking architecture phase:** **R7 — Direct graphics/session architecture**

---

## 1. Mandatory resume order

Read before substantive work:

1. `AGENTS.md`;
2. `README.md`;
3. `docs/DOCUMENTATION.md`;
4. `docs/architecture/GREIA_ARCHITECTURE.md`;
5. accepted ADRs relevant to the task, especially ADR 0012–0018;
6. **`docs/adr/0018-lightweight-ui-foundation.md`** for any Shell/installer/parent/native-UI work;
7. **`docs/engineering/ENGINEERING_FOUNDATIONS.md`** for repository-wide OOP/polymorphism/maintainability/performance rules;
8. `docs/product/PHASE0_CORE_CREATION_ACTIVITIES.md`;
9. `docs/plans/2026-08-08_ARCHITECTURE_REMEDIATION_AND_PLATFORM_COMPLETION.md`;
10. this `HANDOVER.md`;
11. `docs/agents/GREIA_AGENT_OPERATIONS.md`;
12. `skills/greia-activity-authoring/SKILL.md` for Activity work;
13. phase-specific testing/review documents referenced below.

GitHub is canonical. Resolve actual branch HEAD before editing/testing. Do not infer current state from a chat SHA.

---

## 2. Permanent hosted-execution boundary

**Do not use the GitHub Actions execution/query surface without explicit repository-owner authorization for that specific hosted use.**

Without that authorization do not:

- trigger/rerun/dispatch hosted workflows;
- add automatic hosted triggers;
- query Actions runs/status/jobs/steps/logs/artifacts;
- download Actions artifacts.

Repository source reads/writes/commits/PR discussion remain expected.

No GitHub Actions execution/query service was used in the 2026-08-13 UI-foundation tranche.

---

## 3. Verification boundary — do not overclaim

Last complete source gate genuinely executed remains:

```text
commit: 097f0281888a58f6f26425807ce99d9f35449313
provider-free tests: 232 / 232 PASS
project validation: PASS
bundled Activity validation: PASS
source/shell/footprint gate: PASS
```

Earlier focused evidence genuinely executed:

```text
DisplaySessionCoordinator isolated fixture: 22 / 22 PASS
compositor-package pure-logic fixture:       14 / 14 PASS
serial fake-SDL/process fixture:              8 / 8 PASS
```

The serial 8/8 result predates later strengthening.

Everything newer remains **UNPROVEN** unless explicitly recorded otherwise.

The 2026-08-13 UI-foundation tranche did **not** execute:

```text
tests/test_ui_core.py
tests/test_activity_ui.py after shared-cache change
current full make verify
Shell migration
installer migration
idle/invalidation physical measurements
```

No new PASS count is claimed.

---

## 4. Permanent open-source engineering architecture

`AGENTS.md` now makes this a hard repository requirement:

- strong object-oriented foundations around stable domain concepts;
- purposeful polymorphism at genuine variation points;
- narrow typed interfaces/ABCs/protocols;
- composition preferred over inheritance;
- inheritance only for real substitutability;
- explicit dependency injection at architecture seams;
- explicit lifecycle/resource ownership;
- bounded caches, histories, queues, surfaces and transient state;
- no god classes or giant cross-domain managers;
- no repeated backend/type/runtime switch trees when a polymorphic seam is appropriate;
- useful docstrings for public architectural classes and extension points;
- code/module organization that outside contributors can understand without chat history;
- performance treated as architecture correctness, not late optimization.

Detailed guidance:

```text
docs/engineering/ENGINEERING_FOUNDATIONS.md
```

This guidance does **not** mean “everything must be a class.” Small pure calculations remain functions; abstractions must own real concepts, invariants, lifecycle, resource ownership, duplication or extension seams.

---

## 5. Accepted lightweight UI architecture — ADR 0018

Normative decision:

```text
docs/adr/0018-lightweight-ui-foundation.md
```

Greia deliberately uses:

```text
Screen
  -> optional Overlay / Sheet
      -> Panel / Card / Collection
          -> Control
```

Greia deliberately does **not** use a normal desktop/window metaphor.

Do not add:

- arbitrary draggable/resizable windows;
- minimize/maximize state;
- taskbars/docks;
- arbitrary z-order/window-manager behavior;
- filesystem Explorer/Finder concepts;
- generic retained widget/DOM/scene frameworks without a new evidence-backed ADR.

### Collection semantics

`Collection` is the common child-facing grouping abstraction.

A Collection may visually appear as a folder, shelf, box, bag, book, etc., but it is a semantic ordered group of Greia object references and **never a Linux filesystem path**.

---

## 6. UI core source now implemented

New renderer-neutral module:

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

Important semantics:

- `Screen` is one full logical Greia UI surface;
- `Overlay` is bounded transient/modal UI over a Screen;
- `Control` is a small polymorphic interactive element owned by a surface;
- `Collection` is immutable semantic grouping and rejects filesystem-shaped IDs;
- `PagedGrid` computes visible pages deterministically without renderer dependency;
- `BoundedCache` is hard-bounded LRU storage with optional eviction cleanup;
- `InvalidationTracker` separates static dirty rendering from explicit animation;
- `SurfaceNavigator` owns exactly one Screen plus a bounded Overlay stack and routes events polymorphically.

`ui_core.py` imports no Pygame. This is intentional so the semantics survive future renderer/runtime choices.

---

## 7. Current Pygame helper layer

Current first-party Python renderer helper remains:

```text
src/greia_platform/activity_ui.py
```

It still exposes the current Activity-facing helpers:

```text
ChildUiMetrics
load_icon
clear_icon_cache
draw_icon_button
draw_plus_symbol
draw_grid_symbol
draw_undo_symbol
draw_eraser_symbol
mix
```

The icon cache now uses shared `ui_core.BoundedCache` with a hard 64-entry bound.

Writing/Painting continue importing the same existing `activity_ui` API. No deliberate author-facing breaking rename was introduced in this tranche.

Future Shell/installer/native-Pygame sharing should promote renderer-specific primitives under a neutral implementation-layer name only in one coherent migration, not through a half-moved dependency graph.

---

## 8. UI-core regression source

Added:

```text
tests/test_ui_core.py
```

It covers:

- polymorphic Screen/Overlay lifecycle and event routing;
- bounded overlay-stack behavior;
- immutable semantic Collection behavior;
- rejection of filesystem-shaped Collection IDs;
- deterministic PagedGrid page/navigation behavior;
- bounded LRU cache behavior;
- invalidation/animation redraw-state behavior.

Existing:

```text
tests/test_activity_ui.py
```

continues covering 1024×600 child metrics and color helper behavior.

These tests are committed but unexecuted in the current checkout/evidence boundary.

---

## 9. Performance rules now part of UI correctness

For the Acer-class resource floor:

- caches must have explicit bounds;
- images/fonts/scaled assets are reused rather than recreated per frame;
- ordinary controls should draw directly to the owning surface instead of each owning a backing Surface;
- only visible Collection items/pages should be laid out/rendered;
- histories/animations/transient pools need explicit bounds;
- avoid per-frame filesystem IO, image decoding, font construction and large scaling;
- static Shell screens should migrate toward invalidation/event-driven redraw rather than continuously repainting unchanged content;
- normal Shell animation should stay around 30 Hz unless measurement demonstrates a need for more.

Do not optimize by sacrificing input responsiveness or correctness. Measure on low-end hardware before certification.

---

## 10. Existing Shell/installer state relative to the new UI core

The existing Shell already has useful concepts such as paged grids, hit targets, icon/font caching and explicit modes, but they remain implemented locally/procedurally in `src/greia_launcher/main.py`.

The installer still owns local button/layout/font/icon code in `src/greia_installer/main.py`.

They were **not** big-bang rewritten in this tranche because the new UI-core regression source has not executed yet.

Safe migration order after focused PASS:

1. migrate Shell paging to shared `PagedGrid`;
2. migrate Shell icon/font dictionaries to explicit `BoundedCache` ownership;
3. migrate installer icon/font caches to the same bounded resource model;
4. extract real Shell modes incrementally into concrete `Screen`/`Overlay` subclasses;
5. only then introduce invalidation-driven idle redraw with focused tests and physical measurement.

Do not rewrite all Shell UI at once.

---

## 11. Mandatory Phase-0 creative Activities

Product contract:

```text
docs/product/PHASE0_CORE_CREATION_ACTIVITIES.md
```

Current source identities:

```text
org.greia.writing
org.greia.painting
```

Both are source-implemented first tranches and remain unexecuted/hardware-unproven.

Writing currently includes large Unicode text, caret/navigation/wrapping, bounded inverse-edit undo, visual gallery and debounced profile-scoped UTF-8 saving.

Painting currently includes large raster canvas, ten colors, three brush sizes, eraser, bounded stroke undo, gallery and debounced profile-scoped PNG saving.

Neither may be considered Phase-0 product-complete until real 1024×600 visual/input/storage/lifecycle and Acer resource acceptance executes.

---

## 12. R7 remains blocking

Current production graphics/session state:

```text
installed path:           Xorg + xinit compatibility
status:                   PROVISIONAL
production compositor:    none selected
serial direct DRM path:   evidence candidate only
```

Do not:

- make `ActivitySupervisor` the DRM master;
- grant ordinary Activities raw DRM/input ownership;
- remove current X-compatible sandbox concessions before a replacement is accepted;
- select a compositor without evidence;
- claim physical Acer/Pi display acceptance without physical evidence.

Relevant R7 tools remain under:

```text
src/greia_platform/direct_graphics_probe.py
src/greia_platform/kmsdrm_acceptance.py
src/greia_platform/kmsdrm_serial_handoff.py
tools/r7_local_evidence.py
tools/r7_qemu_kmsdrm_acceptance.py
tools/r7_qemu_kmsdrm_handoff_acceptance.py
```

---

## 13. Developer remote path

Developer-only profile:

```text
build/profiles/modern-amd64-dev.toml
```

Remote client:

```text
tools/greia_remote.py
```

Trust separation remains:

```text
/opt/greia-os/activities                 BUILT_IN
/var/lib/greia-developer/activities      DEVELOPER_UNSIGNED
```

No physical remote-control acceptance is currently claimed.

The live graphical installer remote provisioner exists but remains not wired into the canonical installer builder; first-time remote USB installation is therefore not claimed operational.

---

## 14. Exact next source verification step

On owner-controlled Linux at actual branch HEAD:

```bash
PYTHONPATH=src python3 -m unittest \
  tests.test_ui_core \
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

Stop on the first real failure and preserve exact stdout/stderr. Do not weaken a contract/test to manufacture PASS.

Only after that source gate should Shell/installer UI migration proceed.

---

## 15. Exact next R7 evidence step

Protocol:

```text
docs/testing/2026-08-09_R7_EXTERNAL_LINUX_EVIDENCE_EXECUTION.md
```

On the approved disposable/root-safe Linux environment:

```bash
SOURCE_SHA="$(git rev-parse HEAD)"
RUN_ROOT="/var/tmp/greia-r7-${SOURCE_SHA}"
python3 tools/r7_local_evidence.py --run-root "$RUN_ROOT" --plan-only
sudo -E python3 tools/r7_local_evidence.py --run-root "$RUN_ROOT"
```

First failure is authoritative for an attempt. Preserve the run root and do not rerun merely to manufacture PASS.

---

## 16. Active-plan append debt

The active remediation plan remains append-only:

```text
docs/plans/2026-08-08_ARCHITECTURE_REMEDIATION_AND_PLATFORM_COMPLETION.md
```

This repository-access path still lacks a safe line-append operation for the large historical plan. Do not reconstruct/replace the full history merely to insert one paragraph.

The next authenticated local-checkout tranche must append progress entries for:

- the 2026-08-10 creative-source tranche if still absent;
- the 2026-08-13 lightweight UI-foundation tranche.

This is explicit continuity/documentation debt, not hidden implementation completion.

---

## 17. Invariants to preserve

- no visible Linux UI in normal child operation;
- explicit child profile selection;
- Activity remains runtime-neutral;
- global progression remains platform-owned;
- portable profile-scoped child state;
- first-generation Acer is the extreme resource floor;
- ARM64 is co-equal, not a later port;
- no unauthorized GitHub-hosted execution;
- no generic desktop/window-manager architecture;
- no child-facing filesystem folders/paths;
- strong OOP/polymorphic architecture at genuine extension seams;
- composition over unnecessary inheritance;
- explicit bounded resources and cleanup;
- code/documentation must remain understandable to outside contributors;
- R7 evidence boundaries remain honest.
