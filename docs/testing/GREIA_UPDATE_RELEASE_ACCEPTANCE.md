# Greia update release acceptance — one practical work order

**Status:** CURRENT execution guide (2026-10-27). **Owner direction:** fix the updater and confirm working updates promptly, in consolidated runs. **Authority:** ADR 0036 (A/B), ADR 0038 (application generations), and the September lifecycle plan. This document replaces dated update-diagnostic handoffs as the **execution router**, not their factual findings. The previous `1275` diagnostic already captured the failure; there is no need to run its frozen-source comparison or repeat its old single-stage job.

**Pre-release policy:** Greia has no released installed base to preserve. Do not build or test migration bridges, legacy reader paths, old image upgrades or upgrade-format backwards compatibility. Test only fresh images from the current code and updates between coherent *current* acceptance releases. Retain rollback to the previous healthy installation or application generation: rollback is correctness, not backwards compatibility.

**Execution target:** the existing Linux test host and **disposable virtual disks**, using the current committed `main`. Do not flash or overwrite a physical/family disk, or touch real family profiles. Actual production protections (partition identity, compatibility, bounded writes, atomic activation, health and rollback, child-data preservation) remain in force. Remove **process ceremony**, not these protections.

## Working rules — minimize time-to-answer

1. Record current `git rev-parse HEAD`, host/guest architecture, image/package identities and one evidence directory per **consolidated test session**. Preserve unrelated local changes. Pull/merge fast-forward when safe; if work exists, reconcile it rather than resetting/cleaning. Do not create arbitrary source freezes or reject unrelated recent commits because they differ from an old historical SHA.
2. **Implement and test in the same assignment.** The owner explicitly authorizes the local coding agent to fix update-path bugs, add focused tests, build disposable fixtures, execute their full test sequence, and commit coherent fixes to `main`. The restrictions in `GREIA_LOCAL_AGENT_TASK_QUEUE.md` apply to that *separate backlog*, not this implementation/acceptance assignment.
3. Work iteratively: investigate -> repair actual source -> focused test -> continue. Do not end the whole job after every ordinary failure, require a new handoff per subprocess, or preserve a full second set of duplicate source-gate documents. A genuine destructive-target ambiguity, unrecoverable evidence corruption, or unexpected risk to non-disposable data **does** stop destructive actions.
4. Run focused tests while repairing. Run `make verify` **once after the coherent patch set**, record its actual status, and investigate failures in the changed area. Pre-existing unrelated failures must be recorded, **not** used to prevent relevant disposable-QEMU acceptance. Never misreport a failing full suite as PASS.
5. Use one session directory with a concise `RESULT.md`, command logs and machine-readable outcomes. Save the **first real failure** and enough logs to diagnose it; do not produce a sprawling report archive for each preflight. After a fix, re-run the affected scenario. Keep successful image/package artifacts for subsequent test legs when they are still valid for that source. Do not use an old image to claim current-source acceptance.
6. This is a **developer test run**, not authority to publish an ordinary-family release. Release readiness remains a separate decision after measured results.

## First source fix: A/B stage cannot measure `sda2`

Captured production error (guest from `1275e0be1`, reviewed host `78f07861`):

```text
STAGE_CURRENT_CANDIDATE -> ERROR / REFUSED
inactive-slot filesystem is unavailable: block topology observation failed:
slot device capacity is unobservable: sda2
```

Analysis: [old-release stage refusal](../reviews/2026-10-27_AB_OLD_RELEASE_STAGE_REFUSAL_ANALYSIS.md); saved execution: [diagnostic result](../reviews/2026-10-27_AB_OLD_RELEASE_STAGE_DIAGNOSTIC_RESULT.md).

Current owner: `src/greia_platform/system_updates.py`, `_block_node_size_bytes` through `_observe_production_topology`. The primary `BLKGETSIZE64` ioctl is hard-coded as `0x80081272` (64-bit request encoding); the guest is i386; the fallback calls `blockdev --getsize64`, which might be missing or denied. Do not assume a specific root cause from the aggregate error alone.

**Implement in current code:**

- Prefer an architecture-correct ioctl and/or a bounded `/sys/class/block/<validated-device-name>/size` capacity fallback (Linux sector count × 512 bytes). Ensure it works on i386 and x86_64; validate positive integer, sensible bounds, device identity and expected partition size. No arbitrary path traversal, guessed partition, permissive capacity default, or reduced layout identity checks.
- Keep `blockdev` as a useful alternative if appropriate. Surface distinguishable ioctl/sysfs/command causes on failure, with bounded error text; do not turn ordinary unavailable methods into a service crash if another authoritative method succeeds.
- Add focused tests for both ioctl encodings, absent executable, valid/missing/malformed/zero sysfs, command failure and mismatch. Tests must not require real devices.
- A short **read-only** guest probe of both ioctl requests, sysfs and `blockdev` may help distinguish hypotheses, but it is **not** a mandatory prerequisite to implementing the clearly portable fallback. Do not patch the frozen `1275` guest. There is no value in repeating the failed historical stage diagnostic.

## Pre-release compatibility cleanup within this assignment

Greia has **never shipped**. Do not implement backwards compatibility for
older development images, obsolete format readers or historical release
identities. The one-time receiver bridge CLI, implementation and dedicated
tests have already been removed from current `main`. Do **not** recreate
them. Use new current-source images rather than migrating historical test
installations. As part of the ordinary source review, retire any other
*demonstrably unused* development-version compatibility branches that add
maintenance burden, but do not destabilize the first-install bootstrap,
hardware compatibility checks, normal update recovery or rollback.

Because bridge-only tests were deleted, ensure current-language snapshot and
current Python/combined update coverage remains in the focused package and
generation suites; add a simple current-source replacement test if needed.
Do not run a `build-receiver-bridge` command or claim its historical PASS as
a result of the current test run.

## Consolidated installed acceptance — two separate lanes

Use the existing repository tools and retained detailed examples, checking CLI help and current source before execution. Do not copy historical SHAs, old expected bundle hashes or outdated gating blocks. Existing supporting procedures are [A/B Linux test details](2026-10-23_SYSTEM_UPDATE_LINUX_ACCEPTANCE.md), [application package details](2026-10-24_SOFTWARE_UPDATE_ACCEPTANCE.md), [language-resource package details](2026-10-27_LANGUAGE_UPDATE_PACKAGE_ACCEPTANCE.md), and [package operator guide](../development/GREIA_SOFTWARE_UPDATE_PACKAGES.md).

### Lane A — Full-system A/B, disposable i386 QEMU

- Build **two genuinely different** current-source experimental release fixtures and their matching installer, using the existing Greia release/fixture builder; inspect both v3 bundles. Use **one matching coherent build set**, not `1275` image plus current host helpers.
- Run a **real blank-disk install** in QEMU -> first healthy boot into A -> deliver/stage newer bundle into inactive B -> explicit arm/restart -> boot B -> confirm B becomes accepted. Inspect layout PARTUUIDs, capacities, boot journal, system version, mount state and preserved PERSIST child data. A bare QEMU exit code is not acceptance.
- On a fresh disposable clone, inject a health- or boot-failure for candidate B and verify a successful automatic rollback to known-good A **without losing PERSIST data**. Exercise one interrupted-stage/recovery case. If further cases are cheap, continue with reverse B->A and Parent full-system upload; record unexecuted items honestly.
- If a scenario fails, diagnose the first concrete service response, patch current source, run focused tests, rebuild only artifacts affected by the patch, and retry the **relevant** scenario. Do not endlessly restart the whole matrix for unrelated documentation changes.

### Lane B — Lightweight `.greia_update` on an installed disposable system

- Verify Python/platform, Activities and combined package builder/inspector using the current [operator guide](../development/GREIA_SOFTWARE_UPDATE_PACKAGES.md), especially paired `languages/<locale>/manifest.json` and `ui.json` for `en,it,es,fr`.
- On a **current** installed baseline, use normal Parent **Upload & install** for Python/platform update, Activity update and a combined update. Check job transitions to `applied`, code/Activity versions and locale inventory, runtime health, continued operation after closing/disconnecting Parent, and preservation of profiles/saves/unlisted Activities. Include one rejected/broken update and successful prior-generation recovery.
- A/B system-slot acceptance and application generation acceptance are independent; do not withhold one lane's valid results because the other lane fails.

## Single final report and commit

Commit implementation and tests to `main` (no branch/PR unless the owner requests one); preserve concurrent work. Publish **one concise** `docs/reviews/<date>_UPDATE_RELEASE_ACCEPTANCE_RESULT.md` containing:

- tested source SHA(s), host/guest architecture, artifact/package identities, evidence/log paths;
- a compact PASS/FAIL/NOT RUN table: A/B install, A first boot, stage B, arm, B healthy acceptance, rollback, interruption recovery; Python, Activity, combined, rejected update/recovery, Parent disconnected continuation;
- first concrete cause and fix for any failure; targeted tests and actual `make verify` result (with unrelated known failures separately stated);
- outstanding blockers/physical acceptance gaps, if any.

Update `HANDOVER.md`, the lifecycle plan progress ledger and the affected skill/agent instructions **once for the coherent work**, not after every small retry. If current A/B and application lanes pass in QEMU, say so, while still distinguishing physical/USB installer and family release approval.

**Stop only for:** a destructive target that is not demonstrably disposable, possible real-data loss, unresolvable image identity mismatch, or a genuinely unrecoverable host/tooling problem. Otherwise, debug, fix, retest and complete as much of the matrix as the existing Linux host permits in one consolidated session.
