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
    COLLECT_ABORT_GATES,
    COLLECT_CONTINUATION_RULES,
    COLLECT_FROZEN_PREDICATES,
    COLLECT_LEG_ORDER,
    COLLECT_OBSERVED_GATES,
    COLLECT_RED_EVIDENCE_KEYS,
    LAUNCHER_ACCEPTANCE_LEGS,
    LAYOUT_ADAPTER_ID,
    LIFECYCLE_SEQUENCE,
    LOOP_OBSERVE_MAX_ATTEMPTS,
    LOOP_RESCAN_GATE,
    SHIPPED_UPDATE_LEGS,
    BootLegCapture,
    CollectAbortError,
    DeviceCollectRecorder,
    ImageIntegrationSeams,
    LifecycleConfig,
    LifecycleContractError,
    LifecycleHarness,
    LifecycleHarnessError,
    LegTimeoutPolicy,
    assert_collect_destructive_bounds,
    assert_lifecycle_transitions,
    build_device_collect_diagnostics,
    check_boot_exit,
    decide_device_boot_observation,
    file_cross_check_tools,
    lifecycle_spec,
    observe_file_backed_image,
    observe_loop_attached_device,
    require_collect_precondition,
    require_device_host,
    rescan_loop_partitions,
    run_collect_sequence,
    run_file_cross_check,
    shipped_update_authority,
    snapshot_device_collect_state,
    write_device_collect_diagnostics,
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


class _FakeCompleted:
    def __init__(self, returncode: int = 0) -> None:
        self.returncode = returncode


def _fake_run_factory(events: list, *, returncode: int = 0):  # type: ignore[no-untyped-def]
    def _fake_run(argv: object, **kwargs: object) -> _FakeCompleted:
        events.append(("rescan", list(argv), dict(kwargs)))  # type: ignore[arg-type]
        return _FakeCompleted(returncode)
    return _fake_run


def _fake_which_factory(present: dict[str, bool]):  # type: ignore[no-untyped-def]
    def _fake_which(name: str) -> str | None:
        return f"/usr/sbin/{name}" if present.get(name, False) else None
    return _fake_which


_RESCAN_SIG = "1a2b3c4d"
_RESCAN_UUID_A = "aaaaaaaa-1111-2222-3333-444444444444"
_RESCAN_UUID_B = "bbbbbbbb-1111-2222-3333-444444444444"
_RESCAN_UUID_P = "cccccccc-1111-2222-3333-444444444444"


def _rescan_identities(  # type: ignore[no-untyped-def]
    partuuids: dict[str, str] | None = None,
    uuids: dict[str, str] | None = None,
) -> dict[str, dict[str, str]]:
    parts = partuuids or {
        "system-a": f"{_RESCAN_SIG}-02",
        "system-b": f"{_RESCAN_SIG}-03",
        "persist": f"{_RESCAN_SIG}-04",
    }
    fsids = uuids or {
        "system-a": _RESCAN_UUID_A,
        "system-b": _RESCAN_UUID_B,
        "persist": _RESCAN_UUID_P,
    }
    return {
        role: {
            "filesystem_uuid": fsids[role],
            "partuuid": parts[role],
            "scheme": "MBR_PARTUUID",
        }
        for role in ("system-a", "system-b", "persist")
    }


class _QueueProbeRunner:
    """Scripted MbrProbeRunner: pops one stdout per probe call, in order."""

    def __init__(self, answers: list[str], events: list) -> None:  # type: ignore[no-untyped-def]
        from greia_installer.layout import MbrCommandResult

        self._answers = list(answers)
        self._events = events
        self._result = MbrCommandResult

    def run(self, command: object) -> object:
        argv = list(command)  # type: ignore[arg-type]
        self._events.append(("probe", argv))
        if not self._answers:
            raise AssertionError(f"probe runner exhausted answers at {argv!r}")
        return self._result(stdout=self._answers.pop(0), returncode=0)


def _green_answers() -> list[str]:
    return [
        _RESCAN_SIG,
        f"{_RESCAN_SIG}-02", _RESCAN_UUID_A,
        f"{_RESCAN_SIG}-03", _RESCAN_UUID_B,
        f"{_RESCAN_SIG}-04", _RESCAN_UUID_P,
    ]


def _rescan_plan_and_record(tmp: str):  # type: ignore[no-untyped-def]
    from greia_platform.persistent_layout import InstalledLayoutRecord
    from tools.x8_qemu.lifecycle import _record_dict_for_identities

    plan = layout_plan_for_device(3072 * 1024 * 1024)
    record_path = Path(tmp) / "installed-layout.json"
    record = InstalledLayoutRecord.from_dict(
        _record_dict_for_identities(_rescan_identities())
    )
    record.write_to(record_path)
    return plan, record_path


class LoopRescanObserveTests(unittest.TestCase):
    """Rescan-then-observe binding for the post-run loop/cross-check."""

    def test_rescan_runs_partprobe_then_settle_as_argv_arrays(self) -> None:
        events: list = []
        result = rescan_loop_partitions(
            Path("/dev/loop9"),
            run=_fake_run_factory(events),
            which=_fake_which_factory(
                {"partprobe": True, "partx": False, "udevadm": True}
            ),
        )
        self.assertEqual(
            result["attempted"],
            [["partprobe", "/dev/loop9"], ["udevadm", "settle"]],
        )
        self.assertEqual(result["missing"], ["partx"])
        self.assertEqual(result["failures"], [])
        for _kind, argv, kwargs in events:
            self.assertIsInstance(argv, list)
            self.assertFalse(kwargs.get("shell"), "rescan must use shell=False")
        self.assertIn("partprobe", str(result["detail"]))

    def test_rescan_falls_back_to_partx_when_partprobe_missing(self) -> None:
        events: list = []
        result = rescan_loop_partitions(
            Path("/dev/loop9"),
            run=_fake_run_factory(events),
            which=_fake_which_factory(
                {"partprobe": False, "partx": True, "udevadm": True}
            ),
        )
        self.assertEqual(
            result["attempted"],
            [["partx", "-u", "/dev/loop9"], ["udevadm", "settle"]],
        )
        self.assertEqual(result["missing"], ["partprobe"])

    def test_rescan_missing_tools_is_tolerated_never_a_silent_skip(self) -> None:
        events: list = []
        result = rescan_loop_partitions(
            Path("/dev/loop9"),
            run=_fake_run_factory(events),
            which=_fake_which_factory({}),
        )
        self.assertEqual(result["attempted"], [])
        self.assertEqual(
            result["missing"], ["partprobe", "partx", "udevadm"]
        )
        self.assertIn("missing", str(result["detail"]))
        self.assertEqual(events, [])
        # Observation still runs exactly once and goes GREEN.
        with tempfile.TemporaryDirectory() as tmp:
            plan, record_path = _rescan_plan_and_record(tmp)
            probe_events: list = []
            observed = observe_loop_attached_device(
                Path("/dev/loop9"),
                plan=plan,
                record_path=record_path,
                runner=_QueueProbeRunner(_green_answers(), probe_events),
                rescan_run=_fake_run_factory(events),
                rescan_which=_fake_which_factory({}),
                retry_settle_seconds=0,
            )
        self.assertTrue(observed["loop_attach_green"])
        self.assertEqual(observed["observation_attempts"], 1)
        self.assertEqual(len(probe_events), 7)

    def test_transient_empty_probe_goes_green_after_rescan_retry(self) -> None:
        """Break (stale view) -> rescan+retry -> GREEN through the real path."""
        events: list = []
        answers = [_RESCAN_SIG, ""] + _green_answers()
        with tempfile.TemporaryDirectory() as tmp:
            plan, record_path = _rescan_plan_and_record(tmp)
            result = observe_loop_attached_device(
                Path("/dev/loop9"),
                plan=plan,
                record_path=record_path,
                runner=_QueueProbeRunner(answers, events),
                rescan_run=_fake_run_factory(events),
                rescan_which=_fake_which_factory(
                    {"partprobe": True, "partx": True, "udevadm": True}
                ),
                retry_settle_seconds=0,
            )
        self.assertTrue(result["loop_attach_green"])
        self.assertEqual(result["proven_signature"], _RESCAN_SIG)
        self.assertEqual(result["observation_attempts"], 2)
        # The rescan ran before the first production probe.
        kinds = [kind for kind, *_ in events]
        self.assertEqual(kinds[0], "rescan")
        first_probe = kinds.index("probe")
        self.assertTrue(
            all(kind == "rescan" for kind in kinds[:first_probe]),
            f"rescan must precede observation: {kinds!r}",
        )
        rescan_argvs = [argv for kind, argv, *_ in events if kind == "rescan"]
        self.assertIn(["partprobe", "/dev/loop9"], rescan_argvs)
        self.assertIn(["partx", "-u", "/dev/loop9"], rescan_argvs)
        self.assertIn(["udevadm", "settle"], rescan_argvs)

    def test_persistent_absence_reds_at_the_named_rescan_gate(self) -> None:
        """Positive control: absent nodes stay RED, never synthesized green."""
        events: list = []
        with tempfile.TemporaryDirectory() as tmp:
            plan, record_path = _rescan_plan_and_record(tmp)

            def _always_empty(command: object) -> object:
                from greia_installer.layout import MbrCommandResult

                argv = list(command)  # type: ignore[arg-type]
                events.append(("probe", argv))
                if "-s" in argv and "PTUUID" in argv and argv[-1] == "/dev/loop9":
                    return MbrCommandResult(stdout=_RESCAN_SIG, returncode=0)
                return MbrCommandResult(stdout="", returncode=0)

            class _EmptyRunner:
                def run(self, command: object) -> object:
                    return _always_empty(command)

            with self.assertRaises(LifecycleHarnessError) as ctx:
                observe_loop_attached_device(
                    Path("/dev/loop9"),
                    plan=plan,
                    record_path=record_path,
                    runner=_EmptyRunner(),
                    rescan_run=_fake_run_factory(events),
                    rescan_which=_fake_which_factory(
                        {"partprobe": True, "partx": False, "udevadm": True}
                    ),
                    max_attempts=3,
                    retry_settle_seconds=0,
                )
        message = str(ctx.exception)
        self.assertIn(LOOP_RESCAN_GATE, message)
        self.assertIn("/dev/loop9", message)
        self.assertIn("3 observation attempt", message)
        self.assertIn("no PARTUUID for /dev/loop9p2", message)

    def test_wrong_disk_binding_still_reds(self) -> None:
        """Binding is not laundered: off-disk PARTUUIDs stay RED."""
        events: list = []
        answers: list[str] = []
        for _ in range(LOOP_OBSERVE_MAX_ATTEMPTS):
            answers.extend([_RESCAN_SIG, "deadbeef-02"])
        with tempfile.TemporaryDirectory() as tmp:
            plan, record_path = _rescan_plan_and_record(tmp)
            with self.assertRaises(LifecycleHarnessError) as ctx:
                observe_loop_attached_device(
                    Path("/dev/loop9"),
                    plan=plan,
                    record_path=record_path,
                    runner=_QueueProbeRunner(answers, events),
                    rescan_run=_fake_run_factory(events),
                    rescan_which=_fake_which_factory(
                        {"partprobe": True, "partx": False, "udevadm": True}
                    ),
                    retry_settle_seconds=0,
                )
        self.assertIn(LOOP_RESCAN_GATE, str(ctx.exception))
        self.assertIn("wrong-disk", str(ctx.exception))

    def test_cloned_filesystem_uuid_binding_still_reds(self) -> None:
        """Binding is not laundered: cloned filesystem UUIDs stay RED."""
        events: list = []
        answers: list[str] = []
        for _ in range(LOOP_OBSERVE_MAX_ATTEMPTS):
            answers.extend(
                [
                    _RESCAN_SIG,
                    f"{_RESCAN_SIG}-02", _RESCAN_UUID_A,
                    f"{_RESCAN_SIG}-03", _RESCAN_UUID_A,
                    f"{_RESCAN_SIG}-04", _RESCAN_UUID_A,
                ]
            )
        with tempfile.TemporaryDirectory() as tmp:
            plan, record_path = _rescan_plan_and_record(tmp)
            with self.assertRaises(LifecycleHarnessError) as ctx:
                observe_loop_attached_device(
                    Path("/dev/loop9"),
                    plan=plan,
                    record_path=record_path,
                    runner=_QueueProbeRunner(answers, events),
                    rescan_run=_fake_run_factory(events),
                    rescan_which=_fake_which_factory(
                        {"partprobe": True, "partx": False, "udevadm": True}
                    ),
                    retry_settle_seconds=0,
                )
        self.assertIn(LOOP_RESCAN_GATE, str(ctx.exception))
        self.assertIn("cloned", str(ctx.exception))

    def test_run_device_binding_structure_carries_rescan_to_cross_check(self) -> None:
        import inspect as _inspect

        from tools.x8_qemu import lifecycle as module

        run_body = _inspect.getsource(module.LifecycleHarness.run_device)
        self.assertIn("observe_loop_attached_device", run_body)
        self.assertIn("run_file_cross_check", run_body)
        observe_body = _inspect.getsource(module.observe_loop_attached_device)
        for required in (
            "rescan_loop_partitions",
            "udevadm",
            "settle",
            "max_attempts",
            "observation_attempts",
            "LOOP_RESCAN_GATE",
        ):
            self.assertIn(required, observe_body)
        rescan_body = _inspect.getsource(module.rescan_loop_partitions)
        for required in ("partprobe", "partx", "shell=False"):
            self.assertIn(required, rescan_body)
        # No production layout behavior change: the observation
        # authority owns no rescan (its pre-existing install-time
        # partprobe under LegacyBiosAbAdapter.execute is untouched).
        from greia_installer.layout import observe_legacy_mbr_identities

        observe_src = _inspect.getsource(observe_legacy_mbr_identities)
        self.assertNotIn("rescan", observe_src)
        self.assertNotIn("partx", observe_src)

    def test_writer_table_intact_while_partition_view_stale(self) -> None:
        """Falsify the corrupt-table alternative at the source-scope seam.

        The harness writer emits a DOS table that parses to all four
        present primaries, and the production observer probes the
        whole-disk PTUUID before any partition-node PARTUUID — so a
        whole-disk-green / partition-empty split proves a stale kernel
        view (rescan race), not a corrupt table.
        """
        import inspect as _inspect

        from greia_installer.layout import (
            observe_legacy_mbr_identities,
            parse_dos_partition_table,
        )

        with tempfile.TemporaryDirectory() as tmp:
            image = Path(tmp) / "disposable-mbr.img"
            plan = layout_plan_for_device(3072 * 1024 * 1024)
            target = int(getattr(plan, "device_size_bytes"))
            with open(image, "wb") as handle:
                handle.truncate(target)
            write_mbr_table_for_plan(image, plan=plan)
            with open(image, "rb") as handle:
                table = parse_dos_partition_table(handle.read(512))
        self.assertNotEqual(table.disk_signature, "00000000")
        self.assertEqual(
            sorted(p.number for p in table.partitions), [1, 2, 3, 4]
        )
        self.assertTrue(all(p.partition_type != 0x00 for p in table.partitions))
        body = _inspect.getsource(observe_legacy_mbr_identities)
        self.assertLess(
            body.index("read_mbr_disk_signature"),
            body.index("probe_mbr_partition_partuuid"),
            "whole-disk PTUUID must be probed before partition PARTUUIDs",
        )


class CollectSequenceTests(unittest.TestCase):
    """DIAG-C1 fail-collect: real predicates through the real reporting path.

    Multi-fault legs call the frozen production predicates
    (``decide_device_boot_observation``, ``check_boot_exit``) — never a
    helper stub — and collect through the production
    ``DeviceCollectRecorder`` / ``run_collect_sequence`` /
    ``build_device_collect_diagnostics`` reporting path that
    ``run_device_collect`` uses.
    """

    def _consumption_fault(self):  # type: ignore[no-untyped-def]
        """Armed-but-unconsumed boot-B leg through the frozen predicate."""
        pre = {"one_shot_slot": "B", "default_slot": "A"}
        post = {"one_shot_slot": "B", "default_slot": "A"}
        return decide_device_boot_observation(
            leg="boot-B-commit", pre=pre, post=post)

    def _clean_exit_fault(self, tmp: str):  # type: ignore[no-untyped-def]
        """Unclean QEMU exit through the frozen clean-exit gate."""
        log = Path(tmp) / "qemu-boot-B-commit.log"
        log.write_text("fake qemu log\n", encoding="utf-8")
        check_boot_exit(1, leg="boot-B-commit", qemu_log=log)

    def _multi_fault_legs(self, tmp: str):  # type: ignore[no-untyped-def]
        return [
            {
                "leg": "boot-B-commit",
                "gate": "consumption-predicate",
                "frozen_predicate": COLLECT_FROZEN_PREDICATES["consumption-predicate"],
                "run": self._consumption_fault,
                "context": lambda: {
                    "returncode": 0,
                    "serial_log": str(Path(tmp) / "device-boot-B-commit-serial.log"),
                    "qemu_log": str(Path(tmp) / "device-boot-B-commit-qemu.log"),
                    "serial_bytes": 512,
                    "serial_growth_bytes": 512,
                    "on_image_pre": {"one_shot_slot": "B", "default_slot": "A"},
                    "on_image_post": {"one_shot_slot": "B", "default_slot": "A"},
                    "timeout": {"outcome": "progress-clean", "red": False},
                },
            },
            {
                "leg": "recovery-boot-B",
                "gate": "clean-exit-gate",
                "frozen_predicate": COLLECT_FROZEN_PREDICATES["clean-exit-gate"],
                "run": lambda: self._clean_exit_fault(tmp),
                "context": lambda: {
                    "returncode": 1,
                    "qemu_log": str(Path(tmp) / "qemu-boot-B-commit.log"),
                    "serial_bytes": 0,
                    "serial_growth_bytes": 0,
                    "timeout": {"outcome": "silence", "red": True},
                },
            },
            {
                "leg": "reverse-update-B-to-A",
                "gate": "consumption-predicate",
                "frozen_predicate": COLLECT_FROZEN_PREDICATES["consumption-predicate"],
                "run": lambda: "green-leg-still-runs",
            },
        ]

    def test_multi_fault_probe_surfaces_every_red_with_gate_and_evidence(self) -> None:
        """Acceptance: one run surfaces N independent defects."""
        with tempfile.TemporaryDirectory() as tmp:
            recorder = DeviceCollectRecorder()
            verdict = run_collect_sequence(self._multi_fault_legs(tmp), recorder)
            self.assertFalse(verdict["ok"])
            self.assertEqual(verdict["red_count"], 2)
            # Nothing skipped after an observed RED: all legs attempted,
            # including the green leg after both faults.
            self.assertEqual(
                verdict["legs_attempted"],
                ["boot-B-commit", "recovery-boot-B", "reverse-update-B-to-A"],
            )
            reds = recorder.reds
            self.assertEqual(len(reds), 2)
            by_leg = {red["leg"]: red for red in reds}
            self.assertEqual(by_leg["boot-B-commit"]["gate"], "consumption-predicate")
            self.assertIn("armed-but-unconsumed", by_leg["boot-B-commit"]["error"])
            self.assertEqual(
                by_leg["boot-B-commit"]["on_image_post"],
                {"one_shot_slot": "B", "default_slot": "A"},
            )
            self.assertEqual(by_leg["recovery-boot-B"]["gate"], "clean-exit-gate")
            self.assertIn("exited with status 1", by_leg["recovery-boot-B"]["error"])
            self.assertEqual(by_leg["recovery-boot-B"]["returncode"], 1)
            for red in reds:
                self.assertFalse(red["abort"])
                self.assertTrue(red["frozen_predicate"])
            artifact = build_device_collect_diagnostics(
                recorder, run_meta={"probe": "multi-fault"})
            self.assertFalse(artifact["verdict"]["ok"])
            self.assertEqual(artifact["verdict"]["red_count"], 2)
            self.assertEqual(len(artifact["reds"]), 2)

    def test_single_fault_equivalence_with_fail_fast(self) -> None:
        """Each injected fault yields the identical RED as fail-fast."""
        with tempfile.TemporaryDirectory() as tmp:
            try:
                self._consumption_fault()
            except LifecycleHarnessError as exc:
                fail_fast_consumption = str(exc)
            else:
                self.fail("frozen consumption predicate did not RED")
            try:
                self._clean_exit_fault(tmp)
            except LifecycleHarnessError as exc:
                fail_fast_exit = str(exc)
            else:
                self.fail("frozen clean-exit gate did not RED")
            recorder = DeviceCollectRecorder()
            run_collect_sequence(self._multi_fault_legs(tmp), recorder)
            by_leg = {red["leg"]: red for red in recorder.reds}
            # Verbatim fail-fast errors: no swallowed or reworded reds.
            self.assertEqual(by_leg["boot-B-commit"]["error"], fail_fast_consumption)
            self.assertEqual(by_leg["recovery-boot-B"]["error"], fail_fast_exit)
            self.assertEqual(
                by_leg["boot-B-commit"]["error_type"], "LifecycleHarnessError")

    def test_abort_class_stops_collection_immediately(self) -> None:
        """Negative proof: teardown-safety failure aborts, never collected."""
        calls: list[str] = []
        recorder = DeviceCollectRecorder()

        def _green() -> str:
            calls.append("green")
            return "green"

        def _teardown_failure() -> object:
            calls.append("teardown")
            raise CollectAbortError(
                "teardown-loop-detach-safety: loop detach failed for "
                "/dev/loop9 (rc=1); aborting fail closed"
            )

        def _never() -> str:
            calls.append("never")
            return "never"

        legs = [
            {"leg": "boot-A-accepted", "gate": "consumption-predicate",
             "frozen_predicate": "frozen", "run": _green},
            {"leg": "boot-B-commit", "gate": "teardown-loop-detach-safety",
             "frozen_predicate": COLLECT_FROZEN_PREDICATES[
                 "teardown-loop-detach-safety"],
             "run": _teardown_failure},
            {"leg": "recovery-boot-B", "gate": "consumption-predicate",
             "frozen_predicate": "frozen", "run": _never},
        ]
        with self.assertRaises(CollectAbortError):
            run_collect_sequence(legs, recorder)
        self.assertEqual(calls, ["green", "teardown"])
        self.assertEqual(recorder.attempted, ["boot-A-accepted", "boot-B-commit"])
        self.assertEqual(len(recorder.reds), 1)
        self.assertTrue(recorder.reds[0]["abort"])
        self.assertIsNotNone(recorder.abort)
        verdict = recorder.verdict()
        self.assertFalse(verdict["ok"])
        self.assertTrue(verdict["aborted"])

    def test_unexpected_exception_records_red_without_conversion(self) -> None:
        calls: list[str] = []
        recorder = DeviceCollectRecorder()

        def _buggy() -> object:
            calls.append("buggy")
            raise ValueError("synthetic harness bug")

        legs = [
            {"leg": "stage-B-one-shot", "gate": "device_gate_for_image",
             "frozen_predicate": "frozen", "run": _buggy},
            {"leg": "boot-B-commit", "gate": "consumption-predicate",
             "frozen_predicate": "frozen",
             "run": lambda: calls.append("next") or "green"},
        ]
        verdict = run_collect_sequence(legs, recorder)
        self.assertFalse(verdict["ok"])
        self.assertEqual(verdict["red_count"], 1)
        self.assertEqual(calls, ["buggy", "next"])
        red = recorder.reds[0]
        self.assertEqual(red["error_type"], "ValueError")
        self.assertIn("synthetic harness bug", str(red["error"]))


class CollectTimeoutPolicyTests(unittest.TestCase):
    def test_thresholds_match_bootchain_frozen_predicates(self) -> None:
        from tools.x8_qemu.bootchain import (
            BOOT_WAIT_NO_PROGRESS_SECONDS,
            BOOT_WAIT_STALL_SECONDS,
        )

        policy = LegTimeoutPolicy(timeout_seconds=300)
        self.assertEqual(policy.no_progress_seconds, BOOT_WAIT_NO_PROGRESS_SECONDS)
        self.assertEqual(policy.stall_seconds, BOOT_WAIT_STALL_SECONDS)

    def test_classify_timeout_silence_stall_and_clean(self) -> None:
        policy = LegTimeoutPolicy(timeout_seconds=300)
        timed_out = policy.classify(
            serial_growth_bytes=64, image_sha_changed=True,
            elapsed_seconds=300.0, clean_exit=False)
        self.assertEqual(timed_out["outcome"], "timeout")
        self.assertTrue(timed_out["red"])
        silent = policy.classify(
            serial_growth_bytes=0, image_sha_changed=False,
            elapsed_seconds=130.0, clean_exit=False)
        self.assertEqual(silent["outcome"], "silence")
        self.assertTrue(silent["red"])
        stalled = policy.classify(
            serial_growth_bytes=64, image_sha_changed=False,
            elapsed_seconds=130.0, clean_exit=False)
        self.assertEqual(stalled["outcome"], "progress-then-stall")
        self.assertTrue(stalled["red"])
        clean = policy.classify(
            serial_growth_bytes=64, image_sha_changed=True,
            elapsed_seconds=10.0, clean_exit=True)
        self.assertEqual(clean["outcome"], "progress-clean")
        self.assertFalse(clean["red"])
        self.assertIn("ceiling", str(clean["detail"]))


class CollectDiagnosticsTests(unittest.TestCase):
    def test_artifact_schema_carries_every_required_field_per_red(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            recorder = DeviceCollectRecorder()
            try:
                decide_device_boot_observation(
                    leg="boot-B-commit",
                    pre={"one_shot_slot": "B", "default_slot": "A"},
                    post={"one_shot_slot": "B", "default_slot": "A"},
                )
            except LifecycleHarnessError as exc:
                recorder.run_leg(
                    leg="boot-B-commit", gate="consumption-predicate",
                    frozen_predicate="frozen-predicate-text",
                    run=lambda: (_ for _ in ()).throw(exc),
                    context=lambda: {
                        "returncode": 0,
                        "serial_log": str(Path(tmp) / "serial.log"),
                        "qemu_log": str(Path(tmp) / "qemu.log"),
                        "serial_bytes": 128,
                        "serial_growth_bytes": 128,
                        "image_sha256_pre": "ab" * 32,
                        "image_sha256_post": "cd" * 32,
                        "on_image_pre": {"one_shot_slot": "B"},
                        "on_image_post": {"one_shot_slot": "B"},
                        "disk_snapshot": {"default_slot": "A"},
                        "timeout": {"outcome": "progress-clean", "red": False},
                    },
                )
            artifact = build_device_collect_diagnostics(recorder, run_meta={})
            self.assertTrue(artifact["collect_mode"])
            self.assertEqual(artifact["artifact"], "greia-device-collect-diagnostics")
            self.assertEqual(
                artifact["continuation_rules"], list(COLLECT_CONTINUATION_RULES))
            self.assertIn("teardown-loop-detach-safety",
                          artifact["abort_boundary"]["abort_gates"])
            self.assertIn("consumption-predicate",
                          artifact["abort_boundary"]["observed_gates"])
            self.assertEqual(len(artifact["reds"]), 1)
            red = artifact["reds"][0]
            for key in (
                "leg", "gate", "frozen_predicate", "error_type", "error",
                "abort",
            ):
                self.assertIn(key, red)
            for key in COLLECT_RED_EVIDENCE_KEYS:
                self.assertIn(key, red)
            self.assertEqual(red["serial_growth_bytes"], 128)
            self.assertEqual(red["disk_snapshot"], {"default_slot": "A"})
            # Verdict aggregates and never converts.
            self.assertFalse(artifact["verdict"]["ok"])
            self.assertEqual(artifact["verdict"]["red_count"], 1)

    def test_verdict_green_only_when_no_reds(self) -> None:
        recorder = DeviceCollectRecorder()
        recorder.run_leg(leg="boot-A-accepted", gate="consumption-predicate",
                         frozen_predicate="frozen", run=lambda: "green")
        verdict = recorder.verdict()
        self.assertTrue(verdict["ok"])
        self.assertEqual(verdict["red_count"], 0)
        artifact = build_device_collect_diagnostics(recorder, run_meta={})
        self.assertTrue(artifact["verdict"]["ok"])

    def test_artifact_file_written_per_run(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            recorder = DeviceCollectRecorder()
            artifact = build_device_collect_diagnostics(
                recorder, run_meta={"run": "empty"})
            path = write_device_collect_diagnostics(Path(tmp), artifact)
            self.assertTrue(path.is_file())
            self.assertEqual(path.name, "greia-device-collect-diagnostics.json")
            import json as _json

            reloaded = _json.loads(path.read_text(encoding="utf-8"))
            self.assertTrue(reloaded["verdict"]["ok"])

    def test_snapshot_state_never_raises_and_never_synthesizes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            snapshot = snapshot_device_collect_state(
                image=Path(tmp) / "missing.img",
                machine={"boot_control": Path(tmp), "state": Path(tmp),
                         "layout": Path(tmp) / "missing.json",
                         "persist": Path(tmp)},
            )
            for key in ("image_sha256", "default_slot", "journal_state",
                        "accepted_slot", "accepted_sequence", "persist_marker"):
                self.assertIn(key, snapshot)
            self.assertIsNone(snapshot["image_sha256"])
            self.assertIsNone(snapshot["persist_marker"])


class CollectWiringTests(unittest.TestCase):
    def test_run_device_signature_still_takes_no_hook(self) -> None:
        import inspect as _inspect

        from tools.x8_qemu import lifecycle as module

        params = list(_inspect.signature(module.LifecycleHarness.run_device).parameters)
        self.assertEqual(params, ["self"])

    def test_collect_mode_routes_through_production_seams(self) -> None:
        import inspect as _inspect

        from tools.x8_qemu import lifecycle as module

        collect_body = _inspect.getsource(module.LifecycleHarness.run_device_collect)
        for required in (
            "DeviceCollectRecorder",
            "LegTimeoutPolicy",
            "BootLegCapture",
            "assert_collect_destructive_bounds",
            "require_collect_precondition",
            "decide_device_boot_observation",
            "check_boot_exit",
            "read_attestation_signal",
            "_boot_image_once",
            "_read_on_image_grubenv_strict",
            "_stamp_and_gate_on_image_strict",
            "shipped_update_authority",
            "_launcher_boot",
            "observe_loop_attached_device",
            "run_file_cross_check",
            "run_envelope_device",
            "_loop_detach_checked",
            "build_device_collect_diagnostics",
            "write_device_collect_diagnostics",
            "DEVICE_T7_DEVRUN3_COLLECT",
        ):
            self.assertIn(required, collect_body)
        text = Path(module.__file__).read_text(encoding="utf-8")
        self.assertNotIn("simulate_reboot(", text)
        self.assertNotIn("FakeGrubBackend", text)

    def test_collect_leg_order_covers_8_legs_plus_2_bindings(self) -> None:
        self.assertEqual(len(COLLECT_LEG_ORDER), 10)
        for leg in LIFECYCLE_SEQUENCE:
            self.assertIn(leg, COLLECT_LEG_ORDER)
        self.assertIn("post-run-loop-cross-check", COLLECT_LEG_ORDER)
        self.assertIn("devproof-device-envelope", COLLECT_LEG_ORDER)

    def test_abort_boundary_declared_explicitly(self) -> None:
        self.assertIn("teardown-loop-detach-safety", COLLECT_ABORT_GATES)
        self.assertIn("destructive-bound-violation", COLLECT_ABORT_GATES)
        for gate in ("require_device_host", "clean-exit-gate",
                     "consumption-predicate", "attestation-binding"):
            self.assertIn(gate, COLLECT_OBSERVED_GATES)
        self.assertTrue(COLLECT_ABORT_GATES.isdisjoint(COLLECT_OBSERVED_GATES))
        for gate in COLLECT_OBSERVED_GATES:
            self.assertIn(gate, COLLECT_FROZEN_PREDICATES)

    def test_no_image_carve_out_declared(self) -> None:
        rules = list(COLLECT_CONTINUATION_RULES)
        self.assertTrue(
            any("no-image" in rule for rule in rules),
            "continuation rules must carve out the no-image fail-closed return",
        )


class BootLegCaptureForwardingTests(unittest.TestCase):
    """D1: boot-leg REDs forward live evidence via the production capture.

    Uses the real production ``BootLegCapture.to_context`` — the same
    method ``run_device_collect`` wires into every boot-leg recorder
    context — with a run closure that populates the capture
    progressively (pre → boot → post → elapsed) exactly as
    ``_collect_boot_leg`` does, then REDs under the frozen
    consumption predicate. A red regression here means the failure
    path dropped live boot evidence.
    """

    def _failing_boot_run(self, capture: BootLegCapture):  # type: ignore[no-untyped-def]
        def _run() -> object:
            capture.pre = {"one_shot_slot": "B", "default_slot": "A"}
            capture.boot = {
                "returncode": 0,
                "serial_log": "/out/device-boot-B-commit-serial.log",
                "qemu_log": "/out/device-boot-B-commit-qemu.log",
                "serial_bytes": 512,
                "serial_growth_bytes": 512,
                "image_sha256_pre": "ab" * 32,
                "image_sha256_post": "cd" * 32,
            }
            capture.post = {"one_shot_slot": "B", "default_slot": "A"}
            capture.elapsed_seconds = 42.5
            capture.clean_exit = False
            return decide_device_boot_observation(
                leg="boot-B-commit",
                pre={"one_shot_slot": "B", "default_slot": "A"},
                post={"one_shot_slot": "B", "default_slot": "A"},
            )

        return _run

    def test_boot_red_forwards_live_evidence_through_production_capture(self) -> None:
        policy = LegTimeoutPolicy(timeout_seconds=300)
        capture = BootLegCapture()
        recorder = DeviceCollectRecorder()
        verdict = run_collect_sequence(
            [{
                "leg": "boot-B-commit",
                "gate": "consumption-predicate",
                "frozen_predicate": COLLECT_FROZEN_PREDICATES["consumption-predicate"],
                "run": self._failing_boot_run(capture),
                "context": lambda: capture.to_context(
                    machine=None, image=None, policy=policy),
            }],
            recorder,
        )
        self.assertFalse(verdict["ok"])
        self.assertEqual(verdict["red_count"], 1)
        red = recorder.reds[0]
        # Live boot evidence forwarded, not None.
        self.assertEqual(red["returncode"], 0)
        self.assertEqual(red["serial_growth_bytes"], 512)
        self.assertEqual(
            red["qemu_log"], "/out/device-boot-B-commit-qemu.log")
        self.assertEqual(
            red["on_image_pre"], {"one_shot_slot": "B", "default_slot": "A"})
        self.assertEqual(
            red["on_image_post"], {"one_shot_slot": "B", "default_slot": "A"})
        self.assertEqual(red["image_sha256_pre"], "ab" * 32)
        self.assertEqual(red["image_sha256_post"], "cd" * 32)
        # Real elapsed forwarded into the timeout detail.
        timeout = red["timeout"]
        assert isinstance(timeout, dict)
        self.assertEqual(timeout["elapsed_seconds"], 42.5)
        self.assertIn("42.5s", str(timeout["detail"]))
        # Frozen predicate kept verbatim.
        self.assertIn("armed-but-unconsumed", red["error"])
        artifact = build_device_collect_diagnostics(recorder, run_meta={})
        self.assertEqual(artifact["reds"][0]["returncode"], 0)
        self.assertEqual(
            artifact["reds"][0]["on_image_post"],
            {"one_shot_slot": "B", "default_slot": "A"})

    def test_partial_capture_records_what_exists_without_synthesis(self) -> None:
        policy = LegTimeoutPolicy(timeout_seconds=300)
        capture = BootLegCapture()
        capture.pre = {"one_shot_slot": "B", "default_slot": "A"}
        capture.elapsed_seconds = 5.0
        context = capture.to_context(machine=None, image=None, policy=policy)
        self.assertEqual(
            context["on_image_pre"], {"one_shot_slot": "B", "default_slot": "A"})
        self.assertIsNone(context.get("returncode"))
        self.assertIsNone(context.get("on_image_post"))


class CollectPreconditionTests(unittest.TestCase):
    """D2: missing preconditions RED under frozen predicates, never asserts."""

    def test_missing_precondition_raises_frozen_red(self) -> None:
        with self.assertRaises(LifecycleHarnessError) as caught:
            require_collect_precondition(
                None,
                message=("shipped stage precondition absent for boot-B-commit: "
                         "stage-B-one-shot did not establish the shipped endpoint"),
            )
        self.assertIn("shipped stage precondition absent", str(caught.exception))
        with self.assertRaises(AssertionError):
            raise AssertionError("sentinel")
        # The helper never raises AssertionError/IndexError.
        try:
            require_collect_precondition(None, message="frozen wording")
        except AssertionError:
            self.fail("precondition helper must not raise AssertionError")
        except LifecycleHarnessError:
            pass

    def test_cascade_records_frozen_red_and_continues(self) -> None:
        calls: list[str] = []
        recorder = DeviceCollectRecorder()

        def _red_stage() -> object:
            calls.append("stage")
            raise LifecycleHarnessError("shipped stage leg did not report STAGED")

        def _next_leg() -> object:
            calls.append("next")
            require_collect_precondition(
                None,
                message=("shipped stage precondition absent for boot-B-commit: "
                         "stage-B-one-shot did not establish the shipped endpoint"),
            )
            return "unreachable"

        verdict = run_collect_sequence(
            [
                {"leg": "stage-B-one-shot", "gate": "device_gate_for_image",
                 "frozen_predicate": "shipped stage", "run": _red_stage},
                {"leg": "boot-B-commit", "gate": "consumption-predicate",
                 "frozen_predicate": COLLECT_FROZEN_PREDICATES["consumption-predicate"],
                 "run": _next_leg},
            ],
            recorder,
        )
        self.assertFalse(verdict["ok"])
        self.assertEqual(calls, ["stage", "next"])
        self.assertEqual(len(recorder.reds), 2)
        self.assertEqual(
            recorder.reds[1]["error_type"], "LifecycleHarnessError")
        self.assertIn("shipped stage precondition absent",
                      recorder.reds[1]["error"])


class CollectDestructiveBoundTests(unittest.TestCase):
    """D3: destructive-bound violations abort fail-closed, never collected."""

    def test_non_absolute_output_aborts(self) -> None:
        with self.assertRaises(CollectAbortError) as caught:
            assert_collect_destructive_bounds(Path("relative/out"))
        self.assertIn("destructive-bound-violation", str(caught.exception))

    def test_image_escaping_output_aborts(self) -> None:
        with self.assertRaises(CollectAbortError):
            assert_collect_destructive_bounds(
                Path("/out"), Path("/elsewhere/evil.img"))

    def test_image_inside_output_passes(self) -> None:
        assert_collect_destructive_bounds(
            Path("/out"), Path("/out/greia-lifecycle-test.img"))

    def test_destructive_bound_abort_stops_collection(self) -> None:
        calls: list[str] = []
        recorder = DeviceCollectRecorder()

        def _violation() -> object:
            calls.append("violation")
            raise CollectAbortError(
                "destructive-bound-violation: collect image escapes the "
                "disposable output dir; aborting fail closed")

        legs = [
            {"leg": "collect-setup-image", "gate": "device_gate_for_image",
             "frozen_predicate": "frozen", "run": _violation},
            {"leg": "boot-A-accepted", "gate": "consumption-predicate",
             "frozen_predicate": "frozen",
             "run": lambda: calls.append("never") or "never"},
        ]
        with self.assertRaises(CollectAbortError):
            run_collect_sequence(legs, recorder)
        self.assertEqual(calls, ["violation"])
        self.assertTrue(recorder.abort is not None)


# ---------------------------------------------------------------------------
# DIAG-C2-SENSITIVITY: control-sensitivity proof under collect mode.
#
# Preregistered acceptance (frozen before observation; see the task brief):
#  P1. Every inventoried control below demonstrates RED under collect mode:
#      the break calls the real production predicate (never an unrelated
#      syntax/setup failure); the RED is recorded through the real
#      DeviceCollectRecorder / run_collect_sequence /
#      build_device_collect_diagnostics path with its gate named, the
#      verbatim fail-fast error preserved, and per-red evidence attached.
#  P2. After restore, the same predicate observes GREEN (direct call plus
#      a green collect verdict), proving the RED/GREEN flip tracks the
#      production mechanism rather than the harness.
#  P3. A multi-control run with >=2 simultaneous breaks still lists each
#      RED individually (leg + gate + evidence) in the aggregated verdict.
#  P4. No frozen predicate is weakened, waived, narrowed, or proxied to
#      make a cycle pass. Interpretation rule: a red required predicate
#      stays red and is escalated, never laundered into PASS.
# ---------------------------------------------------------------------------

#: Explicit DIAG-C2 positive-control inventory: each row names the control,
#: the production surface that owns the predicate, the gate under which the
#: collect-mode RED must appear, and the break mechanism. The brief-minimum
#: families are all present: report rejection (out-of-order / movement-free
#: / leg-bypassed), image gate (payload-less / tampered / chain-less),
#: clean-exit gate, consumption predicate on armed legs, shipped-leg bypass,
#: launcher-leg bypass, loop/cross-check binding, devproof envelope RED
#: propagation.
DIAG_C2_SENSITIVITY_CONTROL_INVENTORY = (
    ("LC-ORDER", "assert_lifecycle_transitions",
     "lifecycle-report-contract",
     "swap the first two lifecycle steps (out-of-order report)"),
    ("LC-NOMOVE", "assert_lifecycle_transitions",
     "lifecycle-report-contract",
     "freeze every default_slot to A (movement-free report)"),
    ("LC-SHIP", "assert_lifecycle_transitions",
     "lifecycle-report-contract",
     "truncate shipped_update_legs (shipped-leg bypass)"),
    ("LC-LAUNCH", "assert_lifecycle_transitions",
     "lifecycle-report-contract",
     "empty launcher_acceptance_legs (launcher-leg bypass)"),
    ("IMG-PAYLOAD", "device_gate_for_image -> assert_payload_present",
     "device_gate_for_image",
     "zero the sector-2047 descriptor (payload-less image)"),
    ("IMG-TAMPER", "device_gate_for_image -> read_payload_descriptor",
     "device_gate_for_image",
     "non-hex hash bytes in the descriptor (tampered image)"),
    ("IMG-CHAIN", "device_gate_for_image -> verify_boot_chain_present",
     "device_gate_for_image",
     "zero the MBR boot-code bytes (chain-less image)"),
    ("EXIT-CLEAN", "check_boot_exit",
     "clean-exit-gate",
     "nonzero QEMU returncode with a real log file"),
    ("CONSUME-N2", "decide_device_boot_observation",
     "consumption-predicate",
     "pre-armed one-shot still present post-boot (armed-but-unconsumed)"),
    ("CONSUME-N1", "decide_device_boot_observation",
     "consumption-predicate",
     "no staged one-shot for the armed target "
     "(same-disk reboot without transitions)"),
    ("LOOP-BIND", "observe_loop_attached_device",
     "post-run-loop-attach-partition-rescan",
     "empty partition probes across all bounded retries "
     "(persistent absence, never synthesized green)"),
    ("ENVELOPE", "run_envelope_device <- cgroup_gate_report",
     "devproof-device-envelope",
     "cgroup peak at/above the 768 MiB ceiling (envelope gate RED)"),
)

_REPORT_CONTRACT_GATE = "lifecycle-report-contract"
_REPORT_CONTRACT_PREDICATE = (
    "8-step order plus slot movement plus shipped/launcher-leg binding "
    "(assert_lifecycle_transitions)"
)


class DiagC2InventoryTests(unittest.TestCase):
    def test_inventory_covers_every_brief_minimum_family(self) -> None:
        by_id = {row[0]: row for row in DIAG_C2_SENSITIVITY_CONTROL_INVENTORY}
        self.assertEqual(len(by_id), 12)
        for required in (
            "LC-ORDER", "LC-NOMOVE", "LC-SHIP", "LC-LAUNCH",
            "IMG-PAYLOAD", "IMG-TAMPER", "IMG-CHAIN",
            "EXIT-CLEAN", "CONSUME-N2", "CONSUME-N1",
            "LOOP-BIND", "ENVELOPE",
        ):
            self.assertIn(required, by_id)
        for control_id, surface, gate, mechanism in (
            DIAG_C2_SENSITIVITY_CONTROL_INVENTORY
        ):
            self.assertTrue(control_id)
            self.assertTrue(surface)
            self.assertTrue(gate)
            self.assertTrue(mechanism)


@unittest.skipUnless(HAS_CRYPTOGRAPHY, "real lifecycle report needs cryptography")
class DiagC2ReportContractSensitivityTests(unittest.TestCase):
    """LC-ORDER/LC-NOMOVE/LC-SHIP/LC-LAUNCH under collect mode.

    One real source-scope report supplies valid order/movement/legs; each
    leg tampers exactly one axis and REDs through the real collect
    recorder. The aggregated verdict must name every RED individually
    with the report-contract gate; the intact report stays GREEN.
    """

    def test_report_contract_breaks_red_individually_and_restore_green(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            intact = _harness(tmp).run_source_scope()
            assert_lifecycle_transitions(intact)

            def _tampered(mutate):  # type: ignore[no-untyped-def]
                copy = json.loads(json.dumps(intact))
                mutate(copy)
                return copy

            names = [s["step"] for s in intact["steps"]]
            swapped = list(names)
            swapped[0], swapped[1] = swapped[1], swapped[0]
            order_broken = _tampered(
                lambda rep: rep.__setitem__(
                    "steps",
                    [dict(s, step=name)
                     for s, name in zip(rep["steps"], swapped)],
                )
            )
            nomove_broken = _tampered(
                lambda rep: [s.__setitem__("default_slot", "A")
                             for s in rep["steps"]],
            )
            ship_broken = _tampered(
                lambda rep: rep.__setitem__(
                    "shipped_update_legs", ["stage-B-one-shot"])
            )
            launch_broken = _tampered(
                lambda rep: rep.__setitem__("launcher_acceptance_legs", [])
            )
            cases = [
                ("report-out-of-order", order_broken, "out of contract"),
                ("report-movement-free", nomove_broken, "no slot movement"),
                ("report-shipped-bypass", ship_broken, "bypassed the constructor"),
                ("report-launcher-bypass", launch_broken, "bypassed acceptance"),
            ]
            # Fail-fast REDs first: each break trips the frozen predicate
            # for its own reason (never a shared syntax failure).
            fail_fast_errors = {}
            for leg, broken, marker in cases:
                with self.assertRaises(LifecycleContractError) as caught:
                    assert_lifecycle_transitions(broken)
                self.assertIn(marker, str(caught.exception))
                fail_fast_errors[leg] = str(caught.exception)

            legs = []
            for leg, broken, _marker in cases:
                step_names = [s["step"] for s in broken["steps"]]
                legs.append({
                    "leg": leg,
                    "gate": _REPORT_CONTRACT_GATE,
                    "frozen_predicate": _REPORT_CONTRACT_PREDICATE,
                    "run": (lambda b=broken: assert_lifecycle_transitions(b)),
                    "context": (lambda n=step_names: {
                        "disk_snapshot": {"report_step_names": list(n)},
                    }),
                })
            recorder = DeviceCollectRecorder()
            verdict = run_collect_sequence(legs, recorder)
            self.assertFalse(verdict["ok"])
            self.assertEqual(verdict["red_count"], 4)
            self.assertEqual(
                verdict["legs_attempted"], [leg for leg, _, _ in cases])
            by_leg = {red["leg"]: red for red in recorder.reds}
            for leg, broken, marker in cases:
                red = by_leg[leg]
                self.assertEqual(red["gate"], _REPORT_CONTRACT_GATE)
                self.assertEqual(red["error_type"], "LifecycleContractError")
                # Verbatim fail-fast error: collect mode neither swallows
                # nor rewords the RED.
                self.assertEqual(red["error"], fail_fast_errors[leg])
                self.assertIn(marker, red["error"])
                self.assertFalse(red["abort"])
                disk = red["disk_snapshot"]
                assert isinstance(disk, dict)
                self.assertEqual(
                    disk["report_step_names"],
                    [s["step"] for s in broken["steps"]],
                )
            artifact = build_device_collect_diagnostics(
                recorder, run_meta={"diag-c2": "report-contract"})
            self.assertFalse(artifact["verdict"]["ok"])
            self.assertEqual(len(artifact["reds"]), 4)
            for red in artifact["reds"]:
                self.assertEqual(red["gate"], _REPORT_CONTRACT_GATE)

            # RESTORE: the intact report passes direct and collects GREEN.
            assert_lifecycle_transitions(intact)
            restored = DeviceCollectRecorder()
            restored_verdict = run_collect_sequence(
                [{
                    "leg": "report-intact",
                    "gate": _REPORT_CONTRACT_GATE,
                    "frozen_predicate": _REPORT_CONTRACT_PREDICATE,
                    "run": lambda: assert_lifecycle_transitions(intact),
                }],
                restored,
            )
            self.assertTrue(restored_verdict["ok"])
            self.assertEqual(restored_verdict["red_count"], 0)


class DiagC2ImageGateSensitivityTests(unittest.TestCase):
    """IMG-PAYLOAD/IMG-TAMPER/IMG-CHAIN under collect mode.

    A single assembled disposable image is broken along exactly one axis
    at a time through the real ``device_gate_for_image`` (payload plus
    sector-gap plus boot-chain), REDs under collect with the image-gate
    gate, then byte-restored to GREEN. Each break targets the claimed
    mechanism; the restore re-proves the exact pre-break bytes.
    """

    def test_image_gate_breaks_red_under_collect_and_restore_green(self) -> None:
        from tools.x8_qemu.bootchain import MBR_BOOT_CODE_SIZE
        from tools.x8_qemu.payload import DESCRIPTOR_OFFSET

        with tempfile.TemporaryDirectory() as tmp:
            from tools.x8_qemu.lifecycle import (
                assemble_disposable_image,
                device_gate_for_image,
            )

            manifest = assemble_disposable_image(Path(tmp) / "out")
            image = Path(manifest["image"])
            # GREEN baseline through the production gate.
            device_gate_for_image(image)

            with open(image, "rb") as handle:
                handle.seek(DESCRIPTOR_OFFSET)
                intact_descriptor = handle.read(512)
            with open(image, "rb") as handle:
                intact_sector0 = handle.read(512)

            def _break_payload() -> None:
                with open(image, "r+b") as handle:
                    handle.seek(DESCRIPTOR_OFFSET)
                    handle.write(b"\x00" * 512)
                device_gate_for_image(image)

            def _break_tamper() -> None:
                with open(image, "r+b") as handle:
                    handle.seek(DESCRIPTOR_OFFSET + 9)
                    handle.write(b"*" * 64)
                device_gate_for_image(image)

            def _break_chain() -> None:
                with open(image, "r+b") as handle:
                    handle.seek(0)
                    handle.write(b"\x00" * MBR_BOOT_CODE_SIZE)
                device_gate_for_image(image)

            def _restore() -> None:
                with open(image, "r+b") as handle:
                    handle.seek(DESCRIPTOR_OFFSET)
                    handle.write(intact_descriptor)
                    handle.seek(0)
                    handle.write(intact_sector0)
                device_gate_for_image(image)

            breaks = [
                ("image-payload-less", _break_payload, "PayloadError"),
                ("image-tampered-hash", _break_tamper, "PayloadError"),
                ("image-chain-less", _break_chain, "BootchainError"),
            ]
            for leg, break_fn, error_type in breaks:
                # Fail-fast RED through the production gate.
                with self.assertRaises(Exception) as caught:
                    break_fn()
                self.assertEqual(type(caught.exception).__name__, error_type)
                fail_fast_error = str(caught.exception)

                # Collect-mode RED with the image-gate gate and evidence.
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
                            "disk_snapshot": {"image": str(image)},
                        },
                    }],
                    recorder,
                )
                self.assertFalse(verdict["ok"])
                self.assertEqual(verdict["red_count"], 1)
                red = recorder.reds[0]
                self.assertEqual(red["gate"], "device_gate_for_image")
                self.assertEqual(red["error_type"], error_type)
                self.assertEqual(red["error"], fail_fast_error)
                self.assertFalse(red["abort"])
                self.assertEqual(
                    red["image_sha256_pre"], manifest["image_sha256"])
                artifact = build_device_collect_diagnostics(
                    recorder, run_meta={"diag-c2": leg})
                self.assertFalse(artifact["verdict"]["ok"])
                self.assertEqual(
                    artifact["reds"][0]["gate"], "device_gate_for_image")

                # RESTORE the exact bytes and re-prove GREEN both ways.
                _restore()
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


class DiagC2ExitConsumptionSensitivityTests(unittest.TestCase):
    """EXIT-CLEAN/CONSUME-N2/CONSUME-N1 under collect mode.

    Each break calls its frozen predicate (clean-exit gate, consumption
    predicate); each RED appears individually with its gate and the
    verbatim fail-fast error; restores attest GREEN.
    """

    def test_exit_and_consumption_breaks_red_individually(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            log = Path(tmp) / "qemu.log"
            log.write_text("fake qemu log\n", encoding="utf-8")
            armed_pre = {"one_shot_slot": "B", "default_slot": "A"}
            armed_post = {"one_shot_slot": "B", "default_slot": "A"}
            bare_pre = {"one_shot_slot": None, "default_slot": "A"}
            bare_post = {"one_shot_slot": None, "default_slot": "A"}
            consumed_post = {"one_shot_slot": None, "default_slot": "A"}

            def _break_clean_exit() -> None:
                check_boot_exit(1, leg="boot-B-commit", qemu_log=log)

            def _break_armed_unconsumed() -> str:
                return decide_device_boot_observation(
                    leg="boot-B-commit", pre=armed_pre, post=armed_post)

            def _break_no_transition() -> str:
                return decide_device_boot_observation(
                    leg="boot-B-commit", pre=bare_pre, post=bare_post)

            cases = [
                ("boot-B-commit-clean-exit", _break_clean_exit,
                 "clean-exit-gate", "exited with status 1",
                 {"returncode": 1, "qemu_log": str(log)}),
                ("boot-B-commit-armed-unconsumed", _break_armed_unconsumed,
                 "consumption-predicate", "armed-but-unconsumed",
                 {"returncode": 0, "on_image_pre": dict(armed_pre),
                  "on_image_post": dict(armed_post)}),
                ("boot-B-commit-no-transition", _break_no_transition,
                 "consumption-predicate", "no staged transition",
                 {"returncode": 0, "on_image_pre": dict(bare_pre),
                  "on_image_post": dict(bare_post)}),
            ]
            fail_fast_errors = {}
            for leg, break_fn, _gate, _marker, _ctx in cases:
                with self.assertRaises(LifecycleHarnessError) as caught:
                    break_fn()
                fail_fast_errors[leg] = str(caught.exception)

            legs = [{
                "leg": leg,
                "gate": gate,
                "frozen_predicate": COLLECT_FROZEN_PREDICATES[gate],
                "run": break_fn,
                "context": (lambda c=ctx: dict(c)),
            } for leg, break_fn, gate, _marker, ctx in cases]
            recorder = DeviceCollectRecorder()
            verdict = run_collect_sequence(legs, recorder)
            self.assertFalse(verdict["ok"])
            self.assertEqual(verdict["red_count"], 3)
            by_leg = {red["leg"]: red for red in recorder.reds}
            for leg, _break_fn, gate, marker, ctx in cases:
                red = by_leg[leg]
                self.assertEqual(red["gate"], gate)
                self.assertEqual(red["error"], fail_fast_errors[leg])
                self.assertIn(marker, red["error"])
                self.assertFalse(red["abort"])
                for key, value in ctx.items():
                    self.assertEqual(red[key], value)
            artifact = build_device_collect_diagnostics(
                recorder, run_meta={"diag-c2": "exit-consumption"})
            self.assertEqual(artifact["verdict"]["red_count"], 3)

            # RESTORE: clean exit 0 plus consumed/plain attestation GREEN.
            check_boot_exit(0, leg="boot-B-commit", qemu_log=log)
            self.assertEqual(
                decide_device_boot_observation(
                    leg="boot-B-commit", pre=armed_pre,
                    post=consumed_post),
                "B",
            )
            self.assertEqual(
                decide_device_boot_observation(
                    leg="boot-A-accepted", pre=bare_pre, post=bare_post),
                "A",
            )
            green_recorder = DeviceCollectRecorder()
            green_verdict = run_collect_sequence(
                [
                    {"leg": "boot-B-commit-clean-exit",
                     "gate": "clean-exit-gate",
                     "frozen_predicate": COLLECT_FROZEN_PREDICATES[
                         "clean-exit-gate"],
                     "run": lambda: check_boot_exit(
                         0, leg="boot-B-commit", qemu_log=log)},
                    {"leg": "boot-B-commit-consumed",
                     "gate": "consumption-predicate",
                     "frozen_predicate": COLLECT_FROZEN_PREDICATES[
                         "consumption-predicate"],
                     "run": lambda: decide_device_boot_observation(
                         leg="boot-B-commit", pre=armed_pre,
                         post=consumed_post)},
                ],
                green_recorder,
            )
            self.assertTrue(green_verdict["ok"])


class DiagC2LoopBindingSensitivityTests(unittest.TestCase):
    """LOOP-BIND under collect mode, plus the cross-check binding rule.

    The loop-observation break (persistent probe absence) REDs through
    the real ``observe_loop_attached_device`` under the rescan gate and
    restores GREEN with healthy probes. The file cross-check half is
    proven RED-only: a mismatched binding trips the production
    executed-and-green rule and records under collect; executed-and-green
    GREEN on a capable host remains live-scope evidence (source scope
    cannot execute sfdisk/blkid here by design).
    """

    def test_loop_absence_reds_under_collect_and_restores_green(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            plan, record_path = _rescan_plan_and_record(tmp)

            def _break() -> object:
                events: list = []

                def _always_empty(command: object) -> object:
                    from greia_installer.layout import MbrCommandResult

                    argv = list(command)  # type: ignore[arg-type]
                    events.append(("probe", argv))
                    if ("-s" in argv and "PTUUID" in argv
                            and argv[-1] == "/dev/loop9"):
                        return MbrCommandResult(
                            stdout=_RESCAN_SIG, returncode=0)
                    return MbrCommandResult(stdout="", returncode=0)

                class _EmptyRunner:
                    def run(self, command: object) -> object:
                        return _always_empty(command)

                return observe_loop_attached_device(
                    Path("/dev/loop9"),
                    plan=plan,
                    record_path=record_path,
                    runner=_EmptyRunner(),
                    rescan_run=_fake_run_factory(events),
                    rescan_which=_fake_which_factory(
                        {"partprobe": True, "partx": False, "udevadm": True}
                    ),
                    max_attempts=3,
                    retry_settle_seconds=0,
                )

            with self.assertRaises(LifecycleHarnessError) as caught:
                _break()
            self.assertIn(LOOP_RESCAN_GATE, str(caught.exception))
            fail_fast_error = str(caught.exception)

            events: list = []
            recorder = DeviceCollectRecorder()
            verdict = run_collect_sequence(
                [{
                    "leg": "post-run-loop-cross-check",
                    "gate": LOOP_RESCAN_GATE,
                    "frozen_predicate": COLLECT_FROZEN_PREDICATES[
                        LOOP_RESCAN_GATE],
                    "run": _break,
                    "context": lambda: {
                        "disk_snapshot": {
                            "device": "/dev/loop9",
                            "max_attempts": LOOP_OBSERVE_MAX_ATTEMPTS,
                        },
                    },
                }],
                recorder,
            )
            self.assertFalse(verdict["ok"])
            self.assertEqual(verdict["red_count"], 1)
            red = recorder.reds[0]
            self.assertEqual(red["gate"], LOOP_RESCAN_GATE)
            self.assertEqual(red["error"], fail_fast_error)
            self.assertIn("no PARTUUID for /dev/loop9p2", red["error"])
            self.assertFalse(red["abort"])
            artifact = build_device_collect_diagnostics(
                recorder, run_meta={"diag-c2": "loop-bind"})
            self.assertEqual(artifact["reds"][0]["gate"], LOOP_RESCAN_GATE)
            self.assertEqual(events, [])

            # RESTORE: healthy probes observe GREEN direct and under collect.
            probe_events: list = []
            observed = observe_loop_attached_device(
                Path("/dev/loop9"),
                plan=plan,
                record_path=record_path,
                runner=_QueueProbeRunner(_green_answers(), probe_events),
                rescan_run=_fake_run_factory([]),
                rescan_which=_fake_which_factory({}),
                retry_settle_seconds=0,
            )
            self.assertTrue(observed["loop_attach_green"])
            green_recorder = DeviceCollectRecorder()
            green_verdict = run_collect_sequence(
                [{
                    "leg": "post-run-loop-cross-check",
                    "gate": LOOP_RESCAN_GATE,
                    "frozen_predicate": COLLECT_FROZEN_PREDICATES[
                        LOOP_RESCAN_GATE],
                    "run": lambda: observe_loop_attached_device(
                        Path("/dev/loop9"),
                        plan=plan,
                        record_path=record_path,
                        runner=_QueueProbeRunner(
                            _green_answers(), probe_events),
                        rescan_run=_fake_run_factory([]),
                        rescan_which=_fake_which_factory({}),
                        retry_settle_seconds=0,
                    ),
                }],
                green_recorder,
            )
            self.assertTrue(green_verdict["ok"])

    def test_cross_check_mismatch_reds_under_collect_binding(self) -> None:
        """Break (wrong signature) -> binding RED under collect.

        ``run_file_cross_check`` with a wrong expected signature is not
        executed-and-green on any host (mismatch where tools exist,
        explicit deferred elsewhere); the production binding rule
        ("file cross-check must execute and pass") therefore REDs, and
        that RED records under the post-run-loop-cross-check gate instead
        of laundering. Capable-host executed-and-green GREEN stays
        live-scope (unobserved in source scope by design).
        """
        with tempfile.TemporaryDirectory() as tmp:
            image = Path(tmp) / "disposable-mbr.img"
            image.write_bytes(b"\x00" * 4096)
            cross = run_file_cross_check(image, expected_signature="1a2b3c4d")
            self.assertFalse(cross["executed"] and cross["green"])

            def _binding() -> object:
                if not cross["executed"] or not cross["green"]:
                    raise LifecycleHarnessError(
                        "file cross-check must execute and pass "
                        "on a capable host"
                    )
                return cross

            with self.assertRaises(LifecycleHarnessError) as caught:
                _binding()
            fail_fast_error = str(caught.exception)

            recorder = DeviceCollectRecorder()
            verdict = run_collect_sequence(
                [{
                    "leg": "post-run-loop-cross-check",
                    "gate": "post-run-loop-cross-check",
                    "frozen_predicate": COLLECT_FROZEN_PREDICATES[
                        "post-run-loop-cross-check"],
                    "run": _binding,
                    "context": lambda: {
                        "disk_snapshot": {"cross_check": dict(cross)},
                    },
                }],
                recorder,
            )
            self.assertFalse(verdict["ok"])
            red = recorder.reds[0]
            self.assertEqual(red["gate"], "post-run-loop-cross-check")
            self.assertEqual(red["error"], fail_fast_error)
            artifact = build_device_collect_diagnostics(
                recorder, run_meta={"diag-c2": "cross-check"})
            self.assertFalse(artifact["verdict"]["ok"])

            # The enforcement lives in the production collect/device bodies,
            # not in this test: pin the wiring.
            import inspect as _inspect

            from tools.x8_qemu import lifecycle as module

            self.assertIn(
                "file cross-check must execute and pass",
                _inspect.getsource(module.LifecycleHarness.run_device_collect),
            )


class DiagC2EnvelopeSensitivityTests(unittest.TestCase):
    """ENVELOPE under collect mode.

    The cgroup-breach break trips the real ``cgroup_gate_report``
    predicate; the collect leg raises the production
    ``run_envelope_device`` RED wording ("device cgroup gate is RED") so
    the envelope RED propagates with its gate instead of laundering.
    Restore (headroom + swap off) gates GREEN. The live
    ``run_envelope_device`` GREEN on a capable host remains live-scope.
    """

    def test_envelope_cgroup_breach_reds_under_collect(self) -> None:
        from tools.x8_qemu.devproof import (
            CGROUP_CEILING_BYTES,
            GATE_PAYLOAD_BYTES,
            DevproofError,
            cgroup_gate_report,
        )

        breached = cgroup_gate_report(
            payload_bytes=GATE_PAYLOAD_BYTES,
            peak_bytes=CGROUP_CEILING_BYTES,
        )
        self.assertFalse(breached["green"])

        def _break() -> object:
            verdict = cgroup_gate_report(
                payload_bytes=GATE_PAYLOAD_BYTES,
                peak_bytes=CGROUP_CEILING_BYTES,
            )
            if not verdict["green"]:
                raise DevproofError("device cgroup gate is RED")
            return verdict

        with self.assertRaises(DevproofError) as caught:
            _break()
        fail_fast_error = str(caught.exception)

        recorder = DeviceCollectRecorder()
        verdict = run_collect_sequence(
            [{
                "leg": "devproof-device-envelope",
                "gate": "devproof-device-envelope",
                "frozen_predicate": COLLECT_FROZEN_PREDICATES[
                    "devproof-device-envelope"],
                "run": _break,
                "context": lambda: {
                    "disk_snapshot": {
                        "payload_bytes": GATE_PAYLOAD_BYTES,
                        "peak_bytes": CGROUP_CEILING_BYTES,
                        "ceiling_bytes": CGROUP_CEILING_BYTES,
                    },
                },
            }],
            recorder,
        )
        self.assertFalse(verdict["ok"])
        self.assertEqual(verdict["red_count"], 1)
        red = recorder.reds[0]
        self.assertEqual(red["gate"], "devproof-device-envelope")
        self.assertEqual(red["error_type"], "DevproofError")
        self.assertEqual(red["error"], fail_fast_error)
        self.assertFalse(red["abort"])
        artifact = build_device_collect_diagnostics(
            recorder, run_meta={"diag-c2": "envelope"})
        self.assertEqual(
            artifact["reds"][0]["gate"], "devproof-device-envelope")

        # RESTORE: headroom plus swap-off gates GREEN direct and collected.
        restored = cgroup_gate_report(
            payload_bytes=GATE_PAYLOAD_BYTES,
            peak_bytes=CGROUP_CEILING_BYTES - 1024,
            swap_off=True,
            require_swap_off=True,
        )
        self.assertTrue(restored["green"])
        green_recorder = DeviceCollectRecorder()
        green_verdict = run_collect_sequence(
            [{
                "leg": "devproof-device-envelope",
                "gate": "devproof-device-envelope",
                "frozen_predicate": COLLECT_FROZEN_PREDICATES[
                    "devproof-device-envelope"],
                "run": lambda: cgroup_gate_report(
                    payload_bytes=GATE_PAYLOAD_BYTES,
                    peak_bytes=CGROUP_CEILING_BYTES - 1024,
                    swap_off=True,
                    require_swap_off=True,
                ),
            }],
            green_recorder,
        )
        self.assertTrue(green_verdict["ok"])

    def test_envelope_device_fail_closed_propagates_red_under_collect(
        self,
    ) -> None:
        import sys as _sys

        if _sys.platform == "linux" and Path("/dev").exists():
            self.skipTest("device envelope gate is evaluated on Linux runs")
        with tempfile.TemporaryDirectory() as tmp:
            from tools.x8_qemu.devproof import run_envelope_device

            def _break() -> object:
                return run_envelope_device(Path(tmp) / "out")

            with self.assertRaises(Exception) as caught:
                _break()
            fail_fast_error = str(caught.exception)

            recorder = DeviceCollectRecorder()
            verdict = run_collect_sequence(
                [{
                    "leg": "devproof-device-envelope",
                    "gate": "devproof-device-envelope",
                    "frozen_predicate": COLLECT_FROZEN_PREDICATES[
                        "devproof-device-envelope"],
                    "run": _break,
                }],
                recorder,
            )
            self.assertFalse(verdict["ok"])
            self.assertEqual(verdict["red_count"], 1)
            red = recorder.reds[0]
            self.assertEqual(red["gate"], "devproof-device-envelope")
            self.assertEqual(red["error"], fail_fast_error)
            self.assertFalse(red["abort"])


class DiagC2MultiControlTests(unittest.TestCase):
    """P3: simultaneous breaks stay individually listed in one verdict."""

    def test_simultaneous_breaks_stay_individually_listed(self) -> None:
        from tools.x8_qemu.devproof import (
            CGROUP_CEILING_BYTES,
            GATE_PAYLOAD_BYTES,
            DevproofError,
            cgroup_gate_report,
        )

        names = list(LIFECYCLE_SEQUENCE)
        names[0], names[1] = names[1], names[0]
        order_broken = {
            "steps": [
                {"step": name,
                 "default_slot": ("A" if index % 2 == 0 else "B")}
                for index, name in enumerate(names)
            ],
            "shipped_update_legs": list(SHIPPED_UPDATE_LEGS),
            "launcher_acceptance_legs": list(LAUNCHER_ACCEPTANCE_LEGS),
        }
        with tempfile.TemporaryDirectory() as tmp:
            log = Path(tmp) / "qemu.log"
            log.write_text("fake qemu log\n", encoding="utf-8")

            def _break_order() -> None:
                assert_lifecycle_transitions(order_broken)

            def _break_armed_unconsumed() -> str:
                return decide_device_boot_observation(
                    leg="boot-B-commit",
                    pre={"one_shot_slot": "B", "default_slot": "A"},
                    post={"one_shot_slot": "B", "default_slot": "A"},
                )

            def _break_envelope() -> object:
                verdict = cgroup_gate_report(
                    payload_bytes=GATE_PAYLOAD_BYTES,
                    peak_bytes=CGROUP_CEILING_BYTES,
                )
                if not verdict["green"]:
                    raise DevproofError("device cgroup gate is RED")
                return verdict

            legs = [
                {"leg": "report-out-of-order",
                 "gate": _REPORT_CONTRACT_GATE,
                 "frozen_predicate": _REPORT_CONTRACT_PREDICATE,
                 "run": _break_order,
                 "context": lambda: {
                     "disk_snapshot": {"report_step_names": list(names)},
                 }},
                {"leg": "boot-B-commit",
                 "gate": "consumption-predicate",
                 "frozen_predicate": COLLECT_FROZEN_PREDICATES[
                     "consumption-predicate"],
                 "run": _break_armed_unconsumed,
                 "context": lambda: {
                     "on_image_pre": {"one_shot_slot": "B"},
                     "on_image_post": {"one_shot_slot": "B"},
                 }},
                {"leg": "devproof-device-envelope",
                 "gate": "devproof-device-envelope",
                 "frozen_predicate": COLLECT_FROZEN_PREDICATES[
                     "devproof-device-envelope"],
                 "run": _break_envelope,
                 "context": lambda: {
                     "disk_snapshot": {
                         "payload_bytes": GATE_PAYLOAD_BYTES,
                         "peak_bytes": CGROUP_CEILING_BYTES,
                     },
                 }},
            ]
            recorder = DeviceCollectRecorder()
            verdict = run_collect_sequence(legs, recorder)
            self.assertFalse(verdict["ok"])
            self.assertEqual(verdict["red_count"], 3)
            self.assertEqual(
                verdict["legs_attempted"],
                ["report-out-of-order", "boot-B-commit",
                 "devproof-device-envelope"],
            )
            by_leg = {red["leg"]: red for red in recorder.reds}
            self.assertEqual(
                by_leg["report-out-of-order"]["gate"],
                _REPORT_CONTRACT_GATE)
            self.assertIn(
                "out of contract",
                by_leg["report-out-of-order"]["error"])
            self.assertEqual(
                by_leg["boot-B-commit"]["gate"], "consumption-predicate")
            self.assertIn(
                "armed-but-unconsumed", by_leg["boot-B-commit"]["error"])
            self.assertEqual(
                by_leg["devproof-device-envelope"]["gate"],
                "devproof-device-envelope")
            self.assertIn(
                "cgroup gate is RED",
                by_leg["devproof-device-envelope"]["error"])
            for red in recorder.reds:
                self.assertFalse(red["abort"])
                self.assertTrue(red["frozen_predicate"])
            artifact = build_device_collect_diagnostics(
                recorder, run_meta={"diag-c2": "multi-control"})
            self.assertEqual(artifact["verdict"]["red_count"], 3)
            self.assertEqual(len(artifact["reds"]), 3)
            self.assertEqual(
                [red["leg"] for red in artifact["reds"]],
                ["report-out-of-order", "boot-B-commit",
                 "devproof-device-envelope"],
            )


if __name__ == "__main__":
    unittest.main()
