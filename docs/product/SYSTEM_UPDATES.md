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
-> Greia verifies the same artifact
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

The intended flow is deliberately small.

### One-time signing key creation

On a trusted release/operator machine:

```bash
python3 tools/greia_update.py keygen \
  --private-key ./local-secrets/greia-update-ed25519-private.pem \
  --public-key ./out/greia-update-ed25519-public.pem
```

The private key must remain outside Git and outside Greia images.

A reviewed public key is installed into the image's trusted update-key directory when production update activation is enabled.

### Build an update bundle

Given a complete candidate slot payload produced by the canonical image/release builder:

```bash
python3 tools/greia_update.py build \
  --payload ./out/greia-system-slot.img \
  --version 0.14.0 \
  --release-id greia-0.14.0 \
  --platform-family legacy-x86 \
  --architecture i386 \
  --profile legacy-x86-i686 \
  --signer greia-release-main \
  --private-key ./local-secrets/greia-update-ed25519-private.pem \
  --output ./out/greia-0.14.0-legacy-x86-i386.greiaupdate
```

The tool calculates the payload size/SHA-256, canonicalizes the manifest, signs it with Ed25519 and creates the bounded bundle.

### Inspect/verify locally

```bash
python3 tools/greia_update.py inspect \
  ./out/greia-0.14.0-legacy-x86-i386.greiaupdate \
  --public-key ./out/greia-update-ed25519-public.pem
```

This must succeed before distribution.

### Push to a Greia on the LAN

Using a paired Parent bearer credential:

```bash
python3 tools/greia_update.py push \
  ./out/greia-0.14.0-legacy-x86-i386.greiaupdate \
  --url http://greia.local:8766 \
  --bearer "$GREIA_PARENT_BEARER"
```

For the current development bootstrap, the tool may also send the owner-controlled Parent pairing token through the existing legacy header where explicitly requested.

The upload endpoint receives bytes only. It does not grant slot-write authority to the Parent HTTP process.

## 6. Current implementation boundary

The first implementation slice intentionally stops before destructive activation on current machines.

Current `legacy-x86` development profiles still use:

```text
layout = bios-single-ext4
```

Therefore the correct current update status is:

```text
bundle creation/inspection     implemented source
Parent upload/queue            implemented source as the slice lands
signature/hash verification    implemented source
A/B slot activation            unavailable until proven layout/backend exists
automatic rollback             unavailable until proven layout/backend exists
```

No code may silently convert “backend unavailable” into in-place system mutation.

## 7. Future online channel

A network channel can remain intentionally simple. Conceptually:

```text
stable/<platform-family>/<architecture>/channel.json
stable/<platform-family>/<architecture>/<release>.greiaupdate
```

Channel metadata advertises the latest compatible release, size, release notes and bundle URL. The bundle's own trusted signature remains the release-authenticity boundary.

No cloud account is required merely to obtain a public Greia system update.

## 8. Shared-data rule

Routine system update must preserve profiles, saves, creations, progression/rewards/awards, Parent credentials and device configuration.

Before candidate confirmation, shared-state migrations must remain reversible/backward-compatible. An update cannot call itself rollback-safe if it makes the old known-good OS unable to consume shared state.

## 9. Power, free-space and interruption

Before staging/activation Greia must check the applicable backend's capacity and safety requirements. Where power state is available, unsafe battery conditions should block activation.

Downloading/receiving an update may be resumable in a later slice; loss of connection while receiving must never corrupt the currently running OS.

## 10. Release notes

Release notes should be parent-facing and short. They are not executable instructions and must not contain HTML/remote assets that become a trust surface.

## 11. Acceptance before release enablement

Production system-update capability remains false until Greia has evidence for:

- trusted-key provisioning/revocation strategy;
- exact bundle/signature verification;
- A/B layout creation by canonical installer/builders;
- inactive-slot write bounds;
- GRUB/board-specific boot selection;
- boot attempt limiting/health confirmation;
- rollback after interrupted/broken candidate;
- shared-data compatibility/rollback;
- power/free-space handling;
- C0 disk/RAM/process/latency footprint;
- Parent upload and normal network delivery;
- offline removable-media delivery;
- physical Acer and ARM reference acceptance.
