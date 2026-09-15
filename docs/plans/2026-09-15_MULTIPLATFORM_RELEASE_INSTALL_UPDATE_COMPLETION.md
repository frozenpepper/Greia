# Greia — Multiplatform Release / Install / Update Completion Plan

**Status:** ACTIVE — successor blocking implementation plan  
**Created:** 2026-09-15  
**Owner decision:** finish the lifecycle/release architecture now; no further worker-level architecture forks  
**Current repository baseline:** post-V12G main (`0b045747…`) plus ADR 0036  
**Normative architecture:** ADR 0013, ADR 0014, ADR 0030, **ADR 0036**  
**Historical evidence retained:** `docs/plans/GREIA_GATE_P5_V12G_CLOSURE_DECISION_REPORT_2026-09-15.md`, the August architecture-remediation plan, T-BAG R1 evidence  
**Execution style:** direct implementation -> focused tests -> `make verify` at milestone boundaries -> exact image/physical acceptance only when the code is ready. Do not create a new governance/orchestration layer for this plan.

---

# 0. What this plan finishes

This plan replaces the current D6 decision loop and takes Greia through one coherent lifecycle architecture:

```text
profile-driven complete Greia system
        |
        v
canonical relocatable system-slot image
        |
        v
signed .greiaupdate
        |
        +----------------------+----------------------+
        |                      |                      |
        v                      v                      v
fresh PC install         Parent update          Pi factory media
        |                      |                      |
        v                      v                      v
platform A/B layout      inactive A/B slot       Pi A/B layout
        |                      |                      |
        +----------- trusted health / rollback ------+
```

The target outcome is deliberately practical:

- the owner has one supported command/workflow for building a release matrix;
- each supported profile produces one canonical signed `.greiaupdate`;
- the same release artifact is used for fresh install and subsequent updates;
- PC users can make a normal installer USB;
- Pi 400 / Pi 500 users can flash a ready-to-boot factory image to microSD/USB;
- existing Greia users can upload an update through the Parent app and let Greia stage/restart/rollback safely;
- legacy Acer/i386, modern amd64 and Raspberry Pi arm64 are peers beneath common release/slot contracts;
- no second OS payload factory exists;
- no worker is asked to choose the architecture while implementing it.

---

# 1. Binding architecture decisions — workers must implement these, not reconsider them

## D1 — The release payload is a complete Greia OS

The `.greiaupdate` `payload.bin` is a complete relocatable system-slot filesystem image. It is the base operating system, not a bootstrap filesystem.

The V12G 64 MiB payload containing only `{etc,lost+found,run,var}` was a structurally valid test artifact but an architecturally invalid production release. D6 is repaired on the build/release side.

**Reason:** ADR 0030 already chose whole-system payloads; `SlotWriter` and `SlotFinalizer` already implement that model. Removing `apt-get` from finalization merely to tolerate an empty slot would preserve the wrong artifact and expose a later boot failure.

## D2 — One rootfs composition authority

Refactor target-root creation out of the monolithic x86 `build/build-image.sh` into reusable build primitives. The complete target root for a profile is composed once; disk-image, release-slot and factory-media builders consume that result.

Do **not** create `build-arm-image.sh` by copying the x86 builder. Do **not** create an update-only root builder.

**Reason:** the repository already has declarative profiles and package-set composition. Multiplying builders recreates the exact drift that produced D6.

## D3 — Keep `.greiaupdate` v2 unless a proven missing fact requires change

D6 requires stronger semantic validation, not a new bundle schema. Keep current v2 member names/signature model unless an implementation session demonstrates a fact that cannot be represented without a schema field.

**Reason:** changing a stable signed schema increases migration/test work without solving the composition error.

## D4 — Production bundle creation must prove semantic completeness

`build_update_bundle()` (or the source-owned production path it calls) must reject a relocatable filesystem that is not a complete Greia system slot.

Minimum source-owned checks for a production slot:

- valid ext-family filesystem image, no MBR/GPT;
- embedded profile/build identity exists and exactly matches requested profile/family/architecture/version;
- Greia runtime/source payload is present at the installed canonical location;
- systemd/userspace required by the image exists;
- `python3` and the Greia runtime imports required by the target profile work in a mounted/chroot smoke check;
- `dpkg` and `apt-get` exist while offline package finalization uses them;
- target kernel/initramfs inputs required by the profile exist;
- target `system-update` composition required by an update-capable profile exists;
- package/image manifest is present;
- filesystem bytes fit the declared slot/finalization capacity;
- a deliberately empty/minimal ext4 positive-control is rejected.

These checks belong in shared build/release validation, not only in Gate P5.

**Reason:** expensive QEMU lifecycle tests should not be the first place we learn that the signed OS contains no OS.

## D5 — Keep the existing shared finalizer and offline hardware-support pool

The current `SlotWriter` / `SlotFinalizer` is the common install/update mechanism. Machine-specific firmware/microcode remains a release-bound offline support pool. The current chroot `apt-get` finalization is retained for now.

No network APT is allowed during install/update finalization.

**Reason:** this path is already typed, verified and shared. Once the slot is a real Debian/Greia root, installing a bounded verified offline package set is simple and auditable.

## D6 — One release version/sequence across the build matrix

A release operation takes one Greia version and one monotonically increasing release sequence. It emits one signed bundle per exact compatibility profile.

Initial matrix:

```text
acer-aspire-one-i386-ab
raspberry-pi-400-arm64-ab
raspberry-pi-500-arm64-ab
standard-amd64-ab        # becomes release-capable when its backend/media session passes
```

Each bundle remains profile-specific; a Pi-400 bundle does not silently install on Pi-500 merely because both are arm64.

**Reason:** one release number is simple operationally; exact profile compatibility remains safe and explicit.

## D7 — One high-level release CLI is the owner workflow

Create/finish one high-level production tool (preferred source name: `tools/greia_release.py`) with source-owned subcommands equivalent to:

```text
doctor
build-profile
build-matrix
inspect
make-media
```

The supported owner flow becomes conceptually:

```bash
sudo python3 tools/greia_release.py doctor
sudo python3 tools/greia_release.py build-matrix \
  --version <VERSION> \
  --sequence <N> \
  --signing-key <PRIVATE_KEY> \
  --output <DIR>
```

and then:

```bash
sudo python3 tools/greia_release.py make-media \
  --release-dir <DIR> \
  --output <MEDIA_DIR>
```

Exact flags may be adjusted for implementation ergonomics, but the worker may not split this into unrelated architecture-specific user tools.

`tools/greia_update.py` remains reusable low-level bundle/push plumbing; it is not the production release recipe.

**Reason:** multiplatform must be simpler for the owner than manually constructing payloads, setting `GREIA_AB_*` environment variables and invoking several unrelated scripts.

## D8 — Supported build host and ARM cross-build

Official release builds run on x86_64 Linux. The same host builds i386/amd64 and cross-builds arm64 using `qemu-aarch64-static` + binfmt for chroot execution.

`doctor` checks tools, root privilege requirements, binfmt/qemu availability, repository trust keys, free disk, signing-key permissions and profile validity before starting an expensive build.

Do not introduce Docker/VM as a required product build layer.

**Reason:** one Linux builder can produce the matrix without maintaining parallel machines or build stacks.

## D9 — Raspberry Pi uses native firmware A/B, never GRUB

Keep the already-source-owned architecture:

```text
layout:  pi-mbr-tryboot-ab-v1
backend: pi-tryboot-ab-v1
```

Pi target layout is:

```text
P1  FAT32  pi-boot-control
P2  FAT32  pi-boot-a
P3  FAT32  pi-boot-b
P4         extended container
P5  ext4   system-a
P6  ext4   system-b
P7  ext4   persist (remainder)
```

The backend uses Raspberry Pi firmware `autoboot.txt` + one-shot `tryboot`. Candidate boot files are staged into the inactive Pi boot partition from the verified candidate slot/board adapter. Health confirmation makes that boot partition the normal default; failed/missing health leaves the previous normal default in place.

Do not use GRUB or U-Boot on Pi merely to resemble x86. Do not rewrite EEPROM in routine install/update.

**Reason:** Raspberry Pi firmware already supplies the exact one-shot A/B primitive Greia needs, including automatic clearing of tryboot after a failed candidate boot.

## D10 — Pi 400 and Pi 500 are separate profiles, shared implementation

Create:

```text
build/profiles/raspberry-pi-400-arm64-ab.toml
build/profiles/raspberry-pi-500-arm64-ab.toml
```

Both use common arm64 Greia userspace and shared package sets wherever valid, but typed board adapters own different Pi-4/BCM2711 and Pi-5/BCM2712 boot assets.

Initial ARM userspace remains Debian Bookworm-compatible for parity with the current target. Add the pinned official Raspberry Pi package repository/key only for the kernel/firmware/board packages required for the Pi profiles. Use the maintained Raspberry Pi kernel package family (`linux-image-rpi-v8` or its exact profile-owned successor selected in source after package inspection) and the official firmware packages; do not download random GitHub firmware at build time.

The implementation session must record the exact accepted package names/versions/repository key from the live repository in the build report, but it must not redesign the source/repository strategy.

**Reason:** Pi 400 and Pi 500 are different boot generations; common root/runtime code should still stay common.

## D11 — ARM graphics parity does not wait for a DRM rewrite

First ARM release uses Greia's existing lightweight X/SDL/Pygame runtime on Raspberry Pi KMS/DRM-capable drivers. Activities and Shell stay unchanged.

Direct DRM/KMS remains a later graphics-performance architecture item and does not block Pi support.

**Reason:** ARM parity is an OS/lifecycle requirement, not an excuse to reopen the entire display stack.

## D12 — Installation media is platform-appropriate, generated by one tool

We explicitly **drop the requirement that one exact disk image must boot every firmware family**. The old universal-media architecture remains useful safety/design history but is superseded on this point by ADR 0036 and this plan.

The release tool emits:

### PC
A bootable Greia Setup USB image containing the graphical installer, trusted public key and exact signed release bundle(s) appropriate to that media/profile. The installer uses the same privileged installation transaction service and same `.greiaupdate` bundle as system update.

### Raspberry Pi
A ready-to-flash compressed factory image (`.img.xz` or equivalent) for Pi 400 and Pi 500. The image already contains the final Pi A/B/PERSIST layout and is seeded from the exact signed profile bundle. First boot completes normal Greia commissioning/health acceptance.

The factory image is a **container for the signed release**, not a second OS composition path.

**Reason:** this is dramatically simpler for Pi users (flash microSD -> insert -> boot) and removes hot-insert/setup-USB boot-order behavior as a prerequisite for first-class ARM support.

A later Pi recovery USB may be added from the same release set, but it is not blocking.

## D13 — PC installer no longer carries two independent target payloads

For A/B profiles, retire the current situation where `build-installer-image.sh` independently builds `pip-rootfs.squashfs` while also embedding an externally minted `.greiaupdate`.

The A/B PC installer carries and installs the signed release bundle as target authority. A legacy single-root payload path may remain only for historical/non-update profiles until those profiles are retired; it cannot be used for new release-capable profiles.

Remove the production requirement for manually supplied `GREIA_AB_RELEASE_BUNDLE_SRC`. The high-level release/media command supplies its own just-built, hash-bound bundle to the media composer.

**Reason:** fresh install and update must install the same OS bytes.

## D14 — Parent app is delivery/UX only

Parent update flow is:

```text
System Update
-> choose .greiaupdate
-> display version/profile metadata
-> upload with progress
-> Greia verifies
-> Greia stages inactive slot
-> Ready to Restart
-> parent confirms restart
-> healthy candidate accepted OR automatic rollback
```

The browser never signs, runs `apt`, selects slots, writes disks or executes shell/root commands. Existing Greia-password/device-credential auth remains the authority boundary.

Automatic cloud release discovery is deferred; local file upload is enough to complete this architecture cleanly.

## D15 — Existing single-root machines are reinstall-only for this migration

Do not create an in-place repartitioner in this plan. If an older Greia installation is single-root, Parent reports that a new installer/factory image is required for transactional updates.

**Reason:** remotely repartitioning the only working copy is the opposite of a simple robust updater.

## D16 — Testing strategy stops burning hours on predictable composition failures

Three layers:

1. **fast semantic artifact preflight** — mount/inspect exact slot/bundle and prove complete Greia composition;
2. **loop/QEMU platform lifecycle** — only after preflight is green;
3. **physical acceptance** — only for firmware/hardware behavior QEMU cannot establish.

Do not rebuild and run the full 20-minute+ closure to discover a missing file that a 10-second mounted-artifact check could reject.

---

# 2. Required production outputs

A completed release directory should be understandable without reading code. The release tool should emit roughly:

```text
out/releases/<version>-r<sequence>/
  release-report.json
  checksums.sha256
  trusted-public-key-id.txt

  acer-aspire-one-i386-ab/
    greia-<version>-acer-aspire-one-i386-ab.greiaupdate
    slot-image.img
    build-report.json

  raspberry-pi-400-arm64-ab/
    greia-<version>-raspberry-pi-400-arm64-ab.greiaupdate
    slot-image.img
    build-report.json

  raspberry-pi-500-arm64-ab/
    greia-<version>-raspberry-pi-500-arm64-ab.greiaupdate
    slot-image.img
    build-report.json

  standard-amd64-ab/                 # once supported
    ...

out/media/<version>-r<sequence>/
  greia-setup-legacy-i386.img
  greia-pi400-<version>.img.xz
  greia-pi500-<version>.img.xz
  greia-setup-amd64.img              # once supported
```

Intermediate private signing material is never copied into either tree.

The exact filenames may be normalized during implementation, but the one-release-directory / one-media-directory model is binding.

---

# 3. Session plan

Each numbered session is sized for one strong coding LLM session. A session should end with committed coherent work, focused tests, an updated plan progress entry and `HANDOVER.md`. Do not split a session merely because a test failed; fix within the session when practical. Do not combine later physical-hardware work into an earlier source session.

## Session 01 — Canonical target-root composition and semantic slot validator

**Goal:** make it impossible to build the OS twice in two different ways.

### Implement

1. Extract reusable target-root composition from `build/build-image.sh` into `build/lib/` primitives. Keep one implementation for:
   - debootstrap/base setup;
   - repository configuration;
   - profile package resolution;
   - Greia overlay/runtime/assets;
   - system-update composition;
   - boot/kernel package installation;
   - build metadata/manifests;
   - footprint hygiene.
2. Keep `build/build-image.sh` as a thin consumer that turns the canonical composed root into its existing raw target disk image.
3. Add canonical slot-image construction from the same composed root: fixed-size relocatable ext4 filesystem, no partition table.
4. Add a source-owned semantic `system-slot-image` validator implementing D4.
5. Add negative fixtures proving a bare/minimal ext4 image is rejected.
6. Add positive tests proving the normal Acer target root passes and contains `apt-get`/`dpkg`/Greia/runtime/kernel facts.

### Why now

This is the root fix for D6 and the prerequisite for every architecture. Doing ARM before this would copy the current composition mistake.

### Acceptance

- current Acer target image still builds from the shared root composer;
- canonical Acer slot image can be mounted read-only and passes semantic validation;
- deliberate V12G-style minimal payload fails before signing;
- focused builder/profile/update tests green;
- `make verify` green because this is a major build refactor.

No QEMU Gate P5 yet.

---

## Session 02 — Production release builder and D6 closure at artifact level

**Goal:** turn the canonical slot into the only normal `.greiaupdate` source.

### Implement

1. Add `tools/greia_release.py` high-level `doctor`, `build-profile` and `inspect` commands.
2. Wire profile build -> semantic slot validation -> hardware-support member -> persistent contract -> Ed25519 signing -> final bundle inspection.
3. Make the shared production bundle builder reject semantically invalid system-slot payloads even if called through lower-level tooling.
4. Generate `build-report.json`, SHA-256 and exact profile/version/sequence facts.
5. Ensure private key handling is read-only, permission checked and never copied to output.
6. Add regression proving the production CLI cannot reproduce the V12G 64 MiB bundle.

### Why

The owner should never again have to manually mint a payload and hope it matches the target image.

### Acceptance

- one command builds a valid Acer `.greiaupdate` from profile + version + sequence;
- bundle payload is byte-identical to the canonical slot image output;
- signature verification passes with the paired public key;
- mounted payload proves full Greia root and `apt-get`;
- negative minimal payload fails before signature output exists;
- focused tests + `make verify` green.

---

## Session 03 — PC installer convergence and final legacy-x86 Gate P5 closure

**Goal:** finish the part that has consumed weeks and close T3-P on the legacy product path.

### Implement

1. Refactor `build/build-installer-image.sh` A/B path so target authority is the just-built signed `.greiaupdate`, not an independently built `pip-rootfs.squashfs` plus externally supplied release.
2. Preserve the live graphical installer environment and proven legacy removable-boot mechanics.
3. Remove production dependence on manually set `GREIA_AB_RELEASE_BUNDLE_SRC`; media/release orchestration passes the exact release artifact explicitly.
4. Keep D1-D5 fixes intact: socket activation, update socket enablement, canonical `profile.id`, crypto composition, `CAP_SYS_CHROOT`.
5. Add assembled-media preflight: extract installer image read-only and prove its embedded bundle hash/profile/key and live service composition before QEMU.
6. Rebuild official Acer A/B installer from current HEAD and run full Gate P5 closure once.

### Why

After Sessions 01-02, another ENOENT-style composition failure would be caught locally. This is the right point to pay for the expensive lifecycle run.

### Acceptance

- full `make verify` green before product closure;
- official image is SHA-bound to tested HEAD and bundle;
- install A -> boot/health -> update B -> failed candidate rollback -> accepted candidate -> reverse path executes;
- Gate P5 is **9/9 GREEN**;
- T3-P marked DONE only on that evidence;
- if a new genuine product defect appears, fix it in this same architectural model; do not reopen D1-D6 choices or create a new product fork.

**Stop condition:** if semantic preflight is green but lifecycle fails, diagnose the new product defect. Do not weaken Gate P5.

---

## Session 04 — Release matrix CLI and reproducible owner workflow

**Goal:** make release building simple before adding ARM.

### Implement

1. Add `build-matrix` and `make-media` orchestration to `tools/greia_release.py`.
2. Add a declarative release matrix listing supported profile IDs; no copied command scripts per platform.
3. `doctor` checks Linux host, required commands, disk space, signing key, public key, profile validity, package trust files and cross-build facilities.
4. Build artifacts into one version/sequence release tree and emit one top-level release report/checksum file.
5. Reuse persistent apt/pool caches already introduced; cache reuse must not change signed output authority.
6. Document the exact owner commands in `SETUP.md` / build docs.

### Why

ARM work should drop into a stable production factory rather than creating another bespoke build command.

### Acceptance

- Acer matrix build succeeds through the same path as Session 02;
- rerunning with same source/profile/version inputs either produces the same semantically bound system content or records all expected nondeterministic filesystem facts honestly; no false reproducibility claim;
- bad/missing cross-build requirements fail in `doctor`, not 40 minutes later.

---

## Session 05 — ARM64 build substrate and Pi profiles

**Goal:** make ARM a real build target using the common composer.

### Implement

1. Add pinned Raspberry Pi archive trust/repository support to the build composition layer; repository use is profile/board-owned, never globally enabled for x86.
2. Add/finish package-set mappings required by ARM installed boot/display/runtime adapters.
3. Add exact profiles:
   - `raspberry-pi-400-arm64-ab.toml`
   - `raspberry-pi-500-arm64-ab.toml`
4. Both profiles:
   - `architecture=arm64`;
   - `layout_adapter=pi-mbr-tryboot-ab-v1`;
   - `updates.boot_backend=pi-tryboot-ab-v1`;
   - explicit board identity (`pi-400-v1` / `pi-500-v1`);
   - A/B required;
   - current Greia runtime families/Activities;
   - KMS/X display path;
   - same persistent-state contract.
5. Extend canonical root composer for arm64 with qemu-user-static/binfmt chroot support on x86_64 builder.
6. Produce complete Pi slot images and signed `.greiaupdate` bundles through the same release CLI.
7. Record exact kernel/firmware package sources in the generated build report.

### Why

The profile schema already contains the Pi concepts. This session completes the builder rather than inventing new profile semantics.

### Acceptance

- both Pi profiles pass source validation;
- both complete arm64 slot images pass the same semantic validator as Acer;
- `file`/ELF/chroot probes prove arm64 userspace;
- Greia Python/Pygame/runtime smoke imports work under the cross-build chroot;
- bundle signature/compatibility facts are exact per board profile;
- no x86 profile gains Pi repository/packages;
- `make verify` green.

No physical Pi claim yet.

---

## Session 06 — Executable Pi disk layout + durable identity observation

**Goal:** turn the already-defined Pi layout skeleton into a real installer/factory target writer.

### Implement

1. Implement `PiMbrTrybootAbAdapter.build_commands/execute` for the fixed P1/P2/P3 + extended P4 + logical P5/P6/P7 layout.
2. Format boot partitions FAT32 and system/PERSIST ext4 with profile-owned labels.
3. Implement Pi post-layout identity observation behind the existing typed interface; bind actual PARTUUID/filesystem UUID facts, never caller guesses.
4. Extend persistent layout authority to record the Pi boot-role facts needed by the boot backend without contaminating common system-slot identity.
5. Implement loop-image tests for exact partition numbers, sizes, filesystems, distinct IDs and PERSIST remainder.
6. Add failure/fault tests for short disk, missing logical partition, wrong filesystem, identity mismatch and stale target observation.

### Why

The Pi boot backend cannot be safely built on placeholder partition roles.

### Acceptance

- disposable image can be partitioned exactly as D9;
- system A/B identities are distinct and stable;
- layout record round-trips and validates against observed topology;
- no raw user/UI device path can enter the destructive layout API;
- x86 legacy layout regression stays green.

---

## Session 07 — Pi boot assets and native tryboot backend

**Goal:** implement real Pi A/B boot transaction semantics.

### Implement

1. Add typed Pi-400 and Pi-500 board boot-asset adapters.
2. During fresh install/update finalization, mount the inactive Pi boot partition and copy/render the candidate kernel/initramfs/DTBs/firmware/config from the **verified candidate slot**, never from the build host.
3. Render board-correct `config.txt` and root command line using the observed candidate SYSTEM PARTUUID.
4. Implement `pi-tryboot-ab-v1` backend:
   - read current accepted/default boot partition;
   - stage candidate boot partition;
   - verify exact candidate boot files/digests;
   - write durable `autoboot.txt` normal/tryboot mapping;
   - arm with `reboot '0 tryboot'` semantic operation;
   - observe tryboot/partition from device tree;
   - on BOOT_HEALTHY atomically-as-practical commit the new normal default using write+fsync+rename+directory fsync where supported+syncfs+readback;
   - on failure/missing health leave old normal default untouched.
5. Bind boot-asset digests into the existing finalization/boot receipt model rather than inventing a parallel receipt.
6. Add pure/loop tests for A->B and B->A mappings, malformed `autoboot.txt`, wrong partition, interrupted writes and failed candidate state.

### Why

Native tryboot provides the rollback primitive without importing an x86 bootloader to ARM.

### Acceptance

- source contract proves no GRUB/U-Boot Pi fallback;
- candidate arm/commit/rollback state machine passes on disposable filesystems;
- wrong/missing boot files fail before arm;
- common `SystemUpdateService` sees the same semantic states as x86.

---

## Session 08 — Pi factory image builder

**Goal:** give users the simplest possible Raspberry Pi fresh-install artifact.

### Implement

1. Add a Pi factory-media composer invoked only through `greia_release.py make-media`.
2. Input is an already-built, already-verified Pi `.greiaupdate` plus trusted public key and profile facts.
3. Create the final Pi A/B/PERSIST disk layout using the same executable layout adapter as installation.
4. Stream/finalize SYSTEM_A through the same `SlotWriter`/`SlotFinalizer` path.
5. Initialize SYSTEM_B empty, initialize PERSIST, install Pi boot-control/BOOT_A assets, leave BOOT_B ready for future update.
6. Record first-install pending/accepted semantics consistently with the normal installer path.
7. Emit compressed image + checksum + factory-media report binding source bundle SHA/profile/release sequence.
8. Ensure no signing private key enters the factory image.

### Why

Pi users should flash one image, not boot a special installer, remove/insert cards, or understand EEPROM boot order.

### Acceptance

- factory image reconstructs to the exact profile layout and embedded release identity;
- SYSTEM_A base bytes match the signed slot payload before bounded finalization;
- image contains no private key or build cache;
- image boots far enough under available ARM/QEMU emulation for structural/kernel sanity where feasible; no false claim that QEMU proves Pi firmware.

---

## Session 09 — Parent App system-update UX and exact OS integration

**Goal:** make safe updates usable by ordinary parents.

### Greia repo

1. Finish Parent API update status/upload/stage/restart semantics around existing `SystemUpdateInbox` / privileged service.
2. Return bounded progress/state/error payloads; do not expose paths/slots/commands.
3. Ensure device verifies signature/profile/architecture/sequence before staging.
4. Ensure upload connection may disappear after queueing; staging continues device-side.
5. Ensure reboot is an explicit parent action when `READY_TO_RESTART`.

### Parent repo

1. Add a System Update screen/section.
2. File picker accepts `.greiaupdate`.
3. Show release version + target device/profile + signed/verified status after device verification.
4. Upload progress, staging progress, ready-to-restart action, post-reconnect result.
5. Clear explanations for wrong profile, old sequence, bad signature, insufficient space and rollback.
6. No Linux vocabulary in ordinary UI.
7. Repin the accepted Parent runtime through the existing atomic pin tool; do not hand-edit vendor/hash copies.

### Why

The platform update architecture is not finished if parents still need SSH or command-line push tooling.

### Acceptance

- browser -> real Greia API -> privileged update service -> inactive slot path works in VM/image test;
- legacy credential/auth protections remain intact;
- wrong-signature/wrong-profile file never reaches slot write;
- Parent app can reconnect after restart and report accepted or rolled-back release;
- both repos' relevant test suites green; Greia `make verify` green before repin acceptance.

---

## Session 10 — Physical Raspberry Pi 400 acceptance

**Goal:** prove the exact Pi-400 product bytes, not a hand-built surrogate.

### Procedure

1. Build release matrix and Pi-400 factory image from one exact Greia HEAD.
2. Flash factory image to expendable microSD.
3. Boot physical Pi 400.
4. Verify:
   - firmware/DTB/kernel boot;
   - Greia graphical shell reaches INTERACTIVE_READY;
   - keyboard/pointer/audio/network basics;
   - correct profile/board identity;
   - PERSIST survives reboot;
   - Parent API discovery/auth works.
5. Push a newer signed Pi-400 bundle through Parent.
6. Stage -> tryboot candidate -> BOOT_HEALTHY -> commit.
7. Stage a deliberately unhealthy candidate -> prove automatic return to previously accepted partition.
8. Power-cut/fault test around candidate boot-control commit boundaries on expendable media; verify known-good boot remains recoverable.

### Acceptance

A single evidence package binds source HEAD, factory-image SHA, update-bundle SHA and observed boot/update/rollback facts. Pi-400 support remains experimental until this passes.

---

## Session 11 — Physical Raspberry Pi 500 acceptance

Same contract as Session 10, but on Pi 500 and with explicit proof that BCM2712/Pi-5 boot assets are actually used. Do not inherit Pi-400 physical evidence.

### Acceptance

- exact Pi-500 factory image boots and reaches Greia Shell;
- update success + forced rollback pass;
- Pi-500-specific kernel/DTB/boot asset path is recorded;
- no Pi-400 firmware recipe is silently being reused as a fake generic path.

After Sessions 10-11, ARM64/Pi is first-class for the supported profile set.

---

## Session 12 — Modern amd64 A/B profile and UEFI media

**Goal:** complete the third mainstream architecture family without disturbing the Pi/legacy paths.

### Implement

1. Add `standard-amd64-ab` profile using `modern-gpt-ab-v1` and `grub-ab-v1`.
2. Implement the already-defined GPT adapter execution path: BIOS-boot (if retained by profile), ESP, boot-control, A, B, PERSIST.
3. Build complete amd64 slot/release through the same canonical composer/release CLI.
4. Build bootable UEFI Setup USB from the exact signed bundle; use Debian-supported shim/signed GRUB/kernel chain for ordinary Secure Boot compatibility rather than custom signing glue.
5. QEMU/OVMF install/update/rollback first; physical modern reference afterward.

### Why

This completes i386 + amd64 + arm64 under one release contract. It is deliberately after Pi so “ARM later” cannot recur.

### Acceptance

- UEFI Secure Boot OFF and ON acceptance on exact media/profile before marking certified;
- SATA/NVMe target policies proven on disposable hardware/VM as applicable;
- same Parent update flow works unchanged.

---

## Session 13 — Final release-factory polish, migration messaging and closure

**Goal:** make the architecture boring to operate and close the successor plan.

### Implement/review

1. One owner-facing release guide containing only supported commands.
2. `greia_release.py doctor` + build-matrix + make-media end-to-end dry run from clean checkout.
3. Ensure output names clearly identify hardware; generate checksum/release report.
4. Parent on single-root systems reports: transactional update unavailable; create current installer/factory media to migrate. No in-place repartition offer.
5. Remove/deprecate stale manual recipes that mint arbitrary A/B bundles or ask for `GREIA_AB_RELEASE_BUNDLE_SRC` production wiring.
6. Update `SETUP.md`, `HANDOVER.md`, agent operations, OS skill and active-plan routing.
7. Mark the old August blocking plan historical/superseded for implementation sequencing while retaining its still-unfinished non-lifecycle work as a later backlog, not a competing blocker.
8. Run full source verification and one final artifact semantic matrix.
9. Record exact physical support table:
   - Acer legacy i386;
   - Pi 400 arm64;
   - Pi 500 arm64;
   - modern amd64 only if Session 12 physical acceptance exists.

### Definition of done

This plan closes only when:

```text
production release builder cannot sign an incomplete slot
AND fresh install and update consume the same signed release
AND legacy x86 Gate P5 is 9/9 GREEN
AND Parent can upload/stage/restart/observe an update without shell access
AND Pi-400 release + factory media + update + rollback are physically proven
AND Pi-500 release + factory media + update + rollback are physically proven
AND one x86_64 Linux build host can produce the supported profile matrix
AND platform media are generated through one owner-facing release tool
AND current routing/docs no longer send agents back into the V12G D6 decision fork
```

Modern amd64 certification may remain explicitly experimental if physical Secure Boot hardware is not yet available, but the source/build adapter must not block Pi/legacy completion.

---

# 4. What workers are explicitly NOT allowed to redesign

During this plan, workers must not independently decide to:

- replace whole-system releases with package deltas;
- remove A/B rollback to simplify updates;
- install updates in place on the active root;
- replace the shared SlotWriter/SlotFinalizer with platform copies;
- replace Pi tryboot with GRUB/U-Boot;
- make one Pi profile silently accept both board generations;
- switch Pi primary install back to USB + hot-insert microSD;
- require a single universal installer-image hash across BIOS/UEFI/Pi;
- make Parent app perform signing or privileged disk/package work;
- add network APT to candidate finalization;
- create a second installer payload format;
- create a separate ARM Greia runtime/application stack;
- block ARM support on a direct-DRM rewrite;
- implement ordinary remote repartition of single-root systems;
- weaken Gate P5, signature, compatibility, anti-rollback or health-confirmation semantics.

If implementation reveals a genuine contradiction with a binding ADR/source invariant, stop that **specific session**, document the contradiction with exact code/evidence, and ask the owner. Do not invent a replacement architecture in the worker report.

---

# 5. Test/evidence economy

The previous closure cycle spent too much time discovering composition errors sequentially. This plan uses the following cost order:

### Every relevant code session

- focused unit/contract tests for changed surfaces;
- static/shell/profile validation;
- mounted-artifact semantic inspection when an artifact is built.

### Major source/build milestones (Sessions 01, 02, 03, 05, 09, 12, 13)

- full `make verify` before claiming the milestone ready.

### QEMU/image lifecycle

Run only after the exact artifact passes semantic preflight. For legacy x86, Session 03 is the decisive Gate-P5 run; do not rerun it after every local refactor.

### Physical hardware

Use only for facts that genuinely depend on firmware/device behavior. Pi 400 and Pi 500 each require their own physical acceptance; source tests or generic ARM QEMU are not substitutes.

### Failure discipline

When a lifecycle fails:

1. capture the first real failing layer;
2. reproduce it at the cheapest faithful layer possible;
3. fix the owning architecture/component;
4. rerun focused + semantic artifact preflight;
5. rerun the expensive lifecycle only when those are green.

Do not add product special cases merely to make the gate advance.

---

# 6. Immediate next session

**Start Session 01.**

Before implementation, update repository routing in the same first-session commit so agents read this plan rather than the stale D6/`POSTR1-P1-INSTALLER-RED` route:

```text
AGENTS.md
HANDOVER.md
skills/greia-os-work/SKILL.md
```

The August plan and V12G report remain historical evidence. Do not delete or rewrite their progress ledgers.

The first implementation objective is not another closure run. It is:

> **factor one canonical complete target root, create a complete relocatable slot image from it, and make the release validator reject the V12G skeleton class before signing.**

Only after that is green does Session 02 mint the real Acer release and Session 03 pay for the final legacy lifecycle closure.

---

# 7. Decision provenance

This successor plan deliberately consolidates rather than discards the good architecture already present:

- ADR 0013: declarative profiles / payload + adapter composition;
- ADR 0014: ARM64 and Pi 400/500 are first-class;
- ADR 0030: signed whole-system transactional A/B updates;
- existing source: `SlotWriter`, `SlotFinalizer`, A/B profile schema, Pi layout/backend IDs;
- `UNIVERSAL_GREIA_SETUP_MEDIA_ARCHITECTURE.md`: typed target identity, privilege split, Pi native tryboot, shared installer/update authority and A/B/PERSIST safety rules;
- V12G: D1-D5 repairs and decisive proof that an invalid partial release payload reached the common finalizer.

It changes one costly earlier product assumption: **we no longer require one physical setup image to boot every architecture.** We require one release architecture, one build tool and platform-appropriate install media generated from the same signed release. That is the simpler contract for both maintainers and users.
