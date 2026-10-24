"""Intel Mac / UEFI boot plan (UNPROVEN / LAB): layouts, firmware, GRUB, media."""

from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from greia_installer.efi_boot import (
    BiosSingleExt4Layout,
    EfiBootError,
    FirmwareInterface,
    SingleRootLayoutSelector,
    SysfsFirmwareProbe,
    UefiOrBiosGptExt4Layout,
    plan_efi_boot,
    target_profile_supports_efi,
)
from greia_installer.engine import InstallRequest, InstallationEngine, InstallationError
from greia_installer.disk import DeviceObservation, DiskInventory
from greia_installer.device_seams import build_bios_bootloader_installer
from test_installer_engine import RecordingRunner, settings, target

ROOT = Path(__file__).resolve().parents[1]
DEV = Path("/dev/sda")


def fake_sysfs(tmp: Path, *, efi: bool, bits: str | None = None, cpu_flags: str = "fpu lm") -> SysfsFirmwareProbe:
    efi_root = tmp / "efi"
    if efi:
        efi_root.mkdir()
        if bits is not None:
            (efi_root / "fw_platform_size").write_text(bits + "\n")
    cpuinfo = tmp / "cpuinfo"
    cpuinfo.write_text(f"processor\t: 0\nflags\t\t: {cpu_flags}\n")
    return SysfsFirmwareProbe(efi_root=efi_root, cpuinfo=cpuinfo)


class FirmwareDetectionTests(unittest.TestCase):
    def test_bios_when_no_efi_directory(self) -> None:
        with tempfile.TemporaryDirectory() as t:
            fw = fake_sysfs(Path(t), efi=False).probe()
        self.assertFalse(fw.uefi)
        self.assertIsNone(fw.efi_bits)

    def test_bitness_32_and_64(self) -> None:
        with tempfile.TemporaryDirectory() as t:
            self.assertEqual(fake_sysfs(Path(t), efi=True, bits="32").probe(),
                             FirmwareInterface(True, 32))
        with tempfile.TemporaryDirectory() as t:
            self.assertEqual(fake_sysfs(Path(t), efi=True, bits="64").probe(),
                             FirmwareInterface(True, 64))

    def test_missing_size_file_assumes_64_unless_cpu_lacks_lm(self) -> None:
        with tempfile.TemporaryDirectory() as t:
            self.assertEqual(fake_sysfs(Path(t), efi=True).probe().efi_bits, 64)
        with tempfile.TemporaryDirectory() as t:
            self.assertEqual(
                fake_sysfs(Path(t), efi=True, cpu_flags="fpu pae").probe().efi_bits, 32)

    def test_garbage_size_file_follows_same_fallback(self) -> None:
        with tempfile.TemporaryDirectory() as t:
            self.assertEqual(fake_sysfs(Path(t), efi=True, bits="banana").probe().efi_bits, 64)

    def test_invalid_interface_refused(self) -> None:
        with self.assertRaises(EfiBootError):
            FirmwareInterface(True, 16)
        with self.assertRaises(EfiBootError):
            FirmwareInterface(False, 32)

    def test_profile_capability_from_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as t:
            path = Path(t) / "p.json"
            path.write_text(json.dumps({"package_sets": {"target": ["boot-grub-efi"]}}))
            self.assertTrue(target_profile_supports_efi(path))
            path.write_text(json.dumps({"package_sets": {"target": ["boot-grub-pc"]}}))
            self.assertFalse(target_profile_supports_efi(path))
            self.assertFalse(target_profile_supports_efi(Path(t) / "missing.json"))
            path.write_text("not json")
            self.assertFalse(target_profile_supports_efi(path))


class LayoutTests(unittest.TestCase):
    def test_bios_layout_commands_are_the_historical_ones(self) -> None:
        layout = BiosSingleExt4Layout()
        self.assertEqual(layout.partition_commands(DEV), [
            ["parted", "--script", "/dev/sda", "mklabel", "msdos"],
            ["parted", "--script", "/dev/sda", "mkpart", "primary", "ext4", "1MiB", "100%"],
            ["parted", "--script", "/dev/sda", "set", "1", "boot", "on"],
        ])
        self.assertEqual(layout.root_partition(DEV), Path("/dev/sda1"))
        self.assertEqual(layout.format_commands(DEV), [])
        self.assertFalse(layout.uses_efi)

    def test_uefi_plan_sizes_types_and_order(self) -> None:
        layout = UefiOrBiosGptExt4Layout()
        roles = [(p.number, p.role, p.filesystem, p.start_mib, p.end_mib, p.flags)
                 for p in layout.partitions]
        self.assertEqual(roles, [
            (1, "bios-boot", "none", 1, 2, ("bios_grub",)),
            (2, "esp", "fat32", 2, 258, ("esp",)),
            (3, "root", "ext4", 258, None, ("legacy_boot",)),
        ])
        self.assertEqual(layout.root_partition(DEV), Path("/dev/sda3"))
        self.assertEqual(layout.esp_partition(Path("/dev/nvme0n1")), Path("/dev/nvme0n1p2"))

    def test_uefi_commands_are_argument_arrays_in_order(self) -> None:
        layout = UefiOrBiosGptExt4Layout()
        cmds = layout.partition_commands(DEV)
        self.assertEqual(cmds[0], ["parted", "--script", "/dev/sda", "mklabel", "gpt"])
        self.assertIn(["parted", "--script", "/dev/sda", "mkpart", "bios-boot", "1MiB", "2MiB"], cmds)
        self.assertIn(["parted", "--script", "/dev/sda", "mkpart", "esp", "fat32", "2MiB", "258MiB"], cmds)
        self.assertIn(["parted", "--script", "/dev/sda", "mkpart", "greia-root", "ext4", "258MiB", "100%"], cmds)
        self.assertIn(["parted", "--script", "/dev/sda", "set", "1", "bios_grub", "on"], cmds)
        self.assertIn(["parted", "--script", "/dev/sda", "set", "2", "esp", "on"], cmds)
        self.assertTrue(all(isinstance(c, list) and all(isinstance(a, str) for a in c) for c in cmds))
        self.assertEqual(layout.format_commands(DEV),
                         [["mkfs.vfat", "-F", "32", "-n", "GREIA_EFI", "/dev/sda2"]])

    def test_bios_layout_has_no_esp(self) -> None:
        with self.assertRaises(EfiBootError):
            BiosSingleExt4Layout().esp_partition(DEV)

    def test_selection_matrix(self) -> None:
        sel = SingleRootLayoutSelector()
        bios, efi = FirmwareInterface(False), FirmwareInterface(True, 64)
        self.assertIsInstance(sel.select(bios, target_supports_efi=True), BiosSingleExt4Layout)
        self.assertIsInstance(sel.select(efi, target_supports_efi=False), BiosSingleExt4Layout)
        self.assertIsInstance(sel.select(efi, target_supports_efi=True), UefiOrBiosGptExt4Layout)


class GrubCommandTests(unittest.TestCase):
    def test_ia32_native_and_fallbacks(self) -> None:
        plan = plan_efi_boot(FirmwareInterface(True, 32), DEV, 2)
        self.assertEqual(plan.fatal[0], (
            "chroot", "{root}", "grub-install", "--target=i386-efi",
            "--efi-directory=/boot/efi", "--boot-directory=/boot", "--no-nvram",
            "--bootloader-id=greia", "--recheck"))
        targets = [c[3] for c in plan.fatal]
        self.assertEqual(targets, ["--target=i386-efi", "--target=i386-efi", "--target=x86_64-efi"])
        self.assertIn("--removable", plan.fatal[1])
        self.assertIn("--removable", plan.fatal[2])

    def test_x64_native_target_and_loader_path(self) -> None:
        plan = plan_efi_boot(FirmwareInterface(True, 64), DEV, 2)
        self.assertEqual(plan.fatal[0][3], "--target=x86_64-efi")
        nvram = plan.best_effort[0]
        self.assertEqual(nvram[2], "efibootmgr")
        self.assertIn("\\EFI\\greia\\grubx64.efi", nvram)
        self.assertEqual(nvram[nvram.index("--part") + 1], "2")

    def test_bios_grub_command_unchanged(self) -> None:
        from greia_installer.efi_boot import bios_grub_install_command
        self.assertEqual(bios_grub_install_command(DEV), [
            "chroot", "{root}", "grub-install", "--target=i386-pc",
            "--boot-directory=/boot", "--recheck", "/dev/sda"])

    def test_bios_grub_command_uses_verified_boot_control_directory(self) -> None:
        from greia_installer.efi_boot import bios_grub_install_command

        self.assertEqual(
            bios_grub_install_command(
                DEV, boot_directory=Path("/run/greia-install/boot-control")
            ),
            [
                "grub-install",
                "--target=i386-pc",
                "--boot-directory",
                "/run/greia-install/boot-control",
                "--recheck",
                "/dev/sda",
            ],
        )

    def test_bios_bootloader_adapter_rechecks_identity_and_targets_exact_disk(self) -> None:
        boot_directory = Path("/run/greia-install/boot-control")
        target = DeviceObservation(
            name="sda",
            path=DEV,
            size_bytes=8 * 1024**3,
            device_type="disk",
            model="Target",
            serial="SERIAL-BOOT",
            transport="sata",
            removable=False,
            read_only=False,
            mountpoints=(),
            wwn="WWN-BOOT",
        )

        class _Probe:
            calls = 0

            def probe(self):
                self.calls += 1
                return DiskInventory((target,))

        class _Runner:
            def __init__(self, returncode=0):
                self.returncode = returncode
                self.commands = []

            def run(self, command):
                self.commands.append(list(command))
                return SimpleNamespace(returncode=self.returncode)

        probe, runner = _Probe(), _Runner()
        installer = build_bios_bootloader_installer(runner, target_probe=probe)
        installer(target, boot_directory)
        self.assertEqual(probe.calls, 1)
        self.assertEqual(
            runner.commands,
            [[
                "grub-install",
                "--target=i386-pc",
                "--boot-directory",
                str(boot_directory),
                "--recheck",
                str(DEV),
            ]],
        )

    def test_bios_bootloader_adapter_refuses_reenumerated_disk_and_command_failure(self) -> None:
        from greia_installer.fresh_ab_install import FreshAbInstallError

        target = DeviceObservation(
            name="sda",
            path=DEV,
            size_bytes=8 * 1024**3,
            device_type="disk",
            model="Target",
            serial="SERIAL-BOOT-2",
            transport="sata",
            removable=False,
            read_only=False,
            mountpoints=(),
            wwn="WWN-BOOT-2",
        )
        moved = DeviceObservation(
            name="sdb",
            path=Path("/dev/sdb"),
            size_bytes=target.size_bytes,
            device_type="disk",
            model=target.model,
            serial=target.serial,
            transport=target.transport,
            removable=False,
            read_only=False,
            mountpoints=(),
            wwn=target.wwn,
        )

        class _Probe:
            def __init__(self, current):
                self.current = current

            def probe(self):
                return DiskInventory((self.current,))

        class _Runner:
            def __init__(self, returncode):
                self.returncode = returncode
                self.commands = []

            def run(self, command):
                self.commands.append(list(command))
                return SimpleNamespace(returncode=self.returncode)

        moved_runner = _Runner(0)
        moved_installer = build_bios_bootloader_installer(
            moved_runner, target_probe=_Probe(moved)
        )
        with self.assertRaisesRegex(FreshAbInstallError, "identity or locator changed"):
            moved_installer(target, Path("/run/greia-install/boot-control"))
        self.assertEqual(moved_runner.commands, [])

        class _FailedProbe:
            def probe(self):
                raise RuntimeError("inventory unavailable")

        unavailable_runner = _Runner(0)
        unavailable_installer = build_bios_bootloader_installer(
            unavailable_runner, target_probe=_FailedProbe()
        )
        with self.assertRaisesRegex(FreshAbInstallError, "identity could not be rechecked"):
            unavailable_installer(target, Path("/run/greia-install/boot-control"))
        self.assertEqual(unavailable_runner.commands, [])

        failed_runner = _Runner(1)
        failed_installer = build_bios_bootloader_installer(
            failed_runner, target_probe=_Probe(target)
        )
        with self.assertRaisesRegex(FreshAbInstallError, "command failed"):
            failed_installer(target, Path("/run/greia-install/boot-control"))
        self.assertEqual(failed_runner.commands[0][-1], str(DEV))


class FailingNvramRunner(RecordingRunner):
    def run(self, command, *, check=True):
        self.commands.append(list(command))
        if "efibootmgr" in command or "--target=i386-pc" in command:
            if check:
                raise subprocess.CalledProcessError(1, command, "", "efivars not supported")
            return subprocess.CompletedProcess(command, 1, "", "efivars not supported")
        return subprocess.CompletedProcess(command, 0, "", "")


class EngineEfiInstallTests(unittest.TestCase):
    def _engine(self, runner, tmp: Path, *, efi: bool, supports: bool):
        profile = tmp / "profile.json"
        sets = ["boot-grub-pc"] + (["boot-grub-efi"] if supports else [])
        profile.write_text(json.dumps({"package_sets": {"target": sets}}))
        probe = fake_sysfs(tmp, efi=efi, bits="32" if efi else None)
        return InstallationEngine(
            project_root=ROOT, runner=runner, firmware_probe=probe, target_profile_path=profile)

    def test_layout_selected_from_fake_sysfs(self) -> None:
        with tempfile.TemporaryDirectory() as t:
            tmp = Path(t)
            runner = RecordingRunner()
            self.assertIsInstance(self._engine(runner, tmp, efi=True, supports=True)._select_layout()[0],
                                  UefiOrBiosGptExt4Layout)
        with tempfile.TemporaryDirectory() as t:
            self.assertIsInstance(self._engine(RecordingRunner(), Path(t), efi=False, supports=True)._select_layout()[0],
                                  BiosSingleExt4Layout)
        with tempfile.TemporaryDirectory() as t:
            self.assertIsInstance(self._engine(RecordingRunner(), Path(t), efi=True, supports=False)._select_layout()[0],
                                  BiosSingleExt4Layout)

    def test_install_efi_boot_runs_fatal_then_tolerates_nvram_failure(self) -> None:
        with tempfile.TemporaryDirectory() as t:
            tmp = Path(t)
            runner = FailingNvramRunner()
            engine = self._engine(runner, tmp, efi=True, supports=True)
            layout, firmware = engine._select_layout()
            root = tmp / "root"
            esp = root / "boot/efi"
            for rel in ("EFI/BOOT/BOOTIA32.EFI", "EFI/BOOT/BOOTX64.EFI", "EFI/greia/grubia32.efi"):
                (esp / rel).parent.mkdir(parents=True, exist_ok=True)
                (esp / rel).write_bytes(b"x")
            request = InstallRequest(target(), tmp / "p", settings())
            mounted: list[Path] = []
            with mock.patch.object(engine, "_verify_target_identity") as verify:
                engine._install_efi_boot(root, request, layout, firmware, mounted)
            verify.assert_called_once()
            self.assertEqual(mounted, [esp])
            cmds = runner.commands
            self.assertEqual(cmds[0], ["mount", "/dev/sda2", str(esp)])
            grub = [c for c in cmds if "grub-install" in c]
            self.assertEqual([c[c.index("grub-install") + 1] for c in grub],
                             ["--target=i386-efi", "--target=i386-efi", "--target=x86_64-efi",
                              "--target=i386-pc"])
            self.assertEqual(cmds[1][1], str(root))  # {root} materialised
            self.assertTrue(any("efibootmgr" in c for c in cmds))

    def test_missing_efi_binary_is_fatal(self) -> None:
        with tempfile.TemporaryDirectory() as t:
            tmp = Path(t)
            engine = self._engine(RecordingRunner(), tmp, efi=True, supports=True)
            layout, firmware = engine._select_layout()
            with mock.patch.object(engine, "_verify_target_identity"):
                with self.assertRaisesRegex(InstallationError, "EFI boot file"):
                    engine._install_efi_boot(
                        tmp / "root", InstallRequest(target(), tmp / "p", settings()),
                        layout, firmware, [])

    def test_target_without_grub_efi_modules_is_refused(self) -> None:
        with tempfile.TemporaryDirectory() as t:
            with self.assertRaisesRegex(InstallationError, "GRUB i386-efi"):
                InstallationEngine._require_target_efi_grub(Path(t))


class MediaBuildScriptTests(unittest.TestCase):
    script = (ROOT / "build/build-installer-image.sh").read_text()

    def test_mbr_with_esp_and_active_root(self) -> None:
        s = self.script
        self.assertIn('mklabel msdos', s)
        self.assertIn('mkpart primary fat32 1MiB 65MiB', s)
        self.assertIn('set 1 esp on', s)
        self.assertIn('mkpart primary ext4 65MiB 100%', s)
        self.assertIn('set 2 boot on', s)
        self.assertIn('USB_PART="${USB_LOOP}p2"', s)

    def test_both_efi_fallback_images_and_bios_kept(self) -> None:
        s = self.script
        self.assertIn('grub-install --target=i386-pc --boot-directory="$USB_MOUNT/boot"', s)
        self.assertIn("for efi_target in i386-efi x86_64-efi", s)
        self.assertIn("--removable --no-nvram", s)
        self.assertIn("EFI/BOOT/BOOTIA32.EFI", s)
        self.assertIn("EFI/BOOT/BOOTX64.EFI", s)

    def test_one_kernel_cmdline_and_one_grub_cfg_for_bios_and_efi(self) -> None:
        s = self.script
        self.assertEqual(s.count("linux /live/vmlinuz"), 1)
        self.assertIn("linux /live/vmlinuz $LIVE_KERNEL_CMDLINE", s)
        # EFI images read the same /boot/grub/grub.cfg: boot-directory on the ext4 root.
        self.assertEqual(s.count('--boot-directory="$USB_MOUNT/boot"'), 2)
        self.assertIn("boot=live components live-media-path=/live", s)

    def test_package_sets_and_profile_composition(self) -> None:
        pkgs = [l for l in (ROOT / "build/package-sets/boot-grub-efi.txt").read_text().splitlines()
                if l and not l.startswith("#")]
        self.assertEqual(pkgs, ["grub-efi-ia32-bin", "grub-efi-amd64-bin", "efibootmgr", "dosfstools"])
        self.assertNotIn("grub-efi-ia32", [p for p in pkgs if not p.endswith("-bin")] )
        for name in ("legacy-x86-i686", "legacy-x86-i686-dev", "legacy-x86-i686-rc"):
            self.assertIn('"boot-grub-efi"', (ROOT / f"build/profiles/{name}.toml").read_text())
        self.assertIn("dosfstools", (ROOT / "build/package-sets/installer-base.txt").read_text().split())


if __name__ == "__main__":
    unittest.main()
