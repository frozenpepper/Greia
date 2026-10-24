from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from greia_platform.privileged_channel import PeerCredential, encode_response
from greia_platform.update_activation import request_profile_picker_restart
from greia_platform.update_privileged import (
    UPDATE_PRIVILEGED_PANEL_OPS,
    UpdatePrivilegedEndpoint,
    UpdatePrivilegedError,
    build_request,
    read_response,
)


class _Authority:
    def __init__(self) -> None:
        self.calls: list[str] = []

    def candidate_summary(self):
        return type("Summary", (), {"present": False, "release_id": "", "bundle_sha256": ""})()

    def layout_summary(self):
        return {"single_root": True, "slots": ["A"]}

    def status_payload(self):
        self.calls.append("STATUS")
        return {"status": "OK", "identity": {"release_id": "test"}}

    def verify_current_candidate(self):
        self.calls.append("VERIFY_CURRENT_CANDIDATE")
        return self.candidate_summary()

    def stage_current_candidate(self):
        self.calls.append("STAGE_CURRENT_CANDIDATE")
        return {"staged": True}

    def arm_current_candidate(self):
        self.calls.append("ARM_CURRENT_CANDIDATE")
        return {"armed": True}

    def confirm_boot_health(self):
        self.calls.append("CONFIRM_BOOT_HEALTH")
        return {"confirmed": True}

    def reconcile(self):
        self.calls.append("RECONCILE")
        return {"state": "none"}

    def request_restart(self):
        self.calls.append("REQUEST_RESTART")
        return {"status": "REFUSED", "reason": "not staged", "state": "refused"}


class UpdatePrivilegedBridgeTests(unittest.TestCase):
    def test_installed_module_entrypoint_keeps_system_updates_canonical(self) -> None:
        import runpy
        import sys
        from unittest import mock

        from greia_platform import system_updates

        observed: dict[str, bool] = {}

        def entrypoint_probe(_argv: list[str] | None = None) -> int:
            entry_module = sys.modules["__main__"]
            observed["shared_exception_identity"] = (
                entry_module.UpdateBackendUnavailable
                is system_updates.UpdateBackendUnavailable
            )
            return 73

        with mock.patch.object(system_updates, "main", side_effect=entrypoint_probe):
            with self.assertRaises(SystemExit) as exited:
                runpy.run_module(
                    "greia_platform.update_privileged",
                    run_name="__main__",
                    alter_sys=True,
                )
        self.assertEqual(exited.exception.code, 73)
        self.assertIs(observed.get("shared_exception_identity"), True)

    def test_panel_allowlist_excludes_health_confirmation_and_arm(self) -> None:
        self.assertEqual(
            UPDATE_PRIVILEGED_PANEL_OPS,
            frozenset(
                {
                    "STATUS",
                    "VERIFY_CURRENT_CANDIDATE",
                    "STAGE_CURRENT_CANDIDATE",
                    "RECONCILE",
                    "REQUEST_RESTART",
                }
            ),
        )
        authority = _Authority()
        endpoint = UpdatePrivilegedEndpoint(
            authority, allowed_uids=(0, 1003), root_uid=0, panel_uid=1003
        )
        panel = PeerCredential(uid=1003)
        _, op, status = read_response(
            endpoint.handle_request(
                build_request("STATUS"), peer=panel, boot_state="update_ready"
            )
        )
        self.assertEqual(op, "STATUS")
        self.assertEqual(status["status"], "OK")
        for op in sorted(UPDATE_PRIVILEGED_PANEL_OPS - {"STATUS"}):
            with self.subTest(operation=op):
                _, returned_op, _payload = read_response(
                    endpoint.handle_request(
                        build_request(op), peer=panel, boot_state="update_ready"
                    )
                )
                self.assertEqual(returned_op, op)
        for op in ("ARM_CURRENT_CANDIDATE", "CONFIRM_BOOT_HEALTH"):
            with self.subTest(operation=op):
                with self.assertRaisesRegex(UpdatePrivilegedError, "not authorized"):
                    endpoint.handle_request(
                        build_request(op), peer=panel, boot_state="update_ready"
                    )
        self.assertNotIn("ARM_CURRENT_CANDIDATE", authority.calls)
        self.assertNotIn("CONFIRM_BOOT_HEALTH", authority.calls)

    def test_root_retains_health_and_arm_operations(self) -> None:
        authority = _Authority()
        endpoint = UpdatePrivilegedEndpoint(authority)
        for op in ("ARM_CURRENT_CANDIDATE", "CONFIRM_BOOT_HEALTH"):
            with self.subTest(operation=op):
                endpoint.handle_request(
                    build_request(op), peer=PeerCredential(uid=0), boot_state="update_ready"
                )
        self.assertEqual(
            authority.calls,
            ["ARM_CURRENT_CANDIDATE", "CONFIRM_BOOT_HEALTH"],
        )

    def test_client_accepts_only_panel_ops_and_returns_payload(self) -> None:
        from greia_platform.update_client import (
            UpdatePrivilegedClient,
            UpdatePrivilegedClientError,
        )

        class _Connection:
            def __init__(self, *_args: object) -> None:
                self.sent = b""
                self.response = encode_response(
                    "0123456789abcdef", "STATUS", {"status": "OK"}
                )

            def __enter__(self):
                return self

            def __exit__(self, *_args: object) -> None:
                return None

            def settimeout(self, value: float) -> None:
                self.timeout = value

            def connect(self, _path: str) -> None:
                return None

            def sendall(self, data: bytes) -> None:
                self.sent = data

            def shutdown(self, _how: int) -> None:
                return None

            def recv(self, size: int) -> bytes:
                response, self.response = self.response[:size], self.response[size:]
                return response

        client = UpdatePrivilegedClient("/tmp/greia-update-test.sock", socket_factory=_Connection)
        self.assertEqual(client.request("STATUS"), {"status": "OK"})
        with self.assertRaises(UpdatePrivilegedClientError):
            client.request("CONFIRM_BOOT_HEALTH")


class ProfilePickerRestartTests(unittest.TestCase):
    def _session(self, root: Path) -> tuple[object, Path, Path]:
        from greia_platform.profiles import ActiveProfileSession

        run_dir = root / "run"
        run_dir.mkdir(parents=True)
        status = run_dir / "active-profile.json"
        lock = root / "runtime" / "profile-session.lock"
        fence = root / "runtime" / "restart-pending.json"
        fence.parent.mkdir(parents=True)
        return ActiveProfileSession(status, lock_path=lock, restart_fence_path=fence), status, fence

    def test_restart_holds_profile_lock_then_fences_handoff(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            session, _status, fence = self._session(root)
            session.clear()
            events: list[str] = []

            def arm() -> dict[str, object]:
                events.append("arm")
                self.assertFalse(fence.exists())
                return {"armed": True}

            def handoff() -> subprocess.CompletedProcess[bytes]:
                events.append("reboot")
                self.assertTrue(fence.is_file())
                self.assertEqual(fence.stat().st_mode & 0o777, 0o644)
                return subprocess.CompletedProcess([], 0)

            response = request_profile_picker_restart(
                session=session,
                fence_path=fence,
                recheck=lambda: events.append("recheck") or {"ready": True, "journal_state": "update_staged"},
                arm_candidate=arm,
                reboot_handoff=handoff,
                request_id_factory=lambda: "1" * 32,
            )
            self.assertEqual(response["status"], "RESTART_ACCEPTED")
            self.assertEqual(response["state"], "systemd_accepted")
            self.assertEqual(events, ["recheck", "arm", "reboot"])

    def test_cross_process_profile_start_waits_then_observes_restart_fence(self) -> None:
        """A launcher process cannot claim a child across restart handoff."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            session, status, fence = self._session(root)
            session.clear()
            script = r"""
import sys
from pathlib import Path
from greia_platform.profiles import ActiveProfileSession, ChildProfile, ProfileError
status, lock, fence = map(Path, sys.argv[1:])
session = ActiveProfileSession(status, lock_path=lock, restart_fence_path=fence)
print("activation-attempt", flush=True)
try:
    session.write(ChildProfile("11111111111141118111111111111111", "Nora", "rainbow", None, False))
except ProfileError as exc:
    print(f"refused:{exc}", flush=True)
else:
    print("unexpected-activation", flush=True)
    raise SystemExit(3)
"""
            child: subprocess.Popen[str] | None = None

            def recheck() -> dict[str, object]:
                nonlocal child
                env = dict(os.environ)
                repo_root = Path(__file__).resolve().parents[1]
                env["PYTHONPATH"] = str(repo_root / "src")
                child = subprocess.Popen(
                    [
                        sys.executable,
                        "-c",
                        script,
                        str(status),
                        str(session.lock_path),
                        str(fence),
                    ],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    env=env,
                )
                assert child.stdout is not None
                self.assertEqual(child.stdout.readline().strip(), "activation-attempt")
                with self.assertRaises(subprocess.TimeoutExpired):
                    child.wait(timeout=0.05)
                return {"ready": True, "journal_state": "update_staged"}

            try:
                response = request_profile_picker_restart(
                    session=session,
                    fence_path=fence,
                    recheck=recheck,
                    arm_candidate=lambda: {"armed": True},
                    reboot_handoff=lambda: (
                        self.assertTrue(fence.is_file())
                        or subprocess.CompletedProcess([], 0)
                    ),
                    request_id_factory=lambda: "3" * 32,
                )
                self.assertEqual(response["status"], "RESTART_ACCEPTED")
                assert child is not None
                stdout, stderr = child.communicate(timeout=5)
                self.assertEqual(child.returncode, 0, stderr)
                self.assertIn("refused:system restart is pending", stdout)
                self.assertEqual(status.read_text(encoding="utf-8"), '{"schema":1,"state":"profile_picker_idle"}\n')
            finally:
                if child is not None and child.poll() is None:
                    child.kill()
                    child.wait(timeout=5)

    def test_rejected_arm_does_not_leave_profile_fence(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            session, _status, fence = self._session(root)
            session.clear()
            response = request_profile_picker_restart(
                session=session,
                fence_path=fence,
                recheck=lambda: {"ready": True, "journal_state": "update_staged"},
                arm_candidate=lambda: {"armed": False},
                reboot_handoff=lambda: self.fail("reboot must not be requested"),
                request_id_factory=lambda: "2" * 32,
            )
            self.assertEqual(response["status"], "REFUSED")
            self.assertFalse(fence.exists())

    def test_restart_refuses_active_or_malformed_profile_and_does_not_arm(self) -> None:
        from greia_platform.profiles import ProfileError

        for active_state in (
            b'{"profile_id":"11111111111141118111111111111111"}\n',
            b"{broken\n",
        ):
            with self.subTest(active_state=active_state):
                with tempfile.TemporaryDirectory() as directory:
                    root = Path(directory)
                    session, status, fence = self._session(root)
                    status.write_bytes(active_state)
                    armed: list[bool] = []
                    result = request_profile_picker_restart(
                        session=session,
                        fence_path=fence,
                        recheck=lambda: {"ready": True, "journal_state": "update_staged"},
                        arm_candidate=lambda: armed.append(True) or {"armed": True},
                        reboot_handoff=lambda: subprocess.CompletedProcess([], 0),
                    )
                    self.assertEqual(result["status"], "REFUSED")
                    self.assertFalse(armed)
                    self.assertFalse(fence.exists())

    def test_unknown_profile_state_errors_fail_closed(self) -> None:
        from greia_platform.profiles import ActiveProfileSession, ProfileError

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            status = root / "active.json"
            lock = root / "profile.lock"
            status.symlink_to(root / "missing.json")
            session = ActiveProfileSession(status, lock_path=lock)
            with self.assertRaises(ProfileError):
                with session.profile_picker_restart_guard():
                    self.fail("unreadable active-profile state must refuse restart")


if __name__ == "__main__":
    unittest.main()
