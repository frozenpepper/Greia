# Greia software update packages

**Status:** operator guide for ADR 0038; source package builder available, installed Linux acceptance pending
**Architecture:** [ADR 0038](../adr/0038-lightweight-application-update-packages.md) for application packages; [ADR 0036](../adr/0036-unified-system-slot-releases-and-platform-install-media.md) for full-system A/B releases
**Format and CLI owners:** `src/greia_platform/software_update_package.py`, `src/greia_platform/software_update_package_builder.py`, `tools/greia_software_update.py`
**Acceptance handoff:** [language package acceptance](../testing/2026-10-27_LANGUAGE_UPDATE_PACKAGE_ACCEPTANCE.md); the earlier [2026-10-24 Linux acceptance](../testing/2026-10-24_SOFTWARE_UPDATE_ACCEPTANCE.md) remains its own source/installed evidence lane

This guide builds, inspects and sends a typed `.greia_update` package. It does
not claim that a package has been installed or accepted on a Linux device.
The package builder reuses Greia's existing Activity validators and the
existing v3 system-bundle inspector. Routine Python/Activity application
updates are standalone packages: they do not need the old full-system catalog
or a full disk image. Only the `full_system` type uses the existing v3 A/B
bundle and slot writer.

The package manifest describes what to install. The durable job records the
parent's Upload & install command and lets the device continue after the app
disconnects; it is not a publisher certificate or a second package approval.
The full-system inbox discovers its fixed published bundle directly, without
requiring a separate status receipt. Temporary/incomplete uploads are never
applied. Application-generation and A/B recovery state remain necessary to
recover from interruption or broken replacement code.

## 1. Package types and boundaries

`.greia_update` is a ZIP archive with `manifest.json` first. Schema version 1
uses one of these exact `type` values:

| Type | Contents | Activation |
| --- | --- | --- |
| `python_platform` | Complete production Python source snapshot plus fixed runtime-config allowlist | Atomic application generation; supported on bootstrapped single-root and A/B images |
| `activities` | One, a set, or all listed built-in or Parent-source `.greiaactivity` archives | Built-in changes join the application generation; Parent-source changes use the existing PERSIST Activity generation |
| `combined` | Complete Python snapshot plus one/set/all built-in Activities | One atomic application generation |
| `full_system` | One existing unsigned v3 `.greiaupdate` bundle, stored as `full_system/bundle.greiaupdate` | Existing A/B slot writer and health/rollback route; a separate explicit restart is required |

The v1 manifest has `schema_version`, `type`, `version` and `release_id`.
Application types also have `targets` (an empty list means no profile/board
restriction). A `python_platform` component has `files`, each with its fixed
destination `path`, corresponding `member`, `size` and `sha256`. An `activities`
component has `scope` (`one`, `set` or `all`), `source` (`built_in` or `parent`)
and `items`, each recording `activity_id`, Activity `version`, fixed `member`,
`size` and `sha256`. A `full_system` component has exactly one member record
with `member`, `size` and `sha256`; its outer version and release ID must match
the inner v3 bundle.

For example, a built-in Activity package has this shape (the builder writes
the complete canonical member records and hashes):

```json
{
  "activities": {
    "items": [
      {
        "activity_id": "org.greia.writing",
        "version": "0.1.0",
        "member": "activities/org.greia.writing.greiaactivity",
        "size": 1234,
        "sha256": "<64 lowercase hex characters>"
      }
    ],
    "scope": "one",
    "source": "built_in"
  },
  "release_id": "greia-app-0.14.1-example",
  "schema_version": 1,
  "targets": [],
  "type": "activities",
  "version": "0.14.1-example"
}
```

The receiver accepts 1 byte through 2 GiB + 1 MiB. Source bounds also cap the
manifest at 1 MiB, outer entries at 8,192, Python at 4,096 files / 256 MiB
total / 32 MiB per file, Activities at 64 packages / 1.5 GiB total / 128 MiB
per archive, and each extracted Activity tree at 512 MiB and 4,096 entries.
The CLI and installed inspector reject malformed paths, member mismatches,
digest/size mismatches, invalid canonical manifests and invalid nested
packages.

Application `targets` constrain identity facts by exact equality. Each target
object is a conjunction of its supplied `profile`, `platform_family`,
`architecture` and `board` values; multiple target objects are alternatives.
No target objects means the application package is portable across the
curated Greia platforms. `version` and `release_id` are package identity and
display facts; the current application route does not compare version order.
Release operators must publish monotonically newer versions and must inspect
the target fields before distribution. Full-system compatibility continues to
come from the inner v3 manifest and existing A/B writer.

### Python payload contents

A Python update is a full source snapshot, not a patch. It includes every
production `.py` file under:

```text
src/greia_platform/
src/greia_launcher/
src/greia_parent/
src/greia_installer/
```

It also includes the source-owned runtime allowlist: `achievement-policy.toml`,
`activity-launch.toml`, the two `runtime/alsa/greia-activity-*.conf` files,
`audio-settings.toml`, `child-runtime.toml`, `hardware-settings.toml`,
`history-policy.toml`, `permission-policy.toml`, `profile-defaults.toml`,
`progression-policy.toml`, `storage-policy.toml` and `theme-defaults.toml`.
The installed Parent HTML app and its `runtime/parent-app-client.toml` and
`runtime/parent-app-client.manifest.json` integrity pins stay paired with the
installed image and are outside this payload.

The Python snapshot also carries the complete managed language-resource
inventory under `src/greia_platform/languages/`. Every offered canonical locale
has exactly the paired `manifest.json` and `ui.json`; English is required and
the runtime supports at most 32 offered locales. A locale folder without a
manifest is an unoffered authoring scaffold and is not packaged. Before the
generation pointer can switch, the receiver checks the staged manifests,
runtime ordering, English UI keys and interpolation placeholders. The declared
resources are staged with Python code as one candidate. Stale managed locale
manifest/UI files are removed from that candidate; unrelated files, old
generations, Activities, profiles and child data are preserved.

Do not put an interpreter, private environment, wheels, `site-packages`, native
libraries, OS packages, arbitrary filesystem destinations, global art/audio
assets or fonts in a Python package. Python code uses the image's curated
interpreter and dependencies. If an updated Activity owns a resource, that
resource belongs inside its selected `.greiaactivity` archive and remains
subject to the Activity validator and footprint limit. Shared assets remain
owned by the image's existing asset catalogue.

Activity updates name only the IDs in the manifest. Unlisted Activities are
preserved. Built-in updates remain in the built-in source and trust class;
Parent updates remain in the Parent source as `PARENT_TRUSTED_UNSIGNED`.
`combined` is built-in only; a combined package containing Parent-source
Activities is rejected. None of these packages replaces profiles, child saves,
creations, credentials or settings.

## 2. Build and inspect packages

Run from the repository root with the source tree on `PYTHONPATH`. Use a new
output path for each build; the builder refuses to overwrite an existing file.

```bash
export PYTHONDONTWRITEBYTECODE=1
export PYTHONPATH=src
UPDATE_PACKAGE_OUT="$(mktemp -d "${TMPDIR:-/tmp}/greia-software-update.XXXXXX")"
UPDATE_VERSION=0.14.1-example
UPDATE_RELEASE_ID=greia-app-0.14.1-example
```

### Complete Python platform/launcher snapshot

```bash
python3 tools/greia_software_update.py build-python-platform \
  --version "$UPDATE_VERSION" \
  --release-id "$UPDATE_RELEASE_ID" \
  --source-root . \
  --output "$UPDATE_PACKAGE_OUT/python-platform.greia_update"
```

Use optional `--profile`, `--platform-family`, `--architecture` and `--board`
flags when the Python package should target exact installed identity values.
Omit them only when the full snapshot is intentionally compatible with every
curated image carrying this bootstrap.

#### One-time receiver bridge for the frozen 1275-era base

Use this bridge only when the installed application is confirmed to come from
the exact old source snapshot `1275e0be1a9e0cda724ce18151ae65a25f03c98c` and
its existing package reader rejects language JSON paths. Do not build this
bridge for an arbitrary supported image or a newer application generation: it
replaces the complete declared Python/runtime snapshot with that old base,
overlaid with the two receiver modules. The bridge carries no language JSON
or current language registry.

```bash
python3 tools/greia_software_update.py build-receiver-bridge \
  --version 0.13.1-bridge \
  --release-id greia-receiver-bridge-1275e0be1 \
  --base-ref 1275e0be1a9e0cda724ce18151ae65a25f03c98c \
  --git-root . --python-root . \
  --output "$UPDATE_PACKAGE_OUT/receiver-bridge.greia_update"
```

Inspect and upload this bridge first. Wait until the installed device reports
the bridge package `applied` (including its normal fresh launcher/Parent
health checks). Only then build and upload the ordinary current Python or
combined package; that second package carries the complete language JSON
snapshot. Do not send current language code/data to the 1275-era reader before
the bridge is accepted. This is a lightweight two-package route and does not
require an OS image rebuild. It cannot add the receiver to a system with no
application-update bootstrap at all.

For the verified source-only 1275-era chain and the bounded installed
acceptance route, see [language package acceptance](../testing/2026-10-27_LANGUAGE_UPDATE_PACKAGE_ACCEPTANCE.md).

### Built-in Activity one, set and all-current

For one built-in Activity:

```bash
python3 tools/greia_software_update.py build-activities \
  --version "$UPDATE_VERSION" --release-id "$UPDATE_RELEASE_ID" \
  --scope one --source built_in \
  --activity org.greia.writing=activities/writing \
  --output "$UPDATE_PACKAGE_OUT/writing.greia_update"
```

For a set, repeat `--activity` at least twice:

```bash
python3 tools/greia_software_update.py build-activities \
  --version "$UPDATE_VERSION" --release-id "$UPDATE_RELEASE_ID" \
  --scope set --source built_in \
  --activity org.greia.writing=activities/writing \
  --activity org.greia.painting=activities/painting \
  --output "$UPDATE_PACKAGE_OUT/creative-activities.greia_update"
```

For the validated current source inventory, the bounded source-only
`--all-current-activities` option derives its IDs from the canonical Activity
registry. It does not promote a draft catalogue roster:

```bash
python3 tools/greia_software_update.py build-activities \
  --version "$UPDATE_VERSION" --release-id "$UPDATE_RELEASE_ID" \
  --scope all --source built_in --all-current-activities \
  --activities-root activities --runtime runtime/child-runtime.toml \
  --output "$UPDATE_PACKAGE_OUT/all-current-built-in-activities.greia_update"
```

To require an exact match with an installed image's built-in index, point
`--all-from-installed-root` at that mounted image's root filesystem and use
`--activities-root` for the candidate Activity tree:

```bash
python3 tools/greia_software_update.py build-activities \
  --version "$UPDATE_VERSION" --release-id "$UPDATE_RELEASE_ID" \
  --scope all --source built_in \
  --all-from-installed-root /mnt/greia-root \
  --activities-root activities --runtime runtime/child-runtime.toml \
  --output "$UPDATE_PACKAGE_OUT/installed-roster-activities.greia_update"
```

The installed inventory check compares the installed activity index with the
installed Activity trees, then requires the candidate IDs to match that exact
roster. Current image composition makes the `/opt/greia-os` and built-in
Activity-index aliases relative, so these paths resolve inside the supplied
mounted root rather than against the build host's `/`. Keep the image mounted
at the path passed to `--all-from-installed-root`; do not substitute host
`/opt/greia-os`. `all` is unavailable for Parent-source packages.

### Parent-source Activity package

The Parent Activity store at `/var/lib/greia-os/activity-packages` has one
writer identity, `greiapanel:greiapanel`. Its root and generation container
are `0755` so the child can read published Activities; private staging, versions
and receipts remain owner-only. Root-side application/Activity updates preserve
or restore that owner for directories, transaction locks, receipts and staged
generations. Do not repair an image by granting the child write permission or
changing the unrelated profile-group migration. The Linux cross-identity
regression in `test_activity_packages` must run on the test image with the
provisioned accounts; its skip on macOS is not installed permission proof.

Use `source=parent` for a Parent-source Activity archive or validated source
directory. A set uses one or more repeated `--activity ID=PATH` arguments and
must contain at least two IDs. The existing Parent Activity service validates
and publishes the listed items in its PERSIST generation; built-in Activities
are unaffected and unlisted Parent Activities are retained.

```bash
python3 tools/greia_software_update.py build-activities \
  --version "$UPDATE_VERSION" --release-id "$UPDATE_RELEASE_ID" \
  --scope one --source parent \
  --activity org.example.parent-puzzle="$UPDATE_PACKAGE_OUT/parent-puzzle.greiaactivity" \
  --output "$UPDATE_PACKAGE_OUT/parent-puzzle-update.greia_update"
```

### Combined Python plus built-in Activities

`build-combined` always uses built-in Activity trust. The selected Python
snapshot and Activities publish as one application generation:

```bash
python3 tools/greia_software_update.py build-combined \
  --version "$UPDATE_VERSION" --release-id "$UPDATE_RELEASE_ID" \
  --source-root . --scope one \
  --activity org.greia.writing=activities/writing \
  --output "$UPDATE_PACKAGE_OUT/platform-and-writing.greia_update"
```

For a set or all-current built-ins, replace `--scope one --activity …` with
the matching set of repeated `--activity` inputs or with
`--scope all --all-current-activities --activities-root activities`.

### Full-system wrapper

Build the ordinary v3 bundle with the existing
[`GREIA_SYSTEM_UPDATE_RELEASE_WORKFLOW.md`](GREIA_SYSTEM_UPDATE_RELEASE_WORKFLOW.md)
front door, then wrap it without changing its payload:

```bash
UPDATE_V3_VERSION="$(cat VERSION)"
sudo python3 tools/greia_release.py build \
  --version "$UPDATE_V3_VERSION" \
  --output ./out
```

For the Acer A/B target, this publishes
`./out/greia-<UPDATE_V3_VERSION>/updates/acer-aspire-one-i386-ab.greiaupdate`.
Inspect that v3 bundle with the existing release workflow before wrapping:

```bash
python3 tools/greia_software_update.py wrap-full-system \
  --bundle "./out/greia-${UPDATE_V3_VERSION}/updates/acer-aspire-one-i386-ab.greiaupdate" \
  --output "$UPDATE_PACKAGE_OUT/full-system.greia_update"
```

The wrapper runs the existing v3 inspector over the inner bundle and requires
the outer version and release ID to match it. Only an A/B-capable installed
system can activate `full_system`; this wrapper does not add an A/B backend to
a single-root installation.

### Inspect every output before distribution

All build commands emit a JSON summary and re-inspect the completed package.
For a separate saved manifest/report:

```bash
python3 tools/greia_software_update.py inspect "$UPDATE_PACKAGE_OUT/python-platform.greia_update" \
  > "$UPDATE_PACKAGE_OUT/python-platform.inspect.json"
```

Retain the package SHA-256, package size and inspect output with the release
notes. `UPDATE_PACKAGE_OUT` is a new user-writable temporary directory so it
also works after a privileged release build has created a root-owned `out/`.
An inspect PASS establishes package structure and declared digests only;
it does not establish device compatibility or installation success.

## 3. Parent upload and status

On a device that advertises `system.update.package.install`, choose the
`.greia_update` package in Greia Parents or the paired Mobile client and tap
**Upload & install**. The HTML and mobile clients send the file as one bounded
streaming request. Parent returns HTTP `202 Accepted` only after the entire
upload has been synced and a durable job has been written. The accepted job
begins at `queued`; package type/version/release ID are filled in after the
installed OS validates the package.

After the `202` response, the parent may close the app or disconnect the
phone. Greia's stable root helper and systemd timer continue the authorized
job; no catalog, Internet, second authorization or Parent process is needed
to finish it. The Parent process does not write privileged application files.

The authenticated status resource is:

```text
GET /api/v1/system/update
```

The package job is at `software_update.job`. Its bounded public fields are
`job_id`, `state`, `created_at`, `updated_at`, `package_bytes`,
`received_bytes`, `package_type`, `version`, `release_id`, `error_code`,
`error_message`, `activation_requested` and `restart_available`. Finite states
are `queued`, `validating`, `waiting_for_idle`, `applying`, `restarting`,
`applied`, `rolled_back`, `failed` and `ready_to_restart`. Poll again after
reconnecting; upload acknowledgement is not installation acceptance.

Only a validated `full_system` job reaches `ready_to_restart`. Greia does not
restart automatically: the authenticated Parent action
`POST /api/v1/system/update/package/restart` has an empty JSON body and is
available only when `software_update.restart_available` is true. Application
code and Activity updates finish their generation health check without this
restart action.

For an offline command-line upload, stream the file instead of buffering it
into JSON or a shell variable. Use a bearer token from the normal Parent
pairing flow and a certificate already trusted for this device; do not disable
TLS verification:

```bash
curl --fail --show-error --silent \
  --request POST --upload-file "$UPDATE_PACKAGE_OUT/python-platform.greia_update" \
  --header "Authorization: Bearer ${GREIA_PARENT_TOKEN}" \
  --header 'Content-Type: application/vnd.greia.software-update+zip' \
  --cacert "$GREIA_DEVICE_CERT" \
  "https://${GREIA_DEVICE}:8766/api/v1/system/update/package"
```

The caller supplies the established device name/address, trusted certificate
file and Parent bearer credential. Keep credentials out of shell history and
evidence. `--data-binary` is not the recommended transfer for this large body;
`--upload-file` streams the package while the server reads bounded chunks.

## 4. Bootstrap and recovery boundary

The Parent capability is enabled only when the installed image has both:

```text
/etc/greia-os/software-update-bootstrap.json   {"schema_version":1}
/usr/local/lib/greia-os/software-update-bootstrap.py
```

The helper is standard-library-only and exposes only its installed recovery
and apply service modes (`--recover` and `--apply`); systemd owns those
invocations. `greia-software-update-recover.service` runs before launcher and
Parent services. The enabled `greia-software-update-apply.timer` starts 25
seconds after boot and retries pending jobs every 15 seconds.
The application root is one pointer into `/opt/greia-software/generations`;
unchanged files may be hard-linked into a candidate on the same filesystem.
The previous complete generation remains available until the candidate
launcher and Parent reach fresh profile-picker readiness. Failed startup or
an interrupted pointer switch restores the old generation before the services
are exposed. Application generations do not include child data.

There is no supported manual command for installing the bootstrap onto an
older image. Such an image does not expose the `.greia_update` upload route.
First install or reimage from a build that already contains the package API,
marker, helper and units. An already-functional A/B image can reach that base
through its ordinary full-system upgrade route. An older single-root image
without the engine requires a logical backup followed by graphical
reinstallation and data restore; the physical target must be explicitly
operator-selected. A `.greia_update` package cannot bootstrap its own receiver.
The one-time 1275-era receiver bridge in §2 is narrower: it updates an existing
package reader that already accepts `.greia_update`; it cannot create a missing
API, bootstrap marker, helper, or systemd unit.
The single-root application updater does not convert the disk layout.

On an image that already contains the marker/helper but still has a legacy
regular `/opt/greia-os` directory, the first boot runs
`greia-software-update-recover.service` before launcher and Parent and performs
the journaled directory-to-generation migration. The supported first
migration is this normal boot path; do not invoke `--recover` while a child
session or application services are live. The helper's only accepted modes
remain the systemd-owned `--recover` and `--apply` invocations.

Application-generation journal phases record the current root-filesystem UUID
and the package `job_id`. Recovery checks the UUID before using a slot-local
generation pointer instruction, and checks the current job ID before
finalizing that job or cleaning its candidate. This prevents shared boot/PERSIST
state from replaying a stale pointer instruction onto a different A/B root.
If the worker stops between the durable `switching` journal and the `trial`
journal, the next apply tick reconciles the same job and matching idle fence;
on a later boot, the recovery unit resolves the journal before launcher or
Parent imports the application tree.

Before hashing or extracting a package, the apply timer performs a cheap
profile-picker/session-lock check. A busy session leaves the job at
`waiting_for_idle` for a later timer tick. After preparation, the updater
rechecks under the shared lock before changing the single application pointer.
Fresh acceptance requires a new `launcher_interactive_ready` marker with a
monotonic timestamp after the pointer-switch boundary; the launcher event must
arrive within 90 seconds. Parent must then pass its loopback `/healthz` check
(HTTP 200 with `{"status":"ok"}`). Failure of either check restores the
previous generation and checks the old launcher and Parent through the same
readiness path.
