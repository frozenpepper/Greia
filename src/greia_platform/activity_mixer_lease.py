"""Close an idle Activity's Pygame mixer and reopen it transparently.

An open Pygame mixer keeps SDL's audio thread writing silence and SDL's ALSA
hot-plug thread polling for as long as the process lives.  On the Atom N270
reference floor (pygame 2.1.2, SDL 2.26.5, SDL_mixer 2.6.2, ALSA ``dmix``)
that alone costs 4.4-5.1% CPU on a fully static Activity screen
(``SDLAudioP2`` 3.4-4.0%, ``SDLHotplugALSA`` ~1%), whatever the buffer size
(512-4096 frames) and also while paused (``mixer.pause`` or
``SDL_PauseAudioDevice``): SDL keeps feeding silence.  Only closing the mixer
removes it (0%).  Measured on the same device:

* ``pygame.mixer.quit()`` takes 190-380 ms and releases the GIL;
* reopening with the same format takes 91-97 ms in isolation and 280-300 ms
  inside a running Activity loop (re-measured at 87322f0d);
* existing ``Sound`` objects keep their converted samples and play normally
  after a reopen with the same format;
* ``Sound.play`` / ``Channel.play`` on a closed mixer **crash the process**
  (SIGSEGV in pygame 2.1.2); every other mixer call raises ``pygame.error``.

:class:`ActivityMixerLease` therefore closes the mixer once nothing has played
for ``quiet_seconds`` and reopens it, with the same format, channel count,
reservations and channel volumes, immediately before the next mixer use.
Activities keep calling plain Pygame: :func:`install_activity_mixer_lease`
(run by :mod:`greia_platform.python_activity_entry` before any Activity code)
replaces ``pygame.mixer.Sound`` with :class:`LeasedSound`,
``pygame.mixer.Channel`` with :class:`LeasedChannel` and wraps the module
functions, so every playback path passes through the lease and none can reach
a closed SDL mixer.  The frame governor drives :func:`release_idle_activity_audio`
from its wait, so the check costs nothing on a busy loop and needs no Activity
code.  The close runs on a short-lived worker thread so the Activity loop never
stalls for it.

The governor only asks for a close while the child is *idle* (no input for
``FramePolicy.audio_hold_seconds``, 30 s, and no essential motion): closing
while a child plays made the next voice line reopen the device on the loop
thread mid-game (a 220-340 ms freeze in Baia delle Orche).  When the child
comes back to a quiesced mixer the governor calls
:func:`prepare_activity_audio`, which reopens it on a worker thread right
after the response frame, so the first sound no longer pays for the reopen.

The lease never closes while a channel or music is busy (paused channels count
as busy), while another SDL audio device (e.g. a microphone capture) is open,
while a mixer call is in progress, or after music or channel end-events were
used (it then simply stays open, as before).
"""

from __future__ import annotations

import atexit
from collections.abc import Callable, Iterator
from contextlib import contextmanager
import ctypes
import threading
import time
from typing import Any

import pygame

from .input_wait import sdl_library_candidates

#: Seconds without any playback before the mixer closes (matches the Shell).
DEFAULT_QUIET_SECONDS = 10.0
#: Minimum spacing of the cheap idle check driven by the frame governor.
_POLL_INTERVAL = 0.5
#: Pygame's default mixer buffer (frames) when the Activity never chose one.
_DEFAULT_BUFFER = 512
#: SDL keeps at most 16 open audio devices; ids start at 1.
_SDL_MAX_AUDIO_DEVICES = 16
_SDL_INIT_AUDIO = 0x00000010


class SdlAudioDevices:
    """Counts open SDL audio devices (playback and capture) through ctypes."""

    def __init__(self) -> None:
        self._library: ctypes.CDLL | None = None
        self._resolved = False

    def _load(self) -> ctypes.CDLL | None:
        for candidate in sdl_library_candidates():
            try:
                library = ctypes.CDLL(candidate)
                library.SDL_WasInit.argtypes = [ctypes.c_uint32]
                library.SDL_WasInit.restype = ctypes.c_uint32
                if not library.SDL_WasInit(_SDL_INIT_AUDIO):
                    continue
                library.SDL_GetAudioDeviceStatus.argtypes = [ctypes.c_uint32]
                library.SDL_GetAudioDeviceStatus.restype = ctypes.c_int
                return library
            except (OSError, AttributeError):
                continue
        return None

    def open_count(self) -> int | None:
        """Open devices, or None when the initialized SDL cannot be found."""

        if not self._resolved:
            self._library = self._load()
            self._resolved = self._library is not None
        library = self._library
        if library is None:
            return None
        return sum(
            1
            for device in range(1, _SDL_MAX_AUDIO_DEVICES + 1)
            if library.SDL_GetAudioDeviceStatus(device) != 0  # SDL_AUDIO_STOPPED
        )


class MixerBackend:
    """The real ``pygame.mixer`` functions, captured before they are wrapped.

    Tests substitute a fake with the same methods.
    """

    def __init__(self) -> None:
        mixer = pygame.mixer
        self.init = mixer.init
        self.quit = mixer.quit
        self.get_init = mixer.get_init
        self.get_busy = mixer.get_busy
        self.set_num_channels = mixer.set_num_channels
        self.get_num_channels = mixer.get_num_channels
        self.set_reserved = mixer.set_reserved
        self.channel = mixer.Channel
        self._music_busy = mixer.music.get_busy
        self._devices = SdlAudioDevices()

    def music_busy(self) -> bool:
        try:
            return bool(self._music_busy())
        except pygame.error:
            return False

    def other_devices_open(self) -> bool | None:
        """True when an SDL audio device besides the mixer's is open."""

        count = self._devices.open_count()
        return None if count is None else count > 1


class ActivityMixerLease:
    """Owns when the Activity process's mixer device is open.

    ``use()`` brackets every real mixer call: it reopens a quiesced mixer and
    counts the call as in progress so the closer cannot run underneath it.
    ``poll()`` (frame-governor driven) starts the close once the mixer has been
    silent for ``quiet_seconds``.  All state is guarded by one lock; the close
    itself holds it, so a mixer call that arrives meanwhile waits for the close
    and then reopens.
    """

    def __init__(
        self,
        backend: Any | None = None,
        *,
        quiet_seconds: float = DEFAULT_QUIET_SECONDS,
        clock: Callable[[], float] = time.monotonic,
        background: bool = True,
    ) -> None:
        if quiet_seconds <= 0.0:
            raise ValueError("quiet_seconds must be positive")
        self._backend = backend if backend is not None else MixerBackend()
        self._quiet = float(quiet_seconds)
        self._clock = clock
        self._background = background
        self._lock = threading.RLock()
        self._users = 0
        self._last_use = clock()
        self._next_poll = 0.0
        self._closer: threading.Thread | None = None
        self._closing = False
        self._opener: threading.Thread | None = None
        self._opening = False
        # Owed reopen: (frequency, size, channels) of the mixer we closed.
        self._quiesced: tuple[int, int, int] | None = None
        self._buffer = _DEFAULT_BUFFER
        self._num_channels: int | None = None
        self._reserved = 0
        self._volumes: dict[int, tuple[float, ...]] = {}
        self._pinned = False
        self._disabled = False
        self.quiesce_count = 0
        self.reopen_count = 0
        self.last_reopen_seconds: float | None = None

    # -- state -------------------------------------------------------------

    @property
    def is_open(self) -> bool:
        return self._backend.get_init() is not None

    @property
    def quiesced(self) -> bool:
        """True while the lease closed the mixer and owes a reopen."""

        return self._quiesced is not None and not self.is_open

    def reported_init(self) -> tuple[int, int, int] | None:
        """What ``pygame.mixer.get_init()`` reports: a quiesced mixer is 'open'."""

        spec = self._backend.get_init()
        if spec is None and self._quiesced is not None:
            return self._quiesced
        return spec

    def pin(self) -> None:
        """Never close again (music or end-events need a persistent device)."""

        self._pinned = True

    def remember_channel_volume(self, index: int, volume: tuple[float, ...]) -> None:
        self._volumes[index] = volume

    def channel_volume(self, index: int) -> tuple[float, ...] | None:
        return self._volumes.get(index)

    # -- guarded use -------------------------------------------------------

    @contextmanager
    def use(self) -> Iterator[None]:
        """Run one real mixer call: reopen if quiesced, block the closer."""

        with self._lock:
            self._ensure_open_locked()
            self._users += 1
        try:
            yield
        finally:
            with self._lock:
                self._users -= 1
                self._last_use = self._clock()

    @contextmanager
    def if_open(self) -> Iterator[bool]:
        """Run a call only if the mixer is open (stop/busy queries never reopen).

        While a close is in progress this answers "closed" at once instead of
        waiting for it, so a busy check never stalls the Activity loop.
        """

        if not self._lock.acquire(blocking=False):
            if self._closing or self._opening:
                yield False
                return
            self._lock.acquire()
        try:
            open_now = self.is_open and not self._closing
            if open_now:
                self._users += 1
        finally:
            self._lock.release()
        try:
            yield open_now
        finally:
            if open_now:
                with self._lock:
                    self._users -= 1

    def _ensure_open_locked(self) -> None:
        if self._quiesced is None or self.is_open:
            return
        spec = self._quiesced
        started = time.perf_counter()
        frequency, size, channels = spec
        try:
            self._backend.init(
                frequency=frequency, size=size, channels=channels,
                buffer=self._buffer, allowedchanges=0,
            )
        except TypeError:  # a Pygame without ``allowedchanges``
            self._backend.init(frequency=frequency, size=size, channels=channels, buffer=self._buffer)
        # Opened: restore what SDL_mixer forgot when it closed.
        self._quiesced = None
        if self._num_channels is not None:
            self._backend.set_num_channels(self._num_channels)
        if self._reserved:
            self._backend.set_reserved(self._reserved)
        for index, volume in self._volumes.items():
            try:
                self._backend.channel(index).set_volume(*volume)
            except (pygame.error, IndexError, TypeError):
                continue
        if self._backend.get_init() != spec:
            # Another format would play the converted Sounds wrongly: never
            # close again (this reopen is still better than silence).
            self._pinned = True
        self.reopen_count += 1
        self.last_reopen_seconds = time.perf_counter() - started

    # -- explicit Activity calls -------------------------------------------

    def owner_init(self, *args: Any, **kwargs: Any) -> None:
        """``pygame.mixer.init``: a quiesced mixer reopens in its own format."""

        with self._lock:
            if self._quiesced is not None:
                self._ensure_open_locked()
                return
            if not self.is_open:
                buffer = kwargs.get("buffer", args[3] if len(args) > 3 else None)
                if isinstance(buffer, int) and buffer > 0:
                    self._buffer = buffer
            self._backend.init(*args, **kwargs)

    def owner_quit(self) -> None:
        """``pygame.mixer.quit`` by the Activity: closed for good, nothing owed."""

        self.wait_for_close()
        with self._lock:
            self._quiesced = None
            self._backend.quit()

    def remember_num_channels(self, count: int) -> None:
        self._num_channels = int(count)

    def remember_reserved(self, count: int) -> None:
        self._reserved = max(0, int(count))

    def num_channels(self) -> int:
        if self.is_open:
            return int(self._backend.get_num_channels())
        if self._num_channels is not None:
            return self._num_channels
        return 8  # SDL_mixer's default allocation

    def free_channel(self) -> int | None:
        """First idle unreserved channel, as ``Mix_PlayChannel(-1)`` chooses.

        Call inside ``use()``.
        """

        for index in range(self._reserved, int(self._backend.get_num_channels())):
            if not self._backend.channel(index).get_busy():
                return index
        return None

    # -- quiescing ---------------------------------------------------------

    def poll(self) -> bool:
        """Start closing a silent mixer; True when a close was started."""

        now = self._clock()
        if now < self._next_poll or self._pinned or self._disabled:
            return False
        self._next_poll = now + _POLL_INTERVAL
        if self._users or not self.is_open:
            return False
        closer = self._closer
        if closer is not None and closer.is_alive():
            return False
        opener = self._opener
        if opener is not None and opener.is_alive():
            return False
        if self._busy():
            self._last_use = now
            return False
        if now - self._last_use < self._quiet:
            return False
        if self._backend.other_devices_open() is not False:
            # A capture device shares SDL's audio subsystem (or SDL cannot be
            # inspected): closing the mixer could stop it.
            self._last_use = now
            return False
        if not self._background:
            return self._close()
        self._closer = threading.Thread(target=self._close, name="greia-mixer-quiesce", daemon=True)
        self._closer.start()
        return True

    def _busy(self) -> bool:
        try:
            return bool(self._backend.get_busy()) or self._backend.music_busy()
        except pygame.error:
            return True

    def _close(self) -> bool:
        with self._lock:
            if self._users or self._pinned or self._disabled or not self.is_open or self._busy():
                return False
            try:
                spec = self._backend.get_init()
                self._num_channels = int(self._backend.get_num_channels())
                # Owed before the device goes away, so get_init() never
                # reports "no mixer" in between.
                self._quiesced = (int(spec[0]), int(spec[1]), int(spec[2]))
                self._closing = True
                self._backend.quit()
            except Exception:  # noqa: BLE001 - audio must never break the Activity
                self._pinned = True
                if self.is_open:
                    self._quiesced = None
                return False
            finally:
                self._closing = False
            self.quiesce_count += 1
            return True

    def prewarm(self) -> bool:
        """Reopen a quiesced mixer ahead of use; True when a reopen started.

        The frame governor calls this when the child is active again, after
        the frame that answers the input, so the first sound does not reopen
        the device on the loop thread.  With ``background`` the reopen runs on
        a worker thread; status calls meanwhile answer "silent" instead of
        waiting, and a real mixer call simply waits for the reopen to finish.
        """

        if self._quiesced is None or self._disabled or self.is_open:
            return False
        for worker in (self._opener, self._closer):
            if worker is not None and worker.is_alive():
                return False
        if not self._background:
            self._reopen()
            return True
        self._opener = threading.Thread(target=self._reopen, name="greia-mixer-reopen", daemon=True)
        self._opener.start()
        return True

    def _reopen(self) -> None:
        with self._lock:
            if self._disabled or self._quiesced is None or self.is_open:
                return
            self._opening = True
            try:
                self._ensure_open_locked()
            except Exception:  # noqa: BLE001 - the next real use retries and reports
                pass
            finally:
                self._opening = False
                self._last_use = self._clock()

    def wait_for_close(self, timeout: float = 2.0) -> None:
        """Join a close in progress (before ``pygame.quit`` / interpreter exit)."""

        for worker in (self._closer, self._opener):
            if worker is not None and worker is not threading.current_thread():
                worker.join(timeout)

    def shutdown(self) -> None:
        """Stop quiescing and owe nothing; the process is ending."""

        self._disabled = True
        self.wait_for_close()
        with self._lock:
            self._quiesced = None


# -- Pygame integration -------------------------------------------------------

_PygameSound: type = pygame.mixer.Sound
_ACTIVE: ActivityMixerLease | None = None
_ORIGINALS: dict[tuple[Any, str], Any] = {}


def active_mixer_lease() -> ActivityMixerLease | None:
    return _ACTIVE


def release_idle_activity_audio() -> bool:
    """Frame-governor hook (child idle): close the mixer if silent long enough."""

    lease = _ACTIVE
    return lease.poll() if lease is not None else False


def prepare_activity_audio() -> bool:
    """Frame-governor hook (child active): reopen a quiesced mixer off-loop."""

    lease = _ACTIVE
    return lease.prewarm() if lease is not None else False


@contextmanager
def _use() -> Iterator[None]:
    lease = _ACTIVE
    if lease is None:
        yield
        return
    with lease.use():
        yield


def _closed() -> bool:
    lease = _ACTIVE
    return lease is not None and not lease.is_open


def _when_open(call: Callable[..., Any], default: Any, *args: Any) -> Any:
    """Run a status/stop call only while the device is open, else ``default``."""

    lease = _ACTIVE
    if lease is None:
        return call(*args)
    with lease.if_open() as open_now:
        return call(*args) if open_now else default


class LeasedSound(_PygameSound):  # type: ignore[misc, valid-type]
    """``pygame.mixer.Sound`` whose every device call goes through the lease."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        with _use():
            super().__init__(*args, **kwargs)
            self._greia_length = float(_PygameSound.get_length(self))
            self._greia_volume = float(_PygameSound.get_volume(self))

    def play(self, loops: int = 0, maxtime: int = 0, fade_ms: int = 0) -> "LeasedChannel | None":
        lease = _ACTIVE
        if lease is None:
            return _PygameSound.play(self, loops, maxtime, fade_ms)
        with lease.use():
            index = lease.free_channel()
            if index is None:
                return None
            lease._backend.channel(index).play(self, loops, maxtime, fade_ms)
        return LeasedChannel(index)

    def stop(self) -> None:
        _when_open(_PygameSound.stop, None, self)

    def fadeout(self, time: int) -> None:  # noqa: A002 - Pygame's name
        _when_open(_PygameSound.fadeout, None, self, time)

    def get_length(self) -> float:
        length = getattr(self, "_greia_length", None)
        if length is None:
            with _use():
                return float(_PygameSound.get_length(self))
        return length

    def get_volume(self) -> float:
        volume = getattr(self, "_greia_volume", None)
        if volume is None:
            with _use():
                return float(_PygameSound.get_volume(self))
        return volume

    def set_volume(self, value: float) -> None:
        with _use():
            _PygameSound.set_volume(self, value)
            self._greia_volume = float(_PygameSound.get_volume(self))

    def get_num_channels(self) -> int:
        return int(_when_open(_PygameSound.get_num_channels, 0, self))

    def get_raw(self) -> bytes:
        with _use():
            return _PygameSound.get_raw(self)


class LeasedChannel:
    """``pygame.mixer.Channel(i)`` that stays valid across a mixer reopen.

    It holds only the channel index and asks Pygame for the real channel at
    each call.  Status calls on a closed mixer answer "silent" instead of
    reopening it.
    """

    __slots__ = ("_index",)

    def __init__(self, id: int) -> None:  # noqa: A002 - Pygame's name
        index = int(id)
        lease = _ACTIVE
        if lease is not None and lease.quiesced:
            if not 0 <= index < lease.num_channels():
                raise IndexError("invalid channel index")
        else:
            _real_channel(index)  # Pygame's own validation and errors
        self._index = index

    @property
    def index(self) -> int:
        return self._index

    def _real(self) -> Any:
        return _real_channel(self._index)

    def play(self, sound: Any, loops: int = 0, maxtime: int = 0, fade_ms: int = 0) -> None:
        with _use():
            self._real().play(sound, loops, maxtime, fade_ms)

    def queue(self, sound: Any) -> None:
        with _use():
            self._real().queue(sound)

    def set_volume(self, *volume: float) -> None:
        with _use():
            self._real().set_volume(*volume)
            lease = _ACTIVE
            if lease is not None:
                lease.remember_channel_volume(self._index, tuple(volume))

    def get_volume(self) -> float:
        if _closed():
            lease = _ACTIVE
            remembered = lease.channel_volume(self._index) if lease is not None else None
            return float(remembered[0]) if remembered else 1.0
        with _use():
            return float(self._real().get_volume())

    def _status(self, name: str, default: Any, *args: Any) -> Any:
        return _when_open(lambda: getattr(self._real(), name)(*args), default)

    def stop(self) -> None:
        self._status("stop", None)

    def pause(self) -> None:
        self._status("pause", None)

    def unpause(self) -> None:
        self._status("unpause", None)

    def fadeout(self, time: int) -> None:  # noqa: A002 - Pygame's name
        self._status("fadeout", None, time)

    def get_busy(self) -> bool:
        return bool(self._status("get_busy", False))

    def get_sound(self) -> Any:
        return self._status("get_sound", None)

    def get_queue(self) -> Any:
        return self._status("get_queue", None)

    def set_endevent(self, *args: Any) -> None:
        lease = _ACTIVE
        if lease is not None:
            lease.pin()
        with _use():
            self._real().set_endevent(*args)

    def get_endevent(self) -> int:
        with _use():
            return int(self._real().get_endevent())

    def __eq__(self, other: object) -> bool:
        return isinstance(other, LeasedChannel) and other._index == self._index

    def __hash__(self) -> int:
        return hash(("LeasedChannel", self._index))

    def __repr__(self) -> str:
        return f"<LeasedChannel {self._index}>"


def _real_channel(index: int) -> Any:
    lease = _ACTIVE
    factory = lease._backend.channel if lease is not None else _ORIGINALS.get((pygame.mixer, "Channel"), pygame.mixer.Channel)
    return factory(index)


# Module-function wrappers (installed on ``pygame.mixer``).

def _init(*args: Any, **kwargs: Any) -> None:
    _require().owner_init(*args, **kwargs)


def _quit() -> None:
    _require().owner_quit()


def _get_init() -> tuple[int, int, int] | None:
    return _require().reported_init()


def _get_busy() -> bool:
    lease = _require()
    with lease.if_open() as open_now:
        return bool(open_now and lease._backend.get_busy())


def _set_num_channels(count: int) -> None:
    lease = _require()
    with lease.use():
        lease._backend.set_num_channels(count)
        lease.remember_num_channels(lease._backend.get_num_channels())


def _get_num_channels() -> int:
    return _require().num_channels()


def _set_reserved(count: int) -> int:
    lease = _require()
    with lease.use():
        reserved = lease._backend.set_reserved(count)
        lease.remember_reserved(count)
        return reserved


def _silent_when_closed(name: str) -> Callable[..., Any]:
    original = getattr(pygame.mixer, name)

    def call(*args: Any) -> None:
        with _require().if_open() as open_now:
            if open_now:
                original(*args)

    call.__name__ = name
    call.__doc__ = original.__doc__
    return call


def _find_channel(force: bool = False) -> Any:
    lease = _require()
    with lease.use():
        index = lease.free_channel()
        if index is None:
            # Pygame picks the longest-playing channel; a busy mixer is not
            # closed, so the raw channel it returns stays valid.
            return _ORIGINALS[(pygame.mixer, "find_channel")](force)
    return LeasedChannel(index)


def _pinning_music(name: str) -> Callable[..., Any]:
    original = getattr(pygame.mixer.music, name)

    def call(*args: Any, **kwargs: Any) -> Any:
        lease = _require()
        lease.pin()
        with lease.use():
            return original(*args, **kwargs)

    call.__name__ = name
    call.__doc__ = original.__doc__
    return call


def _music_get_busy() -> bool:
    with _require().if_open() as open_now:
        return bool(open_now and _ORIGINALS[(pygame.mixer.music, "get_busy")]())


def _pygame_quit() -> None:
    lease = _ACTIVE
    if lease is not None:
        lease.shutdown()
    _ORIGINALS[(pygame, "quit")]()


def _require() -> ActivityMixerLease:
    lease = _ACTIVE
    if lease is None:  # pragma: no cover - wrappers exist only while installed
        raise pygame.error("Greia mixer lease is not installed")
    return lease


_MUSIC_FUNCTIONS = (
    "load", "unload", "play", "rewind", "stop", "pause", "unpause", "fadeout",
    "set_volume", "get_volume", "set_pos", "get_pos", "queue",
    "set_endevent", "get_endevent",
)


def install_activity_mixer_lease(
    *,
    quiet_seconds: float = DEFAULT_QUIET_SECONDS,
    backend: Any | None = None,
    background: bool = True,
) -> ActivityMixerLease:
    """Route this process's ``pygame.mixer`` through one lease (idempotent).

    Must run before Activity code creates Sounds or Channels; the Python
    Activity entry point calls it right after the interpreter start-up policy.
    """

    global _ACTIVE
    if _ACTIVE is not None:
        return _ACTIVE
    lease = ActivityMixerLease(backend, quiet_seconds=quiet_seconds, background=background)
    replacements: list[tuple[Any, str, Any]] = [
        (pygame.mixer, "Sound", LeasedSound),
        (pygame.mixer, "Channel", LeasedChannel),
        (pygame.mixer, "init", _init),
        (pygame.mixer, "quit", _quit),
        (pygame.mixer, "get_init", _get_init),
        (pygame.mixer, "get_busy", _get_busy),
        (pygame.mixer, "set_num_channels", _set_num_channels),
        (pygame.mixer, "get_num_channels", _get_num_channels),
        (pygame.mixer, "set_reserved", _set_reserved),
        (pygame.mixer, "find_channel", _find_channel),
        (pygame, "quit", _pygame_quit),
    ]
    replacements += [(pygame.mixer, name, _silent_when_closed(name)) for name in ("stop", "pause", "unpause", "fadeout")]
    replacements += [(pygame.mixer.music, name, _pinning_music(name)) for name in _MUSIC_FUNCTIONS if hasattr(pygame.mixer.music, name)]
    replacements.append((pygame.mixer.music, "get_busy", _music_get_busy))
    for owner, name, replacement in replacements:
        _ORIGINALS[(owner, name)] = getattr(owner, name)
        setattr(owner, name, replacement)
    _ACTIVE = lease
    atexit.register(lease.shutdown)
    return lease


def uninstall_activity_mixer_lease() -> None:
    """Restore Pygame's own functions (tests); a quiesced mixer stays closed."""

    global _ACTIVE
    lease = _ACTIVE
    if lease is None:
        return
    lease.shutdown()
    atexit.unregister(lease.shutdown)
    for (owner, name), original in _ORIGINALS.items():
        setattr(owner, name, original)
    _ORIGINALS.clear()
    _ACTIVE = None


__all__ = [
    "ActivityMixerLease",
    "DEFAULT_QUIET_SECONDS",
    "LeasedChannel",
    "LeasedSound",
    "MixerBackend",
    "SdlAudioDevices",
    "active_mixer_lease",
    "install_activity_mixer_lease",
    "prepare_activity_audio",
    "release_idle_activity_audio",
    "uninstall_activity_mixer_lease",
]
