# Greia System Updates — Product and Operator Requirements

**Status:** accepted product direction; implementation incremental
**Date:** 2026-09-16
**Architecture owner:** ADR 0036 (supersedes ADR 0030's release-signing requirements where they conflict)  
**Primary future phase:** R13B

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
- upload a `.greiaupdate` file;
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

### Online

The preferred normal path is device-to-server:

```text
Parent authorizes -> Greia downloads -> Greia verifies/stages
```

The phone/browser does not need to relay the full release and may disconnect after authorization.

### Parent-uploaded file

For development, offline distribution or manual recovery:

```text
parent computer has release.greiaupdate
-> upload through Greia Parents or tooling
-> Greia receives the same artifact
-> privileged updater re-checks machine/profile/board compatibility and PERSIST schema readability before any system write
```

### USB/SD

The same `.greiaupdate` file may later be discovered from removable media. Removable media is untrusted and never autorun; Greia offers the update only after bounded discovery and Parent authorization.

## 4. One artifact

All sources use exactly the same unsigned `.greiaupdate` v3 bundle. There is no separate “online update format” and “offline installer patch format.”

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
  --minimum-slot-bytes 1074790400
```

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

### Build an update bundle — normal path

Given the verified `payload.ext4.zst` produced above, point the tool at the Greia build profile. The tool derives `profile.id`, `platform.family` and `base.architecture` from that file so the operator does not retype compatibility identity by hand:

```bash
python3 tools/greia_update.py build \
  --payload ./out/payload.ext4.zst \
  --payload-uncompressed-bytes <shrunk-image-bytes> \
  --profile-file ./build/profiles/acer-aspire-one-i386-ab.toml \
  --version 0.14.0 \
  --persist-read-min 1 \
  --persist-read-max 1 \
  --persist-write 1
```

Defaults deliberately reduce release-command ceremony:

```text
release_id = greia-<version>
output     = ./out/greia-<version>-<profile-id>.greiaupdate
```

For the example above, the default output is:

```text
./out/greia-0.14.0-acer-aspire-one-i386-ab.greiaupdate
```

Advanced/test tooling may supply explicit `--platform-family`, `--architecture`, `--profile` and `--board` instead of `--profile-file`, but mixing the two forms is rejected. On the normal `--profile-file` path the tool also derives `platform.board` (`"none"` becomes manifest board null) and enforces the profile-owned `storage.system_slot_bytes` destination bound (1536 MiB = 1610612736 for `acer-aspire-one-i386-ab`): a payload whose shrunk size or minimum does not fit that slot is refused before any bundle byte is written, so an Acer A/B payload cannot be bundled under the smaller generic single-root profile through this path.

The tool records the payload size/SHA-256, the shrunk uncompressed size
and the PERSIST schema integers in the canonical manifest and creates the
bounded bundle. It refuses to overwrite an existing output file. An
optional `--hardware-support <hardware-support.tar.zst>` member may be
included; it is genuinely optional.

**Acer release identity:** the Acer path builds the payload with `--profile-id acer-aspire-one-i386-ab` and bundles it with `--profile-file ./build/profiles/acer-aspire-one-i386-ab.toml` end to end. The generic `legacy-x86-i686` profile (still `bios-single-ext4`) is never the Acer packaging identity; using it for an Acer-sized payload is refused by the normal bundle path. A production-installable payload still requires the A/B image/layout builder. Do not wrap today's whole single-root disk image and call that a proven A/B update.

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

For the current development bootstrap, the tool may instead send the owner-controlled Parent pairing token through the existing legacy header:

```bash
python3 tools/greia_update.py push \
  ./out/greia-0.14.0-acer-aspire-one-i386-ab.greiaupdate \
  --url http://greia.local:8766 \
  --legacy-token "$GREIA_PARENT_PAIRING_TOKEN"
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

The first implementation slice intentionally stops before destructive activation on current machines.

Current `legacy-x86-i686` uses:

```text
layout = bios-single-ext4
```

and does not select the reserved `system-update` package set. Therefore the correct current status is:

```text
unsigned v3 bundle creation      source implemented
bundle inspection API            source implemented
real ext4 slot payload builder   source implemented (SOURCE-level; build-host artifact run pending)
shared slot completeness gate    source implemented
Parent update status             source implemented
Parent developer upload/queue    source implemented
single fixed-candidate inbox     source implemented
privileged A/B slot activation   unavailable
boot health confirmation         unavailable
automatic rollback               unavailable
normal online channel download   not implemented yet
USB/SD update delivery           not implemented yet
```

The Parent inbox validates archive structure and the manifest's declared
payload hash/size before publishing exact bytes under one fixed
Greia-owned candidate name, but intentionally performs no signature
check: there is no signature in v3. The future privileged
`SystemUpdateService` re-checks exact machine/profile/board compatibility
and PERSIST schema readability before any inactive-slot write.

The inbox is content-addressed, keeps only the current untrusted candidate, cleans stale receive temporaries and preserves a free-space reserve. A newly received candidate cannot overwrite the bytes of an existing content-addressed artifact.

No code may silently convert “backend unavailable” into in-place system mutation.

## 7. Parent API capabilities

Current semantic capabilities are:

```text
system.update.read
system.update.upload
system.update.activate
```

`system.update.read` is available so all clients can explain system-update status honestly.

`system.update.upload` is false by default while the Parent transport is provisional plaintext HTTP. It may be explicitly enabled on the developer/owner lane to exercise the bounded inbox.

`system.update.activate` remains false on current single-root images regardless of upload availability.

The installed Parent daemon remains the unprivileged `greiapanel` service with `NoNewPrivileges=yes`, `ProtectSystem=strict` and an empty capability bounding set. Slot writing/reboot/boot selection must live in the later privileged typed update service, not in the network-facing HTTP daemon.

## 8. Future online channel

A network channel can remain intentionally simple. Conceptually:

```text
stable/<platform-family>/<architecture>/channel.json
stable/<platform-family>/<architecture>/<release>.greiaupdate
```

Channel metadata advertises the latest compatible release, size, release notes and bundle URL. The bundle's own manifest digest/size checks remain ordinary transfer/integrity aids; compatibility (profile, architecture, board, PERSIST schema) is enforced before any slot write. There is no release signature and no signing-key trust to check.

No cloud account is required merely to obtain a public Greia system update.

## 9. Shared-data rule

Routine system update must preserve profiles, saves, creations, progression/rewards/awards, Parent credentials and device configuration.

Before candidate confirmation, shared-state migrations must remain reversible/backward-compatible. An update cannot call itself rollback-safe if it makes the old known-good OS unable to consume shared state.

## 10. Power, free-space and interruption

Before receiving a manually uploaded bundle, the current inbox preserves a bounded free-space reserve. Before future staging/activation, Greia must additionally check the applicable backend's inactive-slot capacity and safety requirements. Where power state is available, unsafe battery conditions should block activation.

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
- C0 disk/RAM/process/latency footprint, including the crypto/backend dependency delta;
- Parent upload and normal network delivery;
- offline removable-media delivery;
- physical Acer and ARM reference acceptance.
