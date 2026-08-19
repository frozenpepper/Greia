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
    "Back": "Indietro",
    "Ready": "Pronto",
    "Checking the installation files": "Controllo dei file di installazione",
    "Checking the selected disk": "Controllo del disco selezionato",
    "Preparing the internal disk": "Preparazione del disco interno",
    "Creating the Greia OS filesystem": "Creazione del filesystem Greia OS",
    "Copying the system": "Copia del sistema",
    "Applying parent choices": "Applicazione delle scelte del genitore",
    "Adding support for this computer": "Aggiunta del supporto per questo computer",
    "Making the disk bootable": "Preparazione dell'avvio dal disco",
    "Checking the installed system": "Controllo del sistema installato",
    "Installation complete": "Installazione completata",
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
        # typed character) verbatim and translate only the surrounding copy.
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
