"""Runtime-neutral Greia localization primitives.

This module deliberately uses JSON localization bundles so Python Activities and
future Web runtimes can share one package format.  It owns locale normalization,
fallback selection, bounded string/audio catalogue loading, semantic lookup and
small semantic resource variants.  It does not own Parent/profile persistence or
renderer-specific text layout.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
import json
import tomllib
from pathlib import Path, PurePosixPath
from string import Template
from typing import Mapping

from .child_text import display_text


MAX_BUNDLE_BYTES = 256 * 1024
MAX_STRING_ENTRIES = 1024
MAX_AUDIO_ENTRIES = 256
MAX_STRING_CHARS = 8192
MAX_KEY_CHARS = 160
MAX_VARIANT_CHARS = 48
_ALLOWED_AUDIO_SUFFIXES = frozenset({".ogg", ".wav"})


class LocalizationError(ValueError):
    """Raised when locale metadata or localized package resources are invalid."""


class TextDirection(StrEnum):
    LTR = "ltr"
    RTL = "rtl"


@dataclass(frozen=True, slots=True)
class LocaleTag:
    """Canonical, bounded BCP-47-style locale tag used by Greia.

    Greia intentionally implements a conservative interoperable subset rather
    than pretending to be a complete BCP-47 registry.  It accepts a language,
    optional script, optional region, and bounded variants; extension/private-use
    sequences can be added later if the product needs them.
    """

    value: str

    @classmethod
    def parse(cls, raw: str) -> "LocaleTag":
        if not isinstance(raw, str):
            raise LocalizationError("locale tag must be text")
        value = raw.strip()
        if not value or len(value) > 64 or "_" in value:
            raise LocalizationError("locale tag must be a bounded hyphenated tag")
        parts = value.split("-")
        if any(not part or not part.isalnum() for part in parts):
            raise LocalizationError("locale tag contains invalid subtags")

        language = parts[0]
        if not (2 <= len(language) <= 8 and language.isalpha()):
            raise LocalizationError("locale language subtag must contain 2..8 letters")

        canonical = [language.lower()]
        index = 1
        if index < len(parts) and len(parts[index]) == 4 and parts[index].isalpha():
            canonical.append(parts[index].title())
            index += 1
        if index < len(parts):
            region = parts[index]
            if (len(region) == 2 and region.isalpha()) or (
                len(region) == 3 and region.isdigit()
            ):
                canonical.append(region.upper())
                index += 1
        for variant in parts[index:]:
            if not (4 <= len(variant) <= 8 and variant.isalnum()):
                raise LocalizationError("locale variant subtag must contain 4..8 letters/digits")
            canonical.append(variant.lower())
        return cls("-".join(canonical))

    @property
    def language(self) -> str:
        return self.value.split("-", 1)[0]

    def fallback_chain(self) -> tuple["LocaleTag", ...]:
        """Return most-specific to least-specific locale fallbacks.

        Example: `zh-Hant-TW` -> `zh-Hant-TW`, `zh-Hant`, `zh`.
        """

        parts = self.value.split("-")
        return tuple(LocaleTag("-".join(parts[:count])) for count in range(len(parts), 0, -1))

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True, slots=True)
class LocaleContext:
    """Resolved UI locale inherited by one child/Activity launch."""

    requested: LocaleTag
    selected: LocaleTag
    fallback_chain: tuple[LocaleTag, ...]
    direction: TextDirection

    def __post_init__(self) -> None:
        if not self.fallback_chain:
            raise LocalizationError("locale fallback chain must not be empty")
        if self.fallback_chain[0] != self.selected:
            raise LocalizationError("selected locale must lead the fallback chain")


@dataclass(frozen=True, slots=True)
class ActivityLocaleSupport:
    """One Activity's UI-localization declaration.

    `language_neutral=True` means the Activity itself contains no locale-specific
    user-facing UI/audio and may run under any Greia UI locale.  It is not a
    claim that arbitrary hard-coded English strings count as localized.
    """

    ui_locales: tuple[LocaleTag, ...] = ()
    default_ui_locale: LocaleTag | None = None
    language_neutral: bool = False

    def __post_init__(self) -> None:
        if self.language_neutral:
            if self.ui_locales or self.default_ui_locale is not None:
                raise LocalizationError(
                    "language-neutral Activity cannot also declare localized UI locales"
                )
            return
        if not self.ui_locales:
            raise LocalizationError("localized Activity must declare at least one UI locale")
        if len({item.value for item in self.ui_locales}) != len(self.ui_locales):
            raise LocalizationError("Activity UI locales must be unique")
        if self.default_ui_locale is None:
            raise LocalizationError("localized Activity must declare a default UI locale")
        if self.default_ui_locale not in self.ui_locales:
            raise LocalizationError("default UI locale must be one of the Activity UI locales")

    @classmethod
    def neutral(cls) -> "ActivityLocaleSupport":
        return cls(language_neutral=True)

    @classmethod
    def localized(
        cls,
        ui_locales: tuple[str, ...],
        *,
        default_ui_locale: str,
    ) -> "ActivityLocaleSupport":
        return cls(
            ui_locales=tuple(LocaleTag.parse(item) for item in ui_locales),
            default_ui_locale=LocaleTag.parse(default_ui_locale),
        )


def resolve_activity_locale(
    requested_ui_locale: str | LocaleTag,
    support: ActivityLocaleSupport,
    *,
    direction_by_language: Mapping[str, TextDirection | str] | None = None,
) -> LocaleContext | None:
    """Resolve one profile/device UI locale against Activity package support.

    Language-neutral Activities return None because they have no package-local
    translation catalogue to select.  Platform chrome still uses the profile's
    normal Greia locale outside the Activity's authority.
    """

    requested = (
        requested_ui_locale
        if isinstance(requested_ui_locale, LocaleTag)
        else LocaleTag.parse(requested_ui_locale)
    )
    if support.language_neutral:
        return None

    supported = {item.value: item for item in support.ui_locales}
    candidates: list[LocaleTag] = []
    for candidate in requested.fallback_chain():
        if candidate.value in supported and candidate not in candidates:
            candidates.append(supported[candidate.value])
    assert support.default_ui_locale is not None
    for candidate in support.default_ui_locale.fallback_chain():
        if candidate.value in supported and supported[candidate.value] not in candidates:
            candidates.append(supported[candidate.value])
    if not candidates:
        raise LocalizationError("Activity locale declaration has no usable fallback")

    selected = candidates[0]
    direction = _direction_for(selected, direction_by_language or {})
    return LocaleContext(
        requested=requested,
        selected=selected,
        fallback_chain=tuple(candidates),
        direction=direction,
    )


def activity_resources(
    package_root: Path,
    *,
    requested_locale: str | None = None,
    supported_locales: tuple[str, ...] | None = None,
    default_ui_locale: str | None = None,
) -> "LocalizedResources":
    """Compose one Activity's localized strings and audio from Greia settings.

    Normally the Activity declares its supported UI languages in activity.toml;
    only isolated staging/test callers need override these arguments. The
    platform owns profile/device-language lookup, not each game's renderer.
    """
    root = package_root.resolve(strict=True)
    if supported_locales is None:
        try:
            metadata = tomllib.loads((root / "activity.toml").read_text(encoding="utf-8"))
            raw_languages = metadata["activity"]["languages"]
        except (OSError, KeyError, TypeError, tomllib.TOMLDecodeError) as exc:
            raise LocalizationError("Activity has no readable language declaration") from exc
        if not isinstance(raw_languages, list) or not all(
            isinstance(item, str) for item in raw_languages
        ):
            raise LocalizationError("Activity language declaration must be a list of locales")
        supported_locales = tuple(raw_languages)
    if not supported_locales:
        raise LocalizationError("Activity declares no localized UI languages")
    if requested_locale is None:
        from .activity_api import get_profile_locale

        requested_locale = get_profile_locale()
    if default_ui_locale is None:
        default_ui_locale = (
            "it" if "it" in supported_locales else supported_locales[0]
        )
    support = ActivityLocaleSupport.localized(
        supported_locales, default_ui_locale=default_ui_locale
    )
    context = resolve_activity_locale(requested_locale, support)
    if context is None:
        raise LocalizationError("Activity declares language-neutral UI")
    return LocalizedResources(root, context)



@dataclass(frozen=True, slots=True)
class LocalizedAudioCue:
    path: Path
    caption_key: str | None = None


@dataclass(frozen=True, slots=True)
class LocalizationBundle:
    locale: LocaleTag
    direction: TextDirection
    strings: Mapping[str, str]
    audio: Mapping[str, LocalizedAudioCue]

    @classmethod
    def load(cls, package_root: Path, locale: LocaleTag) -> "LocalizationBundle":
        root = package_root.resolve(strict=True)
        bundle_path = root / "locales" / f"{locale.value}.json"
        try:
            size = bundle_path.stat().st_size
        except OSError as exc:
            raise LocalizationError(f"missing localization bundle for {locale.value}") from exc
        if size < 1 or size > MAX_BUNDLE_BYTES:
            raise LocalizationError("localization bundle exceeds size limit")
        try:
            raw = json.loads(bundle_path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise LocalizationError("localization bundle must be valid UTF-8 JSON") from exc
        if not isinstance(raw, dict) or raw.get("schema_version") != 1:
            raise LocalizationError("unsupported localization bundle schema")
        declared = raw.get("locale")
        if not isinstance(declared, str) or LocaleTag.parse(declared) != locale:
            raise LocalizationError("localization bundle locale does not match file name")
        direction = _parse_direction(raw.get("direction", "ltr"))
        strings = _string_table(raw.get("strings", {}))
        audio = _audio_table(root, raw.get("audio", {}))
        return cls(locale, direction, strings, audio)


class LocalizedResources:
    """Per-launch semantic string/audio resolver with per-key locale fallback.

    A caller may provide a small semantic ``variant`` such as ``masculine`` or
    ``feminine``.  The bundle continues to use ordinary semantic keys: Greia
    first tries ``<key>.<variant>`` inside each preferred locale, then the base
    key in that same locale.  This ordering matters: an Italian neutral phrase
    is preferred over an English gendered phrase when Italian lacks a variant.

    The mechanism is deliberately generic and bounded.  It is not a full
    grammatical-message language and it must not be used to fragment gameplay.
    """

    def __init__(
        self,
        package_root: Path,
        context: LocaleContext,
    ) -> None:
        self.package_root = package_root.resolve(strict=True)
        self.context = context
        self._bundles = tuple(
            LocalizationBundle.load(self.package_root, locale)
            for locale in context.fallback_chain
        )
        # English can be a sound fallback even if the Activity default is IT.
        self._english_bundle = next(
            (bundle for bundle in self._bundles if bundle.locale.value == "en"), None
        )
        if self._english_bundle is None and (self.package_root / "locales" / "en.json").is_file():
            self._english_bundle = LocalizationBundle.load(
                self.package_root, LocaleTag.parse("en")
            )
        ordered = list(self._bundles[:1])
        if self._english_bundle is not None and self._english_bundle not in ordered:
            ordered.append(self._english_bundle)
        for bundle in self._bundles[1:]:
            if bundle not in ordered:
                ordered.append(bundle)
        self._text_bundles = tuple(ordered)

    def text(
        self,
        key: str,
        variables: Mapping[str, object] | None = None,
        *,
        variant: str | None = None,
    ) -> str:
        """Resolve one display string under the profile letter-case policy.

        Returned text is child-facing presentation: Greia's default presents
        it in CAPITAL letters unless this child's parent chose normal text.
        Semantic keys and audio cue lookup are never case-transformed.
        """
        key = _resource_key(key)
        lookup_keys = _variant_keys(key, variant)
        value: str | None = None
        for bundle in self._text_bundles:
            for lookup_key in lookup_keys:
                value = bundle.strings.get(lookup_key)
                if value is not None:
                    break
            if value is not None:
                break
        if value is None:
            raise LocalizationError(f"missing localized string: {key}")
        if variables is None:
            variables = {}
        if not isinstance(variables, Mapping):
            raise LocalizationError("localized variables must be a mapping")
        safe: dict[str, str] = {}
        for name, replacement in variables.items():
            name = _placeholder_name(name)
            rendered = str(replacement)
            if len(rendered) > 512 or "\x00" in rendered:
                raise LocalizationError("localized replacement value is invalid")
            safe[name] = rendered
        try:
            return display_text(Template(value).substitute(safe))
        except (KeyError, ValueError) as exc:
            raise LocalizationError(
                f"localized string {key!r} has an unresolved/invalid placeholder"
            ) from exc


    def audio_path(
        self,
        key: str,
        *,
        variant: str | None = None,
        filename: str | None = None,
        allow_fallback: bool = True,
    ) -> Path | None:
        """Find the actual prerecorded speech file, without playing it.

        Resolve the selected-language file first, using any explicit local
        mapping, the English catalogue's stable filename, or conventional
        assets/audio files. Otherwise try the English recording.
        """
        cue = self._resolve_audio(
            key, variant=variant, filename=filename, allow_fallback=allow_fallback
        )
        return cue.path if cue is not None else None

    def speech_paths(self) -> dict[str, Path]:
        """List short prerecorded clips for eager Activity sound caches.

        The locale resolver owns file discovery and English fallback; an
        Activity may keep its own mixer, channels and sound decoding. Both
        existing package speech directories work without per-locale JSON.
        These are filenames, not a promise that every semantic cue exists.
        """
        selected = self.context.selected.value
        folders = (
            self.package_root / "assets" / "audio" / selected,
            self.package_root / "locales" / selected / "audio",
            self.package_root / "assets" / "audio" / "en",
            self.package_root / "locales" / "en" / "audio",
        )
        names: dict[str, str] = {}
        for folder in folders:
            if not folder.is_dir():
                continue
            for candidate in sorted(folder.iterdir()):
                if candidate.is_file() and candidate.suffix.lower() in _ALLOWED_AUDIO_SUFFIXES:
                    names.setdefault(candidate.stem, candidate.name)
        result: dict[str, Path] = {}
        for stem, filename in names.items():
            path = self.audio_path(stem, filename=filename)
            if path is not None:
                result[stem] = path
        return result

    def audio_cue(
        self,
        key: str,
        *,
        variant: str | None = None,
        allow_fallback: bool = True,
    ) -> LocalizedAudioCue:
        """Compatibility API for callers expecting a cue or an exception."""
        cue = self._resolve_audio(key, variant=variant, allow_fallback=allow_fallback)
        if cue is None:
            raise LocalizationError(f"missing localized audio cue: {key}")
        return cue

    def _resolve_audio(
        self,
        key: str,
        *,
        variant: str | None = None,
        filename: str | None = None,
        allow_fallback: bool = True,
    ) -> LocalizedAudioCue | None:
        key = _resource_key(key)
        keys = _variant_keys(key, variant)
        if filename is not None:
            name = PurePosixPath(filename)
            if (
                name.name != filename
                or name.suffix.lower() not in _ALLOWED_AUDIO_SUFFIXES
                or filename in {".", ".."}
                or "\\" in filename
            ):
                raise LocalizationError("audio filename must be one WAV/OGG basename")

        selected = self.context.selected
        english = self._english_bundle
        preferred = next(
            (bundle for bundle in self._bundles if bundle.locale == selected), None
        )

        if preferred is not None:
            for lookup in keys:
                cue = preferred.audio.get(lookup)
                if cue is not None and cue.path.is_file():
                    return cue

        # Reuse one existing semantic key -> filename mapping for every
        # translation; EN is preferred, but legacy IT-only mappings can
        # supply the filename for otherwise unmapped cues such as the
        # Submarine alarm. The contents of files are never modified.
        templates = (
            (english,) + tuple(
                bundle for bundle in self._bundles if bundle is not english
            )
            if english is not None else self._bundles
        )
        for bundle in templates:
            for lookup in keys:
                cue = bundle.audio.get(lookup)
                if cue is None:
                    continue
                projected = _project_locale_audio(
                    self.package_root, cue.path, bundle.locale.value,
                    selected.value,
                )
                if projected is not None and projected.is_file():
                    return LocalizedAudioCue(projected, cue.caption_key)

        for candidate in self._conventional_audio(selected.value, key, filename):
            if candidate.is_file():
                return LocalizedAudioCue(candidate)

        if allow_fallback and selected.language != "en":
            if english is not None:
                for lookup in keys:
                    cue = english.audio.get(lookup)
                    if cue is not None and cue.path.is_file():
                        return cue
            # An IT-only legacy cue map can still identify the filename
            # of an existing English audio clip without inventing a mapping.
            for bundle in templates:
                for lookup in keys:
                    cue = bundle.audio.get(lookup)
                    if cue is None:
                        continue
                    english_path = _project_locale_audio(
                        self.package_root, cue.path, bundle.locale.value, "en"
                    )
                    if english_path is not None and english_path.is_file():
                        return LocalizedAudioCue(english_path, cue.caption_key)
            for candidate in self._conventional_audio("en", key, filename):
                if candidate.is_file():
                    return LocalizedAudioCue(candidate)
        return None

    def _conventional_audio(
        self, locale: str, key: str, filename: str | None
    ) -> tuple[Path, ...]:
        if filename is not None:
            names = (filename,)
        elif key == "activity.title":
            return (
                self.package_root / "locales" / locale / "audio" / "activity-title.wav",
            )
        else:
            names = (f"{key}.ogg", f"{key}.wav")
        # Existing Activities store ordinary speech in either of these
        # two conventional locations. Keep the files where authors put them.
        return tuple(
            directory / name
            for directory in (
                self.package_root / "assets" / "audio" / locale,
                self.package_root / "locales" / locale / "audio",
            )
            for name in names
        )


def _project_locale_audio(
    root: Path, source: Path, source_locale: str, target_locale: str
) -> Path | None:
    """Substitute one locale-directory component of a known audio path."""
    try:
        parts = list(source.relative_to(root).parts)
    except ValueError:
        return None
    for index, part in enumerate(parts):
        if part == source_locale and index > 0 and parts[index - 1] in {"audio", "locales"}:
            parts[index] = target_locale
            return root.joinpath(*parts)
    return None


def _variant_keys(key: str, variant: str | None) -> tuple[str, ...]:
    if variant is None:
        return (key,)
    normalized = _variant_id(variant)
    variant_key = f"{key}.{normalized}"
    if len(variant_key) > MAX_KEY_CHARS:
        raise LocalizationError("localized variant key exceeds length limit")
    return (variant_key, key)


def _variant_id(raw: object) -> str:
    if not isinstance(raw, str):
        raise LocalizationError("localized resource variant must be text")
    value = raw.strip()
    if not value or len(value) > MAX_VARIANT_CHARS:
        raise LocalizationError("localized resource variant length is invalid")
    allowed = "abcdefghijklmnopqrstuvwxyz0123456789_-"
    if value != value.lower() or any(character not in allowed for character in value):
        raise LocalizationError(
            "localized resource variant must be a lower-case semantic ID"
        )
    return value


def _direction_for(
    locale: LocaleTag,
    mapping: Mapping[str, TextDirection | str],
) -> TextDirection:
    raw = mapping.get(locale.language, TextDirection.LTR)
    return raw if isinstance(raw, TextDirection) else _parse_direction(raw)


def _parse_direction(raw: object) -> TextDirection:
    try:
        return TextDirection(str(raw))
    except ValueError as exc:
        raise LocalizationError("text direction must be 'ltr' or 'rtl'") from exc


def _resource_key(raw: object) -> str:
    if not isinstance(raw, str):
        raise LocalizationError("localized resource key must be text")
    value = raw.strip()
    if not value or len(value) > MAX_KEY_CHARS:
        raise LocalizationError("localized resource key length is invalid")
    allowed = "abcdefghijklmnopqrstuvwxyz0123456789._-"
    if value != value.lower() or any(character not in allowed for character in value):
        raise LocalizationError("localized resource key must be lower-case semantic ID")
    return value


def _placeholder_name(raw: object) -> str:
    if not isinstance(raw, str):
        raise LocalizationError("localized placeholder name must be text")
    value = raw.strip()
    if not value or len(value) > 64:
        raise LocalizationError("localized placeholder name is invalid")
    if not (value[0].isalpha() or value[0] == "_"):
        raise LocalizationError("localized placeholder must start with a letter/underscore")
    if any(not (ch.isalnum() or ch == "_") for ch in value):
        raise LocalizationError("localized placeholder contains invalid characters")
    return value


def _string_table(raw: object) -> Mapping[str, str]:
    if not isinstance(raw, dict) or len(raw) > MAX_STRING_ENTRIES:
        raise LocalizationError("localized strings must be a bounded object")
    result: dict[str, str] = {}
    for raw_key, raw_value in raw.items():
        key = _resource_key(raw_key)
        if not isinstance(raw_value, str):
            raise LocalizationError(f"localized string {key!r} must be text")
        if len(raw_value) > MAX_STRING_CHARS or "\x00" in raw_value:
            raise LocalizationError(f"localized string {key!r} exceeds bounds")
        result[key] = raw_value
    return result


def _audio_table(package_root: Path, raw: object) -> Mapping[str, LocalizedAudioCue]:
    if not isinstance(raw, dict) or len(raw) > MAX_AUDIO_ENTRIES:
        raise LocalizationError("localized audio must be a bounded object")
    result: dict[str, LocalizedAudioCue] = {}
    for raw_key, raw_value in raw.items():
        key = _resource_key(raw_key)
        if not isinstance(raw_value, dict):
            raise LocalizationError(f"localized audio cue {key!r} must be an object")
        raw_path = raw_value.get("path")
        if not isinstance(raw_path, str):
            raise LocalizationError(f"localized audio cue {key!r} has no path")
        relative = PurePosixPath(raw_path)
        if (
            relative.is_absolute()
            or not relative.parts
            or any(part in {"", ".", ".."} for part in relative.parts)
            or "\\" in raw_path
        ):
            raise LocalizationError(f"localized audio cue {key!r} has unsafe path")
        path = package_root.joinpath(*relative.parts).resolve(strict=False)
        if package_root not in path.parents:
            raise LocalizationError(f"localized audio cue {key!r} escapes package")
        if path.suffix.lower() not in _ALLOWED_AUDIO_SUFFIXES:
            raise LocalizationError(
                f"localized audio cue {key!r} must use portable OGG/WAV audio"
            )
        caption = raw_value.get("caption_key")
        if caption is not None:
            caption = _resource_key(caption)
        result[key] = LocalizedAudioCue(path=path, caption_key=caption)
    return result
