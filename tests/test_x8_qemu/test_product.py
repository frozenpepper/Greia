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
    inject_update_candidate_into_persist,
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

    def test_unit_disables_start_timeout_for_long_legs(self) -> None:
        # Product legs legitimately outlast systemd's 90 s start timeout
        # (a full install streams gigabytes); the test seam must not let
        # the manager SIGTERM the runner mid-leg.
        self.assertIn("TimeoutStartSec=0", control_unit_text())

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

    def test_runner_powers_off_with_diagnostics_on_phase_failure(self) -> None:
        text = control_runner_text()
        self.assertIn("capturing service diagnostics", text)
        self.assertIn("trap control_exit EXIT", text)
        self.assertIn('umount "$CTL_MNT" || true', text)
        self.assertIn("timeout 8 journalctl --no-pager -u", text)
        self.assertIn("timeout 8 systemctl --no-block poweroff", text)

    def test_runner_text_is_valid_bash(self) -> None:
        import subprocess as _subprocess

        completed = _subprocess.run(
            ["bash", "-n", "/dev/stdin"],
            input=control_runner_text().encode(),
            capture_output=True,
            timeout=60,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr.decode()[:500])


class PersistCandidateInjectionTests(unittest.TestCase):
    def test_loop_attach_failure_does_not_attempt_unmount(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            clone = root / "clone.img"
            clone.write_bytes(b"clone")
            bundle = root / "candidate.greiaupdate"
            bundle.write_bytes(b"candidate")
            with (
                _mock.patch.object(_product, "_require_loop_tools"),
                _mock.patch.object(
                    _product,
                    "_loop_attach",
                    side_effect=LifecycleHarnessError("attach failed"),
                ),
                _mock.patch.object(_product, "_umount_fs") as unmount,
                _mock.patch.object(_product, "_loop_detach") as detach,
            ):
                with self.assertRaisesRegex(LifecycleHarnessError, "attach failed"):
                    inject_update_candidate_into_persist(clone, bundle)
            unmount.assert_not_called()
            detach.assert_not_called()

    def test_uses_canonical_receive_without_host_status_projection(self) -> None:
        from types import SimpleNamespace
        from greia_platform.system_updates import SystemUpdateInbox

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            clone = root / "clone.img"
            clone.write_bytes(b"disposable clone")
            bundle = root / "candidate.greiaupdate"
            bundle.write_bytes(b"fixture bundle bytes")
            runner = SimpleNamespace(returncode=0, stdout="", stderr="")
            captured: dict[str, object] = {}
            fsynced: list[Path] = []
            real_fsync = _product._fsync_file_and_parent

            def track_fsync(path: Path) -> None:
                fsynced.append(Path(path))
                real_fsync(path)

            def receive(inbox: SystemUpdateInbox, source: Path):
                candidate = inbox.candidate_path
                candidate.parent.mkdir(parents=True, exist_ok=True)
                candidate.parent.chmod(0o700)
                shutil.copyfile(source, candidate)
                candidate.chmod(0o600)
                status = inbox.status_path
                status.write_text(
                    __import__("json").dumps({
                        "state": "received",
                        "release": {"release_id": "fixture-release"},
                        "bundle_path": str(candidate),
                        "bundle_sha256": "a" * 64,
                        "activation_available": False,
                    }),
                    encoding="utf-8",
                )
                captured["status"] = __import__("json").loads(
                    status.read_text(encoding="utf-8")
                )
                status.chmod(0o600)
                captured["state_dir"] = inbox.state_dir
                captured["candidate"] = candidate
                return SimpleNamespace(path=str(candidate))

            def mount_persist(source: str, mountpoint: Path, **kwargs) -> None:
                (mountpoint / "greia/namespaces/parent-credentials").mkdir(
                    parents=True, exist_ok=True
                )

            with (
                _mock.patch.object(_product, "_require_loop_tools"),
                _mock.patch.object(_product, "_loop_attach", return_value="/dev/loop7"),
                _mock.patch.object(_product, "_mount_fs", side_effect=mount_persist),
                _mock.patch.object(_product, "_umount_fs"),
                _mock.patch.object(_product, "_loop_detach"),
                _mock.patch.object(SystemUpdateInbox, "receive", receive),
                _mock.patch.object(_product, "_fsync_file_and_parent", track_fsync),
            ):
                proof = inject_update_candidate_into_persist(
                    clone, bundle, runner=lambda *args, **kwargs: runner
                )

            state_dir = Path(str(captured["state_dir"]))
            self.assertEqual(
                state_dir.parts[-3:],
                ("greia", "namespaces", "parent-credentials"),
            )
            self.assertEqual(Path(str(captured["candidate"])).name, "candidate.greiaupdate")
            status = captured["status"]
            self.assertEqual(status["bundle_path"], str(captured["candidate"]))
            self.assertNotIn("guest_candidate_path", proof)
            self.assertEqual(
                fsynced, [Path(proof["candidate_path"]), Path(proof["status_path"])]
            )
            self.assertEqual(proof["candidate_bytes"], bundle.stat().st_size)
            self.assertEqual(proof["parent_ownership"]["inbox_mode"], "0700")
            self.assertEqual(proof["parent_ownership"]["candidate_mode"], "0600")
            self.assertEqual(proof["parent_ownership"]["status_mode"], "0600")

    def test_fixed_candidate_is_discovered_without_status_receipt(self) -> None:
        from greia_platform.system_updates import (
            SystemUpdateInbox,
            SystemUpdateServiceAuthority,
        )

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            guest = SystemUpdateInbox(root / "guest-state")
            guest.candidate_path.parent.mkdir(parents=True)
            guest.candidate_path.write_bytes(b"validated fixture bytes")

            authority = object.__new__(SystemUpdateServiceAuthority)
            authority.state_dir = guest.state_dir
            self.assertEqual(
                authority._current_bundle_path().resolve(),
                guest.candidate_path.resolve(),
            )
            guest.status_path.write_text("invalid progress metadata", encoding="utf-8")
            self.assertEqual(
                authority._current_bundle_path().resolve(),
                guest.candidate_path.resolve(),
            )

    def test_parent_ownership_restoration_is_scoped_and_preserves_private_modes(self) -> None:
        from types import SimpleNamespace

        with tempfile.TemporaryDirectory() as tmp:
            state_dir = Path(tmp) / "parent-credentials"
            updates = state_dir / "system-updates"
            inbox = updates / "inbox"
            inbox.mkdir(parents=True)
            candidate = inbox / "candidate.greiaupdate"
            status = updates / "status.json"
            candidate.write_bytes(b"candidate")
            status.write_bytes(b"status")
            inbox.chmod(0o700)
            candidate.chmod(0o600)
            status.chmod(0o600)
            owner = state_dir.stat()
            real_stat = Path.lstat
            calls: list[tuple[Path, int, int]] = []

            def stat_with_different_owner(path: Path, *args, **kwargs):
                result = real_stat(path, *args, **kwargs)
                if path == state_dir:
                    return SimpleNamespace(
                        st_uid=owner.st_uid + 1,
                        st_gid=owner.st_gid + 1,
                        st_mode=result.st_mode,
                    )
                return result

            with (
                _mock.patch.object(Path, "lstat", autospec=True, side_effect=stat_with_different_owner),
                _mock.patch.object(
                    _product.os,
                    "chown",
                    side_effect=lambda path, uid, gid, **kwargs: calls.append(
                        (Path(path), uid, gid)
                    ),
                ),
            ):
                proof = _product._restore_parent_inbox_ownership(
                    state_dir, candidate_path=candidate, status_path=status
                )
            self.assertEqual(
                [item[0] for item in calls], [updates, inbox, candidate, status]
            )
            self.assertTrue(all(item[1:] == (owner.st_uid + 1, owner.st_gid + 1) for item in calls))
            self.assertEqual(len(proof["paths"]), 4)
            self.assertEqual(inbox.stat().st_mode & 0o777, 0o700)
            self.assertEqual(candidate.stat().st_mode & 0o777, 0o600)
            self.assertEqual(status.stat().st_mode & 0o777, 0o600)

    def test_symlinked_update_namespace_is_refused_before_injection(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            state = root / "parent-credentials"
            state.mkdir()
            external = root / "external"
            external.mkdir()
            (state / "system-updates").symlink_to(external, target_is_directory=True)
            with self.assertRaisesRegex(
                LifecycleHarnessError, "not a real directory"
            ):
                _product._assert_real_persist_update_paths(state)


class ControlPhaseFailureTests(unittest.TestCase):
    def test_zero_exit_after_guest_refusal_is_still_a_phase_failure(self) -> None:
        from types import SimpleNamespace

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            serial = root / "serial.log"
            serial.write_text(
                "x8-control: update VERIFY_CURRENT_CANDIDATE refused: "
                "{'reason': 'no current update candidate in the inbox'}\n"
                "x8-control: phase update-verify failed (exit 1); "
                "capturing service diagnostics\n",
                encoding="utf-8",
            )
            harness = ProductHarness(LifecycleConfig(output_dir=root / "out"))
            with (
                _mock.patch.object(_product, "resolve_device_host_tool", return_value="/qemu"),
                _mock.patch.object(_product.shutil, "which", return_value=None),
                _mock.patch.object(
                    _product.subprocess,
                    "run",
                    return_value=SimpleNamespace(returncode=0, stdout="", stderr=""),
                ),
            ):
                with self.assertRaises(LifecycleHarnessError) as caught:
                    harness._boot_installed_phase(
                        phase="update-verify",
                        argv=["qemu-system-i386"],
                        serial_log=serial,
                        host_log=root / "host.log",
                    )
            self.assertIn("phase update-verify failed", str(caught.exception))
            self.assertIn("no current update candidate in the inbox", str(caught.exception))

    def test_failure_marker_is_bound_to_exact_phase(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            serial = Path(tmp) / "serial.log"
            serial.write_text(
                "x8-control: phase update-stage failed (exit 1)\n",
                encoding="utf-8",
            )
            failure = _product._control_phase_failure(serial, "update-verify")
            self.assertIn("expected phase update-verify", str(failure))
            self.assertIn("observed x8-control: phase update-stage failed", str(failure))


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
