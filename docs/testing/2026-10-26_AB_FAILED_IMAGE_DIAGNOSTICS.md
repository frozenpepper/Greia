# Read the existing failed image — no build or VM retry

Date: 2026-10-26. This is the immediate work order after
[`c387489b5`'s report](../reviews/2026-10-26_AB_STAGE_RETRY_EVIDENCE.md).

**Executed result (2026-10-26, `65cd6212e`):** focused diagnostics/handoff
suites 14 OK; collector exit 0 with cleanup ok. A is the accepted base 0.13.0
slot; B mounted but has no release identity, so B does not contain the next
release; PERSIST still accepts A and update status remains `received`; the old
control's `phase-result.json`/`service-diagnostics.txt` are absent. The first
stage error is unrecoverable from this image. Report:
[`2026-10-26_AB_FAILED_IMAGE_DIAGNOSTICS_RESULT.md`](../reviews/2026-10-26_AB_FAILED_IMAGE_DIAGNOSTICS_RESULT.md).
Do not rebuild or replay blindly; a later bounded diagnostic boot with
corrected capture needs a separate work order.

The stage error was lost, and the control incorrectly continued to arm.
The marker/parser and error capture are corrected in source, but **the actual
installed stage failure is still unknown**. Do not rebuild images, boot QEMU,
replay an update, repair the guest or start a fault matrix in this work order.
Read the existing failed clone first and commit the diagnostic facts.

Run on the same Linux x86_64 host, from current clean `main`. Read `SETUP.md`
and the agent operations manual first. The input below is the failed clone,
not accepted A. Preserve it and the verified bundles. Root-owned `0600`
artifacts remain unchanged; use sudo for reads instead of chmod.

```bash
set -euo pipefail
test "$(git branch --show-current)" = main
git pull --ff-only
test -z "$(git status --porcelain)"
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:. python3 tools/run_tests.py \
  test_x8_qemu.test_diagnostic_handoff test_x8_qemu.test_diagnostics
export FAILED_IMAGE=/var/tmp/greia-ab-stage-abb11b0a0fc999ec536841f02441423546b845fa-20261026T085728Z/healthy-a-to-b/product/installed-clone.img
export DIAG_OUT="/var/tmp/greia-ab-offline-$(git rev-parse HEAD)-$(date -u +%Y%m%dT%H%M%SZ)"
sudo test -s "$FAILED_IMAGE"
test ! -e "$DIAG_OUT"

# PSmisc 23.7 rejects a standalone --. These are absolute file paths.
# Status 1 alone is insufficient: usage errors also use it. Require no output.
command -v fuser >/dev/null
if sudo env LC_ALL=C timeout 10 fuser -v "$FAILED_IMAGE" > /tmp/greia-ab-failed-image-holders.txt 2>&1; then
  echo "Failed image is in use; stop." >&2; exit 1
else
  HOLDER_STATUS=$?
  if (( HOLDER_STATUS != 1 )) || test -s /tmp/greia-ab-failed-image-holders.txt; then
    cat /tmp/greia-ab-failed-image-holders.txt >&2
    echo "Holder check did not prove the image is offline; stop." >&2; exit 1
  fi
fi

mkdir -m 0700 "$DIAG_OUT"
set +e
sudo -E env PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:. python3 \
  -m tools.x8_qemu.diagnostics --image "$FAILED_IMAGE" --output "$DIAG_OUT/image" > "$DIAG_OUT/collector.log" 2>&1
DIAG_STATUS=$?
set -e
printf '%s\n' "$DIAG_STATUS" > "$DIAG_OUT/collector.exit"
git rev-parse HEAD > "$DIAG_OUT/source-head.txt"
cat "$DIAG_OUT/collector.log"
if sudo test -f "$DIAG_OUT/image/diagnostics.json"; then
  sudo cat "$DIAG_OUT/image/diagnostics.json"
else
  echo "Collector produced no JSON; record its first error from collector.log." >&2
  DIAG_STATUS=1
fi
exit "$DIAG_STATUS"
```

The collector attaches the image read-only and mounts A, B and PERSIST with
`ro,noload`; it does not boot, replay filesystem journals or apply updates.
It records slot identities, the existing transaction/layout/status, and any
test-control diagnostics. It attempts all owned cleanup and reports errors.
It does not declare update acceptance. A missing B identity or failed B mount
is a fact to report, not a reason to format or rebuild anything.

The old image predates durable control diagnostics. Its `phase-result.json`
and `service-diagnostics.txt` will normally be absent; production journald is
volatile, so this command cannot recover logs that were never persisted.
Do not claim those missing files explain the stage cause.

Commit a short report with the collector's source SHA, input path, JSON facts,
collector exit/cleanup status and whether B contains the next release. Separate
observed facts from hypotheses. **Stop after the report.** If the first stage
error is unrecoverable, say that explicitly; a later bounded diagnostic boot
needs a separate work order with the corrected capture, not a blind full retry.
