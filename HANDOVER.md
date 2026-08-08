# Greia — Standalone Handover

**Date:** 2026-08-08  
**Version:** `0.13.0-phase0-dev`  
**Repository:** `frozenpepper/Greia` (private)  
**Active implementation branch:** `r6-runtime-integration-recovery`  
**Branch base:** `155a658fa4306297cc6766276a48eb38f7b946d4`  
**Current phase:** R6 — Device Capability / HAL / Runtime integration  
**State:** R6.1 was previously verified in the complete local tree at **219/219** tests. R6.2 runtime-neutral adapter/manager work is now substantially implemented and focused-tested on GitHub, but **R6 remains IN PROGRESS** because the remote repository is still incomplete and the real installed launcher composition call site is absent remotely. R0 remains OPEN.

## 1. Mandatory active plan

The authoritative implementation plan remains:

`docs/plans/2026-08-08_ARCHITECTURE_REMEDIATION_AND_PLATFORM_COMPLETION.md`

The plan audit/correction record is:

`docs/reviews/2026-08-08_ACTIVE_PLAN_AUDIT_AND_CORRECTION.md`

The newest R6.2 implementation/continuity record is:

`docs/reviews/2026-08-08_R6_2_RUNTIME_INTEGRATION_AND_REMOTE_CONTINUITY.md`

Every implementation session must obey `AGENTS.md`: resume the first incomplete blocking phase, use the existing plan instead of inventing a competing one, verify before claiming closure, update continuity documentation, and commit coherent work to GitHub as it proceeds.

## 2. Mandatory architecture read order

Before cross-cutting implementation work, read:

1. `AGENTS.md`
2. `docs/architecture/GREIA_ARCHITECTURE.md`
3. ADR 0012 — platform architecture constitution
4. ADR 0013 — declarative image profiles/composable artifacts
5. ADR 0014 — Greia identity, ARM parity, direct-graphics direction
6. ADR 0015 — Activity identity, capabilities, permissions and events
7. ADR 0016 — universal storage and transactional migrations
8. ADR 0017 — platform-owned sessions/events/progression/reward ledger
9. the active remediation plan
10. `docs/reviews/2026-08-08_R6_2_RUNTIME_INTEGRATION_AND_REMOTE_CONTINUITY.md`
11. this handover

## 3. Non-negotiable architecture

- Greia Shell is the child's OS experience; Linux is substrate.
- No desktop environment, generic WM, shell/login/package manager/filesystem UI/browser chrome in normal child use.
- `Activity` is the universal abstraction above Python/Web/future runtimes.
- Profiles, package trust, effective permissions, durable storage, sessions, progression/rewards, packages, backup/restore and parent policy are Greia-owned services.
- Runtime adapters may own runtime-specific static validation, launch preparation and lifecycle capability declarations; they must **not** fork platform services.
- Device capability, permission request and effective permission grant are separate concepts.
- Device truth comes from the platform Device Capability Service/HAL, never Activity environment variables or manifest claims.
- ARM and legacy x86 are peers. Pi 400/500 are explicit ARM references; the old Acer/Atom remains the extreme low-resource reference.
- Xorg is provisional migration/evidence only; target graphics are DRM/KMS-first and appliance-oriented.
- Durable child state is architecture-neutral.
- Removable media is untrusted and never autorun.
- Global reward economics belong to Greia; Activities report factual normalized events.
- The earlier chat-only generic `Resource Service` idea is rejected. Do not reintroduce it.

## 4. R0 — canonical GitHub completeness

**Status: OPEN and now confirmed broader than the original asset warning.**

GitHub is the intended persistent source of truth, but remote `main` is still not a complete independently buildable mirror of the previously verified local tree.

Originally known gap:

- the verified local tree contained 123 PNG assets;
- remote spot checks such as `assets/icons/core/v1/128/unicorn.png` returned 404.

Additional continuity drift found while resuming R6.2:

- remote `permissions.py` already expected the permanent R3 manifest contract while remote `activities.py` and `runtime/child-runtime.toml` still contained the older prototype schema;
- several R4/R5/R6 files known from the verified local tree are absent remotely;
- the installed launcher composition file named in the prior handover is absent remotely;
- repository code search finds no alternative remote construction site for `PermissionBroker.phase0(...)` or `ActivitySupervisor(...)`.

The R6.2 branch repairs the touched text/schema seams that can be grounded in ADRs and committed consumers, but it does **not** pretend to reconstruct the missing full tree.

Do not claim R0 complete until a clean GitHub clone contains all required source/assets and can independently run `make verify`.

## 5. Earlier phase status

```text
R1   package trust / PermissionBroker / per-Activity authority     FUNCTIONALLY COMPLETE in verified local history
R2   runtime-neutral lifecycle / READY / watchdog                  SOURCE COMPLETE in verified local history
R3   permanent Activity identity / manifest semantics              SOURCE COMPLETE in verified local history
R4   Universal Storage Service                                     SOURCE COMPLETE in verified local history
R5   sessions / events / progression / reward ledger               SOURCE COMPLETE in verified local history
R6   Device Capability / HAL / Runtime Manager integration         IN PROGRESS
R7+  not started under this remediation program
```

Historical local verification milestones:

```text
R2  159/159
R3  169/169
R5  213/213
R6.1 recovered full tree 219/219
```

Those are historical verified-local milestones, **not** claims that the current incomplete GitHub clone can reproduce them yet.

## 6. R1 security properties that must remain true

- package origin/trust is platform-owned;
- effective authority is issued from registry/package provenance plus platform policy;
- external code cannot become a system Activity by copying a built-in ID;
- built-in origin alone cannot self-grant another built-in's privileged operation;
- Activity environment strings cannot expand authority;
- installed Activities receive only narrow per-Activity/platform broker channels, not writable sibling/profile/platform state;
- missing Bubblewrap on an installed system remains fail closed;
- durable sibling Activity state remains inaccessible.

## 7. R2 lifecycle properties that must remain true

The supervisor owns one Activity process from launch through cleanup with:

- nonblocking process creation;
- STARTING/RUNNING/STOPPING/terminal states;
- READY handshake and timeout;
- graceful stop and deadline;
- forced process-group termination;
- system-shutdown termination;
- normalized exit reason/timestamps;
- cleanup and shell recovery;
- optional pause/checkpoint declarations rather than assumed support.

Do not regress to blocking launch or runtime-specific lifecycle copies.

## 8. R3 manifest model now restored on the R6.2 branch

Canonical built-ins:

```text
org.greia.shape-garden
org.greia.workshop-settings
```

Trusted one-time migration aliases:

```text
shape_garden
workshop_settings
```

The branch now restores/uses the permanent contract:

- reverse-DNS canonical identity;
- built-in-only legacy alias migration authority;
- canonical/alias collision rejection;
- required and optional semantic capabilities;
- privileged permission requests as a separate namespace;
- storage schema version;
- factual Activity events (`completion`, `creation`, `milestone`, `score`);
- score ordering (`higher_better` / `lower_better`);
- Activity-authored global reward amounts forbidden.

The registry additionally rejects duplicate canonical IDs and refuses an unconfigured caller-supplied `ActivitySource`, preventing package-origin classification from being replaced through the public validation method.

## 9. R4/R5 boundaries remain runtime-neutral

R6.2 must not absorb or fork these services.

R4 durable state remains Greia-owned logical storage keyed by profile + Activity, brokered into the runtime rather than mounted as a general durable HOME.

R5 sessions/events/progression/rewards remain platform-owned. Activities report only declared factual events; Greia policy owns best-score/progression/reward calculation and the bounded reward ledger.

Future Web must bridge to the same logical storage/event services rather than using browser-local state as authoritative Greia state.

## 10. R6.1 — Device Capability / HAL tranche

Previously recovered and verified in the complete local tree:

- typed HAL protocols/states for display, input, audio, removable media, network and power;
- provisional legacy-X display/input adapters;
- Linux audio/removable-media/network/systemd-power adapters;
- immutable `DeviceCapabilitySnapshot` with semantic capability IDs, source/provenance, portable details and deterministic token;
- deep-frozen snapshot details;
- `DeviceCapabilityService` caching/explicit refresh;
- `HALDeviceCapabilityProbe` semantic mapping;
- PermissionBroker consuming an injected Device Capability Service;
- required missing capability blocking authority;
- optional missing capability removing dependent grants;
- deterministic static service only as test/development fallback.

## 11. R6.2 — work now persisted on GitHub

Branch:

```text
r6-runtime-integration-recovery
```

Detailed record:

```text
docs/reviews/2026-08-08_R6_2_RUNTIME_INTEGRATION_AND_REMOTE_CONTINUITY.md
```

### 11.1 Runtime-neutral Activity Registry

`src/greia_platform/activities.py` now owns only shared package/manifest facts and safety rules. It no longer:

- rejects non-Python runtime types;
- requires `.py` entrypoints;
- parses Python AST;
- validates Python import roots;
- owns Python dependency-file/package-directory rules.

### 11.2 PythonRuntimeAdapter owns Python policy

`PythonRuntimePolicy` / `PythonRuntimeAdapter` now own:

- `.py` entrypoint requirement;
- syntax/AST validation;
- curated allowed/forbidden imports;
- dynamic-import rejection;
- curated-module shadowing rejection;
- Python dependency file/directory/suffix restrictions.

`runtime/child-runtime.toml` separates shared package validation, semantic capabilities, privileged permissions and Python-only policy.

### 11.3 Runtime Manager

A single `RuntimeManager` now maps:

```text
runtime.type -> RuntimeLaunchAdapter
```

It owns:

- adapter lookup;
- runtime-specific package validation;
- semantic device compatibility evaluation;
- launch preparation;
- lifecycle-feature declaration passthrough.

Unknown/unavailable runtimes fail closed.

It does not own Storage, Session, Progression, Reward, package trust, backup, profile authority or parent policy.

### 11.4 Device compatibility

Runtime compatibility consumes the injected `DeviceCapabilityService` only. It records the trusted snapshot token and computes:

- available capabilities;
- required capabilities;
- optional capabilities;
- missing required capabilities;
- effective optional capabilities.

Required missing capability blocks launch preparation. Optional missing capability does not.

Forged `GREIA_ACTIVITY_CAPABILITIES` environment content cannot change this result.

### 11.5 Shared launcher dependency composition

Added:

```text
src/greia_launcher/composition.py
```

`build_launcher_runtime_services(...)` constructs one HAL-backed `DeviceCapabilityService` and injects that same service into:

- `PermissionBroker`;
- `RuntimeManager`.

Current provisional installed HAL composition remains Legacy-X display/input plus Linux audio/removable/network/systemd-power. R7 replaces backend implementations below this semantic seam.

### 11.6 Supervisor integration

`ActivitySupervisor` consumes `RuntimeManager.prepare_launch()` rather than maintaining its own runtime dispatch table.

Installed supervisor construction without an explicitly injected Runtime Manager fails closed. The old mapping/static capability path survives only as a development/test compatibility bridge.

Adapter validation, unavailable runtime and incompatible device failures normalize to the existing launch-failure lifecycle result.

The supervisor also refuses launch if the platform-issued `ActivityAuthority` lacks a manifest-required capability.

## 12. R6.2 focused evidence

A reconstructed local scratch tree was used only to exercise the exact changed R6.2 modules. It is **not** a substitute for the missing complete Greia tree.

Focused suite:

```text
9 / 9 PASS
```

Covered:

1. duplicate canonical Activity ID rejection;
2. unconfigured Activity source rejection;
3. Python package-specific rule lives behind Python adapter;
4. runtime-neutral registry accepts safe non-Python package facts while unavailable runtime fails closed;
5. forbidden Python import rejection;
6. dynamic Python import rejection;
7. required device capability blocks launch preparation when absent;
8. optional capability may be absent without blocking launch;
9. Activity environment cannot forge device truth.

Additional smoke evidence:

- changed registry/runtime/composition/supervisor modules compile;
- installed supervisor without injected Runtime Manager fails closed;
- missing required platform-issued authority prevents child process creation.

There is no GitHub CI status attached to this private branch at present.

## 13. Important R6.2 commits

```text
39d8d0d817e1847e5e2852b2522dfa05d9a34447  restore capability/permission vocabulary split
500b385c75386626e21bad8644d0d5aeb84c677e  bind built-in grants to permanent ID
c1ea1ea22f4f16e1922042fef1ce1da4b988f790  restore runtime-neutral registry contract
b00c112c66d2d076d1976b6f4fdd20fd58c395ab  add Runtime Manager validation/compatibility seam
fe5e5db86ce27e04be8194fa1a4078cd1504b4a1  Runtime Manager/device-authority tests
c84db6a106895574715f6c63724c7355d5a673e9  route project runtime validation through Runtime Manager
7088c6484b7db0c48ea5f73db49c36427ba6718b  add shared HAL-backed launcher service composition
abe19383197e149debab179599b2674f7ac59bc0  supervisor consumes Runtime Manager
2e3a0b2cee94a56f6dea536d563088b45194a4b1  move Python package restrictions into Python policy
8d06b1710d6489b3b895f51f0ee60e32d94a33e5  enforce Python package policy in adapter
5ea4b37ae7c55acd8ea46f1d55f9badf08b4c3e0  keep generic validation catalogue loadable
809ac8c7fd0d6012e2fcff51c8cbad24ca6e3bd2  harden registry identity/source handling
261e5b4d459f26ece6634f99fd142c45f3fd0b5e  pin registry/runtime boundaries with tests
d22a1dd14cf8cc7c91c9367ec0f3388b41cb59b6  record R6.2 runtime/continuity state
```

## 14. Why R6 is still open

Do **not** start R7 yet.

R6 closure still requires:

1. restore/import the complete previously verified source/assets into GitHub;
2. reconcile this R6.2 branch against that complete tree rather than overwriting verified files blindly;
3. locate the real installed launcher composition root;
4. wire `build_launcher_runtime_services(...)` into that real launcher;
5. use the same Device Capability Service instance for permission issuance and Runtime Manager compatibility;
6. run the R6 focused tests in the complete tree;
7. run full `make verify` successfully;
8. review R6 against ADRs 0012, 0014, 0015 and active-plan closure criteria;
9. append verified closure to the active plan and update this handover;
10. only then begin R7.

The absence of the launcher call site is a repository continuity blocker, not permission to invent a replacement launcher architecture.

## 15. Verification truth

Last complete-tree verification before this resumed session:

```text
219 / 219 provider-free tests PASS
project/runtime/Activity/asset/build validation PASS
source footprint approximately 16 MiB
```

Current R6.2 branch evidence:

```text
9 / 9 focused R6.2 tests PASS in reconstructed scratch tree
Python compilation/smoke checks PASS
full make verify NOT CLAIMED because the remote tree is incomplete
```

Never reinterpret the 9 focused tests as a replacement for the historical 219-test gate.

## 16. Later blocking spine

After R6 source closure:

```text
R7   direct DRM/KMS-first graphics/session architecture
R8   Raspberry Pi 400/500 ARM64 image adapters/evidence
R9   embedded Web runtime benchmark/selection/adapter
R10  .greiaactivity package/install/update
R11  .greiabackup portable backup/restore
R12  parent-management integration
R13  branded boot/recovery graphical continuity
R13B signed rollback-safe OS/runtime updates + preserve-profile recovery
R14  final multi-architecture certification
```

## 17. Evidence discipline

Source tests do not prove:

- Linux Bubblewrap namespace behavior;
- broker behavior in installed namespaces;
- direct DRM/KMS;
- Acer behavior/resource limits;
- Pi 400/500 boot/display/input/audio/network;
- real hardware power/recovery;
- Web engine viability;
- boot-cover continuity;
- installer safety;
- OS update/recovery.

**Do not authorize Acer internal-disk installation until the established hardware/image evidence gates are satisfied and reviewed.**
