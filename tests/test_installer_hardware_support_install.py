from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from greia_installer.hardware_support import VerifiedHardwareSupportPool
from greia_installer.hardware_support_install import TargetHardwareSupportInstaller


class RecordingRunner:
    def __init__(self) -> None:
        self.commands: list[list[str]] = []

    def run(self, command, *, check: bool = True):
        self.commands.append(list(command))
        return None


def pool(root: Path) -> VerifiedHardwareSupportPool:
    return VerifiedHardwareSupportPool(
        root,
        "trixie",
        "amd64",
        (),
        frozenset({"firmware-realtek", "intel-microcode"}),
        frozenset({"firmware-realtek"}),
        frozenset({"intel-microcode"}),
        0,
        0,
    )


class TargetHardwareSupportInstallerTests(unittest.TestCase):
    def test_empty_machine_plan_performs_no_mount_or_apt_work(self) -> None:
        runner = RecordingRunner()
        mounted: list[Path] = []
        with tempfile.TemporaryDirectory() as temporary:
            result = TargetHardwareSupportInstaller(runner).install(
                target_root=Path(temporary),
                pool=pool(Path("/verified-pool")),
                packages=(),
                mounted=mounted,
            )
        self.assertEqual(result, ())
        self.assertEqual(runner.commands, [])
        self.assertEqual(mounted, [])

    def test_installs_only_from_temporary_local_repository(self) -> None:
        runner = RecordingRunner()
        mounted: list[Path] = []
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary)
            result = TargetHardwareSupportInstaller(runner).install(
                target_root=target,
                pool=pool(Path("/verified-pool")),
                packages=("firmware-realtek", "intel-microcode"),
                mounted=mounted,
            )
            source = target / "run/greia-hardware-support.list"
            self.assertFalse(source.exists())

        self.assertEqual(result, ("firmware-realtek", "intel-microcode"))
        self.assertEqual(
            mounted,
            [
                target / "dev",
                target / "proc",
                target / "sys",
                target / "run",
                target / "run/greia-installer-scratch",
                target / "run/greia-hardware-support",
            ],
        )
        self.assertEqual(
            runner.commands[:4],
            [
                ["mount", "--rbind", "/dev", str(target / "dev")],
                ["mount", "--make-rslave", str(target / "dev")],
                ["mount", "-t", "proc", "proc", str(target / "proc")],
                ["mount", "--rbind", "/sys", str(target / "sys")],
            ],
        )
        self.assertEqual(
            runner.commands[7],
            [
                "mount",
                "-t",
                "tmpfs",
                "-o",
                "size=256M,mode=1777",
                "tmpfs",
                str(target / "run/greia-installer-scratch"),
            ],
        )
        self.assertEqual(
            runner.commands[8],
            ["mount", "--bind", "/verified-pool", str(target / "run/greia-hardware-support")],
        )
        self.assertEqual(
            runner.commands[9],
            ["mount", "-o", "remount,bind,ro", str(target / "run/greia-hardware-support")],
        )
        flattened = "\n".join(" ".join(command) for command in runner.commands)
        self.assertIn("Dir::Etc::sourcelist=/run/greia-hardware-support.list", flattened)
        self.assertIn("Dir::Etc::sourceparts=-", flattened)
        self.assertIn("Dir::Cache::archives=/run/greia-installer-scratch/apt", flattened)
        self.assertIn("TMPDIR=/run/greia-installer-scratch/tmp", flattened)
        self.assertIn("firmware-realtek", flattened)
        self.assertIn("intel-microcode", flattened)
        self.assertNotIn("deb.debian.org", flattened)
        self.assertNotIn("http://", flattened)
        self.assertNotIn("https://", flattened)

    def test_unverified_candidate_is_rejected_before_mount(self) -> None:
        runner = RecordingRunner()
        mounted: list[Path] = []
        with tempfile.TemporaryDirectory() as temporary:
            with self.assertRaisesRegex(Exception, "not available"):
                TargetHardwareSupportInstaller(runner).install(
                    target_root=Path(temporary),
                    pool=pool(Path("/verified-pool")),
                    packages=("firmware-iwlwifi",),
                    mounted=mounted,
                )
        self.assertEqual(runner.commands, [])
        self.assertEqual(mounted, [])


if __name__ == "__main__":
    unittest.main()
