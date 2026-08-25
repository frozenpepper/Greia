"""Profile-scoped child text letter-case presentation policy.

Greia's target children learn CAPITAL letters first, so the platform default
presents child-facing UI words (Activity names, Collection/Category labels,
instructions, buttons, feedback) in capital letters. A parent may disable this
per child in the Parent App; the child's profile then presents normal text.

The policy is a *presentation* concern only. It must never change gameplay
data, storage keys, event payloads, audio cue lookup or localization keys.
Child-authored content (for example what a child types in the Writing
Activity) is not routed through this helper and is preserved exactly as
authored.

Launch plumbing mirrors the other profile presentation hints: the Shell writes
``GREIA_PROFILE_UPPERCASE`` into the Activity environment and Activities read
the resolved value through :mod:`greia_platform.activity_api` or implicitly via
``LocalizedResources.text()``.
"""

from __future__ import annotations

from enum import StrEnum
import os


class ChildTextCase(StrEnum):
    """Bounded letter-case presentation for one child's UI text."""

    UPPERCASE = "uppercase"
    NORMAL = "normal"


#: Young children learn capitals first, so uppercase presentation is the
#: platform default until a parent explicitly chooses normal text.
DEFAULT_CHILD_TEXT_CASE = ChildTextCase.UPPERCASE

ENVIRONMENT_NAME = "GREIA_PROFILE_UPPERCASE"

# The launch environment is constant for the lifetime of one child process, so
# the resolved policy is cached once instead of consulting os.environ per
# rendered string on low-resource hardware.
_resolved_case: ChildTextCase | None = None


def parse_child_text_case(raw: object) -> ChildTextCase:
    """Parse a bounded case value; unknown values fall back to the default."""

    if isinstance(raw, ChildTextCase):
        return raw
    if isinstance(raw, bool):
        return ChildTextCase.UPPERCASE if raw else ChildTextCase.NORMAL
    value = str(raw).strip().casefold()
    if value in {"1", "true", "on", "yes"}:
        return ChildTextCase.UPPERCASE
    if value in {"0", "false", "off", "no"}:
        return ChildTextCase.NORMAL
    try:
        return ChildTextCase(value)
    except ValueError:
        return DEFAULT_CHILD_TEXT_CASE


def child_text_case_from_environment() -> ChildTextCase:
    """Return the process-resolved letter-case policy."""

    global _resolved_case
    if _resolved_case is None:
        _resolved_case = parse_child_text_case(os.environ.get(ENVIRONMENT_NAME))
    return _resolved_case


def set_child_text_case(case: ChildTextCase | str | bool | None) -> None:
    """Explicitly override the process policy (tests/embedders only).

    ``None`` clears the override and restores environment authority. This must
    never be called by ordinary Activity or Shell runtime code; the value comes
    from the child's profile through the launch environment.
    """

    global _resolved_case
    _resolved_case = None if case is None else parse_child_text_case(case)


def display_text(text: str, case: ChildTextCase | str | bool | None = None) -> str:
    """Present one child-facing display string under the letter-case policy.

    ``case=None`` uses the process-resolved policy (launch environment). The
    transform is Unicode-aware (``str.upper``), so accented locales such as
    Italian render correctly.
    """

    resolved = child_text_case_from_environment() if case is None else parse_child_text_case(case)
    if resolved is ChildTextCase.UPPERCASE:
        return text.upper()
    return text


__all__ = [
    "DEFAULT_CHILD_TEXT_CASE",
    "ChildTextCase",
    "ENVIRONMENT_NAME",
    "child_text_case_from_environment",
    "display_text",
    "parse_child_text_case",
    "set_child_text_case",
]
