# Greia — Standalone Engineering Handover

**Date:** 2026-08-09  
**Version:** `0.13.0-phase0-dev`  
**Repository:** `frozenpepper/Greia` (private)  
**Integration target:** `main`  
**Active branch:** `r7-direct-graphics`  
**Draft PR:** #4 — `R7: direct graphics/session migration and KMSDRM evidence path`  
**Blocking phase:** **R7 — Direct graphics/session architecture**

---

## 1. Mandatory resume rules

Read, in order:

1. `AGENTS.md`;
2. `README.md`;
3. `docs/architecture/GREIA_ARCHITECTURE.md`;
4. accepted ADRs, especially 0012–0017;
5. `docs/plans/2026-08-08_ARCHITECTURE_REMEDIATION_AND_PLATFORM_COMPLETION.md`;
6. this `HANDOVER.md`;
7. the R7 dependency/candidate reviews and testing protocols referenced below.

GitHub remains the canonical source of truth for source persistence. Resolve the actual branch tip from `r7-direct-graphics` when resuming; continuity files themselves advance the branch.

### CRITICAL paid-execution rule

**Do not enable, trigger, rerun, or add GitHub-hosted Actions without explicit repository-owner authorization for that specific use.**

A generic request such as “move forward” is **not** authorization to spend hosted-runner minutes or other paid resources.

This rule is now persisted in `AGENTS.md` on both `main` and `r7-direct-graphics`.

GitHub may be used normally for source reads/writes, commits, branches and PR metadata. R7 verification/evidence must use local or explicitly owner-approved external execution unless the owner separately authorizes GitHub-hosted Actions.

---

## 2. Historical closure boundary

R0–R6 are source-closed. Do not reopen the old v0.12 recovery incident or deep-refactor the completed authority/storage/session/runtime spine without a concrete defect.

The formerly lost post-v0.12 R5 `history.py` was replaced by a **new reviewed R5 implementation**. Never describe it as recovered historical source.

Production Greia still boots through the known **Xorg/xinit compatibility path**.

No direct-KMS production profile is enabled. No compositor has been selected. Serial direct DRM ownership remains evidence-only.

---

## 3. Verification boundary — do not overclaim

The last complete provider-free source gate that actually executed successfully remains:

```text
commit: 097f0281888a58f6f26425807ce99d9f35449313
provider-free tests: 232 / 232 PASS
project validation: PASS
bundled Activity validation: PASS
source/shell/footprint gate: PASS
```

Focused R7 checks that genuinely executed earlier:

```text
isolated DisplaySessionCoordinator fixture: 22 / 22 PASS
isolated compositor-package pure-logic fixture: 14 / 14 PASS
serial KMSDRM fake-SDL/process suite: 8 / 8 PASS before later serial strengthening
```

The latest strengthened serial tests, hardware-settings tests, installer-adapter tests, passive seat/input tests, legacy-X display-session tests, corrected core DisplayTransport tests, Supervisor/display-session integration tests, post-prepare cleanup regression, and local-evidence-orchestrator tests are **committed but have not executed in a real current checkout**.

Do not infer a current complete test count from source structure.

### Prior unauthorized hosted CI

Earlier work created/triggered GitHub Actions without explicit owner authorization. That was incorrect. Several runs failed before step 1, but even unusable hosted runs may consume paid resources. **Do not reproduce, rerun, or query them as an execution strategy.**

The last referenced pre-correction run IDs were:

```text
31316863439  source verification
31316863424  exact-image preflight
31316863437  clean-tree verification
```

They are historical context only, not a path forward.

---

## 4. Hosted Actions are now structurally neutralized

The repository has been changed so ordinary source commits no longer automatically invoke the hosted verification/evidence machinery.

### `main`

`main:.github/workflows/r0-clean-verify.yml` is now manual-only via `workflow_dispatch`.

Commit:

```text
05df6b97bd95e375c9986c6e045a437df749c6a2
```

The permanent no-unapproved-paid-Actions policy is also in `main:AGENTS.md`.

Commit:

```text
c5f02191876d2038880bbbcd09e98b7bd79d2552
```

### `r7-direct-graphics`

The branch copy of `r0-clean-verify.yml` is manual-only.

```text
21be2d987665fd9638154ddd3da82d0ca3f96591
```

R7-only automatic hosted workflows were removed from `.github/workflows`:

```text
63734d9bf280b36feb0b03ef49989d29ed8f4176  remove r7-source-verify.yml
f3534bf13a83d4018fb5e4d00f614af09ab2e105  remove r7-production-image-probe-v3.yml
```

Branch `AGENTS.md` contains the same hard policy:

```text
1c3f407e62f94820e391cd664e41aa7026ca2685
```

Do not reintroduce automatic Actions as part of PR #4 or a future R7 tranche without explicit owner authorization.

---

## 5. R7 architectural invariant

R7 is not “remove Xorg by making each Activity a DRM/input owner.”

The target remains:

- one Greia-owned seat/display/input authority;
- Activities receive bounded surface/event transport rather than broad raw `/dev/input` or DRM-master authority;
- `ActivitySupervisor` owns lifecycle, sandbox and platform-session resources but **must not become DRM master**;
- shell → Activity → shell presentation/recovery is a platform-session concern above runtime-specific process mechanics;
- Python and future Web runtimes share the same session semantics;
- serial direct ownership and a small persistent Greia-owned compositor/session broker are candidates to be measured, not assumed;
- production Xorg remains until direct-session architecture, resource measurements and physical legacy Intel/Acer evidence are accepted.

Primary R7 references:

```text
docs/reviews/2026-08-09_R7_X11_DIRECT_GRAPHICS_DEPENDENCY_AUDIT.md
docs/reviews/2026-08-09_R7_SESSION_OWNERSHIP_CANDIDATE_MATRIX.md
docs/testing/2026-08-09_R7_KMSDRM_ACCEPTANCE.md
docs/testing/2026-08-09_R7_QEMU_KMSDRM_ACCEPTANCE.md
docs/testing/2026-08-09_R7_EXTERNAL_LINUX_EVIDENCE_EXECUTION.md
```

The last file keeps its historical filename but now contains the **local Linux evidence execution protocol**; GitHub Actions are explicitly not used.

---

## 6. DisplaySessionCoordinator is live in the installed launcher

The backend-neutral `DisplaySessionCoordinator` is now part of the real installed Activity path.

### Explicit legacy-X compatibility backend

Source:

```text
src/greia_launcher/display_session_legacy_x.py
```

`LegacyXDisplaySessionBackend` adds no desktop, window manager, display manager, second X server or new authentication process.

Its compatibility contract matches Greia's direct `xinit` path:

- `DISPLAY` is required;
- SDL is pinned to `x11`;
- `XAUTHORITY` is optional but strictly validated when present;
- simultaneous Wayland ambiguity/conflicting SDL selection fails closed;
- no authority file is fabricated simply to satisfy an abstraction.

Relevant commits:

```text
5e44a3926d6989652945f1d5a9625ec997051cca
0c4fb197fa02ba818aed402e20e489779381d110
0e2904679116ee32f4a02616997c71571bd41f27
67bb08d5872317a79c75fc0cd4a1739e387246cf
```

### Installed lifecycle composition

Installed launcher composition injects:

```text
DisplaySessionCoordinator(LegacyXDisplaySessionBackend())
```

Non-installed/windowed development retains the previous no-coordinator path.

The installed Activity lifecycle is now:

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

Display restoration failure changes the authoritative Activity result/history reason to `platform_failure`.

If READY is observed after the child is already terminal, Greia records READY but does not present a dead child surface. The prepared lease is restored during terminal cleanup.

Relevant commits:

```text
07bdc4ef6f1ff8b486e4d369ed1253890a2382a7
f1aa18b6fca32d04cdc7b0063184f49b3638493a
0cec31b2418b88bde25aecd1b484f076e63444aa
5f45c7d44a9f254e5181dc068333a0db7292a658
```

---

## 7. Typed child display transport is authoritative

When a display lease exists, its transport overrides stale inherited competing selectors.

The display transport can represent only bounded environment data:

```text
DISPLAY
XAUTHORITY
WAYLAND_DISPLAY
SDL_VIDEODRIVER
XDG_RUNTIME_DIR
```

Raw DRM/input grants are not representable by `DisplayTransport`.

`DisplaySessionCoordinator` issues exact-object `DisplaySessionLease` authority tokens and rejects stale/fabricated callbacks, including session-ID reuse across generations.

Transport/backend pairing remains strict:

```text
LEGACY_X11    -> SDL x11
WAYLAND       -> SDL wayland
DIRECT_KMSDRM -> SDL kmsdrm
```

---

## 8. Post-prepare environment failure is fail-closed

The previously open cleanup edge is closed.

Source commit:

```text
fb4822999e7196fbb5322449bd30eaaddfe602ba
```

After display preparation plus broker/lifecycle setup, final child-environment assembly is inside the common failed-launch boundary.

If environment assembly fails, Greia now:

```text
never launches the child
→ restores the prepared display lease
→ stops session resources
→ cleans lifecycle control
→ closes authoritative history
→ returns platform_failure
```

Regression commit:

```text
72e9b17a4c97c51405f5183215a7132b2997d1c3
```

The regression deliberately injects a forbidden lifecycle `HOME` after display preparation and requires no process launch plus shell restoration.

This regression is committed but not currently executed.

---

## 9. R7-A settings/installer decoupling state

The generic hardware-settings path is backend-neutral at source level.

- `src/greia_platform/hardware_session.py` owns semantic watcher/retry/status behavior and consumes an injected `HardwareSessionController`.
- literal `xrandr`, `xinput` and libinput-property command mapping lives in `src/greia_platform/hal_legacy_x.py`.
- launcher composition explicitly selects the current compatibility adapter.
- installer resolution discovery consumes the semantic controller.
- `src/greia_installer/composition.py` is the explicit provisional legacy-X installer composition boundary.

Production behavior remains Xorg.

Do not move X command details back into generic HAL/settings modules.

---

## 10. Existing R7 evidence primitives

### Passive direct-graphics/seat/input probe

`src/greia_platform/direct_graphics_probe.py` passively inventories:

- Pygame/SDL versions and compiled SDL video drivers;
- DRM card/render nodes;
- KMS connector/mode topology;
- libdrm/GBM/EGL/libinput/libseat presence;
- bounded `/dev/input/event*` topology and sysfs names;
- logind/seat/session runtime visibility;
- active VT;
- presence-only X11/Xauthority/Wayland/session transport facts.

It opens no DRM/input devices and still requires:

```text
active_kmsdrm_test_required = true
active_seat_input_test_required = true
```

### Active KMSDRM

`src/greia_platform/kmsdrm_acceptance.py` requires explicit takeover acknowledgement, actual selected SDL `kmsdrm`, no residual X/Wayland authority, bounded fullscreen surface dimensions and changing rendered-buffer hashes.

### Serial evidence candidate

`src/greia_platform/kmsdrm_serial_handoff.py` measures:

```text
Shell KMSDRM
→ clean child
→ Shell reacquire
→ abrupt child os._exit(23) without pygame.display.quit()
→ Shell reacquire
```

A PASS would prove mechanical release/reacquisition only. It does not authorize broad Activity DRM/input access or select serial ownership as production architecture.

### QEMU harnesses

```text
tools/r7_qemu_kmsdrm_acceptance.py
tools/r7_qemu_kmsdrm_handoff_acceptance.py
```

They mutate disposable clones only. The source production image is not booted or mutated by the harnesses.

No real current QEMU PASS exists.

---

## 11. Compositor/reference package benchmark

Fixed measurement candidates remain:

```text
cage
weston
wlroots-runtime -> libwlroots-0.18
```

`tools/r7_compositor_package_probe.py` measures incremental closure relative to the current Xorg production image.

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

## 12. Local Linux evidence orchestrator — NEW execution path

Source:

```text
tools/r7_local_evidence.py
```

Commit:

```text
37b536f758bf4918865f3e0419623c36e81af33c
```

This is an OOP orchestration layer around existing R7 implementations, **not** a second test architecture.

It explicitly reports:

```text
hosted_execution = false
github_actions_used = false
source_image_mutated = false
host_packages_installed_by_tool = false
```

### Preconditions

- controlled/disposable x86-64 Linux host;
- root execution for image/mount/QEMU operations;
- clean disposable/root-owned checkout on `r7-direct-graphics`;
- run root outside repository and not already present;
- host prerequisites installed by the operator beforehand;
- the orchestrator itself never runs `apt-get`.

### Pipeline

```text
clean branch + exact source SHA preflight
→ make verify
→ build/build-image.sh modern-amd64
→ require zero surviving source-image loop association
→ hash immutable production image
→ mount production image read-only
→ run installed passive direct-graphics/seat/input probe
→ unmount/detach and rehash source image
→ existing Cage package probe on disposable clone
→ existing Weston package probe on disposable clone
→ existing wlroots-runtime package probe on disposable clone
→ if kmsdrm_compiled = true:
     existing active QEMU KMSDRM proof
     existing serial clean/crash/reacquire QEMU proof
  else:
     record not-run-kmsdrm-not-compiled
→ make verify again
→ confirm exact source commit + clean worktree
→ confirm production-image SHA unchanged + no loop association
→ write bounded local evidence summary
```

The first failure is authoritative for that evidence attempt. The orchestrator writes `evidence/failure.json` and must not rerun active/serial QEMU in the same attempt merely to obtain PASS.

Generated images/logs/evidence remain outside the repository and are never committed/pushed automatically.

### Local orchestrator safety regressions

New test file:

```text
tests/test_r7_local_evidence.py
```

Commit:

```text
396ef3d490e11605912bce8a74e46e266659fa53
```

Coverage pins:

- run root must be outside repository;
- plan is local-only/no Actions;
- fixed package candidate set;
- passive evidence cannot waive active KMSDRM or active seat/input;
- package report requires immutable source image and no host dev/sys/run exposure;
- baseline package removal/change is rejected;
- KMSDRM-not-compiled skips QEMU instead of manufacturing PASS/failure;
- final summary never overclaims active seat/input or physical Acer evidence.

**These new tests are committed but have not executed in a current real checkout.**

---

## 13. Local operator protocol

Historical filename retained:

```text
docs/testing/2026-08-09_R7_EXTERNAL_LINUX_EVIDENCE_EXECUTION.md
```

It now explicitly defines a **local-only** procedure and states GitHub Actions are not used.

Commit:

```text
6c6ca623dda97406572582c6f5c915b2bf72d1a4
```

Plan-only command from a disposable checkout:

```bash
SOURCE_SHA="$(git rev-parse HEAD)"
RUN_ROOT="/var/tmp/greia-r7-${SOURCE_SHA}"
python3 tools/r7_local_evidence.py --run-root "$RUN_ROOT" --plan-only
```

Execution command:

```bash
sudo -E python3 tools/r7_local_evidence.py --run-root "$RUN_ROOT"
```

Return the entire run root as an archive without modifying/rerunning the source after the attempt.

The protocol recommends a disposable/root-owned checkout because the build/evidence toolchain legitimately requires root; do not use a normal personal working checkout whose ownership must remain untouched.

---

## 14. Activity sandbox state — unchanged intentionally

The current Xorg baseline still carries compatibility concessions:

- shared host IPC may still be needed by XShm;
- X/Wayland/SDL transport variables remain in compatibility environment policy;
- `/dev/dri` remains broadly bind-passed.

Do not remove these merely because `DisplaySessionCoordinator` is now live.

After measured evidence selects a direct/compositor design, the direct profile must:

- remove X socket/Xauthority transport;
- enable IPC isolation where no selected runtime requires shared IPC;
- remove or tightly broker raw DRM authority for ordinary Activities;
- route input through Greia-owned seat/session infrastructure rather than raw child `/dev/input` authority.

---

## 15. Production decision — unchanged

**Production remains Xorg/xinit.**

No compositor is selected.

Serial direct ownership remains evidence-only.

The live coordinator integration is not a graphics-backend migration.

Before any production migration, R7 still requires:

- current complete source verification;
- exact installed-SDL and package-delta evidence;
- active KMSDRM and serial recovery evidence where supported;
- active seat/input evidence;
- runtime comparison of serial vs smallest viable compositor/session broker vs Xorg;
- idle/peak RSS, process/FD counts, startup and transition latency;
- crash/forced-return behavior;
- authority-boundary comparison;
- direct-profile sandbox migration after architecture selection;
- physical legacy Intel/Acer scanout/input/suspend/crash acceptance;
- evidence-backed R7 session-architecture ADR.

Pi direct-display evidence remains an R8/R14 gate after Pi board/image adapters exist.

---

## 16. Exact next step

Do **not** add another display mechanism merely for visible progress.

The next legitimate evidence step is:

1. use a controlled/disposable Linux environment;
2. inspect `tools/r7_local_evidence.py --plan-only`;
3. execute the local orchestrator exactly once for the evidence attempt;
4. preserve the first failure or complete evidence bundle;
5. return the entire run-root archive for review;
6. record the actual current `make verify` count from that run;
7. evaluate installed SDL and exact Cage/Weston/wlroots package deltas;
8. if KMSDRM is compiled, evaluate active and serial QEMU results;
9. separately obtain active seat/input evidence;
10. only from those measurements decide whether a compositor/session-broker runtime prototype is justified.

A compositor prototype, if justified, belongs **below `DisplaySessionCoordinator`** and must be compared against serial ownership and Xorg for authority boundary, RAM, disk, processes/FDs, startup, transitions and recovery.

---

## 17. Key latest commits

```text
0c4fb197fa02ba818aed402e20e489779381d110  explicit legacy-X display-session backend
07bdc4ef6f1ff8b486e4d369ed1253890a2382a7  supervisor/display-session integration
0cec31b2418b88bde25aecd1b484f076e63444aa  installed launcher activation
5f45c7d44a9f254e5181dc068333a0db7292a658  minimize launcher integration diff
fb4822999e7196fbb5322449bd30eaaddfe602ba  fail-closed post-prepare environment cleanup
72e9b17a4c97c51405f5183215a7132b2997d1c3  cleanup regression
05df6b97bd95e375c9986c6e045a437df749c6a2  main hosted verifier -> manual-only
21be2d987665fd9638154ddd3da82d0ca3f96591  R7 branch hosted verifier -> manual-only
63734d9bf280b36feb0b03ef49989d29ed8f4176  remove automatic R7 source workflow
f3534bf13a83d4018fb5e4d00f614af09ab2e105  remove automatic R7 exact-image workflow
1c3f407e62f94820e391cd664e41aa7026ca2685  branch no-paid-Actions policy
c5f02191876d2038880bbbcd09e98b7bd79d2552  main no-paid-Actions policy
37b536f758bf4918865f3e0419623c36e81af33c  local Linux R7 evidence orchestrator
396ef3d490e11605912bce8a74e46e266659fa53  local evidence safety regressions
6c6ca623dda97406572582c6f5c915b2bf72d1a4  local-only operator protocol
```

---

## 18. Resume checklist

Before touching source:

```text
[ ] read AGENTS.md, especially paid-execution rule
[ ] read active plan and this handover
[ ] confirm branch r7-direct-graphics
[ ] resolve actual branch tip from GitHub
[ ] do not trigger/query/rerun GitHub Actions as an execution strategy
[ ] preserve production Xorg/xinit
[ ] preserve current X compatibility sandbox concessions until architecture evidence exists
[ ] do not add compositor package/runtime before package/resource evidence
[ ] never make ActivitySupervisor DRM master
[ ] never claim unexecuted tests passed
```

The correct next engineering information is **local Linux evidence**, not another speculative display implementation.
