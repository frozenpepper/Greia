"""Localized spoken labels for Greia Shell catalogue navigation.

The launcher owns when labels are spoken. Activity packages only contribute the
localized semantic ``activity.title`` audio cue already defined by ADR 0028.
Platform Collections use Greia-owned clips under
``assets/audio/system/launcher-labels/<locale>/<collection>.wav``.

This module intentionally contains no TTS. All speech is prerecorded at authoring
time, playback is asynchronous through the launcher's existing pygame mixer,
and failures are presentation-only/fail-silent.
"""

from __future__ import annotations

from pathlib import Path
import time
from typing import Any, Callable

from greia_platform.activities import ActivityManifest
from greia_platform.localization import (
    ActivityLocaleSupport,
    LocalizationError,
    LocalizedResources,
    LocaleTag,
    resolve_activity_locale,
)
from greia_platform.ui_core import BoundedCache


ACTIVITY_TITLE_CUE = "activity.title"
_PLATFORM_LABEL_ROOT = Path("assets/audio/system/launcher-labels")
_ALLOWED_COLLECTION_ID_CHARS = frozenset("abcdefghijklmnopqrstuvwxyz0123456789_-")


def locale_candidates(locale: str) -> tuple[LocaleTag, ...]:
    """Return deterministic catalogue-audio fallback candidates.

    Catalogue speech follows the requested Greia UI locale first. English is a
    final compatibility fallback when supplied, matching ADR 0028's catalogue
    goal without claiming that an Activity's own UI supports English.
    """

    requested = LocaleTag.parse(locale)
    candidates = list(requested.fallback_chain())
    english = LocaleTag.parse("en")
    if english not in candidates:
        candidates.append(english)
    return tuple(candidates)


_TITLE_AUDIO_CACHE: BoundedCache[tuple[str, str], Path | None] = BoundedCache(128)


def activity_title_audio(manifest: ActivityManifest, locale: str) -> Path | None:
    """Resolve the launcher title through the shared Greia speech resolver.

    This is a catalogue locale, independent from which languages the Activity
    currently advertises for gameplay. A missing selected-language file uses
    the existing English compatibility recording.
    """
    cache_key = (str(manifest.root.resolve()), locale)
    if cache_key in _TITLE_AUDIO_CACHE:
        return _TITLE_AUDIO_CACHE[cache_key]

    resolved: Path | None = None
    candidates = locale_candidates(locale)
    languages = tuple(
        candidate.value
        for candidate in candidates
        if (manifest.root / "locales" / f"{candidate.value}.json").is_file()
    )
    if languages:
        default = "en" if "en" in languages else languages[0]
        try:
            support = ActivityLocaleSupport.localized(
                languages, default_ui_locale=default
            )
            context = resolve_activity_locale(locale, support)
            if context is not None:
                resources = LocalizedResources(manifest.root, context)
                resolved = resources.audio_path(ACTIVITY_TITLE_CUE)
        except (LocalizationError, OSError):
            resolved = None

    _TITLE_AUDIO_CACHE[cache_key] = resolved
    return resolved


def collection_title_audio(root: Path, collection_id: str, locale: str) -> Path | None:
    """Resolve a platform-owned Collection spoken label.

    The path convention is intentionally declarative and bounded. Collection IDs
    are platform vocabulary; arbitrary Activity metadata cannot manufacture a
    path or child navigation destination.
    """

    if (
        not collection_id
        or len(collection_id) > 64
        or any(character not in _ALLOWED_COLLECTION_ID_CHARS for character in collection_id)
    ):
        return None
    audio_root = root / _PLATFORM_LABEL_ROOT
    for candidate in locale_candidates(locale):
        path = audio_root / candidate.value / f"{collection_id}.wav"
        if path.is_file():
            return path
    return None


class ShellMixerLease:
    """Owns the Shell's Pygame mixer: opened lazily, closed when quiet.

    An open mixer keeps SDL's audio thread and the ALSA PCM running forever,
    even in silence: on the Atom reference floor Home idled at ~9% CPU instead
    of 2.8% once any Shell sound had played (Acer sweep at 15212f44).  The
    lease opens the mixer immediately before a sound needs it and closes it
    after ``quiet_seconds`` without playback, or at once via ``release()``
    (e.g. when an Activity, a separate process with its own mixer, takes the
    foreground).  ``generation`` changes on every close so holders drop
    channels/Sounds tied to the closed device.
    """

    def __init__(
        self,
        *,
        quiet_seconds: float = 10.0,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        if quiet_seconds <= 0.0:
            raise ValueError("quiet_seconds must be positive")
        self._quiet = float(quiet_seconds)
        self._clock = clock
        self._last_sound: float | None = None
        self.generation = 0

    def ensure_open(self, pygame: Any) -> bool:
        """Open the mixer if needed (fail-soft); True when it is usable."""

        if not pygame.mixer.get_init():
            # Post-intro lazy mixer ownership: the display-only pre-frame
            # path leaves the mixer uninitialized, so open it here
            # immediately before the first audio it serves.
            init = getattr(pygame.mixer, "init", None)
            if init is None:
                return False
            try:
                init()
            except (OSError, RuntimeError, ValueError, pygame.error):
                return False
            if not pygame.mixer.get_init():
                return False
        self._last_sound = self._clock()
        return True

    def note_sound(self) -> None:
        """A sound started: restart the quiet period."""

        self._last_sound = self._clock()

    def poll(self, pygame: Any, now: float | None = None) -> bool:
        """Close the mixer after the quiet period; True when it was closed."""

        try:
            if not pygame.mixer.get_init():
                self._last_sound = None
                return False
            now = self._clock() if now is None else now
            busy = getattr(pygame.mixer, "get_busy", None)
            if self._last_sound is None or (callable(busy) and busy()):
                self._last_sound = now
                return False
            if now - self._last_sound < self._quiet:
                return False
        except Exception:  # noqa: BLE001 - optional presentation must fail silent
            return False
        return self.release(pygame)

    def release(self, pygame: Any) -> bool:
        """Close the mixer now (stops anything playing); True when it closed."""

        try:
            if not pygame.mixer.get_init():
                return False
            quit_mixer = getattr(pygame.mixer, "quit", None)
            if quit_mixer is None:
                return False
            quit_mixer()
        except Exception:  # noqa: BLE001 - optional presentation must fail silent
            return False
        self._last_sound = None
        self.generation += 1
        return True


class SpokenLabelPlayer:
    """Interruptible, bounded launcher narration using pygame's existing mixer.

    ``identity`` is semantic (for example ``activity:org.greia.foo``). Repeated
    pointer-motion events over the same destination therefore do not replay the
    clip. A new destination stops/replaces the previous label instead of building
    an audio queue.
    """

    def __init__(self, *, cache_entries: int = 48, mixer: ShellMixerLease | None = None) -> None:
        self._cache: BoundedCache[str, Any] = BoundedCache(cache_entries)
        self._last_identity: str | None = None
        self._channel: Any = None
        self._mixer = mixer if mixer is not None else ShellMixerLease()

    @property
    def mixer(self) -> ShellMixerLease:
        return self._mixer

    def poll_idle_audio(self, now: float, pygame: Any) -> bool:
        """Close the Shell mixer once it has been quiet; True when closed."""

        if self._mixer.poll(pygame, now):
            self._forget_device()
            return True
        return False

    def release_audio(self, pygame: Any) -> bool:
        """Stop narration and close the Shell mixer now (Activity foreground)."""

        self.stop()
        if self._mixer.release(pygame):
            self._forget_device()
            return True
        return False

    def _forget_device(self) -> None:
        # Channels and decoded Sounds belong to the closed device; the next
        # sound reopens the mixer and reloads its (small) clip.
        self._channel = None
        self._cache.clear()

    def clear_focus(self) -> None:
        """Allow the same destination to speak again after focus leaves it."""

        self._last_identity = None

    def announce(self, identity: str, clip: Path | None, pygame: Any) -> bool:
        if not identity or identity == self._last_identity:
            return False
        self._last_identity = identity
        if clip is None or not clip.is_file():
            return False
        return self._play(clip, pygame, interrupt=True)

    def is_busy(self) -> bool:
        """Whether a clip is currently audible on the narration channel."""

        try:
            return bool(self._channel is not None and self._channel.get_busy())
        except Exception:  # noqa: BLE001 - optional presentation must fail silent
            return False

    def play_if_idle(self, clip: Path | None, pygame: Any) -> bool:
        """Play a character clip on the same channel only when it is silent.

        Character speech (for example the tappable Home greeter) never
        interrupts a playing label or another character line; it simply does
        not start. The semantic label deduplication is reset so the next
        navigation focus speaks normally (navigation may interrupt character
        speech, never the reverse).
        """

        if clip is None or not clip.is_file() or self.is_busy():
            return False
        self._last_identity = None
        return self._play(clip, pygame, interrupt=False)

    def _play(self, clip: Path, pygame: Any, *, interrupt: bool) -> bool:
        try:
            if not self._mixer.ensure_open(pygame):
                return False
            key = str(clip.resolve())
            sound = self._cache.get(key)
            if sound is None:
                sound = pygame.mixer.Sound(key)
                self._cache[key] = sound
            if self._channel is None:
                self._channel = pygame.mixer.find_channel(force=True)
            if self._channel is None:
                return False
            if interrupt:
                self._channel.stop()
            elif self._channel.get_busy():
                return False
            self._channel.play(sound)
            self._mixer.note_sound()
            return True
        except (OSError, RuntimeError, ValueError, pygame.error):
            return False

    def stop(self) -> None:
        try:
            if self._channel is not None:
                self._channel.stop()
        except Exception:  # noqa: BLE001 - optional presentation must fail silent
            pass
        self._channel = None
        self._last_identity = None


class SpokenLabelController:
    """Launcher-owned semantic focus controller for spoken collection/activity titles.

    One instance owns the single interruptible narration channel, the short
    pointer dwell and the semantic deduplication policy.  Collection Home,
    adaptive sub-Collections and the Activity grid all route through this
    single path.

    Pointer dwell is intentionally tiny (default 160 ms) and is evaluated
    against the launcher's own ``time.monotonic()`` polling – no thread,
    subprocess or extra redraw is required.

    Keyboard/controller navigation announces immediately after a *real*
    semantic selection change; a clamped arrow or a repeated motion inside the
    same tile does not replay.
    """

    def __init__(
        self,
        root: Path,
        *,
        player: SpokenLabelPlayer | None = None,
        dwell_ms: int = 160,
        cache_entries: int = 48,
    ) -> None:
        self._root = Path(root)
        self._player = player if player is not None else SpokenLabelPlayer(
            cache_entries=cache_entries
        )
        self._dwell_seconds = max(0, dwell_ms) / 1000.0
        self._pending: tuple[str, Path | None, float] | None = None

    @property
    def player(self) -> SpokenLabelPlayer:
        return self._player

    @property
    def root(self) -> Path:
        """Greia OS root that owns the shared speech assets."""

        return self._root

    def activity_focus(
        self, manifest: ActivityManifest, locale: str
    ) -> tuple[str, Path | None]:
        return (
            f"activity:{manifest.activity_id}",
            activity_title_audio(manifest, locale),
        )

    def collection_focus(
        self, collection_id: str, locale: str
    ) -> tuple[str, Path | None]:
        return (
            f"collection:{collection_id}",
            collection_title_audio(self._root, collection_id, locale),
        )

    def announce_activity(
        self, manifest: ActivityManifest, locale: str, pygame: Any
    ) -> bool:
        identity, clip = self.activity_focus(manifest, locale)
        self._pending = None
        return self._player.announce(identity, clip, pygame)

    def announce_collection(
        self, collection_id: str, locale: str, pygame: Any
    ) -> bool:
        identity, clip = self.collection_focus(collection_id, locale)
        self._pending = None
        return self._player.announce(identity, clip, pygame)

    def navigation_focus_changed(
        self, identity: str, clip: Path | None, pygame: Any
    ) -> bool:
        """Immediate announcement for keyboard/controller focus changes."""

        self._pending = None
        return self._player.announce(identity, clip, pygame)

    def pointer_focus_changed(
        self, identity: str | None, clip: Path | None, now: float
    ) -> None:
        """Stage or cancel a pending pointer announcement.

        ``identity`` is semantic (``activity:…`` or ``collection:…``) or
        ``None`` when the pointer left any speakable target.  The pending
        announcement fires after ``dwell_ms`` via
        :meth:`poll_pending_pointer_focus`.
        """

        if identity is None or clip is None:
            self._pending = None
            return
        if self._pending is not None and self._pending[0] == identity:
            return
        self._pending = (identity, clip, now + self._dwell_seconds)

    def poll_pending_pointer_focus(self, now: float, pygame: Any) -> bool:
        if self._pending is None:
            return False
        identity, clip, due_at = self._pending
        if now < due_at:
            return False
        self._pending = None
        return self._player.announce(identity, clip, pygame)

    def clear_pointer_focus(self) -> None:
        self._pending = None
        self._player.clear_focus()

    def poll_idle_audio(self, now: float, pygame: Any) -> bool:
        """Close the Shell mixer after its quiet period (see ``ShellMixerLease``)."""

        return self._player.poll_idle_audio(now, pygame)

    def release_audio(self, pygame: Any) -> bool:
        """Silence narration and close the Shell mixer immediately."""

        self._pending = None
        return self._player.release_audio(pygame)

    def stop(self) -> None:
        self._pending = None
        self._player.stop()
