# Update-testing agent handoff — 2026-10-27

**Status: old-release stage diagnostic PAUSED on current main. Do not start
that diagnostic from this checkout.** The source
reuse review below covered only frozen host source
`78f07861c0ddfad6ed51fb2e1c564d3f95e70115` and guest source
`1275e0be1a9e0cda724ce18151ae65a25f03c98c`. Current main has since changed
the updater/package builder and adds the receiver bridge, so the old source gate
must stop. Do not run its Linux command blocks from current main or bypass that
gate. Current package delivery has its own source and installed acceptance
route in [the language update package acceptance note](2026-10-27_LANGUAGE_UPDATE_PACKAGE_ACCEPTANCE.md).

**Executed result (2026-10-27, reviewed source `78f07861`):** the one
`update-stage` boot was run from an isolated clean checkout of the reviewed
host source against the verified 1275 guest. Preflight and EN/IT/ES/FR checks
passed. The installed updater **refused** `STAGE_CURRENT_CANDIDATE` with
`inactive-slot filesystem is unavailable: block topology observation failed:
slot device capacity is unobservable: sda2`. `phase-result.json` captured the
`ERROR`/`REFUSED` response; no arm or B boot ran. Report:
[`2026-10-27_AB_OLD_RELEASE_STAGE_DIAGNOSTIC_RESULT.md`](../reviews/2026-10-27_AB_OLD_RELEASE_STAGE_DIAGNOSTIC_RESULT.md).
Healthy B remains untested.

**Old-release job:** one captured stage diagnostic was proposed for the
verified existing images, but is now paused because its reviewed host-source
gate does not pass on current main. The historical instructions below are not
executable from current main. Do not rebuild, reinstall, arm, boot B, or repeat
the full update/fault matrix under that paused handoff.

Read `AGENTS.md`, `SETUP.md` and agent operations. This is for the Linux agent
whose previous attempt stopped at the source-reuse gate. If an installer/A-B
job has already started, do not interrupt it or launch a second job; record its
current state instead. No GitHub Actions, packages/models downloads, voice
inference, translation/audio edits, new language promotion or physical deployment.

## What the latest commits answer

- The closed-stderr fixture is fixed: the Linux 80-test preflight passed. The
  next stop was the old blanket source gate, **before any diagnostic boot**.
  See [the source-gate report](../reviews/2026-10-26_AB_SINGLE_STAGE_DIAGNOSTIC_SOURCE_GATE_FAILURE.md).
- Old-image collection already completed: accepted A is intact, B has no
  finalized release identity, status is still received. The original first
  error was not saved and is unrecoverable. Do not repeat that old collection.
  See [the offline result](../reviews/2026-10-26_AB_FAILED_IMAGE_DIAGNOSTICS_RESULT.md).
- Current main has real production localization changes. They are **absent
  from the old images**, not magically validated by this diagnostic.

## Frozen reuse decision for this diagnostic

Reviewed source: `78f07861c0ddfad6ed51fb2e1c564d3f95e70115`.
Old guest/artifact source: `1275e0be1a9e0cda724ce18151ae65a25f03c98c`.

The 19 changed `src/` paths between them are localization-only: installer
entrypoint/i18n; launcher achievement/catalogue/first-profile/feedback/Parent/
usage presentation; platform gallery/language registry; and the four locale
manifest/UI pairs. Updater/client/slot/boot-transaction owners and build,
runtime, Activity and asset inputs are unchanged. The current host helper
injects its **test control** into a new clone; it does not inject new localization
code into the old guest.

The original review permitted one old-release stage diagnostic from that
reviewed source snapshot. That permission does not cover current main: the
changed updater/package files fail the old source-reuse check. Resuming the
diagnostic requires renewed review of the exact host source; do not bypass the
source gate, alter the frozen guest, or respond with a speculative rebuild.

This does **not** waive the current-release gate. A later planned build is
needed to test the improved language implementation in an installed image.
No fresh build is needed to obtain the missing old-release stage error.

## Language support checked in parallel

At the reviewed source, Python 3.12.7 on this Mac passed the five requested
language suites: **13 + 9 + 7 + 19 + 11 = 59 tests**. EN/IT/ES/FR source
checks each reported zero problems. The 80-test update preflight also passed.
The all-scope documentation auditor also inspected 426 Markdown documents
with zero unresolved repository links, and its four tests passed on this review
worktree including this handoff. These are current **source-only** results; the Linux agent records its own
preflight below. Local evidence: `/tmp/greia-current-language-review/` and
`/tmp/greia-agent-handoff-20261027/` (not assumed present on the Linux host).

Offered languages remain `en, it, es, fr`, in that order. Ordinary additional
LTR languages use manifests, UI catalogs and Activity JSON/TOML. The checker
now validates UI schema/types/size and recursively checks nested placeholders;
regression tests cover the earlier validator gaps. Fifth-language tests remain
component/temporary-root tests, not complete rendered/browser/device proof.
Parents browser chrome still has separate client localization work; RTL,
complex-script/font coverage, audio/listening and image acceptance remain
separate. Do not add a fifth production manifest or generate speech here.

## Application-update compatibility fix

The former JSON-delivery blocker is fixed in source. A normal current Python or
combined package carries the complete managed locale manifest/UI snapshot, and
the receiver validates it before generation activation. The frozen 1275-era
receiver still cannot read those paths directly, so it requires the one-time
bridge first. Use it only after confirming the installed application matches
the exact 1275 base. It replaces that full declared Python/runtime snapshot,
with only the package reader and generation validator overlaid; it carries no
current language code or JSON. Never apply it to an arbitrary or newer image.
After it reaches normal applied/health-accepted state, send a current
Python/combined package.

The source-only bridge chain and separate installed acceptance procedure are
in [the language update package acceptance note](2026-10-27_LANGUAGE_UPDATE_PACKAGE_ACCEPTANCE.md).
These package checks do not resume or prove the paused old-release A/B stage
diagnostic above.

## Execute on the existing Linux host

Run these blocks in one Bash session from the repository root. They use the
existing Python environment. The cheap preflight must pass before the one boot;
on failure save the first error and stop, without modifying tests or images.

```bash
set -euo pipefail
test "$(git branch --show-current)" = main
git pull --ff-only
# Keep unrelated untracked files; do not reset, clean or discard work.
git status --short
git diff --quiet
git diff --cached --quiet
if test -n "$(git ls-files --others --exclude-standard -- src tools tests build runtime activities assets)"; then
  echo "Untracked executable/image input may affect the preflight; stop and report it without deleting it." >&2; exit 1
fi
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:. python3 tools/run_tests.py \
  test_x8_qemu.test_stage_diagnostic test_x8_qemu.test_product \
  test_x8_qemu.test_diagnostics test_x8_qemu.test_diagnostic_handoff
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -B tools/check_greia_language.py en
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -B tools/check_greia_language.py it
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -B tools/check_greia_language.py es
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -B tools/check_greia_language.py fr

# This review permits OLD-RELEASE diagnostics, not current-image acceptance.
OLD_SOURCE=1275e0be1a9e0cda724ce18151ae65a25f03c98c
REVIEWED_SOURCE=78f07861c0ddfad6ed51fb2e1c564d3f95e70115
SOURCE_HEAD="$(git rev-parse HEAD)"
git merge-base --is-ancestor "$OLD_SOURCE" "$REVIEWED_SOURCE"
git merge-base --is-ancestor "$REVIEWED_SOURCE" "$SOURCE_HEAD"
CHANGED_PATHS="$(git diff --name-only "$REVIEWED_SOURCE..$SOURCE_HEAD")"
# New documentation/testing changes are allowed after this review. New executable
# or image inputs need review; do not solve a failed check by rebuilding blindly.
if printf '%s\n' "$CHANGED_PATHS" | grep -Ev '^(docs/|tests/|skills/|HANDOVER\.md$|AGENTS\.md$|CONTRIBUTING\.md$|README\.md$|SETUP\.md$|\.github/CODEOWNERS$|\.gitignore$|$)'; then
  echo "Executable/image input changed after the reviewed snapshot; stop for review, not an automatic build." >&2
  exit 1
fi
# Verify the old target's updater and image composition were unchanged at review.
git diff --exit-code "$OLD_SOURCE..$REVIEWED_SOURCE" -- \
  build runtime activities assets \
  'src/greia_platform/*update*.py' 'src/greia_platform/*slot*.py' \
  'src/greia_platform/boot*.py' 'src/greia_platform/grub*.py' \
  src/greia_platform/privileged_channel.py \
  src/greia_platform/persistent_layout.py \
  src/greia_installer/disk.py src/greia_installer/layout.py \
  src/greia_installer/slots.py src/greia_installer/efi_boot.py \
  src/greia_launcher/boot_health.py

OLD_EVIDENCE=/var/tmp/greia-ab-smoke-1275e0be1a9e0cda724ce18151ae65a25f03c98c-20261026T014350Z
ACCEPTED_A="$OLD_EVIDENCE/vm/first-boot/product/firstboot-clone.img"
NEXT_BUNDLE="$OLD_EVIDENCE/next-fixture/greia-acceptance-fixture-0.13.1-phase0-dev/updates/acer-aspire-one-i386-ab.greiaupdate"
RUN_ROOT="/var/tmp/greia-ab-old-release-stage-$SOURCE_HEAD-$(date -u +%Y%m%dT%H%M%SZ)"
mkdir -m 0700 "$RUN_ROOT"
printf '%s\n' "$SOURCE_HEAD" > "$RUN_ROOT/source-head.txt"
printf '%s\n' "$CHANGED_PATHS" > "$RUN_ROOT/changed-paths-after-review.txt"
printf '%s\n' "$OLD_SOURCE" > "$RUN_ROOT/guest-artifact-source.txt"
printf '%s\n' "$REVIEWED_SOURCE" > "$RUN_ROOT/reviewed-host-source.txt"
git diff --name-status "$OLD_SOURCE..$REVIEWED_SOURCE" -- src tools build runtime activities assets > "$RUN_ROOT/reviewed-old-to-current-diff.txt"
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

The input hashes and prior accepted-A facts are from the completed old-release
reports; these fixed hashes remain the input gate. The Mac review did not read
the Linux-host artifacts. This run has three distinct identities: guest payload source
`OLD_SOURCE`, reviewed host tooling source `REVIEWED_SOURCE`, and actual
executed `SOURCE_HEAD`. Record all three; none proves current-language image
acceptance. The critical-owner comparison deliberately excludes the reviewed
language/UI changes, because they are not inserted into the frozen guest.

Inspect actual free space before copying. The clone helper uses sparse/reflink
copy, not a new image build. Keep accepted A and the bundle. If space is tight,
choose an existing volume with room or remove only stopped, loop-free disposable
failed clones whose reports/diagnostics have already been saved. Never delete
inputs or rebuild merely to get past host disk pressure.

## Run the one stage and collect its first cause

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


## Return evidence and stop

Commit `docs/reviews/2026-10-27_AB_OLD_RELEASE_STAGE_DIAGNOSTIC_RESULT.md` with:
actual host/source SHAs and Python version; guest source and both input hashes;
preflight/checker results; command/final exit; the first concrete response/error
from `result.control_evidence` and service snapshot; slot/journal facts; input
before/after hashes and cleanup audit. Distinguish capture/host failures from
an updater refusal. A zero QEMU exit alone is not a stage result.

Even if staging completes, do not arm or boot B in this work order. Record its
supporting facts and stop. This diagnoses **1275-era updater behavior only**;
Session 04, current-language image acceptance and ordinary-family readiness
remain OPEN. Keep the unchanged `.greia_update` Python/Activity route separate:
[package operator guide](../development/GREIA_SOFTWARE_UPDATE_PACKAGES.md).
Routine application updates do not require a full A/B image rebuild.

The application-package/language-data source blocker described in earlier
reports is resolved by the bridge and complete-snapshot route. This old
diagnostic neither tests nor blocks that route; report the two acceptance lanes
separately. Do not try a current Python package on the frozen pre-bridge reader.
