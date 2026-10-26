# Single-stage diagnostic — preflight failure

Date: 2026-10-26 · Status: **PREFLIGHT FAILED; one-stage boot NOT RUN;
Session 04 OPEN**

Work order: `docs/testing/2026-10-26_AB_SINGLE_STAGE_DIAGNOSTIC.md`
Source: `81ba47dbafe588d88821ba8892c6a5c31a3a1944` (clean `main`)
Evidence:
`/var/tmp/greia-ab-stage-preflight-81ba47dbafe588d88821ba8892c6a5c31a3a1944-20261026T154759Z/`

The work order's `set -e` preflight stopped at the source-test gate. Per its
instructions, no diagnostic VM boot, image build, install, arm, B boot or
update replay was started.

## 1. Source-test failure

Command:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:. python3 tools/run_tests.py \
  test_x8_qemu.test_stage_diagnostic test_x8_qemu.test_product \
  test_x8_qemu.test_diagnostics test_x8_qemu.test_diagnostic_handoff
```

Result: **80 tests ran, 1 failed, 79 passed** in 6.875 s.

Failing test:
`test_generated_stage_failure_avoids_exit_120_from_buffered_stderr`
(`test_x8_qemu.test_product.ControlSeamTextTests`).

```text
File "tests/test_x8_qemu/test_product.py", line 457, in test_generated_stage_failure_avoids_exit_120_from_buffered_stderr
    positive_code, _positive_record = run_script(positive, positive_root)
File "tests/test_x8_qemu/test_product.py", line 444, in run_script
    self.assertFalse(server.is_alive())
AssertionError: True is not false
```

The failing test is the closed-stderr **positive control**. Its fake server
thread was still alive after `server.join(timeout=5)` when the deliberately
broken-stderr child exited. The test therefore failed before reaching its
child-exit-code assertion and before the fixed-runner assertions. This is a
**test-control race**, not an installed-updater result. Consistent with the
symptom, the fake server can remain blocked in `accept()` if the child exits
before connecting; the exact thread state was not captured.

The new stage-diagnostic module's own tests passed; the failing test is in the
existing product control-seam suite.

## 2. Read-only preflight facts (run separately, no boot)

Because the shell stopped at the failing test, the work order's remaining
preflight commands did not run in sequence. They were completed read-only for
this report:

- Changed paths since `1275e0be1`: all within the work order allowlist;
  `allowlist.exit=0`, no violations.
- Accepted-A SHA-256 `83d693d9…`: **OK**.
- Next-bundle SHA-256 `3ae9cdea…`: **OK**.
- Input holder check: `fuser` status 1 with **empty output** (offline).
- Owned loops under the old evidence root: **0**.

Inputs and permissions were preserved; no artifact was chmodded in this
attempt. No `RUN_ROOT` for the one-stage boot was created, and no
`result.json`/collector output exists for this work order.

## 3. Next step

Fix the positive-control fake-server teardown/join in
`tests/test_x8_qemu/test_product.py` so a child that exits before connecting
cannot leave the helper thread alive. Then rerun the work order's preflight.
Only if it passes should the one `update-stage` diagnostic boot be authorized.
Do not rebuild the OS for this harness-only test failure, do not use the old
offline clone again, and do not infer any stage result from this report.
Session 04 remains OPEN; healthy B remains unproven.
