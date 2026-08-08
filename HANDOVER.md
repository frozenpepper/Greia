# Greia — Standalone Engineering Handover

**Date:** 2026-08-08  
**Version:** `0.13.0-phase0-dev`  
**Repository:** `frozenpepper/Greia` (private)  
**Active branch:** `r6-runtime-integration-recovery`  
**Draft PR:** #1 — `R6.2: runtime-neutral Runtime Manager integration and remote recovery`  
**R0 tracking:** issue #2 — `R0: restore GitHub as complete reproducible Greia source of truth`  
**Current functional phase:** R6 — Device Capability / HAL / Runtime integration

## 1. Current state

The long-running v0.12 ZIP recovery is **complete**. Do not reopen it.

The exact uploaded v0.12 archive was used as the historical byte authority:

```text
SHA-256: 7afb5028aa9f70930de1df8df4aa5a1fe00321fbfdeb94a4316cb234c332b124
318 files
123 PNGs
46 Python files
```

The Greia-migrated baseline was rebuilt locally from that archive and reproduced its original complete source gate:

```text
140 / 140 provider-free tests PASS
project validation PASS
shell/source checks PASS
```

Missing baseline source/build/test/config files were then reconciled into the current R6 branch without overwriting newer R1–R6 files.

All **123 PNG assets** were restored. The four authoritative binary inputs were hash-checked, the runtime icon set/contact sheet was regenerated through the recovered extractor, and every resulting PNG was verified byte-for-byte against the archived v0.12 SHA-256 ledger before commit.

Binary recovery commit:

```text
1d34e5e2c67d0113e146c7fa48d16dc60aa9c82c
recovery: restore all 123 ZIP-verified binary assets
```

Temporary transport workflows, base64 payload staging, trigger files and incomplete recovery chunks were removed afterward:

```text
c746125a978b9286c5508e51fe2958c9ec3eae60
recovery: remove one-off R0 transport machinery
```

The **final post-cleanup clean GitHub checkout** was executed at:

```text
298336c5c75757f9df843be89dae2b8988b3b80c
```

and reports:

```text
313 tracked files
123 tracked PNGs
Python compile PASS
158 / 158 unit tests PASS
```

The complete `make verify` gate now reaches `tools/validate_project.py` and fails only because a later, post-v0.12 R5 implementation file is absent:

```text
ModuleNotFoundError: No module named 'greia_platform.history'
```

This is no longer a ZIP/binary recovery problem. It is a distinct historical R5 source-loss incident.

## R6.2 launch-authority/device-snapshot coherence — 2026-08-09

The first post-recovery implementation tranche closes a TOCTOU-style authority gap in R6.2. PermissionBroker records the opaque token of the trusted device snapshot used to compute effective capabilities and permissions in every `ActivityAuthority`. RuntimeManager launch preparation accepts that token as the expected compatibility observation, and ActivitySupervisor supplies it before any child process is created. If the Device Capability Service is refreshed and the semantic snapshot changes between authority issuance and launch preparation, launch fails closed. PermissionBroker still computes grants, RuntimeManager computes runtime/device compatibility, and Supervisor coordinates consistency without either service importing the other's authority type.

---

## 2. Mandatory resume order

Before changing implementation source, read:

1. `AGENTS.md`
2. `docs/architecture/GREIA_ARCHITECTURE.md`
3. `docs/adr/0012-platform-architecture-constitution.md`
4. `docs/adr/0013-declarative-image-profiles-and-composable-build-artifacts.md`
5. `docs/adr/0014-greia-identity-arm-parity-and-direct-graphics-direction.md`
6. `docs/adr/0015-activity-identity-capabilities-permissions-and-events.md`
7. `docs/adr/0016-universal-storage-service-and-transactional-save-migrations.md`
8. `docs/adr/0017-platform-owned-sessions-events-progression-and-reward-ledger.md`
9. `docs/plans/2026-08-08_ARCHITECTURE_REMEDIATION_AND_PLATFORM_COMPLETION.md`
10. `docs/reviews/2026-08-08_ACTIVE_PLAN_AUDIT_AND_CORRECTION.md`
11. `docs/reviews/2026-08-08_R6_2_RUNTIME_INTEGRATION_AND_REMOTE_CONTINUITY.md`
12. this handover
13. GitHub issue #2
14. draft PR #1

Do not begin R7 until R0/R6 closure requirements are genuinely met.

---

## 3. Architecture invariants

- Greia Shell is the child's operating environment; Linux is substrate.
- `Activity` is the stable abstraction above Python, Web and future runtimes.
- Package trust/origin, permissions, storage, sessions, progression/rewards, install/update, backup/restore and parent policy are platform-owned.
- Runtime adapters own runtime-specific validation and launch mechanics only; they must not fork Greia platform services.
- Hardware truth comes from the Device Capability Service/HAL, never Activity manifests or environment text.
- ARM and legacy x86 are peer first-class platform families.
- Xorg is provisional; the target display direction is DRM/KMS beneath stable Greia semantic contracts.
- Durable Activity state remains architecture-neutral and brokered through shared services.
- Activities report factual normalized events; Greia owns progression/reward policy.
- Do not reintroduce the rejected generic `Resource Service`.
- Do not reconstruct missing security/storage/history authority from prose and call it recovered source.

---

## 4. Phase status

```text
R0   canonical complete GitHub repository                         OPEN — narrowed to lost later R5 source
R1   package trust / PermissionBroker / Activity authority        previously verified locally
R2   runtime-neutral lifecycle / READY / watchdog                 previously verified locally
R3   permanent Activity identity / manifest semantics             previously verified locally
R4   Universal Storage Service                                    previously verified locally
R5   sessions / events / progression / reward ledger              previously verified locally; history.py currently lost
R6.1 Device Capability Service / typed HAL                        previously verified locally
R6.2 Runtime Manager / runtime validation / launcher integration  IN PROGRESS
R7+  not started
```

Historical complete-tree milestones:

```text
R2   159/159
R3   169/169
R5   213/213
R6.1 219/219
```

Those are valid historical local-verification records, but the historical **219/219** tree is not yet reproducible from current GitHub because the later R5 history module is absent.

---

## 5. R0 recovery that is now complete

### Baseline source

The v0.12-derived Greia baseline was recovered and validated locally at 140/140. Missing baseline files were added to GitHub while preserving newer R1–R6 files.

### Binary assets

All 123 PNGs are now repository-managed. Representative restored path:

```text
assets/icons/core/v1/128/unicorn.png
```

The asset recovery required exact SHA agreement with the archived v0.12 ledger. It is complete and should not be revisited unless a future integrity check proves actual corruption.

### Clean-clone proof

Final cleaned-tree GitHub Actions evidence at `298336c5...`:

```text
FILES=313
PNG=123
compileall PASS
Ran 158 tests
OK
```

The next command in `make verify` fails specifically at the missing R5 import, not at baseline build/source/assets.

---

## 6. Remaining R0 blocker: lost post-v0.12 R5 history authority

Missing implementation:

```text
src/greia_platform/history.py
```

Likely associated lost historical tests:

```text
tests/test_history.py
```

Authoritative recovery searches already performed:

- direct `/mnt/data` filesystem search for `history.py`, `test_history.py`, Greia/R6 archives and `HistoryPolicy`/`ProgressionPolicy` symbols — no source found;
- File Library searches for those paths/symbols, `greia_work`, R6.1 and 219-test archives — no source found;
- GitHub code search — no implementation found;
- direct historical-ref fetches — 404 for both source/test paths at relevant R5/R6 refs;
- R5 commit `89f58f86ac4a5bc3772c0d73ee8497ec3f3d6402` adds `runtime/history-policy.toml`, not `history.py`;
- R5 validation commit `f6ab2181735723091b1876c9513e47d6e25a94a8` imports `HistoryPolicy` / `ProgressionPolicy` from the absent module;
- the prior R6.1 handover records the former authoritative session-local tree as `/mnt/data/greia_work` and reports 219/219 PASS, but that ephemeral tree no longer exists.

Therefore this is genuine historical source loss. It must not be mislabeled as unfinished ZIP recovery.

If an exact historical copy is found, import it and rerun the full clean gate. If no exact copy exists, a replacement must be explicitly authorized as a **new R5 reimplementation**, designed/reviewed from the accepted ADR and surrounding contracts rather than represented as recovered code.

---

## 7. R6.2 currently persisted

Current R6.2 work includes:

- runtime-neutral Activity Registry;
- permanent reverse-DNS Activity IDs and trusted legacy aliases;
- package-origin/source authority hardening;
- Python AST/import/dependency policy behind `PythonRuntimeAdapter`;
- one `RuntimeManager` mapping runtime type to adapter;
- fail-closed unknown/unavailable runtimes;
- trusted `DeviceCapabilityService` compatibility evaluation;
- shared HAL-backed launcher service composition;
- ActivitySupervisor consuming RuntimeManager;
- required platform-issued capability checks before child process creation.

Focused R6.2 evidence:

```text
17 / 17 PASS
```

The restored clean tree additionally proves **158/158 current unit tests PASS**.

---

## 8. Exact next action

Do not reopen v0.12 recovery and do not start R7.

First priority:

```text
recover an exact authoritative copy of src/greia_platform/history.py
and associated historical test source if available
```

Then:

1. commit the exact recovered R5 source;
2. run clean-clone `make verify`;
3. reconcile any additional later R5/R6 gaps exposed by that gate;
4. complete R6 installed-composition review against ADRs 0012, 0014 and 0015;
5. update active plan and handover;
6. only then close R0/R6 and move toward R7.

If no historical source can be recovered, stop and obtain explicit authorization before implementing a new replacement history/progression service.

---

## 9. Durable recovery evidence

```text
1d34e5e2c67d0113e146c7fa48d16dc60aa9c82c  restore all 123 ZIP-verified binary assets
c746125a978b9286c5508e51fe2958c9ec3eae60  remove one-off R0 transport machinery
298336c5c75757f9df843be89dae2b8988b3b80c  final post-cleanup clean-clone verification trigger
```

R0 issue #2 and draft PR #1 have been updated to the same final recovery boundary.

---

## 10. Final state

```text
v0.12 ZIP baseline recovery: COMPLETE
Greia migration of recovered baseline: VERIFIED locally at 140/140
baseline source/build/test/config import: COMPLETE
123 PNG recovery: COMPLETE, exact and ledger-verified
final cleaned GitHub tree: 313 files / 123 PNGs
current clean unit suite: 158/158 PASS
remaining full-gate blocker: lost post-v0.12 R5 greia_platform.history implementation
historical 219/219 evidence: preserved, but exact missing R5 source does not currently survive
R0: OPEN only for later source recovery/final reproducibility
R6.2: IN PROGRESS
R7: DO NOT START
```
