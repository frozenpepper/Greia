# Acer A/B clean-source smoke retry — evidence report

Date: 2026-10-26 · Status: **PARTIAL — install/first boot PASS, healthy A-to-B
BLOCKED** · Session 04 **OPEN**

Work order: `docs/testing/2026-10-25_AB_SMOKE_RETRY.md`
Source: `866ba68277be8500db62de55a9189d78c9ea704b` (clean `main`)
Evidence root: `/var/tmp/greia-ab-smoke-866ba68277be8500db62de55a9189d78c9ea704b-20261025T162521Z`

**Routing correction (2026-10-26):** the proposed guest-serial investigation in
§8/§9 is superseded by the follow-up in §11. Use the conditional candidate-only
route in `docs/testing/2026-10-26_AB_CANDIDATE_RETRY.md`; do not enter or
manually repair the old guest. If its reuse preconditions fail, use the clean
three-leg fallback in `docs/testing/2026-10-25_AB_SMOKE_RETRY.md`.

## 1. Source gates

- `make verify`: **5,959 tests, 7 failures, 3 errors, 3 skips; NOT GREEN**.
  The failure/error IDs are identical to the documented 9161 Linux baseline
  (5,957 tests, 7 failures, 3 errors, 3 skips); the +2 tests are new committed
  source tests that pass. `BASELINE_REVIEW=matched`.
- Focused A/B product suites (`test_x8_qemu.test_product_boot_health`,
  `test_x8_qemu.test_session04_legs`): **66 tests OK**.
- Logs: `make-verify.log`, `make-verify.exit`, `ab-product-focused.log`,
  `ab-product-focused.exit`, `baseline-review.txt`.

The full gate is comparison evidence only. It does not waive the red baseline
and no release claim is made.

## 2. Clean artifacts built from the frozen SHA

- Base fixture: `greia-acceptance-fixture-0.13.0-phase0-dev`
  - release report SHA-256: `9cfa48ca1ee9b6861d3f1f66ec36c79a39781c34da34a8dcaca913c47410ec8d`
  - bundle SHA-256: `93f55468230ce4e2b63d4665b3e1f826ae384c47b918674fe5c432a2f3c29a17`
  - bundle size: 714,298,003 bytes
- Installer:
  - `greia-os-installer-acer-aspire-one-i386-ab.img`
  - SHA-256: `492483b77231cff7564a909c0c50a3d886d762a055f5ab427b11b4e54bafcdd4`
  - size: 2,270,167,040 bytes
- Next fixture: `greia-acceptance-fixture-0.13.1-phase0-dev`
  - release report SHA-256: `3139e349702d919d1e7881fe3abcf0ce324ffa755f5df94f330e189178d001cd`
  - bundle SHA-256: `76ef1ffe2795124f06f73ec81306313101129b7e23f74de38d5fbd7926a6fee9`
  - bundle size: 714,302,165 bytes
- All three are marked `experimental_acceptance_fixture` and
  `release_eligible: false`; both bundles pass the update inspector.
- The installer builder completed without errors and emitted the i386 BIOS
  plus i386/x86_64 EFI GRUB payloads.

During the first build attempt the fixture refused the 1664 MiB A/B slot because
`MAX_PAYLOAD_BYTES` was still 1536 MiB. Commit `866ba6827` raised the intrinsic
payload bound to 1664 MiB (the destination slot is the fixture's populate
ceiling) and added the capacity regression test; the rebuild then completed.

## 3. Leg results

### 3.1 Install — PASS

`vm/install/result.json`; the production installer completed the A/B layout,
streamed the base payload, applied the hardware-support set, and finalized the
slot. `install/product/disposable-target.img` is the disposable target.

### 3.2 First boot — PASS

`vm/first-boot/result.json`; the first-install health path accepted A:
the credential generator issued the one-use capability, the socket service
consumed it, the first-install journal cleared, default A remained selected,
and the control powered off cleanly. The active-slot digest change is
observational under the current writable-root harness contract; the unbooted
inactive slot stayed strict.

### 3.3 Healthy A-to-B — BLOCKED

`vm/healthy-update/result.json` records a QEMU timeout in the
`update-verify` phase. The guest serial
(`vm/healthy-update/product/product-update-verify-serial.log`) records:

```
x8-control: phase update-verify starting
x8-control: socket /run/greia-os/system-update.sock present
...
x8-control: update VERIFY_CURRENT_CANDIDATE refused:
  {'reason': 'no current update candidate in the inbox', 'status': 'REFUSED'}
```

The preceding `update-status` phase returned `STATUS -> OK` and powered off.
The control then did not power off after the refusal, so the harness waited for
its 2400 s timeout.

## 4. The Issue: candidate present on PERSIST, not discovered by the service

The 0.13.1 candidate was injected before the update boot into the disposable
clone's PERSIST parent-credentials namespace:

```
greia/namespaces/parent-credentials/system-updates/inbox/candidate.greiaupdate
size: 714,302,165 bytes
```

That location is intentionally the source-owned inbox path:

- `src/greia_platform/system_updates.py:475`:
  `inbox_dir = state_dir / "system-updates" / "inbox"`
- installed unit
  `build/overlay/etc/systemd/system/greia-system-update.service:44`:
  `GREIA_UPDATE_STATE_DIR=/var/lib/greia-os`
- installed fstab binds PERSIST
  `.../greia/namespaces/parent-credentials` to `/var/lib/greia-os`

Despite this, the running `greia-system-update.service` still reports no
candidate. The exact running-service cause is **unresolved**. Candidate causes
for the next owner to prove or eliminate:

1. the service's effective state directory differs from the unit file at
   runtime (inspect `systemctl show`/`systemctl cat` and the guest journal);
2. the PERSIST bind is not mounted or is shadowed when the service starts
   (inspect `findmnt`, `stat`, and the fstab bind target on the guest);
3. the `update-status` phase rejects/removes the candidate before
   `update-verify` (the serial shows no removal, but the service journal is
   the authority);
4. candidate naming/manifest validation in `SystemUpdateInbox` differs from
   the host-injected filename or content;
5. the service user cannot read the candidate/inbox at runtime (candidate is
   root:root 0644, inbox root:root 0755; confirm the service user and SELinux/
   DAC state).

Do not treat the healthy A-to-B leg as passed until the running service
actually returns `VERIFIED` for this candidate.

## 5. Harness fixes made during the retry

These are test-only changes under `tools/x8_qemu` and do not alter the
installed image or production trust boundary:

- The control-disk copier now copies every declared phase input, not only
  `phase.json` (the candidate was previously visible on the host control
  directory but absent on the guest control mount).
- The control disk is sized for the candidate on update legs (the previous
  fixed 64 MiB image was far smaller than the 714 MiB bundle).
- The candidate is now injected host-side into the disposable clone's PERSIST
  inbox before the update boot, avoiding a slow 682 MiB guest-to-guest copy and
  the control-disk size trap.
- The control candidate copy is skipped when the inbox already holds the
  candidate.
- The first-boot/health harness fakes gained an explicit candidate-injection
  seam; the focused source suites continue to pass.

## 6. Product fixes carried from the first-boot work

Committed before this retry and verified by the first boot:

- boot-health credential generator and socket service now run with
  `Group=greiakid` and `SupplementaryGroups=pipprofiles`, so they can create
  and consume the one-use token under `/run/greia-os` without DAC override;
- boot history moved from the active slot to
  `/run/greia-persist/greia/diagnostics`;
- the test control unit pulls the real credential/recovery units, starts
  before the launcher and waits for the token.

## 7. What did not run

No healthy B boot, B health acceptance, rollback/reverse, userspace failure,
nonboot, PERSIST refusal, receive-reserve 507, Parent-stop-after-202, observed
`applying` cut, Mobile, physical-device, USB or GUI-rendered acceptance leg
ran. The USB key was not modified. The host was not a Mac; no GitHub Actions
were used.

## 8. Next exact step

Boot a disposable accepted-A clone with the 0.13.1 candidate in the PERSIST
inbox and enter the guest (serial console) before the update phase. Then:

1. confirm the `/var/lib/greia-os` bind and candidate with
   `findmnt`/`ls -l`/`stat`;
2. inspect `systemctl cat/show greia-system-update.service` and its journal;
3. exercise `SystemUpdateInbox` against the running state directory and
   compare its expected candidate name/manifest with the injected bundle;
4. fix the service/harness mismatch, then rerun healthy A-to-B;
5. only after a healthy B acceptance proceed to the 10/23 and 10/24 fault
   matrices.

## 9. Evidence and limitations

- Raw evidence: `/var/tmp/greia-ab-smoke-866ba68277be8500db62de55a9189d78c9ea704b-20261025T162521Z` (full gate, focused suites, build logs, artifact hashes,
  install/first-boot JSON, healthy-update JSON, serial logs).
- Old disposable VM/build evidence from the pre-retry session was pruned to
  bring the host below the work order's disk threshold; this report and the
  source commits are the durable record.
- The full gate remains NOT GREEN. The install/first boot PASS is source/image
  evidence only; the healthy update and every later leg remain unproven.
- Session 04 remains OPEN.

## 10. Commit trail

- `6f00c9f7d` — published the 2026-10-25 A/B smoke work order.
- `0ede382f8` — aligned A/B acceptance checks with writable-root boots.
- `866ba6827` — raised the payload bound to 1664 MiB and added the regression.
- `99cf06d08` — fixed boot-health token access and moved history to PERSIST.
- `344417139` — added host-side A/B candidate injection and recorded the
  partial smoke.
- `bbf33665b` — cleaned HANDOVER markdown escapes.

## 11. 2026-10-26 follow-up — test-harness receipt correction; Linux retry pending

Append-only correction: the prior injector placed `candidate.greiaupdate` in
the PERSIST inbox but did not publish the `status.json` receipt that
`SystemUpdateInbox` uses for canonical candidate discovery. That explains the
missing-candidate result as an incomplete test injection; it does not yet
prove the service will accept the corrected injection at runtime. No Linux
VM rerun has occurred, so healthy A-to-B remains UNPROVEN.

The source-only harness correction now mounts the disposable clone's PERSIST,
publishes the bundle through `SystemUpdateInbox.receive`, projects the validated
`bundle_path` to the guest's `/var/lib/greia-os` location, restores namespace
ownership, and fsyncs candidate and receipt. Control runner uses the same inbox
API when receiving a candidate on control media. Declared control inputs are
copied and control-disk sizing supports the bundle. Refusal errors now produce
bounded serial diagnostics and power off so the host captures a phase marker;
the installer control-disk default-size NameError and related fake seam were
also corrected. All changes are test harness/tests; no shipped updater,
installer or runtime inputs changed in this tranche.

Current source review passed. The candidate guide's focused selectors passed
**168 tests in 1.220 s**, and the broader X8 focused gate passed **296 tests in
3.236 s**. The local full gate is **5,959 tests, 6 failures, 3 errors, 9 skips;
NOT GREEN**. The six failures are the known Foresta English/Spanish/French
content expectations (3), MBR diagnostic wording (1), and Parent Wi-Fi
assertions (2); errors are the ARM64 profile resolution (1) and two macOS
`lsblk` cases. Do not claim the full gate is green. These source results do not
extend the previous Linux install/A acceptance evidence.

After reviewed harness changes are committed, next run
`docs/testing/2026-10-26_AB_CANDIDATE_RETRY.md` on Linux if its source-diff,
artifact-SHA, prior first-boot, and PERSIST checks pass. This reuses the old
clean bundles and accepted-A image. If preflight fails, use the clean three-leg
fallback `docs/testing/2026-10-25_AB_SMOKE_RETRY.md`. Do not inspect or repair
the guest manually. On a healthy B result, continue with the 10/23 and 10/24
fault matrices. Session 04 remains OPEN.

Verification scope: these commands ran on the Mac worktree rooted at
`0c2ca7e07`, with the reviewed harness changes. The full gate started before
the final identity-test fake-injection correction; both final focused runs
include that correction. Separately, `make validate` stopped at the existing
ARM64 builder error; `make shell-check footprint` passed. All Bash fences and
Python heredocs in both retry guides parsed successfully. Local logs are in
`/tmp/greia-ab-candidate-followup/` (temporary, not Linux VM evidence).
