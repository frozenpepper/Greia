"""Child-facing language presentation semantics for Greia.

Greia's target children may not read.  Language is therefore represented
visually with familiar platform-owned flags, not language initials as the
primary child cue.  This module returns semantic flag asset IDs; renderers own
actual artwork and may add spoken language-name feedback.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from .localization import LocaleTag, LocalizationError


class UiLanguageSelection(StrEnum):
    """How an Activity chooses its in-Activity UI locale at launch."""

    FOLLOW_PROFILE = "follow_profile"
    PRELAUNCH_CHOOSER = "prelaunch_chooser"


class ContentLanguageSelection(StrEnum):
    """How language-sensitive Activity content is chosen independently of UI."""

    NONE = "none"
    FIXED = "fixed"
    PRELAUNCH_CHOOSER = "prelaunch_chooser"


# Canonical child-facing language flag convention selected by Greia product
# policy.  This intentionally represents *language*, not geopolitical locale.
# English uses the British flag; Spanish uses Spain, etc. Region-specific
# localization variants do not silently change the language emblem.
_CANONICAL_LANGUAGE_FLAGS: dict[str, str] = {
    "ar": "sa",
    "bg": "bg",
    "ca": "es",
    "cs": "cz",
    "da": "dk",
    "de": "de",
    "el": "gr",
    "en": "gb",
    "es": "es",
    "et": "ee",
    "fi": "fi",
    "fr": "fr",
    "he": "il",
    "hi": "in",
    "hr": "hr",
    "hu": "hu",
    "id": "id",
    "is": "is",
    "it": "it",
    "ja": "jp",
    "ko": "kr",
    "lt": "lt",
    "lv": "lv",
    "ms": "my",
    "nl": "nl",
    "no": "no",
    "pl": "pl",
    "pt": "pt",
    "ro": "ro",
    "ru": "ru",
    "sk": "sk",
    "sl": "si",
    "sr": "rs",
    "sv": "se",
    "th": "th",
    "tr": "tr",
    "uk": "ua",
    "vi": "vn",
    "zh": "cn",
}


@dataclass(frozen=True, slots=True)
class LanguageFlag:
    """Renderer-neutral semantic language emblem."""

    locale: LocaleTag
    country_code: str

    @property
    def asset_id(self) -> str:
        return f"flag.{self.country_code}"


def language_flag(locale: str | LocaleTag) -> LanguageFlag:
    parsed = locale if isinstance(locale, LocaleTag) else LocaleTag.parse(locale)
    country = _CANONICAL_LANGUAGE_FLAGS.get(parsed.language)
    if country is None:
        raise LocalizationError(
            f"Greia has no canonical child-facing flag for language {parsed.language!r}"
        )
    return LanguageFlag(parsed, country)


def supports_language_flag(locale: str | LocaleTag) -> bool:
    try:
        parsed = locale if isinstance(locale, LocaleTag) else LocaleTag.parse(locale)
    except LocalizationError:
        return False
    return parsed.language in _CANONICAL_LANGUAGE_FLAGS


@dataclass(frozen=True, slots=True)
class ActivityLanguageBadge:
    """Launcher-owned dynamic marker for the language an Activity will use.

    Language-neutral Activities do not receive a badge.  Localized Activities
    receive the flag corresponding to their resolved/selected launch locale.
    The badge is composited by Greia over/near the package icon; packages do not
    bake it into their own icon asset.
    """

    flag: LanguageFlag
    differs_from_profile: bool
    selectable: bool


def activity_language_badge(
    *,
    profile_locale: str | LocaleTag,
    launch_locale: str | LocaleTag,
    selectable: bool = False,
) -> ActivityLanguageBadge:
    profile = (
        profile_locale if isinstance(profile_locale, LocaleTag) else LocaleTag.parse(profile_locale)
    )
    launch = (
        launch_locale if isinstance(launch_locale, LocaleTag) else LocaleTag.parse(launch_locale)
    )
    return ActivityLanguageBadge(
        flag=language_flag(launch),
        differs_from_profile=launch.language != profile.language,
        selectable=bool(selectable),
    )


__all__ = [
    "ActivityLanguageBadge",
    "ContentLanguageSelection",
    "LanguageFlag",
    "UiLanguageSelection",
    "activity_language_badge",
    "language_flag",
    "supports_language_flag",
]
