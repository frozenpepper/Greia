"""P5.2 recovery/D31/reverse leg: broken-candidate recovery through real services.

Covers the brief without QEMU/loop/mount contact:

- the pinned unhealthy-candidate construction (remove the root
  health-capability issuer from a real slot rootfs; health-service-failure;
  180s deadline owned by boot_transaction) and its fail-closed bundle
  builder/verifier through the production system_updates owner;
- the source-scope D31 survival fold through the reused devproof fixture
  (semantic preservation through the store parse paths plus byte-identical
  persist bytes, no destructive repair);
- bounded no-ops (already-on-accepted boot, plain boot) and the healthy
  sensitivity control (a valid candidate is not falsely failed);
- the testable leg driver (phase order, observation-before-closure, D31
  and isolation proofs, assert_lifecycle_transitions closure) with
  break -> RED -> restore -> GREEN positive controls;
- the stage inspectors through the real GrubEnvBackend + journal;
- the capable-host entry stays BLOCKED on this host naming the facility.

No direct harness call substitutes for an installed service operation:
mark_candidate_unhealthy appears only in the labeled SOURCE_SCOPE folds
(trigger/D31 mechanism proof through the production owners); the leg
driver observes FAILED from injected authoritative observations and the
capable-host entry observes it from on-image journal bytes.
"""

from __future__ import annotations

import hashlib as _hashlib
import shutil as _shutil
import tempfile
import unittest
import zipfile as _zipfile
from pathlib import Path

from support_artifacts import valid_hardware_support_archive_bytes
from unittest import mock as _mock

from tools.x8_qemu import product as _product
from tools.x8_qemu.lifecycle import (
    LifecycleConfig,
    LifecycleHarnessError,
    assert_lifecycle_transitions,
)
from tools.x8_qemu.product import (
    RECOVERY_D31_REVERSE_LEG_PHASES,
    RECOVERY_D31_REVERSE_OBSERVED_STEPS,
    RECOVERY_D31_REVERSE_STAGES,
    RECOVERY_SHIPPED_UNITS,
    UNHEALTHY_CANDIDATE_MECHANISM,
    UNHEALTHY_CANDIDATE_RECOVERY_CLASS,
    UNHEALTHY_CANDIDATE_UNIT_NAME,
    ProductHarness,
    assert_persist_byte_identical,
    build_recovery_d31_reverse_lifecycle_report,
    build_unhealthy_candidate_bundle,
    describe_unhealthy_candidate_construction,
    inspect_recovery_postrecovery_roots,
    inspect_recovery_prefailure_roots,
    prove_recovery_noop_cases,
    record_shipped_recovery_units,
    run_d31_survival_fold,
    run_recovery_d31_reverse_leg,
    snapshot_persist_tree,
    verify_unhealthy_candidate_bundle,
)

import hermetic_volume


def setUpModule() -> None:
    hermetic_volume.install_for_module()


def _payload_bytes(size: int, tag: bytes) -> bytes:
    body = bytes((index * 31 + 7) % 256 for index in range(size))
    raw = tag + body[len(tag):]
    fixed = bytearray(raw)
    if fixed[510:512] == b"\x55\xaa":
        fixed[510:512] = b"\x00\x00"
    if fixed[512:520] == b"EFI PART":
        fixed[512:520] = b"\x00" * 8
    return bytes(fixed)


def _base_inputs(work: Path) -> dict[str, object]:
    Path(work).mkdir(parents=True, exist_ok=True)
    payload = Path(work) / "base-payload.img"
    payload.write_bytes(_payload_bytes(64 * 1024, b"recovery-base:"))
    hw = work / "hw.tar.zst"
    hw.write_bytes(
        valid_hardware_support_archive_bytes(architecture="x86-64")
    )
    return {
        "payload": payload,
        "hw": hw,
    }


def _recording_mount_fixture(calls: list[str], with_unit: bool = True):
    """Fake loop/mount fns proving order on real file bytes (no loop).

    The fake mount materializes a real fixture tree carrying the pinned
    issuer unit; the builder's real deletion then genuinely removes it.
    A real loop mount would mutate the image bytes as a result; the fake
    unmount appends an explicitly labeled stand-in trailer to the work
    payload copy only after verifying that deletion really happened, so
    the builder's pre/post inequality is exercised without claiming a
    real filesystem mutation. The with_unit=False arm produces no
    trailer (the builder must refuse before the post check).
    """
    state: dict[str, object] = {"mnt": None, "materialized": False}

    def attach(image: Path) -> str:
        calls.append("attach")
        state["image"] = Path(image)
        return "/dev/fake-loop0"

    def mount(node: str, mnt: Path, read_only: bool = False) -> None:
        calls.append(f"mount:{node}:ro={read_only}")
        assert read_only is False
        state["mnt"] = Path(mnt)
        unit = Path(mnt) / "etc/systemd/system" / UNHEALTHY_CANDIDATE_UNIT_NAME
        if with_unit:
            unit.parent.mkdir(parents=True, exist_ok=True)
            unit.write_text("[Unit]\nDescription=fake issuer\n", encoding="utf-8")
            wants = Path(mnt) / "etc/systemd/system/multi-user.target.wants"
            wants.mkdir(parents=True, exist_ok=True)
            try:
                (wants / UNHEALTHY_CANDIDATE_UNIT_NAME).symlink_to(
                    f"../{UNHEALTHY_CANDIDATE_UNIT_NAME}"
                )
            except OSError:
                (wants / UNHEALTHY_CANDIDATE_UNIT_NAME).write_text(
                    "[Unit]\n", encoding="utf-8"
                )
            state["materialized"] = True

    def unmount(mnt: Path) -> None:
        calls.append("unmount")
        if state.get("materialized"):
            unit = Path(mnt) / "etc/systemd/system" / UNHEALTHY_CANDIDATE_UNIT_NAME
            assert not unit.exists() and not unit.is_symlink(), (
                "fake-mount stand-in refused: pinned unit was not really deleted"
            )
            image = state.get("image")
            assert isinstance(image, Path)
            with image.open("ab") as handle:
                handle.write(b"\n# fake-mount image-mutation stand-in\n")

    def detach(loopdev: str, runner=None) -> None:
        calls.append(f"detach:{loopdev}")

    return attach, mount, unmount, detach


def _build_candidate(work: Path, **overrides) -> tuple[dict[str, object], list[str]]:
    inputs = _base_inputs(work)
    calls: list[str] = []
    attach, mount, unmount, detach = _recording_mount_fixture(calls)
    params: dict[str, object] = {
        "base_payload": inputs["payload"],
        "base_hardware_support": inputs["hw"],
        "output_path": work / "unhealthy.greiaupdate",
        "work_dir": work / "candidate-work",
        "release_id": "greia-0.21.1",
        "platform_family": "legacy-x86",
        "architecture": "i386",
        "profile": "legacy-x86-i686",
        "attach_fn": attach,
        "mount_fn": mount,
        "unmount_fn": unmount,
        "detach_fn": detach,
    }
    params.update(overrides)
    result = build_unhealthy_candidate_bundle(**params)  # type: ignore[arg-type]
    return result, calls


def _good_observations() -> dict[str, dict[str, object]]:
    return {
        "stage-broken-candidate": {
            "journal_state": "one_shot_armed",
            "candidate_slot": "A",
        },
        "boot-broken-candidate": {
            "last_booted": "A",
            "journal_state": "candidate_booting",
            "default_slot": "B",
        },
        "recovery-boot-accepted": {
            "journal_state": "failed",
            "journal_note": "recovery:health-service-failure:automatic-reboot:t",
            "last_booted": "B",
            "default_slot": "B",
            "accepted_release_id": "greia-0.21.0",
        },
        "reverse-update-accepted": {
            "journal_state": "accepted",
            "default_slot": "A",
            "accepted_release_id": "greia-0.22.0",
            "committed_slot": "A",
            "last_booted": "A",
        },
    }


def _good_d31() -> dict[str, object]:
    from tools.x8_qemu.devproof import (
        read_d31_representative_state,
        write_d31_representative_state,
    )

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp) / "persist"
        before = write_d31_representative_state(root)
        baseline = read_d31_representative_state(root)
        before_bytes = snapshot_persist_tree(root)
        after = read_d31_representative_state(root)
        after_bytes = snapshot_persist_tree(root)
    return {
        "semantic_before": dict(before),
        "semantic_after": dict(after),
        "_baseline": dict(baseline),
        "bytes_before": dict(before_bytes),
        "bytes_after": dict(after_bytes),
    }


def _hex64(value: str) -> str:
    return _hashlib.sha256(value.encode()).hexdigest()


def _run_leg(**overrides) -> dict[str, object]:
    observations = _good_observations()
    d31 = _good_d31()
    seen: list[str] = []
    digests = {
        ("B", "before"): _hex64("b-before"),
        ("A", "before"): _hex64("a-before"),
        ("B", "after"): _hex64("b-before"),
        ("A", "after"): _hex64("a-after"),
    }
    params: dict[str, object] = {
        "accepted_slot": "B",
        "candidate_slot": "A",
        "accepted_release_id": "greia-0.21.0",
        "candidate_release_id": "greia-0.21.1",
        "reverse_release_id": "greia-0.22.0",
        "boot_fn": seen.append,
        "observe_fn": lambda stage: dict(observations[stage]),
        "d31_fn": lambda: {
            "semantic_before": d31["semantic_before"],
            "semantic_after": d31["semantic_after"],
            "bytes_before": d31["bytes_before"],
            "bytes_after": d31["bytes_after"],
        },
        "slot_digest_fn": lambda slot, when: digests[(slot, when)],
    }
    params.update(overrides)
    result = run_recovery_d31_reverse_leg(**params)  # type: ignore[arg-type]
    result["_seen_phases"] = seen
    return result


class ConstructionPinTests(unittest.TestCase):
    def test_construction_pins_mechanism_and_deadline(self) -> None:
        from greia_platform.boot_transaction import (
            CANDIDATE_HEALTH_DEADLINE_SEC,
            CANDIDATE_RECOVERY_SERVICE,
            CANDIDATE_RECOVERY_TIMER,
        )

        pinned = describe_unhealthy_candidate_construction()
        self.assertEqual(pinned["mechanism"], UNHEALTHY_CANDIDATE_MECHANISM)
        self.assertEqual(
            pinned["recovery_class"], UNHEALTHY_CANDIDATE_RECOVERY_CLASS
        )
        self.assertEqual(pinned["removed_unit"], UNHEALTHY_CANDIDATE_UNIT_NAME)
        self.assertIn(
            "etc/systemd/system/greia-boot-health-credential.service",
            pinned["removed_unit_paths"],  # type: ignore[operator]
        )
        self.assertEqual(pinned["deadline_sec"], 180)
        self.assertEqual(pinned["deadline_sec"], CANDIDATE_HEALTH_DEADLINE_SEC)
        self.assertEqual(pinned["timer"], CANDIDATE_RECOVERY_TIMER)
        self.assertEqual(pinned["service"], CANDIDATE_RECOVERY_SERVICE)

    def test_leg_phases_reuse_bounded_control_vocabulary(self) -> None:
        from tools.x8_qemu.product import CONTROL_PHASES

        for phase in RECOVERY_D31_REVERSE_LEG_PHASES:
            self.assertIn(phase, CONTROL_PHASES)
        # First update-stage round stages the unhealthy candidate, the
        # second round stages the reverse release.
        self.assertEqual(
            RECOVERY_D31_REVERSE_LEG_PHASES.count("update-stage"), 2
        )
        self.assertEqual(
            list(RECOVERY_D31_REVERSE_STAGES),
            [
                "stage-broken-candidate",
                "boot-broken-candidate",
                "recovery-boot-accepted",
                "reverse-update-accepted",
            ],
        )
        self.assertEqual(
            list(RECOVERY_D31_REVERSE_OBSERVED_STEPS),
            [
                "stage-broken-candidate",
                "boot-broken-candidate",
                "recovery-boot-B",
                "reverse-update-B-to-A",
            ],
        )

    def test_shipped_recovery_units_recorded(self) -> None:
        recorded = record_shipped_recovery_units()
        self.assertEqual(set(recorded["sha256"]), set(RECOVERY_SHIPPED_UNITS))  # type: ignore[index]
        for name in RECOVERY_SHIPPED_UNITS:
            digest = recorded["sha256"][name]  # type: ignore[index]
            self.assertRegex(digest, r"^[0-9a-f]{64}$")
        self.assertRegex(recorded["helper_sha256"], r"^[0-9a-f]{64}$")  # type: ignore[operator]

    def test_shipped_recovery_units_blocked_when_absent(self) -> None:
        with self.assertRaises(LifecycleHarnessError) as caught:
            record_shipped_recovery_units(project_root=Path("/nonexistent-root"))
        self.assertIn("BLOCKED", str(caught.exception))


class BuildUnhealthyBundleTests(unittest.TestCase):
    def test_build_records_pinned_mutation_in_order(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            work = Path(tmp)
            result, calls = _build_candidate(work)
            self.assertEqual(
                calls[0], "attach", f"attach must come first ({calls})"
            )
            self.assertTrue(calls[1].startswith("mount:/dev/fake-loop0"))
            self.assertIn("ro=False", calls[1])
            self.assertEqual(calls[-2:], ["unmount", "detach:/dev/fake-loop0"])
            self.assertEqual(result["mechanism"], UNHEALTHY_CANDIDATE_MECHANISM)
            self.assertIn(
                "etc/systemd/system/greia-boot-health-credential.service",
                result["removed_files"],  # type: ignore[operator]
            )
            self.assertIn(
                "etc/systemd/system/multi-user.target.wants/"
                "greia-boot-health-credential.service",
                result["removed_files"],  # type: ignore[operator]
            )
            self.assertNotEqual(
                result["payload_pre_sha256"], result["payload_post_sha256"]
            )
            self.assertEqual(result["release_id"], "greia-0.21.1")
            # Bundle manifest binds the compressed mutated payload bytes:
            # decompressing the archived member yields the staged raw image.
            import zstandard

            from greia_platform.system_updates import (
                PAYLOAD_NAME,
                inspect_update_bundle,
            )

            inspected = inspect_update_bundle(Path(str(result["bundle"])))
            with _zipfile.ZipFile(
                Path(str(result["bundle"])), "r"
            ) as archive:
                compressed = archive.read(PAYLOAD_NAME)
            self.assertEqual(
                inspected.manifest.payload_sha256,
                _hashlib.sha256(compressed).hexdigest(),
            )
            self.assertEqual(
                zstandard.ZstdDecompressor().decompress(compressed),
                (work / "candidate-work" / "unhealthy-candidate-payload.img").read_bytes(),
            )

    def test_base_payload_never_mutated(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            work = Path(tmp)
            inputs = _base_inputs(work)
            before = _hashlib.sha256(inputs["payload"].read_bytes()).hexdigest()  # type: ignore[union-attr]
            calls: list[str] = []
            attach, mount, unmount, detach = _recording_mount_fixture(calls)
            build_unhealthy_candidate_bundle(
                base_payload=inputs["payload"],  # type: ignore[arg-type]
                base_hardware_support=inputs["hw"],  # type: ignore[arg-type]
                output_path=work / "unhealthy.greiaupdate",
                work_dir=work / "candidate-work",
                release_id="greia-0.21.1",
                platform_family="legacy-x86",
                architecture="i386",
                profile="legacy-x86-i686",
                attach_fn=attach,
                mount_fn=mount,
                unmount_fn=unmount,
                detach_fn=detach,
            )
            self.assertEqual(
                _hashlib.sha256(inputs["payload"].read_bytes()).hexdigest(),  # type: ignore[union-attr]
                before,
            )

    def test_missing_base_is_blocked(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            work = Path(tmp)
            inputs = _base_inputs(work)
            with self.assertRaises(LifecycleHarnessError) as caught:
                build_unhealthy_candidate_bundle(
                    base_payload=work / "absent.img",
                    base_hardware_support=inputs["hw"],  # type: ignore[arg-type]
                    output_path=work / "unhealthy.greiaupdate",
                    work_dir=work / "candidate-work",
                    release_id="greia-0.21.1",
                    platform_family="legacy-x86",
                    architecture="i386",
                    profile="legacy-x86-i686",
                )
            self.assertIn("BLOCKED", str(caught.exception))

    def test_mbr_payload_is_red_not_synthesized(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            work = Path(tmp)
            inputs = _base_inputs(work)
            mbr = bytearray(_payload_bytes(64 * 1024, b"mbr:"))
            mbr[510:512] = b"\x55\xaa"
            bad = work / "mbr.img"
            bad.write_bytes(bytes(mbr))
            with self.assertRaises(LifecycleHarnessError) as caught:
                build_unhealthy_candidate_bundle(
                    base_payload=bad,
                    base_hardware_support=inputs["hw"],  # type: ignore[arg-type]
                    output_path=work / "unhealthy.greiaupdate",
                    work_dir=work / "candidate-work",
                    release_id="greia-0.21.1",
                    platform_family="legacy-x86",
                    architecture="i386",
                    profile="legacy-x86-i686",
                )
            self.assertNotIn("BLOCKED", str(caught.exception))
            self.assertIn("MBR", str(caught.exception))

    def test_base_without_issuer_is_red_genuine_mechanism(self) -> None:
        # Positive control counterpart: a base rootfs without the pinned
        # issuer cannot produce a genuine health failure -> RED.
        with tempfile.TemporaryDirectory() as tmp:
            work = Path(tmp)
            inputs = _base_inputs(work)
            calls: list[str] = []
            attach, mount, unmount, detach = _recording_mount_fixture(
                calls, with_unit=False
            )
            with self.assertRaises(LifecycleHarnessError) as caught:
                build_unhealthy_candidate_bundle(
                    base_payload=inputs["payload"],  # type: ignore[arg-type]
                    base_hardware_support=inputs["hw"],  # type: ignore[arg-type]
                    output_path=work / "unhealthy.greiaupdate",
                    work_dir=work / "candidate-work",
                    release_id="greia-0.21.1",
                    platform_family="legacy-x86",
                    architecture="i386",
                    profile="legacy-x86-i686",
                    attach_fn=attach,
                    mount_fn=mount,
                    unmount_fn=unmount,
                    detach_fn=detach,
                )
            self.assertIn("no pinned", str(caught.exception))


class VerifyBundleTests(unittest.TestCase):
    def test_verify_binds_manifest_then_break_restore(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            work = Path(tmp)
            result, _ = _build_candidate(work)
            bundle = Path(str(result["bundle"]))
            good = {
                "platform_family": "legacy-x86",
                "architecture": "i386",
                "profile": "legacy-x86-i686",
                "expected_hardware_sha256": str(result["hardware_support_sha256"]),
            }
            # GREEN: v3 inspection + compatibility bind the manifest.
            bound = verify_unhealthy_candidate_bundle(bundle, **good)  # type: ignore[arg-type]
            self.assertEqual(bound["compatibility"], "compatible")
            self.assertEqual(bound["release_id"], "greia-0.21.1")
            # Break: a tampered copy (payload digest mismatch) -> RED.
            tampered = work / "tampered.greiaupdate"
            with _zipfile.ZipFile(bundle, "r") as src:
                from greia_platform.system_updates import MANIFEST_NAME, PAYLOAD_NAME

                manifest_raw = src.read(MANIFEST_NAME)
                payload = bytearray(src.read(PAYLOAD_NAME))
            payload[10] ^= 0xFF
            with _zipfile.ZipFile(
                tampered, "w", compression=_zipfile.ZIP_STORED
            ) as dst:
                info = _zipfile.ZipInfo(
                    filename=MANIFEST_NAME, date_time=(1980, 1, 1, 0, 0, 0)
                )
                info.compress_type = _zipfile.ZIP_DEFLATED
                dst.writestr(info, manifest_raw)
                info2 = _zipfile.ZipInfo(
                    filename=PAYLOAD_NAME, date_time=(1980, 1, 1, 0, 0, 0)
                )
                info2.compress_type = _zipfile.ZIP_STORED
                dst.writestr(info2, bytes(payload))
            with self.assertRaises(LifecycleHarnessError) as caught:
                verify_unhealthy_candidate_bundle(tampered, **good)  # type: ignore[arg-type]
            self.assertIn("inspection", str(caught.exception).lower())
            # Restore: the intact bundle -> GREEN again.
            restored = verify_unhealthy_candidate_bundle(bundle, **good)  # type: ignore[arg-type]
            self.assertEqual(restored["compatibility"], "compatible")

    def test_verify_rejects_compat_profile_hw(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            work = Path(tmp)
            result, _ = _build_candidate(work)
            bundle = Path(str(result["bundle"]))
            good = {
                "platform_family": "legacy-x86",
                "architecture": "i386",
                "profile": "legacy-x86-i686",
                "expected_hardware_sha256": str(result["hardware_support_sha256"]),
            }
            for field, bad in (
                ("platform_family", "other-family"),
                ("architecture", "amd64"),
                ("profile", "other-profile"),
                ("expected_hardware_sha256", "00" * 32),
            ):
                params = dict(good)
                params[field] = bad
                with self.assertRaises(
                    LifecycleHarnessError, msg=f"field {field}={bad}"
                ):
                    verify_unhealthy_candidate_bundle(bundle, **params)  # type: ignore[arg-type]

    def test_verify_board_mismatch_is_red(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            work = Path(tmp)
            inputs = _base_inputs(work)
            calls: list[str] = []
            attach, mount, unmount, detach = _recording_mount_fixture(calls)
            build_unhealthy_candidate_bundle(
                base_payload=inputs["payload"],  # type: ignore[arg-type]
                base_hardware_support=inputs["hw"],  # type: ignore[arg-type]
                output_path=work / "boarded.greiaupdate",
                work_dir=work / "boarded-work",
                release_id="greia-0.21.1",
                platform_family="legacy-x86",
                architecture="i386",
                profile="legacy-x86-i686",
                board="pi-500",
                attach_fn=attach,
                mount_fn=mount,
                unmount_fn=unmount,
                detach_fn=detach,
            )
            with self.assertRaises(LifecycleHarnessError) as caught:
                verify_unhealthy_candidate_bundle(
                    work / "boarded.greiaupdate",
                    platform_family="legacy-x86",
                    architecture="i386",
                    profile="legacy-x86-i686",
                    expected_hardware_sha256=_hashlib.sha256(
                        inputs["hw"].read_bytes()  # type: ignore[union-attr]
                    ).hexdigest(),
                    board="pi-400",
                )
            self.assertIn("compatibility", str(caught.exception).lower())

    def test_verify_missing_bundle_is_red(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            work = Path(tmp)
            result, _ = _build_candidate(work)
            with self.assertRaises(LifecycleHarnessError) as caught:
                verify_unhealthy_candidate_bundle(
                    work / "absent.greiaupdate",
                    platform_family="legacy-x86",
                    architecture="i386",
                    profile="legacy-x86-i686",
                    expected_hardware_sha256=str(result["hardware_support_sha256"]),
                )
            self.assertIn("inspection", str(caught.exception).lower())


class D31SurvivalFoldTests(unittest.TestCase):
    def test_fold_marks_failed_and_preserves_d31_byte_identical(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            fold = run_d31_survival_fold(Path(tmp) / "d31")
            self.assertEqual(fold["surface"], "SOURCE_SCOPE")
            self.assertTrue(fold["green"])
            self.assertEqual(fold["journal_state"], "failed")
            self.assertEqual(fold["default_slot"], "A")
            self.assertEqual(fold["recovery_class"], "health-service-failure")
            self.assertEqual(fold["recovery_action"], "automatic-reboot")
            self.assertTrue(fold["semantic_preserved"])
            self.assertTrue(fold["persist_byte_identical"])
            self.assertGreater(len(fold["persist_files"]), 0)  # type: ignore[arg-type]

    def test_persist_drift_is_red_then_green(self) -> None:
        # Positive control: the byte comparator is sensitive. Break
        # (drop one file) -> RED; restore -> GREEN.
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "persist"
            from tools.x8_qemu.devproof import write_d31_representative_state

            write_d31_representative_state(root)
            before = snapshot_persist_tree(root)
            victim = sorted(before)[0]
            (root / victim).unlink()
            after = snapshot_persist_tree(root)
            with self.assertRaises(LifecycleHarnessError):
                assert_persist_byte_identical(before, after)
            assert_persist_byte_identical(before, before)

    def test_semantic_drift_is_red(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            from tools.x8_qemu.devproof import (
                read_d31_representative_state,
                verify_d31_rollback,
                write_d31_representative_state,
            )

            root = Path(tmp) / "persist"
            before = write_d31_representative_state(root)
            after = read_d31_representative_state(root)
            tampered = dict(after)
            tampered["device-settings"] = {
                "touchpad_tap": False,
                "touchpad_speed": 9.99,
            }
            with self.assertRaises(Exception):
                verify_d31_rollback(before, tampered)
            verify_d31_rollback(before, after)


class NoopSensitivityTests(unittest.TestCase):
    def test_accepted_boot_refuses_trigger_and_healthy_commits(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            proof = prove_recovery_noop_cases(Path(tmp) / "noop")
            self.assertEqual(proof["surface"], "SOURCE_SCOPE")
            self.assertIn("completed transaction", proof["accepted_boot_trigger_refusal"])  # type: ignore[operator]
            self.assertEqual(proof["plain_boot_default"], "A")
            self.assertEqual(proof["healthy_commit_state"], "accepted")
            self.assertEqual(proof["healthy_commit_default"], "B")


class StageInspectorTests(unittest.TestCase):
    def _layout_record(self, path: Path, *, release_id: str = "greia-0.21.0") -> Path:
        import json

        from greia_platform.persistent_layout import InstalledLayoutRecord

        record = InstalledLayoutRecord.from_dict(
            {
                "accepted_release_id": release_id,
                "accepted_slot": "B",
                "boot_backend": "grub-ab-v1",
                "boot_control": {"active_slot": "B", "kind": "grub-env-v1"},
                "install_profile": "acer-aspire-one-i386-ab",
                "install_target_sha256": "ab" * 32,
                "installed_at_unix": 1757000000,
                "layout_id": "legacy-bios-ab-v1",
                "persist": {"filesystem_uuid": "cccccccc-dddd-eeee-ffff-000000000000", "partuuid": "1a2b3c4d-04"},
                "platform_family": "legacy-x86",
                "schema_version": 1,
                "slot_bytes": 1664 * 1024 * 1024,
                "system_a": {"filesystem_uuid": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee", "partuuid": "1a2b3c4d-02"},
                "system_b": {"filesystem_uuid": "bbbbbbbb-cccc-dddd-eeee-ffffffffffff", "partuuid": "1a2b3c4d-03"},
            }
        )
        path.write_text(json.dumps(record.as_dict()), encoding="utf-8")
        return path

    def _coordinator(self, work: Path, name: str):
        from greia_platform.grub_ab import GrubEnvBackend

        from tools.x8_qemu.lifecycle import _artifact_set

        boot_dir = work / name
        boot_dir.mkdir(parents=True, exist_ok=True)
        backend = GrubEnvBackend.initialize(boot_dir, default_slot="B")
        journal_dir = work / f"{name}-journal"
        journal_dir.mkdir(parents=True, exist_ok=True)
        from greia_platform.boot_transaction import BootTransactionCoordinator

        coordinator = BootTransactionCoordinator.begin_update(
            journal_dir=journal_dir,
            backend=backend,
            candidate_artifacts=_artifact_set("A", "greia-0.22.0"),
            accepted_artifacts=_artifact_set("B", "greia-0.21.0"),
            release_id="greia-0.22.0",
        )
        return backend, journal_dir, coordinator

    def test_prefailure_then_postrecovery_through_production_parsers(self) -> None:
        from greia_platform.boot_transaction import mark_candidate_unhealthy

        with tempfile.TemporaryDirectory() as tmp:
            work = Path(tmp)
            backend, journal_dir, coordinator = self._coordinator(work, "boot")
            coordinator.arm()
            backend.reconcile("A")
            coordinator.observe_boot()
            pre = inspect_recovery_prefailure_roots(
                backend_state_dir=work / "boot",
                journal_dir=journal_dir,
                accepted_slot="B",
                candidate_slot="A",
            )
            self.assertEqual(pre["default_slot"], "B")
            self.assertEqual(pre["last_booted"], "A")
            self.assertIn(pre["journal_state"], ("one_shot_armed", "candidate_booting"))
            mark_candidate_unhealthy(
                coordinator, recovery_class="health-service-failure", detail="t"
            )
            backend.reconcile("B")
            layout = self._layout_record(work / "installed-layout.json")
            post = inspect_recovery_postrecovery_roots(
                backend_state_dir=work / "boot",
                journal_dir=journal_dir,
                accepted_slot="B",
                candidate_slot="A",
                layout_record_path=layout,
                accepted_release_id="greia-0.21.0",
            )
            self.assertEqual(post["journal_state"], "failed")
            self.assertEqual(post["accepted_release_id"], "greia-0.21.0")
            self.assertIn("health-service-failure", post["journal_note"])  # type: ignore[operator]
            self.assertIn("automatic-reboot", post["journal_note"])  # type: ignore[operator]
            self.assertEqual(post["last_booted"], "B")

            # The product harness observes all stages after the recovery
            # reboot. The prefailure inspector must also accept the terminal
            # FAILED journal as evidence that the candidate booted and the
            # deadline trigger recovered it, rather than requiring a live
            # pre-reboot snapshot that no longer exists.
            late = inspect_recovery_prefailure_roots(
                backend_state_dir=work / "boot",
                journal_dir=journal_dir,
                accepted_slot="B",
                candidate_slot="A",
            )
            self.assertEqual(late["journal_state"], "failed")
            self.assertEqual(late["last_booted"], "B")

            with self.assertRaisesRegex(LifecycleHarnessError, "accepted release"):
                inspect_recovery_postrecovery_roots(
                    backend_state_dir=work / "boot",
                    journal_dir=journal_dir,
                    accepted_slot="B",
                    candidate_slot="A",
                    layout_record_path=layout,
                    accepted_release_id="greia-0.20.0",
                )

    def test_prefailure_red_when_default_moved(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            work = Path(tmp)
            backend, journal_dir, coordinator = self._coordinator(work, "boot")
            coordinator.arm()
            backend.reconcile("A")
            coordinator.observe_boot()
            coordinator.commit()
            with self.assertRaises(LifecycleHarnessError):
                inspect_recovery_prefailure_roots(
                    backend_state_dir=work / "boot",
                    journal_dir=journal_dir,
                    accepted_slot="B",
                    candidate_slot="A",
                )

    def test_postrecovery_red_without_failed_journal(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            work = Path(tmp)
            backend, journal_dir, coordinator = self._coordinator(work, "boot")
            coordinator.arm()
            backend.reconcile("A")
            coordinator.observe_boot()
            with self.assertRaises(LifecycleHarnessError):
                inspect_recovery_postrecovery_roots(
                    backend_state_dir=work / "boot",
                    journal_dir=journal_dir,
                    accepted_slot="B",
                    candidate_slot="A",
                )


class LegDriverTests(unittest.TestCase):
    def test_leg_drives_phases_and_closes_lifecycle(self) -> None:
        result = _run_leg()
        self.assertEqual(result["leg"], "recovery-d31-reverse-product")
        self.assertEqual(result["_seen_phases"], list(RECOVERY_D31_REVERSE_LEG_PHASES))
        # Unhealthy staging precedes the candidate boot; reverse stages later.
        phases = result["_seen_phases"]
        self.assertLess(phases.index("update-stage"), phases.index("wait-health-poweroff"))
        self.assertEqual(phases.count("update-stage"), 2)
        self.assertTrue(result["d31_semantic_preserved"])
        self.assertTrue(result["d31_byte_identical"])
        self.assertIsNone(result["slot_isolation"]["active_unchanged"])  # type: ignore[index]
        self.assertIsNone(result["slot_isolation"]["inactive_changed"])  # type: ignore[index]
        self.assertEqual(
            result["slot_isolation"]["scope"],  # type: ignore[index]
            "raw_hashes_observational_across_boots",
        )
        assert_lifecycle_transitions(result["lifecycle_report"])
        self.assertEqual(
            result["lifecycle_report"]["observed_steps"],
            list(RECOVERY_D31_REVERSE_OBSERVED_STEPS),
        )
        self.assertFalse(result["source_image_mutated"])

    def test_leg_refuses_without_observation(self) -> None:
        with self.assertRaises(LifecycleHarnessError) as caught:
            run_recovery_d31_reverse_leg(boot_fn=lambda phase: None)
        self.assertIn("no host-side observation", str(caught.exception))

    def test_leg_red_when_default_moves_before_failure(self) -> None:
        observations = _good_observations()
        observations["boot-broken-candidate"] = dict(
            observations["boot-broken-candidate"], default_slot="A"
        )
        with self.assertRaises(LifecycleHarnessError) as caught:
            _run_leg(observe_fn=lambda stage: dict(observations[stage]))
        self.assertIn("before the failure decision", str(caught.exception))

    def test_leg_red_when_candidate_never_boots(self) -> None:
        observations = _good_observations()
        observations["boot-broken-candidate"] = dict(
            observations["boot-broken-candidate"], last_booted="B"
        )
        with self.assertRaises(LifecycleHarnessError) as caught:
            _run_leg(observe_fn=lambda stage: dict(observations[stage]))
        self.assertIn("did not land", str(caught.exception))

    def test_leg_red_when_no_failed_marking(self) -> None:
        observations = _good_observations()
        observations["recovery-boot-accepted"] = dict(
            observations["recovery-boot-accepted"],
            journal_state="candidate_booting",
            journal_note="",
        )
        with self.assertRaises(LifecycleHarnessError) as caught:
            _run_leg(observe_fn=lambda stage: dict(observations[stage]))
        self.assertIn("did not mark", str(caught.exception))

    def test_leg_red_when_note_leaves_pinned_class(self) -> None:
        observations = _good_observations()
        observations["recovery-boot-accepted"] = dict(
            observations["recovery-boot-accepted"],
            journal_note="recovery:launcher-exit:automatic-reboot:t",
        )
        with self.assertRaises(LifecycleHarnessError) as caught:
            _run_leg(observe_fn=lambda stage: dict(observations[stage]))
        self.assertIn("pinned class", str(caught.exception))

    def test_leg_red_when_reverse_not_accepted(self) -> None:
        observations = _good_observations()
        observations["reverse-update-accepted"] = dict(
            observations["reverse-update-accepted"],
            journal_state="failed",
            default_slot="B",
            accepted_release_id="greia-0.21.0",
        )
        with self.assertRaises(LifecycleHarnessError) as caught:
            _run_leg(observe_fn=lambda stage: dict(observations[stage]))
        self.assertIn("did not accept", str(caught.exception))

    def test_leg_red_when_recovery_changes_previous_release(self) -> None:
        observations = _good_observations()
        observations["recovery-boot-accepted"] = dict(
            observations["recovery-boot-accepted"],
            accepted_release_id="unexpected-release",
        )
        with self.assertRaisesRegex(
            LifecycleHarnessError, "accepted release after recovery"
        ):
            _run_leg(observe_fn=lambda stage: dict(observations[stage]))

    def test_leg_red_then_green_on_d31_restore(self) -> None:
        # Positive control: break the D31 byte snapshot -> RED; the
        # unbroken run (restore) -> GREEN.
        d31 = _good_d31()
        broken_bytes = dict(d31["bytes_after"])
        broken_bytes.pop(sorted(broken_bytes)[0])
        with self.assertRaises(LifecycleHarnessError):
            _run_leg(
                d31_fn=lambda: {
                    "semantic_before": d31["semantic_before"],
                    "semantic_after": d31["semantic_after"],
                    "bytes_before": d31["bytes_before"],
                    "bytes_after": broken_bytes,
                }
            )
        result = _run_leg()
        self.assertTrue(result["d31_byte_identical"])

    def test_leg_requires_distinct_release_advance(self) -> None:
        with self.assertRaises(LifecycleHarnessError):
            _run_leg(candidate_release_id="greia-0.21.0", reverse_release_id="greia-0.22.0")
        with self.assertRaises(LifecycleHarnessError):
            _run_leg(candidate_release_id="greia-0.22.0", reverse_release_id="greia-0.22.0")

    def test_report_rejects_wrong_default(self) -> None:
        with self.assertRaises(LifecycleHarnessError):
            build_recovery_d31_reverse_lifecycle_report(observed_default="B")


class ProductEntryTests(unittest.TestCase):
    def test_recovery_entry_blocked_on_this_host(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            harness = ProductHarness(
                LifecycleConfig(output_dir=Path(tmp) / "out"),
                control_enabled=True,
            )
            with self.assertRaises(LifecycleHarnessError) as caught:
                harness.run_recovery_d31_reverse_product(
                    installed_image=Path(tmp) / "installed.img",
                    unhealthy_bundle=Path(tmp) / "unhealthy.greiaupdate",
                    reverse_bundle=Path(tmp) / "reverse.greiaupdate",
                )
            self.assertIn("BLOCKED", str(caught.exception))

    def test_entry_stages_unhealthy_before_reverse(self) -> None:
        # The unhealthy-before-reverse staging order is proven through
        # this entry point with recording fakes (host gate mocked only).
        staged: list[str] = []
        boots: list[str] = []
        real_stage = _product.ProductHarness._stage_candidate_onto_control

        def fake_stage(self, control_dir: Path, bundle: Path, *, control_image=None):
            staged.append(Path(bundle).name)

        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "out"
            installed = Path(tmp) / "installed.img"
            installed.write_bytes(b"installed-image-bytes")
            unhealthy = Path(tmp) / "unhealthy.greiaupdate"
            unhealthy.write_bytes(b"unhealthy-bytes")
            reverse = Path(tmp) / "reverse.greiaupdate"
            reverse.write_bytes(b"reverse-bytes")
            harness = ProductHarness(
                LifecycleConfig(output_dir=out), control_enabled=True
            )
            with _mock.patch.object(
                _product, "require_product_host", lambda *a, **k: None
            ), _mock.patch.object(
                _product.ProductHarness,
                "_stage_candidate_onto_control",
                fake_stage,
            ), _mock.patch.object(
                _product,
                "clone_product_image",
                lambda src, dst: (_shutil.copy2(src, dst), {"clone": str(dst)})[1],
            ), _mock.patch.object(
                _product,
                "record_shipped_recovery_units",
                lambda **k: {"unit_dir": "fake", "sha256": {}, "helper": "fake",
                             "helper_sha256": "00" * 32},
            ), _mock.patch.object(
                _product, "select_install_qemu_binary", lambda **k: "qemu-system-i386"
            ):
                observations = _good_observations()
                d31 = _good_d31()
                digests = {
                    ("B", "before"): _hex64("eb"),
                    ("A", "before"): _hex64("ab"),
                    ("B", "after"): _hex64("eb"),
                    ("A", "after"): _hex64("aa"),
                }
                result = harness.run_recovery_d31_reverse_product(
                    installed_image=installed,
                    unhealthy_bundle=unhealthy,
                    reverse_bundle=reverse,
                    materialize_fn=lambda control_dir, image: None,
                    boot_fn=lambda phase, argv, serial_log, host_log: boots.append(phase),
                    observe_fn=lambda stage: dict(observations[stage]),
                    d31_fn=lambda: {
                        "semantic_before": d31["semantic_before"],
                        "semantic_after": d31["semantic_after"],
                        "bytes_before": d31["bytes_before"],
                        "bytes_after": d31["bytes_after"],
                    },
                    slot_digest_fn=lambda slot, when: digests[(slot, when)],
                    serial_fn=lambda clone: {
                        "clone": str(clone),
                        "grub_cfg": "grub.cfg",
                        "pre_sha256": "aa" * 32,
                        "post_sha256": "aa" * 32,
                        "substitutions": 0,
                        "source_image_mutated": False,
                    },
                )
        self.assertEqual(staged, ["unhealthy.greiaupdate", "reverse.greiaupdate"])
        self.assertEqual(boots, list(RECOVERY_D31_REVERSE_LEG_PHASES))
        self.assertTrue(result["ok"])
        self.assertEqual(result["reverse_slot"], "A")
        assert_lifecycle_transitions(result["lifecycle_report"])
        del real_stage


if __name__ == "__main__":
    unittest.main()
