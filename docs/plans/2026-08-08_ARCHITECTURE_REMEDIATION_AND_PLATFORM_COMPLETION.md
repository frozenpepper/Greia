# Greia — Architecture Remediation and Platform Completion Plan

**Status:** ACTIVE — mandatory implementation plan until all closure criteria are satisfied
**Created:** 2026-08-08
**Source baseline:** `0.13.0-phase0-dev`
**Authority:** subordinate to the Greia architecture constitution and accepted ADRs; authoritative for implementation ordering and progress tracking while active
**Plan audit:** 2026-08-08 full re-audit completed after an assistant-response consistency failure. See `docs/reviews/2026-08-08_ACTIVE_PLAN_AUDIT_AND_CORRECTION.md`.

---

## 0. Purpose

This plan converts the 2026-08-08 architecture deep review into an ordered implementation program. Greia already has a useful hardened Phase-0 prototype, but several trust, lifecycle, storage, graphics, multi-architecture, package, backup, and recovery boundaries remain provisional or only architectural.

The plan deliberately places **authority, isolation, lifecycle, durable identity, and data ownership before ecosystem expansion**. Web, package distribution, parent features, and polished hardware support must be built on trusted common platform services instead of runtime-specific shortcuts.

When this plan is complete, Greia must have:

- one runtime-neutral Activity model;
- per-Activity durable isolation;
- platform-computed effective permission grants;
- platform-owned Activity lifecycle/watchdog;
- stable Activity identities;
- shared Storage, Session, Event, Progression, and Reward services;
- a semantic Device Capability/HAL layer;
- Python and Web runtime adapters using the same platform services;
- direct appliance graphics without accidental X11 dependence;
- peer i386/x86-64 and Raspberry Pi 400/500 architecture support;
- safe `.greiaactivity` installation/update;
- portable `.greiabackup` backup/restore;
- typed parent authority;
- rollback-safe Greia OS/runtime updates and preserve-profile recovery;
- evidence-backed hardware/release claims.

---

# 1. Mandatory continuation protocol

This file is the **single active implementation plan**.

Every implementation session MUST:

1. read `AGENTS.md`;
2. read ADR 0012, ADR 0013, ADR 0014, and relevant narrower ADRs;
3. read this plan and the latest `HANDOVER.md`;
4. resume the first incomplete blocking phase;
5. not invent a competing plan or skip an open safety prerequisite;
6. append an accurate progress entry here after substantive work;
7. update `HANDOVER.md` with exact state, tests/evidence, blockers, and next step;
8. run the verification required by the phase before claiming source completion;
9. preserve VM/physical-hardware evidence gaps explicitly;
10. commit coherent work to the canonical GitHub repository.

Do not rewrite old progress entries to make history look cleaner. Append corrections.

When—and only when—all final completion criteria are satisfied, the contributor closing this plan MUST mark it `COMPLETE`, append final evidence, update `HANDOVER.md`, and remove the active-plan reference/special resume instructions from `AGENTS.md`. The completed plan remains under `docs/plans/` as historical evidence.

---

# 2. Findings being addressed

## F-01 — Active profile overexposure — HIGH

The reviewed Bubblewrap boundary hid sibling profiles but originally exposed the entire active profile writable.

**Required:** installed Activities receive only `(profile_id, activity_id)` writable state. Extra writable resources are narrow trusted mounts or brokered operations.

## F-02 — Activity-process environment is not authority — HIGH

`GREIA_ACTIVITY_CAPABILITIES` can be changed by Activity code.

**Required:** process environment is descriptive only. Effective authority is issued outside the Activity process.

## F-03 — Blocking Activity lifetime / no watchdog — HIGH

`ActivitySupervisor.launch()` currently blocks on `subprocess.run()`.

**Required:** Greia owns spawn, READY, liveness, graceful stop, forced process-tree termination, cleanup, normalized exit reason, and shell recovery.

## F-04 — Activity-authored global reward values — MEDIUM-HIGH

Prototype manifests can declare concrete global reward amounts.

**Required:** Activities report objectives/events/scores; Greia owns reward economics and global progression.

## F-05 — Runtime abstraction is metadata-only — MEDIUM

Runtime type exists, but validation/execution are Python-specific.

**Required:** a runtime adapter/session seam before Web, without duplicating platform services.

## F-06 — Universal Storage Service absent — HIGH ecosystem prerequisite

**Required:** runtime-neutral KV/private-file storage, quotas, atomic writes/checkpoints, schema versions, transactional migrations, and portable formats.

## F-07 — Automatic Session Service absent — MEDIUM-HIGH

**Required:** authoritative platform session records independent of Activity cooperation.

## F-08 — Progression/Reward Ledger absent — MEDIUM-HIGH

**Required:** normalized events feed platform-owned progression/rewards; no direct Activity balance writes.

## F-09 — Xorg remains while target is direct graphics — HIGH architectural debt

**Required:** evidence-backed DRM/KMS-first Greia display/session path. Xorg remains only where an explicitly certified compatibility adapter is still proven necessary.

## F-10 — ARM is first-class architecturally but Pi images are absent — HIGH

**Required:** Pi 400 and Pi 500 board/image adapters under the same Activity/profile/storage/progression/package/backup contracts.

## F-11 — Web is first-class architecturally but absent — MEDIUM

**Required:** benchmark/select an embedded engine and implement Web as another Activity runtime, never a child browser product.

## F-12 — `.greiaactivity` install/update absent — MEDIUM-HIGH

**Required:** safe archive/import, stable identity/version comparison, staging, immutable installs, atomic activation, rollback, and save-preserving uninstall.

## F-13 — `.greiabackup` absent — HIGH product requirement

**Required:** logical cross-architecture backup/restore, including dormant state for temporarily missing Activities.

## F-14 — Parent privileged authority needs consolidation — HIGH

**Required:** typed privileged services and explicit authorization; no arbitrary shell bridge and no broad privileged child Activity.

## F-15 — Boot cover/recovery remains provisional — HIGH release blocker

**Required:** branded-only boot/recovery without child-accessible Linux details/text fallback.

## F-16 — Hardware/image claims remain unproven — HIGH release blocker

**Required:** QEMU/Acer/Pi evidence, resource measurement, and frame-by-frame graphical acceptance; source tests never substitute for hardware proof.

## F-17 — `/media/pip` migration residue — FIXED / REGRESSION-PROTECTED

**Required:** `/media/greia` remains canonical.

## F-18 — Capabilities, permission requests, and trust origin are conflated — HIGH

Current prototype `runtime.capabilities` mixes ordinary requirements (`display`, `pointer`, `audio.basic`) with privileged requests (`customization.manage`, `profile.manage_own`, `removable_media.read`). The first R1 `ActivityAuthority` also derives booleans directly from the validated manifest, while privileged trust is currently restricted by Activity-ID allowlist.

A manifest request must never equal a grant, and an external package must not obtain system privilege by claiming a reserved ID.

**Required:** a platform `PermissionBroker` computes effective session grants from package trust/origin, manifest request, runtime/hardware capability, build policy, parent policy, and platform security policy. Built-in/system privilege is tied to trusted package identity/origin, not title or Activity ID alone.

## F-19 — Stable Activity IDs must be finalized before durable services — HIGH

Storage, sessions, progression, updates, and backup are keyed by Activity ID, while current built-ins still use prototype IDs.

**Required:** before durable Storage/Session/Progression implementation, either accept existing IDs as permanent or migrate to the canonical namespace with explicit compatibility mapping.

## F-20 — Lifecycle and runtime-adapter ordering was inconsistent — MEDIUM-HIGH

R2 requires runtime-neutral READY/STOP/TERMINATE semantics, while the old plan deferred the runtime seam to R6.

**Required:** R2 introduces the minimal runtime-session/adapter seam needed for lifecycle now; R6 later completes runtime-specific validation/selection integration.

## F-21 — Device Capability Service / HAL core was missing — HIGH

The constitution requires semantic device capabilities and typed Display/Input/Audio/Media/Power/Network services.

**Required:** R6 establishes the HAL/capability authority before direct graphics, Pi, Web, package compatibility, and mature PermissionBroker decisions.

## F-22 — R7/R8 evidence dependency was partially circular — HIGH

Pi physical direct-display evidence cannot be required before the Pi image adapter exists.

**Required:** R7 closes display/session architecture plus x86/VM evidence; R8 then implements Pi board/image adapters and ARM-specific display/input/audio evidence. R14 performs final cross-family certification.

## F-23 — Canonical GitHub continuity is incomplete for binary assets — MEDIUM continuity risk

At audit time `assets/icons/core/v1/128/unicorn.png` exists in the working tree but returns 404 from GitHub, while `AGENTS.md` calls GitHub canonical.

**Required:** R0 is not complete until the repository contains the full build/test working tree, including required binaries, or a documented repository-managed external-asset mechanism exists. Chat-session ZIPs are not canonical project storage.

## F-24 — OS/runtime update and preserve-profile recovery were missing — MEDIUM-HIGH

ADR 0012 requires signed, rollback-safe Greia OS/runtime updates, offline bundles, boot-health confirmation, and preserve-profile reinstall.

**Required:** explicit R13B before final certification.

---

# 3. Cross-cutting rules

1. **One platform service per concern.** Do not create Python/Web copies of storage, sessions, progression, package, backup, or parent policy.
2. **Capability, permission request, and grant are distinct.** Activity code may request; only the platform grants.
3. **Trusted authority stays outside Activity processes.** Effective grants come from a PermissionBroker using package trust/origin plus policy/capability inputs.
4. **Stable identities precede durable state.** Profile IDs and Activity IDs are persistent cross-machine identity; titles are not.
5. **Portable data only.** No pickle/raw memory/absolute host paths/machine IDs as authoritative portable state.
6. **Fail closed.** Installed Greia never silently weakens a required security boundary.
7. **Resource evidence before dependencies.** Disk/RAM/latency/architecture/security-maintenance cost is part of acceptance.
8. **No desktop creep.** No desktop environment, generic WM, or new X11 dependency as a convenience shortcut.
9. **Refactor for concrete boundaries.** Do not rewrite working code merely to make class names match diagrams.
10. **Negative security tests are mandatory.** The unauthorized case must be proven to fail.
11. **Reject a generic Resource Service.** Durable files belong to Storage; static assets to Asset/package; removable media to Media Service; temporary runtime data to Runtime Adapter/session; package cache to Package Manager; hardware availability to HAL.

---

# 4. Ordered implementation phases

## R0 — Continuity, canonical repository, and regression baseline

**Goal:** make this plan and GitHub a real reproducible continuation point.

Required:

- plan committed before implementation changes;
- `AGENTS.md` requires this plan and defines resume/progress/removal rules;
- `HANDOVER.md` current;
- Greia naming regressions covered, including `/media/greia`;
- `make verify` baseline recorded;
- complete build/test working tree represented in GitHub, including required binary assets, or a documented repository-managed external-asset mechanism.

**Closure:** all above true.
**Status:** **COMPLETE** — canonical source/build/test/assets are in GitHub and the clean-clone source gate passes. Physical/hardware evidence remains assigned to later phases.

## R1 — PermissionBroker, trusted Activity authority, and per-Activity isolation

**Goal:** make the installed security boundary match `(profile_id, activity_id)` and ensure packages cannot self-grant privilege.

### R1.1 Effective grants and package trust

Introduce an immutable platform-issued grant object computed by a trusted `PermissionBroker` from:

- trusted package origin/tier;
- manifest permission request;
- runtime capability;
- hardware capability;
- build/profile policy;
- parent policy;
- platform security policy.

The current `ActivityAuthority.from_manifest()` is a useful first safety patch but **PROVISIONAL**. R1 cannot close while the supervisor can derive privilege directly from manifest fields or while built-in privilege is protected only by Activity ID.

Until R3 splits the manifest schema, the overloaded prototype capability field may be translated by trusted platform policy, but it is never itself the grant.

### R1.2 Writable namespace

Installed Activities must:

- receive only their own Activity-data namespace writable;
- see host filesystem read-only;
- not receive the complete active profile root;
- not see sibling Activity state;
- receive customization only through a narrow trusted path/broker where required;
- receive removable media read-only only when granted;
- use narrow own-profile request/broker paths rather than registry access.

### R1.3 SDK context is descriptive

Environment/context may advertise granted features for ergonomics, but cannot authorize effects. Brokered APIs should use supervisor-established session identity/opaque handles where practical.

### R1.4 Negative tests

Prove:

- Activity A cannot receive Activity B state;
- ordinary Activity receives no writable profile customization/progress root;
- forged `GREIA_ACTIVITY_CAPABILITIES` cannot expand authority;
- non-system package claiming a reserved/system Activity ID cannot obtain privileged grants;
- fabricated manifest-like input cannot mint authority;
- privileged system Activity receives only its narrow grant;
- media is hidden unless granted;
- missing Bubblewrap fails closed.

**Source closure:** least-privilege mount shape and PermissionBroker/trust-origin tests pass. Linux Bubblewrap runtime evidence remains a later/final evidence item.
**Status:** **IN PROGRESS** — per-Activity mount patch is real and verified; PermissionBroker/trust-origin work remains.

## R2 — Runtime-neutral Activity lifecycle, readiness, watchdog, forced return

**Goal:** Greia owns Activity lifetime and guaranteed return-to-shell behavior.

Work:

- introduce the minimal runtime lifecycle seam now (`RuntimeSession`/equivalent protocol);
- implement Python process/session behind it;
- replace blocking one-shot launch with a supervised Activity session;
- states such as `STARTING`, `READY`, `RUNNING`, `STOPPING`, `EXITED`, `FAILED`;
- bounded READY handshake;
- spawn/ready/end timestamps;
- graceful stop with deadline;
- forced process-tree termination;
- normalized exit reasons;
- guaranteed shell recovery independent of Activity cooperation;
- responsive shell/event loop;
- pause/checkpoint capability treated as optional, not universal.

Tests: normal exit, launch failure, never-ready, freeze, graceful stop, forced kill, cleanup, one active Phase-0 Activity.

## R3 — Durable Activity identity and normalized manifest semantics

**Goal:** settle identity and authority semantics before durable services depend on them.

Work:

- decide permanent Activity-ID namespace; migrate current prototype IDs now if needed;
- define alias/compatibility migration for any renamed built-ins;
- split **capability requirements** from **permission requests**;
- migrate overloaded prototype `runtime.capabilities`;
- remove/deprecate concrete global reward amounts;
- define normalized objective/event/score semantics;
- retain useful educational skill metadata;
- define Greia-owned progression policy schema, leaving ledger execution to R5;
- reject manifests that directly grant global rewards or self-authorize privileged permissions.

**Closure:** IDs are permanent/migrated; capabilities and permissions are distinct; no Activity-authored global reward economics remain.

## R4 — Universal Storage Service and transactional save migrations

**Goal:** implement one portable storage contract for Python/Web/future runtimes.

Work:

- `ActivityStorage` interface keyed by platform-chosen `(profile_id, activity_id)`;
- JSON-compatible KV state;
- private file/blob area using relative names only;
- atomic writes/checkpoints;
- quota accounting and machine protected-free-space policy;
- schema versions;
- migration snapshot/working copy/validate/commit/rollback;
- architecture-neutral serialization;
- Python SDK integration;
- transport-neutral operations suitable for Web bridge;
- explicit transition from today's raw HOME/XDG convention: authoritative portable saves increasingly use `ActivityStorage`; retained raw files cannot bypass quota/migration/backup semantics.

## R5 — Session Service, events, Progression Engine, Reward Ledger

**Goal:** make session history and progression platform-owned.

Work:

- automatic authoritative session records from supervisor lifecycle;
- bounded local history;
- normalized Activity event envelope;
- validation/deduplication/idempotency;
- platform-owned score/progression calculations;
- auditable reward ledger;
- parent-readable summaries;
- backup hooks;
- local progress is not analytics and is not uploaded by default.

## R6 — Device Capability/HAL core and full Runtime Adapter integration

**Goal:** establish platform-owned hardware capability and runtime selection before graphics/Pi/Web/package compatibility work matures.

### R6.1 Device Capability Service / HAL

Typed semantic interfaces for at least:

- capability snapshot/probing;
- Display Service;
- Input Service;
- Audio Service;
- Removable Media Service;
- Power Service;
- Network Service.

Existing Xorg/xinput/xrandr/systemd behavior may temporarily sit behind provisional adapters. PermissionBroker and compatibility checks consume platform-owned capability facts, not Activity guesses.

### R6.2 Runtime integration

Complete the runtime-adapter protocol begun minimally in R2 for runtime-specific static/package validation, launch preparation, SDK transport, lifecycle session creation, cleanup, and normalized results. Migrate Python behavior without duplicating Storage/Session/Progression.

## R7 — Direct Greia graphics/session architecture

**Goal:** implement the target appliance display/session model without circular Pi evidence requirements.

Work:

- inventory `DISPLAY`, Xauthority, XShm, `xinput`, `xrandr`, Xorg package/service assumptions;
- typed Display/Input implementations behind R6 interfaces;
- prototype SDL direct DRM/KMS/KMSDRM path;
- determine by measurement whether a tiny compositor/session broker is justified for Web surfaces, transitions, crash recovery, and input routing;
- define shell↔Activity surface ownership/recovery;
- move display/input settings behind platform adapters;
- benchmark disk/RAM/startup/latency against Xorg;
- retain Xorg only as an explicit compatibility adapter if physical evidence requires it.

**R7 closure:** direct architecture plus x86/VM and available x86 physical evidence accepted; no Activity API depends on X11. Pi-specific display evidence is deferred explicitly to R8.

## R8 — Raspberry Pi 400 / Pi 500 ARM64 board and image adapters

**Goal:** make ARM a shipping peer, not a later port.

Work:

- select base/kernel/firmware strategy;
- board/image boot adapters beneath the same build-profile schema;
- Pi profiles only after adapters exist;
- integrate R7 direct display/session backend;
- test boot/display/input/audio/network/removable media/shutdown/recovery;
- close Pi-specific HAL/display/input work;
- measure capability/resource classes independently of architecture.

## R9 — Embedded Web runtime benchmark and implementation

**Goal:** add Web without turning Greia into a browser appliance.

Stage A benchmark: WPE/WebKit-style candidates first, alternatives allowed; installed delta, idle/peak RSS, cold/warm startup, Canvas2D/SVG/JS/WebAudio, optional WebGL, R7 display/session integration, i386 feasibility, Pi behavior, security maintenance, crash/forced-return.

Stage B adapter: packaged local content only; no child browser chrome/navigation/downloads/devtools; network denied by default; same Storage/Session/Event services and lifecycle/watchdog as Python; no authoritative unmanaged localStorage/IndexedDB save silo.

## R10 — `.greiaactivity` package/install/update

**Goal:** safe simple parent-facing offline Activity distribution.

Work:

- documented strict container;
- stable Activity ID + version policy;
- package manifest with integrity metadata;
- bounded archive reader rejecting traversal, symlinks/hardlinks, device nodes, case collisions, bombs;
- bounded USB/SD discovery without autorun;
- classify New / Update / Installed / Older / Incompatible / Invalid;
- stage internally and revalidate;
- immutable versions beside current;
- transactional save migration;
- atomic activation and rollback;
- preserve saves on uninstall by default;
- explicit package trust/origin states;
- external package cannot acquire built-in/system privilege merely by claiming an ID;
- signature/authenticity strategy appropriate to the distribution model; SHA-256 is integrity, not publisher authenticity.

## R11 — `.greiabackup` portable backup/restore

**Goal:** move a child's complete logical world between machines/architectures.

Work:

- documented logical archive;
- profiles, avatars/customization, Activity saves/creations, progression/rewards, bounded sessions, installed inventory;
- machine secrets/transient state excluded by default;
- missing-Activity data preserved as dormant namespaces;
- cross-architecture restore tests;
- version/migration rules;
- integrity checks;
- production passphrase encryption only after dedicated security ADR;
- parent USB/SD export/import flow.

## R12 — Parent privileged service and management integration

**Goal:** extend the trusted broker/service foundation from R1 into complete parent management without turning the HTTP application into a monolith.

Typed operations for Activity install/update/remove, backup/restore, profiles, display/input/audio, Wi-Fi/network, diagnostics/recovery, authorization/pairing/revocation, and storage administration. No arbitrary command execution endpoint.

## R13 — Boot cover, recovery, and graphical continuity

**Goal:** satisfy “Linux never appears” without destroying recovery.

Work: replace/patch provisional Plymouth path; no child details/text fallback; branded failure/recovery surfaces; launcher/display/service recovery without shell exposure; deliberate root-owned maintainer recovery route; high-frame-rate firmware→profile-picker capture; failure-transition tests. Release registry changes only after evidence.

## R13B — Greia OS/runtime update and preserve-profile recovery

**Goal:** separate safe system/runtime updates from Activity updates.

Work:

- signed system-update metadata/artifacts;
- complete verification before activation;
- free-space/power preflight;
- rollback-safe/atomic activation strategy suitable for resource constraints;
- boot-health confirmation and rollback;
- offline update bundles;
- explicit Activity runtime/API compatibility behavior;
- preserve-profile reinstall/recovery using logical `.greiabackup` semantics;
- parent UI delegates to R12 typed services.

## R14 — Full multi-architecture certification and Phase-0 closure

Evidence includes:

- exact Acer inventory/profile;
- real target/live images;
- installed C0 footprint below hard limit;
- 768 MiB QEMU installer/runtime;
- installer peak memory/time;
- Bubblewrap/effective-grant behavior;
- direct graphics/input/audio;
- non-destructive Acer USB boot;
- Pi 400 and Pi 500 physical acceptance;
- Activity watchdog/forced-return;
- Activity install/update/rollback;
- backup/restore cross-architecture;
- OS update/rollback/recovery;
- no visible Linux text/desktop under supported normal/failure interactions.

---

# 5. Dependency map

```text
R0 canonical repository + governance
 ↓
R1 trust / PermissionBroker / per-Activity authority
 ↓
R2 runtime-neutral lifecycle + minimal adapter seam
 ↓
R3 stable IDs + capability/permission/event semantics
 ↓
R4 universal storage
 ↓
R5 sessions/events/progression
 ↓
R6 Device Capability/HAL + full runtime integration
 ├────────────→ R7 direct graphics/session (x86/VM evidence)
 │                  └────────→ R8 Pi image + ARM direct-display evidence
 ├────────────→ R9 Web runtime (uses R7 session/surface architecture)
 └────────────→ R10 .greiaactivity

R4 + R5             → R11 .greiabackup
R1 + R6 + R10 + R11 → R12 parent integration
R7 + R12            → R13 boot/recovery
R11 + R12           → R13B OS/runtime update + preserve-profile recovery
all                  → R14 certification
```

The blocking safety spine through R6 remains ordered. After R6, explicitly independent tracks may proceed in parallel when their prerequisites are satisfied. No later track may weaken an earlier boundary.

---

# 6. Verification discipline

For every substantive source change:

```bash
make verify
```

Focused iteration may use:

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

Security phases require positive **and negative** tests. Hardware/display phases require source tests plus exact VM/physical evidence; source structure never proves hardware behavior.

---

# 7. Progress protocol

Append entries using:

```text
YYYY-MM-DD — Phase Rx.y
- Implemented:
- Tests/evidence:
- Decisions:
- Remaining blockers:
- Next exact step:
- Commit(s):
```

Do not rewrite old entries; append corrections.

---

# 8. Progress log

## 2026-08-08 — R0 plan creation

- Implemented: architecture-remediation plan created from the v0.13 deep review.
- Tests/evidence: pre-plan reviewed baseline was 140/140 provider-free tests passing.
- Decisions: authority/isolation and lifecycle precede graphics/Web/package expansion.
- Remaining blockers: R0 AGENTS/HANDOVER wiring; R1 implementation.
- Next exact step: commit plan, then wire `AGENTS.md`.
- Commit(s): `48c38a73148e77884d516ae762b6adc974dbf7af`; `d9222f0e7493b4f92eb99d5ef432abd47b7da294`.

## 2026-08-08 — R1.1/R1.2 first authority-isolation tranche

- Implemented: immutable `ActivityAuthority`; installed Bubblewrap binds only own Activity data writable; whole-profile writable bind removed; customization becomes a narrow privileged bind; unauthorized media hidden at `/media/greia`; avatar request moved into requesting Activity private namespace; SDK capability environment documented as non-authoritative.
- Tests/evidence: focused tests pass; full `make verify` passed **141/141** after first tranche; later focused avatar-request run passed.
- Decisions: namespace/device/mount shape enforces the first safety improvement; environment strings cannot expand authority. Direct customization write access remains temporary and should move behind platform service/broker semantics.
- Remaining blockers at log time: final full gate after avatar tightening; source commits; Linux Bubblewrap evidence; trusted broker design.
- Next exact step at log time: full verification, commit tranche, then eliminate remaining Activity-controlled authority.
- Commit(s): pending at this historical log-entry time.

## 2026-08-08 — Full active-plan audit and correction

- Implemented: re-read the entire plan against ADR 0012/0013/0014, current source, current GitHub state, and a fresh `make verify`; corrected trust semantics and dependencies without erasing earlier history.
- Tests/evidence: fresh local `make verify` passed **141/141**. GitHub `src/greia_launcher/supervisor.py` contains the R1 per-Activity mount patch. GitHub spot-check for `assets/icons/core/v1/128/unicorn.png` returned 404, proving canonical-repository completeness is not yet true.
- Corrections: rejected the chat-only generic `Resource Service`; added PermissionBroker/trust-origin requirements; separated capabilities/permissions/grants; moved minimal runtime lifecycle seam into R2; made stable Activity IDs an R3 prerequisite; added HAL/Device Capability Service to R6; de-circularized R7/R8 evidence; clarified early broker vs R12 parent integration; added R13B OS/runtime updates and preserve-profile recovery.
- Remaining blockers: R0 incomplete for GitHub binaries; R1 still derives effective authority provisionally from validated manifest fields and protects privileged capabilities with an Activity-ID allowlist.
- Next exact step: complete canonical GitHub working tree, then replace `ActivityAuthority.from_manifest()` with PermissionBroker-issued effective grants and add reserved-ID/package-origin spoof tests.
- Commit(s): `7510c0c56e5c80700d9dd830dd067ff83267770b` (audit document); this plan-correction commit.

## 2026-08-09 — R6.2 snapshot-bound launch authority

- Implemented: bound `ActivityAuthority` to the trusted `DeviceCapabilitySnapshot.token` used by PermissionBroker; RuntimeManager launch preparation can require an expected snapshot token; ActivitySupervisor now requires runtime compatibility to use the same semantic device observation before process creation.
- Tests/evidence: positive token-binding coverage plus negative RuntimeManager and Supervisor stale-snapshot tests; focused R6 tests and the complete currently-recoverable unit suite run in GitHub CI.
- Decisions: semantic snapshot equality, not wall-clock time, is the launch-coherence invariant. A changed snapshot fails closed before child creation. RuntimeManager stays independent of PermissionBroker types; Supervisor coordinates via the opaque token.
- Remaining blockers: full `make verify` is still blocked by the separately lost post-v0.12 R5 `src/greia_platform/history.py`; R6 installed composition and broader closure review remain open.
- Next exact step: review the real installed launcher composition path and R6.2 lifecycle/SDK cleanup responsibilities against accepted ADRs, then close remaining runtime-integration gaps without starting R7.
- Commit(s): this tranche commit.

## 2026-08-09 — R6.2 universal storage launch transport

- Implemented: installed launcher composition now loads the platform storage policy and injects one `ActivityStorageService` into `ActivitySupervisor`; each Activity launch opens the profile/Activity durable namespace, starts an ephemeral `ActivityStorageBroker`, exposes only its Unix socket plus per-session token, mounts only the broker runtime directory into Bubblewrap, and cleans the broker on normal/crash/failure cleanup.
- Tests/evidence: added installed-construction fail-closed coverage, an end-to-end `ActivityStorageClient -> broker -> ActivityStorage` write/read test, sandbox mount isolation coverage, broker cleanup-on-exit coverage, focused supervisor/storage tests and the complete currently-recoverable suite.
- Decisions: Storage remains a runtime-neutral Greia platform service and is not moved into `PythonRuntimeAdapter`. The Supervisor owns broker lifetime because it owns the Activity session; RuntimeManager remains responsible for runtime-specific validation/launch preparation. Broker-cleanup failure normalizes an otherwise completed launch to `platform_failure`.
- Remaining blocker: R5 event/progression broker integration cannot be completed honestly while `src/greia_platform/history.py` is lost; do not reconstruct it implicitly.
- Next exact step: audit remaining runtime-specific lifecycle/cleanup behavior after storage transport, then define the explicit R5 reimplementation/recovery boundary needed to restore event-session integration before R6 can close.
- Commit(s): this tranche commit.

## 2026-08-09 — R6.2 runtime-command authority boundary

- Implemented: `RuntimeCommand` now carries runtime-family-specific environment alongside command/cwd; `PythonRuntimeAdapter` owns Python-only process flags; RuntimeManager validates command text, package-bounded working directory and runtime environment before launch; ActivitySupervisor no longer injects Python settings and honors adapter cwd in Bubblewrap.
- Tests/evidence: Python-specific environment ownership, platform-environment override rejection, cwd escape rejection, generic supervisor environment remaining Python-neutral, adapter cwd honored in sandbox, focused runtime/supervisor tests, and complete recoverable suite.
- Decisions: runtime adapters may add bounded runtime-family process settings but cannot overwrite Greia/session/profile/storage authority, `PATH/HOME/XDG_*`, or inherited display/audio transport. Runtime-specific cwd must remain inside the Activity package.
- Remaining blocker: R5 event/session/progression integration remains blocked by lost `greia_platform.history`; RuntimeLifecycleSupport pause/checkpoint remains declarative and is not promoted until a real runtime requires it.
- Next exact step: perform an R6 closure audit against ADRs 0012/0014/0015 and the active plan, separating code-complete R6.2 items from the explicit R5 continuity blocker and any hardware-only evidence gates.
- Commit(s): this tranche commit.

## 2026-08-09 — R6.2 runtime session ownership

- Implemented: runtime adapters now own final runtime process creation, exit collection/normalization, force-stop and runtime cleanup through `RuntimeInvocation`/`RuntimeExit`; RuntimeManager delegates those operations to the selected adapter. ActivitySupervisor still owns Greia sandbox policy, lifecycle deadlines and platform session resources, but no longer calls `Popen`, process-group signals or interprets raw runtime return codes itself.
- Tests/evidence: direct RuntimeManager launch/exit delegation test, Supervisor forced-stop through adapter, focused runtime/supervisor tests, and complete recoverable suite.
- Decisions: Bubblewrap command construction remains platform/sandbox policy; the selected adapter launches the resulting invocation so future Web/native adapters can own their runtime handle semantics without duplicating Greia isolation/storage/session policy. Exit classification is runtime-owned; Greia overlays platform reasons such as ready timeout, forced return and platform cleanup failure.
- Remaining gap: Python READY/STOP marker transport is still created by the Supervisor rather than an adapter-owned lifecycle transport. That is the final R6.2 runtime-specific lifecycle seam to close before source-level R6.2 can be called complete.
- Next exact step: move Python lifecycle READY/STOP transport construction and SDK environment behind the runtime adapter while preserving the same platform session ID and Supervisor state machine.
- Commit(s): this tranche commit.

## 2026-08-09 — R6.2 runtime-owned lifecycle transport

- Implemented: Greia now allocates Activity session identity independently of runtime transport; `ActivitySession` stores that platform session ID explicitly and failed pre-runtime launches no longer manufacture Python marker directories. Runtime adapters create a `RuntimeLifecycleBinding` for the platform session; the Python adapter owns the existing READY/STOP file-marker channel and marker-path environment, while Supervisor consumes only the generic lifecycle-control protocol.
- Tests/evidence: Python binding preserves the platform session ID, lifecycle binding cannot replace session identity, failed unavailable-runtime launches retain a valid platform session with no runtime transport, active Python launches still receive READY/STOP SDK paths through the adapter, focused activity-api/runtime/supervisor tests, and complete recoverable suite.
- Decisions: `GREIA_ACTIVITY_SESSION_ID` is a platform-owned universal SDK fact; runtime-specific lifecycle transport variables are adapter-owned. Future Web/runtime adapters may use `GREIA_RUNTIME_*` bridge variables without changing Supervisor state semantics.
- R6.2 source status: runtime-specific validation, launch preparation, lifecycle transport, runtime-handle creation, exit normalization, force-stop and cleanup are now all behind the adapter/RuntimeManager seam. Platform Storage remains shared and brokered. The remaining full-R6 blocker is not an R6.2 seam: lost post-v0.12 R5 history/session/progression authority prevents complete `make verify` and event/session integration.
- Next exact step: perform and persist the final R6 source-closure audit against ADRs 0012/0014/0015, update PR evidence, and define the explicit R5 reimplementation decision required to unblock full verification; do not begin R7.
- Commit(s): this tranche commit.

## 2026-08-09 — R0/R5/R6 integrated source closure after reviewed R5 reimplementation

- Implemented: explicitly replaced the unrecoverable historical R5 History/Progression authority with a new reviewed implementation grounded in ADR 0017 and surviving policy/protocol contracts; restored automatic authoritative sessions, transactional/idempotent event processing, platform-owned score/progression/reward accounting, restart recovery, logical export and bounded parent summaries; wired per-session authenticated event brokers into the installed launcher; repaired the real `ProfileContext` Universal Storage namespace exposed by integration; corrected built-in package source authority in standalone validation and parent-server registry construction; fixed launch/cleanup failure paths so authoritative session rows always close with normalized reasons.
- Tests/evidence: permanent clean GitHub checkout `7562471d868a23cd90d88b43aed2501988eb5740` reports **318 tracked files / 123 PNGs**, clean worktree, Python compile PASS, R5 invariants PASS, R6 invariants PASS, **194/194 provider-free tests PASS**, project validation PASS, both bundled Activity validators PASS, and source/shell/footprint gate PASS.
- Decisions: **R0 is COMPLETE. R5 is SOURCE-CLOSED as a new reviewed reimplementation, not historical recovery. R6.1 and R6.2 are SOURCE-CLOSED.** Current source also keeps the R1–R4 safety/storage spine green under the complete gate. Source closure does not promote direct-graphics or physical-hardware evidence: Acer/Pi/DRM/KMS obligations remain in R7/R8/R14.
- Remaining blockers: the next blocking architectural phase is R7 direct graphics/session architecture. Later package/backup/parent/recovery/certification phases remain open per the dependency map.
- Next exact step: begin R7 by inventorying every `DISPLAY`, Xauthority, XShm, `xinput`, `xrandr`, Xorg package/config/service and SDL/Pygame assumption; classify interface vs provisional backend dependencies; then implement the direct display/input path beneath the stable R6 HAL without deepening X11.
- Evidence document: `docs/reviews/2026-08-09_R5_REIMPLEMENTATION_AND_R6_INTEGRATED_CLOSURE.md`.
- Key commits: `0cfb82aa89df5ebc9c03a01061ebd8da82f8f4dd`, `5bd867c9488fcd61a598813cdf7a42c396ec3b2c`, `e790a36e36b845d0a9d0ecf057180ffd3a213af3`, `2819f73dcc57c3b69d002532c03f5d2021e7c10f`, `7562471d868a23cd90d88b43aed2501988eb5740`.

## 2026-08-09 — R7 serial ownership and backend-neutral display-session tranche

- Implemented: added an evidence-only serial SDL/KMSDRM ownership probe covering Shell acquisition, clean child takeover, Shell reacquisition, abrupt child death without SDL cleanup, and final Shell reacquisition; installed a disabled PAM/logind VT1 handoff-acceptance service; extended the existing root maintenance controller with a strictly validated `handoff` mode while retaining `active` as default; layered a second disposable QEMU boot over the existing active KMSDRM production-image harness; upgraded the single exact-image CI chain to require both active and serial-handoff QEMU classifications when `kmsdrm` is compiled; introduced `DisplaySessionCoordinator` and typed bounded `DisplayTransport` semantics above runtime-specific process launch; recorded an explicit serial-versus-compositor measurement matrix.
- Tests/evidence: focused serial-handoff unit suite executed **8/8 PASS** against fake SDL/process boundaries; generated QEMU guest handoff script passed `sh -n`; two-boot plan and strict synthetic passing evidence were validated before commit; display-session recovery tests were added but the complete current `make verify` has not executed because GitHub Actions remains unavailable at the runner boundary. No real QEMU serial PASS, Acer PASS, Pi PASS, or newer full source-test count is claimed. Last actually executed complete source gate remains **232/232 PASS at `097f0281888a58f6f26425807ce99d9f35449313`**.
- Decisions: serial direct DRM ownership remains a measurement/evidence candidate only and does **not** authorize broad child `/dev/dri` or raw input access. Shell/Activity ownership semantics are now backend-neutral so serial teardown/reacquire and a persistent compositor can sit below the same launcher contract. Production remains Xorg. Debian Trixie Cage 0.2.0-2 is retained as a compositor benchmark/reference but its stock binary hard-depends on Xwayland; Weston is also a reference candidate. No compositor dependency is added to the production image yet.
- Remaining blockers: obtain executable active + serial QEMU evidence from the exact production image; run the complete source gate; measure exact package closure/RAM/process/startup/transition cost for compositor references; prototype the smallest persistent Greia-owned compositor/session-broker candidate below `DisplaySessionCoordinator`; move final display/input settings behind the selected adapters; compare against Xorg; complete physical legacy Intel/Acer acceptance before production migration.
- Next exact step: measure candidate package/resource closure without enabling a new boot path, then prototype the smallest persistent compositor/session broker underneath the new backend-neutral display-session contract. Treat any serial failure as evidence against the candidate rather than weakening the handoff test.
- Commit(s): `cb2b38b82b67fdc4aa9345526b09f6cf59c2ba04`, `5d18869d5b6f8374f31bca34ac664245445420cb`, `906117ec3a2321778521de0f8a8c00b10a25736d`, `d97a9d8ff6364b7ef2caf6d6dc461ac5528c1963`, `92043ef151074ff448380d4c36eeab34dd4e5282`, `79f37a162971d9f93e9df2efb4f9ce99eb1d81b4`, `ddbe8d9633af77ee7281a80f219c84b4c3c9d462`, `92abc06bc8127d4b1018dd45ae545888c83d73fc`, `eb9b8d40585579d5e5a2710eb59f6b4b7a48482d`, `e26d9fa44a74164df6fcebe3e20a9e55f2c1809e`, `1752eae2637e43a8a7d9c1bbc6ed8dc92f448756`, `772dc5b23a5a821d843738340f925122a7dd3e1a`, `02113b91647cdd14a7cd2d1ddfc459477e967c25`.

## 2026-08-09 — R7 exact compositor package-delta and CI-evidence hardening

- Implemented: added `tools/r7_compositor_package_probe.py` with a fixed candidate set (`cage`, `weston`, `wlroots-runtime`) to measure exact incremental package/filesystem closure in separate disposable clones of the production image; restored the clone's original resolver state and removed measurement-log noise before byte accounting; removed host `/run` from the chroot so maintainer scripts cannot reach the host systemd control socket; snapshot and require `/etc/systemd/system` to remain unchanged; reject candidate transactions that remove or version-change baseline packages; record introduced X-server/desktop-risk components; integrated all three package measurements into the single exact-image R7 workflow; hardened `DisplayTransport` so each typed transport is bound to its exact SDL backend; fixed the exact-image preflight so the expensive gate remains eligible until the generated R7 evidence document actually exists.
- Tests/evidence: provider-free package-probe regressions were added for the fixed candidate set, no-recommends/no-upgrade/no-remove APT contract, host-`/run` exclusion, package-manifest comparison, resolver restoration, log normalization, and systemd-tree change detection; display-transport pairing regressions were added. These new repository tests have **not** executed under the current GitHub runner condition. Current Actions runs `31292322548` (source verification), `31292322559` (exact-image preflight), and `31292322575` (clean-tree verification) failed before step 1 with `steps = null` / no logs; one controlled rerun of source verification and exact-image preflight reproduced the same boundary. The last actually executed complete source gate remains **232/232 PASS at `097f0281888a58f6f26425807ce99d9f35449313`**. No real compositor package-delta report, active QEMU PASS, serial-handoff QEMU PASS, Acer PASS, or Pi PASS is claimed.
- Decisions: package measurement is **incremental relative to the current Xorg production image** and is not an eventual Xorg-removed footprint claim. Measurement helpers must not become generic package installers or mutate production boot/session state. Cage/Weston/wlroots remain benchmark/reference candidates only. Serial direct ownership remains evidence-only. Production remains Xorg. No further CI retries should be spent merely reproducing the same zero-step runner boundary.
- Remaining blockers: obtain one genuinely executable unified exact-image run; compare the real Cage/Weston/wlroots package/file deltas; obtain active and serial KMSDRM QEMU evidence when applicable; run the current complete provider-free source gate; then prototype the smallest compositor/session-broker candidate below `DisplaySessionCoordinator` and measure RSS/process/FD/startup/transition/recovery cost against serial ownership and Xorg. Physical legacy Intel/Acer evidence remains mandatory before production migration.
- Next exact step: let the single unified workflow execute when GitHub runners are functional. Preserve every negative classification. If active acquisition or serial recovery fails, treat that as architectural evidence rather than weakening the gate. Only after exact package/resource evidence exists should a compositor candidate be prototyped below the backend-neutral display-session contract.
- Commit(s): `37f01485080af27b3d0159b79104252d94be14f8`, `a2e63dfcfbdfba2f43646a1d74d9ceb5b915cb08`, `3d52118116dd8fe2203a4b4510a8f3205428e2b1`, `fef55f88143ad330f2ffc30e5e036bd88fa05284`, `c2dfd4064e319cae59320d758e3a3f28aff36c11`, `d59f4fcad9f65bbb06224e93526bd906636ce80c`, `f30a7c85c73387e1e39e4a0269002faad4cd6544`, `cbf5f99de5fff9d17a9a16294926419bc1c3b0b6`, `c77f77a95f37cffaf5b3c5820510da4f56ef5a0c`.

## 2026-08-09 — R7 source-boundary correction, lease ownership, settings decoupling, and passive seat/input evidence

- Implemented: corrected a continuity error where the prior session's prose had described host-namespace hardening that was not actually present on the GitHub branch; the repository was treated as authoritative and corrected before further work. The compositor package probe now exposes no host `/dev`, `/sys`, or `/run`, uses a private bounded tmpfs `/dev` plus fresh procfs, rechecks the immutable source-image hash even on failure, removes disposable clones by default on both success and failure, requires requested packages to exist after the transaction, and protects systemd plus GRUB boot-state trees. `DisplaySessionCoordinator` now issues exact-object `DisplaySessionLease` ownership tokens, rejects stale/fabricated callbacks, makes presentation an explicit in-flight phase, requires backend/transport-kind agreement, and preserves combined primary/restore failure provenance. Active KMSDRM evidence now rejects residual `XAUTHORITY`, rejects bool/non-integer frame counts, and requires deterministic rendered-buffer diversity. Serial KMSDRM evidence now validates exact child frame counts, hashes, surfaces, finite configuration values, three distinct shell recovery buffers, and abrupt-child semantics. R7-A settings decoupling was completed at source level: the generic hardware watcher requires an injected semantic controller; all `xrandr`/`xinput`/libinput command mapping lives in `hal_legacy_x`; launcher composition explicitly selects that compatibility adapter; installer resolution discovery now consumes `HardwareSessionController` and legacy-X selection lives only in `greia_installer.composition`. The passive direct probe now inventories bounded input-event topology, logind/seat/session runtime presence, active VT, and transport-presence facts without opening DRM/input devices or claiming active input.
- Tests/evidence: isolated current display-session fixture executed **22/22 PASS**; isolated current compositor-package pure-logic fixture executed **14/14 PASS** with only the QEMU/raw-image mount dependency stubbed. The earlier serial fake-SDL/process suite executed **8/8 PASS before the latest serial evidence-strengthening edits**, so the strengthened serial suite is not claimed as executed. Later hardware-settings, installer-adapter, active/serial evidence and passive seat/input regressions are committed but could not execute in a real current checkout: this execution container has no GitHub DNS/network access and no existing authenticated checkout. Fresh Actions runs `31294925789` (source), `31294925798` (exact-image preflight) and `31294925820` (clean tree) again failed before step 1 with `steps = null` / no logs; exact-image `build-probe-record` was skipped because preflight never executed. The last actually executed complete source gate therefore remains **232/232 PASS at `097f0281888a58f6f26425807ce99d9f35449313`**.
- Decisions: R7-A is materially source-implemented but is **not labeled fully verified** until the current full gate runs. GitHub remains canonical when chat prose and persisted source disagree. Production remains Xorg; no compositor is selected; serial direct ownership remains evidence-only. `ActivitySupervisor` still intentionally retains X-compatibility concessions (shared IPC, inherited X/Wayland transport variables, broad `/dev/dri` bind) and they must not be removed blindly while production uses Xorg. They will be narrowed only after the display/session architecture is selected and proven. `ActivitySupervisor` must not become DRM owner. No compositor runtime prototype should be added before exact package/resource evidence exists.
- Remaining blockers: one genuinely executable current `make verify`; one genuinely executable unified exact-image run yielding installed-SDL classification and exact Cage/Weston/wlroots deltas; active and serial QEMU evidence where KMSDRM is present; active seat/input evidence; measured compositor-vs-serial-vs-Xorg runtime/resource comparison; explicit direct-profile sandbox authority migration; physical legacy Intel/Acer scanout/input/suspend/crash acceptance before production migration.
- Next exact step: when a runner/environment genuinely executes, run the current full source gate and the existing single exact-image workflow without creating parallel builders or weakening gates. Preserve negative evidence. Only after real package/resource evidence exists should the smallest viable Greia-owned compositor/session-broker candidate be prototyped below `DisplaySessionCoordinator` and compared against serial ownership and Xorg.
- Commit(s): key current tranche commits include `90eb280e9f81d61e8f9eff07906768f110626af1`, `656d16d78335bce8574b130bf60dbabf634bfca4`, `fa6dc192f853bfd97635ef12632590c381071803`, `e7d84a64c8a4147a0b14c5eebee82eb41d0b0f26`, `8d3008e3196ede988c1409d23186d0f2a6dbf8f3`, `50cb0b58551e640d178617308013283f2226ba8e`, `c9ec137189865a976fe6b9c9767c104986379a43`, `87edc24057c4f09ddebb05af2ab44c18bab070c6`, `63189eb9f1ab2fd0a6d29bf3c4d1466b64b28784`, `7d14d13acf55e2cf31ea62622a11ec9093a4778e`, `635bd77f341160a7d0c4bb3c5ca0789e313258f8`, `42b4fb416703c7fb7ef4e3c8a93475d804813661`, and handover refresh `71751658303ef324fb8ecd12df54078aa99dd679`; additional evidence/settings commits are preserved in branch history.

## 2026-08-09 — R7 live installed display-session lifecycle integration

- Implemented: the backend-neutral `DisplaySessionCoordinator` is now composed into the **real installed Activity lifecycle** rather than remaining an evidence/prototype seam. Added `LegacyXDisplaySessionBackend` as an explicit compatibility implementation for the current Xorg/xinit session; it introduces no new window manager/display manager/X server and simply describes the existing child transport. Corrected the legacy-X transport contract to require `DISPLAY` while treating `XAUTHORITY` as optional-but-validated when present, matching Greia's direct `xinit` compatibility path instead of inventing credentials. `ActivitySupervisor` now prepares one display lease using the platform Activity session ID, applies only that lease's bounded transport environment to the child invocation, presents on authoritative READY, avoids presenting a process that already exited after publishing READY, and restores the shell on launch failure, normal exit, crash, forced stop and timeout. Display restore failure now participates in terminal cleanup and converts the authoritative Activity result/history reason to `platform_failure`. Installed launcher composition injects this coordinator only on the installed root; development/windowed paths retain the previous no-coordinator behavior. A follow-up commit removed accidental unrelated `main.py` formatting churn; cumulative comparison against the pre-integration point shows only 9 changed lines in `main.py` plus the new lifecycle regression test file.
- Tests/evidence: added `tests/test_display_session_legacy_x.py` and `tests/test_supervisor_display_session.py` covering xinit-style transport without fabricated Xauthority, invalid/ambiguous compatibility transport, typed transport overriding stale host selectors, READY/present/normal restore, fast READY+exit without dead-surface presentation, presentation failure, restore failure -> `platform_failure`, and process-launch failure recovery. These latest integration tests have **not executed** in a real current checkout. Fresh Actions runs `31314374079` (source), `31314374090` (exact-image preflight) and `31314374082` (clean tree) again failed before step 1 with `steps = null` / no logs; exact-image build remained skipped. The last actually executed complete source gate remains **232/232 PASS at `097f0281888a58f6f26425807ce99d9f35449313`**.
- Decisions: the display-session contract is now a live installed-source boundary, but this is **not a graphics-backend migration**. Production remains Xorg/xinit. `ActivitySupervisor` coordinates lifecycle timing but does not own DRM. Raw Activity `/dev/dri` and shared-IPC X compatibility concessions remain unchanged until a measured direct/compositor design is selected. No compositor is selected and no production package set changes in this tranche.
- Remaining blockers: harden the post-display-prepare child-environment assembly failure path so any `ActivityLifecycleError` enters common failed-launch cleanup; add the new live integration files to the exact-image workflow's future path-trigger/preflight set; obtain a genuinely executable current `make verify`; obtain exact-image SDL/package-delta/QEMU/seat-input evidence; compare compositor-vs-serial-vs-Xorg runtime/resource/authority behavior; require physical legacy Intel/Acer evidence before production migration.
- Next exact step: close the two small source/CI hardening items above, then stop adding display mechanisms until one executable current source/exact-image environment yields the measurements required to choose the next backend prototype.
- Commit(s): `5e44a3926d6989652945f1d5a9625ec997051cca`, `0c4fb197fa02ba818aed402e20e489779381d110`, `0e2904679116ee32f4a02616997c71571bd41f27`, `07bdc4ef6f1ff8b486e4d369ed1253890a2382a7`, `f1aa18b6fca32d04cdc7b0063184f49b3638493a`, `5ce6d3c85cafcc166c15adfc61f14a6c465d4961`, `0cec31b2418b88bde25aecd1b484f076e63444aa`, `5f45c7d44a9f254e5181dc068333a0db7292a658`, handover refresh `b1e012e48d0afaa116da065fbc83d49c2be0d20c`.

---

# 9. Final completion criteria

This plan may be marked complete only when:

- every phase closure is satisfied or superseded by an accepted ADR with equivalent/stronger guarantees;
- no open HIGH finding remains without explicit disposition;
- per-Activity writable isolation is real;
- effective permissions come from a trusted PermissionBroker using package trust/origin plus policy/capability inputs;
- capability availability, permission request, and effective grant are distinct;
- Activity environment state or Activity ID alone cannot grant authority;
- Activity lifecycle/watchdog is platform-owned through a runtime-neutral session seam;
- permanent Activity IDs are locked/migrated before durable data relies on them;
- Storage/Session/Progression/Reward services are shared platform services;
- global reward economics are not Activity-authored;
- Device Capability/HAL services are authoritative above board-specific adapters;
- Python and Web, where supported, use common platform semantics;
- direct graphics is accepted and X11 is not an unintended architectural requirement;
- Pi 400/500 and required x86 references have evidence-backed support status;
- Activity install/update/rollback and child backup/restore satisfy parent workflows;
- boot/recovery continuity meets the no-visible-Linux contract;
- OS/runtime update and preserve-profile recovery have an accepted signed rollback-safe path;
- the canonical GitHub repository is sufficient to reproduce the source/build/test tree without a chat-session archive;
- `make verify` passes;
- `HANDOVER.md` is current;
- the active-plan reference is removed from `AGENTS.md` as the final administrative action.
