# Greia — Standalone Engineering Handover

**Date:** 2026-08-10  
**Version family:** `0.13.x` development  
**Repository:** `frozenpepper/Greia` (private)  
**Integration target:** `main`  
**Active branch:** `r7-direct-graphics`  
**Draft PR:** #4 — `R7: direct graphics/session migration and KMSDRM evidence path`  
**Blocking phase:** **R7 — Direct graphics/session architecture**

---

## 1. Mandatory resume order

Read before substantive work:

1. `AGENTS.md`;
2. `README.md`;
3. `docs/DOCUMENTATION.md`;
4. `docs/architecture/GREIA_ARCHITECTURE.md`;
5. accepted ADRs relevant to the task, especially ADR 0012–0017;
6. `docs/product/PHASE0_CORE_CREATION_ACTIVITIES.md`;
7. `docs/plans/2026-08-08_ARCHITECTURE_REMEDIATION_AND_PLATFORM_COMPLETION.md`;
8. this `HANDOVER.md`;
9. `docs/agents/GREIA_AGENT_OPERATIONS.md`;
10. `skills/greia-activity-authoring/SKILL.md` for Activity work;
11. the exact R7/testing/review docs named below.

GitHub is canonical. Resolve the actual branch HEAD before editing/testing. Do not infer current state from an old chat SHA.

`docs/DOCUMENTATION.md` owns documentation precedence:

```text
AGENTS.md                    repository-wide rules/product invariants
accepted ADRs                normative architecture decisions
source/runtime declarations  exact implemented APIs/schemas/commands
docs/product/*               explicit child-facing product requirements
active remediation plan      ordering and closure criteria
HANDOVER.md                  current branch/evidence/blocker state
docs/testing/*               exact named test/operator procedures
agent operations/skills      derived living manuals
reviews                      dated evidence/analysis snapshots
```

---

## 2. Critical hosted-execution rule

**Do not use the GitHub Actions execution service without explicit repository-owner authorization for that specific use.**

Without authorization do not:

- trigger/rerun/dispatch hosted workflows;
- add automatic hosted triggers;
- query Actions runs/status/jobs/steps/logs/artifacts as evidence;
- download Actions artifacts.

Reading/editing workflow source as ordinary repository source is allowed. GitHub remains expected for source persistence and PR review.

---

## 3. Verification boundary — do not overclaim

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

The 2026-08-10 creative-Activity tranche did **not** execute:

- `tests/test_core_creation_activities.py`;
- `tests/test_activity_theme_access.py`;
- `tests/test_activity_ui.py`;
- standalone Writing/Painting validators;
- current full `make verify`;
- installed/windowed Activity execution;
- developer-image build;
- physical screenshots/input/performance acceptance.

No new PASS count is claimed.

---

## 4. R0–R6 state

R0–R6 are **SOURCE-CLOSED** at their recorded boundaries. Do not reopen the old v0.12 recovery incident without a concrete defect.

The formerly lost post-v0.12 R5 history/progression authority was replaced by a **new reviewed implementation**; never describe it as historical recovery.

The established platform foundations now consumed by the creative Activities include:

- stable Activity manifests/IDs;
- PermissionBroker/trust boundary;
- runtime-neutral lifecycle/READY/STOP;
- profile-scoped Universal Storage;
- automatic sessions/events/progression;
- HAL/device-capability authority;
- Python runtime adapter;
- semantic shared assets.

---

## 5. Active blocking phase — R7

Current production state:

```text
installed graphics/session:   Xorg + xinit compatibility
status:                       PROVISIONAL
production compositor:        none selected
serial direct DRM ownership:  evidence candidate only
ActivitySupervisor DRM owner: forbidden
ordinary raw input ownership: forbidden target direction
```

The installed Activity lifecycle uses backend-neutral `DisplaySessionCoordinator` with `LegacyXDisplaySessionBackend`. This is a real ownership/recovery seam, not a completed direct-graphics migration.

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

Reference compositor/package candidates remain:

```text
cage
weston
wlroots-runtime
```

They are measurement candidates only.

---

## 6. Phase-0 core creation Activities — source first tranche implemented

Canonical product requirement:

```text
docs/product/PHASE0_CORE_CREATION_ACTIVITIES.md
```

### Writing

```text
Activity ID: org.greia.writing
source:      activities/writing/
manifest:    activity.toml
runtime:     Python/Pygame API 0.1
permissions: none
required:    display, keyboard, pointer
optional:    touch
```

Current source implements:

- fullscreen large-text editor;
- approximately 42 px default text at 1024×600 scale;
- Unicode `TEXTINPUT`;
- multiline editing;
- click caret placement;
- arrows/Home/End/Backspace/Delete/Enter;
- soft wrapping and vertical scrolling;
- bounded 32-state undo with large visible undo control;
- visual document gallery;
- new document;
- debounced autosave and transition save;
- UTF-8 private files through Greia Storage;
- no filesystem browser/file dialog;
- no formatting ribbon;
- no privileged permissions;
- no silent old-document eviction when the bounded library is full.

Current durable shape:

```text
KV:    documents.index.v1
files: documents/<uuid>.txt
bound: 120 indexed documents / 120,000 code points each
```

### Painting

```text
Activity ID: org.greia.painting
source:      activities/painting/
manifest:    activity.toml
runtime:     Python/Pygame API 0.1
permissions: none
required:    display, pointer
optional:    touch
```

Current source implements:

- large fullscreen drawing canvas;
- 10 fixed cheerful colors;
- 3 brush sizes;
- eraser;
- large icon-led controls;
- bounded undo;
- New drawing;
- visual gallery;
- direct pointer-stroke feedback;
- debounced PNG saving through Greia Storage;
- no per-frame PNG encoding/storage writes;
- no filesystem browser;
- no privileged permissions;
- no silent old-painting eviction when the bounded library is full.

Painting undo retains at most 24 recent strokes. Oldest strokes are folded into a base canvas, preserving artwork without retaining unlimited full-canvas snapshots.

Current durable shape:

```text
KV:    paintings.index.v1
files: paintings/<uuid>.png
bound: 48 indexed paintings / 24 undoable recent strokes
```

### Creative source is not product-complete yet

Still required:

- execute provider-free tests;
- run both standalone Activity validators;
- run current full `make verify`;
- visually review 1024×600 layout;
- real typing/caret/autosave/relaunch acceptance;
- real fast pointer drawing/undo/autosave/relaunch acceptance;
- quota/failure UX acceptance;
- explicit touch-event acceptance before claiming touch support;
- installed lifecycle/display-session acceptance;
- low-end Acer CPU/RSS/responsiveness measurements;
- eventual `.greiabackup` inclusion once R11 exists.

R7 remains the blocking architecture phase. This creative source work does not select a compositor or advance R7 hardware evidence.

---

## 7. First shared Activity UI primitives

New SDK module:

```text
src/greia_platform/activity_ui.py
```

Current scope only:

- `ChildUiMetrics` for 1024×600-first scaling and large toolbar geometry;
- cached semantic-icon loading/scaling;
- rounded icon buttons;
- small New/Grid/Undo/Eraser symbols;
- bounded RGB `mix()` helper.

Initial consumers:

```text
activities/writing
activities/painting
```

This is **not** a general widget/layout/scene/animation toolkit. Extract future primitives only from repeated real Activity needs and measure them on C0 hardware.

Provider-free source coverage added:

```text
tests/test_activity_ui.py
```

but it has not executed in this tranche.

---

## 8. Theme API least-privilege correction

A source audit during creative implementation found that `get_theme()` previously depended on `GREIA_CUSTOMIZATION_DIR`, which the supervisor exposes only with `customization.manage`.

Giving Writing/Painting that permission merely to obtain colors would be an authority error.

Current source now does:

```text
ordinary Activity get_theme()
    -> trusted canonical default Greia palette
    -> no raw profile customization/wallpaper path
    -> no customization.manage needed

trusted customization Activity get_theme()
    -> existing profile-scoped resolved customization path
```

Files:

```text
src/greia_platform/activity_api.py
tests/test_activity_theme_access.py
```

A future read-only personalized theme snapshot for ordinary Activities remains a legitimate SDK enhancement, but must not expose arbitrary profile customization files merely for cosmetics.

The new theme regressions are committed but unexecuted.

---

## 9. Known Python authoring/runtime limitation

The static validator tolerates package-relative imports, but the current installed Python adapter launches the Activity entrypoint as a **direct file**.

Therefore this is not yet a supported installed pattern:

```python
from .model import Model
```

Do not workaround with `sys.path`, dynamic imports or `importlib` inside Activities.

Writing and Painting keep clean internal classes in one `main.py`, while genuinely reusable cross-Activity code lives in the reviewed `greia_platform.activity_ui` module.

When module-entrypoint semantics are deliberately fixed, update the runtime adapter, tests and Activity skill together.

---

## 10. Developer remote-control/test console

Protocol:

```text
docs/testing/2026-08-09_DEVELOPER_REMOTE_CONTROL.md
```

General procedure:

```text
docs/agents/GREIA_AGENT_OPERATIONS.md
```

Developer profile:

```text
build/profiles/modern-amd64-dev.toml
hostname: greia-dev.local
status: experimental developer-only
```

Build on owner-controlled compatible Linux:

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

Private key is secret local operator material and must not enter Git/evidence archives.

Remote client:

```text
tools/greia_remote.py
```

Main commands:

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

No current hardware acceptance is claimed for this path.

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

must not upgrade package trust or grant privileged permissions.

Explicit built-in replacement testing only:

```bash
python3 tools/greia_remote.py deploy path/to/activity --replace-system
python3 tools/greia_remote.py restore <activity-id>
```

Do not use `--replace-system` to bypass validation/trust failures.

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

It is **not yet wired into `build/build-installer-image.sh`**. First-time remote USB installation is not claimed operational.

Remote installation must drive the existing graphical fail-closed installer. Never replace it with unattended `dd`, a disk-wipe API or generic destructive root command.

---

## 13. Exact next source verification step

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

Stop on the first real failure and return exact stdout/stderr. Do not “fix” a validator/test by weakening the contract.

If all source gates pass, build the developer image:

```bash
sudo bash build/build-developer-image.sh out
```

Then use the developer-remote protocol to perform visual/input acceptance, including Writing and Painting.

---

## 14. Creative Activity installed acceptance sequence

Once the developer target itself is accepted, use ordinary Greia navigation/deployment mechanisms and capture evidence.

Writing acceptance should include:

1. launch and screenshot first usable page;
2. type multilingual/Unicode text;
3. insert/delete/move caret at wrapped lines;
4. use visible undo;
5. wait for autosave;
6. exit/relaunch and verify exact text remains;
7. create a second document and use gallery;
8. force-stop/crash scenario and verify Greia returns safely;
9. collect launcher logs and CPU/RSS evidence.

Painting acceptance should include:

1. launch and screenshot blank canvas;
2. draw slow and fast strokes;
3. exercise colors/sizes/eraser;
4. exercise >24 strokes and bounded undo semantics;
5. wait for autosave;
6. exit/relaunch and verify PNG remains;
7. create second painting and use gallery;
8. force-stop/crash scenario and verify Greia returns safely;
9. collect launcher logs and CPU/RSS evidence.

Touch requires a separate real touch-capable target before claiming support.

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

First failure is authoritative for the attempt. Do not reuse the run root or repeat active/serial evidence merely to manufacture PASS.

Then compare actual serial/compositor/Xorg evidence and require physical legacy Intel/Acer acceptance before production migration. Pi physical display acceptance remains R8/R14 after Pi board/image adapters exist.

---

## 16. Invariants to preserve

- no visible Linux UI in normal child operation;
- explicit Greia profile selection;
- Activity remains runtime-neutral;
- global progression/reward economics remain platform-owned;
- durable child state remains architecture-neutral;
- per-Activity isolation/trust remains fail-closed;
- ordinary theming never grants customization mutation authority;
- child creation quotas never cause silent old-work eviction;
- developer remote access never leaks into release images;
- remote placement never upgrades Activity trust;
- X11 compatibility never becomes Activity API;
- ActivitySupervisor never becomes DRM master;
- destructive installation remains graphical and revalidated;
- no private credentials in Git;
- no unapproved hosted Actions execution/query surface.

---

## 17. Continuity files

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
docs/testing/2026-08-09_DEVELOPER_REMOTE_CONTROL.md
docs/testing/2026-08-09_R7_EXTERNAL_LINUX_EVIDENCE_EXECUTION.md
docs/reviews/2026-08-09_R7_X11_DIRECT_GRAPHICS_DEPENDENCY_AUDIT.md
docs/reviews/2026-08-09_R7_SESSION_OWNERSHIP_CANDIDATE_MATRIX.md
```

After the next substantive implementation tranche:

- commit coherent work;
- append active-plan progress when implementation state changes;
- update this handover;
- update operations/Activity skill when governed contracts change;
- record exactly what verification ran;
- preserve VM/physical gaps;
- state the next legitimate step.
