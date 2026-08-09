# Greia — Standalone Engineering Handover

**Date:** 2026-08-09  
**Version:** `0.13.0-phase0-dev`  
**Repository:** `frozenpepper/Greia` (private)  
**Integration target:** `main`  
**Active branch:** `r7-direct-graphics`  
**Draft PR:** #4 — `R7: direct graphics/session migration and KMSDRM evidence path`  
**Blocking phase:** **R7 — Direct graphics/session architecture**

---

## 1. Resume state

R0–R6 are source-closed. Do not reopen the old v0.12 recovery incident or deep-refactor the completed authority/storage/session/runtime spine without a concrete defect.

The formerly lost post-v0.12 R5 `history.py` was replaced by a **new reviewed R5 implementation**. Never describe it as historical recovery.

Production Greia still boots through the known **Xorg/xinit compatibility path**. No direct-KMS production profile is enabled. No compositor is selected. Serial direct DRM ownership remains evidence-only.

GitHub is canonical. Always resolve the actual `r7-direct-graphics` branch tip before resuming; documentation-only commits may follow the latest source commit.

---

## 2. Verification boundary — do not overclaim

The last complete provider-free source gate that actually executed successfully remains:

```text
commit: 097f0281888a58f6f26425807ce99d9f35449313
provider-free tests: 232 / 232 PASS
project validation: PASS
bundled Activity validation: PASS
source/shell/footprint gate: PASS
```

Focused R7 checks that actually executed earlier:

```text
isolated DisplaySessionCoordinator fixture: 22 / 22 PASS
isolated compositor-package pure-logic fixture: 14 / 14 PASS
serial KMSDRM fake-SDL/process suite: 8 / 8 PASS before later serial strengthening
```

The latest strengthened serial tests, hardware-settings tests, installer-adapter tests, passive seat/input tests, legacy-X display-session tests, corrected core DisplayTransport tests, and Supervisor/display-session integration tests are committed but have **not** executed in a real current checkout.

Newest Actions runs after the final source/CI hardening still fail before step 1:

```text
source verification: 31316863439
  verify = failure
  steps = null
  logs = null

exact-image evidence: 31316863424
  preflight = failure
  steps = null
  logs = null
  build-probe-record = skipped

clean-tree verification: 31316863437
  verify = failure
  steps = null
  logs = null
```

No checkout, Greia test, image build, package transaction, SDL probe or QEMU step executed in those failures. Do not spend retries merely reproducing this condition.

The assistant execution container also has no GitHub DNS/network route and no authenticated checkout, so it cannot substitute a true current local `make verify`.

---

## 3. R7 architectural invariant

R7 is not “remove Xorg by making each Activity a DRM/input owner.”

The target remains:

- one Greia-owned seat/display/input authority;
- Activities receive bounded surface/event transport rather than broad raw `/dev/input` or DRM-master authority;
- `ActivitySupervisor` owns lifecycle, sandbox and platform-session resources but **must not become DRM master**;
- shell → Activity → shell presentation/recovery is a platform session concern above runtime-specific process mechanics;
- Python and future Web runtimes share the same session semantics;
- serial direct ownership and a small persistent Greia-owned compositor/session broker are candidates to be measured, not assumed;
- production Xorg remains until direct-session architecture, resource measurements and physical legacy Intel/Acer evidence are accepted.

Primary R7 references:

```text
docs/reviews/2026-08-09_R7_X11_DIRECT_GRAPHICS_DEPENDENCY_AUDIT.md
docs/reviews/2026-08-09_R7_SESSION_OWNERSHIP_CANDIDATE_MATRIX.md
docs/testing/2026-08-09_R7_KMSDRM_ACCEPTANCE.md
docs/testing/2026-08-09_R7_QEMU_KMSDRM_ACCEPTANCE.md
```

---

## 4. DisplaySessionCoordinator is now live in the installed launcher

This is the central architectural advance of the latest work.

Previously `DisplaySessionCoordinator` was a strong typed contract/evidence seam but the real installed launcher did not compose it around actual Activity lifecycle events.

Now the installed path does.

### Explicit X compatibility backend

New source:

```text
src/greia_launcher/display_session_legacy_x.py
```

`LegacyXDisplaySessionBackend`:

```text
backend_id = legacy-x11-session
transport_kind = LEGACY_X11
```

It adds no desktop, window manager, display manager, second X server or new authentication process. The current X server already hosts Shell and Activity clients.

Its `prepare_activity()`:

- requires the current `DISPLAY` endpoint;
- rejects simultaneous Wayland ambiguity;
- rejects an explicitly conflicting SDL backend;
- preserves `XAUTHORITY` only if it is actually present;
- returns a typed bounded LEGACY_X11 transport.

`present_activity()` and `restore_shell()` intentionally perform no X-server switch: the compatibility launcher already stops repainting while an Activity owns presentation and resumes afterwards.

### Direct-xinit Xauthority correction

Greia's compatibility service invokes `xinit` directly. The typed LEGACY_X11 transport therefore requires `DISPLAY`, while `XAUTHORITY` is optional-but-validated if present. Greia does not invent an authority file merely to satisfy an abstraction.

Core regression coverage was corrected to match this contract.

Relevant source/test commits:

```text
5e44a3926d6989652945f1d5a9625ec997051cca
0c4fb197fa02ba818aed402e20e489779381d110
0e2904679116ee32f4a02616997c71571bd41f27
67bb08d5872317a79c75fc0cd4a1739e387246cf
```

---

## 5. ActivitySupervisor now owns display-session timing, not display hardware

`ActivitySupervisor` accepts an optional injected `DisplaySessionCoordinator`.

Installed launcher composition injects:

```text
DisplaySessionCoordinator(LegacyXDisplaySessionBackend())
```

Non-installed/windowed development keeps the previous no-coordinator path.

The installed Activity path is now:

```text
Greia session ID
→ runtime/package/capability preparation
→ lifecycle + storage/event brokers
→ display prepare(session_id)
→ exact DisplaySessionLease
→ bounded typed transport applied to child environment
→ child launch
→ READY
→ display present(lease)
→ running Activity
→ normal exit / crash / timeout / forced stop / launch failure
→ runtime cleanup
→ display restore(lease)
→ broker/control cleanup
→ authoritative terminal history reason
```

Display restoration failure changes the authoritative Activity result/history reason to:

```text
platform_failure
```

### Fast READY + exit

If an Activity publishes READY but is already terminal when Greia polls it, READY is recorded but the dead child surface is **not** presented. The prepared lease is restored during terminal cleanup.

### Typed transport overrides stale host selectors

When a display lease exists, its transport is authoritative for the child invocation.

Permitted display transport environment names are only:

```text
DISPLAY
XAUTHORITY
WAYLAND_DISPLAY
SDL_VIDEODRIVER
XDG_RUNTIME_DIR
```

Inherited mutually exclusive selectors are removed before the lease is applied. `XDG_RUNTIME_DIR` is preserved unless the selected transport supplies its own value because it may also serve non-display session infrastructure.

Raw DRM/input device grants cannot be represented by `DisplayTransport`.

Relevant commits:

```text
07bdc4ef6f1ff8b486e4d369ed1253890a2382a7
f1aa18b6fca32d04cdc7b0063184f49b3638493a
0cec31b2418b88bde25aecd1b484f076e63444aa
5f45c7d44a9f254e5181dc068333a0db7292a658
```

The `main.py` integration was deliberately cleaned after an initial noisy write; cumulative comparison against the pre-integration point showed only 9 changed lines in `main.py` plus the new lifecycle regression file.

---

## 6. Post-prepare environment failure is now fail-closed

The previously documented source hardening edge is **closed**.

Commit:

```text
fb4822999e7196fbb5322449bd30eaaddfe602ba
```

After display preparation and broker/lifecycle creation, final child-environment assembly is now inside the common failed-launch boundary.

If final environment assembly raises because of a platform/runtime/display collision, invalid typed data or filesystem error, Greia now:

```text
never launches the child
→ restores the prepared display lease
→ stops session resources
→ cleans lifecycle control
→ closes authoritative history
→ returns platform_failure
```

Regression:

```text
tests/test_supervisor_display_session.py
```

Commit:

```text
72e9b17a4c97c51405f5183215a7132b2997d1c3
```

The test deliberately injects a forbidden lifecycle `HOME` after display preparation and asserts:

- process factory is never called;
- Activity session is FAILED;
- exit reason is `platform_failure`;
- the exact display session is restored to Shell.

The regression is committed but not executed in a real current checkout because of the verification boundary above.

---

## 7. Exact-image workflow now covers the live integration

The second previously documented CI hardening edge is also **closed**.

Existing authoritative workflow only:

```text
.github/workflows/r7-production-image-probe-v3.yml
```

Commit:

```text
24dfc5e34ba97bfc98e967b6fb8463b282483c3a
```

Added to the top-level pull-request path coverage:

```text
src/greia_launcher/composition.py
src/greia_launcher/display_session.py
src/greia_launcher/display_session_legacy_x.py
src/greia_launcher/main.py
src/greia_launcher/supervisor.py
tests/test_display_session.py
tests/test_display_session_legacy_x.py
tests/test_supervisor_display_session.py
```

The same live integration files are represented in the internal preflight changed-path regex, so once generated evidence eventually exists, later ownership/lifecycle changes cannot be silently classified as irrelevant.

The commit diff was inspected immediately after the full-file GitHub contents write: **only the intended path-list and preflight-regex lines changed**. The build, package probe, QEMU, source verification and evidence-recording steps were untouched.

Do not create another R7 builder or parallel evidence workflow.

---

## 8. Existing R7 evidence primitives

### Passive probe

`src/greia_platform/direct_graphics_probe.py` passively inventories:

- Pygame/SDL versions and compiled SDL video drivers;
- DRM card/render nodes;
- KMS connector/mode topology;
- libdrm/GBM/EGL/libinput/libseat presence;
- bounded input-event topology;
- logind/seat/session runtime visibility;
- active VT;
- presence-only display/session transport facts.

It does not open DRM/input devices and still requires active KMSDRM plus active seat/input evidence.

### Active KMSDRM

`src/greia_platform/kmsdrm_acceptance.py` requires explicit takeover acknowledgement, actual selected SDL `kmsdrm`, no residual X/Wayland authority, bounded fullscreen surface dimensions and changing rendered-buffer evidence.

### Serial evidence candidate

`src/greia_platform/kmsdrm_serial_handoff.py` measures:

```text
Shell KMSDRM
→ clean child
→ Shell reacquire
→ abrupt child os._exit(23) without pygame.display.quit()
→ Shell reacquire
```

This remains evidence-only and does not authorize broad Activity DRM/input access or select serial ownership as production architecture.

### Disposable QEMU

`tools/r7_qemu_kmsdrm_handoff_acceptance.py` performs the active + serial two-boot sequence on a disposable clone. The source production image is not mutated.

No real current QEMU PASS exists.

---

## 9. Compositor/reference package benchmark

Fixed measurement candidates remain:

```text
cage
weston
wlroots-runtime -> libwlroots-0.18
```

`tools/r7_compositor_package_probe.py` measures **incremental closure relative to the current Xorg production image**, not the eventual Xorg-removed footprint.

The probe:

- never mounts the source image;
- hashes source before/after including failure paths;
- uses one disposable clone per candidate;
- exposes none of host `/dev`, `/sys` or `/run`;
- uses a bounded private tmpfs `/dev` plus fresh procfs;
- uses no-recommends/no-upgrade/no-remove APT policy;
- rejects baseline package removals/version/architecture changes;
- protects systemd and GRUB boot-state trees;
- removes disposable clones by default on success and failure.

No real package transaction report exists yet. No compositor package has been added to production Greia.

---

## 10. Activity sandbox state — unchanged intentionally

The current Xorg production baseline still carries compatibility concessions:

- shared host IPC may still be needed by XShm;
- X/Wayland/SDL transport variables remain in compatibility environment policy;
- `/dev/dri` remains broadly bind-passed.

Do not remove these merely because the display-session coordinator is now live.

After measured evidence selects a direct/compositor design, the direct profile must:

- remove X socket/Xauthority transport;
- enable IPC isolation where no selected runtime requires shared IPC;
- remove or tightly broker raw DRM authority for ordinary Activities;
- route input through Greia-owned seat/session infrastructure rather than raw child `/dev/input` authority.

---

## 11. Single authoritative exact-image evidence chain

Keep using only:

```text
.github/workflows/r7-production-image-probe-v3.yml
```

Intended sequence:

```text
exact modern-amd64 production image
→ builder success + zero leaked resources
→ installed SDL/passive prerequisites
→ Cage package delta
→ Weston package delta
→ wlroots-runtime package delta
→ if kmsdrm compiled: active QEMU KMSDRM
→ serial clean/crash/reacquire QEMU
→ full current source gate
→ persist bounded evidence
```

If installed SDL lacks KMSDRM, that is a packaging classification, not a PASS.

If active acquisition or serial recovery fails, preserve that negative evidence; do not weaken the gate.

---

## 12. Production decision

**UNCHANGED.**

Production boot remains Xorg/xinit.

No compositor is selected.

Serial direct ownership remains evidence-only.

The live use of `DisplaySessionCoordinator` is not a graphics-backend migration. It means the platform ownership/recovery contract is now exercised by real installed-source lifecycle while the compatibility backend preserves today's mechanism.

Before any production migration, R7 still requires:

- current complete source verification;
- exact installed-SDL and package-delta evidence;
- active KMSDRM and serial recovery evidence where supported;
- active seat/input evidence;
- runtime comparison of serial vs smallest viable compositor/session broker vs Xorg;
- idle/peak RSS, process/FD counts, startup and transition latency;
- crash/forced-return behavior;
- authority-boundary comparison;
- physical legacy Intel/Acer scanout/input/suspend/crash acceptance.

Pi direct-display evidence remains an R8/R14 gate after Pi board/image adapters exist.

---

## 13. Exact next step

The two remaining source/CI hardening items from the previous handover are complete.

**Do not add another display mechanism now merely to show progress.**

Next legitimate sequence when an executable environment is available:

1. run the current full `make verify` and record the actual count;
2. execute the existing unified exact-image workflow;
3. preserve exact SDL classification and Cage/Weston/wlroots package deltas;
4. if KMSDRM exists, run active KMSDRM and serial clean/crash/reacquire QEMU evidence;
5. run active seat/input evidence;
6. from those measurements, choose the smallest viable persistent compositor/session-broker reference worth a runtime prototype, if any;
7. prototype it **below `DisplaySessionCoordinator`**;
8. compare compositor vs serial vs Xorg authority, RSS, process/FD count, startup, transition and recovery behavior;
9. write the R7 session-architecture ADR from evidence;
10. require physical legacy Intel/Acer acceptance before switching production.

Until step 1/2 can genuinely execute, preserve the current Xorg production path and the existing evidence gaps.

---

## 14. Key latest source/CI commits

```text
5e44a3926d6989652945f1d5a9625ec997051cca  align LEGACY_X11 transport with direct-xinit reality
0c4fb197fa02ba818aed402e20e489779381d110  add explicit legacy-X session backend
0e2904679116ee32f4a02616997c71571bd41f27  add legacy-X session regressions
07bdc4ef6f1ff8b486e4d369ed1253890a2382a7  integrate display lease into ActivitySupervisor
f1aa18b6fca32d04cdc7b0063184f49b3638493a  explicit installed display-session composition
5ce6d3c85cafcc166c15adfc61f14a6c465d4961  add Supervisor/display lifecycle regressions
0cec31b2418b88bde25aecd1b484f076e63444aa  activate coordinator in installed launcher
5f45c7d44a9f254e5181dc068333a0db7292a658  remove accidental launcher formatting churn
67bb08d5872317a79c75fc0cd4a1739e387246cf  correct core X transport regression
fb4822999e7196fbb5322449bd30eaaddfe602ba  fail closed on post-prepare environment assembly
72e9b17a4c97c51405f5183215a7132b2997d1c3  test post-prepare cleanup
24dfc5e34ba97bfc98e967b6fb8463b282483c3a  include live integration in exact-image gate
```

Active-plan progress from the live integration is recorded at:

```text
c6af8e930165950d182432f21d6385d8c7288f35
```

GitHub branch history remains authoritative for exact chronology.
