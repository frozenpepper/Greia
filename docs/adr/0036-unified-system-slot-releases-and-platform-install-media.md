# ADR 0036 — Unified System-Slot Releases and Platform Install Media

**Status:** ACCEPTED  
**Date:** 2026-09-15  
**Scope:** release building, `.greiaupdate`, fresh installation media, Parent-delivered updates, ARM64/Raspberry Pi, x86 boot backends  
**Extends:** ADR 0013, ADR 0014, ADR 0030  
**Supersedes where conflicting:** the single-binary universal-media product requirement and Pi hot-insert-as-primary-install-flow in `docs/architecture/UNIVERSAL_GREIA_SETUP_MEDIA_ARCHITECTURE.md`

## 1. Decision

Greia has **one system-release model** and several thin platform media/boot adapters.

For each release-capable build profile, the canonical operating-system artifact is one **complete relocatable system-slot filesystem image**. It contains the full Greia userspace for that profile. It is not a bootstrap filesystem, package list, partial tree, test skeleton, or installer reconstruction input.

That exact slot image is wrapped in the signed `.greiaupdate` bundle defined by ADR 0030. The same signed bundle is consumed by:

1. fresh installation;
2. Parent-delivered system update;
3. removable/offline update;
4. factory/install-media creation.

No installer-specific second OS payload format is allowed.

## 2. Canonical system-slot image

The canonical slot image is:

- an ext-family relocatable filesystem image with no MBR/GPT partition table;
- produced from the same profile-driven rootfs composition authority used for Greia target images;
- complete enough to boot as the base Greia OS after bounded platform finalization;
- profile/architecture/platform identified by embedded Greia build/profile facts;
- carrying the package-management/runtime facilities required by the current offline machine-specific finalizer, including `dpkg`/`apt-get` while that finalizer remains package based;
- carrying the kernel/userspace inputs required by the profile; platform boot adapters may copy/render candidate boot-partition assets from the verified slot during finalization;
- signed only after semantic validation proves it is a complete Greia slot image.

`build_update_bundle()` may not sign an arbitrary structurally-valid ext filesystem as a production `system-slot-image`. The V12E/V12F/V12G 64 MiB `{etc,lost+found,run,var}` payload class is invalid by architecture even though it was structurally relocatable.

## 3. Rootfs composition ownership

There is one target-root composition pipeline.

The builder must factor current `build/build-image.sh` target-root construction into reusable composition primitives rather than creating a second ARM builder or a second update-root builder. Disk-image builders, release-slot builders, and factory-media builders consume the same composed root/profile authority.

Platform-specific code is limited to package/repository selection that is genuinely profile specific, boot assets, partition layout, boot selection, storage eligibility, and hardware acceptance.

## 4. Signed release bundle

`.greiaupdate` schema v2 remains the release transport unless implementation proves a new field is strictly required. D6 is **not** grounds for a schema version bump by itself.

A production bundle contains the canonical complete slot image plus the already-defined signed hardware-support member and persistent-state contract. Signature, compatibility and monotonic release-sequence checks remain platform authority.

One Greia release version uses one monotonically increasing release sequence across the release matrix. Each profile gets its own signed bundle because profile compatibility remains exact.

Private signing keys never ship on devices, installer media, source control, or Parent clients.

## 5. Hardware finalization

The existing shared `SlotWriter`/`SlotFinalizer` remains the common install/update path.

The machine-specific hardware-support step remains **offline and release-bound**. The current verified support pool may be installed with `apt-get` inside the mounted candidate slot; this is acceptable because the canonical slot is now a complete Debian/Greia root. Do not redesign the finalizer into static file copying merely to accommodate an invalid partial payload.

The finalizer may specialize a complete slot. It does not construct the base OS.

## 6. A/B update semantics

All newly supported release profiles are A/B from first install:

```text
boot authority
system A
system B
PERSIST
```

Routine update writes only the inactive slot, verifies/finalizes it, arms one candidate boot, and accepts it only after Greia reaches the trusted interactive-health point. Failure or missing confirmation returns to the previously accepted slot. PERSIST is not replaced by routine system updates.

Existing single-root installs are not remotely repartitioned by ordinary update. They require reinstall/migration media.

## 7. Boot backends

Common code owns candidate/accepted semantics; boot mechanics are polymorphic.

- legacy/modern x86 A/B: `grub-ab-v1`;
- Raspberry Pi A/B: `pi-tryboot-ab-v1`, using Raspberry Pi firmware `tryboot`/`autoboot.txt`, never GRUB or U-Boot merely for abstraction symmetry.

For Pi, boot-partition candidate assets are produced from the verified candidate slot and board adapter, written to the inactive Pi boot partition, verified, then armed through native one-shot tryboot. Health commit updates the normal `autoboot.txt` default. A failed tryboot naturally returns to the previous default because the tryboot flag is one-shot.

Routine Greia install/update does not rewrite Raspberry Pi EEPROM to obtain update semantics.

## 8. ARM64 / Raspberry Pi product profiles

Raspberry Pi 400 and Raspberry Pi 500 are first-class ARM64 targets and remain distinct build profiles because they are different boot generations:

```text
raspberry-pi-400-arm64-ab
raspberry-pi-500-arm64-ab
```

They share common Greia ARM64 userspace/package sets wherever possible. Board adapters own the differing firmware/DTB/kernel boot composition.

The ARM base remains Debian-compatible and uses the reviewed Raspberry Pi package repository only for Raspberry Pi kernel/firmware/board support required for these profiles. Repository keys are pinned in Greia build trust; no curl-pipe-shell or runtime package download is introduced.

Initial Pi graphics uses the existing Greia X/SDL appliance path on KMS/DRM-capable Raspberry Pi drivers. Direct DRM/KMS remains a later graphics optimization and does not block ARM parity.

## 9. Build-host strategy

The official build environment is a supported x86_64 Linux build host. It may build:

- i386 natively/chroot-compatible;
- amd64 natively;
- arm64 with `qemu-aarch64-static`/binfmt for build-time chroot execution.

A build preflight must fail clearly when the required cross-architecture execution support is absent. Containers and VMs are not part of the product build architecture and are not required by this decision.

## 10. Installation media: one command, not one magical binary

Greia standardizes the **media creation workflow**, not a single cross-firmware disk image.

The previous requirement that one exact removable image boot legacy BIOS, UEFI and Raspberry Pi made release construction and physical acceptance unnecessarily coupled. It is no longer a release blocker.

The operator uses one release/media tool and the same signed bundles, but it emits platform-appropriate media:

- legacy/modern PC: bootable Greia Setup USB image that runs the graphical installer and installs the selected signed bundle to an eligible internal disk;
- Raspberry Pi 400/500: ready-to-flash factory image for microSD/USB, already laid out as Pi boot-control + boot A/B + system A/B + PERSIST and seeded from the same signed bundle.

For Pi, direct flashing is the ordinary fresh-install path. A future Pi recovery/setup USB may be provided, but microSD hot insertion is not a prerequisite for first-class Pi support.

This is still one architecture: factory media is a container generated from the signed release, not a second release payload.

## 11. Parent update UX

The Parent application never signs releases and never receives root/shell/package-manager authority.

Initial ordinary update UX is deliberately simple:

```text
Parent -> System Update -> Choose Greia update file
-> upload/queue
-> device verifies compatibility/signature/sequence
-> device stages inactive slot
-> "Ready to restart"
-> parent confirms restart
-> Greia accepts after healthy interactive boot or rolls back automatically
```

The browser may display release/version/profile/progress/error state. It may not select raw slots, partitions, commands or mount paths.

Automatic online release discovery can be added later without changing the activation contract.

## 12. Operator release UX

One high-level Greia release CLI becomes the supported production entry point. Exact command names are source-owned, but the product workflow is:

```text
build one profile
build the supported release matrix
inspect/verify artifacts
create platform install media from a built release set
```

The high-level builder owns profile resolution, canonical root composition, semantic slot validation, signing, checksums, media generation and a machine-readable release report. Low-level bundle APIs remain reusable implementation plumbing, not the normal production release recipe.

## 13. Rejected alternatives

Rejected as normal architecture:

- 64 MiB/minimal placeholder filesystems signed as production system slots;
- separate installer root payload and update root payload for the same profile;
- package-by-package mutation of the active root;
- constructing the base OS during finalization;
- GRUB/U-Boot on Raspberry Pi merely to reuse x86 code;
- ordinary Pi install depending on hot-inserting microSD after USB boot;
- one universal setup-image hash as a release blocker;
- worker-selected ad-hoc package copying instead of the verified finalizer;
- Parent-side signing, `apt`, `dd`, mount, shell or boot-slot authority;
- automatic destructive repartition of existing single-root systems.

## 14. Consequence

D6 is resolved on the **release composition side**: production slot payloads become what the already-accepted update architecture says they are — complete system-slot images. The next implementation plan must finish that path first, then close the legacy-x86 lifecycle once, and immediately continue into ARM64/Pi instead of opening another architecture-design cycle.
