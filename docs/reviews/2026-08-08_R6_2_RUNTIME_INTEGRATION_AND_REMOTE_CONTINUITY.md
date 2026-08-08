# Greia R6.2 — Runtime Integration and Remote Continuity Record

**Date:** 2026-08-08  
**Branch:** `r6-runtime-integration-recovery`  
**Base:** `155a658fa4306297cc6766276a48eb38f7b946d4`  
**Status:** R6.2 source seam substantially implemented and focused-tested; **R6 remains IN PROGRESS** because the GitHub repository is still incomplete and the installed launcher composition call site cannot be verified or patched from the remote tree.

## Why this record exists

The prior handover reported a verified local R6.1 tree with 219/219 provider-free tests passing and warned that R0 remained open because GitHub was not yet a complete independently reproducible mirror.

On resumption, remote `main` was confirmed at the expected R6.1 recovery commit. Inspection then found that remote continuity drift was broader than the missing binary asset library:

- `src/greia_platform/permissions.py` already consumed the permanent R3 manifest contract (`required_capabilities`, `optional_capabilities`, `requested_permissions`, `allowed_permissions`);
- the remote `src/greia_platform/activities.py` and `runtime/child-runtime.toml` still represented the older prototype contract (`runtime.capabilities`, Activity-authored rewards, Python policy embedded in the registry);
- several files known to exist in the previously verified local R4/R5/R6 tree are absent remotely, including the launcher composition file named by the handover and some history/session source;
- repository code search finds no remote launcher construction site for `PermissionBroker.phase0(...)` or `ActivitySupervisor(...)`;
- the surviving remote `tests/test_supervisor.py` was pre-R2 and still tested the removed blocking `.launch()` API, prototype Activity IDs, the old sandbox command signature and interpreter resolution on the supervisor.

Historical Git tree checks also proved that important missing files were never committed rather than merely deleted later: `src/greia_platform/history.py`, `src/greia_launcher/main.py`, and `tests/test_history.py` return 404 even at relevant R5-era commit refs. Individual R5 commits preserved selected policy/protocol/broker fragments, but not the complete verified local tree.

Therefore this session did **not** reconstruct a fake complete tree or claim `make verify` against an incomplete repository. It repaired the specific R3/R6 text seams that can be grounded in accepted ADRs and existing committed consumers, replaced one provably obsolete surviving supervisor test module with current contract tests, committed each coherent tranche, and kept R0/R6 closure blockers explicit.

R0 is now tracked explicitly as GitHub issue **#2 — `R0: restore GitHub as complete reproducible Greia source of truth`**.

## Implemented R6.2 architecture

### 1. Runtime-neutral Activity Registry

`src/greia_platform/activities.py` now owns only shared Activity/package facts:

- permanent reverse-DNS Activity identity;
- trusted one-time legacy aliases;
- manifest shape and API version;
- safe relative entrypoint path;
- runtime type declaration;
- required/optional semantic capabilities;
- privileged permission requests;
- normalized factual events and score ordering;
- storage schema version;
- package tree safety, footprint, symlink/executable/archive restrictions;
- package digest and platform-owned source/origin registration;
- duplicate canonical/alias collision rejection.

It no longer parses Python AST, rejects non-Python runtime types, requires `.py` entrypoints, or owns Python import/dependency policy.

Package-origin authority is platform-owned:

- an explicit caller-supplied `ActivitySource` must be one of the registry's configured sources;
- the package must resolve through the registry's own most-specific authoritative configured source;
- when configured source roots overlap, a caller cannot revalidate a nested external package through a less-specific built-in ancestor source.

### 2. Python-specific policy behind `PythonRuntimeAdapter`

`runtime/child-runtime.toml` now separates:

- shared `[validation]` package-tree rules;
- shared `[capabilities]` semantic device/runtime vocabulary;
- shared `[permissions]` privileged-operation vocabulary;
- Python-only import, dependency-file, dependency-directory, and suffix restrictions under `[python]`.

`PythonRuntimePolicy` loads the Python-specific rules. `PythonRuntimeAdapter.validate_package()` owns:

- `.py` entrypoint enforcement;
- syntax/AST parsing;
- curated import roots;
- forbidden imports;
- dynamic-import rejection;
- curated-module shadowing rejection;
- Python dependency/archive/package-directory restrictions.

### 3. Single Runtime Manager

`src/greia_launcher/runtime_adapter.py` now contains one `RuntimeManager` that maps:

```text
runtime.type -> RuntimeLaunchAdapter
```

The manager owns:

- runtime adapter lookup;
- runtime-specific package validation;
- runtime/device compatibility evaluation;
- runtime launch preparation;
- lifecycle feature declaration passthrough.

Unknown/unavailable runtimes fail closed through `RuntimeUnavailableError`.

The manager deliberately does **not** own Storage, Session, Progression, Reward, package trust, backup, profile authority, or parent controls.

### 4. Trusted device compatibility

`RuntimeManager` consumes an injected `DeviceCapabilityService` and never Activity environment variables.

Compatibility records include:

- trusted device snapshot token;
- available semantic capabilities;
- required capabilities;
- optional capabilities;
- missing required capabilities;
- effective optional capabilities.

Missing required capabilities prevent launch preparation. Missing optional capabilities do not.

### 5. Shared HAL-backed launcher dependencies

Added `src/greia_launcher/composition.py`.

`build_launcher_runtime_services(...)` constructs one HAL-backed `DeviceCapabilityService` and injects that exact service into both:

- `PermissionBroker`;
- `RuntimeManager`.

Current installed HAL construction is explicitly provisional:

```text
LegacyXDisplayHAL
LegacyXInputHAL
LinuxAudioHAL
LinuxRemovableMediaHAL
LinuxNetworkHAL
SystemdPowerHAL
```

R7 may replace the X display/input backend below this semantic boundary without changing Activity/runtime/storage/session/progression contracts.

### 6. Supervisor consumes Runtime Manager

`ActivitySupervisor` no longer performs its own runtime-type map lookup for launch.

It calls `RuntimeManager.prepare_launch()` and normalizes adapter validation, runtime availability, or runtime/device incompatibility failures to the existing launch-failure lifecycle result.

Installed construction without an explicitly injected `RuntimeManager` fails closed. A deterministic static-capability fallback is retained only for developer/test construction.

The supervisor also rejects a launch when the platform-issued `ActivityAuthority` does not contain all manifest-required capabilities.

### 7. Supervisor regression coverage brought forward to the current contract

The remote `tests/test_supervisor.py` was demonstrably stale and contradicted the already-accepted R2 lifecycle architecture. It has been replaced with tests of the current seam rather than preserved as compatibility debt.

The new tests cover:

- installed supervisor requires an explicitly injected Runtime Manager;
- missing required platform-issued capability fails before child process creation;
- unavailable runtime becomes normalized launch failure;
- Runtime Manager prepares a child command and READY drives STARTING → RUNNING;
- only one Activity may be active;
- Activity environment is descriptive and host-injected capability strings cannot expand it;
- missing Bubblewrap on an installed path fails closed without starting the child.

The tests use synthetic profile/authority contracts where appropriate so they exercise supervisor responsibilities rather than re-testing PermissionBroker/ProfileStore internals.

## Focused source evidence

A local reconstructed scratch tree was used only to exercise the exact changed R6.2 modules. It is not claimed as the complete canonical Greia tree.

The combined focused suite passed:

```text
17 / 17 PASS
```

Breakdown:

```text
4  runtime-neutral Activity Registry / package-origin boundary tests
6  Runtime Manager / Python adapter / trusted device authority tests
7  current ActivitySupervisor / Runtime Manager integration tests
```

Coverage includes:

1. duplicate canonical Activity IDs fail closed;
2. an unconfigured source cannot replace registry package origin;
3. overlapping configured sources cannot reclassify a nested external package through a built-in ancestor;
4. a Python-only dependency file is accepted by the runtime-neutral registry but rejected by the Python adapter;
5. a safe non-Python package may pass runtime-neutral registry validation while an unavailable runtime fails closed in Runtime Manager;
6. forbidden Python imports are rejected by the Python adapter;
7. dynamic imports are rejected by the Python adapter;
8. missing required device capability blocks runtime launch preparation;
9. missing optional device capability does not block launch preparation;
10. forged `GREIA_ACTIVITY_CAPABILITIES` environment content cannot create device truth;
11. installed supervisor construction requires an injected Runtime Manager;
12. missing required platform authority blocks process creation;
13. unavailable runtime is normalized to launch failure;
14. Runtime Manager launch preparation integrates with supervisor lifecycle/READY handling;
15. one-active-Activity enforcement remains intact;
16. sanitized child environment remains descriptive and cannot inherit forged host authority;
17. missing installed Bubblewrap remains fail closed.

Additional smoke checks passed for:

- Python compilation of the changed registry/runtime/composition/supervisor modules;
- installed supervisor construction failing without an injected Runtime Manager;
- supervisor refusing launch before process creation when platform-issued authority lacks a required capability.

This does **not** replace the complete-tree historical 219-test gate.

## Important GitHub commits

The branch deliberately uses small commits so recovery does not depend on one long uncommitted session. Important implementation/security commits include:

```text
39d8d0d817e1847e5e2852b2522dfa05d9a34447  restore split capability/permission policy
500b385c75386626e21bad8644d0d5aeb84c677e  bind built-in grants to permanent Activity ID
c1ea1ea22f4f16e1922042fef1ce1da4b988f790  restore runtime-neutral Activity Registry contract
b00c112c66d2d076d1976b6f4fdd20fd58c395ab  add Runtime Manager validation/compatibility seam
fe5e5db86ce27e04be8194fa1a4078cd1504b4a1  test Runtime Manager/device authority
c84db6a106895574715f6c63724c7355d5a673e9  validate Activity runtime policy through Runtime Manager
7088c6484b7db0c48ea5f73db49c36427ba6718b  compose shared HAL-backed launcher services
abe19383197e149debab179599b2674f7ac59bc0  make supervisor consume Runtime Manager
2e3a0b2cee94a56f6dea536d563088b45194a4b1  move Python package restrictions into Python policy
8d06b1710d6489b3b895f51f0ee60e32d94a33e5  enforce Python package policy in adapter
809ac8c7fd0d6012e2fcff51c8cbad24ca6e3bd2  harden Registry identity/source handling
261e5b4d459f26ece6634f99fd142c45f3fd0b5e  pin Registry/runtime boundaries
0c41c994ded0a95512ef5ab2df611b74b344b6d1  replace stale blocking-launch supervisor coverage
0a8264871ef0fcd087cec7fd95c8900e89f8d6a9  keep package origin authoritative across overlapping sources
fab599f5dd1ab61cd59fb3aab2fd3435016a77cc  test overlapping-source reclassification denial
```

Documentation/continuity commits follow in branch history. Read current branch HEAD rather than assuming this list is exhaustive.

## Why R6 is not closed

The R6 closure criteria require the installed production launcher to instantiate the HAL-backed Device Capability Service and inject the shared service into permission and runtime decisions, followed by the complete `make verify` gate.

The remote GitHub tree currently cannot prove those points because:

1. the launcher composition call site named by the handover is absent remotely;
2. repository code search finds no alternative remote construction site using `PermissionBroker.phase0` or `ActivitySupervisor`;
3. several previously verified R4/R5 source files and tests are absent remotely;
4. historical commit-tree checks prove some missing authority files were never committed at all;
5. at least one surviving test module had remained at a pre-R2 API until repaired in this branch;
6. the historical binary asset library remains absent;
7. therefore GitHub HEAD/this branch is not an independently reproducible complete tree and cannot honestly run the prior 219-test project gate.

The new `composition.py` is the intended installed composition building block, but wiring it into an invented replacement launcher would create ungrounded architecture and hide the R0 continuity failure.

## Immediate next action

R0 recovery is tracked in GitHub issue #2.

Before marking R6 source-complete or starting R7:

1. restore/import the missing verified source tree into GitHub using a normal Git-capable environment or another complete-tree transfer path;
2. restore the missing binary asset library through a reliable binary/bulk Git path;
3. reconcile this branch against that complete tree rather than overwriting newer/verified files blindly;
4. wire `build_launcher_runtime_services(...)` into the real installed launcher composition root;
5. use the same `DeviceCapabilityService` instance for permission issuance and Runtime Manager compatibility;
6. run the R6 focused suite against the full tree;
7. run `make verify` and require the complete gate to pass;
8. review R6 against ADRs 0012, 0014, 0015 and the active remediation plan;
9. append the verified R6 closure entry to the active plan and update `HANDOVER.md`;
10. only then begin R7 direct graphics.

## Evidence limits

This work is source evidence only. It does not prove Bubblewrap behavior on installed Linux, direct DRM/KMS, Acer hardware, Pi 400/500 hardware, real device/audio/network state, boot continuity, or image installation behavior.

R0 remains OPEN and R6 remains IN PROGRESS.
