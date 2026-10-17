"""Launch cover: the Shell's launch screen continues inside the Activity window.

Why this exists. An Activity's window appears the moment its first
``pygame.display.set_mode`` maps it, but the Activity presents its first frame
only after building its content. On the provisional Legacy-X session SDL maps
that window with a black background, so the child used to watch a black screen
between the Shell's launch screen and the Activity (measured on the Atom N270
Acer at bc31ae93: 1.0-3.8 s, longest for the heaviest Activities).

The hand-off has three steps, all runtime-neutral and pure Pygame:

1. The trusted Shell presents its launch screen *before* starting the Activity
   and publishes the exact pixels it shows as a **launch card**
   (:class:`LaunchCard`, raw RGB with a tiny header) into the Activity's own
   private data directory, ``<activity data>/.greia/launch-card``. That
   directory is already inside the sandbox's allowed paths, so nothing new is
   exposed and no image decoding is needed later. :class:`LaunchCardPublisher`
   owns the write and its removal.
2. :mod:`greia_platform.python_activity_entry` reads the card before any
   Activity code runs (a plain file read, ~6 ms for 1024x600 on the Atom) and
   wraps ``pygame.display.set_mode`` once (:class:`ActivityLaunchCover`).
   The wrapper opens the Activity's first window **hidden** (``HIDDEN``),
   then shows it with a second ``set_mode`` call carrying ``SHOWN``, blits
   the card at the window origin, flips once and restores the original
   function, so the screen goes Shell launch screen -> identical card -> the
   Activity's first frame. Opening hidden matters: a window mapped by the
   first ``set_mode`` showed black for one frame (51-83 ms on the Acer at
   4d6e9c5e) before the card's flip; a hidden first window maps only on the
   showing call, after SDL has its surface, so the next thing on screen is the
   card. Both calls are public Pygame 2 API (no X11). A missing or damaged
   card falls back to the profile theme's background colour (never black).
   The cover never paints after the Activity's own frames: it runs inside the
   first ``set_mode``, before the Activity can draw.
3. The entry then removes the card file. Its absence tells the Shell that the
   Activity window now covers the screen, so the Shell stops repainting its
   hidden launch screen and leaves the CPU to the starting Activity.

What it does not change: READY still means the Activity's own first presented
frame (the Activity calls ``mark_activity_ready`` after its own flip; the
cover's flip is not READY), and nothing here touches X11. Protected Home is
Greia's, not the cover's: the Shell draws it on its launch screen (so the card
carries its picture) and the trusted chrome is shown from the launch onward
(see ``greia_launcher.trusted_chrome_supervisor``). Launches outside a Greia
session (no ``GREIA_ACTIVITY_SESSION_ID``: tests, headless captures, developer
runs) install nothing.
"""

from __future__ import annotations

import os
import struct
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Final, Mapping

#: Directory (inside the Activity data root) and file name of the card.
LAUNCH_CARD_DIRECTORY: Final = ".greia"
LAUNCH_CARD_FILE_NAME: Final = "launch-card"
#: Header: magic, width, height, payload byte count (little-endian).
_MAGIC: Final = b"GREIALC1"
_HEADER: Final = struct.Struct("<8sHHI")
#: Bound on the card size (4K UHD); larger displays fall back to the colour.
MAXIMUM_CARD_PIXELS: Final = 3840 * 2160
_MAXIMUM_FILE_BYTES: Final = _HEADER.size + MAXIMUM_CARD_PIXELS * 3
#: Greia's default cream theme background, used when no theme is known.
DEFAULT_COVER_COLOR: Final = (247, 235, 203)


class LaunchCardError(ValueError):
    """A launch card is malformed or out of bounds."""


@dataclass(frozen=True, slots=True)
class LaunchCard:
    """One full-screen launch frame as raw 8-bit RGB rows (no padding)."""

    width: int
    height: int
    #: ``bytes`` or a zero-copy ``memoryview`` of a file buffer.
    rgb: bytes | memoryview

    def __post_init__(self) -> None:
        if not (1 <= self.width <= 0xFFFF and 1 <= self.height <= 0xFFFF):
            raise LaunchCardError("launch card size is out of bounds")
        if self.width * self.height > MAXIMUM_CARD_PIXELS:
            raise LaunchCardError("launch card is larger than the supported maximum")
        if len(self.rgb) != self.width * self.height * 3:
            raise LaunchCardError("launch card payload does not match its size")

    @property
    def size(self) -> tuple[int, int]:
        return (self.width, self.height)

    @classmethod
    def from_surface(cls, surface: Any, pygame: Any) -> "LaunchCard":
        """Capture what a (display) surface currently shows."""

        width, height = surface.get_size()
        return cls(width, height, pygame.image.tostring(surface, "RGB"))

    def encode(self) -> bytes:
        return _HEADER.pack(_MAGIC, self.width, self.height, len(self.rgb)) + bytes(self.rgb)

    @classmethod
    def decode(cls, data: bytes | bytearray) -> "LaunchCard":
        """Parse an encoded card; the pixels stay a view of ``data`` (no copy)."""

        if len(data) < _HEADER.size:
            raise LaunchCardError("launch card is truncated")
        magic, width, height, length = _HEADER.unpack_from(data)
        if magic != _MAGIC:
            raise LaunchCardError("not a Greia launch card")
        if len(data) != _HEADER.size + length:
            raise LaunchCardError("launch card length does not match its header")
        return cls(width, height, memoryview(data)[_HEADER.size:])


def launch_card_path(activity_data_dir: Path | str) -> Path:
    return Path(activity_data_dir) / LAUNCH_CARD_DIRECTORY / LAUNCH_CARD_FILE_NAME


class LaunchCardPublisher:
    """Trusted Shell side: publish, observe and remove one Activity's card.

    The card directory lives in an Activity-writable tree, so every operation
    goes through a directory descriptor opened with ``O_NOFOLLOW``: a symlink
    planted by an Activity can never redirect a Shell write or unlink outside
    that Activity's own data root. Every method is fail-soft and returns a
    plain bool; a missing card only means the Activity falls back to the
    theme colour.
    """

    def publish(self, activity_data_dir: Path, card: LaunchCard) -> bool:
        payload = card.encode()
        try:
            directory = self._open_card_directory(activity_data_dir, create=True)
        except OSError:
            return False
        temporary = f".{LAUNCH_CARD_FILE_NAME}.{os.getpid()}.tmp"
        try:
            try:
                os.unlink(temporary, dir_fd=directory)
            except FileNotFoundError:
                pass
            handle = os.open(
                temporary,
                os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0),
                0o660,
                dir_fd=directory,
            )
            try:
                view = memoryview(payload)
                while view:
                    view = view[os.write(handle, view):]
            finally:
                os.close(handle)
            os.replace(
                temporary,
                LAUNCH_CARD_FILE_NAME,
                src_dir_fd=directory,
                dst_dir_fd=directory,
            )
            return True
        except OSError:
            try:
                os.unlink(temporary, dir_fd=directory)
            except OSError:
                pass
            return False
        finally:
            os.close(directory)

    def consumed(self, activity_data_dir: Path) -> bool:
        """True once the Activity has painted the card and removed it."""

        try:
            directory = self._open_card_directory(activity_data_dir, create=False)
        except OSError:
            return True
        try:
            os.stat(LAUNCH_CARD_FILE_NAME, dir_fd=directory, follow_symlinks=False)
            return False
        except OSError:
            return True
        finally:
            os.close(directory)

    def discard(self, activity_data_dir: Path) -> None:
        try:
            directory = self._open_card_directory(activity_data_dir, create=False)
        except OSError:
            return
        try:
            os.unlink(LAUNCH_CARD_FILE_NAME, dir_fd=directory)
        except OSError:
            pass
        finally:
            os.close(directory)

    @staticmethod
    def _open_card_directory(activity_data_dir: Path, *, create: bool) -> int:
        flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0)
        root = os.open(str(activity_data_dir), flags)
        try:
            if create:
                try:
                    os.mkdir(LAUNCH_CARD_DIRECTORY, 0o770, dir_fd=root)
                except FileExistsError:
                    pass
            return os.open(LAUNCH_CARD_DIRECTORY, flags, dir_fd=root)
        finally:
            os.close(root)


def theme_background_color(snapshot: str | None) -> tuple[int, int, int]:
    """``background_color`` of a ``GREIA_THEME_SNAPSHOT`` value, or cream.

    A plain substring scan rather than JSON decoding keeps the Activity entry
    from importing anything before the Activity starts.
    """

    if snapshot:
        key = '"background_color"'
        start = snapshot.find(key)
        if start >= 0:
            hash_at = snapshot.find("#", start + len(key))
            value = snapshot[hash_at + 1 : hash_at + 7] if hash_at >= 0 else ""
            if len(value) == 6:
                try:
                    return (int(value[0:2], 16), int(value[2:4], 16), int(value[4:6], 16))
                except ValueError:
                    pass
    return DEFAULT_COVER_COLOR


def read_launch_card(path: Path) -> LaunchCard | None:
    """Read a card without following symlinks; ``None`` when absent or bad."""

    try:
        handle = os.open(str(path), os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
    except OSError:
        return None
    try:
        size = os.fstat(handle).st_size
        if not _HEADER.size <= size <= _MAXIMUM_FILE_BYTES:
            return None
        # One buffer, filled in place: the pixels are never copied again
        # before they reach the window (frombuffer takes a view).
        buffer = bytearray(size)
        view = memoryview(buffer)
        filled = 0
        while filled < size:
            count = os.readv(handle, [view[filled:]])
            if count <= 0:
                return None
            filled += count
        return LaunchCard.decode(buffer)
    except (OSError, LaunchCardError):
        return None
    finally:
        os.close(handle)


class ActivityLaunchCover:
    """Activity side: paint the launch card once, right after the first set_mode.

    ``install`` wraps ``pygame.display.set_mode``. The wrapper restores the
    real function (when nobody wrapped it further in the meantime), opens the
    window hidden and shows it (:meth:`open_window`), paints the card or the
    fallback colour, flips once and removes the card file. Any failure is
    swallowed: the Activity then simply starts as it always did.
    """

    def __init__(
        self,
        card: LaunchCard | None,
        *,
        fallback_color: tuple[int, int, int] = DEFAULT_COVER_COLOR,
        card_path: Path | None = None,
        remove_card: Callable[[Path], None] | None = None,
    ) -> None:
        self._card = card
        self._fallback_color = fallback_color
        self._card_path = card_path
        self._remove_card = remove_card if remove_card is not None else _unlink_quietly
        self._painted = False

    @property
    def painted(self) -> bool:
        return self._painted

    @classmethod
    def from_environment(
        cls, environ: Mapping[str, str] | None = None
    ) -> "ActivityLaunchCover | None":
        environment = os.environ if environ is None else environ
        if not environment.get("GREIA_ACTIVITY_SESSION_ID", "").strip():
            return None
        data_dir = environment.get("GREIA_ACTIVITY_DATA_DIR", "").strip()
        path = launch_card_path(data_dir) if data_dir else None
        return cls(
            read_launch_card(path) if path is not None else None,
            fallback_color=theme_background_color(environment.get("GREIA_THEME_SNAPSHOT")),
            card_path=path,
        )

    def install(self, pygame: Any) -> None:
        display = pygame.display
        original = display.set_mode
        cover = self

        def set_mode(*args: Any, **kwargs: Any) -> Any:
            if display.set_mode is set_mode:
                display.set_mode = original
            if cover._painted:
                return original(*args, **kwargs)
            surface = cover.open_window(original, pygame, args, kwargs)
            cover.paint(surface, pygame)
            return surface

        display.set_mode = set_mode

    @staticmethod
    def open_window(
        set_mode: Callable[..., Any],
        pygame: Any,
        args: tuple[Any, ...],
        kwargs: Mapping[str, Any],
    ) -> Any:
        """Create the first window hidden, then show it; return its surface.

        ``set_mode(size, flags, ...)`` is called twice: once with ``HIDDEN``
        (the window exists but is not mapped, so nothing black can reach the
        screen) and once with ``SHOWN`` (Pygame reuses the window and maps
        it). The caller then paints and flips the card, the first pixels the
        child sees. Calls that already ask for ``HIDDEN`` or ``OPENGL``, or a
        Pygame without the flags, go through unchanged. If the hidden call
        fails the plain call runs, so the Activity behaves exactly as without
        the cover; errors of the showing call are the Activity's own.
        """

        hidden = getattr(pygame, "HIDDEN", 0)
        shown = getattr(pygame, "SHOWN", 0)
        flags = _set_mode_flags(args, kwargs)
        if (
            not hidden
            or not shown
            or flags is None
            or flags & (hidden | getattr(pygame, "OPENGL", 0))
        ):
            return set_mode(*args, **kwargs)
        try:
            positional, named = _with_set_mode_flags(args, kwargs, flags | hidden)
            set_mode(*positional, **named)
        except Exception as exc:  # noqa: BLE001 - fall back to the plain call
            print(f"greia: hidden first window unavailable: {exc}", file=sys.stderr)
            return set_mode(*args, **kwargs)
        positional, named = _with_set_mode_flags(args, kwargs, (flags & ~hidden) | shown)
        return set_mode(*positional, **named)

    def paint(self, surface: Any, pygame: Any) -> bool:
        """Paint and present the cover once; return whether it was presented."""

        if self._painted:
            return False
        self._painted = True
        card, self._card = self._card, None  # release the pixels either way
        try:
            if surface is None or surface.get_flags() & getattr(pygame, "OPENGL", 0):
                return False
            image = (
                pygame.image.frombuffer(card.rgb, card.size, "RGB")
                if card is not None
                else None
            )
            if image is None or image.get_size() != surface.get_size():
                surface.fill(self._fallback_color)
            if image is not None:
                # The window sits at the screen origin, exactly where the Shell
                # drew this frame, so a size mismatch (e.g. a 1024x600 window
                # on an 800x480 screen) still lines up in the visible part.
                surface.blit(image, (0, 0))
            pygame.display.flip()
        except Exception as exc:  # noqa: BLE001 - never block the Activity launch
            print(f"greia: launch cover unavailable: {exc}", file=sys.stderr)
            return False
        if self._card_path is not None:
            self._remove_card(self._card_path)
        return True


def _set_mode_flags(args: tuple[Any, ...], kwargs: Mapping[str, Any]) -> int | None:
    """The ``flags`` of a ``set_mode(size=(0, 0), flags=0, ...)`` call, or None."""

    value = args[1] if len(args) > 1 else kwargs.get("flags", 0)
    if isinstance(value, bool) or not isinstance(value, int):
        return None
    return value


def _with_set_mode_flags(
    args: tuple[Any, ...], kwargs: Mapping[str, Any], flags: int
) -> tuple[tuple[Any, ...], dict[str, Any]]:
    """The same ``set_mode`` call with ``flags`` replaced."""

    named = dict(kwargs)
    if len(args) > 1:
        return (args[0], flags, *args[2:]), named
    named["flags"] = flags
    if args:
        return (args[0],), named
    named.setdefault("size", (0, 0))
    return (), named


def _unlink_quietly(path: Path) -> None:
    try:
        os.unlink(path)
    except OSError:
        pass


def install_activity_launch_cover(
    pygame: Any, environ: Mapping[str, str] | None = None
) -> ActivityLaunchCover | None:
    """Entry hook: install the cover when launched by a Greia session."""

    cover = ActivityLaunchCover.from_environment(environ)
    if cover is not None:
        cover.install(pygame)
    return cover


__all__ = [
    "ActivityLaunchCover",
    "DEFAULT_COVER_COLOR",
    "LAUNCH_CARD_DIRECTORY",
    "LAUNCH_CARD_FILE_NAME",
    "LaunchCard",
    "LaunchCardError",
    "LaunchCardPublisher",
    "MAXIMUM_CARD_PIXELS",
    "install_activity_launch_cover",
    "launch_card_path",
    "read_launch_card",
    "theme_background_color",
]
