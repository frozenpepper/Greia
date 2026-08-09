from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
TOOLS = PROJECT_ROOT / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

from r7_compositor_package_probe import (  # noqa: E402
    CANDIDATES,
    ChrootRuntimeMounts,
    CompositorPackageProbe,
    CompositorPackageProbeError,
    PackageRecord,
    ProbeConfig,
    ResolvConfBackup,
    _capture_resolv_conf,
    _restore_resolv_conf,
    _tree_signature,
    _truncate_measurement_logs,
    compare_package_manifests,
    parse_package_manifest,
)


class _RecordingRunner:
    def __init__(self):
        self.calls: list[list[str]] = []

    def run(self, argv, *, check=True, capture_output=False, text=True):
        command = list(argv)
        self.calls.append(command)
        label = "update" if command[-1] == "update" else "install"
        return subprocess.CompletedProcess(command, 0, f"{label}-stdout\n", f"{label}-stderr\n")


class _MountRecordingRunner:
    def __init__(self):
        self.calls: list[list[str]] = []

    def run(self, argv, *, check=True, capture_output=False, text=True):
        command = list(argv)
        self.calls.append(command)
        return subprocess.CompletedProcess(command, 0, "", "")


class CompositorPackageProbeTests(unittest.TestCase):
    def test_candidate_set_is_fixed_and_small(self):
        self.assertEqual(
            CANDIDATES,
            {
                "cage": ("cage",),
                "weston": ("weston",),
                "wlroots-runtime": ("libwlroots-0.18",),
            },
        )
        with self.assertRaisesRegex(CompositorPackageProbeError, "unknown candidate"):
            ProbeConfig(Path("image"), Path("out"), "not-a-candidate").validate()

    def test_plan_never_mutates_source_or_enables_boot_path(self):
        probe = CompositorPackageProbe(
            ProbeConfig(Path("production.img"), Path("out"), "cage")
        )
        plan = probe.plan()
        self.assertIs(plan["source_image_mutated"], False)
        self.assertIs(plan["boot_or_service_changes"], False)
        self.assertIs(plan["host_run_exposed"], False)
        self.assertEqual(plan["packages"], ["cage"])
        self.assertEqual(
            plan["apt_policy"],
            {
                "install_recommends": False,
                "upgrades_allowed": False,
                "removals_allowed": False,
            },
        )

    def test_install_command_is_fail_closed_against_recommends_upgrades_and_removals(self):
        runner = _RecordingRunner()
        probe = CompositorPackageProbe(
            ProbeConfig(Path("production.img"), Path("out"), "weston"),
            runner=runner,
        )
        log = probe._install_candidate(Path("/clone"))
        self.assertEqual(len(runner.calls), 2)
        install = runner.calls[1]
        self.assertIn("--no-install-recommends", install)
        self.assertIn("--no-upgrade", install)
        self.assertIn("--no-remove", install)
        self.assertIn("Dpkg::Options::=--force-confold", install)
        self.assertEqual(install[-1], "weston")
        self.assertIn("update-stdout", log)
        self.assertIn("install-stderr", log)

    def test_chroot_runtime_mounts_never_expose_host_run(self):
        runner = _MountRecordingRunner()
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            with ChrootRuntimeMounts(root, runner=runner):
                pass
            run_target = str(root / "run")
        flattened = [argument for command in runner.calls for argument in command]
        self.assertNotIn("/run", flattened)
        self.assertNotIn(run_target, flattened)
        self.assertIn("/dev", flattened)
        self.assertIn("/sys", flattened)
        self.assertTrue(
            any(command[:3] == ["mount", "-t", "proc"] for command in runner.calls)
        )
        self.assertTrue(any(command[:2] == ["bash", "-c"] for command in runner.calls))

    def test_manifest_parser_requires_exact_four_field_unique_records(self):
        parsed = parse_package_manifest(
            "alpha\t1.0\tamd64\t12\n"
            "beta\t2.0\tamd64\t34\n"
        )
        self.assertEqual(parsed["alpha"], PackageRecord("alpha", "1.0", "amd64", 12))
        self.assertEqual(parsed["beta"].installed_size_kib, 34)

        bad_inputs = (
            "alpha\t1.0\tamd64\n",
            "alpha\t1.0\tamd64\tnot-a-number\n",
            "alpha\t1.0\tamd64\t-1\n",
            "alpha\t1.0\tamd64\t1\nalpha\t1.0\tamd64\t1\n",
            "",
        )
        for text in bad_inputs:
            with self.subTest(text=text):
                with self.assertRaises(CompositorPackageProbeError):
                    parse_package_manifest(text)

    def test_manifest_comparison_separates_added_removed_and_changed(self):
        baseline = {
            "same": PackageRecord("same", "1", "amd64", 1),
            "changed": PackageRecord("changed", "1", "amd64", 2),
            "removed": PackageRecord("removed", "1", "amd64", 3),
        }
        current = {
            "same": PackageRecord("same", "1", "amd64", 1),
            "changed": PackageRecord("changed", "2", "amd64", 2),
            "added": PackageRecord("added", "1", "amd64", 4),
        }
        delta = compare_package_manifests(baseline, current)
        self.assertEqual(delta["added"], ["added"])
        self.assertEqual(delta["removed"], ["removed"])
        self.assertEqual(
            delta["upgraded_or_changed"],
            [
                {
                    "name": "changed",
                    "before_version": "1",
                    "after_version": "2",
                    "before_architecture": "amd64",
                    "after_architecture": "amd64",
                }
            ],
        )

    def test_resolver_file_backup_restores_content_and_mode(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            resolv = root / "etc/resolv.conf"
            resolv.parent.mkdir(parents=True)
            resolv.write_text("nameserver 192.0.2.1\n", encoding="ascii")
            os.chmod(resolv, 0o640)
            backup = _capture_resolv_conf(root)

            resolv.write_text("nameserver 203.0.113.1\n", encoding="ascii")
            os.chmod(resolv, 0o644)
            _restore_resolv_conf(root, backup)

            self.assertEqual(resolv.read_text(encoding="ascii"), "nameserver 192.0.2.1\n")
            self.assertEqual(resolv.stat().st_mode & 0o777, 0o640)

    def test_resolver_symlink_and_missing_states_restore_exactly(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            etc = root / "etc"
            etc.mkdir()
            resolv = etc / "resolv.conf"
            resolv.symlink_to("../run/systemd/resolve/stub-resolv.conf")
            backup = _capture_resolv_conf(root)
            self.assertEqual(
                backup,
                ResolvConfBackup(
                    "symlink", "../run/systemd/resolve/stub-resolv.conf"
                ),
            )
            resolv.unlink()
            resolv.write_text("temporary\n", encoding="ascii")
            _restore_resolv_conf(root, backup)
            self.assertTrue(resolv.is_symlink())
            self.assertEqual(
                os.readlink(resolv), "../run/systemd/resolve/stub-resolv.conf"
            )

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "etc").mkdir()
            backup = _capture_resolv_conf(root)
            self.assertEqual(backup, ResolvConfBackup("missing", None))
            resolv = root / "etc/resolv.conf"
            resolv.write_text("temporary\n", encoding="ascii")
            _restore_resolv_conf(root, backup)
            self.assertFalse(resolv.exists())

    def test_measurement_logs_are_truncated_but_tree_is_preserved(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            apt_log = root / "var/log/apt/history.log"
            dpkg_log = root / "var/log/dpkg.log"
            apt_log.parent.mkdir(parents=True)
            apt_log.write_text("package transaction\n", encoding="utf-8")
            dpkg_log.write_text("dpkg transaction\n", encoding="utf-8")
            symlink = root / "var/log/current"
            symlink.symlink_to("dpkg.log")

            _truncate_measurement_logs(root)

            self.assertEqual(apt_log.stat().st_size, 0)
            self.assertEqual(dpkg_log.stat().st_size, 0)
            self.assertTrue(symlink.is_symlink())

    def test_systemd_tree_signature_detects_file_and_symlink_changes(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            tree = root / "etc/systemd/system"
            wants = tree / "graphical.target.wants"
            wants.mkdir(parents=True)
            unit = tree / "greia-test.service"
            unit.write_text("[Service]\nType=oneshot\n", encoding="utf-8")
            enabled = wants / "greia-test.service"
            enabled.symlink_to("../greia-test.service")
            before = _tree_signature(tree)

            unit.write_text("[Service]\nType=simple\n", encoding="utf-8")
            self.assertNotEqual(before, _tree_signature(tree))

            unit.write_text("[Service]\nType=oneshot\n", encoding="utf-8")
            enabled.unlink()
            enabled.symlink_to("../different.service")
            self.assertNotEqual(before, _tree_signature(tree))


if __name__ == "__main__":
    unittest.main()
