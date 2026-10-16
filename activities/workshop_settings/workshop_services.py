"""Greia platform adapters for My Greia.

Every choice is saved through the existing trusted customization services:
the avatar through the profile avatar request (``set_active_profile_avatar``),
room/sparkle colours through ``set_theme_color``, pictures through the managed
wallpaper (``set_curated_wallpaper`` / ``disable_wallpaper``) and size through
``set_interface_size``. Nothing here invents storage: the only Activity-owned
record is a tiny note in this Activity's own Greia Storage remembering *which*
curated scene became the wallpaper, so the matching picture tile can be shown
as chosen next time (the managed wallpaper file itself is a normalized copy).

The app depends on the narrow ``CustomizationPort`` protocol, so tests and
tools inject an in-memory implementation instead of touching profile state.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from greia_platform.activity_api import (
    disable_wallpaper,
    get_active_profile,
    get_profile_avatar_choices,
    get_storage,
    get_theme,
    get_theme_palette,
    get_ui_preferences,
    set_active_profile_avatar,
    set_curated_wallpaper,
    set_interface_size,
    set_theme_color,
)

if not __package__:
    __package__ = "activities.workshop_settings"  # type: ignore[assignment]

try:
    from .workshop_content import AVATAR_PRIORITY, CURATED_WALLPAPERS, CUSTOM_CHOICE, MEADOW_CHOICE
    from .workshop_model import ChoiceKind, Look
except ImportError:
    from workshop_content import AVATAR_PRIORITY, CURATED_WALLPAPERS, CUSTOM_CHOICE, MEADOW_CHOICE  # type: ignore[no-redef]
    from workshop_model import ChoiceKind, Look  # type: ignore[no-redef]

Rgb = tuple[int, int, int]
WALLPAPER_NOTE_KEY = "my_greia.wallpaper.v1"
_SIZES = ("compact", "normal", "large")
_DEFAULT_TEXT: Rgb = (61, 44, 31)


@dataclass(frozen=True, slots=True)
class Swatch:
    swatch_id: str
    color: Rgb


@dataclass(frozen=True, slots=True)
class MyGreiaChoices:
    """The bounded choice sets offered to the child."""

    avatars: tuple[str, ...]
    backgrounds: tuple[Swatch, ...]
    accents: tuple[Swatch, ...]
    wallpapers: tuple[str, ...] = (MEADOW_CHOICE, *CURATED_WALLPAPERS)
    sizes: tuple[str, ...] = _SIZES

    def background(self, swatch_id: str) -> Rgb:
        return _lookup(self.backgrounds, swatch_id)

    def accent(self, swatch_id: str) -> Rgb:
        return _lookup(self.accents, swatch_id)


@dataclass(frozen=True, slots=True)
class LoadedState:
    look: Look
    choices: MyGreiaChoices
    text_color: Rgb = _DEFAULT_TEXT
    custom_wallpaper: Path | None = None


class CustomizationPort(Protocol):
    """Narrow persistence seam used by the app (Greia or in-memory)."""

    def load(self) -> LoadedState: ...

    def apply(self, before: Look, after: Look) -> Look:
        """Persist ``after``; return the look the platform actually holds."""
        ...


def ordered_avatars(policy: tuple[str, ...]) -> tuple[str, ...]:
    """Cast-face avatars first (in the cast order), then the rest of the policy."""

    first = tuple(avatar for avatar in AVATAR_PRIORITY if avatar in policy)
    return first + tuple(avatar for avatar in policy if avatar not in first)


class GreiaCustomization:
    """Map My Greia looks onto the trusted Greia customization services."""

    def __init__(self, storage=None) -> None:
        self._storage = storage

    def _store(self):
        if self._storage is None:
            self._storage = get_storage()
        return self._storage

    def load(self) -> LoadedState:
        palette = get_theme_palette()
        theme = get_theme()
        profile = get_active_profile()
        avatars = ordered_avatars(tuple(get_profile_avatar_choices()))
        avatar = str(profile.get("avatar_id") or "")
        if avatar not in avatars and avatars:
            avatar = avatars[0]
        choices = MyGreiaChoices(
            avatars=avatars,
            backgrounds=tuple(Swatch(s.swatch_id, tuple(s.color)) for s in palette.backgrounds),  # type: ignore[arg-type]
            accents=tuple(Swatch(s.swatch_id, tuple(s.color)) for s in palette.accents),  # type: ignore[arg-type]
        )
        wallpaper_path = getattr(theme, "wallpaper_path", None)
        wallpaper = self._identify_wallpaper(wallpaper_path)
        look = Look(
            avatar=avatar,
            background=str(theme.preferences.background),
            accent=str(theme.preferences.accent),
            wallpaper=wallpaper,
            size=get_ui_preferences().interface_size.value,
        )
        return LoadedState(
            look=look,
            choices=choices,
            text_color=tuple(theme.text),  # type: ignore[arg-type]
            custom_wallpaper=wallpaper_path if wallpaper == CUSTOM_CHOICE else None,
        )

    def apply(self, before: Look, after: Look) -> Look:
        applied = before
        for kind in after.changed_kinds(before):
            value = after.value(kind)
            try:
                self._apply_one(kind, value)
            except (OSError, PermissionError, RuntimeError, ValueError, KeyError):
                continue
            applied = applied.with_value(kind, value)
        return applied

    # -- internals ----------------------------------------------------------

    def _apply_one(self, kind: ChoiceKind, value: str) -> None:
        if kind is ChoiceKind.AVATAR:
            set_active_profile_avatar(value)
        elif kind is ChoiceKind.BACKGROUND:
            set_theme_color("background", value)
        elif kind is ChoiceKind.ACCENT:
            set_theme_color("accent", value)
        elif kind is ChoiceKind.SIZE:
            set_interface_size(value)
        elif kind is ChoiceKind.WALLPAPER:
            if value == MEADOW_CHOICE:
                disable_wallpaper()
                self._forget_wallpaper()
            elif value in CURATED_WALLPAPERS:
                path = set_curated_wallpaper(value)
                self._remember_wallpaper(value, path)
            else:
                # An earlier imported picture cannot be recreated here.
                raise ValueError("custom wallpaper cannot be re-applied")

    def _identify_wallpaper(self, path: Path | None) -> str:
        if path is None:
            return MEADOW_CHOICE
        try:
            note = self._store().kv_get(WALLPAPER_NOTE_KEY)
            stat = path.stat()
        except Exception:
            return CUSTOM_CHOICE
        if (
            isinstance(note, dict)
            and note.get("schema_version") == 1
            and note.get("id") in CURATED_WALLPAPERS
            and note.get("mtime_ns") == stat.st_mtime_ns
            and note.get("size") == stat.st_size
        ):
            return str(note["id"])
        return CUSTOM_CHOICE

    def _remember_wallpaper(self, asset_id: str, path: Path) -> None:
        try:
            stat = Path(path).stat()
            self._store().kv_set(
                WALLPAPER_NOTE_KEY,
                {"schema_version": 1, "id": asset_id, "mtime_ns": stat.st_mtime_ns, "size": stat.st_size},
            )
        except Exception:
            # The wallpaper itself is saved; only the "which tile" note is lost.
            return

    def _forget_wallpaper(self) -> None:
        try:
            self._store().kv_delete(WALLPAPER_NOTE_KEY)
        except Exception:
            return


def _lookup(swatches: tuple[Swatch, ...], swatch_id: str) -> Rgb:
    for swatch in swatches:
        if swatch.swatch_id == swatch_id:
            return swatch.color
    return swatches[0].color if swatches else (247, 235, 203)


__all__ = [
    "CustomizationPort",
    "GreiaCustomization",
    "LoadedState",
    "MyGreiaChoices",
    "Swatch",
    "WALLPAPER_NOTE_KEY",
    "ordered_avatars",
]
