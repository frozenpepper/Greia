# ADR 0036 — Simple Multiplatform Releases, A/B Updates, and One Universal Setup Image

**Status:** ACCEPTED — owner-corrected and adversarially reviewed architecture  
**Date:** 2026-09-15  
**Scope:** release building, `.greiaupdate`, universal installation/recovery media, Parent updates, x86, ARM64 and Raspberry Pi  
**Extends:** ADR 0013 and ADR 0014  
**Supersedes where conflicting:** ADR 0030's cryptographic release-signing / anti-tamper requirements and the earlier same-day ADR 0036 text that split installation into platform-specific public images  
**Reaffirms:** the single universal Greia Setup image is a product requirement

## 1. Product decision

Greia has one simple lifecycle architecture:

```text
profile-driven Greia composition
        |
        v
complete relocatable system-slot image
        |
        v
compressed .greiaupdate
        |
        +--------------------------+
        |                          |
        v                          v
ONE universal Setup image      Parent update
        |                          |
        v                          v
fresh/recovery A/B install     inactive A/B slot
        |                          |
        +------- boot health ------+
                 |
          accept or preserve previous
```

There is **one user-facing Greia Setup image**. The same image boots supported legacy-PC, modern-PC, Pi 400 and Pi 500 setup paths.

There is **one OS composition engine**. Fresh installation and system update use the same complete per-profile target-root release. There is no installer-only OS payload and no update-only OS payload.

There is **no hostile-tamper threat model for Greia release files**. A parent/developer deliberately editing local release files is not an architecture problem.

## 2. Safety scope

Keep safeguards for real product failures:

- writing the wrong physical disk;
- losing power or crashing during an update;
- booting a broken candidate;
- installing a release for the wrong architecture/profile/board;
- truncated/corrupt/unusable payloads;
- accidentally producing an update payload that is not a complete Greia OS;
- exhausting update staging space;
- breaking low-memory installer operation;
- reinstalling/updating an OS that cannot read the current PERSIST schema.

Do not create architecture for malicious local file tampering, publisher-identity proof, Greia release signing keys, cryptographic anti-rollback, or hashes/signatures as activation authority.

Checksums may exist as ordinary transfer/debug aids only.

## 3. `.greiaupdate` v3

Greia uses one deliberately simple pre-release bundle format:

```text
manifest.json
payload.ext4.zst
hardware-support.tar.zst     # optional
```

The outer container is ZIP; already-compressed `.zst` members are stored without double compression.

The manifest carries practical facts only:

```text
format version
Greia version
profile id
architecture
platform family
board id or none
uncompressed payload bytes
minimum destination slot bytes
persist_read_schema_min
persist_read_schema_max
persist_write_schema
optional hardware-support presence/size
optional short release notes
```

No signature member, signer identity, key id or security sequence exists.

The old signed experimental format is rejected with a clear rebuild/migration message rather than supported indefinitely.

## 4. Complete OS payload, compressed only for transport

The uncompressed payload is a complete relocatable ext4 image for one system slot.

Build path:

```text
composed target root
-> populate ext4 image
-> filesystem check
-> shrink filesystem
-> practical Greia completeness smoke
-> zstd compression
-> .greiaupdate
```

Install/update path:

```text
payload.ext4.zst
-> stream decompression directly to destination system slot
-> expected raw-byte count check
-> fsync
-> filesystem consistency check
-> expand filesystem to slot capacity
-> mount
-> Greia completeness smoke
-> machine-specific finalization
```

The device does not require a second full uncompressed payload temporary file.

The V12G-style 64 MiB `{etc,lost+found,run,var}` payload is invalid production output.

## 5. One composition engine with explicit artifact roles

The shared build engine supports:

```text
compose_root(profile, role="target")
compose_root(profile, role="live-installer")
```

Common primitives own base/debootstrap, repositories, package-set resolution, Greia overlay/runtime/assets, system-service composition, metadata and footprint hygiene.

Role-specific package sets/overlays are explicit inputs. Architecture/board differences are profile data and adapters, not copied build scripts.

## 6. A/B + PERSIST

All newly supported installations use:

```text
boot-selection state
system A
system B
PERSIST
```

Routine update writes only the inactive slot. The previous accepted slot remains the normal boot default until the candidate reaches Greia health and is committed.

PERSIST contains durable child/Parent/device state and one small ordinary schema marker, conceptually:

```json
{"schema_version": 1}
```

Before trial/update/recovery, current PERSIST schema must fall inside the candidate release's declared readable range.

Before candidate acceptance, migrations must remain backward compatible or transactionally reversible so the previous accepted slot can still recover. After acceptance, the release may advance the PERSIST schema through its normal migration path.

Fresh install writes only A as a valid system. B is formatted but empty/unavailable until the first later update. Fresh A begins as `first_boot_pending`; the first healthy Greia boot marks it accepted.

## 7. Shared writer/finalizer and bounded staging

Fresh install and update share the same `SlotWriter` / `SlotFinalizer` direction:

```text
select destination
-> stream complete slot filesystem
-> check/expand/mount
-> practical Greia smoke
-> bounded machine-specific finalization
-> generate platform boot assets
```

Hardware finalization remains offline. No network APT is used during normal install/update.

Greia stores at most one compressed update candidate. Upload uses a temporary file followed by atomic rename to a fixed candidate. The large candidate is removed after the inactive slot and boot assets are prepared; only small status/journal state remains across reboot.

Before upload/stage, require enough PERSIST free space for the compressed candidate plus a 256 MiB operating reserve.

## 8. Candidate validity is practical usability

Before arming a candidate, prove:

- decompression finished normally;
- expected raw bytes were written;
- destination write was flushed;
- ext filesystem is consistent and mountable;
- architecture/profile/board matches;
- current PERSIST schema is readable;
- Greia runtime/system essentials are present;
- machine-specific finalization completed;
- boot assets were prepared.

This is reliability validation, not provenance/tamper validation.

## 9. One universal Setup image

The public setup artifact is one disk image, optionally distributed compressed:

```text
greia-setup-<version>.img
greia-setup-<version>.img.xz
```

They are the same image, not platform variants.

Layout:

```text
MBR partition table

P1  512 MiB FAT32  GREIA_SETUP_BOOT  active
    +-- SYSLINUX legacy BIOS + i386 kernel/initramfs
    +-- EFI/BOOT amd64 UEFI + amd64 kernel/initramfs
    +-- Pi 400 boot assets
    +-- Pi 500 boot assets
    `-- small setup boot/config metadata

P2  ext4 GREIA_SETUP_DATA
    +-- live/i386/rootfs.squashfs
    +-- live/amd64/rootfs.squashfs
    +-- live/arm64/rootfs.squashfs
    +-- releases/acer-aspire-one-i386-ab.greiaupdate
    +-- releases/standard-amd64-ab.greiaupdate
    +-- releases/raspberry-pi-400-arm64-ab.greiaupdate
    `-- releases/raspberry-pi-500-arm64-ab.greiaupdate
```

The raw image remains <= **7,400,000,000 bytes**, preserving ordinary marketed 8 GB media as the supported floor. If the complete image exceeds that, optimize compression/duplication; do not split the image.

The Acer removable path preserves active-FAT32 + SYSLINUX. Modern x86 uses the UEFI fallback path on the same FAT partition. Pi firmware uses board-filtered files on the same FAT partition.

## 10. Low-memory behavior

On the Acer-class live path:

- `toram` is forbidden;
- only selected i386 SquashFS is mounted from P2;
- amd64/arm64 files remain unused files on USB;
- writable live overlay starts at the current 128 MiB bounded tmpfs configuration.

Adding architectures to the Setup medium must not materially increase Acer idle/live-installer RAM merely because their files exist on P2.

## 11. Setup-media self-protection and target policy

After P2 is mounted, resolve its actual block partition and parent whole disk. Exclude that disk and all descendants from installer targets.

If more than one candidate `GREIA_SETUP_DATA` exists, stop with a simple instruction to remove extra Greia installer drives.

Immediately before destructive work, re-read selected target facts such as path, major:minor, capacity and serial/WWN/MMC CID where available. If changed or missing, clear selection/confirmation.

PC normal install offers eligible internal SATA/NVMe/eMMC-class storage and excludes ordinary removable USB plus Setup disk.

Pi normal fresh install targets the built-in microSD host through topology, not a hard-coded node name. Pi recovery may explicitly offer a microSD in an external USB reader after excluding Setup disk.

Every target policy verifies the complete fixed layout plus PERSIST minimum fits before confirmation.

## 12. Modern x86 compatibility includes Secure Boot without Greia signing infrastructure

The amd64 UEFI setup/installed path uses Debian-provided signed boot components (`shim-signed`, signed GRUB and distro-signed kernel packages or current source-owned equivalents).

Greia manages no Secure Boot private keys or custom trust database.

The compatibility test is simply that the universal image and installed OS boot with Secure Boot ON and OFF on supported modern x86 hardware.

## 13. Raspberry Pi live boot and USB prerequisite

Pi 400 and Pi 500 are distinct board adapters sharing one ARM64 Greia userspace/live root where possible.

The universal FAT boot partition uses official model filters:

```text
[pi400]
# Pi-4-family/Pi400 kernel/initramfs choices

[pi500]
# Pi-5-family/Pi500 kernel/initramfs choices

[all]
```

Pi 400 owns its Pi-4/BCM2711 boot path; Pi 500 owns its Pi-5/BCM2712 path. Unknown ARM hardware does not silently map to a Pi profile.

Initial graphics uses the existing Greia X/SDL/Pygame appliance path. Direct DRM/KMS is later optimization work.

Greia Setup assumes the Pi EEPROM boot order includes USB-MSD. The normal/default empty Raspberry Pi boot order tries SD then USB-MSD and repeats. If a user customized EEPROM to remove USB, Greia documentation directs them to restore a standard USB-capable boot order using Raspberry Pi's normal bootloader configuration/recovery tooling. Greia does not silently rewrite EEPROM or create a second Greia image.

## 14. Raspberry Pi installed layout and tryboot

Installed Pi layout:

```text
P1  FAT32  boot-control-recovery   256 MiB
P2  FAT32  boot-A                  256 MiB
P3  FAT32  boot-B                  256 MiB
P4         extended container as required by MBR
P5  ext4   system-A               2048 MiB
P6  ext4   system-B               2048 MiB
P7  ext4   PERSIST                remainder, minimum 1536 MiB
```

The builder rejects board boot/recovery assets that leave less than 32 MiB free headroom in P1, P2 or P3.

Use native Raspberry Pi `autoboot.txt` + one-shot `tryboot`; no GRUB/U-Boot for symmetry and no routine EEPROM rewrite.

With A accepted:

```text
[all]
tryboot_a_b=1
boot_partition=2
[tryboot]
boot_partition=3
```

After B is healthy, commit swaps normal/tryboot partition numbers. Each A/B boot partition points to its matching system root.

P1 is itself bootable and contains `autoboot.txt`, board-appropriate boot assets, and a minimal recovery kernel/initramfs. `autoboot.txt` replacement uses write-new, fsync, rename, syncfs, re-read.

If firmware falls onto P1 because `autoboot.txt` is missing/malformed, the recovery environment reads accepted-slot/layout state from PERSIST, reconstructs the normal A/B control file, syncs it and reboots. If safe accepted state cannot be determined, it only displays a bounded instruction to use the universal Setup medium.

A userspace health failure can reboot and return to the previous default. A candidate that hangs before Greia userspace may require one manual reset/power cycle; on that next boot the previous accepted default remains selected. Do not promise autonomous pre-kernel recovery without a separate watchdog.

## 15. Pi Setup fresh-install and reinstall flows

Normal fresh install:

```text
blank/unbootable microSD inserted
Setup USB inserted
power on
SD attempt fails -> USB-MSD Setup boots
install to built-in microSD
```

For existing bootable microSD, preferred reinstall after physical proof:

```text
remove card
-> boot Setup USB
-> insert card
-> Refresh Drives
-> reinstall
```

Guaranteed fallback uses the target microSD in an external USB reader while Setup USB boots; install/reinstall it there, then move it back to the built-in slot.

No second installer image is introduced.

## 16. Installed x86 layouts

Legacy i386:

```text
MBR
boot-control  64 MiB ext4
system A    1536 MiB ext4
system B    1536 MiB ext4
PERSIST     remainder, minimum 1024 MiB
GRUB A/B backend
```

Modern amd64:

```text
GPT
ESP           256 MiB FAT32
boot-control   64 MiB ext4
system A     2048 MiB ext4
system B     2048 MiB ext4
PERSIST      remainder, minimum 1536 MiB
UEFI GRUB A/B backend
```

These are product defaults.

## 17. Boot health

A candidate is committed only after Greia reaches existing platform interactive health:

```text
root mounted
PERSIST mounted read/write
critical Greia platform services running
graphical display/session running
Greia Shell interactive/profile-selection readiness
```

Kernel start alone is not acceptance. Parent API availability is not required to accept an otherwise usable child appliance.

## 18. Universal Setup is also bounded recovery media

When Setup detects a valid Greia A/B layout/profile, it may offer:

```text
Reinstall Greia, keep child data
Erase and install Greia
```

Preserve-data reinstall is offered only when PERSIST mounts for inspection and its schema is inside the bundled release's readable range.

It does not repartition or format PERSIST. It writes the matching bundled release to system A, finalizes/rebuilds boot state, clears B as a candidate and marks A first-boot-pending.

If layout/profile/schema cannot be identified safely, preserve-data reinstall is not offered.

## 19. Parent update UX

Normal Parent flow:

```text
System Update
-> Choose Update File
-> show version/profile
-> upload
-> Preparing Update
-> Ready to Restart
-> Restart & Update
-> Updated
```

If candidate userspace starts but fails Greia health, it reboots without commit and the previous version returns.

If the candidate hangs before Greia userspace, one reset/power cycle may be required.

Older bundles are not prohibited for security reasons, but ordinary update proceeds only when the candidate declares the current PERSIST schema readable. Otherwise Parent reports a data-compatibility refusal.

## 20. Owner release/build workflow

Normal release is one command:

```bash
sudo python3 tools/greia_release.py build --version <VERSION> --output <DIR>
```

It builds all target profiles, i386/amd64/arm64 live roots, boot adapters, four update bundles and the one universal Setup image, then emits `.img.xz` plus a concise release report.

Official build host is x86_64 Linux. arm64 chroot phases use `qemu-aarch64-static`/binfmt. Docker/VM is not a requirement.

## 21. Testing philosophy

Use only useful layers:

1. fast source/build/artifact smoke checks;
2. QEMU/loop lifecycle tests;
3. physical firmware/hardware tests.

Run the full repository suite at meaningful integration boundaries, not after every tiny edit.

Do not create new governance gates, artifact authorities, signed reports, evidence tokens or orchestration frameworks as part of this work.

## 22. Definition of done

This architecture is complete when:

```text
one universal Setup image is the normal installer/recovery medium
its public compressed form fits ordinary 8 GB-class media
Acer legacy BIOS boots/installs from it
modern amd64 UEFI boots/installs from it with Secure Boot ON and OFF
Pi 400 boots/installs from it
Pi 500 boots/installs from it

i386/amd64/arm64 share one composition engine with explicit target/live roles
Pi400/Pi500 share ARM64 Greia plus real board adapters
.greiaupdate is unsigned, simple and compressed for transport
no full uncompressed update temp file is required
fresh install and update share the complete target-root release artifact
all new supported installs are A/B + PERSIST
first healthy boot accepts a fresh install
bad candidates never replace the previous default before health
PERSIST schema compatibility is checked before update/recovery
PERSIST survives update, rollback and compatible preserve-data reinstall
Pi P1 provides bounded recovery from broken autoboot control state
Parent can apply a local .greiaupdate without Linux knowledge
one Linux build host creates the complete release in one normal command
```

Nothing in this definition requires protection against a user manually editing Greia files.
