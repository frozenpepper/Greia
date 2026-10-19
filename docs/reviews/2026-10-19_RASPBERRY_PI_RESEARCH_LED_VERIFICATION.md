# Greia Pi 400/500 — research-led adversarial verification (2026-10-19)

**Baseline:** main 43045003e39c4d020647309760d19a41182b98f3.  
**Scope:** native Raspberry Pi 400/500 FAT/MBR A/B install design, offline boot assets, disk eligibility and future firmware acceptance.  
**Research evidence:** official Raspberry Pi configuration/kernel/EEPROM documentation; the Raspberry Pi rpi-image-gen A/B release and slot-mapper guidance; reported Raspberry Pi firmware failures in public forum/issue tracker.  
**Execution evidence:** isolated Python 3.13 harness for the new read-only firmware observation module with replacement implementations of two existing dependencies (8/8 PASS). No genuine Greia repository test execution, image build, loopback partitioning, QEMU or Pi hardware was available. NO Pi production install is enabled.

## Research findings, evidence and consequences

### R1 — tryboot is a native primitive, not an entire rollback guarantee (CRITICAL)

Raspberry Pi's official [autoboot.txt documentation](https://www.raspberrypi.com/documentation/computers/config_txt.html#autoboottxt) confirms the intended three-FAT A/B scheme: first FAT holds autoboot.txt, the next two are A/B boot; the normal and trial mappings select different FAT partitions, and sudo reboot '0 tryboot' uses the one-shot setting. On health failure the flag clears on a normal reboot. The chosen partition is exposed at /proc/device-tree/chosen/bootloader/partition and trial flag at .../tryboot, both **four-byte big-endian binary** rather than printable text.

**Greia consequence:** boot-control strings generated in pi_boot_assets.py match the published example, but reading string values such as '1'/'3', using a stale recorded slot, or treating kernel-root selection as evidence of a correctly mounted system would be incorrect. This pass adds a **read-only** PiBootObservation class that decodes big-endian evidence, compares it to canonical autoboot.txt and the two observed MBR root PARTUUIDs, and rejects contradictory combinations. It does NOT mark the boot healthy or update autoboot.txt. Actual boot-device ancestry, mounted root, finalized slot receipts and Shell health remain prerequisites to a production transaction.

### R2 — corrupted P1 and firmware-dependent fallback behavior (CRITICAL)

Raspberry Pi engineers discussed corruption of autoboot.txt and cases where firmware instead falls back to config.txt or fails to boot ([forum discussion](https://forums.raspberrypi.com/viewtopic.php?t=382903)). The official [EEPROM release notes](https://github.com/raspberrypi/rpi-eeprom/blob/master/firmware-2712/release-notes.md) document January 2025 partition-walking behavior intended to rescue such systems. [EEPROM configuration](https://www.raspberrypi.com/documentation/computers/raspberry-pi.html) describes PARTITION_WALK=1 and its search for valid start4.elf on Pi 4 versus config.txt and DTB on Pi 5.

**Greia consequence:** never describe P1/autoboot recovery as established until BOTH Pi 400 and Pi 500 with their **observed EEPROM versions** demonstrate: missing P1 file, truncated P1 file, invalid P1 file, power interruption around durable commit, corrupt BOOT_B, corrupt SYSTEM_B, and invalid recovery partition. Do not rely on PARTITION_WALK implicitly and do not rewrite EEPROM silently. EEPROM behavior is a per-firmware compatibility requirement, not a property proved by Python unit tests.

### R3 — real A/B GPT failures and FAT partition ordering (HIGH)

[Raspberry Pi firmware issue #818 (2026)](https://github.com/raspberrypi/rpi-eeprom/issues/818) contains reported tryboot failure on CM5 with GPT, EEPROM loops, and a later report that arranging FAT partitions contiguously resolved the failure for one configuration. Raspberry Pi maintainers also report rpi-image-gen GPT working for their own A/B images. Therefore neither “GPT always broken” nor “any GPT/MBR A/B works” is justified.

**Greia consequence:** the existing MBR P1/P2/P3 contiguous FAT, P4 extended, P5/P6/P7 root/data design remains a reasonable first candidate. Do not redesign it preemptively, but require physical test of Pi 400 and Pi 500 **on this exact seven-partition geometry** and actual tryboot cycles. Test firmware with a known working baseline Raspberry Pi A/B image when diagnosing a bootloader limitation separately from Greia.

### R4 — slot identity must be tied to the actual boot device (CRITICAL)

The official Raspberry Pi [rpi-ab-slot-mapper documentation](https://raspberrypi.github.io/rpi-image-gen/layer/rpi-ab-slot-mapper.html) uses boot-disk-backed ancestry, stable by-slot references and explicit active/other boot/system mapping. [rpi-image-gen releases](https://github.com/raspberrypi/rpi-image-gen/releases) mention persistent partition and boot device membership fixes, including handling partitions even when a filesystem is corrupt.

**Greia consequence:** a plausible root=PARTUUID hint and firmware boot_partition=3 do not prove the current running root or mounted P1 belongs to the same physical card as the chosen boot partition. Before health acceptance, resolve sysfs ancestry for firmware-selected boot device, actual / mount, BOOT_A/B, SYS_A/B and PERSIST; bind all to the same current disk and *observed* MBR signature. Do not identify devices by label alone, /dev/mmcblk0 alone, or a recorded slot name. Avoid writing the accepted default based only on the new PiBootObservation class.

### R5 — USB setup versus existing SD and EEPROM boot order (HIGH)

The official [BOOT_ORDER documentation](https://www.raspberrypi.com/documentation/computers/raspberry-pi.html) describes low-nibble-first preference and USB-MSD/SD choices; [USB boot guidance](https://www.raspberrypi.com/documentation/computers/raspberry-pi.html) notes compatibility/power/device selection limitations. Parent-facing reinstall instructions must not assume a populated, bootable SD is ignored in favor of the Setup USB.

**Greia consequence:** retain the accepted blank/unbootable SD + setup-USB route and explicit remove/insert or external-reader recovery path with hardware verification. Physical tests must include: SD absent, blank SD, previously bootable SD, USB flash drives that initialize late, and a USB flash-drive and SD visible simultaneously. Pi's built-in MMC host must always be distinguished positively from the installer USB.

### R6 — model filters, kernel and DTB pairings are documented, but not interchangeable (HIGH)

The official [config.txt model-filter table](https://www.raspberrypi.com/documentation/computers/config_txt.html#conditional-filters) confirms both [pi400] and [pi500] are valid; [pi500] also covers 500+, but Greia's supported target remains 500. The [kernel documentation](https://www.raspberrypi.com/documentation/computers/linux_kernel.html) distinguishes Pi 400 kernel8.img and Pi 500 kernel_2712.img; Pi 500 optimized kernels can use a 16 KiB page size. The official [firmware asset tree](https://github.com/raspberrypi/firmware/tree/master/boot) contains bcm2712-rpi-500.dtb and the Pi4/Pi5 family boot artifacts. The [Linux arm64 Image specification](https://www.kernel.org/doc/html/latest/arch/arm64/booting.html) defines the header and page-size flags.

**Greia consequence:** the existing filtered config.txt and model-specific filenames are **source-aligned** to documentation. However, SHA + ARM64 magic + FDT header is not proof the image has correct /lib/modules, DT overlay fragment support or page-size compatibilities. On ARM release construction, verify kernel release from actual Image build metadata, modules and firmware/DTB provenance, and boot both boards. Never rename arbitrary Debian vmlinuz and declare Pi boot support.

### R7 — partial updates must not damage persistent user data (CRITICAL)

The Raspberry Pi image-gen update work explicitly uses independent boot+system slots and shared persistent state; the release history contains fixes for persistent partition robustness ([release notes](https://github.com/raspberrypi/rpi-image-gen/releases), [A/B layer docs](https://raspberrypi.github.io/rpi-image-gen/layer/rpi-ab-slot-mapper.html)). Their [issue tracker](https://github.com/raspberrypi/rpi-image-gen/issues) includes reports of shared-directory synchronization deleting persistent data; reports are investigation leads, not proof that Greia has the same bug.

**Greia consequence:** verify that a failed candidate update never overwrites or deletes accepted children/profiles/progress, and that PERSIST is not formatted or reshaped during normal A/B update. After applying an update to SYSTEM_B, test refusal/recovery with damaged candidate and power cut while preserving PERSIST checksums. Never infer data safety from a successful boot alone.

## Code changes made by this pass

1. **Typed MMC CID shape:** Pi target eligibility now insists on 32 hexadecimal characters and positive built-in sysfs MMC host evidence, not any nonempty string. Existing fake-card geometry fixture updated to use a valid CID and a negative CID test added. No new hardware privileges or generic MMC override.
2. **Read-only native firmware evidence:** new src/greia_platform/pi_boot_observation.py decodes four-byte big-endian device-tree bootloader properties; parses the single root=PARTUUID= Linux kernel argument; matches selected FAT P2/P3 to root P5/P6 of a common MBR signature, and honors the accepted/trial autoboot mapping. Rejects inconsistent evidence. It cannot reboot or modify firmware/boot partitions.
3. **Eight tests:** new tests/test_pi_boot_observation.py covers normal, trial, accepted B, reverse trial, selected-partition mismatch, wrong root, wrong disk, malformed binary property, duplicate root, recovery/unexpected partition and invalid tryboot flag.

## Verification scope

**Actually executed in this assistant's Linux Python 3.13 environment:** local syntax compilation of the new source and tests, and a focused unittest run after correcting two test expectation mistakes: **8 tests PASS**. The local harness imported the exact new module content but used temporary stand-in implementations of persistent_layout.normalize_mbr_partuuid / split_mbr_partuuid and pi_boot_assets.render_pi_autoboot / parse_pi_autoboot because the complete private Greia source was not available in the container. Therefore this is **ISOLATED NEW-MODULE TESTING, not Greia integration tests**. No GUI, real block device, firmware, image build, tests on full actual repo, or hardware was exercised.

The canonical next tests on the local agent's full checkout:

    export PYTHONDONTWRITEBYTECODE=1
    PYTHONPATH=src python3 -m unittest \
        tests.test_pi_boot_observation tests.test_pi_mmc_host_probe \
        tests.test_pi_installer_layout tests.test_pi_boot_assets \
        tests.test_pi_build_profiles tests.test_installer_layout \
        tests.test_installer_disk -v
    make verify

Stop at first failure, preserve stdout/stderr and exact SHA. Use no privileged physical-drive actions. After source tests, run read-only physical Pi board/EEPROM/MMC topology diagnostics, then disposable loop-backed DOS geometry, followed by complete ARM live boot/installer wiring and separate physical card acceptance. Do not run any target erase until the native install transaction, firmware boot, P1 recovery and USB setup flow are implemented and owner-authorized.

## Risk priority / next implementation order

**P0:** complete ARM native installed boot, boot-device binding, P1 recovery, durable autoboot commit, and rollback; do not weaken the existing early pre-wipe refusal.  
**P1:** ARM64 target+live image composition for each board and the single public BIOS+UEFI+Pi universal image; prove exact media boot and budget.  
**P1:** physical firmware version inventory on Pi 400/500, native tryboot, PARTITION_WALK/recovery and USB/SD boot-order tests.  
**P1:** source tests/loopback geometry and actual FAT free-space proof.  
**P2:** module/DTB release manifest bindings, 4K/16K ABI checks, resource use, and all Greia Activity/locale/peripheral acceptance.

**Conclusion:** the design choices are aligned with important official Raspberry Pi mechanisms, but there is real upstream evidence that plausible A/B configs can fail depending on partition ordering and firmware. The Pi installer remains NOT BOOTABLE / NOT COMPLETED. No hardware success is claimed.
