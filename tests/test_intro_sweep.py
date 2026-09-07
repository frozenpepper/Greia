"""Bounded pre-armed at-boot intro motion sweep (FIX-INTRO-INJECTOR).

Lifecycle tests: arm/fire/disarm, no-fire without arm, no double-fire,
timestamp-log boundedness, non-developer inertness, fixed mousemove-only
transport, intro-bound trigger branches, devctl arm/log verbs, and the
at-boot wrapper/service source contract.

Production-path motion proof (real pointer events draining the intro) is
explicitly deferred to PROVE-INTRO-DRAIN-R; this task claims no P-c verdict.
"""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT / "src"))

from greia_platform import developer_control as devctl  # noqa: E402
from greia_platform import developer_input as devinput  # noqa: E402
from greia_platform.developer_session import DeveloperDisplayEndpoint  # noqa: E402

ENDPOINT = DeveloperDisplayEndpoint(user="greiakid", display=":0")


def _run_ok(*args, **kwargs):
    del args, kwargs
    return subprocess.CompletedProcess([], 0, "", "")


class IntroSweepBoundsTests(unittest.TestCase):
    def test_constants_state_a_bounded_sweep_below_the_intro_window(self):
        self.assertEqual(devinput.INTRO_SWEEP_STEP_COUNT, 10)
        self.assertEqual(devinput.INTRO_SWEEP_STEP_INTERVAL_SECONDS, 0.2)
        self.assertEqual(devinput.INTRO_SWEEP_WAIT_FOR_INTRO_TIMEOUT_SECONDS, 3.0)
        worst_case = (
            devinput.INTRO_SWEEP_WAIT_FOR_INTRO_TIMEOUT_SECONDS
            + devinput.INTRO_SWEEP_STEP_COUNT
            * devinput.INTRO_SWEEP_STEP_INTERVAL_SECONDS
        )
        self.assertLess(worst_case, 7.0)

    def test_coordinates_stay_inside_the_reference_display(self):
        coordinates = devinput.intro_sweep_coordinates()
        self.assertEqual(len(coordinates), devinput.INTRO_SWEEP_STEP_COUNT)
        self.assertEqual(
            coordinates[0],
            (devinput.INTRO_SWEEP_X_START, devinput.INTRO_SWEEP_Y),
        )
        self.assertEqual(
            coordinates[-1],
            (devinput.INTRO_SWEEP_X_END, devinput.INTRO_SWEEP_Y),
        )
        for x, y in coordinates:
            self.assertGreaterEqual(x, 0)
            self.assertLess(x, 1024)
            self.assertGreaterEqual(y, 0)
            self.assertLess(y, 600)
        xs = [x for x, _ in coordinates]
        self.assertEqual(xs, sorted(xs))


class IntroSweepLifecycleTests(unittest.TestCase):
    def _developer(self, tmp: str):
        root = Path(tmp)
        marker = root / "developer-remote"
        marker.write_text("enabled\n", encoding="utf-8")
        arm = root / "intro-sweep.armed"
        log = root / "intro-sweep.log"
        return marker, arm, log

    def _transport(self):
        return (
            mock.patch.object(
                devinput, "_developer_endpoint", return_value=ENDPOINT
            ),
            mock.patch(
                "greia_platform.developer_input.subprocess.run",
                side_effect=_run_ok,
            ),
        )

    def test_no_arm_is_a_noop_with_no_motion_and_no_log(self):
        with tempfile.TemporaryDirectory() as tmp:
            marker, arm, log = self._developer(tmp)
            endpoint_patch, run_patch = self._transport()
            with (
                mock.patch.object(devinput, "DEVELOPER_MARKER", marker),
                endpoint_patch,
                run_patch as run,
            ):
                result = devinput.run_intro_sweep(
                    arm_path=arm,
                    log_path=log,
                    wait_timeout_seconds=0,
                    sleep=lambda _: None,
                )
            self.assertFalse(result.fired)
            self.assertEqual(result.reason, "not-armed")
            self.assertEqual(result.steps, 0)
            run.assert_not_called()
            self.assertFalse(log.exists())

    def test_arm_fire_disarm_lifecycle_uses_only_mousemove_transport(self):
        with tempfile.TemporaryDirectory() as tmp:
            marker, arm, log = self._developer(tmp)
            endpoint_patch, run_patch = self._transport()
            with mock.patch.object(devinput, "DEVELOPER_MARKER", marker):
                armed = devinput.arm_intro_sweep(arm_path=arm)
                self.assertEqual(armed, arm)
                self.assertTrue(arm.is_file())
                sleeps: list[float] = []
                with endpoint_patch, run_patch as run:
                    result = devinput.run_intro_sweep(
                        arm_path=arm,
                        log_path=log,
                        wait_timeout_seconds=0,
                        sleep=sleeps.append,
                    )
            self.assertTrue(result.fired)
            self.assertEqual(result.reason, "fired")
            self.assertEqual(result.steps, devinput.INTRO_SWEEP_STEP_COUNT)
            # Pacing is the sweep's own bounded stepping, never boot orchestration.
            self.assertEqual(len(sleeps), devinput.INTRO_SWEEP_STEP_COUNT - 1)
            for pause in sleeps:
                self.assertEqual(pause, devinput.INTRO_SWEEP_STEP_INTERVAL_SECONDS)
            # Fixed transport: every call is runuser + xdotool mousemove --sync.
            self.assertEqual(run.call_count, devinput.INTRO_SWEEP_STEP_COUNT)
            expected = devinput.intro_sweep_coordinates()
            for call, (x, y) in zip(run.call_args_list, expected):
                argv = call.args[0]
                self.assertEqual(argv[:4], ["runuser", "--user", "greiakid", "--"])
                self.assertIn("DISPLAY=:0", argv)
                self.assertIn("/usr/bin/xdotool", argv)
                self.assertEqual(argv[-4:], ["mousemove", "--sync", str(x), str(y)])
            # One-shot consumed: arm file is gone after the single run.
            self.assertFalse(arm.exists())
            # Timestamp evidence: one correlatable line per step.
            lines = log.read_text(encoding="utf-8").splitlines()
            self.assertEqual(len(lines), devinput.INTRO_SWEEP_STEP_COUNT)
            for index, line in enumerate(lines, start=1):
                self.assertIn(f"step={index}/{devinput.INTRO_SWEEP_STEP_COUNT}", line)
                self.assertIn("utc=", line)
                self.assertIn("monotonic_ns=", line)

    def test_no_double_fire_second_run_is_a_noop(self):
        with tempfile.TemporaryDirectory() as tmp:
            marker, arm, log = self._developer(tmp)
            endpoint_patch, run_patch = self._transport()
            with mock.patch.object(devinput, "DEVELOPER_MARKER", marker):
                devinput.arm_intro_sweep(arm_path=arm)
                with endpoint_patch, run_patch as run:
                    first = devinput.run_intro_sweep(
                        arm_path=arm,
                        log_path=log,
                        wait_timeout_seconds=0,
                        sleep=lambda _: None,
                    )
                    calls_after_first = run.call_count
                    second = devinput.run_intro_sweep(
                        arm_path=arm,
                        log_path=log,
                        wait_timeout_seconds=0,
                        sleep=lambda _: None,
                    )
            self.assertTrue(first.fired)
            self.assertFalse(second.fired)
            self.assertEqual(second.reason, "not-armed")
            self.assertEqual(run.call_count, calls_after_first)

    def test_intro_enter_observation_and_timeout_fallback_both_fire_once(self):
        with tempfile.TemporaryDirectory() as tmp:
            marker, arm, log = self._developer(tmp)
            spool = Path(tmp) / "boot-markers.log"
            endpoint_patch, run_patch = self._transport()
            with mock.patch.object(devinput, "DEVELOPER_MARKER", marker):
                # Fresh intro_enter observation fires.
                spool.write_text(
                    "GREIA_BOOT event=intro_enter monotonic_ns=1\n",
                    encoding="utf-8",
                )
                with mock.patch.dict(
                    os.environ, {"GREIA_BOOT_MARKERS_SPOOL": str(spool)}
                ):
                    self.assertTrue(devinput.wait_for_intro_enter(timeout_seconds=5))
                # Empty spool with an elapsed deadline still fires once
                # (launcher-start-with-deadline fallback) so the arm is never
                # carried to a later boot.
                spool.write_text("", encoding="utf-8")
                with mock.patch.dict(
                    os.environ, {"GREIA_BOOT_MARKERS_SPOOL": str(spool)}
                ):
                    self.assertFalse(devinput.wait_for_intro_enter(timeout_seconds=0))
                    devinput.arm_intro_sweep(arm_path=arm)
                    with endpoint_patch, run_patch as run:
                        result = devinput.run_intro_sweep(
                            arm_path=arm,
                            log_path=log,
                            wait_timeout_seconds=0,
                            sleep=lambda _: None,
                        )
                self.assertTrue(result.fired)
                self.assertEqual(result.steps, devinput.INTRO_SWEEP_STEP_COUNT)
                self.assertEqual(run.call_count, devinput.INTRO_SWEEP_STEP_COUNT)
                self.assertFalse(arm.exists())

    def test_timestamp_log_is_bounded(self):
        with tempfile.TemporaryDirectory() as tmp:
            log = Path(tmp) / "intro-sweep.log"
            for index in range(devinput.INTRO_SWEEP_LOG_MAX_LINES + 50):
                devinput._append_intro_sweep_log(f"INTRO_SWEEP filler={index}", log_path=log)
            text = log.read_text(encoding="utf-8", errors="replace")
            self.assertLessEqual(
                len(text.splitlines()), devinput.INTRO_SWEEP_LOG_MAX_LINES
            )
            self.assertLessEqual(
                len(text.encode("utf-8")), devinput.INTRO_SWEEP_LOG_MAX_BYTES
            )
            # Retrieval is bounded too and keeps the newest evidence.
            capped = devinput.read_intro_sweep_log_text(log_path=log)
            self.assertLessEqual(
                len(capped.splitlines()), devinput.INTRO_SWEEP_LOG_MAX_LINES
            )
            self.assertIn("filler=", capped.splitlines()[-1])

    def test_non_developer_image_is_inert_and_still_disarms(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            missing_marker = root / "missing-marker"
            arm = root / "intro-sweep.armed"
            log = root / "intro-sweep.log"
            arm.write_text("armed\n", encoding="utf-8")
            endpoint_patch, run_patch = self._transport()
            with (
                mock.patch.object(devinput, "DEVELOPER_MARKER", missing_marker),
                endpoint_patch,
                run_patch as run,
            ):
                result = devinput.run_intro_sweep(
                    arm_path=arm,
                    log_path=log,
                    wait_timeout_seconds=0,
                    sleep=lambda _: None,
                )
            self.assertFalse(result.fired)
            self.assertEqual(result.reason, "non-developer-image")
            run.assert_not_called()
            self.assertFalse(arm.exists())
            self.assertFalse(log.exists())

    def test_arm_refuses_non_developer_images(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            missing_marker = root / "missing-marker"
            with mock.patch.object(devinput, "DEVELOPER_MARKER", missing_marker):
                with self.assertRaises(devinput.DeveloperInputError):
                    devinput.arm_intro_sweep(arm_path=root / "intro-sweep.armed")

    def test_xdotool_failure_still_disarms_without_raising(self):
        with tempfile.TemporaryDirectory() as tmp:
            marker, arm, log = self._developer(tmp)
            failing = subprocess.CompletedProcess([], 1, "", "cannot open display")
            with mock.patch.object(devinput, "DEVELOPER_MARKER", marker):
                devinput.arm_intro_sweep(arm_path=arm)
                with (
                    mock.patch.object(
                        devinput, "_developer_endpoint", return_value=ENDPOINT
                    ),
                    mock.patch(
                        "greia_platform.developer_input.subprocess.run",
                        return_value=failing,
                    ),
                ):
                    result = devinput.run_intro_sweep(
                        arm_path=arm,
                        log_path=log,
                        wait_timeout_seconds=0,
                        sleep=lambda _: None,
                    )
            self.assertFalse(arm.exists())
            self.assertEqual(result.steps, 0)


class IntroSweepDevctlTests(unittest.TestCase):
    def _control(self, tmp: str):
        root = Path(tmp)
        marker = root / "developer-remote"
        marker.write_text("enabled\n", encoding="utf-8")
        state = root / "state"
        patches = (
            mock.patch.object(devctl, "DEVELOPER_MARKER", marker),
            mock.patch.object(devinput, "DEVELOPER_MARKER", marker),
            mock.patch.object(devctl, "STATE_ROOT", state),
            mock.patch.object(devctl, "DEVELOPER_ACTIVITY_ROOT", state / "activities"),
            mock.patch.object(devctl, "STAGING_ROOT", state / "staging"),
            mock.patch.object(devctl, "BACKUP_ROOT", state / "backups"),
            mock.patch.object(devctl, "STATE_FILE", state / "deployments.json"),
            mock.patch("greia_platform.developer_control.os.geteuid", return_value=0),
            mock.patch.object(
                devctl.DeveloperDisplayEndpoint, "load", return_value=ENDPOINT
            ),
        )
        for patch in patches:
            patch.start()
            self.addCleanup(patch.stop)
        return devctl.DeveloperControl()

    def test_devctl_arm_and_log_verbs(self):
        with tempfile.TemporaryDirectory() as tmp:
            arm = Path(tmp) / "intro-sweep.armed"
            log = Path(tmp) / "intro-sweep.log"
            with mock.patch.dict(
                os.environ,
                {
                    "GREIA_INTRO_SWEEP_ARM": str(arm),
                    "GREIA_INTRO_SWEEP_LOG": str(log),
                },
            ):
                control = self._control(tmp)
                armed = control.arm_intro_sweep()
                self.assertEqual(armed, str(arm))
                self.assertTrue(arm.is_file())
                self.assertEqual(control.intro_sweep_log(), "")
                devinput._append_intro_sweep_log("INTRO_SWEEP step=1/10", log_path=log)
                self.assertIn("step=1/10", control.intro_sweep_log())

    def test_devctl_parses_arm_and_log_verbs(self):
        self.assertEqual(
            devctl.parse_args(["arm-intro-sweep"]).command, "arm-intro-sweep"
        )
        self.assertEqual(
            devctl.parse_args(["intro-sweep-log"]).command, "intro-sweep-log"
        )
        self.assertEqual(
            devinput.parse_args(["run-intro-sweep"]).command, "run-intro-sweep"
        )


class IntroSweepBootSurfaceTests(unittest.TestCase):
    def test_wrapper_is_fail_closed_and_calls_the_sweep_entry(self):
        wrapper = (
            PROJECT_ROOT
            / "build/overlay/usr/local/lib/greia-os/greia-intro-sweep"
        ).read_text(encoding="utf-8")
        self.assertIn("greia_platform.developer_input", wrapper)
        self.assertIn("run-intro-sweep", wrapper)
        self.assertIn("|| true", wrapper)
        self.assertIn("exit 0", wrapper)

    def test_service_is_marker_and_arm_gated_behind_the_launcher(self):
        unit = (
            PROJECT_ROOT
            / "build/overlay/etc/systemd/system/greia-intro-sweep.service"
        ).read_text(encoding="utf-8")
        self.assertIn(
            "ConditionPathExists=/etc/greia-os/developer-remote", unit
        )
        self.assertIn(
            "ConditionPathExists=/var/lib/greia-developer/intro-sweep.armed", unit
        )
        self.assertIn("After=greia-launcher.service", unit)
        self.assertIn(
            "ExecStart=/usr/local/lib/greia-os/greia-intro-sweep", unit
        )
        self.assertIn("Type=oneshot", unit)
        self.assertIn("WantedBy=graphical.target", unit)
        # Never orders or blocks the launcher itself.
        self.assertNotIn("Requires=greia-launcher.service", unit)
        self.assertNotIn("Before=greia-launcher.service", unit)


if __name__ == "__main__":
    unittest.main()
