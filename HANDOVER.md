# Greia — Standalone Engineering Handover

**Date:** 2026-08-08  
**Version:** `0.13.0-phase0-dev`  
**Repository:** `frozenpepper/Greia` (private)  
**Active branch:** `r6-runtime-integration-recovery`  
**Draft PR:** #1 — `R6.2: runtime-neutral Runtime Manager integration and remote recovery`  
**R0 tracking:** issue #2 — `R0: restore GitHub as complete reproducible Greia source of truth`  
**Current phase:** **R6 — Device Capability / HAL / Runtime integration**  
**Status:** R6.1 was previously verified in a complete local tree at **219/219** provider-free tests. R6.2 is substantially implemented and focused-tested at **17/17 PASS**, but **R6 remains IN PROGRESS** because GitHub is still missing parts of the verified tree and the real installed launcher composition root cannot be recovered from Git history.

---

## 1. Mandatory resume order

Before modifying implementation source, read:

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

`AGENTS.md` and the active remediation plan remain authoritative. Do **not** invent a competing master plan and do **not** begin R7 until R6 closure criteria are genuinely met.

---

## 2. Non-negotiable architecture

- Greia Shell is the child's OS experience; Linux is substrate.
- `Activity` is the universal abstraction above Python, Web, and future runtimes.
- Package trust/origin, effective permissions, durable storage, sessions, progression/rewards, package/update, backup/restore and parent policy are platform-owned.
- Runtime adapters may own runtime-specific static/package validation, launch preparation, runtime support metadata and lifecycle feature declarations. They must **not** fork Greia platform services.
- Device capability, permission request and effective permission grant are different concepts.
- Hardware truth comes only from the platform Device Capability Service/HAL. Activity manifests and environment variables are not device authority.
- ARM and legacy x86 are peer platform families. Pi 400/500 are explicit ARM references; old Acer/Atom remains the low-resource floor.
- Xorg is provisional migration/evidence infrastructure, not the target architecture. R7 is DRM/KMS-first.
- Durable Activity state must remain architecture-neutral and brokered through the shared Storage Service.
- Web must eventually bridge to the same storage/session/event/progression services rather than inventing browser-local authority.
- Activity-authored global reward amounts are forbidden. Activities report factual normalized events; Greia owns progression/reward policy.
- Do not reintroduce the rejected generic `Resource Service` idea.

---

## 3. Phase state

```text
R0   canonical complete GitHub repository                         OPEN
R1   package trust / PermissionBroker / Activity authority        VERIFIED in prior complete local tree
R2   runtime-neutral lifecycle / READY / watchdog                 VERIFIED in prior complete local tree
R3   permanent Activity identity / manifest semantics             VERIFIED in prior complete local tree
R4   Universal Storage Service                                    VERIFIED in prior complete local tree
R5   sessions / events / progression / reward ledger              VERIFIED in prior complete local tree
R6.1 Device Capability Service / typed HAL                        VERIFIED in prior complete local tree
R6.2 Runtime Manager / runtime validation / launcher integration  IN PROGRESS
R7+  not started under the remediation program
```

Historical complete-tree milestones:

```text
R2   159/159
R3   169/169
R5   213/213
R6.1 219/219
```

Those counts are historical verified-local evidence. They are **not** currently reproducible from GitHub until R0 is repaired.

---

## 4. R0 — repository continuity problem

R0 is now tracked explicitly in **GitHub issue #2**.

The repository is intended to be the persistent source of truth, but current Git history is not a complete mirror of the previously verified local tree.

Confirmed gaps/drift:

- historical binary asset library is absent; the prior complete tree contained 123 PNGs and representative paths such as `assets/icons/core/v1/128/unicorn.png` are missing remotely;
- `src/greia_platform/history.py` and associated history tests are absent;
- the real installed launcher composition file referred to by the prior handover (historically `src/greia_launcher/main.py`) is absent;
- repository search finds no alternative current construction site using `PermissionBroker.phase0(...)` or `ActivitySupervisor(...)`;
- remote `main` at the R6.1 recovery head contained schema drift: `permissions.py` already consumed the R3 permanent capability/permission model while `activities.py` and `runtime/child-runtime.toml` still contained prototype-era semantics;
- the surviving `tests/test_supervisor.py` was still pre-R2 and tested the removed blocking `.launch()` API, prototype IDs and obsolete helper signatures.

Historical Git-tree recovery was attempted. `history.py`, launcher `main.py`, and `test_history.py` return 404 even at relevant R5-era commit refs. This proves those verified local files were never committed, not merely deleted from later branches.

Do **not** reconstruct missing storage/history/launcher authority from prose. Recover the exact latest complete tree from a trustworthy archive/workspace and import it to Git instead.

R0 closes only when a clean clone contains all required source/assets and independently passes `make verify`.

---

## 5. R6.1 established boundary

The previously verified R6.1 tranche provides:

- typed semantic HAL states/protocols for display, input, audio, removable media, network and power;
- provisional Legacy-X display/input adapters plus Linux audio/removable/network/systemd-power adapters;
- immutable `DeviceCapabilitySnapshot` with semantic capabilities, provenance/details and deterministic state token;
- deep-frozen nested details;
- `DeviceCapabilityService` caching and explicit refresh;
- `HALDeviceCapabilityProbe` mapping hardware/backend state to semantic Greia capability IDs;
- PermissionBroker consuming an injected Device Capability Service;
- required missing capability refusing authority;
- optional missing capability removing dependent feature/grant;
- static capability service only as deterministic test/development fallback.

R6.2 must consume this boundary, not probe hardware independently.

---

## 6. R6.2 implementation now persisted on GitHub

### 6.1 Runtime-neutral Activity Registry

`src/greia_platform/activities.py` now owns shared package facts only:

- permanent reverse-DNS Activity ID;
- trusted one-time legacy aliases;
- API version and runtime type declaration;
- safe relative entrypoint path;
- required/optional semantic capabilities;
- privileged permission requests;
- normalized factual events / score ordering;
- storage schema version;
- generic package tree safety, footprint, symlink/executable/archive restrictions;
- package digest and platform-owned source/trust registration.

It no longer owns Python AST/import policy, `.py` entrypoint rules or Python dependency-package rules, and it does not reject non-Python runtimes merely because no adapter exists yet.

Identity/origin hardening now includes:

- duplicate canonical IDs fail closed;
- canonical/alias collisions fail closed;
- legacy aliases require built-in origin;
- unconfigured caller-supplied `ActivitySource` is rejected;
- when configured sources overlap, the registry's most-specific authoritative source wins and a caller cannot reclassify a nested external package through a built-in ancestor source.

### 6.2 Python policy lives behind `PythonRuntimeAdapter`

`runtime/child-runtime.toml` separates:

- shared `[validation]` package safety;
- shared `[capabilities]` semantic capability vocabulary;
- shared `[permissions]` privileged-operation vocabulary;
- Python-only policy under `[python]`.

`PythonRuntimePolicy` / `PythonRuntimeAdapter` own:

- `.py` entrypoint requirement;
- AST/syntax validation;
- curated import roots;
- forbidden imports;
- dynamic-import rejection;
- curated-module shadowing rejection;
- Python dependency files/directories/suffixes.

### 6.3 Single Runtime Manager

`src/greia_launcher/runtime_adapter.py` now provides one `RuntimeManager` mapping:

```text
runtime.type -> RuntimeLaunchAdapter
```

It owns:

- adapter lookup;
- runtime-specific package validation;
- semantic device compatibility evaluation;
- launch preparation;
- lifecycle feature declaration passthrough.

Unknown/unavailable runtime fails closed.

It deliberately does **not** own Storage, Session, Progression, Reward, package trust, profile authority, backup or parent controls.

### 6.4 Runtime compatibility uses trusted device truth

Runtime Manager consumes an injected `DeviceCapabilityService` only.

Compatibility records contain:

- device snapshot token;
- available semantic capabilities;
- required capabilities;
- optional capabilities;
- missing required capabilities;
- effective optional capabilities.

Missing required capability blocks launch preparation. Missing optional capability does not.

Forged `GREIA_ACTIVITY_CAPABILITIES` environment text cannot affect this decision.

### 6.5 Shared launcher dependency composition

Added:

```text
src/greia_launcher/composition.py
```

`build_launcher_runtime_services(...)` constructs one HAL-backed `DeviceCapabilityService` and injects that same object into:

- `PermissionBroker`;
- `RuntimeManager`.

The provisional installed HAL beneath this seam remains Legacy-X display/input plus Linux audio/removable/network/systemd-power. R7 may replace backends below the semantic boundary.

### 6.6 Supervisor consumes Runtime Manager

`ActivitySupervisor` no longer maintains its own runtime dispatch table for launch. It calls `RuntimeManager.prepare_launch()`.

Runtime validation/availability/device-compatibility failures normalize to the existing launch-failure lifecycle result.

Installed supervisor construction without an explicitly injected Runtime Manager fails closed. Deterministic static capability fallback exists only for development/test construction.

The supervisor additionally refuses launch if platform-issued `ActivityAuthority` lacks any manifest-required capability.

---

## 7. Focused R6.2 evidence

A reconstructed scratch tree was used only to exercise the changed R6.2 modules. It is **not** the canonical or complete Greia tree.

Latest focused result:

```text
17 / 17 PASS
```

Breakdown:

```text
4  runtime-neutral Activity Registry / package-origin boundary tests
6  Runtime Manager / Python adapter / trusted device-authority tests
7  current ActivitySupervisor / Runtime Manager integration tests
```

The tests cover:

1. duplicate canonical Activity ID rejection;
2. unconfigured source rejection;
3. overlapping source cannot reclassify nested external package as built-in;
4. Python-specific package rule lives behind Python adapter;
5. safe non-Python package facts pass the runtime-neutral Registry but unavailable runtime fails closed;
6. forbidden Python import rejection;
7. dynamic import rejection;
8. required device capability missing blocks launch preparation;
9. optional capability missing does not block launch;
10. Activity environment cannot forge device truth;
11. installed supervisor requires injected Runtime Manager;
12. missing required platform-issued authority blocks process creation;
13. unavailable runtime normalizes to launch failure;
14. Runtime Manager launch preparation integrates with STARTING/READY/RUNNING lifecycle;
15. only one Activity may be active;
16. child environment remains sanitized/descriptive and forged host feature strings do not expand it;
17. missing Bubblewrap on installed path fails closed without child process creation.

Changed modules also passed Python compilation/smoke checks during the tranche.

There is currently no GitHub Actions run attached to the private draft PR.

**Do not reinterpret 17/17 as the complete 219-test gate.**

---

## 8. Persistent GitHub work products

### Branch

```text
r6-runtime-integration-recovery
```

### Draft pull request

```text
#1 R6.2: runtime-neutral Runtime Manager integration and remote recovery
```

Keep PR #1 **draft** until the complete repository is recovered/reconciled and full `make verify` passes.

### R0 issue

```text
#2 R0: restore GitHub as complete reproducible Greia source of truth
```

Issue #2 contains the clean-clone recovery checklist and explicit prohibitions against reconstructing missing authority from prose.

### Detailed R6.2 record

```text
docs/reviews/2026-08-08_R6_2_RUNTIME_INTEGRATION_AND_REMOTE_CONTINUITY.md
```

### Recent implementation/security commits

```text
0c41c994ded0a95512ef5ab2df611b74b344b6d1  test: replace stale blocking-launch supervisor coverage
0a8264871ef0fcd087cec7fd95c8900e89f8d6a9  fix: keep Activity package origin authoritative across overlapping sources
fab599f5dd1ab61cd59fb3aab2fd3435016a77cc  test: prevent overlapping Activity source reclassification
```

Earlier R6.2 commits and their rationale are recorded in the detailed R6.2 review file and PR history. The branch was intentionally committed in small coherent increments throughout the session.

---

## 9. Exact next action

Do **not** start R7.

The next blocking work is repository reconciliation plus final R6 installed composition:

1. recover the latest complete verified Greia tree from a trustworthy workspace/archive;
2. import missing source and the binary asset library into GitHub;
3. reconcile that tree with `r6-runtime-integration-recovery`/PR #1 rather than overwriting either side blindly;
4. locate the real installed launcher composition root;
5. wire `build_launcher_runtime_services(...)` into that real launcher;
6. prove the same HAL-backed `DeviceCapabilityService` instance is used for PermissionBroker authority and Runtime Manager compatibility;
7. run focused R6 tests in the **complete** tree;
8. run `make verify` in the complete tree and require a clean PASS;
9. review R6 against ADRs 0012, 0014 and 0015 plus active-plan R6 closure criteria;
10. append R6 closure to the active plan and update this handover;
11. only then begin R7 direct graphics.

If no complete tree is available, stop at this boundary rather than inventing `history.py`, launcher composition, or other platform authority from documentation.

---

## 10. Security properties to re-prove after reconciliation

```text
external package cannot gain system privilege by copying a system ID
built-in origin alone cannot self-grant another system privilege
caller cannot reclassify package origin through overlapping Activity sources
fabricated manifest/registration cannot mint authority
Activity process cannot forge device capability truth
Activity environment cannot expand sandbox authority
required missing device capability refuses launch
optional missing capability removes only dependent feature/grant
missing Bubblewrap remains fail closed on installed system
Activity A cannot access Activity B durable state
storage/event brokers remain bound to trusted launch identity
reward policy remains platform-owned
runtime adapter type does not fork Storage/Session/Progression
```

---

## 11. Evidence limits

Source tests do not prove:

- real Bubblewrap namespace behavior;
- broker behavior inside installed namespaces;
- direct DRM/KMS;
- Acer memory/input/audio/display behavior;
- Pi 400/500 boot/display/input/audio/network;
- real hardware power/recovery;
- Web engine viability;
- boot-cover continuity;
- installer safety;
- OS update/recovery.

Never promote source-only evidence into physical-hardware claims.

**Do not authorize Acer internal-disk installation until the established hardware/image evidence gates are satisfied and reviewed.**

---

## 12. Final current-state statement

```text
R1–R5 architectural work exists and was previously verified in the complete local tree
R6.1 semantic hardware capability authority was previously verified at 219/219 total tests
R6.2 runtime-neutral Registry / Python adapter / Runtime Manager / supervisor seam is persisted on GitHub
R6.2 focused evidence is 17/17 PASS
R0 repository completeness remains OPEN and tracked by issue #2
R6 remains IN PROGRESS because the real installed launcher/full tree cannot yet be verified
PR #1 remains intentionally draft
R7 must not begin yet
```
