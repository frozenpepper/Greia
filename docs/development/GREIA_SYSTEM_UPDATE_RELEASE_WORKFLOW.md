# Greia System Update Release Workflow

**Status:** developer/release-operator runbook for the current R13B foundation  
**Date:** 2026-08-19  
**Architecture:** ADR 0030  
**Product requirements:** `docs/product/SYSTEM_UPDATES.md`  
**Tool:** `tools/greia_update.py`

This is the short practical procedure for **creating, checking and sending a Greia `.greiaupdate` package**.

It does not claim that current single-root Greia machines can activate the package. Current `bios-single-ext4` profiles intentionally advertise system-update activation as unavailable until the A/B slot backend is implemented and physically proven.

## 1. What you need

On the trusted release/operator computer:

- a current Greia repository checkout;
- Python 3;
- Python `cryptography` available for Ed25519 signing/verification;
- the private Greia release signing key, kept **outside Git**;
- a complete system-slot payload produced by the future/current applicable canonical A/B release builder;
- for pushing to a development Greia, a Parent bearer credential or the explicitly allowed development pairing token.

Never place the private release key in:

```text
Greia repository
Greia image
.greiaupdate bundle
Parent app
USB/SD release directory intended for public distribution
```

## 2. One-time key generation

For development/release-key setup:

```bash
python3 tools/greia_update.py keygen \
  --private-key ./local-secrets/greia-update-ed25519-private.pem \
  --public-key ./out/greia-update-ed25519-public.pem
```

Expected result: two PEM files. The private file is mode `0600`; the public file is distributable after review.

For real releases, key custody/rotation/revocation policy must be finalized before production update activation is enabled.

## 3. Build the package

Normal command:

```bash
python3 tools/greia_update.py build \
  --payload ./out/greia-system-slot.img \
  --profile-file ./build/profiles/legacy-x86-i686.toml \
  --version 0.14.0 \
  --private-key ./local-secrets/greia-update-ed25519-private.pem
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
signer     : greia-release-main
output     : out/greia-0.14.0-legacy-x86-i686.greiaupdate
```

The generated archive contains exactly:

```text
manifest.json
manifest.sig
payload.bin
```

The tool calculates and signs the canonical manifest containing the payload SHA-256 and exact payload size. It refuses to overwrite an existing output path.

### Current payload warning

Do **not** use today's complete `bios-single-ext4` disk image as though it were a proven A/B slot image.

The current source has the package format and delivery path; the canonical A/B **slot-payload builder** is still an R13B implementation item. Until that lands, synthetic/test payloads may exercise format/tests, but no resulting bundle is production-installable on current hardware.

## 4. Verify before distributing

```bash
python3 tools/greia_update.py inspect \
  ./out/greia-0.14.0-legacy-x86-i686.greiaupdate \
  --public-key ./out/greia-update-ed25519-public.pem
```

This must report a valid bundle and `signature_verified: true`.

Do not distribute a release if local signature verification fails.

## 5. Push to a development Greia

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
selected as the one bounded inbox candidate
```

It does **not** mean:

```text
release signature trusted
system slot written
boot slot selected
machine rebooted
update confirmed
```

Those effects belong to the future privileged `SystemUpdateService` + proven slot backend.

## 6. Check device status

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

## 7. Parents HTML app

When `system.update.upload` is advertised, Greia Parents shows a `.greiaupdate` file picker in the system/overview area and sends the file through the same Parent API endpoint.

When the capability is false, the client must not fake the feature with SSH, raw filesystem upload, `apt`, shell commands or a hidden maintenance route.

Normal future Internet update UX will ask Greia to download the release directly; the phone/browser should not relay the entire system image during an ordinary online update.

## 8. Inbox safety

The current unprivileged inbox:

- validates the bounded ZIP shape;
- validates manifest/payload size and SHA-256 consistency;
- stores candidate bytes under a content digest;
- keeps only one current untrusted candidate;
- removes stale receive temporaries;
- preserves a free-space reserve;
- hides filesystem paths from Parent API status;
- does not claim signature verification or activation authority.

The privileged updater must re-open the exact candidate and re-establish:

```text
Ed25519 trusted signer
exact platform family
exact architecture
exact profile
inactive-slot target
power/capacity preflight
rollback-capable boot backend
```

before writing a system slot.

## 9. Current verification commands

When running on an owner-controlled current checkout:

```bash
PYTHONPATH=src python3 -m unittest \
  tests.test_system_updates \
  tests.test_parent_system_updates \
  tests.test_greia_update_tool -v
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

## 10. Next implementation step

The next destructive/update-critical work is **not another HTTP endpoint**. It is:

1. measure RAUC versus a minimal custom backend on the C0/Acer floor;
2. define the canonical A/B disk layout and persistent-data partition contract;
3. make the canonical builder emit the exact inactive-slot payload consumed by `.greiaupdate`;
4. implement the privileged slot backend beneath `SystemUpdateService`;
5. implement bounded boot-attempt/health confirmation and automatic rollback;
6. prove it in VM and on physical Acer before enabling `system.update.activate`.
