# Greia — Standalone Engineering Handover

**Date:** 2026-08-09  
**Version:** `0.13.0-phase0-dev`  
**Repository:** `frozenpepper/Greia` (private)  
**Active branch:** `r6-runtime-integration-recovery`  
**Draft PR:** #1 — `R6.2: runtime-neutral Runtime Manager integration and remote recovery`  
**R0 tracking:** issue #2 — `R0: restore GitHub as complete reproducible Greia source of truth`  
**Current functional phase:** **R6 overall blocked; R6.2 source architecture PASS**

## 1. Current state

The v0.12 recovery incident is finished. Do not reopen it.

The exact uploaded historical archive remains the byte authority for the recovered baseline:

```text
SHA-256: 7afb5028aa9f70930de1df8df4aa5a1fe00321fbfdeb94a4316cb234c332b124
318 files
123 PNGs
46 Python files
```

The Greia-migrated v0.12 baseline was rebuilt locally at **140/140 PASS**, missing baseline source/build/test/config was reconciled into GitHub without overwriting newer R1–R6 work, and all **123 PNGs** were restored and verified byte-for-byte against the archive ledger.

Key recovery commits:

```text
1d34e5e2c67d0113e146c7fa48d16dc60aa9c82c  recovery: restore all 123 ZIP-verified binary assets
c746125a978b9286c5508e51fe2958c9ec3eae60  recovery: remove one-off R0 transport machinery
```

After recovery, real R6.2 implementation resumed and closed the remaining source-level Runtime Adapter gaps. The latest permanent clean-checkout CI evidence is:

```text
audited checkout: cd317a862b12ba6e85971bf23d0146a108c5faef
repository files at that audit: 314
tracked PNGs: 123
Python compile: PASS
R6 architecture-invariant CI step: PASS
provider-free unit suite: 172 / 172 PASS
```

The same clean checkout then ran `make verify`. The entire 172-test suite passed and the gate stopped only here:

```text
ModuleNotFoundError: No module named 'greia_platform.history'
```

That file is a **post-v0.12 R5 source-loss incident**, not unfinished recovery and not an R6.2 defect.

Detailed executable evidence:

```text
docs/reviews/2026-08-09_R6_SOURCE_CLOSURE_AUDIT.md
```

---

## 2. Mandatory resume order

Before implementation work, read in order:

1. `AGENTS.md`
2. `docs/architecture/GREIA_ARCHITECTURE.md`
3. `docs/adr/0012-platform-architecture-constitution.md`
4. `docs/adr/0013-declarative-image-profiles-and-composable-build-artifacts.md`
5. `docs/adr/0014-greia-identity-arm-parity-and-direct-graphics-direction.md`
6. `docs/adr/0015-activity-identity-capabilities-permissions-and-events.md`
7. `docs/adr/0016-universal-storage-service-and-transactional-save-migrations.md`
8. `docs/adr/0017-platform-owned-sessions-events-progression-and-reward-ledger.md`
9. `docs/plans/2026-08-08_ARCHITECTURE_REMEDIATION_AND_PLATFORM_COMPLETION.md`
10. `docs/reviews/2026-08-09_R6_SOURCE_CLOSURE_AUDIT.md`
11. this handover
12. issue #2 and draft PR #1

Do not start R7 until the R0/R5 blocker is resolved and R6 is re-audited against a complete clean-clone gate.

---

## 3. Non-negotiable architecture

- Greia Shell is the child's operating environment; Linux is substrate.
- `Activity` is the stable abstraction above Python, Web and future runtimes.
- Package trust/origin, permissions, durable storage, sessions, progression/rewards, package/update, backup/restore and parent policy are platform-owned.
- Runtime adapters own runtime-specific validation, process preparation, lifecycle transport and runtime-handle mechanics. They must not fork shared Greia services.
- Hardware truth comes from the Device Capability Service/HAL, never Activity manifests or environment strings.
- Capability requirement, permission request and effective grant are different concepts.
- ARM and legacy x86 remain peer platform families.
- Xorg is provisional evidence/migration infrastructure only. R7 is DRM/KMS-first beneath the stable HAL contracts.
- Durable Activity state remains architecture-neutral and brokered.
- Activities report factual normalized events; Greia owns progression/reward policy.
- Do not reconstruct lost security/storage/history authority from prose and call it recovered source.

---

## 4. Phase status

```text
R0   canonical complete GitHub repository                         OPEN — only later R5 source continuity remains
R1   package trust / PermissionBroker / Activity authority        implemented / prior verification preserved
R2   runtime-neutral lifecycle / READY / watchdog                 implemented / prior verification preserved
R3   permanent Activity identity / manifest semantics             implemented / prior verification preserved
R4   Universal Storage Service                                    implemented; now integrated into real launch sessions
R5   sessions / events / progression / reward ledger              historical implementation lost in part; BLOCKING
R6.1 Device Capability Service / typed HAL                        SOURCE PASS; physical evidence remains later
R6.2 full Runtime Adapter integration                             SOURCE ARCHITECTURE PASS
R6   overall phase closure                                        BLOCKED by R0/R5 and full-gate incompleteness
R7+  not started
```

Historical complete-tree milestones remain useful evidence only:

```text
R2   159/159
R3   169/169
R5   213/213
R6.1 219/219
```

The old 219/219 session-local tree no longer exists, so those results cannot substitute for current reproducibility.

---

## 5. R6.2 work completed after recovery

### 5.1 Snapshot-bound launch authority

Commit:

```text
67cb59c7308c71226777742731d957c845e464a6
fix: bind launch authority to device capability snapshot
```

`ActivityAuthority` records the trusted `DeviceCapabilitySnapshot.token` used by PermissionBroker. RuntimeManager launch preparation accepts that token as the expected device observation, and Supervisor supplies it before process creation. If an explicit device refresh changes the semantic snapshot between authority issuance and launch, the launch fails closed.

This closes the stale-authority/TOCTOU gap without coupling RuntimeManager to PermissionBroker types.

### 5.2 R4 Universal Storage wired into real Activity sessions

Implementation milestone:

```text
04e217a…
feat: wire universal storage into Activity launch sessions
```

Installed composition loads `runtime/storage-policy.toml`, constructs the shared `ActivityStorageService`, and injects it into Supervisor.

For every Activity launch, Supervisor:

- opens the durable `(profile_id, activity_id)` namespace;
- starts one ephemeral `ActivityStorageBroker`;
- passes only `GREIA_STORAGE_SOCKET` and `GREIA_STORAGE_TOKEN`;
- mounts only the ephemeral broker runtime root into Bubblewrap;
- never mounts the durable namespace into the Activity;
- stops/removes the broker on terminal cleanup;
- converts broker-cleanup failure to `platform_failure`.

End-to-end `ActivityStorageClient -> broker -> ActivityStorage` read/write and cleanup are covered by tests.

### 5.3 Runtime-command authority boundary

Implementation milestone:

```text
5fbc675…
refactor: isolate runtime-specific launch command policy
```

`RuntimeCommand` now owns runtime-specific command, package-bounded cwd and bounded runtime environment.

Python-only process policy lives in `PythonRuntimeAdapter`, including:

```text
PYTHONNOUSERSITE=1
PYTHONDONTWRITEBYTECODE=1
```

RuntimeManager rejects malformed commands, cwd escaping the Activity package, duplicate/invalid environment entries, and runtime attempts to overwrite Greia/session/profile/storage or platform-owned `PATH/HOME/XDG/display/audio` variables.

Supervisor no longer contains Python-specific process environment policy and Bubblewrap honors adapter-prepared cwd.

### 5.4 Runtime handle/session mechanics behind adapters

Implementation milestone:

```text
3e3c4f7…
refactor: move runtime session mechanics behind adapters
```

The Runtime Adapter/RuntimeManager seam now owns:

- final runtime-handle creation through `RuntimeInvocation`;
- runtime exit collection and normalization;
- force-stop;
- runtime-handle cleanup.

Supervisor retains Greia sandbox policy, state/deadline semantics and platform resource brokers, but it no longer directly creates `Popen`, signals process groups, or decides whether raw runtime return codes mean normal/crash.

### 5.5 Runtime-owned lifecycle transport

Implementation milestone:

```text
94f93941db32a91e77c8af09f0eab4bb7c28bc07
refactor: move lifecycle transport behind runtime adapters
```

Platform session identity is now independent of runtime transport. Greia allocates `ActivitySession.session_id` before runtime preparation; even unavailable-runtime failures have a valid platform session ID without manufacturing Python files.

RuntimeManager asks the selected adapter for a `RuntimeLifecycleBinding` bound to that exact session ID.

`PythonRuntimeAdapter` owns the current READY/STOP marker transport and supplies:

```text
GREIA_ACTIVITY_READY_PATH
GREIA_ACTIVITY_STOP_PATH
```

Supervisor consumes only the generic lifecycle-control protocol (`ready`, `request_stop`, `cleanup`) and owns only the universal:

```text
GREIA_ACTIVITY_SESSION_ID
```

A runtime lifecycle binding cannot replace platform session identity. Invalid bindings are cleaned before failure propagates.

---

## 6. Permanent R6 clean-clone CI invariants

The standing workflow:

```text
.github/workflows/r0-clean-verify.yml
```

now permanently checks the R6 source architecture before `make verify`.

It asserts:

- typed `GreiaHAL`, Display/Input protocols and `DeviceCapabilityService`/HAL probe exist;
- installed launcher composition constructs one trusted device service shared by PermissionBroker and RuntimeManager;
- authority/device compatibility snapshot coherence remains wired;
- Universal Storage service/broker launch transport remains wired;
- `RuntimeCommand`, `RuntimeInvocation`, `RuntimeLifecycleBinding`, adapter exit/force-stop/cleanup seams remain present;
- Python READY/STOP transport remains in the adapter;
- Supervisor contains no concrete `ActivityControlChannel`, Python marker names, direct `subprocess.Popen`, or process-group signaling;
- legacy X remains explicitly provisional below HAL.

At clean checkout `cd317a862...`, this architecture-invariant step passed before the 172/172 suite.

---

## 7. R6 source-closure decision

The executable audit concludes:

```text
R6.1 source architecture: PASS
R6.1 hardware/direct-graphics evidence: NOT CLAIMED
R6.2 source architecture: PASS
R6 overall phase closure: BLOCKED
R7: MUST NOT START
```

R6.2 now satisfies the source-level Runtime Adapter contract required by ADR 0012/0014/0015 and the active plan:

- runtime-neutral package Registry;
- runtime-specific validation behind adapter;
- trusted semantic device compatibility;
- snapshot-bound launch authority;
- runtime-owned command/environment/cwd;
- runtime-owned handle creation;
- runtime-owned exit normalization;
- runtime-owned force-stop and cleanup;
- runtime-owned lifecycle transport;
- platform-owned session identity;
- shared platform-owned Storage transport;
- installed launcher composition using the same trusted device authority on permission and runtime sides.

Do not reopen R6.2 architecture merely because the full gate is red at the known R5 import.

---

## 8. The only current full-gate blocker

Missing authoritative R5 source:

```text
src/greia_platform/history.py
```

Likely associated lost historical tests:

```text
tests/test_history.py
```

Recovery already exhausted:

- current `/mnt/data` filesystem;
- uploaded File Library;
- current GitHub code search;
- relevant R5/R6 historical refs;
- prior session archive/workspace searches.

The historical R5 commits preserve policy TOML, protocols/brokers and validator references, but the actual `HistoryPolicy` / `ProgressionPolicy` implementation never reached Git.

This prevents:

1. full clean-clone `make verify` PASS;
2. honest restoration of R5 History/Progression authority;
3. wiring the surviving event broker into the real History/Progression service;
4. repository-complete R1–R6 integration proof.

---

## 9. Exact next action

The next step requires an explicit project decision.

If authorized, treat the missing R5 History/Progression implementation as a **new reviewed reimplementation**, not as recovered source.

The new R5 tranche must be derived from:

- accepted ADR 0017;
- surviving `runtime/history-policy.toml` and progression policy;
- surviving event protocol/client/broker contracts;
- surviving Storage and profile identity contracts;
- surviving parent progress-summary contract;
- active-plan R5 closure requirements.

Required order:

1. re-audit all surviving R5 contracts before writing replacement authority;
2. implement `HistoryPolicy` / `ProgressionPolicy` and durable session/progression authority with clean OOP boundaries;
3. restore authoritative automatic session lifecycle recording;
4. wire `ActivityEventBroker` to that authority without giving Activities reward control;
5. restore/expand R5 tests, including idempotency, bounded history, reward ledger and cross-profile/Activity isolation;
6. run the complete clean-clone `make verify` gate;
7. fix only genuine additional continuity gaps exposed by that gate;
8. re-run the R6 closure audit;
9. only after R0/R5/R6 all close may R7 direct graphics begin.

Until that decision is made, do not fabricate a minimal `history.py` merely to turn CI green.

---

## 10. Current durable evidence

```text
v0.12 baseline rebuilt:                       140/140 PASS
post-recovery clean suite:                    158/158 PASS
snapshot/storage/runtime-command evolution:   163 -> 167 tests PASS
runtime-session ownership:                    169/169 PASS
runtime lifecycle binding final tranche:      172/172 PASS
permanent clean-checkout R6 invariants:       PASS
clean-checkout full gate:                     172/172 PASS, then missing history.py
```

Primary current review:

```text
docs/reviews/2026-08-09_R6_SOURCE_CLOSURE_AUDIT.md
```

---

## 11. Final current-state statement

```text
v0.12 recovery: COMPLETE
binary/source baseline continuity: COMPLETE
123 PNGs: repository-managed and ledger-verified
R6.2 source architecture: PASS
current recoverable unit suite: 172/172 PASS
permanent R6 CI invariants: PASS
full make verify: BLOCKED only at lost post-v0.12 greia_platform.history import
R5 History/Progression authority: requires explicit new reimplementation decision
R6 overall: NOT CLOSED
PR #1: KEEP DRAFT
R7: DO NOT START
```
