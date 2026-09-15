"""P5.1 product-image mode + test-only guest-control seam (focused tests).

Covers the brief's acceptance for ``tools/x8_qemu/product.py`` without
QEMU, loop, mount or valued-device contact:

- the mode reuses (never duplicates) the frozen 8-transition sequence,
  observation folds and transition contract;
- the control seam drives the real guest sockets and fails closed when
  removed or misrouted (positive control: break -> RED -> restore ->
  GREEN);
- structural pins prove the control module is test-only, can never be
  an attestation source, and leaves official media/release profiles
  unchanged;
- the mode returns BLOCKED (never a fabricated boot) where the
  disposable Linux/QEMU/loop/mount facility or official image is absent.
"""

from __future__ import annotations

import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock as _mock

from tools.x8_qemu import product as _product
from tools.x8_qemu.lifecycle import (
    BOOT_OUTCOME_EXPECTED_SLOT,
    LAUNCHER_ACCEPTANCE_LEGS,
    LIFECYCLE_SEQUENCE,
    PROJECT_ROOT,
    SHIPPED_UPDATE_LEGS,
    LifecycleConfig,
    LifecycleHarness,
    LifecycleHarnessError,
    assert_lifecycle_transitions,
)
from tools.x8_qemu.product import (
    ATTESTATION_SOURCES,
    BOOT_HEALTH_SOCKET_PATH,
    CONTROL_DISK_LABEL,
    CONTROL_PHASES,
    CONTROL_RUNNER_PATH,
    CONTROL_UNIT_NAME,
    INSTALL_SOCKET_PATH,
    UPDATE_SOCKET_PATH,
    ProductHarness,
    assert_control_absent_from_production,
    attest_product_boot,
    clone_product_image,
    control_runner_text,
    control_unit_text,
    inject_control_into_root,
    product_spec,
    read_control_phase,
    require_product_host,
    validate_control_present,
    write_control_phase,
)


def _product_harness(tmp: str, **kwargs: object) -> ProductHarness:
    return ProductHarness(
        LifecycleConfig(output_dir=Path(tmp) / "out"), **kwargs  # type: ignore[arg-type]
    )


def _fake_guest_root(base: Path) -> Path:
    (base / "etc/systemd/system").mkdir(parents=True, exist_ok=True)
    return base


class ProductSpecReuseTests(unittest.TestCase):
    def test_spec_reuses_frozen_sequence_and_contract(self) -> None:
        spec = product_spec()
        self.assertEqual(list(spec["lifecycle_sequence"]), list(LIFECYCLE_SEQUENCE))
        self.assertEqual(len(spec["lifecycle_sequence"]), 8)
        self.assertEqual(list(spec["shipped_update_legs"]), list(SHIPPED_UPDATE_LEGS))
        self.assertEqual(
            list(spec["launcher_acceptance_legs"]), list(LAUNCHER_ACCEPTANCE_LEGS)
        )
        self.assertFalse(spec["control_is_attestation_source"])
        self.assertIs(spec["valued_device_contact"], False)

    def test_no_second_lifecycle_engine(self) -> None:
        source = Path(_product.__file__).read_text(encoding="utf-8")
        self.assertNotIn("LIFECYCLE_SEQUENCE = (", source)
        self.assertNotIn("def decide_device_boot_observation", source)
        self.assertNotIn("def assert_lifecycle_transitions", source)
        self.assertIn("assert_lifecycle_transitions", source)
        self.assertIn("decide_device_boot_observation", source)
        harness = _product_harness(tempfile.mkdtemp())
        try:
            self.assertIsInstance(harness.inner, LifecycleHarness)
        finally:
            shutil.rmtree(harness.config.output_dir.parent, ignore_errors=True)

    def test_product_report_shape_passes_transition_contract(self) -> None:
        steps = [
            {"step": name, "default_slot": ("B" if name in (
                "boot-B-commit", "stage-broken-candidate",
                "boot-broken-candidate", "recovery-boot-B",
            ) else "A")}
            for name in LIFECYCLE_SEQUENCE
        ]
        assert_lifecycle_transitions({
            "steps": steps,
            "shipped_update_legs": list(SHIPPED_UPDATE_LEGS),
            "launcher_acceptance_legs": list(LAUNCHER_ACCEPTANCE_LEGS),
        })


class ControlSeamTextTests(unittest.TestCase):
    def test_unit_is_test_only_oneshot_after_real_services(self) -> None:
        text = control_unit_text()
        self.assertIn("TEST-ONLY", text)
        self.assertIn("Type=oneshot", text)
        self.assertIn(f"ExecStart={CONTROL_RUNNER_PATH}", text)
        for service in (
            "greia-install-transaction.service",
            "greia-system-update.service",
            "greia-boot-health.service",
        ):
            self.assertIn(service, text)

    def test_runner_drives_real_sockets_and_refuses_unknown_phase(self) -> None:
        text = control_runner_text()
        for socket in (
            INSTALL_SOCKET_PATH,
            UPDATE_SOCKET_PATH,
            BOOT_HEALTH_SOCKET_PATH,
        ):
            self.assertIn(socket, text)
        for phase in CONTROL_PHASES:
            self.assertIn(phase, text)
        self.assertIn("refused unknown phase", text)
        self.assertIn("poweroff", text)
        self.assertIn(CONTROL_DISK_LABEL, text)

    def test_runner_text_is_valid_bash(self) -> None:
        import subprocess as _subprocess

        completed = _subprocess.run(
            ["bash", "-n", "/dev/stdin"],
            input=control_runner_text().encode(),
            capture_output=True,
            timeout=60,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr.decode()[:500])


class PhaseChannelTests(unittest.TestCase):
    def test_every_bounded_phase_round_trips(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            for phase in CONTROL_PHASES:
                path = write_control_phase(
                    Path(tmp) / "ctl", phase=phase, inputs={"k": "v"}
                )
                back = read_control_phase(Path(tmp) / "ctl")
                self.assertEqual(back["phase"], phase)
                self.assertTrue(path.is_file())

    def test_unknown_phase_refused_at_write(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(LifecycleHarnessError):
                write_control_phase(Path(tmp), phase="reboot-host")

    def test_missing_phase_file_fails_closed_never_silent_noop(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(LifecycleHarnessError) as caught:
                read_control_phase(Path(tmp) / "absent")
            self.assertIn("fails closed", str(caught.exception))

    def test_corrupt_or_unbounded_phase_file_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "phase.json").write_text("not json{\n", encoding="utf-8")
            with self.assertRaises(LifecycleHarnessError):
                read_control_phase(root)
            (root / "phase.json").write_text('{"phase": "reboot-host"}\n',
                                             encoding="utf-8")
            with self.assertRaises(LifecycleHarnessError):
                read_control_phase(root)


class ControlInjectionTests(unittest.TestCase):
    def test_inject_and_validate_green(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = _fake_guest_root(Path(tmp) / "slot-b")
            proof = inject_control_into_root(root)
            validate_control_present(root)
            runner = Path(proof["runner"])
            self.assertTrue(runner.is_file())
            self.assertTrue(runner.stat().st_mode & 0o111)
            wants = root / "etc/systemd/system/multi-user.target.wants" / CONTROL_UNIT_NAME
            self.assertTrue(wants.is_symlink())

    def test_mask_option_masks_live_service_in_clone_only(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = _fake_guest_root(Path(tmp) / "live")
            (root / "etc/systemd/system/greia-installer.service").write_text(
                "[Service]\n", encoding="utf-8"
            )
            proof = inject_control_into_root(
                root, mask_service="greia-installer.service"
            )
            self.assertEqual(proof["masked"], "greia-installer.service")
            masked = root / "etc/systemd/system/greia-installer.service"
            self.assertTrue(masked.is_symlink())

    def test_inject_into_non_root_refused(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(LifecycleHarnessError):
                inject_control_into_root(Path(tmp) / "no-such-root")

    def test_removed_seam_fails_closed_positive_control(self) -> None:
        # GREEN -> break (remove unit) -> RED -> restore -> GREEN.
        with tempfile.TemporaryDirectory() as tmp:
            root = _fake_guest_root(Path(tmp) / "slot-a")
            inject_control_into_root(root)
            validate_control_present(root)
            (root / "etc/systemd/system" / CONTROL_UNIT_NAME).unlink()
            with self.assertRaises(LifecycleHarnessError) as caught:
                validate_control_present(root)
            self.assertIn("fails closed", str(caught.exception))
            inject_control_into_root(root)
            validate_control_present(root)

    def test_misrouted_runner_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = _fake_guest_root(Path(tmp) / "slot-a")
            inject_control_into_root(root)
            (root / CONTROL_RUNNER_PATH.lstrip("/")).unlink()
            with self.assertRaises(LifecycleHarnessError):
                validate_control_present(root)


class CloneSeparationTests(unittest.TestCase):
    def test_block_device_paths_refused(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(LifecycleHarnessError):
                clone_product_image(
                    Path("/dev/sda"), Path(tmp) / "clone.img"
                )

    def test_missing_official_image_blocked_never_synthesized(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(LifecycleHarnessError) as caught:
                clone_product_image(
                    Path(tmp) / "absent.img", Path(tmp) / "clone.img"
                )
            self.assertIn("BLOCKED", str(caught.exception))
            self.assertFalse((Path(tmp) / "clone.img").exists())

    def test_source_and_clone_must_differ(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            src = Path(tmp) / "src.img"
            src.write_bytes(b"x" * 4096)
            with self.assertRaises(LifecycleHarnessError):
                clone_product_image(src, src)

    def test_clone_records_sha_and_never_touches_source(self) -> None:
        import hashlib as _hashlib

        with tempfile.TemporaryDirectory() as tmp:
            src = Path(tmp) / "official.img"
            body = b"official" * 1024
            src.write_bytes(body)
            before = _hashlib.sha256(body).hexdigest()
            dst = Path(tmp) / "out" / "clone.img"
            with _mock.patch(
                "tools.x8_qemu.product.subprocess.run"
            ) as run_mock:
                def _fake_run(argv: object, **kwargs: object):  # type: ignore[no-untyped-def]
                    shutil.copy2(src, dst)
                    return _mock.Mock(returncode=0)

                run_mock.side_effect = _fake_run
                proof = clone_product_image(src, dst)
            self.assertEqual(proof["source_sha256"], before)
            self.assertEqual(src.read_bytes(), body)
            self.assertEqual(dst.stat().st_size, src.stat().st_size)

    def test_existing_clone_never_replaced(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            src = Path(tmp) / "src.img"
            src.write_bytes(b"y" * 512)
            dst = Path(tmp) / "clone.img"
            dst.write_bytes(b"old")
            with self.assertRaises(LifecycleHarnessError):
                clone_product_image(src, dst)


class AttestationBoundaryTests(unittest.TestCase):
    def test_control_channel_can_never_be_an_attestation_source(self) -> None:
        pre = {"default_slot": "A", "one_shot_slot": None}
        post = {"default_slot": "A", "one_shot_slot": None}
        with self.assertRaises(LifecycleHarnessError) as caught:
            attest_product_boot(
                leg="boot-A-accepted", pre=pre, post=post,
                control_report={"phase": "wait-health-poweroff", "ok": True},
            )
        self.assertIn("only from image bytes", str(caught.exception))

    def test_observation_delegates_to_frozen_predicate(self) -> None:
        observed = attest_product_boot(
            leg="boot-A-accepted",
            pre={"default_slot": "A", "one_shot_slot": None},
            post={"default_slot": "A", "one_shot_slot": None},
        )
        self.assertEqual(observed, "A")
        observed = attest_product_boot(
            leg="boot-B-commit",
            pre={"default_slot": "A", "one_shot_slot": "B"},
            post={"default_slot": "A", "one_shot_slot": None},
        )
        self.assertEqual(observed, "B")

    def test_unconsumed_one_shot_stays_red(self) -> None:
        with self.assertRaises(LifecycleHarnessError):
            attest_product_boot(
                leg="boot-B-commit",
                pre={"default_slot": "A", "one_shot_slot": "B"},
                post={"default_slot": "A", "one_shot_slot": "B"},
            )

    def test_unknown_leg_refused(self) -> None:
        with self.assertRaises(LifecycleHarnessError):
            attest_product_boot(leg="no-such-leg", pre={}, post={})

    def test_attestation_source_list_names_no_control_source(self) -> None:
        self.assertIn(
            "control channel: NOT A SOURCE (orchestration only)",
            ATTESTATION_SOURCES,
        )


class StructuralPinTests(unittest.TestCase):
    def test_control_absent_from_production_trees(self) -> None:
        assert_control_absent_from_production(PROJECT_ROOT)

    def test_positive_control_leak_is_red_then_green(self) -> None:
        # Break: plant the control name in a fake production tree -> RED.
        # Restore: remove it -> GREEN.
        with tempfile.TemporaryDirectory() as tmp:
            fake_src = Path(tmp) / "src"
            fake_src.mkdir(parents=True)
            planted = fake_src / "leak.py"
            planted.write_text(f"# {CONTROL_UNIT_NAME}\n", encoding="utf-8")
            with self.assertRaises(LifecycleHarnessError) as caught:
                assert_control_absent_from_production(Path(tmp))
            self.assertIn("leaked", str(caught.exception))
            planted.unlink()
            assert_control_absent_from_production(Path(tmp))

    def test_production_source_never_imports_control_module(self) -> None:
        hits = [
            str(path) for path in (PROJECT_ROOT / "src").rglob("*.py")
            if "tools.x8_qemu.product" in path.read_text(encoding="utf-8")
        ]
        self.assertEqual(hits, [])

    def test_official_media_and_profiles_unchanged(self) -> None:
        for tree in ("build/overlay", "build/installer-overlay", "build/profiles"):
            base = PROJECT_ROOT / tree
            if not base.is_dir():
                continue
            hits = []
            for path in sorted(base.rglob("*")):
                if not path.is_file() or path.is_symlink():
                    continue
                try:
                    text = path.read_text(encoding="utf-8")
                except (OSError, ValueError):
                    continue
                if CONTROL_UNIT_NAME in text:
                    hits.append(str(path))
            self.assertEqual(hits, [], f"control seam leaked into {tree}")


class ProductGateTests(unittest.TestCase):
    def test_plan_is_non_mutating(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            harness = _product_harness(tmp)
            before = sorted(p for p in Path(tmp).rglob("*"))
            plan = harness.plan()
            after = sorted(p for p in Path(tmp).rglob("*"))
            self.assertEqual(before, after)
            self.assertFalse(plan["source_image_mutated"])
            self.assertEqual(
                plan["lifecycle_sequence"], list(LIFECYCLE_SEQUENCE)
            )

    def test_run_product_blocked_without_facility_or_image(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            harness = _product_harness(tmp)
            with self.assertRaises(LifecycleHarnessError) as caught:
                harness.run_product()
            self.assertIn("BLOCKED", str(caught.exception))

    def test_run_product_fails_closed_when_control_disabled(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            harness = _product_harness(tmp, control_enabled=False)
            with self.assertRaises(LifecycleHarnessError) as caught:
                harness.run_product()
            self.assertIn("fails closed", str(caught.exception))

    def test_require_product_host_names_missing_facility(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(LifecycleHarnessError) as caught:
                require_product_host(
                    official_image=Path(tmp) / "absent.img"
                )
            self.assertIn("BLOCKED", str(caught.exception))

    def test_output_inside_source_tree_refused(self) -> None:
        with self.assertRaises(LifecycleHarnessError):
            ProductHarness(LifecycleConfig(output_dir=PROJECT_ROOT / "build" / "p5"))

    def test_timers_preserved_seven_second_intro_and_3min_recovery(self) -> None:
        from greia_launcher.boot_intro import (
            ANIMATION_SECONDS,
            FINAL_FRAME_HOLD_SECONDS,
        )
        from greia_platform.boot_transaction import CANDIDATE_HEALTH_DEADLINE_SEC

        self.assertAlmostEqual(
            ANIMATION_SECONDS + FINAL_FRAME_HOLD_SECONDS, 7.0
        )
        self.assertEqual(CANDIDATE_HEALTH_DEADLINE_SEC, 180)
        spec = product_spec()
        self.assertEqual(spec["intro_seconds"], 7.0)
        self.assertEqual(spec["recovery_deadline_seconds"], 180)

    def test_expected_slots_cover_every_boot_leg(self) -> None:
        from tools.x8_qemu.lifecycle import BOOT_OUTCOME_LEGS

        for leg in BOOT_OUTCOME_LEGS:
            self.assertIn(leg, BOOT_OUTCOME_EXPECTED_SLOT)


if __name__ == "__main__":
    unittest.main()
