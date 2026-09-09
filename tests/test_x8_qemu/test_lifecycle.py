"""T6-HARNESS3 lifecycle contract: 8-step lifecycle + shipped update path.

Pins the harness's own assertions (``tools/x8_qemu/lifecycle.py``),
including the shipped update path and the on-device observation, plus
one positive control per required RED condition. No QEMU, loop, mount,
or valued-device contact here: device legs run through the production
seams source-scope (sparse block-driver-seam stores, real GrubEnvBackend,
real journal, real launcher seam); device-contact requirements fail
closed with explicit deferred markers instead of false green.
"""

from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

from tools.x8_qemu.lifecycle import (
    BOOT_BACKEND_ID,
    LAUNCHER_ACCEPTANCE_LEGS,
    LAYOUT_ADAPTER_ID,
    LIFECYCLE_SEQUENCE,
    SHIPPED_UPDATE_LEGS,
    ImageIntegrationSeams,
    LifecycleConfig,
    LifecycleContractError,
    LifecycleHarness,
    LifecycleHarnessError,
    assert_lifecycle_transitions,
    file_cross_check_tools,
    lifecycle_spec,
    observe_file_backed_image,
    require_device_host,
    run_file_cross_check,
    shipped_update_authority,
    write_mbr_table_for_plan,
)
from tools.x8_qemu.runner import layout_plan_for_device

HAS_CRYPTOGRAPHY = importlib.util.find_spec("cryptography") is not None


def _harness(tmp: str) -> LifecycleHarness:
    return LifecycleHarness(LifecycleConfig(output_dir=Path(tmp) / "out"))


class LifecycleSpecTests(unittest.TestCase):
    def test_declares_8_step_lifecycle_with_shipped_and_launcher_legs(self) -> None:
        spec = lifecycle_spec()
        self.assertEqual(list(spec["lifecycle_sequence"]), list(LIFECYCLE_SEQUENCE))
        self.assertEqual(len(LIFECYCLE_SEQUENCE), 8)
        for required in (
            "fresh-install-A",
            "boot-A-accepted",
            "stage-B-one-shot",
            "boot-B-commit",
            "stage-broken-candidate",
            "boot-broken-candidate",
            "recovery-boot-B",
            "reverse-update-B-to-A",
        ):
            self.assertIn(required, LIFECYCLE_SEQUENCE)
        for leg in SHIPPED_UPDATE_LEGS:
            self.assertIn(leg, LIFECYCLE_SEQUENCE)
        for leg in LAUNCHER_ACCEPTANCE_LEGS:
            self.assertIn(leg, LIFECYCLE_SEQUENCE)
        self.assertEqual(spec["layout_adapter"], LAYOUT_ADAPTER_ID)
        self.assertEqual(spec["boot_backend"], BOOT_BACKEND_ID)
        self.assertIs(spec["valued_device_contact"], False)
        self.assertIn("block-driver seam", str(spec["fake_boundary"]))

    def test_config_refuses_source_tree_output(self) -> None:
        from tools.x8_qemu.lifecycle import PROJECT_ROOT

        with self.assertRaises(LifecycleHarnessError):
            LifecycleConfig(output_dir=PROJECT_ROOT / "build" / "t6").validate()
        with self.assertRaises(LifecycleHarnessError):
            LifecycleConfig(output_dir=Path("relative/out")).validate()


@unittest.skipUnless(HAS_CRYPTOGRAPHY, "signed bundles need cryptography")
class ShippedLifecycleTests(unittest.TestCase):
    def test_full_8_step_run_green_through_shipped_paths(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            harness = _harness(tmp)
            report = harness.run_source_scope()
            self.assertTrue(report["ok"])
            self.assertEqual(report["classification"], "SOURCE_SCOPE_T6_LIFECYCLE")
            steps = report["steps"]
            assert isinstance(steps, list)
            self.assertEqual(
                [s["step"] for s in steps], list(LIFECYCLE_SEQUENCE)
            )
            by_step = {s["step"]: s for s in steps}
            # Default held on A until the B health commit.
            self.assertEqual(by_step["stage-B-one-shot"]["default_slot"], "A")
            self.assertIsNone(by_step["stage-B-one-shot"]["one_shot_slot"])
            self.assertEqual(by_step["stage-B-one-shot"]["journal_state"], "update_staged")
            self.assertEqual(by_step["boot-B-commit"]["default_slot"], "B")
            self.assertEqual(by_step["boot-B-commit"]["accepted_slot"], "B")
            self.assertEqual(by_step["boot-B-commit"]["accepted_sequence"], 21)
            self.assertEqual(by_step["boot-B-commit"]["launcher"]["accepted_slot"], "B")
            self.assertEqual(
                by_step["boot-B-commit"]["launcher"]["seam_calls"],
                ["interactive_ready"],
            )
            # Broken candidate: FAILED, default untouched on B.
            self.assertEqual(
                by_step["boot-broken-candidate"]["journal_state"], "failed"
            )
            self.assertEqual(by_step["boot-broken-candidate"]["default_slot"], "B")
            # Recovery: no acceptance, PERSIST byte-identical.
            self.assertIsNone(
                by_step["recovery-boot-B"]["launcher"]["accepted_slot"]
            )
            self.assertEqual(
                by_step["recovery-boot-B"]["persist_marker"],
                by_step["boot-A-accepted"]["persist_marker"],
            )
            self.assertEqual(by_step["recovery-boot-B"]["default_slot"], "B")
            # Reverse update: slot role and release identity independent.
            self.assertEqual(by_step["reverse-update-B-to-A"]["default_slot"], "A")
            self.assertEqual(by_step["reverse-update-B-to-A"]["accepted_slot"], "A")
            self.assertEqual(by_step["reverse-update-B-to-A"]["accepted_sequence"], 23)
            self.assertEqual(
                by_step["reverse-update-B-to-A"]["launcher"]["accepted_slot"], "A"
            )
            for leg in SHIPPED_UPDATE_LEGS:
                self.assertIn(leg, report["shipped_update_legs"])
            for leg in LAUNCHER_ACCEPTANCE_LEGS:
                self.assertIn(leg, report["launcher_acceptance_legs"])
            # The harness passes its own transition contract.
            assert_lifecycle_transitions(report)
            self.assertTrue(harness.report_path.is_file())

    def test_default_construction_without_seams_fails_closed(self) -> None:
        """Shipped constructor with no destination seams stages fail-closed."""
        from unittest import mock as _mock

        from greia_platform.grub_ab import GrubEnvBackend
        from greia_platform.system_updates import (
            SystemUpdateInbox,
            UpdateBackendUnavailable,
            build_persistent_state_contract_bytes,
            generate_ed25519_keypair,
        )
        from tools.x8_qemu.lifecycle import (
            build_test_release,
            default_shipped_authority_without_seams,
            fresh_machine_state,
            mint_signing_keys,
        )

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            machine = fresh_machine_state(root / "machine")
            private_key, _ = mint_signing_keys(root / "machine", machine["keys"])
            bundle = build_test_release(
                root / "machine", name="r9", release_id="greia-0.21.0",
                sequence=21, private_key=private_key,
            )
            with _mock.patch.dict(
                __import__("os").environ,
                {
                    "GREIA_SYSTEM_VERSION": "0.20.0",
                    "GREIA_SYSTEM_PLATFORM_FAMILY": "legacy-x86",
                    "GREIA_SYSTEM_ARCHITECTURE": "i386",
                    "GREIA_SYSTEM_PROFILE": "legacy-x86-i686",
                },
                clear=False,
            ):
                authority = default_shipped_authority_without_seams(
                    state_dir=machine["state"],
                    trusted_key_dir=machine["keys"],
                    layout_record_path=machine["layout"],
                    boot_backend=GrubEnvBackend.attach(machine["boot_control"]),
                )
                self.assertIsNone(authority.backend.seams.slot_store_factory)
                SystemUpdateInbox(machine["state"]).receive(bundle)
                verified = authority.verify_current_candidate()
                self.assertTrue(verified.present)
                journal_file = (
                    machine["state"] / "system-updates" / "journal" / "boot-journal.json"
                )
                with self.assertRaises(UpdateBackendUnavailable):
                    authority.stage_current_candidate()
            self.assertFalse(journal_file.exists())
            self.assertEqual(
                GrubEnvBackend.attach(machine["boot_control"]).inspect().default_slot,
                "A",
            )
            _ = build_persistent_state_contract_bytes
            _ = generate_ed25519_keypair

    def test_install_composition_executes_through_shipped_builder(self) -> None:
        from tools.x8_qemu.lifecycle import fresh_machine_state, prove_install_composition

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            machine = fresh_machine_state(root / "machine")
            proof = prove_install_composition(
                root / "proof",
                layout_record_path=machine["layout"],
                password_hash="grub.pbkdf2.sha512.10000.T6HARNESS3ABCDEF0123456789",
            )
            self.assertEqual(proof["install_mode"], "ab")
            self.assertEqual(proof["journal_state"], "first_install_pending")
            self.assertTrue(proof["half_wired_refused"])
            self.assertGreater(proof["grub_cfg_bytes"], 0)


class PositiveControlTests(unittest.TestCase):
    """Each required RED condition fails the run for the right reason."""

    @unittest.skipUnless(HAS_CRYPTOGRAPHY, "signed bundles need cryptography")
    def test_pc1_defeated_candidate_health_forces_failure_and_recovery(self) -> None:
        """Break -> RED -> restore -> GREEN on the recovery trigger."""
        from greia_platform.boot_transaction import (
            BootTransactionCoordinator,
            BootTransactionJournal,
            BootTransactionState,
            mark_candidate_unhealthy,
        )
        from greia_platform.grub_ab import GrubEnvBackend
        from tools.x8_qemu.lifecycle import _artifact_set, fresh_machine_state

        with tempfile.TemporaryDirectory() as tmp:
            machine = fresh_machine_state(Path(tmp) / "machine")
            backend = GrubEnvBackend.attach(machine["boot_control"])
            journal_dir = Path(tmp) / "journal"
            journal_dir.mkdir(parents=True, exist_ok=True)
            coordinator = BootTransactionCoordinator.begin_update(
                journal_dir=journal_dir,
                backend=backend,
                candidate_artifacts=_artifact_set("B", "greia-0.21.0", 21),
                accepted_artifacts=_artifact_set("A", "greia-0.20.0", 20),
                release_id="greia-0.21.0",
                release_sequence=21,
            )
            coordinator.arm()
            # BREAK: the candidate boots but health never confirms.
            backend.reconcile("B")
            coordinator.observe_boot()
            decision = mark_candidate_unhealthy(
                coordinator, recovery_class="health-service-failure",
                detail="pc1 defeated health",
            )
            # RED: FAILED recorded, default never mutated, reboot returns B? No:
            # default stays A (previous accepted), candidate abandoned.
            journal = BootTransactionJournal.load(journal_dir)
            self.assertEqual(journal.state, BootTransactionState.FAILED)
            self.assertIn("recovery:health-service-failure", decision.note)
            self.assertEqual(backend.inspect().default_slot, "A")
            # RESTORE: a fresh machine with healthy acceptance stays GREEN.
            machine2 = fresh_machine_state(Path(tmp) / "machine2")
            backend2 = GrubEnvBackend.attach(machine2["boot_control"])
            backend2.arm_one_shot("B")
            backend2.reconcile("B")
            backend2.commit_accepted("B")
            self.assertEqual(backend2.inspect().default_slot, "B")

    def test_pc2_corrupted_grub_slot_binding_fails_acceptance(self) -> None:
        """Break -> RED -> restore -> GREEN on the GRUB binding."""
        from greia_platform.boot_transaction import BootTransactionError
        from greia_platform.grub_ab import GRUBENV_FILE_NAME, GrubEnvBackend
        from tools.x8_qemu.lifecycle import fresh_machine_state

        with tempfile.TemporaryDirectory() as tmp:
            machine = fresh_machine_state(Path(tmp) / "machine")
            backend = GrubEnvBackend.attach(machine["boot_control"])
            backend.arm_one_shot("B")
            env_path = machine["boot_control"] / GRUBENV_FILE_NAME
            intact = env_path.read_bytes()
            # BREAK: alias the one-shot to the persistent default.
            env_path.write_bytes(intact.replace(b"next_entry=greia-b", b"next_entry=greia-a"))
            with self.assertRaises(BootTransactionError):
                GrubEnvBackend.attach(machine["boot_control"]).inspect()
            # RESTORE the exact bytes and re-prove GREEN.
            env_path.write_bytes(intact)
            observed = GrubEnvBackend.attach(machine["boot_control"]).inspect()
            self.assertEqual(observed.default_slot, "A")
            self.assertEqual(observed.one_shot_slot, "B")

    @unittest.skipUnless(HAS_CRYPTOGRAPHY, "signed bundles need cryptography")
    def test_pc3_broken_rollback_default_invariant_fails_run(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            harness = _harness(tmp)
            report = harness.run_source_scope()
            tampered = json.loads(json.dumps(report))
            steps = tampered["steps"]
            assert isinstance(steps, list)
            for step in steps:
                if isinstance(step, dict):
                    step["default_slot"] = "A"
            with self.assertRaises(LifecycleContractError):
                assert_lifecycle_transitions(tampered)

    def test_pc4_same_disk_reboot_without_transitions_fails_contract(self) -> None:
        degenerate = {
            "steps": [
                {"step": "fresh-install-A", "default_slot": "A"},
                {"step": "fresh-install-A", "default_slot": "A"},
            ],
            "shipped_update_legs": [],
            "launcher_acceptance_legs": [],
        }
        with self.assertRaises(LifecycleContractError):
            assert_lifecycle_transitions(degenerate)
        # No slot movement either: identical defaults fail even with names.
        no_movement = {
            "steps": [
                {"step": name, "default_slot": "A"} for name in LIFECYCLE_SEQUENCE
            ],
            "shipped_update_legs": list(SHIPPED_UPDATE_LEGS),
            "launcher_acceptance_legs": list(LAUNCHER_ACCEPTANCE_LEGS),
        }
        with self.assertRaises(LifecycleContractError):
            assert_lifecycle_transitions(no_movement)

    def test_pc5_bypass_of_shipped_constructor_or_launcher_leg_fails(self) -> None:
        from tools.x8_qemu import lifecycle as module

        text = Path(module.__file__).read_text(encoding="utf-8")
        # The harness must drive the shipped constructor, never route around it.
        self.assertIn("build_live_update_service", text)
        self.assertIn("apply_prepared_state", text)
        self.assertIn("run_post_intro_acceptance", text)
        self.assertNotIn("simulate_reboot(", text)
        self.assertNotIn("FakeGrubBackend", text)
        # A report missing any shipped/launcher leg fails the contract.
        with tempfile.TemporaryDirectory() as tmp:
            harness = LifecycleHarness(LifecycleConfig(output_dir=Path(tmp) / "out"))
            report = dict(harness.run_source_scope()) if HAS_CRYPTOGRAPHY else None
            if report is not None:
                bypassed = json.loads(json.dumps(report))
                bypassed["shipped_update_legs"] = ["stage-B-one-shot"]
                with self.assertRaises(LifecycleContractError):
                    assert_lifecycle_transitions(bypassed)
                bypassed2 = json.loads(json.dumps(report))
                bypassed2["launcher_acceptance_legs"] = []
                with self.assertRaises(LifecycleContractError):
                    assert_lifecycle_transitions(bypassed2)


class ObservationTests(unittest.TestCase):
    def test_file_backed_observation_binds_record_to_topology(self) -> None:
        from tools.x8_qemu.lifecycle import _mbr_table_span_bytes

        with tempfile.TemporaryDirectory() as tmp:
            image = Path(tmp) / "disposable-mbr.img"
            plan = layout_plan_for_device(3072 * 1024 * 1024)
            # The file is exactly the plan size: the plan-derived table
            # span agrees with it (single source of truth, no fudge).
            target = int(getattr(plan, "device_size_bytes"))
            self.assertEqual(_mbr_table_span_bytes(plan), target)
            with open(image, "wb") as handle:
                handle.truncate(target)
            write_mbr_table_for_plan(image, plan=plan)
            result = observe_file_backed_image(image, plan=plan)
            self.assertTrue(result.record_matches_topology)
            self.assertEqual(result.disk_signature, "1a2b3c4d")
            self.assertEqual(
                set(result.observed_identities), {"system-a", "system-b", "persist"}
            )
            # Teardown/remount/reload: the record persists and reloads.
            self.assertTrue((image.parent / "installed-layout.json").is_file())
            # The file cross-check reports honestly: executed (not skipped)
            # where tools exist, explicit deferred elsewhere — never false green.
            cross = run_file_cross_check(image, expected_signature="1a2b3c4d")
            tools = file_cross_check_tools()
            if tools["sfdisk"] is not None and tools["blkid"] is not None:
                self.assertTrue(cross["executed"])
                self.assertTrue(cross["green"])
            else:
                self.assertFalse(cross["executed"])
                self.assertFalse(cross["green"])
                self.assertIn("deferred", cross["detail"])

    def test_device_host_gate_fails_closed_off_linux(self) -> None:
        import sys as _sys

        if _sys.platform == "linux" and Path("/dev").exists():
            self.skipTest("capable-host gate is evaluated on Linux device runs")
        with self.assertRaises(LifecycleHarnessError):
            require_device_host()

    def test_image_assembly_stays_outside_source_tree(self) -> None:
        from tools.x8_qemu.lifecycle import assemble_disposable_image

        with tempfile.TemporaryDirectory() as tmp:
            manifest = assemble_disposable_image(Path(tmp) / "out")
            self.assertTrue(Path(manifest["image"]).is_file())
            self.assertEqual(manifest["adapter"], "legacy-bios-ab-v1")
            self.assertEqual(manifest["install_composition_mode"], "ab")
            self.assertEqual(len(manifest["image_sha256"]), 64)


class HarnessBoundaryTests(unittest.TestCase):
    def test_lifecycle_has_no_parallel_mechanisms(self) -> None:
        from tools.x8_qemu import lifecycle as module

        text = Path(module.__file__).read_text(encoding="utf-8")
        for forbidden in (
            "class SlotWriter",
            "class SlotFinalizer",
            "def render_grub_ab_config",
            "def build_update_bundle",
            "class GrubEnvBackend",
            "class BootTransactionJournal",
        ):
            self.assertNotIn(forbidden, text)
        for required in (
            "from greia_installer.layout import",
            "from greia_platform.system_updates import",
            "GrubEnvBackend",
            "build_live_update_service",
            "LauncherApplication",
            "mark_candidate_unhealthy",
            "observe_legacy_mbr_identities",
        ):
            self.assertIn(required, text)

    def test_unknown_lifecycle_step_is_refused(self) -> None:
        with self.assertRaises(LifecycleContractError):
            assert_lifecycle_transitions(
                {"steps": [{"step": "not-a-step"}],
                 "shipped_update_legs": [], "launcher_acceptance_legs": []}
            )


if __name__ == "__main__":
    unittest.main()
