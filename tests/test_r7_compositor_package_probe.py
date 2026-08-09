from __future__ import annotations

import os
import shutil
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
    _boot_state_signature,
    _capture_resolv_conf,
    _prepare_clone_for_apt,
    _restore_resolv_conf,
    _tree_signature,
    _truncate_measurement_logs,
    compare_package_manifests,
    parse_package_manifest,
)


class _RecordingRunner:
    def __init__(self, *, fail_at: int | None = None):
        self.calls: list[list[str]] = []
        self.fail_at = fail_at

    def run(self, argv, *, check=True, capture_output=False, text=True):
        command = list(argv)
        self.calls.append(command)
        if self.fail_at is not None and len(self.calls) == self.fail_at:
            raise RuntimeError("synthetic failure")
        label = "update" if command and command[-1] == "update" else "install"
        return subprocess.CompletedProcess(
            command,
            0,
            f"{label}-stdout\n",
            f"{label}-stderr\n",
        )


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

    def test_plan_never_mutates_source_or_exposes_host_session_or_hardware(self):
        probe = CompositorPackageProbe(
            ProbeConfig(Path("production.img"), Path("out"), "cage")
        )
        plan = probe.plan()
        self.assertIs(plan["source_image_mutated"], False)
        self.assertIs(plan["boot_or_service_changes"], False)
        self.assertEqual(
            plan["chroot_runtime"],
            {
                "private_minimal_dev": True,
                "fresh_procfs": True,
                "host_devices_exposed": False,
                "host_sysfs_exposed": False,
                "host_run_exposed": False,
            },
        )
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

    def test_chroot_runtime_uses_private_dev_and_fresh_proc_only(self):
        runner = _RecordingRunner()
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            with ChrootRuntimeMounts(root, runner=runner):
                pass
            dev_target = str(root / "dev")
            proc_target = str(root / "proc")
            sys_target = str(root / "sys")
            run_target = str(root / "run")

        mount_calls = [
            command for command in runner.calls if command and command[0] == "mount"
        ]
        self.assertEqual(len(mount_calls), 2)
        self.assertEqual(mount_calls[0][:3], ["mount", "-t", "tmpfs"])
        self.assertEqual(mount_calls[0][-1], dev_target)
        self.assertEqual(
            mount_calls[1], ["mount", "-t", "proc", "proc", proc_target]
        )

        flattened = [argument for command in runner.calls for argument in command]
        for forbidden in ("/dev", "/sys", "/run", sys_target, run_target):
            self.assertNotIn(forbidden, flattened)

        mknod_calls = [
            command for command in runner.calls if command and command[0] == "mknod"
        ]
        self.assertEqual(len(mknod_calls), 5)
        self.assertEqual(
            {Path(command[3]).name for command in mknod_calls},
            {"null", "zero", "full", "random", "urandom"},
        )
        self.assertTrue(
            all(Path(command[3]).parent == Path(dev_target) for command in mknod_calls)
        )
        self.assertTrue(any(command[:2] == ["bash", "-c"] for command in runner.calls))

    def test_chroot_runtime_setup_failure_still_cleans_private_mounts(self):
        runner = _RecordingRunner(fail_at=3)
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            with self.assertRaisesRegex(RuntimeError, "synthetic failure"):
                with ChrootRuntimeMounts(root, runner=runner):
                    pass
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

    def test_prepare_failure_removes_policy_and_restores_resolver(self):
        import r7_compositor_package_probe as module

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            resolv = root / "etc/resolv.conf"
            resolv.parent.mkdir(parents=True)
            resolv.write_text("nameserver 192.0.2.1\n", encoding="ascii")
            os.chmod(resolv, 0o640)
            (root / "usr/sbin").mkdir(parents=True)

            original_chmod = module.os.chmod

            def failing_chmod(path, mode):
                if str(path).endswith("policy-rc.d"):
                    raise OSError("synthetic chmod failure")
                return original_chmod(path, mode)

            module.os.chmod = failing_chmod
            try:
                with self.assertRaisesRegex(OSError, "synthetic chmod failure"):
                    _prepare_clone_for_apt(root)
            finally:
                module.os.chmod = original_chmod

            self.assertEqual(
                resolv.read_text(encoding="ascii"),
                "nameserver 192.0.2.1\n",
            )
            self.assertEqual(resolv.stat().st_mode & 0o777, 0o640)
            self.assertFalse((root / "usr/sbin/policy-rc.d").exists())

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

    def test_tree_signature_handles_single_file_and_symlink(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            target = root / "target"
            target.write_text("one\n", encoding="utf-8")
            before = _tree_signature(target)
            target.write_text("two\n", encoding="utf-8")
            self.assertNotEqual(before, _tree_signature(target))

            link = root / "link"
            link.symlink_to("target")
            self.assertEqual(_tree_signature(link)[0][1], "symlink")

    def test_boot_state_signature_detects_grub_and_systemd_changes(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "etc/systemd/system").mkdir(parents=True)
            (root / "etc/default").mkdir(parents=True)
            grub = root / "etc/default/grub"
            grub.write_text("GRUB_TIMEOUT=0\n", encoding="utf-8")
            before = _boot_state_signature(root)

            grub.write_text("GRUB_TIMEOUT=5\n", encoding="utf-8")
            self.assertNotEqual(before, _boot_state_signature(root))

    def test_run_deletes_clone_on_success_and_failure_unless_kept(self):
        class Probe(CompositorPackageProbe):
            @staticmethod
            def _require_privileged_host():
                return None

            def _require_tools(self):
                return None

            def _clone_source_image(self, source):
                shutil.copyfile(source, self.test_image)

            def _measure_clone(self, source, source_sha):
                return {
                    "schema_version": 1,
                    "ok": True,
                    "source_image_sha256": source_sha,
                }

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "source.img"
            source.write_bytes(b"source")
            probe = Probe(ProbeConfig(source, root / "out", "cage"))
            result = probe.run()
            self.assertFalse(probe.test_image.exists())
            self.assertTrue(probe.report_path.exists())
            self.assertEqual(
                result["source_image_sha256_after"],
                result["source_image_sha256"],
            )

        class FailingProbe(Probe):
            def _measure_clone(self, source, source_sha):
                raise RuntimeError("synthetic measurement failure")

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "source.img"
            source.write_bytes(b"source")
            probe = FailingProbe(ProbeConfig(source, root / "out", "cage"))
            with self.assertRaisesRegex(RuntimeError, "synthetic measurement failure"):
                probe.run()
            self.assertFalse(probe.test_image.exists())
            self.assertFalse(probe.report_path.exists())

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "source.img"
            source.write_bytes(b"source")
            probe = FailingProbe(
                ProbeConfig(source, root / "out", "cage", keep_test_image=True)
            )
            with self.assertRaisesRegex(RuntimeError, "synthetic measurement failure"):
                probe.run()
            self.assertTrue(probe.test_image.exists())

    def test_run_rechecks_source_hash_even_when_measurement_fails(self):
        class MutatingProbe(CompositorPackageProbe):
            @staticmethod
            def _require_privileged_host():
                return None

            def _require_tools(self):
                return None

            def _clone_source_image(self, source):
                shutil.copyfile(source, self.test_image)

            def _measure_clone(self, source, source_sha):
                source.write_bytes(b"mutated")
                raise RuntimeError("original failure")

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "source.img"
            source.write_bytes(b"source")
            probe = MutatingProbe(ProbeConfig(source, root / "out", "cage"))
            with self.assertRaisesRegex(
                CompositorPackageProbeError,
                "source image hash changed",
            ):
                probe.run()


if __name__ == "__main__":
    unittest.main()
