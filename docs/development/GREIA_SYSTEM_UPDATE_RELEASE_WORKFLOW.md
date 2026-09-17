# Greia System Update Release Workflow

**Status:** developer/release-operator runbook for the ADR 0036 v3 flow
**Date:** 2026-09-16
**Architecture:** ADR 0036 (supersedes the old signed-bundle requirements of ADR 0030 where they conflict)
**Product requirements:** `docs/product/SYSTEM_UPDATES.md`
**Tools:** `tools/build_release.py`, `tools/greia_update.py`
**Implementation state:** Session 02 source scope complete; real-artifact build-host run pending (see `HANDOVER.md` §26)

This is the short practical procedure for **building, checking and sending a Greia `.greiaupdate` v3 package**.

The v3 bundle is unsigned and compressed. There is no signing key, no signer
identity, no signature member and no release sequence — and no `payload.bin`
or tar payload. The payload is a real relocatable ext4 slot image compressed
with zstd (`payload.ext4.zst`). Any old signed v2 bundle (`manifest.sig`,
`payload.bin`) is rejected with a rebuild/migration message, not interpreted.

It does not claim that current single-root Greia machines can activate the package. Current `bios-single-ext4` profiles intentionally advertise system-update activation as unavailable until the A/B slot backend is implemented and physically proven.

## 1. What you need

On the build/release host:

- a current Greia repository checkout;
- Python 3;
- `zstd` (payload and hardware-support compression);
- e2fsprogs (`mkfs.ext4`, `e2fsck`, `resize2fs`, `debugfs`) for the real slot image and its read-only verification;
- a composed target root for the release profile (see `build/lib/compose.sh`, role `target`), plus the generic kernel and initramfs files seeded into the image;
- for pushing to a development Greia, a Parent bearer credential or the explicitly allowed development pairing token.

There is deliberately no release signing key and no `cryptography`
requirement. Never place operator credentials in:

```text
Greia repository
Greia image
.greiaupdate bundle
Parent app
USB/SD release directory intended for public distribution
```

## 2. Build the real slot payload

Real flow (ADR 0036 §4):

```text
composed target root
-> populate ext4 image (mkfs.ext4 -d <staging>)
-> filesystem check (e2fsck -f -y)
-> shrink filesystem (resize2fs -M)
-> filesystem re-check (e2fsck -f -y)
-> Greia completeness smoke (shared slot validator + debugfs path probes)
-> zstd compression (zstd -19)
-> payload.ext4.zst
```

Normal command:

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

The producer seeds the generic kernel/initramfs plus the release identity,
then validates the staging tree with the shared slot completeness validator
(`src/greia_platform/slot_writer.py`) before any image byte is emitted: a
skeleton root (for example only `{etc, lost+found, run, var}`) is refused
before compression, naming the missing userspace paths. It refuses to
overwrite an existing output path. No privileged operations and no network
are involved.

### Current payload boundary

Do **not** wrap a whole single-root disk image, a partition table, or a tar
archive and call that a slot payload. The producer rejects images carrying
an MBR/GPT signature and rejects legacy tar bodies: the payload must be a
relocatable ext4 image, and the staging tree must carry real Greia userspace
including `usr/bin/apt-get`, `usr/bin/dpkg` and `usr/bin/env`.

## 3. Verify the payload before bundling

```bash
python3 tools/build_release.py verify-payload \
  --payload ./out/payload.ext4.zst
```

This decompresses through the build seam and proves, read-only: the zstd
framing, the ext4 superblock magic, relocatability (no MBR/GPT signature), a
clean `e2fsck -n` pass, and every required Greia path via `debugfs stat`
(userspace directories and files, the generic boot pair, build-info and the
release identity). Do not bundle a payload that fails this check.

## 4. Build the v3 bundle

Normal command:

```bash
python3 tools/greia_update.py build \
  --payload ./out/payload.ext4.zst \
  --payload-uncompressed-bytes <shrunk-image-bytes> \
  --profile-file ./build/profiles/legacy-x86-i686.toml \
  --version 0.14.0 \
  --persist-read-min 1 \
  --persist-read-max 1 \
  --persist-write 1
```

The tool reads these compatibility facts from the canonical profile:

```text
profile.id
platform.family
base.architecture
```

It defaults:

```text
release ID : greia-0.14.0
output     : out/greia-0.14.0-legacy-x86-i686.greiaupdate
```

`--payload-uncompressed-bytes` is the shrunk image size reported by the
`build-payload` step; `--minimum-slot-bytes` defaults to it. The three
`--persist-*` values carry PERSIST schema compatibility in the manifest.
An optional `--hardware-support <hardware-support.tar.zst>` member may be
included; it is genuinely optional.

The generated archive contains exactly:

```text
manifest.json
payload.ext4.zst
hardware-support.tar.zst     # only when supplied
```

The outer container is ZIP with the already-compressed `.zst` members
stored without double compression. The manifest carries practical facts
only (format version, Greia version, profile id, architecture, platform
family, board id or none, uncompressed payload bytes, minimum destination
slot bytes, PERSIST schema integers, optional hardware-support
presence/size, optional short release notes). The tool refuses to overwrite
an existing output path.

## 5. Verify before distributing

```bash
python3 tools/greia_update.py inspect \
  ./out/greia-0.14.0-legacy-x86-i686.greiaupdate
```

This reports the manifest facts and validates bundle structure, payload
digest/size and PERSIST schema fields. There is no signature to verify and
no public key to supply. Do not distribute a release that fails inspection.

## 6. Push to a development Greia

Preferred paired-device credential:

```bash
python3 tools/greia_update.py push \
  ./out/greia-0.14.0-legacy-x86-i686.greiaupdate \
  --url http://greia.local:8766 \
  --bearer "$GREIA_PARENT_BEARER"
```

Current development bootstrap alternative:

```bash
python3 tools/greia_update.py push \
  ./out/greia-0.14.0-legacy-x86-i686.greiaupdate \
  --url http://greia.local:8766 \
  --legacy-token "$GREIA_PARENT_PAIRING_TOKEN"
```

`push` streams the bundle in 1 MiB chunks. It does not load a potentially large OS image into memory.

The Parent API endpoint is:

```text
POST /api/v1/system/update/bundle
```

The network-facing Parent daemon remains unprivileged. Successful upload means only:

```text
bundle received
structure checked
payload size/hash checked
selected as the one fixed inbox candidate
```

It does **not** mean:

```text
system slot written
boot slot selected
machine rebooted
update confirmed
```

Those effects belong to the future privileged `SystemUpdateService` + proven slot backend.

## 7. Check device status

```bash
python3 tools/greia_update.py status \
  --url http://greia.local:8766 \
  --bearer "$GREIA_PARENT_BEARER"
```

On today's single-root images, expect update read/status support but:

```text
system.update.activate = false
activation_available   = false
```

That is correct, not an error to bypass.

## 8. Parents HTML app

When `system.update.upload` is advertised, Greia Parents shows a `.greiaupdate` file picker in the system/overview area and sends the file through the same Parent API endpoint.

When the capability is false, the client must not fake the feature with SSH, raw filesystem upload, `apt`, shell commands or a hidden maintenance route.

Normal future Internet update UX will ask Greia to download the release directly; the phone/browser should not relay the entire system image during an ordinary online update.

## 9. Inbox safety

The current unprivileged inbox:

- validates the bounded ZIP shape;
- validates manifest/payload size and SHA-256 consistency;
- publishes the candidate under one fixed Greia-owned name via atomic rename;
- keeps only that one current candidate;
- removes stale receive temporaries;
- deletes the large candidate after successful inactive-slot staging;
- preserves a free-space reserve;
- hides filesystem paths from Parent API status;
- performs no signature verification and claims no activation authority.

The privileged updater must re-open the exact candidate and re-establish:

```text
exact platform family
exact architecture
exact profile
board compatibility
PERSIST schema readability
inactive-slot target and capacity
power/capacity preflight
rollback-capable boot backend
```

before writing a system slot.

## 10. Current verification commands

When running on an owner-controlled current checkout:

```bash
PYTHONPATH=src python3 -m unittest \
  tests.test_system_updates \
  tests.test_parent_system_updates \
  tests.test_greia_update_tool \
  tests.test_update_v3_bundle \
  tests.test_build_release \
  tests.test_slot_writer -v
```

Then run the complete repository gate:

```bash
make verify
```

For the external Parent HTML repository:

```bash
npm test
```

Do not label the current update tranche PASS until those commands execute at the exact recorded revisions.

## 11. Next implementation step

The Session 02 source scope (canonical composer roles, real ext4 slot
producer, shared completeness validator) is complete; the remaining
Session 02 leg is one privileged Linux build-host
`build-payload` → `verify-payload` → bundle cycle to promote SOURCE-level
proof to a real-artifact run. After that, the lifecycle plan's Session 03
(owner release CLI) and Session 04 (legacy i386 lifecycle with the real
payload) are next. The next destructive/update-critical work after the
payload run is **not another HTTP endpoint**. It is:

1. wire the fresh A/B installer to the real just-built bundle;
2. initialize the PERSIST schema marker and prove schema refusal;
3. implement the privileged slot backend beneath `SystemUpdateService`;
4. implement bounded boot-attempt/health confirmation and automatic rollback;
5. prove install → healthy boot → update → commit → failed candidate → previous release in product-mode QEMU and on physical Acer before enabling `system.update.activate`.
```

Note: the old signed-bundle `keygen`/`manifest.sig`/Ed25519 workflow (ADR 0030)
is superseded by ADR 0036 and is historical only; do not use it for new releases.
