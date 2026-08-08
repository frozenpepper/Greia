# Greia — Standalone Handover

**Date:** 2026-08-08  
**Version:** `0.13.0-phase0-dev`  
**State:** active architecture-remediation plan audited; R0 canonical-repository completeness remains open; R1 trusted package-origin/PermissionBroker authority implemented in the verified local tree and substantially mirrored to GitHub; full local verification **147/147**; R2+ not implemented.

## 1. Mandatory active plan

The authoritative implementation plan is:

`docs/plans/2026-08-08_ARCHITECTURE_REMEDIATION_AND_PLATFORM_COMPLETION.md`

The plan audit/correction record is:

`docs/reviews/2026-08-08_ACTIVE_PLAN_AUDIT_AND_CORRECTION.md`

`AGENTS.md` requires every implementation session to read the active plan, resume the first incomplete blocking phase, append progress after substantive work, update this handover, verify before claiming completion, and remove the active-plan reference only after the complete plan is closed.

## 2. Current architecture invariants

- Greia is the child's graphical operating environment; Linux is substrate.
- No conventional desktop, WM, shell, login prompt, package manager, filesystem UI or browser chrome belongs in normal child operation.
- Activity is the universal abstraction above Python/Web/future runtimes.
- Profiles, permissions, storage, sessions, progression/rewards, package/update, backup/restore and parent policy are platform-owned services.
- ARM and legacy x86 are peers. Pi 400 and Pi 500 are explicit ARM references; old Acer/Atom remains the extreme low-resource reference.
- Xorg is a provisional migration/evidence implementation only. Target graphics remain direct DRM/KMS-first appliance graphics.
- Child state is architecture-neutral and portable.
- Removable media is untrusted and never autorun.
- Global reward economics belong to Greia, not Activity packages.
- The previously suggested generic `Resource Service` was an assistant hallucination and is explicitly rejected by the audited plan.

## 3. R0 — canonical repository status

**Status: OPEN / partially blocked by connector transfer mechanics.**

The GitHub repository is the long-term canonical location, but it is not yet a complete reproducible mirror of the current verified working tree.

Confirmed gaps include the binary asset library. The working tree contains 123 PNG assets; GitHub previously returned 404 for a canonical icon path such as `assets/icons/core/v1/128/unicorn.png`.

During the current session the GitHub Git-object path was tested successfully: binary `create_blob` and `create_tree` work. However, the connector accepts binary content only as base64 string payloads and does not expose a mounted-file/bulk upload primitive. Importing the existing multi-megabyte PNG collection this way is not considered reliable enough for R0 closure.

Temporary R0 probe marker files created during that experiment were removed from repository HEAD.

Text/source mirroring is continuing as files are touched. Do **not** claim R0 complete or the remote tree independently buildable until required source plus binary assets are actually present or an explicit repository-managed external asset mechanism is accepted.

## 4. R1 — trusted Activity authority

**Status: IN PROGRESS, major authority tranche implemented.**

### 4.1 Per-Activity filesystem authority retained

The first R1 tranche replaced the writable whole-active-profile sandbox with per-Activity writable state:

- only `(profile_id, activity_id)` data is writable for ordinary Activities;
- profile/platform roots remain hidden;
- customization is a narrow privileged bind only when effectively granted;
- removable media is hidden unless effectively granted;
- avatar/profile requests live inside the requesting Activity's private namespace;
- Activity-process capability environment values are SDK hints only and cannot expand the namespace policy.

### 4.2 Package origin/trust is now platform-owned

Added `greia_platform.trust` with `PackageTrust` states and `ActivitySource`.

Package origin is configuration supplied by Greia itself, never by `activity.toml`. A package therefore cannot become a built-in system Activity by copying an Activity ID or title.

### 4.3 Registry-issued package identity

`ActivityRegistry` now produces immutable `ActivityRegistration` records containing the validated manifest, package SHA-256 digest, platform-owned package trust and source identity.

`registration_for()` accepts only the exact manifest object issued by the current registry discovery pass. A fabricated/replaced manifest is not accepted as trusted registration state.

Plain `Path` roots default to developer/unsigned trust. The verified local launcher explicitly marks only its shipped system catalogue root as built-in.

### 4.4 PermissionBroker / effective grants

Added `greia_platform.permissions.PermissionBroker` and `ActivityAuthority`.

The broker distinguishes requested capabilities, requested privileged permissions, effective capabilities and granted permissions.

Effective grants currently intersect package trust/origin, manifest request, runtime capability availability, provisional Phase-0 hardware/build capability availability, build permission policy, parent permission policy and platform security policy.

`runtime/permission-policy.toml` defines the Phase-0 system grant policy.

System privilege now requires **both** package source trust = `BUILT_IN` and an explicit built-in identity grant in platform policy. Thus an external package named `workshop_settings` gets no system permissions, while a different built-in Activity also cannot simply request a system permission and receive it.

Future signed/publisher/parent-trusted states remain deny-by-default until the package trust/signature phase deliberately specifies policy.

### 4.5 Supervisor uses effective authority

The supervisor no longer derives mounts/devices from the manifest. It receives a platform-issued `ActivityAuthority`.

- audio device exposure uses effective capability;
- customization bind uses granted permission;
- removable-media visibility uses granted permission;
- avatar request channel uses granted permission;
- SDK environment mirrors `authority.sdk_features` only;
- package trust is exposed descriptively as `GREIA_PACKAGE_TRUST`.

### 4.6 Launcher integration in verified local tree

The verified local launcher creates the system `ActivitySource` as `BUILT_IN`, loads `runtime/permission-policy.toml`, retrieves the registry-issued `ActivityRegistration`, asks `PermissionBroker` for effective grants, passes that authority to `ActivitySupervisor`, and consumes an own-profile avatar request only when `profile.manage_own` is **granted**, not merely requested in the manifest.

This launcher file is still part of the R0 remote-mirroring gap and must not be inferred from chat if remote source is absent.

## 5. Current verification

Fresh local verification after the final origin+identity PermissionBroker policy:

```text
make verify
```

passes:

- **147 / 147 provider-free unit tests**;
- project/runtime/Activity/asset validation;
- bundled Activity validation;
- existing build/system-overlay source gates;
- source footprint approximately 15 MiB.

New R1 negative tests prove:

- external/developer package copying the real system Activity ID gets zero privileged grants;
- built-in origin alone is insufficient for a non-system Activity to self-request system permission;
- fabricated manifest objects are not accepted as registry-issued registrations;
- parent policy can remove an otherwise valid built-in grant;
- unavailable required capability prevents a permission grant;
- forged Activity-process environment capability values cannot expand sandbox authority;
- missing Bubblewrap remains fail closed.

This is **source evidence only**. Linux Bubblewrap runtime behavior remains unproven until controlled Linux/VM evidence.

## 6. Important R1 design constraints going forward

- Current manifest `runtime.capabilities` remains semantically overloaded as request vocabulary. R3 owns the formal schema split between hardware/runtime capability requirements and privileged permission requests.
- R1 must nevertheless never treat those requests as authority; only `PermissionBroker` effective grants drive privileged effects.
- Phase-0 hardware capability inputs are static/provisional and must not be mistaken for physical capability evidence. R6 replaces them with the Device Capability Service/HAL.
- Future R10 package installation must never place external packages into a source root classified as built-in. Package activation must preserve explicit origin/trust metadata.
- Future signed package states do not automatically imply system permission. Trust policy must be explicit.

## 7. R1 remaining work

Before R1 is marked source-complete:

1. mirror the verified local launcher/profile integration as canonical GitHub source rather than leaving it only in the local working tree/continuity material;
2. audit every current privileged Activity effect and prove it uses effective grants or an equivalent trusted boundary;
3. remove any obsolete continuity patch once the corresponding canonical source is remote;
4. rerun `make verify`;
5. append the R1 closure entry to the active plan.

Linux Bubblewrap execution evidence may remain UNPROVEN until the controlled evidence phase if that distinction is explicit.

## 8. Next implementation phase after R1 source closure

**R2 — runtime-neutral non-blocking Activity lifecycle.**

R2 must replace the current blocking `subprocess.run()` model with the minimal shared session/adapter seam needed for STARTING/READY/RUNNING/STOPPING/terminal states, bounded READY handshake, responsive Greia Shell, graceful stop deadline, forced process-tree termination, normalized exit reasons, guaranteed return to shell after crash/freeze, and future Python/Web parity without implementing lifecycle twice.

Do not start Web/package expansion ahead of this lifecycle boundary.

## 9. Later audited plan spine

```text
R0 canonical repository/governance
 ↓
R1 PermissionBroker/trust/per-Activity authority
 ↓
R2 runtime-neutral lifecycle/session seam
 ↓
R3 stable IDs + capability/permission/event manifest semantics
 ↓
R4 universal storage
 ↓
R5 sessions/events/progression
 ↓
R6 Device Capability/HAL + full runtime integration
```

Then, where dependencies allow: R7 direct graphics → R8 Pi 400/500 image + ARM evidence; R9 Web runtime; R10 `.greiaactivity`; R11 `.greiabackup`; R12 parent integration; R13 boot/recovery continuity; R13B signed rollback-safe Greia OS/runtime updates and preserve-profile recovery; R14 final certification.

## 10. Current remote R1 commits

Important current commits include:

- `f5c0f8a815046ccebb6424e42d03e3f2d3ed39b3` — package trust/origin types;
- `e0213657858d57a4477ac475ad672a15f56ce6c6` — PermissionBroker/effective grants;
- `4a44d0c8dce7f41857939d4c43f9389872ba528e` — Phase-0 permission policy;
- `6cdcbfe98f6d762bf53ff876d8a8f747ed104fc6` — runtime privilege allowlist removal;
- `07edbf2865a57ac426ffc240dddcd0fd34f71448` — corrected Activity registration/provenance source;
- `7fff3aa5d772c224418f84bf1a04a773070db7ee` — supervisor uses issued authority;
- `5c4293ad80041b2223960357e4d6efc5c9a53010` — PermissionBroker negative tests;
- `6f1b3f08ff8bfe8c7eda561d45cf33525eabf0ec` — sandbox tests driven by effective grants.

## 11. Evidence discipline

Do not infer Linux image, Bubblewrap runtime, DRM/KMS, Acer, Raspberry Pi, Web-engine, memory/footprint, boot-continuity or update/recovery acceptance from source tests alone.

**Do not authorize Acer internal-disk installation before the established hardware/image evidence gates are satisfied and reviewed.**
