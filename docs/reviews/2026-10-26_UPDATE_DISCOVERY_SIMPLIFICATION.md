# Package discovery simplification

Date: 2026-10-26. Scope: source on the Mac worktree based on `4de1401fc`.
Owner direction: the uploaded package owns its contents and identity; a
separate status receipt must not be required to recognize it.

## Implemented

- `SystemUpdateServiceAuthority` resolves the fixed inbox candidate directly,
  never a path supplied by status. Candidate summaries read the bounded package
  manifest without hashing the whole payload on polling. Verification/staging
  still inspect the full package and check machine compatibility.
- `SystemUpdateInbox.status_payload` can reconstruct a received view from the
  published package when reporting state is absent, malformed or stale.
  It does not recreate a consumed/missing candidate or publish temporary uploads.
- The QEMU harness no longer rewrites a host-side status path for the guest.
  Normal receive, private ownership/modes and flushing remain.
- Typed `.greia_update` jobs and application-generation recovery are unchanged.
  Their durable job records the parent's install command and lets the OS finish
  independently after transfer; it is not an additional package certificate.

ADR 0036, operator/product guides, operations and the OS work skill now describe
the distinction. No signature or extra admission mechanism was introduced.

## Verification

Independent Luna source review: PASS, no material findings. The reviewer also
ran the 38 service tests and 45 harness tests successfully.

The final focused run passed **327 tests in 10.343 s**, using:

```bash
SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy PYTHONDONTWRITEBYTECODE=1 \
PYTHONPATH=src:tests /opt/anaconda3/bin/python3 tools/run_tests.py \
  test_x8_qemu.test_product test_x8_qemu.test_product_install \
  test_x8_qemu.test_product_boot_health test_x8_qemu.test_session04_legs \
  test_x8_qemu.test_product_boot_health_identity test_system_update_service \
  test_system_updates test_parent_system_updates test_update_privileged_bridge \
  test_update_product_negatives test_update_activation_contract \
  test_software_update_jobs test_software_update_package \
  test_software_update_generation test_software_update_bootstrap \
  test_greia_software_update_tool
```

Coverage includes missing/malformed/stale status, fixed candidate selection,
corrupt and consumed candidates, compatibility before slot contact, unchanged
activation/recovery, lightweight package jobs, and application generations.
An earlier run used the nonexistent selector `test_update_activation`; the final
run above corrected it to `test_update_activation_contract`.

`make verify PYTHON=/opt/anaconda3/bin/python3` completed **5,961 tests in
306.848 s: 6 failures, 3 errors, 9 skips; NOT GREEN** (dummy SDL video/audio,
fault handler and bytecode suppression enabled). Failure/error IDs match the
prior Mac run: Foresta en/es/fr content expectations (3), MBR wording (1),
Parent Wi-Fi assertions (2); ARM64 profile support (1 error), missing macOS
`lsblk` (2 errors). The two added service tests pass; no new failure ID appears.
This does not waive the red gate or claim Linux runtime acceptance.
Separately, `make validate` stops at the existing unsupported ARM64 target-builder
error. `make shell-check footprint` passes. Bash fences and Python heredocs in
the current Linux smoke guide parse successfully. Temporary local logs:
`/tmp/greia-update-simplification/`.

## Linux continuation

No image build, mount, QEMU or physical test ran on this Mac. Session 04 remains
OPEN. Because installed updater source changed, the old `866ba6827` artifacts
cannot prove this fix. Follow
[`2026-10-25_AB_SMOKE_RETRY.md`](../testing/2026-10-25_AB_SMOKE_RETRY.md) from
current committed `main`: build both fixtures and installer, install, first-A
health, healthy A-to-B. Stop at the first failed leg and preserve the report.
Do not repair status or patch the old guest. The candidate-only reuse guide is
historical for this change. Later fault/rollback/device acceptance remains open.

Routine Python/Activity `.greia_update` packages continue to follow
[`GREIA_SOFTWARE_UPDATE_PACKAGES.md`](../development/GREIA_SOFTWARE_UPDATE_PACKAGES.md)
and do not require a full-image rebuild for each application update.
