# Greia Core Creation Activities — Source Tranche Review — 2026-08-10

**Scope:** first source implementation of mandatory Phase-0 Writing and Painting Activities, first shared child-Activity UI primitives, least-privilege theme-read correction, and durability/performance hardening  
**Status:** SOURCE IMPLEMENTED / STATICALLY REVIEWED / EXECUTION UNPROVEN  
**Blocking architecture phase remains:** R7 direct graphics/session  
**Hardware acceptance:** NOT RUN

Canonical product requirement:

```text
docs/product/PHASE0_CORE_CREATION_ACTIVITIES.md
```

---

## 1. Why this tranche exists

The first child-ready Greia image must be useful for creating as well as consuming content. The accepted Phase-0 baseline therefore includes:

- `org.greia.writing` — simple large-text child writing;
- `org.greia.painting` — simple child painting/drawing.

This source work proceeds in parallel with R7 only because it consumes already-established Activity/lifecycle/Storage contracts. It does not select or alter the production display backend and does not satisfy any R7 hardware/evidence closure criterion.

---

## 2. Writing source

```text
activities/writing/activity.toml
activities/writing/main.py
```

Implemented source behavior includes:

- Python/Pygame API `0.1`;
- stable ID `org.greia.writing`;
- no privileged permission request;
- required `display`, `keyboard`, `pointer`; optional `touch`;
- fullscreen editing;
- large default text at the 1024×600 reference scale;
- Unicode `TEXTINPUT`;
- multiline text, caret placement/navigation, wrapping and scroll;
- visual gallery and New;
- debounced automatic saves plus transition/exit save attempts;
- child-initiated Close/New/gallery/document-switch transitions proceed only after a successful required save;
- UTF-8 Greia private files and a bounded logical index;
- rollback attempt if empty-file creation succeeds but logical-index creation fails;
- no filesystem browser/file-dialog abstraction;
- no formatting-ribbon/desktop-office scope;
- no silent eviction of older child documents on library pressure.

### Writing undo memory model

The initial full-document-snapshot idea was rejected during static review as technically bounded but inappropriate for the ~768 MiB reference class.

Current undo stores inverse edit operations containing only:

```text
start position
removed fragment
inserted fragment
cursor before/after
```

Bounds:

```text
recent operations:          128 maximum
total retained edit payload: 65,536 changed characters maximum
```

An oversized single paste/edit remains valid document content but is deliberately not retained as an undo payload. A one-character edit on a 50,000-character document therefore retains one changed character, not another 50,000-character snapshot.

### Writing creation transaction

New-document creation writes the empty private UTF-8 file before adding the logical index record. If index creation fails, Writing attempts to delete the just-created private file before propagating failure, reducing hidden quota leakage from a partial New operation.

### Writing caret boundary

Soft wrapping can create a logical cursor index that is both the end of one visual line and the start of the next. Writing assigns that boundary to the later visual line and renders the caret once, avoiding ambiguous/double caret ownership.

---

## 3. Painting source

```text
activities/painting/activity.toml
activities/painting/main.py
```

Implemented source behavior includes:

- Python/Pygame API `0.1`;
- stable ID `org.greia.painting`;
- no privileged permission request;
- required `display`, `pointer`; optional `touch`;
- large fullscreen raster canvas;
- ten fixed colors, three brush sizes, eraser;
- visual gallery and New;
- pointer-point decimation;
- debounced PNG save through Greia Storage;
- child-initiated Close/New/gallery/painting-switch transitions proceed only after a successful required save;
- no per-frame PNG encoding or durable write;
- no filesystem browser;
- no silent eviction of older child paintings when the bounded library is full.

### Painting undo/vector memory model

Painting does not retain unlimited full-canvas undo snapshots.

Current bounds:

```text
recent undo stroke chunks: 24 maximum
sampled points/chunk:      2,048 maximum
```

An exceptionally long continuous mouse-down gesture is split into bounded continuation chunks rather than allowing one Python point list to grow indefinitely. When the 24-entry undo window fills, the oldest stroke chunk is folded into a base canvas and removed from vector undo history while the visible artwork remains unchanged.

### Painting creation transaction

New Painting creation now writes a real blank PNG first, then adds the logical library record. If the index write fails, Painting attempts to delete the newly written PNG before reporting failure.

This prevents ambiguous index-only “blank paintings” and reduces hidden quota leakage after partial New operations.

---

## 4. Save-failure transition rule

A durability defect was found during the final pass: the initial UI attempted a save before New/Gallery/Close but could continue even when that save failed.

Current rule for both Activities:

- automatic save failure leaves the current creation dirty and visibly in error;
- a child-initiated transition that would abandon the current in-memory creation does **not** proceed until the required save succeeds;
- existing/older work is never deleted automatically to hide quota pressure;
- platform-enforced lifecycle STOP remains authoritative and cannot be vetoed by an Activity.

This separates child UX durability from platform lifecycle authority cleanly.

---

## 5. Shared child-Activity UI primitives

Added:

```text
src/greia_platform/activity_ui.py
```

This is intentionally a very small shared SDK layer justified by two real consumers. It currently contains:

- `ChildUiMetrics` — 1024×600-first proportional metrics;
- large common toolbar-button geometry;
- cached semantic-icon loading/scaling;
- rounded icon-button rendering;
- small shared New/Grid/Undo/Eraser symbols;
- bounded RGB mixing.

It is **not** a general widget/layout/scene/animation system.

Desired extraction discipline remains:

1. real Activities first;
2. measured/repeated need second;
3. smallest reusable primitive third;
4. low-end measurement before richer shared abstractions become canon.

---

## 6. Theme API authority defect found during implementation

Writing/Painting exposed a platform contract inconsistency.

`get_theme()` was documented as an ordinary Activity read API, but implementation depended on `GREIA_CUSTOMIZATION_DIR`. The installed supervisor exposes that profile customization path only when `customization.manage` is granted.

Granting Writing/Painting mutation authority merely to obtain Greia colors would have violated least privilege.

Source correction:

```text
src/greia_platform/activity_api.py
```

Current semantics:

```text
ordinary unprivileged Activity
    -> get_theme()
    -> canonical default Greia resolved palette
    -> no raw profile customization/wallpaper path
    -> no customization.manage

trusted customization context
    -> get_theme()
    -> existing resolved child customization state
```

A future ordinary-Activity **read-only personalized theme snapshot** remains useful, but must not expose raw customization files or mutation authority.

Regression source:

```text
tests/test_activity_theme_access.py
```

---

## 7. Python authoring/runtime mismatch deliberately not changed

The static Activity validator currently tolerates package-relative imports, while the installed Python runtime adapter launches the configured entrypoint as a direct file.

Therefore this is not yet a supported installed pattern:

```python
from .model import Model
```

The tempting fix was to broaden runtime launch semantics to module execution. That was **not** done in this tranche because the current full regression suite cannot execute here and creative-app work should not silently alter the stable runtime seam.

Instead:

- Activity-local implementation remains internally class-structured inside each `main.py`;
- genuinely shared child UI primitives moved into reviewed `greia_platform.activity_ui`;
- the limitation is explicit in `skills/greia-activity-authoring/SKILL.md`.

A future runtime-module-entrypoint change must include dedicated runtime/supervisor regressions and a current full source gate.

---

## 8. Provider-free regression source added

```text
tests/test_core_creation_activities.py
tests/test_activity_ui.py
tests/test_activity_theme_access.py
```

Coverage includes:

- text-buffer editing and inverse edits;
- Writing undo operation-count bound;
- Writing total changed-text payload bound;
- oversized single undo payload refusal without discarding the actual edit;
- proof that one-character edits on large documents retain only changed fragments;
- stale/mismatched inverse-edit rejection;
- document index/order/portable UTF-8 behavior;
- new-document private-file rollback on simulated index failure;
- refusal without silent old-work eviction;
- bounded preview semantics;
- painting index/order/private-file behavior;
- transactional blank-PNG rollback on simulated Painting index failure;
- bounded Painting undo;
- 2,048-point stroke-chunk limit;
- invalid stroke rejection;
- shared 1024×600 UI geometry/scaling;
- RGB helper bounds;
- ordinary canonical-theme access without customization authority;
- preservation of trusted customization-context theme behavior.

**None of these new tests executed in this tranche.**

---

## 9. Static contract checks performed

The source was cross-checked against the repository’s current declarations for:

- Activity manifest shape;
- capability/permission vocabulary;
- curated Python import roots;
- semantic icon IDs;
- theme default identifiers/colors;
- Greia Storage private-file/KV API;
- Storage policy bounds;
- lifecycle READY/STOP usage;
- current direct-file Python entrypoint behavior.

This is source review, not execution evidence.

---

## 10. Current evidence boundary

Last complete source gate that actually executed remains:

```text
commit: 097f0281888a58f6f26425807ce99d9f35449313
provider-free tests: 232 / 232 PASS
project validation: PASS
bundled Activity validation: PASS
source/shell/footprint gate: PASS
```

This tranche did **not** run:

- the new focused tests;
- standalone Writing validator;
- standalone Painting validator;
- current `make verify`;
- installed/windowed Writing or Painting;
- storage-broker autosave/relaunch acceptance;
- visual screenshot acceptance;
- physical keyboard/pointer/touch acceptance;
- CPU/RSS/frame-pacing measurements;
- Acer acceptance.

No newer PASS count is claimed.

No GitHub Actions execution/query service was used for this implementation tranche.

---

## 11. Exact next execution step

On an owner-controlled Linux checkout at actual branch HEAD:

```bash
PYTHONPATH=src python3 -m unittest \
  tests.test_core_creation_activities \
  tests.test_activity_theme_access \
  tests.test_activity_ui \
  -v

PYTHONPATH=src python3 tools/validate_activity.py activities/writing
PYTHONPATH=src python3 tools/validate_activity.py activities/painting

PYTHONPATH=src python3 -m unittest discover \
  -s tests \
  -p 'test_developer_remote.py' \
  -v

make verify
```

Stop at the first real failure and preserve exact output.

Only after the source gate is current should the developer image and installed visual/input acceptance proceed as specified in `HANDOVER.md`.

---

## 12. Product acceptance still open

Writing still needs real acceptance for:

- long Unicode text;
- wrapping/caret behavior;
- repeated undo on long documents;
- keyboard/input-method behavior;
- autosave/relaunch/save-failure behavior;
- gallery scaling;
- 1024×600 visual comfort;
- low-end latency/RSS.

Painting still needs real acceptance for:

- slow/fast pointer stroke quality;
- behavior at the 2,048-point continuation boundary;
- >24-stroke bounded undo behavior;
- eraser feel;
- PNG autosave/relaunch/save-failure behavior;
- gallery scaling;
- touch semantics before claiming touch support;
- 1024×600 visual comfort;
- low-end CPU/RSS/frame pacing.

Both still need installed lifecycle/crash/forced-return acceptance and future logical backup integration.

---

## 13. R7 relationship

R7 remains blocking. Production remains on the provisional Xorg/xinit compatibility backend. No compositor is selected by this work, no raw DRM/input authority is granted to Activities, and no physical direct-graphics evidence is advanced.

Writing and Painting are useful future acceptance workloads for whatever display/session architecture is selected because they exercise sustained keyboard input, sustained pointer rendering, autosave, profile-scoped durable data and real child-visible return/recovery.

---

## 14. Continuity note — active plan append

`AGENTS.md` normally requires a substantive implementation tranche to append the active remediation plan progress log.

The current GitHub connector exposes only whole-file replacement for that approximately 700-line append-only historical plan, and this execution environment has no authenticated/networked local Git checkout. Reconstructing/replacing the entire historical plan merely to insert one paragraph would create an unacceptable continuity/truncation risk.

Therefore:

- **the active-plan historical file was intentionally not rewritten in this tranche**;
- current implementation/evidence is fully recorded in `HANDOVER.md`, the canonical product requirement, the Activity skill, and this dated review;
- the next authenticated local-checkout tranche must append the corresponding 2026-08-10 progress entry to the existing active plan without rewriting its historical entries.

This is explicit administrative documentation debt, not hidden implementation debt, and does not change R7 ordering or closure status.
