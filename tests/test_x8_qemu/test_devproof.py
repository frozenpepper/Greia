"""T7-DEVPROOF envelope contract: D31, interruptions, resources, gates.

Pins the envelope wiring in ``tools/x8_qemu/devproof.py`` plus its
additive attachment to the lifecycle reports. No QEMU, loop, mount, or
valued-device contact here: device-measured values stay fail-closed
behind ``require_device_host`` (live green belongs to a capable Linux
host); these tests prove the shape, the RED controls, and the
source-scope measurements.
"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from tools.x8_qemu.devproof import (
    CGROUP_CEILING_BYTES,
    D31_FIXTURES,
    GATE_PAYLOAD_BYTES,
    INTERRUPTION_CASES,
    INTERRUPTION_EXPECTED_SLOT,
    PAYLOAD_ACCEPT_BYTES,
    DevproofContractError,
    DevproofError,
    DevproofPreflightError,
    cgroup_gate_report,
    check_storage_preflight,
    envelope_spec,
    measure_resource_envelope,
    prove_near_full_preflight,
    read_cgroup_peak_bytes,
    read_d31_representative_state,
    record_leg_sample,
    run_cgroup_gate,
    run_envelope_device,
    run_envelope_source_scope,
    run_interruption_case,
    run_interruption_matrix,
    run_d31_rollback_proof,
    summarize_leg_peaks,
    verify_d31_rollback,
    write_d31_representative_state,
)


class EnvelopeSpecTests(unittest.TestCase):
    def test_frozen_envelope_shape(self) -> None:
        spec = envelope_spec()
        self.assertEqual(list(spec["interruption_cases"]), list(INTERRUPTION_CASES))
        self.assertEqual(len(INTERRUPTION_CASES), 7)
        self.assertEqual(
            spec["interruption_expected_slot"], dict(INTERRUPTION_EXPECTED_SLOT)
        )
        self.assertEqual(list(spec["d31_fixtures"]), list(D31_FIXTURES))
        self.assertEqual(len(D31_FIXTURES), 5)
        self.assertEqual(spec["cgroup_ceiling_bytes"], 768 * 1024 * 1024)
        self.assertEqual(spec["payload_accept_bytes"], 256 * 1024 * 1024)
        self.assertEqual(spec["gate_payload_bytes"], 220 * 1024 * 1024)
        self.assertEqual(CGROUP_CEILING_BYTES, 768 * 1024 * 1024)
        self.assertEqual(PAYLOAD_ACCEPT_BYTES, 256 * 1024 * 1024)
        self.assertEqual(GATE_PAYLOAD_BYTES, 220 * 1024 * 1024)
        self.assertLessEqual(GATE_PAYLOAD_BYTES, PAYLOAD_ACCEPT_BYTES)
        self.assertTrue(spec["device_measured_only"])


class D31RollbackTests(unittest.TestCase):
    def test_full_proof_green_through_store_apis(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            proof = run_d31_rollback_proof(Path(tmp) / "d31")
            self.assertTrue(proof["green"])
            self.assertEqual(proof["journal_state"], "failed")
            self.assertEqual(proof["default_slot"], "A")
            self.assertTrue(proof["semantic_preserved"])

    def test_settings_drift_is_red_then_restores_green(self) -> None:
        """Break -> RED -> restore -> GREEN on the D31 semantic check."""
        from greia_platform.hardware import HardwareSettingsStore
        from tools.x8_qemu.devproof import _hardware_defaults

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "persist"
            before = write_d31_representative_state(root)
            settings_path = root / "device-settings" / "settings.json"
            intact = settings_path.read_bytes()
            # BREAK: drift the settings value outside the store contract.
            store = HardwareSettingsStore(_hardware_defaults(), root / "device-settings")
            store.update(touchpad_tap=False, touchpad_speed=0.1)
            after = read_d31_representative_state(root)
            with self.assertRaises(DevproofError):
                verify_d31_rollback(before, after)
            # RESTORE the exact bytes and re-prove GREEN.
            settings_path.write_bytes(intact)
            restored = read_d31_representative_state(root)
            verify_d31_rollback(before, restored)

    def test_missing_fixture_is_red(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "persist"
            before = write_d31_representative_state(root)
            after = dict(read_d31_representative_state(root))
            del after["activity-save"]
            with self.assertRaises(DevproofContractError):
                verify_d31_rollback(before, after)


class InterruptionMatrixTests(unittest.TestCase):
    def test_all_seven_cases_reconcile_to_expected_slots(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            matrix = run_interruption_matrix(Path(tmp) / "matrix")
            self.assertTrue(matrix["green"])
            self.assertEqual(len(matrix["cases"]), 7)
            for entry in matrix["cases"]:
                self.assertEqual(
                    entry["reconciled_slot"],
                    INTERRUPTION_EXPECTED_SLOT[entry["case"]],
                )
                self.assertEqual(entry["expected"], entry["reconciled_slot"])
                self.assertTrue(entry["green"])
            self.assertEqual(
                [entry["case"] for entry in matrix["cases"]],
                list(INTERRUPTION_CASES),
            )

    def test_committed_backend_converges_on_committed_slot(self) -> None:
        """Positive control: case 7 must prove backend B, not assert A."""
        from greia_platform.grub_ab import GrubEnvBackend

        with tempfile.TemporaryDirectory() as tmp:
            entry = run_interruption_case(
                "committed-backend-unwritten-accepted-state", Path(tmp)
            )
            self.assertEqual(entry["reconciled_slot"], "B")
            # The backend on disk agrees: re-read the committed default.
            backend = GrubEnvBackend.attach(
                Path(tmp) / "committed_backend_unwritten_accepted_state"
                / "boot-control"
            )
            self.assertEqual(backend.inspect().default_slot, "B")

    def test_unknown_case_is_red(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(DevproofContractError):
                run_interruption_case("not-a-case", Path(tmp))


class ResourceEnvelopeTests(unittest.TestCase):
    def test_envelope_is_measured_with_named_denominator(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            envelope = measure_resource_envelope(Path(tmp) / "work")
            for key in (
                "max_rss_bytes",
                "decompression_delta_bytes",
                "finalization_peak_rss_bytes",
                "staging_workspace_bytes",
                "disk_total_bytes",
                "disk_used_bytes",
                "disk_free_bytes",
                "slot_a_bytes",
                "slot_b_bytes",
                "persist_minimum_bytes",
                "persist_headroom_bytes",
                "diagnostic_budget_bytes",
            ):
                self.assertGreaterEqual(envelope[key], 0)
            self.assertGreater(envelope["max_rss_bytes"], 0)
            self.assertGreater(envelope["disk_total_bytes"], 0)
            self.assertIn("denominator", envelope)

    def test_envelope_uses_plan_slot_facts_and_bundle_presence(self) -> None:
        from tools.x8_qemu.runner import (
            PROFILE_PERSIST_MINIMUM_BYTES,
            PROFILE_SLOT_BYTES,
        )

        with tempfile.TemporaryDirectory() as tmp:
            bundle = Path(tmp) / "r21.greiaupdate"
            bundle.write_bytes(b"fake-bundle-bytes")
            envelope = measure_resource_envelope(
                Path(tmp) / "work", bundle_path=bundle
            )
            self.assertEqual(envelope["slot_a_bytes"], PROFILE_SLOT_BYTES)
            self.assertEqual(envelope["slot_b_bytes"], PROFILE_SLOT_BYTES)
            self.assertEqual(
                envelope["persist_minimum_bytes"], PROFILE_PERSIST_MINIMUM_BYTES
            )
            self.assertTrue(envelope["bundle_present"])
            self.assertEqual(envelope["bundle_bytes"], bundle.stat().st_size)
            absent = measure_resource_envelope(Path(tmp) / "work-absent")
            self.assertFalse(absent["bundle_present"])
            self.assertEqual(absent["bundle_bytes"], 0)

    def test_preflight_green_and_near_full_refusal(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            proof = prove_near_full_preflight(Path(tmp) / "preflight")
            self.assertTrue(proof["green"])
            self.assertTrue(proof["negative"]["refused"])
            self.assertFalse((Path(tmp) / "preflight" / "preflight-sentinel").exists())

    def test_preflight_refuses_before_staging_work(self) -> None:
        import shutil as _shutil

        with tempfile.TemporaryDirectory() as tmp:
            disk = _shutil.disk_usage(tmp)
            with self.assertRaises(DevproofPreflightError):
                check_storage_preflight(
                    Path(tmp),
                    # Total capacity is invariant while free space can move
                    # as unrelated full-suite temporary files are deleted.
                    required_bytes=disk.total + 1,
                    reserved_bytes=1024,
                )

    def test_preflight_rejects_non_positive_requirement(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(DevproofContractError):
                check_storage_preflight(Path(tmp), required_bytes=0)


class CgroupGateTests(unittest.TestCase):
    def test_representative_payload_green_with_headroom(self) -> None:
        verdict = cgroup_gate_report(
            payload_bytes=GATE_PAYLOAD_BYTES,
            peak_bytes=CGROUP_CEILING_BYTES - 1024,
            swap_off=True,
            require_swap_off=True,
        )
        self.assertTrue(verdict["green"])
        self.assertFalse(verdict["diagnostic_only"])
        self.assertGreater(verdict["headroom_bytes"], 0)

    def test_larger_payload_is_diagnostic_only_never_green(self) -> None:
        """Positive control: the T2-closed scaling range never goes green."""
        verdict = cgroup_gate_report(
            payload_bytes=300 * 1024 * 1024, peak_bytes=1024
        )
        self.assertFalse(verdict["green"])
        self.assertTrue(verdict["diagnostic_only"])

    def test_ceiling_breach_is_red(self) -> None:
        verdict = cgroup_gate_report(
            payload_bytes=GATE_PAYLOAD_BYTES, peak_bytes=CGROUP_CEILING_BYTES
        )
        self.assertFalse(verdict["green"])

    def test_swap_on_is_red_where_required(self) -> None:
        """Positive control: swap-on fails the device-scope gate."""
        verdict = cgroup_gate_report(
            payload_bytes=GATE_PAYLOAD_BYTES,
            peak_bytes=CGROUP_CEILING_BYTES - 1024,
            swap_off=False,
            require_swap_off=True,
        )
        self.assertFalse(verdict["green"])
        self.assertIn("swap", str(verdict.get("reason", "")).lower())

    def test_gate_measures_a_real_peak(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            gate = run_cgroup_gate(Path(tmp), payload_bytes=GATE_PAYLOAD_BYTES)
            self.assertIn("peak_bytes", gate["peak"])
            self.assertIn("source", gate["peak"])
            self.assertIn("streaming_peak_bytes", gate["peak"])
            self.assertGreater(int(gate["peak"]["streaming_peak_bytes"]), 0)
            self.assertEqual(gate["payload_bytes"], GATE_PAYLOAD_BYTES)
            peak = read_cgroup_peak_bytes()
            self.assertGreater(int(peak["peak_bytes"]), 0)


class EnvelopeRunnerTests(unittest.TestCase):
    def test_source_scope_envelope_green_without_device_claim(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            report = run_envelope_source_scope(Path(tmp) / "out")
            self.assertTrue(report["ok"])
            self.assertEqual(report["classification"], "SOURCE_SCOPE_T7_DEVPROOF")
            self.assertFalse(report["device_scope"]["executed"])
            self.assertTrue(report["d31"]["green"])
            self.assertTrue(report["interruptions"]["green"])
            self.assertTrue(report["near_full_preflight"]["green"])
            self.assertTrue((Path(tmp) / "out" / "devproof-envelope.json").is_file())

    def test_device_envelope_fails_closed_off_capable_host(self) -> None:
        import sys as _sys

        if _sys.platform == "linux" and Path("/dev").exists():
            self.skipTest("device gate is evaluated on Linux device runs")
        with tempfile.TemporaryDirectory() as tmp:
            # Preregistered predicate: red stays red, never proxied by
            # source-scope evidence.
            with self.assertRaises(Exception):
                run_envelope_device(Path(tmp) / "out")

    def test_lifecycle_source_report_carries_envelope(self) -> None:
        from tools.x8_qemu.lifecycle import LifecycleConfig, LifecycleHarness

        with tempfile.TemporaryDirectory() as tmp:
            harness = LifecycleHarness(
                LifecycleConfig(output_dir=Path(tmp) / "out")
            )
            report = harness.run_source_scope()
            self.assertTrue(report["ok"])
            envelope = report["devproof_envelope"]
            assert isinstance(envelope, dict)
            self.assertTrue(envelope["ok"])
            self.assertTrue(envelope["d31"]["green"])
            self.assertEqual(len(envelope["interruptions"]["cases"]), 7)

    def test_envelope_uses_production_seams_without_fakes(self) -> None:
        from tools.x8_qemu import devproof as module

        text = Path(module.__file__).read_text(encoding="utf-8")
        for required in (
            "HardwareSettingsStore",
            "ProfileStore",
            "ProfileHistoryStore",
            "ActivityStorageService",
            "ParentDeviceCredentialStore",
            "GrubEnvBackend",
            "BootTransactionCoordinator",
            "mark_candidate_unhealthy",
        ):
            self.assertIn(required, text)
        for forbidden in (
            "simulate_reboot(",
            "FakeGrubBackend",
            "FakeSlotStore",
        ):
            self.assertNotIn(forbidden, text)


class LegTracingTests(unittest.TestCase):
    def test_leg_sample_measures_real_rss(self) -> None:
        sample = record_leg_sample("fresh-install-A")
        self.assertEqual(sample["leg"], "fresh-install-A")
        self.assertEqual(sample["surface"], "SOURCE_SCOPE")
        self.assertGreater(int(sample["rss_bytes"]), 0)
        device = record_leg_sample("stage-B-one-shot", surface="DEVICE")
        self.assertEqual(device["surface"], "DEVICE")

    def test_leg_sample_rejects_empty_leg_and_surface(self) -> None:
        with self.assertRaises(DevproofContractError):
            record_leg_sample("")
        with self.assertRaises(DevproofContractError):
            record_leg_sample("fresh-install-A", surface="GUEST")

    def test_leg_summary_defers_without_samples(self) -> None:
        summary = summarize_leg_peaks(None)
        self.assertEqual(summary["tracing"], "deferred")
        self.assertEqual(summary["legs"], [])
        self.assertIsNone(summary["install_update_max_rss_bytes"])
        self.assertIsNone(summary["install_update_min_memavailable_bytes"])
        self.assertEqual(summarize_leg_peaks([])["tracing"], "deferred")

    def test_leg_summary_records_max_across_legs(self) -> None:
        samples = [
            record_leg_sample("fresh-install-A"),
            record_leg_sample("stage-B-one-shot"),
        ]
        summary = summarize_leg_peaks(samples)
        self.assertEqual(summary["tracing"], "recorded")
        self.assertEqual(summary["leg_count"], 2)
        self.assertEqual(
            [row["leg"] for row in summary["legs"]],
            ["fresh-install-A", "stage-B-one-shot"],
        )
        self.assertEqual(
            summary["install_update_max_rss_bytes"],
            max(int(sample["rss_bytes"]) for sample in samples),
        )

    def test_leg_summary_red_on_unmeasured_sample_then_green(self) -> None:
        """Break -> RED -> restore -> GREEN on the leg-peak summary."""
        samples = [dict(record_leg_sample("fresh-install-A"))]
        broken = dict(samples[0])
        broken["rss_bytes"] = 0
        with self.assertRaises(DevproofContractError):
            summarize_leg_peaks([broken])
        restored = summarize_leg_peaks(samples)
        self.assertEqual(restored["tracing"], "recorded")

    def test_envelope_carries_leg_peaks_or_explicit_deferred(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            samples = [
                record_leg_sample("fresh-install-A"),
                record_leg_sample("boot-B-commit"),
            ]
            envelope = measure_resource_envelope(
                Path(tmp) / "work-legs", leg_samples=samples
            )
            peaks = envelope["leg_peaks"]
            assert isinstance(peaks, dict)
            self.assertEqual(peaks["tracing"], "recorded")
            self.assertEqual(
                envelope["install_update_max_rss_bytes"],
                max(int(sample["rss_bytes"]) for sample in samples),
            )
            deferred = measure_resource_envelope(Path(tmp) / "work-nolegs")
            assert isinstance(deferred["leg_peaks"], dict)
            self.assertEqual(deferred["leg_peaks"]["tracing"], "deferred")
            self.assertIsNone(deferred["install_update_max_rss_bytes"])

    def test_source_runner_threads_lifecycle_leg_samples(self) -> None:
        samples = [record_leg_sample("fresh-install-A")]
        with tempfile.TemporaryDirectory() as tmp:
            report = run_envelope_source_scope(
                Path(tmp) / "out", leg_samples=samples
            )
            self.assertTrue(report["ok"])
            peaks = report["resource_envelope"]["leg_peaks"]
            assert isinstance(peaks, dict)
            self.assertEqual(peaks["tracing"], "recorded")
            self.assertEqual(
                [row["leg"] for row in peaks["legs"]], ["fresh-install-A"]
            )


if __name__ == "__main__":
    unittest.main()
