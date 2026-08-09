from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from tools.r7_local_evidence import (
    LocalEvidenceConfig,
    LocalEvidenceError,
    LocalR7EvidenceOrchestrator,
    validate_package_report,
    validate_passive_probe,
)


class LocalR7EvidenceTests(unittest.TestCase):
    def test_run_root_must_be_outside_repository(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            repo = Path(temporary) / "repo"
            repo.mkdir()
            with self.assertRaisesRegex(LocalEvidenceError, "outside the repository"):
                LocalEvidenceConfig(
                    run_root=repo / "evidence",
                    repository_root=repo,
                ).validate()

    def test_plan_is_local_only_and_reuses_existing_r7_implementations(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            repo = root / "repo"
            repo.mkdir()
            orchestrator = LocalR7EvidenceOrchestrator(
                LocalEvidenceConfig(
                    run_root=root / "run",
                    repository_root=repo,
                )
            )
            plan = orchestrator.plan()

        self.assertIs(plan["hosted_execution"], False)
        self.assertIs(plan["github_actions_used"], False)
        self.assertIs(plan["source_image_mutated"], False)
        self.assertIs(plan["host_packages_installed_by_tool"], False)
        self.assertEqual(
            plan["package_candidates"],
            ["cage", "weston", "wlroots-runtime"],
        )
        self.assertEqual(
            plan["existing_implementations"],
            {
                "builder": "build/build-image.sh",
                "package_probe": "tools/r7_compositor_package_probe.py",
                "qemu_handoff": "tools/r7_qemu_kmsdrm_handoff_acceptance.py",
                "passive_probe": "greia_platform.direct_graphics_probe",
            },
        )

    def test_passive_evidence_cannot_waive_active_kmsdrm_or_input(self) -> None:
        valid = {
            "schema_version": 1,
            "passive": True,
            "assessment": {
                "active_kmsdrm_test_required": True,
                "active_seat_input_test_required": True,
            },
            "sdl": {
                "video_drivers": ["x11", "kmsdrm"],
                "kmsdrm_compiled": True,
            },
        }
        validate_passive_probe(valid)

        without_input = {
            **valid,
            "assessment": {
                **valid["assessment"],
                "active_seat_input_test_required": False,
            },
        }
        with self.assertRaisesRegex(LocalEvidenceError, "waives active seat/input"):
            validate_passive_probe(without_input)

        without_kms = {
            **valid,
            "assessment": {
                **valid["assessment"],
                "active_kmsdrm_test_required": False,
            },
        }
        with self.assertRaisesRegex(LocalEvidenceError, "waives active KMSDRM"):
            validate_passive_probe(without_kms)

    def test_package_report_requires_immutable_source_and_private_host_boundary(self) -> None:
        image_sha = "a" * 64
        valid = {
            "schema_version": 1,
            "ok": True,
            "candidate": "cage",
            "source_image_sha256": image_sha,
            "source_image_sha256_after": image_sha,
            "source_image_mutated": False,
            "host_devices_exposed": False,
            "host_sysfs_exposed": False,
            "host_run_exposed": False,
            "boot_or_service_changes": False,
            "apt_policy": {
                "install_recommends": False,
                "upgrades_allowed": False,
                "removals_allowed": False,
            },
            "packages": {
                "removed": [],
                "upgraded_or_changed": [],
            },
        }
        validate_package_report(valid, candidate="cage", image_sha=image_sha)

        for unsafe_key in (
            "source_image_mutated",
            "host_devices_exposed",
            "host_sysfs_exposed",
            "host_run_exposed",
            "boot_or_service_changes",
        ):
            unsafe = dict(valid)
            unsafe[unsafe_key] = True
            with self.subTest(unsafe_key=unsafe_key):
                with self.assertRaises(LocalEvidenceError):
                    validate_package_report(
                        unsafe,
                        candidate="cage",
                        image_sha=image_sha,
                    )

        changed = {
            **valid,
            "packages": {
                "removed": ["baseline-package"],
                "upgraded_or_changed": [],
            },
        }
        with self.assertRaisesRegex(LocalEvidenceError, "changed baseline packages"):
            validate_package_report(changed, candidate="cage", image_sha=image_sha)

    def test_kmsdrm_not_compiled_records_skip_without_invoking_qemu(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            repo = root / "repo"
            repo.mkdir()
            orchestrator = LocalR7EvidenceOrchestrator(
                LocalEvidenceConfig(
                    run_root=root / "run",
                    repository_root=repo,
                )
            )
            report = orchestrator._run_qemu_if_applicable(
                {"sdl": {"kmsdrm_compiled": False}},
                "b" * 64,
            )
            status = (root / "run/evidence/qemu-status.txt").read_text(
                encoding="utf-8"
            )

        self.assertIsNone(report)
        self.assertEqual(status, "not-run-kmsdrm-not-compiled\n")

    def test_summary_never_overclaims_unrun_input_or_physical_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            repo = root / "repo"
            repo.mkdir()
            orchestrator = LocalR7EvidenceOrchestrator(
                LocalEvidenceConfig(
                    run_root=root / "run",
                    repository_root=repo,
                )
            )
            summary = orchestrator._summary(
                source_sha="c" * 40,
                image_sha="d" * 64,
                passive={
                    "sdl": {
                        "video_drivers": ["kmsdrm"],
                        "kmsdrm_compiled": True,
                    }
                },
                package_reports={
                    "cage": {"classification": "PACKAGE_DELTA_PASS"},
                },
                qemu_report={
                    "classification": "SERIAL_QEMU_KMSDRM_HANDOFF_PASS"
                },
            )

        self.assertIs(summary["github_actions_used"], False)
        self.assertIs(summary["active_seat_input_evidence_complete"], False)
        self.assertIs(summary["physical_legacy_intel_acer_evidence_complete"], False)
        self.assertIs(summary["production_session_changed"], False)
        self.assertEqual(
            summary["qemu_classification"],
            "SERIAL_QEMU_KMSDRM_HANDOFF_PASS",
        )


if __name__ == "__main__":
    unittest.main()
