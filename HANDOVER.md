# Greia — Standalone Engineering Handover

**Date:** 2026-08-09  
**Version:** `0.13.0-phase0-dev`  
**Repository:** `frozenpepper/Greia` (private)  
**Canonical integration target:** `main`  
**Active branch:** `r7-direct-graphics`  
**Draft PR:** #4 — `R7: direct graphics/session migration and KMSDRM evidence path`  
**Current blocking phase:** **R7 — Direct graphics/session architecture**

---

## 1. Resume state

R0–R6 are source-closed. Do **not** reopen the old v0.12 recovery incident or refactor the completed authority/storage/session/runtime spine without a concrete R7 integration defect.

The former lost post-v0.12 R5 `history.py` was replaced by a new reviewed R5 implementation. Never describe it as recovered historical source.

Production Greia still boots through the known **Xorg/xinit compatibility path**. No direct-KMS production profile/package set is enabled. No compositor has been selected. Serial direct DRM ownership remains evidence-only.

GitHub is the persistent source of truth. Resolve the exact branch tip from `r7-direct-graphics` when resuming rather than trusting a hand-written hash. The last source commit immediately before this handover refresh is:

```text
5f45c7d44a9f254e5181dc068333a0db7292a658
```

That commit removes accidental formatting churn from the installed-launcher integration. Relative to the pre-integration commit `f1aa18b6fca32d04cdc7b0063184f49b3638493a`, `src/greia_launcher/main.py` has only 9 changed lines; the other cumulative change is the new display-session lifecycle regression file.

---

## 2. Exact verification boundary — do not overclaim

The last complete provider-free source gate that actually executed successfully remains:

```text
source checkpoint: 097f0281888a58f6f26425807ce99d9f35449313
provider-free tests: 232 / 232 PASS
project validation: PASS
bundled Activity validation: PASS
source/shell/footprint gate: PASS
```

Do **not** claim a newer complete test count.

Focused checks that actually executed earlier in R7:

```text
isolated current DisplaySessionCoordinator fixture: 22 / 22 PASS
isolated compositor-package pure-logic fixture: 14 / 14 PASS
serial KMSDRM fake-SDL/process suite: 8 / 8 PASS before later serial strengthening
```

The latest strengthened serial tests, hardware-settings tests, installer-adapter tests, passive seat/input tests, legacy-X display-session tests, and Supervisor/display-session lifecycle integration tests are committed but have **not** executed in a real current checkout.

Fresh GitHub Actions triggered after the real installed-launcher integration still fail before step 1:

```text
source verification run 31314374079
  verify: failure
  steps = null
  logs = null

exact-image run 31314374090
  preflight: failure
  steps = null
  logs = null
  build-probe-record: skipped because preflight never executed

clean-tree run 31314374082
  verify: failure
  steps = null
  logs = null
```

No checkout, Greia test, image build, package transaction, SDL probe, or QEMU step executed in those jobs. Do not burn retries merely to reproduce this condition.

The current execution environment also has no GitHub DNS/network route and no existing authenticated checkout, so it cannot run a true current `make verify` locally.

---

## 3. R7 architecture rule

R7 is **not** “remove Xorg by handing DRM/input authority to every Activity.”

The target invariant remains:

- one Greia-owned seat/display/input authority;
- Activities receive bounded surface/event transport, not broad raw `/dev/input` or DRM-master authority;
- `ActivitySupervisor` owns Activity lifecycle, sandbox and platform-session resources but must not become DRM master;
- shell → Activity → shell presentation/recovery is a platform session concern above runtime-specific process mechanics;
- Python and future Web runtimes share the same display-session semantics;
- serial direct ownership and a small persistent Greia-owned compositor/session broker remain candidates to be measured;
- production Xorg remains until direct-session architecture, resource measurements and physical legacy Intel/Acer evidence are accepted.

Primary R7 documents:

```text
docs/reviews/2026-08-09_R7_X11_DIRECT_GRAPHICS_DEPENDENCY_AUDIT.md
docs/reviews/2026-08-09_R7_SESSION_OWNERSHIP_CANDIDATE_MATRIX.md
docs/testing/2026-08-09_R7_KMSDRM_ACCEPTANCE.md
docs/testing/2026-08-09_R7_QEMU_KMSDRM_ACCEPTANCE.md
```

---

## 4. Real launcher now uses the display-session contract

This is the major change in the latest tranche.

Before this tranche, `DisplaySessionCoordinator` was a strong source contract and evidence seam but the normal installed launcher did not actually compose it around real Activity lifecycle events.

Now the installed path does.

### 4.1 Explicit X11 compatibility backend

New file:

```text
src/greia_launcher/display_session_legacy_x.py
```

Class:

```text
LegacyXDisplaySessionBackend
```

Properties:

```text
backend_id = legacy-x11-session
transport_kind = LEGACY_X11
```

The current Xorg session runs shell and Activity clients in the same X server. Therefore the compatibility backend deliberately does **not** add a window manager, display manager, auth helper, or second X/session process.

`prepare_activity()`:

- requires the current `DISPLAY` endpoint;
- rejects simultaneous `WAYLAND_DISPLAY` ambiguity;
- rejects an explicitly conflicting non-`x11` `SDL_VIDEODRIVER`;
- preserves `XAUTHORITY` only if it actually exists in the process environment;
- returns a typed `DisplayTransport(kind=LEGACY_X11, sdl_video_driver="x11", ...)`.

`present_activity()` and `restore_shell()` are intentionally no-op server mechanics for the compatibility backend because the launcher already stops repainting while the child is active and resumes repainting after cleanup.

### 4.2 Xauthority contract corrected to match the actual xinit path

Greia starts the compatibility session with `xinit` directly, not `startx`.

`DisplayTransport` therefore now requires `DISPLAY` for `LEGACY_X11`, while `XAUTHORITY` is optional. If `XAUTHORITY` is present, it must still be an absolute bounded valid path.

Do not invent an Xauthority path merely to satisfy an abstraction.

Relevant commit:

```text
5e44a3926d6989652945f1d5a9625ec997051cca
```

### 4.3 Installed composition

`src/greia_launcher/composition.py` now defines:

```text
provisional_installed_display_session()
```

which returns:

```text
DisplaySessionCoordinator(LegacyXDisplaySessionBackend())
```

The function is explicitly provisional. Replacing this factory with a measured direct/compositor backend should not require Activity API or lifecycle changes.

Relevant commit:

```text
f1aa18b6fca32d04cdc7b0063184f49b3638493a
```

### 4.4 ActivitySupervisor integration

`ActivitySupervisor` now accepts an optional injected:

```text
display_coordinator: DisplaySessionCoordinator | None
```

Installed launcher composition injects it; non-installed/windowed development keeps `None`, preserving existing development behavior.

For one platform Activity session ID, the supervisor now performs:

```text
platform session ID allocated
→ runtime/package/capability preparation
→ lifecycle transport and brokers created
→ display coordinator prepare_activity(session_id)
→ typed DisplaySessionLease stored
→ lease transport environment applied to child invocation
→ child starts
→ READY observed
→ coordinator.activity_ready(lease)
→ Activity becomes RUNNING
→ normal exit / crash / timeout / forced stop / launch failure
→ runtime cleanup
→ coordinator.activity_ended(lease) / shell recovery
→ resource cleanup
→ authoritative history terminal reason
```

A display restore failure changes the authoritative Activity result to:

```text
platform_failure
```

before final history closure.

This is important: display recovery is now part of Greia platform lifecycle correctness, not a launcher-UI afterthought.

Relevant commit:

```text
07bdc4ef6f1ff8b486e4d369ed1253890a2382a7
```

### 4.5 Fast READY + exit edge

If an Activity publishes READY and exits between two supervisor polls, Greia records the READY event but deliberately does **not** call `present_activity()` for a process that is already dead. It restores the prepared display lease during terminal cleanup.

This avoids briefly presenting a stale/dead child surface merely because a READY marker existed.

### 4.6 Typed display environment becomes authoritative for the child transport

When a display lease exists, the child process receives transport values from the lease rather than arbitrary inherited display selectors.

Supported transport environment names are only:

```text
DISPLAY
XAUTHORITY
WAYLAND_DISPLAY
SDL_VIDEODRIVER
XDG_RUNTIME_DIR
```

Before the typed transport is applied, inherited mutually exclusive selectors are removed:

```text
DISPLAY
XAUTHORITY
WAYLAND_DISPLAY
SDL_VIDEODRIVER
```

`XDG_RUNTIME_DIR` is preserved unless the selected transport explicitly supplies one, because it can also serve non-display/session infrastructure.

No DRM/input device path can be represented by `DisplayTransport`.

### 4.7 Installed launcher activation

`src/greia_launcher/main.py` now builds the provisional display coordinator only on the installed root and injects it into `ActivitySupervisor`.

Relevant commits:

```text
0cec31b2418b88bde25aecd1b484f076e63444aa
5f45c7d44a9f254e5181dc068333a0db7292a658
```

The second commit removes accidental unrelated formatting churn from the first. Cumulative comparison against the pre-integration point confirms only 9 semantic/format lines differ in `main.py`.

---

## 5. New lifecycle regression coverage

New file:

```text
tests/test_supervisor_display_session.py
```

Committed tests cover:

1. typed Wayland transport replacing stale host X/Wayland/SDL selector variables;
2. READY causing prepare → present and normal exit causing restore using one session ID;
3. fast READY+terminal exit recording READY without presenting a dead surface;
4. presentation failure restoring the shell, force-stopping the Activity, and returning `platform_failure`;
5. shell-restore failure converting an otherwise normal process exit into `platform_failure` and leaving the coordinator fail-closed;
6. process-launch failure after display prepare restoring the prepared display session.

New file:

```text
tests/test_display_session_legacy_x.py
```

covers:

- xinit-style `DISPLAY` without XAUTHORITY;
- optional valid XAUTHORITY preservation;
- invalid relative authority rejection;
- missing DISPLAY rejection;
- simultaneous Wayland rejection;
- conflicting SDL backend rejection;
- no-op compatibility present/restore mechanics.

These tests are **committed but unexecuted** in a real current checkout due to the verification boundary above.

---

## 6. One known source hardening edge remains

Do not lose this item.

The display lease and brokers are prepared immediately before final child-environment assembly. `_sanitized_environment()` can raise `ActivityLifecycleError` for a lifecycle/display environment collision or invalid transport environment.

The current `start()` call to `_sanitized_environment()` is not yet wrapped in the common `_failed_launch_session(...)` cleanup path.

The typed current backends should normally provide valid data, so this is not evidence of a current production failure; however, architecturally it should be hardened so **any post-prepare environment assembly failure restores the display and releases brokers/control before returning `platform_failure`**.

This is a good next source patch before further mechanism work.

---

## 7. Existing R7 evidence primitives remain unchanged in status

### Passive probe

`src/greia_platform/direct_graphics_probe.py` inventories without active device acquisition:

- SDL/Pygame versions and compiled video drivers;
- DRM cards/render nodes;
- connector/mode topology;
- libdrm/GBM/EGL/libinput/libseat visibility;
- bounded input-event topology;
- logind/seat/session runtime visibility;
- active VT;
- transport-presence facts.

It still explicitly requires later active KMSDRM and active seat/input evidence.

### Active KMSDRM

`src/greia_platform/kmsdrm_acceptance.py` requires explicit takeover acknowledgement, actual SDL `kmsdrm`, no X/Wayland authority, a valid fullscreen surface, and changing rendered-buffer evidence.

### Serial handoff

`src/greia_platform/kmsdrm_serial_handoff.py` measures:

```text
Shell KMSDRM
→ clean child
→ Shell reacquire
→ abrupt child os._exit(23) without pygame.display.quit()
→ Shell reacquire
```

This remains evidence-only and does not authorize serial direct ownership for production.

### QEMU

`tools/r7_qemu_kmsdrm_handoff_acceptance.py` still performs a two-boot sequence on a disposable clone only.

No real current QEMU PASS exists.

---

## 8. Compositor package benchmark state

`tools/r7_compositor_package_probe.py` retains fixed benchmark candidates:

```text
cage
weston
wlroots-runtime -> libwlroots-0.18
```

It measures incremental closure relative to the **current Xorg production image**. It is not the final Xorg-removed footprint.

The probe:

- never mounts the source production image;
- hashes source before/after, including failure paths;
- uses one disposable clone per candidate;
- exposes none of host `/dev`, `/sys`, or `/run`;
- uses a bounded private tmpfs `/dev` plus fresh procfs;
- uses no-recommends/no-upgrade/no-remove APT policy;
- rejects baseline package changes/removals;
- protects systemd and GRUB boot-state trees;
- cleans APT/log noise;
- removes disposable clones by default on success and failure.

No real package-delta transaction has executed yet.

No compositor package has been added to a Greia production package set.

---

## 9. Activity sandbox state — do not migrate prematurely

Production Activities still carry compatibility concessions inherited from the accepted Xorg path:

- shared host IPC may still be needed for XShm;
- X/Wayland/SDL transport variables remain part of compatibility environment policy;
- `/dev/dri` remains broadly bind-passed.

Do **not** remove these merely because `DisplaySessionCoordinator` is now live.

After real evidence selects the direct/compositor session architecture, the direct profile should:

- remove X socket/Xauthority transport;
- enable IPC isolation where no selected runtime requires shared host IPC;
- remove or tightly broker raw DRM authority for ordinary Activities;
- ensure input events come through Greia-owned seat/session infrastructure rather than raw `/dev/input` access.

---

## 10. Single authoritative exact-image gate

Do not create a parallel builder or R7 gate.

Existing workflow:

```text
.github/workflows/r7-production-image-probe-v3.yml
```

Intended evidence chain:

```text
exact modern-amd64 production image
→ builder cleanup proof
→ installed SDL/passive direct prerequisites
→ Cage package delta
→ Weston package delta
→ wlroots package delta
→ active QEMU KMSDRM when compiled
→ serial clean/crash/reacquire QEMU
→ full source gate
→ persist bounded evidence
```

The evidence document is still absent, so the workflow remains eligible. Its current executions fail before preflight step 1 for the external zero-step condition described above.

Future workflow path filters should explicitly include the new live integration files (`supervisor.py`, `composition.py`, `main.py`, `display_session_legacy_x.py` and their R7 tests) before the evidence document exists/changes the preflight behavior. This is another small source/CI hardening item.

---

## 11. Production decision

**UNCHANGED.**

Production boot remains Xorg/xinit.

No compositor is selected.

Serial direct ownership remains evidence-only.

The fact that `DisplaySessionCoordinator` is now used by the real launcher does not imply a graphics migration. It means the stable ownership/recovery contract is finally exercised by production-path source while the compatibility backend preserves the current mechanism.

Even a future active + serial QEMU PASS is not enough to switch production. R7 still requires:

- exact package/resource comparisons;
- a persistent compositor/session-broker runtime prototype if the measurements justify it;
- idle/peak RSS;
- process/FD count;
- startup and transition latency;
- crash/forced-return behavior;
- authority-boundary comparison against serial ownership and Xorg;
- physical legacy Intel/Acer scanout/input/suspend/crash evidence.

Pi direct-display evidence remains an R8/R14 physical gate after Pi image adapters exist.

---

## 12. Exact next steps

Resume in this order:

1. harden the post-display-prepare environment-assembly failure path so it always enters `_failed_launch_session(...)` and restores display/brokers/control;
2. add the new real-launcher/session integration files to the unified exact-image workflow trigger/preflight path set;
3. run current `make verify` as soon as a real checkout/runner can execute and record the actual count;
4. run the existing single exact-image workflow and preserve all negative evidence;
5. inspect installed SDL and exact Cage/Weston/wlroots package deltas;
6. if KMSDRM exists, execute active and serial QEMU evidence without weakening either test;
7. execute active seat/input evidence;
8. only after those measurements, select the smallest viable compositor/session-broker reference worth a runtime prototype beneath `DisplaySessionCoordinator`;
9. measure compositor vs serial vs Xorg resource/authority/recovery behavior;
10. write the R7 session-architecture ADR from evidence;
11. require physical legacy Intel/Acer acceptance before production migration.

Do not implement a compositor merely to make visible progress while the package/resource evidence is unavailable.

---

## 13. Key commits from the latest tranche

```text
5e44a3926d6989652945f1d5a9625ec997051cca  align LEGACY_X11 transport with direct-xinit authority reality
0c4fb197fa02ba818aed402e20e489779381d110  add explicit legacy X display-session compatibility backend
0e2904679116ee32f4a02616997c71571bd41f27  add legacy X display-session regression tests
07bdc4ef6f1ff8b486e4d369ed1253890a2382a7  bind display-session lease into ActivitySupervisor lifecycle
f1aa18b6fca32d04cdc7b0063184f49b3638493a  compose provisional installed display session explicitly
5ce6d3c85cafcc166c15adfc61f14a6c465d4961  add Supervisor/display-session lifecycle regressions
0cec31b2418b88bde25aecd1b484f076e63444aa  activate coordinator in installed launcher
5f45c7d44a9f254e5181dc068333a0db7292a658  remove accidental launcher formatting churn
```

GitHub branch history is authoritative for exact chronology.
