from __future__ import annotations

import hashlib
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from greia_installer.disk import BlockDevice
from greia_installer.engine import InstallRequest, InstallResult, InstallationEngine, InstallationError
from greia_platform.hardware import HardwareDefaults, HardwareSettings


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def target() -> BlockDevice:
    return BlockDevice(
        name="sda",
        path=Path("/dev/sda"),
        size_bytes=7_500_000_000,
        device_type="disk",
        model="Acer internal drive",
        serial="PRIVATE-SERIAL",
        transport="ata",
        removable=False,
        read_only=False,
        mountpoints=(),
        wwn="PRIVATE-WWN",
        major_minor="8:0",
    )


def settings() -> HardwareSettings:
    defaults = HardwareDefaults.load(PROJECT_ROOT / "runtime" / "hardware-settings.toml")
    return HardwareSettings(
        schema_version=defaults.schema_version,
        touchpad_tap=defaults.touchpad_tap,
        touchpad_speed=defaults.touchpad_speed,
        mouse_speed=defaults.mouse_speed,
        natural_scrolling=defaults.natural_scrolling,
        resolution=defaults.resolution,
    )


class RecordingRunner:
    def __init__(self) -> None:
        self.commands: list[list[str]] = []

    def run(self, command, *, check=True):
        self.commands.append(list(command))
        return subprocess.CompletedProcess(command, 0, "", "")


class StaticGrubHasher:
    def hash(self, secret: str) -> str:
        return "grub.pbkdf2.sha512.10000.STATIC" + secret[:2]


class InstallerEngineTests(unittest.TestCase):
    def test_payload_digest_accepts_valid_sidecar_and_rejects_damage(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            payload = root / "payload.squashfs"
            sidecar = root / "payload.squashfs.sha256"
            payload.write_bytes(b"known payload")
            sidecar.write_text(hashlib.sha256(payload.read_bytes()).hexdigest() + "  payload.squashfs\n")
            InstallationEngine._verify_payload(payload)

            payload.write_bytes(b"damaged payload")
            with self.assertRaisesRegex(InstallationError, "damaged"):
                InstallationEngine._verify_payload(payload)

    def test_explicit_embedded_digest_is_independent_of_payload_sidecar(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            payload = root / "payload.squashfs"
            embedded = root / "expected-payload.sha256"
            payload.write_bytes(b"known payload")
            embedded.write_text(hashlib.sha256(payload.read_bytes()).hexdigest() + "\n")
            InstallationEngine._verify_payload(payload, embedded)
            self.assertFalse(Path(f"{payload}.sha256").exists())

    def test_missing_digest_stops_before_any_disk_command(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            payload = Path(temporary) / "payload.squashfs"
            payload.write_bytes(b"payload")
            runner = RecordingRunner()
            engine = InstallationEngine(project_root=PROJECT_ROOT, runner=runner)
            request = InstallRequest(target(), payload, settings())
            with mock.patch("greia_installer.engine.os.geteuid", return_value=0):
                with self.assertRaisesRegex(InstallationError, "integrity record is missing"):
                    engine.install(request)
            self.assertEqual(runner.commands, [])

    def test_power_is_rechecked_in_engine_immediately_before_first_disk_mutation(self) -> None:
        class UnsafePowerProbe:
            def installation_block_reason(self) -> str | None:
                return "Connect the power adapter before installing (battery is 10%)."

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            payload = root / "payload.squashfs"
            digest = root / "payload.squashfs.sha256"
            payload.write_bytes(b"verified payload")
            digest.write_text(hashlib.sha256(payload.read_bytes()).hexdigest() + "\n")
            runner = RecordingRunner()
            engine = InstallationEngine(
                project_root=PROJECT_ROOT,
                runner=runner,
                power_probe=UnsafePowerProbe(),
            )
            request = InstallRequest(target(), payload, settings(), payload_digest=digest)
            with mock.patch("greia_installer.engine.os.geteuid", return_value=0), \
                 mock.patch.object(engine, "_verify_target"):
                with self.assertRaisesRegex(InstallationError, "power adapter"):
                    engine.install(request)
            destructive = {"wipefs", "parted", "mkfs.ext4", "grub-install"}
            self.assertFalse(
                any(command and command[0] in destructive for command in runner.commands),
                runner.commands,
            )

    def test_chroot_mount_is_recorded_before_propagation_configuration(self) -> None:
        class FailingRunner(RecordingRunner):
            def run(self, command, *, check=True):
                super().run(command, check=check)
                if list(command[:2]) == ["mount", "--make-rslave"]:
                    raise subprocess.CalledProcessError(1, command, stderr="failed")
                return subprocess.CompletedProcess(command, 0, "", "")

        with tempfile.TemporaryDirectory() as temporary:
            mounted: list[Path] = []
            engine = InstallationEngine(project_root=PROJECT_ROOT, runner=FailingRunner())
            with self.assertRaises(subprocess.CalledProcessError):
                engine._mount_chroot_filesystems(Path(temporary), mounted)
            self.assertEqual(mounted, [Path(temporary) / "dev"])

    def test_cleanup_tries_normal_unmount_before_lazy_fallback(self) -> None:
        runner = RecordingRunner()
        engine = InstallationEngine(project_root=PROJECT_ROOT, runner=runner)
        mountpoint = Path("/tmp/greia-test-mount")
        with mock.patch.object(engine, "_is_mountpoint", side_effect=[True, False]):
            error = engine._cleanup_mounts([mountpoint])
        self.assertIsNone(error)
        self.assertEqual(
            runner.commands,
            [["umount", str(mountpoint)], ["umount", "-l", str(mountpoint)]],
        )

    def test_cleanup_reports_surviving_mount_and_never_recursively_deletes_it(self) -> None:
        runner = RecordingRunner()
        engine = InstallationEngine(project_root=PROJECT_ROOT, runner=runner)
        mountpoint = Path("/tmp/greia-test-mount")
        with mock.patch.object(engine, "_is_mountpoint", side_effect=[True, True]):
            error = engine._cleanup_mounts([mountpoint])
        self.assertIsInstance(error, InstallationError)
        self.assertIn("temporary directory was preserved", str(error))

    def test_root_fstab_uses_verified_uuid_not_shared_label(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            filesystem_uuid = "12345678-1234-5678-9abc-def012345678"
            InstallationEngine._write_root_fstab(root, filesystem_uuid)
            fstab = (root / "etc/fstab").read_text(encoding="ascii")
            self.assertIn(f"UUID={filesystem_uuid} / ext4", fstab)
            self.assertNotIn("LABEL=GREIA_ROOT", fstab)

    def test_filesystem_uuid_reader_rejects_missing_or_malformed_output(self) -> None:
        class UUIDRunner(RecordingRunner):
            def __init__(self, output: str) -> None:
                super().__init__()
                self.output = output

            def run(self, command, *, check=True):
                self.commands.append(list(command))
                return subprocess.CompletedProcess(command, 0, self.output, "")

        valid = "12345678-1234-5678-9abc-def012345678\n"
        engine = InstallationEngine(project_root=PROJECT_ROOT, runner=UUIDRunner(valid))
        self.assertEqual(
            engine._read_filesystem_uuid(Path("/dev/sda1")),
            valid.strip(),
        )
        engine = InstallationEngine(project_root=PROJECT_ROOT, runner=UUIDRunner("not-a-uuid\n"))
        with self.assertRaisesRegex(InstallationError, "valid UUID"):
            engine._read_filesystem_uuid(Path("/dev/sda1"))

    def test_grub_uuid_and_recovery_material_are_per_install_while_clone_ids_stay_empty(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "etc/ssh").mkdir(parents=True)
            (root / "etc/ssh/ssh_host_rsa_key").write_text("shared")
            (root / "var/lib/dbus").mkdir(parents=True)
            (root / "var/lib/dbus/machine-id").write_text("shared")
            engine = InstallationEngine(
                project_root=PROJECT_ROOT,
                runner=RecordingRunner(),
                grub_password_hasher=StaticGrubHasher(),
            )
            filesystem_uuid = "12345678-1234-5678-9abc-def012345678"
            engine._write_grub_root_uuid(root, filesystem_uuid)
            credential = engine._personalize_target(root)
            self.assertEqual(credential.user, "greia-recovery")
            self.assertEqual(len(credential.code), 20)
            self.assertEqual((root / "etc/machine-id").read_text(), "")
            self.assertFalse((root / "var/lib/dbus/machine-id").exists())
            self.assertFalse((root / "etc/ssh/ssh_host_rsa_key").exists())
            self.assertEqual(
                (root / "etc/greia-os/root-filesystem-uuid").read_text().strip(),
                filesystem_uuid,
            )
            self.assertTrue((root / "etc/greia-os/grub-recovery.pbkdf2").read_text().startswith("grub.pbkdf2."))
            self.assertTrue((root / "etc/greia-os/grub-recovery-code").read_text().strip())

    def test_install_result_groups_recovery_code_for_parent_display(self) -> None:
        result = InstallResult(
            recovery_user="greia-recovery",
            recovery_code="ABCDEFGHJKLMNPQRSTUV",
        )
        self.assertEqual(result.grouped_recovery_code, "ABCD EFGH JKLM NPQR STUV")

    def test_install_record_hashes_device_identity_instead_of_storing_serial(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            defaults = root / "opt/greia-os/runtime/hardware-settings.toml"
            defaults.parent.mkdir(parents=True)
            defaults.write_bytes((PROJECT_ROOT / "runtime/hardware-settings.toml").read_bytes())
            runner = RecordingRunner()
            engine = InstallationEngine(project_root=PROJECT_ROOT, runner=runner)
            request = InstallRequest(target(), root / "unused", settings())
            engine._write_initial_configuration(root, request)
            record = (root / "etc/greia-os/install-record.json").read_text()
            self.assertIn("target_identity_sha256", record)
            self.assertNotIn("PRIVATE-SERIAL", record)
            self.assertNotIn("PRIVATE-WWN", record)


if __name__ == "__main__":
    unittest.main()
