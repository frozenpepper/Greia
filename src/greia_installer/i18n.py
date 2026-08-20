from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from greia_platform.system_language import DEFAULT_SYSTEM_LOCALE, system_language


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
    "Connect now, or set it up later in Greia Parents.": "Connettiti ora oppure configuralo più tardi in Greia Parents.",
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
}


@dataclass(frozen=True, slots=True)
class InstallerTranslator:
    """Translate installer-owned presentation copy without touching state logic."""

    locale: str = DEFAULT_SYSTEM_LOCALE

    def __post_init__(self) -> None:
        try:
            canonical = system_language(self.locale).locale
        except Exception:
            canonical = DEFAULT_SYSTEM_LOCALE
        object.__setattr__(self, "locale", canonical)

    @property
    def language(self) -> str:
        return self.locale.split("-", 1)[0].lower()

    def text(self, value: str) -> str:
        if self.language != "it" or not value:
            return value
        fixed = _ITALIAN.get(value)
        if fixed is not None:
            return fixed

        # Dynamic child/parent-visible strings keep machine data (SSID, counts,
        # typed character, battery percentage) verbatim and translate only the
        # surrounding copy.
        if value.startswith("Press the key that types “") and value.endswith("”"):
            character = value[len("Press the key that types “") : -1]
            return f"Premi il tasto che scrive “{character}”"
        if value.startswith("Connecting to ") and value.endswith("…"):
            return f"Connessione a {value[len('Connecting to ') : -1]}…"
        if value.startswith("Connected to "):
            return f"Connesso a {value[len('Connected to '):]}"
        if value.startswith("Wi-Fi: "):
            return value
        if " of " in value and value.endswith(" pressed"):
            left, right = value[:-len(" pressed")].split(" of ", 1)
            if left.isdigit() and right.isdigit():
                return f"{left} di {right} premuti"
        if value.startswith("After ") and " more key" in value:
            count = value[len("After ") :].split(" ", 1)[0]
            if count.isdigit():
                noun = "tasto" if count == "1" else "tasti"
                return f"Dopo altri {count} {noun} mostrerò un elenco da confermare."
        if value == "Connect the power adapter before installing (battery level could not be read).":
            return "Collega l'alimentatore prima di installare (impossibile leggere il livello della batteria)."
        if value.startswith("Connect the power adapter before installing (battery is ") and value.endswith("%)."):
            percent = value[len("Connect the power adapter before installing (battery is ") : -3]
            if percent.isdigit():
                return f"Collega l'alimentatore prima di installare (batteria al {percent}%)."
        return value


class LocalizedFont:
    """Pygame Font proxy translating only the text passed to render()."""

    __slots__ = ("_font", "_translator")

    def __init__(self, font: Any, translator: InstallerTranslator) -> None:
        self._font = font
        self._translator = translator

    def render(self, text: str, *args: Any, **kwargs: Any) -> Any:
        return self._font.render(self._translator.text(str(text)), *args, **kwargs)

    def __getattr__(self, name: str) -> Any:
        return getattr(self._font, name)


class LocalizedTypography:
    """GreiaTypography proxy preserving metrics/cache behavior with localized copy."""

    __slots__ = ("_typography", "translator")

    def __init__(self, typography: Any, locale: str) -> None:
        self._typography = typography
        self.translator = InstallerTranslator(locale)

    def font(self, role: Any, size: int) -> LocalizedFont:
        return LocalizedFont(self._typography.font(role, size), self.translator)

    def render(self, text: str, *args: Any, **kwargs: Any) -> Any:
        return self._typography.render(self.translator.text(str(text)), *args, **kwargs)

    def measure(self, text: str, *args: Any, **kwargs: Any) -> Any:
        return self._typography.measure(self.translator.text(str(text)), *args, **kwargs)

    def prefix_width(self, text: str, *args: Any, **kwargs: Any) -> Any:
        return self._typography.prefix_width(
            self.translator.text(str(text)), *args, **kwargs
        )

    def clear(self) -> None:
        self._typography.clear()

    def __getattr__(self, name: str) -> Any:
        return getattr(self._typography, name)
