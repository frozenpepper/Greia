# Greia — Standalone Engineering Handover

**Date:** 2026-08-09
**Version:** `0.13.0-phase0-dev`
**Repository:** `frozenpepper/Greia` (private)
**Canonical integration branch at this handover:** `r6-runtime-integration-recovery`
**PR:** #1 — R0/R5/R6 integrated recovery and source closure
**Current functional phase:** **R7 — Direct Greia graphics/session architecture**

## 1. Current source state

The long recovery/source-loss incident is closed at source level. Do not reopen v0.12 recovery and do not recreate R5 again.

Authoritative clean-checkout source evidence:

```text
checkout: 7562471d868a23cd90d88b43aed2501988eb5740
tracked files: 318
tracked PNGs: 123
git worktree: clean
Python compile: PASS
R5 source architecture invariants: PASS
R6 source architecture invariants: PASS
provider-free tests: 194 / 194 PASS
project validation: PASS
bundled Activity validators: PASS (2 / 2)
source/shell/footprint gate: PASS
```

The permanent `.github/workflows/r0-clean-verify.yml` is read-only CI and enforces R5/R6 source invariants plus full `make verify`.

## 2. Phase classification

```text
R0   canonical repository / reproducibility                COMPLETE
R1   PermissionBroker / trust / per-Activity authority     source implementation green in complete gate
R2   runtime-neutral lifecycle/watchdog                    source implementation green in complete gate
R3   permanent Activity IDs / caps / perms / events        source implementation green in complete gate
R4   Universal Storage                                     source implementation green; real ProfileContext namespace repaired
R5   sessions / events / progression / reward ledger       SOURCE-CLOSED — NEW reviewed reimplementation
R6.1 Device Capability Service / typed HAL                  SOURCE-CLOSED
R6.2 Runtime Manager / runtime adapter integration          SOURCE-CLOSED
R7   direct graphics/session architecture                  NEXT / NOT YET IMPLEMENTED
R8+  not started or open per active plan
```

“Source-closed” is intentionally narrower than physical certification. Direct DRM/KMS, Acer behavior, Pi 400/500 behavior, installed-image performance, and no-visible-Linux hardware evidence remain assigned to R7/R8/R14.

## 3. R0 continuity closure

Historical v0.12 archive byte authority remains:

```text
SHA-256 7afb5028aa9f70930de1df8df4aa5a1fe00321fbfdeb94a4316cb234c332b124
318 archive files
123 PNGs
```

All required baseline source/build/test/config and all 123 PNG assets are now repository-managed. The current GitHub tree passes the full source/build/test gate without any chat-session archive or lost local workspace.

## 4. R5 replacement — important provenance

The former post-v0.12 `src/greia_platform/history.py` was genuinely lost and could not be recovered. The current module is **not historical recovered source**. It is a new reviewed reimplementation authorized on 2026-08-09 and grounded in:

1. ADR 0017;
2. `runtime/history-policy.toml`;
3. `runtime/progression-policy.toml`;
4. surviving event protocol/client/broker contracts;
5. Profile/Storage contracts;
6. parent progress-summary contract.

Core authority: `ProfileHistoryStore` owns the private per-profile SQLite implementation; Activities do not. It records authoritative sessions before runtime/storage/sandbox/child creation, READY/final state, restart recovery, bounded event history, score aggregates, reward balances/ledger and portable logical export.

Event idempotency is content-bound and transactional. An identical replay returns the existing event without progression duplication; conflicting reuse fails. Rewards are computed only from Greia progression policy; Activity payload reward-like fields have no authority.

## 5. Installed R5 integration

Installed launcher composition creates one `PlatformHistoryService`. `ActivitySupervisor` owns session orchestration and per-session broker lifetime but not SQLite policy.

Every Activity launch receives, where applicable:

- Universal Storage broker socket + opaque token;
- Event broker socket + opaque token;
- runtime-adapter lifecycle transport;
- platform session ID.

Durable Storage/history roots are never mounted into the Activity sandbox. The event broker binds the trusted live manifest + profile history store + platform progression policy + platform session ID.

Launch failure, runtime failure, READY timeout, forced stop, platform failure, normal completion and platform restart are normalized distinctly. Missing Bubblewrap and cleanup failures are regression-tested so authoritative rows do not remain falsely open.

## 6. Parent progress boundary

`ParentProgressReader` is wired into parent status/API/UI. It exposes only bounded logical summaries. It does not expose DB paths, raw event payloads, idempotency keys, broker tokens, or internal session IDs. Corrupt history returns `available:false` and does not take other parent controls down.

## 7. R4 integration repair discovered during R5 work

Real `ProfileContext` previously lacked `activity_storage_dir()`, while synthetic Supervisor tests accidentally hid that production mismatch. Profiles now have a dedicated `storage/` namespace, separate from raw Activity data/HOME, with validated per-Activity directories. This is covered by real ProfileContext tests.

## 8. R6 source architecture

R6 source closure remains intact after the R5 integration:

- one shared HAL-backed `DeviceCapabilityService` feeds PermissionBroker and RuntimeManager;
- launch authority carries the semantic device snapshot token and stale compatibility fails before process creation;
- Activity Registry remains runtime-neutral;
- Python validation/env/lifecycle transport/process behavior is behind `PythonRuntimeAdapter`;
- RuntimeManager owns adapter lookup/compatibility/launch delegation;
- runtime adapters own command/cwd/runtime env, runtime handle creation, exit normalization, force-stop and cleanup;
- platform session identity remains runtime-independent;
- Supervisor contains no Python READY/STOP marker implementation, direct `Popen`, or process-group signaling;
- Storage, Session, Event, Progression and Reward remain common platform services rather than Python-specific services.

## 9. Key commits

```text
1d34e5e2c67d0113e146c7fa48d16dc60aa9c82c  restore all 123 archive-verified PNG assets
67cb59c7308c71226777742731d957c845e464a6  snapshot-bind launch authority
94f93941db32a91e77c8af09f0eab4bb7c28bc07  runtime-owned lifecycle transport
0cfb82aa89df5ebc9c03a01061ebd8da82f8f4dd  new R5 History/Progression authority
b89906cc5b3a6d01e87dd6177838976dd001f500  trust-aware Activity validator regression coverage
5bd867c9488fcd61a598813cdf7a42c396ec3b2c  real ProfileContext durable Storage namespace
e790a36e36b845d0a9d0ecf057180ffd3a213af3  installed sessions/event broker integration
2819f73dcc57c3b69d002532c03f5d2021e7c10f  R5 failure-path + parent progress closure
7562471d868a23cd90d88b43aed2501988eb5740  permanent clean R5/R6 architecture gate
```

## 10. Mandatory resume order

Before implementation:

1. `AGENTS.md`
2. `README.md`
3. `docs/architecture/GREIA_ARCHITECTURE.md`
4. ADR 0012
5. ADR 0013
6. ADR 0014
7. ADR 0015
8. ADR 0016
9. ADR 0017
10. `docs/plans/2026-08-08_ARCHITECTURE_REMEDIATION_AND_PLATFORM_COMPLETION.md`
11. `docs/reviews/2026-08-09_R5_REIMPLEMENTATION_AND_R6_INTEGRATED_CLOSURE.md`
12. this handover

## 11. Exact next phase — R7

Do not refactor R1–R6 again unless an R7 integration test exposes a concrete defect.

First R7 tranche:

1. inventory every `DISPLAY`, Xauthority, XShm, `xinput`, `xrandr`, Xorg package/config/service/session assumption;
2. inspect `build/overlay/usr/local/lib/greia-os/greia-x-session`, Xorg configs, package sets, `hardware_session.py`, `hal.py`, launcher/Pygame/SDL initialization and related tests;
3. classify each dependency as target interface, provisional backend, build/boot glue, or removable legacy debt;
4. define the direct Display/Input backend beneath the existing R6 typed HAL; do not change Activity APIs;
5. prototype SDL direct DRM/KMS/KMSDRM and establish VM/x86 measurement methodology;
6. determine by evidence—not convenience—whether a tiny compositor/session broker is required for shell↔Activity ownership, Web surfaces, transitions and crash recovery;
7. do not deepen X11 and do not claim hardware success from source tests.

## 12. Non-negotiable continuity rules

- GitHub is canonical source of truth; commit coherent tranches as work proceeds.
- Do not reopen v0.12 recovery.
- Do not describe the new R5 implementation as recovered historical source.
- Do not fork Storage/Session/Event/Progression/Reward per runtime.
- Do not make Activity environment text trusted authority.
- Do not expose a Linux desktop/shell/WM in the normal child path.
- Xorg is provisional; R7 must move toward the direct graphics target rather than layering more architecture on X11.
- Hardware evidence gaps must stay explicit until actually tested.
