# Existing failed A/B image — diagnostic result

Date: 2026-10-26 · Status: **DIAGNOSTIC COMPLETE; installed stage cause
UNRECOVERABLE FROM THIS IMAGE; healthy B UNPROVEN; Session 04 OPEN**

Work order: `docs/testing/2026-10-26_AB_FAILED_IMAGE_DIAGNOSTICS.md`
Collector source: `65cd6212e2e0023d9e6f131d52e24d80396ce66d`
Input image:
`/var/tmp/greia-ab-stage-abb11b0a0fc999ec536841f02441423546b845fa-20261026T085728Z/healthy-a-to-b/product/installed-clone.img`
(size 7,516,192,768 bytes)
Diagnostic output:
`/var/tmp/greia-ab-offline-65cd6212e2e0023d9e6f131d52e24d80396ce66d-20261026T145341Z/image/diagnostics.json`
(SHA-256 `c7f01595ff8633729d9e2e948f40319ebdc56a9e184669b5f494f3af3d709f17`)

Focused diagnostics/handoff suites: **14 tests, OK**. Holder preflight:
`fuser` status 1 with empty output, so the image was offline; no `--` form was
used. Collector exit: **0**; cleanup attempted with loop `/dev/loop37` and
reported **ok**; post-run audit found no owned loop associations.

## Observed facts

- **Slot A** mounted read-only and contains the base release identity:
  `greia-acceptance-fixture-0.13.0-phase0-dev`, role `system-a`, slot `A`.
- **Slot B** mounted read-only, but its
  `/etc/greia-os/release-identity.json` is **missing**. B therefore does not
  contain the next release.
- **PERSIST layout record**: accepted release
  `greia-acceptance-fixture-0.13.0-phase0-dev`, accepted slot `A`, active slot
  `A`; both A and B filesystem/PARTUUID identities are present; slot size
  1,744,830,464 bytes.
- **PERSIST boot journal**: state `accepted`, accepted/candidate slot `A`,
  `first_install: true`, base release, completed first-install/health
  transitions.
- **PERSIST update status**: next release
  `greia-acceptance-fixture-0.13.1-phase0-dev`, bundle SHA
  `3ae9cdeafa6e52459016e1a23315648ee4b8887a314c77c288259c1df4d68aa5`
  (matches the next bundle), state **`received`**, `activation_available:
  false`. Its `bundle_path` is a `/tmp/greia-x8-persist-…` host-mount path
  left by injection.
- `phase-result.json` and `service-diagnostics.txt` are **missing**, as
  expected for this image: it predates durable control diagnostics, and
  journald is volatile.
- Collector `errors`: empty.

## Hypotheses (not established causes)

- The missing B release identity and the status still being `received` are
  consistent with the stage failing before B finalization. The available facts
  cannot distinguish a service refusal, service/control crash, or a lost
  control error before poweroff.
- The source follow-up demonstrates that exit 120 can result from a buffered
  stderr flush to a closed pipe. That is a **possible loss mechanism**, not
  proof of this installed stage's first error.
- The host temporary `bundle_path` in `status.json` is an injection artifact;
  candidate discovery uses the fixed inbox path and already returned
  `VERIFIED`, so this path is not evidence of the stage cause.

## Conclusion

The first stage error is **unrecoverable from this image**. Healthy B is not
acceptance and remains UNPROVEN. Do not format or rebuild anything from this
result. A later bounded diagnostic boot with the corrected capture needs a
separate work order; do not run a blind full retry. Session 04 remains OPEN.

## Follow-up — one captured stage operation, no rebuild

The offline question is answered; repeat reads cannot recover a volatile error
that was not saved. Missing B identity establishes no finalized release identity,
not absence of all candidate payload bytes. A source audit found no supported
capacity, missing-zstd or launcher-readiness explanation: stage probes sysfs
inventory directly, uses the shared capacity/finalization path, and preserves
UPDATE_STAGED across accepted-A boots. No speculative production fix was made.

The next scoped work order is
[`2026-10-26_AB_SINGLE_STAGE_DIAGNOSTIC.md`](../testing/2026-10-26_AB_SINGLE_STAGE_DIAGNOSTIC.md).
The new `tools/x8_qemu/stage_diagnostic.py` clones the verified accepted-A image,
injects the bundle into clone PERSIST offline, injects the corrected control
into A, boots exactly `update-stage` once and always collects the stopped clone.
The control disk is phase-only 64 MiB; host bound is 2,400 seconds above the
existing client stage bound of 1,800 seconds. No install/build/arm/B boot/matrix
is performed. A normal QEMU return is not reported as stage or health acceptance.
The helper preserves raw collector evidence, phase/collector failures and both
inputs' before/after hashes; error and cleanup outcomes propagate to CLI status.

Source evidence on the Mac worktree based on `4bd024410`:

- New helper: **8 tests PASS**, independently rerun/reviewed by Luna with no
  blocking findings. Tests run the real default ProductHarness branch with
  external I/O faked, assert one stage call and its 2,400-second configuration,
  validate actual nested collector schema, collect after stage failure, and
  reject collector errors, failed cleanup or source/bundle mutation.
- Broader integration selectors: **288 tests PASS in 14.295 s**, covering
  stage diagnostic/control/collector/runbook, install/boot-health/identity,
  Session 04, system-update service and production seam composition.
- `make verify`: **5,961 tests in 286.264 s; 6 failures, 3 errors, 9 skips;
  NOT GREEN**. IDs are the previous Mac groups: Foresta en/es/fr (3), MBR
  wording (1), Parent Wi-Fi assertions (2); ARM64 profile support (1 error)
  and missing macOS `lsblk` (2 errors). No full-suite PASS is claimed.
- Separate `make validate` stops at the existing ARM64 builder error;
  `make shell-check footprint`, diff whitespace checks and work-order Bash
  syntax pass. Temporary logs: `/tmp/greia-single-stage-followup/`.

No Linux image build, mount, QEMU boot or update ran here. The actual installed
stage cause and healthy B remain UNPROVEN. Session 04 remains OPEN. The newer
collaboration policy/CODEOWNERS commits were preserved and are exactly allowed
as non-image documentation in the reuse preflight. No production source or
image-build input changed in this follow-up.
