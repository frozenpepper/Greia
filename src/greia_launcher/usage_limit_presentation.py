from __future__ import annotations

from dataclasses import dataclass

from greia_platform.usage_limits import UsageLimitStatus


@dataclass(frozen=True, slots=True)
class HomeUsageLimitPresentation:
    """Passive child-home read model for today's Activity-time budget."""

    visible: bool
    text: str
    exhausted: bool


def home_usage_limit_presentation(
    status: UsageLimitStatus,
) -> HomeUsageLimitPresentation:
    """Format a calm, low-frequency remaining-time message for Greia Home.

    The shell should rebuild this model when entering/returning to Home. It is
    intentionally not a ticking seconds countdown: Home time is not charged and
    Atom-class devices should not spend idle work refreshing a static budget.
    """
    remaining = status.effective_remaining_seconds
    if remaining is None:
        return HomeUsageLimitPresentation(False, "", False)
    if remaining <= 0:
        return HomeUsageLimitPresentation(True, "Finished for today", True)
    if remaining < 60:
        return HomeUsageLimitPresentation(True, "Less than 1 min left today", False)

    minutes = remaining // 60
    hours, minutes = divmod(minutes, 60)
    if hours and minutes:
        text = f"{hours} h {minutes} min left today"
    elif hours:
        text = f"{hours} h left today"
    else:
        text = f"{minutes} min left today"
    return HomeUsageLimitPresentation(True, text, False)


__all__ = ["HomeUsageLimitPresentation", "home_usage_limit_presentation"]
