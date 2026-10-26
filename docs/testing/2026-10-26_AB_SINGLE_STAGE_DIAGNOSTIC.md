# One captured stage operation on a fresh clone

**Current next-action handoff:**
[`2026-10-27_UPDATE_AGENT_HANDOFF.md`](2026-10-27_UPDATE_AGENT_HANDOFF.md)
records the reviewed old-release-only reuse decision after language changes.
Use that document; the older procedure below preserves its executed history.
Do not apply its blanket source gate as an extra step after the new handoff.

Date: 2026-10-26. The [offline result](../reviews/2026-10-26_AB_FAILED_IMAGE_DIAGNOSTICS_RESULT.md)
is complete: the original error was not saved and cannot be recovered from
that image. Do not repeat collection from that old clone.

**Latest preflight result (2026-10-26, `81ba47dba`):** **FAILED** at the source
test gate. `test_generated_stage_failure_avoids_exit_120_from_buffered_stderr`
left its positive-control fake server thread alive after
`server.join(timeout=5)` (80 tests: 79 passed, 1 failed). Per this work order,
the one-stage boot was **not** started. The read-only source allowlist, input
hashes, holder and old-loop checks were completed separately and passed. Report:
[`2026-10-26_AB_SINGLE_STAGE_DIAGNOSTIC_PREFLIGHT_FAILURE.md`](../reviews/2026-10-26_AB_SINGLE_STAGE_DIAGNOSTIC_PREFLIGHT_FAILURE.md).
**Source follow-up:** the test fixture is corrected; the final preflight passes
80 tests with parent `PYTHONUNBUFFERED=1`. Rerun the commands below from current
main; if the preflight passes, continue directly with the one diagnostic boot
already scoped here. Do not stop just to request another approval, and do not
rebuild the OS for this tests-only correction.

**Latest source-reuse stop (2026-10-26, `abd9f5045` → continued localization head):** the
80-test preflight passed at `abd9f5045`, but the pull added
`src/greia_platform/languages/en/manifest.json` and `.../it/manifest.json`,
which are production source outside the reuse allowlist. Per the stop rule, the
one-stage boot was **not** started. During push reconciliation main continued
to advance (at last check `ef8eb3415`) with the broader localization implementation (installer/launcher/
platform source and en/es/fr/it manifests), so the source gate is unchanged and
broader. A reviewer must either record an explicit reuse exception or rebuild
the next bundle/image. Report:
[`2026-10-26_AB_SINGLE_STAGE_DIAGNOSTIC_SOURCE_GATE_FAILURE.md`](../reviews/2026-10-26_AB_SINGLE_STAGE_DIAGNOSTIC_SOURCE_GATE_FAILURE.md).

This work order boots **only `update-stage` once**, using the corrected capture.
It reuses accepted A and the next bundle, writes only a fresh disposable clone,
then collects its saved response/error and slot facts automatically. It does
not build images, install, arm, boot B, or run an acceptance/fault matrix.
Stage verifies compatibility internally; separate status/verify boots are
unnecessary. A returned QEMU call does not establish stage or health acceptance.

Use the existing Linux x86_64 host after reading `SETUP.md` and agent operations.
Root-owned input artifacts are read with sudo; keep their permissions/content.
Preserve the old reports, captured diagnostic files, accepted-A image and
verified bundle. A failed check
stops this work order; it does not trigger another build or automatic retry.

## Preflight before the one boot

```bash
set -euo pipefail
test "$(git branch --show-current)" = main
git pull --ff-only
test -z "$(git status --porcelain)"
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:. python3 tools/run_tests.py \
  test_x8_qemu.test_stage_diagnostic test_x8_qemu.test_product \
  test_x8_qemu.test_diagnostics test_x8_qemu.test_diagnostic_handoff

OLD_SOURCE=1275e0be1a9e0cda724ce18151ae65a25f03c98c
SOURCE_HEAD="$(git rev-parse HEAD)"
git merge-base --is-ancestor "$OLD_SOURCE" "$SOURCE_HEAD"
CHANGED_PATHS="$(git diff --name-only "$OLD_SOURCE..$SOURCE_HEAD")"
if printf '%s\n' "$CHANGED_PATHS" | grep -Ev '^(tools/x8_qemu/|tests/|docs/|skills/|HANDOVER\.md$|AGENTS\.md$|CONTRIBUTING\.md$|README\.md$|SETUP\.md$|\.github/CODEOWNERS$)'; then
  echo "Changed path may affect the image; stop and inspect it, do not rebuild blindly." >&2
  exit 1
fi

OLD_EVIDENCE=/var/tmp/greia-ab-smoke-1275e0be1a9e0cda724ce18151ae65a25f03c98c-20261026T014350Z
ACCEPTED_A="$OLD_EVIDENCE/vm/first-boot/product/firstboot-clone.img"
NEXT_BUNDLE="$OLD_EVIDENCE/next-fixture/greia-acceptance-fixture-0.13.1-phase0-dev/updates/acer-aspire-one-i386-ab.greiaupdate"
RUN_ROOT="/var/tmp/greia-ab-stage-only-$SOURCE_HEAD-$(date -u +%Y%m%dT%H%M%SZ)"
mkdir -m 0700 "$RUN_ROOT"
printf '%s\n' "$SOURCE_HEAD" > "$RUN_ROOT/source-head.txt"
printf '%s\n' "$CHANGED_PATHS" > "$RUN_ROOT/changed-paths.txt"
df -h "$RUN_ROOT" > "$RUN_ROOT/free-space.txt"
sudo test -s "$ACCEPTED_A"
sudo test -s "$NEXT_BUNDLE"

command -v fuser >/dev/null
if sudo env LC_ALL=C timeout 10 fuser -v "$ACCEPTED_A" "$NEXT_BUNDLE" > "$RUN_ROOT/image-holders.txt" 2>&1; then
  echo "An input is in use; stop." >&2; exit 1
else
  HOLDER_STATUS=$?
  if (( HOLDER_STATUS != 1 )) || test -s "$RUN_ROOT/image-holders.txt"; then
    cat "$RUN_ROOT/image-holders.txt" >&2
    echo "Holder check failed or produced diagnostics; stop." >&2; exit 1
  fi
fi
sudo losetup --list --noheadings --output NAME,BACK-FILE > "$RUN_ROOT/loops.before.txt"
if grep -F "$OLD_EVIDENCE/" "$RUN_ROOT/loops.before.txt"; then
  echo "Old input/evidence still has attached loops; stop and diagnose." >&2; exit 1
fi
printf '%s  %s\n' 83d693d915d53e314906fc7e4b319257ba201855121aa1f529f0bf998bf7d1a2 "$ACCEPTED_A" | sudo sha256sum -c -
printf '%s  %s\n' 3ae9cdeafa6e52459016e1a23315648ee4b8887a314c77c288259c1df4d68aa5 "$NEXT_BUNDLE" | sudo sha256sum -c -
```

These hashes and accepted-A facts are from the completed `1275e0be1` report
and the subsequent offline work. The additional allowlisted root documents
are collaboration policy, navigation and workstation setup documentation,
not image build inputs. Any
other changed path needs review before reuse. Inspect actual free space for one sparse/reflink clone, the received bundle
and staged B before proceeding. The shared clone helper already uses
`cp --reflink=auto --sparse=always`; raw image length is not allocated size.
If space is the blocker, choose an existing volume with room or remove only
stopped, loop-free old disposable failed clones whose diagnostics have already
been saved. Never delete accepted A or the verified bundle and never rebuild
images merely to resolve host disk pressure.

## Run once and report the saved cause

```bash
set +e
sudo -E env PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:. python3 \
  -m tools.x8_qemu.stage_diagnostic \
  --installed-image "$ACCEPTED_A" --release-bundle "$NEXT_BUNDLE" \
  --output "$RUN_ROOT/run" > "$RUN_ROOT/command.log" 2>&1
DIAG_STATUS=$?
set -e
printf '%s\n' "$DIAG_STATUS" > "$RUN_ROOT/command.exit"
cat "$RUN_ROOT/command.log"
if sudo test -f "$RUN_ROOT/run/result.json"; then
  sudo cat "$RUN_ROOT/run/result.json"
else
  echo "No result JSON: report the first command.log error; do not retry." >&2
  DIAG_STATUS=1
fi
sudo losetup --list --noheadings --output NAME,BACK-FILE > "$RUN_ROOT/loops.after.txt"
if grep -F -e "$OLD_EVIDENCE/" -e "$RUN_ROOT/" "$RUN_ROOT/loops.after.txt"; then
  echo "Owned loop association remains; record cleanup failure." >&2
  DIAG_STATUS=1
fi
printf '%s\n' "$DIAG_STATUS" > "$RUN_ROOT/final.exit"
exit "$DIAG_STATUS"
```

The helper publishes `run/result.json` and
`run/offline-collector/diagnostics.json`, preserving the new clone and serial/
host logs named in `result.logs`. It injects the bundle offline into PERSIST;
the control disk is only 64 MiB. The stage client has its existing 1,800-second
bound inside the 2,400-second host ceiling. No arm command is issued.

In `result.control_evidence`, read `phase-result.json`'s parsed `json` fields:
`error`, `cause_chain` and `response`. Read `service-diagnostics.txt` as well.
Report the first concrete service refusal/exception; do not substitute a later
symptom or infer success from QEMU exit zero. If the boot/collector itself
fails, report that layer with its saved error. The helper collects offline even
after a stage exception and propagates collector and input-preservation errors.

Commit one short report with source SHA, input hashes, command/final exit,
stage response or first error, collector/loop cleanup status and slot/journal
facts. If stage completed, say which facts establish that; **healthy B is still
not tested**. Stop after this report, on either outcome. No automatic rebuild,
rerun, arm, B boot or remaining matrix follows this diagnostic work order.
