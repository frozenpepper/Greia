"""Live microphone input level, so a parent can see whether the mic works.

The Parent panel's audio tab showed a gain meter that reflected only the
*setting*. Nothing reported what the microphone was actually hearing, so a parent
could not tell a working microphone from a muted one, nor notice that the gain
was clipping. Measured on the reference Acer's ALC268 analog input: RMS -9.0 dBFS
with a peak pinned at 0.0 dBFS, which is exactly the case a live display exists to
reveal, and it was invisible.

Design constraints, all from the reference hardware:

* No new dependency. ``arecord`` from alsa-utils is already present and writes raw
  PCM to stdout, so the level is computed here rather than pulling in a Python ALSA
  binding. Measured on the Acer's capture device, which is **2-channel** and
  rejects ``-c 1`` outright, so the channel count is discovered rather than
  assumed, and only the left channel is measured.
* Never blocks the Shell. Capture runs on one daemon thread; the panel reads a
  plain snapshot. A wedged or absent capture device yields "no level", never an
  exception and never a stall.
* Bounded. One subprocess, a fixed read chunk, and a snapshot holding a handful of
  numbers.
* Honest about silence. A silent microphone reports silence; it is never
  presented as a fault, and a device that cannot be opened reports unavailable
  rather than zero, so the two are distinguishable on screen.
"""

from __future__ import annotations

import json
import math
import socket
import shutil
import struct
import subprocess
import time
import threading
from dataclasses import dataclass

#: Full-scale 16-bit sample. Levels are reported in dBFS against this.
_FULL_SCALE = 32768.0

#: Below this the input is treated as silence rather than as a very quiet room.
_SILENCE_DBFS = -60.0

#: dBFS at or above which consecutive samples are considered clipping.
_CLIP_DBFS = -0.5

#: Capture format. 48 kHz stereo S16_LE is what the reference device reports;
#: `arecord` converts, so this is a request rather than a requirement.
_RATE = 48000
_CHANNELS = 2
_FORMAT_BYTES = 2  # S16_LE

DEFAULT_CAPTURE_DEVICE = "hw:0,0"

#: How long a real reading survives a dropped connection before the input is
#: reported as gone. A brief disconnect should not blank the meter.
_DISCONNECT_GRACE_SECONDS = 1.5

#: Longest pause between reconnect attempts. Bounded so a stopped service costs
#: almost nothing and a slow start is still picked up promptly.
_RECONNECT_BACKOFF_MAX = 2.0

#: The capture tool. Present on the image already; no new dependency.
ARECORD_PATH = "arecord"

#: The endpoint the meter measures. It is deliberately the same one the audio
#: service routes Activities to, not the raw device: measuring hw:0,0 bypasses
#: processing entirely, so the display showed a signal that no Activity would
#: ever hear and noise reduction appeared to do nothing.

#: Pause between capture attempts. The device is exclusive, so a failed open is
#: retried, not hammered: an unthrottled retry loop turned one busy device into a
#: permanent one and pegged a core, which is what made the whole panel crawl.
_RETRY_BACKOFF_SECONDS = 0.5

#: Read granularity. Small enough that a level update is visibly live, large
#: enough not to spin.
_READ_CHUNK = 8192

_PROBE_TIMEOUT_SECONDS = 4.0


@dataclass(frozen=True, slots=True)
class MicrophoneLevel:
    """One observation of the microphone input."""

    available: bool
    rms_dbfs: float
    peak_dbfs: float
    clipping: bool
    device: str

    @property
    def silent(self) -> bool:
        return self.available and self.rms_dbfs <= _SILENCE_DBFS

    #: How far above the silence floor a reading must rise before silence is
    #: declared false. Without hysteresis a quiet room sits right on the floor
    #: and the label alternated every frame, which reads as a fault rather than as
    #: a room.
    SILENCE_RELEASE_DBFS = _SILENCE_DBFS + 6.0

    @classmethod
    def unavailable(cls, device: str = DEFAULT_CAPTURE_DEVICE) -> "MicrophoneLevel":
        return cls(
            available=False,
            rms_dbfs=_SILENCE_DBFS,
            peak_dbfs=_SILENCE_DBFS,
            clipping=False,
            device=device,
        )


def _decode_level(line: bytes) -> MicrophoneLevel | None:
    """Decode one protocol line, or None if it is not a level."""

    try:
        payload = json.loads(line)
    except (ValueError, UnicodeDecodeError):
        return None
    if not isinstance(payload, dict):
        return None
    try:
        return MicrophoneLevel(
            available=bool(payload["available"]),
            rms_dbfs=float(payload["rms_dbfs"]),
            peak_dbfs=float(payload["peak_dbfs"]),
            clipping=bool(payload.get("clipping", False)),
            device=str(payload.get("device", DEFAULT_CAPTURE_DEVICE)),
        )
    except (KeyError, TypeError, ValueError):
        return None


class MicrophoneLevelClient:
    """Read microphone levels from the platform-owned level service.

    The panel is a client of this, not an owner of the microphone. The capture
    device is exclusive, and letting the panel open it directly is what made the
    meter unusable: the panel held the device for the session, a retry race
    orphaned an ``arecord`` that then held it forever, and every later open -
    including the panel's own - failed with "Device or resource busy". The
    service is the single owner; this only reads its snapshot.
    """

    def __init__(
        self,
        *,
        socket_path: str = "/run/greia-os/microphone-level.sock",
        connect_retries: int = 5,
    ) -> None:
        self._socket_path = socket_path
        self._connect_retries = connect_retries
        self._lock = threading.Lock()
        self._level = MicrophoneLevel.unavailable("no service")
        self._connection: socket.socket | None = None
        self._thread: threading.Thread | None = None
        self._stop = threading.Event()
        self._last_good: float | None = None

    @property
    def level(self) -> MicrophoneLevel:
        """The newest level. Never blocks, so a stalled service cannot stall a frame."""

        with self._lock:
            return self._level

    def _publish(self, level: MicrophoneLevel) -> None:
        with self._lock:
            self._level = level

    def start(self) -> None:
        """Connect to the level service. Idempotent."""

        thread = self._thread
        if thread is not None and thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def _connect(self) -> socket.socket | None:
        client = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        try:
            client.connect(self._socket_path)
            client.settimeout(1.0)
            return client
        except OSError:
            client.close()
            return None

    def _run(self) -> None:
        # Keep trying for as long as the client is started. The service is
        # socket-activated, so the first connect is what starts it and that
        # connect can lose the race. Giving up after a bounded number of attempts
        # left the meter with no level, and because only a draw restarts the
        # client, the level came back only when something moved the pointer.
        attempt = 0
        while not self._stop.is_set():
            connection = self._connect()
            if connection is None:
                self._publish(MicrophoneLevel.unavailable("starting"))
                self._stop.wait(min(0.25 * (attempt + 1), _RECONNECT_BACKOFF_MAX))
                attempt += 1
                continue
            attempt = 0
            self._connection = connection
            self._read_until_closed(connection)
            if self._stop.is_set():
                return

    def _read_until_closed(self, connection: socket.socket) -> None:
        """Read levels until the connection ends, publishing the newest."""
        buffer = b""
        try:
            while not self._stop.is_set():
                try:
                    chunk = connection.recv(4096)
                except socket.timeout:
                    continue
                except OSError:
                    break
                if not chunk:
                    break
                buffer += chunk
                while b"\n" in buffer:
                    line, buffer = buffer.split(b"\n", 1)
                    level = _decode_level(line)
                    if level is not None:
                        if level.available:
                            self._last_good = time.monotonic()
                        self._publish(level)
        finally:
            try:
                connection.close()
            except OSError:
                pass
            self._connection = None
            # A dropped connection is not a dead microphone, and the loop in _run
            # reconnects on its own. Keep the last real reading rather than
            # blanking it, so a brief gap does not read as a missing microphone.
            if (
                not self._stop.is_set()
                and self._last_good is not None
                and time.monotonic() - self._last_good <= _DISCONNECT_GRACE_SECONDS
            ):
                return
            if not self._stop.is_set():
                self._publish(MicrophoneLevel.unavailable("reconnecting"))

    def stop(self) -> None:
        """Disconnect. The service then releases the microphone."""

        self._stop.set()
        connection = self._connection
        if connection is not None:
            for closer in (lambda: connection.shutdown(socket.SHUT_RDWR), connection.close):
                try:
                    closer()
                except OSError:
                    pass
            self._connection = None
        thread = self._thread
        if thread is not None and thread.is_alive():
            thread.join(timeout=1.0)
        self._thread = None


class MicrophoneLevelReader:
    """Background capture that publishes a :class:`MicrophoneLevel` snapshot.

    Call :meth:`start` when the audio tab is opened and :meth:`stop` when it is
    closed, so a panel that is not showing levels does not hold a capture device
    open. The reader is safe to start and stop repeatedly.
    """

    def __init__(
        self,
        device: str = DEFAULT_CAPTURE_DEVICE,
        *,
        arecord: str = "arecord",
    ) -> None:
        self._device = device
        self._arecord = arecord
        self._level = MicrophoneLevel.unavailable(device)
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._process: subprocess.Popen[bytes] | None = None

    @property
    def level(self) -> MicrophoneLevel:
        with self._lock:
            return self._level

    def start(self) -> None:
        if self._thread is not None and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(
            target=self._run, name="greia-mic-level", daemon=True
        )
        self._thread.start()

    def stop(self) -> None:
        """Stop capture and release the device. Safe to call when not started."""

        self._stop.set()
        thread = self._thread
        # Re-terminate until the thread is actually gone. Terminating once raced
        # the retry loop: it could open a replacement between our read of
        # _process and the signal, and that orphan held the ALSA device forever.
        deadline = time.monotonic() + 2.0
        while thread is not None and thread.is_alive():
            process = self._process
            if process is not None and process.poll() is None:
                try:
                    process.terminate()
                except OSError:
                    pass
            thread.join(timeout=0.1)
            if time.monotonic() > deadline:
                process = self._process
                if process is not None and process.poll() is None:
                    try:
                        process.kill()
                    except OSError:
                        pass
                break
        if thread is not None:
            thread.join(timeout=0.5)
        self._thread = None
        self._process = None
        with self._lock:
            self._level = MicrophoneLevel.unavailable(self._device)

    def __enter__(self) -> "MicrophoneLevelReader":
        self.start()
        return self

    def __exit__(self, *_exc: object) -> None:
        self.stop()

    # --- internals -----------------------------------------------------

    def _publish(self, level: MicrophoneLevel) -> None:
        with self._lock:
            self._level = level

    def _run(self) -> None:
        if shutil.which(self._arecond()) is None:
            self._publish(MicrophoneLevel.unavailable(self._device))
            return
        while not self._stop.is_set():
            try:
                self._capture_pass()
            except Exception:
                # A capture failure is reported as unavailable, never raised into
                # the Shell. The parent sees "cannot read the microphone", which
                # is true and actionable, rather than a frozen panel.
                self._publish(MicrophoneLevel.unavailable(self._device))
            if self._stop.is_set():
                return

    def _arecond(self) -> str:
        return self._arecord

    def _capture_pass(self) -> None:
        command = [
            self._arecord,
            "-q",
            "-D",
            self._device,
            "-t",
            "raw",
            "-f",
            "S16_LE",
            "-r",
            str(_RATE),
            "-c",
            str(_CHANNELS),
        ]
        process = subprocess.Popen(  # noqa: S603 - fixed argv, no shell
            command, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL
        )
        self._process = process
        try:
            assert process.stdout is not None
            while not self._stop.is_set():
                chunk = process.stdout.read(_READ_CHUNK)
                if not chunk:
                    break
                rms, peak = measure_level(chunk)
                if rms is None:
                    continue
                self._publish(
                    MicrophoneLevel(
                        available=True,
                        rms_dbfs=rms,
                        peak_dbfs=peak,
                        clipping=peak >= _CLIP_DBFS,
                        device=self._device,
                    )
                )
        finally:
            if process.poll() is None:
                try:
                    process.terminate()
                except OSError:
                    pass
            try:
                process.wait(timeout=1.0)
            except subprocess.TimeoutExpired:  # pragma: no cover - defensive
                process.kill()
            self._process = None


def measure_level(chunk: bytes) -> tuple[float | None, float | None]:
    """Return ``(rms_dbfs, peak_dbfs)`` for interleaved stereo S16_LE PCM.

    Only the left channel is measured: it is the one a parent is closest to, and
    averaging channels would let a loud right channel mask a silent left one.
    """

    usable = len(chunk) - (len(chunk) % (_FORMAT_BYTES * _CHANNELS))
    if usable < _FORMAT_BYTES * _CHANNELS:
        return None, None
    samples = struct.unpack(f"<{usable // _FORMAT_BYTES}h", chunk[:usable])
    left = samples[0::_CHANNELS]
    if not left:
        return None, None
    total = 0
    peak = 0
    for value in left:
        total += value * value
        magnitude = -value if value < 0 else value
        if magnitude > peak:
            peak = magnitude
    rms = math.sqrt(total / len(left))
    rms_db = 20.0 * math.log10(rms / _FULL_SCALE) if rms > 0 else _SILENCE_DBFS
    peak_db = 20.0 * math.log10(peak / _FULL_SCALE) if peak > 0 else _SILENCE_DBFS
    return max(rms_db, _SILENCE_DBFS), max(peak_db, _SILENCE_DBFS)


__all__ = [
    "MicrophoneLevel",
    "MicrophoneLevelReader",
    "SILENCE_FLOOR_DBFS",
]

#: Exposed for the panel's meter scale.
SILENCE_FLOOR_DBFS = _SILENCE_DBFS
