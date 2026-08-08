# Greia — Architecture Remediation and Platform Completion Plan

**Status:** ACTIVE — mandatory implementation plan until all closure criteria are satisfied  
**Created:** 2026-08-08  
**Source baseline:** `0.13.0-phase0-dev`  
**Authority:** subordinate to the Greia architecture constitution and accepted ADRs; authoritative for implementation ordering and progress tracking while active

---

## 0. Purpose

This plan converts the 2026-08-08 architecture deep review into one ordered implementation program. Greia's architecture is ahead of the current Phase-0 code: the prototype already has useful hardened boundaries, but several are weaker than the constitutional design or are still only documented. This plan closes those gaps without discarding tested behavior, without creating Python/Web-specific copies of platform services, and without weakening the old-hardware or ARM goals.

The ordering is deliberate: **authority → lifecycle → manifest/progression boundary → storage → sessions/progression → runtime adapters → graphics/ARM/Web → packages/backups/parent integration → release evidence**.

When complete, Greia must have a real runtime-neutral Activity platform, per-Activity durable isolation, trusted capability enforcement, platform-owned lifecycle/storage/sessions/progression, direct appliance graphics, peer ARM/x86 support, safe offline Activity installation/update, portable backup/restore, typed parent authority and evidence-backed release claims.

---

# 1. Mandatory continuation protocol

This file is the **active implementation plan**.

Every future implementation session MUST:

1. read `AGENTS.md`;
2. read the architecture constitution and relevant ADRs;
3. read this plan;
4. resume the first incomplete phase below;
5. not create a competing plan or jump ahead around an open safety prerequisite;
6. append progress here after substantive work;
7. update `HANDOVER.md` with exact current phase, verification, blockers and next step;
8. run the required verification before claiming source completion;
9. preserve VM/hardware evidence gaps explicitly;
10. commit coherent work to the canonical GitHub repository.

Do not rewrite old progress entries to make history look cleaner. Append corrections.

When—and only when—all final completion criteria are satisfied, the contributor closing this plan MUST mark it `COMPLETE`, append final evidence, update `HANDOVER.md`, and remove the active-plan reference/special resume instructions from `AGENTS.md`. The plan remains in `docs/plans/` as historical evidence.

---

# 2. Findings being addressed

## F-01 — Active profile overexposure — HIGH

The reviewed Bubblewrap command hid sibling profiles but bound the whole active profile writable. One Activity could therefore reach sibling Activity state and profile-owned data.

**Required:** installed Activities receive only `(profile_id, activity_id)` writable state. Any extra resource is a narrow trusted mount or brokered service.

## F-02 — Environment capability strings are not authority — HIGH

`GREIA_ACTIVITY_CAPABILITIES` is Activity-process state and can be changed by Activity code.

**Required:** environment capability values are descriptive/ergonomic only. Real authority lives outside the Activity process in namespace/device/network/broker policy derived from the validated manifest and platform trust policy.

## F-03 — Blocking Activity lifetime/no watchdog — HIGH

`ActivitySupervisor.launch()` still blocks on `subprocess.run()`.

**Required:** Greia owns spawn, READY, liveness, stop deadline, forced termination, cleanup and normalized exit reason, and can always recover the shell.

## F-04 — Activity-authored global reward values — MEDIUM-HIGH

Prototype manifests can declare concrete reward amounts.

**Required:** Activities describe objectives/events/scores; Greia owns reward economics and global progression policy.

## F-05 — Runtime abstraction not yet concrete — MEDIUM

Runtime type exists in metadata, but validation/execution remain Python-specific.

**Required:** introduce a small runtime-adapter protocol when it enables the second runtime. Keep storage/session/progression/package/backup outside runtime adapters.

## F-06 — Universal storage not implemented — HIGH ecosystem prerequisite

**Required:** runtime-neutral profile+Activity storage API, private files, quotas, atomic writes/checkpoints, schema versions and transactional migrations.

## F-07 — Automatic Session Service not implemented — MEDIUM-HIGH

**Required:** authoritative platform session records independent of Activity cooperation.

## F-08 — Progression/reward service not implemented — MEDIUM-HIGH

**Required:** normalized Activity events feed platform-owned progression/reward state; no direct Activity global-balance writes.

## F-09 — Xorg remains implementation while target is direct graphics — HIGH architectural debt

**Required:** evidence-backed DRM/KMS-first Greia display/session path; Xorg removed from target profiles only after replacement proves equivalent or stronger behavior.

## F-10 — ARM architecture accepted, Pi images absent — HIGH project-goal gap

**Required:** Pi 400 and Pi 500 board/image adapters under the same Activity/profile/storage/progression/package/backup contracts.

## F-11 — Web first-class in architecture, absent in implementation — MEDIUM project-goal gap

**Required:** benchmark embedded engines, select one by evidence, then implement Web as another Activity runtime—never as a child browser product.

## F-12 — `.greiaactivity` install/update path absent — MEDIUM-HIGH

**Required:** stable IDs, version comparison, bounded scanning, staged validation, immutable versions, atomic activation, rollback and save-preserving uninstall.

## F-13 — `.greiabackup` absent — HIGH product requirement

**Required:** portable logical backup/restore across i386/amd64/ARM64, including dormant save namespaces for Activities not currently installed.

## F-14 — Parent privileged authority needs consolidation — HIGH as scope grows

**Required:** typed privileged services, explicit authorization, no arbitrary command endpoint and no broad privileged child Activity.

## F-15 — Boot cover/recovery remains provisional — HIGH release blocker

**Required:** verified branded-only boot cover and graphical recovery without an Escape/details/text path exposing Linux.

## F-16 — Hardware/image claims remain unproven — HIGH release blocker

**Required:** source tests never substitute for QEMU/Acer/Pi evidence, resource measurement or frame-by-frame graphical acceptance.

## F-17 — `/media/pip` migration residue — FIXED IN CURRENT R1 WORK

**Required:** `/media/greia` stays canonical and regression tests prevent active prototype paths from returning.

---

# 3. Cross-cutting rules

- One platform service per concern; no Python/Web copies of storage, progression, backup, install/update or parent policy.
- Trusted authority stays outside Activity processes.
- Profile IDs and Activity IDs are stable durable identity; presentation names are not.
- Authoritative child data is architecture-neutral; no pickle/raw memory/absolute-host-path storage contract.
- Installed-system security falls closed; no silent unsandboxed fallback.
- New platform dependencies require disk/RAM/latency/architecture/security-maintenance evidence.
- No desktop environment, generic window manager or new X11 dependency as a convenience shortcut.
- Introduce abstractions for a concrete capability, not to make diagrams and class names match aesthetically.
- Negative security tests are mandatory: proving the allowed case works is insufficient.

---

# 4. Ordered implementation phases

## R0 — Continuity, plan authority and regression baseline

**Goal:** make this the single active program and lock a verified starting point.

Required:

- commit this plan before implementation work;
- make `AGENTS.md` require it and define resume/progress/removal rules;
- update `HANDOVER.md`;
- preserve Greia naming tests including `/media/greia`;
- run `make verify`.

**Closure:** plan and AGENTS wiring committed; verified baseline remains at least 140/140; no known active technical path uses prototype naming.

**Status:** COMPLETE.

## R1 — Kernel/supervisor-enforced Activity authority and per-Activity storage isolation

**Goal:** make the real installed security boundary match `(profile_id, activity_id)`.

### R1.1 Trusted launch authority

Use an immutable launch-authority object derived by platform code from the validated manifest. It controls actual namespace/device/resource exposure. Activity environment variables only mirror that state.

### R1.2 Writable namespace

Installed Activities must:

- receive only their own Activity data directory writable;
- see host filesystem read-only;
- not receive the complete active profile root;
- not see sibling Activity state;
- receive customization only through a narrow trusted path where required;
- receive removable media read-only only when authorized;
- use a narrow own-profile request/broker path rather than registry access.

### R1.3 Capability behavior

Forging `GREIA_ACTIVITY_CAPABILITIES` must not create mounts, devices, media visibility, profile mutation authority or future broker credentials.

### R1.4 Tests

Prove at source level:

- Activity A cannot receive Activity B state;
- ordinary Activity receives no writable profile customization/progress root;
- forged capability environment cannot expand sandbox authority;
- trusted built-in privileged Activity gets only its narrow resource;
- media is hidden unless authorized;
- missing Bubblewrap still fails closed;
- ordinary Activity receives no profile-request channel.

**Source closure:** least-privilege sandbox command and negative tests pass. Linux Bubblewrap runtime evidence remains a separate R14 evidence item.

**Status:** IN PROGRESS — first source tranche implemented and fully verified; see progress log.

## R2 — Non-blocking Activity lifecycle, readiness and watchdog

Replace blocking one-shot execution with a supervised Activity session. Define states such as `STARTING`, `READY`, `RUNNING`, `STOPPING`, `EXITED`, `FAILED`; bounded READY; timestamps; graceful stop deadline; forced termination; process-tree cleanup; normalized exit reasons (`normal`, `crash`, `launch_failure`, `ready_timeout`, `forced_stop`, `system_shutdown`, etc.); guaranteed shell recovery; responsive shell/event loop.

Tests: normal exit, launch failure, never-ready, freeze, graceful stop, forced kill, cleanup, exactly one active Phase-0 Activity.

## R3 — Manifest semantics and platform-owned progression boundary

Remove/deprecate concrete global reward amounts from Activity manifests. Define objective/event/score semantics; retain useful educational skill metadata; reject direct global reward grants; place global reward mapping in Greia-owned policy.

## R4 — Universal Storage Service and save migrations

Implement runtime-neutral `ActivityStorage`: profile+Activity scope, JSON-compatible key/value, private file/blob area, atomic writes/checkpoints, quota accounting, schema versioning, migration working-copy/snapshot/commit/rollback and portable serialization rules. Python SDK uses it first; Web later uses the same semantics through its bridge.

## R5 — Session Service, event pipeline and Progression/Reward Ledger

Implement authoritative supervisor-created sessions, bounded local history, normalized Activity events, validation/deduplication/idempotency, platform-owned score/progression calculations, reward ledger, parent summaries and backup hooks. Treat this as local child progress, not telemetry.

## R6 — Runtime Adapter abstraction and Python migration

Introduce a minimal adapter protocol for runtime-specific package validation, launch preparation, SDK transport, READY/stop and normalized result. Migrate current Python behavior into it without weakening sandbox rules. Platform Storage/Session/Progression remain outside adapters.

## R7 — Direct Greia graphics/session architecture

Inventory all X11-specific contracts; define typed Display/Input platform interfaces; prototype SDL/direct DRM/KMS path; decide with evidence whether a tiny compositor/session broker is needed for Web surfaces/transitions/crash recovery/input routing; move resolution/input settings behind adapters; benchmark resource cost against Xorg; remove Xorg only after acceptance.

## R8 — ARM64 Pi 400/Pi 500 board/image adapters

Select base/kernel/firmware strategy, implement board/image adapters beneath shared build profiles, add Pi profiles only after adapters exist, and physically prove boot/display/input/audio/network/removable media/shutdown/recovery. Capability class remains separate from CPU architecture.

## R9 — Embedded Web runtime benchmark and adapter

Benchmark WPE/WebKit-style candidates first (alternatives allowed): installed delta, RSS, startup, Canvas2D/SVG/JS/WebAudio, optional WebGL, direct-display integration, i386 feasibility, Pi behavior, security maintenance and crash/forced-return behavior.

Then implement packaged local Web Activities with no browser chrome, no child devtools/downloads/navigation, network denied by default, same lifecycle/watchdog and same Storage/Session/Event services. No authoritative unmanaged localStorage/IndexedDB save silo.

## R10 — `.greiaactivity` package/install/update

Document strict container; stable ID/version policy; package manifest/integrity; safe archive reader rejecting traversal, symlink/hardlink/device/case-collision/bomb hazards; bounded USB/SD discovery; classify New/Update/Installed/Older/Incompatible/Invalid; stage internally; validate again; install immutable version beside current; transactional save migration; atomic activation; rollback; preserve saves on uninstall by default; reserve authenticity/signing separately from SHA-256 integrity.

## R11 — `.greiabackup` portable backup/restore

Document logical archive for profiles, avatars/customization, Activity saves/creations, progression/rewards, bounded session history and installed inventory. Exclude machine secrets/transient state by default. Preserve missing-Activity data as dormant namespaces. Test cross-architecture restore. Select passphrase encryption/KDF only through a dedicated security ADR.

## R12 — Parent privileged service and management integration

Consolidate typed requests for Activity install/update/remove, backup/restore, profiles, display/input/audio, Wi-Fi/network and diagnostics/recovery. Enforce authorization/pairing/revocation and bounded parameters. Never expose arbitrary shell command execution.

## R13 — Boot cover, recovery and graphical continuity

Replace/patch provisional Plymouth path; eliminate child-accessible details/text fallback; add branded recovery states; keep a deliberate root-owned maintainer recovery route; capture firmware-to-profile-picker at high frame rate; test failure transitions. Release adapter registry changes only after evidence.

## R14 — Multi-architecture certification and Phase-0 closure

Close source claims with evidence: exact Acer inventory/profile, real target/live images, C0 footprint, 768 MiB QEMU install/runtime, installer peak memory/time, Bubblewrap runtime behavior, direct graphics/input/audio, Acer USB boot, Pi 400 and Pi 500 physical acceptance, watchdog, install/update/backup/restore flows and no visible Linux text/desktop under supported normal/failure interactions.

---

# 5. Dependency map

```text
R0
 ↓
R1 authority/isolation
 ↓
R2 lifecycle/watchdog
 ↓
R3 manifest/progression boundary
 ↓
R4 storage
 ↓
R5 sessions/events/progression
 ↓
R6 runtime adapters
 ├──────────────→ R9 Web
 └→ R7 direct graphics → R8 Pi adapters

R4 + R5 + R6 → R10 .greiaactivity
R4 + R5      → R11 .greiabackup
R10 + R11    → R12 parent integration
R7 + R12     → R13 boot/recovery
all          → R14 certification
```

Parallel work is allowed only after prerequisites and may never weaken an earlier boundary.

---

# 6. Verification discipline

For substantive source work:

```bash
make verify
```

Focused iteration may use:

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

Remove generated Activity bytecode/caches before final validation where required.

Security phases require positive and negative tests. Hardware/display phases require source tests **plus** exact VM/physical evidence; source structure never proves hardware behavior.

---

# 7. Progress log

## 2026-08-08 — R0 plan creation and continuity wiring

- Implemented: created this plan from the architecture deep review and made it the mandatory active plan in `AGENTS.md`.
- Tests/evidence: reviewed baseline was 140/140 provider-free tests passing.
- Decision: authority/isolation and lifecycle precede graphics/Web/package expansion.
- Commits: `48c38a73148e77884d516ae762b6adc974dbf7af` (plan); `d9222f0e7493b4f92eb99d5ef432abd47b7da294` (AGENTS active-plan/resume/removal rules).
- Status: R0 complete.

## 2026-08-08 — R1.1/R1.2 first authority-isolation tranche

- Implemented: added immutable `ActivityAuthority` in the supervisor; installed Bubblewrap policy now binds only the current Activity's own data directory at `/run/greia-activity-data` instead of the entire active profile; profile registry/platform state remain hidden; `customization.manage` receives a separate narrow customization bind; unauthorized media is hidden at `/media/greia`; media-capable trusted Activity sees the existing root only read-only through the host ro-bind; avatar-change request storage moved into the requesting Activity's own private `.greia/requests/avatar.json` namespace; ordinary Activities receive no avatar-request environment path; SDK environment capability checks are explicitly documented as usability checks rather than security authority.
- Additional security correction: launcher request consumption is restricted to a manifest that actually declares `profile.manage_own`, preventing an ordinary Activity from manually writing a correctly named request into its own data directory and having it consumed solely because it forged process environment state.
- Migration correction: active runtime/system-overlay media defaults now use `/media/greia` rather than `/media/pip`.
- Tests/evidence: new negative test proves forged `GREIA_ACTIVITY_CAPABILITIES` cannot add customization/media authority; least-privilege command tests prove the active profile root/customization are absent for an ordinary Activity; focused profile/API/supervisor tests pass; final local `make verify` passes **141/141 provider-free tests**, project/runtime/activity/asset validation and existing build/source gates.
- Decisions: installed authority is enforced first by supervisor/kernel namespace shape. Direct customization write access remains only for the allowlisted built-in settings Activity as a narrow mount; later universal service/broker work may replace that mount without exposing the profile root.
- GitHub source commits currently landed for this tranche include `42942fb4804134ee04d9103448396aaf8364e1ea` (supervisor authority), `8cbda88a960c9173dd8d75955247873334c3eae3` (SDK capability semantics/media root), `6310d05ba162c0372dca944af1b54027e024dd55` (least-privilege tests), `556d6647afb085f54bd86c3a8f654b3d0f40a892`, `40926ac3ba21565212259d47cbdf547b962c5ebb`, and `0bdb6bb66b8de615e4397388698c0a852cfe43ca` (system-overlay media root).
- Remaining R1 work: ensure all supporting profile/launcher request-path changes are mirrored in the canonical repository; add any final negative tests needed for request consumption; obtain Linux Bubblewrap runtime evidence later under R14. Then mark R1 source closure and begin R2.
- Next exact step: finish canonical-source mirroring for the avatar-request consumption path, rerun `make verify`, mark R1 source closure if no remaining trusted-authority gap exists, then begin non-blocking lifecycle/watchdog design.

---

# 8. Final completion criteria

This plan is complete only when:

- R0–R14 are closed or superseded by an accepted ADR with equivalent/stronger guarantees;
- no HIGH architecture-review finding remains without explicit separate authority/plan;
- per-Activity writable isolation is real;
- Activity-controlled environment cannot create authority;
- lifecycle/watchdog/forced-return is platform-owned;
- storage/session/progression are shared platform services;
- global reward economics are not Activity-authored;
- supported Python/Web runtimes share common platform semantics;
- direct graphics is accepted and X11 is not an unintended required layer;
- Pi 400/500 and required x86 support statuses are evidence-backed;
- install/update and backup/restore satisfy the defined parent workflows;
- boot/recovery meets the no-visible-Linux contract;
- `make verify` passes;
- `HANDOVER.md` is current;
- the active-plan reference/special resume instructions are removed from `AGENTS.md` as the final administrative action.
