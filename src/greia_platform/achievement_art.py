from __future__ import annotations

import struct
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

from .activities import ActivityManifest


_MAX_EMBLEMS_PER_ACTIVITY = 12
_MAX_EMBLEM_BYTES = 512 * 1024
_MIN_EMBLEM_DIMENSION = 32
_MAX_EMBLEM_DIMENSION = 1024
_PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


class ActivityAchievementArtError(ValueError):
    """An Activity's optional achievement artwork is unsafe or malformed."""


@dataclass(frozen=True, slots=True)
class ActivityAchievementEmblem:
    """One Activity-owned decorative emblem admitted by Greia policy.

    The Activity owns only this visual contribution. It cannot create a global
    achievement, choose an unlock condition, mutate profile progress, select a
    tier/frame, or write child-facing global achievement copy.
    """

    activity_id: str
    emblem_id: str
    asset_path: Path
    width: int
    height: int
    byte_size: int


def load_activity_achievement_emblems(
    manifest: ActivityManifest,
) -> tuple[ActivityAchievementEmblem, ...]:
    """Read and validate optional ``achievement_art.emblems`` from an Activity.

    V1 deliberately accepts only small square PNG emblems. Greia renders the
    trusted medal/trophy/rosette frame around the emblem, which keeps the shared
    library coherent and avoids runtime SVG or arbitrary drawing execution.
    """

    manifest_path = manifest.root / "activity.toml"
    try:
        with manifest_path.open("rb") as handle:
            raw = tomllib.load(handle)
    except (OSError, tomllib.TOMLDecodeError) as exc:
        raise ActivityAchievementArtError(
            f"cannot read Activity achievement art from {manifest_path}: {exc}"
        ) from exc

    raw_art = raw.get("achievement_art")
    if raw_art is None:
        return ()
    if not isinstance(raw_art, dict):
        raise ActivityAchievementArtError("achievement_art must be a table")

    unknown_art_keys = set(raw_art) - {"emblems"}
    if unknown_art_keys:
        raise ActivityAchievementArtError(
            "unsupported achievement_art keys: " + ", ".join(sorted(unknown_art_keys))
        )

    raw_emblems = raw_art.get("emblems", [])
    if not isinstance(raw_emblems, list) or not all(
        isinstance(item, dict) for item in raw_emblems
    ):
        raise ActivityAchievementArtError(
            "achievement_art.emblems must be an array of tables"
        )
    if len(raw_emblems) > _MAX_EMBLEMS_PER_ACTIVITY:
        raise ActivityAchievementArtError(
            f"an Activity may declare at most {_MAX_EMBLEMS_PER_ACTIVITY} achievement emblems"
        )

    result: list[ActivityAchievementEmblem] = []
    seen: set[str] = set()
    for raw_emblem in raw_emblems:
        assert isinstance(raw_emblem, dict)
        unknown_keys = set(raw_emblem) - {"id", "asset"}
        if unknown_keys:
            raise ActivityAchievementArtError(
                "unsupported achievement emblem keys: "
                + ", ".join(sorted(unknown_keys))
            )

        emblem_id = _bounded_id(raw_emblem.get("id"), "achievement emblem id")
        if emblem_id in seen:
            raise ActivityAchievementArtError(
                f"duplicate achievement emblem id: {emblem_id}"
            )
        seen.add(emblem_id)

        asset = raw_emblem.get("asset")
        if not isinstance(asset, str) or not asset.strip():
            raise ActivityAchievementArtError("achievement emblem asset must be text")
        relative = Path(asset.strip())
        if relative.is_absolute() or ".." in relative.parts:
            raise ActivityAchievementArtError(
                "achievement emblem asset must be a safe relative path"
            )
        if relative.suffix.casefold() != ".png":
            raise ActivityAchievementArtError(
                "achievement emblem asset must be a PNG file"
            )

        unresolved = manifest.root / relative
        # Check the package entry itself before resolve(): resolving first would
        # erase the information that the entry was a symlink. ActivityRegistry
        # already rejects package symlinks globally, but this art boundary must
        # remain safe when called independently in tests/tooling too.
        try:
            if unresolved.is_symlink():
                raise ActivityAchievementArtError(
                    "achievement emblem asset cannot be a symlink"
                )
        except OSError as exc:
            raise ActivityAchievementArtError(
                f"cannot inspect achievement emblem asset: {relative.as_posix()}"
            ) from exc

        try:
            asset_path = unresolved.resolve(strict=True)
        except OSError as exc:
            raise ActivityAchievementArtError(
                f"achievement emblem asset does not exist: {relative.as_posix()}"
            ) from exc
        if manifest.root not in asset_path.parents or not asset_path.is_file():
            raise ActivityAchievementArtError(
                "achievement emblem asset must be a file inside its Activity package"
            )

        try:
            byte_size = asset_path.stat().st_size
        except OSError as exc:
            raise ActivityAchievementArtError(
                f"cannot inspect achievement emblem asset: {relative.as_posix()}"
            ) from exc
        if byte_size <= 0 or byte_size > _MAX_EMBLEM_BYTES:
            raise ActivityAchievementArtError(
                f"achievement emblem asset must be 1..{_MAX_EMBLEM_BYTES} bytes"
            )

        width, height = _png_dimensions(asset_path)
        if width != height:
            raise ActivityAchievementArtError(
                "achievement emblem PNG must be square"
            )
        if not (
            _MIN_EMBLEM_DIMENSION <= width <= _MAX_EMBLEM_DIMENSION
            and _MIN_EMBLEM_DIMENSION <= height <= _MAX_EMBLEM_DIMENSION
        ):
            raise ActivityAchievementArtError(
                "achievement emblem PNG dimensions must be between "
                f"{_MIN_EMBLEM_DIMENSION} and {_MAX_EMBLEM_DIMENSION} pixels"
            )

        result.append(
            ActivityAchievementEmblem(
                activity_id=manifest.activity_id,
                emblem_id=emblem_id,
                asset_path=asset_path,
                width=width,
                height=height,
                byte_size=byte_size,
            )
        )

    return tuple(result)


def emblem_map(
    manifest: ActivityManifest,
) -> Mapping[str, ActivityAchievementEmblem]:
    return {
        item.emblem_id: item for item in load_activity_achievement_emblems(manifest)
    }


def _png_dimensions(path: Path) -> tuple[int, int]:
    try:
        with path.open("rb") as handle:
            header = handle.read(24)
    except OSError as exc:
        raise ActivityAchievementArtError(f"cannot read achievement emblem PNG: {path}") from exc
    if len(header) < 24 or header[:8] != _PNG_SIGNATURE or header[12:16] != b"IHDR":
        raise ActivityAchievementArtError("achievement emblem asset is not a valid PNG")
    width, height = struct.unpack(">II", header[16:24])
    if width <= 0 or height <= 0:
        raise ActivityAchievementArtError("achievement emblem PNG has invalid dimensions")
    return width, height


def _bounded_id(value: object, label: str) -> str:
    if not isinstance(value, str):
        raise ActivityAchievementArtError(f"{label} must be text")
    normalized = value.strip().casefold()
    allowed = set("abcdefghijklmnopqrstuvwxyz0123456789._-")
    if (
        not normalized
        or len(normalized) > 96
        or not normalized[0].isalnum()
        or not normalized[-1].isalnum()
        or any(character not in allowed for character in normalized)
    ):
        raise ActivityAchievementArtError(
            f"{label} must be a bounded lower-case identifier"
        )
    return normalized


__all__ = [
    "ActivityAchievementArtError",
    "ActivityAchievementEmblem",
    "emblem_map",
    "load_activity_achievement_emblems",
]
