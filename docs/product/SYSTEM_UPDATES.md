# Greia System Updates — Product and Operator Requirements

**Status:** accepted product direction; implementation incremental  
**Date:** 2026-08-19  
**Architecture owner:** ADR 0030  
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
- decide whether a signature is trusted;
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
-> privileged updater later re-verifies trust before any system write
```

### USB/SD

The same `.greiaupdate` file may later be discovered from removable media. Removable media is untrusted and never autorun; Greia offers the update only after bounded discovery and Parent authorization.

## 4. One artifact

All sources use exactly the same signed `.greiaupdate` bundle. There is no separate “online update format” and “offline installer patch format.”

Current bundle contract is source-owned by:

```text
src/greia_platform/system_updates.py
```

The target shape is:

```text
release.greiaupdate
├── manifest.json
├── manifest.sig
└── payload.bin
```

The first release implementation uses whole-system slot payloads. Delta transport may be added later behind the same semantic service.

## 5. Simple release-creation workflow

The repository provides one operator tool:

```text
tools/greia_update.py
```

The intended flow is deliberately small. Signing/verification requires Python's reviewed `cryptography` package on the release/operator machine. Greia's future production verifier dependency is isolated in `build/package-sets/system-update.txt`; current single-root images do not include that package set yet.

### One-time signing key creation

On a trusted release/operator machine:

```bash
python3 tools/greia_update.py keygen \
  --private-key ./local-secrets/greia-update-ed25519-private.pem \
  --public-key ./out/greia-update-ed25519-public.pem
```

The private key must remain outside Git and outside Greia images.

A reviewed public key is installed into the image's trusted update-key directory when production update activation is enabled.

### Build an update bundle — normal path

Given a complete candidate **system-slot payload** produced by the canonical release builder, point the tool at the Greia build profile. The tool derives `profile.id`, `platform.family` and `base.architecture` from that file so the operator does not retype compatibility identity by hand:

```bash
python3 tools/greia_update.py build \
  --payload ./out/greia-system-slot.img \
  --profile-file ./build/profiles/legacy-x86-i686.toml \
  --version 0.14.0 \
  --private-key ./local-secrets/greia-update-ed25519-private.pem
```

Defaults deliberately reduce release-command ceremony:

```text
release_id = greia-<version>
signer     = greia-release-main
output     = ./out/greia-<version>-<profile-id>.greiaupdate
```

For the example above, the default output is:

```text
./out/greia-0.14.0-legacy-x86-i686.greiaupdate
```

Advanced/test tooling may supply explicit `--platform-family`, `--architecture` and `--profile` instead of `--profile-file`, but mixing the two forms is rejected.

The tool calculates the payload size/SHA-256, canonicalizes the manifest, signs it with Ed25519 and creates the bounded bundle. It refuses to overwrite an existing output file.

**Important current boundary:** today's canonical `legacy-x86-i686` profile is still `bios-single-ext4`; its normal builder does not yet produce an installable A/B slot payload. The command above defines the release packaging workflow now, but a production-installable payload requires the later R13B A/B image/layout builder. Do not wrap today's whole single-root disk image and call that a proven A/B update.

### Inspect/verify locally

```bash
python3 tools/greia_update.py inspect \
  ./out/greia-0.14.0-legacy-x86-i686.greiaupdate \
  --public-key ./out/greia-update-ed25519-public.pem
```

This verifies the bundle structure, payload digest and Ed25519 signature against the supplied public key. It must succeed before distribution.

### Push to a Greia on the LAN

Using a paired Parent bearer credential:

```bash
python3 tools/greia_update.py push \
  ./out/greia-0.14.0-legacy-x86-i686.greiaupdate \
  --url http://greia.local:8766 \
  --bearer "$GREIA_PARENT_BEARER"
```

For the current development bootstrap, the tool may instead send the owner-controlled Parent pairing token through the existing legacy header:

```bash
python3 tools/greia_update.py push \
  ./out/greia-0.14.0-legacy-x86-i686.greiaupdate \
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
signed bundle creation           source implemented
bundle inspection/signature API  source implemented
Parent update status             source implemented
Parent developer upload/queue    source implemented
single-candidate bounded inbox   source implemented
A/B slot payload builder         NOT implemented
trusted key installation         NOT enabled on current profiles
privileged A/B slot activation   unavailable
boot health confirmation         unavailable
automatic rollback               unavailable
normal online channel download   not implemented yet
USB/SD update discovery          not implemented yet
```

The Parent inbox validates archive structure and the signed manifest's declared payload hash/size before storing exact bytes, but intentionally reports `signature_verified = false`: receiving bytes in an unprivileged HTTP process is not the release-trust boundary. The future privileged `SystemUpdateService` re-verifies the Ed25519 signature against installed trusted Greia public keys and checks exact machine/profile compatibility before any inactive-slot write.

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

Channel metadata advertises the latest compatible release, size, release notes and bundle URL. The bundle's own trusted signature remains the release-authenticity boundary.

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

- trusted-key provisioning/revocation strategy;
- exact bundle/signature verification;
- canonical A/B slot payload generation;
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
