from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
BOOTSTRAP_PATH = (
    ROOT / "build/overlay/usr/local/lib/greia-os/software-update-bootstrap.py"
)
SPEC = importlib.util.spec_from_file_location("greia_software_update_bootstrap_test", BOOTSTRAP_PATH)
assert SPEC is not None and SPEC.loader is not None
bootstrap = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = bootstrap
SPEC.loader.exec_module(bootstrap)


def _job(paths: object, job_id: str, state: str = "applying") -> dict[str, object]:
    path = Path(getattr(paths, "job"))
    path.parent.mkdir(parents=True, exist_ok=True)
    job = {
        "job_id": job_id,
        "state": state,
        "created_at": "2026-10-24T00:00:00+00:00",
        "updated_at": "2026-10-24T00:00:00+00:00",
        "package_bytes": 1,
        "received_bytes": 1,
        "package_type": "python_platform",
        "version": "1.0.0",
        "release_id": "greia-test-1.0.0",
        "error_code": None,
        "error_message": None,
        "activation_requested": True,
        "previous_generation": "base",
        "candidate_generation": "app-" + job_id,
    }
    path.write_text(
        json.dumps({"schema_version": 1, "job": job}, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    path.chmod(0o600)
    Path(getattr(paths, "job_lock")).touch(mode=0o660)
    Path(getattr(paths, "pending")).touch(mode=0o600)
    return job


def _paths(root: Path) -> bootstrap.BootstrapPaths:
    marker = root / "etc/greia-os/software-update-bootstrap.json"
    helper = root / "usr/local/lib/greia-os/software-update-bootstrap.py"
    root_uuid = root / "etc/greia-os/root-filesystem-uuid"
    marker.parent.mkdir(parents=True)
    helper.parent.mkdir(parents=True)
    root_uuid.write_text("11111111-1111-4111-8111-111111111111\n", encoding="ascii")
    marker.write_text('{"schema_version":1}\n', encoding="utf-8")
    helper.write_text("#!/usr/bin/python3\n", encoding="utf-8")
    helper.chmod(0o755)
    generations = root / "opt/greia-software/generations"
    generations.mkdir(parents=True)
    state = root / "var/lib/greia-os/software-updates"
    state.mkdir(parents=True)
    active_runtime = root / "run/greia-os"
    active_runtime.mkdir(parents=True)
    restart_runtime = root / "run/greia-update-authority"
    restart_runtime.mkdir(parents=True)
    builtin_index = root / "usr/share/greia/activity-index-v1.json"
    builtin_index.parent.mkdir(parents=True)
    return bootstrap.BootstrapPaths(
        marker=marker,
        helper=helper,
        application_root=root / "opt/greia-os",
        generation_root=generations,
        software_update_root=state,
        candidate=state / "candidate.greia_update",
        job=state / "job.json",
        job_lock=state / "job.lock",
        pending=state / "pending",
        journal=state / "apply-journal.json",
        active_profile=active_runtime / "active-profile.json",
        root_filesystem_uuid=root_uuid,
        active_profile_lock=restart_runtime / "profile-session.lock",
        restart_fence=restart_runtime / "restart-pending.json",
        boot_marker_spool=active_runtime / "boot-markers.log",
        builtin_index=builtin_index,
    )


def _make_generation(paths: bootstrap.BootstrapPaths, generation_id: str) -> Path:
    root = paths.generation_root / generation_id
    root.mkdir()
    (root / "src/greia_platform").mkdir(parents=True)
    (root / "src/greia_platform/generation_probe.py").write_text(
        f"VALUE = {generation_id!r}\n", encoding="utf-8"
    )
    (root / "activity-index-v1.json").write_text("{}\n", encoding="utf-8")
    return root


def _point_to(paths: bootstrap.BootstrapPaths, generation_id: str) -> None:
    paths.application_root.parent.mkdir(parents=True, exist_ok=True)
    paths.application_root.symlink_to(
        Path("greia-software/generations") / generation_id,
        target_is_directory=True,
    )
    paths.builtin_index.symlink_to(
        "../../../opt/greia-os/activity-index-v1.json"
    )


def _ready_marker(paths: bootstrap.BootstrapPaths, monotonic_ns: int) -> None:
    paths.boot_marker_spool.write_text(
        "GREIA_BOOT event=launcher_interactive_ready "
        f"monotonic_ns={monotonic_ns}\n",
        encoding="utf-8",
    )


class SoftwareUpdateBootstrapRecoveryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(prefix="greia-update-bootstrap-")
        self.root = Path(self.temporary.name)
        self.paths = _paths(self.root)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def test_interrupted_legacy_directory_migration_recovers_from_pre_rename_journal(self) -> None:
        app = self.paths.application_root
        app.mkdir(parents=True)
        (app / "src").mkdir()
        (app / "activity-index-v1.json").write_text("{}\n", encoding="utf-8")
        self.paths.builtin_index.symlink_to(str(app / "activity-index-v1.json"))
        real_replace = bootstrap.os.replace

        def fail_first_directory_move(source, destination):
            if Path(source) == app:
                raise OSError("simulated power cut before legacy-root rename")
            return real_replace(source, destination)

        with mock.patch.object(bootstrap.os, "replace", side_effect=fail_first_directory_move):
            with self.assertRaisesRegex(OSError, "power cut"):
                bootstrap.migrate_directory_layout(self.paths)
        journal = json.loads(self.paths.journal.read_text("utf-8"))
        self.assertEqual(journal["phase"], "migration_started")
        self.assertTrue(app.is_dir())

        bootstrap.recover_before_services(self.paths)
        self.assertTrue(app.is_symlink())
        self.assertEqual(
            bootstrap.current_generation_id(self.paths),
            journal["candidate_generation"],
        )
        self.assertEqual(self.paths.builtin_index.read_text("utf-8"), "{}\n")
        self.assertEqual(
            json.loads(self.paths.journal.read_text("utf-8"))["phase"], "layout_ready"
        )
        self.assertEqual(
            self.paths.builtin_index.readlink(),
            Path("../../../opt/greia-os/activity-index-v1.json"),
        )

    def test_index_alias_is_normalized_to_a_fake_root_relative_link(self) -> None:
        _make_generation(self.paths, "base")
        _point_to(self.paths, "base")
        self.paths.builtin_index.unlink()
        self.paths.builtin_index.symlink_to(
            str(self.paths.application_root / "activity-index-v1.json")
        )
        bootstrap._restore_builtin_index_alias(self.paths)
        self.assertEqual(
            self.paths.builtin_index.readlink(),
            Path("../../../opt/greia-os/activity-index-v1.json"),
        )
        resolved_root = self.root.resolve()
        self.assertTrue(self.paths.builtin_index.resolve(strict=True).is_relative_to(resolved_root))
        self.assertEqual(self.paths.builtin_index.read_text("utf-8"), "{}\n")

    def test_interrupted_pointer_switch_restores_the_previous_complete_generation(self) -> None:
        _make_generation(self.paths, "base")
        candidate = "app-" + "1" * 32
        _make_generation(self.paths, candidate)
        _point_to(self.paths, candidate)
        job_id = "1" * 32
        _job(self.paths, job_id)
        bootstrap._write_journal(
            self.paths,
            {
                "schema_version": 1,
                "phase": "switching",
                "job_id": job_id,
                "previous_generation": "base",
                "candidate_generation": candidate,
            },
        )

        # This is the power-loss cut after the pointer rename but before the
        # stable worker can publish the trial phase.
        bootstrap.recover_before_services(self.paths)
        self.assertEqual(bootstrap.current_generation_id(self.paths), "base")
        self.assertEqual(
            json.loads(self.paths.job.read_text("utf-8"))["job"]["state"],
            "rolled_back",
        )
        self.assertFalse(self.paths.pending.exists())
        self.assertFalse(self.paths.restart_fence.exists())

    def test_trial_rollback_rejects_pre_trial_health_marker(self) -> None:
        _make_generation(self.paths, "base")
        candidate = "app-" + "2" * 32
        _make_generation(self.paths, candidate)
        _point_to(self.paths, candidate)
        job_id = "2" * 32
        job = _job(self.paths, job_id, "restarting")
        self.paths.boot_marker_spool.write_text(
            "GREIA_BOOT event=launcher_interactive_ready monotonic_ns=10\n",
            encoding="utf-8",
        )
        bootstrap._write_restart_fence(self.paths, job_id)
        bootstrap._write_journal(
            self.paths,
            {
                "schema_version": 1,
                "phase": "trial",
                "job_id": job_id,
                "previous_generation": "base",
                "candidate_generation": candidate,
                "readiness_boundary_monotonic_ns": 10,
            },
        )
        with mock.patch.object(bootstrap, "_run_systemctl") as systemctl, mock.patch.object(
            bootstrap, "_wait_for_ready", return_value=True
        ), mock.patch.object(bootstrap, "_start_parent_and_wait"):
            bootstrap._reconcile_application_trial(self.paths, job)
        self.assertGreaterEqual(systemctl.call_count, 3)
        self.assertEqual(bootstrap.current_generation_id(self.paths), "base")
        self.assertEqual(
            json.loads(self.paths.job.read_text("utf-8"))["job"]["state"],
            "rolled_back",
        )

    def test_trial_commit_requires_fresh_marker_and_candidate_still_active(self) -> None:
        _make_generation(self.paths, "base")
        candidate = "app-" + "3" * 32
        _make_generation(self.paths, candidate)
        _point_to(self.paths, candidate)
        job_id = "3" * 32
        job = _job(self.paths, job_id, "restarting")
        _ready_marker(self.paths, 101)
        bootstrap._write_restart_fence(self.paths, job_id)
        journal = {
            "schema_version": 1,
            "phase": "trial",
            "job_id": job_id,
            "previous_generation": "base",
            "candidate_generation": candidate,
            "readiness_boundary_monotonic_ns": 100,
        }
        bootstrap._write_journal(self.paths, journal)
        with mock.patch.object(bootstrap, "_run_systemctl"), mock.patch.object(
            bootstrap, "_start_parent_and_wait"
        ):
            bootstrap._reconcile_application_trial(self.paths, job)
        self.assertEqual(
            json.loads(self.paths.journal.read_text("utf-8"))["phase"], "committed"
        )
        self.assertEqual(
            json.loads(self.paths.job.read_text("utf-8"))["job"]["state"], "applied"
        )

    def test_late_old_ready_marker_is_rejected_and_rotation_keeps_fresh_marker(self) -> None:
        _ready_marker(self.paths, 99)
        self.assertFalse(bootstrap._fresh_launcher_ready(self.paths, 100))
        with self.paths.boot_marker_spool.open("wb") as handle:
            handle.write(b"x" * (70 * 1024))
            handle.write(
                b"\nGREIA_BOOT event=launcher_interactive_ready monotonic_ns=101\n"
            )
        self.assertTrue(bootstrap._fresh_launcher_ready(self.paths, 100))

    def test_parent_start_without_loopback_health_rolls_back_candidate(self) -> None:
        _make_generation(self.paths, "base")
        candidate = "app-" + "5" * 32
        _make_generation(self.paths, candidate)
        _point_to(self.paths, candidate)
        job_id = "5" * 32
        job = _job(self.paths, job_id, "restarting")
        bootstrap._write_restart_fence(self.paths, job_id)
        _ready_marker(self.paths, 101)
        bootstrap._write_journal(
            self.paths,
            {
                "schema_version": 1,
                "phase": "trial",
                "job_id": job_id,
                "previous_generation": "base",
                "candidate_generation": candidate,
                "readiness_boundary_monotonic_ns": 100,
            },
        )
        with mock.patch.object(bootstrap, "_run_systemctl"), mock.patch.object(
            bootstrap, "_wait_for_ready", return_value=True
        ), mock.patch.object(
            bootstrap,
            "_start_parent_and_wait",
            side_effect=[bootstrap.BootstrapError("Parent health timed out"), None],
        ):
            bootstrap._reconcile_application_trial(self.paths, job)
        self.assertEqual(bootstrap.current_generation_id(self.paths), "base")
        self.assertEqual(
            json.loads(self.paths.job.read_text("utf-8"))["job"]["state"],
            "rolled_back",
        )

    def test_trial_without_a_health_boundary_rolls_back_immediately(self) -> None:
        _make_generation(self.paths, "base")
        candidate = "app-" + "a" * 32
        _make_generation(self.paths, candidate)
        _point_to(self.paths, candidate)
        job_id = "a" * 32
        job = _job(self.paths, job_id, "restarting")
        bootstrap._write_restart_fence(self.paths, job_id)
        bootstrap._write_journal(
            self.paths,
            {
                "schema_version": 1,
                "phase": "trial",
                "job_id": job_id,
                "previous_generation": "base",
                "candidate_generation": candidate,
            },
        )
        with mock.patch.object(bootstrap, "_run_systemctl"), mock.patch.object(
            bootstrap, "_wait_for_ready", return_value=True
        ), mock.patch.object(bootstrap, "_start_parent_and_wait"):
            bootstrap._reconcile_application_trial(self.paths, job)
        self.assertEqual(bootstrap.current_generation_id(self.paths), "base")
        self.assertEqual(
            json.loads(self.paths.job.read_text("utf-8"))["job"]["state"],
            "rolled_back",
        )

    def test_switching_journal_next_tick_rolls_back_candidate_without_reboot(self) -> None:
        _make_generation(self.paths, "base")
        candidate = "app-" + "6" * 32
        _make_generation(self.paths, candidate)
        _point_to(self.paths, candidate)
        job_id = "6" * 32
        job = _job(self.paths, job_id, "applying")
        bootstrap._write_restart_fence(self.paths, job_id)
        bootstrap._write_journal(
            self.paths,
            {
                "schema_version": 1,
                "phase": "switching",
                "job_id": job_id,
                "previous_generation": "base",
                "candidate_generation": candidate,
            },
        )
        with mock.patch.object(bootstrap, "_profile_picker_idle", return_value=True), mock.patch.object(
            bootstrap, "_run_systemctl"
        ), mock.patch.object(bootstrap, "_wait_for_ready", return_value=True), mock.patch.object(
            bootstrap, "_start_parent_and_wait"
        ):
            bootstrap.apply_pending(self.paths)
        self.assertEqual(bootstrap.current_generation_id(self.paths), "base")
        self.assertEqual(
            json.loads(self.paths.job.read_text("utf-8"))["job"]["state"],
            "rolled_back",
        )

    def test_switching_previous_pointer_requeues_without_stopping_old_services(self) -> None:
        _make_generation(self.paths, "base")
        candidate = "app-" + "7" * 32
        _make_generation(self.paths, candidate)
        _point_to(self.paths, "base")
        job_id = "7" * 32
        job = _job(self.paths, job_id, "applying")
        bootstrap._write_restart_fence(self.paths, job_id)
        bootstrap._write_journal(
            self.paths,
            {
                "schema_version": 1,
                "phase": "switching",
                "job_id": job_id,
                "previous_generation": "base",
                "candidate_generation": candidate,
            },
        )
        with mock.patch.object(bootstrap, "_profile_picker_idle", return_value=True), mock.patch.object(
            bootstrap, "_run_systemctl"
        ) as systemctl, mock.patch.object(bootstrap, "_start_parent_and_wait"):
            bootstrap.apply_pending(self.paths)
        self.assertEqual(bootstrap.current_generation_id(self.paths), "base")
        self.assertFalse(any(call.args[0] == "stop" for call in systemctl.call_args_list))
        self.assertEqual(
            json.loads(self.paths.job.read_text("utf-8"))["job"]["state"],
            "waiting_for_idle",
        )
        self.assertTrue(self.paths.pending.exists())

    def test_waiting_for_idle_skips_package_inspection_until_picker_is_idle(self) -> None:
        _make_generation(self.paths, "base")
        _point_to(self.paths, "base")
        job_id = "8" * 32
        _job(self.paths, job_id, "waiting_for_idle")
        with mock.patch.object(bootstrap, "_pin_installed_source"), mock.patch.object(
            bootstrap, "_profile_picker_idle", return_value=False
        ), mock.patch(
            "greia_platform.software_update_apply.prepare_software_update"
        ) as prepare:
            result = bootstrap.apply_pending(self.paths)
            self.assertEqual(
                result,
                0,
                json.loads(self.paths.job.read_text("utf-8"))["job"],
            )
            self.assertEqual(bootstrap.apply_pending(self.paths), 0)
            prepare.assert_not_called()
            bootstrap._profile_picker_idle.return_value = True
            prepare.side_effect = RuntimeError("stop after proving preparation started")
            self.assertEqual(bootstrap.apply_pending(self.paths), 1)
            prepare.assert_called_once()

    def test_apply_pending_runs_durable_validation_idle_switch_health_commit(self) -> None:
        _make_generation(self.paths, "base")
        candidate = "app-" + "d" * 32
        _make_generation(self.paths, candidate)
        _point_to(self.paths, "base")
        job_id = "d" * 32
        _job(self.paths, job_id, "queued")

        @contextmanager
        def profile_guard():
            yield

        plan = SimpleNamespace(
            kind="application_generation",
            package_type="python_platform",
            version="2.0.0",
            release_id="greia-test-2.0.0",
            package_sha256="d" * 64,
            package_size=123,
            previous_generation="base",
            candidate_generation=candidate,
            profile_session=SimpleNamespace(profile_picker_restart_guard=profile_guard),
            activity_service=None,
        )

        def systemctl(*arguments: str) -> None:
            if arguments[:2] == ("start", "greia-launcher.service"):
                _ready_marker(self.paths, bootstrap.time.monotonic_ns() + 100)

        with mock.patch.object(bootstrap, "_pin_installed_source"), mock.patch.object(
            bootstrap, "_profile_picker_idle", return_value=True
        ), mock.patch(
            "greia_platform.software_update_apply.prepare_software_update",
            return_value=plan,
        ) as prepare, mock.patch.object(
            bootstrap, "_run_systemctl", side_effect=systemctl
        ), mock.patch.object(
            bootstrap, "_wait_for_parent_ready", return_value=True
        ), mock.patch.object(
            bootstrap, "_job_state_update", wraps=bootstrap._job_state_update
        ) as update:
            self.assertEqual(bootstrap.apply_pending(self.paths), 0)
        prepare.assert_called_once()
        states = [call.args[1] for call in update.call_args_list]
        self.assertEqual(states, ["validating", "validating", "waiting_for_idle", "applying", "restarting", "applied"])
        self.assertEqual(bootstrap.current_generation_id(self.paths), candidate)
        self.assertEqual(
            json.loads(self.paths.job.read_text("utf-8"))["job"]["state"], "applied"
        )
        self.assertEqual(
            json.loads(self.paths.journal.read_text("utf-8"))["phase"], "committed"
        )
        self.assertFalse(self.paths.pending.exists())
        self.assertFalse(self.paths.restart_fence.exists())

    def test_failed_generation_restores_data_and_allows_a_later_update(self) -> None:
        _make_generation(self.paths, "base")
        first_candidate = "app-" + "e" * 32
        second_candidate = "app-" + "f" * 32
        _make_generation(self.paths, first_candidate)
        _point_to(self.paths, "base")
        data = self.root / "var/lib/greia-profiles/child/data.json"
        data.parent.mkdir(parents=True)
        data.write_text("{\"saved\":true}\n", encoding="utf-8")
        first_job_id = "e" * 32
        _job(self.paths, first_job_id, "queued")

        @contextmanager
        def profile_guard():
            yield

        def plan_for(job_id: str, candidate: str) -> SimpleNamespace:
            return SimpleNamespace(
                kind="application_generation",
                package_type="python_platform",
                version="2.0.0",
                release_id="greia-test-2.0.0",
                package_sha256=job_id * 2,
                package_size=123,
                previous_generation="base",
                candidate_generation=candidate,
                profile_session=SimpleNamespace(profile_picker_restart_guard=profile_guard),
                activity_service=None,
            )

        def prepare(job: dict[str, object], _paths: object) -> SimpleNamespace:
            if job.get("job_id") == "f" * 32:
                _make_generation(self.paths, second_candidate)
                return plan_for("f" * 32, second_candidate)
            return plan_for(first_job_id, first_candidate)

        with mock.patch.object(bootstrap, "_pin_installed_source"), mock.patch.object(
            bootstrap, "_profile_picker_idle", return_value=True
        ), mock.patch(
            "greia_platform.software_update_apply.prepare_software_update",
            side_effect=prepare,
        ), mock.patch.object(bootstrap, "_run_systemctl"), mock.patch.object(
            bootstrap, "_wait_for_ready", side_effect=[False, True, True]
        ), mock.patch.object(bootstrap, "_start_parent_and_wait"):
            self.assertEqual(bootstrap.apply_pending(self.paths), 0)
            self.assertEqual(bootstrap.current_generation_id(self.paths), "base")
            self.assertEqual(data.read_text("utf-8"), "{\"saved\":true}\n")
            self.assertEqual(
                json.loads(self.paths.job.read_text("utf-8"))["job"]["state"],
                "rolled_back",
            )

            _job(self.paths, "f" * 32, "queued")
            self.paths.candidate.write_bytes(b"next accepted package")
            result = bootstrap.apply_pending(self.paths)
            self.assertEqual(
                result,
                0,
                json.loads(self.paths.job.read_text("utf-8"))["job"],
            )
        self.assertEqual(bootstrap.current_generation_id(self.paths), second_candidate)
        self.assertEqual(data.read_text("utf-8"), "{\"saved\":true}\n")
        self.assertEqual(
            json.loads(self.paths.job.read_text("utf-8"))["job"]["state"], "applied"
        )

    def test_committed_old_job_cannot_mark_new_queued_job_applied(self) -> None:
        _make_generation(self.paths, "base")
        committed = "app-" + "9" * 32
        _make_generation(self.paths, committed)
        _point_to(self.paths, committed)
        current_job_id = "a" * 32
        _job(self.paths, current_job_id, "queued")
        self.paths.candidate.write_bytes(b"new candidate")
        bootstrap._write_journal(
            self.paths,
            {
                "schema_version": 1,
                "phase": "committed",
                "job_id": "9" * 32,
                "previous_generation": "base",
                "candidate_generation": committed,
            },
        )
        bootstrap.recover_before_services(self.paths)
        job = json.loads(self.paths.job.read_text("utf-8"))["job"]
        self.assertEqual(job["job_id"], current_job_id)
        self.assertEqual(job["state"], "queued")
        self.assertTrue(self.paths.pending.exists())
        self.assertEqual(self.paths.candidate.read_bytes(), b"new candidate")

    def test_other_slot_drops_foreign_app_generation_journal_without_touching_job(self) -> None:
        _make_generation(self.paths, "base")
        _point_to(self.paths, "base")
        current_job_id = "b" * 32
        _job(self.paths, current_job_id, "restarting")
        current_job = json.loads(self.paths.job.read_text("utf-8"))
        current_job["job"]["package_type"] = "full_system"
        current_job["job"]["restart_requested"] = False
        self.paths.job.write_text(json.dumps(current_job) + "\n", encoding="utf-8")
        self.paths.candidate.write_bytes(b"full-system candidate")
        bootstrap._write_journal(
            self.paths,
            {
                "schema_version": 1,
                "phase": "committed",
                "job_id": "c" * 32,
                "previous_generation": "base",
                "candidate_generation": "app-" + "c" * 32,
            },
        )
        self.paths.root_filesystem_uuid.write_text(
            "22222222-2222-4222-8222-222222222222\n", encoding="ascii"
        )
        bootstrap.recover_before_services(self.paths)
        job = json.loads(self.paths.job.read_text("utf-8"))["job"]
        self.assertEqual(job["job_id"], current_job_id)
        self.assertEqual(job["state"], "restarting")
        self.assertEqual(bootstrap.current_generation_id(self.paths), "base")
        self.assertTrue(self.paths.pending.exists())
        self.assertEqual(self.paths.candidate.read_bytes(), b"full-system candidate")

    def test_other_slot_fails_only_the_matching_interrupted_application_job(self) -> None:
        _make_generation(self.paths, "base")
        _point_to(self.paths, "base")
        job_id = "c" * 32
        _job(self.paths, job_id, "restarting")
        bootstrap._write_journal(
            self.paths,
            {
                "schema_version": 1,
                "phase": "trial",
                "job_id": job_id,
                "previous_generation": "base",
                "candidate_generation": "app-" + job_id,
                "readiness_boundary_monotonic_ns": 100,
            },
        )
        self.paths.root_filesystem_uuid.write_text(
            "33333333-3333-4333-8333-333333333333\n", encoding="ascii"
        )
        bootstrap.recover_before_services(self.paths)
        job = json.loads(self.paths.job.read_text("utf-8"))["job"]
        self.assertEqual(job["job_id"], job_id)
        self.assertEqual(job["state"], "failed")
        self.assertEqual(job["error_code"], "application_slot_changed")
        self.assertFalse(self.paths.pending.exists())
        self.assertFalse(self.paths.candidate.exists())

    def test_worker_import_path_stays_on_its_original_generation_after_switch(self) -> None:
        base = _make_generation(self.paths, "base")
        candidate_id = "app-" + "4" * 32
        _make_generation(self.paths, candidate_id)
        _point_to(self.paths, "base")
        pinned_source = str((base / "src").resolve())
        probe_name = "greia_update_generation_probe"
        (base / "src" / probe_name).mkdir()
        (base / "src" / probe_name / "__init__.py").write_text(
            "VALUE = 'original'\n", encoding="utf-8"
        )
        candidate_source = self.paths.generation_root / candidate_id / "src" / probe_name
        candidate_source.mkdir()
        (candidate_source / "__init__.py").write_text(
            "VALUE = 'candidate'\n", encoding="utf-8"
        )
        sys.modules.pop(probe_name, None)
        original_path = list(sys.path)
        try:
            bootstrap._pin_installed_source(self.paths)
            self.assertEqual(sys.path[0], pinned_source)
            bootstrap.switch_generation(self.paths, candidate_id)
            imported = __import__(probe_name)
            self.assertEqual(imported.VALUE, "original")
            self.assertEqual(sys.path[0], pinned_source)
        finally:
            sys.path[:] = original_path
            sys.modules.pop(probe_name, None)


if __name__ == "__main__":
    unittest.main()


class AbRootFilesystemIdentityTests(unittest.TestCase):
    def _ab_paths(self, root: Path, *, cmdline: str, layout: dict[str, object] | None = None):
        paths = _paths(root)
        paths.root_filesystem_uuid.unlink()
        layout_path = root / "etc/greia-os/layout/installed-layout.json"
        layout_path.parent.mkdir(parents=True, exist_ok=True)
        document = layout or {
            "schema_version": 1,
            "accepted_slot": "A",
            "system_a": {
                "partuuid": "deadbeef-02",
                "filesystem_uuid": "11111111-1111-4111-8111-111111111111",
            },
            "system_b": {
                "partuuid": "deadbeef-03",
                "filesystem_uuid": "22222222-2222-4222-8222-222222222222",
            },
        }
        layout_path.write_text(json.dumps(document), encoding="utf-8")
        cmdline_path = root / "proc/cmdline"
        cmdline_path.parent.mkdir(parents=True, exist_ok=True)
        cmdline_path.write_text(cmdline, encoding="ascii")
        from dataclasses import replace

        return replace(
            paths,
            layout_record=layout_path,
            proc_cmdline=cmdline_path,
        )

    def test_booted_slot_uuid_is_used_when_single_root_file_is_absent(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = self._ab_paths(
                Path(tmp), cmdline="BOOT_IMAGE=/boot/vmlinuz root=PARTUUID=deadbeef-02 ro\n"
            )
            self.assertEqual(
                bootstrap._current_root_uuid(paths),
                "11111111-1111-4111-8111-111111111111",
            )

    def test_candidate_boot_binds_its_own_slot_not_the_accepted_slot(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = self._ab_paths(
                Path(tmp), cmdline="root=PARTUUID=DEADBEEF-03 ro\n"
            )
            self.assertEqual(
                bootstrap._current_root_uuid(paths),
                "22222222-2222-4222-8222-222222222222",
            )

    def test_unknown_or_ambiguous_booted_partuuid_fails_closed(self) -> None:
        for cmdline in (
            "root=PARTUUID=deadbeef-99 ro\n",
            "root=PARTUUID=deadbeef-02 root=PARTUUID=deadbeef-03\n",
            "root=/dev/sda2 ro\n",
        ):
            with self.subTest(cmdline=cmdline), tempfile.TemporaryDirectory() as tmp:
                paths = self._ab_paths(Path(tmp), cmdline=cmdline)
                with self.assertRaises(bootstrap.BootstrapError):
                    bootstrap._current_root_uuid(paths)


class TerminalCandidateCleanupTests(unittest.TestCase):
    def test_terminal_update_clears_candidate_under_the_same_job_lock(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = _paths(Path(tmp))
            job = _job(paths, "a" * 32)
            paths.candidate.write_bytes(b"package")
            updated = bootstrap._job_state_update(
                paths,
                "applied",
                expected_job_id=job["job_id"],
                clear_candidate=True,
            )
            self.assertEqual(updated["state"], "applied")
            self.assertFalse(paths.candidate.exists())
            self.assertFalse(paths.pending.exists())

    def test_expected_job_identity_prevents_marking_a_new_upload(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = _paths(Path(tmp))
            job = _job(paths, "b" * 32)
            paths.candidate.write_bytes(b"new-package")
            with self.assertRaises(bootstrap.BootstrapError):
                bootstrap._job_state_update(
                    paths,
                    "applied",
                    expected_job_id="c" * 32,
                    clear_candidate=True,
                )
            self.assertTrue(paths.candidate.exists())
            self.assertEqual(bootstrap._read_job_locked(paths)["state"], "applying")
            self.assertTrue(job)
