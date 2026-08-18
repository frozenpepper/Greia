"""Bounded read-only theme snapshots for ordinary Activity launches.

An Activity should be able to respect the active child's visual choices without
receiving the profile customization directory or `customization.manage`.
Snapshots contain resolved presentation values only; wallpaper files and write
paths remain outside ordinary Activity authority.
"""

from __future__ import annotations

import json
from typing import Mapping

from .customization import ResolvedTheme, ThemePreferences


MAX_THEME_SNAPSHOT_BYTES = 2048


class ThemeSnapshotError(ValueError):
    pass


def encode_theme_snapshot(theme: ResolvedTheme) -> str:
    payload = {
        "schema_version": 1,
        "background": theme.preferences.background,
        "accent": theme.preferences.accent,
        "text": theme.preferences.text,
        "background_color": _rgb_hex(theme.background),
        "panel_color": _rgb_hex(theme.panel),
        "accent_color": _rgb_hex(theme.accent),
        "text_color": _rgb_hex(theme.text),
        "accent_text_color": _rgb_hex(theme.accent_text),
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    if len(encoded.encode("utf-8")) > MAX_THEME_SNAPSHOT_BYTES:
        raise ThemeSnapshotError("resolved theme snapshot exceeds bound")
    return encoded


def decode_theme_snapshot(raw: str) -> ResolvedTheme:
    if not isinstance(raw, str) or not raw:
        raise ThemeSnapshotError("theme snapshot must be non-empty text")
    if len(raw.encode("utf-8")) > MAX_THEME_SNAPSHOT_BYTES:
        raise ThemeSnapshotError("theme snapshot exceeds bound")
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ThemeSnapshotError("theme snapshot must be valid JSON") from exc
    if not isinstance(payload, dict) or payload.get("schema_version") != 1:
        raise ThemeSnapshotError("unsupported theme snapshot schema")
    background_id = _id(payload, "background")
    accent_id = _id(payload, "accent")
    text_id = _id(payload, "text")
    return ResolvedTheme(
        preferences=ThemePreferences(
            schema_version=1,
            background=background_id,
            accent=accent_id,
            text=text_id,
            wallpaper_enabled=False,
        ),
        background=_rgb(payload, "background_color"),
        panel=_rgb(payload, "panel_color"),
        accent=_rgb(payload, "accent_color"),
        text=_rgb(payload, "text_color"),
        accent_text=_rgb(payload, "accent_text_color"),
        wallpaper_path=None,
    )


def _id(payload: Mapping[str, object], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value or len(value) > 64:
        raise ThemeSnapshotError(f"invalid theme snapshot {key}")
    allowed = "abcdefghijklmnopqrstuvwxyz0123456789._-"
    if value != value.lower() or any(character not in allowed for character in value):
        raise ThemeSnapshotError(f"invalid theme snapshot {key}")
    return value


def _rgb(payload: Mapping[str, object], key: str) -> tuple[int, int, int]:
    value = payload.get(key)
    if not isinstance(value, str) or len(value) != 7 or not value.startswith("#"):
        raise ThemeSnapshotError(f"invalid theme snapshot {key}")
    try:
        return tuple(int(value[index : index + 2], 16) for index in (1, 3, 5))  # type: ignore[return-value]
    except ValueError as exc:
        raise ThemeSnapshotError(f"invalid theme snapshot {key}") from exc


def _rgb_hex(color: tuple[int, int, int]) -> str:
    if len(color) != 3 or any(
        not isinstance(channel, int) or isinstance(channel, bool) or channel < 0 or channel > 255
        for channel in color
    ):
        raise ThemeSnapshotError("resolved theme contains invalid RGB value")
    return "#" + "".join(f"{channel:02X}" for channel in color)


__all__ = [
    "MAX_THEME_SNAPSHOT_BYTES",
    "ThemeSnapshotError",
    "decode_theme_snapshot",
    "encode_theme_snapshot",
]
