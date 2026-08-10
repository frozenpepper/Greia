# Greia Core Creation Activities — Source Tranche Review — 2026-08-10

**Scope:** first source implementation of mandatory Phase-0 Writing and Painting Activities, first shared child-Activity UI primitives, and least-privilege theme-read correction  
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

## 2. Source added

### Writing

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
- bounded edit-operation undo;
- visual gallery and New;
- debounced automatic saves plus transition/exit save attempts;
- UTF-8 Greia private files and a bounded logical index;
- rollback attempt if empty-file creation succeeds but logical-index creation fails;
- no filesystem browser/file-dialog abstraction;
- no formatting-ribbon/desktop-office scope;
- no silent eviction of older child documents on library pressure.

Writing’s undo history was specifically hardened after static review. It now retains up to **128 inverse edit operations** containing only inserted/deleted fragments and cursor positions rather than 32 complete document snapshots. A single-character edit on a 50,000-character document therefore records one changed character, not a second 50,000-character string.

### Painting

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
- bounded stroke undo;
- visual gallery and New;
- pointer-point decimation;
- debounced PNG save through Greia Storage;
- no per-frame PNG encoding or durable write;
- no filesystem browser;
- no silent eviction of older child paintings when the bounded library is full.

Painting’s undo model retains only recent stroke geometry. Once the history window is exceeded, the oldest stroke is folded into a base canvas and removed from undo history rather than retaining unlimited full-canvas snapshots.

---

## 3. Shared child-Activity UI primitives

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

This is the desired extraction direction: real Activities first, measured duplication second, smallest reusable primitive third.

---

## 4. Theme API authority defect found during implementation

Writing/Painting initially exposed a platform contract inconsistency.

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

A future ordinary-Activity **read-only personalized theme snapshot** remains a useful enhancement, but must be implemented without exposing raw customization files or mutation authority.

Regression source:

```text
tests/test_activity_theme_access.py
```

---

## 5. Python authoring/runtime mismatch deliberately not changed

The static Activity validator currently ignores package-relative imports, while the installed Python runtime adapter launches the configured entrypoint as a direct file.

Therefore this is not yet a supported installed pattern:

```python
from .model import Model
```

The tempting fix was to broaden runtime launch semantics to support package/module execution. That was **not** done in this tranche because the current full regression suite cannot execute here and this creative-app work should not silently alter the stable runtime seam.

Instead:

- Activity-local implementation remains internally class-structured inside each `main.py`;
- genuinely shared child UI primitives moved into reviewed `greia_platform.activity_ui`;
- the limitation is now explicit in `skills/greia-activity-authoring/SKILL.md`.

A future runtime-module-entrypoint change must include dedicated runtime/supervisor regressions and a current full source gate.

---

## 6. Durability/safety review decisions

### No silent child-work eviction

Both repositories have bounded visible libraries, but reaching that bound refuses a new creation rather than silently deleting or dropping an older creation from the logical index.

The Activity skill now makes this a general creation-tool rule.

### No phantom New state on refusal

Writing and Painting were hardened so a refused New operation leaves the existing current creation/library intact and exposes an error state rather than switching to an unsavable fake creation.

### Writing creation rollback

Writing creates an empty private UTF-8 document file before adding the logical library entry. If that index write fails, the repository now attempts to remove the just-created private file before propagating the failure, reducing hidden quota leakage from partial New operations.

### Writing caret boundary

Soft wrapping can create a cursor index that is simultaneously the end of one visual line and the start of the next. Writing now assigns that boundary to the later visual line and renders the caret once, preventing ambiguous/double visual ownership.

### Memory-bounded undo

- Writing: maximum **128 inverse edit operations**; no full-document undo snapshots.
- Painting: maximum 24 recent strokes; older strokes are folded into base pixels.

These are Activity-level UX/memory bounds beneath the platform Storage quota and may be tuned after physical measurement.

---

## 7. Provider-free regression source added

```text
tests/test_core_creation_activities.py
tests/test_activity_ui.py
tests/test_activity_theme_access.py
```

Coverage includes:

- text-buffer editing and inverse edits;
- bounded edit-operation Writing undo;
- proof that a one-character edit on a large document stores only the changed fragment;
- rejection of mismatched/stale inverse edits;
- document index/order/portable text behavior;
- new-document private-file rollback on simulated index failure;
- refusal without silent eviction;
- bounded preview semantics;
- painting index/order/private-file behavior;
- bounded Painting undo and invalid stroke rejection;
- shared 1024×600 UI geometry/scaling;
- RGB helper bounds;
- ordinary canonical-theme access without customization authority;
- preservation of trusted customization-context theme behavior.

**None of these new tests executed in this tranche.**

---

## 8. Static contract checks performed

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

## 9. Current evidence boundary

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

## 10. Exact next execution step

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

## 11. Product acceptance still open

Writing still needs real acceptance for:

- long Unicode text;
- wrapping/caret behavior;
- repeated undo on long documents;
- keyboard/input-method behavior;
- autosave/relaunch/failure behavior;
- gallery scaling;
- 1024×600 visual comfort;
- low-end latency/RSS.

Painting still needs real acceptance for:

- slow/fast pointer stroke quality;
- >24-stroke bounded undo behavior;
- eraser feel;
- PNG autosave/relaunch/failure behavior;
- gallery scaling;
- touch semantics before claiming touch support;
- 1024×600 visual comfort;
- low-end CPU/RSS/frame pacing.

Both still need installed lifecycle/crash/forced-return acceptance and future logical backup integration.

---

## 12. R7 relationship

R7 remains blocking. Production remains on the provisional Xorg/xinit compatibility backend. No compositor is selected by this work, no raw DRM/input authority is granted to Activities, and no physical direct-graphics evidence is advanced.

Writing and Painting are useful future acceptance workloads for whatever display/session architecture is selected because they exercise sustained keyboard input, sustained pointer rendering, autosave, profile-scoped durable data and real child-visible return/recovery.

---

## 13. Continuity note — active plan append

`AGENTS.md` normally requires a substantive implementation tranche to append the active remediation plan progress log.

The current GitHub connector exposes only whole-file replacement for that approximately 700-line append-only historical plan, and this execution environment has no authenticated/networked local Git checkout. Reconstructing/replacing the entire historical plan merely to insert one paragraph would create an unacceptable continuity/truncation risk.

Therefore:

- **the active-plan historical file was intentionally not rewritten in this tranche**;
- current implementation/evidence is fully recorded in `HANDOVER.md`, the canonical product requirement, the Activity skill, and this dated review;
- the next authenticated local-checkout tranche must append the corresponding 2026-08-10 progress entry to the existing active plan without rewriting its historical entries.

This is explicit administrative documentation debt, not hidden implementation debt, and does not change R7 ordering or closure status.
