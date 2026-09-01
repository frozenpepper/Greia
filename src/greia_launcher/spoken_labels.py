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
from typing import Any

from greia_platform.activities import ActivityManifest
from greia_platform.localization import LocalizationBundle, LocalizationError, LocaleTag
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


def activity_title_audio(manifest: ActivityManifest, locale: str) -> Path | None:
    """Resolve one Activity's localized launcher-title audio cue, if supplied."""

    for candidate in locale_candidates(locale):
        bundle_path = manifest.root / "locales" / f"{candidate.value}.json"
        if not bundle_path.is_file():
            continue
        try:
            cue = LocalizationBundle.load(manifest.root, candidate).audio.get(
                ACTIVITY_TITLE_CUE
            )
        except (LocalizationError, OSError):
            continue
        if cue is not None and cue.path.is_file():
            return cue.path
    return None


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


class SpokenLabelPlayer:
    """Interruptible, bounded launcher narration using pygame's existing mixer.

    ``identity`` is semantic (for example ``activity:org.greia.foo``). Repeated
    pointer-motion events over the same destination therefore do not replay the
    clip. A new destination stops/replaces the previous label instead of building
    an audio queue.
    """

    def __init__(self, *, cache_entries: int = 48) -> None:
        self._cache: BoundedCache[str, Any] = BoundedCache(cache_entries)
        self._last_identity: str | None = None
        self._channel: Any = None

    def clear_focus(self) -> None:
        """Allow the same destination to speak again after focus leaves it."""

        self._last_identity = None

    def announce(self, identity: str, clip: Path | None, pygame: Any) -> bool:
        if not identity or identity == self._last_identity:
            return False
        self._last_identity = identity
        if clip is None or not clip.is_file():
            return False
        try:
            if not pygame.mixer.get_init():
                return False
            key = str(clip.resolve())
            sound = self._cache.get(key)
            if sound is None:
                sound = pygame.mixer.Sound(key)
                self._cache.put(key, sound)
            if self._channel is None:
                self._channel = pygame.mixer.find_channel(force=True)
            if self._channel is None:
                return False
            self._channel.stop()
            self._channel.play(sound)
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
