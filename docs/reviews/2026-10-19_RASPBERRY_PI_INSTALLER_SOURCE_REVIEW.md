# Greia Raspberry Pi installer — independent source review and refinement

**Date:** 2026-10-19  
**Scope:** the earlier WIP Pi 400/500 implementation in draft PR #10, audited against current `main`, ADR 0036 and the accepted multiplatform lifecycle plan.  
**Evidence:** GitHub source inspection; platform and kernel boot-format documentation. **No compiled image, project tests, loop partition run or physical Pi was executed.**

## Critical original failure: a staged blob was overwritten before commit

The earlier PR claimed `PiMbrTrybootAbAdapter` was executable, 256 MiB FAT boot partitions existed and Pi EBR overhead was charged. Inspection of the **actual committed SHA** `9f209139` showed the old `_DeferredExecutionAdapter`, `BOOT_BYTES = 64 * MIB`, and no Pi `build_commands`. The intended implementation existed only as an earlier uncommitted Git blob. A later new-blob write against the old base file replaced it when the tree was committed. This is a verifiable source/claim mismatch, not a hardware limitation.

**Remedy in this refinement:** reconstruct the executable adapter from the intended implementation, apply storage-minimum accounting to that **same content** and add the missing Pi destination policy check. Apply the unified new file to `main`. Tests are intentionally source-only until run by the local operator. Future agents must inspect **the resulting committed file** (and diff) rather than assume every generated blob was included.

## Other confirmed defects

1. **Pi target never appears / removable card denied.** `LsblkDiskProbe` used no sysfs MMC host observer, so `mmc_host_built_in` was always false, and `InstallTargetPolicy.evaluate` denied removable/hotplug before the Pi-specific policy could apply. Added `PiMmcHostObserver`: strict Pi 400/500 model, platform MMC ancestry, real card CID, and USB ancestry exclusion. The Pi policy alone may accept a removable microSD when those positive conditions hold; external USB stays rejected.
2. **Digest does not prove a kernel can be booted.** The offline stager copied `boot/vmlinuz-greia` under a Pi firmware kernel name based only on SHA. A compressed x86/generic Debian vmlinuz could pass SHA verification and fail firmware boot. Added an uncompressed AArch64 Image header check at byte offset 0x38. It is a necessary format preflight, **not** proof of correct modules, DTB or physical boot.
3. **Missing Pi disk safety in adapter.** Original executable candidate accepted any absolute whole-disk locator; now requires the Pi built-in-microSD policy before it emits destructive commands. This defense-in-depth does not replace the session's live-USB ancestry and refreshed target identity checks.
4. **Pi 400 vs Pi 500 requires distinct assets.** Pi 400 firmware's `kernel8.img` / BCM2711 and Pi 500 `kernel_2712.img` / BCM2712 and page-size/module/DTB compatibility are not interchangeable. Boot staging remains board-specific with no unknown board fallback. Main Debian `linux-image-arm64` may **not** be a suitable native Pi firmware image just because it installs on arm64.
5. **Fake Pi tryboot != production firmware boot.** `FakePiTrybootBackend` uses its own plain-text `boot_partition` fixture and a `tryboot.json` simulation; it is not the native tryboot backend. Offline `render_pi_autoboot` uses real `[all]`/`[tryboot]` partition selection. Do not connect fake backend to installation.
6. **Incomplete image/lifecycle path remains blocking.** The Phase 0 image composer rejects ARM64; no Pi firmware+live root is published; full fresh installer still runs GRUB for implemented x86 backends and deliberately refuses Pi **before erase**. P1 recovery, firmware sync/verification, update tryboot health/rollback and physical acceptance are not implemented. Preserve this refusal until they are.
7. **Documentation/workflow drift.** Core Greia work must follow `AGENTS.md`'s main-branch policy, not the unauthorized feature/draft PR created previously. The accepted 2026-09-15 lifecycle plan is the active owner; this report is subordinate, not a second roadmap.

## Important unproven risks to resolve before destructive Pi acceptance

- **DOS extended/EBR behavior on physical storage.** P4/P5-P7 commands are now generated, but exact `parted` extents, partition numbering, filesystem alignment, usable PERSIST bytes and MBR firmware partition walking require a disposable loop-image test followed by physical Pi proof. A role-model size proof is not the same as the actual formatted partition size.
- **Identity races and hot-swap:** verify that inserting a microSD after USB boot populates sysfs and that a removed/reinserted card is reidentified by CID and current major:minor before any write. Never use a stale `/dev/mmcblk0` locator. If the Pi board/host is unrecognized, show zero eligible targets rather than enable generic `allow_mmc`.
- **Installer-versus-live media:** ensure P2 `GREIA_SETUP_DATA` is mounted with the exact expected live-media-id and its USB parent whole disk is excluded; multiple setup devices mean zero targets. Verify the Pi firmware USB boot EEPROM setting without modifying it.
- **Kernel ABI and firmware:** supply a native ARM64 Image, initramfs and `/lib/modules/<uname-r>` that belong to the same build; include the board-matched DTB and KMS overlay. Pi 500 optimized 16 KiB configuration may affect packages, SDL/KMS and memory; measure rather than infer. Offline stager's check is insufficient to release.
- **FAT boot pair and recovery:** P1 must contain a bootable recovery kernel/initramfs, not just `autoboot.txt`. P2/P3 require observed root PARTUUID and at least 32 MiB FAT free space **after formatting**. Test missing/truncated/zero `autoboot.txt`, loss of power around FAT rename/sync, corrupt B boot/system, kernel hang before health, and acceptance only after Greia Shell/profile-selection readiness.
- **One public image:** the x86 path must remain bootable while adding Pi boot firmware on the same active FAT partition. The entire universal image must fit <=7,400,000,000 bytes. Multiple architectures on the media must not cause i386 `toram`/RAM inflation.
- **Nontechnical product:** parental installer UX must remain graphical, localized into en/it/es/fr, safe for a novice, and never reveal the Linux shell or a destructive default selection.

## Review of change structure

The Pi partition adapter stays behind `LayoutAdapter`; Pi positive MMC topology stays in the shared typed disk-probe/policy seam, not `if device.startswith('/dev/mmcblk0')` in the UI; boot assets stay an offline `PiBootAssetStager` consuming existing `BootArtifactSet`. Do **not** create a parallel release format, second graphical installer, or independent Pi Activity runtime.

## Verification and next actions

Source-only tests provided (not executed): `tests.test_pi_installer_layout`, `tests.test_pi_boot_assets`, `tests.test_pi_build_profiles`, `tests.test_pi_mmc_host_probe`, and existing `tests.test_installer_layout`, `tests.test_installer_disk`, `tests.test_build_profiles_storage`. Exact operator command:

```bash
export PYTHONDONTWRITEBYTECODE=1
PYTHONPATH=src python3 -m unittest \
  tests.test_pi_installer_layout \
  tests.test_pi_boot_assets \
  tests.test_pi_build_profiles \
  tests.test_pi_mmc_host_probe \
  tests.test_installer_layout \
  tests.test_installer_disk \
  tests.test_build_profiles_storage -v
make verify
```

Prerequisites: Python 3.12+ and repo dependencies installed per `SETUP.md`. Stop at first failure; capture exit code, full stdout/stderr, `git rev-parse HEAD`, and `git status --short`. Do not run `build_commands` against actual disks. Do not spend hosted Actions or cloud provider money without owner approval. With source tests green, authorize **disposable loopback** `parted` geometry validation only; still no physical card erasure until complete ARM boot chain and separate owner-approved acceptance procedure.

Reference material: Raspberry Pi config and tryboot docs https://www.raspberrypi.com/documentation/computers/config_txt.html ; Raspberry Pi native kernels https://www.raspberrypi.com/documentation/computers/linux_kernel.html ; AArch64 raw Image header https://www.kernel.org/doc/html/latest/arch/arm64/booting.html .

## 2026-10-19 — follow-up verification pass 2 (post-commit, `e37aa437` baseline)

**Scope:** actual `main` source and previously committed Pi tests; official Raspberry Pi autoboot/kernel documentation. **Evidence:** source inspection plus locally executed isolated Python reproduction of the frozen+slotted-dataclass `super()` failure; **no actual Greia test suite/installer image was run**.

### Confirmed runtime defect repaired

`PiBuiltInMicroSdTargetPolicy` is `@dataclass(frozen=True, slots=True)` and previously called zero-argument `super()._removable_rejection(observation)` in the fallback path. Python dataclasses synthesize a replacement class when `slots=True`, so `super()` can raise `TypeError: super(type, obj): obj must be an instance or subtype of type`. Reproduced independently with the same `@dataclass(frozen=True, slots=True)` subclass pattern in Python. This was on the **negative SD-destination path**, where a removable card lacks proven built-in MMC + CID; instead of a controlled “not eligible” result, evaluation raised.

**Fix:** explicit `InstallTargetPolicy._removable_rejection(self, observation)` delegation. Added focused no-exception rejection regression and integration test that passes `lsblk` JSON through the **actual** `LsblkDiskProbe`, injected Pi 500 sysfs fixture/CID, Pi target policy, and inventory eligible-target filtering with a USB device present. This checks an end-to-end detection path absent from the previous hand-built `DeviceObservation` tests.

### Boot file format check tightened

Previous stager/tests treated `b"dtb"` and `b"kms"` as acceptable board DTB and KMS overlay files, so an obviously unbootable file could be staged successfully under a plausible name. The stager now requires an FDT magic header, a 40-byte minimum header and consistent declared total size for both `.dtb` and `.dtbo`. Added negative cases for 3-byte DTB and length-mismatched overlay; synthetic valid headers in positive tests prove only this boundary.

**Limit:** FDT container validation does *not* confirm the board's `compatible` metadata, overlay correctness, firmware/kernel-module ABI, live hardware detection or actual boot. Those remain acceptance blockers; do not downgrade them to “verified” because a file has FDT magic.

### Other source checks

- Re-read `PiMbrTrybootAbAdapter` on actual `main`: it now subclasses `LayoutAdapter` and emits P1/P2/P3 FAT, P4 extended, P5/P6/P7 logical ext4 commands; output still unexecuted against `parted` or loopback. Its target policy recheck exists and the early, no-erasure Pi refusal remains in `fresh_ab_install.py`.
- Checked the `[all]` + `tryboot_a_b=1` + `[tryboot]` selection and Pi 400 `kernel8.img` vs Pi 500 `kernel_2712.img` against Raspberry Pi official documentation (see references below). Source agreement is **not** physical firmware behavior evidence.
- Only source files and tests were changed. ARM64 live/root composition and production Pi A/B firmware boot, recovery and the required one public universal image remain absent.

### Integration risks newly made explicit

- The current fresh-install request requires a **GRUB password hash** and its result exposes `grub_config_text`. The future Pi boot installation must replace these x86-only transaction assumptions polymorphically rather than feeding fabricated GRUB values to satisfy a shared request shape.
- The current boot-asset stager proves kernel/initramfs receipt hashes but does not bind the supplied firmware/DTB/overlay files to a trusted per-board release manifest. Implement release/board compatibility verification when the ARM image composer is integrated; a directory name alone is not a release binding.
- Current Pi MBR P7 extends to `100%` and its theoretical PERSIST remainder calculation may differ slightly from actual filesystem usable bytes due to partition/FS rounding. The exact minimum-size boundary remains **source-modeled** and requires a disposable loop-device geometry/filesystem check, not a source-only PASS.
- During physically safe tests, verify sysfs path/model/CID on Pi 400 and Pi 500 separately. The strict board-specific MMC observer can intentionally refuse any unrecognized host; no generic allow-MMC fallback.
- The Pi 500 kernel optimization can use 16 KiB pages, while common Pi 400 ARM64 kernels use 4 KiB; a matching AArch64 Image magic does not prove kernel/userland/firmware compatibility.

### Required next real verification

On the exact committed `main` SHA with Python >=3.12 and dependencies installed via `SETUP.md`:

```bash
export PYTHONDONTWRITEBYTECODE=1
PYTHONPATH=src python3 -m unittest \
    tests.test_pi_installer_layout \
    tests.test_pi_boot_assets \
    tests.test_pi_build_profiles \
    tests.test_pi_mmc_host_probe \
    tests.test_installer_layout \
    tests.test_installer_disk \
    tests.test_build_profiles_storage -v
make verify
```

Stop at first failure, return full stdout/stderr, command RC, pinned `git rev-parse HEAD`, and `git status --short`. **Do not run destructive commands on a physical disk.** Only a subsequent owner-authorized disposable loop test can validate the planned geometry, and only a full native Pi media implementation followed by explicit authorization can permit hardware installation. This pass remains SOURCE REVIEW / local Python isolated reproduction, *not* repository tests green or installer complete.

Official references: https://github.com/raspberrypi/documentation/blob/master/documentation/asciidoc/computers/config_txt/autoboot.adoc and https://www.raspberrypi.com/documentation/computers/linux_kernel.html .
