"""P2-DEVCTL-VERB: permanent greia-devctl harness verb.

Proves the `run-device-collect` verb through the real mechanism:
arg parsing through the real `parse_args`, bound enforcement through
the real verb validation (no mocks on the guard), delegation wiring to
the production `LifecycleHarness.run_device_collect` path with the
pinned 300/120/120 policy and 768 MiB guest cap, and a positive
control (break -> RED, restore -> GREEN).

Preregistered acceptance predicates (frozen before observation):

1. The `run-device-collect` verb exists in the shipped greia-devctl
   surface with exactly `--output-dir` (required) and `--keep-image`
   (flag); unknown arguments are rejected, never passed through.
2. Out-of-bound outputs (relative, /tmp, /dev partition, /boot,
   /etc, /opt/greia-os, unrelated roots) are refused fail-closed and
   never reach the harness seam.
3. The harness receives `timeout_seconds == 300`,
   `memory_mib == 768`, `cpus == 1`, `seabios_path is None`, with the
   frozen 120/120 no-progress/stall thresholds; the production
   `LifecycleConfig` module defaults are unchanged.
4. `run-device-collect --help` exits 0 without root or a developer
   marker and documents the bounds.
5. Harness failures stay fail-closed with the verbatim error preserved.
"""

from __future__ import annotations

import inspect
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from greia_platform import developer_control as devctl  # noqa: E402
from greia_platform.developer_session import DeveloperDisplayEndpoint  # noqa: E402
from tools.x8_qemu import bootchain as _bootchain  # noqa: E402
from tools.x8_qemu import lifecycle as _lifecycle  # noqa: E402


WORK_ROOT = "/var/lib/greia/greia-device-work"


def _good_output() -> Path:
    return Path(WORK_ROOT) / "run-1"


class _RecordingHarness:
    """Test double behind the verb's harness_factory seam."""

    def __init__(self, config: object) -> None:
        self.config = config
        self.calls = 0

    def run_device_collect(self) -> dict[str, object]:
        self.calls += 1
        return {
            "schema_version": 1,
            "ok": True,
            "collect_mode": True,
            "classification": "DEVICE_T7_DEVRUN3_COLLECT",
        }


def _control() -> devctl.DeveloperControl:
    marker = Path(tempfile.gettempdir()) / "devctl-collect-test-marker"
    marker.write_text("enabled\n", encoding="utf-8")
    state = Path(tempfile.mkdtemp(prefix="devctl-collect-state-"))
    endpoint = DeveloperDisplayEndpoint(user="greiakid", display=":0")
    patches = (
        mock.patch.object(devctl, "DEVELOPER_MARKER", marker),
        mock.patch.object(devctl, "STATE_ROOT", state),
        mock.patch.object(devctl, "DEVELOPER_ACTIVITY_ROOT", state / "activities"),
        mock.patch.object(devctl, "STAGING_ROOT", state / "staging"),
        mock.patch.object(devctl, "BACKUP_ROOT", state / "backups"),
        mock.patch.object(devctl, "STATE_FILE", state / "deployments.json"),
        mock.patch("greia_platform.developer_control.os.geteuid", return_value=0),
        mock.patch.object(
            devctl.DeveloperDisplayEndpoint, "load", return_value=endpoint
        ),
    )
    for patch in patches:
        patch.start()
    control = devctl.DeveloperControl()
    for patch in patches:
        patch.stop()
    return control


class DeviceCollectVerbTests(unittest.TestCase):
    def test_verb_registered_with_bounded_arguments(self) -> None:
        args = devctl.parse_args(
            ["run-device-collect", "--output-dir", f"{WORK_ROOT}/run-1"]
        )
        self.assertEqual(args.command, "run-device-collect")
        self.assertEqual(args.output_dir, Path(f"{WORK_ROOT}/run-1"))
        self.assertFalse(args.keep_image)
        kept = devctl.parse_args(
            ["run-device-collect", "--output-dir", f"{WORK_ROOT}/run-1",
             "--keep-image"]
        )
        self.assertTrue(kept.keep_image)
        with self.assertRaises(SystemExit):
            devctl.parse_args(["run-device-collect"])
        # No generic passthrough: a trailing bare command is rejected.
        with self.assertRaises(SystemExit):
            devctl.parse_args(
                ["run-device-collect", "--output-dir", f"{WORK_ROOT}/run-1",
                 "losetup"]
            )

    def test_production_config_defaults_untouched(self) -> None:
        defaults = _lifecycle.LifecycleConfig(output_dir=Path("/tmp/probe-defaults"))
        self.assertEqual(defaults.timeout_seconds, 300)
        self.assertEqual(defaults.memory_mib, 1024)
        self.assertEqual(devctl.DEVICE_COLLECT_MEMORY_MIB, 768)
        self.assertEqual(devctl.DEVICE_COLLECT_TIMEOUT_SECONDS, 300)

    def test_bound_refusals_fail_closed_before_harness(self) -> None:
        control = _control()
        refused = [
            Path("relative/run"),
            Path("/tmp/evil.img"),
            Path("/tmp"),
            Path("/dev/sda"),
            Path("/dev/loop0"),
            Path("/boot/grub/grub.cfg"),
            Path("/etc/greia-os/developer-remote"),
            Path("/opt/greia-os/activities"),
            Path("/"),
            Path("/var/lib/greia-developer/activities"),
            Path("/var/lib/greia/greia-device-work-evil/run"),
        ]
        for candidate in refused:
            with self.subTest(candidate=str(candidate)):
                def _must_not_run(_config: object) -> _RecordingHarness:
                    raise AssertionError("harness seam reached for refused input")

                with self.assertRaises(devctl.DeveloperControlError):
                    control.run_device_collect(
                        candidate, harness_factory=_must_not_run
                    )

    def test_symlink_escape_is_refused(self) -> None:
        control = _control()
        with tempfile.TemporaryDirectory() as tmp:
            outside = Path(tmp) / "outside"
            outside.mkdir()
            link = Path(tmp) / "link-run"
            link.symlink_to(outside, target_is_directory=True)

            def _must_not_run(_config: object) -> _RecordingHarness:
                raise AssertionError("harness seam reached via symlink")

            with mock.patch.object(
                devctl, "DEVICE_COLLECT_WORK_ROOT", Path(tmp) / "work"
            ):
                (Path(tmp) / "work").mkdir()
                with self.assertRaises(devctl.DeveloperControlError):
                    control.run_device_collect(link, harness_factory=_must_not_run)

    def test_positive_control_break_red_restore_green(self) -> None:
        control = _control()
        # BREAK: out-of-bound write attempt is refused fail-closed (RED).
        reached = []

        def _must_not_run(_config: object) -> _RecordingHarness:
            reached.append(True)
            raise AssertionError("unreachable")

        with self.assertRaisesRegex(
            devctl.DeveloperControlError, "refuses|only inside"
        ):
            control.run_device_collect(
                Path("/tmp/positive-control.img"), harness_factory=_must_not_run
            )
        self.assertEqual(reached, [])

        # RESTORE: legitimate disposable run proceeds (GREEN) with the
        # pinned policy observed at the harness seam.
        seen: dict[str, object] = {}

        def _factory(config: object) -> _RecordingHarness:
            seen["config"] = config
            return _RecordingHarness(config)

        result = control.run_device_collect(_good_output(), harness_factory=_factory)
        self.assertEqual(result["ok"], True)
        config = seen["config"]
        assert isinstance(config, _lifecycle.LifecycleConfig)
        self.assertEqual(config.timeout_seconds, 300)
        self.assertEqual(config.memory_mib, 768)
        self.assertEqual(config.cpus, 1)
        self.assertIsNone(config.seabios_path)
        self.assertEqual(
            Path(config.output_dir).resolve(strict=False),
            Path(WORK_ROOT).resolve(strict=False) / "run-1",
        )
        # The pinned config passes the real production validation.
        config.validate(project_root=PROJECT_ROOT)
        # Frozen thresholds are the real DIAG-C1 values, not copies.
        self.assertEqual(_bootchain.BOOT_WAIT_NO_PROGRESS_SECONDS, 120.0)
        self.assertEqual(_bootchain.BOOT_WAIT_STALL_SECONDS, 120.0)
        policy = _lifecycle.LegTimeoutPolicy(timeout_seconds=300.0)
        self.assertEqual(policy.no_progress_seconds, 120.0)
        self.assertEqual(policy.stall_seconds, 120.0)

    def test_delegation_targets_production_collect_path(self) -> None:
        self.assertTrue(callable(_lifecycle.LifecycleHarness.run_device_collect))
        body = inspect.getsource(devctl.DeveloperControl.run_device_collect)
        self.assertIn("LifecycleHarness(config)", body)
        self.assertIn("harness.run_device_collect()", body)
        self.assertIn("DEVICE_COLLECT_WORK_ROOT", body)
        self.assertNotIn("shell=True", body)
        self.assertNotIn("subprocess", body)

    def test_harness_failures_stay_fail_closed_verbatim(self) -> None:
        control = _control()

        class _RedHarness:
            def run_device_collect(self) -> dict[str, object]:
                raise _lifecycle.LifecycleHarnessError("boom-red-predicate")

        with self.assertRaisesRegex(
            devctl.DeveloperControlError, "failed closed.*boom-red-predicate"
        ):
            control.run_device_collect(
                _good_output(), harness_factory=lambda cfg: _RedHarness()
            )

        class _BadShape:
            def run_device_collect(self) -> object:
                return ["not", "a", "report"]

        with self.assertRaises(devctl.DeveloperControlError):
            control.run_device_collect(
                _good_output(), harness_factory=lambda cfg: _BadShape()  # type: ignore[arg-type]
            )

    def test_keep_image_must_be_bool(self) -> None:
        control = _control()
        with self.assertRaises(devctl.DeveloperControlError):
            control.run_device_collect(_good_output(), keep_image="yes")  # type: ignore[arg-type]

    def test_help_documents_bounds_without_privilege(self) -> None:
        completed = subprocess.run(
            [sys.executable, "-m", "greia_platform.developer_control",
             "run-device-collect", "--help"],
            capture_output=True,
            text=True,
            cwd=str(PROJECT_ROOT),
            env={"PYTHONPATH": str(SRC_ROOT), "PATH": "/usr/bin:/bin"},
        )
        self.assertEqual(completed.returncode, 0)
        self.assertIn("--output-dir", completed.stdout)
        self.assertIn("--keep-image", completed.stdout)
        flattened = completed.stdout.replace("\n", " ").replace(
            "greia- device-work", "greia-device-work"
        )
        self.assertIn("greia-device-work", flattened)
        self.assertIn("768", completed.stdout)


if __name__ == "__main__":
    unittest.main()
