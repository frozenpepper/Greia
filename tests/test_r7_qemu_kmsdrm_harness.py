from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path

from tools.r7_qemu_kmsdrm_acceptance import (
    EvidenceBundle,
    HarnessConfig,
    QemuKMSDRMAcceptanceError,
    QemuKMSDRMAcceptanceHarness,
    guest_runner_text,
    guest_unit_text,
    validate_evidence,
)


def passing_bundle() -> EvidenceBundle:
    return EvidenceBundle(
        summary={
            "schema_version": 1,
            "ok": True,
            "phase": "complete",
            "acceptance_status": "0",
            "active_vt": "tty1",
            "launcher_masked": True,
        },
        passive={
            "schema_version": 1,
            "passive": True,
            "sdl": {"kmsdrm_compiled": True},
            "drm": {"card_nodes": ["card0"]},
            "assessment": {"kmsdrm_prerequisites_visible": True},
        },
        active={
            "schema_version": 1,
            "ok": True,
            "requested_video_driver": "kmsdrm",
            "actual_video_driver": "kmsdrm",
            "surface": {"width": 1024, "height": 768},
            "frame_count": 3,
            "frame_sha256": ["a" * 64, "b" * 64, "c" * 64],
        },
    )


class QemuKMSDRMHarnessTests(unittest.TestCase):
    def test_plan_is_non_mutating_and_uses_headless_virtio_gpu(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            harness = QemuKMSDRMAcceptanceHarness(
                HarnessConfig(
                    source_image=root / "production.img",
                    output_dir=root / "out",
                )
            )
            plan = harness.plan()
            self.assertIs(plan["source_image_mutated"], False)
            self.assertIs(plan["normal_launcher_masked_only_in_clone"], True)
            argv = plan["qemu"]
            self.assertIsInstance(argv, list)
            self.assertIn("virtio-vga", argv)
            self.assertIn("none", argv)
            self.assertIn("-display", argv)
            self.assertIn("-vga", argv)
            self.assertIn("-nic", argv)
            self.assertIn("-no-reboot", argv)
            self.assertNotIn("-snapshot", argv)

    def test_qemu_command_preserves_guest_disk_writes_and_has_no_network(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            harness = QemuKMSDRMAcceptanceHarness(
                HarnessConfig(source_image=root / "source.img", output_dir=root / "out")
            )
            image = root / "clone.img"
            argv = harness.qemu_argv(image)
            self.assertEqual(argv[argv.index("-device") + 1], "virtio-vga")
            self.assertEqual(argv[argv.index("-display") + 1], "none")
            self.assertEqual(argv[argv.index("-vga") + 1], "none")
            self.assertEqual(argv[argv.index("-nic") + 1], "none")
            drive = argv[argv.index("-drive") + 1]
            self.assertIn(f"file={image}", drive)
            self.assertIn("format=raw", drive)
            self.assertNotIn("snapshot=on", drive)

    def test_guest_boot_unit_runs_after_first_boot_without_enabling_normal_launcher(self) -> None:
        unit = guest_unit_text()
        self.assertIn("After=greia-first-boot.service", unit)
        self.assertIn("Requires=greia-first-boot.service", unit)
        self.assertIn("Conflicts=greia-launcher.service", unit)
        self.assertIn("ExecStart=/usr/local/sbin/greia-r7-qemu-kmsdrm-boot-test", unit)
        self.assertIn("WantedBy=multi-user.target", unit)

    def test_guest_runner_requires_passive_prerequisites_then_active_kmsdrm(self) -> None:
        script = guest_runner_text()
        passive_index = script.index("phase=passive-probe")
        active_index = script.index("phase=active-acceptance")
        complete_index = script.index("phase=complete")
        self.assertLess(passive_index, active_index)
        self.assertLess(active_index, complete_index)
        self.assertIn("chvt 1", script)
        self.assertIn("kmsdrm_compiled", script)
        self.assertIn("kmsdrm_prerequisites_visible", script)
        self.assertIn('systemctl start "$acceptance"', script)
        self.assertIn('payload.get("actual_video_driver") != "kmsdrm"', script)
        self.assertIn("/proc/[0-9]*/comm", script)
        self.assertIn("systemctl poweroff --no-block", script)
        self.assertNotIn("greia-run-kmsdrm-acceptance", script)

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "guest-runner.sh"
            path.write_text(script, encoding="utf-8")
            syntax = subprocess.run(
                ["sh", "-n", str(path)],
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(syntax.returncode, 0, syntax.stderr)

    def test_strong_evidence_bundle_passes(self) -> None:
        validate_evidence(passing_bundle())

    def test_wrong_active_driver_is_rejected(self) -> None:
        baseline = passing_bundle()
        active = dict(baseline.active)
        active["actual_video_driver"] = "x11"
        with self.assertRaisesRegex(QemuKMSDRMAcceptanceError, "not kmsdrm"):
            validate_evidence(
                EvidenceBundle(
                    summary=baseline.summary,
                    passive=baseline.passive,
                    active=active,
                )
            )

    def test_missing_passive_kmsdrm_is_rejected(self) -> None:
        baseline = passing_bundle()
        passive = dict(baseline.passive)
        passive["sdl"] = {"kmsdrm_compiled": False}
        passive["assessment"] = {"kmsdrm_prerequisites_visible": False}
        with self.assertRaisesRegex(QemuKMSDRMAcceptanceError, "does not enumerate"):
            validate_evidence(
                EvidenceBundle(
                    summary=baseline.summary,
                    passive=passive,
                    active=baseline.active,
                )
            )

    def test_malformed_nested_evidence_fails_closed(self) -> None:
        baseline = passing_bundle()
        passive = dict(baseline.passive)
        passive["sdl"] = "not-an-object"
        with self.assertRaisesRegex(QemuKMSDRMAcceptanceError, "does not enumerate"):
            validate_evidence(
                EvidenceBundle(
                    summary=baseline.summary,
                    passive=passive,
                    active=baseline.active,
                )
            )

    def test_invalid_frame_hash_is_rejected(self) -> None:
        baseline = passing_bundle()
        active = dict(baseline.active)
        active["frame_sha256"] = ["a" * 64, "b" * 64, "not-a-sha256"]
        with self.assertRaisesRegex(QemuKMSDRMAcceptanceError, "malformed frame hash"):
            validate_evidence(
                EvidenceBundle(
                    summary=baseline.summary,
                    passive=baseline.passive,
                    active=active,
                )
            )

    def test_invalid_config_fails_closed(self) -> None:
        with self.assertRaisesRegex(QemuKMSDRMAcceptanceError, "timeout"):
            QemuKMSDRMAcceptanceHarness(
                HarnessConfig(
                    source_image=Path("source.img"),
                    output_dir=Path("out"),
                    timeout_seconds=5,
                )
            )


if __name__ == "__main__":
    unittest.main()
