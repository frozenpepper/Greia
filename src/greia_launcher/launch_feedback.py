"""Child-facing launch feedback, shared by the Shell overlay and Activity badge.

Locale follows the already resolved Shell/profile UI language.  Text-only:
no runtime speech synthesis, locale persistence or second supported-language
registry. Unsupported legacy tags use the existing English safety fallback.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class LaunchFeedback:
    overlay: str
    badge: str
    wait: str


_COPY: dict[str, LaunchFeedback] = {
    "en": LaunchFeedback("Starting…", "Starting...", "Please wait…"),
    "it": LaunchFeedback("Avvio…", "Avvio...", "Attendi…"),
    "es": LaunchFeedback("Iniciando…", "Iniciando...", "Espera…"),
    "fr": LaunchFeedback("Démarrage…", "Démarrage...", "Veuillez patienter…"),
}


def launch_feedback(locale: str | None) -> LaunchFeedback:
    """Resolve typed feedback for an effective UI locale, never process LANG."""
    base = str(locale or "en").strip().replace("_", "-").split("-", 1)[0].lower()
    return _COPY.get(base, _COPY["en"])
