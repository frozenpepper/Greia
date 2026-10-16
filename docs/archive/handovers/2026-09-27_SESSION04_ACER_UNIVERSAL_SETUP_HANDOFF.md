# Greia handoff — Session 04, Acer boot failure, and universal Setup architecture

**Date:** 2026-09-27
**Purpose:** standalone continuation record for the next ChatGPT/agent session.
**Current architectural theme:** finish Session 04 without confusing the standalone A/B engineering image with the future one-image multiplatform Setup artifact.

## 1. Current repository position

The key current history, newest relevant first:

- `31d1de2a3a4a86ad7b33b6e4db95abd7877aadb8`
  - local-agent recovery runbook added.
- `cc679a9b5a51ffc221f71ccff1ff9a78f4f4df5d`
  - agent operations now pin the proven Acer removable boot path.
- `257fdf95b9c0b03d69468e1fc7a24c7213907c73`
  - active plan marks the A/B GRUB USB route unproven on the reference Acer.
- `cee3127f41bbd2f51468ac90b58a27ff568a22d7`
  - HANDOVER routes next Acer physical boot through Syslinux.
- `d4bece3188ec497a6fa2e5501c8ccada7d2e4d94`
  - safe raw media writer fixed for util-linux flat partition-sibling output.
- `c45713d5848a4d3435751b55e36e89373872ec7d`
  - physical failure review source-state correction.
- `7db7d6c1163598824737db515d1804ec13d4356d`
  - Acer A/B GRUB physical boot failure review.
- `7d337d0d01e58e3ee303b43964590a0334f3fbc0`
  - Orbiter replacement-disk migration recorded complete and verified.
- `c8054717844840e2268d9abecd62da818ad60ef6`
  - latest core Session-04 source state before later docs/host/media-writer-only changes.

The exact latest main may advance after this handoff. Require `31d1de2a...` as an ancestor rather than pinning forever to one docs SHA.

## 2. The mistake that just happened

The owner asked for a physical installer USB test.

A raw `acer-aspire-one-i386-ab` image was built and flashed. That image uses a GRUB/MBR removable first stage.

On the reference Acer Aspire One it produced:
- screen on;
- brief blinking cursor;
- then black screen;
- no Greia boot screen;
- no installer.

This was a preventable mistake in task routing.

The repository already contained accepted physical evidence from August:
- `docs/INSTALLATION_USB_BOOT_POSTMORTEM.md`
- `docs/archive/reviews/2026-08-20_ACER_INSTALLER_BOOT_REGRESSION.md`

Those records prove that, on this Acer + USB-stick/firmware combination:
- GRUB's MBR removable path does not reliably execute;
- active FAT32 + Syslinux does;
- Syslinux printed visible boot stages and ultimately reached the Greia installer once the live-media identity was correct.

The 2026-09-27 failure is therefore not evidence that “Greia cannot boot this Acer”; it is evidence that the wrong intermediate boot artifact was chosen for the physical test.

## 3. Critical architecture distinction

There are three separate boot responsibilities:

### A. Removable universal Setup medium

Final product requirement: **one physical Setup image** for all supported hardware.

That image deliberately contains multiple first-stage boot paths.

Authoritative current design from ADR 0036 + active plan:

```text
P1  FAT32 GREIA_SETUP_BOOT active
    |
    +-- SYSLINUX legacy BIOS boot files
    +-- i386 live kernel/initramfs
    +-- EFI/BOOT amd64 UEFI files
    +-- amd64 live kernel/initramfs
    +-- Pi 400 firmware/DTB/kernel/initramfs
    +-- Pi 500 firmware/DTB/kernel/initramfs
    +-- config.txt / Pi board selection

P2  ext4 GREIA_SETUP_DATA
    |
    +-- live/i386/rootfs.squashfs
    +-- live/amd64/rootfs.squashfs
    +-- live/arm64/rootfs.squashfs
    +-- acer-aspire-one-i386-ab.greiaupdate
    +-- standard-amd64-ab.greiaupdate
    +-- raspberry-pi-400-arm64-ab.greiaupdate
    +-- raspberry-pi-500-arm64-ab.greiaupdate
```

So “one image” never meant “one bootloader”.

### B. Installed Acer internal disk

The installed Acer uses the normal legacy x86 A/B layout and GRUB A/B boot backend.

GRUB works on the Acer internal disk. The August postmortem explicitly distinguishes that from the failed removable-USB GRUB MBR path.

Therefore:
- USB first stage = Syslinux;
- installed internal disk = GRUB A/B.

No contradiction.

### C. Raspberry Pi installed system

Pi uses native Raspberry firmware/tryboot semantics. It does not need GRUB/U-Boot merely for symmetry.

## 4. Why we moved toward one image in the first place

The owner explicitly required one universal Setup image so a parent does not need to know:
- i386 vs amd64 vs arm64;
- BIOS vs UEFI;
- Pi 400 vs Pi 500;
- which installer to download.

The final release must produce one user-facing Setup image plus per-profile update bundles.

The architecture was deliberately designed to let:
- Acer firmware consume Syslinux from P1;
- modern PC firmware consume UEFI files from P1;
- Pi firmware consume Pi boot assets from P1;
- all of them mount the matching architecture live root from P2 and run the same installer application.

This requirement remains correct and must not be rolled back because the wrong standalone engineering image was physically tested.

## 5. Active implementation phase

The authoritative active plan is:

`docs/plans/2026-09-15_MULTIPLATFORM_RELEASE_INSTALL_UPDATE_COMPLETION.md`

Current sessions:

- Session 01: update-bundle/runtime simplification
- Session 02: canonical root composer + complete slot
- Session 03: owner release CLI + compact outputs
- **Session 04: finish legacy i386 lifecycle with real payload**
- Session 05: modern amd64 + UEFI A/B
- Session 06: ARM64 build substrate + real Pi profiles
- Session 07: Pi 400/500 live boot board adapters
- Session 08: compose real universal Setup image
- Session 09: common installer behavior
- Session 10+: Pi A/B, recovery, Parent update, physical closeout

Do not jump directly to Session 08 now. The active plan explicitly waits for the real amd64 and Pi boot paths before composing the final universal medium.

## 6. Session 04 actual status

Session 04 goal:

```text
fresh A/B install
-> first healthy A acceptance
-> healthy A -> B update
-> B commit
-> userspace-broken candidate -> recovery
-> nonboot candidate -> reset -> previous accepted slot
-> PERSIST-incompatible candidate refused before mutation
```

Before the Orbiter disk failure, source work had reached:
- all nine focused suites PASS at core source `c8054717`;
- immutable S03 release bundle verified;
- four Session-04 candidate bundles verified.

Then a diagnostic installer rebuild failed because the old Orbiter root disk had real hardware medium errors.

The owner replaced the disk.
The replacement is documented healthy.
The migration is complete.
Heavy build/QEMU work is allowed again.

The core Session-04 source did not materially change after `c8054717`; later relevant source change was the independent `build/write-image.sh` safe-writer fix.

## 7. Session-04 installer/service repairs already landed

The transaction service originally had two distinct problems.

### A. Capability problem

The service needed apt's normal privilege-drop operations.

Exact current intended set:

```text
CAP_SYS_ADMIN
CAP_SYS_CHROOT
CAP_SETUID
CAP_SETGID
```

Keep:
- `NoNewPrivileges=yes`
- `ProtectSystem=strict`

Do not add `CAP_CHOWN` merely because APT printed an ownership warning.

### B. Python module identity problem

The systemd unit used to execute:
`python3 -m greia_installer.transaction_service`

Composition later imported the same implementation as:
`greia_installer.transaction_service`

This could split the module into `__main__` and canonical package instances, including separate exception classes and module globals.

Repair:
- thin executable `transaction_service_entrypoint.py`;
- implementation remains canonical/library-only;
- systemd runs the entrypoint;
- permanent regressions exercise wrapper topology and refusal survival.

## 8. Apt CAP_CHOWN decision is deliberately deferred

The previous diagnostic run showed an early warning around APT's partial-directory `chown`.

Follow-up source review found:
- APT treats that specific failed chown as a warning and continues;
- Greia was keeping only the first 256 stderr characters;
- therefore the actual fatal apt/dpkg/postinst line could be later and hidden.

Current source now preserves bounded stderr:
- head;
- separator;
- fatal tail.

Therefore:
**do not add CAP_CHOWN until the new diagnostic fresh-install run shows the actual fatal line.**

Relevant docs:
- `docs/archive/testing/2026-09-25_SESSION04_APT_OWNERSHIP_DECISION.md`
- `docs/testing/2026-09-25_SESSION04_POST_GITHUB_REPAIR_ORBITER_VALIDATION.md`

## 9. Chroot mount cleanup repair already landed

A newly introduced cleanup path used normal unmount followed by lazy detach and could erase bookkeeping even when cleanup remained unresolved.

This was replaced by shared:
- recursive unmount on exact recorded roots;
- minimal-root collapse for nested bind trees;
- fail-closed behavior;
- failed roots remain tracked.

Fresh installer, legacy installer and update staging share this cleanup owner.

Do not reintroduce lazy unmount merely to make a gate pass.

## 10. The Acer physical test we actually need now

Before continuing to debate universal-media implementation, re-prove the accepted removable boot path after all later source changes.

Use exactly:

```bash
sudo bash tools/build-and-flash-development-usb.sh   legacy-x86-i686-dev   /dev/sdX
```

This is:
- a development/reference image;
- active FAT32 + Syslinux;
- visible tty1 diagnostics;
- panic stays visible;
- not the final product image;
- not a split-product decision.

The owner should report the last visible stage:
- Syslinux?
- Loading vmlinuz?
- Loading initrd?
- live-boot/kernel text?
- Greia framebuffer?
- graphical language chooser?

A positive result re-confirms the physical first stage that the future universal image must preserve.

## 11. Important current documentation drift

`docs/architecture/UNIVERSAL_GREIA_SETUP_MEDIA_ARCHITECTURE.md` is an older plan and still describes legacy Acer USB boot using GRUB MBR.

That conflicts with:
- accepted August physical postmortem;
- ADR 0036;
- active plan A16.

Do not use that old section as current authority.

The local-agent runbook requires a narrow correction/banner so another agent cannot repeat the mistake.

Likewise the 2026-09-27 physical review should receive an appended clarification:
- failure belongs to the standalone/intermediate A/B GRUB engineering image;
- one-image architecture remains correct;
- final universal image already intends Syslinux for legacy BIOS.

## 12. Safe raw USB writer bug

During the failed physical campaign, `build/write-image.sh` refused the already-partitioned USB because util-linux 2.39.x returned disk + partitions as flat siblings.

Workaround at the time required owner-authorized external `sgdisk --zap-all`.

A narrow source fix has now landed:
`d4bece3188ec497a6fa2e5501c8ccada7d2e4d94`

It now:
- locates the exact confirmed whole-disk root;
- accepts only direct `part` siblings whose `PKNAME` is that disk;
- still refuses unrelated/mapper topology;
- keeps removable/root-disk/fingerprint protections.

This fix has not yet received an executed focused regression in the current session. Validate it narrowly when convenient. It is not the blocker for the named Acer Syslinux development writer.

## 13. Host state

Old Orbiter disk:
- failed with real medium errors;
- removed/replaced.

Replacement disk:
- migration recorded complete at `7d337d0d`;
- healthy;
- heavy build/QEMU work permitted again.

The physical failure review records two stale autoclear Greia loops left by the failed build:
- loop2
- loop34

These require reboot to clear.

Before next image build:
`sudo losetup -a | grep greia`

If still present, reboot once and verify clean before building.

Never use `losetup -D`.

## 14. What the next local agent must do

Exact durable runbook:
`docs/agents/2026-09-27_SESSION04_ACER_RECOVERY_RUNBOOK.md`

High-level:
1. sync current main;
2. read ADR 0036 + active plan + August/September boot postmortems;
3. reconcile stale universal-media docs narrowly;
4. clear stale loops by reboot if needed;
5. build/flash the known-good Syslinux development USB;
6. stop for owner physical Acer result;
7. independently resume Session-04 QEMU diagnostic fresh-install run;
8. capture the actual apt fatal tail;
9. if green, remove temporary diagnostics, rebuild clean, complete lifecycle;
10. `make verify`, close Session 04, open Session 05.

## 15. What the next ChatGPT session should NOT do

Do not:
- tell the user the universal one-image architecture was a mistake;
- create an Acer-only public installer;
- change the Acer installed boot backend away from GRUB A/B merely because USB GRUB fails;
- try to force one first-stage bootloader across BIOS/UEFI/Pi;
- jump to universal-image implementation before Session 05–07 prerequisites;
- add CAP_CHOWN from the old warning;
- introduce another gate/orchestrator framework;
- rerun large test matrices reflexively when a narrow physical fact is needed.

## 16. Future universal-image target, when Session 08 legitimately arrives

The final media must implement active plan A12/A16/A17/A18:

```text
one MBR-partitioned USB image
|
+-- P1 FAT32 active
|   +-- Syslinux legacy BIOS
|   +-- signed-distro amd64 UEFI removable boot files
|   +-- Pi 400 firmware/DTB/kernel/initramfs
|   +-- Pi 500 firmware/DTB/kernel/initramfs
|   +-- config.txt board filters
|
+-- P2 ext4
    +-- i386 live squashfs
    +-- amd64 live squashfs
    +-- arm64 live squashfs
    +-- four compressed .greiaupdate bundles
```

The Acer must not load amd64/ARM roots into RAM.
No `toram`.
Acer overlay begins at 128 MiB.
Final raw image <= 7,400,000,000 bytes.

## 17. User preference/process correction from this session

The owner explicitly pushed back against overengineering.

Operational implication:
- solve the actual blocker;
- use existing architecture;
- add only safeguards tied to real failure modes;
- avoid creating new scaffolding, meta-gates, evidence frameworks or extra artifacts for ordinary work;
- real physical tests should be used when they answer a physical question;
- do not make a ten-step governance exercise out of building and testing one USB.

The correct immediate physical action is intentionally simple:
**build the proven Syslinux development USB and let the owner boot it.**

## 18. New-session opening prompt suggestion

The user can begin the next session with:

> Working on Greia OS. Read `docs/archive/handovers/2026-09-27_SESSION04_ACER_UNIVERSAL_SETUP_HANDOFF.md` and `docs/agents/2026-09-27_SESSION04_ACER_RECOVERY_RUNBOOK.md`. Continue from current GitHub main. Keep the one universal Setup image architecture: Syslinux for legacy BIOS removable boot, UEFI files for modern PC, Pi firmware for Pi, all on one future image. First review the local-agent result/physical Acer result, then continue Session 04 without introducing new scaffolding.


---

## 19. Correction to §11 of this handoff (appended after execution)

§11 states that `docs/architecture/UNIVERSAL_GREIA_SETUP_MEDIA_ARCHITECTURE.md` "still
describes legacy Acer USB boot using GRUB MBR". Checked against source: **this is false.**
The document already mandates `MBR -> active FAT32 -> SYSLINUX` for the removable legacy
first stage, already records that the Acer rejected GRUB-on-USB, and already lists
replacing that SYSLINUX path with GRUB as a forbidden failure mode. Its GRUB references in
the target-layout section are the **installed internal-disk A/B** layout, which is correct
and must not be changed.

Only the precedence was genuinely missing; the authority line now names ADR 0036 as the
normative owner of the universal Setup image, with the active plan. See the correction
appended to `docs/agents/2026-09-27_SESSION04_ACER_RECOVERY_RUNBOOK.md` §13 and §12 of
`docs/archive/reviews/2026-09-27_ACER_AB_GRUB_INSTALLER_PHYSICAL_BOOT_FAILURE.md`.

Every architectural conclusion in §§3 and 4 of this handoff stands unchanged: one
universal image, multiple first stages, Syslinux for legacy-BIOS removable boot, UEFI
files for modern x86, Raspberry firmware for Pi, and GRUB A/B retained on the installed
Acer internal disk.
