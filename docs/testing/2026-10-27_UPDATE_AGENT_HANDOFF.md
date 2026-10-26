# Update-testing agent handoff — 2026-10-27

**Immediate job:** run one captured **old-release stage diagnostic**, using the
verified existing images. Do not rebuild, reinstall, arm, boot B, or repeat the
full update/fault matrix. Stop after one result.

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

## Explicit reuse decision for this diagnostic

Reviewed source: `78f07861c0ddfad6ed51fb2e1c564d3f95e70115`.
Old guest/artifact source: `1275e0be1a9e0cda724ce18151ae65a25f03c98c`.

The 19 changed `src/` paths between them are localization-only: installer
entrypoint/i18n; launcher achievement/catalogue/first-profile/feedback/Parent/
usage presentation; platform gallery/language registry; and the four locale
manifest/UI pairs. Updater/client/slot/boot-transaction owners and build,
runtime, Activity and asset inputs are unchanged. The current host helper
injects its **test control** into a new clone; it does not inject new localization
code into the old guest.

**Decision: reuse is permitted for diagnosing this old release's stage failure.**
This explicitly resolves the decision requested by the source-gate report.
Do not run the old `1275..HEAD` blanket allowlist as an additional gate here;
use the reviewed-snapshot checks below. Do not broaden an allowlist by hand.
A new post-review executable/image change means stop and report the paths;
it does not authorize a speculative rebuild.

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

## Application-update compatibility blocker — do not trial this combination

**Do not send a current `python_platform` or `combined` package to the old
pre-manifest `1275e0be1` image as a test of the new language implementation.**
This is a source-proven packaging gap, not an invitation to test a likely crash:

- `software_update_package_builder._collect_python_snapshot` selects only `.py`
  files and the fixed `PYTHON_RUNTIME_ALLOWLIST`. The language `manifest.json`
  and `ui.json` files are not included. The package inspector's `_package_path`
  rejects adding these JSON paths by hand.
- Generation staging preserves existing data but cannot invent missing language
  files. Its syntax/root checks do not import the new language registry.
- Updated `system_language.py` loads manifests during import; a pre-manifest
  base has no such directory. The package cannot deliver the required new data.
  Startup would fail; do not rely on a trial/rollback to discover this.

Record this blocker separately. Before application-update testing resumes,
core source work must provide the required bounded language data through the
existing package builder/inspector and validate it before switching generations,
or explicitly establish a compatible base. No manual copying into the guest,
JSON injection outside the inspector, automatic full-image rebuild, or package
format redesign belongs in this diagnostic run. The desired lightweight route
needs to carry its required data; this work order changes no implementation.

A compatible current image may already contain the original four language
folders, but adding a fifth folder through Python packages is also blocked by
the same data-inventory restriction. Edits to existing UI JSON are likewise absent from these Python packages.
Activity-specific JSON/TOML does not replace the platform language manifests. The manifest tests passing on current source
therefore do not establish delivery through application-update packages.

This does not block the **old-release full-system stage diagnostic below**:
its two old frozen images carry their original code/data together and do not
receive the new Python registry. Do not mix these two test questions.

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

Include the application-package/language-data blocker in the returned report.
Do not try a current Python package on an old image to reproduce what the
source already demonstrates. No source-only language result or successful
old-release stage clears that blocker.
