from __future__ import annotations

import os
import platform
from pathlib import Path


def voice_home() -> Path:
    """Return machine-local Greia voice-production state outside the repository."""
    configured = os.environ.get("GREIA_VOICE_HOME", "").strip()
    if configured:
        return Path(configured).expanduser()
    system = platform.system()
    if system == "Darwin":
        return Path.home() / "Library" / "Application Support" / "Greia" / "voice-production"
    if system == "Windows":
        return Path(os.environ.get("LOCALAPPDATA", Path.home())) / "Greia" / "voice-production"
    xdg_data = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))
    return xdg_data / "greia" / "voice-production"
