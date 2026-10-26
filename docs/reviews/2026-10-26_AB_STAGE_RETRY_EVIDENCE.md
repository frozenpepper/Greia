# A/B healthy-update retry — evidence report

Date: 2026-10-26 · Status: **FAILED — healthy A-to-B not accepted; first
failure at `update-stage`; Session 04 OPEN**

Work order: `docs/testing/2026-10-26_AB_STAGE_RETRY.md`
Source: `abb11b0a0fc999ec536841f02441423546b845fa` (clean `main`)
Reused source: `1275e0be1a9e0cda724ce18151ae65a25f03c98c`
Evidence root: `/var/tmp/greia-ab-stage-abb11b0a0fc999ec536841f02441423546b845fa-20261026T085728Z`

This was the single healthy A-to-B retry authorized after the harness staging
and cleanup fixes. It did not rebuild the OS, install, or run the fault matrix.

## 1. Source and harness preflight

- Changed paths from `1275e0be1..abb11b0a0` are entirely inside the work
  order's allowlist (`tools/x8_qemu/`, `tests/`, `docs/`, `skills/`,
  `HANDOVER.md`). The record is `changed-paths-since-1275.txt`.
- Focused harness selectors: **176 tests, OK** (`focused-source.log`,
  `focused-source.exit=0`). This includes the new stage-timeout and loop
  cleanup delegation tests.
- Host: the same x86_64 Linux/QEMU build host; no host setup failure blocked
  the leg.

## 2. Reuse preflight

- Base bundle hash `b45f0fc7…` and next bundle hash `3ae9cdea…`: **OK**.
- Accepted-A SHA-256 `83d693d915d53e314906fc7e4b319257ba201855121aa1f529f0bf998bf7d1a2`:
  **OK**.
- Prior first-boot JSON validated against the base manifest and current helper
  shape: accepted/default/committed A, accepted journal, schema-1 PERSIST,
  inactive B unchanged, source image unmutated.
- `fuser` holder check: **status 1 (no holders)**. PSmisc 23.7 rejects the
  work order's `fuser -v -- <files>` form with a usage error; the equivalent
  supported `fuser -v <files>` was recorded in
  `image-holders.deviation.txt`.
- The reused bundles were root-owned `0600`; they were changed to `0644` so the
  work order's user-level hash/inspect/JSON checks could read them. Contents and
  hashes were unchanged (`artifact-permissions.*`).
- Loops before the leg: **zero owned associations** (`loops.before.txt`).

## 3. Result

- `update-status`: `STATUS -> OK`
- `update-verify`: `VERIFY_CURRENT_CANDIDATE -> VERIFIED`
- `update-stage`: **`phase update-stage failed (exit 120)`**
- `update-arm`: `ARM_CURRENT_CANDIDATE refused:
  {'reason': 'update transaction is accepted, not staged', 'status': 'REFUSED'}`

The driver recorded `ok: false`, `healthy-a-to-b.exit=1`,
`healthy-a-to-b-tee.exit=0`, and `loop-audit.exit=0`. Accepted A's SHA before
and after is unchanged. The loop audit is empty.

The **first concrete error is the stage failure**, not the arm refusal. The
arm refusal is consistent with no successfully staged transaction and is
downstream of that failure.

## 4. Diagnosis: test-control marker was masked

The stage serial log contains:

```
greia login: x8-control: phase update-stage failed (exit 120); capturing service diagnostics
```

`_control_phase_failure` in `tools/x8_qemu/product.py:1987` looks for a line
that **starts with** `x8-control: phase `. Because the serial login prompt
prefixes the stage marker, the parser did not recognize the stage failure. The
harness therefore booted `update-arm`, where the service correctly refused the
unstaged transaction. This is a **test-control** defect: a failed phase must
stop the leg regardless of a preceding console prompt.

The stage exit code 120 is not the old 30-second test-client timeout. The
immutable base payload's shipped `/opt/greia-os/src/greia_platform/update_client.py`
has the production `STAGE_CURRENT_CANDIDATE` bound of 1800 s
(`base-payload-update-client-timeout.txt`). The stage process exited 120 before
that bound and the captured serial does not contain a traceback or the
service's stage error. The service-journal capture did not flush the stage
detail before the control powered off. The installed updater's stage completion
therefore remains **UNPROVEN**; no production refusal is claimed.

## 5. Evidence boundary and next step

Healthy A-to-B does **not** close: no stage completion, arm, B boot, B health or
final host observation ran. GUI, rollback/reverse, Parent/fault, complete
full-system acceptance, physical and USB remain open. Session 04 stays OPEN.

The next action is a test-control fix, against the same verified inputs, not an
OS rebuild:

1. recognize a phase-failure marker even when a serial/prompt prefix precedes
   `x8-control: phase `, and fail immediately on it;
2. preserve enough of the stage service journal/error line to identify the
   update's first failure before poweroff.

Then authorize one new healthy A-to-B attempt. Do not reuse this failed clone
for another run and do not start the larger fault matrix from this result.

Operational note: the previous run's failed healthy-update clone and control
image were pruned to keep host disk use at the 80% threshold; its result and
serial logs were preserved. This retry's failed clone remains under the new
evidence root.
