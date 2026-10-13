"""Semantic, lightweight localized copy for Greia's on-device Parent overlay.

Only named, UI-owned messages are translated here; never run dynamic
user-provided text (child names, SSIDs, passwords, service errors) through
an arbitrary string-substitution dictionary. This source catalogue is
authoring-stage for es/fr; selection is still gated by system_language.py.

All messages are static or have typed, named placeholders. The platform's
existing Font/fit services remain the only renderer; no runtime I/O.
"""
from __future__ import annotations

from string import Formatter

from greia_platform.localization import LocalizationError, LocaleTag


_MESSAGES: dict[str, dict[str, str]] = {
    "parent.title": {
        "en": "Parent Settings", "it": "Impostazioni genitori",
        "es": "Ajustes familiares", "fr": "Paramètres parents",
    },
    "auth.prompt": {
        "en": "Enter Parent Password", "it": "Inserisci la password genitore",
        "es": "Introduce la contraseña de padres",
        "fr": "Saisissez le mot de passe parent",
    },
    "auth.cancel": {
        "en": "Cancel", "it": "Annulla",
        "es": "Cancelar", "fr": "Annuler",
    },
    "auth.unlock": {
        "en": "Unlock", "it": "Sblocca",
        "es": "Sbloccar", "fr": "Déverrouiller",
    },
    "auth.rejected": {
        "en": "Incorrect password", "it": "Password errata",
        "es": "Contraseña incorrecta", "fr": "Mot de passe incorrect",
    },
    "auth.unavailable": {
        "en": "Cannot check the password right now",
        "it": "Impossibile verificare la password adesso",
        "es": "No se puede comprobar la contraseña ahora",
        "fr": "Impossible de vérifier le mot de passe actuellement",
    },
    "tab.language": {
        "en": "Language", "it": "Lingua", "es": "Idioma", "fr": "Langue",
    },
    "tab.audio": {
        "en": "Audio & Mic", "it": "Audio e microfono",
        "es": "Audio y micro", "fr": "Audio et micro",
    },
    "tab.accounts": {
        "en": "Kids", "it": "Bambini", "es": "Niños", "fr": "Enfants",
    },
    "tab.security": {
        "en": "Password", "it": "Password",
        "es": "Contraseña", "fr": "Mot de passe",
    },
    "tab.wifi": {
        "en": "Wi-Fi", "it": "Wi-Fi", "es": "Wi-Fi", "fr": "Wi-Fi",
    },
    "tab.ssh": {
        "en": "SSH", "it": "SSH", "es": "SSH", "fr": "SSH",
    },
    "tab.info": {
        "en": "Remote & Pairing", "it": "Remoto e abbinamento",
        "es": "Control y vinculación", "fr": "Accès et association",
    },
    "tab.pointer": {
        "en": "Pointer", "it": "Puntatore",
        "es": "Puntero", "fr": "Pointeur",
    },
    "language.title": {
        "en": "Greia language", "it": "Lingua di Greia",
        "es": "Idioma de Greia", "fr": "Langue de Greia",
    },
    "language.note": {
        "en": "Device language. Some Activities may use another language.",
        "it": "Lingua del dispositivo. Alcune attività possono usarne un'altra.",
        "es": "Idioma del equipo. Algunas actividades pueden usar otro.",
        "fr": "Langue de l'appareil. Certaines activités peuvent en utiliser une autre.",
    },
    "language.option.en": {
        "en": "English", "it": "Inglese",
        "es": "Inglés", "fr": "Anglais",
    },
    "language.option.it": {
        "en": "Italian", "it": "Italiano",
        "es": "Italiano", "fr": "Italien",
    },
    "language.option.es": {
        "en": "Spanish", "it": "Spagnolo",
        "es": "Español", "fr": "Espagnol",
    },
    "language.option.fr": {
        "en": "French", "it": "Francese",
        "es": "Francés", "fr": "Français",
    },
    "language.changed": {
        "en": "Language changed to {name}.",
        "it": "Lingua impostata: {name}.",
        "es": "Idioma cambiado a {name}.",
        "fr": "Langue définie sur {name}.",
    },
    "language.failed": {
        "en": "Could not change language: {detail}",
        "it": "Impossibile cambiare lingua: {detail}",
        "es": "No se pudo cambiar el idioma: {detail}",
        "fr": "Impossible de changer de langue : {detail}",
    },
}

LOCALES = ("en", "it", "es", "fr")


def _language(locale: str) -> str:
    try:
        language = LocaleTag.parse(locale).language
    except (LocalizationError, ValueError):
        language = "en"
    return language if language in LOCALES else "en"


def panel_message(key: str, locale: str, **variables: str) -> str:
    """Resolve only a known semantic message; do not translate user data.

    Unknown keys and mismatched interpolation fields are authoring bugs,
    not a signal to expose machine keys on the child-facing screen.
    """
    source = _MESSAGES[key]
    message = source[_language(locale)]
    expected = {
        field_name
        for _, field_name, _, _ in Formatter().parse(message)
        if field_name is not None
    }
    if expected != set(variables):
        raise ValueError(f"invalid fields for panel message {key}")
    return message.format(**variables)


def audit_panel_messages() -> list[str]:
    """Pure authoring audit: every language must have equal keys/fields."""
    errors: list[str] = []
    for key, messages in _MESSAGES.items():
        if set(messages) != set(LOCALES):
            errors.append(f"{key}: locale coverage mismatch")
            continue
        expected = {
            field_name for _, field_name, _, _ in Formatter().parse(messages["en"])
            if field_name is not None
        }
        for locale, message in messages.items():
            actual = {
                field_name for _, field_name, _, _ in Formatter().parse(message)
                if field_name is not None
            }
            if not message.strip() or actual != expected:
                errors.append(f"{key}/{locale}: empty message or placeholder mismatch")
    return errors
