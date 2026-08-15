from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping


DEFAULT_ENDPOINT_PATH = Path("/etc/greia-os/developer-display.json")
_USER_RE = re.compile(r"^[a-z_][a-z0-9_-]{0,31}$")
_DISPLAY_RE = re.compile(r"^:[0-9]{1,3}(?:\.[0-9]{1,3})?$")


class DeveloperSessionError(RuntimeError):
    """Raised when the development display/session descriptor is invalid."""


@dataclass(frozen=True, slots=True)
class DeveloperDisplayEndpoint:
    user: str
    display: str

    @classmethod
    def load(cls, path: Path = DEFAULT_ENDPOINT_PATH) -> "DeveloperDisplayEndpoint":
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise DeveloperSessionError(
                f"developer display endpoint is missing or invalid: {exc}"
            ) from exc
        if not isinstance(payload, Mapping):
            raise DeveloperSessionError("developer display endpoint root must be an object")
        user = payload.get("user")
        display = payload.get("display")
        if not isinstance(user, str) or not _USER_RE.fullmatch(user):
            raise DeveloperSessionError("developer display user is invalid")
        if not isinstance(display, str) or not _DISPLAY_RE.fullmatch(display):
            raise DeveloperSessionError("developer display selector is invalid")
        return cls(user=user, display=display)

    def runuser_prefix(self) -> list[str]:
        return [
            "runuser",
            "--user",
            self.user,
            "--",
            "/usr/bin/env",
            f"DISPLAY={self.display}",
        ]
