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
  `docs/archive/testing/2026-09-25_SESSION04_INSTALL_EXECUTE_ROOT_CAUSE_AND_DECISION.md`.
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
- Follow-up review selected and landed the narrow repair: keep
  `NoNewPrivileges=yes` / `ProtectSystem=strict` and add only `CAP_SETUID` and
  `CAP_SETGID` to the existing `CAP_SYS_ADMIN` / `CAP_SYS_CHROOT` contract.
  It also found and repaired a second service-topology defect: executing
  `transaction_service` itself with `python -m` while composition re-imported
  it canonically could split `__main__` and package module/class identity. A
  thin `transaction_service_entrypoint` now owns execution and the service
  implementation is library-only. Permanent contract tests pin both repairs.
  Session 04 remains OPEN pending Orbiter focused tests, installer rebuild and
  product-mode QEMU; temporary diagnostics remain until a confirming install.

## 2026-09-25 — Post-GitHub Orbiter validation blocked at apt ownership

- The repair ancestor was verified in `46a654fdc27acd20193285c702fb2761911c8936`,
  with `HEAD == origin/main`, clean tree, immutable S03 bundle SHA, and 84 GB
  free. Focused validation passed: 23 unit-contract, 46 transaction-service,
  13 seam-composition, 20 Session-04 legs, and 38 ProductHarness install tests.
- A new diagnostic installer was built from S03 and its live SquashFS was
  inspected. The canonical entrypoint, library-only service, exact four
  capabilities, `NoNewPrivileges=yes`, `ProtectSystem=strict`, embedded bundle
  SHA, 58 support packages, 710070272 support ceiling, and no bytecode all
  matched the repair contract.
- The first post-repair QEMU run exposed missing target-chroot `/dev/pts`.
  A shared `dev/proc/sys/run` chroot mount helper was added. The next run
  reached package configuration but recursive binds left the slot busy; normal
  then lazy detach cleanup was added and regression-covered.
- The latest clean diagnostic run is preserved at
  `docs/testing/session04-evidence/post-repair-04-cap-chown-refusal.log`.
  Apt now reaches package configuration and fails only at
  `chown _apt:root /var/cache/apt/archives/partial` with
  `SetupAPTPartialDirectory (1: Operation not permitted)`.
- This requires an explicit decision beyond the authorized exact four-
  capability contract: add `CAP_CHOWN` or change apt ownership/privilege
  behavior. No such change was applied. The QEMU attempt was stopped cleanly;
  no Session-04 mounts or loops remain, and approximately 73 GB was free at
  cleanup. Session 04 remains OPEN; no lifecycle leg or clean-build acceptance
  has started.

## 2026-09-25 — Apt ownership decision brief prepared

`docs/archive/testing/2026-09-25_SESSION04_APT_OWNERSHIP_DECISION.md` records the
post-GitHub Orbiter evidence and the explicit decision between adding
`CAP_CHOWN` and changing apt's ownership/privilege behavior. It preserves the
four-capability contract as the current authority, documents the proven
`chown _apt:root` failure, and forbids silently extending the sandbox. No
option has been applied; Session 04 remains OPEN pending owner/agent review.


## 2026-09-25 — Session 04 apt ownership conclusion deferred pending fatal-tail proof

- Reviewed `docs/archive/testing/2026-09-25_SESSION04_APT_OWNERSHIP_DECISION.md` and the committed QEMU refusal.
- The visible `chown _apt:root ... SetupAPTPartialDirectory` line is warning-level in APT; the prior runner kept only the first 256 stderr characters, so a later fatal apt/dpkg/postinst reason could be hidden.
- Do **not** add `CAP_CHOWN` yet. The exact four-capability contract remains authoritative.
- GitHub repair now preserves bounded stderr head + fatal tail so the next refusal can identify the real failure.
- Replaced lazy/best-effort chroot detach with shared recursive fail-closed cleanup across fresh install, legacy install and update staging. Nested binds collapse to exact minimal tracked roots; failed roots remain recorded.
- Next: focused Orbiter tests -> rebuild diagnostic installer from unchanged S03 bundle -> fresh-install leg only -> inspect the actual fatal tail. Reconsider capabilities only from that evidence. Session 04 remains OPEN.


## 2026-09-25 — Session 04 infrastructure stop: Orbiter root disk failure

- All focused Session-04 suites were green at `c8054717`; S03 and all candidate digests re-verified.
- The next installer build failed with an unreadable SquashFS immediately after `mksquashfs` success.
- Kernel logs on Orbiter's sole `/dev/sda` report repeated current ATA/SCSI medium errors, including during the failed build. Treat this as hardware failure, not a Greia source defect.
- **Do not resume heavy build/QEMU I/O on this disk.**
- Preserve local-only immutable artifacts to healthy storage first. Clone source fresh from GitHub rather than copying the repo from the failing disk.
- Re-hash the copied Session-03 release and four candidate bundles before accepting them as continuity evidence.
- Once on healthy storage/build media, resume exactly at: focused validation if environment changed -> diagnostic installer rebuild -> fresh-install-only rerun -> inspect true apt fatal tail. Do not add `CAP_CHOWN` without that proof.

## 2026-09-27 — A/B GRUB installer fails to boot on the reference Acer (PHYSICAL, negative)

- Built `acer-aspire-one-i386-ab` from the verified S03 bundle `6b5cf05f…` at HEAD
  `b3bccfb4` (docs-only ahead of `c8054717`; note `git pull` could not authenticate in
  this environment, so no sync actually occurred). Image
  `greia-os-installer-acer-aspire-one-i386-ab.img`, 1818230784 bytes, SHA-256
  `f75b7c4f105420fbf11323062f5a50ba59c4516d66de48b9e3e09782b414f6d7`, digest re-verified
  before and after flashing.
- Flashed to `/dev/sdb` (LaCie iamaKey, serial `eca3505216d7d3`, 8086618112 B) with
  `tools/greia_release.py write-media --erase-device`. Write verified: MBR present, GRUB
  boot sector `eb 63 90`, `sdb1` ext4 `PIP_INSTALL`, first 64 MiB byte-identical to the
  image. `sgdisk --zap-all` was required first, under explicit owner authorisation,
  because the safe writer refuses already-partitioned media (see below).
- **PHYSICAL result: negative at the earliest stage.** Owner reports black screen with a
  brief blinking cursor, then black. No Greia boot screen, no graphical installer,
  installation not startable. First physical evidence for this artifact; it is a failure.
- **Cause class is a known, already-accepted constraint, not a new discovery.**
  `build/live-syslinux/syslinux.cfg.in` records that GRUB's MBR does not work on the
  reference Acer firmware+stick combination; the proven path is
  `legacy-x86-i686-dev` on Syslinux/FAT32. The A/B release route is GRUB. The image also
  ships `quiet splash loglevel=0 console=null panic=0`, the diagnostic suppression that
  `docs/archive/reviews/2026-08-20_ACER_INSTALLER_BOOT_REGRESSION.md` §3.1 prohibits, which is
  why the failure presented without a readable error. The removed GRUB theme and the
  1600x900 full-colour boot-canvas regeneration were reintroduced 2026-08-20..24 and are
  in the shipped image.
- **The A/B GRUB route has no positive physical evidence on the reference device and now
  has one negative result. Treat it as UNPROVEN there** until a physical pass exists; the
  2026-08-20 record's "physical re-acceptance pending" was never closed.
- Two hypotheses tested and **refuted** — do not re-propose: PAE (four-way QEMU CPU
  cross-test; `core2duo`, `n270`, `qemu32` all boot to the live squashfs;
  `WARNING: PAE disabled` in zero runs) and UEFI-only firmware (a real support limit of a
  provably BIOS-only image, but not established as this failure). QEMU does prove the
  GRUB→kernel→initramfs chain is sound on emulated legacy-BIOS x86.
- **New tooling defect, real and separable:** `build/write-image.sh:51` demands exactly one
  `lsblk --json <device>` entry, but util-linux 2.39.3 returns disk plus partitions as flat
  siblings, so the safe writer **cannot flash any already-partitioned USB stick**. This
  forced the authorised out-of-writer erase and blocks routine re-flashing of used media.
- Uninvestigated per owner instruction: 982 MiB accounted installed size against a ≤800 MiB
  profile preferred target (required target <1000 MiB).
- Decisions D1–D8 for the lead agent are in
  `docs/archive/reviews/2026-09-27_ACER_AB_GRUB_INSTALLER_PHYSICAL_BOOT_FAILURE.md`. Chief: which
  boot path is the product path for the reference device, and whether `console=null` /
  `panic=0` may ship in a product installer.
- Next action: owner returns the stick, then
  `sudo bash tools/build-and-flash-development-usb.sh legacy-x86-i686-dev /dev/sdX`,
  requiring both installer-artifact and final read-only USB verification to report PASS,
  then record the last visible boot stage per the 2026-08-20 review §8. Do not rebuild or
  reflash `acer-aspire-one-i386-ab` onto the reference Acer until the boot-path and
  console-suppression decisions are made.


## 2026-09-27 — Acer A/B GRUB physical boot failure

- Physical `acer-aspire-one-i386-ab` USB test failed before the Greia boot screen.
- Existing accepted Acer postmortems already prove this firmware/stick combination does not reliably execute the GRUB/MBR removable-media path; active FAT32 + Syslinux is the proven first-stage path.
- Mark the current A/B GRUB removable installer **UNPROVEN on the reference Acer**. Do not repeat that physical test unchanged.
- Immediate physical recovery: build/flash `legacy-x86-i686-dev` with `tools/build-and-flash-development-usb.sh`; capture exact last visible stage. This is a narrow sanity test of the already-proven boot path, not a replacement for A/B lifecycle work.
- After positive Syslinux boot evidence, reconcile the A/B installer medium with the proven Syslinux/FAT32 first stage while keeping the A/B installed-disk/update semantics separate.
- The unrelated safe-writer bug that rejected already-partitioned removable disks has been fixed in `build/write-image.sh`; no external `sgdisk --zap-all` workaround should be needed for ordinary reflashing.

## 2026-09-27 — Acer Syslinux dev USB built; verifier FAT gate blocks physical test

- Ran the named proven procedure for real at `cadfe472`:
  `sudo bash tools/build-and-flash-development-usb.sh legacy-x86-i686-dev /dev/sdb`
  (LaCie iamaKey, serial `eca3505216d7d3`, 8086618112 B, `RM=1`; desktop automount
  `/media/orb/PIP_INSTALL` unmounted first). This is the A16 legacy-BIOS removable path,
  **not** the A/B GRUB engineering image from the previous entry.
- Artifact: `out/greia-os-installer-legacy-x86-i686-dev.img`, 1289748480 bytes, SHA-256
  `5b8bada7797a363173303978461d0f583cb306c567f29934ec73455e1b214c91`.
  `Developer installer artifact verification: PASS`.
- Media written with the postmortem-proven writer: active FAT32 `GREIA`, Syslinux VBR
  patched into the partition boot sector, `syslinux mbr.bin` in the MBR first 440 bytes,
  `ldlinux.sys`/`syslinux.cfg`/modules under `/boot/syslinux`. Boot diagnostics contract
  holds: `console=tty1`, `panic=0`, no `quiet`/`splash`/`console=null`/`loglevel=0`/
  timed panic reboot.
- **`usb_flash_readback_verification=FAIL`.** `tools/verify-live-usb.sh` gates on
  `fsck.vfat -n` exit status. Two benign causes, both verified by hand: the patched boot
  sector vs the stale `mkfs.fat` backup at sector 6 (fsck itself calls this "mostly
  harmless"), and 29 stale free clusters / free-cluster summary off by 29.
- Every substantive check the gate never reached was run independently and **all passed**:
  partition-1 bootable, `.disk/live-uuid` match (`667eed94-…`), `console=tty1`, `panic=0`,
  no suppression, `vmlinuz`/`initrd.img`/`filesystem.squashfs` byte-identical, all three
  `payload/` files byte-identical, `syslinux.cfg` identical to template, `ldlinux.sys`
  present. Conclusion: the media is content-correct and bootable; the **gate** is too strict
  for this writer recipe. Owner decision pending — do not weaken or delete the check
  without a decision.
- Validated the `d4bece31` safe-writer fix narrowly: `bash -n` passes, and one regression
  added to the existing owner `tests/test_greia_release.py` pins the corrected topology
  rule (direct `part` siblings accepted, unrelated mapper sibling refused). 14/14 pass.
- Documentation reconciled: the universal-media architecture document was verified
  **already correct** about `MBR -> active FAT32 -> SYSLINUX`; only its authority line
  lacked ADR 0036. The runbook/handoff claims that it prescribed GRUB MBR were false and
  are corrected by appended notes. §12 appended to the 2026-09-27 failure review confirming
  the failed artifact was the intermediate Session-04 GRUB engineering installer and that
  one-universal-image is not invalidated. **Do not replace installed Acer GRUB A/B.**
- Stale loops now three (`loop2`, `loop34`, `loop35`), all `autoclear=1`, clearing only on
  reboot. The leak is **reproducible**: `build-installer-image.sh` cleanup reports
  `loop partition mappings remain after bounded partx teardown` on this host, so §12's
  "loop audit must be empty" rule fails on every build until a reboot happens. One Orbiter
  reboot is owed. Never `losetup -D`.
- Session 04 lifecycle untouched this turn: no QEMU leg, no transaction/capability change,
  `CAP_CHOWN` still **NOT AUTHORIZED**. Next software step is unchanged: diagnostic Session-04
  installer rebuild from the unchanged S03 bundle, **fresh install only**, and report the
  true apt fatal tail before any capability change.

## 2026-10-03 — Acer hardening reconciliation: role-specific Wi-Fi ownership restored

- Local source acceptance of the review candidate stopped before build because
  the live installer already ships
  `EnableNetworkConfiguration=true`; a candidate that also assigned wireless
  DHCP to systemd-networkd would create two L3 authorities.
- Canonical `main` now preserves the intended split:
  - live installer: iwd owns association/authentication + L3; networkd marks
    wireless unmanaged;
  - installed target: iwd owns association/authentication only; networkd keeps
    `DHCP=yes`.
- The same tranche carries the previously reviewed bounded B4 profile ownership
  migration and its source regression tests from the Acer first-boot
  restart-loop investigation.
- Artifact verifiers now inspect the iwd policy together with the matching
  networkd policy rather than assuming one wireless L3 owner for every image
  role.
- Evidence boundary: **UNPROVEN beyond source review**. No image was built, no
  USB was flashed, and the Acer was not modified in this tranche. The next gate
  is provider-free/local source validation on the exact canonical `main`
  commit; only after that passes may a development installer be rebuilt and
  physically re-accepted.

## 2026-10-03 — Canonical source acceptance stopped on one stale B3 staging assertion

- Exact tested canonical source before this correction:
  `af6fb79298e7b6ed5366151aa14ebe2e3d26ebd1`.
- Role-specific Wi-Fi ownership passed all source checks, five focused suites
  passed 85/85, both negative ownership controls bit correctly, and the B4
  first-boot/profile contract passed all ten explicit source invariants.
- `make verify` ran 3897 tests and produced 16 failures: the historical 15
  unrelated failures plus exactly one new failure,
  `test_image_staging_contract.TargetImageCarriesFirstBootFixesTests.test_first_boot_repairs_profile_data_ownership`.
- That failure was a stale staging test asserting the retired B3 marker and
  recurring/unbounded ownership-repair shape. It contradicted the accepted B4
  design already covered by `test_first_boot_migration.py`.
- Canonical `main` now updates only that staging contract. The replacement
  asserts the stronger B4 image-staging invariants: symlink/non-directory root
  refusal, fixed-root 2770 normalization, B4 marker gating, top-level
  group-write repair, recursion limited to `progress`/`storage`, `-xdev`,
  `chown -h`, and absence of the retired B3/unbounded sweep.
- No runtime/build implementation changed in this correction. No image, USB or
  Acer operation occurred.
- Evidence boundary remains **SOURCE / UNPROVEN** until the corrected staging
  test and full provider-free verification are rerun on the exact new
  canonical `main` SHA.

## 2026-10-05 — B4/network ownership reconciliation source-accepted

Exact tested source: `69624a4f96d6f441327966a85ba5deb0ea3fcab4`.

Owner-controlled local evidence:

- corrected image-staging suite: 19/19 PASS;
- focused first-boot/network/tmpfiles/update suites: 85/85 PASS;
- retired-B3-marker positive control: expected FAIL observed;
- unbounded whole-tree-recursion positive control: expected FAIL observed;
- full unittest phase: 3897 tests, 15 failures, 8 skipped;
- the 15 failure identities are byte-for-byte/identity-exact with the established
  unrelated historical baseline;
- the previously new B4 staging failure is absent;
- worktree remained clean and no build, USB write or Acer mutation occurred.

Therefore the B4/profile migration and role-specific Wi-Fi ownership
reconciliation are **SOURCE-ACCEPTED**.

The broad `make verify` target still exits 1 at the test phase because the
historical 15 are real unresolved failures; therefore its later `validate`,
`shell-check` and `footprint` phases did not execute. Those three source
gates must be run explicitly before spending another build/flash cycle.
No hardware/image evidence is claimed yet for the reconciled source.

## 2026-10-06 — Build-host loop leak root cause fixed at source

The pre-build host gate found `/dev/loop11` still associated with a deleted
target image from an earlier successful legacy development-installer build.
The exact source cause was identified in `build/build-installer-image.sh`:
after creating `TARGET_LOOP` with `losetup --partscan`, the payload path
performed a plain `losetup -d "$TARGET_LOOP"` and immediately cleared
`TARGET_LOOP`. If the partition child remained open, Linux converted the
parent to AUTOCLEAR rather than releasing it; final cleanup could no longer see
the loop, deleted the temporary target image, and left a loop mapped to a
deleted backing file.

Source repair generalizes the lifecycle rule:
- the target-payload early detach now uses the shared verified
  `safe_unmount_paths` + `safe_detach_loop` path and clears its variable
  only after success;
- legacy image finalization and both read-only image verifiers now use the same
  shared verified cleanup rather than direct `losetup -d`;
- cleanup failure makes an otherwise successful command fail and preserves its
  work data instead of deleting the backing tree;
- a repository-wide regression scans build/tool shell scripts and rejects any
  `--partscan` owner that lacks shared verified detach or directly calls
  `losetup -d`.

No full image build has yet tested this repair. A small synthetic loop lifecycle
acceptance on the build host is required first. The already-stuck historical
`/dev/loop11` remains an operator/host-state blocker until it is gone; source
changes do not retroactively release it.

## 2026-10-06 — Final two partition-scanned loop owners repaired

Post-reboot host evidence cleared the historical leaked Greia loop and proved
`safe_detach_loop` on a real disposable partition-scanned ext4 image:
partition child creation, mount/write/unmount, child removal and parent
disassociation all completed with no residual loop association.

The repository-wide loop-cleanup regression then correctly exposed two remaining
owners that still bypassed the shared helper:

- `tools/build-live-usb.sh` — the physically proven Syslinux/FAT32 writer
  mounted the installer image through a `--partscan` loop and used direct
  `losetup -d` in its cleanup trap.
- `tools/verify-development-target-image.sh` — the target-image verifier did
  the same for its read-only artifact mount.

Both now source `build/lib/safe-cleanup.sh`, use `safe_unmount_paths` and
`safe_detach_loop`, and fail closed while preserving work state if verified
teardown cannot complete. The USB media-writing recipe itself is unchanged;
only cleanup of the read-only source-image loop was altered.

Current evidence boundary: SOURCE EDITED / LOCAL RE-ACCEPTANCE OWED. The build
host was clean after reboot (no Greia loops, root filesystem below 80%) and the
shared synthetic helper path is proven. Do not begin the expensive build/flash
cycle until `tests/test_build_loop_cleanup_contract.py` and the focused shell
gates pass on the exact new canonical main.

## 2026-10-06 — Final pre-build gate accepted; hardware campaign authorized next

Exact tested source:
`8eec98d7b5e52375bf08790f2fd00cf8a5f006d0`.

Owner-controlled local evidence closed the final loop-cleanup source gate and
reconfirmed the full pre-build tail:

- `tests/test_build_loop_cleanup_contract.py`: 3/3 PASS;
- all seven `--partscan` owners route through shared verified teardown;
- the only direct `losetup -d` remaining is inside
  `build/lib/safe-cleanup.sh` under child-removal + parent-disassociation
  verification;
- `make shell-check`: PASS;
- `make validate`: PASS, 45/45 Activities;
- `make footprint`: PASS;
- `make clean-bytecode`: PASS;
- host reboot cleared all historical Greia loops;
- synthetic partition-scanned ext4 loop acceptance proved
  `safe_detach_loop` removes both child mappings and parent association;
- build host root filesystem remained below 80% usage;
- LaCie iamaKey was identified by serial `eca3505216d7d3` as a removable
  whole disk, still mounted and intentionally untouched.

This closes the non-destructive pre-build phase. No additional source gate is
required before the next campaign.

**Next exact step:** destructive owner-controlled campaign using the canonical
front door
`tools/build-and-flash-development-usb.sh legacy-x86-i686-dev <LaCie whole disk>`,
after re-identifying the LaCie by serial and unmounting all of its filesystems.
Require source-artifact verification, USB readback verification, and a post-run
Greia-loop audit before moving the stick to the reference Acer. Then perform a
fresh install and judge the **first installed boot** without hotpatching or a
second corrective boot.

## 2026-10-06 — Full build/flash exposed second-generation loop cleanup defects

The first destructive campaign after the pre-build PASS built and flashed a
valid `legacy-x86-i686-dev` USB but correctly stopped before Acer testing at
the post-build loop-hygiene gate.

Exact campaign source: `64103e48412b6ccafbd8c68b1585f7dc3e7ff2ef`.
Artifact evidence:
- installer image: 1,290,797,056 bytes;
- SHA-256: `f803c9edff7482b122dea49abd7d12e664d7773dc9ef3180cffb45c4387d801d`;
- source artifact verification: PASS;
- USB flash readback verification: PASS;
- Syslinux/FAT32 writer: PASS;
- live media id: `2afcbbba-9722-4020-8caf-a16132b54f51`.

Hard failure: `/dev/loop0` remained associated with the deleted target image
under `/tmp/greia-installer-build.OPrdqB/...img`, with `loop0p1` still
present. Acer boot/install was not started.

The run exposed three independent cleanup design faults:
1. `safe_detach_loop` required `partx -d` to remove partition children
   before requesting parent detach. On this kernel the child remains while the
   parent association is live, so the helper could never reach `losetup -d`.
   Linux loop teardown is lazy; the correct order is parent detach first after
   unmount, then wait for parent association **and** partition children to
   disappear.
2. several EXIT-trap handlers returned a non-zero value rather than exiting
   with it, so an otherwise successful process could still report success after
   cleanup failure. The child builder is invoked under the parent's `set -e`;
   once the child genuinely exits non-zero, that status is already sufficient
   to stop the parent.
3. `safe_unmount_path_tree` used `findmnt -R --target` even when the
   requested path was no longer a mountpoint. `findmnt --target` then resolved
   the containing root filesystem and the safety guard saw unrelated
   `/snap/...` mounts. Non-mount paths must be an immediate no-op.

Source repair now:
- requests lazy parent detach before waiting for partition children;
- pins the original backing identity and refuses loop-number reuse;
- waits for both parent disassociation and child removal;
- makes non-mount cleanup paths no-op;
- centralizes EXIT-trap termination in `safe_cleanup_exit`, preserving an
  original non-zero status but converting cleanup failure after success to rc=1;
- routes all seven partscan owners through that authoritative exit contract;
- makes the canonical build+flash front door reject both pre-existing and
  post-run Greia build loops;
- adds executable regression tests for the exact kernel shape where children
  persist until parent detach is requested and for cleanup-failure exit status.

Evidence boundary: SOURCE EDITED / LOCAL ACCEPTANCE OWED. The already written
USB remains artifact/readback verified and Acer remains untouched.

### Loop cleanup redesign implementation candidate

The completed source candidate for the second-generation cleanup redesign is
`258f2189a6e2e9de604becd8b63b4eab28771113`. Any following commits in this
documentation update are non-runtime. Local acceptance must pin this candidate
or a documentation-only descendant and must first exercise the already-leaked
field loop before authorizing another full build.

## 2026-10-06 — Field reproduction proved parent-only detach is insufficient; interleaved teardown implemented

The exact leaked `/dev/loop0` from campaign `OPrdqB` was re-tested against
the parent-first cleanup candidate. Identity and mount safety checks passed.
`safe_detach_loop` issued `losetup -d` repeatedly; AUTOCLEAR changed 0 -> 1
but the parent backing association and `loop0p1` remained for all bounded
retries. No manual recovery was attempted and Acer remained untouched.

Kernel behavior explains the deadlock: an open partition contributes an opener
to the whole disk, so `LOOP_CLR_FD` marks AUTOCLEAR and defers final teardown
while extra openers remain. Pure parent-first teardown therefore cannot finish
a persistent child, while the earlier pure partx-first design could not make
progress before detach was pending.

The cleanup contract is now explicitly interleaved:
1. unmount all owned mounts;
2. pin the original loop backing identity;
3. request parent detach (`losetup -d`);
4. settle udev;
5. if the parent remains associated and partition children remain, run bounded
   `partx -d` **after** detach is pending;
6. settle and require both parent association and children to disappear;
7. refuse loop-number reuse and emit fuser/sysfs holder diagnostics on bounded
   failure.

All seven partscan owners again declare `partx` explicitly.

Regression coverage now includes:
- deterministic detach-first / partx-second ordering;
- backing-identity pin;
- all owners declaring `partx`;
- a privileged real-host fixture
  `tools/test-loop-cleanup-deleted-backing.sh` that creates a partscan loop,
  deliberately holds the partition open, unlinks the backing pathname, then
  requires the shared helper to recover once the opener releases.

Evidence boundary: SOURCE EDITED / LOCAL ACCEPTANCE OWED. The existing verified
USB product content remains unchanged and Acer remains untested.

### Interleaved cleanup implementation candidate

Exact implementation candidate:
`3f3f50d1f586872c6b02865e027635b3ac67c1fb`.

Following commits in this update are documentation/operational guidance only.
Local acceptance must pin this candidate or a documentation-only descendant.

## 2026-10-07 — Interleaved field acceptance stopped on stale test inventory only

Owner-controlled acceptance at canonical `6b3706d41b898de2e1c2ddfa0a59b72ae4e8c8a0`
passed source identity, product-content boundary and shell syntax, then stopped
at the focused loop-cleanup suite: 10/11 tests passed.

The sole failure was not a cleanup implementation defect. The new privileged
fixture `tools/test-loop-cleanup-deleted-backing.sh` is itself a legitimate
`--partscan` owner, sources `safe-cleanup.sh`, and calls
`safe_detach_loop`, but the hard-pinned `PARTSCAN_OWNERS` tuple had not been
extended to include it. The discovery equality check therefore correctly
reported the fixture as an unexpected owner.

Repair is intentionally narrow: add the existing
`DELETED_BACKING_FIXTURE` constant to `PARTSCAN_OWNERS`. No cleanup,
builder, verifier, target/runtime, USB-content or Acer behavior changed.

Exact repair commit:
`6de59fba28a889cc86550926f0bca870eb01ed27`.

Next acceptance resumes at the focused loop-contract suite. The privileged
deleted-backing fixture, real OPrdqB field-loop teardown, artifact re-verifier
and USB readback verifier remain unexecuted and unproven.

## 2026-10-07 — Historical OPrdqB loop classified as poisoned host state; stop redesigning teardown

The third-generation interleaved helper was accepted in source and in the
privileged deleted-backing fixture, then tested once against the exact historical
OPrdqB field loop. The helper still could not release that loop:

- backing remained the deleted OPrdqB target image;
- AUTOCLEAR remained set;
- `loop0p1` persisted;
- parent and child were unmounted;
- `fuser` reported no userspace opener;
- sysfs holders were empty;
- parent-detach + post-detach `partx -d` exhausted the bounded retry window.

This is now classified as **historical poisoned kernel state**, not an open
product/build cleanup algorithm requirement. The distinction is evidenced by:

- fresh synthetic partscan teardown: PASS;
- deleted-backing + deliberately held partition fixture: PASS;
- all current partscan owners: shared verified cleanup;
- cleanup failure: authoritative process failure;
- the exact pre-existing months-old OPrdqB orphan: still not recoverable without
  host reboot.

Do not add a fourth speculative teardown primitive merely to recover this one
already-poisoned loop. A reboot is the supported host recovery for this state.

Policy from this point:

1. **Before any new build/flash campaign:** zero pre-existing Greia build loops
   is still mandatory. If the historical OPrdqB loop is present, reboot first.
2. **For a running build/verifier:** compare post-run state with the pre-run
   baseline and fail on any newly introduced Greia loop. Current source should
   not create one.
3. **For Acer acceptance of an already-built/readback-verified USB:** the
   historical host-only OPrdqB loop is not a product blocker. It is unrelated to
   USB bytes, target runtime, first boot, Wi-Fi or Acer disk state.
4. The already-written LaCie remains valid because product-content paths are
   unchanged since `64103e48`, its source artifact and USB readback both
   passed, and the cleanup-only changes do not alter target payload bytes.

Next exact step: re-identify the existing image/USB, optionally rerun read-only
artifact/readback verification using **baseline-aware loop accounting** (the
known OPrdqB loop may remain, but no additional Greia loop may appear), then
proceed to Acer USB boot, live Wi-Fi, fresh install and first-installed-boot
acceptance. No rebuild is required.

## 2026-10-07 — Physical first-installed-boot failure root-caused; product source repaired

The existing verified LaCie was finally booted on the reference Acer and a fresh
install was observed without hotpatching. The first installed boot restart-looped
before `launcher_interactive_ready`.

Read-only field evidence established the proximate failure:

- `/run/greia-os` and the fixed profile data root were correct;
- Parent created the new profile root 17 seconds **after** the B4 marker;
- that profile root and its Parent-owned children were
  `greiapanel:pipprofiles 2750`;
- child history initialization failed creating `progress` with
  `PermissionError`;
- B4 is structurally unable to repair fresh profiles because first-boot is
  ordered before Parent creation.

Source review then exposed why the intended creation-time repair disappeared:
the Parent unit had `RestrictSUIDSGID=yes`, while `ProfileStore` attempted
`chmod(2770)` and swallowed `PermissionError`.

The source repair establishes the invariant at the real owner:

1. Parent service `UMask=0007` makes directories under the existing setgid
   `pipprofiles` root land directly as `2770` while retaining
   `RestrictSUIDSGID=yes`.
2. `ProfileStore` validates exact mode + managed group and fails with
   `ProfileError` on any repair failure.
3. New profile directories are prepared/verified before registry publication;
   failed new creates do not publish a broken child-visible profile.
4. Child-owned `progress` and `storage` remain child-created.
5. B5 is a one-time bounded compatibility migration for already-created
   Parent-owned profile/customization/activity directories only.

Two independent physical defects found in the same capture were also repaired:

- `greia-boot-observer.service` is now enabled only for `*-ab-v1` layouts;
  its required layout/release authority does not exist on single-root targets.
- developer status/log collection no longer requires a display endpoint, and
  canonical developer composition now writes the role-specific
  `developer-display.json` that the installed control path expects.

The one-per-cycle `pkexec` warning remains open/non-blocking; evidence proves
it is not the loop cause.

**Important evidence/routing change:** product-content files have changed since
the USB built at `64103e48`. That USB remains valid evidence of the failure
but may no longer be used to accept the fix. Source acceptance must run on the
new candidate, then the build host must reboot to clear the known historical
OPrdqB poisoned loop before any new build. A fresh canonical
`legacy-x86-i686-dev` build+flash and another no-hotpatch first-installed-boot
Acer acceptance are required.

### Fresh first-boot repair implementation candidate

Exact implementation/test candidate:
`af97ddbd7a881d3977c83c1ee99da1b8c0e7e997`.

The candidate changes exactly nine implementation/test files relative to the
pre-diagnosis routing state `5fb75c24`:

- `build/lib/compose.sh`
- `build/overlay/etc/systemd/system/greia-parent.service`
- `build/overlay/usr/local/lib/greia-os/first-boot`
- `src/greia_platform/developer_control.py`
- `src/greia_platform/profiles.py`
- `tests/test_boot_health_product_composition.py`
- `tests/test_developer_remote.py`
- `tests/test_first_boot_migration.py`
- `tests/test_profiles.py`

Following commits in this documentation tranche are documentation-only. No
owner/local test execution is claimed yet.


### 2026-10-08 — My Greia trusted system-content composition correction (SOURCE-ONLY)

`src/greia_platform/activity_release.py` now fixes the mandatory system Activity
`org.greia.workshop-settings` outside curated educational Activity release
policy. `tools/stage_release_activities.py` copies both the approved curated
child set and this immutable system set into one atomically validated installed
root; staged identity must match both, and an ordinary release roster cannot
claim its reserved package/ID. The release `status="draft"` gate remains
unchanged and still blocks official target build. Tests added/updated in
`tests/test_stage_release_activities.py` and
`tests/test_activity_release_selection.py`; these are UNEXECUTED source
assertions. No owner Linux release command, installer media, Acer installation,
boot, rollback or physical trust acceptance occurred. The 2026-09-15 lifecycle
sequence and its independent blockers do not change.


### 2026-10-12 — Language chooser truthful registry and staged ES/FR installer copy (SOURCE WIP)

The 12-language installer first-screen selector claimed ten locales
without real Greia system/Activity translation coverage. The
owner's new scoped `docs/plans/2026-10-12_GREIA_FOUR_LANGUAGE_ROLLOUT/PLAN.md`
fixes this claim: canonical `SUPPORTED_SYSTEM_LANGUAGES` now
contains only en/it, consumed unchanged by installer, Parent
API and installed Parent Settings. Legacy records with no longer
supported locales are preserved but fall back safely to en at runtime.
The separate staging translator contains 108 ES and 108 FR
installer source messages, including disk-destructive warnings
and dynamic statuses, but ES/FR are **not** offered to installer
users until comprehensive text, voiced assets and real install
acceptance pass. Test migration and provider-free inventory source
committed; local GLA-014 task handles current SHA validation and
non-destructive GUI preview. No new physical installer run,
USB flash, first-boot, QEMU, rollback, release packaging or
C0 footprint acceptance was executed. Prior lifecycle blockers
and install/update/release scope remain unchanged; the new
four-language plan does not replace this plan.


### 2026-10-17 — Installer quiet-screen/restart source publication

Owner requested publication of existing installer work, excluding video files.
Live GRUB/Syslinux/SD kernel arguments and `LIVE_REQUIRED_ARGUMENTS` now include
`nonetworking` to suppress live-boot ifupdown preconfiguration on the networkd
live root. The installer service restarts even when xinit exits zero after a
client crash (`Restart=always`), with a five-start/300-second retry budget.
The new root-owned `installer-exit-cover` stop helper attempts a fail-soft
repaint through the existing framebuffer renderer; the composed-root verifier
requires the helper and restart policy. Existing regression tests were extended.

`make verify` passed on these installer changes over parent `672ae9101`:
5,395 fast-lane tests, 8 skipped, project/Activity validation, shell syntax
and source footprint checks (local log `/tmp/greia-installer-commit-verify.log`).
Evidence scope is SOURCE only:
no image build/flash, QEMU rerun, physical install, boot, Wi-Fi or recovery
acceptance is claimed here. This preserves the current lifecycle phase and
its open gates. Next: validate the rebuilt RC through the existing image and
physical acceptance route, including retry exhaustion and quiet-screen recovery.


### 2026-10-18 — RC installer rebuilt/flashed; quiet boot QEMU-verified; physical acceptance next

The 2026-10-17 RC physical freeze was root-caused on the actual stick: its
`boot/syslinux/syslinux.cfg` used `console=null`, fatal on the Debian 686
kernel (no ttynull; live-boot `init` dies, `panic=0` halts on the banner). The
source fix is the published `672ae910` + `ee7a40d1` pair.

`legacy-x86-i686-rc` was rebuilt at `ee7a40d1` and written to the 8 GB LaCie
(`/dev/sdc`, iamaKey `eca3505216d7d3`) through the front-door components run in
a private mount namespace (desktop-host rule in `GREIA_AGENT_OPERATIONS.md`).
Artifact verification PASS, USB read-back verification PASS; image SHA-256
`07240e27416b9801d8b981e43c383d79425697e545402e61d6964a18127b12ac`; live media
id `22857a5a-9fdb-4d9c-923d-ab659eed38ff`; payload 1,203 MiB (<1,300 gate).

The flashed media was QEMU-booted (snapshot; `-cpu n270`): the quiet Syslinux
entry reaches the Greia boot splash and then the installer language screen with
`greia-installer.service` active and no shell text. Evidence:
`docs/reviews/acer/2026-10-18_RC_INSTALLER_QEMU_BOOT_VERIFICATION/`.
Negative control: a `-cpu pentium3` run lacks SSE2, NumPy import fails, and the
restart limit + exit cover make it look like a stalled splash; not an image
defect.

Open lifecycle gates: physical Acer install/first-boot, hidden verbose recovery
path, installer crash/retry exhaustion on hardware, and the live-installer
`greia-devctl` source/docs mismatch (§13.5 of the image-creation document).
Host note: one kernel-pinned loop device remains from a non-namespaced attempt
and clears on reboot.


### 2026-10-18 — Quiet media clears the stock Syslinux banner (owner decision); rebuilt/reflashed/QEMU-verified

Owner report from the first acceptance run: the stock `SYSLINUX 6.04 … H. Peter
Anvin` banner stayed on screen through the quiet phase, including after a
shutdown that re-booted the inserted key. Owner decision: cut it on the quiet
release-candidate path.

Source `529accef`: `build/live-syslinux/clear.msg` (one form-feed byte) and
`DISPLAY /boot/syslinux/clear.msg` in the quiet template only; writer copies
the byte on quiet media; the read-only verifier requires the directive,
byte-compares the file, and refuses any `DISPLAY` on the diagnostic template.
`console=tty1` + `panic=0`, the hidden `verbose` recovery label and the
diagnostic media stay unchanged.

Rebuilt and reflashed through the front door in a private mount namespace:
artifact verification PASS, USB read-back PASS, loop hygiene PASS. Image
SHA-256 `b92cfd58f2967fa581d88a5c675f6926bbf979869318bb302570b5a416aff2f2`,
live media id `d60ca3a7-372a-4b48-92fb-55c75077daa9`, payload 1,203 MiB.
QEMU of the flashed stick (snapshot, `-cpu n270`): no Syslinux text at 0.8 s
or 1.5 s; installer language screen at 190 s with no shell. Evidence:
`docs/reviews/acer/2026-10-18_QUIET_BANNER_CLEAR_QEMU_VERIFICATION/`.

Closure still requires physical Acer re-acceptance, including the hidden
`verbose` recovery path (premortem F2).


### 2026-10-18 — Installer completion power-off: unprivileged button repaired via a root finish-marker path

Owner report: the completion button did nothing, and the physical power button
left the machine black and never shut down. QEMU reproduced the definite part:
the UI's `systemctl poweroff` as `nobody` (NoNewPrivileges, no logind session)
is denied ("Call to PowerOff failed: Access denied").

Repair: the UI writes `/run/greia-installer/finish-request` in its own
RuntimeDirectory; a new root `greia-installer-finish.path` unit watches that
exact file and runs the one-shot `greia-installer-finish.service`, whose helper
raises shutdown visibility (`SetShowStatus yes`, kernel console loglevel 8) and
then performs the single `systemctl poweroff`. The composer enables the path
unit and the composed root verifier requires the pair, the helper and the
enable symlink. The completion page now shows a manual fallback if the marker
write fails. No new package, daemon or polkit grant.

The visibility raise runs only after the completion button was deliberately
pressed, so the quiet child-facing boot is unchanged; on a failed or hung
shutdown the parent sees the last stop job or kernel message instead of a mute
black screen.

Rebuilt and reflashed at `1284f6a1` (image
`369bb29b472708c3115f5125940baa83110765e63f6915a07d60e94a92ede5cd`, live media
`7de4bafd-a7fc-4706-9833-96690929eaf8`, payload 1,203 MiB; artifact, USB
read-back and loop hygiene PASS). QEMU verified the new path: the finish path
unit was active and an unprivileged `nobody` marker creation triggered the
root service and a clean ACPI power-off.

Physical retest: the on-screen completion button now powers the Acer off.
The first successful shutdown showed the diagnostic transcript and then
systemd-shutdown teardown warnings over the Greia cover. The finish helper no
longer raises visibility; because PID1 forwards its log level to
systemd-shutdown, the helper lowers the manager `LogLevel` to `emerg` just
before `systemctl poweroff`, so the branded cover is the last visible frame
(QEMU frame capture confirms a clean splash with no terminal text).
`installer-exit-cover` supplies that frame; the composed-root verifier
enforces the silence and rejects status/printk raising. Rebuilt and reflashed
at `6f3c809c` (image
`47ab4ec639175f8b21aa69aec0f3aa1d172eab7d8a4ce24fdc775f92031fb6a0`, live media
`a1d8e713-5090-4570-be68-83db7cfda8c6`, payload 1,203 MiB; artifact, USB
read-back and loop hygiene PASS). QEMU capture of the marker-triggered
shutdown ends on the clean Greia splash with no terminal text. Physical F18
closure remains after the Acer retest.


### 2026-10-19 — Raspberry Pi 400/500 source foundation recovered after committed-file review

Owner requested Pi implementation and further review. Review found the earlier PR #10 committed the **deferred 64 MiB Pi layout**, despite a prior staged executable blob. This is a provenance/engineering continuity error, not a claim that hardware evidence is missing. Refined source now includes executable Pi 256 MiB FAT/P4 extended/P5-P7 ext4 commands with EBR capacity overhead and positive built-in microSD eligibility, shared observed-MBR identities, strict board-specific ARM64 profile definitions, offline native Pi boot asset staging and ARM64 Image-header checks, sysfs built-in MMC/CID evidence, and negative source tests. The full installed-Pi transaction **continues to refuse before erase** because live ARM boot, real kernel/module/firmware pairing, P1 recovery and production tryboot are unfinished. The default builder intentionally rejects ARM64 until bootable composition is implemented. **Evidence SOURCE ONLY / UNPROVEN; tests not run this turn.** Follow `docs/reviews/2026-10-19_RASPBERRY_PI_INSTALLER_SOURCE_REVIEW.md` for the exact code defects, acceptance matrix and next action. The universal Setup image and Pi 400/500 support are NOT COMPLETE.


### 2026-10-19 — Pi source verification pass 2: slotted-dataclass target-policy TypeError, DTB placeholders

Checked actual `main` `e37aa437` source (not uncommitted blobs). Confirmed `PiBuiltInMicroSdTargetPolicy._removable_rejection` erroneously used zero-argument `super()` in a frozen/slotted dataclass; independent local Python reproduction raised `TypeError` on a negative/rejection path. Fixed with direct shared base-method delegation. The built-in MMC evidence and `lsblk` integration now have a regression test exercising real probe→sysfs→policy filtering with both Pi microSD and USB present. Native Pi offline boot staging previously accepted 3-byte placeholder DTB/DTBO files; it now checks FDT magic and declared length, with negative tests. Official Raspberry Pi tryboot/kernel-file specification agrees with intended selected partition/kernels, but runtime remains unconnected. **Evidence: source inspection + isolated Python reproduction only. No project tests, loop/device execution or boot performed. Pi release and universal installer remain OPEN.** See `docs/reviews/2026-10-19_RASPBERRY_PI_INSTALLER_SOURCE_REVIEW.md`, follow-up verification pass 2, for exact remaining work and test commands.


### 2026-10-19 — Research-led Pi installation/A-B third verification (SOURCE + ISOLATED TEST ONLY)

Researched Raspberry Pi's official autoboot/tryboot/EEPROM/kernel contracts, Pi rpi-image-gen A/B boot-device-backed slot mapping and persistent-state repair practices, public firmware issue #818 (CM5 tryboot on GPT; FAT grouping and bootloader-version differences), and corrupted-autoboot partition-walking reports. The plan's MBR P1/P2/P3 contiguous FAT layout remains a plausible candidate but is NOT hardware-proved. Added positive 32-hex MMC CID check and tests, and new **read-only** firmware evidence decoding of big-endian /proc/device-tree/chosen/bootloader partition + tryboot flags; verifies boot partition P2/P3 versus root hint P5/P6 and shared observed MBR signature. It is explicitly **not** sufficient to accept/promote a boot: actual mounted-root/boot-disk ancestry, finalized receipt and Shell health are still missing.

Eight tests passed in isolated Python 3.13 run with stand-in Greia helpers; full repository tests, make verify, actual loop partitioning, Pi firmware and physical hardware were not run. P1 recovery/partition walk is firmware-version-sensitive, and USB/SD boot ordering and PERSIST continuity need explicit physical/fault testing. Do not permit install-card erasure or describe the ARM/universal installer as complete. Authoritative detailed findings: docs/reviews/2026-10-19_RASPBERRY_PI_RESEARCH_LED_VERIFICATION.md. Next: local full-source testing; read-only Pi EEPROM evidence; loopback geometry; native installed Pi A/B & recovery; ARM live boot + universal media and Pi400/Pi500 physical acceptance.


### 2026-10-19 — Authoring-reference exclusion from runtime asset composition (SOURCE)

The owner-directed voice-master migration exposed that the existing broad `audio/***` runtime copy also included canonical authoring references. `compose_install_runtime_assets` now hides `audio/characters/canonical/` on the sender while allowing `--delete` to remove stale copies from reused staging roots. The existing real-rsync contract verifies all canonical versions remain absent and shared playable audio remains installed. Four focused packaging tests PASS. No image was rebuilt; no installer/update/physical acceptance or lifecycle phase closure is claimed. The voice provider/master migration itself is tracked in the non-lifecycle remediation ledger and `docs/reviews/2026-10-19_VOXSTAGE_VOICE_MIGRATION.md`.


### 2026-10-19 — RC installer rebuilt from current `main` and flashed to the LaCie (BUILD + USB READ-BACK PASS)

Owner asked to pull all commits, build the installer image and flash the only connected 8 GB LaCie USB key (whole-device disposal authorized).

- **Source:** `main` fast-forwarded `6965adb9` → `b750e714` (voice v0.2/VoxStage migration, Pi installer source foundation and reviews); clean working tree at build start.
- **Target media identification:** `/dev/sdc`, `iamaKey`, serial `eca3505216d7d3`, vendor LaCie, `TRAN=usb RM=1 TYPE=disk`, 7.5 GiB, previously mounted at `/media/orb/GREIA`; unmounted before the front door.
- **Command:** `tools/build-and-flash-development-usb.sh legacy-x86-i686-rc /dev/sdc ./out --operator-key /home/orb/greia-rc/greia-operator.pub` inside `setsid nohup sudo -n unshare --mount --propagation private`, log `out/rc-build7-b750e714.log`.
- **Result:** `operator_ssh_key=SHA256:0oRmaFqZpIYFsGj0N2++I6oma2kHtqdOQMQjXITYVXU`; payload accounted **1,201 MiB** (< 1,300 owner gate); image SHA-256 `d177baec8ba0cf8229fee05512e1a1e4ec31994a3152b88fca229dfee199f514`; live media id `a7f03fe3-2240-48e6-9c53-811c35765b26`; `boot_console_policy=quiet`.
- **Gates:** `Developer installer artifact verification: PASS`, `Greia live USB read-only verification: PASS`, `usb_readback_verification=PASS`, `loop_hygiene_verification=PASS`; an independent re-run of `tools/verify-live-usb.sh` after the build also PASSed; no Greia loop devices remain.
- **Evidence scope:** source/build/media read-back only. No QEMU boot and no physical Acer install/first-boot was performed in this turn; physical Acer acceptance (premortem §5 F1–F19, F2 hidden `verbose` path) remains the next exact step.
- **Exact next step:** install from this LaCie on the reference Acer through the graphical installer, then run the premortem first-boot checklist and record the results here and in `HANDOVER.md`.


### 2026-10-21 — Installed Aspire 1280x800: Activity viewport + target Wi-Fi firmware (DEVICE + SOURCE)

Owner reported that Activities on a newly installed Acer Aspire laptop (1280x800, not the 1024x600 reference netbook) did not fill either axis, left stale Shell pixels/pointer around the Activity, and that the installed OS found no Wi-Fi networks although the live installer did.

- **Display root cause:** built-in Activities still call `pygame.display.set_mode((1024, 600), RESIZABLE)`. On a 1280x800 X screen that maps a 1024x600 window over the larger Shell window; the uncovered Shell pixels keep the old background and its hidden pointer. The reference-canvas mapping was correct but never received the real surface.
- **Display fix (`0a0b4659`):** `greia_platform.activity_display` installs a platform-owned display-request policy in `python_activity_entry` for Greia sessions. The requested size is replaced with the exact Shell viewport (`GREIA_ACTIVITY_VIEWPORT`, recorded by the launcher on mode change/resize); flags are preserved. The launch cover still handles the first-window card. The Simulator keeps its synthetic-viewport adapter. Authoring design/skill docs now state that `screen.get_size()` is the real viewport and that authors must not open a smaller window.
- **Device evidence:** deployed the pre-rebase equivalent (`a2ac1386`; final `0a0b4659`) to the installed RC (`greia-devctl source-deploy`), restarted the Shell, opened `alfabeto_leo` at 1280x800. `xdotool getwindowgeometry` shows the Activity surface at `1280x800+0+0`; the screenshot shows the Activity filling the panel with Home still on top and no stale Shell band.
- **Wi-Fi root cause:** the installed target had no `firmware-iwlwifi`; `iwl3945` failed to load `iwlwifi-3945-2.ucode` and `iwd` could not bring the station up. The live installer has the broad firmware cover, so its scan worked. The target hardware-support plan recorded only `intel-microcode` even though the bound driver declares the firmware.
- **Wi-Fi device recovery:** on the installed system, `apt-get install firmware-iwlwifi` (after correcting the clock for TLS), `modprobe iwl3945`, restart `iwd`: station associated with the saved profile and `systemd-networkd` acquired `192.168.68.112`; `networkctl` reports `routable (configured)`, online.
- **Installer source fix (`813b43d0`):** after the payload copy and before target configuration, the engine takes a second complete hardware inventory and merges late-bound verified packages from the same frozen support pool into the pre-erase plan. An incomplete refresh leaves the initial plan unchanged. `install-record.json` records the final merged package list. Focused planner/merge tests pass; `make verify` ran 5,480 tests with the inherited ARM64-profile error, the known `morbidi_mostriciattoli` startup-budget flake and the stale MBR-message expectation, plus the `build_profile` executable-mode error that `a8a64fdd` now fixes. Full aggregate gate remains red for the inherited cases, not for these changes.
- **Evidence scope:** source + focused tests + physical/device runtime on the installed Aspire. No QEMU boot and no fresh install from a rebuilt image yet.
- **Detailed implementation/evidence:** `docs/reviews/acer/2026-10-21_ASPIRE_1280X800_VIEWPORT_AND_TARGET_WIFI.md` (call flow, contracts, tests, device evidence, limits, image data).
- **Exact next step:** rebuild/flash the RC with these commits, then reinstall (or deploy-source) and confirm the display and Wi-Fi on a clean install; keep the Acer premortem/first-boot checklist as the physical acceptance boundary.

### 2026-10-21 — RC rebuilt/flashed with the Aspire fixes (BUILD + USB READ-BACK PASS)

Rebuilt `legacy-x86-i686-rc` from `fa15c88f` (viewport normalization, post-copy hardware-support re-plan, executable `build_profile`, plus the promoted v0.3 voice masters) and flashed the authorized 8 GB LaCie `/dev/sdc` (`iamaKey`, serial `eca3505216d7d3`) through `tools/build-and-flash-development-usb.sh` inside `sudo -n unshare --mount --propagation private`, log `out/rc-build8-fa15c88f.log`.

- Image SHA-256 `ff339ad76b65acd4c0f998c81da61577127400c4aee13a59963e68d2bcd4838e`; live media id `7b50ef65-a0a8-4427-afb3-667ef37a52d1`; payload accounted **1,257 MiB** (< 1,300 owner gate); target payload 518,950,912 bytes; `boot_console_policy=quiet`.
- `Developer installer artifact verification: PASS`, `Greia live USB read-only verification: PASS`, `usb_readback_verification=PASS`, `loop_hygiene_verification=PASS`; an independent verifier re-run PASSed; no Greia loop devices remain.
- **Evidence scope:** build/artifact/media read-back. The installed Aspire was fixed in place with the earlier source deploy and the manual firmware package; a **clean install from this new stick** and the Acer premortem §5 F1–F19 physical checklist remain the next acceptance step.

### 2026-10-21 — Firmware selection unblocked inside the install/update sandboxes (SOURCE + REAL SYSTEMD SANDBOX)

Correction to the Aspire Wi-Fi entry above: the installed target lacked `firmware-iwlwifi` because `ProtectKernelModules=yes` hid `/usr/lib/modules` from `greia-install-transaction.service` (and `greia-system-update.service`). `modinfo`/isenkram reported every driver as unknown (exit 1), which the bound-driver resolver accepted as "built-in", so no driver firmware was ever selected on any machine. `813b43d0`'s post-copy refresh runs in the same sandbox and does not change that outcome.

- Units: `ProtectKernelModules=yes` removed; `SystemCallFilter=~@module` added; `CAP_SYS_MODULE` stays outside both bounding sets (`tests/test_firmware_resolution_unit_contract.py`).
- Resolution: `LinuxKernelModules` gates both resolvers and the update selection (unreadable module tree → incomplete → single-root pre-erase refusal / A/B seam refusal / update selection None); `modinfo` uses the sysfs module name; loaded-module, missing-`modinfo`, timeout and other failing exits are incomplete, not diagnostics.
- Evidence: focused suites PASS; build host `systemd-run` with the unit capability set: old → refusal "kernel module metadata is unreadable", new → complete, `firmware-misc-nonfree` selected for `tg3`, `modprobe dummy` denied. Not a clean install; the current LaCie image predates the fix.
- Next: rebuild/flash the RC and clean-install the Aspire; accept only when `install-record.json` lists `firmware-iwlwifi` and `iwd` connects with no manual package.

### 2026-10-21 — Aspire Wi-Fi suspend/resume recovery (DEVICE + SOURCE)

The installed Aspire lost Wi-Fi after a lid-close/resume: `iwl3945` failed
`wiphy_resume` with `-110` (`Unable to change power state from D3hot to D0`),
`wlan0` went down and `iwctl` reported no station. A manual
`modprobe -r iwl3945; modprobe iwl3945; systemctl restart iwd` recovered the
interface and DHCP without reboot. Added the target `systemd-sleep` post hook
`build/overlay/usr/lib/systemd/system-sleep/greia-wifi-resume` (post only,
only when `iwl3945` is loaded, bounded modprobe calls, `try-restart iwd`),
with an overlay contract test. Manually invoked on the device: back to
`routable (configured)` on `192.168.68.112`, HTTPS 200.

**Evidence scope:** remote device + focused test. The hook is not yet in a
rebuilt image; it was installed in place. **Caution:** an unattended
`rtcwake -m mem -s 20` did not wake from the RTC alarm, so the device remained
suspended and needs the power button; do not use that as an unattended test.
Next: wake the device, close/open the lid, confirm automatic reconnect, then
rebuild/flash with the hook.


### 2026-10-21 — Acer Parent panel Wi-Fi connect responsiveness (DEVICE + SOURCE)

The HTML Parent app froze while connecting Wi-Fi because the installed Parent API was single-threaded: each connect ran a scan and an association attempt before any other request could be served. `ProductionParentApiHTTPServer` is now a bounded `ThreadingHTTPServer` (four slots, daemon threads), `connect_wifi` reuses a 15 s scan cache, and a new `IwdWifiBackend.connected_ssid()` fast path returns immediately for the already-connected network. Focused tests pass.

Deployed `ea0ab12f4` to the Acer and verified: already-connected connect 0.07 s; `/api/v1/devices` responded in 0.0036 s while a failing connect took 7.07 s; Wi-Fi stayed on `Wireless Pendente` at 192.168.68.112 with HTTPS 200. The diagnostic device credential was revoked. The current LaCie image (`96abaccf…`, built from `37d06316e`) predates this fix; rebuild before a reinstall.


### 2026-10-21 — Parents app connected-Wi-Fi feedback (DEVICE + SOURCE)

The Acer's Parents app listed networks but did not say which one was connected. Added `connected_ssid` to `/api/v1/network/wifi` and a green `Connected to <SSID>` / `Not connected to Wi-Fi` status plus a `Connected` row badge to the vendored Parent app; updated the integrity manifest. The pin revision is unchanged (Greia-side visual patch; upstream sync pending). The Acer's installed app files and backend were patched directly because the source-deploy stage is blocked by a concurrent oversized Activity (53.95 MB > 50 MB) from the 2x-art commit. Verified: payload `connected_ssid="Wireless Pendente"`, served JS contains the status, `greia-parent` integrity OK, Wi-Fi `192.168.68.112`, HTTPS 200. The LaCie image predates this patch.


### 2026-10-21 — Incomplete hardware detection never stops the install (SOURCE)

Owner decision: an incomplete hardware/firmware detection must not refuse an installation. `InstallerHardwareEnablementPlan` now carries `fallback_firmware`: when the plan is incomplete, the pool-provided subset of `FALLBACK_NETWORK_FIRMWARE` (`firmware-iwlwifi`, `-realtek`, `-atheros`, `-brcm80211`, `-libertas`, `-misc-nonfree`) is unioned with whatever the resolvers did produce and with microcode. `engine._prepare_hardware_support` and the A/B `device_seams` seam proceed (stderr journal line) instead of refusing; the A/B `selected_installed_bytes` bound covers the fallback. `install-record.json` records `hardware_detection: "incomplete"`, `hardware_fallback_packages` and up to three diagnostics; the completion page shows a localized (it/en/es/fr) note via a display-only flag on the `INSTALLED` answer. Pool verification failures (corrupt/unverified pool, identity mismatch) still refuse before any disk change. The hardware-inventory attestation gate (`inventory_complete`, sysfs token) is unchanged. UNPROVEN on hardware; unit tests only.

### 2026-10-21 — Legacy Mac / netbook hardware support, source tranche (SOURCE, UNPROVEN)

Implements the source-level recommendations of the two 2026-10-21 hardware reviews. Pool: `FORCED_FIRMWARE_PACKAGES` in `tools/build_hardware_support_pool_manifest.py` forces the network, Ralink/nouveau and AMD-graphics firmware packages into the candidate manifest (still filtered by APT availability and the pool finalizer; no b43 downloader, no broadcom-sta, no SOF). Installer: `hardware_id_rules.DEFAULT_DEVICE_ID_RULES` adds packages from PCI/USB IDs only if the verified pool provides them and flags Broadcom b43-family and wl-only Wi-Fi chips (`InstallerHardwareEnablementPlan.unsupported_wifi`, `wifi_firmware_unavailable`); the flag reaches the completion page through the A/B seam as a display-only note (it/en/es/fr) and the first diagnostic of the install record. Target overlay: `greia-legacy-hardware.conf` (`hid_apple fnmode=1`, `blacklist b43`; applesmc/bcm5974/applespi are in-tree and alias-loaded) and an extended `greia-wifi-resume` driver list. Tests: `tests/test_hardware_id_rules.py` plus the updated overlay contract. Size impact: the broad isenkram-derived pool already contains these packages whenever Contents lists them, so the forced list adds only packages isenkram missed; `firmware-amd-graphics` and `firmware-iwlwifi` are the large ones (tens of MiB each, FROM-KNOWLEDGE, not measured) and stay installer-pool-only unless a rule or detection selects them. Remaining: EFI boot (Macs), wl modules, LAB validation on real hardware.


### 2026-10-21 — Intel Mac / UEFI boot for the i686 image (SOURCE, UNPROVEN / LAB)

Owner goal: one i686 image that also boots and installs on Intel Macs 2006-2017. Added `src/greia_installer/efi_boot.py` (firmware probe, `bios-single-ext4` and `uefi-or-bios-gpt-ext4` single-root layouts, GRUB EFI/efibootmgr command plan), wired into `InstallationEngine` (BIOS commands unchanged), the `boot-grub-efi` package set in the three `legacy-x86-i686*` profiles, and an MBR+ESP installer USB with `BOOTIA32.EFI`/`BOOTX64.EFI` in `build/build-installer-image.sh`. Evidence: `tests/test_installer_efi_boot.py` (22 tests, fake sysfs/runner) plus existing installer/layout/profile suites; no image build, no hardware. Not done / LAB: x64 EFI GRUB booting the i686 kernel, Apple acceptance of MBR-table ESP media, GOP framebuffer boot cover, package size measurement, `grub_ab.py` EFI branch (A/B profiles untouched).


### 2026-10-22 — RC rebuilt/flashed under the new 1,500 MiB ceiling (BUILD + MEDIA READ-BACK)

Owner decision: the single-root installed-core ceiling is now 1,500 MiB (was 1,300), official for future builds. The four-language `@2x` art (~34 MiB) and the EFI boot payload (`grub-efi-ia32-bin`, `grub-efi-amd64-bin`, `efibootmgr`; ~34 MiB) had pushed the RC to 1,323 MiB. 1,500 keeps one image with the shipped art and both boot paths while staying comfortably inside the reference Acer's 7 GB storage target; the ≤800 MiB preferred core and the 1 GiB A/B slot limit are unchanged, and >1,500 MiB still requires architecture review. Landed in `398a6ca4a` across all single-root profiles, `AGENTS.md` contract 6, the RC runbook, profiles README, gate comment and tests.

Two build regressions found and fixed while producing the media: the build host needed `grub-efi-ia32-bin` (the script now checks both EFI module dirs before any disk mutation; runbook §13.2 lists the packages, `696122e6f`), and the SD finalizer/live-USB writer/both verifiers still assumed the ext4 root was p1 although the new MBR image is p1 = FAT32 ESP, p2 = ext4 root. `build/lib/installer-image-root.sh` now resolves the first ext4 partition for all four consumers, with a source contract test (`c6744c78a`).

Built and flashed `legacy-x86-i686-rc` at `c6744c78a` through `tools/build-and-flash-development-usb.sh` inside `sudo -n unshare --mount --propagation private`, log `out/rc-build13-c6744c78.log`, to the authorized 8 GB LaCie `/dev/sdc` (`iamaKey`, serial `eca3505216d7d3`). Image SHA-256 `09c1c9ad4a8abe861fc96027f9165beb99bba47858e535b8f2efde15784a4acf`; live media id `ab395c7f-e2dd-45cd-8d0d-ed4be6e39b2a`; payload accounted **1,323 MiB** (<1,500); target payload 555,003,904 bytes / SHA-256 `babfe052e2cf9e3e8df3aef1c7b8ee96b71f8f94abb0518c1af338869aae2aba`; `boot_console_policy=quiet`.

Gates: artifact verification PASS, live USB read-only verification PASS, `usb_readback_verification=PASS`, `source_artifact_verification=PASS`, `usb_flash_readback_verification=PASS`, `loop_hygiene_verification=PASS`, no Greia loops. Evidence scope: build/artifact/media read-back only; no QEMU boot, no physical install. The EFI path remains UNPROVEN. Next exact step: clean-install the reference Aspire from this LaCie and run the premortem §5 F1–F19 checklist.


## 2026-10-23 — Session 04 persistent-state and Parent delivery source integration

Owner direction: complete the reliable update path using GPT-6 Luna workers;
no Lunacy workflow. Image builds, privileged Linux tests, installs and physical
acceptance are deferred to another agent/machine through the committed work
order `docs/testing/2026-10-23_SYSTEM_UPDATE_LINUX_ACCEPTANCE.md`. Keep the
scope on ordinary reliability and rollback; no signing/anti-tampering or new
security programme.

Implemented source extends the existing v3/inactive-slot engine:

- Fresh A/B installation writes the schema, layout record and first-install
  journal to actual PERSIST, and GRUB config/environment to actual verified
  boot-control storage. Both slots receive UUID-bound fstab composition and
  namespace-map-derived durable binds. Single-root rendering stays unchanged.
- The root-owned layout authority is a **directory bind** at
  `/etc/greia-os/layout`; atomic record replacement remains visible across
  slots. The shared journal is `/run/greia-persist/greia/boot-journal`, with
  schema at `/run/greia-persist/greia/persist-schema.json`. Credential issuance,
  health commit and deadline recovery read the same installed journal.
- Parent owns one durable background check/download/verify/prepare job through
  the existing inbox and typed root socket. GET status stays cached while root
  stages. The static catalog requires exact profile/family/architecture/board
  compatibility and genuinely newer comparable versions.
- Restart is explicit. Root rechecks mounted/staged state and holds the same
  profile-session lock as activation through an explicit picker-idle proof,
  one-shot arm and bounded systemd handoff. Lost responses reconcile and do
  not automatically repeat reboot.
- HTML controls are published at `e0116787bb324ca4685ad832cbc8d4d9e5b3461d`
  and vendored via the canonical pin tool. Mobile uses that shared core;
  local Mobile commit `06441e56e5e38d6e4a70f6e435d9d4ea7f339273` has no
  configured remote. Update UI covers EN/IT/ES/FR.
- The existing index builder gains four-language notes, bounded per-target
  history and atomic local publication. Owner build/inspect/index plus shared
  site-ftp remains the pipeline; no hosted Actions execution was requested/run.

Evidence and residual verification are recorded in HANDOVER and
`docs/reviews/2026-10-23_SYSTEM_UPDATE_IMPLEMENTATION_EVIDENCE.md`. Local
source checks do not close Session 04. The real exact-unit finalization,
A→B→A, interrupted update, bad userspace/kernel recovery and child-data
survival remain **UNPROVEN** until the external work order runs.

Current transfer remains the full compressed v3 bundle, including for Python
changes. No small-patch route is implemented or accepted. Manual file upload
still receives only; staging currently requires online catalog selection.
These are explicit limits, not release-complete offline/delta claims.

## 2026-10-24 — Source evidence reconciliation and BIOS install proof still owed

Append-only correction to the Oct 23 integration entry: the available
integrated source run is 743 tests, OK with 2 skips; separate focus runs report
33 issuer, 32 recovery, and 76 product/GRUB tests PASS. These results all
predate the lifecycle worker's pending BIOS installer fix. Keep them labeled
pre-fix until that worker reports its final focused run. Exact paths and
negative evidence are in
`docs/reviews/2026-10-23_SYSTEM_UPDATE_IMPLEMENTATION_EVIDENCE.md`.

The checkout sampled for that report has base `2fd29dffa75edc3ce5edd16431a86e6722a68830`
with an uncommitted source worktree; the base is not a source freeze. The
work-order file is currently untracked despite the Oct 23 wording that called
it committed. No source SHA has been invented. Commit the implementation and
work-order before the external Linux runner starts, then record the exact
source SHA in the execution receipt.

`make verify` remains NOT GREEN: the first available full run reported 5,876
tests, 17 failures, 28 errors and 8 skips; subsequent integrated/final runs
aborted with signal 6 at the typography cleanup / Activity tempo test. The
ARM64 builder refusal and MBR message expectation were reproduced on the clean
baseline. No Linux build, QEMU guest, installation, Parent browser/device, or
physical hardware acceptance ran in this evidence set.

Add an explicit external acceptance gate after the BIOS fix: install onto a
blank disposable disk with the guest in BIOS mode, then boot the installed
system through BIOS GRUB into Greia and retain both boot evidence and the
installed MBR/GRUB state. Installer return status, generated GRUB files and
source tests are insufficient. Continue to hold Session 04 OPEN until this
gate and the real updater, A→B→A, rollback, interruption, PERSIST and
child-data predicates in the work order pass.

## 2026-10-24 — BIOS installer source reruns passed; Linux boot remains open

Append-only correction to the evidence snapshot above: the BIOS installer
adapter fix is now included in the dirty source worktree. Its eight focused
suites passed 116 tests. The settled 38-module source gate passed **770 tests,
2 skipped** at `/tmp/greia-update-completion/focused-final-frozen.log`; an
independent fresh-process rerun passed the same count at
`/tmp/greia-update-completion/focused-final-bios-rerun.log`. The earlier
combined attempt with one seam assertion failure remains recorded; it did not
recur after the test inspected the production `shell=False` runner and adapter
argv delegation. Exact details are in the dated implementation evidence
review.

These are source/fake-runner results. They do not establish that a built
installer can install to a blank BIOS VM disk or that the installed MBR/GRUB
chain boots Greia. The frozen-source full `make verify` run had not produced a
final summary at this snapshot; it remains unresolved, not PASS. Source is
uncommitted and the work order untracked, so the base SHA is not a source
freeze. Keep Session 04 OPEN and require the BIOS blank-disk install/boot
predicate before A/B update acceptance.

## 2026-10-24 — Frozen full gate completed; failure disposition remains open

Append-only correction: the frozen-worktree `make verify` run completed at
`/tmp/greia-update-completion/make-verify-frozen-bios.log`: **5,890 tests in
302.538 seconds, FAILED with 7 failures, 3 errors, 8 skipped**. The full gate is
NOT GREEN. Nine outcomes match separately reproduced clean-baseline issues:
three Foresta Parole assertions, two Parent Wi-Fi assertions, one MBR message
expectation, one ARM64 profile-resolution error, and two installer-state
errors from unavailable macOS `lsblk` behavior.

One additional failure is the aggregate run of
`test_launcher_long_session_memory.ShellLaunchCycleMemoryTests.test_repeated_launches_do_not_grow_shell_memory`
(675,948 retained-surface bytes after 24 launches versus a 524,288-byte bound).
The two-test module passes separately on baseline and current worktrees at
`/tmp/greia-update-completion/memory-baseline.log` (8.333 s) and
`/tmp/greia-update-completion/memory-current.log` (7.296 s). The full-suite
failure is unresolved/order-dependent and is not proven to be baseline. Keep
it open. The focused 38-module run remains PASS (770 tests, 2 skipped), but
does not waive the full gate or any Linux boot/update acceptance predicate.


## 2026-10-24 — Update source freeze and exact-commit focused evidence

Source committed as `4eaad25471fe47b72e900ea2f34777f41be5542b`. The post-commit affected-suite run
executed 770 tests in 15.941s, OK (2 skipped), with the SHA recorded in
`/tmp/greia-update-completion/focused-4eaad2547.log`. The full-gate failures
recorded above remain; this focused result does not supersede them. The source
freeze includes the reviewed BIOS boot installation adapter. Real image,
Linux exact-unit, fresh boot/update/recovery and device proof are still owed
through the committed external-machine work order. Session 04 remains OPEN.


## 2026-10-24 — Owner correction: lightweight Python/Activity updates are primary

The owner explicitly corrected the full-image focus and authorized completion
of `.greia_update` ZIP packages with a main type manifest: Python platform,
one/set/all Activities, combined Python plus Activities, and full-system.
ADR 0038 records this accepted scope. Application updates must work on
single-root installs with the new bootstrap; only Linux replacement retains
the A/B requirement. Upload carries installation authorization, and the OS
must continue after durable acknowledgement without the phone/app/catalog.
No implementation or runtime acceptance is claimed by this direction entry;
append actual source/tests and the operator/Linux handoff when implemented.

## 2026-10-24 — Typed application package guide and external acceptance handoff

ADR 0038's owner-authorized package format and build/inspection slice is now
documented in `docs/development/GREIA_SOFTWARE_UPDATE_PACKAGES.md`; the exact
installed acceptance procedures for all package types, durable Parent upload,
single-root activation, recovery, idle fencing and full-system A/B restart are
in `docs/testing/2026-10-24_SOFTWARE_UPDATE_ACCEPTANCE.md`. “All current”
built-in packages use the validated current registry or an exact installed
Activity index, not a draft future roster. The guide records the actual
commands, type/trust boundaries, limits and stable bootstrap path/helper; no
manual bootstrap installation command is supported.

The local source/build evidence directory is
`/tmp/greia-software-update-review-20261024/`. Inspection succeeded for a
268-file, 1,309,073-byte `python_platform` package (SHA-256
`da62fcb61ff63716c7ad7fd725308e57e7dcf62e17e85dcd733c45cc20eb5c90`) and a
45-Activity, 214,690,711-byte `activities` package (SHA-256
`0fe18e3899dd8f33e0ff11ba39bebcaea260ffe72eb93e4340821127bc1c20cf`). Their
JSON inspect reports and hashes are listed in HANDOVER. Package format/builder
review reported 18 focused tests PASS. The artifacts were generated before a
committed source freeze, so treat them as local source/build evidence only.

The Parent durable-receipt and installed apply/recovery integration is not
yet source-frozen. The previously recorded 5,890-test full gate remains
NOT GREEN (7 failures, 3 errors, 8 skips); the aggregate-only Shell memory
failure remains unresolved/order-dependent. No Linux image build, VM/guest,
installed acceptance or physical-device evidence has been produced. Keep
Session 04 OPEN. Next: finish/review/commit the integrated source; run exact
focused and repository gates; then execute both dated Linux acceptance orders
from a clean committed checkout on the authorized external Linux host.


### 2026-10-24 — Lightweight package implementation committed; final local evidence

Implementation source is committed at `771d52c7a9f75fb10481919d9ebef83b1d18adc9`. The exact-commit focused
rerun passed **177/177** tests (`/tmp/greia-software-final/focused-771d52c7a.log`).
The final integrated `make verify` run executed **5,942 tests**, with **6 failures,
3 errors and 8 skips** (`/tmp/greia-software-final/make-verify-final.log`); it is
NOT GREEN. The eight newly exposed integration failures were repaired and their
142-test focused run passed. Remaining outcomes match the previously reproduced
baseline: three Foresta audio-review expectations, two Parent Wi-Fi source
assertions, MBR observation wording, unsupported ARM64 target composition, and two
macOS `lsblk` installer cases. The earlier aggregate Shell memory failure did not
recur in this run. No unrelated baseline tests were waived or changed.

`make validate` separately stops at the same unsupported ARM64 profile
(`/tmp/greia-software-final/remaining-gates.log`). Final `make shell-check footprint`
passed (`/tmp/greia-software-final/shell-footprint-final.log`), as did staged diff
hygiene. HTML is published/pinned at `a1da70e6c69b907b128147ac876cc3cf17053d47`.
Mobile is committed locally at `79a61435393a34ab6d792d8c08776e92d0b0f04d`;
its checkout has no configured remote. Mobile typecheck and 34 app tests pass;
its shared core retains six baseline failures (96/102 pass).

Source work and operator documentation are persisted; **Session 04 remains OPEN**.
No image build, Linux installation, QEMU boot, physical-device apply/rollback or
rendered browser/mobile acceptance ran here. The next exact action is to execute
`docs/testing/2026-10-24_SOFTWARE_UPDATE_ACCEPTANCE.md` on the other Linux machine,
alongside the full-system work order where applicable. Use the committed operator
guide `docs/development/GREIA_SOFTWARE_UPDATE_PACKAGES.md` for all package recipes.

## 2026-10-24 — Linux installed software-update acceptance: partial pass

Append-only result entry. Full evidence and per-predicate disposition are in
`docs/reviews/2026-10-24_SOFTWARE_UPDATE_LINUX_ACCEPTANCE_RESULT.md`; evidence
root is
`/var/tmp/greia-software-update-e8fed0ec494763834114e49863cc64aa66e70f2e-20261024T155314Z/`.
The run found and fixed two source defects on `main`:

- `e8fed0ec4` corrected the RC verifier's target extraction so the
  `opt/greia-os` generation symlink and index alias are inspected rather than
  lost; the corrected verifier passed the already-built RC image.
- `0bf1e15e6` keeps the initial Parent Activity generation traversable
  (`0555`, with repair of older non-traversable generations); a root-side
  update had created `root:root 0700`, blocking `greiakid` and causing a
  post-switch launcher loop.

Focused package/update coverage passed 125/125 at `e8fed0ec4`. The full gate
executed 5,943 tests with 8 failures, 3 errors and 2 skips and remains NOT
GREEN for the documented baseline/environment outcomes; it was not waived.
On a disposable repaired clone, real GUI installation, guest bootstrap facts,
Parent HTTPS pairing/durable 202, two sequential Python applies, the
child-active idle fence, built-in one/set/source-all/installed-root-all,
combined Python+Activity, startup-failure rollback and a subsequent valid apply
all passed. The observed `trial` power cut recovered to `base`/`rolled_back` on
cold boot.

The Acer A/B/full-system route is **BLOCKED** by the release-safe boot-cover
gate (`greia-early-framebuffer-v1` is not registered release-safe); no current
A/B bundle, installer or harness leg ran. Parent-source Activity seeding is
**BLOCKED** by the root-owned
`/var/lib/greia-os/activity-packages/generations` state tree, which the
`greiapanel` Parent service cannot chmod/write (HTTP 400
`activity_install_rejected`). NOT RUN: clean fixed-source rebuild/install,
partial-upload negative, 507 reserve, Parent-stop-after-202, observed
`applying` cut, full-system/A/B, seeded-creation hashes and Mobile upload. The
USB key was not modified. Session 04 remains OPEN. Next: correct the Parent
Activity state-tree ownership boundary, rebuild/reinstall the closed source,
repeat the clean core cases, then obtain an owner decision on the release-safe
cover before A/B acceptance.

### 2026-10-24 — Linux acceptance blockers remediated in source

Source freeze: `ab02b9ec6fc7108e7b873b2b2c8c68eefd47ff18`. The post-commit rerun executed
170 tests in 17.955 seconds, **OK with 1 Linux-only skip**; exact log:
`/tmp/greia-acceptance-followup/focused-ab02b9ec6.log`. The later evidence
commit changes documentation only; the full gate remains NOT GREEN as below.

Follow-up to Linux report `f5a7db98a` and its two preceding fixes. The RC
verifier extraction fix was retained. Parent Activity storage is now
`greiapanel:greiapanel 0755`, with private transaction containers owner-only.
Root-side staging, locks, pointer/receipt publication and legacy repair preserve
that owner; published generations remain read-only and child-readable. Cleanup
no longer chmods hardlinked files. Existing profile-group identities and dated
evidence were preserved; no profile-group migration was added.

The first follow-up full gate exposed an additional real initialization race:
permission repair sealed another caller's hidden staging directory. Repair now
considers only complete published generations. Regressions cover concurrent
first initialization, writable private staging, legacy active-directory
migration, Parent UMask=0007, retained-generation file modes, and a root update
followed by ordinary Parent install/uninstall.

The explicit `greia_release.py build-acceptance-fixture` command reuses the
existing Acer A/B composition, receipt, payload, hardware-support and bundle
producers. It emits separate experimental paths/identity/report and cannot be
added to the public update index. Ordinary `build`/`build-profile` still enforce
the release-safe boot-cover gate. The two Linux work orders now select this
fixture route for current-source VM acceptance; production release acceptance
is not implied.

Independent Luna source reviews passed both changes. The final combined focus
executed **170 tests, OK with 1 Linux-only identity test skipped**
(`/tmp/greia-acceptance-followup/focused-final.log`). Release/index/RC verifier
focus separately passed 70 tests. The skipped cross-user test still requires
Linux root with the provisioned service accounts; macOS does not prove it.

`make verify` is **NOT GREEN**. The initial completed follow-up ran 5,954 tests
with 8 failures, 3 errors and 9 skips: six previously recorded content/message
failures, the unresolved aggregate Shell memory failure (866,748 retained
surface bytes), and the initialization race fixed afterward; errors were ARM64
and two macOS lsblk cases. After the race fix, the final full retry aborted with
signal 6 in Quattro Amici's native Pygame audio warming path, without a final
test summary (`/tmp/greia-acceptance-followup/make-verify-final.log`). No claim is
made that this abort is baseline-proven or resolved. Separate validation stops
at the known unsupported ARM64 profile; shell checks and footprint pass.

No Linux image build, mount, QEMU or physical operation ran here. **Session 04
remains OPEN**. Next: commit/freeze this source, build and graphically install a
fresh RC, rerun both ownership initialization orders and the existing apply/
idle/rollback cases without manual guest repair; then build the explicit A/B
fixtures and execute the remaining VM cases. Preserve the original Linux
report as repaired-clone evidence and append a new exact-source runtime report.

## 2026-10-25 — Exact-source Linux retry: ownership/order PASS, A/B capacity blocked

Append-only result entry. Full evidence is in
`docs/reviews/2026-10-25_SOFTWARE_UPDATE_LINUX_RETRY.md`; evidence root is
`/var/tmp/greia-software-update-9161af3b30e3b96da314b24f4aba0e507eb46e7c-20261024T220454Z/`.
Focused coverage passed **170 tests, OK with 1 Linux-only skip**; the full gate
ran **5,957 tests, 7 failures, 3 errors, 3 skips** and remains NOT GREEN for the
documented baseline/environment outcomes.

A clean RC (`de75a782f786304235d89a631444c99a4ec04407567d34873b2d8119f040b0a2`)
was installed into two fresh 16 GiB targets. Clone A applied Python before any
Parent Activity seed and then installed a Parent Activity through the ordinary
route (HTTP 201); the store stayed `greiapanel:greiapanel`, with private
transaction directories and child-readable/non-writable `0555` generations.
Clone B seeded two Parent Activities first, applied Parent-source one and set
updates, then a built-in update, preserving both Parents and all 45 built-ins;
ordinary Parent install/uninstall returned 201/200 with data preserved. The
real-account root-to-`greiapanel` handoff test passed inside the guest. A capped
partial upload produced no 202, pending, candidate or new job.

The explicit A/B fixture bundle built and inspected
(`greia-acceptance-fixture-0.13.0-phase0-dev`, bundle SHA-256
`6f1e85eac0c6f0f81498e429c8c6f17ca46f45f8ed8552bc9f8c7cd4947592e3`), but the
matching installer build refused the profile capacity gate: **1287 MiB**
accounted installed use against `required_core_mib=1000` and
`architecture_review_mib=1250` with a 1536 MiB slot. The fixture did not waive
the production capacity gate. The A/B installer, ProductHarness, full-system
wrapper and A/B update/rollback legs remain NOT RUN pending an owner capacity
decision (raise the A/B build limit with finalizer-reserve evidence, or reduce
payload). The 507, Parent-stop, observed `applying` cut, Mobile, seeded-creation
hash and physical legs also remain NOT RUN; the USB key was not modified.
Session 04 remains OPEN. No release, A/B or physical claim is made.

## 2026-10-25 — A/B first-boot health accepted; slot isolation needs an owner decision

Append-only result entry. On the 1664 MiB A/B target the first boot now
issues and consumes the one-use boot-health capability, commits the
first-install journal, remains default A, and powers off; the harness's
post-boot health observation passes. Fixes in this boundary: the credential
generator and socket service now have launcher/runtime group access instead
of an empty-capability `root:root` context, and boot history is persisted to
`/run/greia-persist/greia/diagnostics` rather than the active slot. The
test-only X8 control now pulls the real credential/recovery units, starts
before the launcher and waits for the token.

The next harness guard, **active-slot isolation**, fails because slot A's raw
digest changes during its own acceptance boot. The A/B root is remounted
writable; moving history to PERSIST did not make the active slot
byte-identical. This is an A/B writable-state architecture decision (read-only
active slot with PERSIST binds versus a declared bounded active-slot
exception), not a capacity or health-token failure. The healthy B update,
rollback/failure legs and the clean A/B installer/fixture rebuild remain NOT
RUN. Session 04 remains OPEN; details are in
`docs/reviews/2026-10-25_SOFTWARE_UPDATE_LINUX_RETRY.md`.

### 2026-10-25 — Simpler A/B smoke; writable-root hash gate corrected

Implementation checkpoint: `0ede382f853bb0770e5b44b6fb741dd1d83cba4c`.
A post-commit rerun passed **335/335** in 3.180 seconds; log:
`/tmp/greia-ab-simplification/focused-0ede382f8.log`. The full gate above was
run on the same frozen implementation before the checkpoint; later changes
only record documentation evidence. Linux smoke execution remains pending.

The latest Linux report reached successful first-install health acceptance on
a patched disposable A/B target, then failed a harness raw-partition equality
check across A's own boot. The next bundle predates the credential-unit fixes
and the installer was patched; neither is a clean current-source artifact.
The report remains historical runtime evidence, not clean A/B acceptance.

ADR 0036 now explicitly clarifies the existing writable-root model. Full-system
SlotWriter still refuses active/accepted destinations; ordinary boot writes
are not updater writes. First-boot B remains strictly unchanged, and valid
unbooted write-window checks retain the strict helper. Across combined boot/
update/recovery legs, hashes have an explicit observational scope and no
byte-isolation PASS claim. Expected boot roles, release identity, mounted-root/
default/journal/PERSIST and health/recovery checks remain; recovery additionally
binds the previous accepted release to its PERSIST layout record. That binding
is semantic evidence, not an inventory of the old root's file contents.

The new primary retry is `docs/testing/2026-10-25_AB_SMOKE_RETRY.md`: clean
same-source baseline and next fixtures, clean installer, then install → first A
acceptance → healthy A-to-B. It writes per-leg result/error/traceback logs with
bounded 2400-second leg timeouts. Larger fault/reverse/data-survival tests come
after this initial smoke; Session 04 is not closed or waived. No read-only root,
new overlay, profile capacity change, or production updater bypass was added.

Independent Luna source review passed. The combined focused run passed
**335/335** (`/tmp/greia-ab-simplification/focused-final.log`); the short guide's
exact 66-test source command also passed. Four stale expectations/fixtures
from the preceding unit-group and boot-alias commits were corrected without
changing those production fixes: root User/empty capabilities and runtime-group
access remain asserted; temporary finalizer fixtures now supply the actual
kernel/initramfs inputs and prove hardlink aliases while retaining fstab mode.

The initial full `make verify` ran 5,958 tests: 8 failures, 5 errors and 9 skips,
including those four now-corrected test cases. The final full rerun completed
5,958 tests in 271.197 seconds: **6 failures, 3 errors, 9 skips; NOT GREEN**
(`/tmp/greia-ab-simplification/make-verify-final.log`). The remaining outcomes
are the recorded Foresta content (3), Parent Wi-Fi assertions (2), MBR message
wording (1), ARM64 profile error and two macOS lsblk errors. No new failure
remains in that run. Separate validation stops at the unsupported ARM64 profile;
shell/footprint checks and the short guide's Bash/Python syntax checks pass.
No Linux image build, mount, QEMU or physical operation ran here. Next: freeze
this source and give the Linux agent only the short smoke guide for its first
retry; retain first failure and clean artifacts, then continue the larger
matrix after all three legs pass. **Session 04 remains OPEN.**

## 2026-10-26 — Clean-source A/B smoke: install/first PASS, healthy blocked

Ran the 2026-10-25 A/B smoke work order from clean `866ba6827` after fixing the
missed 1664 MiB payload bound (`866ba6827`). Full gate matched the red baseline
(5,959 tests, 7F/3E/3S; same IDs, +2 tests); focused A/B suites 66 OK. Built the
0.13.0 base fixture/installer and 0.13.1 next fixture from that SHA. The install
leg and first boot (default A accepted, clean poweroff) **PASSED**.

The healthy A-to-B leg is **BLOCKED** at `update-verify`: the running
`greia-system-update.service` reports no candidate in the inbox although the
0.13.1 candidate is present in the disposable clone's PERSIST
`greia/namespaces/parent-credentials/system-updates/inbox`. Test-only harness
changes now inject the candidate host-side and copy control inputs; the next
owner must reconcile the service's inbox path/discovery with that location and
rerun healthy A-to-B. No B health, rollback/failure, 507, Parent-stop,
applying-cut, Mobile or physical leg ran. Evidence is under
`/var/tmp/greia-ab-smoke-866ba68277be8500db62de55a9189d78c9ea704b-20261025T162521Z/`.
Session 04 remains OPEN.

Detailed retry evidence and root-cause analysis:
`docs/reviews/2026-10-26_AB_SMOKE_RETRY_EVIDENCE.md`.

## 2026-10-26 — Candidate receipt projection corrected in test harness; VM retry pending

- Follow-up source work explains the previous update-verify refusal: host-side
  injection wrote the fixed candidate file but omitted the `status.json`
  receipt used by canonical `SystemUpdateInbox` discovery. The harness now calls
  `SystemUpdateInbox.receive` on the mounted disposable PERSIST tree, projects
  only the validated `bundle_path` to the guest's canonical
  `/var/lib/greia-os` path, restores inbox ownership, and fsyncs candidate and
  receipt. Guest control uses the same inbox API when receiving control media.
- Test orchestration also copies declared inputs, sizes the control disk for
  the bundle, emits bounded refusal diagnostics/poweroff for fail-fast serial
  evidence, initializes installer control-disk defaults, and aligns fake seams
  with the production helper. These are `tools/x8_qemu`/test changes only; no
  shipped updater, installer or runtime input changed in this tranche.
- Source review passed. Focused candidate-guide selectors: **168 tests,
  PASS in 1.220 s**. Broader X8 focused gate: **296 tests, PASS in 3.236 s**.
  Local `make verify`: **5,959 tests, 6 failures, 3 errors, 9 skips; NOT GREEN**
  (Foresta en/es/fr 3, MBR wording 1, Parent Wi-Fi 2; ARM64 profile 1 and
  macOS `lsblk` 2 errors). No full-gate or Linux-runtime pass is claimed.
- The Linux run from clean source `866ba6827` installed and accepted A, but the
  candidate-verification/update-to-B leg remains UNPROVEN. Next: after the
  reviewed harness changes are committed, follow
  `docs/testing/2026-10-26_AB_CANDIDATE_RETRY.md` if old bundles, accepted-A,
  source-diff, SHA, first-boot and PERSIST preflight all pass. Otherwise use
  the clean three-leg fallback `docs/testing/2026-10-25_AB_SMOKE_RETRY.md`.
  Do not manually repair the old guest. After healthy B, execute the remaining
  10/23 and 10/24 fault matrix. Session 04 remains OPEN.

## 2026-10-26 — Owner-directed package discovery simplification

The fixed published full-system package now owns candidate identity; status
is reporting/progress only. Discovery and public status recover from a missing,
malformed or stale receipt using the package manifest, without hashing the large
payload on polling. Full verification, compatibility, incomplete-upload isolation,
consumed-candidate removal, device-owned jobs and recovery remain. The harness
removes host-to-guest receipt projection. ADR 0036 and current operator/product
manuals now state that distinction. ADR 0038's lightweight application route
and independent on-device continuation remain unchanged.

Production source changed, so the next Linux action is the current-source
clean build/install/first-A/healthy-B route in
`docs/testing/2026-10-25_AB_SMOKE_RETRY.md`. The old candidate-only reuse guide
is historical; old images cannot prove this implementation. Source results:
`docs/reviews/2026-10-26_UPDATE_DISCOVERY_SIMPLIFICATION.md`. No new VM/device
claim; Session 04 remains OPEN.

## 2026-10-26 — Current-source A/B rerun: install/first PASS, stage harness timeout

Executed the clean route from `1275e0be1` on Linux. Host preflight passed and
the run started at 76% disk use after pruning oversized superseded `866ba6827`
artifacts (small logs preserved outside the tree). Full `make verify`:
**5,961 tests, 6 failures, 3 errors, 3 skips**; all failure/error IDs match the
documented Linux baseline and the earlier extra timing failure did not recur,
so `BASELINE_REVIEW=matched` was recorded without waiving the red baseline.
Focused A/B selectors passed **232 tests**.

Built the 0.13.0 base fixture (bundle
`b45f0fc77aaf04883442a74be742dc4e1fa888648a55e274b51b836a5b662a9b`), the
installer (`1edbcb0bec1b8b279543e74d4a39c0b2dc61454ce102f988fbe0fa75ce325571`)
and the 0.13.1 next fixture (bundle
`3ae9cdeafa6e52459016e1a23315648ee4b8887a314c77c288259c1df4d68aa5`) from that
SHA. Both fixtures are experimental/non-release and both bundles inspect
cleanly. The install leg and first boot (default/committed A, accepted base
release, clean poweroff) **PASSED**.

The healthy A-to-B leg is **FAILED at `update-stage`**, not at discovery: the
installed service returned `STATUS -> OK` and `VERIFY_CURRENT_CANDIDATE ->
VERIFIED`, then the test-only guest control's hard-coded 30 s socket timeout
fired while `STAGE_CURRENT_CANDIDATE` was writing the ~714 MB candidate. No
stage completion, arm, B boot/health or final host observation ran; healthy B
remains **UNPROVEN**. This is a harness control-bound defect, not a recorded
production refusal. The run also leaked 19 loop devices; they were detached
with `build/lib/safe-cleanup.sh` and the post-cleanup loop audit is empty.

Evidence root:
`/var/tmp/greia-ab-smoke-1275e0be1a9e0cda724ce18151ae65a25f03c98c-20261026T014350Z/`.
Report:
`docs/reviews/2026-10-26_AB_SMOKE_CLEAN_SOURCE_RERUN_EVIDENCE.md`. Next: fix
the test-only stage timeout and loop cleanup, commit a new freeze, then rebuild
and rerun all three legs; do not reuse these images with modified harness
source. Session 04 remains OPEN; no rollback, Parent/fault, full-system,
physical or USB claim is made.

## 2026-10-26 — Harness staging bound and cleanup correction

The clean `1275e0be1` rerun establishes installed candidate STATUS/VERIFY as
well as install/A health, but not healthy B. Its 30-second test client bound
cut off staging; the report also records 19 loop associations. Current source
reuses the production operation timeout for status/verify/stage (stage 1,800 s),
keeps root-only test arm separate, and replaces ignored teardown results with
scoped repository cleanup and explicit failure reporting. This changes only
harness/tests, not shipped updater behavior.

Next is the bounded healthy A-to-B route in
`docs/testing/2026-10-26_AB_STAGE_RETRY.md`, conditional on unchanged shipped
source/build inputs plus exact bundle/accepted-A hashes, prior first-boot proof
and offline/loop checks. This supersedes the report's blanket rebuild direction
for harness-only changes. Otherwise rebuild via the clean three-leg guide.
No new Linux/physical success is claimed. Source verification is appended to
`docs/reviews/2026-10-26_AB_SMOKE_CLEAN_SOURCE_RERUN_EVIDENCE.md`; Session 04 OPEN.

Owner workflow correction in this follow-up: the immediate work order runs
cheap source/host preflight, then only the healthy update against preserved
verified images. A missing tool, timeout, stale test assertion or cleanup issue
is not a rebuild trigger. Diagnose the failing layer first. Rebuild only for
changed shipped/build inputs or actually missing/corrupt artifacts. Record the
single retry result and stop; do not automatically start the remaining fault
matrix. Those release obligations remain OPEN separately.

## 2026-10-26 — Stage retry result: stage failure masked by login-prefixed marker

Executed the single retry in `docs/testing/2026-10-26_AB_STAGE_RETRY.md` from
`abb11b0a0`, reusing the verified `1275e0be1` bundles and accepted-A clone.
Source-diff allowlist passed; focused harness suites **176 tests OK**. Reuse
hashes and prior first-boot JSON validated; holder check reported no users and
there were no owned loops before the leg. Host-preflight deviations recorded:
PSmisc 23.7 rejects the work order's `fuser -v -- <files>` form (equivalent
supported form used, status 1 = no holders), and the reused root-owned `0600`
bundles were made `0644` so the user-level checks could read them.

The leg reached `update-status -> OK` and `update-verify -> VERIFIED`, then
**`update-stage` failed with `phase update-stage failed (exit 120)`**.
`update-arm` then correctly refused with `update transaction is accepted, not
staged`. The stage failure marker was prefixed by `greia login:` on the serial
console, so `_control_phase_failure` did not recognize it and the harness
continued to the arm phase. The first concrete error is the stage failure; the
arm refusal is downstream. The immutable base payload's shipped client has the
1800 s stage bound, so this is not the old 30 s test-client timeout. The
captured serial does not include the stage service error/traceback, so
installed-updater stage completion remains **UNPROVEN**; no production refusal
is claimed. Accepted-A SHA is unchanged and the post-leg loop audit is 0.

Evidence:
`/var/tmp/greia-ab-stage-abb11b0a0fc999ec536841f02441423546b845fa-20261026T085728Z/`.
Report: `docs/reviews/2026-10-26_AB_STAGE_RETRY_EVIDENCE.md`. Next: fix the
test-control failure-marker handling and stage journal capture, then authorize
a new single attempt; do not reuse the failed clone or rebuild the OS for this
harness-only cause. Session 04 remains OPEN; no B health, rollback, Parent,
full-system, physical or USB claim is made.

## 2026-10-26 — Correct masked failure and collect existing-image diagnostics

The `abb11b0a0` report is a failed stage, not healthy B. Prefix matching missed
the reported login-prefixed marker and incorrectly continued to arm. Source
now reproduces/detects those bytes, stops the phase sequence, and persists
bounded raw response/refusal and exception-cause diagnostics before poweroff.
A subprocess demonstrates exit 120 from stderr-flush failure; the installed
stage's actual first error is still unknown. Separate stage/arm boots were
traced against the real journal/reconciliation owners and preserve staged state.

The immediate route is `docs/testing/2026-10-26_AB_FAILED_IMAGE_DIAGNOSTICS.md`:
read-only collection from the existing failed clone, report and stop. No rebuild
or fresh VM/update run. The collector reuses scoped teardown and mounts with
read-only loop plus `ro,noload`; its output is facts, not acceptance. PSmisc
holder syntax/status handling and sudo reads of root-owned artifacts are also
corrected. Production code/build inputs remain unchanged. Source evidence is
appended to `docs/reviews/2026-10-26_AB_STAGE_RETRY_EVIDENCE.md`; Session 04 OPEN.

## 2026-10-26 — Failed-image read: B empty, stage cause unrecoverable

Executed the offline work order from `65cd6212e`. Focused diagnostics/handoff
suites: **14 tests OK**. The failed clone was proven offline (fuser status 1
with empty output) and the collector exited 0 with cleanup ok (loop
`/dev/loop37` detached; no owned loops after). Diagnostic JSON SHA-256
`c7f01595…`, stored under
`/var/tmp/greia-ab-offline-65cd6212e2e0023d9e6f131d52e24d80396ce66d-20261026T145341Z/`.

Facts: A is the accepted base 0.13.0 slot; B mounted but has **no release
identity**, so B does not contain the next 0.13.1 release; PERSIST layout
still accepts A, the boot journal is `accepted`, and update status names the
next bundle but remains **`received`** with activation unavailable. The old
control's `phase-result.json` and `service-diagnostics.txt` are absent, as
expected for this image. Collector errors are empty.

The stage failed before B finalization, but the first stage error is
**unrecoverable from this image**: the facts cannot distinguish a service
refusal, crash, or lost control error. The demonstrated closed-stderr flush is
a possible loss mechanism, not proof. Do not rebuild or replay blindly. A
later bounded diagnostic boot with corrected capture needs a separate work
order. Healthy B remains UNPROVEN; Session 04 OPEN. Report:
`docs/reviews/2026-10-26_AB_FAILED_IMAGE_DIAGNOSTICS_RESULT.md`.

## 2026-10-26 — Offline facts received; bounded stage-only diagnostic

The offline result at `10de26ce8` confirms accepted A, missing B release
identity and received update status; old first-error logs are unrecoverable.
Source audit found no established capacity, dependency or boot-order cause.
The next work order is `docs/testing/2026-10-26_AB_SINGLE_STAGE_DIAGNOSTIC.md`:
reuse verified inputs, make a fresh clone, inject the candidate offline, boot
only stage once, then collect response/error and offline facts even on failure.
No rebuild/install/arm/B boot/full matrix. New helper/tests live under
`tools/x8_qemu` / `tests/test_x8_qemu`; no production source changed.

The helper uses the actual default ProductHarness phase executor with a
2,400-second bound, a phase-only 64 MiB control disk, and the existing collector.
It retains errors, collector state and source/bundle before/after hashes without
claiming stage or health acceptance. New collaboration policy/CODEOWNERS commits
are preserved and exactly allowlisted as non-image source for artifact reuse.
Evidence is appended to `docs/reviews/2026-10-26_AB_FAILED_IMAGE_DIAGNOSTICS_RESULT.md`.
No Linux boot executed on this Mac; actual stage cause and healthy B unproven.
Session 04 remains OPEN.

## 2026-10-26 — Single-stage diagnostic preflight failure

Ran the work order preflight from clean `81ba47dba`. The source-test gate ran
**80 tests with one failure**:
`test_generated_stage_failure_avoids_exit_120_from_buffered_stderr` left its
positive-control fake-server thread alive after `server.join(timeout=5)`. The
other 79 tests passed, including the new stage-diagnostic suite. Per the work
order, the one-stage VM boot was **not** started; no install, arm, B boot,
update replay or collector run occurred. The remaining read-only preflight
checks passed: source allowlist clean, accepted-A/next-bundle hashes OK, holder
status 1 with empty output, zero old-evidence loops. Inputs were preserved.

This is a test-control race, not an installed-updater result. Report:
`docs/reviews/2026-10-26_AB_SINGLE_STAGE_DIAGNOSTIC_PREFLIGHT_FAILURE.md`.
Next: fix the fake-server teardown/join, rerun the preflight, then authorize
the single stage boot. Do not rebuild the OS for this harness-only failure.
The installed stage cause and healthy B remain UNPROVEN; Session 04 OPEN.

## 2026-10-26 — Deterministic closed-stderr preflight fixture

The Linux report at `920595d4e` correctly stopped before VM work on a test
fixture failure. The 10 KB pre-script stderr write could fail before connection;
the server also had EOF/cancellation cleanup defects. Only that fixture changed:
short controlled buffering, explicit child environment, real request/refusal
assertions, EOF handling, bounded join-before-close and guaranteed child reap.
The final work-order preflight passes 80 tests in 14.162 s with parent
PYTHONUNBUFFERED=1; independent Luna review passed and repeated the final case
8 times. Exact evidence is appended to the preflight-failure report.

No production/harness implementation or image inputs changed. Next rerun the
existing single-stage work-order preflight; if green continue directly to its
one scoped stage diagnostic boot and report. No rebuild or new approval loop.
Actual stage cause/healthy B remain UNPROVEN; Session 04 remains OPEN.

## 2026-10-26 — Single-stage diagnostic source-gate stop

Reran the work order from current main. The corrected source preflight passed
**80 tests OK** with parent `PYTHONUNBUFFERED=1`. The work order's own
`git pull --ff-only` advanced main to `abd9f5045` and added
`src/greia_platform/languages/en/manifest.json` plus
`.../it/manifest.json`. These are shipped `src/` files outside the strict A/B
reuse allowlist, so the work order stopped before the one-stage diagnostic
boot. No VM, install, arm, B boot, update replay or collector ran.

The new files are selector metadata (locale/name/native/flag/order/direction);
they are not in the accepted-A image or next bundle from `1275e0be1`. During
push reconciliation, main continued to advance (at last check `ef8eb3415`) with the broader
localization implementation (installer/launcher/platform source plus
en/es/fr/it manifests), so the source gate is unchanged and broader. Whether
any of it is irrelevant to the updater-stage target is a review decision, not a
safe assumption under the gate. Read-only input checks pass: accepted-A and
next-bundle hashes OK, holder status 1 with empty output, zero old-evidence
loops. Report:
`docs/reviews/2026-10-26_AB_SINGLE_STAGE_DIAGNOSTIC_SOURCE_GATE_FAILURE.md`.
Next: record an explicit reuse exception or rebuild the next bundle/image; do
not boot until that decision is recorded. Actual stage cause and healthy B
remain UNPROVEN; Session 04 OPEN.

## 2026-10-27 — Reviewed old-release diagnostic exception and package/data blocker

The latest agent stopped before VM work at the blanket old-source reuse gate.
Review of `1275e0be1..78f07861c` finds 19 localization/UI production source
changes but unchanged updater/slot/boot and build/runtime/Activity/asset inputs.
The new `docs/testing/2026-10-27_UPDATE_AGENT_HANDOFF.md` explicitly permits one
old-release stage diagnostic on the frozen existing payloads, with reviewed-
host and actual-host source identities separate. It does not waive current-
release or current-language image acceptance. One stage, collect, report, stop;
no rebuild/install/arm/B boot/matrix. Current source gates passed: 80 update
preflight tests; 59 language tests and four zero-issue locale checks.

The same review identifies a source compatibility blocker for application
updates: Python/combined package inventories and inspector paths exclude new
language manifest/UI JSON, while the new registry imports require them.
Do not trial current registry code on a pre-manifest base through that package
route. A bounded package-data/validation fix or compatible-base contract is
needed before those trials; do not infer that a full image rebuild is the
normal solution for lightweight updates. This is documentation/source review
only; no implementation or Linux acceptance is added. Session 04 remains OPEN.

## 2026-10-27 — Language resources delivered by application packages

Implemented the bounded missing data path in ADR 0038's existing ZIP route.
Normal Python/combined snapshots include every offered canonical locale's
manifest/UI pair; schema, English coverage and placeholders are checked before
publication. Stale managed JSON is removed only from private staging, preserving
the prior generation and child data. No production locale/audio edits or new
registry were introduced.

The actual pre-manifest `1275e0be1` reader rejects JSON. A one-time
`build-receiver-bridge --base-ref …` exports that exact old Python/runtime
snapshot and overlays only the reader and generation modules. The old reader
can stage this ordinary code-only v1 package, then the bridged reader can stage
the normal current JSON-bearing package. This source chain is tested through
isolated old/bridged processes and a fresh candidate-registry import. A separate
temporary fifth-locale test changes only data. The bridge must not be sent to
an unknown/newer base and cannot supply an absent update bootstrap.

Source verification on the worktree based on `d1d6b60ad`, Python 3.12.7/macOS:
121 focused update/language tests PASS; four offered-language checkers zero
problems; real-source normal/bridge CLI builds PASS; fresh Luna review PASS;
427-document link audit and four auditor tests PASS. The required `make verify`
run remains RED with 5,990 tests, six failures, three errors and nine skips in
the recorded unrelated voice-review, MBR assertion, Parent JS assertion,
ARM-builder and missing-macOS-`lsblk` cases. The initial concurrent focused
invocation raced bytecode cleanup; its final sequential rerun passed all 121.
Evidence logs: `/tmp/greia-language-update-20261027/` on the Mac.

Updated package guide, ADR, operations and skills; the precise next installed
check is `docs/testing/2026-10-27_LANGUAGE_UPDATE_PACKAGE_ACCEPTANCE.md`, using
an existing idle matching disposable target, with no OS rebuild or interference
with another test. Old A/B diagnostic instructions are explicitly paused on
current main after updater source changed; no stale gate rerun is requested.
Installed health/Parent-disconnection acceptance and A/B stage diagnosis remain
UNPROVEN. Session 04 remains OPEN; this is source completion of the language
package-data gap, not image/device or lifecycle closure.

## 2026-10-27 — Old-release stage diagnostic executed; updater refused

Resumed the paused old-release diagnostic from the reviewed host source
`78f07861` in an isolated clean checkout, not current main. Preflight passed:
80 update tests OK in 4.183 s; EN/IT/ES/FR checkers each reported zero source/
placeholder problems; frozen-source and critical-owner gates clean; accepted-A
and next-bundle hashes OK; holder status 1; no owned loops before the leg.

The one `update-stage` boot was attempted and the stopped clone collected.
`STAGE_CURRENT_CANDIDATE` was **refused** by the installed updater:

```text
inactive-slot filesystem is unavailable:
block topology observation failed:
slot device capacity is unobservable: sda2
```

`phase-result.json` records `ERROR`/`REFUSED`, empty `cause_chain`; the service
snapshot shows the update service active and otherwise healthy. This is a
captured production refusal, not a capture/host failure. A remains accepted
0.13.0; B has no finalized release identity; PERSIST status remains `received`;
input and bundle hashes are unchanged. Collector cleanup was ok (loop
`/dev/loop13`, no owned loops after); command/final exits are 1 because staging
was refused. No arm or B boot ran. Report:
`docs/reviews/2026-10-27_AB_OLD_RELEASE_STAGE_DIAGNOSTIC_RESULT.md`.

This diagnoses only `1275`-era updater behavior on the disposable image.
Healthy B, current-language image acceptance, rollback/fault matrix and
physical/USB acceptance remain UNPROVEN; Session 04 OPEN. Do not automatically
rebuild, retry, arm or boot B.

## 2026-10-27 — Old-release stage refusal analysis

Added `docs/reviews/2026-10-27_AB_OLD_RELEASE_STAGE_REFUSAL_ANALYSIS.md`, a
reviewable source-path analysis of the captured refusal. It traces the failure
through `_observe_production_topology` / `_probe_role_fact` /
`_block_node_size_bytes`; active `sda2` capacity is unobservable before the
inactive-slot write. The cheapest hypothesis is the hard-coded 64-bit
`BLKGETSIZE64` ioctl request on an i386 guest; the `blockdev` fallback and
service device policy are alternatives.

Recommended order: a read-only guest probe of `/sys/class/block/*/size`, both
ioctl encodings, `blockdev`, `lsblk` and the service capability/device policy;
then a bounded sysfs/parent-disk capacity fallback in current main with i386
and fallback tests; then a current fixture/image and the real install →
first-A → stage → arm → B health route. Do not patch the frozen 1275 guest.
No new runtime evidence; healthy B and Session 04 remain OPEN.
