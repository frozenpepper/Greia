"""P5.4 boot-performance product wiring tests (source scope, no QEMU).

Proves the ``tools/x8_qemu/boot_perf.py`` fold reuses the frozen
instrument (``preintro_timing.compare``), derives the three P5.4
intervals from canonical markers, keeps regressions red, keeps missing
markers ``NOT_READY``, proves the seven-second intro unchanged and no
pre-intro update/health work, binds exact SHAs, and that the real entry
stays ``BLOCKED`` on this host (darwin, no Linux/QEMU facility) with
nothing fabricated.
"""

from __future__ import annotations

import hashlib
import sys
import tempfile
import unittest
from pathlib import Path

from tools.x8_qemu import boot_perf
from tools.x8_qemu import preintro_timing
from tools.x8_qemu.lifecycle import LifecycleConfig, LifecycleHarnessError


def _measurement(**overrides):
    base = {
        "label": "test",
        "qemu_start_monotonic": 100.0,
        "first_intro_frame": 110.0,
        "intro_end": 117.0,
        "interactive_ready": 120.0,
        "update_service_started": None,
        "timed_out": False,
    }
    base.update(overrides)
    return preintro_timing.BootMeasurement(**base)


def _serial(*, with_health_before=False, missing_first=False):
    lines = []
    if with_health_before:
        lines.append("Started Greia OS boot-health semantic service")
    if not missing_first:
        lines.append("GREIA_BOOT event=intro_first_frame_flipped monotonic_ns=1")
    lines.append("GREIA_BOOT event=intro_end monotonic_ns=2")
    lines.append("GREIA_BOOT event=launcher_interactive_ready monotonic_ns=3")
    return "\n".join(lines) + "\n"


def _hex(byte=b"x"):
    return hashlib.sha256(byte).hexdigest()


class BootPerfIntervalsTest(unittest.TestCase):
    def test_intervals_derive_three_required_spans(self):
        measurement = _measurement()
        intervals = boot_perf.derive_boot_perf_intervals(measurement)
        self.assertAlmostEqual(intervals["power_to_first_frame"], 10.0)
        self.assertAlmostEqual(intervals["total_to_ready"], 20.0)
        self.assertAlmostEqual(intervals["intro_duration"], 7.0)
        self.assertAlmostEqual(intervals["intro_end_to_ready"], 3.0)
        self.assertAlmostEqual(intervals["first_frame_to_ready"], 10.0)

    def test_missing_markers_are_none_never_interpolated(self):
        measurement = _measurement(first_intro_frame=None, intro_end=None)
        intervals = boot_perf.derive_boot_perf_intervals(measurement)
        self.assertIsNone(intervals["power_to_first_frame"])
        self.assertIsNone(intervals["intro_duration"])


class BootPerfCompareTest(unittest.TestCase):
    def test_canonical_pair_passes_strict(self):
        base = _measurement()
        activated = _measurement(
            qemu_start_monotonic=200.0,
            first_intro_frame=210.5,
            intro_end=217.5,
            interactive_ready=220.5,
        )
        record = boot_perf.build_boot_perf_record(
            baseline=base,
            activated=activated,
            serial_text=_serial(),
            installed_image_sha256=_hex(b"image"),
            source_sha256=_hex(b"source"),
        )
        self.assertEqual(record["overall"], "PASS")
        self.assertEqual(record["comparison"]["overall"], "PASS")
        self.assertEqual(record["health_preintro"]["verdict"], "PASS")

    def test_regression_stays_red_never_narrowed(self):
        base = _measurement()
        activated = _measurement(
            qemu_start_monotonic=200.0,
            first_intro_frame=220.0,  # +10 s over baseline, tolerance is +2 s
            intro_end=227.0,
            interactive_ready=230.0,
        )
        record = boot_perf.build_boot_perf_record(
            baseline=base,
            activated=activated,
            serial_text=_serial(),
            installed_image_sha256=_hex(b"image"),
            source_sha256=_hex(b"source"),
        )
        self.assertEqual(record["comparison"]["overall"], "FAIL")
        self.assertEqual(record["overall"], "FAIL")

    def test_missing_marker_is_not_ready_never_pass(self):
        base = _measurement()
        activated = _measurement(first_intro_frame=None, intro_end=None)
        record = boot_perf.build_boot_perf_record(
            baseline=base,
            activated=activated,
            serial_text=_serial(missing_first=True),
            installed_image_sha256=_hex(b"image"),
            source_sha256=_hex(b"source"),
        )
        self.assertEqual(record["comparison"]["overall"], "NOT_READY")
        self.assertEqual(record["overall"], "NOT_READY")

    def test_frozen_p4_update_before_first_is_fail(self):
        base = _measurement()
        activated = _measurement(
            qemu_start_monotonic=200.0,
            first_intro_frame=210.0,
            intro_end=217.0,
            interactive_ready=220.0,
            update_service_started=205.0,  # before first frame
        )
        result = preintro_timing.compare(base, activated)
        self.assertEqual(
            result["predicates"]["P4_no_update_work_pre_intro"]["verdict"], "FAIL"
        )
        record = boot_perf.build_boot_perf_record(
            baseline=base,
            activated=activated,
            serial_text=_serial(),
            installed_image_sha256=_hex(b"image"),
            source_sha256=_hex(b"source"),
        )
        self.assertEqual(record["overall"], "FAIL")


class BootPerfHealthIntroTest(unittest.TestCase):
    def test_health_work_before_first_is_red(self):
        verdict = boot_perf.check_no_preintro_health_work(
            _serial(with_health_before=True)
        )
        self.assertEqual(verdict["verdict"], "FAIL")

    def test_health_work_absent_is_pass(self):
        verdict = boot_perf.check_no_preintro_health_work(_serial())
        self.assertEqual(verdict["verdict"], "PASS")

    def test_health_work_after_first_is_not_flagged(self):
        text = (
            "GREIA_BOOT event=intro_first_frame_flipped monotonic_ns=1\n"
            "GREIA_BOOT event=intro_end monotonic_ns=2\n"
            "Started Greia OS boot-health semantic service\n"
            "GREIA_BOOT event=launcher_interactive_ready monotonic_ns=3\n"
        )
        verdict = boot_perf.check_no_preintro_health_work(text)
        self.assertEqual(verdict["verdict"], "PASS")

    def test_missing_first_frame_is_not_ready(self):
        verdict = boot_perf.check_no_preintro_health_work(
            _serial(missing_first=True)
        )
        self.assertEqual(verdict["verdict"], "NOT_READY")

    def test_seven_second_intro_proved_unchanged(self):
        proof = boot_perf.verify_seven_second_intro_unchanged()
        self.assertEqual(proof["total_seconds"], 7.0)
        self.assertEqual(proof["animation_seconds"], 5.0)
        self.assertEqual(proof["hold_seconds"], 2.0)

    def test_health_red_drags_record_red(self):
        base = _measurement()
        activated = _measurement(
            qemu_start_monotonic=200.0,
            first_intro_frame=210.5,
            intro_end=217.5,
            interactive_ready=220.5,
        )
        record = boot_perf.build_boot_perf_record(
            baseline=base,
            activated=activated,
            serial_text=_serial(with_health_before=True),
            installed_image_sha256=_hex(b"image"),
            source_sha256=_hex(b"source"),
        )
        self.assertEqual(record["health_preintro"]["verdict"], "FAIL")
        self.assertEqual(record["overall"], "FAIL")

    def test_positive_control_break_then_restore(self):
        base = _measurement()
        activated = _measurement(
            qemu_start_monotonic=200.0,
            first_intro_frame=210.5,
            intro_end=217.5,
            interactive_ready=220.5,
        )
        red = boot_perf.build_boot_perf_record(
            baseline=base,
            activated=activated,
            serial_text=_serial(with_health_before=True),
            installed_image_sha256=_hex(b"image"),
            source_sha256=_hex(b"source"),
        )
        self.assertEqual(red["overall"], "FAIL")
        green = boot_perf.build_boot_perf_record(
            baseline=base,
            activated=activated,
            serial_text=_serial(),
            installed_image_sha256=_hex(b"image"),
            source_sha256=_hex(b"source"),
        )
        self.assertEqual(green["overall"], "PASS")


class BootPerfBindingTest(unittest.TestCase):
    def test_missing_sha_refuses_never_fabricated(self):
        base = _measurement()
        with self.assertRaises(LifecycleHarnessError):
            boot_perf.build_boot_perf_record(
                baseline=base,
                activated=_measurement(),
                serial_text=_serial(),
                installed_image_sha256="not-a-sha",
                source_sha256=_hex(b"source"),
            )
        with self.assertRaises(LifecycleHarnessError):
            boot_perf.build_boot_perf_record(
                baseline=base,
                activated=_measurement(),
                serial_text=_serial(),
                installed_image_sha256=_hex(b"image"),
                source_sha256="",
            )

    def test_record_binds_exact_shas(self):
        image_sha = _hex(b"image")
        source_sha = _hex(b"source")
        record = boot_perf.build_boot_perf_record(
            baseline=_measurement(),
            activated=_measurement(
                qemu_start_monotonic=200.0,
                first_intro_frame=210.5,
                intro_end=217.5,
                interactive_ready=220.5,
            ),
            serial_text=_serial(),
            installed_image_sha256=image_sha,
            source_sha256=source_sha,
        )
        self.assertEqual(record["installed_image_sha256"], image_sha)
        self.assertEqual(record["source_sha256"], source_sha)


class BootPerfEntryTest(unittest.TestCase):
    def test_real_entry_is_blocked_on_this_host(self):
        with tempfile.TemporaryDirectory(prefix="greia-boot-perf-") as tmp:
            out = Path(tmp) / "out"
            out.mkdir()
            config = LifecycleConfig(output_dir=out)
            image = Path(tmp) / "installed.img"
            image.write_bytes(b"installed-bytes")
            bundle = Path(tmp) / "candidate.greiaupdate"
            bundle.write_bytes(b"bundle-bytes")
            with self.assertRaises(LifecycleHarnessError) as ctx:
                boot_perf.run_boot_perf_product(
                    config=config,
                    installed_image=image,
                    release_bundle=bundle,
                    baseline=_measurement(),
                )
            self.assertIn("BLOCKED", str(ctx.exception))

    def test_missing_source_sha_is_blocked_not_minted(self):
        with tempfile.TemporaryDirectory(prefix="greia-boot-perf-") as tmp:
            out = Path(tmp) / "out"
            out.mkdir()
            config = LifecycleConfig(output_dir=out)
            image = Path(tmp) / "installed.img"
            image.write_bytes(b"installed-bytes")
            with self.assertRaises(LifecycleHarnessError) as ctx:
                boot_perf.run_boot_perf_product(
                    config=config,
                    installed_image=image,
                    release_bundle=None,
                    baseline=_measurement(),
                    measure_fn=lambda **kwargs: _measurement(),
                )
            # Either the facility gate (darwin) or the source-SHA gate
            # fires first; both are BLOCKED, never a minted record.
            self.assertIn("BLOCKED", str(ctx.exception))

    def test_preregistration_is_available_for_evidence(self):
        text = boot_perf.preregistration_text()
        self.assertIn("P1", text)
        self.assertIn("P4", text)


if __name__ == "__main__":
    unittest.main()
