"""First-boot profile setup: the renderer-free wizard model.

On a brand-new Greia the profile registry holds only the placeholder that
``ProfileStore.ensure_initialized`` created (see
``ProfileStore.first_profile_setup``). Instead of showing a picker with an
anonymous "Explorer" card, the child Shell runs this short wizard once:

    welcome -> name -> picture -> age (optional) -> check -> celebrate -> Home

This module owns the step machine, the name editing/validation rules and the
commit call. It has no Pygame dependency; ``first_profile_screen`` renders it
and ``first_profile_presentation`` hosts it in the Shell. Profile storage is
never touched directly: the host injects the ``ProfileStore`` commit function,
so the platform profile authority stays the single writer (no parallel store).
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol
import unicodedata

from greia_platform.profiles import ChildProfile, ProfileError, ProfilePolicy


class FirstProfileStep(StrEnum):
    """Wizard steps in their fixed order (age is skippable)."""

    WELCOME = "welcome"
    NAME = "name"
    AVATAR = "avatar"
    AGE = "age"
    CHECK = "check"
    CELEBRATE = "celebrate"


#: Voice cue played when each step is entered.
STEP_CUES: dict[FirstProfileStep, str] = {
    FirstProfileStep.WELCOME: "first_boot.welcome",
    FirstProfileStep.NAME: "first_boot.ask_name",
    FirstProfileStep.AVATAR: "first_boot.ask_avatar",
    FirstProfileStep.AGE: "first_boot.ask_age",
    FirstProfileStep.CHECK: "first_boot.check",
    FirstProfileStep.CELEBRATE: "first_boot.celebrate",
}

_ORDER: tuple[FirstProfileStep, ...] = tuple(FirstProfileStep)

#: Ages offered as big number buttons; the profile field accepts 1..18.
DEFAULT_AGE_CHOICES: tuple[int, ...] = (3, 4, 5, 6, 7, 8, 9, 10)

#: Separators allowed inside a name besides letters (e.g. "Anna Maria",
#: "Jean-Luc", "D'Angelo"). Digits/symbols are refused at input time.
_NAME_SEPARATORS = frozenset(" -'")


class FirstProfileVoice(Protocol):
    """Plays one prerecorded cue; must be fail-silent when a clip is missing."""

    def say(self, cue_id: str) -> bool: ...


class SilentVoice:
    """Voice used when the Shell has no audio (tests, muted hosts)."""

    def __init__(self) -> None:
        self.spoken: list[str] = []

    def say(self, cue_id: str) -> bool:
        self.spoken.append(cue_id)
        return False


ProfileCommit = Callable[[str, str, "int | None"], ChildProfile]


def normalize_display_name(raw: str) -> str:
    """Return the name to store: NFC, trimmed, single spaces, friendly case.

    Children usually type in one case (the on-screen keys are capitals); a
    one-case name is stored in title case so Parent surfaces show "Anna"
    rather than "ANNA". Mixed case typed by a grown-up ("McKenzie") is kept.
    Child-facing screens still apply the capital-letter display policy.
    """

    text = " ".join(unicodedata.normalize("NFC", raw).split())
    letters = [character for character in text if character.isalpha()]
    if letters and (
        all(character.isupper() for character in letters)
        or all(character.islower() for character in letters)
    ):
        text = text.title()
    return text


@dataclass(frozen=True, slots=True)
class FirstProfileDraft:
    """Immutable snapshot of what the person has chosen so far."""

    name: str
    avatar_id: str
    approximate_age: int | None


class FirstProfileWizard:
    """Step machine and validated draft for the first child profile.

    Every transition into a step plays that step's cue through the injected
    ``voice``. ``confirm`` calls the injected ``commit`` exactly once per
    attempt; a refused commit keeps the wizard on the check step and plays
    the try-again cue. The wizard never retries or writes on its own.
    """

    def __init__(
        self,
        policy: ProfilePolicy,
        *,
        voice: FirstProfileVoice | None = None,
        avatars: Sequence[str] | None = None,
        age_choices: Sequence[int] = DEFAULT_AGE_CHOICES,
    ) -> None:
        self.policy = policy
        self.voice: FirstProfileVoice = voice if voice is not None else SilentVoice()
        offered = tuple(avatars) if avatars is not None else tuple(policy.avatars)
        # Only avatars the policy accepts can ever be committed.
        self.avatars: tuple[str, ...] = tuple(a for a in offered if a in policy.avatars) or (
            policy.default_avatar,
        )
        self.age_choices: tuple[int, ...] = tuple(
            age for age in age_choices if 1 <= int(age) <= 18
        )
        self.max_name_characters = policy.max_name_characters
        self.step = FirstProfileStep.WELCOME
        self.name = ""
        self.avatar_id = (
            policy.default_avatar if policy.default_avatar in self.avatars else self.avatars[0]
        )
        self.approximate_age: int | None = None
        self.commit_failed = False
        self.completed_profile: ChildProfile | None = None
        self.revision = 0
        self._started = False

    # -- lifecycle ---------------------------------------------------------
    def start(self) -> None:
        """Speak the welcome line once (the host calls this when shown)."""

        if not self._started:
            self._started = True
            self._say(STEP_CUES[self.step])

    @property
    def finished(self) -> bool:
        return self.completed_profile is not None

    @property
    def draft(self) -> FirstProfileDraft:
        return FirstProfileDraft(self.display_name, self.avatar_id, self.approximate_age)

    # -- name --------------------------------------------------------------
    @property
    def display_name(self) -> str:
        return normalize_display_name(self.name)

    def name_valid(self) -> bool:
        try:
            self.policy.validate_name(self.display_name)
        except ProfileError:
            return False
        return any(character.isalpha() for character in self.display_name)

    def type_text(self, text: str) -> bool:
        """Append accepted characters; returns True when the name changed."""

        changed = False
        for character in unicodedata.normalize("NFC", text or ""):
            if len(self.name) >= self.max_name_characters:
                break
            if character.isalpha():
                self.name += character
                changed = True
            elif character in _NAME_SEPARATORS:
                # No leading separator and no doubled spaces/hyphens.
                if self.name and self.name[-1] not in _NAME_SEPARATORS:
                    self.name += character
                    changed = True
        if changed:
            self._touch()
        return changed

    def backspace(self) -> bool:
        if not self.name:
            return False
        self.name = self.name[:-1]
        self._touch()
        return True

    # -- choices -----------------------------------------------------------
    def select_avatar(self, avatar_id: str) -> bool:
        if avatar_id not in self.avatars:
            return False
        self.avatar_id = avatar_id
        self._touch()
        return True

    def select_age(self, age: int) -> bool:
        if age not in self.age_choices:
            return False
        self.approximate_age = age
        self._touch()
        return True

    def skip_age(self) -> None:
        self.approximate_age = None
        self._go(FirstProfileStep.CHECK)

    # -- navigation --------------------------------------------------------
    def next(self) -> bool:
        """Advance from the current step; returns True when the step changed.

        The name step refuses to advance without a valid name and plays the
        name-empty cue instead. The check step does not advance here: saving
        goes through :meth:`confirm`.
        """

        step = self.step
        if step is FirstProfileStep.NAME and not self.name_valid():
            self._say("first_boot.name_empty")
            return False
        if step in (FirstProfileStep.CHECK, FirstProfileStep.CELEBRATE):
            return False
        index = _ORDER.index(step)
        self._go(_ORDER[index + 1])
        return True

    def back(self) -> bool:
        if self.step in (FirstProfileStep.WELCOME, FirstProfileStep.CELEBRATE):
            return False
        self.commit_failed = False
        index = _ORDER.index(self.step)
        self._go(_ORDER[index - 1])
        return True

    def confirm(self, commit: ProfileCommit) -> ChildProfile | None:
        """Create the profile through ``commit``; celebrate on success."""

        if self.step is not FirstProfileStep.CHECK or self.finished:
            return None
        if not self.name_valid():
            self._go(FirstProfileStep.NAME)
            self._say("first_boot.name_empty")
            return None
        try:
            profile = commit(self.display_name, self.avatar_id, self.approximate_age)
        except (ProfileError, OSError, ValueError):
            self.commit_failed = True
            self._touch()
            self._say("first_boot.try_again")
            return None
        self.commit_failed = False
        self.completed_profile = profile
        self._go(FirstProfileStep.CELEBRATE)
        return profile

    def replay(self) -> bool:
        """Replay the current step's line (the on-screen listen button)."""

        return self._say(STEP_CUES[self.step])

    # -- internals ---------------------------------------------------------
    def _go(self, step: FirstProfileStep) -> None:
        if step is self.step:
            return
        self.step = step
        self._touch()
        self._say(STEP_CUES[step])

    def _touch(self) -> None:
        self.revision += 1

    def _say(self, cue_id: str) -> bool:
        try:
            return bool(self.voice.say(cue_id))
        except Exception:  # noqa: BLE001 - speech is optional and fail-silent
            return False
