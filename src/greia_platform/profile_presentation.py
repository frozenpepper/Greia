"""Profile-scoped presentation and grammatical-addressing preferences.

This state is intentionally separate from core child identity.  A parent may
choose a small presentation hint (neutral/boy/girl) that Greia can use for an
initial visual palette and for child-directed grammatical agreement.  It must
never become an Activity eligibility, capability, progression or security fact.

The preference lives beside the profile's other customization state.  Ordinary
Activities receive only resolved semantic launch values from the Shell; they do
not receive this file or the customization directory.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
import json
import os
from pathlib import Path
import tempfile

from .customization import ThemeStore


class ProfilePresentationError(ValueError):
    """Raised when profile presentation state violates the bounded contract."""


class ProfilePresentation(StrEnum):
    NEUTRAL = "neutral"
    BOY = "boy"
    GIRL = "girl"


class GrammaticalGender(StrEnum):
    """Small agreement selector exposed to localization, not an identity model."""

    NEUTRAL = "neutral"
    MASCULINE = "masculine"
    FEMININE = "feminine"


@dataclass(frozen=True, slots=True)
class PresentationThemeSeed:
    background: str
    accent: str
    text: str


@dataclass(frozen=True, slots=True)
class ProfilePresentationPreferences:
    schema_version: int = 1
    presentation: ProfilePresentation = ProfilePresentation.NEUTRAL

    @property
    def grammatical_gender(self) -> GrammaticalGender:
        return {
            ProfilePresentation.NEUTRAL: GrammaticalGender.NEUTRAL,
            ProfilePresentation.BOY: GrammaticalGender.MASCULINE,
            ProfilePresentation.GIRL: GrammaticalGender.FEMININE,
        }[self.presentation]

    @property
    def theme_seed(self) -> PresentationThemeSeed:
        # Deliberately subtle starting points, not permanent boy/girl themes.
        # Once a real theme preference exists Greia never overwrites it merely
        # because this presentation preference changes.
        return {
            ProfilePresentation.NEUTRAL: PresentationThemeSeed(
                "cream", "sunshine", "cocoa"
            ),
            ProfilePresentation.BOY: PresentationThemeSeed(
                "sky", "turquoise", "navy"
            ),
            ProfilePresentation.GIRL: PresentationThemeSeed(
                "lavender", "raspberry", "plum"
            ),
        }[self.presentation]

    def as_json_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "presentation": self.presentation.value,
            "grammatical_gender": self.grammatical_gender.value,
        }


class ProfilePresentationStore:
    """Atomic bounded store in one profile's customization namespace."""

    FILE_NAME = "presentation.json"
    MAX_FILE_BYTES = 4096

    def __init__(self, state_dir: Path):
        self.state_dir = state_dir.resolve()
        self.path = self.state_dir / self.FILE_NAME

    def read(self) -> ProfilePresentationPreferences:
        try:
            if self.path.stat().st_size > self.MAX_FILE_BYTES:
                return ProfilePresentationPreferences()
            raw = json.loads(self.path.read_text(encoding="utf-8"))
        except (FileNotFoundError, OSError, UnicodeDecodeError, json.JSONDecodeError):
            return ProfilePresentationPreferences()
        if not isinstance(raw, dict):
            return ProfilePresentationPreferences()
        try:
            if raw.get("schema_version", 1) != 1:
                raise ProfilePresentationError("unsupported profile presentation schema")
            value = raw.get("presentation", ProfilePresentation.NEUTRAL.value)
            if not isinstance(value, str):
                raise ProfilePresentationError("profile presentation must be text")
            return ProfilePresentationPreferences(
                schema_version=1,
                presentation=ProfilePresentation(value),
            )
        except (ProfilePresentationError, ValueError):
            return ProfilePresentationPreferences()

    def set(
        self,
        value: str | ProfilePresentation,
    ) -> ProfilePresentationPreferences:
        try:
            presentation = (
                value if isinstance(value, ProfilePresentation) else ProfilePresentation(str(value))
            )
        except ValueError as exc:
            raise ProfilePresentationError(
                "profile presentation must be neutral, boy, or girl"
            ) from exc
        preferences = ProfilePresentationPreferences(presentation=presentation)
        self._write(preferences)
        return preferences

    def seed_theme_if_unset(
        self,
        theme_store: ThemeStore,
        preferences: ProfilePresentationPreferences | None = None,
    ) -> bool:
        """Apply the starting palette only when the child has no saved theme.

        This is intentionally one-way initialization.  Changing boy/girl/neutral
        later never destroys a theme the child or parent has already chosen.
        """

        if theme_store.preferences_path.exists():
            return False
        selected = preferences or self.read()
        if selected.presentation is ProfilePresentation.NEUTRAL:
            return False
        seed = selected.theme_seed
        theme_store.set_colors(
            background=seed.background,
            accent=seed.accent,
            text=seed.text,
        )
        return True

    def reset(self) -> None:
        self.path.unlink(missing_ok=True)

    def version_token(self) -> int:
        try:
            return self.path.stat().st_mtime_ns
        except OSError:
            return 0

    def _write(self, preferences: ProfilePresentationPreferences) -> None:
        self.state_dir.mkdir(parents=True, exist_ok=True)
        payload = json.dumps(
            {
                "schema_version": preferences.schema_version,
                "presentation": preferences.presentation.value,
            },
            sort_keys=True,
            separators=(",", ":"),
        ) + "\n"
        descriptor, temporary_name = tempfile.mkstemp(
            prefix=f".{self.path.name}.", dir=self.state_dir
        )
        temporary = Path(temporary_name)
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
                handle.write(payload)
                handle.flush()
                os.fsync(handle.fileno())
            try:
                os.chmod(temporary, 0o660)
            except PermissionError:
                pass
            temporary.replace(self.path)
        except BaseException:
            temporary.unlink(missing_ok=True)
            raise


__all__ = [
    "GrammaticalGender",
    "PresentationThemeSeed",
    "ProfilePresentation",
    "ProfilePresentationError",
    "ProfilePresentationPreferences",
    "ProfilePresentationStore",
]
