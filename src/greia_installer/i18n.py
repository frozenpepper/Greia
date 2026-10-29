from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from greia_platform.localization import LocalizationError, LocaleTag

from .i18n_es_fr import FRENCH, SPANISH
from greia_platform.system_language import DEFAULT_SYSTEM_LOCALE, SUPPORTED_SYSTEM_LOCALES, language_ui


# Installer copy is deliberately owned separately from installer state/disk logic.
# English is the source/fallback language. A locale is only advertised here when
# this surface actually has reviewed copy for it; selecting another valid Greia
# device locale therefore remains safe and falls back to English rather than
# pretending the installer is translated.
_ITALIAN: dict[str, str] = {
    "Start": "Inizia",
    "Choose the internal disk": "Scegli il disco interno",
    "No safe internal disk was found.": "Non è stato trovato un disco interno sicuro.",
    "Input and screen": "Input e schermo",
    "Pointer setup": "Configurazione del puntatore",
    "Pointer feel": "Sensazione del puntatore",
    "Touchpad feel": "Sensazione del touchpad",
    "Mouse feel": "Sensazione del mouse",
    "Mouse feel (when a mouse is attached)": "Sensazione del mouse (quando è collegato un mouse)",
    "Disable while typing": "Disattiva durante la digitazione",
    "Reset pointer feel": "Ripristina la sensazione del puntatore",
    "Pointer feel reset": "Sensazione del puntatore ripristinata",
    "Try it here": "Provalo qui",
    "Click a circle, or press 1 2 3": "Fai clic su un cerchio, oppure premi 1 2 3",
    "Nice click!": "Bel clic!",
    "Pointer preview unavailable": "Anteprima del puntatore non disponibile",
    "Display": "Schermo",
    "Resolution: Automatic": "Risoluzione: automatica",
    "Greia screens: Automatic": "Schermi Greia: automatico",
    "Screen size detected automatically": "Dimensioni dello schermo rilevate automaticamente",
    "Safe display: installer uses safe pixels (1024x600)": "Schermo sicuro: il programma usa pixel sicuri (1024x600)",
    "This screen is not fully supported — safe pixels are used": "Questo schermo non è pienamente supportato — vengono usati pixel sicuri",
    "This screen is not fully supported — install is paused.": "Questo schermo non è pienamente supportato — installazione in pausa.",
    "Tap touchpad to click": "Tocca il touchpad per fare clic",
    "Natural scrolling": "Scorrimento naturale",
    "Mouse speed": "Velocità del mouse",
    "Touchpad speed": "Velocità del touchpad",
    "Screen resolution": "Risoluzione dello schermo",
    "Ready to install": "Pronto per l'installazione",
    "Unknown disk": "Disco sconosciuto",
    "Wi-Fi: set up later": "Wi-Fi: configura più tardi",
    "Everything currently on this disk will be erased.": "Tutto ciò che si trova su questo disco verrà cancellato.",
    "Tap-to-click starts disabled and can be changed later.": "Il tocco per fare clic parte disattivato e può essere cambiato più tardi.",
    "Hold to erase and install": "Tieni premuto per cancellare e installare",
    "Keep holding…": "Continua a tenere premuto…",
    "Installing": "Installazione in corso",
    "Do not remove the USB key.": "Non rimuovere la chiavetta USB.",
    "All done!": "Fatto!",
    "Greia is installed and ready.": "Greia è installato e pronto.",
    "Your Parent login is:  greia  /  greia": "Accesso genitore:  greia  /  greia",
    "You can change it in Greia Parents after first boot.": "Puoi cambiarlo in Greia Parents dopo il primo avvio.",
    "Close the demo": "Chiudi la demo",
    "I'm ready — turn off": "È pronto — spegni",
    "Installation stopped": "Installazione interrotta",
    " The selected disk may be incomplete if installation had already begun.": " Il disco selezionato potrebbe essere incompleto se l'installazione era già iniziata.",
    "Your keyboard": "La tua tastiera",
    "I'm listening — press that key now.": "Ti ascolto — premi quel tasto adesso.",
    "Or press Enter to see the list now.": "Oppure premi Invio per vedere subito l'elenco.",
    "Use Up/Down or click to choose, then Enter to confirm": "Usa Su/Giù o fai clic per scegliere, poi Invio per confermare",
    "Confirm": "Conferma",
    "US English": "Inglese (USA)",
    "UK English": "Inglese (UK)",
    "Wi-Fi (optional)": "Wi-Fi (facoltativo)",
    "Connect now to make Greia ready for the Parents app. You can also set up Wi-Fi later.": "Connettiti ora per preparare Greia all’app Genitori. Puoi anche configurare il Wi-Fi più tardi.",
    "Looking for Wi-Fi networks…": "Ricerca delle reti Wi-Fi…",
    "Wi-Fi": "Wi-Fi",
    "No wireless adapter is available. You can continue offline.": "Nessun adattatore Wi-Fi disponibile. Puoi continuare offline.",
    "Continue offline": "Continua offline",
    "This network will be ready after the first boot.": "Questa rete sarà pronta dopo il primo avvio.",
    "Continue": "Continua",
    "Refresh": "Aggiorna",
    "Skip for now": "Salta per ora",
    "No networks found. Refresh, or continue offline.": "Nessuna rete trovata. Aggiorna oppure continua offline.",
    "Open": "Aperta",
    "Password": "Password",
    "Enterprise — later": "Enterprise — più tardi",
    "Wi-Fi password": "Password Wi-Fi",
    "Connect": "Connetti",
    "Enterprise Wi-Fi can be configured later in Greia Parents.": "Il Wi-Fi Enterprise può essere configurato più tardi in Greia Parents.",
    "This Wi-Fi network needs enterprise credentials; configure it later in Greia Parents": "Questa rete Wi-Fi richiede credenziali Enterprise; configurala più tardi in Greia Parents",
    "Open Wi-Fi networks do not use a password": "Le reti Wi-Fi aperte non usano una password",
    "Wi-Fi scan could not start": "Impossibile avviare la ricerca delle reti Wi-Fi",
    "Wi-Fi scan results are unavailable": "I risultati della ricerca Wi-Fi non sono disponibili",
    "Wi-Fi connected but its saved profile could not be read": "Wi-Fi connesso, ma non è stato possibile leggere il profilo salvato",
    "Could not connect to the selected Wi-Fi network": "Impossibile connettersi alla rete Wi-Fi selezionata",
    "Wi-Fi device disappeared while connecting": "Il dispositivo Wi-Fi non è più disponibile durante la connessione",
    "Wi-Fi connection was rejected": "La connessione Wi-Fi è stata rifiutata",
    "Wi-Fi connection timed out": "Tempo scaduto durante la connessione Wi-Fi",
    "Wi-Fi scan timed out": "Tempo scaduto durante la ricerca Wi-Fi",
    "iwd is not available": "Il servizio Wi-Fi iwd non è disponibile",
    "iwd D-Bus service is unavailable": "Il servizio D-Bus di iwd non è disponibile",
    "python3-dbus is missing from the system": "Manca python3-dbus nel sistema",
    "Back": "Indietro",
    "Ready": "Pronto",
    "Checking the installation files": "Controllo dei file di installazione",
    "Checking hardware compatibility": "Controllo della compatibilità hardware",
    "Checking the selected disk": "Controllo del disco selezionato",
    "Preparing the internal disk": "Preparazione del disco interno",
    "Creating the Greia OS filesystem": "Creazione del filesystem Greia OS",
    "Copying the system": "Copia del sistema",
    "Applying parent choices": "Applicazione delle scelte del genitore",
    "Adding support for this computer": "Aggiunta del supporto per questo computer",
    "Making the disk bootable": "Preparazione dell'avvio dal disco",
    "Checking the installed system": "Controllo del sistema installato",
    "Installation complete": "Installazione completata",
    "installation must run as root in the live installer": "L'installazione deve essere eseguita come root nell'ambiente live",
    "installation payload integrity record is missing": "Manca il record di integrità dei file di installazione",
    "installation payload integrity record is invalid": "Il record di integrità dei file di installazione non è valido",
    "installation payload could not be read": "Impossibile leggere i file di installazione",
    "installation payload is damaged; the disk was not changed": "I file di installazione sono danneggiati; il disco non è stato modificato",
    "selected disk disappeared": "Il disco selezionato non è più disponibile",
    "selected disk identity changed; installation stopped": "L'identità del disco selezionato è cambiata; installazione interrotta",
    "selected disk is no longer an eligible unmounted internal disk": "Il disco selezionato non è più un disco interno idoneo e non montato",
    "new filesystem has no valid UUID": "Il nuovo filesystem non ha un UUID valido",
    "Strong": "Forte",
    "Good": "Buono",
    "Fair": "Discreto",
    "Weak": "Debole",
    # 2026-10-17 installer redesign copy.
    "Install Greia": "Installa Greia",
    "Greia will be installed on this computer's internal disk.": "Greia verrà installato sul disco interno di questo computer.",
    "First you choose the keyboard, the disk, the pointer, the screen and Wi-Fi.": "Prima scegli tastiera, disco, puntatore, schermo e Wi-Fi.",
    "Nothing is erased until you confirm at the last step.": "Non viene cancellato nulla finché non confermi all'ultimo passo.",
    "Keep the power adapter connected.": "Tieni collegato l'alimentatore.",
    "Suggested": "Consigliata",
    "Greia will be installed on the disk you choose. Only internal disks that are safe to use are shown.": "Greia verrà installato sul disco che scegli. Sono mostrati solo i dischi interni sicuri da usare.",
    "Automatic": "Automatica",
    "More networks": "Altre reti",
    "Wi-Fi could not be checked": "Impossibile controllare il Wi-Fi",
    "This cannot be undone.": "Non si può annullare.",
    "Keyboard": "Tastiera",
    "Disk": "Disco",
    "Pointer": "Puntatore",
    "Screen": "Schermo",
    "Install": "Installa",
    "Set up later": "Più tardi",
    "This can take several minutes.": "Può richiedere diversi minuti.",
    "Time elapsed": "Tempo trascorso",
    "Do not turn off the computer.": "Non spegnere il computer.",
    "Parent login": "Accesso genitore",
    "Some hardware could not be identified automatically. If Wi-Fi or sound do not work, check them in Greia Parents after first boot.": "Alcune parti del computer non sono state riconosciute automaticamente. Se Wi-Fi o audio non funzionano, controllali in Greia Parents dopo il primo avvio.",
    "This computer's Wi-Fi chip needs firmware Greia cannot include. Use an Ethernet cable or a USB Wi-Fi adapter.": "Il chip Wi-Fi di questo computer richiede un firmware che Greia non può includere. Usa un cavo Ethernet o un adattatore Wi-Fi USB.",
    "After the computer turns off, remove the USB key, then turn the computer on again.": "Quando il computer si è spento, togli la chiavetta USB e poi riaccendilo.",
    "The power-off request could not be sent. Press the computer's power button to switch it off.": "La richiesta di spegnimento non è stata inviata. Premi il pulsante di accensione del computer per spegnerlo.",
    "very slow": "molto lenta",
    "slow": "lenta",
    "medium": "media",
    "fast": "veloce",
    "very fast": "molto veloce",
    "tap to click": "tocco per fare clic",
    "disable while typing": "disattiva durante la digitazione",
    "Wi-Fi password must be at least 8 characters.": "La password Wi-Fi deve avere almeno 8 caratteri.",
    "Enterprise Wi-Fi is not supported yet.": "Il Wi-Fi Enterprise non è ancora supportato.",
    "Confirming the selected disk": "Conferma del disco selezionato",
    "Installing Greia OS": "Installazione di Greia OS",
    "The install service is unavailable; installation stopped": "Il servizio di installazione non è disponibile; installazione interrotta",
    "No disk is selected; installation stopped": "Nessun disco selezionato; installazione interrotta",
    "The selected disk changed; choose the internal disk again": "Il disco selezionato è cambiato; scegli di nuovo il disco interno",
    "the selected disk changed; confirmation invalidated": "Il disco selezionato è cambiato; conferma annullata",
    "This screen is not fully supported — installation to the internal disk is paused. Ask a grown-up to try a supported screen.": "Questo schermo non è pienamente supportato — l'installazione sul disco interno è in pausa. Prova con uno schermo supportato.",
    # 2026-10-17 installer follow-ups: streamed progress phases.
    "Setting up the system": "Configurazione del sistema",
    "Still working on this step": "Questo passaggio è ancora in corso",
}


_TRANSLATIONS: dict[str, dict[str, str]] = {
    "it": _ITALIAN,
    "es": SPANISH,
    "fr": FRENCH,
}

# Formatted status text is translated without translating SSIDs, keys,
# percentages, disk identities or any other untrusted machine payload.
_DYNAMIC_MESSAGES: dict[str, dict[str, str]] = {
    "it": {
        "press_key": "Premi il tasto che scrive “{value}”",
        "connecting": "Connessione a {value}…",
        "connected": "Connesso a {value}",
        "pressed": "{left} di {right} premuti",
        "more_keys_one": "Dopo un altro tasto mostrerò un elenco da confermare.",
        "more_keys": "Dopo altri {value} tasti mostrerò un elenco da confermare.",
        "power_unknown": "Collega l'alimentatore prima di installare (impossibile leggere il livello della batteria).",
        "power_percent": "Collega l'alimentatore prima di installare (batteria al {value}%).",
        "nice_click": "Bel clic!{value}",
        "greia_screens": "Schermi Greia: {value}",
        "resolution": "Risoluzione: {value}",
        "pointer_unavailable": "Anteprima del puntatore non disponibile{value}",
        "hold_seconds": "Tieni premuto il pulsante per {value} secondi.",
        "hold_keys_seconds": "Tieni premuto Invio o Spazio per {value} secondi.",
        "not_adjustable": "Non regolabile su questo touchpad: {value}",
    },
    "es": {
        "press_key": "Pulsa la tecla que escribe “{value}”",
        "connecting": "Conectando con {value}…",
        "connected": "Conectado a {value}",
        "pressed": "{left} de {right} pulsadas",
        "more_keys_one": "Después de otra tecla mostraré una lista para confirmar.",
        "more_keys": "Después de {value} teclas más mostraré una lista para confirmar.",
        "power_unknown": "Conecta el adaptador de corriente antes de instalar (no se pudo leer el nivel de batería).",
        "power_percent": "Conecta el adaptador de corriente antes de instalar (batería al {value}%).",
        "nice_click": "¡Buen clic!{value}",
        "greia_screens": "Pantallas Greia: {value}",
        "resolution": "Resolución: {value}",
        "pointer_unavailable": "Vista previa del puntero no disponible{value}",
        "hold_seconds": "Mantén pulsado el botón {value} segundos.",
        "hold_keys_seconds": "Mantén pulsado Intro o Espacio {value} segundos.",
        "not_adjustable": "No se puede ajustar en este panel táctil: {value}",
    },
    "fr": {
        "press_key": "Appuyez sur la touche qui écrit « {value} »",
        "connecting": "Connexion à {value}…",
        "connected": "Connecté à {value}",
        "pressed": "{left} touches sur {right} enfoncées",
        "more_keys_one": "Après une touche supplémentaire, j’afficherai une liste à confirmer.",
        "more_keys": "Après {value} touches supplémentaires, j’afficherai une liste à confirmer.",
        "power_unknown": "Branchez l’alimentation avant l’installation (niveau de batterie illisible).",
        "power_percent": "Branchez l’alimentation avant l’installation (batterie à {value} %).",
        "nice_click": "Bien joué !{value}",
        "greia_screens": "Écrans Greia : {value}",
        "resolution": "Résolution : {value}",
        "pointer_unavailable": "Aperçu du pointeur indisponible{value}",
        "hold_seconds": "Maintenez le bouton enfoncé {value} secondes.",
        "hold_keys_seconds": "Maintenez Entrée ou Espace enfoncée {value} secondes.",
        "not_adjustable": "Non réglable sur ce pavé tactile : {value}",
    },
}


def _dynamic_text(value: str, language: str) -> str:
    """Translate exact known dynamic templates; preserve raw data verbatim."""
    msg = language_ui(language, "installer_dynamic") or _DYNAMIC_MESSAGES.get(language, {})
    if not msg:
        return value
    if value.startswith("Press the key that types “") and value.endswith("”"):
        return msg["press_key"].format(value=value[len("Press the key that types “"):-1])
    if value.startswith("Connecting to ") and value.endswith("…"):
        return msg["connecting"].format(value=value[len("Connecting to "):-1])
    if value.startswith("Connected to "):
        return msg["connected"].format(value=value[len("Connected to "):])
    if value.startswith("Wi-Fi: "):
        # A status prefix may include an SSID; preserve the whole payload.
        return value
    if " of " in value and value.endswith(" pressed"):
        left, right = value[:-len(" pressed")].split(" of ", 1)
        if left.isdigit() and right.isdigit():
            return msg["pressed"].format(left=left, right=right)
    if value.startswith("After ") and " more key" in value:
        count = value[len("After "):].split(" ", 1)[0]
        if count.isdigit():
            return (
                msg["more_keys_one"]
                if count == "1"
                else msg["more_keys"].format(value=count)
            )
    if value == "Connect the power adapter before installing (battery level could not be read).":
        return msg["power_unknown"]
    if value.startswith("Connect the power adapter before installing (battery is ") and value.endswith("%)."):
        percent = value[len("Connect the power adapter before installing (battery is "):-3]
        if percent.isdigit():
            return msg["power_percent"].format(value=percent)
    if value.startswith("Nice click!"):
        return msg["nice_click"].format(value=value[len("Nice click!"):])
    if value.startswith("Greia screens: "):
        return msg["greia_screens"].format(value=value[len("Greia screens: "):])
    if value.startswith("Resolution: ") and value != "Resolution: Automatic":
        return msg["resolution"].format(value=value[len("Resolution: "):])
    if value.startswith("Keep the button pressed for ") and value.endswith(" seconds."):
        count = value[len("Keep the button pressed for "):-len(" seconds.")]
        if count.isdigit():
            return msg["hold_seconds"].format(value=count)
    if value.startswith("Hold Enter or Space for ") and value.endswith(" seconds."):
        count = value[len("Hold Enter or Space for "):-len(" seconds.")]
        if count.isdigit():
            return msg["hold_keys_seconds"].format(value=count)
    if value.startswith("Not adjustable on this touchpad: "):
        # Each listed control is installer copy; translate item by item.
        table = {**_TRANSLATIONS.get(language, {}), **language_ui(language, "installer")}
        items = value[len("Not adjustable on this touchpad: "):].split(" · ")
        return msg["not_adjustable"].format(
            value=" · ".join(table.get(item, item) for item in items)
        )
    if value.startswith("Pointer preview unavailable"):
        return msg["pointer_unavailable"].format(value=value[len("Pointer preview unavailable"):])
    return value


@dataclass(frozen=True, slots=True)
class InstallerTranslator:
    """Translate installer-only copy independently from selectable OS locales.

    Spanish/French are intentionally available to source acceptance and
    preview renderers before promotion into the device language selector.
    """

    locale: str = DEFAULT_SYSTEM_LOCALE

    def __post_init__(self) -> None:
        try:
            language = LocaleTag.parse(self.locale).value
        except (LocalizationError, ValueError):
            language = DEFAULT_SYSTEM_LOCALE
        if language not in SUPPORTED_SYSTEM_LOCALES:
            base = LocaleTag.parse(language).language
            language = base if base in SUPPORTED_SYSTEM_LOCALES else DEFAULT_SYSTEM_LOCALE
        object.__setattr__(self, "locale", language)

    @property
    def language(self) -> str:
        return self.locale

    def text(self, value: str) -> str:
        if not value:
            return value
        table = _TRANSLATIONS.get(self.language, {})
        translated = language_ui(self.language, "installer").get(value, table.get(value))
        if translated is not None:
            return translated
        return _dynamic_text(value, self.language)


class LocalizedFont:
    """Pygame Font proxy translating the text passed to render() and size().

    ``size()`` must translate too: layout code measures copy before drawing
    it, and measuring the English source while rendering the (longer) Italian
    copy is exactly how translated labels overflowed their buttons.
    ``base`` exposes the untranslated font for text that is already final
    (translated-then-wrapped lines, SSIDs, disk models).
    """

    __slots__ = ("_font", "_translator")

    def __init__(self, font: Any, translator: InstallerTranslator) -> None:
        self._font = font
        self._translator = translator

    @property
    def base(self) -> Any:
        return self._font

    def render(self, text: str, *args: Any, **kwargs: Any) -> Any:
        return self._font.render(self._translator.text(str(text)), *args, **kwargs)

    def size(self, text: str) -> Any:
        return self._font.size(self._translator.text(str(text)))

    def __getattr__(self, name: str) -> Any:
        return getattr(self._font, name)


class LocalizedTypography:
    """GreiaTypography proxy preserving metrics/cache behavior with localized copy.

    Font proxies are memoised per (role, size): the shared text-surface cache
    is keyed by font identity, so a fresh proxy per call would miss it on
    every frame and silently restore per-frame rasterization on the Atom.
    """

    __slots__ = ("_typography", "translator", "_fonts")

    _MAX_FONTS = 32

    def __init__(self, typography: Any, locale: str) -> None:
        self._typography = typography
        self.translator = InstallerTranslator(locale)
        self._fonts: dict[tuple[Any, int], LocalizedFont] = {}

    def font(self, role: Any, size: int) -> LocalizedFont:
        key = (role, int(size))
        cached = self._fonts.get(key)
        if cached is None:
            if len(self._fonts) >= self._MAX_FONTS:
                self._fonts.clear()
            cached = LocalizedFont(self._typography.font(role, size), self.translator)
            self._fonts[key] = cached
        return cached

    def render(self, text: str, *args: Any, **kwargs: Any) -> Any:
        return self._typography.render(self.translator.text(str(text)), *args, **kwargs)

    def measure(self, text: str, *args: Any, **kwargs: Any) -> Any:
        return self._typography.measure(self.translator.text(str(text)), *args, **kwargs)

    def prefix_width(self, text: str, *args: Any, **kwargs: Any) -> Any:
        return self._typography.prefix_width(
            self.translator.text(str(text)), *args, **kwargs
        )

    def clear(self) -> None:
        self._fonts.clear()
        self._typography.clear()

    def __getattr__(self, name: str) -> Any:
        return getattr(self._typography, name)
