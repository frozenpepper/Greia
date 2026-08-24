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
- runtime-neutral interaction profiles and Phase-0 controller/joystick support;
- Python and Web runtime adapters using the same platform services and input semantics;
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

**Required:** a platform `PermissionBroker` computes effective session grants from package trust/origin, manifest request, runtime capability, hardware capability, build policy, parent policy, and platform security policy. Built-in/system privilege is tied to trusted package identity/origin, not title or Activity ID alone.

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

## F-25 — Controller/input conventions would fragment per Activity — HIGH Phase-0 UX/architecture risk

Without a shared input model, each Activity could invent joystick button numbers, dead zones, controller-as-mouse behavior and keyboard mappings independently. A future Web runtime would then require a second incompatible controller stack, and raw controller access could bypass protected Greia system input.

**Required:** ADR 0020 runtime-neutral interaction profiles; controller as a first-class HAL capability; centralized mapping/dead-zone/virtual-pointer policy; Greia-owned physical device/system-input authority; Python/Web semantic parity; physical controller evidence in R7/R14.

---

# 3. Cross-cutting rules

1. **One platform service per concern.** Do not create Python/Web copies of storage, sessions, progression, package, backup, parent policy, or standard input mapping.
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
12. **Input intent is not physical-device authority.** Activities declare interaction profiles; Greia owns controller discovery/normalization, reserved system input, and the production physical-input path. Do not grant ordinary Activities raw `/dev/input` to manufacture controller support.

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
- Input Service, including controller availability;
- Audio Service;
- Removable Media Service;
- Power Service;
- Network Service.

Existing Xorg/xinput/xrandr/systemd behavior may temporarily sit behind provisional adapters. PermissionBroker and compatibility checks consume platform-owned capability facts, not Activity guesses.

### R6.2 Runtime integration

Complete the runtime-adapter protocol begun minimally in R2 for runtime-specific static/package validation, launch preparation, SDK transport, lifecycle session creation, cleanup, and normalized results. Migrate Python behavior without duplicating Storage/Session/Progression/input semantics.

## R7 — Direct Greia graphics/session/input architecture

**Goal:** implement the target appliance display/session/input model without circular Pi evidence requirements.

Work:

- inventory `DISPLAY`, Xauthority, XShm, `xinput`, `xrandr`, Xorg package/config/service assumptions;
- typed Display/Input implementations behind R6 interfaces;
- prototype SDL direct DRM/KMS/KMSDRM path;
- preserve ADR 0019 trusted Home/Back above Activity rendering and consume protected system input before Activity delivery;
- implement ADR 0020 physical controller ownership/brokerage without ordinary Activity raw `/dev/input` authority;
- map keyboard/pointer/touch/controller into the runtime-neutral interaction profiles and reserve controller Guide/system input where reliably available;
- prove bounded controller discovery/open/reconnect and virtual-pointer behavior;
- determine by measurement whether a tiny compositor/session broker is justified for Web surfaces, transitions, crash recovery, trusted chrome and input routing;
- define shell↔Activity surface/input ownership/recovery;
- move display/input settings behind platform adapters;
- benchmark disk/RAM/process/FD/startup/input/latency cost against Xorg;
- retain Xorg only as an explicit compatibility adapter if physical evidence requires it.

**R7 closure:** direct display/session/input architecture plus x86/VM and available x86 physical evidence accepted; no Activity API depends on X11 or raw host input devices; mandatory Home remains outside Activity authority; controller/joystick Shell navigation, simple game mapping, pointer virtual-pointer behavior, disconnect/reconnect and reserved system-input interception are proven for the selected backend; resource cost is acceptable on the Acer floor. Pi-specific display/input evidence is deferred explicitly to R8.

## R8 — Raspberry Pi 400 / Pi 500 ARM64 board and image adapters

**Goal:** make ARM a shipping peer, not a later port.

Work:

- select base/kernel/firmware strategy;
- board/image boot adapters beneath the same build-profile schema;
- Pi profiles only after adapters exist;
- integrate R7 direct display/session/input backend;
- test boot/display/keyboard/pointer/controller/audio/network/removable media/shutdown/recovery;
- close Pi-specific HAL/display/input work;
- measure capability/resource classes independently of architecture.

## R9 — Embedded Web runtime benchmark and implementation

**Goal:** add Web without turning Greia into a browser appliance.

Stage A benchmark: WPE/WebKit-style candidates first, alternatives allowed; installed delta, idle/peak RSS, cold/warm startup, Canvas2D/SVG/JS/WebAudio, optional WebGL, R7 display/session/input integration, i386 feasibility, Pi behavior, security maintenance, crash/forced-return.

Stage B adapter: packaged local content only; no child browser chrome/navigation/downloads/devtools; network denied by default; same Storage/Session/Event services and lifecycle/watchdog as Python; same ADR 0019 external system chrome; same ADR 0020 interaction-profile/controller semantics through a Web bridge rather than per-page controller-brand mappings; no authoritative unmanaged localStorage/IndexedDB save silo.

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

ADR 0022 permits an earlier **non-closing Parent API/client foundation** after the relevant shared services exist: versioning, LAN discovery, per-device credential/revocation primitives, capability advertisement, and HTML/native client parity may wrap already-existing unprivileged profile/status/settings services. This exception does not authorize privileged effects, substitute package/backup/update implementations, or change R12 closure prerequisites. Full R12 still waits for the services it delegates to, including R10/R11 where applicable.

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
- platform-owned Home/Back and protected system input;
- Phase-0 controller/joystick navigation, game mapping, virtual pointer, reconnect and latency/resource evidence;
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
 ├────────────→ R7 direct graphics/session/input (x86/VM evidence)
 │                  └────────→ R8 Pi image + ARM display/input evidence
 ├────────────→ R9 Web runtime (uses R7 session/surface/input architecture)
 └────────────→ R10 .greiaactivity

R4 + R5             → R11 .greiabackup
R1 + R6 + R10 + R11 → R12 parent integration
R7 + R12            → R13 boot/recovery
R11 + R12           → R13B OS/runtime update + preserve-profile recovery
all                  → R14 certification
```

The blocking safety spine through R6 remains ordered. After R6, explicitly independent tracks may proceed in parallel when their prerequisites are satisfied. No later track may weaken an earlier boundary. ADR 0022's non-closing Parent API/client foundation is an allowed preparatory tranche only; it does not move the R12 closure dependency shown above.

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

Security phases require positive **and negative** tests. Hardware/display/input phases require source tests plus exact VM/physical evidence; source structure never proves hardware behavior.

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
- Remaining blocker: R5 event/progression broker integration cannot be completed honestly while `src/greia_platform.history` is lost; do not reconstruct it implicitly.
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
- Remaining blockers: obtain executable active + serial QEMU evidence from the exact production image; run the complete source gate; measure exact package closure/RAM/process/FD/startup/transition cost for compositor references; prototype the smallest persistent Greia-owned compositor/session-broker candidate below `DisplaySessionCoordinator`; move final display/input settings behind platform adapters; compare against Xorg; complete physical legacy Intel/Acer acceptance before production migration.
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

## 2026-08-09 — R7 paid-CI correction and local evidence execution path

- Implemented: corrected an execution-governance failure: GitHub-hosted Actions had been used without explicit repository-owner authorization. Hosted paid execution is now opt-in only. `main` clean verification was changed to manual-only (`05df6b97bd95e375c9986c6e045a437df749c6a2`); the R7 branch clean verifier is manual-only (`21be2d987665fd9638154ddd3da82d0ca3f96591`); the R7 automatic source and exact-image hosted workflows were removed (`63734d9bf280b36feb0b03ef49989d29ed8f4176`, `f3534bf13a83d4018fb5e4d00f614af09ab2e105`). A permanent rule was added to `AGENTS.md` on the branch and independently on `main` requiring explicit owner authorization before enabling, triggering, rerunning or adding GitHub-hosted Actions (`1c3f407e62f94820e391cd664e41aa7026ca2685`, `c5f02191876d2038880bbbcd09e98b7bd79d2552`). Added `tools/r7_local_evidence.py`, an OOP local Linux orchestrator that reuses the existing production builder, passive direct-graphics probe, fixed compositor package probe, and active+serial QEMU harness while keeping all generated evidence outside the repository and never installing host packages or committing/pushing evidence. Reworked `docs/testing/2026-08-09_R7_EXTERNAL_LINUX_EVIDENCE_EXECUTION.md` into a local-only controlled-Linux operator protocol.
- Tests/evidence: added `tests/test_r7_local_evidence.py` covering run-root isolation, no-GitHub-Actions plan semantics, fixed package candidate set, mandatory active KMSDRM and active seat/input follow-up flags, immutable source-image/package-boundary validation, KMSDRM-not-compiled QEMU skip semantics, and non-overclaiming summary behavior. These new tests are **committed but not executed**. The last complete source gate that actually executed remains **232/232 PASS at `097f0281888a58f6f26425807ce99d9f35449313`**. No new package-delta, active QEMU, serial QEMU, seat/input or physical Acer result is claimed.
- Decisions: GitHub remains canonical for source persistence, but GitHub-hosted execution is not implicitly authorized and must not be used without explicit owner approval for that specific use. R7 evidence execution now proceeds on a controlled/disposable local Linux environment via existing Greia implementations. First failure is preserved; the local orchestrator does not rerun active/serial QEMU in the same attempt, does not mutate the production source image, and deliberately leaves active seat/input and physical Acer evidence incomplete. Production remains Xorg/xinit. No compositor is selected and no Activity becomes DRM/input owner.
- Remaining blockers: execute the current source gate in a controlled local Linux checkout; build and inspect the exact current production image; obtain real Cage/Weston/wlroots package deltas; if installed SDL exposes KMSDRM, obtain active and serial QEMU evidence; obtain active seat/input evidence; compare compositor-vs-serial-vs-Xorg authority/resource/runtime behavior; migrate the direct-profile sandbox only after architecture selection; complete physical legacy Intel/Acer acceptance before production migration.
- Next exact step: in a disposable/root-owned Linux checkout, inspect `python3 tools/r7_local_evidence.py --run-root <outside-repo-path> --plan-only`, then run the local orchestrator exactly once for the evidence attempt and return the complete run-root archive. Preserve the first failure and do not weaken/retry the active evidence path merely to obtain PASS. Only after real package/runtime evidence exists should a compositor/session-broker prototype be selected, and any such prototype belongs below `DisplaySessionCoordinator`.
- Commit(s): `05df6b97bd95e375c9986c6e045a437df749c6a2`, `21be2d987665fd9638154ddd3da82d0ca3f96591`, `63734d9bf280b36feb0b03ef49989d29ed8f4176`, `f3534bf13a83d4018fb5e4d00f614af09ab2e105`, `1c3f407e62f94820e391cd664e41aa7026ca2685`, `c5f02191876d2038880bbbcd09e98b7bd79d2552`, `37b536f758bf4918865f3e0419623c36e81af33c`, `396ef3d490e11605912bce8a74e46e266659fa53`, `6c6ca623dda97406572582c6f5c915b2bf72d1a4`, handover refresh `faf2a5ab5cc6c8a2c4729d48763a353fe12e120d`.

## 2026-08-09 — R7 developer remote-control/test-console tranche

- Implemented: added an explicit experimental `modern-amd64-dev` image profile and `developer-remote` package set; added a canonical-builder wrapper plus bounded raw-image provisioner that generates a per-image operator Ed25519 client key, installs only the public half for `greiaadmin`, enables SSH only on the marked developer image, validates sudo/sshd configuration, refuses persistent cloned SSH host identity, and declares the installed developer display endpoint as `greiakid@:0`. Added a Greia-owned `greia-devctl` privileged command surface, root-owned deployment state, deterministic developer-only wired DHCP/mDNS preparation, status/log/screenshot/service/power controls, and constrained GUI input via a fixed `xdotool` backend. Added a Mac/operator `tools/greia_remote.py` client for wait/status/screenshot/logs/key/mouse/text/deploy/remove/restore/restart/reboot/poweroff/shell operations. Ordinary remote Activity deployments now live under `/var/lib/greia-developer/activities`, are registered by the real launcher as a separate `DEVELOPER_UNSIGNED` source, cannot request privileged permissions, and cannot collide with the built-in root; deliberate `--replace-system` testing is explicit and preserves the original built-in for restore. Added a typed developer display-session endpoint so installed Greia and the planned live installer can use different display owners without duplicating control logic. Added `tools/provision_developer_installer.py` to provision the existing live graphical installer with key-only SSH, wired DHCP/mDNS and `root@:0` developer display control while preserving the installer’s graphical safety model.
- Tests/evidence: `tests/test_developer_remote.py` now covers developer-vs-normal profile separation, display-endpoint validation, screenshot/input execution under the declared display user, developer marker enforcement, root-only deployment metadata vs readable developer Activity source, path/ID rejection, `BUILT_IN` versus `DEVELOPER_UNSIGNED` launcher sources, non-overlapping roots, fixed xdotool invocation, image-profile/host-key provisioning constraints, remote client key/known-host behavior, and live-installer remote-but-not-unattended policy. These tests are **committed but not executed**. No developer image has been built in a current Linux checkout; no SSH login, mDNS, screenshot, xdotool input, remote Activity deployment, reboot/reconnect, or live-installer remote-control result is claimed. The last complete source gate that actually executed remains **232/232 PASS at `097f0281888a58f6f26425807ce99d9f35449313`**.
- Decisions: remote control is a developer/test capability only and must never be enabled implicitly on normal/release profiles. SSH is transport, not product authority: password/root login stay disabled and passwordless sudo is bounded to `greia-devctl`. Remote file placement may not upgrade Activity trust. Current screenshot/input are Xorg-development compatibility implementations beneath a stable developer-session/control seam and do not select X11 as R7 production architecture. Remote installation must drive the existing graphical fail-closed installer; no unattended destructive disk-write command is accepted. The live-installer provisioner is source-implemented but **not wired into `build/build-installer-image.sh` yet** because that destructive-media-sensitive integration must receive a real Linux build/test instead of an unexecuted whole-file builder rewrite.
- Remaining blockers: run current source tests locally; build `modern-amd64-dev`; verify unique first-boot SSH host keys, key-only `greiaadmin` login, deterministic wired DHCP/mDNS, screenshots and bounded GUI input on the target; verify ordinary remote deployment retains `DEVELOPER_UNSIGNED` trust and built-in replace/restore is reversible; then integrate the live-installer provisioner at the two canonical builder hook points and prove remote graphical installation without weakening eligible-target/payload/device confirmation. R7 graphics/package/QEMU/seat/input/Acer evidence remains separately outstanding.
- Next exact step: on an owner-controlled Linux checkout, run the focused developer-remote suite and full `make verify`; build the developer target with `sudo bash build/build-developer-image.sh out`; install/boot it through an existing safe path and execute the acceptance checklist in `docs/testing/2026-08-09_DEVELOPER_REMOTE_CONTROL.md` from the operator computer. Preserve the first real failures. Only after target remote control is proven should the canonical live-installer builder hooks be added and tested.
- Commit(s): key tranche commits include `0592226229770a42a7ddcb40d4035cc4ee9b6041`, `2d87d1fdc4f04ca9154cee34bd350ee25a3e47c0`, `9e3694efefcafa67cf432173e0a5f7a4acca82ca`, `ec9000476f5f234c2a44200533974730de2d2801`, `223292db0c512c89d675dca5348a86741ff15b0d`, `2880683be3d8eda7881610789abe1b051b00605e`, `d96bc90bd5ed8cb9025dfb456c5b8aa3e7455d14`, `0cc35694ed710c78c011f18b0b2639ecbcd4ad13`, `fefea94ad015e286220e43a6e77de33ac0f50ecd`, `b7898af51fa06a72877749928f3116c20eb68007`, `c3e206b203f66352a2aba21870fe6bf95261a036`.

## 2026-08-13 — Phase-0 creative source and lightweight UI/engineering consolidation

- Implemented: added first-party Writing and Painting source tranches with bounded undo/persistence behavior; introduced renderer-neutral `ui_core.py` with Screen/Overlay/Control/Collection/PagedGrid/BoundedCache/InvalidationTracker/SurfaceNavigator; accepted ADR 0018; added mandatory repository-wide OOP/polymorphism/maintainability guidance in `docs/engineering/ENGINEERING_FOUNDATIONS.md`; consolidated `docs/DOCUMENTATION.md`, README and the Activity authoring skill around canonical owners; added `pygame_ui.py` as the platform-wide import name for the existing single Pygame helper implementation while preserving current `activity_ui.py` compatibility.
- Tests/evidence: UI/creative regression source is committed but has not executed in a real current checkout. No new PASS is claimed. The last genuinely executed complete source gate remains **232/232 PASS at `097f0281888a58f6f26425807ce99d9f35449313`**.
- Decisions: Greia uses Screen/Overlay/Collection semantics rather than desktop windows/filesystem folders. Performance/resource bounds are part of UI correctness. Strong OOP means cohesive domain objects and purposeful polymorphism at real variation points, not maximal class count. Existing Shell/installer UI will migrate incrementally only after focused/current source verification; no big-bang UI rewrite is authorized. R7 production graphics status remains unchanged.
- Remaining blockers: run focused UI/creative tests and current `make verify`; then migrate Shell paging/resource caches and installer font/icon caches onto the common UI foundation; continue R7 exact-image/package/QEMU/seat/input/physical evidence separately.
- Next exact step: on an owner-controlled current checkout, run `tests.test_ui_core`, `tests.test_ui_core_lifecycle`, `tests.test_activity_ui`, `tests.test_core_creation_activities`, `tests.test_activity_theme_access`, validate Writing/Painting, then `make verify`. Preserve first failure and do not weaken tests. Only after PASS should existing Shell/installer behavior migrate to shared primitives.
- Commit(s): UI/engineering consolidation is preserved in branch history; resolve actual current HEAD from GitHub before execution.

## 2026-08-15 — R7 platform-owned Activity system navigation contract

- Implemented: accepted `docs/product/ACTIVITY_SYSTEM_NAVIGATION.md` and ADR 0019; added renderer-neutral mandatory Home/optional Back geometry and action contracts in `greia_platform.system_chrome`; added a backend-neutral exact-lease `SystemChromeCoordinator`; added `SystemChromeNavigationBridge` so validated platform chrome actions enter the existing Greia Activity stop lifecycle without runtime-specific exit logic; added canonical Pygame Home/Back glyph primitives; added focused regression source; updated AGENTS, documentation authority, engineering guidance, README, ADR 0018 and the Activity authoring skill.
- Tests/evidence: new system-chrome and compatibility regression source is committed but has not executed in a real current checkout. No new PASS is claimed. The last genuinely executed complete source gate remains **232/232 PASS at `097f0281888a58f6f26425807ce99d9f35449313`**. There is no current trusted Xorg/compositor system-chrome runtime evidence.
- Decisions: Home is mandatory Greia-owned chrome outside Activity rendering/input authority; Back, when available, means return to the Greia launch origin after ending the Activity and is not browser history or Activity-internal navigation. ADR 0019 narrows R7 closure: a production backend must preserve trusted Home above Activity content and consume protected-region input before Activity dispatch. Raw serial DRM/KMS ownership by the Activity cannot close R7 by itself unless another trusted layer preserves this invariant. A tiny Greia-owned compositor/session broker may be justified by this requirement, but no desktop/window-manager behavior is authorized.
- Remaining blockers: run the focused/current source gate; implement and compose a concrete trusted `SystemChromeBackend` as part of R7; prove overlay/input authority and graceful/forced Home return against real Activity content; measure resource impact on the Acer floor; extend future Web acceptance so page content cannot manipulate system chrome.
- Next exact step: execute `tests.test_system_chrome` with the existing UI/creative focused suite and current `make verify`. After source PASS, integrate the chrome coordinator beside `DisplaySessionCoordinator`, prototype the smallest trusted overlay/input backend, and preserve negative evidence rather than falling back to an Activity-drawn or DOM-injected button.
- Commit(s): source/docs are preserved in branch history; resolve actual current HEAD from GitHub before execution.

## 2026-08-15 — Phase-0 runtime-neutral input profiles and controller foundation

- Implemented: accepted `docs/product/ACTIVITY_INPUT_STANDARDS.md` and ADR 0020; added `greia_platform.input_core` with runtime-neutral interaction profiles, semantic actions, brand-neutral physical controller vocabulary, centralized circular dead-zone normalization and bounded Greia virtual pointer; added `controller` to the typed HAL/device-capability/runtime vocabulary; added conservative controller-presence probing without opening Activity devices; added `pygame_input.py` translating keyboard/SDL-controller events into Greia semantics plus an explicitly bounded trusted controller owner (maximum 4 open / 16 scanned); added `[input].profile` to the Activity manifest contract with API-0.1 `hybrid` compatibility; added `get_input_profile()` and platform launch-context propagation; declared Painting=`pointer` and Writing=`text`; added focused source regressions and a dedicated physical controller acceptance protocol; updated AGENTS, README, architecture, engineering foundations, documentation map, agent operations, Activity skill and ADR 0019 product cross-reference.
- Tests/evidence: all input/controller tests added in this tranche are **committed but unexecuted**. No Shell controller navigation, physical controller, reconnect, virtual-pointer-on-real-Activity, reserved Guide interception, Web bridge or Acer latency/resource PASS is claimed. The last genuinely executed complete source gate remains **232/232 PASS at `097f0281888a58f6f26425807ce99d9f35449313`**.
- Decisions: controller is a device capability, not an Activity-specific control scheme. New Activities declare interaction intent (`navigation`, `pointer`, `directional`, `game`, `text`, `hybrid`). Simple games use the learned arrows+Space / D-pad-or-left-stick+south-face baseline; pointer Activities use a Greia semantic virtual pointer; text Activities retain real typing/editing semantics. Consumer-brand labels terminate at backend adapters. Controller Guide/system input is platform-reserved where available. Ordinary Activities do not gain raw `/dev/input`; production physical-device ownership/brokerage is an R7 platform responsibility. A fallback controller Home chord remains intentionally undecided pending accidental-activation evidence.
- Remaining blockers: execute the focused input/UI/source gate; then compose the bounded trusted Pygame controller owner/standard navigation mapping into the existing Shell loop without a big-bang launcher rewrite; implement the production R7 physical-input/system-input broker alongside trusted system chrome; prove controller navigation, analog repeat/dead zones, disconnect/reconnect, pointer virtual cursor, Guide interception and Activity raw-device denial on real hardware; measure resource/input latency on the Acer floor; later implement equivalent Web semantic transport.
- Next exact step: run `tests.test_input_core`, `tests.test_pygame_input`, `tests.test_activity_input_contract`, `tests.test_hal_legacy_x`, `tests.test_system_chrome` plus the existing UI/creative focused gate and `make verify`. If source passes, make the smallest Shell integration using `PygameControllerSet`/`PygameInputTranslator`, then execute `docs/testing/2026-08-15_PHASE0_INPUT_CONTROLLER_ACCEPTANCE.md` on owner-controlled hardware. Do not broaden the Activity sandbox to `/dev/input` as an implementation shortcut.
- Commit(s): source/docs are preserved in branch history; resolve actual current HEAD from GitHub before execution.

## 2026-08-16 — Ubuntu aggregate source gate PASS + Activity-bytecode validation fix

- Implemented: fixed the last reachable failure in the canonical Ubuntu aggregate source gate. `tests/test_core_creation_activities.py` loads the first-party Writing/Painting Activities directly from the Activity tree via `importlib.util.spec_from_file_location` + `exec_module`, which wrote `__pycache__` caches into the Activity folders that the later `validate` stage must reject. The test module now sets `sys.dont_write_bytecode = True` so the Activity tree stays bytecode-free. Documented in `docs/reviews/2026-08-16_UBUNTU_ACTIVITY_BYTECODE_VALIDATION_FIX.md`; HANDOVER updated.
- Tests/evidence: on the owner-controlled Ubuntu host, `bash tools/run_hardware_enablement_source_gate.sh` exits **0** at `f305aed…` + fix: focused HE suites 77+32 PASS, full suite 530 PASS, project validation 4 Activities PASS, shell-check/footprint PASS. This is the first genuinely executed complete aggregate source gate since `097f0281888a58f6f26425807ce99d9f35449313` (232/232).
- Decisions: the Activity tree must remain free of Python bytecode; test modules that load Activity source must suppress bytecode writes rather than leave caches that violate Activity validation.
- Remaining blockers: proceed through the current rerun runbook — build the `legacy-x86-i686` installer, verify image SHA-256, positively identify the SD, raw-write, and physical read-back verify. Later hardware-enablement evidence still requires a canonical installer build, VM installation, and diverse physical-machine acceptance.
- Next exact step: `sudo bash build/build-legacy-x86-sd-installer.sh out`, verify artifacts/SHA, then SD identification/write/read-back per the rerun runbook.
- Commit(s): this progress entry ships with the test fix, its review, and the HANDOVER update in the current `main` commit.

## 2026-08-17 — Boot animation: direct 52-frame Plymouth theme integration & cleanup

- Implemented: replaced the experimental chunk/generator machinery with direct runtime PNG assets. The repository now carries one canonical Plymouth theme under `build/overlay/etc/plymouth/themes/greia/` containing 52 lossless 222x600 RGB PNG frames (`frame_0000.png` through `frame_0051.png`), `greia.plymouth`, and `greia.script` configured for 7 fps refresh playback (`Plymouth.SetRefreshRate(7)`). Deleted the experimental `runtime/boot-animation`, `build/boot-animation`, and `00-greia-boot-animation` initramfs hooks from the tree. Removed duplicate theme copy from `build/installer-overlay/etc/plymouth/themes/greia/` and wired `build/build-installer-image.sh` to stage the canonical theme directly from `$PROJECT_ROOT/build/overlay/etc/plymouth/themes/greia`.
- Tests/evidence: `tests/test_boot_animation_contract.py` added and passing (5/5 PASS), verifying canonical directory layout, 52 frames, 222x600 dimensions, 8-bit RGB color depth, 7 fps script contract, generator removal, and installer builder wiring.
- Decisions: boot animation uses direct canonical PNG runtime assets without runtime generator, base85 encoding, or frame reconstruction. One canonical copy in `build/overlay/etc/plymouth/themes/greia/` serves both installed target and live installer.
- Remaining blockers: physical Acer boot and visual verification of Plymouth animation playback during actual startup.
- Next exact step: continue hardware-enablement SD installer build and physical verification per rerun runbook.
- Commit(s): boot animation integration commit on `main`.

## 2026-08-17 — R12 preparatory Parent API/client foundation (non-closing)

- Implemented: accepted ADR 0022 and `docs/product/PARENT_MANAGEMENT.md`; added the narrower parent-management architecture design; introduced API-v1 protocol/capability vocabulary, bounded per-device credential storage with hashed persisted tokens and independent revocation, a versioned JSON facade over existing profile/progress/hardware/Activity-inventory services, `_greia-parent._tcp` Avahi discovery, and a dependency-free responsive HTML client that uses `/api/v1`. `greia-parent.service` now starts the API-first server while the legacy server-rendered UI remains available as a compatibility/troubleshooting view.
- Tests/evidence: added `tests/test_parent_api.py` for credential persistence/revocation bounds, capability truthfulness, bootstrap/bearer behavior, Activity-path non-disclosure, HTML API usage, mDNS advertisement and normal-image SSH separation. The new source was syntax-checked while authored, but no current repository test suite or `make verify` was executed in this GitHub-connector environment; **no PASS is claimed** for the current head.
- Decisions: the HTML page is the first client, not the parent authority implementation; future native clients use the same discovery/pairing/auth/API contract. Normal/release SSH stays off and is not a Parent API transport. Activity installation, backup/restore, audio/network management, SSH control and system update remain unavailable capabilities until their typed platform services/broker exist. The current shared pairing token and plaintext HTTP remain explicitly PROVISIONAL bootstrap/transport and cannot satisfy production pairing security.
- Remaining blockers: current R7 remains the primary blocking platform phase; the newer repository head still needs a genuine source-gate run; production parent pairing still needs short-lived Greia-local QR/code challenge + Allow/Deny and authenticated encrypted transport; privileged parent operations still require the R12 typed broker and R10/R11 service prerequisites.
- Next exact step: when repository verification is run on the owner-controlled Linux checkout, include `tests/test_parent_api.py` and preserve the first genuine failure. Separately, the next Parent slice is local pairing-challenge state/Greia-screen confirmation design followed by the typed privileged broker contract; do not implement SSH/package installation as shell shortcuts.
- Commit(s): `50591969e11278bb1e767cf3e2da80cdb0b7e192`, `10fc96dba2387f3fe7a6641eccec5cf79d07a05e`, `e04aa162ee78c0e42b7b353975ad957f4f631776`; plan/HANDOVER synchronization commits follow this entry.

## 2026-08-18 — R7 hardware reconciliation + R10/R12 preparatory launcher/package tranche (non-closing)

- Implemented: deeply reconciled the August real-hardware install/boot failures back into authoritative build inputs and hardware-independent regression contracts; made live/target storage initramfs policy target-kernel-aware and architecture-neutral; persisted GUI-stdin, runtime-directory, provisional-Xorg wrapper/service, legacy-input, Bubblewrap mount-topology and kiosk-focus fixes; removed known-password/root-SSH bootstrap behavior from both canonical builders so developer reachability is key-provisioning-only. Added a reusable lightweight launcher presentation layer with bounded motion/scroll/depth primitives, shallow icon/card shadows, hover/selection effects, a short launch squiggle/bounce, explicit Activity name bands, scrollable two-row collections, dedicated launcher categories, stable category icons, persistent in-category icon/title + local Back hierarchy, and package-owned bounded icons. Added the guarded `.greiaactivity` **new-install** service with bounded archive validation, ordinary registry/trust validation, immutable digest-addressed versions, receipt-before-activation ordering, process-wide local-store `flock` serialization, atomic activation, a distinct `PARENT_TRUSTED_UNSIGNED` source, hot launcher discovery that rebuilds launch authority before catalogue publication, capability-gated Parent API upload, and the pinned Parent HTML upload UI.
- Tests/evidence: new regression source exists for hardware-install invariants, launcher motion/scroll/presentation/category/name/icon behavior, Activity manifests/packages and Parent API/client behavior. These tests were **not executed in this GitHub-connector session**; no new `make verify`, installer-image, QEMU or physical-hardware PASS is claimed. The latest genuinely executed complete owner-controlled aggregate gate remains the 2026-08-16 Ubuntu run with focused 77+32 PASS, full suite 530 PASS, four-Activity project validation PASS and source/shell/footprint PASS.
- Decisions: the Acer exposed general architecture defects; hardware fixes are complete only when physical behavior, authoritative build input, hardware-independent regression and root-cause documentation agree. Build-host probing is not target-hardware authority. Base builders fail closed; profile/package-set labels do not mint credentials. `All` is the launcher root; launcher-local category Back is distinct from ADR-0019 Activity Home/Back. Educational tags are not launcher navigation metadata. R7 remains open and Xorg/xinit remains a provisional compatibility backend. This tranche does **not** close R10: updates/removal/rollback/signature/revocation/save migration remain open. `activities.install` remains false on ordinary/release systems while Parent transport is provisional HTTP.
- Remaining blockers: run the new focused source tests and current `make verify` on an owner-controlled checkout; rebuild and inspect exact live/target images; verify target initramfs contents/media UUID-payload coherence/key-only developer behavior; repeat physical Acer install/boot/input/launcher acceptance and basic acceptance on additional x86 hardware; visually accept Activity labels/category header/back/scroll/hover/launch behavior at 1024×600; complete R7 direct display/input/system-chrome evidence; finish secure Parent pairing/encrypted transport; finish R10 update/remove/rollback/signature/revocation/save-migration policy and implementation.
- Next exact step: execute the focused suites named in `HANDOVER.md`, then `make verify`. If green, rebuild the legacy installer/target via canonical builders, inspect generated initramfs/media contracts, repeat physical install/boot/launcher acceptance, verify explicit key-only developer provisioning, and exercise an owner-enabled `.greiaactivity` install through the Parent HTML client. Preserve the first genuine failure and do not weaken gates to obtain PASS.
- Commit(s): key correction-loop commits include `39d3c46b345e6a5b412fb84b89712e1e6060792`, `48f15ae95349243023fb8798745eac4a70c184ca`, `43687167fc7b51720499ba59cfef6783d1a2b35c`, `33dbe71a4982723e8659f6546bb91deab78b0dcc`, `eeca76c0b87e617785d4b53bae7b0bd337031091`, `8ad1153df01b108a7f15eef4f533a54aa8d0677c`, `40eca5312577eb7d08e8ca485938d6c45984c370`, `7fe0a3a41926a271e47598be4bbc92044b37a8ae`, `d392cfb2065eb123b5bc1c1555e364c7d5fd89f8`, `7bb7119c69881910bca430a2a7ec403da5c0456d`; exact current state and broader tranche history are recorded in `HANDOVER.md` and `docs/reviews/2026-08-18_REAL_HARDWARE_INSTALLATION_AND_LAUNCHER_REVIEW.md`.

## 2026-08-18 — R12 preparatory Parent credential/SSH policy reconciliation (non-closing)

- Implemented: reconciled the owner credential-policy amendment into source, tests, Parent client and living documentation. The end-install random recovery code UX is gone; the installer completion screen reports the simple `greia` / `greia` login. A typed `greia_platform.main_credential.MainCredentialStore` stores the main Parent password only as a bounded PBKDF2 digest with a typed change operation requiring the current password. The Parent API adds `/api/v1/parent-password` (GET/PUT) and the `parent.password` capability; the served HTML client and the pinned external Parent HTML client both expose a Change Parent password control. Per-child Greia-profile passwords already support set/replace/clear without returning material; the Parent client now exposes that control. Developer/test images remain reachable over SSH as `greia` / `greia` after install/reboot (root denied, operator key retained as an additional path); base images fail closed with `greia` locked and SSH off. The live installer overlay's stale desktop-console Xwrapper was also persisted to the appliance-session policy.
- Tests/evidence: executed on the 2026-08-18 local-agent checkout — focused suites (installation-hardware, ui-motion-scroll, launcher-presentation, activity-packages, activity-contract, parent-api, main-credential, installer-engine, installer-state, grub-security, developer-remote, developer-remote-snapshot) **114 PASS**; complete `make verify` **663 PASS**; Parent-App `npm test` at pinned `e30bcbc` **10 PASS**. No fresh installer image or physical hardware acceptance was executed in this session.
- Decisions: the owner policy amendment (§0 of the 2026-08-18 local-agent session doc) is the active contract; old key-only `greiaadmin` and random-recovery-code text is treated as policy drift and reconciled, not preserved. The main Parent password is a typed Greia-owned credential separate from revocable per-device bearer credentials. Development SSH availability and final release SSH policy are separate questions.
- Remaining blockers: rebuild and physically accept a fresh installer/target on the Acer; verify `greia` / `greia` SSH continuity after first boot; live Parent password change + child-password round-trips; launcher physical acceptance at 1024×600; R7 direct display/input evidence remains the primary blocking platform phase.
- Next exact step: build a fresh legacy installer via the canonical builder, write the identified USB media, and run physical install/boot/launcher acceptance; verify SSH continuity and Parent live integration.
- Commit(s): `9676fff`, `9baa48b`, `c02f838`, `ed3ea70`, `36e2cd9`, `9e6f0eb` on Greia `main`; `32c22d8`, `e30bcbc` on `frozenpepper/Greia-Parent-App-Html`.

## 2026-08-18 — R7 early-boot visual/audio architecture tranche (non-closing)

- Implemented: replaced the provisional Plymouth boot cover with a Greia-owned early framebuffer architecture in the normal target and installer path. Added a canonical white-frame logo lineage derived from the legacy final animation frame (Professor Pip mascot + GREIA wordmark): `assets/boot/source/greia-boot-logo.png`, `assets/boot/static/greia-boot-logo.png`, and P6 PPMs in both overlays, with a reproducible `tools/generate_boot_artwork.py`. Registered `greia-early-framebuffer-v1` as the boot-cover backend (empty runtime package set) and switched all x86 profiles off Plymouth. Builders now compile `build/early-boot/greia-fb-splash.c` inside the target root with the target `klcc` toolchain, verify ELF architecture, and purge `libklibc-dev` before manifest/footprint capture; both initramfs trees get the hook plus init-top/local-premount/init-bottom nonblocking draw attempts. GRUB shows the canonical white frame via `background_image` with zero interactive timeout in both target and installer. Plymouth theme staging, `plymouth-start` ordering, quit/release handling and masks were removed. The launcher now presents the white frame immediately, then a one-shot monotonic-time intro (target 0.85 s, hard max 1.0 s) and a gentle ~0.8 s PCM boot chime that starts only after the first real frame and fails silently.
- Tests/evidence: executed on the 2026-08-18 local-agent checkout — boot/profile/installer focused set **108 PASS**; boot-experience contract suite **16 PASS** (including chime WAV validity, white-frame artwork lineage, P6 PPM equality, initramfs hooks/stages, builder target-arch compile contract, GRUB logo, intro bounds, one-shot intro/chime); complete `make verify` **706 PASS**. No fresh installer image or physical hardware acceptance was executed in this session.
- Decisions: Plymouth is migration debt, not the future Greia boot architecture. The legacy 52-frame animation is artwork source material only. The early renderer queries fbdev geometry at runtime and never encodes Acer/1024×600 assumptions. The launcher owns animation and audio; initramfs stays Python/SDL/audio-free. `_RELEASE_SAFE_BOOT_COVERS` remains empty until physical acceptance.
- Remaining blockers: build fresh target/installer images and inspect generated initramfs (renderer architecture, PPM, no Plymouth/build-only leak); physical Acer boot acceptance (consoleless, white continuity, intro <=1.0 s, chime, one-shot, SSH/logs); second x86 machine/VM anti-Acer check; R7 direct display/input evidence remains the primary blocking platform phase.
- Next exact step: build a fresh `legacy-x86-i686-dev` installer/target via the canonical builder, inspect initramfs/image artifacts, then run physical Acer + second-machine boot acceptance.
- Commit(s): `0bbc996`, `9d0cb8e`, `6a82d4a`, `70cd73d`, `789629e`, `1516fe1` on Greia `main`.

## 2026-08-19 — Platform Unicode/color-emoji and Writing tranche (non-closing)

- Implemented: extended the existing Nunito `GreiaTypography` service into one platform-owned mixed-text renderer with Noto Color Emoji fallback, Pillow embedded-color rasterization, hard-bounded emoji surfaces, safe present-but-broken fallback behavior, Unicode text/emoji presentation-selector semantics, and Unicode extended-grapheme segmentation through the packaged `python3-regex` path. Added `fonts-noto-color-emoji` and `python3-regex` to the Pygame Shell/Python runtime package sets. Added a bounded reusable `EmojiPalette` model. Migrated the first-party Writing Activity from raw/codepoint-based Pygame text handling to Greia typography plus grapheme-atomic cursor movement, Backspace/Delete, undo restoration, wrapping, hit-testing, vertical navigation, preview generation and length truncation; preserved ordinary UTF-8 persistence. Added a large child-facing emoji picker with seven semantic categories and eighteen common emoji per category; it inserts standard Unicode and derives its category/grid geometry from the actual Greia-safe viewport rather than a fixed resolution. Re-exported the typography/grapheme/palette contract through `greia_platform.pygame_ui` and updated the visual style guide, Phase-0 creation requirements and Activity-authoring skill.
- Tests/evidence: added `tests/test_typography_emoji.py` and `tests/test_writing_emoji_editing.py`, including ZWJ/skin-tone/flag/keycap/combining-grapheme segmentation, safe cursor/delete/undo behavior, presentation-selector semantics, palette bounds/selection and package-composition assertions. These new tests are **committed but have not executed in an owner-controlled current checkout**. No current-head `make verify`, image build, real Pygame color-pixel screenshot, C0 footprint/RSS/latency result, or physical Acer emoji/picker PASS is claimed. Private implementation research established the backend approach but is not repository acceptance evidence.
- Decisions: Nunito Sans remains the normal Greia interface family; Noto Color Emoji is a platform fallback, not a system-icon family. Emoji remain ordinary UTF-8 content. Child-visible text editing operates on grapheme clusters rather than Python codepoints. Activities must not crawl host font directories, maintain independent emoji-range/ZWJ logic, or replace protected Greia Home/Back/system icons with emoji. The current Debian CBDT native-strike detail is intentionally hidden inside the renderer so a future SDL3/Web backend can replace it without changing Activity semantics. A missing/corrupt fallback resource degrades without crashing the child session, while release/package verification still requires the declared dependency to be present. R7 production display/session/input architecture remains unchanged and open.
- Remaining blockers: execute the new focused typography/Writing tests and the current complete source gate; validate the Writing Activity with the normal validator; build a current image and verify the installed emoji font/dependencies; visually inspect the required simple/VS16/skin-tone/ZWJ/flag/keycap specimen and picker at 800×600 and 1024×600; measure installed-size, first-render/cached-render latency, RSS and bounded-cache behavior on the C0/Acer floor; prove real input/edit/save/relaunch behavior. A universal cross-surface picker renderer and touch/controller picker navigation remain later work; the Writing picker is the current reference consumer.
- Next exact step: on the owner-controlled Linux checkout run `PYTHONPATH=src python3 -m unittest tests.test_typography_emoji tests.test_writing_emoji_editing -v`, the relevant existing Writing/UI/Activity validation tests, then `make verify`. Preserve the first failure. If and only if the exact current source gate passes, build the canonical image and perform installed visual/resource evidence before describing emoji as physically accepted.
- Commit(s): tranche starts at `b6b39440c056091514814a39cf8230bbda28d60e`; subsequent source/package/Writing/picker/test/docs commits are preserved contiguously on `main` through this plan entry.

## 2026-08-19 — R13B transactional system-update foundation (non-closing)

- Implemented: accepted ADR 0030 and `docs/product/SYSTEM_UPDATES.md`; added the dedicated `docs/development/GREIA_SYSTEM_UPDATE_RELEASE_WORKFLOW.md`; introduced the strict `.greiaupdate` schema-1 artifact (`manifest.json`, Ed25519 `manifest.sig`, whole-slot `payload.bin`) with canonical manifest serialization, exact payload SHA-256/size binding, bounded archive parsing, exact platform-family/architecture/profile compatibility identity, lazy reviewed `cryptography` signing/verification, a typed `SystemUpdateBackend` variation seam and an explicitly fail-closed unavailable backend for today's single-root machines. Added an unprivileged `SystemUpdateInbox` that keeps one current candidate, preserves a free-space reserve, hides local paths from API status and stores/publishes received bytes content-addressably. The Parent HTTP receiver now streams directly into a private staging file on the update-state filesystem and publishes that same inode via hard link, avoiding a second full-size local copy on the C0/Acer disk floor. Added `tools/greia_update.py` with `keygen`, profile-derived `build`, `inspect`, streamed `push` and `status`; normal build derives `profile.id`, `platform.family` and `base.architecture` from the canonical profile and defaults release ID/signer/output name. Added Parent API semantic resources/capabilities for update status/upload/activation, switched the installed Parent service to the update-aware composition while retaining unprivileged `greiapanel`/`NoNewPrivileges`/`ProtectSystem=strict`/empty capabilities, and added a capability-driven `.greiaupdate` upload/status UI in the separately pinned Parent HTML client. Reserved `python3-cryptography` in a separate `system-update` package set that current profiles intentionally do not select.
- Tests/evidence: committed `tests/test_system_updates.py`, `tests/test_system_update_streaming.py`, `tests/test_parent_system_updates.py`, and `tests/test_greia_update_tool.py`; the external Parent client adds `tests/system_update_api.test.js`. Coverage includes structural/hash tamper rejection, strict signature envelope types, signature round-trip/wrong-key behavior when the provider is present, exact compatibility identity, bounded single-candidate inbox/idempotency, same-inode streamed publication, free-space preflight, fail-closed unavailable activation, current `bios-single-ext4` activation-false regression, unprivileged Parent service hardening, profile-derived release identity and Parent client routing/media-type behavior. These tests are **committed but have not executed in an owner-controlled current checkout**. No current-head `make verify`, A/B slot-write, boot-confirmation, rollback, VM update, Acer update or Pi update PASS is claimed. The last complete source evidence remains historical pre-later-tranche evidence; current-head execution is required.
- Decisions: Greia itself is the updater; the Parents client only authorizes, delivers and observes. Update delivery source is independent from activation, so future direct Internet download, Parent upload and USB/SD all feed the same signed artifact/service. Upload receipt is not signature trust and not activation authority. Production authenticity requires a trusted release signature; HTTPS alone is insufficient. Whole-system inactive-slot payloads come before package-by-package or delta mutation. Shared child/platform data must remain outside routine slot replacement and any pre-confirmation migration must be reversible/backward-compatible. The current `legacy-x86-i686` profile remains `bios-single-ext4`; `system.update.activate` is therefore false and no in-place `apt`, active-root mutation, raw `dd`, mount or bootloader shortcut is permitted. RAUC remains a strong measured candidate below ADR 0030, not a selected dependency.
- Remaining blockers: execute the focused/current source and Parent-client gates; measure the `cryptography` and RAUC-vs-minimal-backend resource/dependency delta; define the canonical A/B system-slot + persistent-data layout across x86/Pi; make the canonical release builder emit the exact slot payload consumed by `.greiaupdate`; define trusted public-key provisioning/rotation/revocation; implement privileged inactive-slot staging, boot-selection attempt limits, health confirmation and automatic rollback; prove interrupted/broken candidates in VM and on physical Acer; then implement normal device-direct online channel download and bounded USB/SD discovery through the same bundle service. Production Parent pairing/encrypted transport remains required before normal release code/system upload is enabled.
- Next exact step: on an owner-controlled current checkout run `PYTHONPATH=src python3 -m unittest tests.test_system_updates tests.test_system_update_streaming tests.test_parent_system_updates tests.test_greia_update_tool -v`, then `make verify`, and run `npm test` in the pinned external Parent client. Preserve the first genuine failure and record exact revisions. If source is green, perform the RAUC-versus-minimal-backend C0 measurement and A/B disk/payload-builder design; do **not** enable `system.update.activate` before the slot/boot/rollback evidence exists.
- Commit(s): architecture/product foundation begins at `780f4aab0ac9bd254d9ec4f2d875883ab21b8286`; operator/tooling/Parent/source hardening is preserved on `main` through `6b40bcfab6704ac95dd062699a0cffcc9183288f`; plan/HANDOVER synchronization follows.

## 2026-08-19 — On-Device Parent Settings Panel, Key Chord, Simulator Remote Bridge & UI Performance

- Implemented: Added platform Wi-Fi service (`src/greia_platform/wifi.py`) and SSH maintenance service (`src/greia_platform/ssh_maintenance.py`). Re-exported Wi-Fi models and controller from `greia_platform` in `greia_installer`. Added `KeyChordTracker` (`src/greia_launcher/key_chord.py`) to detect holding `s` + `t` for 5.0 seconds on the initial profile picker screen with immediate reset on key release. Added on-device `ParentSettingsOverlay` (`src/greia_launcher/parent_panel.py`) with parent password gate (`MainCredentialStore`), Wi-Fi network scanner/connector with masked password entry, SSH maintenance on-demand toggle switch, and remote pairing companion info. Integrated key chord and parent settings overlay into `LauncherApplication` and `GreiaLauncherPresentation`. Enabled `network.manage` and `maintenance.ssh` capabilities and added endpoints in `greia_parent` Parent API (`/api/v1/network/wifi` and `/api/v1/maintenance/ssh`). Added 6 new built-in activities (`cucciolo_mio`, `foresta_parole`, `orchestra_animali`, `pasticceria_magica`, `teatrino_fiabe`, `volo_draghetto`). Added standalone storage fallback and API resilience for running activities in standalone mode. Applied rendering performance optimizations across the launcher (bounded label, category, and depth shadow caching; pure text fast path in typography; throttled wallpaper stat checks).
- Activity Simulator Extension: Added `SimulatorRemoteBridge` (`src/greia_simulator/remote_bridge.py`) running a loopback HTTP server (`http://127.0.0.1:8767`) serving an interactive HTML5 web canvas (real-time 30 fps screen stream with mouse/keyboard capture), a REST input API, and a CLI control tool `tools/greia_simulator_ctl.py` (`status`, `screenshot`, `key`, `click`, `move`, `text`, `chord`). Enabled live display streaming and remote input polling in subprocess activities via `python_activity.py`.
- Tests/evidence: Added `tests/test_key_chord.py`, `tests/test_ssh_maintenance.py`, `tests/test_launcher_parent_panel.py`, `tests/test_simulator_remote_bridge.py`, `tests/test_ui_performance.py`, and updated `tests/test_parent_api.py`. Full source gate executed: 781 tests passed in `make verify`, project validation passed, all 10 first-party activities validated, and footprint/shell checks passed cleanly. Live visual and interactive control verified via `tools/greia_simulator_ctl.py`.
- Decisions: Hidden key chord is accidental-activation resistant (holding `s` + `t` for 5.0 seconds). Entering parent panel requires parent password authentication (`greia` by default). SSH remains disabled by default on release images and can be enabled on-demand by parents. Wi-Fi and SSH logic are shared platform services rather than duplicated between installer, launcher, and web parent API. Simulator bridge is developer-tooling-only on loopback and preserves the clean `_draw()` non-override boundary via `_on_frame_presented`.
- Remaining blockers: Physical on-device Acer Wi-Fi association and SSH toggle acceptance testing.
- Next exact step: Proceed to physical test validation and continue R7 direct graphics/session/input phase.

## 2026-08-19 — Device-default language selection across installer and Parent surfaces (non-closing)

- Implemented: added one canonical Greia device-language registry/service in `src/greia_platform/system_language.py`; the initial selector contains English, Italian, Spanish, German, French, Simplified Chinese, Portuguese, Arabic, Hindi, Indonesian, Bengali and Swahili. Added a mandatory flag-first `greia_installer.entrypoint` before the existing installer flow, with pointer/keyboard navigation and viewport reflow; the selected locale is bound into the real `InstallRequest`, so the existing installation engine records it in `/etc/greia-os/install-record.json`. Later Parent changes are stored atomically as `/var/lib/greia-system-settings/language.json`, with resolution precedence override → install record → English. Added `GET/PUT /api/v1/settings/language` and `settings.language` to the Parent API, with the OS returning the canonical language list so browser clients do not carry a competing registry. Added a capability-driven Greia Language card to the pinned external Parent HTML Settings page. Added Language as the first tab of the authenticated hidden on-device Parent Settings overlay and a tightly scoped `greia-languagectl set <supported-locale>` helper rather than broad launcher write/root authority. `get_profile_locale()` now inherits the current device setting when no profile override exists. Added live-installer `fonts-noto-color-emoji`, `python3-pil` and `python3-regex` dependencies so the first-screen flag UI uses the same Greia typography/emoji path instead of failing or rendering tofu on the live image. Added `docs/product/SYSTEM_LANGUAGE_AND_LOCALIZATION.md` and refreshed HANDOVER/Parent-client docs.
- Tests/evidence: committed `tests/test_system_language.py` and external `tests/language_api.test.js`. Source coverage includes the exact canonical registry, `zh` → `zh-CN`, install-record bootstrap and later override, malformed-state fallback, Activity locale inheritance, Parent route/capability/update semantics, mandatory language-first installer entry point, live-installer flag-rendering dependencies, narrow sudo-helper policy and helper executable-mode contract. The earlier **781-test** owner-controlled `make verify` predates this language tranche. These new language changes have **not** executed in an owner-controlled current checkout; no current-head aggregate PASS, Parent `npm test` PASS, rebuilt-installer PASS, Acer language-selector PASS, install-transfer PASS, or reboot-persistence PASS is claimed.
- Decisions: there is one platform-owned selectable-language registry for installer, on-device Parent settings and Parent API clients. Flags are presentation cues only; locale tags remain language identity. The install record remains historical evidence of the original installer choice; later language changes live in separate mutable Greia system state. A selectable locale means Greia can persist/propagate that preference—it does **not** claim every platform surface or Activity already has complete translations, script-font coverage, shaping or RTL layout. Activity fallback remains honest to the locales each Activity actually ships. Arabic/CJK/Indic font/shaping and Arabic RTL, translated platform/Parent string catalogues and responsive translated-text acceptance remain separate localization work. R7 ordering/status is unchanged.
- Remaining blockers: run the focused language/Parent/installer tests and current `make verify`; run `npm test` on the pinned external Parent revision; rebuild the current legacy installer and physically prove the flag-first chooser on the Acer/reference viewport; select Italian, complete install/reboot and verify it becomes the device default; change language from Greia Parents and hidden Parent Settings and verify both surfaces observe the same persistent state after reboot; then execute the separate translation/font/shaping/RTL localization-content tranche where support is claimed.
- Next exact step: on an owner-controlled current checkout resolve/record the exact `main` SHA, run `PYTHONPATH=src python3 -m unittest tests.test_system_language tests.test_parent_api tests.test_installer_engine -v`, then `make verify`, and run `npm test` at the Greia-pinned Parent HTML revision. Preserve the first genuine failure. If source is green, rebuild the canonical legacy developer installer, use the Acer-compatible syslinux/FAT32 media path, and perform the language install-transfer/persistence acceptance above before extending physical support claims.
- Commit(s): language source/product/client work is preserved contiguously on `main`; key late hardening commits include `e8795c721269e6a9837eb96560707724adcddedf` (live-installer typography dependencies), `991d5937812035a3ec4552f9ab5afbfb734298e4` (language regression hardening), and `0fd98ce61e5838475d5915667e4e8f8fcaa9b70c` (installer entrypoint cleanup). Resolve current head because other agents may commit concurrently.

## 2026-08-23 — Launcher hover-transition frame-drop elimination on reference Acer (non-closing)

- Implemented: on-device profiling of the reference Acer Aspire One (`greia-dev.local`, legacy-x86-i686 developer image at source SHA `387ba8da9bf15d188a9afbd0578484182e81ce33`) showed every pointer hover transition rebuilt the full 1024×600 activities scene (~190 ms, ~5 fps), dominated by alpha-blitting the large unconverted shared panel artwork and six card surfaces; steady cached frames were already fast (~3.5 ms). Fixes (commit `68899e9`, pushed to `origin/main`): optional one-time `display_converter` on `PygameVisualSurfaceCache` so shared artwork uses converted fast blit paths (launcher passes a converter and a working-set-sized bounded entry count); pre-composited opaque scene backdrop (background + wallpaper + `ui.panel.base`) blitted once per rebuild instead of blending the big RGBA panel each time; activities cache key split into static scene state versus dynamic hover/launch-tick state so pointer hover and launch animation repair only affected tiles from the backdrop (chrome-hover changes keep the full-rebuild path); profile badge overlay restores from the composed backdrop (fixes wallpaper-era artifacts); adaptive idle pacing (8 ms polls for 1 s after interaction, then 40 ms wake cadence). Added reproducible draw-path profiler `tools/profile_launcher_draw.py` and pixel-equivalence regression tests `tests/test_launcher_hover_scene_performance.py`.
- Tests/evidence: focused launcher suites PASS locally (`test_launcher_pacing_dirty_redraw`, `test_launcher_shell_productization_contract`, `test_launcher_title_and_icon_contract`, `test_launcher_presentation`, `test_launcher_layout`, new hover-scene tests: 6/6). Full discover: 1028 tests, 4 FAIL — all four boot-contract/boot-diagnostics failures reproduce identically on clean HEAD `387ba8d` via stash (pre-existing test/source drift around `panic=30` vs accepted `panic=5` postmortem decision; not touched by this tranche). `make validate` PASS (20/20), `make visual-assets-check` PASS, footprint/shell-check PASS. Physical-device measurements (Acer, i686, SDL dummy draw path): hover transition 189.6 → 26.6 ms/frame (5.3 → 37.6 fps); full scene rebuild 191.0 → 81.8 ms (12.2 fps); steady cached frame 3.46 → 3.34 ms; idle launcher CPU ~10–11% → ~5–8%; card-sweep CPU ~26–46% (avg ~32%) → ~11–25% (avg ~16%); launcher RSS unchanged (~153 MB). On-device visual verification: Collection Home, in-category grid, hover lift + title disclosure pill, selection star, category chips, pagination and rapid cross-card traversal all render correctly with no ghosting artifacts. Evidence scope: physical-hardware performance for these specific phases; not an R7 display/session acceptance and not a simulator/aggregate gate claim.
- Decisions: incremental tile repair is presentation-only and falls back to the proven full rebuild whenever any aspect exceeds tile-level dynamics (chrome hover, missing backdrop, geometry mismatch); the scene backdrop remains a bounded LRU keyed by theme/geometry; pacing constants are measurement-backed against the previously accepted 50 ms-tolerant interaction budget.
- Remaining blockers: pre-existing boot-contract test drift (4 tests) requires owner disposition; aggregate current-head `make verify` PASS remains unclaimed until that drift is resolved.
- Next exact step: owner decides boot-test expectation direction (`panic=30` vs accepted postmortem `panic=5`), then re-run `make verify` on current head; continue R7 from its first incomplete blocking gate.
- Commit(s): `68899e9` on `main`.

## 2026-08-23 — Parent Settings overlay password/input repair and UI-thread stall removal (non-closing)

- Implemented (commit `3c3e91f`): the chord-opened on-device Parent Settings panel could not receive typed passwords because parent-panel mode never activated SDL text input (`pygame.key.start_text_input()`), so `TEXTINPUT` events never arrived while bare KEYDOWN keys still worked. Entry/exit is now centralized in `_enter_parent_panel`/`_exit_parent_panel`, which manage text input and clear stale input events at every transition site in both the production and legacy run loops. Separately, `SystemSshMaintenanceProvider.status()` (two systemctl subprocesses plus a route probe) was called per-frame by the Info tab, blocked mid-draw every ~2 s on the SSH tab and was double-polled by `drain()`; SSH status now refreshes on a worker thread into a queue drained exactly like Wi-Fi scan results, tabs render only cached snapshots with honest placeholders, toggles cache their returned status, Audio-tab mic-gain reads are throttled, and the full-screen translucent dim is composited once per picker-state change (`dim_surface()` + `draw_backdrop=False`) instead of alpha-blended every redraw.
- Tests/evidence: new `tests/test_parent_panel_input_lifecycle.py` (4 PASS: text-input lifecycle across entry/exit, non-blocking throttled refresh returning before slow providers complete, toggle caching without extra polls, mic-gain read throttle). Physical Acer verification via injected 5 s chord through the developer remote surface: auth dialog renders, typed dots appear, unlock succeeds, all five tabs render with device IP from cached status, Info/SSH tabs idle at 6–9 % launcher CPU (previously subprocess-per-frame), close restores the picker. Full discover 1042 tests with only the five pre-existing failures reproduced on clean HEAD (4 boot-contract `panic=30` drifts + stale `_sanitized_environment` signature in `test_child_shell_visual_context`). Case study appended to `docs/engineering/GREIA_PERFORMANCE_BEST_PRACTICES.md`.
- Decisions: text-input lifecycle belongs to the mode-transition seam rather than individual widgets; status/subprocess work is background-per-second, never per-frame; modal dim uses an opaque cached composite keyed by the underlying picker state.
- Remaining blockers: owner disposition of the five pre-existing test failures before any aggregate `make verify` PASS claim.
- Next exact step: continue R7 from its first incomplete blocking gate.
- Commit(s): `3c3e91f` on `main`.

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
- Python and Web, where supported, use common platform semantics including Activity input profiles;
- direct graphics/session/input architecture is accepted and X11 is not an unintended architectural requirement;
- platform-owned Activity Home remains available outside Activity rendering/input authority across every supported runtime/backend;
- controller/joystick support is proven from Shell through representative Activity profiles without broad raw Activity input authority;
- reserved controller system input is intercepted by Greia before Activity delivery where the hardware exposes it;
- Pi 400/500 and required x86 references have evidence-backed support status;
- Activity install/update/rollback and child backup/restore satisfy parent workflows;
- boot/recovery continuity meets the no-visible-Linux contract;
- OS/runtime update and preserve-profile recovery have an accepted signed rollback-safe path;
- the canonical GitHub repository is sufficient to reproduce the source/build/test tree without a chat-session archive;
- `make verify` passes;
- `HANDOVER.md` is current;
- the active-plan reference is removed from `AGENTS.md` as the final administrative action.

---

## 2026-08-23 — R12 preparatory Parent-client repin and implemented discovery reconciliation (non-closing)

- Implemented: re-resolved both repository heads before integration and preserved the concurrent reference-Acer launcher/performance work plus the new engineering performance manual. Detected a connected microphone-gain tranche already present in Greia (`HardwareSettings.mic_gain`, 0.5×–4.0×, default 2.0×) that the rebuilt external Parent client had not yet exposed; added a fail-soft microphone-level control to the rebuilt HTML client, aligned its deterministic demo adapter with the real Greia bounds/default, and added dedicated hardware-audio tests. Froze the coherent Parent runtime/test revision at `7ff7e318eb246618dab26939ba086999864538ce`. Advanced `runtime/parent-app-client.toml` and `runtime/parent-app-client.manifest.json` to that revision and replaced the old observer-era integrity set with the exact rebuilt 12-file runtime. Reconciled `PARENT_MANAGEMENT.md` and `CHILD_ACTIVITY_DISCOVERY_AND_AUDIENCE.md` with current source: audience/adaptive-difficulty manifest fields, `presentation.discovery_tags`, profile age/challenge fields, per-child discovery policy/API, fail-open ranking/filtering, explicit Parent overrides and adaptive one-level sub-Collections are implemented foundations rather than future-only design. Refreshed root `HANDOVER.md` as the current continuation contract while retaining the measured Acer/R7 evidence boundary.
- Tests/evidence: external Parent client exact changed blobs were byte-compared with the local tested copies; `node --check src/views_device.js` PASS; `node --check src/demo_api.js` PASS; `npm test` **28/28 PASS**. The regenerated Greia Parent-client manifest was checked locally against the exact Parent runtime bytes: **12/12 byte-count + SHA-256 PASS**; the TOML pin parsed successfully and its revision matched the manifest. No hosted GitHub Actions were queried/run. No current Greia aggregate PASS is claimed: the retained current discover evidence remains 1028 tests with 4 pre-existing boot-contract/diagnostics failures around stale `panic=30` expectations versus accepted `panic=5` source/postmortem direction.
- Decisions: the Parent HTML client remains one API-first product renderer; deleted MutationObserver-era modules stay deleted. Microphone gain is currently a typed hardware setting and does not imply the broader `settings.audio` capability is complete. Parent runtime JavaScript remains exact-revision/integrity pinned and is never fetched from moving repository `main`. Adaptive child discovery remains bounded to Home → primary → optional sub-Collection → Activity; primary/group vocabularies are platform-owned; effective catalogue is per child after Parent policy; missing audience metadata fails open; explicit Parent overrides win. This cross-cutting R12 preparatory work does not close/skip R7 or production Parent pairing/encrypted transport.
- Remaining blockers: owner disposition of the four stale boot-contract tests before a current aggregate green claim; R7 direct graphics/session/input remains the first blocking architecture phase; Parent manual desktop/mobile visual acceptance remains open; Parent client is still source-pinned-not-yet-vendored; production pairing needs short-lived challenge + local Allow/Deny + authenticated encrypted transport; complete R10/R11/R12 privileged/package/backup work remains governed by the dependency map.
- Next exact step: preserve `7ff7e318...` as the Parent runtime pin unless a newer reviewed runtime is intentionally accepted; on an owner-controlled browser checkout perform desktop/narrow visual acceptance including mic gain; separately resolve the `panic=30` vs `panic=5` boot-test direction, rerun current aggregate verification, then continue R7 from its first incomplete gate without conflating launcher-render performance with display/session closure.
- Commit(s): Parent `08da3d0e442bb7fab51b52c4c0642905757733bd`, `bf47c9a1056c9223aabb81402a3071d56cd22027`, `7ff7e318eb246618dab26939ba086999864538ce`; Greia `e9576fdbab37cc5c2a134743c39d9238ef288c95`, `31ea8afab5d43fde5a994dee274b43c6eef63ec8`, `e8802c5130434fb9ec05ea42adaa06854d7893a3`, `43cbd012298284c1605c3eae7403462e8505cea8`, `5fa3452329b49ca71b9f95533b64591e285faa58`; this plan-append commit follows.

---

## 2026-08-23 — Achievement Presentation, Activity Victory Contracts & Progression Simulator Acceptance (non-closing)

- Implemented: executed the complete interactive simulator acceptance protocol from `Greia_Achievement_Activity_Simulator_Acceptance_2026-08-23.md`. Verified full lifecycle and presentation of achievements, star progression, and shared Activity victory screens across Clinica Cuccioli, Memory delle Meraviglie, and Costruiamo Ponti. Cleaned up redundant `mark_activity_ready()` calls in Activity victory branches and updated history test assertions to reflect progression policy rules.
- Tests/evidence: full protocol executed in `./tmp/greia-achievement-simulator-acceptance/` with verdict **ACCEPTED** recorded in `results.md`. 23 screenshots captured across initial route, out-of-order rejection, shared victory cards, celebratory popups, NEW/seen badge library states, restart persistence, profile isolation, and 5 responsive viewports (`1024x600 normal`, `1024x600 large`, `1280x800 normal`, `1366x768 compact`, `1920x1080 normal`). Verified once-per-session star award rule (`star=1` after 5 patients; `star=3` after 3 bridge crossings), secret badge concealment (`greia.stars.constellation` hidden, visible denominator `/6`), zero spurious frame repaints during 5s idle display, and full profile isolation. All 1,110 repository unit tests PASS.
- Decisions: activities remain pure domain event producers and never mutate stars or unlock badges directly; celebration dismissal preserves NEW tag until library viewing; secret badges remain concealed from locked slots and total counts until unlocked; idle static screens remain strictly event-driven with 0 idle frame repaints.
- Remaining blockers: R7 display/session direct KMS architecture remains the first blocking architecture gate.
- Next exact step: proceed with R7 direct KMS and input architecture milestones.


## 2026-08-24 — Platform-owned microphone processing physically accepted on reference Acer (non-closing)

- Implemented and physically accepted the ADR 0031 lightweight microphone route on the reference Acer Aspire One (Atom N270, Debian 12 i686): `greia_mic_light` as an in-process ALSA ExtPlug (`src/greia_platform/audio_alsa/`) running SpeexDSP denoising at its in-spec 24 kHz via FIR decimation from the 48 kHz transport, with a primed delay-line FIFO; on-demand only (no daemon, zero idle cost). Boot probe service maintains `/run/greia-audio/lightweight-ready` from a real capture probe; verified recreated automatically after a real reboot.
- Integration finding: SDL 2.26 (pygame 2.1.2) cannot open arbitrary ALSA PCM names, so routed `audio.basic` launches now also receive `ALSA_CONFIG_PATH` composing the Activity's ALSA view (raw `hw:` hints hidden, `default`/`sysdefault` resolved to the routed asymmetric PCM: capture through the denoiser, playback through stock dmix). New SDK accessor `get_sdl_capture_device()` designates the SDL-enumerated device carrying the route; Teatrino migrated off first-device enumeration. Processing-off and non-`audio.basic` launches verified to receive no route.
- Physical evidence (see `docs/reviews/2026-08-24_ACER_MICROPHONE_PHYSICAL_ACCEPTANCE.md`): live route proof during real launcher-driven Teatrino recording (capture hardware at 48000 Hz owned by the Teatrino pid); measured −19.9 dB stationary noise-floor reduction with voice band preserved (stimulus A/B within ~1.5 dB), zero glitches, ~5–10% of one core, +0.4 MB RSS; Parent API default/off/restore/reboot-persistence PASS; negative capability check PASS. Owner A/B verdict: routed clearly better. Advanced endpoint intentionally not installed (`available.advanced = false`).
- Commits: microphone tranche landed across `51ad24e`..`2972127` on `main` (plugin, composition, launcher/SDK/Teatrino migration, tests, this evidence). Parent client pin unchanged at `f64067b` (runtime bytes identical to the locally tested `ce8ef76`; 45/45 npm tests, syntax checks, desktop+mobile visual review PASS).
- Remaining: image-build integration must compile the ALSA plugin into future i686 images (images without it honestly fall back to raw); R7 display/session direct KMS architecture remains the first blocking architecture gate.

## 2026-08-24 — Nascondino nel Bosco Performance & Composition Overhaul (non-closing)

- Implemented: Complete refactoring and optimization of `org.greia.nascondino-bosco` (Woodland Hide & Seek) following `skills/greia-activity-authoring/ENGINEERING.md`, `REFACTORING.md`, and `TERMINAL_RENDERING.md`. Decomposed the monolithic 714-line `main.py` into cohesive modules: `woodland_model.py` (domain state, animals, grounded spots, invariants), `woodland_art.py` (pre-rendered background baking with `PygameSceneRenderer`, cached animal portraits, cute peeking clue sprites, Lilli mascot guide), `woodland_audio.py` (synthesized sound effects for rustle, pop, and victory), `woodland_renderer.py` (one-pass active game compositor, responsive HUD layout, target card, star pill, leaping animal animation, sparkle particles), `woodland_app.py` (lifecycle, event loop, input dispatch, `PygameCompletionScreen` terminal victory integration), and thin `main.py` composition root with test compatibility exports (`ANIMALS`, `SEASONS`, `WoodlandAudio`, `SPOTS`).
- Visual composition fix: Grounded all 5 interactive hiding spots to real scene geometry in `forest_meadow_day_v1` (left hero oak tree hollow at `x=110, y=350`, left round bush at `x=125, y=475`, center fallen log at `x=485, y=485`, right rock cluster at `x=715, y=480`, right flowering bush at `x=890, y=470`). Eliminated all floating procedural shapes and the floating pine tree at `y=210` in the sky.
- Physical Acer performance evidence: Pre-rendered static scenery once onto an opaque 1024×600 surface (`1.88 ms` blit time) and cached all font and animal portrait surfaces. Physical measurement on Acer Aspire One (Intel Atom N270 1.6 GHz, 32-bit Debian 12) demonstrated frame render time dropping from **505.35 ms (2.0 FPS)** to **9.05 ms (110.5 FPS capability, locked at 30 FPS)** — a **55× speedup** in per-frame rendering time.
- Tests/evidence: Added `tests/test_activity_nascondino_bosco.py` (9/9 PASS). Full test suite executed: **1,142 tests PASS**, project validation PASS, all 19 first-party activities validated cleanly. Deployed and verified on physical Acer hardware (`greia-dev.local`). Tested interactive end-to-end flow in the simulator (`greia_simulator.child_shell`): profile login, category navigation to `Esplora`, launch of `Nascondino nel Bosco`, 4 animal discoveries, `PygameCompletionScreen` terminal victory presentation ("TROVATI TUTTI!", "GIOCA ANCORA"), restart round via `primary_contains`, and clean return to Shell via protected Home button `(36, 36)`. Fixed `primary_action_rect` to canonical `primary_contains` on `PygameCompletionScreen`.

---

## 2026-08-24 — Activity Top Space Reclamation and Painting Performance Optimization (non-closing)

- Implemented: Reclaimed ~100px of wasted vertical screen space across first-party creation activities by integrating Activity toolbar buttons directly into the top bar (`ChildUiMetrics.activity_toolbar_button`) alongside platform-owned Home/Back system chrome, and starting activity content (`ChildUiMetrics.activity_content_rect`) immediately below the top bar (~80px instead of ~178px).
- Vertical space gains on 1024×600:
  - Painting (Drawing) canvas height: **326px → 420px (+28.8% usable canvas)**
  - Writing editor height: **404px → 498px (+23.3% usable editor)**
- Painting performance optimization:
  - Pre-scaled and cached all tool button icons, color dish wells, brush size buttons, and gallery card frames on initialization, completely eliminating all 17 per-frame `pygame.transform.smoothscale()` calls (over 510 software bilinear rescales/second on CPU).
  - Pre-rendered static studio background onto a dedicated display-format Surface.
  - Pre-instantiated status fonts and pre-rendered status label surfaces (`"Salvo"`, `"Salva..."`, `"Errore"`).
  - Frame render time dropped significantly, eliminating CPU hotspots on Atom/Pi class hardware.
- Tests & Evidence:
  - `test_activity_ui.py` (8/8 PASS): verified all toolbar buttons and content rectangles across compact, normal, large sizes and resolutions (640×480 to 4K) remain strictly non-overlapping with system chrome protected region.
  - `test_core_activity_system_safe_ui.py` (3/3 PASS) and `test_core_creation_activities.py` (16/16 PASS).
  - All 19 activities validated cleanly via `tools/validate_activity.py`.
  - Project validated via `tools/validate_project.py`.
  - Simulator visual captures across 1024×600, 800×600, 1280×720, 1366×768, 1920×1080 and Compact/Normal/Large interface sizes saved in `tmp/simulator_evidence/`.

---

## 2026-08-24 — Labirinto Magico Fullscreen Expansion, Extreme Complexity & Sliding Movement (non-closing)

- Implemented: Overhauled `org.greia.labirinto-magico` (Magical Labyrinth) following `skills/greia-activity-authoring/ENGINEERING.md`.
  - Removed the cramped on-screen D-pad arrow controls that previously consumed the entire right side of the screen.
  - Expanded the maze across the full viewport (~2.5× screen area) below a streamlined Home-safe top bar HUD (Star score pill, Difficulty switcher, World theme switcher, New Maze button).
  - Scaled up difficulty complexity with 9 progressive levels up to an intricate **89×41** grid ("Infinito") with 35 collectible crystal stars and hundreds of corridors.
## 2026-08-24 — Il Volo del Draghetto Performance, Responsive Arrow Input & Endless Flight Overhaul (non-closing)

- Implemented: Complete performance, look, and gameplay overhaul of `org.greia.volo-draghetto` (Il Volo del Draghetto / Dragon Flight) following `skills/greia-activity-authoring/ENGINEERING.md`.
  - Identified and eliminated the Intel Atom N270 software blitting bottleneck: blitting full-frame un-converted `1280x220` transparent `SRCALPHA` surfaces across the frame twice per tick caused CPU-bound floating-point software alpha-blending that consumed **53.63 ms/frame** alone, pushing frame times to **73.04 ms (~13 FPS)**.
  - Rewrote `dragon_art.py` and `dragon_renderer.py` using hardware-friendly display-converted colorkey surfaces (`surface.convert()` with `.set_colorkey((1, 2, 3))`).
  - Replaced giant continuous alpha strips with 3 fast pre-rendered storybook cumulus clouds scrolling with independent parallax velocities (`0.23 ms` total).
  - Measured physical Acer Aspire One frame render time: dropped from **73.04 ms** to **6.19 ms** (a **12× speedup** / ~161 FPS rendering headroom, running locked at 30 FPS with ~20% CPU load).
  - Cleaned up HUD and interaction design: removed all intrusive text toast banners ("SCATTO ARCOBALENO", "20 STELLINE", etc.) that caused performance hiccups and readability friction for young children.
  - Converted gameplay from a 20-star victory interruption into an endless, relaxing flight with cumulative stars (`⭐ 228  🏆 3495`), 10-star fanfare audio cues, and continuous scenery/obstacle generation.
  - Added responsive, snappy arrow key altitude control (`Up`/`Down`/`W`/`S` at continuous and discrete steps), right-arrow turbo dash, and accessory customization (`👑 Look`).
- Architecture:
  - Decomposed into `dragon_model.py`, `dragon_art.py`, `dragon_audio.py`, `dragon_renderer.py`, `dragon_app.py`, and thin `main.py`.
- Tests & Evidence:
  - `tests/test_activity_volo_draghetto.py` (**10/10 PASS**).
  - Full test suite `make verify`: **1,167 unit tests PASS**, project validation PASS, all 19 first-party activities valid.
  - Physical deployment and live verification on Acer Aspire One display `:0` (`greia-dev.local`). Live screenshots confirm smooth 30 FPS animation, responsive arrow controls, rainbow boosts, cloud bounces, accessory toggles, and clean uncluttered HUD.



