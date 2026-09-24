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

## 2026-09-19 — Session 02 R4 autonomous repair docs closeout (R4-H-DOCS)

- R4 defects recorded (review of R3/post-R3 source): (A) boot-control 32 MiB vs binding A21 64 MiB; (B) Acer `image.size_mib` 4352 inflated by installed-disk capacity through duplicate-overhead validation; (C) PERSIST staging free-space double-count of the resident bundle; (D) divergent build/runtime support-archive parsers, no shared module; (EF) whole-artifact buffering + two-pass staging; (G) operator-typed payload size facts trusted without artifact verification. Repair ownership: sibling lanes R4-A-BOOT / R4-B-CAPACITY / R4-C-PERSIST / R4-D-PARSER / R4-EF-STAGE / R4-G-RECEIPT; no repair code in this docs tranche.
- This tranche (docs-only, autonomous): authoritative R4 closeout added as `HANDOVER.md` §30; stale active-looking owner-routing in §8b and the paused-run resume trigger superseded with `HISTORICAL — NOT CURRENT ROUTING` banners (history preserved, not rewritten); dangling `docs/handovers/TBAG-opencode2-plugin-handoff/` reference marked historical (directory deleted); `docs/development/GREIA_SYSTEM_UPDATE_RELEASE_WORKFLOW.md` "real-artifact build-host run pending" replaced with R4-bound reproof pending/completed wording. No doc in this tranche asks the owner for hardware work to finish R4.
- Autonomous acceptance at the docs-tranche HEAD: 8 focused suites green (129 tests OK, 1 skipped: acer_ab_slot_capacity 6, release_cli_finalized_capacity 11, candidate_support 19, system_update_service_orchestration 7 with 1 skipped, build_profiles 9, build_release 20, slot_writer 45, system_updates 12); `git diff --check` clean; `make shell-check` clean. Full `make verify` exceeds this lane's budget; owned by R4-V-VERIFY at the integrated HEAD.
- Orbiter/physical boundary: earlier proofs stand without re-claim (R2 T15 boundary incl. `make verify` 3415 OK / 3 skipped; HW-01A payload leg at `4c571995`, headroom 1196425216 ≤ 1610612736 GREEN). R4-bound Orbiter reproof at the current SHA is PENDING; installer assembly, exact-service staging, Acer acceptance and all hardware legs stay DEFERRED (listed, never waived).
- What remains open and the exact next step: integrate the R4 code lanes, then R4-V-VERIFY runs the full baseline-relative sweep (`git diff --check`, `make verify`, Orbiter non-destructive legs where reachable) at the final integrated HEAD. Session 03 stays CLOSED until then.

## 2026-09-19 — R4 SHA-bound closeout at final integrated HEAD `c4ab45aa` (R4-H-DOCS2)

- Append-only binding; the 2026-09-19 R4-H-DOCS entry above is preserved as the docs-tranche record (base `c58051c2` + delta, full verify and Orbiter reproof PENDING at that point). This entry, plus `HANDOVER.md` §31, carries the final SHA binding. No earlier entry rewritten; no owner hardware errand added.
- Final integrated SHA: `c4ab45aaea5968d5a1bf911e2b883b012dd8cc3e` (R4-V-VERIFY5 baseline-relative PASS; tree clean; `git diff --check` exit 0).
- Focused suites green at that SHA: `test_acer_ab_slot_capacity` 6; `test_release_cli_finalized_capacity` 11; `test_candidate_support` 19; `test_system_update_service_orchestration` 7 (1 skipped); `test_build_profiles` 9; `test_build_release` 20; `test_slot_writer` 45; `test_system_updates` 12; `test_payload_receipt_binding` 17; `test_hardware_support_archive_verdicts` 22; `test_candidate_support_streaming` 15; `test_candidate_support_persist` 5; `test_support_outer_bound` 7; `test_installer_layout` 15; `test_installer_legacy_ab_layout` 16; `test_legacy_boot_control_contract` 3; `test_ab_capacity_separation` 6; `test_build_profiles_storage` 11; `test_persistent_layout` 40; `test_hardware_support_pool_build_script` 3; `test_hardware_support_pool_finalize` 7; `test_hardware_support_pool_manifest` 6; `test_hardware_support_installed_size` 3; `test_installer_hardware_support_install` 3; `test_installer_hardware_support_pool` 13; `test_installer_hardware_support_service` 3; `test_installer_builder_hardware_support` 4; `test_acer_ab_release_identity` 5; `test_greia_update_tool` 4; `test_update_v3_bundle` 6; `test_system_update_service` 35; `test_system_update_streaming` 4; `test_clone_neutral_target` 6; `test_installer_persist` 20; `test_release_v2` 13. Named legs confirmed by test name (explicit receipt refusals/success, 5-way mismatch refusal, schema pin, compressed-overflow, single-bound, `read(-1)` refusal, single-open, outer round-trip/mismatch/pre-stream, order-lift both directions).
- `make verify`: `make validate` exit 0; `make shell-check` exit 0; `make footprint` exit 0; `make test` Ran 3587, FAILED errors=11 skipped=4 — preserved red, pre-existing environmental `AF_UNIX path too long` at `tools/x8_qemu/lifecycle.py:926` (mechanism-proven, outside the R4 delta surface; identical to R4-V-VERIFY4).
- Orbiter §§11.1–11.8: §11.1 identity, §11.2 unit legs + verify stages, §11.5 CLI-level positive bundle (rc 0; payload 282/65536/65536; support 750/88576; required total 84017152; headroom 1526595584), §11.6 CLI-level over-capacity refusal (rc 2; required 1971388416 > slot 1610612736; no output file), §11.7 PERSIST sensitivity, §11.8 single-traversal/single-extraction/cleanup — PROVEN. Strict artifact legs needing a Linux build host (real target-root compose, real ext4 payload, real dpkg pool, `systemd-analyze verify`, mounts/loop) UNPROVEN on the darwin host and DEFERRED, never waived.
- Deferred-physical list (per §12): Acer fresh install, real A/B partition write, exact-service staging, candidate boot/health commit/rollback, PERSIST survival, physical USB boot, 4161 MiB boundary reproof, hardware footprint/timing — required before binary/family release, not before R4 source closure.
- Session 03 status: CLOSED under this plan's sequencing until this plan opens it; R4 source closure is bound here.

## 2026-09-19 — R4 Linux-lane closeout at Linux-proven HEAD `762d4ebd` (R4-H-FINAL)

- Append-only rebinding of gaps G1–G3 after R4-V-LINUX verification-8 landed BLOCKED with substantial Linux green. The two 2026-09-19 R4 entries above are preserved as the docs-tranche and darwin-bound records; this entry, plus `HANDOVER.md` §32, carries the Linux-bound numbers. No earlier entry rewritten; no owner hardware errand added.
- Linux-proven SHA: `762d4ebdfa11d2f0c560cc990c68ecef3985bb14` (Orbiter clone exact-match, clean tree, `git diff --check` exit 0; zero project writes). Source-equivalence: `git diff c4ab45aa..762d4ebd` touches only `HANDOVER.md` (§31) and this ledger — no `src/`/`build/`/`tools/`/`tests/` delta — so the Linux numbers apply to the `c4ab45aa` source content.
- Focused suites green at that SHA (short remote TMPDIR `/tmp/gv8/tmp`): §10 focused 129/129; extra layout/support/persist/receipt/bound 127/127; emoji 38/38 (after host-level `python3-regex` install); PERSIST/streaming/outer-bound 27/27; `make validate`, `make shell-check`, `make footprint` all exit 0.
- `make verify`: full `make test` Ran 3557 in 2049 s, FAILED failures=2 errors=11 skipped=8. Eight errors are a host-prerequisite gap (missing `regex` backend), resolved green at host level. The remaining 5 reds (2 failures + 3 errors) are preserved with host-divergence mechanisms (forged-peer RST, `/nonexistent-probe` vs qemu-present host, `_host_which` PATH fallback, MBR part-UUID `sfdisk` semantic, boot-perf qemu-presence assumption), each reproduced in isolation and each outside the R4 delta — never waived.
- Orbiter §§11.1–11.8: §11.1 identity PROVEN; §11.2 `systemd-analyze verify` on both service units exit 0 PROVEN; §11.3 full-debootstrap target-root compose RED per the no-mount boundary (profile resolution succeeds; minimal-staging numbers apparent 207 B / allocated 77824 B with clone-neutrality proven); §11.4 real ext4 payload PROVEN (compressed 1668 / uncompressed 8646656 / minimum 67108864, `greia-strict-v8`, sha `979cff63…`, 13 checked paths); §11.5 positive bundle PROVEN (bundle 3911 B rc 0 schema 3; support 1508/83968; required finalized 151011328; headroom 1459601408 ≤ 1610612736); §11.6 negative refusal PROVEN (rc 2, required 1789394944 > slot 1610612736, no output file); §11.7 PERSIST sensitivity PROVEN; §11.8 single-traversal/cleanup PROVEN.
- Gap rebinding: G1 substantially PROVEN except debootstrap compose (RED per boundary); G2 NOT green — 5 reds preserved, fix owned by implementation follow-ups; G3 bound here.
- Worktree-divergence note: the authoring R4-H-FINAL worktree (baseline `b7854246`) carries a 7-file host-divergence delta vs the Linux-proven tree on exactly the routed surface; that delta is UNPROVEN on Linux and unclaimed here, owned by follow-up triage lanes.
- Deferred-physical list (per §12): no mounts/loop/install/destructive work on either lane; Acer install, A/B writes, exact-service staging, boot/health/rollback, PERSIST survival, USB boot, 4161 MiB reproof, hardware footprint/timing — required before binary/family release, not before R4 source closure.
- Session 03 status: CLOSED under this plan's sequencing until this plan opens it; the gate re-evaluates against the Linux-bound evidence above.

## 2026-09-20 — R4 post-review closure patch landed; local validation pending

- Independent review of `67c7c445` found five closure issues, not a new
  architecture failure: low-level bundle production still tolerated malformed
  supplied hardware support; support archive inspection accepted partial
  expected facts until an internal assertion; the active release runbook still
  showed stale 1 GiB Acer payload numbers; the root HW-03 file still looked like
  current owner routing; and the handover/ledger state did not yet describe the
  final post-review closure path consistently.
- Source fixes landed on `main`: `4f5d4ae9` makes
  `build_update_bundle()` fail closed on any canonical support-parser refusal;
  `5bb58d7b` makes expected support size/SHA an explicit both-or-neither
  contract. Regression fixtures were updated through `04adb6ed` so valid
  producer tests carry real valid support archives and malformed parity cases
  no longer depend on production publishing invalid support.
- Documentation/routing fixes landed: active release instructions use
  release-specific sizing placeholders rather than stale 1 GiB constants;
  `HW-03-PHYSICAL-LEGS.md` is explicitly historical/do-not-execute; the
  release workflow now routes to local closure validation and then Session 03.
- Fresh validation is deliberately **PENDING**, not inferred from older R4
  evidence. The exact autonomous brief is
  `docs/testing/2026-09-20_R4_CLOSURE_LOCAL_VALIDATION.md`: py_compile,
  focused update/support suites, baseline-relative diff check, full
  `make verify`, doc-routing checks, clean tree before/after. No source edits,
  Acer, Orbiter, Docker, mounts, destructive storage work, or owner intervention
  are part of that validation.
- Session 03 opens when that current-HEAD local validation returns green. If it
  fails, repair the demonstrated source/test defect only. Physical Acer
  install/update/rollback acceptance remains deferred certification evidence
  before a binary/family release and does not route this closure patch.

## 2026-09-20 — First closure validation failed; test-contract migration repaired

- Source-only validation at `749584b9` kept the owner machine within the
  intended boundary: no installer/image build and no hardware action.
- Production fail-closed support bundling was correct, but the test suite had
  widespread stale fixtures that still passed arbitrary zstd-looking bytes to
  `build_update_bundle()`. Focused candidate-support tests produced 6 errors;
  full `make verify` produced 147 errors from the same fixture class. The
  first `test_ab_install_composition` failure reproduced in isolation.
- The repair keeps production strict. Tests that need valid support now use the
  shared valid artifact from `tests/support_artifacts.py`; tests explicitly
  proving runtime rejection of malformed support construct the outer candidate
  directly in tests rather than asking the production producer to emit an
  invalid release.
- EOF whitespace defects reported by `git diff --check` were fixed.
- The local validation contract now explicitly forbids installer/root/release
  artifact builds, debootstrap, QEMU, mounts/loops, media writes, Docker,
  Orbiter, or physical hardware work on the owner system.
- Fresh current-HEAD validation remains pending. Session 03 starts only after
  the source/test validation returns green; physical Acer acceptance remains a
  later binary-release certification activity.

## 2026-09-20 — Second closure validation: core green, final fixture classes repaired

- Validation at `76361d724fe16a761695160f5cc42dd9f4557f62` had all eight core
  focused suites green and 12/14 high-fanout suites green.
- Remaining focused failures were ordering/setup drift, not product failures:
  valid candidate support allowed T3/update-activation staging to advance to
  incomplete host inventory before their intended missing-device predicate.
- Full `make verify` reported 49 errors, led by one truncated-support runtime
  negative still routed through the strict producer and shared x8 lifecycle
  helpers that still manufactured arbitrary compressed support bytes.
- Repairs preserve the production contract: malformed runtime candidates use a
  tests-only outer constructor; no-device tests satisfy only the inventory
  prerequisite and retain the production device resolver; x8 A/B lifecycle
  bundles use optional-null support because those tests do not exercise
  hardware-support installation.
- The validation brief now targets candidate-support streaming plus x8
  bootchain/devproof/devrun3 source-scope tests before full `make verify`.
- Owner-host boundary remains source/test execution only. No real installer,
  root/release image, debootstrap, QEMU execution, mount/loop, media-write,
  Docker, Orbiter, or physical-device action is authorized by this closure.

## 2026-09-20 — Third closure validation: final deterministic test defects repaired

- At `545f7a45`, every focused regression, diff check and documentation-routing
  check was green; full `make verify` still exposed one reproducible lifecycle
  ordering error plus one non-reproducible devproof storage-preflight failure.
- The lifecycle negative now provides only the complete inventory prerequisite
  so the shipped production path reaches and proves its intended missing-device
  refusal.
- The devproof race was caused by comparing against a mutable free-space
  snapshot. Both helper and direct test now request `total capacity + 1 byte`,
  which cannot become satisfiable when unrelated suite cleanup frees blocks.
- Future closure validation captures the entire full-suite output and uses a
  >=1200 s execution allowance; the suite currently takes approximately
  14–16 minutes on the owner host.
- Owner-host scope remains source/static/unit/integration testing only. Installer
  or release builds, Greia root composition, debootstrap, real QEMU, mounts,
  loop devices, media writes, Docker, Orbiter and physical hardware remain out
  of scope.

## 2026-09-20 — R4 source closure GREEN; Session 03 open

- Exact validated source/test HEAD:
  `44927e37dcb150d9fb6cbad7226a52c35c41bf91`.
- Validation ran source/static/unit/integration checks only; no installer/root/
  release-image build, debootstrap, real QEMU, mount/loop, media write, Docker,
  Orbiter or physical-device operation occurred.
- All declared focused suites passed, including 14/14 high-fanout regression
  suites, candidate-support streaming, bootchain, devproof, devrun3 and the
  complete 74-test lifecycle suite.
- `git diff --check 67c7c445..44927e37`: PASS.
- `make verify`: PASS, exit 0 — 3589 tests OK, 4 skipped, 451.024 s; validate,
  shell-check, footprint and final clean-bytecode stages also completed.
- Tree was clean before and after; no source/test edits occurred during the
  validation.
- Session 02/R4 source closure is therefore complete.
- **Session 03 — owner release CLI + compact release outputs is OPEN and is the
  next engineering session.**
- Physical Acer install/update/rollback remains deferred binary-release
  certification evidence and does not block Session 03.

## 2026-09-20 — Session 03 owner release CLI source implementation landed; source validation pending

- Added `tools/greia_release.py` as the single owner-facing release
  orchestration entry point with `build`, `doctor`, `build-profile`,
  `inspect` and `write-media`.
- Session 03 matrix intentionally contains only
  `acer-aspire-one-i386-ab`; final multi-platform output/report structure is
  established without fabricating the universal Setup image or future
  amd64/Pi bundles.
- The CLI reuses the established authorities instead of reimplementing them:
  shared `compose_root`, `build_release.py` payload/receipt/support producer,
  and `greia_update.py` profile-bound v3 bundle/capacity path.
- Added `build/compose-release-profile.sh` as the shell-owned composition
  lifecycle adapter: compose target, tear its mounts down, compose live,
  populate exact hardware support while the live chroot is active, then bounded
  cleanup. Python owns no mount/chroot cleanup. Direct `compose.sh` execution
  was also made self-cleaning; sourced image builders retain their existing
  cleanup ownership.
- Removed normal release minimum-size archaeology:
  `build_release_payload(... minimum_slot_bytes=None)` derives the minimum
  after real ext4 shrink as `shrunk_bytes + PAYLOAD_MIN_HEADROOM`; explicit
  values remain low-level overrides. The owner CLI passes the resulting
  payload receipt to `greia_update.py build`.
- Version must equal repository `VERSION`; release scratch/cache paths are
  centralized; final publication is atomic; failed builds preserve scratch and
  never publish the final release directory.
- `release-report.json` records source SHA, profile/layout facts,
  target/live/bundle sizing, payload/support/bundle hashes, portable producer
  facts and exact published-directory media accounting. Universal Setup is
  explicitly `deferred` to Session 08.
- `doctor` checks official Linux/x86_64/root/tool/profile/builder/workspace
  prerequisites using the selected output filesystem. `write-media` delegates
  to the existing safe writer and retains its exact-device interactive
  confirmation.
- Source-level regression coverage added in `tests/test_greia_release.py`
  plus producer-derived-minimum coverage in `tests/test_build_release.py`.
- **No real artifact build has been run in this source tranche.** Owner-host
  validation is strictly source/static/unit/integration only; no
  `greia_release.py build`, root composition, debootstrap, QEMU, mounts/loops,
  media write, Docker, Orbiter or physical hardware action is authorized.
- Next: execute
  `docs/testing/2026-09-20_SESSION03_RELEASE_CLI_LOCAL_VALIDATION.md`.
  If source validation is green, complete Session 03 with one real one-command
  Acer release build on the appropriate supported x86_64 Linux build host.
  Session 04 remains closed until that real release artifact exists.

## 2026-09-20 — Session 03 first source validation found one macOS path-spelling test defect; repaired

- Source validation at `8dd2d8c436202555a7d5966130c2846aea8804b8`
  stayed inside the source-only host boundary: no release/root/installer build,
  debootstrap, real QEMU, mounts/loops, media writes, Docker, Orbiter or
  physical-device work.
- py_compile, bash syntax, 7/8 focused suites, diff check and shell-check were
  green. `test_greia_release.py` had one deterministic failure; full
  `make verify` ran 3601 tests with the same single failure and 4 skips.
- Root cause: production intentionally canonicalizes `--output` through
  `Path.resolve()`. On macOS, TemporaryDirectory can be spelled under
  `/var/...` while canonical resolution returns `/private/var/...`. The
  test compared those two equivalent spellings as raw strings.
- Repair `dc36cfc93f01d5a9a3085421c499aa5b6d3c3e62` changes tests only:
  the path-schema test now explicitly asserts canonical output ownership and
  the build test compares against `release_root.resolve()`.
- Production release orchestration remains unchanged. Fresh corrected-HEAD
  validation is pending; no PASS is inferred from the failed run.
- If corrected source validation is green, Session 03 still requires one real
  one-command Acer release build on a supported x86_64 Linux build host before
  Session 04 opens.

## 2026-09-21 — Session 03 corrected source validation GREEN; real owner build is the remaining closure step

- The corrected Session 03 source validation is green after the canonical-path
  test repair: full `make verify` PASS with **3601 tests OK, 4 skipped**;
  project validation, Activity validation, source footprint and final
  clean-bytecode also completed successfully.
- The first-run failure is closed as a test-only macOS path-spelling issue:
  production intentionally canonicalizes release output paths, while the old
  assertion compared unresolved `/var/...` against resolved
  `/private/var/...`. Repair `dc36cfc93f01d5a9a3085421c499aa5b6d3c3e62`
  leaves production release behavior unchanged and asserts the canonical-path
  contract explicitly.
- Session 03 source scope is therefore green. No release/root/installer build,
  debootstrap, real QEMU, mount/loop, media write, Docker, Orbiter or physical
  hardware operation was part of that owner-workstation validation.
- The remaining Session 03 done-condition is now one real execution of the
  **single owner release command** on a supported x86_64 Linux build host,
  proving the current Acer-only matrix produces a complete Greia release
  directory, source-bound report, profile-specific update bundle and compact
  intermediates without manual low-level parameter plumbing.
- Canonical procedure:
  `docs/testing/2026-09-21_SESSION03_LINUX_RELEASE_BUILD_ACCEPTANCE.md`.
- Terminology correction: this is a **Greia release build with the current
  Acer-only matrix**, not an Acer installer image. The one universal
  `greia-setup-<version>.img.xz` remains a Session 08 output after the
  amd64 and ARM/Pi boot paths are real.
- Session 04 opens only after the Linux owner-command build acceptance is
  green.

## 2026-09-21 — Session 03 real Linux build attempt failed on live-media identity ordering; shared-composer repair implemented

- First owner-command build ran on Orbiter at exact source
  `65af8805faf00f1218abb5dbf0bd562a692426bd`.
- Preflight was green: current `main`, clean tree, focused release CLI 11/11
  PASS, and `greia_release.py doctor` PASS with all 6 checks green.
- The build correctly failed before publication while composing the
  live-installer root. Kernel package configuration invoked
  `update-initramfs`; the Greia
  `greia-live-media-id` hook refused because
  `/etc/greia-os/live-media-id` was absent. The linux-image and meta-package
  dpkg failures were consequences of that first hook failure.
- Root cause is composition ownership/order drift: the traditional
  `build/build-installer-image.sh` path seeded the live-media identifier
  before package installation, but the shared
  `compose_root(... role=live-installer)` route used by Session 03 did not
  own that prerequisite.
- Repair moves that invariant into the shared composition layer through
  `compose_prepare_live_media_identity`. Generic live-root composition calls
  it before package installation; the traditional installer-image consumer
  delegates to the same helper.
- The helper is root-local and idempotent: a valid existing identity is
  preserved for repeated operations on one root; a fresh root receives a
  fresh UUID. `COMPOSE_LIVE_MEDIA_ID` is only an output used by the outer
  installer-media assembly.
- The fail-closed initramfs hook remains unchanged. No update-initramfs,
  dpkg, or release-CLI bypass was introduced.
- Regression coverage now locks shared ownership and ordering before the
  kernel postinst boundary.
- Repair commits:
  `05d058c3`, `9a187baf`, `1c5bb376`, `a6fd434a`.
- Failed-build evidence/scratch at the old SHA remains preserved and there
  were no leftover mounts.
- Next: validate the repaired current `main` on Orbiter with shell syntax,
  focused build/release suites and `make verify`. If green, rerun the
  Session 03 Linux owner-build acceptance from a fresh SHA-derived work root.
  Session 04 remains closed until that build succeeds and publishes/inspects
  the release artifacts.

## 2026-09-22 — Session 03 repair validation hit verification-hygiene boundary; cleanup/footprint scope corrected

- Validation at `99f9588d62380e01537adc4eff09cbd93c065769`
  passed shell syntax, release CLI focused tests (11/11), system-overlay focused
  tests (23/23), and `git diff --check`.
- `make verify` stopped before unit tests because its initial
  `clean-bytecode` target recursively walked the entire checkout and hit the
  intentionally preserved, root-owned failed release scratch/cache tree under
  ignored `tmp/`.
- This is not a product regression and the preserved failure evidence must not
  be deleted/chowned as a prerequisite for ordinary source verification.
- `clean-bytecode` now traverses only source-owned Python trees
  (`src tests tools activities`) and the repository root non-recursively.
- The source-footprint stage had the same conceptual defect: “source
  archive-relevant” used `du` over the whole checkout, counting ignored build
  evidence and risking the same permission failure. In Git checkouts it now
  sums tracked-file sizes only; explicit runtime-payload measurements remain
  unchanged.
- Regression coverage locks both boundaries.
- Repair commits: `51ec3aba`, `dfbf8dc8`, `71375f55`, `d1f60390`.
- Next: pull current main; with the old failed root still present and untouched,
  prove `make clean-bytecode` and `build/footprint-source.sh` succeed, run
  the hygiene-focused test and full `make verify`; only then run doctor and a
  fresh Session 03 owner build. Session 04 remains closed.

## 2026-09-22 — Hygiene gate caught Make recipe escaping defect; repaired

- Validation at `e9ba8f01e16ae3d9912e9d2396e90068eef591d0`
  stopped in the focused hygiene test before any cleanup traversal, doctor, or
  release build.
- The source-bounded `clean-bytecode` design was correct, but the Make recipe
  used shell loop references as `$root` instead of `$$root`. GNU make would
  consume `$r` before the shell, so the loop would not clean the intended
  source roots.
- The focused test correctly caught this before execution.
- `972aeb7e` fixes all three Make recipe references to `$$root`.
- `30c47909` strengthens the regression contract to require the escaped
  directory guard and both escaped `find` calls.
- `05cd356f` was a connector-side no-op commit (same Makefile blob); it was
  detected immediately by re-fetching the file and carries no behavioral
  change.
- Old privileged build evidence remains preserved and untouched.
- Next: rerun the hygiene test, direct cleanup/footprint proofs and full
  `make verify`; only if green proceed to doctor and a fresh Session 03 owner
  build. Session 04 remains closed.

## 2026-09-22 — Hygiene regression corrected to avoid connector-sensitive dollar literals

- Validation at `d5530b78d9c4bde7e7b302fb3a9d37204c5369a7`
  confirmed the Makefile itself was correct (`$$root` in all three loop
  references) but the focused regression still asserted the buggy
  single-dollar spelling.
- The repeated mismatch came from the GitHub contents write path collapsing
  literal `$$` sequences inside the Python test source.
- `5f7aaa19` removes those connector-sensitive literals from the test and
  constructs the expected escaped Make variable at runtime with
  `chr(36) * 2 + "root"`; it also explicitly rejects the single-dollar form.
- The committed test blob and Makefile were re-fetched and verified after the
  write.
- Next: rerun the focused hygiene test only; if green, proceed directly through
  the direct cleanup/footprint proofs, full `make verify`, doctor, and the
  owner build. Session 04 remains closed.

## 2026-09-22 — Session 03 reached hardware-support pool; pool now owns required APT metadata

- Owner build at `821934af4e387b7b1278a3a2c6736cd5d48db447`
  passed the repaired source gate (3603 tests, 8 skipped) and doctor (6/6).
- The previous live-media-id/kernel-postinst failure did not recur.
- The next failure was APT exit 100 while resolving
  `alsa-topology-conf` during hardware-support pool population.
- Debian Bookworm still publishes that package; the failure was caused by
  internal sequencing, not package removal.
- `compose_root()` legitimately applies footprint hygiene and clears remote
  APT lists before Session 03 calls the separate pool producer. The pool
  producer incorrectly depended on those caller-owned lists remaining present.
- The traditional installer-image path populated the pool before hygiene, which
  hid this dependency.
- The pool producer now owns its APT metadata lifecycle: refresh before
  availability/dependency resolution, finalize the self-contained pool, then
  remove remote lists again on success.
- Repair commits: `70729300`, `93675ba1`, `cf2f0068`.
- Next: validate current main, doctor, then run a fresh owner build. Session 04
  remains closed until Session 03 publishes and inspects the release.

## 2026-09-22 — Privileged release bytecode pollution + false-green cleanup repaired

- Validation at `3a8a1a221e316230bb507aacccaa56b74261a867`
  ran 3603 tests successfully, but final bytecode cleanup hit 64 permission
  errors on root-owned generated bytecode under source trees.
- Those artifacts came from prior `sudo greia_release.py doctor/build`
  execution importing project modules and launching privileged Python helpers.
- `make verify` also incorrectly returned 0 because failures inside the
  `clean-bytecode` shell loop were not propagated.
- `712d351a`: privileged release execution disables Python bytecode before
  project imports and passes `PYTHONDONTWRITEBYTECODE=1` to the whole release
  subprocess tree.
- `ed61ddfd`: bytecode cleanup now fails truthfully on deletion errors.
- `b106980b` + `2d5f8645`: regression coverage locks both behaviors.
- One historical-state cleanup is explicitly required after pulling:
  `sudo make clean-bytecode`. The target is source-scoped and must not touch
  preserved ignored release evidence.
- Next: one-time generated-bytecode cleanup; focused hygiene/release tests;
  full non-root `make verify`; privileged doctor plus explicit proof that no
  root-owned source bytecode reappears; then a fresh owner build to exercise
  the pending hardware-pool APT-metadata repair.
- Session 04 remains closed.

## 2026-09-22 — Bytecode cleanup single-owner repair; local acceptance agent given bounded repair authority

- The `8717db49` cleanup attempt exposed another single-dollar Make-loop
  regression and removed nothing.
- Root cause of the repeated `$$ -> $` mutation was corrected: it came from
  JavaScript `String.replace` replacement-string semantics in this session's
  patch tooling, not from the GitHub connector.
- The shell loop has been eliminated rather than patched again.
- `tools/clean_bytecode.py` now solely owns source-bytecode cleanup; Make
  delegates directly to it. The helper is source-scoped, preserves ignored
  evidence, raises on deletion failures, and raises on unreadable traversal.
- Focused tests exercise scoping and failure propagation.
- Effective repair commits:
  `c19757a0`, `0ee7e44a`, `a45e4879`, `d8888c1e`, `5a23a49b`,
  `02ef7c18`.
- The privileged release bytecode-prevention repair from `712d351a` remains
  required and still awaits post-doctor/build live proof.
- For the remainder of Session 03, the local Linux acceptance agent may make,
  test and commit bounded obvious repairs in the active release/verification
  path instead of stopping on every source-local defect. It must stop for
  destructive-device/media actions, security/trust weakening, broad
  architectural decisions, package-policy changes with product impact,
  evidence deletion, or genuinely ambiguous fixes.
- Next: one-time privileged cleanup via the new owner; focused tests; full
  non-root verify; doctor + root-bytecode contamination check; fresh owner
  build to exercise the pending hardware-pool APT metadata repair.
- Session 04 remains closed until Session 03 publishes/inspects a real release.

## 2026-09-22 — Hardware-pool intermediate ownership repair; archive allowlist preserved

- The real owner build on `6935a411` cleared the live-media identity and
  APT-metadata stages and failed later at hardware-support archiving:
  `unexpected pool top-level files: ['available-candidates.txt',
  'candidates.json']`.
- The pool producer's candidate-discovery intermediates were left at the pool
  top level after finalization consumed the manifest. Repaired at the
  ownership seam: the producer removes both intermediates right after
  successful finalization, keeping the fail-closed archive allowlist
  (`manifest.json`, `Packages`, `Packages.gz`, `pool/`) intact instead of
  widening it. Overlay regression now locks finalize < cleanup < hygiene
  ordering.
- Pre-commit validation: focused overlay 23/23 OK; full `make verify` 3608
  tests OK (skipped=8), exit 0, no permission errors. Doctor and the failed
  build recreated zero root-owned source bytecode.
- Next: commit, push if remote is quiet, fresh owner build against the
  repaired producer.

## 2026-09-22 — Payload shrink defect repaired (flex_bg); support semantics still open

- Bundle capacity refusal on `248ab0df` (required 2405617664 > slot
  1610612736) traced to a real producer defect, not product sizing: the
  shipped payload filesystem spans the full slot with ~472 MiB free
  because default flex_bg (one flex group over all 12 block groups) makes
  e2fsprogs `resize2fs -M` report the current size as the minimum.
  Bisected empirically (200M/512M shrink, 1G/1.5G refuse; identical 1.5G
  without flex_bg shrinks 393216 -> 257690 blocks).
- Repair: payload mkfs uses `-O ^flex_bg`; post-shrink size is now derived
  from authoritative `dumpe2fs -h` geometry with a fail-closed
  container==extent check. Locked by command-shape, strict-parse,
  mismatch-refusal, and real-e2fsprogs regression tests (new
  `test_payload_shrink_real.py`, Linux-gated). Pre-commit `make verify`:
  3612 tests OK, exit 0.
- Still open: re-measure the real payload receipt via owner rebuild, then
  the hardware-support selected-set capacity semantics (§5-8 of the
  capacity mission). No slot/product change authorized yet.

## 2026-09-22 — Hardware-support selected-set capacity semantics implemented (source scope)

- Bundle time has no machine inventory: `tools/greia_update.py`
  `_check_profile_capacity` proves base payload + generic reserves against
  the profile slot with support term 0, while still fail-closed verifying
  the support metadata. Corrupt support still refuses (`rc=2`).
- `tools/finalize_hardware_support_pool.py` now freezes verified
  per-candidate `dependency_closures` (candidate + recursive
  Depends/Pre-Depends alternatives present in the pool; conservative
  superset, `--no-install-recommends` scope). Validated by
  `hardware_support_archive.py` (`sorted/unique/self-member/pool-member/
  candidate-key` checks) and carried on `VerifiedHardwareSupportPool`.
- `VerifiedHardwareSupportPool.selected_installed_bytes(firmware, microcode)`
  is the new bound owner: union of selected closures, de-duplicated,
  summed over verified per-package installed sizes. Empty selection binds
  0; missing closures or unknown selection refuse fail-closed (never falls
  back to the whole-pool total).
- Fresh install: `device_seams.py` resolves the machine selection from the
  same attested snapshot via `InstallerHardwareEnablementPlanner`
  (`inventory_snapshot` replay seam, no second racy snapshot) and proves
  capacity on the selected bound; `fresh_ab_install.py` ceiling-checks the
  selected bound against the image-authorized whole-pool
  `GREIA_AB_SUPPORT_INSTALLED_BYTES` (`total_installed_bytes`, never
  compressed bytes) and passes the selected bound into
  `SlotFinalizer.finalize()` (`support_installed_bytes` override, same
  formula re-check).
- System update staging: new `support_pool_factory` seam reuses the open
  candidate stage pool (no second extraction); capacity preflight runs
  after inventory/selection on the verified selected bound and threads the
  same number through `SlotWriter` and finalization. Without a staged pool
  only an empty selection binds 0.
- Single formula owner unchanged:
  `greia_installer.layout.require_finalized_slot_capacity`
  (`base + support + FINALIZATION_GROWTH_BYTES + SLOT_METADATA_RESERVE_BYTES`).
- Tests: closure finalize/validation/selection suites, release-CLI
  bundle-accept + tamper-refusal rewrite, orchestration harness
  `dependency_closures` + `support_pool_factory`, seam-composition pool
  closures + `support_pool_factory` production assertion + selected-bound
  regression.
- Next: full `make verify`, then owner rebuild to re-measure the real
  payload receipt and exercise the selected-set path on a real release.
  Session 04 remains closed.
- Pre-commit `make verify`: 3618 tests OK (skipped=8), exit 0, clean tree.

## 2026-09-23 — Session 03 CLOSED on real owner release build

- Successful source SHA: `6c58601eaad32ad2bba30acb24e33333b9c4bbf3`
  (HEAD = origin/main, ahead/behind 0 0, tracked tree clean).
- Doctor exit 0 (`ok=true`, Acer profile present); no root-owned source
  bytecode after doctor or after build.
- Owner build exit 0, `status=complete`, `source_commit == SOURCE_HEAD`.
- Payload real: compressed=383881888, uncompressed=1110081536,
  minimum=1111130112,
  sha256=c9b58aee72e058c288204e1bb1136859a8d8d8807f21a66178789982a4b3f543
  (old broken 1610612736 gone — flex_bg/geometry repair proven in the
  production artifact).
- Bundle: 540126645 bytes,
  sha256=6b5cf05f6ad81979fc9bd53c4f1ae1491da024eaf436aabe31e35779f4860a67.
- Hardware support: packages=58, compressed=156244008,
  whole-pool-installed=710070272 (ceiling), dependency-closures=37,
  archive sha256=f228a314383bec838aed06fc808bd564dc85c96ac70537a3163918313842c24e.
  Archive allowlist intact; no live-media-id / APT-candidate regressions.
- Inspect report PASS; inspect bundle PASS (privileged read; bundle
  publishes root-owned mode 600). Consistency PASS. Transient
  `.greia-work` clean, no leftover mounts, tree clean, HEAD unchanged.
- Universal Setup image stays deferred to Session 08.
- Session 03 CLOSED; Session 04 OPEN.

## 2026-09-25 — Session 04 EXECUTE root cause found; security decision pending

- Corrected the temporary faulthandler lifetime with a module-owned serial
  handle and reduced the repeating interval to 120 seconds. Added marker-gated
  socket-boundary diagnostics and focused regression coverage. The transaction
  service suite passed 45 tests; Session-04 harness tests passed 20; product
  install harness tests passed 38.
- Rebuilt the instrumented legacy i386 installer through the canonical builder
  and inspected the built live SquashFS. Profile, embedded S03 bundle SHA, and
  58-package/710070272 support facts matched the recorded Session-03 inputs.
- Final product-mode QEMU evidence is captured in
  `docs/testing/session04-evidence/attempt13-install-execute-serial.log` and
  summarized in
  `docs/testing/2026-09-25_SESSION04_INSTALL_EXECUTE_ROOT_CAUSE_AND_DECISION.md`.
  The service remained active through `finalize-completeness`, then apt in the
  mounted slot failed `setgroups`, `setegid`, and `seteuid` with
  `Operation not permitted`; systemd recorded `Result=exit-code` and
  `ExecMainStatus=1`. The client empty response is downstream of that service
  refusal; no external SIGKILL is claimed.
- Host sandbox reproduction was completed as a separate diagnostic: the
  unsandboxed exact-artifact service stack passed, while the host full sandbox
  hit a distinct early e2fsck SIGSEGV. Bisect showed that removing
  `ProtectSystem=strict` or `NoNewPrivileges=yes` avoided that host-only
  failure, but this does not explain the guest apt failure and is not authority
  to weaken the shipped unit.
- No product repair has been applied. Session 04 remains OPEN, blocked on the
  explicit security decision: add narrowly scoped `CAP_SETUID`/`CAP_SETGID`, or
  choose an explicit root apt-sandbox policy. Temporary diagnostics and
  evidence remain until that decision; owned mounts, loops, and scratch were
  removed and host disk had approximately 84 GB free at cleanup.
