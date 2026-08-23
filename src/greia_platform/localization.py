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
from pathlib import Path, PurePosixPath
from string import Template
from typing import Mapping


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

    def text(
        self,
        key: str,
        variables: Mapping[str, object] | None = None,
        *,
        variant: str | None = None,
    ) -> str:
        key = _resource_key(key)
        lookup_keys = _variant_keys(key, variant)
        value: str | None = None
        for bundle in self._bundles:
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
            return Template(value).substitute(safe)
        except (KeyError, ValueError) as exc:
            raise LocalizationError(
                f"localized string {key!r} has an unresolved/invalid placeholder"
            ) from exc

    def audio_cue(
        self,
        key: str,
        *,
        variant: str | None = None,
    ) -> LocalizedAudioCue:
        key = _resource_key(key)
        lookup_keys = _variant_keys(key, variant)
        for bundle in self._bundles:
            for lookup_key in lookup_keys:
                cue = bundle.audio.get(lookup_key)
                if cue is not None:
                    return cue
        raise LocalizationError(f"missing localized audio cue: {key}")


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
