# Greia — Final Multiplatform Release / Universal Installer / Update Completion Plan

**Status:** ACTIVE — authoritative successor plan  
**Created:** 2026-09-15  
**Adversarial review:** 2026-09-15 — architecture attacked twice and revised after owner corrections  
**Owner requirement:** one universal Greia Setup image is mandatory  
**Normative architecture:** ADR 0036  
**Execution style:** direct implementation -> focused tests -> full verification only at sensible milestones -> QEMU/physical tests only when they answer something source tests cannot  
**Explicit process rule:** do not add security/governance machinery unless it prevents a concrete product failure.

---

# 0. Goal

Finish the install/update/multiplatform workstream and stop reopening its architecture.

Greia must end with this product model:

```text
ONE OWNER BUILD COMMAND
        |
        v
complete i386 / amd64 / arm64 Greia releases
        |
        +-------------------------+
        |                         |
        v                         v
ONE UNIVERSAL SETUP IMAGE     .greiaupdate files
        |                         |
        v                         v
PC / Pi fresh install         Parent app update
        |                         |
        +------------+------------+
                     v
               A/B system slots
                     |
            healthy boot -> keep
            failed boot  -> previous slot remains default
```

Supported first-class targets at completion:

```text
Acer Aspire One / legacy i386 BIOS
modern amd64 UEFI PC
Raspberry Pi 400 / arm64
Raspberry Pi 500 / arm64
```

ARM64 is a first-class Greia architecture. Pi 400 and Pi 500 are the first supported ARM boards; they are board adapters beneath common ARM/runtime/installer/update code, not a Pi-only fork.

---

# 1. Adversarial review — weaknesses found and closed by this revision

This plan was attacked as if another competent engineer were trying to prove it would waste another month. The following weaknesses were real and are now explicitly resolved below.

## R1 — The previous bundle/media design would become unnecessarily huge

Current experimental `.greiaupdate` stores a raw ext filesystem payload uncompressed inside ZIP. Four complete release payloads plus three installer live roots could make the mandatory universal image needlessly enormous.

**Decision:** the new simple bundle transports the slot image as `payload.ext4.zst`. The ext4 image is shrunk before compression and streamed through `zstd` directly into the destination slot. No full uncompressed update file is staged on PERSIST.

The public universal Setup image must fit on an ordinary marketed **8 GB** USB/SD device. Raw output maximum is **7,400,000,000 bytes**. If the first complete matrix exceeds that, reduce duplication/compress better; do not split the public image.

## R2 — The old session order tried to freeze universal media before real amd64/Pi components existed

That would force placeholder boot contracts and later rework.

**Decision:** finish real amd64 and ARM/Pi live-boot components first. Compose the universal image only after all three architecture boot paths are real.

## R3 — Pi reinstall/USB boot order was hand-waved

Raspberry Pi's normal/default EEPROM boot flow commonly tries SD before USB. A blank/unbootable target card can therefore fall through to USB, but a bootable existing card may prevent Setup USB boot. A user can also have a customized EEPROM boot order that does not include USB at all.

**Decision:** ordinary fresh install uses a blank/unbootable microSD already inserted plus the Setup USB. Reinstall/recovery uses the same image with one of two supported paths:

```text
preferred: remove card -> boot Setup USB -> insert card -> Refresh Drives
fallback:  put target microSD in an external USB card reader -> boot Setup USB -> reinstall card -> move card back
```

Built-in microSD hot insertion must be physically tested on both Pi 400 and Pi 500 before it is documented as the preferred reinstall path. If the Pi EEPROM has been customized to remove USB-MSD boot entirely, the support instruction is to restore a normal USB-capable Raspberry Pi boot order using the Raspberry Pi firmware/Imager tooling; Greia does not create a second installer image or silently rewrite EEPROM.

## R4 — “No Secure Boot” was being treated as simplification, but it hurts modern-PC compatibility

We do not need Greia signing infrastructure. We *do* want normal modern PCs to boot without telling parents to change firmware settings.

**Decision:** modern amd64 uses the Debian-provided signed shim/GRUB/kernel path where available. Greia does not create or manage its own Secure Boot keys. Secure Boot ON/OFF boot compatibility is tested as ordinary hardware compatibility, not as a security program.

## R5 — “One rootfs composer” risked conflating target roots and installer live roots

A live installer needs different packages/services from an installed child OS. Literally making them the same tree would bloat one side or contaminate the other.

**Decision:** one composition engine with explicit artifact roles:

```text
compose_root(profile, role="target")
compose_root(profile, role="live-installer")
```

Both share base/repository/profile/Greia composition primitives. Role-specific package sets and overlays are declarative inputs, not copied scripts.

## R6 — The current update inbox is content-addressed by hashes and retains a complete bundle

That is unnecessary complexity and can waste PERSIST space.

**Decision:** one candidate file only. Upload to a temporary file, atomically rename to a fixed Greia-owned candidate name, stage it, then delete the large candidate once the inactive slot and boot assets are complete. Keep only small update status metadata across reboot.

## R7 — Byte-for-byte hash readback is not the useful definition of a good slot

The failure we care about is an unusable filesystem, not proving bytes were not intentionally changed.

**Decision:** slot staging checks decompressor success, expected raw byte count, `fsync`, filesystem consistency, mountability, and the same practical Greia completeness smoke test used at build time. Hashes are not activation authority.

## R8 — Fresh-install acceptance state was underspecified

A freshly installed A slot has no previous slot to roll back to and should not immediately be treated like a proven accepted update base.

**Decision:** fresh install boots A as `first_boot_pending`. The first healthy Greia boot records A as accepted and enables normal A/B update activation. If first boot fails, recovery is the universal Setup image; empty B is not presented as a rollback copy.

## R9 — “Boot succeeded” was too vague

Kernel start is not a healthy child appliance.

**Decision:** candidate commit uses the existing Greia health path and means, at minimum:

```text
root filesystem mounted
PERSIST mounted read/write
critical Greia platform services running
graphical display/session started
Greia Shell reaches interactive/profile-selection readiness
```

The Parent API is useful but is not required to commit an otherwise usable child appliance. Do not invent a second health framework.

## R10 — A one-shot candidate does not magically reboot itself after every possible failure

A kernel/userspace health failure can trigger a controlled reboot. A candidate that hangs before Greia userspace may remain stuck until hardware reset/power cycle. This is true for both GRUB and Pi tryboot unless additional firmware watchdog state is configured.

**Decision:** do not rewrite EEPROM or add another watchdog architecture in this workstream. The guarantee is:

```text
candidate is one-shot
previous accepted slot remains the normal default until commit
if candidate health fails after userspace starts, Greia reboots to previous
if candidate hangs before that, one power cycle/reset returns to previous
```

The Parent/UI wording must not promise impossible pre-kernel self-recovery.

## R11 — Pi board boot composition was still left too vague

**Decision:** the universal Setup `config.txt` uses Raspberry Pi's model filters. Pi 400 uses `[pi400]` / the Pi-4 family path; Pi 500 uses `[pi500]` / the Pi-5 family path. The Pi 400 live boot uses the appropriate `kernel8.img` family; Pi 500 uses the `kernel_2712.img` family when provided by the selected stable Raspberry Pi kernel packages. Board DTBs/overlays coexist on the same FAT partition.

## R12 — Low-memory correctness could regress when the universal image grows

The image may contain several architectures, but the Acer must not load them into RAM.

**Decision:** no `toram`. Only the selected architecture's SquashFS is mounted from `GREIA_SETUP_DATA`; the writable live overlay starts at the current proven **128 MiB** bound. Adding amd64/ARM files to the USB must have essentially no idle-RAM cost on i386.

## R13 — The universal Setup image should be useful for recovery, not only destructive fresh install

**Decision:** when Setup detects a valid existing Greia A/B layout, it offers a simple **Reinstall Greia, keep child data** recovery operation. That operation does not repartition or format PERSIST. It rewrites one system slot from the matching release, rebuilds boot state, and makes that repaired slot the normal boot. If the existing layout cannot be identified safely, only the normal erase/install path is offered.

This is not a general rescue environment and does not expose Linux tools.

## R14 — Removing the old signed persistent-state contract must not remove data compatibility checks

Security signatures were unnecessary, but PERSIST compatibility is a real data-safety problem. An old Setup image must not offer “keep child data” and then install an OS that cannot read those saves/settings.

**Decision:** PERSIST stores one small integer schema version. Every release manifest declares the inclusive PERSIST schema range it can read during trial/recovery and the schema version it writes after accepted migrations. Candidate staging and preserve-data reinstall require the current PERSIST schema to be readable by the candidate. This is a compatibility check, not anti-rollback security.

## R15 — The Pi boot-control partition should be a real fallback, not a tiny text-file island

A power cut while replacing `autoboot.txt` is a genuine reliability failure. Depending on undocumented partition walking is unnecessary.

**Decision:** installed Pi partition 1 is a **bootable control/recovery partition**, containing `autoboot.txt` plus a minimal board-appropriate recovery kernel/initramfs. If `autoboot.txt` is missing/malformed and firmware falls back to partition 1, recovery reads the accepted-slot state from PERSIST, reconstructs `autoboot.txt`, and reboots. If PERSIST/layout cannot be read, it displays a bounded recovery message directing the parent to the universal Setup medium.

Pi boot-control and boot-A/boot-B are 256 MiB each rather than speculative 64/128 MiB sizes. Build-time asset sizing must retain at least 32 MiB free headroom in each boot filesystem.

## R16 — Pi USB boot capability is a hardware prerequisite, not something the installer can wish into existence

Raspberry Pi 4/400 and Pi 5/500 use EEPROM `BOOT_ORDER`; the normal empty/default order tries SD and then USB-MSD, but user-customized EEPROM settings may remove USB.

**Decision:** Greia Setup does not mutate EEPROM. The Pi support contract requires a USB-MSD-capable boot order. Physical acceptance records the tested boot order. Troubleshooting for a customized no-USB order points to Raspberry Pi's standard bootloader configuration/recovery tooling. The Greia product artifact remains one universal image.

---

# 2. Binding architecture decisions

Workers implementing this plan do not reopen these decisions.

## A1 — One universal Setup image is mandatory

There is one public setup image:

```text
greia-setup-<version>.img
```

The downloadable form may be the compressed representation:

```text
greia-setup-<version>.img.xz
```

`.img` and `.img.xz` are the same disk image in raw/compressed form, not different platform installers.

The image contains the boot paths and live roots required for legacy BIOS, x86-64 UEFI, Pi 400 and Pi 500.

No separate public PC/Pi installer may replace this requirement.

## A2 — No hostile-tamper architecture

Normal release/update code does not require:

```text
Greia release signing keys
manifest signatures
Greia release trust stores
cryptographic anti-rollback
hash equality as authorization
artifact identity ceremonies
```

The real protection targets are wrong-disk writes, incomplete builds, interrupted writes, incompatible payloads and broken boots.

## A3 — `.greiaupdate` v3 is a small practical container

Use one clean pre-release format break. The new format is a ZIP container:

```text
manifest.json
payload.ext4.zst
hardware-support.tar.zst     # optional; only for profiles/finalization that need it
```

ZIP stores the already-compressed `.zst` members with `ZIP_STORED`; do not double-compress them.

The manifest carries only:

```text
format_version = 3
Greia version
profile id
architecture
platform family
board id (or none)
uncompressed payload bytes
minimum destination slot bytes
persist_read_schema_min
persist_read_schema_max
persist_write_schema
hardware-support presence/size when present
optional short release notes
```

No signature, signer, key id, release security sequence, or per-member cryptographic authority.

`payload.ext4.zst` is created from a valid complete ext4 system-slot image after filesystem shrink. `zstd` is a required system-update/live-installer dependency and replaces the current cryptography-only update dependency.

## A4 — Complete OS payload; compressed only for transport

The uncompressed payload is a relocatable ext4 image containing the complete Greia target OS.

Build flow:

```text
composed target root
-> populate ext4 image
-> e2fsck
-> shrink filesystem to practical minimum
-> smoke validate
-> zstd compress
-> package .greiaupdate
```

Install/update flow:

```text
.greiaupdate payload.ext4.zst
-> stream zstd decompression
-> SlotWriter writes destination slot
-> verify raw byte count
-> fsync
-> e2fsck/read-only consistency check
-> expand filesystem to destination slot
-> mount
-> Greia completeness smoke
-> machine-specific finalization
```

No complete uncompressed payload temp file is required on the device.

## A5 — One composition engine, two explicit artifact roles

Refactor the current `build/build-image.sh` responsibilities into reusable build primitives rather than another monolithic script copy.

Common primitives own:

```text
base/debootstrap
architecture-aware repositories
profile/package-set resolution
Greia overlay/runtime/assets
system service composition
build metadata
footprint hygiene
```

Role inputs own the intentional differences:

```text
target role         -> child OS packages/services/runtime
live-installer role -> installer packages/services/live boot requirements
```

Architecture/board differences are profile and adapter data.

Do not create an independent ARM builder or update-root builder.

## A6 — A/B + PERSIST is the normal installed model

All newly supported installs use two replaceable system slots and separate persistent data.

Routine update always writes the inactive slot. PERSIST is never reformatted during normal update.

## A7 — PERSIST owns durable child/Parent state and one schema marker

At minimum:

```text
profiles
Activity saves/creations
progression/rewards
Parent settings/credentials
device preferences
update acceptance/status metadata
persist-schema.json
```

`persist-schema.json` is small ordinary state, conceptually:

```json
{"schema_version": 1}
```

It is not signed or hashed for authority.

Before candidate trial/recovery, current PERSIST schema must fall inside the candidate's declared readable range.

Before candidate acceptance, migrations must remain backward compatible or transactionally reversible so the previous accepted slot can still recover. After acceptance, the release may advance `persist_write_schema` through the normal migration path.

An older bundle whose readable range excludes current PERSIST is rejected by ordinary Parent update and is not eligible for preserve-data reinstall. This is data protection, not anti-rollback security.

## A8 — One shared writer/finalizer

Fresh install and update both use the common `SlotWriter` / `SlotFinalizer` direction.

Platform adapters own only actual platform differences:

```text
layout
boot files
boot one-shot/commit
install target policy
board-specific hardware finalization
```

## A9 — Hardware finalization remains offline

No network APT during install/update.

The optional hardware-support member contains the bounded packages needed by the current machine-specific finalizer. The finalizer may continue using target-root `apt-get` against that offline pool.

Profiles that need no extra support do not carry an artificial non-empty hardware-support archive.

## A10 — Update inbox is one bounded candidate, not an artifact store

The running Greia device receives at most one update candidate:

```text
candidate.uploading
-> atomic rename -> candidate.greiaupdate
-> stage inactive slot
-> delete candidate.greiaupdate after successful staging/boot-asset preparation
-> preserve small status/journal only
```

Before upload, require enough PERSIST free space for the compressed bundle plus **256 MiB** free reserve. If not, Parent reports insufficient free space instead of making hidden copies.

No content-addressed filenames or bundle digest authority.

## A11 — Installed slot staging validates usability, not provenance

After writing a candidate slot:

```text
decompression completed successfully
raw byte count matches manifest
device write + fsync completed
filesystem check passes
filesystem mounts
Greia target completeness smoke passes
PERSIST schema is readable by candidate
finalization passes
boot assets are generated
```

Only then can the backend arm the one-shot candidate.

## A12 — Universal Setup media layout is fixed

Use MBR with two partitions:

```text
P1  512 MiB FAT32  GREIA_SETUP_BOOT  active
P2  ext4           GREIA_SETUP_DATA  remainder
```

P1 contains:

```text
SYSLINUX legacy BIOS boot files
i386 live kernel/initramfs
EFI/BOOT amd64 UEFI boot files
amd64 live kernel/initramfs
Pi 400 firmware/DTB/kernel/initramfs assets
Pi 500 firmware/DTB/kernel/initramfs assets
config.txt/cmdline files needed by Pi board filters
small setup boot metadata
```

P2 contains only bulk data:

```text
live/i386/rootfs.squashfs
live/amd64/rootfs.squashfs
live/arm64/rootfs.squashfs
releases/acer-aspire-one-i386-ab.greiaupdate
releases/standard-amd64-ab.greiaupdate
releases/raspberry-pi-400-arm64-ab.greiaupdate
releases/raspberry-pi-500-arm64-ab.greiaupdate
```

The final raw image must be <= **7,400,000,000 bytes** so ordinary 8 GB-class media remains sufficient.

The exact MBR partition type used for P1 is an implementation constant selected by the first boot proof that satisfies both the preserved Acer SYSLINUX path and UEFI removable boot; it is not a reason to split the image.

## A13 — Universal live boot does not preload the universal image

No `toram` on the low-memory release path.

Each boot adapter passes the selected architecture to initramfs. Initramfs mounts `GREIA_SETUP_DATA` read-only and mounts only that architecture's SquashFS.

Writable live state uses the existing bounded tmpfs overlay, initially **128 MiB** on the Acer-class path.

If multiple `GREIA_SETUP_DATA` partitions are present, Setup fails with a simple instruction to remove extra Greia installer drives rather than guessing.

## A14 — Setup-media self-exclusion comes from the actually mounted P2 device

Once P2 is mounted, resolve its block partition and parent whole disk. That whole disk and its partitions are excluded from install targets for the session.

Immediately before destructive work, re-read target:

```text
path
major:minor
capacity
serial/WWN/CID where available
read-only/removable state
```

If it changed or disappeared, clear confirmation and return to target selection.

This is ordinary wrong-disk protection, not a trust system.

## A15 — Target policies are platform-specific but simple

### PC

Offer eligible internal SATA/NVMe/eMMC-class target storage. Exclude the mounted Setup disk and ordinary removable USB storage from the normal path.

### Pi 400 / Pi 500

Normal fresh-install target is the built-in microSD host. Identify it through sysfs/device topology, not by assuming `/dev/mmcblk0` forever.

Recovery may also explicitly offer an external microSD reader after excluding the Setup disk; the user must select that reader/card in the normal erase confirmation flow.

Every target policy computes the complete required layout size before confirmation and refuses media that cannot fit all fixed partitions plus the PERSIST minimum.

## A16 — Legacy removable boot remains SYSLINUX

Preserve:

```text
MBR -> active FAT32 -> SYSLINUX -> i386 live kernel/initramfs
```

Do not replace the physically working Acer removable path for architectural symmetry.

## A17 — Modern UEFI uses distro-signed compatibility, not Greia security infrastructure

The universal image's amd64 UEFI path and installed modern-amd64 path use the standard Debian signed boot packages (`shim-signed`, signed GRUB and distro-signed kernel packages or their source-owned current equivalents).

Purpose: boot ordinary Secure-Boot-enabled PCs without requiring firmware changes.

Greia owns no signing key and implements no custom Secure Boot trust process in this plan.

Test UEFI boot with Secure Boot both ON and OFF in OVMF and on one physical modern reference PC.

## A18 — Raspberry Pi live-boot assets coexist by official model filters

One P1 `config.txt` uses official model filters:

```text
[pi400]
# Pi 400 / Pi-4-family live kernel/initramfs settings

[pi500]
# Pi 500 / Pi-5-family live kernel/initramfs settings

[all]
# common reset/default section
```

Pi 400 and Pi 500 board adapters provide their real DTBs/firmware/overlays and kernel names. Do not use a generic model string or guess Pi generation.

The common arm64 live SquashFS is shared unless a measured package incompatibility proves a board-specific live root is necessary.

## A19 — Raspberry Pi installed layout and tryboot semantics are concrete

Installed Pi layout:

```text
P1 FAT32  pi-boot-control-recovery   256 MiB
P2 FAT32  pi-boot-a                  256 MiB
P3 FAT32  pi-boot-b                  256 MiB
P4        extended container as required by MBR
P5 ext4   system-a                  2048 MiB
P6 ext4   system-b                  2048 MiB
P7 ext4   PERSIST                   remainder, minimum 1536 MiB
```

The image builder rejects a board boot/recovery asset set that leaves less than **32 MiB free headroom** in P1, P2 or P3; workers do not silently grow partitions per board.

P1 is bootable and contains:

```text
autoboot.txt
board-appropriate firmware/DTBs
minimal recovery kernel/initramfs
recovery config/cmdline
```

With A accepted, P1 `autoboot.txt` is:

```text
[all]
tryboot_a_b=1
boot_partition=2
[tryboot]
boot_partition=3
```

After B is proven healthy, commit swaps 2 and 3. Each A/B boot partition has the boot files/cmdline necessary to mount its matching system root.

Candidate arm uses the Raspberry Pi one-shot `tryboot` reboot flag. Routine Greia install/update does not rewrite EEPROM.

`autoboot.txt` commit discipline:

```text
write autoboot.new
fsync file
rename over autoboot.txt
syncfs boot-control filesystem
re-read expected content
```

Keep a small `autoboot.prev` diagnostic copy.

If firmware lands on P1 because `autoboot.txt` is absent/malformed, the minimal recovery environment reads accepted-slot metadata and current layout from PERSIST, reconstructs the normal A/B `autoboot.txt`, syncs it and reboots. It does not run a general shell. If it cannot identify a safe accepted slot/PERSIST, it shows a bounded instruction to boot the universal Setup medium.

## A20 — Pi Setup boot/reinstall flows are fixed

### Normal fresh install

Prerequisite: the Pi EEPROM boot order includes USB-MSD. The normal/default empty Raspberry Pi boot order is SD first, then USB-MSD, then repeat.

```text
blank/unbootable target microSD inserted
Setup USB inserted
power on
SD attempt fails -> firmware falls through to USB
Greia Setup boots
install to built-in microSD
```

### Existing bootable microSD / reinstall

Preferred after physical proof:

```text
remove target card
boot Setup USB
insert target card when Setup is ready
Refresh Drives
Reinstall/Install
```

Guaranteed fallback independent of built-in hotplug:

```text
put target microSD in external USB card reader
boot Setup USB
select that microSD reader/card
install/reinstall
move card back to built-in slot
```

If USB-MSD was removed from a customized EEPROM `BOOT_ORDER`, Greia documentation directs the parent to restore a standard USB-capable boot order with Raspberry Pi's normal bootloader configuration/recovery tooling. Greia Setup itself does not modify EEPROM and no Pi-specific Greia image is created.

## A21 — Installed x86 layouts are fixed defaults

### Legacy i386

```text
MBR
boot-control: 64 MiB ext4
system A:    1536 MiB ext4
system B:    1536 MiB ext4
PERSIST:     remainder, minimum 1024 MiB
GRUB A/B backend
```

### Modern amd64

```text
GPT
ESP:          256 MiB FAT32
boot-control:  64 MiB ext4
system A:    2048 MiB ext4
system B:    2048 MiB ext4
PERSIST:     remainder, minimum 1536 MiB
UEFI GRUB A/B backend
```

These are product defaults. Workers do not tune them ad hoc per machine.

## A22 — Fresh-install state is explicit

Fresh installation writes only A.

```text
A = first_boot_pending
B = empty/unavailable
PERSIST schema = release persist_write_schema
```

First healthy Greia boot:

```text
A = accepted
normal system update becomes available
```

B is created/formatted during install but is not a valid boot candidate until a later update stages it.

## A23 — Candidate health uses existing Greia interactive readiness

Commit only after existing platform health observes:

```text
root mounted
PERSIST read/write
critical Greia services healthy
display/session active
Shell interactive/profile-selection ready
```

If userspace starts but this point is not reached within the existing bounded health/reconciliation path, trigger a normal reboot; the one-shot candidate is not committed, so the previous system returns.

A failure before Greia userspace may require one manual reset/power cycle. On that next boot, the previous accepted slot is still the default.

## A24 — Setup media is also the bounded recovery medium

When Setup finds a valid Greia A/B layout/profile, UI may offer:

```text
Reinstall Greia, keep child data
Erase and install Greia
```

`Reinstall Greia, keep child data` is available only when:

```text
layout/profile is recognized
PERSIST filesystem mounts read-only for inspection
PERSIST schema exists and is within the bundled release's readable range
```

Then it:

- does not repartition;
- does not format PERSIST;
- writes the matching current release into system A;
- finalizes/rebuilds boot assets;
- clears B as an update candidate;
- marks A `first_boot_pending`;
- preserves PERSIST.

If layout/profile/schema facts are inconsistent, the preserve-data option is unavailable. Do not guess around damaged state.

## A25 — Parent update UX stays simple

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

If the candidate health check fails after userspace started, Greia reboots and Parent later reports that the previous version was restored.

For a pre-kernel candidate hang, documentation/UI says one power cycle returns to the previous version; do not claim impossible autonomous recovery.

Selecting an older compatible bundle may show an explicit downgrade warning, but the ordinary update path proceeds only if the candidate declares the current PERSIST schema readable. A developer may manually alter/recover files outside the product flow; Greia does not build security machinery to prevent that.

## A26 — Owner build workflow is one command

Normal release:

```bash
sudo python3 tools/greia_release.py build \
  --version <VERSION> \
  --output <DIR>
```

The command:

1. runs practical host preflight;
2. builds target roots/profile bundles for all supported targets;
3. builds one live root for i386, amd64 and arm64;
4. assembles real platform boot assets;
5. composes the universal Setup image;
6. emits the compressed public `.img.xz` form;
7. writes a concise release report.

Developer subcommands may include:

```text
doctor
build-profile
build-live-root
build-setup-image
inspect
write-media
```

`write-media` is an owner/developer convenience. Ordinary Windows/macOS/Linux users can flash the same downloadable image with an established graphical image writer; Greia does not build a separate cross-platform flashing application in this workstream.

## A27 — Official build host is x86_64 Linux

It builds i386/amd64 normally and arm64 with `qemu-aarch64-static` + binfmt for chroot phases.

No Docker/VM requirement.

`doctor` checks tools, root capability needed for loop/mount/image operations, disk space, zstd/xz, qemu/binfmt, repositories and profile validity.

## A28 — Testing catches bugs; it is not a new process product

Use:

```text
focused source tests while coding
mounted/chroot artifact smoke tests before QEMU
make verify at selected major milestones
QEMU/loop for software lifecycle
physical hardware for firmware/board behavior
```

No new T-BAG hierarchy, artifact authority, signed reports, evidence tokens, or immutable-attempt bureaucracy.

---

# 3. Final release output

Normal output:

```text
out/greia-<version>/
  release-report.json
  greia-setup-<version>.img.xz

  updates/
    acer-aspire-one-i386-ab.greiaupdate
    standard-amd64-ab.greiaupdate
    raspberry-pi-400-arm64-ab.greiaupdate
    raspberry-pi-500-arm64-ab.greiaupdate

  intermediate/                 # developer/build cache, not public product
    greia-setup-<version>.img
    ...
```

The four `.greiaupdate` bundles and the universal image come from the same build invocation and composition authority.

No public per-platform installer images are produced.

---

# 4. Core transactions

## 4.1 Fresh install

```text
boot universal Setup image
-> select live root from boot architecture
-> mount P2 read-only
-> detect exact supported profile/board
-> enumerate eligible targets
-> exclude Setup disk
-> user selects target
-> verify complete layout fits
-> immediate target recheck
-> explicit erase confirmation
-> create platform layout
-> write/decompress matching release to system A
-> filesystem check + expand + mount
-> common finalizer
-> initialize PERSIST with release persist_write_schema
-> format empty system B
-> install platform boot backend
-> mark A first_boot_pending
-> sync
-> reboot
-> first healthy Greia boot marks A accepted
```

## 4.2 Running-system update

```text
Parent chooses .greiaupdate
-> upload one compressed candidate
-> parse manifest
-> profile/architecture/board/space checks
-> require current PERSIST schema within candidate readable range
-> choose inactive slot
-> stream-decompress into inactive slot
-> filesystem + Greia completeness checks
-> finalizer
-> generate inactive-slot boot assets
-> delete large uploaded candidate
-> arm one-shot boot
-> Ready to Restart
-> reboot
-> BOOT_HEALTHY -> commit candidate
-> complete compatible PERSIST migration / write persist_write_schema
-> otherwise previous remains default and PERSIST remains previous-readable
```

## 4.3 Setup-media recovery preserving data

```text
boot universal Setup
-> detect valid existing Greia A/B layout
-> mount/inspect PERSIST without changing it
-> require current PERSIST schema readable by bundled release
-> choose Reinstall Greia, keep child data
-> leave partition table/PERSIST untouched
-> rewrite system A from matching bundled release
-> finalize/rebuild boot state
-> clear B candidate state
-> A first_boot_pending
-> reboot
-> healthy A accepted
```

## 4.4 Pi boot-control recovery

```text
firmware lands on P1 recovery/control
-> recovery initramfs mounts PERSIST read-only
-> read accepted slot + layout
-> reconstruct autoboot.txt for accepted A/B default
-> sync
-> reboot
```

If accepted state/layout cannot be determined, display a simple instruction to boot the universal Setup image; do not mutate system partitions blindly.

---

# 5. Implementation sessions

Each session is sized for one strong coding LLM. It should implement, test, repair regressions, update this plan progress and commit coherent work. Do not turn a session into a planning/gating exercise.

## Session 01 — Simplify the update bundle/runtime

### Implement

- introduce `.greiaupdate` format v3 from A3;
- remove signature/signer/key/release-sequence requirements from update production code;
- remove Ed25519/cryptography from `system-update` package requirements;
- add `zstd` to update/live requirements;
- replace `payload.bin` with `payload.ext4.zst`;
- allow hardware-support member to be genuinely optional;
- add the three small PERSIST schema compatibility fields;
- simplify `SystemUpdateService` compatibility logic to version/profile/architecture/board/space/PERSIST schema;
- replace content-addressed inbox with one atomic fixed candidate;
- delete the candidate after successful slot staging;
- update focused tests to prove old experimental signed format is rejected with a migration message, not silently interpreted;
- update `AGENTS.md`, `HANDOVER.md` and `skills/greia-os-work/SKILL.md` routing so this plan is the current route.

### Done when

A small synthetic valid v3 bundle can be created, received, inspected and staged without any key material; incompatible architecture/profile or unreadable PERSIST schema is rejected; the inbox never keeps multiple candidate copies.

No long QEMU run yet.

---

## Session 02 — Canonical root composer + compressed complete slot

### Implement

- refactor `build/build-image.sh` composition into reusable `build/lib/` primitives;
- add explicit `target` and `live-installer` composition roles;
- keep current Acer image builder as a thin consumer of the target composer;
- build a real Acer ext4 system-slot image from the same composed target root;
- run `e2fsck` and shrink it before transport compression;
- add practical slot completeness validator;
- zstd-compress the slot into v3 bundle;
- change common slot writer to accept a decompressed stream/raw byte count rather than requiring a raw payload temp file;
- after write: fsync, filesystem check, expand, mount, smoke, finalizer;
- make a V12G-like minimal filesystem fail before QEMU.

### Done when

Acer target image and Acer update slot are produced from one root composition implementation, and the complete slot includes real Greia userspace plus the current finalizer's `apt-get`/`dpkg` needs.

Run focused build/update tests and **`make verify`** at this major refactor boundary.

---

## Session 03 — Owner release CLI + compact release outputs

### Implement

`tools/greia_release.py`:

```text
build
doctor
build-profile
inspect
write-media
```

Initially the matrix may contain only the real Acer profile, but the output directory/schema is final.

- centralize build temp/cache handling;
- make low-level shell builders implementation details;
- report target/live/bundle sizes;
- enforce practical output paths and clear failures;
- add media-size accounting that later universal composition uses.

### Done when

one owner command builds the complete Acer release bundle and reports exactly what was produced without environment-variable archaeology.

---

## Session 04 — Finish legacy i386 lifecycle with the real payload

### Implement/verify

- wire fresh A/B installer to the release CLI's just-built real bundle;
- remove production `GREIA_AB_RELEASE_BUNDLE_SRC` manual plumbing;
- fresh install writes A, formats but does not clone B;
- initialize PERSIST schema marker;
- first healthy boot marks A accepted;
- second release stages B;
- candidate B boots and commits;
- intentionally broken userspace candidate fails health and reboots to A;
- intentionally non-booting candidate is confirmed to leave A as normal default after reset;
- prove an unreadable PERSIST-schema candidate is refused before slot activation;
- fix any remaining product-composition bugs directly.

### Done when

```text
fresh install -> first healthy boot -> update -> commit -> failed candidate -> previous release
```

works in product-mode QEMU with real bundles.

The old Gate-P5 document becomes historical evidence. Do not create another gate hierarchy.

Run **`make verify`** after closure.

---

## Session 05 — Real modern amd64 target and UEFI A/B

### Implement

- `standard-amd64-ab` profile;
- amd64 target root + v3 update bundle;
- executable `modern-gpt-ab-v1` layout;
- ESP/boot-control/system A/B/PERSIST;
- UEFI GRUB one-shot/commit backend using the same semantic journal;
- Debian signed shim/GRUB/kernel compatibility packages;
- amd64 `live-installer` root;
- internal-storage target policy for SATA/NVMe/eMMC while excluding ordinary removable USB.

### Done when

OVMF can install, boot, update and recover a bad candidate with Secure Boot OFF and ON using distro-provided signed boot components. No Greia signing keys exist.

---

## Session 06 — ARM64 build substrate + real Pi profiles

### Implement

- remove x86-only builder guard where the shared composer now supports arm64;
- qemu-aarch64-static/binfmt build path;
- shared ARM64 target/live package sets;
- Raspberry Pi repository/key as ordinary package-repository configuration;
- Pi 400 profile using stable `linux-image-rpi-v8` family/current equivalent;
- Pi 500 profile using stable `linux-image-rpi-2712` family/current equivalent;
- shared Greia ARM64 userspace/Activities;
- board-specific boot assembly remains outside the generic root composer;
- create complete compressed v3 bundles for both profiles.

### Done when

both profiles build complete target roots/bundles through the same root composer as x86 and pass the same practical completeness checks.

---

## Session 07 — Pi 400/500 live-boot board adapters

### Implement

- `Pi400BoardAdapter` and `Pi500BoardAdapter` or equivalent typed registrations;
- device-tree compatibility detection;
- board firmware/DTB/overlay extraction from the selected packages;
- Pi 400 `kernel8.img` live path;
- Pi 500 `kernel_2712.img` live path;
- one common arm64 live SquashFS;
- single `config.txt` using `[pi400]` and `[pi500]` filters;
- board-specific cmdline/initramfs selections;
- no EEPROM writes.

### Done when

an assembled FAT boot tree can be inspected deterministically and contains both real board paths without name collisions or fake shared firmware assumptions.

---

## Session 08 — Compose the real universal Setup image

Only now compose the universal image, because all three architecture boot paths exist.

### Implement

- MBR + 512 MiB active FAT32 P1 + ext4 P2;
- preserved SYSLINUX Acer boot path;
- real signed-distro amd64 UEFI path;
- real Pi 400/500 boot files/config from Session 07;
- i386/amd64/arm64 live roots on P2;
- four compressed v3 release bundles on P2;
- initramfs architecture selection and P2 mount;
- no `toram`;
- 128 MiB Acer live overlay;
- mounted-P2 device ancestry exported to installer target exclusion;
- multiple-Setup-drive ambiguity refusal;
- raw-image <= 7,400,000,000-byte product limit;
- `.img.xz` public compression.

### Done when

one image boots legacy BIOS QEMU, amd64 OVMF and reaches the Pi firmware/kernel handoff path in available emulation/source checks; its size fits the product limit.

Run **`make verify`** here.

---

## Session 09 — Common graphical installer across all profiles

### Implement

One installer application/UI:

```text
Welcome
Detected Greia hardware
Choose target
Confirm erase
Install progress
Done / reboot
```

Under it:

- profile selection from actual platform facts;
- target policies from A15;
- complete-layout capacity check;
- mounted-Setup-disk exclusion;
- immediate recheck before erase;
- platform layout adapter;
- matching bundle selection from P2;
- common stream writer/finalizer;
- PERSIST initialization/schema marker;
- first_boot_pending state;
- platform boot backend installation.

No platform-specific installer fork and no root/shell UI.

### Done when

all four profile transactions execute through the same installer orchestration in source/loop tests.

---

## Session 10 — Pi installed layout + native tryboot A/B + boot-control recovery

### Implement

- executable Pi MBR/extended layout from A19 using 256 MiB P1/P2/P3;
- builder headroom check for boot assets;
- P1 bootable minimal recovery/control environment;
- fresh filesystem/partition identity observation;
- boot A/B asset generation from board adapter + staged slot;
- concrete `autoboot.txt` shown in A19;
- one-shot tryboot arm;
- boot observation from device-tree;
- healthy commit swaps default boot partition;
- failed candidate leaves previous default;
- durable small-file commit sequence for autoboot;
- P1 recovery reconstructs `autoboot.txt` from accepted-slot state;
- unreadable accepted state falls back to a bounded “use Greia Setup” recovery message;
- no EEPROM mutation.

### Done when

loop/source tests cover A->B and B->A state transitions, interrupted staging, invalid boot-partition preparation, missing/truncated `autoboot.txt`, recovery reconstruction and reboot reconciliation.

Run **`make verify`** after the common Pi backend lands.

---

## Session 11 — Setup recovery/reinstall + Pi reinstall ergonomics

### Implement

- recognize an existing valid Greia A/B layout/profile;
- inspect PERSIST schema before offering preserve-data recovery;
- add `Reinstall Greia, keep child data` only when bundled release can read current PERSIST;
- preserve PERSIST exactly;
- rewrite system A, clear B candidate state, rebuild boot backend, first_boot_pending;
- add Pi `Refresh Drives` path after card insertion;
- support an explicitly selected external microSD reader on Pi recovery while still excluding Setup USB;
- document customized Pi EEPROM no-USB boot order as a firmware prerequisite/troubleshooting case, not a Greia image variant;
- never expose arbitrary USB disk install on PC through this recovery work.

### Done when

recovery tests prove PERSIST survives compatible reinstall, incompatible PERSIST schema removes the preserve-data option, and malformed/unknown layouts do not receive it.

---

## Session 12 — Parent update API + Parent-app UX

### Greia repo

- simple candidate upload/status API;
- profile/version presentation;
- PERSIST capacity preflight;
- PERSIST schema compatibility preflight;
- stage through common update service;
- progress/state;
- ready-to-restart;
- requested restart;
- successful/rolled-back result;
- no signing/trust vocabulary or raw slot authority.

### Parent repo

System Update panel:

```text
Current version
Choose Update File
Upload progress
Preparing Update
Ready to Restart
Restart & Update
Result
```

Older compatible version -> explicit downgrade/data warning. PERSIST-incompatible version -> ordinary update refused with a clear message.

### Done when

browser -> Acer update -> restart -> commit works end to end, plus a failed-health candidate returns to prior system and is reported coherently.

Run **`make verify`** in Greia plus Parent repository tests at this integration boundary.

---

## Session 13 — Physical Raspberry Pi 400 completion

Use the normal owner build and universal image.

Verify/fix:

```text
record EEPROM BOOT_ORDER; confirm USB-MSD is present
blank microSD + Setup USB -> USB Setup boot
correct Pi400 board filter/kernel
installer UI
built-in microSD target only
fresh install
first Greia boot
Shell + representative Activities
Parent connection
newer update to inactive slot
tryboot candidate
commit
failed userspace candidate -> automatic reboot -> previous
pre-kernel bad candidate -> one reset/power cycle -> previous
missing/corrupt autoboot.txt -> P1 recovery -> accepted system restored
PERSIST survives
reinstall recovery by hot-inserting built-in card if supported
external-reader recovery fallback
```

Do not create a Pi400-specific image to fix a failure.

---

## Session 14 — Physical Raspberry Pi 500 completion

Repeat the same product flow independently on Pi 500, specifically proving:

- EEPROM BOOT_ORDER includes USB-MSD;
- `[pi500]` path is active;
- Pi-5/BCM2712 kernel/DTB assets are really used;
- Pi 400 assumptions did not leak into Pi 500;
- native tryboot A/B works;
- P1 recovery works;
- built-in card and external-reader reinstall flows behave as documented.

Fix source and rerun affected cases in the same session.

---

## Session 15 — Physical modern PC + Acer + final one-command release closeout

From a clean supported Linux build host:

```bash
sudo python3 tools/greia_release.py build --version <candidate> --output <dir>
```

Require one build to produce:

```text
greia-setup-<candidate>.img.xz
four profile .greiaupdate bundles
release-report.json
```

Then smoke the produced release on:

```text
physical Acer legacy BIOS
one physical modern amd64 PC, Secure Boot ON and OFF
physical Pi 400 evidence from Session 13
physical Pi 500 evidence from Session 14
```

Confirm installer-image creation with a mainstream GUI imager using the public compressed image.

Remove obsolete active instructions/tools for:

```text
release signing/key generation
old signed bundle format
manual GREIA_AB_RELEASE_BUNDLE_SRC workflow
split-platform public install images
stale D6/Gate-P5 next-step routing
```

Update README/SETUP/HANDOVER/skills/architecture docs to the single normal release workflow and close this plan.

Run final **`make verify`** and Parent tests. Do not create a new meta-gate after they pass.

---

# 6. Explicit worker prohibitions

Do not:

```text
split the public Setup image by platform
reintroduce Greia release signing/key/trust infrastructure
turn checksums into authorization or product identity
create another anti-tamper/anti-rollback subsystem
store raw uncompressed slot images inside the update bundle
remove simple PERSIST schema compatibility just because signatures were removed
create a second ARM rootfs builder
create a second Pi installer UI
use GRUB/U-Boot on Pi for symmetry
rewrite Pi EEPROM during routine install/update
make direct DRM a Pi prerequisite
use toram on the Acer live installer
preload all universal-image live roots into RAM
mutate the active slot during normal update
run network APT during install/update
create package-by-package active-root upgrades
create another T-BAG/gate/orchestration hierarchy
create another installer-only OS payload
turn Parent browser into a privileged disk/package tool
promise autonomous rollback from a pre-kernel hang without a watchdog/reset mechanism
rely on a non-bootable Pi control partition and hope partition-walk behavior saves it
```

If physical hardware proves a low-level assumption wrong, fix the adapter/composer while preserving the product architecture. Report a genuine architecture contradiction to the owner rather than silently changing the product requirement.

---

# 7. Definition of complete

This workstream is finished only when all of this is true:

```text
ONE universal Setup image is the normal installer/recovery medium
its public compressed form fits ordinary 8 GB-class media

Acer legacy BIOS boots it and installs Greia
modern amd64 UEFI boots it with Secure Boot ON and OFF and installs Greia
Pi 400 boots it and installs Greia to microSD
Pi 500 boots it and installs Greia to microSD

i386, amd64 and arm64 use one root-composition engine
live-installer and target roles are explicit inputs to that engine
Pi 400/500 share ARM64 Greia and differ only through real board adapters

.greiaupdate is simple, unsigned and compressed for transport
no full uncompressed update temp file is required on the device
all new supported installs use A/B + PERSIST
fresh install and update consume the same complete target-root release authority
first healthy boot accepts a fresh install
Parent can upload/apply a local .greiaupdate and restart into it
bad candidate never replaces the previous default until healthy
pre-kernel candidate failure recovers on the next reset/power cycle
PERSIST schema compatibility is checked before trial/update/recovery
PERSIST survives update, rollback and compatible preserve-data reinstall

the universal Setup image can reinstall an existing valid A/B Greia while keeping PERSIST
Pi installed media has a bootable P1 recovery/control path for broken autoboot state
Pi reinstall has both a tested built-in-card flow and external-reader fallback
customized Pi firmware without USB-MSD boot has a clear standard-firmware remediation path, not a second Greia image

one supported x86_64 Linux build host creates the whole release with one normal command
no Greia signing-key/trust-chain workflow is required
no worker-facing architecture choice remains open in this lifecycle plan
```

At that point close this plan and move on. Do not redesign install/update again unless actual shipped hardware or user requirements force a new decision.

---

# 8. Progress ledger (append-only)

Session progress is recorded here as dated append-only entries. Never rewrite
or reorder earlier plan content; corrections are new entries. The de-facto
entry format is `## YYYY-MM-DD — <outcome title> (<TASK-ID>)`, bullets
recording implementation and verification, and a final bullet naming what
remains open and the exact next step.

## 2026-09-16 — Session 02 source scope complete: canonical composer roles, real ext4 slot producer, shared completeness validator (T05)

- Session 02 objective (one root composition implementation; complete slot with real Greia userspace plus the finalizer's `apt-get`/`dpkg` needs) is implemented at SOURCE level through T01–T04; all four tasks are reviewer-accepted PASS.
- T01: one shared composition engine exists — `build/lib/compose.sh` exposes role-typed `compose_root --profile <id-or-path> --role <target|live-installer> --root <path>`, composing into a caller-provided directory with no partitioning/mkfs/loop/boot assembly. `build/build-image.sh` is a thin target consumer (`compose_resolve_profile … "target"` + `compose_root --role target`, then target-only boot assembly and footprint gate). `build/build-installer-image.sh` byte-unchanged by T01.
- T02: `build/build-installer-image.sh` composes through the same engine (`compose_resolve_profile … "live-installer"` + the full live-installer `compose_*` sequence), with role differences declarative in the engine and zero diff to `build/lib/compose.sh` and `build/build-image.sh`. Live root still excludes target-only content (no `activities`, no full assets).
- T03: practical slot completeness validator defined once in `src/greia_platform/slot_writer.py` (`check_slot_completeness` / `slot_completeness_missing` / `REQUIRED_SLOT_COMPLETENESS_*`); production `BlockSlotFilesystem.check_completeness`, the `system_updates` passthrough, test fakes and QEMU lifecycle fakes all delegate to it. `SlotFinalizer.finalize` calls it strictly before package install, image build and all slot writes, so the V12G skeleton shape (`{etc, lost+found, run, var}`) is refused fail-closed naming the missing paths (`usr`, `bin`, `opt/greia-os`, `etc/greia-os`, `usr/bin/apt-get`, `usr/bin/dpkg`, `usr/bin/env`). The validator carries no `boot/*` knowledge.
- T04: real-ext4 slot producer `build_release_payload` (`tools/build_release.py`) runs the ordered e2fsprogs sequence `mkfs.ext4 -d <staging>` → `e2fsck -f -y` → `resize2fs -M` → `e2fsck -f -y` → `zstd -19 -c` through the injectable `ReleaseCommandRunner` protocol (`shell=False`, argument arrays), calls the shared T03 validator on the staging tree before any image byte, enforces shrink post-condition and 1 MiB headroom, and rejects partition tables (MBR/GPT) and legacy tar bodies. Read-only `verify_release_payload` proves ext4 magic plus relocatability, runs `e2fsck -n`, and proves 13 image-content paths via `debugfs stat`. Build→verify→`build_update_bundle`/`inspect_update_bundle` round-trips to an unsigned v3 bundle (`ZIP_STORED payload.ext4.zst`, no signer/signature/key/sequence).
- D6 (slot payload with no `apt-get`) is resolved at SOURCE level: release payloads are now complete target-root ext4 images carrying `apt-get`/`dpkg`/`env`, and the shared validator refuses payload-only skeletons before compression and before slot finalization.
- Evidence actually produced and its level: SOURCE-level only — `make shell-check` clean; focused contract suites green (`test_build_release` 8/8, `test_slot_writer` 45, `test_system_update*` 51, `test_update_v3_bundle` 6, `test_build_*` 45, plus T01/T02 shell-contract/boot suites); independent negative/positive/sensitivity probes (skeleton RED, populated GREEN, symlink-leaf RED, random-bytes/MBR/GPT RED, ordered-command and validator-identity assertions). Real zstd/v3-bundle bytes exercised; no e2fsprogs on this host so mkfs/e2fsck/resize2fs/debugfs behavior was proven through the injected runner seam. No privileged debootstrap/chroot/loop image build was executed here; no real image or bundle artifact was produced.
- T05 (this task): Session 02 documentation route — this ledger entry, `HANDOVER.md` routing/D6/evidence-boundary update, and correction of the stale signed-v2/`payload.bin` instructions in `docs/development/GREIA_SYSTEM_UPDATE_RELEASE_WORKFLOW.md` and `docs/product/SYSTEM_UPDATES.md` to the real v3 flow (composed target root → real ext4 image → `e2fsck`/shrink → completeness smoke → zstd `payload.ext4.zst` → unsigned v3 bundle).
- `skills/greia-os-work/SKILL.md` and `docs/agents/GREIA_AGENT_OPERATIONS.md`: no change required by Session 02 — the skill already routes lifecycle work to this plan and labels the signed v2 flow historical, and the manual's build/update procedure (before-debootstrap apt-cache mounts, capable build-host process rules) is untouched by the composer/slot work. Stated explicitly instead of editing for its own sake.
- What remains open and the exact next step: Session 02 obligations remaining are the unexecuted build-host artifact leg — one privileged Linux build-host `build-payload` → `verify-payload` → bundle cycle to promote SOURCE-level proof to a real-artifact run (the `mkfs.ext4` size-suffix spelling is pinned by the seam test and confirmed by that run). Next is that Session 02 boundary run, then Session 03 (owner release CLI + compact release outputs).

## 2026-09-16 — Session 02 documentation correction to ADR 0036 lifecycle reality (T07)

- `docs/development/README.md`: the "System update release workflow" index bullets rewritten to the unsigned v3 flow (composed target root → real ext4 slot payload → read-only payload verification → unsigned v3 bundle build → local inspection), with no release key generation and no signature verification. Consistent with `docs/development/GREIA_SYSTEM_UPDATE_RELEASE_WORKFLOW.md`, which T05 already rewrote.
- `docs/release/GREIA_PUBLIC_RELEASE_READINESS.md` Gate E conformance pass: removed trusted update public-key provisioning, signing-key custody/backup/rotation/revocation, and exact signature verification before privileged writes; fixed the stale "signed" intro wording; restated the failure-injection probe "bad signature" as corrupt/tampered bundle (v3 has no signature). The remaining capability list (rollback-safe layout, canonical slot-payload builder, compatibility checks, inactive-slot staging, preflight, bounded writes, boot-attempt limit, post-boot health, rollback, schema-compatible migrations, PERSIST preservation, Parent progress/result, normal and offline sources, downgrade/replay policy, interruption behavior, withdrawal process) is unchanged and consistent with ADR 0036 and this plan. No new trust or anti-rollback requirement introduced.
- `skills/greia-os-work/SKILL.md`: lifecycle routing pointer bumped to Session 02 source-complete with the build-host artifact boundary leg as the current entry point, then Session 03. Routing only; no procedure restated or duplicated.
- `docs/product/SYSTEM_UPDATES.md`: the Parent-client prohibition restated as never deciding release trust (there is no v3 signature to decide on).
- No genuine contradiction found: Gate E required nothing that ADR 0036 removed beyond the three rejected capabilities, so no escalation was needed. Docs-only change; no `src/`, `build/`, `tools/`, `tests/` or Activity file touched.
- What remains open and the exact next step: the Session 02 build-host artifact leg (privileged `build-payload` → `verify-payload` → bundle cycle), then Session 03 (owner release CLI + compact release outputs).

## 2026-09-16 — Remaining pre-0036 release/update wording reconciled with unsigned v3 (T09)

- `docs/release/GREIA_PUBLIC_RELEASE_READINESS.md` conformance pass outside Gate E (Gate E itself untouched — T07 owns it): gaps item 5 now states unsigned v3 bundle/inbox work with no trusted-key installation; Gate B release property now states no release signing keys or trusted update public keys are provisioned; 7.1 artifacts list content-integrity hashes (SHA-256, not release signatures); Gate K review lists update bundle-integrity/rollback tests; Gate O build record lists content-integrity identity (artifact SHA-256, not a signature); RC evidence pack lists artifact hashes as content-integrity aids, not signatures; release-track step reads tag/publish artifacts; section 27 item 7 now requires staged-safely + health-checked + automatically rollback-capable + PERSIST-schema compatible updates; item 17 now requires traceability to immutable source SHA, profile and dependency inventory with content-integrity verification. No new trust, signing or anti-rollback requirement introduced. Preserved: private-key/SSH-key hygiene including the repository-history secret audit, Parent pairing/transport cryptography, SBOM/provenance traceability, and hashes as integrity aids.
- `docs/product/SYSTEM_UPDATES.md`: the Parent-uploaded-file flow now states the privileged updater re-checks machine/profile/board compatibility and PERSIST schema readability before any system write, with no residual "trust" wording implying a v3 signature.
- No genuine contradiction found: no gate genuinely requires a capability ADR 0036 removed beyond stale wording, so no escalation was needed. Docs-only change; no `src/`, `build/`, `tools/`, `tests/` or Activity file touched.
- What remains open and the exact next step: the Session 02 build-host artifact leg (privileged `build-payload` → `verify-payload` → bundle cycle), then Session 03 (owner release CLI + compact release outputs).

## 2026-09-16 — Session 02 COMPLETE: real-artifact leg proven on orbiter (T11/T13/T15, s02 Gate PASS)

- **T11 (integrated):** `tools/build_release.py` payload producer completes the real ~1 GiB Acer-class `zstd -19` step inside stated configurable bounds (600 s per command / 1800 s compression through the injectable runner seam); output spelling, ext4 sequence, relocatable/no-signing/`ZIP_STORED` contract unchanged.
- **T13 (integrated):** `build_hardware_support_set` fails closed under the same timeout contract (timeout expiry → `ReleaseBuildError`, never raw `TimeoutExpired`; non-positive bounds refused before any work).
- **T15 (PASS, accepted):** full Session 02 boundary verdict with the real artifact leg on the owner-provisioned orbiter lane: real `acer-aspire-one-i386-ab` target root composed via `compose_root --role target`, production `build-payload`/`verify-payload` green, v3 bundle round-trip (`ZIP_STORED payload.ext4.zst`, sizes/hashes bound); source-level predicates re-measured at the pinned HEAD; V12G negative/positive controls green; `make verify` green (3415 tests OK, 3 skipped).
- Superseded without execution: T06/T08/T10 (local Docker attempts), T12/T14 (re-briefs). The local-container venue was abandoned by owner decision after Docker Desktop RAM pressure (~14 GB), a daemon stall, and a host-RAM pre-flight refusal; standing container/lane discipline recorded in the (git-ignored) T-BAG run authority. No predicate weakened at any step.
- Session 02 exit predicates satisfied; s02 Gate PASS independently reproduced. Next: Session 03 (owner release CLI + compact release outputs). Evidence does not certify VM/physical-hardware behavior.

## 2026-09-18 — Session 02 repair tranche R2 source-complete (run `TBag/runs/R2`)

- Implemented `GREIA_SESSION02_REPAIR_LOCAL_AGENT_PLAN.md` Repairs A–J plus Analyst-triaged amendments, all through implement → fresh-review → integrate: T01 Acer A/B 1536 MiB + capacity regression; T02 composer-owned clone neutrality; T03 shared fstab renderer + finalizer UUID specialization; T04 candidate hardware-support archive drives finalization; T05 Installed-Size accounting; T06 updater CAP_SYS_ADMIN+CAP_SYS_CHROOT; T07 PERSIST fallback provisional (Session 04 owns); T08 streaming payload compression/verification; T09 Acer profile identity; T10 retired X-Pip-Token path; T12 payload-stage clone gate; T14 installer wording; T16 fstab mode; T17 headroom docs; T18 final sweep accepted PASS.
- Committed as `5bd8c6e3` + `ab3c4c4e` + `e9fe5044`; tree clean. Phase gate (3 auditor passes) verdict: source consistent; exit predicates needing Orbiter artifacts, exact-service staging and Acer acceptance remain UNPROVEN — Session 03 must not begin.
- Exact owner next step: Orbiter clean-Linux Acer target-root + payload + bundle inspection with headroom math (repair plan §16), then Acer install/update/failure drill (§§17–18), evidence per §24.

## 2026-09-18 — R2 repair hardware legs CANCELLED by owner (run abandoned, red preserved)

- Orbiter payload leg proven: HW-01A GREEN at `4c571995` (real target root, payload 383798895 B / 1111490560 B, bundle `greia-0.13.0-acer-aspire-one-i386-ab.greiaupdate`, headroom 1196425216 ≤ 1610612736). HW-01B STOP (loop/mount prohibited on Orbiter). HW-05 + HW-03A + HW-03B integrated (STOP / NOT-EXECUTABLE, reviewer PASS each).
- Explicit Human cancellation (`TBag/runs/R2/owner-decisions/R2-cancellation.md`, run `abandoned`): HW-02, HW-03 (all three hardware executions in `HW-03-PHYSICAL-LEGS.md`), HW-04 closed WITHOUT execution. Gate GATE-04 stays BLOCKED as history; Session 03 never opened.
- No predicate waived or proxied. Future hardware evidence opens a NEW run/phase bound to its own SHA and must not inherit these verdicts.
