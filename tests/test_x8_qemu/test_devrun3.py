"""T7-DEVRUN3 device-lifecycle contract: gate wiring, frozen legs, sector guard.

Pins the ``run_device`` replacement through the production seams only:
payload + sector-gap gate on the real boot path, one real SeaBIOS boot
per frozen boot-outcome leg with on-image observation, clean-exit gate,
post-run loop/cross-check binding, and honest device classification.
No QEMU, loop, mount, or valued-device contact here: device execution
itself stays fail-closed behind ``require_device_host`` (live green
belongs to T7-DEVRUN-LIVE2); these tests prove the wiring, the RED
controls, and the frozen leg definition at source scope.
"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from tools.x8_qemu.lifecycle import (
    BOOT_OUTCOME_EXPECTED_SLOT,
    BOOT_OUTCOME_LEGS,
    DEVICE_BOOT_ARMED_TARGET,
    LAUNCHER_ACCEPTANCE_LEGS,
    LIFECYCLE_SEQUENCE,
    NON_BOOT_TRANSITIONS,
    SHIPPED_UPDATE_LEGS,
    LifecycleConfig,
    LifecycleContractError,
    LifecycleHarness,
    LifecycleHarnessError,
    assert_lifecycle_transitions,
    assemble_disposable_image,
    check_boot_exit,
    decide_device_boot_observation,
    device_gate_for_image,
    device_qemu_argv,
    lifecycle_spec,
    require_device_host,
)
from tools.x8_qemu.payload import (
    PARTITION_1_FIRST_SECTOR,
    PAYLOAD_MAGIC,
    PayloadError,
    SECTOR_GAP_COORDINATION_NOTE,
    SECTOR_GAP_FIRST_SECTOR,
    SECTOR_GAP_LAST_SECTOR,
    assert_payload_present,
    embed_payload_descriptor,
    read_payload_descriptor,
    verify_sector_gap_reserved,
    verify_staged_payload,
)


def _device_harness(tmp: str) -> LifecycleHarness:
    return LifecycleHarness(LifecycleConfig(output_dir=Path(tmp) / "out"))


class FrozenLegDefinitionTests(unittest.TestCase):
    def test_eight_transitions_partition_into_3_non_boot_plus_5_boot(self) -> None:
        self.assertEqual(
            list(NON_BOOT_TRANSITIONS),
            ["fresh-install-A", "stage-B-one-shot", "stage-broken-candidate"],
        )
        self.assertEqual(
            list(BOOT_OUTCOME_LEGS),
            [
                "boot-A-accepted",
                "boot-B-commit",
                "boot-broken-candidate",
                "recovery-boot-B",
                "reverse-update-B-to-A",
            ],
        )
        self.assertEqual(
            set(NON_BOOT_TRANSITIONS) | set(BOOT_OUTCOME_LEGS),
            set(LIFECYCLE_SEQUENCE),
        )
        self.assertEqual(len(LIFECYCLE_SEQUENCE), 8)
        self.assertEqual(len(NON_BOOT_TRANSITIONS), 3)
        self.assertEqual(len(BOOT_OUTCOME_LEGS), 5)
        self.assertEqual(
            dict(BOOT_OUTCOME_EXPECTED_SLOT),
            {
                "boot-A-accepted": "A",
                "boot-B-commit": "B",
                "boot-broken-candidate": "A",
                "recovery-boot-B": "B",
                "reverse-update-B-to-A": "A",
            },
        )
        self.assertEqual(
            dict(DEVICE_BOOT_ARMED_TARGET),
            {
                "boot-A-accepted": None,
                "boot-B-commit": "B",
                "boot-broken-candidate": "A",
                "recovery-boot-B": None,
                "reverse-update-B-to-A": "A",
            },
        )
        spec = lifecycle_spec()
        self.assertEqual(
            list(spec["non_boot_transitions"]), list(NON_BOOT_TRANSITIONS)
        )
        self.assertEqual(list(spec["boot_outcome_legs"]), list(BOOT_OUTCOME_LEGS))

    def test_leg_partition_drift_is_itself_red(self) -> None:
        import tools.x8_qemu.lifecycle as module

        intact_non_boot = module.NON_BOOT_TRANSITIONS
        try:
            module.NON_BOOT_TRANSITIONS = ("fresh-install-A",)  # type: ignore[assignment]
            with self.assertRaises(LifecycleContractError):
                assert_lifecycle_transitions(
                    {"steps": [], "shipped_update_legs": [],
                     "launcher_acceptance_legs": []}
                )
        finally:
            module.NON_BOOT_TRANSITIONS = intact_non_boot
        # Intact definition still passes its own contract on a real report.
        with tempfile.TemporaryDirectory() as tmp:
            report = _device_harness(tmp).run_source_scope()
            assert_lifecycle_transitions(report)


class DeviceGateTests(unittest.TestCase):
    """Payload-less/tampered images RED the real boot-path gate."""

    def test_device_gate_break_restore_round_trip(self) -> None:
        from tools.x8_qemu.bootchain import STUB_CORE_SECTORS, stub_core_sha256
        from tools.x8_qemu.payload import DESCRIPTOR_OFFSET

        with tempfile.TemporaryDirectory() as tmp:
            manifest = assemble_disposable_image(Path(tmp) / "out")
            image = Path(manifest["image"])
            # GREEN: payload present, gap reserved, chain installed.
            gate = device_gate_for_image(image)
            self.assertEqual(gate["descriptor"]["magic"], "GREIAPY1")
            self.assertEqual(gate["descriptor"]["descriptor_sector"], 2047)
            # BREAK: wipe the descriptor sector (512 bounded bytes).
            with open(image, "r+b") as handle:
                handle.seek(DESCRIPTOR_OFFSET)
                handle.write(b"\x00" * 512)
            # RED: the device gate fails closed (payload + gap agree).
            with self.assertRaises(PayloadError):
                device_gate_for_image(image)
            with self.assertRaises(PayloadError):
                assert_payload_present(image)
            # RESTORE the exact binding and re-prove GREEN.
            reproven = verify_staged_payload(Path(tmp) / "out" / "guest-payload")
            embed_payload_descriptor(
                image,
                reproven,
                core_sha256=stub_core_sha256(),
                core_sectors=STUB_CORE_SECTORS,
            )
            device_gate_for_image(image)
            assert_payload_present(image)

    def test_device_gate_refuses_tampered_hashes(self) -> None:
        from tools.x8_qemu.payload import DESCRIPTOR_OFFSET

        with tempfile.TemporaryDirectory() as tmp:
            manifest = assemble_disposable_image(Path(tmp) / "out")
            image = Path(manifest["image"])
            # Non-hex hash bytes: malformed descriptor REDs the gate.
            with open(image, "r+b") as handle:
                handle.seek(DESCRIPTOR_OFFSET + 9)
                handle.write(b"*" * 64)
            with self.assertRaises(PayloadError):
                device_gate_for_image(image)

    def test_gate_install_binding_refuses_swapped_descriptor(self) -> None:
        from tools.x8_qemu.lifecycle import bind_gate_to_install

        gate = {
            "descriptor": {
                "grub_cfg_sha256": "ab" * 32,
                "grubenv_sha256": "cd" * 32,
            }
        }
        matching = {"grub_cfg_sha256": "ab" * 32, "grubenv_sha256": "cd" * 32}
        bind_gate_to_install(gate, matching)
        swapped = {"grub_cfg_sha256": "ab" * 32, "grubenv_sha256": "ef" * 32}
        with self.assertRaises(LifecycleHarnessError):
            bind_gate_to_install(gate, swapped)
        with self.assertRaises(LifecycleHarnessError):
            bind_gate_to_install({}, matching)

    def test_run_device_fails_closed_off_capable_host(self) -> None:
        import sys as _sys

        if _sys.platform == "linux" and Path("/dev").exists():
            self.skipTest("device gate is evaluated on Linux device runs")
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(LifecycleHarnessError):
                _device_harness(tmp).run_device()
            with self.assertRaises(LifecycleHarnessError):
                require_device_host()


class CleanExitGateTests(unittest.TestCase):
    def test_unclean_qemu_exit_is_red(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            log = Path(tmp) / "qemu.log"
            log.write_text("fake log\n", encoding="utf-8")
            check_boot_exit(0, leg="boot-B-commit", qemu_log=log)
            with self.assertRaises(LifecycleHarnessError):
                check_boot_exit(1, leg="boot-B-commit", qemu_log=log)
            with self.assertRaises(LifecycleHarnessError):
                check_boot_exit(137, leg="boot-A-accepted", qemu_log=log)

    def test_device_argv_is_a_real_seabios_boot(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            image = Path(tmp) / "disk.img"
            image.write_bytes(b"\x00" * 1024)
            argv, serial_log, host_log = device_qemu_argv(
                image, output_dir=Path(tmp), leg="boot-B-commit",
                memory_mib=1024, cpus=1, seabios_path=None,
            )
            self.assertEqual(argv[0], "qemu-system-x86_64")
            self.assertIn("-no-reboot", argv)
            self.assertIn("strict=on", " ".join(argv))
            self.assertNotIn("snapshot", " ".join(argv))
            self.assertIn(f"file={image}", " ".join(argv))
            self.assertTrue(str(serial_log).endswith("device-boot-B-commit-serial.log"))
            self.assertTrue(str(host_log).endswith("device-boot-B-commit-qemu.log"))


class DeviceObservationDecisionTests(unittest.TestCase):
    """N1/N2 live analogues decided from on-image pre/post bytes."""

    def test_armed_leg_consumed_attests(self) -> None:
        observed = decide_device_boot_observation(
            leg="boot-B-commit",
            pre={"default_slot": "A", "one_shot_slot": "B"},
            post={"default_slot": "A", "one_shot_slot": None},
        )
        self.assertEqual(observed, "B")

    def test_n1_same_disk_reboot_without_transition_is_red(self) -> None:
        # No staged one-shot for the leg's target: nothing to attest.
        with self.assertRaises(LifecycleHarnessError):
            decide_device_boot_observation(
                leg="boot-B-commit",
                pre={"default_slot": "A", "one_shot_slot": None},
                post={"default_slot": "A", "one_shot_slot": None},
            )
        # Wrong-target arm is equally RED.
        with self.assertRaises(LifecycleHarnessError):
            decide_device_boot_observation(
                leg="boot-B-commit",
                pre={"default_slot": "A", "one_shot_slot": "A"},
                post={"default_slot": "A", "one_shot_slot": None},
            )

    def test_n2_armed_but_unconsumed_is_red(self) -> None:
        with self.assertRaises(LifecycleHarnessError):
            decide_device_boot_observation(
                leg="boot-B-commit",
                pre={"default_slot": "A", "one_shot_slot": "B"},
                post={"default_slot": "A", "one_shot_slot": "B"},
            )
        with self.assertRaises(LifecycleHarnessError):
            decide_device_boot_observation(
                leg="reverse-update-B-to-A",
                pre={"default_slot": "B", "one_shot_slot": "A"},
                post={"default_slot": "B", "one_shot_slot": "A"},
            )

    def test_plain_leg_attests_post_default_from_image(self) -> None:
        observed = decide_device_boot_observation(
            leg="boot-A-accepted",
            pre={"default_slot": "A", "one_shot_slot": None},
            post={"default_slot": "A", "one_shot_slot": None},
        )
        self.assertEqual(observed, "A")
        observed = decide_device_boot_observation(
            leg="recovery-boot-B",
            pre={"default_slot": "B", "one_shot_slot": None},
            post={"default_slot": "B", "one_shot_slot": None},
        )
        self.assertEqual(observed, "B")
        # Unexpected one-shot or a moved default is RED either side
        # (boot-A-accepted expects the A default throughout).
        for pre, post in (
            ({"default_slot": "A", "one_shot_slot": "B"},
             {"default_slot": "A", "one_shot_slot": None}),
            ({"default_slot": "A", "one_shot_slot": None},
             {"default_slot": "A", "one_shot_slot": "B"}),
            ({"default_slot": "B", "one_shot_slot": None},
             {"default_slot": "B", "one_shot_slot": None}),
            ({"default_slot": "A", "one_shot_slot": None},
             {"default_slot": "B", "one_shot_slot": None}),
        ):
            with self.assertRaises(LifecycleHarnessError):
                decide_device_boot_observation(
                    leg="boot-A-accepted", pre=pre, post=post
                )

    def test_unknown_leg_is_red(self) -> None:
        with self.assertRaises(LifecycleContractError):
            decide_device_boot_observation(
                leg="cold-boot-A",
                pre={"default_slot": "A", "one_shot_slot": None},
                post={"default_slot": "A", "one_shot_slot": None},
            )


class SectorGapGuardTests(unittest.TestCase):
    def test_gap_reserved_on_assembled_image(self) -> None:
        from tools.x8_qemu.payload import DESCRIPTOR_SECTOR

        with tempfile.TemporaryDirectory() as tmp:
            manifest = assemble_disposable_image(Path(tmp) / "out")
            image = Path(manifest["image"])
            guard = verify_sector_gap_reserved(image)
            self.assertEqual(guard["reserved_first_sector"], 1)
            self.assertEqual(guard["reserved_last_sector"], 2047)
            self.assertEqual(guard["partition_1_first_sector"], 2048)
            self.assertEqual(guard["descriptor_sector"], 2047)
            self.assertEqual(guard["core_sectors"], 15)
            self.assertEqual(guard["sector_state"], "descriptor-bound-core")
            self.assertEqual(SECTOR_GAP_FIRST_SECTOR, 1)
            self.assertEqual(SECTOR_GAP_LAST_SECTOR, 2047)
            self.assertEqual(PARTITION_1_FIRST_SECTOR, 2048)
            self.assertEqual(DESCRIPTOR_SECTOR, 2047)

    def test_gap_refuses_foreign_descriptor_break_restore_green(self) -> None:
        from tools.x8_qemu.bootchain import STUB_CORE_SECTORS, stub_core_sha256
        from tools.x8_qemu.payload import DESCRIPTOR_OFFSET

        with tempfile.TemporaryDirectory() as tmp:
            manifest = assemble_disposable_image(Path(tmp) / "out")
            image = Path(manifest["image"])
            with open(image, "rb") as _sector_handle:
                _sector_handle.seek(DESCRIPTOR_OFFSET)
                intact = _sector_handle.read(512)
            # BREAK: foreign (non-zero, non-descriptor) bytes at sector 2047.
            with open(image, "r+b") as handle:
                handle.seek(DESCRIPTOR_OFFSET)
                handle.write(b"COREIMGB" + b"\x01" * 504)
            with self.assertRaises(PayloadError):
                verify_sector_gap_reserved(image)
            with self.assertRaises(PayloadError):
                embed_payload_descriptor(
                    image,
                    verify_staged_payload(Path(tmp) / "out" / "guest-payload"),
                    core_sha256=stub_core_sha256(),
                    core_sectors=STUB_CORE_SECTORS,
                )
            # RESTORE the exact descriptor bytes and re-prove GREEN.
            with open(image, "r+b") as handle:
                handle.seek(DESCRIPTOR_OFFSET)
                handle.write(intact)
            verify_sector_gap_reserved(image)
            read_payload_descriptor(image)

    def test_gap_refuses_swapped_core_bytes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            manifest = assemble_disposable_image(Path(tmp) / "out")
            image = Path(manifest["image"])
            # BREAK: one flipped byte inside the bound core region.
            with open(image, "r+b") as handle:
                handle.seek(2 * 512)
                handle.write(b"\x07")
            with self.assertRaises(PayloadError):
                verify_sector_gap_reserved(image)
            with self.assertRaises(PayloadError):
                device_gate_for_image(image)

    def test_gap_refuses_nonzero_gap_tail(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            manifest = assemble_disposable_image(Path(tmp) / "out")
            image = Path(manifest["image"])
            # BREAK: a byte hidden deep in the reserved gap (sector 1000).
            with open(image, "r+b") as handle:
                handle.seek(1000 * 512)
                handle.write(b"\x07")
            with self.assertRaises(PayloadError):
                verify_sector_gap_reserved(image)

    def test_coordination_note_names_the_constraint(self) -> None:
        from tools.x8_qemu.lifecycle import PROJECT_ROOT

        self.assertIn("1-2047", SECTOR_GAP_COORDINATION_NOTE)
        self.assertIn("core.img", SECTOR_GAP_COORDINATION_NOTE)
        self.assertIn("LIFECYCLE.md", SECTOR_GAP_COORDINATION_NOTE)
        self.assertIn("GREIAPY1", PAYLOAD_MAGIC.decode("ascii"))
        # The constraint is recorded where the future GRUB installer
        # must read it (LIFECYCLE.md section 8).
        procedure = (PROJECT_ROOT / "tools" / "x8_qemu" / "LIFECYCLE.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("## 8.", procedure)
        self.assertIn("1–2047", procedure)
        self.assertIn("core.img", procedure)
        self.assertIn("GREIAPY1", procedure)


class DeviceWiringBoundaryTests(unittest.TestCase):
    def test_run_device_drives_production_seams_without_fakes(self) -> None:
        import inspect as _inspect

        from tools.x8_qemu import lifecycle as module

        body = _inspect.getsource(module.LifecycleHarness.run_device)
        for required in (
            "require_device_host",
            "assemble_disposable_image",
            "device_gate_for_image",
            "install_payload_to_device",
            "bind_gate_to_install",
            "_boot_image_once",
            "_read_on_image_grubenv",
            "decide_device_boot_observation",
            "_stamp_and_gate_on_image",
            "read_attestation_signal",
            "shipped_update_authority",
            "_launcher_boot",
            "observe_loop_attached_device",
            "run_file_cross_check",
            "DEVICE_T7_DEVRUN3",
        ):
            self.assertIn(required, body)
        # The launcher traversal runs through the real production seam:
        # run_device folds each boot through _launcher_boot, which drives
        # the production acceptance graph (no stubbed launcher).
        launcher_path = _inspect.getsource(module.run_launcher_acceptance)
        for required in ("apply_prepared_state", "maybe_accept_production_boot"):
            self.assertIn(required, launcher_path)
        text = Path(module.__file__).read_text(encoding="utf-8")
        self.assertNotIn("simulate_reboot(", text)
        self.assertNotIn("FakeGrubBackend", text)
        # run_device takes no stubbed-spawn hook: non-proxying is structural.
        params = list(_inspect.signature(module.LifecycleHarness.run_device).parameters)
        self.assertEqual(params, ["self"])

    def test_source_scope_classification_unchanged(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            report = _device_harness(tmp).run_source_scope()
            self.assertEqual(report["classification"], "SOURCE_SCOPE_T6_LIFECYCLE")
            self.assertFalse(report["device_scope"]["executed"])
            assert_lifecycle_transitions(report)


class DeviceGateCollectSensitivityTests(unittest.TestCase):
    """DIAG-C2-SENSITIVITY: image-gate REDs stay RED under collect mode.

    Companion to the full ``DIAG_C2_SENSITIVITY_CONTROL_INVENTORY`` in
    ``test_lifecycle.py`` from the device-gate owner's surface: each
    break calls the real ``device_gate_for_image`` (payload plus
    sector-gap plus boot chain), each RED records through the real
    ``DeviceCollectRecorder`` / ``run_collect_sequence`` /
    ``build_device_collect_diagnostics`` path with the
    ``device_gate_for_image`` gate and the verbatim fail-fast error, and
    each byte-exact restore re-proves GREEN. Preregistered predicates:
    RED-under-collect with gate named plus GREEN after restore; no
    frozen predicate weakened.
    """

    def test_collect_sensitivity_payload_less_red_and_restore_green(
        self,
    ) -> None:
        from tools.x8_qemu.lifecycle import (
            COLLECT_FROZEN_PREDICATES,
            DeviceCollectRecorder,
            build_device_collect_diagnostics,
            run_collect_sequence,
        )
        from tools.x8_qemu.payload import DESCRIPTOR_OFFSET, PayloadError

        with tempfile.TemporaryDirectory() as tmp:
            manifest = assemble_disposable_image(Path(tmp) / "out")
            image = Path(manifest["image"])
            device_gate_for_image(image)
            with open(image, "rb") as handle:
                handle.seek(DESCRIPTOR_OFFSET)
                intact = handle.read(512)

            def _break() -> object:
                with open(image, "r+b") as handle:
                    handle.seek(DESCRIPTOR_OFFSET)
                    handle.write(b"\x00" * 512)
                return device_gate_for_image(image)

            with self.assertRaises(PayloadError) as caught:
                _break()
            fail_fast_error = str(caught.exception)

            recorder = DeviceCollectRecorder()
            verdict = run_collect_sequence(
                [{
                    "leg": "collect-setup-image",
                    "gate": "device_gate_for_image",
                    "frozen_predicate": COLLECT_FROZEN_PREDICATES[
                        "device_gate_for_image"],
                    "run": _break,
                    "context": lambda: {
                        "image_sha256_pre": manifest["image_sha256"],
                        "disk_snapshot": {"image": str(image)},
                    },
                }],
                recorder,
            )
            self.assertFalse(verdict["ok"])
            self.assertEqual(verdict["red_count"], 1)
            red = recorder.reds[0]
            self.assertEqual(red["gate"], "device_gate_for_image")
            self.assertEqual(red["error_type"], "PayloadError")
            self.assertEqual(red["error"], fail_fast_error)
            self.assertFalse(red["abort"])
            self.assertEqual(
                red["image_sha256_pre"], manifest["image_sha256"])
            artifact = build_device_collect_diagnostics(
                recorder, run_meta={"diag-c2": "payload-less"})
            self.assertFalse(artifact["verdict"]["ok"])
            self.assertEqual(
                artifact["reds"][0]["gate"], "device_gate_for_image")

            # RESTORE the exact descriptor bytes and re-prove GREEN.
            with open(image, "r+b") as handle:
                handle.seek(DESCRIPTOR_OFFSET)
                handle.write(intact)
            device_gate_for_image(image)
            green_recorder = DeviceCollectRecorder()
            green_verdict = run_collect_sequence(
                [{
                    "leg": "collect-setup-image",
                    "gate": "device_gate_for_image",
                    "frozen_predicate": COLLECT_FROZEN_PREDICATES[
                        "device_gate_for_image"],
                    "run": lambda: device_gate_for_image(image),
                }],
                green_recorder,
            )
            self.assertTrue(green_verdict["ok"])

    def test_collect_sensitivity_gap_foreign_and_core_swap_red(self) -> None:
        from tools.x8_qemu.lifecycle import (
            COLLECT_FROZEN_PREDICATES,
            DeviceCollectRecorder,
            build_device_collect_diagnostics,
            run_collect_sequence,
        )
        from tools.x8_qemu.payload import (
            DESCRIPTOR_OFFSET,
            PayloadError,
            verify_sector_gap_reserved,
        )

        with tempfile.TemporaryDirectory() as tmp:
            manifest = assemble_disposable_image(Path(tmp) / "out")
            image = Path(manifest["image"])
            device_gate_for_image(image)
            verify_sector_gap_reserved(image)
            with open(image, "rb") as handle:
                handle.seek(DESCRIPTOR_OFFSET)
                intact_descriptor = handle.read(512)
            with open(image, "rb") as handle:
                handle.seek(2 * 512)
                intact_core_byte = handle.read(1)

            def _break_foreign() -> object:
                with open(image, "r+b") as handle:
                    handle.seek(DESCRIPTOR_OFFSET)
                    handle.write(b"COREIMGB" + b"\x01" * 504)
                return device_gate_for_image(image)

            def _restore_descriptor() -> None:
                with open(image, "r+b") as handle:
                    handle.seek(DESCRIPTOR_OFFSET)
                    handle.write(intact_descriptor)
                device_gate_for_image(image)

            def _break_core_swap() -> object:
                with open(image, "r+b") as handle:
                    handle.seek(2 * 512)
                    handle.write(
                        b"\x07" if intact_core_byte != b"\x07" else b"\x08")
                return device_gate_for_image(image)

            def _restore_core() -> None:
                with open(image, "r+b") as handle:
                    handle.seek(2 * 512)
                    handle.write(intact_core_byte)
                device_gate_for_image(image)

            for leg, break_fn, restore_fn in (
                ("image-gap-foreign", _break_foreign, _restore_descriptor),
                ("image-core-swap", _break_core_swap, _restore_core),
            ):
                with self.assertRaises(PayloadError) as caught:
                    break_fn()
                fail_fast_error = str(caught.exception)

                recorder = DeviceCollectRecorder()
                verdict = run_collect_sequence(
                    [{
                        "leg": leg,
                        "gate": "device_gate_for_image",
                        "frozen_predicate": COLLECT_FROZEN_PREDICATES[
                            "device_gate_for_image"],
                        "run": break_fn,
                        "context": lambda: {
                            "image_sha256_pre": manifest["image_sha256"],
                        },
                    }],
                    recorder,
                )
                self.assertFalse(verdict["ok"])
                red = recorder.reds[0]
                self.assertEqual(red["gate"], "device_gate_for_image")
                self.assertEqual(red["error_type"], "PayloadError")
                self.assertEqual(red["error"], fail_fast_error)
                self.assertFalse(red["abort"])
                artifact = build_device_collect_diagnostics(
                    recorder, run_meta={"diag-c2": leg})
                self.assertFalse(artifact["verdict"]["ok"])

                restore_fn()
                green_recorder = DeviceCollectRecorder()
                green_verdict = run_collect_sequence(
                    [{
                        "leg": leg,
                        "gate": "device_gate_for_image",
                        "frozen_predicate": COLLECT_FROZEN_PREDICATES[
                            "device_gate_for_image"],
                        "run": lambda: device_gate_for_image(image),
                    }],
                    green_recorder,
                )
                self.assertTrue(green_verdict["ok"])


if __name__ == "__main__":
    unittest.main()
