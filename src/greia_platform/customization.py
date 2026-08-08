from __future__ import annotations

import json
import os
from itertools import islice
import tempfile
import tomllib
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable, Mapping


class CustomizationError(ValueError):
    """Raised when customization state or imported media is invalid."""


@dataclass(frozen=True, slots=True)
class ColorSwatch:
    swatch_id: str
    color: tuple[int, int, int]

    @property
    def hex_color(self) -> str:
        return "#" + "".join(f"{channel:02X}" for channel in self.color)


@dataclass(frozen=True, slots=True)
class ThemePalette:
    schema_version: int
    default_background: str
    default_accent: str
    default_text: str
    backgrounds: tuple[ColorSwatch, ...]
    accents: tuple[ColorSwatch, ...]
    texts: tuple[ColorSwatch, ...]

    @classmethod
    def load(cls, path: Path) -> "ThemePalette":
        with path.resolve(strict=True).open("rb") as handle:
            raw = tomllib.load(handle)
        defaults = _mapping(raw, "defaults")
        palette = cls(
            schema_version=_integer(raw, "schema_version", minimum=1),
            default_background=_text(defaults, "background"),
            default_accent=_text(defaults, "accent"),
            default_text=_text(defaults, "text"),
            backgrounds=_swatches(raw, "backgrounds"),
            accents=_swatches(raw, "accents"),
            texts=_swatches(raw, "texts"),
        )
        palette.background(palette.default_background)
        palette.accent(palette.default_accent)
        palette.text(palette.default_text)
        return palette

    def background(self, swatch_id: str) -> ColorSwatch:
        return _find_swatch(self.backgrounds, swatch_id, "background")

    def accent(self, swatch_id: str) -> ColorSwatch:
        return _find_swatch(self.accents, swatch_id, "accent")

    def text(self, swatch_id: str) -> ColorSwatch:
        return _find_swatch(self.texts, swatch_id, "text")


@dataclass(frozen=True, slots=True)
class ThemePreferences:
    schema_version: int
    background: str
    accent: str
    text: str
    wallpaper_enabled: bool = False


@dataclass(frozen=True, slots=True)
class ResolvedTheme:
    preferences: ThemePreferences
    background: tuple[int, int, int]
    panel: tuple[int, int, int]
    accent: tuple[int, int, int]
    text: tuple[int, int, int]
    accent_text: tuple[int, int, int]
    wallpaper_path: Path | None

    def as_json_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.preferences.schema_version,
            "background": self.preferences.background,
            "accent": self.preferences.accent,
            "text": self.preferences.text,
            "wallpaper_enabled": self.wallpaper_path is not None,
            "background_color": _rgb_hex(self.background),
            "panel_color": _rgb_hex(self.panel),
            "accent_color": _rgb_hex(self.accent),
            "text_color": _rgb_hex(self.text),
            "accent_text_color": _rgb_hex(self.accent_text),
        }


class ThemeStore:
    """Owns the small, bounded customization state shared by child and parent UI."""

    PREFERENCES_NAME = "theme.json"
    WALLPAPER_NAME = "wallpaper.jpg"

    def __init__(self, palette: ThemePalette, state_dir: Path):
        self.palette = palette
        self.state_dir = state_dir.resolve()

    @classmethod
    def load(cls, defaults_path: Path, state_dir: Path) -> "ThemeStore":
        return cls(ThemePalette.load(defaults_path), state_dir)

    @property
    def preferences_path(self) -> Path:
        return self.state_dir / self.PREFERENCES_NAME

    @property
    def wallpaper_path(self) -> Path:
        return self.state_dir / self.WALLPAPER_NAME

    def read_preferences(self) -> ThemePreferences:
        defaults = self.default_preferences()
        try:
            raw = json.loads(self.preferences_path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            return defaults
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            return defaults
        if not isinstance(raw, dict):
            return defaults
        try:
            schema_version = raw.get("schema_version", self.palette.schema_version)
            background = raw.get("background", defaults.background)
            accent = raw.get("accent", defaults.accent)
            text = raw.get("text", defaults.text)
            wallpaper_enabled = raw.get("wallpaper_enabled", False)
            if not isinstance(schema_version, int) or isinstance(schema_version, bool):
                raise CustomizationError("theme schema version must be an integer")
            if not all(isinstance(value, str) for value in (background, accent, text)):
                raise CustomizationError("theme swatch identifiers must be strings")
            if not isinstance(wallpaper_enabled, bool):
                raise CustomizationError("wallpaper_enabled must be a boolean")
            preferences = ThemePreferences(
                schema_version=schema_version,
                background=background,
                accent=accent,
                text=text,
                wallpaper_enabled=wallpaper_enabled,
            )
            self._validate(preferences)
            return preferences
        except (CustomizationError, TypeError, ValueError):
            return defaults

    def default_preferences(self) -> ThemePreferences:
        return ThemePreferences(
            schema_version=self.palette.schema_version,
            background=self.palette.default_background,
            accent=self.palette.default_accent,
            text=self.palette.default_text,
            wallpaper_enabled=False,
        )

    def resolve(self) -> ResolvedTheme:
        preferences = self.read_preferences()
        background = self.palette.background(preferences.background).color
        accent = self.palette.accent(preferences.accent).color
        text = self.palette.text(preferences.text).color
        wallpaper = self.wallpaper_path if preferences.wallpaper_enabled and self.wallpaper_path.is_file() else None
        return ResolvedTheme(
            preferences=preferences,
            background=background,
            panel=_mix(background, (255, 255, 255), 0.78),
            accent=accent,
            text=text,
            accent_text=_best_contrast_text(accent),
            wallpaper_path=wallpaper,
        )

    def set_colors(
        self,
        *,
        background: str | None = None,
        accent: str | None = None,
        text: str | None = None,
    ) -> ThemePreferences:
        current = self.read_preferences()
        updated = ThemePreferences(
            schema_version=self.palette.schema_version,
            background=background or current.background,
            accent=accent or current.accent,
            text=text or current.text,
            wallpaper_enabled=current.wallpaper_enabled,
        )
        self._validate(updated)
        self._write(updated)
        return updated

    def set_wallpaper_enabled(self, enabled: bool) -> ThemePreferences:
        current = self.read_preferences()
        if enabled and not self.wallpaper_path.is_file():
            raise CustomizationError("no imported wallpaper is available")
        updated = ThemePreferences(
            schema_version=self.palette.schema_version,
            background=current.background,
            accent=current.accent,
            text=current.text,
            wallpaper_enabled=enabled,
        )
        self._write(updated)
        return updated

    def clear_wallpaper(self) -> ThemePreferences:
        """Remove the managed image while preserving the child's color choices."""

        current = self.read_preferences()
        try:
            self.wallpaper_path.unlink()
        except FileNotFoundError:
            pass
        updated = ThemePreferences(
            schema_version=self.palette.schema_version,
            background=current.background,
            accent=current.accent,
            text=current.text,
            wallpaper_enabled=False,
        )
        self._write(updated)
        return updated

    def reset(self) -> None:
        for path in (self.preferences_path, self.wallpaper_path):
            try:
                path.unlink()
            except FileNotFoundError:
                pass

    def version_token(self) -> tuple[int, int]:
        return (_mtime_ns(self.preferences_path), _mtime_ns(self.wallpaper_path))

    def _write(self, preferences: ThemePreferences) -> None:
        self._validate(preferences)
        self.state_dir.mkdir(parents=True, exist_ok=True)
        payload = json.dumps(asdict(preferences), sort_keys=True, separators=(",", ":")) + "\n"
        _atomic_write_text(self.preferences_path, payload)

    def _validate(self, preferences: ThemePreferences) -> None:
        if preferences.schema_version != self.palette.schema_version:
            raise CustomizationError("theme schema version does not match the platform")
        self.palette.background(preferences.background)
        self.palette.accent(preferences.accent)
        self.palette.text(preferences.text)


@dataclass(frozen=True, slots=True)
class WallpaperCandidate:
    path: Path
    media_id: str
    display_name: str
    size_bytes: int


class RemovableImageScanner:
    ALLOWED_SUFFIXES = frozenset({".jpg", ".jpeg", ".png", ".webp", ".bmp", ".gif"})

    def __init__(
        self,
        media_root: Path,
        *,
        maximum_files: int = 80,
        maximum_depth: int = 4,
        maximum_source_bytes: int = 20 * 1024 * 1024,
        maximum_entries: int = 2_000,
        maximum_directories: int = 200,
    ):
        self.media_root = media_root.resolve()
        self.maximum_files = maximum_files
        self.maximum_depth = maximum_depth
        self.maximum_source_bytes = maximum_source_bytes
        self.maximum_entries = maximum_entries
        self.maximum_directories = maximum_directories

    def scan(self) -> tuple[WallpaperCandidate, ...]:
        """Return a bounded catalogue without traversing an entire large device."""

        if not self.media_root.is_dir():
            return ()
        candidates: list[WallpaperCandidate] = []
        inspected_entries = 0
        inspected_directories = 0
        try:
            mounts = sorted(self.media_root.iterdir(), key=lambda item: item.name.casefold())
        except OSError:
            return ()
        for mount in mounts:
            if len(candidates) >= self.maximum_files or inspected_entries >= self.maximum_entries:
                break
            if not mount.is_dir() or mount.is_symlink() or mount.name.startswith("."):
                continue
            queue: list[tuple[Path, int]] = [(mount, 0)]
            while queue and len(candidates) < self.maximum_files:
                if inspected_entries >= self.maximum_entries or inspected_directories >= self.maximum_directories:
                    break
                directory, depth = queue.pop(0)
                inspected_directories += 1
                try:
                    remaining = max(0, self.maximum_entries - inspected_entries)
                    if remaining == 0:
                        break
                    with os.scandir(directory) as iterator:
                        entries = sorted(
                            islice(iterator, remaining),
                            key=lambda entry: entry.name.casefold(),
                        )
                except OSError:
                    continue
                for entry in entries:
                    inspected_entries += 1
                    if inspected_entries > self.maximum_entries:
                        break
                    if entry.name.startswith(".") or entry.is_symlink():
                        continue
                    path = Path(entry.path)
                    try:
                        if entry.is_dir(follow_symlinks=False):
                            if depth + 1 < self.maximum_depth:
                                queue.append((path, depth + 1))
                            continue
                        if not entry.is_file(follow_symlinks=False):
                            continue
                        if path.suffix.casefold() not in self.ALLOWED_SUFFIXES:
                            continue
                        stat = entry.stat(follow_symlinks=False)
                    except OSError:
                        continue
                    if stat.st_size <= 0 or stat.st_size > self.maximum_source_bytes:
                        continue
                    candidates.append(
                        WallpaperCandidate(
                            path=path.resolve(),
                            media_id=mount.name,
                            display_name=path.stem[:80],
                            size_bytes=stat.st_size,
                        )
                    )
                    if len(candidates) >= self.maximum_files:
                        break
        candidates.sort(key=lambda candidate: (candidate.media_id.casefold(), candidate.path.as_posix().casefold()))
        return tuple(candidates)

    def validate_path(self, source: Path) -> Path:
        if source.is_symlink():
            raise CustomizationError("wallpaper source may not be a symbolic link")
        resolved = source.resolve(strict=True)
        if self.media_root not in resolved.parents:
            raise CustomizationError("wallpaper source is outside removable media")
        if resolved.is_symlink() or not resolved.is_file():
            raise CustomizationError("wallpaper source is not a regular file")
        if resolved.suffix.casefold() not in self.ALLOWED_SUFFIXES:
            raise CustomizationError("unsupported wallpaper image format")
        size = resolved.stat().st_size
        if size <= 0 or size > self.maximum_source_bytes:
            raise CustomizationError("wallpaper source exceeds the import size limit")
        return resolved


class WallpaperImporter:
    """Normalizes one removable-media image into a bounded managed wallpaper."""

    MAX_PIXELS = 12_000_000
    MAX_OUTPUT_BYTES = 2 * 1024 * 1024
    MAX_DIMENSIONS = (1600, 1200)

    def __init__(self, store: ThemeStore, scanner: RemovableImageScanner):
        self.store = store
        self.scanner = scanner

    def import_image(self, source: Path) -> Path:
        source = self.scanner.validate_path(source)
        try:
            from PIL import Image, ImageOps, UnidentifiedImageError
        except ImportError as exc:
            raise CustomizationError("the curated image runtime is unavailable") from exc

        self.store.state_dir.mkdir(parents=True, exist_ok=True)
        temporary = self.store.wallpaper_path.with_suffix(".tmp.jpg")
        try:
            Image.MAX_IMAGE_PIXELS = self.MAX_PIXELS
            with Image.open(source) as opened:
                if opened.width * opened.height > self.MAX_PIXELS:
                    raise CustomizationError("wallpaper has too many pixels")
                image = ImageOps.exif_transpose(opened)
                image.load()
                image = image.convert("RGB")
                image.thumbnail(self.MAX_DIMENSIONS, Image.Resampling.LANCZOS)
                self._save_bounded(image, temporary)
        except (
            OSError,
            ValueError,
            UnidentifiedImageError,
            Image.DecompressionBombError,
        ) as exc:
            temporary.unlink(missing_ok=True)
            if isinstance(exc, CustomizationError):
                raise
            raise CustomizationError(f"cannot import wallpaper: {exc}") from exc

        os.chmod(temporary, 0o660)
        temporary.replace(self.store.wallpaper_path)
        self.store.set_wallpaper_enabled(True)
        return self.store.wallpaper_path

    def _save_bounded(self, image: object, target: Path) -> None:
        working = image
        for quality in (84, 76, 68, 60):
            working.save(target, format="JPEG", quality=quality, optimize=True)  # type: ignore[attr-defined]
            if target.stat().st_size <= self.MAX_OUTPUT_BYTES:
                return
        working.thumbnail((1280, 960))  # type: ignore[attr-defined]
        working.save(target, format="JPEG", quality=60, optimize=True)  # type: ignore[attr-defined]
        if target.stat().st_size > self.MAX_OUTPUT_BYTES:
            target.unlink(missing_ok=True)
            raise CustomizationError("normalized wallpaper still exceeds the managed size limit")


def _mapping(container: Mapping[str, object], key: str) -> Mapping[str, object]:
    value = container.get(key)
    if not isinstance(value, dict):
        raise CustomizationError(f"{key} must be a table")
    return value


def _integer(container: Mapping[str, object], key: str, *, minimum: int) -> int:
    value = container.get(key)
    if not isinstance(value, int) or isinstance(value, bool) or value < minimum:
        raise CustomizationError(f"{key} must be an integer >= {minimum}")
    return value


def _text(container: Mapping[str, object], key: str) -> str:
    value = container.get(key)
    if not isinstance(value, str) or not value.strip():
        raise CustomizationError(f"{key} must be non-empty text")
    return value.strip()


def _swatches(container: Mapping[str, object], key: str) -> tuple[ColorSwatch, ...]:
    raw = container.get(key)
    if not isinstance(raw, list) or not raw:
        raise CustomizationError(f"{key} must be a non-empty array")
    result: list[ColorSwatch] = []
    seen: set[str] = set()
    for entry in raw:
        if not isinstance(entry, dict):
            raise CustomizationError(f"{key} contains an invalid swatch")
        swatch_id = _text(entry, "id")
        if swatch_id in seen:
            raise CustomizationError(f"duplicate {key} swatch: {swatch_id}")
        seen.add(swatch_id)
        result.append(ColorSwatch(swatch_id, _parse_hex(_text(entry, "color"))))
    return tuple(result)


def _find_swatch(swatches: Iterable[ColorSwatch], swatch_id: str, kind: str) -> ColorSwatch:
    for swatch in swatches:
        if swatch.swatch_id == swatch_id:
            return swatch
    raise CustomizationError(f"unknown {kind} swatch: {swatch_id}")


def _parse_hex(value: str) -> tuple[int, int, int]:
    if len(value) != 7 or not value.startswith("#"):
        raise CustomizationError(f"invalid RGB color: {value}")
    try:
        return tuple(int(value[index : index + 2], 16) for index in (1, 3, 5))  # type: ignore[return-value]
    except ValueError as exc:
        raise CustomizationError(f"invalid RGB color: {value}") from exc


def _mix(left: tuple[int, int, int], right: tuple[int, int, int], right_weight: float) -> tuple[int, int, int]:
    return tuple(round(a * (1.0 - right_weight) + b * right_weight) for a, b in zip(left, right))  # type: ignore[return-value]


def _relative_luminance(color: tuple[int, int, int]) -> float:
    values = []
    for channel in color:
        value = channel / 255.0
        values.append(value / 12.92 if value <= 0.04045 else ((value + 0.055) / 1.055) ** 2.4)
    return values[0] * 0.2126 + values[1] * 0.7152 + values[2] * 0.0722


def _best_contrast_text(background: tuple[int, int, int]) -> tuple[int, int, int]:
    return (32, 27, 24) if _relative_luminance(background) > 0.45 else (255, 255, 255)


def _rgb_hex(color: tuple[int, int, int]) -> str:
    return "#" + "".join(f"{channel:02X}" for channel in color)


def _mtime_ns(path: Path) -> int:
    try:
        return path.stat().st_mtime_ns
    except OSError:
        return 0


def _atomic_write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temporary, 0o660)
        temporary.replace(path)
    except BaseException:
        temporary.unlink(missing_ok=True)
        raise
