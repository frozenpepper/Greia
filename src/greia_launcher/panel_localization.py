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
from greia_platform.system_language import SUPPORTED_SYSTEM_LOCALES, language_ui


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
        "en": "Parents is unavailable. Try again shortly.",
        "it": "Genitori non è disponibile. Riprova tra poco.",
        "es": "La app para padres no está disponible. Inténtalo de nuevo en breve.",
        "fr": "Parents est indisponible. Réessayez dans un instant.",
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
        "en": "Remote access", "it": "Accesso remoto",
        "es": "Acceso remoto", "fr": "Accès à distance",
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

LOCALES = SUPPORTED_SYSTEM_LOCALES


def _language(locale: str) -> str:
    try:
        language = LocaleTag.parse(locale).value
    except (LocalizationError, ValueError):
        language = "en"
    if language in LOCALES:
        return language
    base = language.split("-", 1)[0]
    return base if base in LOCALES else "en"


def panel_message(key: str, locale: str, **variables: str) -> str:
    """Resolve only a known semantic message; do not translate user data.

    Unknown keys and mismatched interpolation fields are authoring bugs,
    not a signal to expose machine keys on the child-facing screen.
    """
    if key not in _MESSAGES and key.startswith("language.option."):
        from greia_platform.system_language import system_language
        return system_language(key[len("language.option."):]).native_name
    source = _MESSAGES[key]
    selected = _language(locale)
    message = language_ui(selected, "parent").get(key, source.get(selected, source["en"]))
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
        if any(locale not in messages and key not in language_ui(locale, "parent") for locale in LOCALES):
            errors.append(f"{key}: locale coverage mismatch")
            continue
        expected = {
            field_name for _, field_name, _, _ in Formatter().parse(messages["en"])
            if field_name is not None
        }
        for locale in LOCALES:
            message = language_ui(locale, "parent").get(key, messages.get(locale, ""))
            actual = {
                field_name for _, field_name, _, _ in Formatter().parse(message)
                if field_name is not None
            }
            if not message.strip() or actual != expected:
                errors.append(f"{key}/{locale}: empty message or placeholder mismatch")
    return errors

# Named legacy Parent form constants retain their English ownership in
# panel_strings. Localizations are keyed by the same semantic identifier,
# not by substring-matching user data or maintaining a second English base.
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
    "AUDIO_NOISE_PROCESSING": {"it": "Filtro standard", "es": "Filtro estándar", "fr": "Filtre standard"},
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
    message = language_ui(language, "parent_constants").get(
        name, options.get(language, getattr(_source_copy, name))
    )
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
    return language_ui(language, "parent_audio_presets").get(
        str(value), _AUDIO_PRESETS[value].get(language, _source_copy.AUDIO_PRESET_NAMES[value])
    )


def audit_panel_constants() -> list[str]:
    """Ensure all four languages preserve English messages and placeholders."""
    errors = []
    for name, translations in _FORM_TRANSLATIONS.items():
        source = getattr(_source_copy, name, None)
        if not isinstance(source, str) or any(
            locale != "en" and locale not in translations
            and name not in language_ui(locale, "parent_constants")
            for locale in LOCALES
        ):
            errors.append(f"{name}: missing source or language")
            continue
        expected = {
            part for _, part, _, _ in Formatter().parse(source)
            if part is not None
        }
        for locale in LOCALES:
            message = (source if locale == "en" else language_ui(locale, "parent_constants").get(
                name, translations.get(locale, "")
            ))
            found = {
                part for _, part, _, _ in Formatter().parse(message)
                if part is not None
            }
            if not message.strip() or expected != found:
                errors.append(f"{name}/{locale}: empty or bad interpolation")
    if set(_AUDIO_PRESETS) != set(_source_copy.AUDIO_PRESET_NAMES):
        errors.append("audio.presets: missing source value")
    return errors


# These platform-owned setting labels are not arbitrary user strings. Values
# such as SSIDs, IPs and admin names are injected *only* as named parameters.
_MESSAGES.update({
    "state.on": {"en": "On", "it": "Attivo", "es": "Activado", "fr": "Activé"},
    "state.off": {"en": "Off", "it": "Disattivo", "es": "Desactivado", "fr": "Désactivé"},
    "state.unavailable": {"en": "Unavailable", "it": "Non disponibile", "es": "No disponible", "fr": "Indisponible"},
    "pointer.title": {"en": "Pointer feel", "it": "Impostazioni puntatore", "es": "Comportamiento del puntero", "fr": "Réglage du pointeur"},
    "pointer.note": {"en": "Comfort is preference — try the test area. Arrows move, Space selects, Esc closes.", "it": "Prova l'area di test per trovare la velocità giusta. Frecce per muoversi, Spazio per scegliere, Esc per chiudere.", "es": "Prueba los controles para encontrar la velocidad adecuada. Flechas para moverte, Espacio para elegir y Esc para cerrar.", "fr": "Testez les réglages pour trouver la bonne vitesse. Flèches pour naviguer, Espace pour choisir et Échap pour fermer."},
    "pointer.touchpad.speed": {"en": "Touchpad speed", "it": "Velocità touchpad", "es": "Velocidad del panel táctil", "fr": "Vitesse du pavé tactile"},
    "pointer.mouse.speed": {"en": "Mouse speed", "it": "Velocità mouse", "es": "Velocidad del ratón", "fr": "Vitesse de la souris"},
    "pointer.touchpad.none": {"en": "(no touchpad detected)", "it": "(touchpad non rilevato)", "es": "(panel táctil no detectado)", "fr": "(pavé tactile non détecté)"},
    "pointer.mouse.none": {"en": "(no mouse detected)", "it": "(mouse non rilevato)", "es": "(ratón no detectado)", "fr": "(souris non détectée)"},
    "pointer.toggle.tap": {"en": "Tap to click", "it": "Tocca per fare clic", "es": "Tocar para hacer clic", "fr": "Toucher pour cliquer"},
    "pointer.toggle.scroll": {"en": "Natural scroll", "it": "Scorrimento naturale", "es": "Desplazamiento natural", "fr": "Défilement naturel"},
    "pointer.toggle.typing": {"en": "Off while typing", "it": "Disattiva mentre scrivi", "es": "Desactivar al escribir", "fr": "Désactiver pendant la frappe"},
    "pointer.reset": {"en": "Reset to defaults", "it": "Ripristina valori iniziali", "es": "Restablecer valores", "fr": "Rétablir les réglages"},
    "pointer.test": {"en": "Test area", "it": "Area di prova", "es": "Zona de prueba", "fr": "Zone de test"},
    "pointer.preset.very slow": {"en": "Very slow", "it": "Molto lenta", "es": "Muy lenta", "fr": "Très lente"},
    "pointer.preset.slow": {"en": "Slow", "it": "Lenta", "es": "Lenta", "fr": "Lente"},
    "pointer.preset.medium": {"en": "Medium", "it": "Media", "es": "Media", "fr": "Moyenne"},
    "pointer.preset.fast": {"en": "Fast", "it": "Veloce", "es": "Rápida", "fr": "Rapide"},
    "pointer.preset.very fast": {"en": "Very fast", "it": "Molto veloce", "es": "Muy rápida", "fr": "Très rapide"},
    "wifi.status": {"en": "Status: {phase}", "it": "Stato: {phase}", "es": "Estado: {phase}", "fr": "État : {phase}"},
    "wifi.connected": {"en": " (Connected: {ssid})", "it": " (Connesso a: {ssid})", "es": " (Conectado a: {ssid})", "fr": " (Connecté à : {ssid})"},
    "wifi.error": {"en": "Error: {detail}", "it": "Errore: {detail}", "es": "Error: {detail}", "fr": "Erreur : {detail}"},
    "wifi.scan": {"en": "Scan", "it": "Cerca", "es": "Buscar", "fr": "Rechercher"},
    "wifi.empty": {"en": "No networks found. Press Scan.", "it": "Nessuna rete trovata. Premi Cerca.", "es": "No se encontraron redes. Pulsa Buscar.", "fr": "Aucun réseau trouvé. Appuyez sur Rechercher."},
    "wifi.enterprise": {"en": " (Enterprise)", "it": " (Aziendale)", "es": " (Empresa)", "fr": " (Entreprise)"},
    "wifi.network": {"en": "Network: {ssid}", "it": "Rete: {ssid}", "es": "Red: {ssid}", "fr": "Réseau : {ssid}"},
    "wifi.security": {"en": "Security: {level}", "it": "Protezione: {level}", "es": "Seguridad: {level}", "fr": "Sécurité : {level}"},
    "wifi.password": {"en": "Password", "it": "Password", "es": "Contraseña", "fr": "Mot de passe"},
    "wifi.password.placeholder": {"en": "Type password…", "it": "Inserisci password…", "es": "Introduce la contraseña…", "fr": "Saisissez le mot de passe…"},
    "wifi.connect": {"en": "Connect", "it": "Connetti", "es": "Conectar", "fr": "Se connecter"},
    "wifi.choose": {"en": "Select a Wi-Fi network from the list", "it": "Seleziona una rete Wi-Fi dall'elenco", "es": "Selecciona una red Wi-Fi de la lista", "fr": "Sélectionnez un réseau Wi-Fi dans la liste"},
    "ssh.title": {"en": "SSH maintenance access", "it": "Accesso manutenzione SSH", "es": "Acceso de mantenimiento SSH", "fr": "Accès maintenance SSH"},
    "ssh.checking": {"en": "Checking SSH status…", "it": "Controllo stato SSH…", "es": "Comprobando el estado de SSH…", "fr": "Vérification de l'état SSH…"},
    "ssh.enabled": {"en": "SSH is on", "it": "SSH attivo", "es": "SSH activado", "fr": "SSH activé"},
    "ssh.disabled": {"en": "SSH is off", "it": "SSH disattivo", "es": "SSH desactivado", "fr": "SSH désactivé"},
    "ssh.turn_on": {"en": "Turn on", "it": "Attiva", "es": "Activar", "fr": "Activer"},
    "ssh.turn_off": {"en": "Turn off", "it": "Disattiva", "es": "Desactivar", "fr": "Désactiver"},
    "ssh.admin": {"en": "Administrative user: {username}", "it": "Utente amministratore: {username}", "es": "Usuario administrador: {username}", "fr": "Utilisateur administrateur : {username}"},
    "ssh.ip": {"en": "Device IP: {ip}", "it": "IP dispositivo: {ip}", "es": "IP del dispositivo: {ip}", "fr": "IP de l'appareil : {ip}"},
    "ssh.port": {"en": "SSH Port: {port}", "it": "Porta SSH: {port}", "es": "Puerto SSH: {port}", "fr": "Port SSH : {port}"},
    "ssh.command": {"en": "Connection command: ssh {username}@{ip}", "it": "Comando di connessione: ssh {username}@{ip}", "es": "Comando de conexión: ssh {username}@{ip}", "fr": "Commande de connexion : ssh {username}@{ip}"},
    "ssh.note": {"en": "Note: SSH allows administrative terminal access. Keep disabled when not in use.", "it": "Attenzione: SSH consente l'accesso amministrativo al terminale. Lascialo disattivato se non serve.", "es": "Atención: SSH permite acceder al terminal con permisos de administración. Desactívalo cuando no lo uses.", "fr": "Attention : SSH permet d'accéder au terminal en administrateur. Désactivez-le quand vous n'en avez pas besoin."},
    "info.title": {"en": "Greia Parents from another device", "it": "Controllo genitori da remoto", "es": "Acceso remoto para padres", "fr": "Contrôle parental à distance"},
    "info.intro": {"en": "Greia Parents is accessible from any browser on this home network.", "it": "Greia Parents è accessibile da un browser sulla rete di casa.", "es": "Greia Parents se puede abrir en cualquier navegador de esta red.", "fr": "Greia Parents est accessible depuis un navigateur sur ce réseau."},
    "info.step_wifi": {"en": "1. Connect your phone or laptop to the same Wi-Fi network.", "it": "1. Collega il telefono o il portatile alla stessa rete Wi-Fi.", "es": "1. Conecta el móvil o portátil a la misma red Wi-Fi.", "fr": "1. Connectez votre téléphone ou ordinateur au même réseau Wi-Fi."},
    "info.step_url": {"en": "2. Open https://{ip}:8766 in your browser.", "it": "2. Apri https://{ip}:8766 nel browser.", "es": "2. Abre https://{ip}:8766 en el navegador.", "fr": "2. Ouvrez https://{ip}:8766 dans votre navigateur."},
    "info.step_mdns": {"en": "3. mDNS service: _greia-parent._tcp (Bonjour / Avahi auto-discovery).", "it": "3. Servizio mDNS: _greia-parent._tcp (rilevamento Bonjour / Avahi).", "es": "3. Servicio mDNS: _greia-parent._tcp (detección Bonjour / Avahi).", "fr": "3. Service mDNS : _greia-parent._tcp (découverte Bonjour / Avahi)."},
    "info.step_login": {"en": "4. Parent login: username 'greia', initial password 'greia'.", "it": "4. Accesso genitori: utente 'greia', password iniziale 'greia'.", "es": "4. Acceso para padres: usuario 'greia', contraseña inicial 'greia'.", "fr": "4. Accès parent : identifiant 'greia', mot de passe initial 'greia'."},
})


# Small pointer-speed controls need unique, recognizable short labels.
# Taking the first word of "very slow" and "very fast" made both "very".
_MESSAGES.update({
    "pointer.preset.short.very slow": {"en": "V.Slow", "it": "Min.", "es": "M.Len.", "fr": "T.Len."},
    "pointer.preset.short.slow": {"en": "Slow", "it": "Lenta", "es": "Lenta", "fr": "Lente"},
    "pointer.preset.short.medium": {"en": "Med.", "it": "Media", "es": "Media", "fr": "Moy."},
    "pointer.preset.short.fast": {"en": "Fast", "it": "Vel.", "es": "Ráp.", "fr": "Rap."},
    "pointer.preset.short.very fast": {"en": "V.Fast", "it": "Max.", "es": "M.Ráp.", "fr": "T.Rap."},
})


# Feedback is localizable too: never show an English success after an
# unsuccessful hardware mutation, and never translate OS error details.
_MESSAGES.update({
    "audio.processing.unavailable": {"en": "Advanced noise reduction is not available on this Greia.", "it": "La riduzione avanzata del rumore non è disponibile su questo Greia.", "es": "La reducción avanzada del ruido no está disponible en este Greia.", "fr": "La réduction avancée du bruit n'est pas disponible sur cet appareil Greia."},
    "audio.processing.failed": {"en": "Could not change noise cancelling: {detail}", "it": "Impossibile cambiare la riduzione del rumore: {detail}", "es": "No se pudo cambiar la reducción del ruido: {detail}", "fr": "Impossible de modifier la réduction du bruit : {detail}"},
    "audio.processing.changed": {"en": "Noise cancelling set to {mode}.", "it": "Riduzione del rumore: {mode}.", "es": "Reducción del ruido: {mode}.", "fr": "Réduction du bruit : {mode}."},
    "audio.mode.off": {"en": "off", "it": "disattivata", "es": "desactivada", "fr": "désactivée"},
    "audio.mode.advanced": {"en": "advanced", "it": "avanzata", "es": "avanzada", "fr": "avancée"},
    "audio.mode.lightweight": {"en": "lightweight", "it": "leggera", "es": "ligera", "fr": "légère"},
    "pointer.disabled.touchpad": {"en": "No touchpad detected — touchpad speed is not active.", "it": "Touchpad non rilevato: velocità non disponibile.", "es": "No se detectó un panel táctil: no puedes ajustar su velocidad.", "fr": "Pavé tactile non détecté : réglage de vitesse indisponible."},
    "pointer.disabled.mouse": {"en": "No mouse detected — mouse speed is not active.", "it": "Mouse non rilevato: velocità non disponibile.", "es": "No se detectó un ratón: no puedes ajustar su velocidad.", "fr": "Souris non détectée : réglage de vitesse indisponible."},
    "pointer.disabled.toggle": {"en": "No touchpad detected — this switch is not active.", "it": "Touchpad non rilevato: comando non disponibile.", "es": "No se detectó un panel táctil: control desactivado.", "fr": "Pavé tactile non détecté : commande indisponible."},
    "pointer.device.touchpad": {"en": "Touchpad", "it": "Touchpad", "es": "Panel táctil", "fr": "Pavé tactile"},
    "pointer.device.mouse": {"en": "Mouse", "it": "Mouse", "es": "Ratón", "fr": "Souris"},
    "pointer.speed.changed": {"en": "{device} feel set to {name}.", "it": "Velocità {device}: {name}.", "es": "Velocidad de {device}: {name}.", "fr": "Vitesse de {device} : {name}."},
    "pointer.change.failed": {"en": "Could not apply: {detail}", "it": "Impossibile applicare: {detail}", "es": "No se pudo aplicar: {detail}", "fr": "Impossible d'appliquer : {detail}"},
    "pointer.toggle.changed": {"en": "{state}: {setting}.", "it": "{state}: {setting}.", "es": "{state}: {setting}.", "fr": "{state} : {setting}."},
    "pointer.reset.failed": {"en": "Could not reset pointer settings: {detail}", "it": "Impossibile ripristinare il puntatore: {detail}", "es": "No se pudo restablecer el puntero: {detail}", "fr": "Impossible de réinitialiser le pointeur : {detail}"},
    "pointer.reset.done": {"en": "Pointer settings reset to defaults.", "it": "Impostazioni puntatore ripristinate.", "es": "Ajustes del puntero restablecidos.", "fr": "Réglages du pointeur réinitialisés."},
    "pointer.test.done": {"en": "Tapped — try moving across the test area.", "it": "Fatto! Prova a muovere il puntatore nell'area di prova.", "es": "¡Bien! Prueba a mover el puntero por la zona de prueba.", "fr": "Bien ! Essayez de déplacer le pointeur dans la zone de test."},
})


# Polish pass (2026-10-17): named states that used to leak machine values
# (Wi-Fi phase/security enum names) or were missing (rate limit, key hints).
_MESSAGES.update({
    "auth.hint": {"en": "Enter unlocks · Esc cancels", "it": "Invio sblocca · Esc annulla", "es": "Intro desbloquea · Esc cancela", "fr": "Entrée déverrouille · Échap annule"},
    "auth.rate_limited": {"en": "Too many attempts. Please wait a moment.", "it": "Troppi tentativi. Attendi un momento.", "es": "Demasiados intentos. Espera un momento.", "fr": "Trop de tentatives. Patientez un instant."},
    "panel.hint": {"en": "Tab: next section · Esc: close", "it": "Tab: sezione successiva · Esc: chiudi", "es": "Tab: siguiente sección · Esc: cerrar", "fr": "Tab : section suivante · Échap : fermer"},
    "wifi.title": {"en": "Wi-Fi", "it": "Wi-Fi", "es": "Wi-Fi", "fr": "Wi-Fi"},
    "wifi.phase.idle": {"en": "Not started", "it": "Non avviato", "es": "Sin iniciar", "fr": "Non démarré"},
    "wifi.phase.unavailable": {"en": "Wi-Fi not available", "it": "Wi-Fi non disponibile", "es": "Wi-Fi no disponible", "fr": "Wi-Fi indisponible"},
    "wifi.phase.scanning": {"en": "Searching…", "it": "Ricerca in corso…", "es": "Buscando…", "fr": "Recherche…"},
    "wifi.phase.ready": {"en": "Ready", "it": "Pronto", "es": "Listo", "fr": "Prêt"},
    "wifi.phase.connecting": {"en": "Connecting…", "it": "Connessione…", "es": "Conectando…", "fr": "Connexion…"},
    "wifi.phase.connected": {"en": "Connected", "it": "Connesso", "es": "Conectado", "fr": "Connecté"},
    "wifi.phase.error": {"en": "Error", "it": "Errore", "es": "Error", "fr": "Erreur"},
    "wifi.security.open": {"en": "Open network", "it": "Rete aperta", "es": "Red abierta", "fr": "Réseau ouvert"},
    "wifi.security.personal": {"en": "Password protected", "it": "Protetta da password", "es": "Protegida con contraseña", "fr": "Protégé par mot de passe"},
    "wifi.security.enterprise": {"en": "Enterprise login", "it": "Accesso aziendale", "es": "Acceso empresarial", "fr": "Connexion entreprise"},
})
