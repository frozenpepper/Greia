"""Hardware-aware Activity READY timeout policy.

The supervisor kills an Activity that has not presented its first frame
(READY) within a bounded time, so a hung start can never trap the child on the
launch wait screen. A single hard 15 s bound was measured to be wrong for the
C0 reference floor: on the Atom N270 Acer healthy Activities reached READY in
13.5-20.6 s, so launches near the bound passed or were killed by chance.

The bound stays a liveness limit, not a performance target. It is declared per
**compatibility class** in ``runtime/activity-launch.toml`` and selected from
the image's own declared class (``/etc/greia-os/image-profile.json`` ->
``platform.compatibility_class``); Greia never benchmarks the machine. Every
value is clamped to ``[MINIMUM, MAXIMUM]`` and an unreadable policy or profile
falls back to the built-in table, so a damaged file can neither disable the
liveness bound nor make it unbounded. The Shell keeps showing its launch wait
screen for the whole STARTING period.
"""

from __future__ import annotations

import json
import logging
import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Final, Mapping

logger = logging.getLogger(__name__)

DEFAULT_READY_TIMEOUT_SECONDS: Final = 15.0
MINIMUM_READY_TIMEOUT_SECONDS: Final = 5.0
MAXIMUM_READY_TIMEOUT_SECONDS: Final = 60.0
INSTALLED_IMAGE_PROFILE: Final = Path("/etc/greia-os/image-profile.json")
POLICY_FILE_NAME: Final = "activity-launch.toml"

#: Built-in fallback mirrors runtime/activity-launch.toml.
_BUILT_IN_CLASS_TIMEOUTS: Final[Mapping[str, float]] = {"C0": 30.0, "C1": 20.0}


def _bounded(value: float) -> float:
    return max(MINIMUM_READY_TIMEOUT_SECONDS, min(MAXIMUM_READY_TIMEOUT_SECONDS, value))


@dataclass(frozen=True, slots=True)
class ActivityReadyTimeoutPolicy:
    """READY liveness bounds keyed by declared hardware compatibility class."""

    default_seconds: float = DEFAULT_READY_TIMEOUT_SECONDS
    class_seconds: Mapping[str, float] = field(
        default_factory=lambda: dict(_BUILT_IN_CLASS_TIMEOUTS)
    )

    def seconds_for(self, compatibility_class: str | None) -> float:
        if compatibility_class is not None and compatibility_class in self.class_seconds:
            return _bounded(self.class_seconds[compatibility_class])
        return _bounded(self.default_seconds)

    @classmethod
    def load(cls, path: Path) -> "ActivityReadyTimeoutPolicy":
        try:
            with path.open("rb") as handle:
                raw = tomllib.load(handle)
            table = raw["ready_timeout_seconds"]
            if not isinstance(table, dict):
                raise TypeError("ready_timeout_seconds must be a table")
            default = float(table.get("default", DEFAULT_READY_TIMEOUT_SECONDS))
            classes = {
                str(name): float(value)
                for name, value in table.items()
                if name != "default" and not isinstance(value, bool)
            }
        except (OSError, KeyError, TypeError, ValueError, tomllib.TOMLDecodeError) as exc:
            logger.warning(
                "Activity launch timing policy %s is unusable (%s); using built-in bounds",
                path,
                exc,
            )
            return cls()
        return cls(default_seconds=default, class_seconds=classes)


def installed_compatibility_class(image_profile: Path = INSTALLED_IMAGE_PROFILE) -> str | None:
    """Return the image's declared compatibility class, or None off-image."""

    try:
        profile = json.loads(image_profile.read_text(encoding="utf-8"))
        value = profile["platform"]["compatibility_class"]
    except (OSError, ValueError, KeyError, TypeError):
        return None
    return value if isinstance(value, str) and value else None


def resolve_ready_timeout_seconds(
    policy_path: Path,
    image_profile: Path = INSTALLED_IMAGE_PROFILE,
) -> float:
    return ActivityReadyTimeoutPolicy.load(policy_path).seconds_for(
        installed_compatibility_class(image_profile)
    )


def ready_timeout_for(runtime_services: object) -> float:
    """READY bound carried by composed runtime services (default off-image)."""

    value = getattr(runtime_services, "activity_ready_timeout_seconds", None)
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return _bounded(float(value))
    return DEFAULT_READY_TIMEOUT_SECONDS


__all__ = [
    "ActivityReadyTimeoutPolicy",
    "DEFAULT_READY_TIMEOUT_SECONDS",
    "MAXIMUM_READY_TIMEOUT_SECONDS",
    "MINIMUM_READY_TIMEOUT_SECONDS",
    "POLICY_FILE_NAME",
    "installed_compatibility_class",
    "ready_timeout_for",
    "resolve_ready_timeout_seconds",
]
