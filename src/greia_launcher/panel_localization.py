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
        "es": "Desbloquear", "fr": "Déverrouiller",
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

// Named legacy Parent form constants retain their English ownership in
// panel_strings. Localizations are keyed by the same semantic identifier,
// not by substring-matching user data or maintaining a second English base.
from greia_launcher import panel_strings as _source_copy

_FORM_TRANSLATIONS: dict[str, dict[str, str]] = {
    "AUDIO_TITLE": {"it": "Guadagno del microfono", "es": "Ganancia del micrófono", "fr": "Gain du microphone"},
    "AUDIO_INTRO": {"it": "Regola il volume di registrazione per le attività vocali e il teatrino. Scegli un livello predefinito o regolalo a passi.", "es": "Ajusta el volumen de grabación para actividades de voz y teatro de títeres. Elige un nivel o ajústalo por pasos.", "fr": "Règle le volume d'enregistrement des activités vocales et du théâtre de marionnettes. Choisis un niveau ou ajuste-le par étapes."},
    "AUDIO_LEVEL_LABEL": {"it": "Livello", "es": "Nivel", "fr": "Niveau"},
    "AUDIO_DECREASE": {"it": "−25%", "es": "−25%", "fr": "−25%"},
    "AUDIO_INCREASE": {"it": "+25%", "es": "+25%", "fr": "+25%"},
    "AUDIO_INPUT_LABEL": {"it": "Ingresso del microfono", "es": "Entrada del micrófono", "fr": "Entrée du microphone"},
    "AUDIO_INPUT_SILENT": {"it": "Nessun suono rilevato", "es": "No se detecta sonido", "fr": "Aucun son détecté"},
    "AUDIO_INPUT_CLIPPING": {"it": "Audio distorto", "es": "Saturación", "fr": "Saturation"},
    "AUDIO_INPUT_UNAVAILABLE": {"it": "Impossibile leggere il microfono. Controlla che sia collegato.", "es": "No se puede leer el micrófono. Comprueba que esté conectado.", "fr": "Microphone inaccessible. Vérifiez qu'il est connecté."},
    "AUDIO_PRESETS_TITLE": {"it": "Livelli consigliati", "es": "Niveles recomendados", "fr": "Réglages conseillés"},
    "AUDIO_BOOST_SUFFIX": {"it": "amplificazione", "es": "amplificación", "fr": "amplification"},
    "AUDIO_NOISE_TITLE": {"it": "Riduzione del rumore", "es": "Reducción de ruido", "fr": "Réduction du bruit"},
    "AUDIO_NOISE_NOTE": {"it": "Il filtro leggero è sempre attivo; quello avanzato richiede un microfono compatibile.", "es": "El filtro ligero siempre está activo; el avanzado necesita un micrófono compatible.", "fr": "Le filtre léger reste actif ; le mode avancé nécessite un microphone compatible."},
    "AUDIO_NOISE_PROCESSING": {"it": "Riduzione del rumore", "es": "Reducción de ruido", "fr": "Réduction du bruit"},
    "AUDIO_NOISE_ADVANCED": {"it": "Riduzione avanzata", "es": "Reducción avanzada", "fr": "Réduction avancée"},
    "AUDIO_INPUT_WAITING": {"it": "Lettura del microfono…", "es": "Leyendo el micrófono…", "fr": "Lecture du microphone…"},
    "ACCOUNTS_TITLE": {"it": "Profili dei bambini", "es": "Perfiles infantiles", "fr": "Profils des enfants"},
    "ACCOUNTS_INTRO": {"it": "Ogni bambino ha i propri salvataggi, impostazioni e cronologia. Rimuovere un profilo cancella definitivamente i suoi dati.", "es": "Cada niño tiene sus archivos, ajustes e historial. Eliminar un perfil borra sus datos definitivamente.", "fr": "Chaque enfant a ses créations, réglages et historique. Supprimer un profil efface définitivement ses données."},
    "ACCOUNTS_ADD": {"it": "Aggiungi bambino", "es": "Añadir niño", "fr": "Ajouter un enfant"},
    "ACCOUNTS_REMOVE": {"it": "Rimuovi", "es": "Eliminar", "fr": "Supprimer"},
    "ACCOUNTS_RENAME": {"it": "Rinomina", "es": "Cambiar nombre", "fr": "Renommer"},
    "ACCOUNTS_EDIT": {"it": "Modifica profilo", "es": "Editar perfil", "fr": "Modifier le profil"},
    "ACCOUNTS_SAVE": {"it": "Salva modifiche", "es": "Guardar cambios", "fr": "Enregistrer"},
    "ACCOUNTS_EMPTY": {"it": "Nessun profilo bambino presente.", "es": "Todavía no hay perfiles infantiles.", "fr": "Aucun profil enfant pour le moment."},
    "ACCOUNTS_NAME_LABEL": {"it": "Nome", "es": "Nombre", "fr": "Nom"},
    "ACCOUNTS_NAME_PLACEHOLDER": {"it": "Nome del bambino", "es": "Nombre del niño", "fr": "Nom de l'enfant"},
    "ACCOUNTS_AGE_LABEL": {"it": "Età indicativa (facoltativa)", "es": "Edad aproximada (opcional)", "fr": "Âge approximatif (facultatif)"},
    "ACCOUNTS_AGE_PLACEHOLDER": {"it": "Età", "es": "Edad", "fr": "Âge"},
    "ACCOUNTS_AVATAR_LABEL": {"it": "Avatar", "es": "Avatar", "fr": "Avatar"},
    "ACCOUNTS_CREATE": {"it": "Crea profilo", "es": "Crear perfil", "fr": "Créer un profil"},
    "ACCOUNTS_CANCEL": {"it": "Annulla", "es": "Cancelar", "fr": "Annuler"},
    "ACCOUNTS_CONFIRM_REMOVE_TITLE": {"it": "Rimuovere questo profilo?", "es": "¿Eliminar este perfil infantil?", "fr": "Supprimer ce profil enfant ?"},
    "ACCOUNTS_CONFIRM_REMOVE_BODY": {"it": "Tutti i salvataggi di questo bambino verranno cancellati. L'operazione è irreversibile.", "es": "Se borrarán todos los archivos guardados de este niño. Esta acción no se puede deshacer.", "fr": "Toutes les données enregistrées de cet enfant seront effacées. Cette action est irréversible."},
    "ACCOUNTS_CONFIRM_REMOVE_YES": {"it": "Elimina definitivamente", "es": "Eliminar definitivamente", "fr": "Supprimer définitivement"},
    "ACCOUNTS_LIMIT_REACHED": {"it": "Il sistema consente al massimo {count} profili bambino.", "es": "Este sistema permite como máximo {count} perfiles infantiles.", "fr": "Ce système permet au maximum {count} profils enfants."},
    "ACCOUNTS_ACTIVE_HINT": {"it": "Non puoi rimuovere il profilo del bambino attivo.", "es": "No puedes eliminar el perfil infantil activo.", "fr": "Le profil de l'enfant connecté ne peut pas être supprimé."},
    "SECURITY_TITLE": {"it": "Password genitori", "es": "Contraseña de padres", "fr": "Mot de passe parent"},
    "SECURITY_INTRO": {"it": "La password dei genitori sblocca queste impostazioni e gestisce i profili bambino. Conservala dove i bambini non possono trovarla.", "es": "La contraseña de padres desbloquea estos ajustes y gestiona los perfiles infantiles. Guárdala donde los niños no puedan encontrarla.", "fr": "Le mot de passe parent ouvre ces réglages et gère les profils enfants. Gardez-le hors de portée des enfants."},
    "SECURITY_CURRENT_LABEL": {"it": "Password attuale", "es": "Contraseña actual", "fr": "Mot de passe actuel"},
    "SECURITY_NEW_LABEL": {"it": "Nuova password", "es": "Contraseña nueva", "fr": "Nouveau mot de passe"},
    "SECURITY_CONFIRM_LABEL": {"it": "Ripeti la nuova password", "es": "Repite la contraseña nueva", "fr": "Confirmer le nouveau mot de passe"},
    "SECURITY_CHANGE": {"it": "Cambia password", "es": "Cambiar contraseña", "fr": "Changer le mot de passe"},
    "SECURITY_MISMATCH": {"it": "Le nuove password non coincidono.", "es": "Las contraseñas nuevas no coinciden.", "fr": "Les deux nouveaux mots de passe ne correspondent pas."},
    "SECURITY_CURRENT_WRONG": {"it": "La password attuale non è corretta.", "es": "La contraseña actual es incorrecta.", "fr": "Le mot de passe actuel est incorrect."},
    "SECURITY_CHANGED": {"it": "Password genitori modificata.", "es": "Contraseña de padres cambiada.", "fr": "Mot de passe parent modifié."},
    "SECURITY_TOO_SHORT": {"it": "Usa almeno {count} caratteri.", "es": "Usa al menos {count} caracteres.", "fr": "Utilisez au moins {count} caractères."},
    "SECURITY_TOO_LONG": {"it": "Usa al massimo {count} caratteri.", "es": "Usa como máximo {count} caracteres.", "fr": "Utilisez au maximum {count} caractères."},
    "STATUS_SAVED": {"it": "Salvato.", "es": "Guardado.", "fr": "Enregistré."},
    "STATUS_BUSY": {"it": "Operazione in corso…", "es": "En curso…", "fr": "En cours…"},
    "STATUS_OFFLINE": {"it": "Il servizio genitori non risponde. Riprova tra poco.", "es": "El servicio de padres no responde. Vuelve a intentarlo en un momento.", "fr": "Le service parents ne répond pas. Réessayez dans un instant."},
}

_AUDIO_PRESETS: dict[float, dict[str, str]] = {
    1.0: {"it": "Normale", "es": "Normal", "fr": "Normal"},
    1.5: {"it": "Medio", "es": "Medio", "fr": "Moyen"},
    2.0: {"it": "Alto", "es": "Alto", "fr": "Élevé"},
    3.0: {"it": "Forte", "es": "Fuerte", "fr": "Fort"},
    4.0: {"it": "Massimo", "es": "Máximo", "fr": "Maximum"},
}


def panel_constant(name: str, locale: str, **variables: str) -> str:
    """Translate a named panel form/control value from its English source."""
    options = _FORM_TRANSLATIONS[name]
    language = _language(locale)
    message = getattr(_source_copy, name) if language == "en" else options[language]
    fields = {
        field for _, field, _, _ in Formatter().parse(message)
        if field is not None
    }
    if fields != set(variables):
        raise ValueError(f"invalid fields for panel constant {name}")
    return message.format(**variables)


def panel_audio_preset(value: float, locale: str) -> str:
    """Translate a known gain preset without changing numeric gain."""
    language = _language(locale)
    if language == "en":
        return _source_copy.AUDIO_PRESET_NAMES[value]
    return _AUDIO_PRESETS[value][language]


def audit_panel_constants() -> list[str]:
    """Ensure all four languages preserve English messages and placeholders."""
    errors = []
    for name, translations in _FORM_TRANSLATIONS.items():
        source = getattr(_source_copy, name, None)
        if not isinstance(source, str) or set(translations) != {"it", "es", "fr"}:
            errors.append(f"{name}: missing source or language")
            continue
        expected = {
            part for _, part, _, _ in Formatter().parse(source)
            if part is not None
        }
        for locale, message in translations.items():
            found = {
                part for _, part, _, _ in Formatter().parse(message)
                if part is not None
            }
            if not message.strip() or expected != found:
                errors.append(f"{name}/{locale}: empty or bad interpolation")
    if set(_AUDIO_PRESETS) != set(_source_copy.AUDIO_PRESET_NAMES):
        errors.append("audio.presets: missing source value")
    return errors
