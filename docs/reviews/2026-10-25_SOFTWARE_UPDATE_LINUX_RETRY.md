# Software update Linux retry — exact-source runtime result

Date: 2026-10-25
Status: **CLEAN SOURCE RETRY PASSES SINGLE-ROOT OWNERSHIP/ORDER CASES; A/B FIXTURE BLOCKED BY CAPACITY; Session 04 OPEN**
Work order: `docs/testing/2026-10-24_SOFTWARE_UPDATE_ACCEPTANCE.md`
Source: `9161af3b30e3b96da314b24f4aba0e507eb46e7c` (code fix `ab02b9ec6`)
Host: Ubuntu 24.04 x86_64, KVM, QEMU 8.2.2, Python 3.12.3
Evidence root: `/var/tmp/greia-software-update-9161af3b30e3b96da314b24f4aba0e507eb46e7c-20261024T220454Z/`
Prior repaired-clone report: `docs/reviews/2026-10-24_SOFTWARE_UPDATE_LINUX_ACCEPTANCE_RESULT.md`

This retry rebuilt the RC installer and both fresh installed targets from the
committed ownership fix. No guest chmod/chown repair was used.

## Source gates

- Focused package/update/ownership/release fixture suite: **170 tests, OK with
  1 Linux-only skip** (`software-update-focused.log`). The skipped test was the
  real-account root-to-Parent handoff, which was then run successfully inside
  the installed guest (below).
- Full `make verify`: **5,957 tests, 7 failures, 3 errors, 3 skips; NOT GREEN**
  (`make-verify.log`). Failures were the documented Foresta content (3), Parent
  Wi-Fi source assertions (2), MBR message wording (1), and `morbidi`
  first-frame timing (1); errors were ARM64 plus the two missing optional Linux
  voice modules. No new failure appeared.

## Single-root clean retry

- RC installer built and verified: SHA-256
  `de75a782f786304235d89a631444c99a4ec04407567d34873b2d8119f040b0a2`.
- Real GUI install into fresh 16 GiB QEMU disks, detached boot, guest bootstrap
  facts PASS: marker exact, helper executable, apply timer enabled, recovery
  active, `/opt/greia-os` generation symlink and Activity-index alias correct.
- Clean image baseline: `/var/lib/greia-os/activity-packages` is
  `greiapanel:greiapanel 0755` and empty.

### Fresh clone A — Python before Parent seed

1. Child profile `TEST` created; Parent HTTPS pairing succeeded.
2. Python update uploaded and applied **before any Parent Activity seed**:
   job `88fb947b4eca4cab8d4441bd1821acb1`, version `0.13.1-retry`,
   `queued -> validating -> waiting_for_idle -> applied`; pointer
   `app-88fb947b4eca4cab8d4441bd1821acb1`.
3. Root update created the Parent store as `greiapanel:greiapanel` with
   private `0700` staging/versions/receipts and child-readable `0555`
   `gen-000001`.
4. Ordinary Parent install of `org.example.acceptance-painting` returned HTTP
   `201`; `/api/v1/activities` listed it as
   `parent_trusted_unsigned`; the child could traverse/read the generation and
   a child write probe was refused.

### Fresh clone B — Parent seed before updates

1. Two Parent Activities seeded through the ordinary Parent route first:
   `org.example.acceptance-painting` and `org.example.acceptance-writing`
   (`0.1.0-retry`), both HTTP `201`, active `gen-000003`.
2. Parent-source `one` update for painting (`0.2.0-retry`) applied:
   job `b4cc58599f994f5ea494651e29bf7111`.
3. Parent-source `set` update for painting + writing (`0.3.0-retry`) applied:
   job `48297eb63b5340e3acdcccd7742e42b5`; active `gen-000005`; both listed
   Parents retained `parent_trusted_unsigned`; built-in count stayed 45.
4. Built-in `writing` update applied after the Parent Activities:
   job `0b83ee6ca6d149dead02b6ecaa87fd8a`; both Parent Activities and all 45
   built-ins remained.
5. Ordinary Parent install of `org.example.acceptance-again` returned `201`;
   ordinary uninstall of `org.example.acceptance-writing` returned `200` with
   `profile_data_preserved=true`. Active Parent generation `gen-000007`
   contained the remaining two test Activities; built-ins remained 45.

### Real-account Linux regression

`test_activity_packages.ActivityPackageServiceTests.test_linux_root_to_greiapanel_store_handoff`
was run inside the installed guest as root with the real `greiakid`/
`greiapanel` accounts: **PASS**. `/tmp` and `/var/tmp` are too small for the
staging reserve, so the test used `TMPDIR=/var/lib/greia-os`; that is a test
environment adjustment, not a guest repair.

### Partial upload negative

A capped partial POST of the Python package returned curl exit `28` and **no
HTTP 202**. The authenticated status kept the same terminal job
(`0b83ee6ca6d149dead02b6ecaa87fd8a`, `applied`); offline inspection of the
stopped clone showed `NO_PENDING`, `NO_CANDIDATE`, and no queued job.

## A/B acceptance fixture — BLOCKED by profile capacity

The explicit `build-acceptance-fixture` command built and inspected the
experimental base bundle:

- fixture `greia-acceptance-fixture-0.13.0-phase0-dev`
- bundle SHA-256 `6f1e85eac0c6f0f81498e429c8c6f17ca46f45f8ed8552bc9f8c7cd4947592e3`
- payload 1,427,955,712 uncompressed bytes; minimum slot 1,429,004,288
- `artifact_class=experimental_acceptance_fixture`; `release_eligible=false`

The matching A/B installer build refused before publication:

```text
FAIL: accounted installed filesystem use is 1287 MiB (file data 1287 MiB,
filesystem used 1287 MiB); profile acer-aspire-one-i386-ab requires <1000 MiB.
```

The A/B profile declares `required_core_mib = 1000`,
`architecture_review_mib = 1250`, and `system_slot_bytes = 1536 MiB`. The
1287 MiB payload fits neither the 1000 MiB build gate nor the 1250 MiB
architecture-review threshold, so the fixture installer, ProductHarness,
full-system wrapper and A/B update/rollback legs were **NOT RUN**. This work
order's fixture route correctly did not waive the capacity gate. A/B
acceptance now needs an owner capacity decision (new A/B build limit with the
1536 MiB slot/finalizer reserve, or payload reduction), not a source waiver.

## Not run

- Receive-reserve HTTP `507` and retry.
- Parent-stop-after-durable-202 helper leg.
- Observed `applying` power-cut (the earlier repaired-clone `trial` cut is
  retained as historical evidence, not as this clean-source predicate).
- Full-system `.greia_update` and all A/B first-boot/update/rollback/PERSIST
  acceptance (blocked by the capacity gate above).
- Mobile-client upload and rendered HTML Parent UI (host streaming Parent API
  was used).
- Seeded child creations/saves hash comparison; profile survival was checked,
  but no creations were seeded in this retry.
- Physical hardware and USB media acceptance. The 8 GB LaCie remained
  unmodified.

## Next exact steps

1. Owner decision on the Acer A/B capacity: raise the A/B build/architecture
   limits with evidence that the 1536 MiB slot plus finalizer reserve still
   fits, or reduce the A/B payload.
2. Rebuild the A/B fixture installer and run ProductHarness §3/§10 once the
   capacity gate is accepted.
3. Run the remaining 507/Parent-stop/observed-applying-cut recipes on
   disposable clones.
4. Keep Session 04 OPEN; no release, A/B, physical or family-readiness claim is
   made here.

## A/B retry after owner size decisions (2026-10-25)

Owner decisions raised the Acer A/B acceptance-build accounting gate to
**1,500 MiB** and, after the measured hardware-support/initramfs failure, the
A/B system slot to **1,664 MiB** (1,500 MiB installed core plus 164 MiB
headroom; the 7 GB Acer reference target still fits). Source commits:
`9078fcd3b` (1500 build gate), `1ea67ab7b` (1664 slot and capacity tests),
`6d56a31ad` (harness live-partition selection), `6c6e64a82` (publish finalized
kernel/initramfs aliases), `8263462e0` (same-filesystem hardlink alias seam;
the 25 MiB initramfs exceeds the 8 MiB metadata write bound).

The explicit experimental fixture bundle built and inspected
(`greia-acceptance-fixture-0.13.0-phase0-dev`, bundle SHA-256
`6f1e85eac0c6f0f81498e429c8c6f17ca46f45f8ed8552bc9f8c7cd4947592e3`). A
disposable A/B installer was built from the 1664 MiB profile; the final
8263462e0 link change was injected into a disposable copy of its live root
(`ab-installer-patched.img`, SHA-256
`179ff31e8e54e8f175eae454d822d3d704abe05e40e2f36340137b211547c40a`) so the
18-minute-plus install/first-boot cycle could be observed. A clean full
installer build from 8263462e0 remains required for final evidence.

Observed with the patched disposable installer:

- **PASS — A/B install leg.** The installer transaction completed the fresh
  A/B layout, streamed slot A, applied the real hardware-support package set
  (including `intel-microcode`), and finalized the slot on the 1664 MiB slot
  without the earlier `ENOSPC`/initramfs failure. The finalizer now publishes
  `boot/vmlinuz-greia` and `boot/initramfs-greia.img` as hardlinks; the
  production GRUB config's kernel/initrd paths exist.
- **PASS — BIOS boot begins.** The installed first-boot clone boots from its
  BIOS GRUB entries into the Greia userspace; the control service reports the
  shipped boot-health socket present and powers off cleanly.
- **BLOCKED — first-boot health acceptance.** The PERSIST boot journal remains
  `first_install_pending` instead of ACCEPTED. The control `wait-health-poweroff`
  phase reached its socket but `greia_launcher.boot_health.maybe_load_production_token()`
  returned `None`, so it skipped the CONFIRM and powered off. The root
  credential/launcher token path is the next owner to debug; this is not a
  size/capacity failure. No healthy B update or rollback leg ran after this
  boundary.

Session 04 remains OPEN. Next exact steps: determine why the first-install
boot-health token is absent/failed on the A/B installed image (credential
service, finalization receipt, and launcher post-intro CONFIRM), repeat the
first boot after the fix, then build the clean 8263462e0 installer and run the
healthy-update and failure/rollback legs.

## A/B first-boot health accepted; active-slot isolation boundary (2026-10-25 late)

The **first-boot health path now works end-to-end** on the installed A/B
target. The test control starts the real credential/recovery units, the
generator issues the one-use capability, the socket service consumes it,
commits the first-install journal, and the control powers off cleanly. The
ProductHarness post-boot observation (default A, accepted release, pending
cleared, valid PERSIST) passed before the next guard refused the run.

Product defects fixed and verified in this boundary:

- `greia-boot-health-credential.service` and `greia-boot-health.service`
  could not create/consume the delivery token under `/run/greia-os`, whose
  tmpfiles ownership is `0770 greiakid:pipprofiles`, because both ran
  `root:root` with `CapabilityBoundingSet=` empty. Both now run with
  `Group=greiakid` and `SupplementaryGroups=pipprofiles`; the token is
  issued and consumed without DAC override.
- Boot history was written to `/var/lib/greia-os/diagnostics` on the active
  slot. The shipped service now writes it to
  `/run/greia-persist/greia/diagnostics` (PERSIST), so accepting a slot does
  not write that diagnostic into the slot.
- The test-only X8 control unit now `Wants` the credential/recovery units,
  is ordered `Before=greia-launcher.service`, waits for the token or an
  already-accepted journal, and streams the credential/recovery/service
  failure state to serial. This is harness-only under `tools/x8_qemu`.

Remaining **BLOCKED** boundary: `run_first_boot_product` then failed its
active-slot isolation guard:

```
LifecycleHarnessError: first-boot slot isolation violated: slot A changed
across its own acceptance boot
```

The first-install journal is accepted and the PERSIST boot history is no
longer on slot A, so this is not a health-commit failure. The active A/B
root is mounted/remounted writable during boot (the GRUB `ro` is re-mounted
read-write from the installed fstab/readiness path), and ordinary boot state
writes make the raw slot-A partition digest differ. Moving boot history to
PERSIST alone did not satisfy the harness's byte-identical active-slot
contract. This needs an explicit A/B writable-state decision: make the
active slot genuinely read-only and bind/persist writable state (including
`/var/lib/greia-os`), or define and enforce a bounded active-slot exception
in the acceptance contract. Do not silently relax the isolation guard. **Owner decision 2026-10-25:**
hand off this evidence; the architecture choice is deferred to the next
implementation owner.

No healthy B update, failure/rollback leg, 507, Parent-stop, applying-cut,
Mobile or physical leg ran after this boundary. The current `next.greiaupdate`
payload predates these unit fixes; it was not rebuilt, so the update-health
slot B would still carry the old credential/service units. The clean full
A/B installer from the fixed source was also not rebuilt; the tested target
was patched in place as a disposable fixture. Session 04 remains OPEN.

## Harness correction and short next retry (2026-10-25; source-only)

The follow-up resolves the testing-contract wall without changing the current
writable-root architecture. Hashes spanning a slot's own boot are diagnostic;
they are not runtime proof that the updater left every byte unchanged. The
first-A boot still requires untouched B to be identical. Production wrong-slot
refusals, authoritative boot/default/release/journal/PERSIST checks and recovery
accepted-release binding remain in force. This does not assert old-root file
inventory equality or mark any unexecuted Linux case passed.

Use `docs/testing/2026-10-25_AB_SMOKE_RETRY.md` next, rather than starting the
entire fault matrix. Rebuild baseline, next bundle and installer from the same
new source; do not reuse the patched installer or stale next payload described
above. Run install, first-A health and healthy A-to-B; preserve per-leg error
JSON/traceback/logs on failure. Remaining rollback/reverse, interruption,
Parent/device and data-survival gates stay open. Current source verification
and its full-gate result are recorded in HANDOVER. This addendum does not alter
the Linux observations or PASS/NOT RUN boundaries above.

The source follow-up passed 335 focused tests and the short guide's exact
66-test command. Its final macOS full run completed 5,958 tests with 6 failures,
3 errors and 9 skips, all matching recorded content/message/ARM64/macOS
outcomes; the full gate remains NOT GREEN. No Linux image/VM step was run in
this follow-up. Use the exact committed source and new smoke work order for
the next actual Linux result.
