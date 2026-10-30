# Universal Greia Setup Media Architecture — Revised and Red-Teamed

**Status:** REVISED ARCHITECTURAL PLAN & SPECIFICATION  
**Target:** R8 / Multi-Platform Installer Convergence + update-capable installation baseline  
**Authority:** subordinate to accepted ADRs; aligned with ADR 0012, ADR 0013, ADR 0014, ADR 0021, ADR 0030 and **ADR 0036**  
**Normative owner for the universal Setup image:** ADR 0036 §9 together with the active plan `docs/plans/2026-09-15_MULTIPLATFORM_RELEASE_INSTALL_UPDATE_COMPLETION.md`. Where this document and those two disagree, they win. This document remains the detailed design rationale.
**Reaffirmed here, and unchanged by any 2026-09-27 event:** the legacy-BIOS removable first stage is `MBR -> active FAT32 -> SYSLINUX -> i386 live kernel/initramfs`. UEFI files for modern x86 and Raspberry Pi firmware/config/DTB assets coexist on that same FAT boot partition. Removable USB first stage and installed internal-disk boot are separate owners; the installed Acer uses GRUB A/B and that is not in question.  
**Product invariant:** Installation is graphical and fail-closed. Whole-disk installation offers only verified eligible targets. Media identity, payload authority, target identity, power state and compatibility are rechecked immediately before destructive work.

---

# 0. Executive decision

Retain the product goal:

> **A parent downloads and flashes one Greia Setup image and does not need to understand CPU architecture, BIOS/UEFI, Raspberry Pi generations, partitions, kernels or installer variants.**

The setup image is universal at the **product and application-contract level**. It is not implemented by pretending every platform has the same firmware, bootloader, partition scheme or target-storage rules.

The single artifact may contain multiple boot adapters, architecture-specific live roots, signed release artifacts and architecture/suite hardware-support pools beneath one installer application and one common transaction model.

Four decisions are locked by this revision:

1. **Every new release-capable installation creates the final update-capable A/B storage contract from day one.** The old single-root PC and simple Pi `boot + root` layouts are not the target architecture.
2. **Installation and system update consume the same signed Greia release authority.** The installer must not create a second `shared assets + target tar` image factory that can drift from `.greiaupdate` releases.
3. **Boot transactions are polymorphic.** x86 uses a GRUB backend; Raspberry Pi uses the EEPROM firmware's native `tryboot` / `autoboot.txt` A/B mechanism. Common Greia code sees one semantic candidate/health/rollback contract.
4. **The universal removable Setup medium starts from Greia's physically proven legacy-BIOS primitive, not from an aesthetically cleaner but unproven GPT/GRUB design.** The current reference Acer has already proven active-FAT32 + SYSLINUX removable boot and has already rejected GRUB-on-USB on the tested firmware/media combination.

The last rule applies to the **removable Setup medium only**. It does not change the modern installed-target decision to use GPT/UEFI where appropriate.

---

# 1. Corrections and non-negotiable design constraints

## 1.1 A/B layout is mandatory for new release installations

ADR 0030 already defines the stable update model:

```text
boot transaction authority
system A
system B
persistent Greia data
```

A new installer that creates only one mutable root knowingly creates a machine on which `system.update.activate` must remain false.

All new release-capable profiles therefore create a proven A/B layout. Experimental profiles without such a backend remain fail-closed for activation.

## 1.2 Do not create a parallel installer payload format

The previous `shared/ + target.tar.zst + installer reconstruction` concept is rejected.

Use the same signed whole-system release/slot artifact consumed by the update subsystem. Installer and updater share:

- release parsing and signature/compatibility checks;
- slot writer;
- hardware `SlotFinalizer`;
- release identity;
- platform boot-transaction backend;
- final verification semantics.

The tested release must be the installed release.

## 1.3 Pi 400 and Pi 500 are distinct boot generations

Do not use one Pi-4 firmware recipe for both boards.

- Pi 400 is BCM2711 / Pi-4-family.
- Pi 500 is BCM2712 / Pi-5-family.
- Pi-4-family firmware such as `start4.elf` is not a generic Pi-5 boot recipe.
- Pi 5/500 use a different firmware/kernel path.
- `bootcode.bin` is not the ordinary boot stage for Pi 400/500.

One ARM64 live root may still be shared where valid, but board-family boot assets are generated and verified by typed adapters.

## 1.4 Pi 500 is not Pi 500+

Ordinary Pi 500 uses microSD as its primary built-in OS storage. Pi 500+ is the separate keyboard model with integrated M.2/NVMe capability.

```text
Pi 400   -> primary target microSD
Pi 500   -> primary target microSD
Pi 500+  -> separate future/reference profile if deliberately adopted
```

Do not advertise an internal NVMe target on ordinary Pi 500.

## 1.5 Unknown ARM hardware fails closed

Never default unknown ARM64 hardware to the Pi 400 profile.

Compatibility uses trusted facts such as:

- architecture and CPU ABI;
- exact device-tree compatible values;
- boot mode / firmware family;
- declarative image-profile compatibility;
- measured minimum RAM/storage;
- vendor-neutral hardware inventory.

Human-readable model strings are diagnostic presentation only.

## 1.6 Advanced profile selection is bounded

Normal parents may choose only among profiles the compatibility engine has already proven eligible. Unsafe profile forcing belongs only to an explicit developer/recovery lane.

## 1.7 Setup-media self-exclusion must use physical ancestry

A label such as `GREIA_SETUP` is not destructive authority and can be duplicated.

Preserve the existing Greia live-media identifier and resolve the actual mounted live-medium source through major:minor/sysfs to its physical whole-disk ancestor. The whole disk and all descendants are permanently ineligible for the current installer session.

If ancestry is ambiguous, expose zero targets.

The privileged install service repeats this resolution immediately before destructive work.

## 1.8 Target selection uses durable identity, not path or list index

A block-device observation distinguishes:

```text
session locator:
  /dev path
  major:minor
  sysfs path

durable identity facts:
  serial / WWN / NGUID / EUI where available
  MMC CID for SD/eMMC where available
  capacity
  transport/topology facts
```

The UI stores a strong `identity_key`, not `selected_target = 0` as destructive authority. If the selected medium disappears or a new medium reuses the same `/dev` path, selection and confirmation are invalidated.

## 1.9 MMC/removable eligibility is platform policy

Do not add a global `allow_mmc=True` switch.

- normal PC whole-disk install accepts only positively eligible internal storage and continues to reject the setup USB/removable external disks;
- Pi 400/500 may explicitly accept the card in the built-in microSD host;
- internal eMMC must not be rejected merely because its Linux node starts with `/dev/mmcblk`;
- USB mass-storage install on Pi is a separate proven capability, not an accidental consequence of appearing as `/dev/sdX`.

## 1.10 Refresh Drives is transactional

Refresh is allowed only before destructive installation.

On refresh:

1. create a new bounded inventory generation;
2. resolve setup-media ancestry again;
3. recompute platform target eligibility;
4. preserve a prior selection only when the durable identity still matches;
5. clear selection/confirmation if device identity, capacity, read-only state, mount state or active storage-stack state changed.

## 1.11 Secure Boot is part of modern-amd64 acceptance

`EFI/BOOT/BOOTX64.EFI` existing is not sufficient modern-PC evidence.

Preferred release path is the supported Debian shim + signed GRUB + signed kernel chain unless a later Greia-specific signed chain is deliberately adopted.

Modern-amd64 release acceptance must boot the exact setup/installed artifacts with Secure Boot both ON and OFF. “Disable Secure Boot” may remain engineering recovery guidance, but it is not the ordinary product definition.

## 1.12 The graphical installer should not own block devices directly

The current prototype graphical installer runs as root. The target release architecture separates:

```text
unprivileged greia-installer UI
        |
        | narrow Unix-domain semantic protocol
        v
socket-activated privileged installation service
        |
        v
layout / slot / boot writes
```

The privileged request schema cannot accept arbitrary commands, paths, URLs, mount locations, block devices or bootloader arguments supplied by the UI.

## 1.13 Universal removable media must preserve the proven Acer BIOS path

Greia already has accepted physical evidence in:

```text
docs/engineering/boot/INSTALLATION_USB_BOOT_POSTMORTEM.md
build/live-syslinux/syslinux.cfg.in
```

That evidence established, on the reference Acer class:

```text
GRUB MBR on removable USB -> not a reliable boot path
plain MBR + active FAT32 + SYSLINUX -> boots
```

Therefore R8 must not begin by replacing the known-good removable-media path with GPT + BIOS GRUB and asking the weakest reference machine to prove it again.

The first universal-media candidate MUST preserve:

```text
MBR partition table
active FAT32 first partition
SYSLINUX MBR/VBR legacy-BIOS path
explicit kernel/initramfs locations
Greia live-media identity
```

UEFI and Raspberry Pi boot assets are layered onto that same artifact. GPT removable media may be reconsidered later only if it provides a material benefit and the exact candidate physically passes every reference platform.

This constraint is about the Setup USB. The installed legacy x86 target may still use GRUB because internal-disk GRUB is a separately proven firmware path.

## 1.14 Low-memory live-boot behavior is part of correctness

The Acer-class floor makes live-environment memory policy an architectural constraint.

For C0/legacy live installer profiles:

- `toram` is forbidden;
- the compressed live root remains on the Setup medium and is read through the live filesystem/loop path;
- writable copy-on-write state is a bounded tmpfs overlay;
- the overlay limit is explicit rather than inheriting an unbounded/default fraction of physical RAM;
- actual overlay use, process RSS/anonymous memory and `MemAvailable` are measured during the full installer transaction, not only at idle;
- Python/Pygame/hardware-probe peaks are part of the acceptance measurement.

Current Greia media already uses an explicit `overlay-size=128M` and no `toram`. Treat that as the starting evidence-backed ceiling, not as a permanent optimum.

Do **not** encode speculative `64 MiB overlay` or `120 MiB idle RAM` limits as architecture constants before measurement. R8 must establish release budgets from the exact image and the physical reference machine, then tighten them if evidence supports it.

## 1.15 Pi microSD hot insertion is a product gate, not an assumed kernel feature

The preferred Pi parent flow depends on inserting the target microSD after the Setup USB has already booted. Therefore Pi 400 and Pi 500 must each prove, with the exact Greia ARM64 live kernel:

```text
boot without target microSD
-> begin bounded block/udev/kernel observation
-> insert card
-> kernel observes insertion
-> a block device appears
-> durable MMC identity is readable
-> Refresh Drives discovers it
-> target policy classifies it correctly
```

The acceptance test is backend-neutral. Do not hardcode a guessed kernel driver name or “enable polling” workaround into architecture before evidence identifies the failure layer.

If hot insertion fails, the ordinary product flow remains unresolved. Evaluate an already-configured USB-first boot order, a physically proven firmware boot-selection flow, or an explicit external microSD-reader recovery path. Do not silently rewrite EEPROM to preserve the one-image claim.

## 1.16 FAT32 boot-control durability is layered, not atomic

`autoboot.txt` lives on FAT. A successful rename does not make the operation crash-atomic and FAT is not a transactional database.

The Pi boot backend should use the strongest practical write discipline:

```text
write autoboot.new
-> fsync the new file
-> rename over autoboot.txt
-> fsync the containing directory where supported
-> syncfs the boot-control filesystem
-> re-read and verify exact expected bytes
```

This is a durability layer, not the rollback mechanism.

Rollback safety comes from the combination of:

- independently bootable A and B boot partitions;
- independently bootable A and B system slots;
- one-shot `tryboot`;
- known-good `tryboot_a_b` / `autoboot` behavior;
- proven firmware partition-walk/recovery behavior;
- Greia persistent accepted-slot state;
- power-cut/fault tests at every boot-control commit boundary.

If the required firmware capabilities or recovery behavior are unavailable, unknown or not proven on the exact Pi generation, do not arm an update candidate. Routine Greia installation/update must not silently update EEPROM to obtain them.

---

# 2. Core architecture

```text
Greia release factory
   |-- live i386
   |-- live amd64
   |-- live arm64
   |-- signed Greia releases / system-slot payloads
   `-- signed hardware-support pools
             |
             v
Universal Setup image composer
             |
             v
greia-setup-universal.img
             |
   +---------+----------+
   |         |          |
 BIOS      UEFI      Pi EEPROM
   |         |          |
   +---- architecture-appropriate live root
             |
             v
   unprivileged installer UI
             |
      semantic plan request
             |
             v
 privileged install transaction service
             |
  re-probe + verify all authorities
             |
   +---------+----------+
   |         |          |
 legacy    modern      Pi
 MBR A/B   GPT A/B   tryboot A/B
   |         |          |
   +---------+----------+
             |
             v
      first boot -> INTERACTIVE_READY -> BOOT_HEALTHY
```

Common code owns UI, localization, hardware inventory, target identity, power policy, payload verification, confirmation, settings, hardware-support resolution, transaction state, slot finalization and verification.

Platform adapters own only firmware/boot mechanics, physical layout and storage eligibility.

The removable-media composer and the installed-target layout adapters are intentionally separate concepts. The Setup USB may use an MBR/FAT compatibility layout while a modern installed target uses GPT.

---

# 3. Universal Setup-media boot candidate

## 3.1 Preferred R8 candidate: MBR + active FAT32 compatibility foundation

The first R8 universal-media candidate is:

```text
sector 0
  SYSLINUX-compatible MBR code + DOS/MBR partition table

P1 GREIA_SETUP_BOOT    FAT32, active
   |-- SYSLINUX BIOS loader + modules/config
   |-- i386 live kernel/initramfs needed by the BIOS path
   |-- signed amd64 UEFI removable path under EFI/BOOT
   |-- amd64 live kernel/initramfs as required by the UEFI path
   |-- Pi 400 boot assets
   |-- Pi 500 boot assets
   `-- media-identity/bootstrap metadata

P2 GREIA_SETUP_DATA    data filesystem selected by measured compatibility
   |-- live/i386/rootfs.squashfs
   |-- live/amd64/rootfs.squashfs
   |-- live/arm64/rootfs.squashfs
   |-- signed release artifacts
   |-- verified hardware-support pools
   `-- signed setup-media manifest
```

The exact P2 filesystem is an implementation decision to prove, not a label-only mount contract. The initramfs must resolve the correct Setup-data partition from the Greia media identity and its physical ancestry; it must not trust `LABEL=GREIA_SETUP_DATA` as destructive or identity authority.

Reasons for this baseline:

- it preserves the physically proven Acer removable-boot primitive;
- it keeps one FAT boot partition that UEFI and Pi firmware can both consume;
- it separates boot-critical FAT content from larger live/release payloads;
- it does not force legacy BIOS to execute GRUB from removable media;
- it keeps modern installed disks free to use GPT independently.

The exact same image hash must physically boot:

```text
Acer legacy BIOS
modern amd64 UEFI / Secure Boot OFF
modern amd64 UEFI / Secure Boot ON
Pi 400 EEPROM USB
Pi 500 EEPROM USB
```

No platform-specific rebuild may be substituted during acceptance.

## 3.2 GPT removable media is no longer the primary candidate

A GPT universal Setup image is not forbidden, but it is **demoted to an evidence-gated alternative**.

Do not spend R8 replacing a known-good Acer path merely because GPT is cleaner for modern firmware. Reconsider GPT only if:

1. it solves a concrete measured problem the MBR/FAT candidate cannot solve;
2. the exact GPT artifact still boots the physical Acer reference;
3. UEFI Secure Boot and both Pi generations also pass;
4. no new bootloader-specific recovery regression is introduced.

Do not publish separate “legacy” and “modern” Setup downloads to hide universal-media failure.

`BOOTIA32.EFI` is not part of current release claims unless an actual 32-bit-UEFI hardware class is adopted and certified.

---

# 4. Pi Setup-USB boot order and target-card insertion

Pi 4-generation and later firmware may select a bootable SD card before USB depending on EEPROM boot order. Therefore “USB inserted + existing bootable microSD inserted” does not guarantee that the Setup USB starts.

The first parent-safe workflow to prove is:

```text
power off
remove target microSD
insert Greia Setup USB
boot installer from USB
insert target microSD after installer is running
Refresh Drives
install
```

This becomes product guidance only after Pi 400 and Pi 500 physical evidence proves hot insertion/enumeration reliably with the exact Greia live kernel.

The R8.5 hotplug gate records, at minimum:

```text
udev/block events
kernel log around insertion
/sys/class/mmc_host state
/sys/block state
lsblk before/after
resolved durable MMC identity
installer inventory generation before/after
```

Do not prescribe driver-specific polling from prose alone.

If hot insertion is not reliable, evaluate, in order:

1. already-configured USB-first EEPROM boot order;
2. a simple, physically proven firmware boot-selection interaction;
3. an external microSD reader as an explicit recovery/install workflow.

The installer must not silently rewrite Raspberry Pi EEPROM boot order or firmware merely to preserve the one-image product goal.

---

# 5. Host compatibility and profile selection

Preserve ADR 0013's distinction:

```text
build profile = what an image contains
hardware inventory = what the current machine actually is/can do
```

A bounded `InstallerHostContext` should expose trusted facts such as architecture, relevant CPU ABI/features, BIOS/UEFI/Pi boot family, Secure Boot state when observable, device-tree compatible values, RAM, display suitability, storage controllers, setup-media identity, hardware-inventory token and Pi boot capability facts.

The setup image contains a signed catalogue of installable release profiles. Compatibility intersects host facts with that catalogue.

```text
0 matches -> installation unsupported / no destructive action
1 match   -> select automatically
N matches -> choose highest-priority stable compatible profile;
             Advanced may show other already-compatible choices
```

Unknown ARM boards never default to a known Pi.

For Pi update-capable profiles, compatibility must also expose whether the required one-shot and recovery semantics are actually available/proven. A board being “Pi 400” or “Pi 500” is not by itself sufficient update authority.

---

# 6. Installer and updater share release/slot authority

Fresh install and later update must not have independent slot writers.

Common abstractions should include equivalents of:

```python
class LayoutAdapter(Protocol): ...
class SlotWriter(Protocol): ...
class SlotFinalizer(Protocol): ...
class BootInstaller(Protocol): ...
class BootTransactionBackend(Protocol): ...
class InstallVerifier(Protocol): ...
```

Fresh installation:

```text
verify signed release
-> create layout
-> write base release to SYSTEM_A
-> finalize SYSTEM_A for actual hardware
-> verify slot and boot artifacts
-> leave SYSTEM_B inactive/invalid
-> initialize PERSIST
-> install boot backend with A as default
-> first boot
-> accept A only after normal Greia health
```

There is no reason to copy the initial release into B just to duplicate install time and wear.

---

# 7. Reconcile ADR 0021 hardware enablement with A/B updates

ADR 0021 correctly keeps installer media broad while installing only hardware support the actual machine needs. A/B updates correctly replace whole system slots. Those two rules conflict unless machine-specific hardware finalization is reusable.

Introduce one platform-owned `SlotFinalizer` used by both installer and updater.

The signed release contract must bind the release-scoped Hardware Support Pool used for finalization, directly or through an exact signed member inventory. The planned `.greiaupdate` v2 schema must therefore bind at least:

```text
base system-slot payload digest
hardware-support pool digest/schema
allowed automatic package classes
```

Exact bundle layout remains source-owned by `src/greia_platform/system_updates.py`; do not create an installer-only trust format.

The finalizer may only:

1. mount the new/inactive slot;
2. resolve support through the current vendor-neutral hardware inventory;
3. install approved firmware/microcode classes from the release-bound pool;
4. apply profile-owned host configuration;
5. regenerate candidate-local initramfs/boot artifacts where required;
6. write a bounded finalization receipt.

Receipt should bind release ID, base payload digest, support-pool digest, hardware inventory token, exact installed package/version/digests, finalizer version and resulting generic/host initramfs identities.

A future update follows the same pipeline for inactive B. If required hardware support cannot be resolved/finalized before candidate activation, do not arm the candidate; keep the accepted slot.

---

# 8. Installed layout authority

Every installed system gets a root-owned machine-readable layout record in persistent platform state. It identifies semantic roles with stable PARTUUID/UUID plus the expected disk identity:

```text
schema_version
layout_id
platform_family
boot_backend
whole-disk identity
boot-control role(s)
system A
system B
persistent
slot size
accepted slot
```

Updater and boot services never guess writable partitions by partition number or Parent input.

---

# 9. Legacy BIOS x86 target layout

For the legacy reference where MBR remains the physically proven installed-disk format:

```text
MBR + >=1 MiB GRUB embedding space
P1 GREIA_BOOT_CONTROL   small ext4, active
P2 GREIA_SYSTEM_A       fixed ext4
P3 GREIA_SYSTEM_B       fixed ext4
P4 GREIA_PERSIST        ext4 remainder
```

`BOOT_CONTROL` owns stable GRUB configuration/environment outside both replaceable system slots. Each system slot carries its own kernel and generic initramfs under `/boot`.

The fact that removable USB GRUB failed on the reference Acer does **not** imply internal-disk GRUB is invalid; the accepted postmortem explicitly distinguishes those paths.

Candidate update:

```text
accepted/default = A
GRUB next_entry  = B
```

`BOOT_HEALTHY` promotes B to persistent default. If B never becomes healthy, consumed one-shot selection means the next boot remains A.

Before promotion, prove on Acer:

- the exact A/B target layout boots;
- GRUB environment writes are reliable;
- kernel/root-mount failure returns to A;
- the measured minimum storage still leaves an acceptable PERSIST budget.

Partition sizes are declarative profile data, not hardcoded Acer constants.

---

# 10. Modern amd64 target layout

Use GPT:

```text
P1 GREIA_BIOS_BOOT      BIOS Boot partition
P2 GREIA_ESP            FAT32
P3 GREIA_BOOT_CONTROL   small ext4
P4 GREIA_SYSTEM_A       fixed ext4
P5 GREIA_SYSTEM_B       fixed ext4
P6 GREIA_PERSIST        ext4 remainder
```

The BIOS Boot partition permits deliberate BIOS fallback where supported. ESP owns the signed UEFI chain. Stable GRUB config/environment remains outside replaceable A/B roots.

Modern release acceptance must prove:

```text
Secure Boot ON
-> trusted shim
-> signed GRUB
-> signed kernel
-> Greia
```

and Secure Boot OFF, using the exact release image.

Do not infer target boot policy solely from CPU architecture; record whether the installer itself booted through BIOS or UEFI and have the modern adapter deliberately install/verify its supported target paths.

---

# 11. Raspberry Pi 400 / Pi 500 target layout and boot transaction

Use Raspberry Pi native firmware A/B semantics rather than GRUB.

Because Pi `tryboot` / `autoboot` has had real partition-table/boot-control edge cases, the first installed Pi A/B candidate deliberately uses an MBR/DOS table until Pi 400 + Pi 500 physical evidence justifies changing it:

```text
P1 GREIA_PI_BOOT_CONTROL   FAT32
P2 GREIA_PI_BOOT_A         FAT32
P3 GREIA_PI_BOOT_B         FAT32
P4 extended container
   P5 GREIA_SYSTEM_A       ext4
   P6 GREIA_SYSTEM_B       ext4
   P7 GREIA_PERSIST        ext4
```

Initial semantic boot contract:

```text
[all]
tryboot_a_b=1
boot_partition=2

[tryboot]
boot_partition=3
```

A is accepted. B is the one-shot candidate. BOOT_B points to SYSTEM_B.

Candidate update:

```text
write/finalize SYSTEM_B
-> stage and verify BOOT_B
-> arm one-shot tryboot
-> reboot in tryboot mode
```

If B fails before `BOOT_HEALTHY`, the one-shot state must clear so normal boot returns to accepted A.

If B becomes healthy:

```text
persist Greia accepted-slot state
-> durable-write new autoboot mapping
-> verify boot-control bytes
-> B becomes default
-> A becomes rollback candidate
```

The `autoboot.txt` commit is **not** described as atomic merely because a rename succeeded.

The implementation must use a bounded durable-write primitive equivalent to:

```text
write temporary file
fsync(file)
rename
fsync(directory where supported)
syncfs(boot-control filesystem)
re-read
verify exact content
```

Then fault-test at every boundary.

Required Pi recovery evidence includes:

- missing `autoboot.txt`;
- zero-length/truncated `autoboot.txt`;
- syntactically corrupt boot control;
- power loss before rename;
- power loss after rename but before final sync/verification;
- corrupt BOOT_B;
- corrupt SYSTEM_B;
- candidate kernel failure;
- candidate userspace failure;
- partition-walk/recovery behavior with the exact EEPROM/firmware state.

Before erasing a Pi target, prove required one-shot A/B and recovery capabilities. Missing/unknown capability blocks the update-capable installation profile before erase. Routine installation/update does not silently rewrite EEPROM.

---

# 12. Pi boot files are release-bound

Pi firmware cannot consume the system-slot kernel exactly as GRUB does from ext4, so the Pi boot adapter stages signed release boot content into the inactive BOOT_A/B FAT partition.

Before arming tryboot, verify the candidate root and boot partition together:

```text
SYSTEM_B release identity
BOOT_B kernel digest
BOOT_B initramfs digest
BOOT_B DTB/overlay digests
BOOT_B config/cmdline generated-contract digest
```

A failed candidate never mutates BOOT_A or SYSTEM_A.

---

# 13. Persistent storage contract

`GREIA_PERSIST` owns shared mutable state, including at minimum:

- Parent credentials/pairing state;
- child profiles;
- Activity saves/creations;
- progression/rewards/awards;
- device settings;
- hardware inventory/finalization receipts;
- system-update and release-acceptance state;
- layout authority;
- bounded logs/evidence and update inbox state where architecture requires it.

Routine slot replacement never owns this data. Before candidate confirmation, shared-state migration must remain backward-readable or transactional so the previously accepted slot can still recover.

---

# 14. Declarative storage/profile extensions

Extend the existing TOML profile schema instead of hardcoding platform branches in shell/Python.

Illustrative fields:

```toml
[storage]
layout_adapter = "legacy-bios-ab-v1"
system_slot_bytes = 0
persistent_minimum_bytes = 0

[installer]
target_policy = "pc-internal-v1"
live_memory_class = "c0-bounded-overlay-v1"

[updates]
backend = "grub-ab-v1"
required = true
```

Pi selects a Pi layout/target/tryboot backend. `tools/build_profile.py` remains the typed parser/validator.

Minimum target bytes are calculated from complete layout overhead + two slots + persistent minimum + reserve/alignment. There is no universal `4 GiB` target constant.

Live-memory limits are likewise profile/build facts derived from measurement, not model-name conditionals buried in Python.

---

# 15. Live installer RAM and writable-overlay budget

The live installer is an appliance, not a general Debian live desktop.

For the lowest supported class:

```text
toram = forbidden
persistent overlay = forbidden for ordinary Setup flow
compressed root = read from Setup medium
writable overlay = bounded tmpfs
```

The current legacy boot contract's explicit `overlay-size=128M` is the starting point for measurement.

R8 must produce an exact-image resource report on the physical reference during:

1. boot to first installer frame;
2. idle installer;
3. hardware inventory/refresh;
4. settings pages;
5. release verification;
6. target planning;
7. write/finalization/verification;
8. completion page.

Record at least:

```text
MemTotal
MemAvailable minimum
swap state
tmpfs/overlay configured ceiling
tmpfs/overlay peak actual use
installer process RSS peak
installer process anonymous peak
largest child/helper RSS peak
OOM/pressure events
```

A release budget is accepted only after measurement. Do not hard-code an arbitrary 64 MiB overlay or 120 MiB idle threshold merely because it sounds conservative.

If the exact universal image regresses materially versus the already-working installer path, stop and fix the live composition before adding more platform payloads.

---

# 16. Setup-media size and deduplication

Do not promise `~2.1 GB` or `4 GB USB` from estimates.

The release builder reports measured:

- raw image bytes;
- compressed download bytes;
- each live root;
- each release bundle;
- each hardware-support pool;
- FAT boot partition use/free headroom;
- Setup-data partition use/free headroom;
- duplicate-content estimate.

The product's minimum flash-device capacity is derived from the actual raw image plus explicit margin.

Correctness and one signed release authority come before deduplication. Initial universal media may carry compressed per-profile artifacts even when some Activity/audio content duplicates. Add cross-bundle content-addressed deduplication only after measurement proves it worthwhile.

---

# 17. Setup-media manifest and identity

The setup image has its own bounded signed/verified manifest binding:

```text
media schema/release ID
boot assets
supported live architectures
live roots
release bundles
hardware-support pools
size + SHA-256 for each authoritative member
```

Verify it before enabling installation.

This detects corruption/partial copies and creates the installable profile catalogue, but it does not replace independent `.greiaupdate` release signatures.

For the two-partition Setup-media candidate, boot-partition metadata and Setup-data identity must resolve to the same physical medium and signed media identity. Labels are hints only.

The existing `greia.live_media_id` mechanism should be preserved/evolved rather than replaced by a plain `LABEL=` lookup.

---

# 18. Privilege-separated transaction service

Target services conceptually become:

```text
greia-installer-ui.service          User=unprivileged installer identity
        |
        v
greia-install-transaction.socket
        |
        v
greia-install-transaction.service   User=root, one-shot/socket-activated
```

The UI sends only semantic data such as expected target identity, chosen eligible profile ID, approved settings and confirmation-plan digest.

The root service resolves media artifact, actual target device, layout adapter, boot adapter and support pool from Greia-owned verified state.

Immediately before the first irreversible command it rechecks:

- setup-medium physical identity;
- target durable identity and eligibility;
- target capacity and mount/storage-stack state;
- signed release and profile compatibility;
- complete hardware-support plan;
- power safety;
- layout feasibility.

Any failure returns to UI without disk mutation.

---

# 19. Common installer transaction stages

Refactor the current BIOS-specific engine around semantic stages rather than a giant platform switch:

```text
DISCOVER
VERIFY_SETUP_MEDIA
PROBE_HOST
SELECT_PROFILE
PROBE_TARGETS
SELECT_TARGET
PLAN
USER_CONFIRM
PRIVILEGED_REVERIFY
ERASE
CREATE_LAYOUT
WRITE_SYSTEM_A
FINALIZE_SYSTEM_A
INITIALIZE_SYSTEM_B
INITIALIZE_PERSIST
INSTALL_BOOT_BACKEND
WRITE_LAYOUT_AUTHORITY
VERIFY
SYNC
COMPLETE
```

Platform adapters implement only the mechanics that genuinely differ.

---

# 20. Existing single-root installations

Do not remotely repartition them through ordinary system update.

Migration policy:

```text
single-root Greia
-> system.update.activate=false
-> Parent explains update-capable reinstall/migration is required
-> boot-tested Greia Setup media
-> backup portable Greia state
-> destructive reinstall into proven A/B layout
-> restore compatible state
-> verify
```

Any future in-place repartitioner is a separate recovery/installer project with physical recovery requirements. The current working Acer must not be the first experiment.

---

# 21. Recovery direction

The same setup image is the first recovery medium. Its architecture must permit later explicit transactions such as:

```text
reinstall and erase
repair boot
restore system while preserving child data
restore .greiabackup
diagnostics
```

Those are not all required in the first R8 implementation, but A/B roots, separate PERSIST, signed releases, layout authority and boot-backend repair seams must not prevent them.

---

# 22. Implementation sequence

## R8.0 — Reconcile authorities

Before destructive code:

1. reconcile ADR 0021 + ADR 0030 around shared `SlotFinalizer`;
2. define `.greiaupdate` v2 hardware-support binding alongside the planned release-sequence/anti-rollback work;
3. extend profile schema for storage layout, update backend and live-memory class;
4. define typed layout, slot, target-policy and boot-transaction interfaces;
5. preserve current installer safety tests;
6. preserve the accepted removable Acer SYSLINUX path as a regression authority.

Gate: documentation/schema/source contracts only; `make verify` green before destructive behavior changes.

## R8.1 — Target identity + privilege split

Implement durable identity, live-media ancestry self-exclusion, target-policy adapters, refresh generations/selection invalidation and unprivileged UI -> privileged local installer service. Test with synthetic/loop devices.

## R8.2 — Common A/B transaction model

Implement storage roles/layout authority, slot writer, shared SlotFinalizer, receipts and loopback fault injection.

## R8.3 — Legacy BIOS A/B installed target

Implement MBR boot-control + A + B + PERSIST and GRUB one-shot candidate behavior. QEMU first, then physical Acer with boot-tested recovery media.

Do not conflate this internal-disk GRUB work with the removable Setup-media SYSLINUX requirement.

## R8.4 — Modern amd64 A/B

Implement GPT/ESP/boot-control/A/B/PERSIST and Secure-Boot-compatible UEFI chain. Test OVMF, Secure Boot, SATA and NVMe before physical modern reference evidence.

## R8.5 — Pi ARM64 board/live adapters + hotplug gate

Implement arm64 live root, typed BCM2711/Pi400 and BCM2712/Pi500 boot assets, exact device-tree compatibility, EEPROM capability probe and Pi microSD target policy.

Before accepting the preferred parent workflow, physically prove on **both** Pi 400 and Pi 500:

```text
USB boot with target card absent
-> hot insert target card
-> kernel/udev block event
-> /dev block device
-> durable MMC identity
-> Refresh Drives inventory update
-> correct target-policy classification
```

If this fails, stop and resolve the product boot/insert workflow before destructive Pi implementation.

## R8.6 — Pi tryboot A/B

Implement candidate MBR Pi layout, inactive boot+root pair staging, verification, one-shot tryboot, health commit and rollback/fault tests.

Required source/physical work includes a dedicated boot-control durability primitive and power-cut injection around `autoboot.txt`.

Physical Pi 400 + Pi 500 evidence is mandatory, including proven partition-walk/recovery behavior.

## R8.7 — Universal media composer

Only after individual adapters work independently, compose one exact MBR-based media image whose first boot partition preserves the accepted active-FAT32 + SYSLINUX legacy path while also carrying signed UEFI removable boot and Pi boot assets.

The data partition carries live roots, signed releases, support pools and the signed setup-media manifest.

Do not switch the Acer lane back to GRUB merely to make the media layout look uniform.

## R8.8 — Exact-image boot + low-memory matrix

One exact setup-image hash must boot:

```text
Acer legacy BIOS
modern amd64 UEFI / Secure Boot OFF
modern amd64 UEFI / Secure Boot ON
Pi 400 EEPROM USB
Pi 500 EEPROM USB
```

No per-test rebuilds.

On the exact same image, execute the C0 live-memory measurement lane. `toram` must remain absent. A low-memory regression blocks acceptance even if boot succeeds.

The Acer firmware/bootloader lane requires direct physical observation. A pre-kernel firmware hang cannot be accepted or diagnosed merely because SSH later works on a different boot path.

## R8.9 — Install + update/rollback matrix

From that exact image:

```text
Acer -> internal disk -> A/B -> boot A
modern amd64 -> SATA/NVMe -> A/B -> boot A
Pi 400 -> microSD -> Pi A/B -> boot A
Pi 500 -> microSD -> Pi A/B -> boot A
```

Then execute one successful update and one deliberately failed candidate rollback on each boot-backend family.

## R8.10 — Interruption/fault testing

Inject faults during:

```text
payload verification
target confirmation
partitioning
SYSTEM_A write
finalization
boot-control creation
final sync
later SYSTEM_B update
candidate selection
pre-BOOT_HEALTHY boot
Pi autoboot temporary write
Pi autoboot fsync/rename/syncfs/verify boundaries
```

Fresh-install failure may leave the selected target uninstalled; it must never damage setup media or another disk.

Update failure must retain the previously accepted system.

On Pi, FAT boot-control write discipline by itself is not sufficient evidence; prove recovery from malformed/missing/truncated control state and abrupt power removal.

---

# 23. Permanent regression guards

Source validation should reject:

- a release profile with single-root layout and `updates.required=true`;
- an update backend without A/B semantic roles;
- unknown ARM auto-mapped to a known Pi;
- direct model-string package/profile selection;
- ordinary UI accepting a raw target path as authority;
- target selection stored only by list index;
- setup-media label used as sole self-exclusion authority;
- global `allow_mmc=True` eligibility shortcuts;
- direct root block writes from the graphical UI module;
- arbitrary shell/command execution through installer protocol;
- a second installer-only system tar/payload authority;
- installer/update compatibility engines diverging;
- Pi 400/500 sharing a fake single firmware recipe;
- Pi update backend implemented through GRUB;
- modern-amd64 release claims without Secure Boot evidence;
- activation on existing `bios-single-ext4` layouts;
- hardware finalization mutating the active/accepted slot;
- candidate acceptance before `BOOT_HEALTHY`;
- `toram` in the low-memory release Setup profile;
- an unbounded/default live writable-overlay policy on the C0 profile;
- the universal-media composer replacing the accepted legacy removable SYSLINUX path with GRUB without new physical acceptance;
- Pi parent-flow documentation claiming hot insertion before Pi 400 and Pi 500 evidence exists;
- Pi boot-control code treating FAT rename as transactional/atomic rollback authority;
- Pi update activation without proven required one-shot/recovery capability.

---

# 24. Local-agent stop conditions

STOP before destructive work if any occurs:

1. setup-media physical ancestor cannot be uniquely identified;
2. target identity changes after selection;
3. target is selected only by `/dev` path;
4. Pi profile depends on an unknown-board fallback;
5. ordinary UI can force an incompatible profile;
6. target does not fit complete A/B + persistent layout;
7. platform boot backend cannot prove rollback;
8. required Pi tryboot/recovery capability is unavailable, unknown or unproven;
9. Secure Boot is being disabled merely to make a modern release claim;
10. active/accepted system slot would be overwritten;
11. a single-root existing machine is about to be repartitioned as ordinary update;
12. unsigned/untrusted hardware support is required;
13. required hardware support cannot be resolved before erase/candidate activation;
14. installer and updater have diverged slot/payload writers;
15. UI has gained arbitrary root/shell authority;
16. setup media is considered eligible target storage;
17. removable USB storage is selected in ordinary PC policy;
18. ordinary Pi 500 is offered Pi-500+-style internal NVMe;
19. media-size requirements are still estimates;
20. physical evidence comes from a different image SHA;
21. low-memory live profile uses `toram`;
22. the universal Setup candidate abandons active-FAT32/SYSLINUX on the Acer without explicit replacement physical evidence;
23. the Pi ordinary flow assumes microSD hotplug but either Pi 400 or Pi 500 has not passed the exact-image hotplug gate;
24. a FAT32 rename is being described as power-loss atomic;
25. Pi recovery depends on partition-walk/tryboot behavior that has not been physically proven on the exact firmware state.

---

# 25. Product flow

## PC

```text
Download one Greia Setup image
-> flash USB
-> boot USB
-> Greia detects compatible computer
-> choose eligible internal storage
-> review normal keyboard/pointer/display/settings pages
-> Hold to Install
-> Greia creates A/B + persistent system
-> remove USB
-> boot Greia
```

The same image reaches the installer through different low-level boot adapters:

```text
legacy BIOS removable -> MBR + active FAT32 + SYSLINUX
modern UEFI removable -> signed removable UEFI path on the FAT partition
```

Parents do not see that distinction.

## Pi 400 / Pi 500

Subject to the boot-order/hot-insertion physical gate:

```text
Download the same Greia Setup image
-> flash USB
-> boot Pi from USB
-> insert target microSD if required by boot order
-> Refresh Drives
-> choose eligible microSD
-> Hold to Install
-> Greia creates Pi-native tryboot A/B + persistent layout
-> remove USB
-> boot Greia
```

No `dd`, partition editor, shell, `raspi-config`, GRUB, EEPROM or raw firmware vocabulary belongs in the ordinary parent flow.

---

# 26. Definition of complete

Universal setup is complete only when all are simultaneously true:

```text
one exact setup-image hash boots every supported reference
AND the removable legacy-BIOS path preserves or supersedes the physically
    accepted active-FAT32/SYSLINUX behavior with explicit physical evidence
AND the C0 live installer does not use toram
AND exact-image C0 memory/overlay budgets are measured and accepted
AND setup media can never be selected as target
AND target identity survives refresh/re-probe safely
AND profile selection has no unsafe fallback
AND Pi 400 and Pi 500 hot-insertion behavior is either physically proven
    for the product flow or replaced by another proven parent-safe flow
AND every new release installation is A/B-capable
AND persistent child/Parent data is outside replaceable slots
AND installer and updater share release/slot authority
AND x86 one-shot rollback is physically proven
AND Pi one-shot rollback is physically proven
AND Pi FAT boot-control power-cut recovery is physically proven
AND Pi partition-walk/recovery behavior is physically proven
AND modern Secure Boot is physically proven
AND machine-specific hardware support survives future slot updates
AND install + successful update + forced rollback are proven on
    physical Acer + modern amd64 + Pi 400 + Pi 500
```

The architecture is not complete merely because all source tests pass. Boot firmware, removable-media behavior, low-memory live operation, Pi card insertion and power-loss recovery are physical acceptance lanes.
