# Raspberry Pi 400 / Pi 500 installer — executable closure work order

**Date:** 2026-10-19  
**Status:** IN PROGRESS — partial source implementation, **not bootable/usable**  
**Authority:** ADR 0036; `docs/plans/2026-09-15_MULTIPLATFORM_RELEASE_INSTALL_UPDATE_COMPLETION.md`; `docs/architecture/UNIVERSAL_GREIA_SETUP_MEDIA_ARCHITECTURE.md`. This note is a work order, not a competing architecture.

## Audit finding

Do not conflate typed Pi profile schema, native tryboot fakes, or role-model partition plans with usable hardware support. The current default branch previously had none of the indispensable arm64 boot/root composition, Pi firmware FAT media, native Pi fresh-install boot finalization or physical Pi 400/500 acceptance. The current x86 BIOS installer is not cross-architecture.

## Implemented in the 2026-10-19 feature branch

- Pi DOS partition adapter emits a complete command array for P1 256 MiB FAT32 boot-control/recovery, P2 256 MiB FAT32 BOOT_A, P3 256 MiB FAT32 BOOT_B, P4 extended, P5/P6 ext4 system slots and P7 ext4 PERSIST.
- Pi alignment accounting includes three extra 1 MiB logical-EBR reservations; canonical disk-minimum computation and PERSIST remainder incorporate them; invalid exact-fit targets refuse.
- Post-layout DOS identity observer is shared with the legacy MBR adapter; role partition numbers remain enforced (Pi uses 5/6/7).
- Pi layout tests use only a command-recording fake and never perform device writes.
- **Safety gate:** the full fresh-install orchestrator refuses non-GRUB backends *before any destructive partition command* until Pi-specific finalization exists. This is intentional and must not be removed merely to make tests green.

## Remaining production work (required before declaring Pi support)

1. **Pi profiles:** add declarative Pi 400 and Pi 500 ARM64 A/B profiles with native boot adapters; make the composition-engine/package maps deliberately support them rather than weakening `check_phase0_builder_support`. Select and lock real kernel/firmware/DTB assets for Pi 4/BCM2711 and Pi 5/BCM2712; cross-build on supported Debian host with binfmt/qemu-user or native arm64; fail on missing packages/DTBs.
2. **ARM system release:** compose full relocatable Greia arm64 ext4 system slots with current Python/SDL/Pygame runtime and four released locale assets, boot hooks/services and kernel modules. Build matching `.greiaupdate` v3 complete payloads. Run read-only completeness and capacity/footprint checks.
3. **Pi live setup boot:** build Pi 400 and Pi 500 firmware/kernel/DTB/initramfs boot paths on the *same public universal* FAT32 Setup partition used by existing BIOS/SYSLINUX and future amd64 UEFI. ARM live SquashFS on P2 must mount by physical media identity without `toram`; supply sufficient drivers for Pi USB-MSD and target SD MMC.
4. **Board selection/target policy:** discriminate Pi 400 and Pi 500 from device tree exactly. Probe the EEPROM USB boot capability; never silently edit EEPROM. Verify built-in microSD host via sysfs topology, positive CID/size identity and medium ancestry; specifically prove USB install stick cannot appear as install target. Test microSD hot insertion after USB boot on each board.
5. **Native installed boot:** construct board-specific BOOT_A and BOOT_B FAT files containing complete signed-off kernel/initramfs/DTB/overlays/firmware, `cmdline.txt` with the **observed** corresponding system-root PARTUUID, and P1 recovery assets with at least 32 MiB headroom in every FAT filesystem. Write initial P1 `autoboot.txt` with `[all]`, `tryboot_a_b=1`, `boot_partition=2`, `[tryboot]`, `boot_partition=3`. No GRUB. Do not mark ready until verified boot assets and PERSIST/journal survive restart.
6. **Native tryboot backend:** implement production `BootTransactionBackend` using actual firmware `reboot '0 tryboot'`, observed chosen boot partition and tryboot flags; one-shot candidate, health acceptance and durable normal/tryboot swap, fallback, power-cut fault tests and P1 recovery path. The existing `FakePiTrybootBackend` is not production boot support.
7. **Universal-media assembly:** combine i386 BIOS/SYSLINUX, amd64 UEFI, Pi 400 and Pi 500 boot payloads with their architecture-specific live roots and releases into one `greia-setup-<version>.img` (optionally `.img.xz`). Enforce the **7,400,000,000-byte** size cap; USB read-back and image integrity; do not release separate substitute Pi installers.
8. **Full preflight and transaction wiring:** only after items 1–7 work, replace the early Pi refusal with a selected `PiBootInstaller` behind the current installation transaction, maintaining the same eligible-target identity refresh, profile/release matching, capacity gate, post-layout observation, SlotWriter/SlotFinalizer, PERSIST setup and first-boot acceptance.
9. **Acceptance:** locally run `make verify`, Pi isolated source tests, loop/disposable-image DOS geometry proof, exact-image QEMU aarch64 where possible. Physically install on **Pi 400 and Pi 500 independently**, reboot to Shell/profile picker, verify display/audio/touch/keyboard/WiFi, four languages, parent management, poweroff, updates and rollback including corrupted B and interrupted writes. Label tests by source/QEMU/physical level; do not claim acceptance from unit tests alone.

## Local agent safe first run

On a clean checkout of the feature branch:

```bash
export PYTHONDONTWRITEBYTECODE=1
PYTHONPATH=src python3 -m unittest tests.test_pi_installer_layout tests.test_installer_layout -v
make verify
```

Prerequisites: Python 3.12+ and project development dependencies. No disk devices or USB/SD media need to be present. **Do not** run partition scripts against physical disks; recording-runner tests must contain no `wipefs`, `parted` or `mkfs` executions outside fakes. Stop on first test failure; capture the full command/output/exit code and current commit SHA. If tests fail, do not mark support implemented. On actual Pi hardware, do not authorize live erasure until separate owner approval and the complete boot preflight exists.

## Official boot behavior to uphold

See Raspberry Pi's native `autoboot.txt` and `tryboot` documentation: `https://www.raspberrypi.com/documentation/computers/config_txt.html#autoboottxt`. Pi 400 uses Pi-4-family firmware/kernel; Pi 500 requires Pi-5-family device-tree/kernel choice. Do not use a single `kernel8.img` assumption without checking the selected board and built assets.
