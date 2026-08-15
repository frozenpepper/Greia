from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


REFERENCE_WIDTH = 1024
REFERENCE_HEIGHT = 600


class SystemNavigationAction(StrEnum):
    """Greia-owned navigation actions that Activities cannot redefine."""

    HOME = "home"
    BACK = "back"


@dataclass(frozen=True, slots=True)
class UiRect:
    """Renderer-neutral integer rectangle used by trusted platform chrome."""

    x: int
    y: int
    width: int
    height: int

    def __post_init__(self) -> None:
        if self.x < 0 or self.y < 0:
            raise ValueError("UI rectangle origin must be non-negative")
        if self.width < 1 or self.height < 1:
            raise ValueError("UI rectangle dimensions must be positive")

    @property
    def right(self) -> int:
        return self.x + self.width

    @property
    def bottom(self) -> int:
        return self.y + self.height

    def contains(self, x: int, y: int) -> bool:
        return self.x <= x < self.right and self.y <= y < self.bottom


@dataclass(frozen=True, slots=True)
class ActivitySystemChromeLayout:
    """Stable protected geometry for Greia-owned Activity navigation chrome.

    The platform, never the Activity, owns rendering and input inside the
    protected region. The complete two-control region is reserved even when
    Back is not currently shown, so Activity layout does not jump as navigation
    context changes.
    """

    surface_width: int
    surface_height: int
    home_hitbox: UiRect
    back_hitbox: UiRect
    protected_region: UiRect
    visual_size: int
    back_available: bool

    @classmethod
    def for_surface(
        cls,
        width: int,
        height: int,
        *,
        back_available: bool = False,
    ) -> "ActivitySystemChromeLayout":
        width = int(width)
        height = int(height)
        if width < 1 or height < 1:
            raise ValueError("surface dimensions must be positive")

        scale = max(0.5, min(width / REFERENCE_WIDTH, height / REFERENCE_HEIGHT))
        hit_size = max(48, min(64, int(round(60 * scale))))
        visual_size = max(28, min(40, int(round(36 * scale))))
        margin = max(6, min(10, int(round(8 * scale))))
        gap = max(4, min(8, int(round(6 * scale))))

        required_width = margin * 2 + hit_size * 2 + gap
        required_height = margin * 2 + hit_size
        if width < required_width or height < required_height:
            raise ValueError("surface is too small for mandatory Greia system chrome")

        home = UiRect(margin, margin, hit_size, hit_size)
        back = UiRect(home.right + gap, margin, hit_size, hit_size)
        protected = UiRect(
            0,
            0,
            back.right + margin,
            hit_size + margin * 2,
        )
        return cls(
            surface_width=width,
            surface_height=height,
            home_hitbox=home,
            back_hitbox=back,
            protected_region=protected,
            visual_size=visual_size,
            back_available=bool(back_available),
        )

    def action_at(self, x: int, y: int) -> SystemNavigationAction | None:
        """Return the platform action for a point inside trusted chrome."""

        if self.home_hitbox.contains(int(x), int(y)):
            return SystemNavigationAction.HOME
        if self.back_available and self.back_hitbox.contains(int(x), int(y)):
            return SystemNavigationAction.BACK
        return None

    @property
    def visible_actions(self) -> tuple[SystemNavigationAction, ...]:
        actions = [SystemNavigationAction.HOME]
        if self.back_available:
            actions.append(SystemNavigationAction.BACK)
        return tuple(actions)
