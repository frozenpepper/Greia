"""Installer follow-ups: streamed install progress, keyboard erase hold, text floors.

Zero disk contact: the root service runs on the fake probe/engine harness of
``test_install_transaction_service``; the A/B byte counter wraps an
in-memory slot store; the UI runs in demo mode with fake input.
"""

from __future__ import annotations

import math
import os
import socket
import tempfile
import threading
import unittest
from pathlib import Path
from unittest import mock

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

import pygame  # noqa: E402

from greia_installer.engine import InstallProgress, InstallResult  # noqa: E402
from greia_installer.fresh_ab_install import _ProgressSlotStorage  # noqa: E402
from greia_installer.install_progress import (  # noqa: E402
    MIN_FRAME_INTERVAL_SECONDS,
    ProgressFrame,
    ProgressFrameError,
    ProgressReporter,
    overall_fraction,
    parse_progress_payload,
)
from greia_installer.install_transaction import INSTALLER_UI_UID  # noqa: E402
from greia_installer.main import InstallerApplication, InstallerPage  # noqa: E402
from greia_installer.presentation import text_floors, text_scale  # noqa: E402
from greia_installer.transaction_client import (  # noqa: E402
    InstallTransactionClient,
    TransactionClientError,
    socket_transport,
)
from greia_platform.privileged_channel import encode_response  # noqa: E402

from test_install_transaction_service import (  # noqa: E402
    UI_PEER,
    READY,
    ServiceHarness,
    eligible_digest,
    make_disk,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]


class FakeClock:
    def __init__(self) -> None:
        self.now = 100.0

    def __call__(self) -> float:
        return self.now


def _valid_payload(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "status": "RUNNING",
        "phase": "copy",
        "fraction": 0.4,
        "phase_fraction": 0.38,
        "done_bytes": 380,
        "total_bytes": 1000,
    }
    payload.update(overrides)
    return payload


class ProgressPayloadParsingTests(unittest.TestCase):
    def test_valid_payload_round_trips(self) -> None:
        frame = parse_progress_payload(_valid_payload())
        self.assertEqual(frame, ProgressFrame("copy", 0.4, 0.38, 380, 1000))
        self.assertEqual(parse_progress_payload(frame.to_payload()), frame)

    def test_phase_without_measurement_is_valid(self) -> None:
        frame = parse_progress_payload(
            _valid_payload(phase="check", phase_fraction=None, done_bytes=None, total_bytes=None)
        )
        self.assertIsNone(frame.phase_fraction)
        self.assertIsNone(frame.done_bytes)

    def test_malformed_payloads_are_refused(self) -> None:
        bad = (
            _valid_payload(phase="format-everything"),
            _valid_payload(phase=7),
            _valid_payload(status="INSTALLED"),
            _valid_payload(fraction=math.nan),
            _valid_payload(fraction=1.5),
            _valid_payload(fraction=-0.1),
            _valid_payload(fraction=True),
            _valid_payload(fraction="0.4"),
            _valid_payload(phase_fraction=math.inf),
            _valid_payload(done_bytes=1001),
            _valid_payload(done_bytes=-1),
            _valid_payload(done_bytes=1.5),
            _valid_payload(total_bytes=None),
            _valid_payload(total_bytes=1 << 60),
            _valid_payload(path="/dev/sda"),
        )
        for payload in bad:
            with self.subTest(payload=payload):
                with self.assertRaises(ProgressFrameError):
                    parse_progress_payload(payload)


class ProgressReporterTests(unittest.TestCase):
    def make(self) -> tuple[ProgressReporter, list[dict[str, object]], FakeClock]:
        frames: list[dict[str, object]] = []
        clock = FakeClock()
        return ProgressReporter(frames.append, clock=clock), frames, clock

    def test_updates_inside_one_phase_are_limited_to_two_hertz(self) -> None:
        reporter, frames, clock = self.make()
        for step in range(1, 1001):
            clock.now += 0.001  # 1,000 chunk writes in one second
            reporter.phase("copy", done_bytes=step, total_bytes=1000)
        # The first report plus at most one per 0.5 s.
        self.assertLessEqual(len(frames), 1 + int(1.0 / MIN_FRAME_INTERVAL_SECONDS))
        self.assertGreaterEqual(len(frames), 2)
        for earlier, later in zip(frames, frames[1:]):
            self.assertGreaterEqual(later["fraction"], earlier["fraction"])

    def test_phase_change_is_never_delayed(self) -> None:
        reporter, frames, clock = self.make()
        reporter.phase("check")
        clock.now += 0.01
        reporter.phase("partition")
        clock.now += 0.01
        reporter.phase("copy", done_bytes=0, total_bytes=10)
        self.assertEqual([frame["phase"] for frame in frames], ["check", "partition", "copy"])

    def test_overall_fraction_never_moves_backwards(self) -> None:
        reporter, frames, clock = self.make()
        reporter.phase("copy", done_bytes=9, total_bytes=10)
        clock.now += 1
        reporter.phase("check")  # an out-of-order milestone
        self.assertEqual(frames[-1]["phase"], "check")
        self.assertGreaterEqual(frames[-1]["fraction"], overall_fraction("copy", 0.9))

    def test_byte_counts_place_the_phase_on_the_overall_bar(self) -> None:
        reporter, frames, _clock = self.make()
        reporter.phase("copy", done_bytes=500, total_bytes=1000)
        self.assertAlmostEqual(frames[0]["phase_fraction"], 0.5)
        self.assertAlmostEqual(frames[0]["fraction"], overall_fraction("copy", 0.5), places=3)
        self.assertEqual(frames[0]["done_bytes"], 500)

    def test_failing_writer_disables_reporting_without_raising(self) -> None:
        calls: list[object] = []

        def broken(payload: object) -> None:
            calls.append(payload)
            raise BrokenPipeError("UI went away")

        reporter = ProgressReporter(broken, clock=FakeClock())
        reporter.phase("check")
        reporter.phase("partition")
        self.assertTrue(reporter.disabled)
        self.assertEqual(len(calls), 1)

    def test_unknown_phase_is_ignored(self) -> None:
        reporter, frames, _clock = self.make()
        reporter.phase("rm-rf")
        self.assertEqual(frames, [])

    def test_legacy_engine_stages_map_onto_shared_phases(self) -> None:
        reporter, frames, clock = self.make()
        for fraction, stage in (
            (0.01, "payload"),
            (0.02, "hardware"),
            (0.10, "erase"),
            (0.32, "copy"),
            (0.74, "hardware"),
            (0.78, "bootloader"),
            (1.0, "complete"),
        ):
            clock.now += 1
            reporter.engine_progress(InstallProgress(fraction, stage, "x"))
        self.assertEqual(
            [frame["phase"] for frame in frames],
            ["check", "check", "partition", "copy", "setup", "bootloader", "complete"],
        )
        self.assertEqual(frames[-1]["fraction"], 1.0)


class ProgressEngine:
    """Fake legacy engine that reports stages, then succeeds."""

    def __init__(self) -> None:
        self.requests: list[object] = []

    def install(self, request: object, on_progress: object = None) -> InstallResult:
        self.requests.append(request)
        for fraction, stage in ((0.01, "payload"), (0.10, "erase"), (0.32, "copy"), (0.78, "bootloader")):
            if on_progress is not None:
                on_progress(InstallProgress(fraction, stage, stage))  # type: ignore[operator]
        return InstallResult()


class StreamedProgressProtocolTests(unittest.TestCase):
    def _prepared(self, harness: ServiceHarness, client: InstallTransactionClient):
        return client.prepare(
            expected_target_identity=eligible_digest(harness),
            compatible_profile_id="profile-test",
            settings_snapshot=harness.prepare_snapshot(),
        )

    def test_progress_reaches_the_ui_live_over_the_unix_socket(self) -> None:
        from greia_installer.transaction_service import handle_connection

        harness = ServiceHarness([make_disk()])
        engine = ProgressEngine()
        harness.service.engine_factory = lambda: engine  # type: ignore[assignment]
        with tempfile.TemporaryDirectory(dir="/tmp") as temporary:
            path = Path(temporary) / "tx.sock"
            listener = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            listener.bind(str(path))
            listener.listen(2)

            def serve(count: int) -> None:
                for _ in range(count):
                    connection, _ = listener.accept()
                    handle_connection(connection, service=harness.service, peer_uid=INSTALLER_UI_UID)

            server = threading.Thread(target=serve, args=(2,), daemon=True)
            server.start()
            try:
                transport = socket_transport(path, timeout=10.0)
                client = InstallTransactionClient(transport)
                prepared = self._prepared(harness, client)
                frames: list[ProgressFrame] = []
                receipt = client.execute(
                    transaction_nonce=prepared.transaction_nonce,
                    plan_digest=prepared.plan_digest,
                    on_progress=frames.append,
                )
                server.join(timeout=10)
            finally:
                listener.close()
        self.assertEqual(receipt.target_identity, eligible_digest(harness))
        self.assertEqual(len(engine.requests), 1)
        self.assertEqual(
            [frame.phase for frame in frames], ["check", "partition", "copy", "bootloader"]
        )
        self.assertEqual([frame.fraction for frame in frames], [0.01, 0.10, 0.32, 0.78])

    def test_buffered_transport_relays_progress_then_verifies_the_final_answer(self) -> None:
        harness = ServiceHarness([make_disk()])
        engine = ProgressEngine()
        harness.service.engine_factory = lambda: engine  # type: ignore[assignment]

        def transport(raw: bytes) -> bytes:
            lines: list[bytes] = []
            final = harness.service.handle_request(
                raw, peer=UI_PEER, boot_state=READY, progress=lines.append
            )
            return b"".join(lines) + final

        client = InstallTransactionClient(transport)
        prepared = self._prepared(harness, client)
        frames: list[ProgressFrame] = []
        client.execute(
            transaction_nonce=prepared.transaction_nonce,
            plan_digest=prepared.plan_digest,
            on_progress=frames.append,
        )
        self.assertEqual(len(frames), 4)

    def test_malformed_progress_is_dropped_and_refusal_still_surfaces(self) -> None:
        bogus = encode_response("0123456789abcdef", "PROGRESS", {"status": "RUNNING", "phase": "nuke"})
        good = encode_response(
            "0123456789abcdef", "PROGRESS", ProgressFrame("copy", 0.5, 0.5).to_payload()
        )
        refusal = encode_response(
            "0123456789abcdef", "ERROR", {"status": "REFUSED", "reason": "selected disk disappeared"}
        )
        frames: list[ProgressFrame] = []
        client = InstallTransactionClient(lambda _raw: bogus + good + refusal)
        with self.assertRaisesRegex(TransactionClientError, "selected disk disappeared"):
            client.execute(transaction_nonce="n" * 32, plan_digest="d" * 64, on_progress=frames.append)
        self.assertEqual([frame.phase for frame in frames], ["copy"])

    def test_two_final_answers_fail_closed(self) -> None:
        answer = encode_response("0123456789abcdef", "EXECUTE", {"status": "INSTALLED"})
        client = InstallTransactionClient(lambda _raw: answer + answer)
        with self.assertRaises(TransactionClientError):
            client.execute(transaction_nonce="n" * 32, plan_digest="d" * 64)

    def test_execute_still_carries_only_nonce_and_digest(self) -> None:
        import json

        sent: list[bytes] = []

        def transport(raw: bytes) -> bytes:
            sent.append(raw)
            raise OSError("stop here")

        client = InstallTransactionClient(transport)
        with self.assertRaises(TransactionClientError):
            client.execute(transaction_nonce="n" * 32, plan_digest="d" * 64, on_progress=lambda _f: None)
        self.assertEqual(set(json.loads(sent[0])["params"]), {"transaction_nonce", "plan_digest"})


class MemorySlot:
    def __init__(self, capacity: int) -> None:
        self.data = bytearray(capacity)
        self.flushed = False

    @property
    def capacity_bytes(self) -> int:
        return len(self.data)

    def write_at(self, offset: int, data: bytes) -> None:
        self.data[offset : offset + len(data)] = data

    def read_at(self, offset: int, length: int) -> bytes:
        return bytes(self.data[offset : offset + length])

    def flush(self) -> None:
        self.flushed = True


class RecordingSink:
    def __init__(self, *, fail: bool = False) -> None:
        self.calls: list[tuple[str, int | None, int | None]] = []
        self.fail = fail

    def phase(self, phase_id: str, *, phase_fraction=None, done_bytes=None, total_bytes=None) -> None:
        self.calls.append((phase_id, done_bytes, total_bytes))
        if self.fail:
            raise RuntimeError("display broke")


class AbByteCountingTests(unittest.TestCase):
    def test_copy_and_readback_are_measured_against_the_payload_size(self) -> None:
        inner = MemorySlot(64)
        sink = RecordingSink()
        storage = _ProgressSlotStorage(inner, sink, total_bytes=32)
        self.assertEqual(storage.capacity_bytes, 64)
        storage.write_at(0, b"a" * 16)
        storage.write_at(16, b"b" * 16)
        storage.flush()
        self.assertEqual(storage.read_at(0, 16), b"a" * 16)
        storage.read_at(16, 16)
        self.assertTrue(inner.flushed)
        self.assertEqual(
            sink.calls,
            [("copy", 16, 32), ("copy", 32, 32), ("verify", 16, 32), ("verify", 32, 32)],
        )

    def test_a_failing_display_sink_never_breaks_the_slot_write(self) -> None:
        inner = MemorySlot(8)
        storage = _ProgressSlotStorage(inner, RecordingSink(fail=True), total_bytes=8)
        storage.write_at(0, b"12345678")
        self.assertEqual(storage.read_at(0, 8), b"12345678")


class FakeKeyState:
    def __init__(self, down: set[int]) -> None:
        self.down = down

    def get_pressed(self):
        down = self.down

        class _State:
            def __getitem__(self, key: int) -> bool:
                return key in down

        return _State()


class FakeMouse:
    def get_pressed(self, *, num_buttons=3):
        return (False, False, False)

    def get_pos(self):
        return (-1, -1)


class FakeInput:
    """Real pygame key constants with scripted keyboard/mouse state."""

    def __init__(self, down: set[int]) -> None:
        self.key = FakeKeyState(down)
        self.mouse = FakeMouse()

    def __getattr__(self, name: str):
        return getattr(pygame, name)


class KeyEvent:
    def __init__(self, key: int, repeat: bool = False) -> None:
        self.key = key
        self.repeat = repeat


class KeyboardEraseHoldTests(unittest.TestCase):
    def make_app(self) -> InstallerApplication:
        app = InstallerApplication(
            root=PROJECT_ROOT,
            payload=Path("/tmp/not-used.squashfs"),
            payload_digest=None,
            windowed=True,
            demo=True,
        )
        app.state.page = InstallerPage.CONFIRM
        return app

    def press(self, app: InstallerApplication, key: int, fake: FakeInput, *, repeat: bool = False) -> bool:
        fresh = app._note_key_down(KeyEvent(key, repeat))
        fake.key.down.add(key)
        return app._handle_confirm_key(key, fake, fresh=fresh)

    def release(self, app: InstallerApplication, key: int, fake: FakeInput) -> None:
        fake.key.down.discard(key)
        app._note_key_up(key)

    def test_enter_alone_never_starts_the_erase_hold(self) -> None:
        app = self.make_app()
        fake = FakeInput(set())
        self.assertTrue(self.press(app, pygame.K_RETURN, fake))
        self.assertIsNone(app._hold_started)
        self.assertEqual(app.state.page, InstallerPage.CONFIRM)
        self.assertTrue(app._confirm_keyboard)  # focus ring revealed on Back
        self.release(app, pygame.K_RETURN, fake)
        self.press(app, pygame.K_RETURN, fake)
        self.assertEqual(app.state.page, InstallerPage.WIFI)  # Enter on Back = Back

    def test_fresh_press_on_focused_erase_control_holds_for_two_seconds(self) -> None:
        app = self.make_app()
        fake = FakeInput(set())
        self.press(app, pygame.K_TAB, fake)
        self.release(app, pygame.K_TAB, fake)
        self.assertEqual(app._confirm_focus, "install")
        with mock.patch("greia_installer.main.time.monotonic", return_value=50.0):
            self.press(app, pygame.K_SPACE, fake)
        self.assertEqual(app._hold_started, 50.0)
        with mock.patch.object(app, "_start_installation") as start:
            with mock.patch("greia_installer.main.time.monotonic", return_value=51.0):
                app._update_install_hold(fake)
            start.assert_not_called()
            self.assertIsNotNone(app._hold_started)
            with mock.patch("greia_installer.main.time.monotonic", return_value=52.05):
                app._update_install_hold(fake)
            start.assert_called_once_with()
        self.assertIsNone(app._hold_started)

    def test_release_cancels_the_keyboard_hold(self) -> None:
        app = self.make_app()
        fake = FakeInput(set())
        self.press(app, pygame.K_RIGHT, fake)
        self.release(app, pygame.K_RIGHT, fake)
        self.press(app, pygame.K_RETURN, fake)
        self.assertIsNotNone(app._hold_started)
        self.release(app, pygame.K_RETURN, fake)
        self.assertIsNone(app._hold_started)
        with mock.patch.object(app, "_start_installation") as start:
            app._update_install_hold(fake)
            start.assert_not_called()

    def test_lost_keyup_is_caught_by_live_keyboard_state(self) -> None:
        app = self.make_app()
        fake = FakeInput(set())
        self.press(app, pygame.K_TAB, fake)
        self.release(app, pygame.K_TAB, fake)
        self.press(app, pygame.K_RETURN, fake)
        fake.key.down.discard(pygame.K_RETURN)  # SDL says released, no KEYUP seen
        with mock.patch.object(app, "_start_installation") as start:
            with mock.patch("greia_installer.main.time.monotonic", return_value=1e9):
                app._update_install_hold(fake)
            start.assert_not_called()
        self.assertIsNone(app._hold_started)

    def test_key_held_from_the_previous_page_and_auto_repeat_are_ignored(self) -> None:
        app = self.make_app()
        fake = FakeInput(set())
        # Enter went down on the Wi-Fi page and is still held on arrival.
        app.state.page = InstallerPage.WIFI
        app._note_key_down(KeyEvent(pygame.K_RETURN))
        fake.key.down.add(pygame.K_RETURN)
        app.state.page = InstallerPage.CONFIRM
        app._update_install_hold(fake)
        app._confirm_focus = "install"  # even with focus already on erase
        app._confirm_keyboard = True
        self.press(app, pygame.K_RETURN, fake)  # SDL auto-repeat of the held key
        self.press(app, pygame.K_RETURN, fake, repeat=True)
        self.assertIsNone(app._hold_started)
        self.assertEqual(app.state.page, InstallerPage.CONFIRM)
        # A genuine new press after releasing it does start the hold.
        self.release(app, pygame.K_RETURN, fake)
        self.press(app, pygame.K_RETURN, fake)
        self.assertIsNotNone(app._hold_started)

    def test_moving_focus_or_leaving_the_page_cancels(self) -> None:
        app = self.make_app()
        fake = FakeInput(set())
        self.press(app, pygame.K_TAB, fake)
        self.release(app, pygame.K_TAB, fake)
        self.press(app, pygame.K_RETURN, fake)
        self.press(app, pygame.K_TAB, fake)  # another key while holding
        self.assertIsNone(app._hold_started)
        self.assertEqual(app._confirm_focus, "back")
        self.release(app, pygame.K_RETURN, fake)
        self.release(app, pygame.K_TAB, fake)
        self.press(app, pygame.K_TAB, fake)
        self.press(app, pygame.K_RETURN, fake)
        app.state.page = InstallerPage.WIFI
        app._update_install_hold(fake)
        self.assertIsNone(app._hold_started)
        app.state.page = InstallerPage.CONFIRM
        app._update_install_hold(fake)
        self.assertEqual(app._confirm_focus, "back")  # re-entry resets focus

    def test_keyboard_hold_repaints_without_input(self) -> None:
        app = self.make_app()
        surface = pygame.Surface((1024, 600))
        before = app._render_signature(surface)
        fake = FakeInput(set())
        self.press(app, pygame.K_TAB, fake)
        self.assertNotEqual(app._render_signature(surface), before)


class ProgressUiStateTests(unittest.TestCase):
    def make_app(self) -> InstallerApplication:
        app = InstallerApplication(
            root=PROJECT_ROOT,
            payload=Path("/tmp/not-used.squashfs"),
            payload_digest=None,
            windowed=True,
            demo=True,
        )
        app.state.page = InstallerPage.INSTALLING
        return app

    def test_drained_progress_changes_the_repaint_signature(self) -> None:
        app = self.make_app()
        surface = pygame.Surface((1024, 600))
        with mock.patch("greia_installer.main.time.monotonic", return_value=10.0):
            before = app._render_signature(surface)
            app._events.put(InstallProgress(0.4, "copy", "Copying the system", 0.38))
            app._drain_worker_events()
            after = app._render_signature(surface)
            app._events.put(InstallProgress(0.41, "copy", "Copying the system", 0.40))
            app._drain_worker_events()
            later = app._render_signature(surface)
        self.assertNotEqual(before, after)
        self.assertNotEqual(after, later)

    def test_bar_never_moves_backwards_and_phase_clock_restarts(self) -> None:
        app = self.make_app()
        with mock.patch("greia_installer.main.time.monotonic", return_value=10.0):
            app._apply_progress(InstallProgress(0.5, "copy", "Copying the system", 0.5))
        with mock.patch("greia_installer.main.time.monotonic", return_value=20.0):
            app._apply_progress(InstallProgress(0.3, "copy", "Copying the system", 0.6))
        self.assertEqual(app.state.progress.fraction, 0.5)
        self.assertEqual(app._phase_since, 10.0)
        with mock.patch("greia_installer.main.time.monotonic", return_value=30.0):
            app._apply_progress(InstallProgress(0.72, "verify", "Checking the installed system", 0.0))
        self.assertEqual(app._phase_since, 30.0)

    def test_stalled_phase_reports_its_own_elapsed_time(self) -> None:
        app = self.make_app()
        with mock.patch("greia_installer.main.time.monotonic", return_value=100.0):
            app._apply_progress(InstallProgress(0.04, "check", "Checking the installation files"))
        self.assertIsNone(app._stalled_phase_seconds(100.0 + app.STALL_SECONDS - 1))
        self.assertEqual(app._stalled_phase_seconds(195.0), 95)
        surface = pygame.Surface((800, 480))
        with mock.patch("greia_installer.main.time.monotonic", return_value=195.0):
            app._draw(surface, pygame)  # draws the "still working" line

    def test_demo_engine_reports_measured_copy_and_verify(self) -> None:
        from greia_installer.main import DemoInstallationEngine

        seen: list[InstallProgress] = []
        with mock.patch("greia_installer.main.time.sleep"):
            DemoInstallationEngine().install(None, seen.append)  # type: ignore[arg-type]
        copies = [item for item in seen if item.stage == "copy"]
        self.assertTrue(copies and all(item.phase_fraction is not None for item in copies))
        fractions = [item.fraction for item in seen]
        self.assertEqual(fractions, sorted(fractions))
        self.assertEqual(seen[-1].stage, "complete")


class TextFloorTests(unittest.TestCase):
    def test_reference_panel_sizes(self) -> None:
        self.assertEqual(text_floors(600), (20, 16))
        self.assertEqual(text_floors(480), (17, 15))

    def test_scale_never_goes_below_the_floors(self) -> None:
        for height in range(480, 1201, 8):
            with self.subTest(height=height):
                scale = text_scale(height)
                body_floor, hint_floor = text_floors(height)
                self.assertGreaterEqual(scale.body, body_floor)
                self.assertGreaterEqual(scale.hint, hint_floor)
                self.assertGreaterEqual(scale.control, scale.body - 2)

    def test_installer_applies_the_floor_to_kit_labels(self) -> None:
        app = InstallerApplication(
            root=PROJECT_ROOT,
            payload=Path("/tmp/not-used.squashfs"),
            payload_digest=None,
            windowed=True,
            demo=True,
        )
        app._fonts(480)
        self.assertGreaterEqual(app._look().min_text_px, 15)
        self.assertGreaterEqual(app._body_px, 17)
        app._fonts(600)
        self.assertGreaterEqual(app._body_px, 20)
        self.assertGreaterEqual(app._hint_px, 16)


if __name__ == "__main__":
    unittest.main()
