# Software update package Linux acceptance

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

## 1. Freeze and record the exact source

Start only after package/apply/Parent implementation is committed on `main`.
Record the exact source SHA, Parent HTML runtime pin, Mobile revision, Linux
host/tool versions, installer/package digests and all logs under an evidence
directory outside the checkout. Preserve unrelated untracked media and
outputs. Do not edit source during an acceptance run.

Read `SETUP.md`, `AGENTS.md`, `HANDOVER.md`, the current lifecycle plan, ADRs
0036/0038, the operator guide above, the previous
`2026-10-23_SYSTEM_UPDATE_LINUX_ACCEPTANCE.md` work order and the OS-work skill.
From a clean checkout at the recorded SHA, prepare an evidence directory:

```bash
SOURCE_HEAD="$(git rev-parse HEAD)"
UPDATE_EVIDENCE="/var/tmp/greia-software-update-$SOURCE_HEAD"
mkdir -p "$UPDATE_EVIDENCE"
printf '%s\n' "$SOURCE_HEAD" > "$UPDATE_EVIDENCE/source-head.txt"
uname -a > "$UPDATE_EVIDENCE/host.txt"
python3 --version >> "$UPDATE_EVIDENCE/host.txt"
git status --short
test -z "$(git status --porcelain)"
```

Run the repository-wide verification and preserve its exact result:

```bash
set -o pipefail
make verify 2>&1 | tee "$UPDATE_EVIDENCE/make-verify.log"
```

Run the affected source suite separately even if the repository-wide gate
fails:

```bash
set -o pipefail
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 tools/run_tests.py \
  test_software_update_package test_greia_software_update_tool \
  test_software_update_generation test_software_update_jobs \
  test_software_update_bootstrap test_parent_update_delivery \
  test_parent_system_updates test_activity_packages -v \
  2>&1 | tee "$UPDATE_EVIDENCE/software-update-focused.log"
```

A failure remains a failure; do not weaken test predicates. Record whether the
historical full-gate-only retained-surface memory failure recurs; isolation
PASS on another host does not waive an aggregate failure.

## 2. Build actual disposable images and packages

Build an experimental single-root `legacy-x86-i686-rc` installer without
flashing media:

```bash
sudo -E bash tools/build-development-installer.sh \
  legacy-x86-i686-rc "$UPDATE_EVIDENCE/single-root-installer"
```

Build a real `acer-aspire-one-i386-ab` release and matching installer using
the owner release tools:

```bash
UPDATE_RELEASE_VERSION="$(cat VERSION)"
sudo -E python3 tools/greia_release.py doctor --output "$UPDATE_EVIDENCE"
sudo -E python3 tools/greia_release.py build \
  --version "$UPDATE_RELEASE_VERSION" \
  --output "$UPDATE_EVIDENCE/releases"
UPDATE_RELEASE="$UPDATE_EVIDENCE/releases/greia-$UPDATE_RELEASE_VERSION"
UPDATE_BASE_BUNDLE="$UPDATE_RELEASE/updates/acer-aspire-one-i386-ab.greiaupdate"
sudo -E build/build-installer-image.sh acer-aspire-one-i386-ab \
  "$UPDATE_EVIDENCE/ab-installer" --release-bundle "$UPDATE_BASE_BUNDLE"
```

Use the existing
`2026-10-23_SYSTEM_UPDATE_LINUX_ACCEPTANCE.md` procedure for the actual v3
bundle, BIOS fresh-install/boot proof, and disposable product harness. Pass
the exact source commit for this package implementation; its old `4eaad...`
source pin is historical and does not contain ADR 0038. Install the RC
graphically in QEMU onto a new file-backed disposable virtual disk; install
the A/B image with its existing product harness. Keep both legs separate and
do not treat the experimental RC as an ordinary family release. Never flash
or guess a host `/dev` target.

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

Also build negative fixtures with the normal builder or focused fixture
helpers: wrong target, malformed/noncanonical manifest, truncated outer ZIP,
bad declared digest, corrupted nested `.greiaactivity`, corrupted nested v3
payload, combined Parent-source Activity, unknown/extra manifest fields and a
package missing a required Python entrypoint. Inspect must reject each bad
package before it is uploaded. Keep SHA-256, byte counts, and full inspect
reports for every input.

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
3. After the `202`, stop the Parent service and cut the guest network. Do not
   send another authorization or invoke the privileged helper by hand.
4. Observe the root-owned timer/service process the queued job. Read the
   bounded job JSON while Parent is stopped; then restart Parent and confirm
   `GET /api/v1/system/update` reports the same `job_id` and terminal state.
5. Repeat after forcibly terminating Parent during a separate accepted job.
   The accepted job must finish without Parent recovery, phone connection,
   catalog access or internet.

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
