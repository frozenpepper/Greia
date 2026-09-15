# ADR 0036 — Simple Multiplatform Releases, A/B Updates, and One Universal Setup Image

**Status:** ACCEPTED — owner-corrected architecture  
**Date:** 2026-09-15  
**Scope:** release building, `.greiaupdate`, universal installation media, Parent updates, x86, ARM64 and Raspberry Pi  
**Extends:** ADR 0013 and ADR 0014  
**Supersedes where conflicting:** ADR 0030's cryptographic release-signing / anti-tamper requirements and the earlier same-day ADR 0036 text that split installation into platform-specific public images  
**Reaffirms:** the single universal Greia Setup image is a product requirement

## 1. Product decision

Greia gets one simple lifecycle architecture:

```text
profile-driven Greia rootfs
        |
        v
complete relocatable system-slot image
        |
        v
.greiaupdate
        |
        +--------------------------+
        |                          |
        v                          v
universal Setup image        Parent update
        |                          |
        v                          v
fresh A/B install            inactive A/B slot
        |                          |
        +------- boot health ------+
                 |
          accept or rollback
```

There is **one user-facing Greia Setup image**. The same image must boot the supported legacy-PC, modern-PC and Raspberry Pi setup paths.

There is **one OS composition pipeline**. Fresh installation and system update use the same complete per-profile system-slot artifact. There is no installer-only OS payload and no update-only OS payload.

There is **no hostile-tamper threat model for release files**. Greia is a family appliance, not a secure-boot distribution system. A parent or developer manually modifying a file is not an architecture problem.

## 2. What safety actually matters

Keep safeguards only for real failure modes:

- writing the wrong physical disk;
- losing power or crashing during an update;
- booting a broken new release;
- installing a release for the wrong architecture/profile;
- obviously corrupt or incomplete release files;
- accidentally producing an update payload that does not contain a usable Greia OS.

Do **not** build architecture for:

- malicious local file tampering;
- proving publisher identity cryptographically;
- hiding or protecting release contents;
- preventing a knowledgeable owner from downgrading;
- preventing manual modification of Greia files;
- treating hashes/signatures as governance or authority.

A checksum may be used internally as an ordinary corruption diagnostic if already cheap/useful. It is not an authorization mechanism, release identity, or acceptance gate. No worker may grow a security subsystem around it.

## 3. `.greiaupdate` is a simple local release bundle

The update artifact remains named:

```text
.greiaupdate
```

It contains a small manifest plus the complete system-slot payload and, where needed, the hardware-support payload used by finalization.

Conceptually:

```text
manifest.json
payload.bin
hardware-support/ or equivalent existing bounded member
```

The manifest carries practical facts only:

```text
format version
Greia version
profile id
architecture
platform/board compatibility
payload size
optional corruption checksum
```

No private keys. No public-key store. No signature. No signer identity. No anti-rollback cryptographic sequence. No trust ceremony.

The update service accepts a bundle when it is structurally readable, compatible with the current machine/profile, fits the inactive slot, and contains a complete Greia system image.

Downgrade policy is simple product UX: ordinary UI can warn when selecting an older version; an explicit parent/developer choice may proceed. It is not a security boundary.

## 4. The payload is the complete Greia OS

`payload.bin` is a complete relocatable filesystem image for one system slot.

It is not:

- an empty ext4 filesystem;
- a bootstrap tree;
- a package list;
- a partial root that finalization must turn into an OS.

The V12G-style 64 MiB `{etc,lost+found,run,var}` payload is therefore invalid production output.

The base OS is built once. Finalization may add machine-specific firmware/microcode and boot artifacts, but it does not construct the operating system.

## 5. One rootfs composition authority

Refactor the existing `build/build-image.sh` composition logic into reusable build primitives.

The same composer produces the canonical target root for:

```text
legacy i386
modern amd64
arm64 / Pi 400
arm64 / Pi 500
```

Architecture/profile differences are data and adapters, not copied build pipelines.

From the composed root we may derive:

```text
system-slot image
live installer root
raw development/test image
```

but they all come from the same composition authority.

Do not create a copied `build-arm-image.sh` that duplicates the x86 build logic. Do not create an update-only root builder.

## 6. Cheap completeness validation, not security validation

Before packaging a production `.greiaupdate`, run a fast mounted/chroot smoke check that proves the slot is actually usable.

Check practical essentials such as:

- profile/architecture metadata exists;
- Greia runtime files exist;
- systemd/userspace needed by the profile exists;
- Python and key Greia imports run;
- kernel/initramfs inputs exist where required;
- `apt-get`/`dpkg` exist while the current offline hardware-finalizer needs them;
- the filesystem fits the configured slot;
- a deliberately minimal filesystem is rejected.

This exists to catch builder mistakes like D6 in seconds instead of discovering them after a long QEMU run.

It is **not** a tamper detector and must not evolve into one.

## 7. A/B remains because it is simple and useful

All newly supported installations use:

```text
system A
system B
PERSIST
boot-selection state
```

Routine update:

```text
current system = A
-> write complete new release to B
-> finalize B
-> mark B as next boot
-> reboot
-> Greia reaches usable Shell/health point
   -> B becomes current
OR
-> boot/health fails
   -> return to A
```

The same works in reverse on the next update.

PERSIST contains child profiles, saves, settings and Parent data and is not replaced by routine OS updates.

This is failure recovery, not security machinery.

## 8. Shared installer/update implementation

Keep the existing shared `SlotWriter` / `SlotFinalizer` direction.

Both fresh install and update use the same basic operation:

```text
choose destination system slot
-> write complete system-slot image
-> mount it
-> perform bounded machine-specific finalization
-> write boot assets/state
-> verify basic usability
```

Do not build parallel installer and updater implementations.

Hardware finalization remains offline. Network access is not required while installing or applying an update.

## 9. One universal Setup image is mandatory

The release produces one public setup artifact:

```text
greia-setup-<version>.img
```

That image is a compatibility container with several small boot paths. It does **not** pretend all firmware families are identical.

Recommended layout:

```text
MBR partition table

P1  FAT32  GREIA_SETUP_BOOT  active
    |
    +-- SYSLINUX legacy-BIOS files + i386 kernel/initramfs
    +-- EFI/BOOT x86-64 UEFI files + amd64 kernel/initramfs
    +-- Pi 400 firmware/boot files
    +-- Pi 500 firmware/boot files
    `-- small setup metadata

P2  Linux data filesystem  GREIA_SETUP_DATA
    |
    +-- live/i386/rootfs.squashfs
    +-- live/amd64/rootfs.squashfs
    +-- live/arm64/rootfs.squashfs
    +-- releases/acer-aspire-one-i386-ab.greiaupdate
    +-- releases/standard-amd64-ab.greiaupdate
    +-- releases/raspberry-pi-400-arm64-ab.greiaupdate
    `-- releases/raspberry-pi-500-arm64-ab.greiaupdate
```

The legacy Acer path keeps the already-proven active-FAT32 + SYSLINUX removable boot method.

Modern PC firmware uses the UEFI files on the same FAT partition.

Raspberry Pi firmware uses its board-appropriate files on the same FAT partition.

After the kernel starts, the architecture-appropriate live root mounts P2 and runs the same Greia installer application.

The image does not need cryptographic self-identity or hash-based authority. Setup-media self-exclusion uses the actually mounted physical device ancestry so the installer does not erase its own USB.

## 10. Raspberry Pi support is first-class

Supported ARM profiles:

```text
raspberry-pi-400-arm64-ab
raspberry-pi-500-arm64-ab
```

They share one ARM64 Greia userspace where possible. Board adapters own only the Pi-4/BCM2711 versus Pi-5/BCM2712 firmware/kernel/DTB differences.

Unknown ARM hardware does not silently map to a Pi profile; the installer simply says the hardware is unsupported.

Initial Pi graphics uses the existing Greia X/SDL/Pygame appliance path with appropriate KMS/DRM drivers. Direct DRM/KMS is later optimization work and does not block ARM support.

## 11. Raspberry installed layout and updates

Pi uses the already-designed native layout:

```text
P1  FAT32  boot-control
P2  FAT32  boot-A
P3  FAT32  boot-B
P4         extended container where needed
P5  ext4   system-A
P6  ext4   system-B
P7  ext4   PERSIST
```

Pi update boot selection uses Raspberry Pi firmware `tryboot` / `autoboot.txt` through the `pi-tryboot-ab-v1` adapter.

No GRUB or U-Boot is added merely for abstraction symmetry.

No automatic EEPROM rewriting is part of routine Greia update/install.

The Pi backend only needs to provide the same simple semantic operations as x86:

```text
current_slot()
stage_next(slot)
commit(slot)
rollback/default_previous()
```

## 12. PC installed layouts

Legacy x86 keeps:

```text
legacy-bios-ab-v1
GRUB A/B boot backend
```

Modern amd64 uses:

```text
modern-gpt-ab-v1
UEFI-capable GRUB A/B boot backend
```

Do not make Secure Boot or cryptographic boot-chain work a blocker for the core lifecycle unless the owner separately decides to support/certify it as a product feature. Ordinary UEFI boot is required; hostile boot-chain protection is not.

## 13. Universal Setup installation flow

### PC

```text
flash the one Greia Setup image to USB
-> boot USB
-> graphical Greia installer
-> installer identifies compatible profile
-> choose eligible internal disk
-> confirm erase/install
-> create A/B + PERSIST
-> install complete Greia system to A
-> configure boot backend
-> reboot
```

### Raspberry Pi 400 / 500

Preferred flow using the same Setup image:

```text
flash the one Greia Setup image to USB
-> boot Pi from USB
-> installer identifies Pi model
-> choose the built-in target microSD
-> confirm erase/install
-> create Pi boot A/B + system A/B + PERSIST
-> install Greia to A
-> reboot from microSD
```

Physical testing decides the practical boot-order/card-insertion instructions for Pi 400 and Pi 500. If an existing bootable card prevents USB setup boot, recovery instructions may require removing it for initial USB boot and inserting it when the installer is running. That is a UX/firmware behavior to document, not a reason to create a second image.

## 14. Parent update UX

Keep it boring:

```text
Parent app
-> System Update
-> Choose .greiaupdate file
-> Greia checks "is this for this machine and does it look complete?"
-> write inactive slot
-> Ready to restart
-> Restart & Update
-> successful Greia boot: done
   or
-> failed boot: previous system comes back
```

No release keys, certificates, signing UI, raw partitions, shell commands, package-manager UI or slot-selection UI.

Later, optional Internet update discovery can download the same `.greiaupdate` automatically. It does not change the updater.

## 15. Owner release/build workflow

Create one high-level release CLI, preferably:

```text
tools/greia_release.py
```

Supported workflow:

```text
doctor
build-profile
build-matrix
build-setup-image
inspect
```

Normal release operation should be approximately:

```bash
sudo python3 tools/greia_release.py doctor
sudo python3 tools/greia_release.py build-matrix --version <VERSION> --output <DIR>
sudo python3 tools/greia_release.py build-setup-image --release-dir <DIR>
```

No signing key argument. No key generation step. No trust-store maintenance.

The release directory should contain understandable ordinary files:

```text
release-report.json
releases/<profile>.greiaupdate
greia-setup-<version>.img
```

Optional checksums may be emitted for download/copy troubleshooting, but they are informational only.

## 16. Build host and ARM cross-build

Official release builder: x86_64 Linux.

It builds:

- i386;
- amd64;
- arm64 using `qemu-aarch64-static`/binfmt where chroot execution is needed.

`doctor` checks only practical build prerequisites: tools, disk space, privileges needed by image creation, qemu/binfmt for ARM, profiles and package repositories.

No Docker or VM requirement is introduced.

## 17. Existing single-root installs

Do not implement remote in-place repartitioning in this project slice.

Old single-root Greia systems show a simple Parent message that this update generation requires reinstalling with the current universal Setup image. Portable user data migration/backup is handled separately.

## 18. Testing philosophy

Use only three useful layers:

1. **fast build/artifact smoke tests** — catch missing OS files, wrong profile, oversized slot, invalid media composition;
2. **QEMU/loop tests** — exercise installer/update transaction logic without risking hardware;
3. **physical tests** — firmware boot, Pi behavior and real-device install/update/rollback.

Do not create new governance gates, evidence authorities, cryptographic identities or hash-equality rituals around these tests.

A test result answers one question: did the thing work?

## 19. Definition of done

This architecture is complete when:

```text
one universal Setup image boots the supported Acer, modern PC, Pi 400 and Pi 500 paths
AND the graphical installer works on all of them
AND all new installs create A/B + PERSIST
AND the same rootfs composition builds install/update payloads
AND Parent can apply a local .greiaupdate without technical Linux knowledge
AND a normal update replaces only the inactive slot
AND a broken candidate returns to the previous slot
AND child/Parent data survives OS replacement
AND one Linux build host can produce i386 + amd64 + arm64 releases and the universal image
```

Nothing in this definition requires protection against a user manually editing Greia files.
