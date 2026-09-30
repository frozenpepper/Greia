"""Platform-owned microphone input level service.

The microphone is an exclusive hardware device. The first implementation let the
Parent panel open it directly, which failed three ways on the reference Acer: the
panel held the device for the rest of the session because nothing ever released
it, stop() raced its own retry loop and orphaned an ``arecord`` that then held the
device forever, and a busy device was retried without pause, spinning a core.
Every later open - including the panel's own - then failed with "Device or
resource busy", which the panel could only report as a missing microphone.

This service is the single owner of the capture. It is socket-activated, so it
only exists while someone is actually watching a level, and it starts the capture
only while a client is connected. The panel reads a snapshot over the socket and
never touches the device, so there is no contention to lose and no orphan to leak.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import socket
import subprocess
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from greia_platform.microphone_level import (
    ARECORD_PATH,
    _CLIP_DBFS,
    DEFAULT_CAPTURE_DEVICE,
    MicrophoneLevel,
    measure_level,
)

#: The socket the panel connects to. It lives beside the existing platform
#: sockets under /run/greia-os.
MICROPHONE_LEVEL_SOCKET_PATH = "/run/greia-os/microphone-level.sock"

#: How often a connected client is sent the latest level. The eye cannot use more
#: than this, and a slow consumer must not make the capture loop spin.
PUBLISH_INTERVAL_SECONDS = 0.05

#: Read granularity of the capture stream, in bytes.
_READ_CHUNK = 1024


class MicrophoneCapture(Protocol):
    """The one operation this service needs from a capture source.

    Keeping it narrow means the device ownership can be tested with a fake, and a
    different capture backend can be substituted without touching the protocol.
    """

    def stream(self) -> "MicrophoneLevelStream": ...


@dataclass(frozen=True, slots=True)
class MicrophoneLevelStream:
    """An open capture of the microphone, owned by exactly one caller."""

    def levels(self) -> "Iterator[MicrophoneLevel]": ...
    def close(self) -> None: ...


class ArecordMicrophoneCapture:
    """Capture the microphone with a single long-lived ``arecord``.

    One process for the life of the connection, killed deterministically on close.
    Restarting a bounded burst was what made each new burst race the previous one
    for an exclusive device and lose.
    """

    def __init__(self, device: str = DEFAULT_CAPTURE_DEVICE) -> None:
        self._device = device
        self._process: subprocess.Popen[bytes] | None = None
        self._stop = threading.Event()
        self._lock = threading.Lock()

    def stream(self) -> MicrophoneLevelStream:
        # shutil.which, not os.path.exists: ARECORD_PATH is a bare command name,
        # and exists() on a bare name is always False, which made the service
        # refuse every connection and report a dead microphone on a machine with a
        # perfectly good one.
        if shutil.which(ARECORD_PATH) is None:
            raise OSError(f"{ARECORD_PATH} is not available on PATH")
        command = [
            ARECORD_PATH,
            "-q",
            "-D",
            self._device,
            "-t",
            "raw",
            "-f",
            "S16_LE",
            "-r",
            "48000",
            "-c",
            "2",
        ]
        process = subprocess.Popen(  # noqa: S603 - fixed argv, no shell
            command, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL
        )
        with self._lock:
            self._process = process
        return _ArecordLevelStream(process, self._device, self._stop)


class _ArecordLevelStream:
    """Yield one level per read of the capture pipe."""

    def __init__(
        self,
        process: subprocess.Popen[bytes],
        device: str,
        stop: threading.Event,
    ) -> None:
        self._process = process
        self._device = device
        self._stop = stop

    def levels(self):
        assert self._process.stdout is not None
        while not self._stop.is_set():
            # A blocking read is correct here: this runs on the capture thread, not
            # on any thread a client can observe, so capture latency can never
            # become UI latency.
            chunk = self._process.stdout.read(_READ_CHUNK)
            if not chunk:
                break
            rms, peak = measure_level(chunk)
            if rms is not None:
                yield MicrophoneLevel(
                    available=True,
                    rms_dbfs=rms,
                    peak_dbfs=peak,
                    clipping=peak >= _CLIP_DBFS,
                    device=self._device,
                )

    def close(self) -> None:
        self._stop.set()
        process = self._process
        if process.poll() is None:
            try:
                process.terminate()
                process.wait(timeout=0.5)
            except (OSError, subprocess.TimeoutExpired):
                try:
                    process.kill()
                    process.wait(timeout=0.5)
                except (OSError, subprocess.TimeoutExpired):
                    pass


def encode_level(level: MicrophoneLevel) -> bytes:
    """Serialise a level for the socket protocol."""

    return (
        json.dumps(
            {
                "available": level.available,
                "rms_dbfs": level.rms_dbfs,
                "peak_dbfs": level.peak_dbfs,
                "clipping": level.clipping,
                "device": level.device,
            },
            separators=(",", ":"),
        )
        + "\n"
    ).encode()


class _Session:
    """One active client, and the event that ends it."""

    def __init__(self) -> None:
        self.stop = threading.Event()
        #: Set once this session has closed its capture and released the device.
        self.released = threading.Event()


class MicrophoneLevelService:
    """Serve microphone levels to one client at a time over a unix socket.

    There is one device, so only one client can have it. A new connection takes
    the device over from the previous one rather than being refused: refusing
    meant a single client that vanished without closing - a killed process, a
    panel restarted underneath us - held the capture for good, and every later
    client was told the device was busy. That included the Parent panel, which
    then had no level, asked for no frames, and sat frozen. There is no queue to
    be honest about either: the most recent meter is the one a parent is looking
    at.
    """

    def __init__(
        self,
        *,
        socket_path: str = MICROPHONE_LEVEL_SOCKET_PATH,
        capture_factory=None,
        publish_interval: float = PUBLISH_INTERVAL_SECONDS,
    ) -> None:
        self._socket_path = socket_path
        self._capture_factory = capture_factory or ArecordMicrophoneCapture
        self._publish_interval = publish_interval
        self._sessions = threading.Lock()
        self._active: _Session | None = None

    def serve_forever(self) -> None:
        """Accept connections until the process is stopped."""

        path = Path(self._socket_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists():
            path.unlink()
        listener = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        listener.bind(self._socket_path)
        os.chmod(self._socket_path, 0o660)
        listener.listen(4)
        try:
            while True:
                try:
                    connection, _ = listener.accept()
                except OSError:
                    return
                thread = threading.Thread(
                    target=self._serve_client, args=(connection,), daemon=True
                )
                thread.start()
        finally:
            listener.close()
            if path.exists():
                path.unlink()

    def _serve_client(self, connection: socket.socket) -> None:
        """Stream levels to one client, releasing the device when it goes away."""

        session = _Session()
        with self._sessions:
            previous = self._active
            self._active = session
        if previous is not None:
            # Take the device over. Signalling the previous session is not enough:
            # its capture is closed by its own handler, and opening ours before
            # that happened raced the previous arecord for the exclusive device
            # and lost, so the new client saw a stream that died instantly. Wait
            # for the device to be genuinely released, bounded so a wedged
            # predecessor cannot block the meter forever.
            previous.stop.set()
            previous.released.wait(timeout=2.0)
        stream: MicrophoneLevelStream | None = None
        stop = session.stop
        latest: list[MicrophoneLevel] = [MicrophoneLevel.unavailable("starting")]
        pump: threading.Thread | None = None
        try:
            capture = self._capture_factory()
            stream = capture.stream()

            def pump_levels() -> None:
                try:
                    for level in stream.levels():  # type: ignore[union-attr]
                        latest[0] = level
                except (OSError, ValueError):
                    latest[0] = MicrophoneLevel.unavailable("read failed")
                finally:
                    stop.set()

            pump = threading.Thread(target=pump_levels, daemon=True)
            pump.start()
            while True:
                # Send before checking for exit: a capture that ends immediately
                # would otherwise stop the loop before the client ever saw a
                # level, which reads as a dead microphone rather than a finished
                # capture.
                try:
                    connection.sendall(encode_level(latest[0]))
                except OSError:
                    break
                if stop.is_set():
                    break
                time.sleep(self._publish_interval)
            if pump is not None:
                pump.join(timeout=0.5)
        except OSError:
            pass
        finally:
            if stream is not None:
                stream.close()
            try:
                connection.close()
            except OSError:
                pass
            with self._sessions:
                if self._active is session:
                    self._active = None
            session.released.set()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Serve microphone input levels")
    parser.add_argument("--socket", default=MICROPHONE_LEVEL_SOCKET_PATH)
    args = parser.parse_args(argv)
    MicrophoneLevelService(socket_path=args.socket).serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
