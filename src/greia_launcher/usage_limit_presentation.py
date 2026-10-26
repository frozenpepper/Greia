from __future__ import annotations

from dataclasses import dataclass

from greia_platform.child_text import display_text
from greia_platform.system_language import language_ui
from greia_platform.usage_limits import UsageLimitStatus


@dataclass(frozen=True, slots=True)
class HomeUsageLimitPresentation:
    """Passive child-home read model for today's Activity-time budget."""

    visible: bool
    text: str
    exhausted: bool


_MESSAGES: dict[str, dict[str, str]] = {
    "en": {
        "finished": "Finished for today",
        "under_minute": "Less than 1 min left today",
        "minutes": "{minutes} min left today",
        "hours": "{hours} h left today",
        "hours_minutes": "{hours} h {minutes} min left today",
    },
    "it": {
        "finished": "Finito per oggi",
        "under_minute": "Meno di 1 min per oggi",
        "minutes": "{minutes} min rimasti oggi",
        "hours": "{hours} h rimaste oggi",
        "hours_minutes": "{hours} h {minutes} min rimasti oggi",
    },
    "es": {
        "finished": "Terminado por hoy",
        "under_minute": "Menos de 1 min para hoy",
        "minutes": "{minutes} min para hoy",
        "hours": "{hours} h para hoy",
        "hours_minutes": "{hours} h {minutes} min para hoy",
    },
    "de": {
        "finished": "Für heute fertig",
        "under_minute": "Weniger als 1 min für heute",
        "minutes": "Noch {minutes} min heute",
        "hours": "Noch {hours} h heute",
        "hours_minutes": "Noch {hours} h {minutes} min heute",
    },
    "fr": {
        "finished": "Terminé pour aujourd'hui",
        "under_minute": "Moins de 1 min aujourd'hui",
        "minutes": "Encore {minutes} min aujourd'hui",
        "hours": "Encore {hours} h aujourd'hui",
        "hours_minutes": "Encore {hours} h {minutes} min aujourd'hui",
    },
}


def home_usage_limit_presentation(
    status: UsageLimitStatus,
    *,
    locale: str = "en",
    uppercase: bool = False,
) -> HomeUsageLimitPresentation:
    """Format a calm, localized remaining-time message for Greia Home.

    The shell rebuilds this model when entering/returning to Home. It is
    intentionally not a ticking seconds countdown: Home time is not charged and
    Atom-class devices should not spend idle work refreshing a static budget.
    Child letter-case policy is applied only after localization.
    """
    remaining = status.effective_remaining_seconds
    if remaining is None:
        return HomeUsageLimitPresentation(False, "", False)

    language = str(locale or "en").replace("_", "-").split("-", 1)[0].casefold()
    messages = {**_MESSAGES.get(language, _MESSAGES["en"]), **language_ui(locale or "en", "usage_limit")}

    if remaining <= 0:
        text = messages["finished"]
        return HomeUsageLimitPresentation(
            True, display_text(text, uppercase), True
        )
    if remaining < 60:
        text = messages["under_minute"]
        return HomeUsageLimitPresentation(
            True, display_text(text, uppercase), False
        )

    minutes_total = remaining // 60
    hours, minutes = divmod(minutes_total, 60)
    if hours and minutes:
        text = messages["hours_minutes"].format(hours=hours, minutes=minutes)
    elif hours:
        text = messages["hours"].format(hours=hours)
    else:
        text = messages["minutes"].format(minutes=minutes)
    return HomeUsageLimitPresentation(True, display_text(text, uppercase), False)


__all__ = ["HomeUsageLimitPresentation", "home_usage_limit_presentation"]
