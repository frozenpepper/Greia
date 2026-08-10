# Greia — Standalone Engineering Handover

**Date:** 2026-08-10  
**Version family:** `0.13.x` development  
**Repository:** `frozenpepper/Greia` (private)  
**Integration target:** `main`  
**Active branch:** `r7-direct-graphics`  
**Draft PR:** #4 — `R7: direct graphics/session migration and KMSDRM evidence path`  
**Blocking architecture phase:** **R7 — Direct graphics/session architecture**

---

## 1. Resume without chat history

Read in this order before substantive work:

1. `AGENTS.md`;
2. `README.md`;
3. `docs/DOCUMENTATION.md`;
4. `docs/architecture/GREIA_ARCHITECTURE.md`;
5. accepted ADRs relevant to the work, especially ADR 0012–0017;
6. `docs/product/PHASE0_CORE_CREATION_ACTIVITIES.md`;
7. `docs/plans/2026-08-08_ARCHITECTURE_REMEDIATION_AND_PLATFORM_COMPLETION.md`;
8. this `HANDOVER.md`;
9. `docs/agents/GREIA_AGENT_OPERATIONS.md`;
10. `skills/greia-activity-authoring/SKILL.md` for Activity work;
11. the phase-specific testing/review documents named below.

GitHub is canonical. Resolve actual branch HEAD before editing or testing; do not trust a SHA remembered from chat.

Documentation ownership is defined by `docs/DOCUMENTATION.md`:

```text
AGENTS.md                    repository-wide work/product rules
docs/product/*               accepted child-facing product requirements
accepted ADRs                normative architecture decisions
source/runtime declarations  exact implemented APIs/schemas/commands
active remediation plan      ordering and closure criteria
HANDOVER.md                  current implementation/evidence/blocker state
docs/testing/*               exact named procedures
agent operations/skills      derived living manuals
reviews                      dated analysis/evidence/provenance
```

---

## 2. Critical hosted-execution rule

**Do not use the GitHub Actions execution service without explicit repository-owner authorization for that specific use.**

Without authorization do not:

- trigger/rerun/dispatch hosted workflows;
- add automatic hosted triggers;
- query Actions runs/status/jobs/steps/logs/artifacts;
- download Actions artifacts.

Reading/editing workflow source as normal repository source is allowed. GitHub commits/PR review/source persistence remain expected.

No Actions execution/query service was used in the 2026-08-10 creative implementation tranche.

---

## 3. Verification/evidence boundary — do not overclaim

Last complete source gate genuinely executed:

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

The serial 8/8 result predates later strengthening of that path.

Everything newer that has not explicitly executed remains **UNPROVEN / committed but unexecuted**.

The current creative tranche has **not** executed:

```text
tests/test_core_creation_activities.py
tests/test_activity_theme_access.py
tests/test_activity_ui.py
standalone Writing validator
standalone Painting validator
current full make verify
installed/windowed Writing or Painting
developer-image build
physical screenshot/input/performance acceptance
```

No newer PASS count is claimed.

---

## 4. R0–R6 state

R0–R6 are **SOURCE-CLOSED** at their recorded boundaries. Do not reopen the old v0.12 recovery incident without a concrete defect.

The formerly lost post-v0.12 R5 history/progression authority was replaced by a **new reviewed implementation**; never describe it as historical recovery.

The source foundations now consumed by the creative Activities include:

- stable Activity manifests/IDs;
- PermissionBroker/trust boundary;
- runtime-neutral lifecycle/READY/STOP;
- profile-scoped Universal Storage;
- automatic sessions/events/progression;
- HAL/device-capability authority;
- Python runtime adapter;
- semantic shared assets.

---

## 5. R7 remains the blocking architecture phase

Current production state:

```text
installed graphics/session:   Xorg + xinit compatibility
status:                       PROVISIONAL
production compositor:        none selected
serial direct DRM ownership:  evidence candidate only
ActivitySupervisor DRM owner: forbidden
ordinary raw input ownership: forbidden target direction
```

Installed Activity lifecycle already uses backend-neutral `DisplaySessionCoordinator` with `LegacyXDisplaySessionBackend`. That is a real ownership/recovery seam, **not** a completed direct-graphics migration.

Current X-compatible sandbox concessions must not be removed blindly while production still uses Xorg.

Relevant R7 source/tools:

```text
src/greia_launcher/display_session.py
src/greia_launcher/display_session_legacy_x.py
src/greia_platform/direct_graphics_probe.py
src/greia_platform/kmsdrm_acceptance.py
src/greia_platform/kmsdrm_serial_handoff.py
tools/r7_compositor_package_probe.py
tools/r7_qemu_kmsdrm_acceptance.py
tools/r7_qemu_kmsdrm_handoff_acceptance.py
tools/r7_local_evidence.py
```

Reference package/compositor candidates remain:

```text
cage
weston
wlroots-runtime
```

They are measurement candidates only.

---

## 6. Mandatory Phase-0 creative baseline — first source tranche implemented

Canonical product contract:

```text
docs/product/PHASE0_CORE_CREATION_ACTIVITIES.md
```

Dated source review:

```text
docs/reviews/2026-08-10_CORE_CREATION_SOURCE_TRANCHE.md
```

### Writing

```text
Activity ID: org.greia.writing
source:      activities/writing/
runtime:     Python/Pygame API 0.1
permissions: none
required:    display, keyboard, pointer
optional:    touch
```

Current source implements:

- fullscreen large-text editing;
- approximately 42 px default body text at the 1024×600 reference scale;
- Unicode `TEXTINPUT`;
- multiline text;
- click caret placement;
- arrows/Home/End/Backspace/Delete/Enter;
- soft wrapping and vertical scrolling;
- one unambiguous caret owner at soft-wrap boundaries;
- large visible Undo plus optional Ctrl/Cmd-Z;
- **128 recent edit-operation undo entries**;
- undo stores inserted/deleted fragments and cursor positions, not full-document snapshots;
- visual document gallery;
- New document;
- debounced autosave plus transition/exit save attempts;
- UTF-8 private files through Greia Storage;
- rollback attempt for an empty private file if new-document index creation fails;
- no filesystem browser/file dialog;
- no formatting ribbon;
- no privileged permissions;
- no silent old-document eviction when the bounded library is full;
- refused New leaves existing work/library intact rather than creating an unsavable phantom document.

Current logical/durability bounds:

```text
KV index:      documents.index.v1
private files: documents/<uuid>.txt
library:       120 indexed documents
text:          120,000 Unicode code points per document
undo:          128 recent edit operations
```

### Painting

```text
Activity ID: org.greia.painting
source:      activities/painting/
runtime:     Python/Pygame API 0.1
permissions: none
required:    display, pointer
optional:    touch
```

Current source implements:

- large fullscreen raster canvas;
- 10 fixed cheerful colors;
- 3 brush sizes;
- eraser;
- large icon-led controls;
- bounded undo;
- New drawing;
- visual gallery;
- direct pointer-stroke feedback;
- pointer-point decimation;
- debounced PNG saving through Greia Storage;
- no per-frame PNG encoding/storage write;
- no filesystem browser;
- no privileged permissions;
- no silent old-painting eviction;
- refused New leaves existing painting/library intact instead of creating a phantom unsavable painting.

Painting undo retains at most 24 recent strokes. When the window fills, the oldest stroke is folded into a base canvas and removed from undo history. Artwork remains visible without unlimited full-canvas history.

Current logical/durability bounds:

```text
KV index:      paintings.index.v1
private files: paintings/<uuid>.png
library:       48 indexed paintings
undo:          24 recent strokes
```

### Creative source is not product-complete

Still required before Phase-0/user-ready acceptance:

- execute the new focused tests;
- run both standalone Activity validators;
- run a current complete `make verify`;
- real 1024×600 visual review;
- Writing Unicode/caret/wrap/autosave/relaunch acceptance;
- Painting slow/fast stroke/undo/eraser/autosave/relaunch acceptance;
- quota/save-failure UX acceptance;
- gallery scaling beyond the first six visible cards;
- explicit touch-event acceptance before claiming touch support;
- installed display/session exit/crash/forced-return acceptance;
- Acer CPU/RSS/responsiveness/frame-pacing measurements;
- eventual logical `.greiabackup` integration once R11 exists.

R7 remains blocking. Creative source work does not select a compositor or advance R7 hardware evidence.

---

## 7. First shared Activity UI primitives

New SDK module:

```text
src/greia_platform/activity_ui.py
```

Current scope:

- `ChildUiMetrics` — 1024×600-first scaling and large toolbar geometry;
- cached semantic-icon loading/scaling;
- rounded icon buttons;
- small New/Grid/Undo/Eraser symbols;
- bounded RGB `mix()` helper.

Initial consumers:

```text
activities/writing
activities/painting
```

This is deliberately **not** a general widget/layout/scene/animation toolkit. Extract future primitives only from repeated real Activity needs and measure their cost on the C0 reference hardware.

Provider-free source coverage exists in:

```text
tests/test_activity_ui.py
```

but remains unexecuted in this tranche.

---

## 8. Theme API least-privilege correction

Creative implementation exposed a platform contract defect: `get_theme()` previously depended on `GREIA_CUSTOMIZATION_DIR`, while the supervisor exposes that profile path only with `customization.manage`.

Giving ordinary creative Activities mutation authority merely to obtain colors would be wrong.

Current source behavior:

```text
ordinary Activity get_theme()
    -> trusted canonical default Greia resolved palette
    -> no raw child customization/wallpaper path
    -> no customization.manage required

trusted customization context get_theme()
    -> existing profile-scoped resolved customization state
```

Files:

```text
src/greia_platform/activity_api.py
tests/test_activity_theme_access.py
```

A future ordinary-Activity read-only personalized theme snapshot is a valid enhancement, but it must not expose raw profile customization files just for cosmetics.

Regression source is committed but unexecuted.

---

## 9. Known Python Activity modularity limitation

The static validator tolerates package-relative imports, but the installed Python adapter launches `runtime.entrypoint` as a **direct file**.

Therefore this is not yet a supported installed pattern:

```python
from .model import Model
```

Do not work around it with `sys.path`, dynamic imports or `importlib` in an Activity.

Writing and Painting keep internally clean classes in one `main.py`; genuinely reusable cross-Activity code lives in reviewed `greia_platform.activity_ui`.

A future module-entrypoint change must update runtime adapter tests and the Activity skill, and must receive a current full source gate.

---

## 10. Developer remote-control/test console

Protocols:

```text
docs/agents/GREIA_AGENT_OPERATIONS.md
docs/testing/2026-08-09_DEVELOPER_REMOTE_CONTROL.md
```

Developer profile:

```text
build/profiles/modern-amd64-dev.toml
hostname: greia-dev.local
status: experimental / developer-only
```

Build on compatible owner-controlled Linux:

```bash
sudo bash build/build-developer-image.sh out
```

Expected local artifacts:

```text
out/greia-os-modern-amd64-dev.img
out/greia-os-modern-amd64-dev-ssh-key
out/greia-os-modern-amd64-dev-ssh-key.pub
out/greia-os-modern-amd64-dev-developer-remote.json
```

The private key is secret operator material and must not enter Git/shared evidence.

Remote helper:

```text
tools/greia_remote.py
```

Commands include:

```text
wait status screenshot logs restart restart-installer
key mousemove click type
deploy remove restore
reboot poweroff shell
```

Dedicated known-hosts file:

```text
~/.greia/known_hosts
```

No physical developer-remote acceptance is currently claimed.

---

## 11. Developer Activity trust boundary

Built-in source:

```text
/opt/greia-os/activities
trust = BUILT_IN
```

Ordinary remote developer source:

```text
/var/lib/greia-developer/activities
trust = DEVELOPER_UNSIGNED
```

Normal deployment:

```bash
python3 tools/greia_remote.py deploy path/to/activity
```

must not upgrade trust or grant privileged permissions.

Explicit built-in replacement test only:

```bash
python3 tools/greia_remote.py deploy path/to/activity --replace-system
python3 tools/greia_remote.py restore <activity-id>
```

Do not use `--replace-system` to bypass ordinary validation/trust failures.

---

## 12. Live graphical installer remote boundary

Source exists:

```text
tools/provision_developer_installer.py
```

Intended live identity:

```text
greia-installer-dev.local
root@:0 display endpoint
key-only greiaadmin SSH
wired DHCP/mDNS
```

It remains **not wired into `build/build-installer-image.sh`**. First-time remote USB installation is therefore not claimed operational.

Remote installation must drive the existing graphical fail-closed installer. Never substitute unattended `dd`, a disk-wipe API or a generic destructive root command.

---

## 13. Exact next source verification step

On owner-controlled Linux at actual branch HEAD:

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

Stop at the first real failure and preserve exact stdout/stderr. Do not weaken a test or validator to manufacture PASS.

If the current source gate passes, build the developer image:

```bash
sudo bash build/build-developer-image.sh out
```

Then use the developer-remote protocol for real visual/input/storage acceptance, including Writing and Painting.

---

## 14. Creative installed acceptance sequence

Once the developer target itself is accepted:

### Writing

1. launch and screenshot first usable page;
2. type multilingual/Unicode text;
3. exercise insert/delete/caret movement across soft wraps;
4. exercise visible Undo repeatedly on a long document;
5. wait for autosave;
6. exit/relaunch and verify exact text remains;
7. create a second document and use gallery;
8. exercise a save/quota failure without losing current/old work;
9. force-stop/crash and prove Greia returns safely;
10. collect launcher logs and CPU/RSS evidence.

### Painting

1. launch and screenshot blank canvas;
2. draw slow and fast strokes;
3. exercise colors/sizes/eraser;
4. draw more than 24 strokes and exercise bounded undo;
5. wait for autosave;
6. exit/relaunch and verify PNG remains;
7. create a second painting and use gallery;
8. exercise a save/quota failure without deleting old work;
9. force-stop/crash and prove Greia returns safely;
10. collect launcher logs and CPU/RSS/frame-pacing evidence.

Touch needs separate real touch-capable acceptance before being claimed supported.

---

## 15. Exact next R7 evidence step

Protocol:

```text
docs/testing/2026-08-09_R7_EXTERNAL_LINUX_EVIDENCE_EXECUTION.md
```

On owner-controlled disposable/root-safe x86-64 Linux:

```bash
SOURCE_SHA="$(git rev-parse HEAD)"
RUN_ROOT="/var/tmp/greia-r7-${SOURCE_SHA}"
python3 tools/r7_local_evidence.py --run-root "$RUN_ROOT" --plan-only
sudo -E python3 tools/r7_local_evidence.py --run-root "$RUN_ROOT"
```

First failure is authoritative for the attempt. Do not reuse the run root or repeat active/serial evidence just to obtain PASS.

Only evidence may justify serial/direct/compositor selection. Physical legacy Intel/Acer acceptance remains mandatory before production migration. Pi physical display acceptance remains R8/R14 after Pi board/image adapters exist.

---

## 16. Active-plan administrative debt from this tranche

`AGENTS.md` normally requires every substantive implementation tranche to append:

```text
docs/plans/2026-08-08_ARCHITECTURE_REMEDIATION_AND_PLATFORM_COMPLETION.md
```

The available GitHub connector can only replace that approximately 700-line append-only historical file as a whole, and the current execution environment has no authenticated/networked local Git checkout. Reconstructing the historical plan merely to insert one paragraph creates an unacceptable truncation/provenance risk.

Therefore the plan file was **intentionally not rewritten** in this tranche.

The complete current implementation/evidence state is preserved in:

```text
HANDOVER.md
docs/product/PHASE0_CORE_CREATION_ACTIVITIES.md
docs/reviews/2026-08-10_CORE_CREATION_SOURCE_TRANCHE.md
skills/greia-activity-authoring/SKILL.md
```

The **next authenticated local-checkout tranche must append** a 2026-08-10 creative-source progress entry to the existing active plan without modifying/reformatting its historical entries. This is administrative documentation debt only; it does not alter R7 ordering or closure status.

---

## 17. Invariants to preserve

- no visible Linux UI in normal child operation;
- explicit Greia profile selection;
- Activity remains runtime-neutral;
- global progression/reward economics remain platform-owned;
- durable child state remains architecture-neutral;
- per-Activity isolation/trust remains fail-closed;
- ordinary theming never grants customization mutation authority;
- child creation quota pressure never silently deletes/evicts old work;
- developer remote access never leaks into release images;
- remote placement never upgrades Activity trust;
- X11 compatibility never becomes Activity API;
- ActivitySupervisor never becomes DRM master;
- destructive installation remains graphical and revalidated;
- no private credentials in Git;
- no unapproved hosted Actions execution/query surface.

---

## 18. Continuity files

```text
AGENTS.md
README.md
docs/DOCUMENTATION.md
HANDOVER.md
docs/architecture/GREIA_ARCHITECTURE.md
docs/product/PHASE0_CORE_CREATION_ACTIVITIES.md
docs/plans/2026-08-08_ARCHITECTURE_REMEDIATION_AND_PLATFORM_COMPLETION.md
docs/agents/GREIA_AGENT_OPERATIONS.md
skills/greia-activity-authoring/SKILL.md
docs/reviews/2026-08-10_DOCUMENTATION_DEEP_REVIEW.md
docs/reviews/2026-08-10_PHASE0_CREATIVE_BASELINE_DECISION.md
docs/reviews/2026-08-10_CORE_CREATION_SOURCE_TRANCHE.md
docs/testing/2026-08-09_DEVELOPER_REMOTE_CONTROL.md
docs/testing/2026-08-09_R7_EXTERNAL_LINUX_EVIDENCE_EXECUTION.md
docs/reviews/2026-08-09_R7_X11_DIRECT_GRAPHICS_DEPENDENCY_AUDIT.md
docs/reviews/2026-08-09_R7_SESSION_OWNERSHIP_CANDIDATE_MATRIX.md
```

After the next substantive tranche:

- commit coherent work;
- repair the pending active-plan append when an authenticated local checkout is available;
- otherwise append active-plan progress normally when implementation state changes;
- update this handover;
- update operations/Activity skill when governed contracts change;
- record exactly what verification actually ran;
- preserve VM/physical evidence gaps;
- state the next legitimate step.
