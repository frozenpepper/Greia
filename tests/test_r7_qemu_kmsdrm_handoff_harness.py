from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
TOOLS = PROJECT_ROOT / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

from r7_qemu_kmsdrm_handoff_acceptance import (  # noqa: E402
    HandoffHarnessConfig,
    QemuKMSDRMHandoffError,
    QemuKMSDRMSerialHandoffHarness,
    handoff_guest_runner_text,
    validate_handoff_evidence,
)


def passing_summary() -> dict[str, object]:
    return {
        "schema_version": 1,
        "ok": True,
        "phase": "complete",
        "service_status": "0",
        "active_vt": "tty1",
        "launcher_masked": True,
    }


def _phase(digest: str) -> dict[str, object]:
    return {
        "actual_video_driver": "kmsdrm",
        "surface": {"width": 1024, "height": 768},
        "frame_sha256": digest,
        "duration_seconds": 0.1,
    }


def passing_handoff() -> dict[str, object]:
    return {
        "schema_version": 1,
        "ok": True,
        "requested_video_driver": "kmsdrm",
        "shell_initial": _phase("a" * 64),
        "clean_child": {
            "return_code": 0,
            "result": {
                "schema_version": 1,
                "ok": True,
                "actual_video_driver": "kmsdrm",
            },
        },
        "shell_after_clean": _phase("b" * 64),
        "crash_child": {
            "return_code": 23,
            "result": {
                "schema_version": 1,
                "ok": True,
                "actual_video_driver": "kmsdrm",
                "surface": {"width": 1024, "height": 768},
                "frame_sha256": "d" * 64,
                "intentional_abrupt_exit": True,
            },
        },
        "shell_after_crash": _phase("c" * 64),
        "recovery": {
            "clean_child_reacquired": True,
            "crash_child_reacquired": True,
        },
    }


class QemuKMSDRMHandoffHarnessTests(unittest.TestCase):
    def test_plan_layers_two_boots_over_same_disposable_clone(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            harness = QemuKMSDRMSerialHandoffHarness(
                HandoffHarnessConfig(
                    source_image=root / "production.img",
                    output_dir=root / "out",
                )
            )
            plan = harness.plan()

        self.assertIs(plan["source_image_mutated"], False)
        self.assertIs(plan["production_launcher_changed"], False)
        self.assertEqual(len(plan["boots"]), 2)
        self.assertEqual(plan["boots"][0]["purpose"], "baseline-active-kmsdrm")
        self.assertEqual(
            plan["boots"][1]["purpose"], "serial-shell-child-shell-handoff"
        )
        self.assertEqual(
            plan["boots"][1]["service"],
            "greia-kmsdrm-handoff-acceptance.service",
        )
        self.assertTrue(harness.baseline.config.keep_test_image)

    def test_guest_runner_rejects_x_runs_handoff_then_powers_off(self) -> None:
        script = handoff_guest_runner_text()
        self.assertLess(script.index("phase=reject-x"), script.index("phase=serial-handoff"))
        self.assertLess(script.index("phase=serial-handoff"), script.index("phase=complete"))
        self.assertIn("chvt 1", script)
        self.assertIn("/proc/[0-9]*/comm", script)
        self.assertIn('systemctl start "$service"', script)
        self.assertIn("greia-kmsdrm-handoff-acceptance.service", script)
        self.assertIn("clean_child_reacquired", script)
        self.assertIn("crash_child_reacquired", script)
        self.assertIn('get("return_code") != 23', script)
        self.assertIn("systemctl poweroff --no-block", script)
        self.assertIn("trap finish EXIT HUP INT TERM", script)
        self.assertNotIn("greia-run-kmsdrm-acceptance", script)

        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "handoff-guest.sh"
            path.write_text(script, encoding="utf-8")
            syntax = subprocess.run(
                ["sh", "-n", str(path)],
                text=True,
                capture_output=True,
                check=False,
            )
        self.assertEqual(syntax.returncode, 0, syntax.stderr)

    def test_passing_handoff_evidence_is_accepted(self) -> None:
        validate_handoff_evidence(passing_summary(), passing_handoff())

    def test_summary_must_prove_launcher_masked_and_tty1(self) -> None:
        for key, value, expected in (
            ("launcher_masked", False, "launcher"),
            ("active_vt", "tty2", "tty1"),
            ("service_status", "1", "service"),
        ):
            with self.subTest(key=key):
                summary = passing_summary()
                summary[key] = value
                with self.assertRaisesRegex(QemuKMSDRMHandoffError, expected):
                    validate_handoff_evidence(summary, passing_handoff())

    def test_all_shell_phases_must_use_kmsdrm(self) -> None:
        handoff = passing_handoff()
        handoff["shell_after_crash"]["actual_video_driver"] = "x11"
        with self.assertRaisesRegex(QemuKMSDRMHandoffError, "shell_after_crash"):
            validate_handoff_evidence(passing_summary(), handoff)

    def test_shell_frame_hashes_must_be_valid_and_not_all_identical(self) -> None:
        malformed = passing_handoff()
        malformed["shell_after_clean"]["frame_sha256"] = "bad"
        with self.assertRaisesRegex(QemuKMSDRMHandoffError, "malformed frame hash"):
            validate_handoff_evidence(passing_summary(), malformed)

        identical = passing_handoff()
        identical["shell_after_clean"]["frame_sha256"] = "a" * 64
        identical["shell_after_crash"]["frame_sha256"] = "a" * 64
        with self.assertRaisesRegex(QemuKMSDRMHandoffError, "distinct frame hashes"):
            validate_handoff_evidence(passing_summary(), identical)

    def test_crash_child_requires_expected_abrupt_exit_and_evidence(self) -> None:
        handoff = passing_handoff()
        handoff["crash_child"]["return_code"] = 1
        with self.assertRaisesRegex(QemuKMSDRMHandoffError, "crash child"):
            validate_handoff_evidence(passing_summary(), handoff)

        handoff = passing_handoff()
        handoff["crash_child"]["result"]["intentional_abrupt_exit"] = False
        with self.assertRaisesRegex(QemuKMSDRMHandoffError, "abrupt kmsdrm"):
            validate_handoff_evidence(passing_summary(), handoff)


if __name__ == "__main__":
    unittest.main()
