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
**Status:** **REOPENED / INCOMPLETE** — governance wiring and source verification are real, but GitHub binary-asset completeness is not yet true.

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
