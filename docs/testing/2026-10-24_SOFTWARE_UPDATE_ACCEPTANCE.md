# Software update package Linux acceptance

> **2026-10-27 UPDATE — DETAILED REFERENCE, NOT THE CURRENT TOP-LEVEL EXECUTION GATE.** Use the [single current update release acceptance guide](GREIA_UPDATE_RELEASE_ACCEPTANCE.md) for the owner's consolidated repair and Linux/QEMU test run. Keep this document's useful Parent API, update generation, negative and fault-test recipes; don't apply its old per-session source freeze, sequential stop orders or historic fixture identities as mandatory gates. Report application-update success separately from A/B success.

**Date:** 2026-10-24
**Status:** UNPROVEN; external Linux-agent handoff
**Authority:** ADR 0038 plus ADR 0036 for full-system A/B behavior
**Operator guide:** [Greia software update packages](../development/GREIA_SOFTWARE_UPDATE_PACKAGES.md)
**Lifecycle plan:** [2026-09-15 multiplatform lifecycle](../plans/2026-09-15_MULTIPLATFORM_RELEASE_INSTALL_UPDATE_COMPLETION.md)

This work order verifies package updates against real installed Greia
services. Source tests, package inspection, a successful HTTP `202`, and a
successful image build are separate evidence from installed Linux acceptance.
Do not use GitHub Actions. Do not build or install on the Mac running this
task. Use another Linux machine with disposable QEMU/KVM guests. Never select
or guess a host `/dev` target. Do not run this procedure on a family device.

## Follow-up after the first Linux run (2026-10-24)

Read `docs/reviews/2026-10-24_SOFTWARE_UPDATE_LINUX_ACCEPTANCE_RESULT.md`
before this retry. Its passed application cases used a manually repaired RC
clone, so they do not establish clean acceptance of the committed ownership
fix. Rebuild and graphically install a fresh RC; do not manually chmod/chown the
guest to make a test pass. On one fresh clone, apply a Python update before
seeding any Parent Activity, then install a distinct Parent Activity through
the ordinary Parent route (the original failing order). On another fresh clone,
seed the Parent Activity first, apply a Parent-source update and a Python/built-in
update, then use ordinary Parent install and uninstall again. Require success
throughout and verify child read access without child write access. Retain the
original failed response and the clean retry's responses.

`test_activity_packages.ActivityPackageServiceTests.test_linux_root_to_greiapanel_store_handoff`
also checks the actual root-to-service-user boundary on Linux when root and the
provisioned accounts are available. Run it in that environment; if it skips,
record SKIP and use the installed Parent/API sequence above for actual identity
proof. Source-only mocks or the macOS skip do not close that predicate.

A/B acceptance uses the explicitly experimental fixture command in §2 and the
companion work order. It does not accept the boot cover for normal releases or
authorize publication. Rebuild next/reverse fixture versions from this same
source; do not reuse old September bundles or the manually repaired RC image.

## Execution order

1. Read prerequisites and freeze source/evidence in §§1 and 8. The host/build
   requirements in §8 apply before any image command.
2. Run the focused and full source gates, build/inspect images and package
   fixtures using §§1–2 and 9.
3. For the next A/B attempt, first execute the clean-source install → first
   boot → healthy A-to-B smoke in
   [`2026-10-25_AB_SMOKE_RETRY.md`](2026-10-25_AB_SMOKE_RETRY.md). It rebuilds
   both fixtures and a clean installer from one SHA. Keep this evidence
   separate from the single-root GUI install/detached boot in §8.
4. After that initial A/B smoke, pair the fresh disposable Parent target; run
   upload, continuation, activation, health and restart predicates in §§3–7.
   Use §9 canaries, §10 A/B harness legs and §11 fault recipes only on
   disposable clones; these remain later gates, not a precondition to the smoke.
5. Record PASS/FAIL/NOT RUN per predicate, with exact artifacts and reason.
   Session 04 remains OPEN until all owned lifecycle gates have evidence.

## 1. Freeze and record the exact source

Start only after package/apply/Parent implementation is committed on `main`.
Record the exact source SHA, Parent HTML runtime pin, Mobile revision, Linux
host/tool versions, installer/package digests and all logs under an evidence
directory outside the checkout. Preserve unrelated untracked media and
outputs. Do not edit source during an acceptance run.

Read `SETUP.md`, `AGENTS.md`, `HANDOVER.md`, the current lifecycle plan, ADRs
0036/0038, the operator guide above, the previous
`2026-10-23_SYSTEM_UPDATE_LINUX_ACCEPTANCE.md` work order and the OS-work skill.
The 2026-10-23 work order owns v3 online/A/B/PERSIST acceptance. Its old
statements that there is no delta/data-only route and that uploads cannot
prepare offline describe only that v3 route; they do not constrain ADR 0038
application packages. For ADR 0038 use this work order and
`docs/development/GREIA_SOFTWARE_UPDATE_PACKAGES.md` as the current route.
From a clean checkout at the recorded SHA, prepare an evidence directory:

```bash
set -euo pipefail
SOURCE_HEAD="$(git rev-parse HEAD)"
RUN_ID="$(date -u +%Y%m%dT%H%M%SZ)"
UPDATE_EVIDENCE="/var/tmp/greia-software-update-$SOURCE_HEAD-$RUN_ID"
export SOURCE_HEAD RUN_ID UPDATE_EVIDENCE
mkdir "$UPDATE_EVIDENCE"
UPDATE_PACKAGE_OUT="$UPDATE_EVIDENCE/packages"
mkdir "$UPDATE_PACKAGE_OUT"
export UPDATE_PACKAGE_OUT
printf '%s\n' "$SOURCE_HEAD" > "$UPDATE_EVIDENCE/source-head.txt"
uname -a > "$UPDATE_EVIDENCE/host.txt"
python3 --version >> "$UPDATE_EVIDENCE/host.txt"
git status --short
test -z "$(git status --porcelain)"
```

Run the repository-wide verification and preserve its exact result:

```bash
set +e
set -o pipefail
make verify 2>&1 | tee "$UPDATE_EVIDENCE/make-verify.log"
VERIFY_PIPE_STATUS=("${PIPESTATUS[@]}")
VERIFY_STATUS="${VERIFY_PIPE_STATUS[0]}"
VERIFY_TEE_STATUS="${VERIFY_PIPE_STATUS[1]}"
set -e
printf '%s\n' "$VERIFY_STATUS" > "$UPDATE_EVIDENCE/make-verify.exit"
printf '%s\n' "$VERIFY_TEE_STATUS" > "$UPDATE_EVIDENCE/make-verify-tee.exit"
```

Run the affected source suite separately even if the repository-wide gate
fails:

```bash
set +e
set -o pipefail
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 tools/run_tests.py \
  test_software_update_package test_greia_software_update_tool \
  test_software_update_generation test_software_update_jobs \
  test_software_update_bootstrap test_parent_update_delivery \
  test_parent_system_updates test_activity_packages \
  test_greia_release test_build_update_index \
  test_image_tmpfiles_identities test_rc_image_contract \
  test_parent_active_index -v \
  2>&1 | tee "$UPDATE_EVIDENCE/software-update-focused.log"
FOCUSED_PIPE_STATUS=("${PIPESTATUS[@]}")
FOCUSED_STATUS="${FOCUSED_PIPE_STATUS[0]}"
FOCUSED_TEE_STATUS="${FOCUSED_PIPE_STATUS[1]}"
set -e
printf '%s\n' "$FOCUSED_STATUS" > "$UPDATE_EVIDENCE/software-update-focused.exit"
printf '%s\n' "$FOCUSED_TEE_STATUS" > "$UPDATE_EVIDENCE/software-update-focused-tee.exit"
if (( FOCUSED_STATUS != 0 || FOCUSED_TEE_STATUS != 0 )); then
  echo "Focused package/update source gate failed; stop before image construction." >&2
  exit 1
fi
if (( VERIFY_TEE_STATUS != 0 )); then
  echo "Could not preserve the full-gate log; stop before image construction." >&2
  exit 1
fi
```

A failure remains a failure; do not weaken test predicates. Latest committed
local full-gate evidence is **5,942 tests, 6 failures, 3 errors, 8 skips** and
NOT GREEN; the six content/message failures and three errors are listed in the
top 2026-10-24 `HANDOVER.md` entry. The earlier 5,890-test run had an
additional retained-surface memory failure (675,948 bytes after 24 launches
against a 524,288-byte bound); it did not recur in the later 5,942-test run.
Keep it as historical watch evidence, not as a current failure. Compare current
failures with the clean-baseline findings in
`docs/reviews/2026-10-23_SYSTEM_UPDATE_IMPLEMENTATION_EVIDENCE.md`; report
exact counts, test IDs and logs. Do not relabel the full gate green because
some outcomes reproduce on baseline.

The focused suite must exit 0 before image construction. If the full gate
fails, compare exact test IDs/messages and counts with the known outcomes in
`HANDOVER.md` and the clean-baseline comparisons in the linked evidence review.
Continue only when there are no additional failures/errors or changed known
failure causes; record the exact status actually observed on this Linux host.
If some known local failures disappear on Linux, that is an improvement and
does not block. Any new failure, increased count, or changed failure cause
stops this run before the first image build. The known baseline is comparison
context, not an accepted PASS or a predicate waiver.

For Linux-specific comparison, also use the committed acceptance result at
`docs/reviews/2026-10-24_SOFTWARE_UPDATE_LINUX_ACCEPTANCE_RESULT.md`: its full run
reported 5,943 tests, 8 failures, 3 errors and 2 skips. It reproduced the
optional voice-module errors, ARM64 error and `morbidi` timing case on a clean
pre-update baseline. Its aggregate-only `piccola_serra` timing failure and the
historical aggregate Shell memory failure remain unresolved watch cases, not
proven baseline passes. Record the exact new host result and do not erase this
uncertainty or claim full-gate/release closure from the focused update suite.
Current follow-up source-gate counts belong in `HANDOVER.md`, not in reused
runtime acceptance claims.

## 2. Build actual disposable images and packages

Build an experimental single-root `legacy-x86-i686-rc` installer without
flashing media:

```bash
sudo -E unshare --mount --propagation private -- \
  bash tools/build-development-installer.sh \
  legacy-x86-i686-rc "$UPDATE_EVIDENCE/single-root-installer"
```

Build a disposable A/B acceptance fixture and matching installer with the
explicit fixture-only command. The report marks this artifact experimental,
the release ID is fixture-specific, and `build_update_index.py` refuses the
report. This exercises current source on a Linux VM; it is not release or
boot-cover acceptance.

```bash
UPDATE_FIXTURE_VERSION="$(cat VERSION)"
UPDATE_FIXTURE_ID="greia-acceptance-fixture-$UPDATE_FIXTURE_VERSION"
sudo -E unshare --mount --propagation private -- \
  python3 tools/greia_release.py doctor --output "$UPDATE_EVIDENCE"
sudo -E unshare --mount --propagation private -- \
  python3 tools/greia_release.py build-acceptance-fixture \
  --version "$UPDATE_FIXTURE_VERSION" \
  --output "$UPDATE_EVIDENCE/acceptance-fixtures"
UPDATE_FIXTURE="$UPDATE_EVIDENCE/acceptance-fixtures/$UPDATE_FIXTURE_ID"
UPDATE_FIXTURE_REPORT="$UPDATE_FIXTURE/release-report.json"
UPDATE_BASE_BUNDLE="$UPDATE_FIXTURE/updates/acer-aspire-one-i386-ab.greiaupdate"
python3 - "$UPDATE_FIXTURE_REPORT" "$UPDATE_FIXTURE_ID" <<'PYCODE'
import json, sys
from pathlib import Path
report = json.loads(Path(sys.argv[1]).read_text())
assert report["artifact_class"] == "experimental_acceptance_fixture", report
assert report["release_eligible"] is False, report
assert report["release_id"] == sys.argv[2], report
PYCODE
python3 tools/greia_release.py inspect "$UPDATE_FIXTURE_REPORT"
python3 tools/greia_update.py inspect "$UPDATE_BASE_BUNDLE"
sudo -E unshare --mount --propagation private -- \
  env PIP_RELEASE_BUILD=0 bash build/build-installer-image.sh acer-aspire-one-i386-ab \
  "$UPDATE_EVIDENCE/ab-installer" --release-bundle "$UPDATE_BASE_BUNDLE"
UPDATE_INSTALLER="$UPDATE_EVIDENCE/ab-installer/greia-os-installer-acer-aspire-one-i386-ab.img"
UPDATE_BASE_RELEASE_ID="$UPDATE_FIXTURE_ID"
export UPDATE_FIXTURE_VERSION UPDATE_FIXTURE_ID UPDATE_FIXTURE UPDATE_FIXTURE_REPORT
export UPDATE_BASE_BUNDLE UPDATE_INSTALLER UPDATE_BASE_RELEASE_ID
sha256sum "$UPDATE_FIXTURE_REPORT" "$UPDATE_BASE_BUNDLE" "$UPDATE_INSTALLER" \
  > "$UPDATE_EVIDENCE/ab-fixture-artifacts.sha256"
```

Use §§8–10 below for the exact single-root route and the 2026-10-23 work
order's A/B lifecycle route. The fixture command composes the actual profile,
shrinks and verifies the actual ext4 payload, derives the payload receipt and
slot minimum, validates the hardware-support archive, and creates the v3
bundle through the existing tools. No production capacity, compatibility,
payload, bundle, installer, layout or boot-health gate is waived. The one
release-specific difference is intentional development composition with
`PIP_RELEASE_BUILD=0`; the production `build` and `build-profile` commands
always set it to `1` and keep the release-safe boot-cover check. Never publish
fixture outputs, never use them on family/physical devices, and never call
their completion release acceptance. Keep the interactive single-root RC
install and automated A/B product harness as separate evidence legs. Never
flash media, select a host block device, or guess a `/dev` target.

Install both targets into separate disposable virtual disks. The single-root
case must be a genuine fresh installed root with the software-update bootstrap
present, not an A/B guest whose slot backend was hidden. For both guests,
record exact runtime facts before testing:

```bash
test "$(cat /etc/greia-os/software-update-bootstrap.json)" = '{"schema_version":1}'
test -x /usr/local/lib/greia-os/software-update-bootstrap.py
systemctl is-enabled greia-software-update-apply.timer
systemctl is-active greia-software-update-recover.service
readlink /opt/greia-os || test -d /opt/greia-os
readlink /usr/share/greia/activity-index-v1.json
df -B1 / /var/lib/greia-os
```

Capture the exact composed-root marker/helper and unit files from each image.
The root helper supports only its installed `--recover` and `--apply` service
modes. Do not invent a manual bootstrap/install command. An older image without
the marker/helper cannot accept a `.greia_update`; document the supported
route used to reach the test image. An already-functional A/B image may use
its ordinary full-system upgrade route. An older single-root image without
the engine requires a logical backup followed by graphical reinstallation and
data restore to a build that contains the bootstrap; the physical target must
be explicitly operator-selected. A package cannot bootstrap its own receiver.
The first migration of a legacy regular `/opt/greia-os` directory happens
through the normal boot-ordered recovery unit. Do not invoke `--recover` while
a child session or application services are live.

Build and inspect all package types using the exact commands in the operator
guide. Include at minimum:

1. A complete `python_platform` package.
2. Built-in `activities` packages with `one`, `set` and all 45 currently
   indexed Activities. For `all`, use the current image's installed-root
   index in the target-specific run; use `--all-current-activities` only for
   the recorded source-roster build.
3. A Parent-source `activities` package updating a disposable Parent Activity
   seeded through the existing Parent Activity route.
4. A `combined` package carrying a Python canary and one built-in Activity.
5. A `full_system` wrapper around a separately built and inspected v3 A/B
   bundle.

For target-specific `all`, mount the disposable installed root read-only on
the Linux build host and use that mount path with the guide's
`--all-from-installed-root` command. Verify both aliases resolve within the
mount before building; never let a host absolute path satisfy the check:

```bash
TARGET_ROOT="$(realpath /mnt/greia-root)"
APP_ROOT="$(realpath "$TARGET_ROOT/opt/greia-os")"
ACTIVITY_INDEX="$(realpath "$TARGET_ROOT/usr/share/greia/activity-index-v1.json")"
case "$APP_ROOT" in "$TARGET_ROOT"/*) ;; *) exit 1 ;; esac
case "$ACTIVITY_INDEX" in "$TARGET_ROOT"/*) ;; *) exit 1 ;; esac
```

Current image composition uses root-relative aliases so these resolutions
remain inside the supplied mounted root. Retain the resolved paths and the
builder's inspect report with the package evidence.

Source-only negative fixture coverage is owned by these named cases in
`tests/test_software_update_package.py`, executed by the focused gate in §1:
`test_invalid_type_fields_path_digest_and_truncated_zip_fail_closed`,
`test_inspector_rejects_runtime_invalid_nested_activity_archive`,
`test_combined_package_is_one_typed_snapshot_and_parent_source_is_rejected`,
`test_full_system_wrapper_revalidates_inner_payload_digest`,
`test_python_tree_walk_error_fails_closed_and_required_entrypoints_are_checked`,
and `test_python_targets_match_exactly_and_default_is_portable`. These are
source-test evidence, not installed-runtime proof. For the separate runtime
negative control, upload a well-formed package for a different exact target
identity to a disposable guest: `inspect` is expected to pass because it has
no installed-device identity. Require receiver compatibility rejection before
any candidate or job is published; retain inspect, identity and before/after
Parent status.

## 3. Test transfer, Parent closure and durable continuation

For each package type, upload through the actual HTML Parent client, then
repeat representative cases through the matching Mobile client. Confirm the
client selects only `.greia_update`, displays bounded receipt progress and
shows the job result after reconnecting.

For at least one Python, one built-in Activity and one Parent Activity package:

1. Start the upload from an authenticated Parent session.
2. Require HTTP `202` only after the whole file has been received and the
   on-disk job is durable (`schema_version=1`, `state=queued`, exact
   `package_bytes=received_bytes`). A partial request must not create a
   published candidate or authorized job.
3. On a dedicated disposable clone, use §11's offline-provisioned one-shot to
   stop Parent after the durable job handoff; cut the clone's QEMU network only
   after recording the HTTP `202`. Never invoke the privileged helper by hand.
4. While Parent is stopped, the authenticated API is unavailable and the
   root-owned job file is not readable through SSH. Retain the host-side `202`,
   test-helper/serial evidence and (after poweroff) §11's offline job copy.
   Restore Parent/network and confirm `GET /api/v1/system/update` reports the
   same `job_id` and terminal state.
5. Repeat on a separate fresh clone with the helper's explicit SIGKILL marker.
   Record systemd restart evidence and prove the accepted job reaches terminal
   state with the same ID across Parent process termination/restart.

Exercise interruption at receive and apply boundaries on separate guest
clones. Kill an upload before its final byte and confirm there is no `202`,
no published `pending` job and no incomplete candidate presented as accepted.
Hard-stop the VM while a package is in `applying` and again while its durable
journal reports application `switching`/`trial`. Cold-boot it, allow the
installed recovery service to run before launcher/Parent, and confirm the
outcome is one complete previous or candidate generation—never a mixed tree.
For root application-generation journal records, retain `base_root_uuid` and
`job_id`; verify the root UUID is the installed root and the job ID matches the
durable package job before that job is finalized or its candidate is cleaned.
Exercise same-boot reconciliation after killing the worker between
`switching` and `trial`; it must reconcile only the same job and matching idle
fence.
Exercise the journaled legacy-directory migration by starting from a
disposable pre-generation root that already contains the new stable bootstrap;
power-cut during its durable `migration_started` window, boot again and prove
that `/opt/greia-os` resolves to one complete recoverable generation before
either application service imports it. If a requested crash window cannot be
reached or observed, mark that predicate NOT RUN rather than substituting a
mocked test as Linux proof.

## 4. Verify each application type on single-root and A/B

Run the application package cases on both installed layouts. Preserve the
same guest before/after; capture the active root pointer, job, apply journal,
service journal, Activity indexes/trust records, profile data, creations,
credentials and settings hashes/semantic values.

### Python platform/launcher

- Apply a real full Python snapshot on the single-root RC guest and A/B guest.
- Verify the code is published through one application-generation pointer
  switch; the update never writes through to the active generation file by
  file.
- Confirm an unchanged asset/config inode is reused where the generation
  implementation hard-links it. Confirm changed Python files are new files
  and no obsolete Python module remains after the complete snapshot.
- Repeat with two newer operator version/release identities, including a
  second update after the first has reached `applied`. Record that the device
  does not impose version ordering; the release process must avoid accidental
  downgrades.
- Seed child saves/creations before apply and verify their hashes and logical
  values remain unchanged.

### Built-in Activity one/set/all

- Apply a `one` package and a `set` package; confirm only listed built-in IDs
  change, the built-in trust class stays built-in, and the built-in index
  changes atomically with the application generation.
- Apply the exact installed-index `all` package. Confirm it includes all 45
  IDs in this baseline, preserves every listed ID, and deletes no unlisted
  or Parent-source Activity.
- Confirm a candidate all-set with a missing or extra ID is rejected before
  activation.

### Parent-source Activity one/set

- Seed one disposable Parent-source Activity through the current ordinary
  Parent Activity route. Apply a Parent-source one-package update, then a
  set-package update with at least two test IDs.
- Verify only the listed Parent IDs change in the active PERSIST generation,
  their trust remains `PARENT_TRUSTED_UNSIGNED`, built-in registrations stay
  untouched, and unlisted Parent Activities and all child data remain intact.
- Confirm `all` is rejected for Parent source and `combined` cannot claim
  Parent trust.

### Combined Python plus built-in Activities

- Apply one combined package and verify the Python code and selected built-in
  Activity/index become visible under the same generation ID.
- Force failure during the pointer/trial boundary on a disposable clone and
  cold-boot. Require recovery to restore the entire previous combined
  generation or accept the entire candidate after fresh readiness; a new
  Python root paired with old Activity/index (or the reverse) is a failure.

## 5. Prove idle activation, fresh health and rollback

Start a child Activity under a real child profile, then queue a Python or
combined package. While the child remains active, require the job to remain
`waiting_for_idle`, the active pointer to remain unchanged, and the child
process/data to remain intact. Return through Greia's real profile picker.
Confirm the updater then obtains the existing profile-session idle fence,
changes the application pointer, starts the new launcher/Parent and records
fresh profile-picker readiness before reporting `applied`. Verify a new child
launch cannot race the pointer switch.
While the child is active, confirm the timer returns after its cheap
session-lock check without hashing, extracting or compiling the package. At
acceptance, retain the post-switch `launcher_interactive_ready` marker and its
monotonic timestamp, plus the loopback Parent `/healthz` HTTP 200 response with
`{"status":"ok"}`. Require the launcher event within 90 seconds and the Parent
health check afterward; failure of either must restore the prior generation
and recheck the old launcher and Parent health.

For rollback, build a disposable full-snapshot package that compiles but causes
launcher startup to fail before fresh profile-picker readiness. Send it only
to a disposable guest. Require the previous generation pointer to be
restored, both launcher and Parent services to return, the durable journal to
record `rolled_back`, and the Parent status to expose the bounded error. Do not
use this fixture on a physical/family device. Run a separate valid candidate
after rollback and confirm the job engine recovers for the next update.

## 6. Prove full-system restart remains explicit and A/B-only

Upload a valid `full_system` package through the same `Upload & install`
action. Require the v3 A/B writer to stage the inactive slot and the package
job to become `ready_to_restart` with `restart_available=true`; the machine
must not restart before the Parent asks. Confirm application package types
never expose `restart_available`.

Use the explicit **Restart & Update** action only after observing the actual
profile picker. Verify the root fence excludes a running child session until
the picker-idle proof, then boots the one-shot inactive slot. Run one healthy
fresh-boot acceptance and one candidate startup failure. Confirm the healthy
slot is accepted only after actual health evidence, the failed candidate
rolls back to the previous accepted slot, and profile data/credentials remain
unchanged. A `.greia_update` full-system wrapper does not allow a single-root
image to activate A/B behavior.

## 7. Storage, repetition and final evidence

On disposable clones, measure low-space behavior separately for Parent
receipt, built-in generation staging and Parent PERSIST Activity staging:

- Before receipt, inadequate free space must refuse with HTTP `507` and no
  package/job publication while preserving the configured 256 MiB receive
  reserve.
- During application staging, insufficient generation/PERSIST space must
  produce a bounded failure and leave the active pointer and all child data
  unchanged. Verify the previous complete generation remains readable.
- After freeing only disposable test space, retry a fresh package and verify
  the updater still works.

Apply at least three sequential application updates (Python, Activity and a
combined package) with a cold reboot between selected steps. Confirm two
generations remain sufficient for current/rollback, obsolete staging files
are bounded/cleaned, the current generation passes readiness and unmodified
assets are reused rather than copied wholesale. Record disk free bytes before
receipt, before generation staging, after apply and after cleanup.

Retain exact commands, package and image SHA-256 values, byte counts, job and
apply-journal snapshots, systemd unit properties/journals, active generation
IDs, Activity indexes/trust receipts, child-data before/after checks and
negative results. Report each predicate as PASS, FAIL or NOT RUN. Keep Session
04 OPEN until these Linux predicates and the earlier blank-disk BIOS GRUB,
PERSIST, A/B→B/A, interruption and rollback requirements in the 2026-10-23
work order are satisfied. Do not claim release acceptance, physical hardware
proof or ordinary-family readiness from this work order alone.

## 8. Linux host and graphical single-root VM

Use an x86_64 Debian/Ubuntu Linux host with root/sudo, QEMU (`qemu-system-i386`
or `qemu-system-x86_64`), `qemu-img`, `curl`, `socat`, Python 3, loop/mount
and `losetup` tools, `mksquashfs`, `unsquashfs`, and the exact GRUB EFI
packages required by the selected image builder. Follow `SETUP.md` §10 and `docs/INSTALLER_IMAGE_CREATION_AND_BOOT.md`
for build prerequisites and host checks. Keep build/evidence storage outside
the checkout, below 80% filesystem utilization before starting, and preserve
the repository's private mount-namespace build procedure. Use `-cpu n270`,
768 MiB and one vCPU for this i386 reference-class guest. If any prerequisite
or host resource bound is missing, stop before composing images.

After §2 has built the RC installer, set these file paths and create a new
file-backed 16 GiB disposable target. This is a QEMU file, never a host
block-device path:

```bash
RC_INSTALLER="$UPDATE_EVIDENCE/single-root-installer/greia-os-installer-legacy-x86-i686-rc.img"
RC_TARGET="$UPDATE_EVIDENCE/single-root-target.img"
QEMU_I386_GUEST="$(command -v qemu-system-i386 || command -v qemu-system-x86_64)"
export QEMU_I386_GUEST
qemu-img create -f raw "$RC_TARGET" 16G
sha256sum "$RC_INSTALLER" "$UPDATE_BASE_BUNDLE" > "$UPDATE_EVIDENCE/single-root-inputs.sha256"
```

Launch the actual installer image with a writable target disk, a GUI display,
serial capture and guest-only network forwards. Launch QEMU with the GUI visible;
keep the launching shell open to retain the recorded PID. Select the second 16
GiB disk in Greia's installer and complete its normal verified-target
confirmation. This is an operator GUI step; no current single-root automation
harness proves it.

```bash
"$QEMU_I386_GUEST" -machine pc,accel=kvm:tcg -cpu n270 -m 768 -smp 1 \
  -drive "file=$RC_INSTALLER,format=raw,snapshot=on,if=ide,index=0" \
  -drive "file=$RC_TARGET,format=raw,if=ide,index=1" \
  -device e1000,netdev=net0 \
  -netdev user,id=net0,hostfwd=tcp::18766-:8766,hostfwd=tcp::2222-:22 \
  -serial "file:$UPDATE_EVIDENCE/single-root-install.serial.log" \
  -display gtk -no-reboot -boot order=c \
  > "$UPDATE_EVIDENCE/single-root-install.qemu.log" 2>&1 &
QEMU_PID=$!
printf '%s\n' "$QEMU_PID" > "$UPDATE_EVIDENCE/single-root-install.qemu.pid"
```

Capture the GUI install and completion screens. Keep this launching shell open;
the GUI is visible while QEMU runs in the background and its PID is recorded. Power off from Greia's
installer completion screen. After the QEMU process exits, run `wait "$QEMU_PID"`
and require `kill -0 "$QEMU_PID"` to fail before reusing the target image. Then
boot only the installed target (the installer image is detached):

```bash
"$QEMU_I386_GUEST" -machine pc,accel=kvm:tcg -cpu n270 -m 768 -smp 1 \
  -drive "file=$RC_TARGET,format=raw,if=ide,index=0" \
  -device e1000,netdev=net0 \
  -netdev user,id=net0,hostfwd=tcp::18766-:8766,hostfwd=tcp::2222-:22 \
  -serial "file:$UPDATE_EVIDENCE/single-root-boot.serial.log" \
  -display gtk -no-reboot -boot order=c \
  > "$UPDATE_EVIDENCE/single-root-boot.qemu.log" 2>&1 &
QEMU_PID=$!
printf '%s\n' "$QEMU_PID" > "$UPDATE_EVIDENCE/single-root-boot.qemu.pid"
```

Wait for the real Greia Shell/profile picker and capture it. The RC development
image provisions the `greia` / `greia` SSH login. The host-forwarded endpoints
are `127.0.0.1:2222` → guest SSH and `127.0.0.1:18766` → guest Parent HTTPS
8766. For read-only guest inspection, use `ssh -p 2222 greia@127.0.0.1` and
the permitted bounded `greia-devctl` interface where available; do not add
generic passwordless sudo or mutate the installed source tree. From a host
browser, open `https://127.0.0.1:18766/`, accept the expected self-signed
certificate warning for this disposable guest, and complete the normal Parent
password/pairing flow. Do not reset or revoke pre-existing credentials; this
target must be fresh and disposable. Use the actual **Upload & install** UI to
choose the host-side `.greia_update` file. If using the CLI route instead,
follow the operator guide's streaming `curl --upload-file` command with a
bearer token obtained through normal pairing and a trusted device certificate;
never disable TLS verification or put credentials in logs/history.

After install, record the guest facts listed in §2 over SSH. If SSH, the GUI,
Parent pairing, or the package capability is absent, stop and record the
observable error; do not substitute the A/B harness or claim installed
single-root acceptance.

The A/B product harness install/first-boot/healthy-update sequence is
automated and has no Parent GUI. For the authenticated Parent package route on
that layout, copy its health-committed output to a new raw image, then boot
that isolated copy with QEMU's GUI and the same port forwards. Do not upload to
the harness evidence image or reuse it for unrelated fault legs:

```bash
AB_ACCEPTED="$UPDATE_EVIDENCE/vm/healthy-update/product/installed-clone.img"
AB_PACKAGE_TARGET="$UPDATE_EVIDENCE/ab-parent-package-target.img"
cp --reflink=auto --sparse=always "$AB_ACCEPTED" "$AB_PACKAGE_TARGET"
AB_ACCEPTED_SHA_BEFORE="$(sha256sum "$AB_ACCEPTED" | awk '{print $1}')"
sha256sum "$AB_ACCEPTED" "$AB_PACKAGE_TARGET" > "$UPDATE_EVIDENCE/ab-parent-target.sha256"
AB_PARENT_LOOP=
cleanup_ab_parent_fixture() {
  if [ -n "$AB_PARENT_LOOP" ]; then
    sudo bash -c 'source build/lib/safe-cleanup.sh; safe_unmount_paths /mnt/greia-ab-parent-a /mnt/greia-ab-parent-b; safe_detach_loop "$1"' _ "$AB_PARENT_LOOP"
  fi
}
trap cleanup_ab_parent_fixture EXIT
LOOP="$(sudo losetup --find --show --partscan "$AB_PACKAGE_TARGET")"
AB_PARENT_LOOP="$LOOP"
lsblk -f "$LOOP" | tee "$UPDATE_EVIDENCE/ab-parent-partitions.txt"
SYS_A_PART="$(sudo lsblk -lnpo NAME,LABEL "$LOOP" | awk '$2 == "GREIA_SYS_A" {print $1}')"
SYS_B_PART="$(sudo lsblk -lnpo NAME,LABEL "$LOOP" | awk '$2 == "GREIA_SYS_B" {print $1}')"
test "$(printf '%s\n' "$SYS_A_PART" | sed '/^$/d' | wc -l | tr -d ' ')" -eq 1
test "$(printf '%s\n' "$SYS_B_PART" | sed '/^$/d' | wc -l | tr -d ' ')" -eq 1
test -b "$SYS_A_PART" && test -b "$SYS_B_PART"
sudo mkdir -p /mnt/greia-ab-parent-a /mnt/greia-ab-parent-b
sudo mount "$SYS_A_PART" /mnt/greia-ab-parent-a
sudo mount "$SYS_B_PART" /mnt/greia-ab-parent-b
for SLOT_ROOT in /mnt/greia-ab-parent-a /mnt/greia-ab-parent-b; do
  DROPIN="$SLOT_ROOT/etc/systemd/system/greia-parent.service.d/90-acceptance-activity-install.conf"
  sudo test ! -e "$DROPIN" && sudo test ! -L "$DROPIN"
  sudo install -d -m 0755 "$(dirname "$DROPIN")"
  sudo tee "$DROPIN" >/dev/null <<'EOF'
[Service]
Environment=GREIA_PARENT_ACTIVITY_INSTALL=1
EOF
  sudo chmod 0644 "$DROPIN"
  sudo grep -Fx 'Environment=GREIA_PARENT_ACTIVITY_INSTALL=1' "$DROPIN"
done
sudo sync
cleanup_ab_parent_fixture
AB_PARENT_LOOP=
trap - EXIT
sha256sum "$AB_ACCEPTED" "$AB_PACKAGE_TARGET" > "$UPDATE_EVIDENCE/ab-parent-target-after-fixture.sha256"
AB_ACCEPTED_SHA_AFTER="$(sha256sum "$AB_ACCEPTED" | awk '{print $1}')"
test "$AB_ACCEPTED_SHA_AFTER" = "$AB_ACCEPTED_SHA_BEFORE"
"$QEMU_I386_GUEST" -machine pc,accel=kvm:tcg -cpu n270 -m 768 -smp 1 \
  -drive "file=$AB_PACKAGE_TARGET,format=raw,if=ide,index=0" \
  -device e1000,netdev=net0 \
  -netdev user,id=net0,hostfwd=tcp::18766-:8766,hostfwd=tcp::2222-:22 \
  -serial "file:$UPDATE_EVIDENCE/ab-parent.serial.log" \
  -display gtk -no-reboot -boot order=c \
  > "$UPDATE_EVIDENCE/ab-parent.qemu.log" 2>&1 &
QEMU_PID=$!
printf '%s\n' "$QEMU_PID" > "$UPDATE_EVIDENCE/ab-parent.qemu.pid"
```

The A/B product profile does not carry the developer-remote marker, so
`GREIA_PARENT_ACTIVITY_INSTALL` defaults off and Parent-source seeding would
otherwise correctly return HTTP 403. The bounded offline drop-in above enables
the existing install/remove capability only on this disposable copy; it adds
no SSH, sudo, API privilege, or image-wide default. Both initial slot roots
receive the same drop-in. A later full-system update replaces a slot root and
may remove this test-only file: run Parent-store application cases before the
full-system cases, or prepare another disposable copy and recheck the
capability. An expected capability-disabled HTTP 403 is not an ownership
failure. The untouched `AB_ACCEPTED` image remains the source evidence. Record
both hashes, the two `GREIA_SYS_*` labels, and the drop-in contents. The
`ab-parent-target-after-fixture.sha256` row for `AB_ACCEPTED` must equal its
before value; if it does not, stop and preserve the evidence.

Use the GUI profile picker and normal Parent password/pairing flow. Before
seeding, require the Parent Activity capability to report `activities.install`
true; if it is absent, stop and record the observed response rather than
proceeding to an expected 403. Then seed the disposable Parent Activity via
the ordinary Parent Activity upload/install UI and perform the A/B
application-package cases in §§3–5. If this non-developer A/B image exposes no
guest SSH or local Parent panel, the host-forwarded HTTPS browser route remains
the expected path. Do not enable SSH or alter pairing privileges to collect
root-owned updater records; use the online authenticated Parent status for job
state and the offline clone evidence route in §11 for root-only files. Discard
the patched `AB_PACKAGE_TARGET` after this test; do not copy its drop-in into a
production profile, release image, or other acceptance image.

## 9. Valid and startup-failure application canaries

Build one ordinary full Python snapshot from the exact checkout using the
operator-guide command in §2. Build a second, structurally valid startup-fail
fixture from a disposable source copy. The added statement is valid Python and
causes the launcher package import to fail; the production checkout remains
untouched.

```bash
CANARY_ROOT="$UPDATE_EVIDENCE/startup-failure-source"
mkdir -p "$CANARY_ROOT"
cp -a src runtime "$CANARY_ROOT/"
printf '\nraise RuntimeError("Greia update startup-failure acceptance canary")\n' \
  >> "$CANARY_ROOT/src/greia_launcher/__init__.py"
CANARY_VERSION="0.14.1-startup-failure-canary"
CANARY_RELEASE_ID="greia-app-0.14.1-startup-failure-canary"
python3 tools/greia_software_update.py build-python-platform \
  --version "$CANARY_VERSION" --release-id "$CANARY_RELEASE_ID" \
  --source-root "$CANARY_ROOT" \
  --output "$UPDATE_PACKAGE_OUT/startup-failure.greia_update"
python3 tools/greia_software_update.py inspect \
  "$UPDATE_PACKAGE_OUT/startup-failure.greia_update" \
  > "$UPDATE_EVIDENCE/startup-failure.inspect.json"
sha256sum "$UPDATE_PACKAGE_OUT/startup-failure.greia_update" \
  > "$UPDATE_EVIDENCE/startup-failure.sha256"
```

Inspect must PASS before upload. Upload this fixture only to a fresh disposable
single-root VM clone after preserving the known-good target copy. Wait for the
actual post-switch launcher readiness failure and require the old generation
pointer to return, the job to become `rolled_back` or the documented bounded
startup failure state, and both launcher and Parent health to recover. Record
the job, generation pointer/journal before and after, systemd status/journal,
and child-data hashes. Do not accept a result merely because the package
uploaded or its outer digest passed. Then upload the ordinary valid full
snapshot and confirm a later job succeeds after rollback.

Run the concrete partial-stream, durable-202 Parent-stop, and observed-applying
power-cut recipes in §11. Those recipes establish only their stated observations;
they do not establish an unobserved `switching`/`trial` journal cut or every
internal fsync boundary. Mark only the exact unreachable phase NOT RUN.

## 10. A/B product-harness calls and unsupported fault controls

The A/B product harness is source-owned at `tools/x8_qemu/product.py`; it has
no command-line entry point. The 2026-10-23 work order §3 contains the current
exact inline Python runner for `ProductHarness.run_product`, first boot and
healthy B update. Run it with no fake callbacks. Its install leg masks the
graphical installer in a disposable clone and drives the shipped installer
socket: this is automated installer/service and disk-parser proof, **not**
graphical installer review. The interactive single-root procedure in §8 is a
separate GUI proof. Keep the A/B evidence under a separate output directory.

For A/B failure legs, after the §3 runner has produced
`vm/healthy-update/product/installed-clone.img`, run this real-fixture driver
from the repository root. It extracts the accepted B release's actual payload
and hardware-support member, invokes the source-owned candidate builders with
their required keyword arguments, inspects the bundles, and gives each
`ProductHarness` leg a unique output directory. It never supplies fake
callbacks. Run it under the same `sudo -E env ... python3` boundary as the §3
runner:

Before the 2026-10-23 §3 runner, follow its §2 recipe to build a distinct
second healthy release and set `UPDATE_NEXT_BUNDLE` to its exact v3 bundle.
Before this failure driver, build one further distinct, monotonically newer
release using that same disposable-checkout procedure and export its exact
bundle as `UPDATE_REVERSE_BUNDLE`. Inspect all three release IDs and versions;
do not reuse an older bundle as the reverse update.

```bash
sudo -E env PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:tests:. python3 - <<'PYCODE'
import hashlib, json, os, shutil, subprocess, zipfile
from pathlib import Path
from tools.x8_qemu.lifecycle import LifecycleConfig
from tools.x8_qemu.product import (
    ProductHarness, build_nonbooting_candidate_bundle,
    build_unhealthy_candidate_bundle,
)
from tools.x8_qemu.gate_p5 import prepare_on_image_d31_seed
from greia_platform.system_updates import build_update_bundle, inspect_update_bundle

evidence = Path(os.environ["UPDATE_EVIDENCE"])
root = evidence / "vm"
base = root / "healthy-update/product/installed-clone.img"
accepted_bundle = Path(os.environ["UPDATE_NEXT_BUNDLE"])
accepted = inspect_update_bundle(accepted_bundle).manifest
work = root / "failure-fixtures"
work.mkdir(parents=True, exist_ok=True)
payload_zst = work / "accepted-payload.ext4.zst"
hardware = work / "accepted-hardware-support.tar.zst"
with zipfile.ZipFile(accepted_bundle) as archive:
    with archive.open("payload.ext4.zst") as source, payload_zst.open("wb") as sink:
        shutil.copyfileobj(source, sink, length=1024 * 1024)
    if "hardware-support.tar.zst" not in archive.namelist():
        raise SystemExit("BLOCKED: accepted v3 bundle lacks hardware-support.tar.zst")
    with archive.open("hardware-support.tar.zst") as source, hardware.open("wb") as sink:
        shutil.copyfileobj(source, sink, length=1024 * 1024)
payload = work / "accepted-payload.ext4"
subprocess.run(["zstd", "-d", "-f", "-o", str(payload), str(payload_zst)], check=True)
common = dict(
    base_payload=payload, base_hardware_support=hardware,
    platform_family=accepted.platform_family, architecture=accepted.architecture,
    profile=accepted.profile, board=accepted.board,
)
unhealthy_id = accepted.release_id + "-userspace-failure"
nonboot_id = accepted.release_id + "-nonboot-failure"
unhealthy_info = build_unhealthy_candidate_bundle(
    **common, output_path=work / "unhealthy.greiaupdate",
    work_dir=work / "unhealthy-work", release_id=unhealthy_id)
nonboot_info = build_nonbooting_candidate_bundle(
    **common, output_path=work / "nonboot.greiaupdate",
    work_dir=work / "nonboot-work", release_id=nonboot_id)
refusal_id = accepted.release_id + "-persist-refusal"
refusal = work / "persist-refusal.greiaupdate"
refusal_manifest = build_update_bundle(
    payload_path=payload_zst, hardware_support_path=hardware,
    output_path=refusal, version=accepted.version + "-persist-refusal",
    release_id=refusal_id, platform_family=accepted.platform_family,
    architecture=accepted.architecture, profile=accepted.profile,
    board=accepted.board, payload_uncompressed_bytes=accepted.payload_uncompressed_bytes,
    minimum_slot_bytes=accepted.payload_minimum_slot_bytes,
    persist_read_schema_min=2, persist_read_schema_max=2,
    persist_write_schema=2, release_notes="Disposable PERSIST schema refusal fixture.")
for path in (Path(unhealthy_info["bundle"]), Path(nonboot_info["bundle"]), refusal):
    inspect_update_bundle(path)
def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()

fixture_paths = (Path(unhealthy_info["bundle"]), Path(nonboot_info["bundle"]), refusal)
(work / "fixture-report.json").write_text(json.dumps({
    "accepted_release_id": accepted.release_id,
    "fixtures": [{"path": str(path), "bytes": path.stat().st_size,
                  "sha256": sha256(path)}
                 for path in fixture_paths],
}, indent=2) + "\n")

def harness(name):
    return ProductHarness(LifecycleConfig(
        output_dir=root / name, timeout_seconds=1200,
        memory_mib=1024, cpus=1, keep_image=True), official_image=base)

def save(name, result):
    destination = root / name
    destination.mkdir(parents=True, exist_ok=True)
    (destination / "result.json").write_text(json.dumps(result, indent=2) + "\n")
    if result.get("ok") is not True:
        raise SystemExit(f"FAIL: {name}: {result}")

save("userspace-failure", harness("userspace-failure").run_userspace_failure_product(
    installed_image=base, unhealthy_bundle=Path(unhealthy_info["bundle"]),
    accepted_release_id=accepted.release_id, candidate_release_id=unhealthy_id))
save("nonboot-failure", harness("nonboot-failure").run_nonboot_failure_product(
    installed_image=base, nonboot_bundle=Path(nonboot_info["bundle"]),
    accepted_release_id=accepted.release_id, candidate_release_id=nonboot_id))
save("persist-refusal", harness("persist-refusal").run_persist_refusal_product(
    installed_image=base, refused_bundle=refusal,
    accepted_release_id=accepted.release_id))
reverse_bundle = Path(os.environ["UPDATE_REVERSE_BUNDLE"])
reverse = inspect_update_bundle(reverse_bundle).manifest
d31_source = root / "d31-source.img"
subprocess.run(["cp", "--reflink=auto", "--sparse=always", str(base), str(d31_source)], check=True)
recovery_name = "recovery-d31-reverse"
recovery_root = root / recovery_name
seed = prepare_on_image_d31_seed(
    installed_image=d31_source,
    recovery_clone=recovery_root / "product/recovery-clone.img",
    work_dir=root / "d31-seed-work")
save(recovery_name, harness(recovery_name).run_recovery_d31_reverse_product(
    installed_image=d31_source,
    unhealthy_bundle=Path(unhealthy_info["bundle"]),
    reverse_bundle=reverse_bundle, accepted_release_id=accepted.release_id,
    candidate_release_id=unhealthy_id, reverse_release_id=reverse.release_id,
    d31_fn=seed["d31_fn"]))
PYCODE
```

The refusal fixture above sets schema read/write to 2 while the accepted
profile uses schema 1; it remains a structurally valid v3 bundle. Build
`UPDATE_REVERSE_BUNDLE` as a third real release with a unique newer release
ID before this driver; do not use an older package as the reverse release.
The driver seeds D31 through the existing `prepare_on_image_d31_seed` API and
preserves the unmodified healthy image in its prior evidence path. If the real
PERSIST mapping cannot be observed, that API deliberately returns BLOCKED; do
not invent a mapping or success-shaped report. Record each harness JSON
result, serial/host logs and all generated image/bundle hashes.

Use §11's bounded, file-backed disposable-clone recipe for the real Parent
receive-reserve HTTP 507 predicate. It does not fill the host filesystem and
restores the clone before retry. Generation/PERSIST staging low-space predicates
remain distinct: record NOT RUN unless the exact staging failure is safely
induced and observed. These limits leave Session 04 OPEN and are not waivers.


## 11. Fault recipes on disposable raw-disk clones

The existing Linux shell variables from §§1–2 remain in scope. Choose a real
inspected package and trusted certificate/token from normal pairing; never save
the bearer token in evidence. The examples use the single-root raw target. For
A/B, set `VM_ORIGINAL` to a stopped copy of the harness-installed raw image and
use the A/B PERSIST backing path below.

```bash
set -euo pipefail
FAULT_EVIDENCE="$UPDATE_EVIDENCE/faults"
VM_ORIGINAL="$UPDATE_EVIDENCE/single-root-target.img"
PACKAGE="$UPDATE_PACKAGE_OUT/python-platform.greia_update"
GUEST=127.0.0.1
PARENT_PORT=18767
SSH_PORT=2223
GREIA_DEVICE_CERT="$UPDATE_EVIDENCE/parent.crt"  # trusted cert copied after normal pairing
mkdir -p "$FAULT_EVIDENCE"
sha256sum "$VM_ORIGINAL" "$PACKAGE" > "$FAULT_EVIDENCE/input.sha256"
stat -c '%n %s bytes' "$PACKAGE" > "$FAULT_EVIDENCE/package-size.txt"
read -rsp 'Parent bearer token: ' GREIA_PARENT_TOKEN; printf '\n'; export GREIA_PARENT_TOKEN
export FAULT_EVIDENCE VM_ORIGINAL PACKAGE GUEST PARENT_PORT SSH_PORT GREIA_DEVICE_CERT
```

Before copying or mounting a guest image, shut it down and verify its recorded
QEMU PID has exited (`wait "$QEMU_PID"`, then require `kill -0 "$QEMU_PID"`
to fail). If the VM was launched from a previous terminal, read its recorded
PID file and verify that process has exited before proceeding. Never copy or mount a live raw disk. Create each fault leg from the
original stopped image; discard mutated clones after retaining evidence:

```bash
cp --reflink=auto --sparse=always "$VM_ORIGINAL" "$FAULT_EVIDENCE/partial-upload.img"
cp --reflink=auto --sparse=always "$VM_ORIGINAL" "$FAULT_EVIDENCE/applying-cut.img"
cp --reflink=auto --sparse=always "$VM_ORIGINAL" "$FAULT_EVIDENCE/low-space-507.img"
cp --reflink=auto --sparse=always "$VM_ORIGINAL" "$FAULT_EVIDENCE/parent-stop.img"
sha256sum "$FAULT_EVIDENCE/"*.img > "$FAULT_EVIDENCE/clone-inputs.sha256"
```

### QEMU monitor, VM stop and network-cut mechanism

Use this launcher for each raw clone; the name gives its monitor/serial/PID
artifacts unique paths. Keep this Linux-host shell open while the guest runs:

```bash
start_fault_vm() {
  local disk="$1" name="$2"
  "$QEMU_I386_GUEST" -machine pc,accel=kvm:tcg -cpu n270 -m 768 -smp 1 \
    -drive "file=$disk,format=raw,if=ide,index=0" \
    -device e1000,id=greianic,netdev=net0 \
    -netdev user,id=net0,hostfwd=tcp::18767-:8766,hostfwd=tcp::2223-:22 \
    -serial "file:$FAULT_EVIDENCE/$name.serial.log" \
    -display gtk -no-reboot \
    -monitor "unix:$FAULT_EVIDENCE/$name.monitor,server,nowait" \
    > "$FAULT_EVIDENCE/$name.qemu.log" 2>&1 &
  QEMU_PID=$!
  printf '%s\n' "$QEMU_PID" > "$FAULT_EVIDENCE/$name.qemu.pid"
}
start_fault_vm "$FAULT_EVIDENCE/partial-upload.img" partial-upload
```

Abrupt power cut (do not use ACPI powerdown):

```bash
printf 'quit\n' | socat - "UNIX-CONNECT:$FAULT_EVIDENCE/applying-cut.monitor"
wait "$QEMU_PID"
if kill -0 "$QEMU_PID" 2>/dev/null; then echo 'QEMU still running; do not copy/mount' >&2; exit 1; fi
```

Use the same `quit`, `wait "$QEMU_PID"` and `kill -0` check after each fault
clone before copying or mounting it. While a clone is running, the host shell
that launched it waits at the final `wait`; use a second host terminal for HMP
commands, then the original shell resumes and confirms process exit. To cut network after a durable `202`, while leaving the guest up, first inspect HMP's exact NIC frontend name, then disable it (normally `e1000.0`; use the observed name):

```bash
printf 'info network\n' | socat - "UNIX-CONNECT:$FAULT_EVIDENCE/parent-stop.monitor"
printf 'set_link greianic off\n' | socat - "UNIX-CONNECT:$FAULT_EVIDENCE/parent-stop.monitor"
printf 'info network\n' | socat - "UNIX-CONNECT:$FAULT_EVIDENCE/parent-stop.monitor"
```

Retain before/after monitor output showing the frontend link down; the queued job can continue offline. A client disconnect alone is not a Parent stop.

### Partial upload: prove no HTTP 202, candidate, or queued job

Use a fresh clone with normal pairing/token and trusted guest certificate. Start the fresh clone with `start_fault_vm "$FAULT_EVIDENCE/partial-upload.img" partial-upload`. This streams the real package at a capped rate, then curl aborts it before completion; it does not edit guest files or fabricate a job. The trusted certificate contains `greia.local`; `--resolve` keeps TLS hostname validation enabled while reaching the forwarded port. Keep credentials out of shell history and saved logs. Run from Linux host, with the corresponding VM on `18767`:

```bash
PKG_BYTES=$(stat -c %s "$PACKAGE")
test "$PKG_BYTES" -gt 65536
set +e
curl --max-time 2 --limit-rate 4096 --silent --show-error \
  --request POST --upload-file "$PACKAGE" \
  --header "Authorization: Bearer ${GREIA_PARENT_TOKEN}" \
  --header 'Content-Type: application/vnd.greia.software-update+zip' \
  --cacert "$GREIA_DEVICE_CERT" --resolve greia.local:18767:127.0.0.1 \
  --dump-header "$FAULT_EVIDENCE/partial-response.headers" \
  --output "$FAULT_EVIDENCE/partial-response.body" \
  https://greia.local:18767/api/v1/system/update/package
CURL_STATUS=$?
set -e
printf 'curl_exit=%s package_bytes=%s\n' "$CURL_STATUS" "$PKG_BYTES" \
  > "$FAULT_EVIDENCE/partial-response.result"
```

Exit 28 from curl's 2-second transfer cap is expected; retain response headers/body and require they contain no HTTP `202`. Then GET authenticated status and save the JSON:

```bash
curl --fail --silent --show-error \
  --header "Authorization: Bearer ${GREIA_PARENT_TOKEN}" \
  --cacert "$GREIA_DEVICE_CERT" --resolve greia.local:18767:127.0.0.1 \
  https://greia.local:18767/api/v1/system/update \
  > "$FAULT_EVIDENCE/partial-status.json"
```

Require no new software-update job ID. Stop the clone with HMP and wait for its recorded PID:

```bash
printf 'quit\n' | socat - "UNIX-CONNECT:$FAULT_EVIDENCE/partial-upload.monitor"
wait "$QEMU_PID"
if kill -0 "$QEMU_PID" 2>/dev/null; then echo 'QEMU still running; do not inspect disk' >&2; exit 1; fi
```

Then do offline root/state inspection below, and require no `candidate.greia_update`, `pending`, or queued job. Record any stale prior state; use a known-clean clone if one exists. Curl's timeout alone is not PASS; offline state must show no candidate, pending marker, or queued job, and any captured response must not contain `202`.

### Observed `applying` power cut and offline root-owned evidence extraction

Start a fresh applying-cut clone with `start_fault_vm "$FAULT_EVIDENCE/applying-cut.img" applying-cut`. Upload a valid package through Parent and poll the real authenticated `GET /api/v1/system/update` response at short intervals, saving each JSON response. The observation predicate is the actual `software_update.job.state == "applying"`; only after seeing and saving that exact response, issue monitor `quit` immediately. If the state changes before `quit`, or is never observed, mark this fault NOT RUN. Cold boot the same clone normally by calling `start_fault_vm "$FAULT_EVIDENCE/applying-cut.img" applying-cut-recovery`; recovery must run before launcher/Parent. Capture the second serial log, `greia-devctl status` and Parent status after boot. The image configures journald `Storage=volatile`, so a hard power cut may erase post-cut journal history; do not rely on it for the cut point. A post-boot `greia-devctl logs --service parent --lines 500` is supplemental only. Read-only SSH commands are limited to the documented bounded `greia-devctl` verbs; never invoke bootstrap helper manually.

For root-owned mode-0600 evidence, power off the guest first. On Linux host, identify partitions from this image's own partition table (`lsblk -f`, `fdisk -l`); attach **the raw image file** as a loop device and mount the identified partitions read-only. For A/B, `/var/lib/greia-os` is the PERSIST bind source `/greia/namespaces/parent-credentials` on the PERSIST filesystem mounted at `/run/greia-persist`; for single-root, use the installed root filesystem unless its recorded mount layout says otherwise. Do not assume a partition number:

```bash
# Preserve the power-cut clone: inspect a new raw copy so ext4 mount journal
# replay, if any, cannot change the evidence source used for cold-recovery boot.
INSPECTION_IMAGE="$FAULT_EVIDENCE/applying-cut-inspect.img"
cp --reflink=auto --sparse=always "$FAULT_EVIDENCE/applying-cut.img" "$INSPECTION_IMAGE"
LOOP=$(sudo losetup --find --show --partscan "$INSPECTION_IMAGE")
install -d -m 0700 "$FAULT_EVIDENCE/evidence/applying-cut"
lsblk -f "$LOOP" | tee "$FAULT_EVIDENCE/evidence/applying-cut/partitions.txt"
# Set ROOT_PART and STATE_PART only from this output; never reuse host devices.
sudo mkdir -p /mnt/greia-cut-root /mnt/greia-cut-state
LAYOUT=single-root # choose exactly: single-root or ab from this imagedisk
if [ "$LAYOUT" = single-root ]; then
  sudo mount -o ro "$ROOT_PART" /mnt/greia-cut-root
  STATE_MOUNT=/mnt/greia-cut-root/var/lib/greia-os
elif [ "$LAYOUT" = ab ]; then
  sudo mount -o ro "$ROOT_PART" /mnt/greia-cut-root
  sudo mount -o ro "$STATE_PART" /mnt/greia-cut-state
  STATE_MOUNT=/mnt/greia-cut-state/greia/namespaces/parent-credentials
else
  echo "Unknown layout; stop without mounting" >&2; exit 1
fi
UPDATE_DIR="$STATE_MOUNT/software-updates"
sudo test -d "$UPDATE_DIR"
sudo blkid "$ROOT_PART" > "$FAULT_EVIDENCE/evidence/applying-cut/root-uuid.txt"
sudo readlink -v /mnt/greia-cut-root/opt/greia-os \
  > "$FAULT_EVIDENCE/evidence/applying-cut/active-root-pointer.txt" 2>&1 || true
```

Extract without changing guest bytes; host root is needed to read job/candidate modes. Keep provenance and original mode/ownership metadata:

```bash
install -d -m 0700 "$FAULT_EVIDENCE/evidence/applying-cut"
STATE_ROOT="$UPDATE_DIR"
sudo find "$UPDATE_DIR" -maxdepth 1 -type f \
  \( -name job.json -o -name pending -o -name candidate.greia_update -o -name apply-journal.json \) \
  -exec stat -c '%n %a %u:%g %s' {} \; \
  -exec cp --preserve=mode,ownership,timestamps {} "$FAULT_EVIDENCE/evidence/applying-cut/" \;
sudo stat -c '%n %a %u:%g %s' "$STATE_ROOT/apply-journal.json" 2>/dev/null || true
sudo cp --preserve=mode,ownership,timestamps "$STATE_ROOT/apply-journal.json" \
  "$FAULT_EVIDENCE/evidence/applying-cut/apply-journal.json" 2>/dev/null || true
sudo bash -c 'sha256sum "$1"/*' _ "$FAULT_EVIDENCE/evidence/applying-cut" | \
  sudo tee "$FAULT_EVIDENCE/evidence/applying-cut.sha256" >/dev/null
sudo bash -c 'source build/lib/safe-cleanup.sh; safe_unmount_paths /mnt/greia-cut-root /mnt/greia-cut-state; safe_detach_loop "$1"' _ "$LOOP"
```

Do not treat a post-boot terminal status as proof of the interrupted phase; retain the pre-cut JSON showing `applying`, job ID, pre-cut package digest, and after-recovery job/journal/generation evidence. Check both filesystem image and job JSON for atomic old-or-new result, not a mixed tree. `find`/`cp` above are offline host reads only.

### Receive-reserve low-space: observed HTTP 507 on a disposable clone

Use a clean clone with software-update bootstrap present and no pending/busy job. Keep the VM stopped while attaching/mounting its raw clone as above, **read/write**, and mount the filesystem that backs `/var/lib/greia-os/software-updates`. For A/B this is PERSIST namespace `/greia/namespaces/parent-credentials`; for single-root it is the installed root. Place a named filler in that same filesystem. The endpoint requires package bytes + 268435456 bytes free; leave 32 MiB below that threshold (about 224 MiB remains free beyond package size) so boot/log activity still has room. This triggers the actual `require_receive_capacity()` check and does not fill the host filesystem.

```bash
PKG_BYTES=$(stat -c %s "$PACKAGE")
NEEDED=$((PKG_BYTES + 268435456))
# Attach the low-space clone to a loop device as above; mount its installed root
# at /mnt/greia-root and (A/B only) PERSIST at /mnt/greia-persist. The actual
# backing path is /mnt/greia-persist/greia/namespaces/parent-credentials on A/B,
# or /mnt/greia-root/var/lib/greia-os on single-root.
# Set LOOP, LAYOUT, ROOT_PART and (A/B only) STATE_PART from this image table.
sudo mkdir -p /mnt/greia-root /mnt/greia-persist
if [ "$LAYOUT" = single-root ]; then
  sudo mount "$ROOT_PART" /mnt/greia-root
  STATE_MOUNT=/mnt/greia-root/var/lib/greia-os
elif [ "$LAYOUT" = ab ]; then
  sudo mount "$STATE_PART" /mnt/greia-persist
  STATE_MOUNT=/mnt/greia-persist/greia/namespaces/parent-credentials
else
  echo "Unknown layout; stop without mounting" >&2; exit 1
fi
UPDATE_DIR="$STATE_MOUNT/software-updates"
sudo test -d "$UPDATE_DIR"
FREE=$(sudo python3 -c 'import shutil,sys; print(shutil.disk_usage(sys.argv[1]).free)' "$UPDATE_DIR")
TARGET_FREE=$((NEEDED - 33554432))
FILL=$((FREE - TARGET_FREE))
test "$FILL" -gt 0
sudo python3 -c 'import shutil,sys; print(shutil.disk_usage(sys.argv[1]).free)' "$UPDATE_DIR" \
  > "$FAULT_EVIDENCE/low-space-before-bytes.txt"
sudo fallocate -l "$FILL" "$UPDATE_DIR/.acceptance-low-space-filler"
sudo chmod 0600 "$UPDATE_DIR/.acceptance-low-space-filler"
ACTUAL_FREE=$(sudo python3 -c 'import shutil,sys; print(shutil.disk_usage(sys.argv[1]).free)' "$UPDATE_DIR")
test "$ACTUAL_FREE" -lt "$NEEDED"
test "$ACTUAL_FREE" -gt "$((NEEDED - 67108864))"
printf 'free=%s required=%s margin=%s\n' "$ACTUAL_FREE" "$NEEDED" "$((NEEDED - ACTUAL_FREE))" \
  > "$FAULT_EVIDENCE/low-space-injected.txt"
sudo bash -c 'source build/lib/safe-cleanup.sh; safe_unmount_paths /mnt/greia-root /mnt/greia-persist; safe_detach_loop "$1"' _ "$LOOP"
```

Start the low-space clone with `start_fault_vm "$FAULT_EVIDENCE/low-space-507.img" low-space-507`, then submit the package through the real Parent `Upload & install` or documented streaming curl route. Require HTTP `507` / `insufficient_storage`; the Parent UI may display its bounded refusal. Save response and authenticated status. Require no new `job_id`, candidate, or `pending`; do not start a package job. Stop QEMU and wait for the recorded PID before remounting the same raw clone read/write using a fresh loop device and newly observed partition identities:

```bash
printf 'quit\n' | socat - "UNIX-CONNECT:$FAULT_EVIDENCE/low-space-507.monitor"
wait "$QEMU_PID"
if kill -0 "$QEMU_PID" 2>/dev/null; then echo 'QEMU still running; do not mount disk' >&2; exit 1; fi
```


```bash
LOOP=$(sudo losetup --find --show --partscan "$FAULT_EVIDENCE/low-space-507.img")
lsblk -f "$LOOP" | tee "$FAULT_EVIDENCE/low-space-partitions.txt"
# Set ROOT_PART/STATE_PART from this fresh output; do not reuse the previous loop device.
sudo mkdir -p /mnt/greia-root /mnt/greia-persist
if [ "$LAYOUT" = single-root ]; then
  sudo mount "$ROOT_PART" /mnt/greia-root
  STATE_MOUNT=/mnt/greia-root/var/lib/greia-os
elif [ "$LAYOUT" = ab ]; then
  sudo mount "$STATE_PART" /mnt/greia-persist
  STATE_MOUNT=/mnt/greia-persist/greia/namespaces/parent-credentials
else
  echo "Unknown layout; stop without mounting" >&2; exit 1
fi
sudo rm -- "$STATE_MOUNT/software-updates/.acceptance-low-space-filler"
sudo df -B1 "$STATE_MOUNT/software-updates" | sudo tee "$FAULT_EVIDENCE/low-space-restored.txt"
sudo bash -c 'source build/lib/safe-cleanup.sh; safe_unmount_paths /mnt/greia-root /mnt/greia-persist; safe_detach_loop "$1"' _ "$LOOP"
```

Retry upload only after filler removal and verify normal operation. If package+reserve will not fit in the test filesystem, stop and mark this predicate NOT RUN; do not shrink host/guest filesystems.

### Parent stop after durable 202 without generic guest privilege

For this leg, provision the separate `parent-stop.img` clone below and start it
with `start_fault_vm "$FAULT_EVIDENCE/parent-stop.img" parent-stop`; keep its
monitor socket name as `parent-stop.monitor`. The production `greia-devctl`
deliberately has no stop-parent verb. Do not use guessed `greia` password/sudo or add one. To test Parent-independent continuation, provision **only the disposable raw VM clone while it is stopped** with a test-only systemd helper, via offline loop mount. Use this fixture only for application packages (full-system jobs stop at `ready_to_restart`). Its fixed job is: after `greia-parent.service` has started, watch the existing shared `job.json` for a valid schema-1 nonterminal application envelope with matching `package_bytes == received_bytes`, the same job ID in the regular `pending` marker, and a regular non-symlink candidate; wait 2 seconds after observing that durable handoff so Parent can return HTTP 202; then stop or SIGKILL Parent; wait for that same `job_id` to reach terminal `applied|rolled_back|failed`; then ensure Parent is active again for post-reconnect status. It has no HTTP listener, no arbitrary command input, does not touch job/candidate/journal, and runs once. Do not install this into source/image or a production device. If offline fixture provisioning is outside operator authority, mark Parent-stop predicate NOT RUN and retain the observed-applying/partial/507 recipes above.

Test-only helper `/usr/local/lib/greia-os/acceptance-parent-handoff.py` (install mode 0755 in clone) content:

```python
#!/usr/bin/python3
import json, subprocess, time
from pathlib import Path
job_path = Path('/var/lib/greia-os/software-updates/job.json')
candidate = Path('/var/lib/greia-os/software-updates/candidate.greia_update')
overall_deadline = time.monotonic() + 780
queue_deadline = min(overall_deadline, time.monotonic() + 120)
pending_path = Path('/var/lib/greia-os/software-updates/pending')
kill_parent = Path('/var/lib/greia-os/acceptance-parent-handoff.kill-parent').exists()
last_id = None
while time.monotonic() < queue_deadline:
    try:
        document = json.loads(job_path.read_text())
        job = document.get('job', {}) if document.get('schema_version') == 1 else {}
        if (job.get('state') in {'queued', 'validating', 'waiting_for_idle', 'applying'}
                and job.get('job_id')
                and job.get('package_type') in {'python_platform', 'activities', 'combined'}
                and job.get('package_bytes') == job.get('received_bytes')
                and candidate.is_file() and not candidate.is_symlink()
                and pending_path.is_file() and pending_path.read_text().strip() == job['job_id']):
            last_id = job['job_id']
            time.sleep(2.0)  # allow Parent to deliver its already-durable HTTP 202
            break
    except (OSError, ValueError):
        pass
    time.sleep(0.05)
if last_id is None:
    raise SystemExit('NOT RUN: no complete durable queued job observed within 120s')
try:
    action = 'kill Parent' if kill_parent else 'stop Parent'
    print(f'acceptance observed durable application job {last_id}; {action}')
    if kill_parent:
        subprocess.run(['/usr/bin/systemctl', 'kill', '--signal=SIGKILL', 'greia-parent.service'], check=True)
    else:
        subprocess.run(['/usr/bin/systemctl', 'stop', 'greia-parent.service'], check=True)
    while time.monotonic() < overall_deadline:
        try:
            document = json.loads(job_path.read_text())
            job = document.get('job', {}) if document.get('schema_version') == 1 else {}
            if job.get('job_id') == last_id and job.get('state') in {'applied', 'rolled_back', 'failed'}:
                Path('/var/lib/greia-os/acceptance-parent-handoff.done').write_text(last_id + '\n')
                print(f'acceptance job {last_id} reached {job["state"]}; restarting Parent')
                break
        except (OSError, ValueError):
            pass
        time.sleep(0.25)
    else:
        raise SystemExit('FAIL: same job did not reach terminal state within 780s')
finally:
    # The helper is test-only and bounded; restore Parent even on a failed leg.
    subprocess.run(['/usr/bin/systemctl', 'start', 'greia-parent.service'], check=True)
```

Install `/etc/systemd/system/greia-acceptance-parent-handoff.service` in the clone:

```ini
[Unit]
Description=Disposable VM acceptance: stop Parent after durable software update receipt
After=greia-parent.service
Wants=greia-parent.service
ConditionPathExists=/etc/greia-os/software-update-bootstrap.json
ConditionPathExists=/var/lib/greia-os/acceptance-parent-handoff.enabled

[Service]
Type=simple
User=root
Group=root
ExecStart=/usr/bin/python3 -I -B /usr/local/lib/greia-os/acceptance-parent-handoff.py
TimeoutStartSec=900
NoNewPrivileges=yes
PrivateTmp=yes
ProtectHome=yes
ProtectSystem=strict
ReadWritePaths=/var/lib/greia-os
RestrictAddressFamilies=AF_UNIX

[Install]
WantedBy=multi-user.target
```

Save the two displayed blocks verbatim on the Linux host as
`$FAULT_EVIDENCE/acceptance-parent-handoff.py` and
`$FAULT_EVIDENCE/greia-acceptance-parent-handoff.service`. With the
`parent-stop.img` clone stopped and copied, inspect its partitions, mount its
root and state backing filesystems read/write, install the test files, create
the one-shot markers and enable symlink, then unmount/detach:

```bash
LOOP=$(sudo losetup --find --show --partscan "$FAULT_EVIDENCE/parent-stop.img")
lsblk -f "$LOOP" | tee "$FAULT_EVIDENCE/parent-stop-partitions.txt"
# Set LAYOUT and partition variables only from the output above.
LAYOUT=single-root # or ab, as shown by this clone's own layout
sudo mkdir -p /mnt/greia-fixture-root /mnt/greia-fixture-state
if [ "$LAYOUT" = single-root ]; then
  sudo mount "$ROOT_PART" /mnt/greia-fixture-root
  ROOT_MOUNT=/mnt/greia-fixture-root
  STATE_MOUNT=/mnt/greia-fixture-root/var/lib/greia-os
elif [ "$LAYOUT" = ab ]; then
  sudo mount "$ROOT_PART" /mnt/greia-fixture-root
  sudo mount "$STATE_PART" /mnt/greia-fixture-state
  ROOT_MOUNT=/mnt/greia-fixture-root
  STATE_MOUNT=/mnt/greia-fixture-state/greia/namespaces/parent-credentials
else
  echo "Unknown layout; stop without mounting" >&2; exit 1
fi
sudo install -D -m 0755 "$FAULT_EVIDENCE/acceptance-parent-handoff.py" \
  "$ROOT_MOUNT/usr/local/lib/greia-os/acceptance-parent-handoff.py"
sudo install -D -m 0644 "$FAULT_EVIDENCE/greia-acceptance-parent-handoff.service" \
  "$ROOT_MOUNT/etc/systemd/system/greia-acceptance-parent-handoff.service"
sudo install -D -m 0600 /dev/null "$STATE_MOUNT/acceptance-parent-handoff.enabled"
# For the separate force-kill leg only:
# sudo install -D -m 0600 /dev/null "$STATE_MOUNT/acceptance-parent-handoff.kill-parent"
sudo install -d -m 0755 "$ROOT_MOUNT/etc/systemd/system/multi-user.target.wants"
sudo ln -s ../greia-acceptance-parent-handoff.service \
  "$ROOT_MOUNT/etc/systemd/system/multi-user.target.wants/greia-acceptance-parent-handoff.service"
sudo bash -c 'source build/lib/safe-cleanup.sh; safe_unmount_paths /mnt/greia-fixture-root /mnt/greia-fixture-state; safe_detach_loop "$1"' _ "$LOOP"
```

The helper first waits at most 120 seconds for the durable nonterminal application envelope, matching pending marker and candidate, sleeps 2 seconds for the HTTP 202 response to reach the host, then stops or kills Parent and waits within a total 900-second deadline. Ensure the host captured HTTP 202 before accepting the stop event. On timeout it leaves/restarts Parent and records NOT RUN/FAIL from the observed boundary. While offline-mounting the clone, install the shown helper at `/usr/local/lib/greia-os/acceptance-parent-handoff.py` mode 0755 and the shown unit at `/etc/systemd/system/greia-acceptance-parent-handoff.service` mode 0644; create the empty `/var/lib/greia-os/acceptance-parent-handoff.enabled` marker (and, for kill mode only, the `.kill-parent` marker), then symlink `etc/systemd/system/multi-user.target.wants/greia-acceptance-parent-handoff.service` to `../greia-acceptance-parent-handoff.service`. Do not alter the installed production service units. Start clone; use normal Parent UI/API upload. After observed HTTP 202, cut QEMU network. The test oneshot stops or kills Parent only after seeing the durable application handoff; timer/apply continue without depending on the Parent process or network. Record monitor link-down, 202, copied `job.json`, available persistent unit logs and the helper's `.done` marker; journald uses volatile storage so do not promise post-power-cut service journals. Wait for terminal state, restore network if needed, then Parent comes back and `GET /api/v1/system/update` must report the same job ID/state. If helper doesn't stop Parent after queued state or job isn't terminal, FAIL; if the queued boundary was missed, repeat on a fresh clone. Remove this test fixture by discarding the clone.


The update job and apply journal are root-only. Use the offline extraction
above, not guessed `sudo systemctl` commands or SSH sudo.
