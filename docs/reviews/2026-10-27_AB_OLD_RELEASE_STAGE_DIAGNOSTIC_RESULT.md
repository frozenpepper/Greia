# Old-release A/B stage diagnostic — result

Date: 2026-10-27 · Status: **STAGE REFUSED; DIAGNOSTIC COMPLETE; healthy B
NOT TESTED; Session 04 OPEN**

Work order: `docs/testing/2026-10-27_UPDATE_AGENT_HANDOFF.md`
Executed from the reviewed host source, not current main:
`78f07861c0ddfad6ed51fb2e1c564d3f95e70115` (isolated clean checkout).
Guest/artifact source: `1275e0be1a9e0cda724ce18151ae65a25f03c98c`.
Host: Linux `orbiter` x86_64, Python 3.12.3.
Evidence:
`/var/tmp/greia-ab-old-release-stage-78f07861c0ddfad6ed51fb2e1c564d3f95e70115-20261027T004919Z/`

## Preflight and input gate

- 80-test update preflight (`test_stage_diagnostic`, `test_product`,
  `test_diagnostics`, `test_diagnostic_handoff`): **OK** in 4.183 s.
- `check_greia_language.py` for en/it/es/fr: **0 source/placeholder problems**
  each.
- Reviewed-source gate `78f07861..78f07861`: empty; critical updater/slot/
  boot/build/runtime/activity/asset comparison `1275e0be1..78f07861`: **clean**.
- Accepted-A SHA-256
  `83d693d915d53e314906fc7e4b319257ba201855121aa1f529f0bf998bf7d1a2`: **OK**.
- Next-bundle SHA-256
  `3ae9cdeafa6e52459016e1a23315648ee4b8887a314c77c288259c1df4d68aa5`: **OK**.
- Input holder check: `fuser` status 1 with empty output (offline). No owned
  loops before the run.

## Stage result

The helper attempted exactly one `update-stage` boot and collected the stopped
clone. `command.exit=1`, `final.exit=1`, `stage_outcome=FAILED_OR_NOT_COMPLETED`,
`collector_outcome=COLLECTED`, `collector_errors=[]`.

The first concrete response is a **production updater refusal**, not a capture
or host failure:

```text
operation: STAGE_CURRENT_CANDIDATE
returned_op: ERROR
status: REFUSED
reason: inactive-slot filesystem is unavailable:
        block topology observation failed:
        slot device capacity is unobservable: sda2
```

`phase-result.json` (569 bytes) contains the refusal with an empty `cause_chain`.
`service-diagnostics.txt` shows `greia-system-update.service` active/running,
`Result=success`, `NRestarts=0`; the socket and recovery service are healthy.
There is no service-journal exception beyond the captured refusal.

The control's stage process exited 1 after the refusal, so the boot did not
return a successful stage; no arm command was issued and B was not booted.

## Slot/journal facts after the failed stage

- A: base release `greia-acceptance-fixture-0.13.0-phase0-dev`, role
  `system-a`, slot A.
- B: mounted, but **release identity missing** (no finalized next release).
- PERSIST layout: accepted/active slot A, base release, both A/B partition
  identities present, slot size 1,744,830,464 bytes.
- Boot journal: `accepted`, candidate/accepted slot A, `first_install: true`.
- Update status: next release 0.13.1, state **`received`**, activation
  unavailable.
- Input image and release bundle hashes are unchanged before/after.
- Collector cleanup: attempted, loop `/dev/loop13`, status **ok**; post-run
  owned-loop audit is empty. The clone and logs are preserved under the
  evidence root.

## Interpretation and boundary

This identifies the old-release stage failure as a **slot block-topology
observation refusal** while resolving the inactive slot; the reason names
`sda2` (the active A partition) and an unobservable capacity. It is not the
previous control timeout and not a missing diagnostic capture. The exact
lower-level cause is not specified by the empty `cause_chain`; a focused
old-release slot-topology correction/review would be required before another
stage attempt. Source-path analysis and the recommended read-only probe are in
[`2026-10-27_AB_OLD_RELEASE_STAGE_REFUSAL_ANALYSIS.md`](2026-10-27_AB_OLD_RELEASE_STAGE_REFUSAL_ANALYSIS.md).

This proves only `1275`-era updater behavior on this disposable image. Healthy
B, arm, rollback, current-language image acceptance, full-system/fault matrix
and physical/USB acceptance were not tested. Session 04 remains OPEN. Stop
here; do not automatically rebuild, rerun or arm.
