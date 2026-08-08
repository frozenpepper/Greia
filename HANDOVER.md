# Greia — Standalone Engineering Handover

**Date:** 2026-08-08  
**Version:** `0.13.0-phase0-dev`  
**Repository:** `frozenpepper/Greia` (private)  
**Active branch:** `r6-runtime-integration-recovery`  
**Draft PR:** #1 — `R6.2: runtime-neutral Runtime Manager integration and remote recovery`  
**R0 tracking:** issue #2 — `R0: restore GitHub as complete reproducible Greia source of truth`  
**Current functional phase:** R6 — Device Capability / HAL / Runtime integration

## Current state in one paragraph

The long-running v0.12 recovery incident is now bounded correctly. The exact uploaded `pip-kids-os-phase0-v0.12` archive was used as the byte authority for the historical Phase-0 baseline. The Greia-migrated baseline was rebuilt locally and passed its original complete **140/140** provider-free gate. GitHub now contains the recovered baseline source/build/test/config tree and **all 123 PNG assets**, with every PNG verified byte-for-byte against the archived v0.12 SHA-256 ledger before commit. A fresh GitHub checkout at the post-recovery branch reports **337 tracked files, 123 PNGs, Python compilation PASS, and 158/158 unit tests PASS**. Full `make verify` now reaches project validation and stops only because the later, post-v0.12 R5 implementation file `src/greia_platform/history.py` is absent. That file is not in the v0.12 archive, is not present anywhere in the current `/mnt/data` runtime, is not present in File Library search, and returns 404 at the relevant historical R5 Git refs. Do not reopen the ZIP/binary recovery: that part is complete. The remaining continuity blocker is specifically the lost post-ZIP R5 history/progression implementation authority.

---

## 1. Mandatory resume order

Before implementation work:

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
13. GitHub issue #2 and draft PR #1

Do not begin R7 until R6 closure criteria and repository continuity requirements are satisfied.

---

## 2. Non-negotiable architecture

- Greia Shell is the child's operating environment; Linux is substrate.
- `Activity` is the stable abstraction above Python, Web, and future runtimes.
- Package trust/origin, permissions, storage, sessions, progression/rewards, install/update, backup/restore and parent policy remain platform-owned.
- Runtime adapters own only runtime-specific package/static validation, launch preparation, runtime support metadata and lifecycle declarations.
- Hardware truth comes from the Device Capability Service/HAL, never Activity manifests or environment variables.
- ARM and legacy x86 are peer first-class platform families.
- Xorg is provisional; target display direction is direct DRM/KMS beneath Greia semantic contracts.
- Durable Activity state must be architecture-neutral and brokered through shared platform services.
- Activities report factual normalized events; Greia owns global reward/progression amounts.
- Do not recreate the rejected generic `Resource Service`.
- Do not reconstruct missing security/storage/history authority from prose merely to satisfy tests.

---

## 3. Phase state

```text
R0   canonical complete GitHub repository                         OPEN — narrowed to later R5 source loss
R1   package trust / PermissionBroker / Activity authority        previously verified locally
R2   runtime-neutral lifecycle / READY / watchdog                 previously verified locally
R3   permanent Activity identity / manifest semantics             previously verified locally
R4   Universal Storage Service                                    previously verified locally
R5   sessions / events / progression / reward ledger              previously verified locally; history.py source currently lost
R6.1 Device Capability Service / typed HAL                        previously verified locally
R6.2 Runtime Manager / runtime validation / launcher integration  IN PROGRESS
R7+  not started
```

Historical complete-tree milestones recorded before source loss:

```text
R2   159/159
R3   169/169
R5   213/213
R6.1 219/219
```

The latest currently reproducible clean-GitHub evidence is **158/158 unit tests PASS** plus exact asset recovery. The historical 219/219 full result must not be claimed as currently reproducible until the post-v0.12 R5 source gap is recovered from an exact authority.

---

## 4. R0 recovery — what is now complete

### 4.1 Exact archive authority

The exact uploaded v0.12 ZIP used for recovery had SHA-256:

```text
7afb5028aa9f70930de1df8df4aa5a1fe00321fbfdeb94a4316cb234c332b124
```

Archive inventory:

```text
318 files total
123 PNG files
46 Python source files
```

The Greia-migrated baseline was rebuilt from those bytes and passed:

```text
140 / 140 provider-free tests PASS
project validation PASS
shell/source checks PASS
```

### 4.2 Missing baseline text/source tree restored

The active GitHub branch previously had only about 105 tracked files and no Makefile verification target. The archive-derived Greia baseline was reconciled by adding missing files only; newer R1–R6 files were preserved rather than overwritten.

The recovered set included missing build scripts, installers, system overlays, runtime configuration, Activities, tools and baseline tests.

### 4.3 All 123 binary assets restored exactly

The binary recovery is complete and must not be reopened.

Authoritative source inputs were taken from the locally rebuilt ZIP tree and hash-verified before transport. Runtime icons/contact sheet were regenerated using the recovered extractor and then every resulting PNG was checked against the archived SHA-256 ledger.

GitHub independently required:

```text
four source/boot input hashes PASS
runtime art regeneration PASS
ZIP_LEDGER_PNGS_VERIFIED=123
unit suite PASS
```

The resulting Git commit is:

```text
1d34e5e2c67d0113e146c7fa48d16dc60aa9c82c
recovery: restore all 123 ZIP-verified binary assets
```

Representative recovered path:

```text
assets/icons/core/v1/128/unicorn.png
```

### 4.4 Clean GitHub checkout after recovery

A clean GitHub Actions checkout after the asset commit reported:

```text
FILES=337
PNG=123
Python compile PASS
158 / 158 unit tests PASS
```

All asset tests pass. `make verify` now proceeds through the unit suite and stops in `tools/validate_project.py` only at:

```text
ModuleNotFoundError: No module named 'greia_platform.history'
```

This is a fundamentally different state from the pre-recovery repository: the v0.12 baseline and binary library are now durable in GitHub.

### 4.5 Recovery machinery cleanup

Temporary transport workflows, base64 staging, trigger files and incomplete recovery chunks were removed after successful persistence:

```text
c746125a978b9286c5508e51fe2958c9ec3eae60
recovery: remove one-off R0 transport machinery
```

Permanent SHA manifests and recovery ledgers remain as provenance evidence. The normal clean-clone verification workflow remains.

---

## 5. R0 remaining blocker — post-v0.12 R5 history authority

The remaining full-gate error is not part of the v0.12 ZIP recovery.

Missing source:

```text
src/greia_platform/history.py
```

Likely associated historical test source:

```text
tests/test_history.py
```

Known exact evidence:

- v0.12 necessarily predates R5 and does not contain these files;
- current `/mnt/data` was searched directly for `history.py`, `test_history.py`, Greia R6 archives and symbol definitions; no copy exists;
- File Library targeted searches for `greia_platform.history`, `HistoryPolicy`, `ProgressionPolicy`, `history.py`, `test_history.py`, `greia_work`, R6.1 archives and 219-test trees did not recover source;
- GitHub code search finds no `HistoryPolicy`/`ProgressionPolicy` implementation;
- `src/greia_platform/history.py` and `tests/test_history.py` return 404 at relevant R5-era refs, including the recovered R6.1 head;
- R5 commit `89f58f86ac4a5bc3772c0d73ee8497ec3f3d6402` adds the bounded history policy configuration but not `history.py`;
- R5 validation commit `f6ab2181735723091b1876c9513e47d6e25a94a8` imports `HistoryPolicy` and `ProgressionPolicy` from the absent module, confirming the verified local tree had source that Git never received;
- the previous R6.1 handover records the old session-local authoritative tree as `/mnt/data/greia_work` and reports 219/219 PASS, but that ephemeral tree no longer exists.

Therefore the remaining continuity issue is a genuine historical source-loss incident, not an unresolved ZIP transport problem.

**Safety rule:** do not invent this authority from ADR prose or from validator expectations merely to make `make verify` green. Recover an exact copy from a trustworthy prior archive/workspace if one becomes available. If no exact source exists, any reimplementation must be explicitly authorized as a new R5 reconstruction and reviewed as new code, not represented as recovered source.

---

## 6. R6.2 source currently persisted

The current R6.2 branch includes:

- runtime-neutral Activity Registry and package-origin hardening;
- permanent reverse-DNS Activity IDs and one-time trusted aliases;
- `PythonRuntimePolicy` / `PythonRuntimeAdapter` owning Python-specific AST/import/dependency rules;
- one `RuntimeManager` mapping runtime type to adapter;
- unknown/unavailable runtimes fail closed;
- runtime device compatibility consumes injected trusted `DeviceCapabilityService` snapshots;
- forged Activity environment capability strings do not create device truth;
- shared launcher composition constructs one HAL-backed Device Capability Service for PermissionBroker and RuntimeManager;
- `ActivitySupervisor` consumes RuntimeManager and normalizes runtime failures into lifecycle launch failure;
- installed supervisor without an injected RuntimeManager fails closed;
- required platform-issued capability absence refuses launch before process creation.

Focused R6.2 evidence remains:

```text
17 / 17 focused tests PASS
```

The clean restored tree additionally runs **158/158 current unit tests PASS** before hitting the missing R5 history module during project validation.

---

## 7. Exact next action

Do not reopen the v0.12 recovery and do not start R7.

The first blocking action is now only:

```text
recover an exact authoritative copy of src/greia_platform/history.py
(and associated test source if available)
```

Search trustworthy historical workspaces/archives first. Once recovered:

1. import the exact R5 source to GitHub;
2. rerun the complete clean-clone `make verify` gate;
3. compare resulting test count with the historical 219/219 evidence and explain legitimate drift;
4. reconcile any remaining later R5/R6 source gaps found by that gate;
5. complete R6 launcher integration review against ADRs 0012, 0014 and 0015;
6. update the active remediation plan and this handover;
7. only then consider R0/R6 closure and R7.

If an exact historical R5 copy cannot be recovered, stop and explicitly decide whether to authorize a new reviewed reimplementation of the missing history/progression service. Do not silently synthesize it.

---

## 8. Current durable commits/evidence

Important current recovery commits:

```text
1d34e5e2c67d0113e146c7fa48d16dc60aa9c82c  recovery: restore all 123 ZIP-verified binary assets
c03893a17e8a08a3dad4aa89e9257ed03fd34915  recovery: run clean-clone gate after complete ZIP asset restore
c746125a978b9286c5508e51fe2958c9ec3eae60  recovery: remove one-off R0 transport machinery
```

Current clean-GitHub evidence from the post-asset verification run:

```text
337 tracked files
123 tracked PNGs
158 / 158 unit tests PASS
full gate blocked only by missing greia_platform.history import
```

Draft PR #1 remains draft. R0 issue #2 remains open but its scope is now narrowed from baseline/asset reconstruction to post-v0.12 R5 source recovery and final reproducibility closure.

---

## 9. Final current-state statement

```text
v0.12 ZIP baseline recovery: COMPLETE
Greia migration of recovered baseline: VERIFIED locally at 140/140
missing baseline text/build/test/config import to GitHub: COMPLETE
123 PNG binary asset recovery: COMPLETE and byte-verified
clean GitHub unit suite: 158/158 PASS
remaining full make verify blocker: missing post-v0.12 R5 src/greia_platform/history.py
historical 219/219 tree: evidence exists, exact missing R5 source does not currently survive
R0: OPEN, now narrowly due to later source loss rather than ZIP recovery
R6.2: IN PROGRESS
R7: DO NOT START
```
