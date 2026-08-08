# Greia — Standalone Handover

Date: 2026-08-08  
Version: `0.13.0-phase0-dev`  
State: architecture-remediation plan ACTIVE; R0 complete; R1 authority/isolation in progress; local full verification 141/141 passing after first R1 tranche; hardware/display/ARM/Web evidence still pending.

## 1. Mandatory active plan

The authoritative implementation plan is:

`docs/plans/2026-08-08_ARCHITECTURE_REMEDIATION_AND_PLATFORM_COMPLETION.md`

`AGENTS.md` requires every future implementation session to read that plan, resume the first incomplete phase, append progress after substantive work, update this handover, and remove the active-plan reference only after the plan's final completion criteria are all satisfied.

Do not replace it with a new competing plan while it is active.

## 2. Current phase

**R1 — kernel/supervisor-enforced Activity authority and per-Activity storage isolation.**

The architecture deep review found that the old Bubblewrap boundary hid sibling profiles but still exposed the complete active profile root writable. It also found that `GREIA_ACTIVITY_CAPABILITIES` was being used as an SDK permission check even though Activity code can mutate its own environment.

The current R1 work addresses those findings before lifecycle, Web, graphics or package expansion.

## 3. R1 work completed in the current tranche

Implemented and verified locally:

- added immutable `ActivityAuthority` derived by platform code from the validated Activity manifest;
- installed Bubblewrap command no longer binds the complete active profile root writable;
- ordinary Activities bind only their own Activity data directory at `/run/greia-activity-data`;
- sibling Activity/profile/platform state remains hidden;
- trusted `customization.manage` receives a separate narrow customization bind rather than the whole profile;
- unauthorized removable media is hidden at `/media/greia`;
- media-capable trusted Activity sees media only through the host read-only root view;
- `GREIA_ACTIVITY_CAPABILITIES` remains available for SDK ergonomics but is explicitly documented as **not** the security authority;
- avatar-change requests now live inside the requesting Activity's own private data namespace at `.greia/requests/avatar.json`;
- ordinary Activities receive no avatar-request environment path;
- launcher-side avatar-request consumption occurs only for a validated manifest declaring `profile.manage_own`, preventing a forged environment variable from creating own-profile mutation authority;
- active system/runtime defaults were corrected from the missed `/media/pip` prototype path to `/media/greia`.

## 4. Verification

After the first R1 authority/isolation tranche:

```text
make verify
```

passes locally with:

- **141 / 141 provider-free unit tests PASS**;
- project/runtime/activity/asset validation PASS;
- bundled Activity validation PASS;
- existing build/system-overlay source gates PASS;
- source footprint remains approximately 15 MiB.

New/updated negative tests prove that:

- an ordinary Activity's sandbox command does not include the active profile root;
- only the Activity's own data directory is writable;
- ordinary Activity receives no customization or profile-request channel;
- forged `GREIA_ACTIVITY_CAPABILITIES` cannot add customization/media mounts;
- removable media is hidden unless authorized;
- missing Bubblewrap still fails closed.

This remains **source evidence only**. Linux Bubblewrap execution of the new mount layout must still be evidenced under the later certification phase.

## 5. Relevant commits

Plan/continuity:

- `48c38a73148e77884d516ae762b6adc974dbf7af` — create active architecture-remediation plan;
- `d9222f0e7493b4f92eb99d5ef432abd47b7da294` — make the plan mandatory in `AGENTS.md` with resume/progress/removal rules;
- `4bd561471b8f425fd918e3d3e62ba00b4e40ad0b` — log first R1 implementation progress in the active plan.

R1 source/tests/system overlay already mirrored into GitHub:

- `42942fb4804134ee04d9103448396aaf8364e1ea` — per-Activity supervisor authority/mount shape;
- `8cbda88a960c9173dd8d75955247873334c3eae3` — SDK capability semantics and Greia media root;
- `6310d05ba162c0372dca944af1b54027e024dd55` — least-privilege/forged-capability supervisor tests;
- `556d6647afb085f54bd86c3a8f654b3d0f40a892` — Greia removable-media service path;
- `40926ac3ba21565212259d47cbdf547b962c5ebb` — launcher media environment path;
- `0bdb6bb66b8de615e4397388698c0a852cfe43ca` — tmpfiles Greia media root;
- `5f648f9d0c5f7d69cb7e1b6b3db21df5e9120b1c` — exact supporting diff for profile-scoped avatar request consumption where the earlier documentation-first repository bootstrap does not yet contain those full source files.

## 6. Repository-mirroring note

The Greia GitHub repository was initially bootstrapped documentation-first before the complete v0.13 tree was available. Current implementation work is being moved into the canonical repository as it is touched.

For R1, the supervisor, Activity API, tests and relevant system-overlay files are present as source. The exact remaining profile/launcher request-path changes are preserved in:

`docs/reviews/2026-08-08_R1_SUPPORTING_PROFILE_REQUEST_DIFF.patch`

Do not reconstruct those changes from memory. A future source-mirroring pass should apply/replace that continuity patch with the full canonical `profiles.py`, `main.py`, and `test_profiles.py` files, then remove the temporary need for the patch as an implementation carrier.

## 7. R1 remaining work

Before marking R1 source-complete:

1. ensure the profile/launcher avatar-request changes are represented as full canonical source files in GitHub, not only the continuity patch;
2. review all current privileged Activity operations and verify each effect is enforced by a trusted mount/device/broker boundary rather than Activity-controlled environment state;
3. add any final negative tests needed around own-profile request consumption;
4. rerun `make verify`;
5. append the R1 closure entry to the active plan.

Linux Bubblewrap runtime evidence can remain UNPROVEN until the controlled Linux/VM evidence phase, provided the source phase labels that gap explicitly.

## 8. Next phase

After R1 source closure, begin:

**R2 — non-blocking Activity lifecycle, READY handshake, watchdog, graceful stop and forced return.**

The current blocking `subprocess.run()` supervisor must evolve into a runtime-neutral supervised Activity session before Web or a broad package ecosystem is added.

## 9. Stable architecture that remains in force

- Activity is the universal abstraction above runtimes.
- Python and future Web share storage/session/progression/package/backup semantics.
- ARM and i386 are peer first-class platform families; Pi 400 and Pi 500 are explicit ARM references.
- Xorg is a provisional migration/evidence baseline, not Greia's target architecture.
- Direct DRM/KMS-first appliance graphics remains the target direction.
- Platform owns durable child data, sessions, progression and rewards.
- Activity state is architecture-neutral and logically keyed by `(profile_id, activity_id)`.
- Removable media is untrusted and never autorun.
- `.greiaactivity` and `.greiabackup` remain future open platform formats to be implemented by the active plan.
- Source tests never substitute for Acer/Pi/QEMU hardware evidence.

## 10. Important later blockers

The active plan also covers:

- non-blocking lifecycle/watchdog;
- removal of Activity-authored global reward amounts;
- universal Storage/Session/Progression services;
- runtime-adapter abstraction;
- direct graphics replacement for Xorg;
- Pi 400/500 image adapters;
- embedded Web runtime benchmark/selection;
- `.greiaactivity` install/update;
- `.greiabackup` portable restore;
- typed Parent privileged service integration;
- branded-only boot/recovery continuity;
- full multi-architecture certification.

Do not authorize Acer internal-disk installation before the established hardware/image evidence gates are satisfied and reviewed.
