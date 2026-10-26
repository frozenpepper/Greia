# Current-source A/B smoke rerun — evidence report

Date: 2026-10-26 · Status: **PARTIAL — install/first boot PASS; healthy
A-to-B FAILED at `update-stage` (harness timeout); Session 04 OPEN**

Work order: `docs/testing/2026-10-25_AB_SMOKE_RETRY.md`
Source: `1275e0be1a9e0cda724ce18151ae65a25f03c98c` (clean `main`)
Evidence root: `/var/tmp/greia-ab-smoke-1275e0be1a9e0cda724ce18151ae65a25f03c98c-20261026T014350Z`

This is the clean three-leg rerun required after the installed-updater
discovery simplification. It does not reuse the superseded `866ba6827`
images. Large obsolete artifacts from that earlier run were pruned before this
run to meet the work order's below-80%-disk prerequisite; their small logs and
JSON were preserved at
`/var/tmp/greia-superseded-866ba6827-evidence-text-20261026`.

## 1. Host and source gates

- Host: Linux `x86_64`, Python 3.12.3, QEMU/qemu-img 8.2.2; SMART overall
  health **PASSED**; run started at 76% disk use.
- `make verify`: **5,961 tests, 6 failures, 3 errors, 3 skips; NOT GREEN**.
  Every failure/error ID is present in the documented `866ba6827` Linux
  baseline (5,959 tests, 7 failures, 3 errors, 3 skips); the earlier extra
  `test_representative_activities_reach_first_frame_cheaply`
  (`morbidi_mostriciattoli`) failure did not recur. No new failure or changed
  cause was observed; `BASELINE_REVIEW=matched`. This is comparison evidence,
  not a waiver.
- Focused A/B selectors from the work order:
  **232 tests, OK** (`test_x8_qemu.test_product`,
  `test_product_install`, `test_product_boot_health`,
  `test_session04_legs`, `test_product_boot_health_identity`,
  `test_system_update_service`, `test_system_updates`,
  `test_parent_system_updates`, `test_update_privileged_bridge`).
- Logs: `make-verify.log`, `make-verify.exit`, `baseline-review.txt`,
  `ab-product-focused.log`, `ab-product-focused.exit`.

## 2. Artifacts built from the frozen SHA

- Base fixture `greia-acceptance-fixture-0.13.0-phase0-dev`
  - report SHA-256: `2241776d7c68040e098975758e696e22e9a2ba0ad8632a1b8e78ef0e6fd1e59a`
  - bundle SHA-256: `b45f0fc77aaf04883442a74be742dc4e1fa888648a55e274b51b836a5b662a9b`
  - bundle size: 714,301,588 bytes
- Installer `greia-os-installer-acer-aspire-one-i386-ab.img`
  - SHA-256: `1edbcb0bec1b8b279543e74d4a39c0b2dc61454ce102f988fbe0fa75ce325571`
  - size: 2,270,167,040 bytes
- Next fixture `greia-acceptance-fixture-0.13.1-phase0-dev`
  - report SHA-256: `3b86a165f93a70f9e6ca28dd123bd9280d64fa67db29987c2543d4eed271571d`
  - bundle SHA-256: `3ae9cdeafa6e52459016e1a23315648ee4b8887a314c77c288259c1df4d68aa5`
  - bundle size: 714,243,764 bytes
- Both fixtures are `experimental_acceptance_fixture` with
  `release_eligible: false`; both bundles pass `greia_update.py inspect`.
  The installer builder emitted i386 BIOS plus i386/x86_64 EFI GRUB payloads.

Hashes/sizes: `artifacts.sha256`, `artifacts.size`; build/doctor logs are
`doctor-base.log`, `build-base-fixture.log`, `build-installer.log`,
`doctor-next.log`, `build-next-fixture.log`.

## 3. Leg results

### 3.1 Install — PASS

`vm/install/result.json` reports `ok: true`, base bundle SHA `b45f0fc7…`,
`source_image_mutated: false`, and the production installer phases
`install-prepare`/`install-execute` completed. Default observed slot is A.

### 3.2 First boot — PASS

`vm/first-boot/result.json` reports `ok: true`, default/committed slot A,
accepted release `greia-acceptance-fixture-0.13.0-phase0-dev`, journal state
`accepted`, inactive slot B unchanged, and a clean poweroff. The accepted-A
clone is `vm/first-boot/product/firstboot-clone.img`
(SHA-256 `83d693d915d53e314906fc7e4b319257ba201855121aa1f529f0bf998bf7d1a2`,
7,516,192,768 bytes).

### 3.3 Healthy A-to-B — FAILED at `update-stage`

`vm/healthy-update/result.json` reports `ok: false`, `elapsed_seconds:
591.1006727049989`:

```
product installed control phase update-stage failed: x8-control: phase
update-stage failed (exit 120); capturing service diagnostics; reason: greia
login: x8-control: update failed: TimeoutError: timed out
```

The per-phase serial logs show the installed updater discovery fix working:

- `update-status`: `STATUS -> OK`
- `update-verify`: `VERIFY_CURRENT_CANDIDATE -> VERIFIED`
- `update-stage`: the control reached the shipped socket, then the test-only
  guest client raised `TimeoutError: timed out` and the control powered off.

Exact first-failure serial tail
(`product-update-stage-serial.log`):

```
x8-control: phase update-stage starting
x8-control: socket /run/greia-os/system-update.sock present
...
greia login: x8-control: update failed: TimeoutError: timed out
  File "<stdin>", line 55, in <module>
x8-control: phase update-stage failed (exit 120); capturing service diagnostics
...
[   46.806643] reboot: Power down
```

The control runner in `tools/x8_qemu/product.py:476` sets
`client.settimeout(30.0)` for all update operations. `STAGE_CURRENT_CANDIDATE`
must verify and write the ~714 MB candidate into the inactive slot; 30 s is
not a credible bound for that work under this QEMU target. The service had
started and no refusal response was recorded before the control powered off.
The failure is therefore a **test-harness control timeout**, not evidence of a
production stage refusal. Stage completion, arm, B boot/health and the
post-update observation were not reached. Healthy B remains **UNPROVEN**.

The leg left 19 associated loop devices across install/first-boot/healthy
outputs (including partscan clones and deleted control images). They were
detached with `build/lib/safe-cleanup.sh` `safe_detach_loop`; the post-cleanup
`losetup -a | grep greia` audit is empty. This harness cleanup leak must be
fixed before relying on repeated runs.

Logs: `ab-smoke.log`, `vm/healthy-update/result.json`,
`vm/healthy-update/product/product-update-status-serial.log`,
`product-update-verify-serial.log`, `product-update-stage-serial.log`.

## 4. Evidence boundary and next step

Install and first-A acceptance are PASS for this exact source and artifacts.
The installed-updater discovery/verify path is now demonstrated through
`VERIFIED`. The healthy A-to-B acceptance remains OPEN because `update-stage`,
arm, B boot, B health and the final host observation did not run.

Before the next attempt, fix the test-only control so `STAGE_CURRENT_CANDIDATE`
gets a bounded timeout appropriate to writing the slot (or stream progress),
and fix the loop-cleanup leak. Because that changes harness source, freeze a
new committed `main` SHA and rebuild all three inputs; do not reuse these
images with a modified harness. GUI, rollback/reverse, Parent/fault, 507,
full-system, physical and USB legs remain NOT RUN. Session 04 remains OPEN.

## 5. Source follow-up — timeout/cleanup repair and bounded retry

This is an append-only correction to the next-step instruction above. No
new Linux VM run occurred on the Mac. The report's actual install/A and
STATUS/VERIFIED results remain tied to `1275e0be1`; healthy B is UNPROVEN.

The test control now uses `UpdatePrivilegedClient` for its panel-supported
operations, inheriting the production finite stage bound of 1,800 seconds.
ARM is intentionally root-only and retains a bounded framed test request;
no production allowlist is broadened. The old helper did one lazy loop detach
and ignored errors. Teardown now uses the repository's scoped unmount/detach
helpers rather than silently accepting leftovers. Actual clearance of the
reported field devices still requires the Linux rerun; source is not VM proof.

The next guide is [`2026-10-26_AB_STAGE_RETRY.md`](../testing/2026-10-26_AB_STAGE_RETRY.md).
It may reuse this report's bundles and accepted-A only when source-path checks
prove shipped/build inputs unchanged, exact published hashes match, the old
first-boot proof passes, and image-holder/loop checks establish offline inputs.
This replaces the blanket requirement to rebuild unchanged images after a
harness-only fix. On any failed prerequisite use the clean three-leg fallback.
Never reuse the failed healthy-update clone or repair guest state.

Source verification ran on the worktree based on `87838b3d6`:

- Final broader source run: **320 tests PASS in 3.556 s**. Selectors:
  `test_x8_qemu.test_product`, `test_product_install`,
  `test_product_boot_health`, `test_product_boot_health_identity`,
  `test_session04_legs`, `test_product_recovery_d31_reverse`, plus
  `test_system_update_service`, `test_parent_system_updates`,
  `test_update_privileged_bridge`, `test_slot_writer`,
  `test_build_loop_cleanup_contract`, `test_build_cleanup_contract`.
- Fresh Luna review: **PASS, no remaining findings** after the unmount failure
  path and executable offline preflight were corrected. The guide selector set
  independently passed **176 tests**.
- Tests execute the generated ARM and STAGE Python against fake sockets,
  assert the actual stage timeout, and cover success-path teardown failure,
  continued detach after unmount failure, mounted-tree preservation and primary
  exception retention. Legacy helper assertions were updated to check exact
  owned resources through the safe helper seam.
- Bash/Python guide syntax checks pass; `make shell-check footprint` passes.
  Separate `make validate` stops at the existing unsupported ARM64 builder.
- Final-source `make verify`: **5,961 tests in 293.848 s; 6 failures, 3 errors,
  9 skips; NOT GREEN**. Failure IDs match the previous Mac results: Foresta
  en/es/fr content expectations (3), MBR wording (1), Parent Wi-Fi assertions
  (2); errors are ARM64 target-builder support (1) and missing macOS `lsblk`
  (2). An earlier pre-final cleanup revision's full run aborted in native
  Pygame/Quattro Amici audio/rendering; it produced no completed-suite result.
  The completed final run above supersedes it for test totals, without making
  the red gate green.

Temporary local logs: `/tmp/greia-stage-followup/`. These checks used mocked
host-resource operations; no Linux image/mount/loop/QEMU run was performed.
The exact 19 devices are field-report evidence, not reproduced instances.
No production source or image producer changed in this tranche.

Owner follow-up: the revised handoff explicitly forbids speculative rebuilds
for host/harness/test-preflight failures and stops after one healthy-update
result. A further Luna contract audit checked guest module availability,
operation allowlists, actual timeout values (VERIFY 60 s, STAGE 1,800 s) and
the documented host phase budget (2,400 s). The 1275 image already passed real
VERIFY under its old 30-second control; the revised guide does not require
another full image build. The generic harness configuration's shorter default
is not used by this work order; preserve the explicit 2,400-second setting.
