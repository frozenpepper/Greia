from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Any

# Greia default interface typeface: Nunito Sans (SIL OFL 1.1).
# See GREIA_VISUAL_STYLE_GUIDE.md section 3 and
# build/trust/nunito-sans-2.3.2.provenance.
#
# Fonts are loaded once per (role, size) and cached; consumers never open raw
# font paths. A missing/corrupt font degrades to the pygame default instead of
# crashing the session, which is the child-safe fallback the style guide
# requires (section 17.11).


class FontRole(StrEnum):
    BODY = "body"
    SECONDARY = "secondary"
    CONTROL = "control"
    TITLE = "title"
    DISPLAY = "display"


# Semantic role -> static Nunito Sans weight file.
_WEIGHT_FILES: dict[FontRole, str] = {
    FontRole.BODY: "NunitoSans-Regular.ttf",
    FontRole.SECONDARY: "NunitoSans-Regular.ttf",
    FontRole.CONTROL: "NunitoSans-SemiBold.ttf",
    FontRole.TITLE: "NunitoSans-Bold.ttf",
    FontRole.DISPLAY: "NunitoSans-ExtraBold.ttf",
}


@dataclass(frozen=True, slots=True)
class FontSpec:
    role: FontRole
    size: int

    def __post_init__(self) -> None:
        if self.size < 8 or self.size > 160:
            raise ValueError("font size must be within [8, 160]")


class TypographyError(RuntimeError):
    pass


class GreiaTypography:
    """Bounded font provider keyed by semantic role and size.

    Loads Nunito Sans static weights from the Greia assets directory. If the
    font family is unavailable it falls back to the pygame default font so UI
    never breaks, and records the degradation.
    """

    _MAX_CACHE = 64

    def __init__(self, font_dir: Path | None = None) -> None:
        self._font_dir = Path(font_dir) if font_dir is not None else None
        self._cache: dict[FontSpec, Any] = {}
        self._degraded: bool | None = None
        self._fallback: Any = None
        self._pygame_font = None

    def _ensure_pygame(self) -> Any:
        import pygame

        if self._pygame_font is None:
            pygame.font.init()
            self._pygame_font = pygame.font
        return self._pygame_font

    @property
    def degraded(self) -> bool:
        return bool(self._degraded)

    def font(self, role: FontRole, size: int) -> Any:
        spec = FontSpec(role, size)
        cached = self._cache.get(spec)
        if cached is not None:
            return cached
        if len(self._cache) >= self._MAX_CACHE:
            self._cache.clear()
        font = self._load(spec)
        self._cache[spec] = font
        return font

    def _load(self, spec: FontSpec) -> Any:
        pygame_font = self._ensure_pygame()
        filename = _WEIGHT_FILES.get(spec.role)
        if filename is None:
            raise TypographyError(f"no font file for role {spec.role}")
        path = None
        if self._font_dir is not None:
            candidate = self._font_dir / filename
            if candidate.is_file():
                path = candidate
        if path is None and self._degraded is not True:
            # Lazily probe the canonical Greia install location.
            canonical = Path("/opt/greia-os/assets/fonts/nunito-sans") / filename
            if canonical.is_file():
                path = canonical
        if path is not None:
            try:
                return pygame_font.Font(str(path), spec.size)
            except (OSError, ValueError):
                pass
        self._degraded = True
        return pygame_font.Font(None, spec.size)
