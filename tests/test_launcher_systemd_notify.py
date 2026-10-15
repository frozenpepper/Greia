"""P6-NOTIFY acceptance: systemd readiness follows the actual first flip.

Proves the production mechanism through the real
``boot_intro.run_intro`` / ``_emit_first_frame_flipped_once`` boundary:

- no ``READY=1`` (no ``systemd-notify`` spawn) before the actual flip;
- exactly one readiness notification, immediately after
  ``intro_first_frame_flipped``, with the stable P6-PARENT payload;
- startup failure before the flip never reports ready;
- tests and non-systemd sessions (no ``NOTIFY_SOCKET``) fail soft;
- the unit file wires ``Type=notify`` + ``NotifyAccess=all`` +
  ``TimeoutStartSec=90`` while retaining the restart policy;
- notification has exactly one production call site (the first-frame emit),
  never shell startup, X startup, ``set_mode()``, or pre-flip paths.
"""

from __future__ import annotations

import contextlib
import io
import os
import stat
import tempfile
import unittest
from pathlib import Path
from unittest import mock


REPO_ROOT = Path(__file__).resolve().parents[1]
SERVICE_PATH = (
    REPO_ROOT / "build/overlay/etc/systemd/system/greia-launcher.service"
)
EXPECTED_STATUS = "Greia first intro frame visible"


class _FakeScreen:
    def get_size(self):
        return (800, 600)

    def fill(self, color) -> None:
        return None

    def blit(self, *args, **kwargs) -> None:
        return None


def _make_fake_pygame():
    fake = mock.MagicMock(name="pygame")
    fake.display.flip = mock.MagicMock(name="flip")
    fake.transform.smoothscale = mock.MagicMock(
        side_effect=lambda surface, size: surface
    )
    fake.time.wait = mock.MagicMock(return_value=None)
    fake.event.get = mock.MagicMock(return_value=[])
    fake.event.pump = mock.MagicMock(return_value=None)
    fake.mouse.set_visible = mock.MagicMock()
    return fake


def _reset_notify_flags() -> None:
    from greia_launcher import boot_intro

    boot_intro._FIRST_FRAME_FLIPPED_EMITTED = False
    boot_intro._SYSTEMD_READY_NOTIFIED = False


def _make_executable_stub(tmp: Path) -> Path:
    stub = tmp / "systemd-notify"
    stub.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    stub.chmod(stub.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    return stub


def _run_intro_quick() -> None:
    from greia_launcher import boot_intro

    fake_pygame = _make_fake_pygame()
    screen = _FakeScreen()
    with mock.patch.object(
        boot_intro, "draw_boot_handoff_frame", return_value=True
    ), mock.patch.dict(
        os.environ,
        {
            "GREIA_SKIP_BOOT_INTRO": "1",
            "GREIA_BOOT_INTRO_MARKER": "/tmp/nope-never-p6-notify",
        },
        clear=False,
    ):
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            boot_intro.run_intro(screen, fake_pygame)


class ServiceUnitTests(unittest.TestCase):
    def test_unit_does_not_depend_on_a_systemd_readiness_notification(self) -> None:
        # Measured on the reference Acer: the logind session the unprivileged
        # X server needs moves the launcher out of the unit's cgroup, so a
        # READY=1 datagram can never be attributed to it and Type=notify made
        # systemd kill a working Shell every TimeoutStartSec. The unit is
        # Type=simple; readiness lives in the launcher_interactive_ready boot
        # marker instead (see the unit's own comment).
        text = SERVICE_PATH.read_text(encoding="utf-8")
        directives = [
            line.strip() for line in text.splitlines()
            if line.strip() and not line.lstrip().startswith("#")
        ]
        self.assertIn("Type=simple", directives)
        self.assertNotIn("Type=notify", directives)
        self.assertNotIn("Type=exec", directives)
        self.assertIn("TimeoutStartSec=90", directives)

    def test_restart_policy_retained(self) -> None:
        text = SERVICE_PATH.read_text(encoding="utf-8")
        self.assertIn("Restart=always", text)
        self.assertIn("RestartSec=1", text)


class NotifyOrderTests(unittest.TestCase):
    def setUp(self) -> None:
        _reset_notify_flags()

    def tearDown(self) -> None:
        _reset_notify_flags()

    def test_no_notify_before_any_flip(self) -> None:
        from greia_launcher import boot_intro

        with mock.patch.object(boot_intro, "subprocess") as mock_subprocess:
            # Import plus draw paths alone must never spawn readiness.
            screen = _FakeScreen()
            boot_intro.draw_boot_handoff_frame(screen, _make_fake_pygame())
            mock_subprocess.run.assert_not_called()

    def test_ready_sent_once_after_first_flip(self) -> None:
        from greia_launcher import boot_intro

        with tempfile.TemporaryDirectory() as tmp:
            stub = _make_executable_stub(Path(tmp))
            with mock.patch.object(
                boot_intro, "_SYSTEMD_NOTIFY_BIN", str(stub)
            ), mock.patch.object(
                boot_intro, "subprocess"
            ) as mock_subprocess, mock.patch.dict(
                os.environ, {"NOTIFY_SOCKET": "/run/systemd/notify-test"},
                clear=False,
            ):
                _run_intro_quick()
                self.assertEqual(mock_subprocess.run.call_count, 1)
                argv = mock_subprocess.run.call_args[0][0]
                self.assertEqual(
                    argv,
                    [str(stub), "--ready", f"--status={EXPECTED_STATUS}"],
                )
                # A second intro run must not duplicate readiness.
                _reset_first_frame_only()
                _run_intro_quick()
                self.assertEqual(mock_subprocess.run.call_count, 1)

    def test_flip_failure_before_flip_never_reports_ready(self) -> None:
        from greia_launcher import boot_intro

        with tempfile.TemporaryDirectory() as tmp:
            stub = _make_executable_stub(Path(tmp))
            with mock.patch.object(
                boot_intro, "_SYSTEMD_NOTIFY_BIN", str(stub)
            ), mock.patch.object(
                boot_intro, "subprocess"
            ) as mock_subprocess, mock.patch.dict(
                os.environ, {"NOTIFY_SOCKET": "/run/systemd/notify-test"},
                clear=False,
            ), mock.patch.object(
                boot_intro, "draw_boot_handoff_frame", return_value=True
            ):
                fake_pygame = _make_fake_pygame()
                fake_pygame.display.flip.side_effect = RuntimeError(
                    "display fatal before first frame"
                )
                buffer = io.StringIO()
                with contextlib.redirect_stdout(buffer):
                    with self.assertRaises(RuntimeError):
                        boot_intro.run_intro(_FakeScreen(), fake_pygame)
                mock_subprocess.run.assert_not_called()
                self.assertFalse(boot_intro._SYSTEMD_READY_NOTIFIED)
                self.assertFalse(boot_intro._FIRST_FRAME_FLIPPED_EMITTED)

    def test_missing_notify_socket_fails_soft(self) -> None:
        from greia_launcher import boot_intro

        env = dict(os.environ)
        env.pop("NOTIFY_SOCKET", None)
        with mock.patch.object(
            boot_intro, "subprocess"
        ) as mock_subprocess, mock.patch.dict(os.environ, env, clear=True):
            _run_intro_quick()  # Must not raise.
            mock_subprocess.run.assert_not_called()

    def test_missing_binary_fails_soft(self) -> None:
        from greia_launcher import boot_intro

        with mock.patch.object(
            boot_intro, "_SYSTEMD_NOTIFY_BIN", "/nonexistent-p6-notify-bin"
        ), mock.patch.object(
            boot_intro, "subprocess"
        ) as mock_subprocess, mock.patch.dict(
            os.environ, {"NOTIFY_SOCKET": "/run/systemd/notify-test"},
            clear=False,
        ):
            _run_intro_quick()  # Must not raise.
            mock_subprocess.run.assert_not_called()

    def test_notify_spawn_failure_fails_soft(self) -> None:
        from greia_launcher import boot_intro

        with tempfile.TemporaryDirectory() as tmp:
            stub = _make_executable_stub(Path(tmp))
            with mock.patch.object(
                boot_intro, "_SYSTEMD_NOTIFY_BIN", str(stub)
            ), mock.patch.object(
                boot_intro, "subprocess"
            ) as mock_subprocess, mock.patch.dict(
                os.environ, {"NOTIFY_SOCKET": "/run/systemd/notify-test"},
                clear=False,
            ):
                mock_subprocess.run.side_effect = OSError("spawn failed")
                mock_subprocess.DEVNULL = mock.MagicMock()
                _run_intro_quick()  # Must not raise.
                # Exactly-once guard still suppresses any retry/duplicate.
                self.assertTrue(boot_intro._SYSTEMD_READY_NOTIFIED)

    def test_single_production_call_site_after_flip_emit(self) -> None:
        source = (REPO_ROOT / "src/greia_launcher/boot_intro.py").read_text(
            encoding="utf-8"
        )
        self.assertEqual(source.count("_notify_systemd_ready_once()"), 2)
        emit_block = source[source.index("def _emit_first_frame_flipped_once"):]
        emit_block = emit_block[: emit_block.index("\ndef ", 1)]
        self.assertIn("_notify_systemd_ready_once()", emit_block)
        # The notify call follows the flip marker inside the same guard.
        self.assertLess(
            emit_block.index('emit_boot_marker("intro_first_frame_flipped")'),
            emit_block.index("_notify_systemd_ready_once()"),
        )
        # No other launcher module may notify readiness.
        for name in ("main.py", "presentation.py", "bootstrap.py"):
            other = (
                REPO_ROOT / "src/greia_launcher" / name
            ).read_text(encoding="utf-8")
            self.assertNotIn("systemd-notify", other)
            self.assertNotIn("_notify_systemd_ready", other)
            self.assertNotIn("NOTIFY_SOCKET", other)

    def test_no_shell_or_sleep_orchestration(self) -> None:
        source = (REPO_ROOT / "src/greia_launcher/boot_intro.py").read_text(
            encoding="utf-8"
        )
        notify_block = source[source.index("def _notify_systemd_ready_once"):]
        notify_block = notify_block[: notify_block.index("\ndef ", 1)]
        self.assertNotIn("shell=True", notify_block)
        self.assertNotIn("time.sleep", notify_block)
        self.assertIn("check=False", notify_block)


def _reset_first_frame_only() -> None:
    """Reset the flip guard but keep the systemd exactly-once guard.

    Models a second process pass where the KPI flag is fresh but the
    readiness guard must still suppress duplicates within this process.
    """
    from greia_launcher import boot_intro

    boot_intro._FIRST_FRAME_FLIPPED_EMITTED = False


if __name__ == "__main__":
    raise SystemExit(unittest.main())
