# Greia — Architecture Remediation and Platform Completion Plan

**Status:** ACTIVE — mandatory implementation plan until all closure criteria are satisfied  
**Created:** 2026-08-08  
**Source baseline:** `0.13.0-phase0-dev`  
**Authority:** subordinate to the Greia architecture constitution and accepted ADRs; authoritative for implementation ordering and progress tracking while active

---

## 0. Purpose

This plan converts the 2026-08-08 architecture deep review into an ordered implementation program.

The review found that Greia's architecture is substantially stronger than the current Phase-0 implementation. The existing implementation is a useful hardened prototype, but several boundaries are still provisional or weaker than the architecture requires. The objective of this plan is to close those gaps **without discarding working safety properties, without introducing runtime-specific parallel systems, and without weakening the low-end/ARM goals**.

The plan deliberately puts authority, isolation, lifecycle and data ownership ahead of Web, packaging, graphics polish or ecosystem expansion. New runtime and package work must be built on trustworthy platform boundaries rather than retrofitted later.

When this plan is complete:

- the Greia Activity abstraction is real in implementation rather than mostly architectural;
- each Activity has a kernel/supervisor-enforced writable namespace limited to its own data;
- Activity capabilities are enforced by trusted platform components, not self-reported environment variables;
- the supervisor owns Activity lifetime, readiness, watchdog, graceful stop and forced recovery;
- storage, sessions, progression and reward authority are shared platform services;
- manifests describe facts/requirements rather than granting global reward economics;
- runtime adapters can support Python and Web without forking platform services;
- the child graphics path no longer depends architecturally on X11;
- Raspberry Pi 400/500 and legacy i386 are supported as peer reference families below the same platform contracts;
- `.greiaactivity` install/update and `.greiabackup` backup/restore use the same stable identities and storage model;
- parent controls operate through typed privileged services;
- every major claim is backed by the appropriate source, VM or physical-hardware evidence.

---

# 1. Mandatory continuation protocol

This document is the **active implementation plan**.

Every future contributor/agent working on implementation MUST:

1. read `AGENTS.md`;
2. read the architecture constitution and relevant ADRs referenced there;
3. read this plan before modifying implementation source;
4. find the first phase below whose closure criteria are not all satisfied;
5. resume from that phase rather than inventing a competing work plan;
6. update the progress log in this file after every substantive implementation turn;
7. update `HANDOVER.md` with the exact current phase, completed work, verification and blockers;
8. run the required source verification before claiming a source phase complete;
9. preserve unresolved evidence gates explicitly;
10. commit coherent work to the canonical GitHub repository.

Do not skip an earlier safety/authority phase merely because a later feature is more visible.

Once **all** phases and final closure criteria in this plan are complete, the contributor completing the plan MUST:

- mark this document `COMPLETE`;
- add a final closure log entry with evidence references;
- update `HANDOVER.md`;
- remove the active-plan reference and special resume instructions for this file from `AGENTS.md`;
- retain this file under `docs/plans/` as historical implementation evidence.

---

# 2. Review findings being addressed

## F-01 — Active profile is overexposed to Activities — HIGH

Current Bubblewrap isolation hides sibling profiles and platform state, but binds the entire active profile root writable into the Activity namespace.

That means an Activity can potentially access or mutate:

- another Activity's save directory under the same profile;
- profile customization data;
- profile-local progress data;
- future profile-local service state.

This violates the constitutional durable namespace `(profile_id, activity_id)`.

**Required outcome:** ordinary Activities receive only their own writable Activity data namespace. Additional writable resources are explicit capability-specific mounts or brokered services, never the whole profile root.

## F-02 — Environment capability strings are not an authorization boundary — HIGH

`GREIA_ACTIVITY_CAPABILITIES` is supplied to the child process and consumed by SDK helper checks. An Activity controls its own process environment after launch, so these checks cannot authorize privileged operations.

**Required outcome:** capabilities remain useful descriptive SDK context, but security enforcement occurs in trusted supervisor/broker/filesystem/device boundaries outside Activity control.

## F-03 — Activity lifetime is blocking and lacks platform watchdog/forced-return ownership — HIGH

The supervisor currently uses blocking `subprocess.run()`. There is no durable Activity process/session handle, readiness timeout, health/watchdog path, graceful-stop deadline or platform-owned forced termination contract.

**Required outcome:** Greia owns the process from spawn to cleanup and can always return to the shell after freeze/crash/failure.

## F-04 — Manifest reward amounts conflict with platform-owned reward economics — MEDIUM-HIGH

Current manifests may contain concrete reward definitions such as `reward.star = 1`.

The architecture says Activities report facts; Greia decides global rewards and progression.

**Required outcome:** manifests may declare objective/event semantics, educational contributions and presentation metadata, but global reward values/mappings live in platform policy/configuration controlled by Greia.

## F-05 — Runtime abstraction is explicit in metadata but not yet polymorphic in implementation — MEDIUM

The current registry/supervisor correctly exposes `runtime.type`, but validation and execution are Python-specific.

**Required outcome:** introduce a small runtime-adapter protocol only when it enables concrete multi-runtime work. Avoid broad speculative refactoring and avoid runtime conditionals leaking into platform services.

## F-06 — Universal storage service is architectural only — HIGH for future ecosystem work

Current Activity storage is mostly filesystem convention and environment setup.

**Required outcome:** platform-owned Activity storage API with architecture-neutral key/value/private-file semantics, quota accounting, atomic writes/checkpoints, schema versions and migration transactions.

## F-07 — Automatic session service is architectural only — MEDIUM-HIGH

**Required outcome:** Greia creates authoritative session records independent of Activity cooperation, including normalized start/ready/end/exit reason and bounded history.

## F-08 — Progression/reward ledger is architectural only — MEDIUM-HIGH

**Required outcome:** normalized Activity events feed a platform-owned progression engine and reward ledger. Activities cannot directly mutate global balances.

## F-09 — Xorg is still implemented while Greia targets direct appliance graphics — HIGH architectural debt

Current Xorg behavior is a migration baseline, not the intended architecture.

**Required outcome:** measured DRM/KMS-first graphical/session implementation with a minimal abstraction usable by shell and runtime adapters. Remove Xorg only after equivalent or stronger evidence exists.

## F-10 — ARM is first-class architecturally but no Pi image adapters exist — HIGH project goal gap

**Required outcome:** Pi 400 and Pi 500 board/image adapters and profiles below shared contracts, with physical evidence for boot/display/input/audio/network/removable media.

## F-11 — Web is first-class architecturally but unimplemented — MEDIUM project goal gap

**Required outcome:** benchmark and select an embedded Web engine, then implement a Web runtime adapter sharing lifecycle/storage/session/progression/permissions with Python.

## F-12 — Activity package/install/update format is architectural only — MEDIUM-HIGH

**Required outcome:** `.greiaactivity` transport, safe scanning/import, stable-ID version comparison, staged validation, immutable version install, atomic activation, rollback and save-preserving uninstall.

## F-13 — Portable backup/restore is architectural only — HIGH product requirement gap

**Required outcome:** `.greiabackup` logical export/restore portable across i386/amd64/ARM64 and capable of preserving data for temporarily missing Activities.

## F-14 — Parent management needs brokered privileged authority — HIGH as capabilities grow

**Required outcome:** parent operations use typed privileged services and explicit authorization. Child Activities never gain broad privileged filesystem/process interfaces.

## F-15 — Provisional boot-cover/recovery evidence remains incomplete — HIGH release blocker

Stock Plymouth remains development-only because Linux details can still be exposed under certain paths.

**Required outcome:** verified noninteractive branded boot cover plus graphical recovery behavior, with frame-by-frame evidence.

## F-16 — Hardware/image claims remain unproven — HIGH release blocker

The source test suite does not prove Acer or Raspberry Pi behavior, installed footprint, 768 MiB installer behavior, graphics performance or sandbox/runtime overhead.

**Required outcome:** preserve the existing evidence discipline and close hardware claims only with appropriate VM/physical evidence.

## F-17 — Greia migration residue — FIXED during review, regression-protected

`GREIA_MEDIA_ROOT` and sandbox media hiding still referenced `/media/pip` after the technical rebrand.

**Required outcome:** `/media/greia` is canonical and regression tests prevent reintroduction of active prototype paths outside explicitly historical documentation.

---

# 3. Cross-cutting implementation rules

These apply to every phase.

### 3.1 One platform service per concern

Do not create Python-specific and Web-specific storage, session, progression, package or backup systems.

### 3.2 Trusted authority stays outside Activity processes

An Activity may request or describe capabilities. It may not authorize itself.

Trusted enforcement mechanisms may include:

- mount namespace shape;
- device exposure;
- network namespace/policy;
- Unix socket or other broker endpoints owned by Greia;
- parent-service authorization;
- package validation and trusted Activity classification.

### 3.3 Stable identities

Profile IDs and Activity IDs are durable cross-machine identities. UI names/titles are not identity.

### 3.4 Data is portable

Authoritative child data must not rely on Python pickle, absolute host paths, CPU-native object serialization or machine-specific IDs.

### 3.5 Fail closed

Installed Greia must not silently fall back from a required security boundary to a weaker one.

### 3.6 Resource evidence before dependency adoption

Every new runtime/system dependency must have disk/RAM/latency and architecture-support evidence before becoming part of a certified profile.

### 3.7 No desktop creep

Do not introduce a desktop environment, generic WM or X11 dependency to solve a local problem.

### 3.8 Refactor only for a concrete boundary

Do not rewrite working Phase-0 code solely to match class names from architecture diagrams. Introduce abstractions when they are required for the next verified capability.

---

# 4. Ordered implementation phases

## R0 — Continuity, plan authority and regression baseline

**Goal:** establish this plan as the single active remediation program and lock the current verified baseline.

Work:

- commit this plan before implementation changes;
- reference it explicitly from `AGENTS.md` as mandatory active plan;
- add resume/progress/removal instructions to `AGENTS.md`;
- update `HANDOVER.md` to identify R1 as the current phase;
- add/retain tests for Greia technical naming, including `/media/greia`;
- run `make verify` and record baseline.

Closure:

- plan committed;
- `AGENTS.md` points to it;
- baseline remains 140/140 or higher;
- no known active Greia technical path falls back to prototype naming.

## R1 — Kernel/supervisor-enforced Activity authority and per-Activity storage isolation

**Goal:** make the real security boundary match `(profile_id, activity_id)`.

### R1.1 Define an Activity execution authority model

Introduce a small immutable trusted launch-policy object derived from a validated manifest plus runtime catalogue/trust policy.

It should distinguish:

- ordinary Activity data access;
- read-only removable media;
- audio/device exposure;
- privileged system-Activity operations;
- future broker endpoints.

Do not let Activity code instantiate a more privileged policy.

### R1.2 Restrict writable filesystem exposure

For installed/sandboxed Activities:

- expose only the current Activity's private data directory writable;
- keep host filesystem read-only;
- hide the complete profile registry/tree;
- do not mount the active profile root wholesale;
- expose customization only when needed and preferably through a broker rather than direct write access;
- expose avatar/profile mutations through a narrow request/broker interface, not writable profile root access;
- expose removable media read-only only when explicitly authorized.

### R1.3 Make SDK capability checks advisory/descriptive

Keep capability information available for friendly early errors and feature discovery, but document/test that it is not the security boundary.

Every privileged effect must still fail if the trusted platform boundary did not grant it, even if Activity code forges environment variables.

### R1.4 Tests

Add tests proving:

- Activity A cannot name/mount Activity B's data path;
- an ordinary Activity receives no writable profile customization/progress root;
- forged `GREIA_ACTIVITY_CAPABILITIES` cannot create a privileged mount/broker authority;
- privileged system Activity receives only its specific narrow authority;
- `/media/greia` is hidden unless removable-media read is authorized;
- missing sandbox still fails closed.

**R1 closure:** source tests pass and the generated sandbox command demonstrates least-privilege mounts. Linux Bubblewrap runtime evidence remains separately required.

## R2 — Non-blocking Activity lifecycle, readiness and watchdog

**Goal:** make Greia own Activity lifetime and guaranteed return-to-shell behavior.

Work:

- replace blocking one-shot execution with a supervised process/session object;
- define states such as `STARTING`, `READY`, `RUNNING`, `STOPPING`, `EXITED`, `FAILED`;
- introduce a bounded READY handshake mechanism that works across runtime families;
- record spawn/ready/end timestamps;
- support graceful stop request with deadline;
- force terminate after deadline;
- ensure child process tree dies with parent/supervisor;
- normalize exit reasons (`normal`, `crash`, `launch_failure`, `ready_timeout`, `forced_stop`, `system_shutdown`, etc.);
- guarantee shell recovery independent of Activity cooperation;
- keep UI thread/event loop responsive while Activity runs;
- design pause/checkpoint semantics as capability-based, not assumed universal.

Tests:

- normal exit;
- launch failure;
- never-ready Activity;
- frozen Activity;
- graceful stop;
- forced kill;
- supervisor cleanup;
- exactly one active Activity per child session for Phase 0.

**R2 closure:** deterministic source/process tests pass; real Linux freeze/kill/return behavior becomes an evidence gate.

## R3 — Manifest semantics and platform-owned progression boundary

**Goal:** remove global reward economics from Activity packages before the progression service is implemented.

Work:

- deprecate/remove manifest reward amount definitions;
- define normalized Activity event/objective declarations;
- retain educational skill contributions as descriptive input where useful;
- define score semantics without granting platform currency;
- create platform-owned reward/progression policy mapping Activity facts to global rewards;
- migrate bundled Activities/tests;
- reject manifests attempting to directly grant global reward balances.

**R3 closure:** bundled manifests contain no direct global reward amounts and validation enforces the boundary.

## R4 — Universal Storage Service and transactional save migrations

**Goal:** replace filesystem convention with the runtime-neutral storage contract.

Work:

- define `ActivityStorage` interface/protocol;
- implement profile+Activity scoped key/value data;
- implement private file/blob area;
- atomic writes and checkpoint semantics;
- quota accounting and bounded growth policy;
- storage schema version;
- migration transaction with source snapshot/working copy/commit/rollback;
- architecture-neutral serialization rules;
- integrate Python SDK;
- define transport-neutral operations suitable for future Web bridge;
- preserve existing data paths through migration where required.

**R4 closure:** storage APIs are runtime-neutral, per-Activity isolated and migration-tested.

## R5 — Session Service, event pipeline and Progression/Reward Ledger

**Goal:** establish platform-owned history and progression.

Work:

- authoritative automatic session records from supervisor lifecycle;
- bounded local session-history database/schema;
- normalized Activity event envelope;
- validation/deduplication/idempotency rules;
- platform-owned score/progression calculations;
- reward ledger with auditability and no Activity direct-write path;
- parent-readable summaries;
- backup hooks;
- privacy policy: local child progress is not analytics and is not uploaded by default.

**R5 closure:** Activity cooperation is optional for session existence; forged Activity events cannot directly mutate global reward state outside validated policy.

## R6 — Runtime Adapter abstraction and Python adapter migration

**Goal:** make the existing runtime seam concrete just before adding the second runtime.

Work:

- introduce a small runtime-adapter protocol for package validation, launch preparation, SDK transport, readiness, stop and normalized result;
- migrate current Python behavior into `PythonRuntimeAdapter` without weakening sandbox rules;
- keep Runtime Manager free of Python-specific paths/import validation;
- do not duplicate Storage/Session/Progression logic;
- keep image profile runtime declarations aligned with implemented adapters.

**R6 closure:** Python passes all existing behavior through the generic manager and adding a runtime does not require changes to platform data/progression services.

## R7 — Direct Greia graphics/session architecture

**Goal:** replace Xorg as the target implementation while preserving proven behavior until replacement evidence exists.

Work:

- inventory all X11-specific contracts (`DISPLAY`, Xauthority, `xinput`, `xrandr`, shared IPC/XShm, package sets, installer startup);
- define typed Display/Input platform interfaces;
- prototype SDL direct DRM/KMS/KMSDRM path on Linux;
- determine whether a minimal compositor/session broker is justified for Web surfaces and crash-safe transitions;
- define shell/activity ownership handoff and recovery;
- migrate resolution/input settings to platform adapters rather than shell commands;
- measure memory/disk/latency against Xorg baseline;
- retain Xorg only as explicit compatibility adapter if physical evidence proves necessary;
- remove Xorg package/service dependency from target profiles only after acceptance.

**R7 closure:** direct path passes VM plus required physical reference evidence and no Activity API depends on X11.

## R8 — ARM64 board/image adapters for Raspberry Pi 400 and Pi 500

**Goal:** make ARM first-class in shipping/build implementation.

Work:

- select base/kernel/firmware strategy;
- implement Pi board/image boot adapter beneath shared build profile schema;
- create explicit Pi 400 and Pi 500 profiles only after adapter implementation;
- share Activity/runtime/storage/progression/package/backup contracts unchanged;
- test boot, display, input, audio, Wi-Fi/network, USB/SD, shutdown/recovery;
- measure resource classes and optional capabilities independently from CPU architecture.

**R8 closure:** both Pi reference devices pass the defined physical acceptance protocol.

## R9 — Embedded Web runtime selection and implementation

**Goal:** add Web as a real Activity runtime without turning Greia into a browser appliance.

Stage A — benchmark:

- WPE/WebKit-style candidates first, alternatives allowed;
- disk delta;
- idle/peak RSS;
- cold/warm launch;
- Canvas2D/SVG/JS;
- WebAudio/audio latency;
- optional WebGL;
- direct display integration;
- i386/C0 feasibility;
- Pi 400/500 performance;
- security maintenance lifecycle.

Stage B — adapter:

- packaged local content only;
- no browser chrome/navigation/downloads/devtools in child mode;
- network denied by default;
- Greia SDK bridge uses the same Storage/Session/Event APIs;
- no authoritative unmanaged localStorage/IndexedDB state;
- same lifecycle/watchdog/forced-return model as Python.

**R9 closure:** at least one reference Web Activity passes common Activity acceptance on supported profiles; unsupported low-end profiles report compatibility cleanly rather than bloating C0.

## R10 — `.greiaactivity` package/install/update system

**Goal:** implement simple parent-facing offline Activity distribution with safe updates.

Work:

- strict documented container format;
- stable Activity ID + semantic version policy;
- package manifest with hashes/size metadata;
- bounded safe archive reader rejecting traversal, symlinks, device nodes, case collisions and bombs;
- removable-media bounded discovery without autorun;
- classify New / Update / Installed / Older / Incompatible / Invalid;
- stage to internal storage before full validation;
- install immutable version beside current;
- perform save migration transactionally;
- atomic activation switch;
- rollback on failure;
- preserve saves on uninstall by default;
- reserve signature/trust chain without mislabeling SHA-256 as authenticity.

**R10 closure:** USB/SD multi-package scenarios, interrupted update and rollback are source/VM tested.

## R11 — `.greiabackup` portable backup/restore

**Goal:** meet the core parent requirement that a child's world can move to a new machine.

Work:

- documented logical archive schema;
- profiles, avatars/customization, Activity saves/creations, progression/rewards, bounded session history and installed inventory;
- exclude machine secrets and transient state by default;
- preserve missing-Activity namespaces as dormant save-only state;
- cross-architecture restore tests;
- version compatibility/migration rules;
- integrity checking;
- dedicated security ADR for passphrase encryption/KDF before production encryption is selected;
- parent UI flow for export to and import from USB/SD.

**R11 closure:** representative i386-origin backup restores logically to ARM64/amd64 test fixture without data loss.

## R12 — Parent privileged service and management integration

**Goal:** consolidate privileged machine management behind one typed parent authority layer.

Work:

- typed requests for Activity install/update/remove;
- backup/restore;
- child/profile administration;
- display/input/audio settings;
- network/Wi-Fi;
- diagnostics/recovery;
- authorization/pairing/revocation;
- bounded validated parameters only;
- no arbitrary command execution endpoint;
- audit-safe local logging without child-data surveillance.

**R12 closure:** parent UI cannot escape typed operations into arbitrary shell/system mutation.

## R13 — Boot cover, recovery and release graphical continuity

**Goal:** satisfy the “Linux never appears” product contract without destroying recoverability.

Work:

- replace/patch provisional stock Plymouth path;
- no Escape/details/text fallback in child mode;
- branded failure/recovery surfaces;
- launcher/display/service failure recovery without shell exposure;
- deliberate root-owned recovery path for maintainers/parents;
- high-frame-rate capture from firmware handoff to profile picker;
- test kernel/display failure transitions.

**R13 closure:** release adapter registry accepts the boot-cover backend only after evidence.

## R14 — Full multi-architecture certification and Phase-0 closure

**Goal:** turn source architecture into evidenced supported-system claims.

Required evidence includes:

- exact Acer inventory and selected architecture profile;
- real target/live images;
- installed C0 footprint below hard limit;
- 768 MiB QEMU installer/runtime run;
- installer peak memory/time;
- Bubblewrap/runtime isolation behavior;
- direct graphics/input/audio behavior;
- non-destructive Acer USB boot;
- Pi 400 and Pi 500 physical acceptance;
- Activity watchdog/forced-return;
- install/update/backup/restore scenarios;
- no visible Linux text/desktop path under supported normal/failure interactions.

**R14 closure:** all supported-profile claims have evidence and remaining unsupported capabilities are explicitly classified rather than implied.

---

# 5. Dependency/order map

```text
R0 governance
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
 ├──────────────→ R9 Web runtime
 │
 └→ R7 direct graphics → R8 Pi adapters

R4 + R5 + R6 → R10 .greiaactivity
R4 + R5      → R11 .greiabackup
R10 + R11    → R12 parent management integration
R7 + R12     → R13 boot/recovery continuity
all          → R14 certification/closure
```

Some implementation can proceed in parallel after prerequisites, but no phase may weaken an earlier boundary.

---

# 6. Verification strategy

## Every substantive source change

Run:

```text
make verify
```

If focused tests are needed during iteration:

```text
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

Remove generated `__pycache__`/bytecode before final packaging/validation where activity validation requires it.

## Security-boundary phases

Tests must verify both positive and negative behavior. A feature working is insufficient; unauthorized variants must fail closed.

## Hardware/display phases

Source tests are necessary but never sufficient. Record exact image/profile, hardware, kernel/base, commands/protocol, metrics and captured failure evidence.

---

# 7. Documentation/progress protocol

After each substantive turn update this section and `HANDOVER.md`.

Use entries of the form:

```text
YYYY-MM-DD — Phase Rx.y
- Implemented:
- Tests/evidence:
- Decisions:
- Remaining blockers:
- Next exact step:
- Commit(s):
```

Do not rewrite old log entries to make history look cleaner. Append corrections explicitly.

---

# 8. Progress log

## 2026-08-08 — R0 plan creation

- Implemented: architecture-remediation plan created from the v0.13 deep review.
- Tests/evidence: pre-plan reviewed baseline was 140/140 provider-free tests passing.
- Decisions: authority/isolation and lifecycle precede graphics/Web/package expansion.
- Remaining blockers: R0 AGENTS/HANDOVER wiring; R1 implementation.
- Next exact step: commit this plan, then make `AGENTS.md` reference it as mandatory active plan.
- Commit(s): pending at document creation time.

---

# 9. Final completion criteria

This plan may be marked complete only when all of the following are true:

- R0–R14 closure criteria are satisfied or explicitly superseded by accepted ADR with equivalent/stronger guarantees;
- no open HIGH architecture-review finding remains without a separate active plan/ADR and explicit reason;
- per-Activity writable isolation is real;
- capability security does not trust Activity-controlled environment state;
- Activity lifecycle/watchdog is platform-owned;
- storage/session/progression are shared platform services;
- global reward economics are not Activity-authored;
- Python and Web, where supported, use common platform semantics;
- direct graphics path is accepted and X11 is not an unintended required layer;
- Pi 400/500 and required x86 references have evidence-backed support status;
- Activity install/update and child backup/restore satisfy the parent workflows;
- boot/recovery visual continuity meets the no-visible-Linux contract;
- `make verify` passes;
- `HANDOVER.md` is current;
- the active-plan reference to this file is removed from `AGENTS.md` as the final administrative action.
