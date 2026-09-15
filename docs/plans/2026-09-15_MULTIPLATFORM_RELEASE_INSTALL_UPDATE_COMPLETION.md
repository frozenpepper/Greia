# Greia — Final Multiplatform Release / Universal Installer / Update Completion Plan

**Status:** ACTIVE — authoritative successor plan  
**Created:** 2026-09-15  
**Owner requirement:** one universal Greia Setup image is mandatory  
**Architecture:** ADR 0036 (owner-corrected simple lifecycle architecture)  
**Execution style:** direct implementation -> focused tests -> full verification at sensible milestones -> QEMU/physical tests only when useful  
**Explicit process rule:** do not add security/governance machinery unless it prevents a real product failure.

---

# 0. Goal

Finish this workstream and stop reopening it.

Greia must end with a release/update/install system that is easy for both the project owner and normal parents:

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
            successful boot -> keep
            failed boot     -> rollback
```

Supported first-class targets at completion:

```text
Acer Aspire One / legacy i386 BIOS
modern amd64 UEFI PC
Raspberry Pi 400 / arm64
Raspberry Pi 500 / arm64
```

ARM64 is a first-class build/runtime architecture. Pi 400/500 are the first supported ARM boards, implemented through board adapters rather than a Pi-only fork.

---

# 1. Decisions are closed

Workers implementing this plan do **not** redesign these decisions.

## A1 — One universal Setup image is a hard requirement

There is one public installer artifact:

```text
greia-setup-<version>.img
```

The same image contains the boot paths and live roots required for legacy BIOS, x86-64 UEFI, Pi 400 and Pi 500.

No separate public PC installer image, Pi 400 image or Pi 500 image is allowed as a replacement for this requirement.

### Why

This is the product experience the owner wants: one image to download/flash, irrespective of Greia hardware.

The correct implementation is not one common bootloader. It is one **container image with several small firmware-specific boot paths**.

---

## A2 — No hostile-tamper architecture

Greia does not protect release files from an owner/developer intentionally modifying them.

Remove or retire from the normal release/update path:

```text
release signing keys
manifest signatures
public-key trust stores for Greia releases
anti-tamper authorization
hash-equality as release authority
cryptographic anti-rollback sequencing
"trusted artifact" governance ceremonies
```

A checksum may exist only as an ordinary corruption/debugging aid. It cannot become a trust/permission system.

### Why

The real threats here are bad builds, wrong-device erasure, interrupted writes and failed boots. Manual file tampering is not a product threat worth architectural complexity.

---

## A3 — `.greiaupdate` stays, but becomes simple

Use `.greiaupdate` as the portable update container.

The new simple bundle format contains:

```text
manifest.json
payload.bin
hardware-support member(s) only where current finalization requires them
```

The manifest contains only useful compatibility/build facts:

```text
format_version
Greia version
profile id
architecture
platform / board compatibility
payload size
optional corruption checksum
```

No signature member. No signer identity. No key id.

Because Greia is still pre-release, do not build a compatibility maze for the existing signed experimental format. Introduce one simplified format version, update all current producers/consumers, and reject the old experimental format with a clear message.

### Why

A clean one-time format break is simpler than indefinitely carrying machinery that the product does not need.

---

## A4 — The update payload is the complete OS

`payload.bin` is a complete relocatable system-slot filesystem image.

It must already contain the Greia base OS. The finalizer may add machine-specific firmware/microcode and boot artifacts; it does not construct Debian/Greia from an empty filesystem.

The V12G 64 MiB payload was the wrong artifact, not evidence that the installer should learn how to build an OS during installation.

### Why

This makes fresh install, update and rollback understandable and keeps one composition path.

---

## A5 — One rootfs composer

There is one rootfs composition implementation for every architecture.

Refactor the current target build into reusable code/primitives that accept a declarative build profile and produce a complete target root.

The same composer is used for:

```text
i386 Greia
amd64 Greia
arm64 Greia
system-slot images
live installer roots
raw developer/test images
```

Architecture-specific differences belong in profile data and adapters, not copied build scripts.

### Why

D6 happened because two artifacts called “the system” were built independently. This decision eliminates that class of bug.

---

## A6 — A/B is the only normal update model

New supported installs use:

```text
system A
system B
PERSIST
boot-selection state
```

Update always writes the inactive slot.

Example:

```text
running A
-> write new release to B
-> finalize B
-> boot B once
-> Greia usable: commit B
-> Greia broken: boot A again
```

PERSIST survives both updates and rollback.

### Why

A/B is simple operationally and solves the failures that matter: interrupted update and bad release.

---

## A7 — User data is not part of system slots

PERSIST owns durable child/Parent state:

```text
profiles
Activity saves/creations
progression/rewards
Parent settings/auth data
system preferences intended to survive OS replacement
```

System A/B contains replaceable OS/runtime content.

Any data migration performed before a new candidate is accepted must remain readable by the previous release or be deferred until after acceptance.

### Why

Rollback is useless if the new OS irreversibly mutates the only copy of user data before proving it works.

---

## A8 — Keep one common installer/update writer/finalizer

Continue the existing `SlotWriter` / `SlotFinalizer` direction.

Fresh install and update both do the same fundamental thing:

```text
write complete slot image
-> mount
-> machine-specific finalization
-> boot artifacts
-> basic verification
```

Do not create separate Pi, PC, installer and updater copies of this logic.

### Why

Only partition layout and boot selection genuinely differ by platform.

---

## A9 — Keep hardware finalization offline

The release/system bundle contains everything required to install/update without Internet access.

The existing bounded offline package support mechanism may continue to use `apt-get` inside the candidate root while that is the simplest implementation.

No network APT is used during normal install/update.

### Why

Offline install/update is predictable and matches Greia’s appliance model.

---

## A10 — Universal Setup image layout

Use one MBR-based compatibility image:

```text
P1  FAT32  GREIA_SETUP_BOOT  active
P2  ext4   GREIA_SETUP_DATA
```

### P1 contains

```text
legacy BIOS / SYSLINUX loader
legacy i386 installer kernel + initramfs
EFI/BOOT/BOOTX64.EFI and amd64 installer boot files
Pi 400 firmware / board boot files
Pi 500 firmware / board boot files
small common setup configuration
```

### P2 contains

```text
live/i386/rootfs.squashfs
live/amd64/rootfs.squashfs
live/arm64/rootfs.squashfs
releases/acer-aspire-one-i386-ab.greiaupdate
releases/standard-amd64-ab.greiaupdate
releases/raspberry-pi-400-arm64-ab.greiaupdate
releases/raspberry-pi-500-arm64-ab.greiaupdate
```

P2 is ext4. Firmware never needs to read it; the kernel/initramfs mounts it after boot.

### Why

- FAT32 P1 works for Pi firmware and UEFI and preserves the already-working Acer removable-media primitive.
- Large live roots/releases do not need to fit in FAT32.
- One image can contain all platforms without forcing one bootloader onto all of them.

---

## A11 — Legacy Setup USB boot stays SYSLINUX

Do not replace the proven Acer removable boot path just for symmetry.

```text
MBR
-> active FAT32
-> SYSLINUX
-> i386 installer kernel/initramfs
```

Installed legacy x86 may still use GRUB for A/B boot selection.

### Why

The removable Acer path is already physically known to work. There is no benefit in reopening it.

---

## A12 — Modern PC Setup boot is ordinary UEFI

The same P1 carries x86-64 UEFI removable boot files under `EFI/BOOT`.

Modern Greia requires normal UEFI boot. Secure Boot certification is **not** a blocker for this lifecycle plan unless the owner later explicitly promotes it to a release requirement.

### Why

We need modern hardware support, not another security project.

---

## A13 — Pi 400 and Pi 500 are distinct board adapters

Profiles:

```text
raspberry-pi-400-arm64-ab
raspberry-pi-500-arm64-ab
```

Shared:

```text
arm64 base/rootfs
Greia runtime
Activities
installer application
update service
A/B semantics
```

Board adapter owns:

```text
firmware files
kernel/DTB choice
config.txt fragments/board filters
installed boot-partition asset generation
board detection
```

Do not pretend Pi 400 and Pi 500 are the same boot generation.

### Why

This is the clean path to real ARM support without duplicating Greia itself.

---

## A14 — ARM64 is generic in architecture, Pi-specific only in adapters

Core architecture is `arm64`, not `raspberry-pi`.

Define/retain polymorphic seams such as:

```text
BuildProfile
BoardAdapter
LayoutAdapter
BootBackend
LiveBootAdapter
InstallTargetPolicy
```

Pi 400/500 are registered implementations.

A future ARM board adds a profile + board/boot adapters; it does not fork the installer/updater/rootfs composer.

### Why

The user explicitly requires ARM support, not merely a one-off Pi hack.

---

## A15 — Pi installed layout uses native tryboot

Use:

```text
pi-mbr-tryboot-ab-v1
pi-tryboot-ab-v1
```

Installed target:

```text
P1 FAT32 boot-control
P2 FAT32 boot-A
P3 FAT32 boot-B
P4 extended container where required
P5 ext4 system-A
P6 ext4 system-B
P7 ext4 PERSIST
```

Use Raspberry Pi firmware `tryboot` / `autoboot.txt` for one-shot candidate selection.

No GRUB or U-Boot on Pi just to look like x86.

Routine Greia install/update does not rewrite EEPROM settings.

### Why

The Pi firmware already provides the A/B primitive we need.

---

## A16 — Installed x86 layouts

### Legacy i386

```text
MBR
boot-control
system A
system B
PERSIST
GRUB A/B backend
```

Slot size decision:

```text
system A: 1536 MiB
system B: 1536 MiB
PERSIST: remainder, minimum 512 MiB
```

### Modern amd64

```text
GPT
ESP: 256 MiB
boot-control: 64 MiB
system A: 2048 MiB
system B: 2048 MiB
PERSIST: remainder, minimum 1024 MiB
GRUB UEFI A/B backend
```

### Pi 400 / 500

```text
boot-control: 64 MiB FAT32
boot A: 128 MiB FAT32
boot B: 128 MiB FAT32
system A: 2048 MiB
system B: 2048 MiB
PERSIST: remainder, minimum 1024 MiB
```

These values are product defaults. A later footprint optimization may reduce them, but implementation workers do not invent different sizes per session.

### Why

The Acer root is currently near 1 GiB, so 1.5 GiB slots give useful headroom while fitting the reference storage. Modern/Pi media can afford 2 GiB slots.

---

## A17 — Setup-media self-protection is simple

The installer must not erase the USB it is running from.

At startup, determine the actual block device containing mounted `GREIA_SETUP_DATA`, resolve its parent whole-disk device, and exclude that disk from install targets.

Immediately before erase, re-read:

```text
target path
major:minor
capacity
serial/CID when available
```

If the selected device disappeared or changed, require reselection.

No signed device identity, no cryptographic device authority, no elaborate persistence model.

### Why

Wrong-disk erasure is a real risk; malicious device impersonation is not a product concern here.

---

## A18 — One graphical installer application

The same Greia installer package/UI runs in i386, amd64 and arm64 live roots.

The UI flow stays simple:

```text
Welcome
-> detected hardware/profile
-> choose eligible target disk
-> erase/install confirmation
-> progress
-> complete/reboot
```

Platform adapters supply layout/boot mechanics underneath it.

The installer does not expose partitions, package managers or Linux shell concepts to parents.

### Why

Multiplatform support must stay below the product UI.

---

## A19 — Parent update UX is intentionally boring

Initial Parent flow:

```text
System Update
-> Choose .greiaupdate
-> show Greia version and target profile
-> upload
-> Preparing update
-> Ready to Restart
-> Restart & Update
-> Updated
```

If candidate boot fails:

```text
Greia restored the previous version.
```

If an older version is selected, show a warning and allow the parent/developer to proceed explicitly.

No keys, certificates, signatures, raw slots or package-manager terminology.

### Why

The Parent app should control the appliance, not explain Linux update internals.

---

## A20 — One owner-facing release command

Create `tools/greia_release.py` as the normal build entry point.

Normal production build:

```bash
sudo python3 tools/greia_release.py build \
  --version <VERSION> \
  --output <DIR>
```

That command:

1. checks build-host prerequisites;
2. builds all supported profile roots;
3. creates each `.greiaupdate`;
4. creates i386/amd64/arm64 live roots;
5. composes the one universal Setup image;
6. writes a small human/machine-readable build report.

Developer helpers may exist:

```text
doctor
build-profile
build-live-root
build-setup-image
inspect
```

but the owner does not need to run them for a normal release.

### Why

The release process itself must be simpler than the architecture it drives.

---

## A21 — Build host

Official builder: x86_64 Linux.

It builds:

```text
i386 natively/chroot-compatible
amd64 natively
arm64 with qemu-aarch64-static + binfmt when chroot execution is required
```

No Docker/VM requirement.

`doctor` checks only practical prerequisites: tools, disk space, root privileges required for image/loop work, qemu/binfmt for ARM, package repositories and profile validity.

### Why

One normal Linux build machine should produce the entire product.

---

## A22 — Testing is for finding bugs, not creating gates

Use:

```text
focused source tests during implementation
make verify at major session boundaries
mounted-artifact smoke tests before QEMU
QEMU/loop lifecycle tests for software behavior
physical machines only for real firmware/hardware behavior
```

Do not create new gate hierarchies, evidence tokens, immutable attempt directories, signed reports, artifact identity rituals or orchestration frameworks as part of this plan.

### Why

The current workstream has already lost too much time to process instead of product.

---

# 2. Final release output

A normal build output is intentionally small and understandable:

```text
out/greia-<version>/
  release-report.json
  greia-setup-<version>.img

  updates/
    acer-aspire-one-i386-ab.greiaupdate
    standard-amd64-ab.greiaupdate
    raspberry-pi-400-arm64-ab.greiaupdate
    raspberry-pi-500-arm64-ab.greiaupdate
```

Optional developer/debug intermediates may live below an `intermediate/` directory and are not user-facing release artifacts.

Optional checksums may be emitted as convenience for transfer troubleshooting, but nothing in the updater/install architecture depends on them as authority.

---

# 3. Universal image boot architecture

The single image has these boot paths:

```text
                     greia-setup.img
                            |
        +-------------------+-------------------+
        |                   |                   |
 legacy BIOS            amd64 UEFI          Raspberry Pi
        |                   |                   |
    SYSLINUX          EFI/BOOT loader     Pi firmware files
        |                   |                   |
 i386 kernel/initrd    amd64 kernel/initrd   arm64 kernel/initrd
        |                   |                   |
        +-------------------+-------------------+
                            |
                 common Greia Setup app
                            |
              detect board/profile/target
                            |
                  install matching bundle
```

All paths use the same P2 data partition after kernel startup.

The live roots contain the same installer code and UI. Only architecture packages/drivers differ.

---

# 4. Fresh install transaction

Common transaction:

```text
1. boot universal Setup image
2. detect platform/profile
3. find eligible target disks
4. exclude Setup USB
5. user selects target
6. recheck target still exists/is same size/device
7. user confirms erase
8. create profile layout
9. format partitions
10. write matching complete release to system A
11. run common finalizer
12. initialize empty system B filesystem
13. initialize PERSIST
14. install/configure platform boot backend
15. set A as normal boot
16. sync
17. reboot
```

System B is not cloned on fresh install. It remains empty until the first update.

### Why

Cloning A wastes install time and storage writes without improving rollback: there is no previous release to roll back to immediately after fresh installation.

---

# 5. Update transaction

Common installed-device transaction:

```text
1. Parent uploads or device obtains .greiaupdate
2. parse manifest
3. verify profile/architecture/board compatibility
4. warn if version is older; allow explicit downgrade
5. mount/inspect payload enough to reject an obviously incomplete OS
6. choose inactive slot
7. write payload
8. run common finalizer
9. generate/update boot assets for inactive slot
10. mark inactive slot as one-shot next boot
11. report Ready to Restart
12. reboot when parent chooses
13. if Greia reaches usable Shell health: commit candidate
14. otherwise boot backend returns to previous slot
```

No step attempts to prove that the parent/developer did not manually edit the update file.

---

# 6. Realistic implementation sessions

Each session is intended for one strong coding LLM. The model is expected to implement, test, fix regressions, update the plan progress and commit coherent work in the same session.

Do not split sessions into bureaucracy-only sub-gates. If a focused test finds a bug, fix the bug and continue.

## Session 01 — Simplify `.greiaupdate` and fix D6 at the source

### Implement

- replace signed experimental bundle contract with the simple bundle from A3;
- remove release-key/signature verification from production update/install path;
- remove or quarantine now-dead key-management code/tests/docs;
- keep only practical manifest/profile/version/size fields;
- factor canonical rootfs composition from `build/build-image.sh` into reusable build primitives;
- create complete relocatable system-slot image from that root;
- add fast completeness smoke validation;
- make a V12G-style minimal filesystem fail that validation;
- keep `SlotWriter` / `SlotFinalizer` as the common consumer;
- update stale routing in `AGENTS.md`, `HANDOVER.md`, `skills/greia-os-work/SKILL.md` so this plan is the current route.

### Reason

This kills both sources of wasted time: the fake minimal system payload and the unnecessary trust machinery.

### Done when

- Acer complete slot builds;
- it contains the real Greia OS and `apt-get` required by current finalization;
- simple `.greiaupdate` can be built/read without keys;
- incomplete payload is rejected immediately;
- current focused update/build tests and `make verify` pass.

Do not run a long physical/QEMU closure until this is green.

---

## Session 02 — One release builder command

### Implement

`tools/greia_release.py` with:

```text
build
doctor
build-profile
inspect
```

`build --version --output` initially builds the existing Acer release completely.

Unify temporary directories, caching, logs and final output layout.

Make `build-installer-image.sh` / other low-level scripts callable implementation details rather than the owner recipe.

### Reason

The build system must be pleasant before multiplying architectures.

### Done when

one command produces a usable Acer `.greiaupdate`, report and all intermediate facts needed by later universal media composition.

---

## Session 03 — Close legacy i386 install/update with the real payload

### Implement / verify

- wire Acer A/B installer to the just-built real `.greiaupdate`;
- remove manual `GREIA_AB_RELEASE_BUNDLE_SRC` production workflow;
- ensure fresh install writes system A and leaves B empty;
- boot installed A;
- apply a second release to B;
- boot/commit B;
- inject one broken candidate and prove return to A;
- fix any remaining product-composition bugs directly.

### Reason

We finish the path that consumed all this time before adding more platforms.

### Done when

legacy i386 performs:

```text
fresh install -> boot -> update -> successful candidate -> bad candidate rollback
```

in QEMU/product mode using the real release path.

The old 9-predicate Gate-P5 document becomes historical evidence; do not invent another successor gate framework.

---

## Session 04 — Universal image composer + legacy/UEFI boot container

### Implement

Create a universal-image composer using the A10 layout.

Implement:

- MBR + active FAT32 P1;
- ext4 P2;
- accepted SYSLINUX legacy boot files;
- amd64 UEFI removable boot files;
- P2 path convention for live roots and updates;
- initramfs logic to locate/mount P2 and exclude the Setup disk from install targets;
- common setup manifest/config needed by the installer, without signatures.

At this point Pi files may be absent, but the **media format is final** and has reserved/typed adapter locations for them.

### Reason

Establish the one-image foundation before adding ARM.

### Done when

one image boots the existing legacy QEMU path and an amd64 UEFI QEMU/OVMF setup path into the same installer application.

---

## Session 05 — Real amd64 profile and installed A/B backend

### Implement

- `standard-amd64-ab` profile;
- amd64 canonical root and `.greiaupdate`;
- `modern-gpt-ab-v1` executable layout adapter;
- GPT/ESP/boot-control/A/B/PERSIST formatting;
- UEFI GRUB A/B backend;
- amd64 live root in universal image;
- generic modern-PC target eligibility.

Do not make Secure Boot part of this session.

### Reason

Get normal modern PCs supported with the same architecture before ARM-specific boot work.

### Done when

universal image can boot under OVMF, install to a virtual modern disk, boot Greia, update inactive slot and roll back a bad candidate.

---

## Session 06 — ARM64 build substrate + common ARM Greia root

### Implement

- make build profiles truly support arm64 in the real composer rather than schema-only support;
- configure x86_64 build host cross-chroot through `qemu-aarch64-static`/binfmt;
- add shared arm64 package sets;
- build common arm64 Greia runtime/Activities;
- create Pi 400 and Pi 500 profiles sharing that root authority;
- add official Raspberry Pi kernel/firmware repository/package configuration required by those profiles;
- keep board-specific boot assembly outside the common root composer.

### Reason

ARM must be a real peer architecture, not a copied Pi build script.

### Done when

both Pi profiles produce complete arm64 slot images and simple `.greiaupdate` files that pass the same completeness checks as x86.

---

## Session 07 — Pi board adapters + universal Setup USB boot

### Implement

- Pi 400 board adapter;
- Pi 500 board adapter;
- board detection from device-tree compatible facts;
- Pi-4/BCM2711 boot asset generation;
- Pi-5/BCM2712 boot asset generation;
- common arm64 live root;
- P1 `config.txt`/board-selection arrangement allowing both board generations to coexist;
- universal image composer inserts both Pi boot asset families;
- arm64 initramfs mounts the same P2 and launches the same installer app;
- Pi target policy offers only the appropriate built-in microSD target and never the Setup USB.

### Reason

This is where the universal image becomes genuinely PC + Pi rather than just a format promise.

### Done when

one generated universal image reaches Greia Setup on both Pi 400 and Pi 500 in physical smoke tests, with correct board/profile detection.

If boot order makes an existing bootable SD take precedence over USB, document the simple recovery insertion procedure; do not create a second image.

---

## Session 08 — Pi destructive layout + native A/B update backend

### Implement

- executable `pi-mbr-tryboot-ab-v1` layout adapter;
- boot-control/boot-A/boot-B/system-A/system-B/PERSIST formatting;
- correct physical partition identity observation;
- boot A on fresh install;
- `pi-tryboot-ab-v1` implementation using Raspberry firmware one-shot candidate semantics;
- copy candidate kernel/initramfs/DTB/firmware assets into inactive boot partition;
- health commit changes normal default;
- failed candidate returns to prior pair;
- bounded handling of interrupted `autoboot.txt` updates without pretending FAT is transactional.

### Reason

Pi should use its own simple native boot mechanism below the same Greia update contract.

### Done when

loop/source tests are green and the implementation is ready for real Pi install/update testing.

---

## Session 09 — Complete universal installer behavior across all four profiles

### Implement

Make the common graphical Setup application fully profile-driven:

```text
Acer -> legacy i386 profile/layout/backend
modern PC -> amd64 profile/layout/backend
Pi 400 -> Pi400 profile/layout/backend
Pi 500 -> Pi500 profile/layout/backend
```

Unify:

- target listing;
- Setup-media exclusion;
- target recheck immediately before erase;
- confirmation/progress/error UI;
- bundle selection from P2;
- common slot writing/finalization;
- reboot/finish UX.

No platform-specific installer screens unless the hardware actually requires different user input.

### Reason

Multiplatform implementation is complete only when the user experience is still one installer.

### Done when

all profile paths can execute from the same Setup codebase and one composed universal image.

---

## Session 10 — Parent update API and Parent-app UX

### Greia repo

- expose simple update status;
- accept local `.greiaupdate` upload;
- parse/show version/profile;
- stage through existing system update service;
- expose progress and `ready_to_restart`;
- perform requested restart;
- report successful update or rollback result.

### Parent repo

Implement a simple System Update panel:

```text
current version
Choose Update File
upload/progress
Preparing
Ready to Restart
Restart & Update
result
```

Older compatible version -> warning + explicit continue.

Remove any UI text/workflow about signing, verification keys, trust roots or artifact authenticity.

### Reason

The normal parent must finally be able to update Greia without a shell or manual disk work.

### Done when

browser upload -> device stage -> restart -> candidate acceptance works end to end on the existing x86 reference path.

---

## Session 11 — Physical Pi 400 and Pi 500 completion

Use the same normal release build and the same universal Setup image.

For **each** Pi:

```text
boot Setup USB
install to target microSD
remove Setup USB
boot Greia
exercise Shell + representative Activities
connect Parent app
upload newer .greiaupdate
stage inactive slot
restart
confirm new release
then stage an intentionally non-booting candidate
confirm previous release returns
confirm user data remains
```

Also test the practical reinstall story when a pre-existing bootable microSD affects USB boot priority.

Fix discovered bugs in source in this session; rerun the affected case.

### Reason

Firmware/board behavior cannot be completed from source inspection alone.

### Done when

Pi 400 and Pi 500 are actually usable Greia machines, not schema entries.

---

## Session 12 — One-image release build + final cleanup

Run the normal owner command from a clean supported Linux build host:

```bash
sudo python3 tools/greia_release.py build --version <candidate> --output <dir>
```

It must produce:

```text
one universal greia-setup image
four profile update bundles
one small release report
```

Then:

- boot/install/update smoke the release on Acer, modern amd64 reference, Pi 400 and Pi 500;
- remove obsolete signed-bundle/key-generation user workflows from docs/tools if no longer used anywhere;
- remove stale split-media instructions;
- make `SETUP.md`, `README.md`, `HANDOVER.md`, the OS skill and architecture docs point to one release workflow;
- preserve historical failure reports as history, not active instructions;
- document old single-root systems as requiring reinstall with the current universal Setup image;
- close this plan.

### Reason

The last session proves the system is actually simpler for the owner, not merely cleaner internally.

---

# 7. Things workers must NOT do

During this plan, do not:

```text
split the public Setup image by platform
reintroduce mandatory release signing
create key-generation/trust-store infrastructure
use hashes as authorization or product identity
grow an anti-tamper threat model
add an anti-rollback security subsystem
mutate the active system slot during normal update
create package-by-package active-root upgrades
create a separate ARM OS builder
create a separate Pi installer application
use GRUB/U-Boot on Pi just for symmetry
make direct DRM work a prerequisite for Pi support
require Docker/VM for release builds
create another T-BAG/gate/orchestrator hierarchy for this plan
create a second installer-only OS payload
turn the Parent browser into a privileged package/disk tool
```

If implementation discovers a real hardware fact that contradicts one of these decisions, report the concrete fact. Do not silently redesign the product.

---

# 8. Definition of complete

This workstream is finished when all of these are true:

```text
ONE universal Setup image is the normal installer for supported Greia hardware

Acer legacy BIOS boots that image and installs Greia
modern amd64 UEFI boots that image and installs Greia
Pi 400 boots that image and installs Greia to microSD
Pi 500 boots that image and installs Greia to microSD

i386, amd64 and arm64 come from one rootfs composition architecture
Pi 400/500 use shared arm64 Greia plus small board adapters

all new supported installs use A/B + PERSIST
fresh install and update consume the same complete system-slot release artifact
Parent app can apply a local .greiaupdate and restart into it
bad update automatically returns to the previous system
user data survives update and rollback

one supported Linux build host can create the complete release with one normal command
no signing-key/trust-chain workflow is required
no worker-facing architecture decision remains open in this lifecycle plan
```

At that point this plan is closed and the team moves on to other Greia release work instead of redesigning installation/update again.
