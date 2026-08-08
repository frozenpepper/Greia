# Greia — Standalone Handover

**Date:** 2026-08-08  
**Version:** `0.13.0-phase0-dev`  
**State:** audited remediation plan ACTIVE; R2/R3/R4/R5 source-complete locally; R6.1 Device Capability/HAL authority tranche recovered and verified; R0 canonical GitHub completeness remains open because binary assets and some historical source are absent remotely; final local verification **219/219** passing; R6 remains the current functional phase.

## 1. Mandatory active plan

The authoritative implementation plan is:

`docs/plans/2026-08-08_ARCHITECTURE_REMEDIATION_AND_PLATFORM_COMPLETION.md`

The plan audit/correction record is:

`docs/reviews/2026-08-08_ACTIVE_PLAN_AUDIT_AND_CORRECTION.md`

Every implementation session must obey `AGENTS.md`: read the active plan, resume the first incomplete blocking phase, append progress after substantive work, update this handover, verify before claiming closure, and remove the active-plan reference only after the whole program is complete.

## 2. Architectural authority

Read in this order before cross-cutting changes:

1. `AGENTS.md`
2. `docs/architecture/GREIA_ARCHITECTURE.md`
3. ADR 0012 — platform architecture constitution
4. ADR 0013 — declarative image profiles/composable artifacts
5. ADR 0014 — Greia identity, ARM parity, direct-graphics direction
6. ADR 0015 — permanent Activity identity, capability requirements, permissions, events
7. ADR 0016 — universal storage, ephemeral runtime state, transactional save migrations
8. active remediation plan
9. this handover

## 3. Non-negotiable current architecture

- Greia Shell is the child's OS experience; Linux is substrate.
- No desktop environment, generic WM, shell/login/package manager/filesystem UI/browser chrome in normal child use.
- Activity is the universal abstraction above Python/Web/future runtimes.
- Profiles, effective permissions, durable storage, sessions, progression/rewards, packages, backup/restore and parent policy are Greia-owned services.
- ARM and legacy x86 are peers. Raspberry Pi 400/500 are explicit ARM references; the old Acer/Atom remains the extreme C0 reference.
- Xorg is provisional migration/evidence only; target graphics are DRM/KMS-first and appliance-oriented.
- Activity process environment values are descriptive, never security authority.
- Durable child state is architecture-neutral.
- Removable media is untrusted and never autorun.
- Global reward economics belong to Greia; Activities report facts/events.
- The earlier chat-only generic `Resource Service` idea was hallucinated and is rejected. Do not reintroduce it.

## 4. R0 — canonical GitHub completeness

**Status: OPEN.**

The private repository `frozenpepper/Greia` is the intended long-term canonical repository but is still not a complete independently buildable mirror of the verified local tree.

Known gap: the local tree contains 123 PNG assets and remote spot-checks such as `assets/icons/core/v1/128/unicorn.png` returned 404. The GitHub connector supports binary Git blobs but only through base64 string payloads and exposes no mounted-file/bulk upload primitive, so multi-megabyte asset import remains an operational blocker. Temporary probe files have been removed.

Continue mirroring touched text/source files, but do not claim R0 closed until all required source/assets are actually remote or an explicitly accepted repository-managed asset mechanism replaces them.

## 5. R1 — package trust, PermissionBroker, per-Activity authority

The security model now uses platform-owned package origin/trust and registry-issued Activity registrations. `PermissionBroker` computes effective grants from package trust/origin, validated manifest requests, runtime/build/parent/security policy and provisional capability availability.

System privilege requires both trusted built-in origin and explicit built-in identity policy. External packages cannot gain privilege by copying a system Activity ID. Built-in origin alone is insufficient for another Activity to self-request system permission.

The sandbox no longer exposes the whole active profile writable. Effective grants control narrow customization/media/profile-request access; sibling profile/Activity/platform state remains hidden. Activity-controlled capability environment strings cannot expand authority.

Linux Bubblewrap execution remains runtime evidence for R14.

## 6. R2 — runtime-neutral Activity lifecycle — SOURCE COMPLETE locally

Implemented:

- nonblocking `Popen` session ownership;
- one active Activity per child session for Phase 0;
- per-launch UUID control channel;
- STARTING/RUNNING/STOPPING/terminal state;
- READY handshake and timeout;
- graceful-stop request/deadline;
- forced process-group termination;
- system-shutdown termination;
- normalized exit reasons/timestamps;
- cleanup and shell recovery contract;
- minimal `RuntimeLaunchAdapter` + `PythonRuntimeAdapter`;
- pause/checkpoint explicitly optional; Phase-0 Python claims neither;
- child SDK `mark_activity_ready()` / `activity_stop_requested()`.

The fast READY-then-exit race is covered and fixed.

R2 full verification milestone was **159/159** before later phases added tests.

## 7. R3 — permanent IDs and manifest semantics — SOURCE COMPLETE locally

ADR 0015 accepted.

Canonical first-party IDs:

- `org.greia.shape-garden` (trusted one-time legacy alias `shape_garden`)
- `org.greia.workshop-settings` (trusted one-time legacy alias `workshop_settings`)

Rules:

- canonical Activity IDs are reverse-DNS durable identity;
- legacy aliases are migration authority and accepted only from trusted built-in provenance in Phase 0;
- canonical/legacy collisions fail closed;
- profile migration is no-merge and idempotent after success;
- manifest capability requirements and privileged permission requests are separate;
- missing required capability blocks launch authority;
- missing optional capability allows launch but blocks dependent permission;
- `education.rewards` is forbidden;
- Activities declare factual events (`completion`, `creation`, `milestone`, `score`); score events declare higher/lower-is-better semantics;
- Greia R5 owns event→progression/reward mapping.

R3 full verification milestone was **169/169**.

## 8. R4 — Universal Storage Service — SOURCE COMPLETE locally

ADR 0016 accepted.

### 8.1 Durable vs ephemeral state

Authoritative durable Activity state lives in Greia-managed:

`profile/storage/<activity_id>/`

It is **not mounted into the Activity sandbox**.

Activity HOME/XDG/lifecycle scratch is a Greia-owned ephemeral per-session runtime workspace (installed target: under `/run/greia-os/activity-runtime/<session_id>`). It is removed on exit. Direct Python file writes there are therefore not an alternative persistent save system.

The legacy/profile `activities/<activity_id>` namespace remains only for narrow compatibility/system-request state and is not general HOME.

### 8.2 Storage API

`ActivityStorage`/`ActivityStorageService` provide:

- portable JSON key/value state;
- private binary files with conservative portable relative paths;
- atomic writes;
- quota and file-count/size/path limits;
- protected machine free-space reserve;
- platform metadata and checkpoint tokens;
- strict revalidation of existing namespaces;
- storage schema comparison;
- transactional migrations.

Current Phase-0 policy (`runtime/storage-policy.toml`):

- 32 MiB namespace quota;
- 2 MiB KV total;
- 256 KiB per KV value;
- 16 MiB per private file;
- 512 private files;
- 64 MiB protected machine free-space reserve;
- 2 rollback snapshots.

These are platform defaults, not Activity-owned authority and not constitutional constants.

### 8.3 Runtime-neutral broker

Activities access storage through a per-session Greia broker:

- Unix-domain socket;
- random session token;
- broker already bound to one trusted `ActivityStorage`, so the Activity cannot select profile/Activity identity in requests;
- physical storage path never exposed;
- bounded frame/header/payload protocol;
- at most 2 active requests and backlog 2;
- stalled request timeout 2 seconds;
- host/internal error paths sanitized;
- broker directory/socket removed at cleanup.

Python uses `ActivityStorageClient` via `get_storage()`. Future Web must bridge to these same logical semantics rather than own authoritative localStorage/IndexedDB state.

### 8.4 Migration

Manifest requires:

```toml
[storage]
schema_version = 1
```

Opening older schema raises `StorageMigrationRequired`; newer stored schema fails closed.

Migration copies old storage to a Greia working namespace while old data remains active. Only after target schema/quota validation does commit rename old active state to a bounded rollback snapshot and atomically promote the working copy. Failed/uncommitted migrations remove the working copy and preserve old active state. R10 Package Manager owns when Activity version migrations run/activate.

Prototype Activity-ID migration moves both compatibility and durable storage namespaces and refuses collisions.

### 8.5 R4 hardening found during review

Before closure, additional hardening was added:

- private-file reads take the storage lock;
- final-component symlinks are rejected on read;
- storage lock symlinks are rejected and `O_NOFOLLOW` is used where available;
- existing storage is revalidated against current file-size/count/quota policy on open;
- malformed metadata types fail rather than coerce;
- normalized Unicode object-key collisions fail;
- broker threading/backlog/timeouts are bounded for low-memory hardware;
- oversized KV payloads are rejected before JSON decode.

## 9. R5 — Session/Event/Progression — SOURCE COMPLETE locally

R5 is source-complete locally under ADR 0017. Greia now creates authoritative sessions before child launch, persists READY/terminal/restart outcomes, accepts only manifest-declared normalized events through a live-session-bound broker, provides transactional idempotency, owns best-score calculation and progression/reward economics, maintains a bounded auditable reward ledger, exposes bounded parent-readable summaries, and provides logical R11 backup export. Activity cooperation is optional for session existence; forged reward/profile/session fields have no authority.

R5 closure milestone was **213/213** tests plus project/runtime/Activity/asset/build validation and approximately 16 MiB source footprint. Child progress remains local product state, not analytics, and R5 introduces no default upload path. Linux/Bubblewrap broker behavior remains evidence-pending.

## 10. R6 — Device Capability Service / HAL — IN PROGRESS

Recovered after the interrupted session and verified as a coherent first tranche:

- typed HAL protocols/states for display, input, audio, removable media, network and power;
- provisional legacy-X display/input adapters wrap the existing X session controller without making X11 a permanent Greia contract;
- Linux audio/removable-media/network/systemd-power probes;
- immutable `DeviceCapabilitySnapshot` with portable semantic capability IDs, provenance/source ID, machine metadata, details and deterministic state token;
- `DeviceCapabilityService` owns snapshot caching/refresh;
- `HALDeviceCapabilityProbe` maps board/backend observations into Greia semantic capabilities;
- `PermissionBroker` now consumes an injected trusted `DeviceCapabilityService` for launch/grant decisions instead of treating Phase-0 static hardware assumptions as the live authority;
- a deterministic static capability service remains only as an explicit source-test/developer fallback;
- missing required device capability fails launch authority, while missing optional capability removes the dependent permission grant;
- X-session controller now exposes bounded pointer-presence probing for the provisional HAL adapter.

The snapshot details are deep-frozen after validation so the token and visible observation cannot diverge through later mutation.

R6 is **not complete**. R6.2 still needs runtime-specific package/static validation, compatibility/resource selection and full Runtime Manager integration, and the installed launcher composition root must inject the real HAL-backed capability service rather than relying on the deterministic static fallback. R7/R8 later replace provisional X/board backends without changing this semantic capability contract.

## 11. Current verification

Final recovered-tree verification after R6.1 recovery:

```text
make verify
```

passes:

- **219 / 219 provider-free unit tests**;
- project/runtime/Activity/asset validation;
- canonical Activity validation;
- build/system-overlay source contracts;
- source footprint approximately **16 MiB**.

Current Activity digests:

- `org.greia.shape-garden`: `dd53995e845564fc1bf735de76c1f4753d8de9e829cc86e78ba562265f21ca99`
- `org.greia.workshop-settings`: `a2d60444a3e95f2f00d5f0a1410819955e108bfbcc22315cf20d4ff4bfbcfeae`

This remains **source evidence**. Linux Unix-socket/Bubblewrap/Acer/Pi/runtime behavior remains UNPROVEN until controlled evidence phases.

## 12. Immediate next work inside R6

Continue R6.2 in this order:

1. move runtime-specific package/static validation behind the Runtime Adapter/Manager rather than leaving Python validation as a universal registry concern;
2. add runtime compatibility/resource selection using the trusted semantic device capability snapshot;
3. inject the HAL-backed `DeviceCapabilityService` at the installed launcher composition root;
4. keep Storage/Session/Progression/PermissionBroker runtime-neutral;
5. add negative tests proving runtime or Activity code cannot forge device capability truth;
6. preserve X11 only as a provisional backend until R7 direct graphics is evidence-ready.

Do not jump to Web, Pi image, or direct graphics implementation around this shared capability/HAL/runtime boundary.

## 13. Later blocking spine

After R6:

- R7 direct DRM/KMS-first graphics;
- R8 Pi 400/500 ARM64 image adapters/evidence;
- R9 embedded Web runtime;
- R10 `.greiaactivity`;
- R11 `.greiabackup`;
- R12 parent management integration;
- R13 boot/recovery continuity;
- R13B signed rollback-safe Greia OS/runtime updates + preserve-profile recovery;
- R14 final multi-architecture certification.

## 14. Evidence discipline

Never infer Linux image, Bubblewrap runtime, direct DRM/KMS, Acer, Raspberry Pi, Web engine, memory/footprint, boot continuity, update/recovery or installer acceptance from source tests alone.

**Do not authorize Acer internal-disk installation until the established hardware/image evidence gates are satisfied and reviewed.**
