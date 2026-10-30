# Greia System Updates — Product and Operator Requirements

**Status:** accepted product direction; implementation incremental
**Reviewed:** 2026-10-24
**Architecture owner:** ADR 0038 for typed application packages; ADR 0036 for full-system A/B releases (both supersede ADR 0030's signing requirements where they conflict)
**Current lifecycle owner:** 2026-09-15 completion plan, Session 04 (OPEN)

## 1. Parent-facing goal

A parent should be able to keep Greia current without learning Linux, package managers, partitions or bootloaders.

Normal intended experience:

```text
System
Greia OS 0.x.y

Update available: 0.x.z
[ Update Greia ]
```

Greia then downloads/verifies/prepares the update itself. Once the candidate is safely staged:

```text
Update ready
[ Restart & Update ]
```

The child is never interrupted automatically in the middle of an Activity merely because an update exists.

Application-code packages use one authenticated **Upload & install** action.
Greia may apply a Python, Activity or combined application generation after
the complete upload is durably accepted; the Parent app and phone may then
close. Only a full-system A/B package waits for the parent to request a
separate restart.

After reboot:

```text
Greia updated successfully
```

If the candidate cannot boot/confirm health:

```text
The update could not be completed.
Greia restored the previous version.
Your children's data was preserved.
```

## 2. Parents app role

Greia Parents is the primary human-control surface for system updates, but it is not the update engine.

The Parents client may:

- display current OS release and update state;
- ask Greia to check for an update;
- authorize download/preparation;
- upload a typed `.greia_update` application package or a `.greiaupdate`
  full-system bundle;
- show progress/status/error classifications;
- request restart once Greia reports the candidate ready;
- show success/rollback after reconnection.

It must not:

- execute shell/package-manager commands;
- write OS partitions/files directly;
- select boot slots;
- decide release trust;
- implement rollback itself.

The same API is used by the built-in responsive HTML client and future native clients.

## 3. Update sources

### Online full-system update

The preferred normal path is device-to-server:

```text
Parent authorizes -> Greia downloads -> Greia verifies/stages
```

The phone/browser does not need to relay the full release and may disconnect after authorization.

The online catalog/check/prepare path downloads and stages full-system v3
bundles. It remains separate from the local `.greia_update` package upload.
The legacy manual `.greiaupdate` bundle endpoint remains receive-only and
preparing that candidate still needs an online catalog selection. Do not
describe that legacy upload as installed success.

### Parent-uploaded file

For offline package distribution or manual recovery:

```text
parent has release.greia_update
-> upload through Greia Parents or its package endpoint
-> Greia durably acknowledges receipt and queues installation
-> installed root bootstrap validates and applies without the phone, Parent process, catalog or internet
```

The package types are `python_platform`, `activities`, `combined` and
`full_system`. Python and Activity packages use the image's curated runtime;
they do not install Linux packages or private Python environments. A
`full_system` type wraps the existing v3 `.greiaupdate` and keeps its A/B
compatibility, explicit restart and boot-health/rollback route. See
`docs/development/GREIA_SOFTWARE_UPDATE_PACKAGES.md` for the exact manifest,
CLI and status contract.

### USB/SD

The same `.greiaupdate` file may later be discovered from removable media. Removable media is untrusted and never autorun; Greia offers the update only after bounded discovery and Parent authorization.

## 4. Full-system A/B bundle

The typed `.greia_update` package is the Parent-uploadable application
container. Its `full_system` type wraps the same unsigned `.greiaupdate` v3
bundle used by the existing online/full-system route. There is no second OS
image writer.

Current bundle contract is source-owned by:

```text
src/greia_platform/system_updates.py
```

The target shape is:

```text
release.greiaupdate
├── manifest.json
├── payload.ext4.zst
└── hardware-support.tar.zst     # optional
```

The outer container is ZIP with the already-compressed `.zst` members
stored without double compression. The manifest carries practical facts
only (format version, Greia version, profile id, architecture, platform
family, board id or none, uncompressed payload bytes, minimum destination
slot bytes, PERSIST schema integers, optional hardware-support
presence/size, optional short release notes). There is no signature
member, signer identity, key id or release sequence. Old signed bundles
(`manifest.sig`, `payload.bin`) are rejected with a rebuild/migration
message, not interpreted.

The first release implementation uses whole-system slot payloads. Delta transport may be added later behind the same semantic service.

## 5. Simple release-creation workflow

The repository provides two operator tools:

```text
tools/build_release.py    # real ext4 slot payload + read-only verification
tools/greia_update.py     # unsigned v3 bundle build / inspect / push / status
```

The intended flow is deliberately small. No signing key and no
`cryptography` package are required anywhere: the build host needs
`zstd` plus e2fsprogs (`mkfs.ext4`, `e2fsck`, `resize2fs`, `debugfs`).
There is no release-signing ceremony to perform and no public key to
install into images.

### Build the real slot payload first

Given the composed target root for the release profile (role `target`
of the canonical composition engine) plus the generic kernel and
initramfs, build the real relocatable ext4 slot image:

```bash
python3 tools/build_release.py build-payload \
  --staging-dir ./out/composed-target-root \
  --kernel ./out/vmlinuz-generic \
  --initramfs ./out/initrd-generic \
  --output ./out/payload.ext4.zst \
  --profile-id acer-aspire-one-i386-ab \
  --release-id greia-0.14.0 \
  --filesystem-bytes 1073741824 \
  --minimum-slot-bytes 1074790400 \
  --receipt-output ./out/payload-receipt.json
```

`--receipt-output` writes the machine-readable payload receipt measured
from the finished artifact (`schema_version`, `payload_sha256`,
`payload_compressed_bytes`, `payload_uncompressed_bytes`,
`minimum_slot_bytes`, `profile_id`, `release_id`). The normal bundle path
consumes that receipt via `greia_update.py build --payload-receipt`, which
verifies it against the payload artifact before any bundle byte is
written. Field and flag names are stable for Session 03.

`--minimum-slot-bytes` is the candidate's minimum base filesystem size,
not the destination slot size: it must cover the actual shrunk ext4 size
reported by the `build-payload` step plus the 1 MiB finalization headroom
(`PAYLOAD_MIN_HEADROOM` in `tools/build_release.py`; 1073741824 + 1048576
= 1074790400 in this example). Take the shrunk size from the producer
output for each release; do not copy the destination slot size
(1536 MiB = 1610612736 for `acer-aspire-one-i386-ab`) by habit, and do not
raise the manifest minimum to 1536 MiB unless the base OS genuinely needs
that much space before finalization — an inflated minimum can only refuse
valid slots, never create capacity.

The producer runs `mkfs.ext4 -d <staging>` → `e2fsck -f -y` →
`resize2fs -M` → `e2fsck -f -y` → `zstd -19`, validates the staging tree
with the shared slot completeness validator before any image byte
(a skeleton root is refused before compression), and rejects partition
tables and tar bodies. Verify the payload read-only before bundling:

```bash
python3 tools/build_release.py verify-payload \
  --payload ./out/payload.ext4.zst
```

### Build an update bundle — normal path (verified receipt flow)

Given the verified `payload.ext4.zst` and its `build-payload --receipt-output`
receipt produced above, point the tool at the Greia build profile. The tool derives `profile.id`, `platform.family` and `base.architecture` from that file so the operator does not retype compatibility identity by hand:

```bash
python3 tools/greia_update.py build \
  --payload ./out/payload.ext4.zst \
  --payload-receipt ./out/payload-receipt.json \
  --profile-file ./build/profiles/acer-aspire-one-i386-ab.toml \
  --version 0.14.0 \
  --persist-read-min 1 \
  --persist-read-max 1 \
  --persist-write 1
```

The normal `--profile-file` build derives size facts from the receipt and
verifies it against the payload artifact in full (shape → profile/release
identity → sha256 → compressed size → streamed decompressed length →
manual-vs-receipt equality) before any bundle byte is written. Bare
`--payload-uncompressed-bytes` / `--minimum-slot-bytes` without
`--payload-receipt` are a DEVELOPER-ONLY low-level seam
(`--developer-allow-unverified-payload-facts`): test/low-level usage only,
never normal production.

Defaults deliberately reduce release-command ceremony:

```text
release_id = greia-<version>
output     = ./out/greia-<version>-<profile-id>.greiaupdate
```

For the example above, the default output is:

```text
./out/greia-0.14.0-acer-aspire-one-i386-ab.greiaupdate
```

The explicit `--platform-family`, `--architecture`, `--profile` and `--board` flag form is a DEVELOPER-ONLY low-level seam without a profile file: mixing it with `--profile-file` is rejected, and it carries no profile slot bound, so it is never normal production. It still requires `--payload-receipt` deriving size facts from the payload artifact with the same full artifact verification, or the DEVELOPER-ONLY `--developer-allow-unverified-payload-facts` seam with manually typed sizes. On the normal `--profile-file` path the tool also derives `platform.board` (`"none"` becomes manifest board null) and enforces the profile-owned `storage.system_slot_bytes` destination bound (1536 MiB = 1610612736 for `acer-aspire-one-i386-ab`): a payload whose shrunk size or minimum does not fit that slot is refused before any bundle byte is written, so an Acer A/B payload carrying the headroom minimum from the payload example above cannot be bundled under the smaller generic single-root profile through this path (`--minimum-slot-bytes` defaults to `--payload-uncompressed-bytes`, so at exactly 1073741824 with no explicit minimum the size guard cannot discriminate).

The tool records the payload size/SHA-256, the shrunk uncompressed size
and the PERSIST schema integers in the canonical manifest and creates the
bounded bundle. It refuses to overwrite an existing output file. An
optional `--hardware-support <hardware-support.tar.zst>` member may be
included; it is genuinely optional.

**Acer release identity:** the Acer path builds the payload with `--profile-id acer-aspire-one-i386-ab` and bundles it with `--profile-file ./build/profiles/acer-aspire-one-i386-ab.toml` end to end. The generic `legacy-x86-i686` profile (still `bios-single-ext4`) is never the Acer packaging identity; using it for an Acer-sized payload carrying that headroom minimum is refused by the normal bundle path. A production-installable payload still requires the A/B image/layout builder. Do not wrap today's whole single-root disk image and call that a proven A/B update.

### Inspect/verify locally

```bash
python3 tools/greia_update.py inspect \
  ./out/greia-0.14.0-acer-aspire-one-i386-ab.greiaupdate
```

This verifies the bundle structure and the payload digest/size against the
manifest. It must succeed before distribution. There is no signature to
check and no public key to supply.

### Push to a Greia on the LAN

Using a paired Parent bearer credential:

```bash
python3 tools/greia_update.py push \
  ./out/greia-0.14.0-acer-aspire-one-i386-ab.greiaupdate \
  --url http://greia.local:8766 \
  --bearer "$GREIA_PARENT_BEARER"
```

The CLI streams the file in bounded chunks rather than reading a large system image into RAM.

### Read status

```bash
python3 tools/greia_update.py status \
  --url http://greia.local:8766 \
  --bearer "$GREIA_PARENT_BEARER"
```

The upload endpoint receives bytes only. It does not grant slot-write authority to the Parent HTTP process.

## 6. Current implementation boundary

The owner release CLI has produced real Acer bundles (Session 03 closed
2026-09-23). ADR 0038 adds source for typed `.greia_update` packages and a
stable root apply/recovery bootstrap. Python, built-in Activity, Parent
Activity and combined application packages are designed to run on a
single-root image when that image contains the bootstrap marker/helper. They
do not convert single-root storage into A/B. Full-system activation remains
limited to the A/B route.

The package builder and focused package-format tests are SOURCE evidence.
Linux build/install/runtime acceptance is
`docs/testing/2026-10-24_SOFTWARE_UPDATE_ACCEPTANCE.md`; the existing A/B,
blank-disk BIOS and slot rollback predicates remain in
`docs/testing/2026-10-23_SYSTEM_UPDATE_LINUX_ACCEPTANCE.md`. Session 04 stays
OPEN until those external predicates pass. An older installed image without
the stable bootstrap does not advertise `.greia_update`; there is no manual
bootstrap CLI. Use a current installer/reimage or a supported A/B full-system
route to an image carrying the helper.

```text
v3 full-system release builder       implemented; prior Linux build evidence
typed .greia_update format/builder   SOURCE reviewed; final gate pending
Parent durable package receipt      SOURCE reviewed; final gate pending
stable application apply/recovery   SOURCE reviewed; Linux proof OPEN
built-in and Parent Activity updates SOURCE reviewed; Linux proof OPEN
full-system A/B writer/health       existing route; Session 04 OPEN
USB/SD automatic package discovery DEFERRED
Python-only delta transport        not implemented or measured
```

The legacy Parent inbox validates `.greiaupdate` archive facts before
publishing the fixed candidate, and the privileged `SystemUpdateService`
re-checks exact machine/profile/board compatibility and PERSIST schema
readability before any inactive-slot write. The `.greia_update` endpoint
streams the typed outer package into one durable job; the stable root
bootstrap then validates member sizes/digests, canonical Activity packages,
runtime syntax and declared target selectors before staging. Both formats
use ordinary checksums for corruption detection and contain no signature
authority.

The fixed published full-system package supplies candidate identity directly.
Its discovery does not require `status.json`; missing or stale reporting state
cannot hide it or choose another file. Status reports progress, while the
device-owned job and slot journal preserve authorized work and recovery.

The bounded stores keep one current accepted job/candidate, clean stale
receive temporaries and preserve free-space reserves. A second upload cannot
race an active job. Application generation staging keeps the prior complete
generation and publishes one pointer only after validation.

No code may silently convert “backend unavailable” into in-place system mutation.

## 7. Parent API capabilities

Current semantic capabilities are:

```text
system.update.read
system.update.upload
system.update.check
system.update.prepare
system.update.restart
system.update.activate
system.update.package.install
```

`system.update.read` is available so all clients can explain system-update status honestly.

`system.update.upload` controls the legacy full-system bundle receive route.
`system.update.package.install` is advertised only when the new bootstrap
marker and stable helper are present. The typed package endpoint uses the
authenticated Parent API and is not inferred merely from file selection.

`system.update.activate` describes full-system slot activation and remains
unavailable where no A/B backend is ready. It does not gate application-code
packages, which have a separate typed apply path and still require the
profile-picker idle fence.

The installed Parent daemon remains the unprivileged `greiapanel` service with `NoNewPrivileges=yes`, `ProtectSystem=strict` and an empty capability bounding set. Slot writing/reboot/boot selection live in the privileged typed update service, not in the network-facing HTTP daemon.

## 8. Device-owned online channel

Greia reads a single static index using the image/service-owned
`GREIA_SYSTEM_UPDATE_INDEX_URL` (default
`https://www.frozenpepper.it/greia/updates/greia-updates.json`) and
`GREIA_SYSTEM_UPDATE_CHANNEL=stable|dev` (default stable). The phone does not
send a URL. No account or separate update server application is required.

The API is source-owned by `greia_parent.update_api` and `protocol`:

| Request | Body | Result |
| --- | --- | --- |
| GET `/api/v1/system/update` | none | cached inbox/job/readiness/catalog plus `software_update` job/status |
| POST `/api/v1/system/update/check` | `{}` | 202 with durable `job` |
| POST `/api/v1/system/update/prepare` | `{"release_id":"..."}` | 202 with durable `job` |
| POST `/api/v1/system/update/restart` | `{}` | 202 with durable `job` |
| POST `/api/v1/system/update/package` | binary `.greia_update`, typed media type | 202 after complete bytes and job are durable |
| POST `/api/v1/system/update/package/restart` | `{}` | 202 only for a full-system job in `ready_to_restart` |

GET retains `state`, `release`, `upload_available`, `activation_available`
and adds `activation_reason`, `check_available`, `prepare_available`,
`restart_available`, `delivery: {job, readiness, catalog}`. Clients refresh
capabilities as readiness changes. The catalog contains compatible release
facts, never a caller-selected download URL or filesystem path.

`UpdateDeliveryService` owns the online check/download/prepare operation;
`UpdateJobStore`, `UpdateCatalogClient` and `UpdateBundleReceiver` own its
storage, metadata/network and streaming. `SoftwareUpdateJobStore` owns one
durable `.greia_update` receipt and public status; the stable root bootstrap
and typed apply service own package inspection, application generation,
child-idle activation and recovery. The existing `SystemUpdateService` remains
the full-system slot-writing owner. Status reads never wait for root's serial
staging operation. Closing the Parent app does not cancel an accepted job. A
reconnect never automatically authorizes full-system reboot.

The root broker accepts only semantic Parent operations. Restart holds the
shared profile-session lock, requires explicit picker-idle evidence, rechecks
the staged transaction and records a volatile fence before systemd handoff.
New profile selection uses the same lock/fence. Missing/corrupt state refuses
restart. Successful staging is not healthy boot acceptance.

Online full-system delivery states: `checking`, `checked`, `queued`, `downloading`,
`receiving`, `verifying`, `staging`, `ready_to_restart`, `restart_pending`,
`updated`, `rolled_back`, `failed`. Exact public fields and capability gates
remain source-owned. The separate typed package job has finite states
`queued`, `validating`, `waiting_for_idle`, `applying`, `restarting`,
`applied`, `rolled_back`, `failed` and `ready_to_restart`; only full-system
packages can reach the last state. Runtime acceptance must exercise durable
acknowledgement, Parent/phone disconnection, fresh application readiness,
rollback and full-system first boot through the Parent clients.

### 8.1 Selected first channel format: `greia-updates/1` (2026-10-16)

The first concrete channel is **one static JSON index** for all platforms,
published next to the bundles on the project website, generated by
`tools/build_update_index.py` from a complete `release-report.json`:

```json
{
  "schema": "greia-updates/1",
  "updated_at": "2026-11-01T10:00:00+00:00",
  "parents_app": {"latest": "1.1.0", "minimum": "1.0.0",
                   "ios_url": "https://apps.apple.com/…", "android_url": "https://play.google.com/…",
                   "notes": {"en": "…", "it": "…"}},
  "greia_os": {"channels": {
    "stable": [{"version": "0.14.0", "release_id": "greia-0.14.0", "published_at": "2026-11-01",
                "profiles": ["acer-aspire-one-i386-ab"], "platform_family": "legacy-x86",
                "architecture": "i386", "board": "…", "notes": {"en": "…", "it": "…"},
                "update": {"url": "https://…/greia-0.14.0/acer-aspire-one-i386-ab.greiaupdate",
                           "size": 123456789, "sha256": "…"},
                "setup_image": null, "install_help_url": "https://…/how-to-update"}],
    "dev": []}}
}
```

Rules:

- Parent clients fetch it with a plain GET (no device identifiers, no query
  parameters) and compare it with the device's `GET /api/v1/system` `os`
  identity: exact profile **and** platform family **and** architecture, with
  exact board match unless the release deliberately has `board: null`.
  The device-owned channel is configured as above; native discovery also
  recognizes developer and RC identities.
- The index is discovery only: unsigned, no trust authority. Greia still
  validates compatibility and integrity before any slot write, and
  installation remains a Greia-side action (§6–7). The Parent controls the
  durable device job; it does not relay an ordinary online bundle.
- `parents_app` lets native Parent clients show "update available/required";
  the HTML client may ignore it.
- `greia_os.installers` (added 2026-10-30) lists downloadable installer
  images for the website's Downloads page, newest first per target `id`:
  `version`, `build`, `status` (`technical-preview` | `release`),
  `published_at`, `platform_family`, `architecture`, `boot`,
  `reference_hardware`, `min_media_gb`, `notes` and
  `image {url, file_name, size, sha256}`. It is written by
  `tools/build_installer_index.py`, which `tools/build_update_index.py`
  preserves. Device and Parent update readers read only `channels`, so an
  installer entry is never an update offer.

## 9. Shared-data rule

Routine system update must preserve profiles, saves, creations, progression/rewards/awards, Parent credentials and device configuration.

Before candidate confirmation, shared-state migrations must remain reversible/backward-compatible. An update cannot call itself rollback-safe if it makes the old known-good OS unable to consume shared state.

## 10. Power, free-space and interruption

Before receiving a manually uploaded bundle, the current inbox preserves a bounded free-space reserve. Before staging/activation, Greia additionally checks the applicable backend's inactive-slot capacity and safety requirements. Where power state is available, unsafe battery conditions should block activation.

Downloading/receiving an update may become resumable in a later slice; loss of connection while receiving must never corrupt the currently running OS.

## 11. Release notes

Release notes should be parent-facing and short. They are not executable instructions and must not contain HTML/remote assets that become a trust surface.

## 12. Acceptance before release enablement

Production system-update capability remains false until Greia has evidence for:

- exact bundle/integrity verification;
- canonical real-ext4 slot payload generation;
- A/B layout creation by canonical installer/builders;
- inactive-slot write bounds;
- GRUB/board-specific boot selection;
- boot attempt limiting/health confirmation;
- rollback after interrupted/broken candidate;
- shared-data compatibility/rollback;
- power/free-space handling;
- C0 disk/RAM/process/latency footprint, including the updater/backend dependency footprint;
- Parent upload and normal network delivery;
- offline removable-media delivery;
- physical Acer and ARM reference acceptance.
