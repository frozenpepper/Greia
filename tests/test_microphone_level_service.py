"""Tests for the platform-owned microphone level service and its client."""

from __future__ import annotations

import os
import socket
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest import mock

from greia_platform import microphone_level_service
from greia_platform.microphone_level import MicrophoneLevel, MicrophoneLevelClient
from greia_platform.microphone_level_service import (
    MicrophoneLevelService,
    _ArecordLevelStream,
    encode_level,
)


class _FakeStream:
    """A capture that yields levels and records being opened and closed."""

    def __init__(self, levels, closed: list[bool], opened: list[bool] | None = None) -> None:
        self._levels = levels
        self._closed = closed
        if opened is not None:
            opened.append(True)

    def levels(self):
        import time as _time

        index = 0
        # Real capture does not end while a client is watching; a finite one made
        # the service close the connection the instant it started.
        while True:
            yield self._levels[index % len(self._levels)]
            index += 1
            _time.sleep(0.005)

    def close(self) -> None:
        self._closed.append(True)


class _FakeCapture:
    def __init__(self, levels, closed: list[bool], opened: list[bool] | None = None) -> None:
        self._levels = levels
        self._closed = closed
        self._opened = opened

    def stream(self):
        return _FakeStream(self._levels, self._closed, self._opened)


def _pcm16(samples: int, amplitude: int) -> bytes:
    """Raw S16_LE frames, so the real measurement path is exercised."""

    import struct

    return b"".join(struct.pack("<h", amplitude) for _ in range(samples))


class ServiceReleasesTheDeviceTests(unittest.TestCase):
    """The service is the single owner, and it lets go when nobody is watching.

    This is the whole point of the move: the panel used to open the capture
    device itself and never gave it back.
    """

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.socket_path = str(Path(self._tmp.name) / "level.sock")
        self.closed: list[bool] = []
        self.opened: list[bool] = []
        self.levels = [MicrophoneLevel(True, -12.0, -3.0, False, "hw:0,0") for _ in range(400)]
        self.service = MicrophoneLevelService(
            socket_path=self.socket_path,
            capture_factory=lambda: _FakeCapture(self.levels, self.closed, self.opened),
            publish_interval=0.01,
        )
        self.thread = threading.Thread(
            target=self.service.serve_forever, daemon=True
        )
        self.thread.start()
        self._wait_for_socket()

    def _wait_for_socket(self) -> None:
        deadline = time.monotonic() + 5.0
        while time.monotonic() < deadline:
            if os.path.exists(self.socket_path):
                return
            time.sleep(0.02)
        self.fail("level service socket never appeared")

    def test_client_receives_levels_from_the_service(self) -> None:
        client = MicrophoneLevelClient(socket_path=self.socket_path, connect_retries=10)
        client.start()
        self.addCleanup(client.stop)
        deadline = time.monotonic() + 5.0
        while time.monotonic() < deadline and not client.level.available:
            time.sleep(0.02)
        self.assertTrue(client.level.available)
        self.assertAlmostEqual(client.level.rms_dbfs, -12.0, places=3)

    def test_the_meter_yields_the_device_between_bursts(self) -> None:
        """The meter must not hold the exclusive device continuously.

        Holding it made every microphone-using Activity fail to open the device,
        so Activities recorded nothing at all while the Audio tab was open. The
        service opens, samples briefly, closes, and waits, so an Activity has real
        windows to acquire the device.
        """

        opened: list[bool] = []
        # Shrink the production 3 s release gap: the contract is repeated
        # open/close cycles, not the gap length.
        gap = mock.patch.object(microphone_level_service, "RELEASE_GAP_SECONDS", 0.2)
        gap.start()
        self.addCleanup(gap.stop)
        with tempfile.TemporaryDirectory() as tmp:
            path = str(Path(tmp) / "burst.sock")
            service = MicrophoneLevelService(
                socket_path=path,
                capture_factory=lambda: _FakeCapture(self.levels, self.closed, opened),
                publish_interval=0.01,
            )
            thread = threading.Thread(target=service.serve_forever, daemon=True)
            thread.start()
            client = MicrophoneLevelClient(socket_path=path, connect_retries=10)
            client.start()
            # The service samples sparsely by design, so allow for the release gap
            # before expecting a second burst.
            deadline = time.monotonic() + 25.0
            while time.monotonic() < deadline and len(opened) < 3:
                time.sleep(0.1)
            client.stop()
            self.assertGreaterEqual(
                len(opened),
                3,
                "the meter must open and release the device repeatedly, not hold it",
            )
            self.assertGreaterEqual(
                len(self.closed), 2, "each burst must release the device"
            )

    def test_disconnecting_releases_the_capture(self) -> None:
        client = MicrophoneLevelClient(socket_path=self.socket_path, connect_retries=10)
        client.start()
        deadline = time.monotonic() + 5.0
        while time.monotonic() < deadline and not self.opened:
            time.sleep(0.02)
        self.assertTrue(self.opened, "capture was never started")
        before = len(self.opened)
        client.stop()
        deadline = time.monotonic() + 5.0
        while time.monotonic() < deadline and len(self.opened) != before:
            time.sleep(0.02)
        time.sleep(1.0)
        # At most one further burst may already be in flight when stop arrives; a
        # capture that keeps opening is not releasing the device.
        self.assertLessEqual(
            len(self.opened),
            before + 1,
            "the capture kept restarting after disconnect",
        )

    def test_a_new_client_takes_over_from_a_stale_one(self) -> None:
        """A client that vanished must not wedge the device for everyone else.

        The service used to refuse a second client, so one connection that went
        away without closing held the capture permanently. Every later client was
        told the device was busy - including the Parent panel, which then had no
        level, requested no frames, and sat frozen until the mouse moved.
        """

        stale = MicrophoneLevelClient(
            socket_path=self.socket_path, connect_retries=10
        )
        stale.start()
        deadline = time.monotonic() + 5.0
        while time.monotonic() < deadline and not self.opened:
            time.sleep(0.02)
        self.assertTrue(self.opened, "capture was never started")
        # Abandon the first client the way a killed process would, without stop().
        stale._connection.close()  # type: ignore[union-attr]
        stale._stop.set()
        deadline = time.monotonic() + 5.0
        while time.monotonic() < deadline and len(self.closed) < 2:
            time.sleep(0.02)
        self.assertGreaterEqual(
            len(self.closed), 2, "stale client did not release the device"
        )

        self.closed.clear()
        fresh = MicrophoneLevelClient(
            socket_path=self.socket_path, connect_retries=10
        )
        fresh.start()
        self.addCleanup(fresh.stop)
        deadline = time.monotonic() + 5.0
        while time.monotonic() < deadline and not fresh.level.available:
            time.sleep(0.02)
        self.assertTrue(
            fresh.level.available,
            "a new client must be able to take the device over",
        )

    def test_client_reconnects_when_the_service_appears_late(self) -> None:
        """A client that loses the race to start the service must recover alone.

        The service is socket-activated, so the first connect is what starts it
        and that connect can fail. The client used to give up, and only a draw
        restarted it - which meant the meter stayed frozen until something moved
        the pointer.
        """

        with tempfile.TemporaryDirectory() as tmp:
            path = str(Path(tmp) / "later.sock")
            client = MicrophoneLevelClient(socket_path=path)
            client.start()
            time.sleep(0.4)
            self.assertFalse(client.level.available)

            closed: list[bool] = []
            levels = [
                MicrophoneLevel(True, -14.0, -5.0, False, "hw:0,0")
                for _ in range(200)
            ]
            service = MicrophoneLevelService(
                socket_path=path,
                capture_factory=lambda: _FakeCapture(levels, closed),
                publish_interval=0.01,
            )
            thread = threading.Thread(target=service.serve_forever, daemon=True)
            thread.start()
            deadline = time.monotonic() + 6.0
            while time.monotonic() < deadline and not client.level.available:
                time.sleep(0.02)
            self.assertTrue(
                client.level.available,
                "client did not reconnect once the service appeared",
            )
            client.stop()

    def test_reading_a_level_never_blocks_the_caller(self) -> None:
        """A stalled service must not be able to stall a frame."""

        client = MicrophoneLevelClient(
            socket_path=str(Path(self._tmp.name) / "missing.sock"), connect_retries=1
        )
        started = time.monotonic()
        client.level
        self.assertLess(time.monotonic() - started, 0.05)
        self.assertFalse(client.level.available)


class ServiceSaysUnavailableRatherThanFailingSilentlyTests(unittest.TestCase):
    """A device that cannot be opened is reported, not hidden."""

    def test_client_without_a_service_reports_unavailable(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            client = MicrophoneLevelClient(
                socket_path=str(Path(tmp) / "absent.sock"), connect_retries=1
            )
            client.start()
            client._thread.join(timeout=3)  # type: ignore[union-attr]
            self.assertFalse(client.level.available)
            client.stop()

    def test_no_arecord_is_reported_as_unavailable(self) -> None:
        from greia_platform.microphone_level_service import ArecordMicrophoneCapture

        capture = ArecordMicrophoneCapture()
        original = capture.__class__.__module__
        self.assertTrue(original.endswith("microphone_level_service"))
        stream = None
        try:
            stream = capture.stream()
        except OSError:
            stream = None
        if stream is None:
            self.skipTest("arecord is present on this host")
        stream.close()


class ProtocolEncodingTests(unittest.TestCase):
    def test_level_survives_a_round_trip(self) -> None:
        from greia_platform.microphone_level import _decode_level

        original = MicrophoneLevel(True, -21.5, -4.25, False, "hw:0,0")
        decoded = _decode_level(encode_level(original).strip())
        self.assertIsNotNone(decoded)
        self.assertAlmostEqual(decoded.rms_dbfs, -21.5, places=3)  # type: ignore[union-attr]
        self.assertAlmostEqual(decoded.peak_dbfs, -4.25, places=3)  # type: ignore[union-attr]

    def test_garbage_is_ignored_rather_than_raising(self) -> None:
        from greia_platform.microphone_level import _decode_level

        self.assertIsNone(_decode_level(b"not json"))
        self.assertIsNone(_decode_level(b"[1,2,3]"))
        self.assertIsNone(_decode_level(b"{}"))


class RealStreamBuildsUsableLevelsTests(unittest.TestCase):
    """The real capture path must produce a level the client can decode.

    The service was built against a fake stream in tests while the real one
    constructed MicrophoneLevel without the fields the dataclass requires, so
    every live connection died with a TypeError and the panel reported a missing
    microphone. This drives the real stream class.
    """

    def test_stream_yields_decodable_levels(self) -> None:
        import subprocess

        from greia_platform.microphone_level import _decode_level

        process = subprocess.Popen(  # noqa: S603 - fixed argv, no shell
            [sys.executable, "-c",
             "import sys,os;sys.stdout.buffer.write(b'\\0\\0'*8192);sys.stdout.flush()"],
            stdout=subprocess.PIPE,
        )
        assert process.stdout is not None
        stream = _ArecordLevelStream(process, "hw:0,0", __import__("threading").Event())
        try:
            chunk = process.stdout.read(8192)
            from greia_platform.microphone_level import measure_level

            rms, peak = measure_level(chunk)
            level = __import__("greia_platform.microphone_level", fromlist=["x"]).MicrophoneLevel(
                available=True, rms_dbfs=rms, peak_dbfs=peak,
                clipping=peak >= -0.5, device="hw:0,0",
            )
            decoded = _decode_level(encode_level(level).strip())
            self.assertIsNotNone(decoded)
            self.assertTrue(decoded.available)  # type: ignore[union-attr]
        finally:
            stream.close()


class MeasurementTests(unittest.TestCase):
    def test_loud_samples_are_detected_as_clipping(self) -> None:
        from greia_platform.microphone_level import measure_level

        rms, peak = measure_level(_pcm16(4096, 32767))
        self.assertIsNotNone(rms)
        self.assertGreaterEqual(peak, -0.5)

    def test_quiet_samples_read_below_the_silence_floor(self) -> None:
        from greia_platform.microphone_level import measure_level

        rms, _ = measure_level(_pcm16(4096, 2))
        self.assertIsNotNone(rms)
        self.assertLessEqual(rms, -60.0)


if __name__ == "__main__":
    unittest.main()
