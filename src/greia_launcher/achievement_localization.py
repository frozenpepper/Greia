from __future__ import annotations

from dataclasses import dataclass

from greia_platform.system_language import (
    DEFAULT_SYSTEM_LOCALE,
    SUPPORTED_SYSTEM_LANGUAGES,
    SystemLanguageError,
    resolve_child_locale,
    system_language,
    language_ui,
)


@dataclass(frozen=True, slots=True)
class AchievementUiStrings:
    """Child-facing Shell copy for the achievement experience."""

    library_title: str
    empty_library: str
    new_label: str
    new_badge: str


# Keep this table aligned with SUPPORTED_SYSTEM_LANGUAGES. Badge definitions own
# their own localized title/description/hint copy; this table owns only Greia
# Shell chrome around those definitions.
_UI_STRINGS: dict[str, AchievementUiStrings] = {
    "en": AchievementUiStrings(
        "MY BADGES",
        "Badges will appear as you explore Greia.",
        "NEW",
        "NEW BADGE!",
    ),
    "it": AchievementUiStrings(
        "I MIEI DISTINTIVI",
        "I distintivi arriveranno esplorando Greia.",
        "NUOVO",
        "NUOVO DISTINTIVO!",
    ),
    "es": AchievementUiStrings(
        "MIS INSIGNIAS",
        "Las insignias aparecerán mientras exploras Greia.",
        "NUEVO",
        "¡NUEVA INSIGNIA!",
    ),
    "de": AchievementUiStrings(
        "MEINE ABZEICHEN",
        "Beim Erkunden von Greia erscheinen Abzeichen.",
        "NEU",
        "NEUES ABZEICHEN!",
    ),
    "fr": AchievementUiStrings(
        "MES BADGES",
        "Les badges apparaîtront en explorant Greia.",
        "NOUVEAU",
        "NOUVEAU BADGE !",
    ),
    "zh-CN": AchievementUiStrings(
        "我的徽章",
        "探索 Greia 时会获得徽章。",
        "新",
        "新徽章！",
    ),
    "pt": AchievementUiStrings(
        "OS MEUS DISTINTIVOS",
        "Os distintivos aparecerão à medida que exploras Greia.",
        "NOVO",
        "NOVO DISTINTIVO!",
    ),
    "ar": AchievementUiStrings(
        "شاراتي",
        "ستظهر الشارات أثناء استكشاف Greia.",
        "جديد",
        "شارة جديدة!",
    ),
    "hi": AchievementUiStrings(
        "मेरे बैज",
        "Greia को खोजते हुए बैज मिलेंगे।",
        "नया",
        "नया बैज!",
    ),
    "id": AchievementUiStrings(
        "LENCANA SAYA",
        "Lencana akan muncul saat kamu menjelajahi Greia.",
        "BARU",
        "LENCANA BARU!",
    ),
    "bn": AchievementUiStrings(
        "আমার ব্যাজ",
        "Greia ঘুরে দেখার সঙ্গে সঙ্গে ব্যাজ পাওয়া যাবে।",
        "নতুন",
        "নতুন ব্যাজ!",
    ),
    "sw": AchievementUiStrings(
        "BEJI ZANGU",
        "Beji zitaonekana unapogundua Greia.",
        "MPYA",
        "BEJI MPYA!",
    ),
}


def resolve_achievement_locale() -> str:
    """Resolve the locale the child Shell was actually launched to present.

    Explicit launch context wins. This is important for the Activity Simulator:
    it intentionally supplies GREIA_PROFILE_LOCALE/GREIA_DEVICE_LOCALE without
    pretending to have an installed-device language record. On installed Greia,
    where those explicit values are normally absent, the persistent system
    language store remains authoritative.
    """

    # A malformed higher-priority value never hides a valid lower-priority one.
    return resolve_child_locale()


def achievement_ui_strings(locale: str | None) -> AchievementUiStrings:
    """Return localized Shell chrome with language/base-language fallback."""

    requested = (locale or "").strip().replace("_", "-")
    try:
        canonical = system_language(requested).locale
    except SystemLanguageError:
        canonical = DEFAULT_SYSTEM_LOCALE

    base = canonical.split("-", 1)[0]
    original = _UI_STRINGS.get(canonical, _UI_STRINGS.get(base, _UI_STRINGS[DEFAULT_SYSTEM_LOCALE]))
    overrides = language_ui(canonical, "achievements")
    return AchievementUiStrings(**{
        key: overrides.get(key, getattr(original, key))
        for key in ("title", "empty", "new_label", "new_badge")
    })


def missing_supported_locales() -> tuple[str, ...]:
    """Return supported Greia locales missing achievement Shell chrome."""

    return tuple(
        item.locale for item in SUPPORTED_SYSTEM_LANGUAGES
        if item.locale not in _UI_STRINGS and not all(
            key in language_ui(item.locale, "achievements")
            for key in ("title", "empty", "new_label", "new_badge")
        )
    )


__all__ = [
    "AchievementUiStrings",
    "achievement_ui_strings",
    "missing_supported_locales",
    "resolve_achievement_locale",
]
