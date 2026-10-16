"""Prepared opaque completion presentation for low-resource Pygame Activities.

Victory/completion is a terminal Activity state, not a translucent overlay that
should keep the live game simulating and repainting underneath. This module owns
the reusable Pygame presentation half of that contract:

* the full logical frame is opaque;
* finite text and geometry are prepared only when content changes;
* repeated ``draw`` calls are one opaque blit;
* the primary action hit target is stable and queryable by the Activity.

The Activity lifecycle owner remains responsible for stopping active simulation
and for invalidating/re-preparing the completion screen only when its semantic
content actually changes.

ADR 0037 upgrades the same owner compatibly: passing a ``CompletionScene`` turns
the text card into the shared cast completion scene (cheering cast friend,
star row, replay and optional next buttons with keyboard/controller focus).
Without a scene the legacy card is rendered exactly as before.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import TYPE_CHECKING, Final, Protocol

import pygame

from .input_core import InputEdge, SemanticAction, SemanticInputEvent
from .typography import FontRole, GreiaTypography
from .ui_core import Overlay, UiEventResult

if TYPE_CHECKING:  # pragma: no cover - typing only
    from .activity_controls import ControlKit, KitInput


RgbColor = tuple[int, int, int]


class CompletionTypography(Protocol):
    """Narrow rendering seam used by the prepared completion screen."""

    def render(
        self,
        text: str,
        role: FontRole,
        size: int,
        color: RgbColor,
    ) -> pygame.Surface: ...


@dataclass(frozen=True, slots=True)
class CompletionPalette:
    """Opaque colors for one completion presentation."""

    background: RgbColor = (30, 41, 59)
    panel: RgbColor = (255, 252, 245)
    panel_border: RgbColor = (234, 179, 8)
    title: RgbColor = (180, 83, 9)
    body: RgbColor = (71, 85, 105)
    primary: RgbColor = (34, 197, 94)
    primary_text: RgbColor = (255, 255, 255)
    achievement: RgbColor = (234, 179, 8)
    achievement_inner: RgbColor = (254, 240, 138)


@dataclass(frozen=True, slots=True)
class CompletionContent:
    """Semantic content that determines one prepared terminal frame."""

    title: str
    primary_label: str
    body_lines: tuple[str, ...] = ()
    achievement_count: int = 0
    secondary_label: str | None = None

    def __post_init__(self) -> None:
        if not self.title.strip():
            raise ValueError("completion title must not be empty")
        if not self.primary_label.strip():
            raise ValueError("completion primary label must not be empty")
        if self.achievement_count < 0:
            raise ValueError("completion achievement_count must be >= 0")
        if self.secondary_label is not None and not self.secondary_label.strip():
            raise ValueError("completion secondary label must not be blank")


class CompletionAction(StrEnum):
    """Child choice on the completion frame: replay (primary) or next (secondary)."""

    PRIMARY = "primary"
    SECONDARY = "secondary"


@dataclass(frozen=True, slots=True, eq=False)
class CompletionScene:
    """Opt-in art/behaviour that upgrades the card to the shared cast scene.

    ``kit`` supplies the painter (theme tokens, cached pills, focus ring) and the
    shared art resolver (``ui.completion.card``, ``ui.control.star``, cast
    ``pose_cheer``, ``icon.hud.replay``). ``character`` is one canonical cast id
    or ``None`` for no friend. ``star_total`` shows unearned stars as outlines.
    """

    kit: "ControlKit"
    character: str | None = None
    star_total: int | None = None
    primary_glyph: str | None = "replay"
    secondary_glyph: str | None = None


class PygameCompletionScreen:
    """Prepare and replay one opaque low-cost Activity completion frame.

    ``prepare`` is semantic invalidation: it rebuilds only when content or palette
    changes. ``draw`` never creates fonts, text surfaces, alpha overlays or other
    frame-sized resources. The retained frame is intentionally bounded to one
    logical surface.
    """

    DEFAULT_WIDTH: Final = 1024
    DEFAULT_HEIGHT: Final = 600

    def __init__(
        self,
        typography: CompletionTypography | GreiaTypography,
        *,
        width: int = DEFAULT_WIDTH,
        height: int = DEFAULT_HEIGHT,
        palette: CompletionPalette = CompletionPalette(),
        primary_rect: pygame.Rect | None = None,
        scene: CompletionScene | None = None,
    ) -> None:
        if width <= 0 or height <= 0:
            raise ValueError("completion dimensions must be positive")
        self._typography = typography
        self._width = int(width)
        self._height = int(height)
        self._palette = palette
        self._scene = scene
        self._content: CompletionContent | None = None
        self._frame: pygame.Surface | None = None
        self._explicit_primary = primary_rect is not None
        self._secondary_rect: pygame.Rect | None = None
        self._buttons: dict[CompletionAction, object] = {}
        self._focused = CompletionAction.PRIMARY
        self._hovered: CompletionAction | None = None
        self._pressed: CompletionAction | None = None
        self.focus_visible = False
        if primary_rect is not None:
            self._primary_rect = primary_rect.copy()
        elif scene is not None:
            self._primary_rect = self._scene_layout(False)[0]
        else:
            self._primary_rect = self._compute_primary_rect()
        if not pygame.Rect(0, 0, self._width, self._height).contains(self._primary_rect):
            raise ValueError("completion primary_rect must fit inside logical frame")

    @property
    def is_prepared(self) -> bool:
        return self._frame is not None

    @property
    def primary_rect(self) -> pygame.Rect:
        return self._primary_rect.copy()

    @property
    def secondary_rect(self) -> pygame.Rect | None:
        return self._secondary_rect.copy() if self._secondary_rect is not None else None

    @property
    def has_scene(self) -> bool:
        return self._scene is not None

    @property
    def focused_action(self) -> CompletionAction:
        return self._focused

    @property
    def prepared_surface(self) -> pygame.Surface | None:
        """Expose the retained surface read-only for diagnostics/tests."""

        return self._frame

    def prepare(
        self,
        content: CompletionContent,
        *,
        palette: CompletionPalette | None = None,
    ) -> None:
        """Prepare one terminal frame, rebuilding only for semantic changes."""

        resolved_palette = palette or self._palette
        if (
            self._frame is not None
            and self._content == content
            and self._palette == resolved_palette
        ):
            return

        self._palette = resolved_palette
        self._content = content
        if self._scene is not None:
            frame = self._build_scene_frame(content, resolved_palette, self._scene)
        else:
            frame = self._build_frame(content, resolved_palette)
        if pygame.display.get_init() and pygame.display.get_surface() is not None:
            # Display format once: the opaque frame is blitted every presented
            # frame while the completion screen is up.
            frame = frame.convert()
        self._frame = frame

    def clear(self) -> None:
        """Release terminal content when the Activity restarts."""

        self._content = None
        self._frame = None
        self._buttons = {}
        self._secondary_rect = None
        self._focused = CompletionAction.PRIMARY
        self._hovered = None
        self._pressed = None
        self.focus_visible = False

    def draw(self, target: pygame.Surface) -> None:
        """Blit the prepared opaque frame (plus cached scene buttons) to the surface."""

        frame = self._frame
        if frame is None:
            raise RuntimeError("completion screen must be prepared before draw")
        target.blit(frame, (0, 0))
        if self._buttons:
            for action, button in self._buttons.items():
                button.hovered = action is self._hovered  # type: ignore[attr-defined]
                button.pressed = action is self._pressed  # type: ignore[attr-defined]
                button.draw(target)  # type: ignore[attr-defined]
            if self.focus_visible:
                focused = self._buttons.get(self._focused)
                if focused is not None:
                    self._draw_focus(target, focused)

    def primary_contains(self, point: tuple[int, int]) -> bool:
        return self._primary_rect.collidepoint(point)

    def secondary_contains(self, point: tuple[int, int]) -> bool:
        return self._secondary_rect is not None and self._secondary_rect.collidepoint(point)

    def action_at(self, point: tuple[int, int]) -> CompletionAction | None:
        if self.primary_contains(point):
            return CompletionAction.PRIMARY
        if self.secondary_contains(point):
            return CompletionAction.SECONDARY
        return None

    def handle_input(self, event: "KitInput") -> CompletionAction | None:
        """Route kit pointer / semantic input; return the chosen action, if any.

        Arrows / D-pad / stick move focus between replay and next; Space, Enter
        or the south face button choose the focused action; a pointer chooses
        on release over the same button. Returns ``None`` while still choosing.
        """

        from .activity_controls import KitPointer, PointerPhase

        if isinstance(event, SemanticInputEvent):
            if event.edge is not InputEdge.PRESSED:
                return None
            if event.action in {SemanticAction.NAV_LEFT, SemanticAction.MOVE_LEFT}:
                self._focused = CompletionAction.PRIMARY
                self.focus_visible = True
                return None
            if event.action in {SemanticAction.NAV_RIGHT, SemanticAction.MOVE_RIGHT}:
                if self._secondary_rect is not None:
                    self._focused = CompletionAction.SECONDARY
                self.focus_visible = True
                return None
            if event.action in {SemanticAction.NAV_UP, SemanticAction.NAV_DOWN}:
                self.focus_visible = True
                return None
            if event.action in {SemanticAction.ACTIVATE, SemanticAction.PRIMARY}:
                return self._focused
            return None
        if isinstance(event, KitPointer):
            action = self.action_at(event.position)
            if event.phase is PointerPhase.MOVE:
                self._hovered = action
            elif event.phase is PointerPhase.DOWN:
                self._pressed = action
                if action is not None:
                    self._focused = action
                self.focus_visible = False
            elif event.phase is PointerPhase.UP:
                pressed, self._pressed = self._pressed, None
                if action is not None and (pressed is None or pressed is action):
                    return action
            else:
                self._pressed = None
        return None

    def _draw_focus(self, target: pygame.Surface, button: object) -> None:
        scene = self._scene
        if scene is None:
            return
        from .activity_controls import ControlPainter

        rect = button.rect  # type: ignore[attr-defined]
        lip = button.lip  # type: ignore[attr-defined]
        face = pygame.Rect(rect.x, rect.y, rect.width, rect.height - lip)
        painter = scene.kit.painter
        ring = painter.focus_ring(face.size, face.height // 2)
        pad = ControlPainter.FOCUS_PAD
        target.blit(painter.presentable(ring, target), (face.x - pad, face.y - pad))

    # -- shared cast completion scene (ADR 0037) --------------------------------

    def _card_rect(self) -> pygame.Rect:
        card_w = min(760, self._width - 96)
        card_h = min(440, self._height - 72)
        return pygame.Rect(
            self._width // 2 - card_w // 2,
            self._height // 2 - card_h // 2 + 8,
            card_w,
            card_h,
        )

    def _scene_layout(self, with_secondary: bool) -> tuple[pygame.Rect, pygame.Rect | None]:
        card = self._card_rect()
        column_left = card.left + int(card.width * 0.38)
        column = pygame.Rect(column_left, card.top, card.right - 36 - column_left, card.height)
        height = max(56, min(84, int(card.height * 0.18)))
        bottom = card.bottom - int(card.height * 0.1)
        if with_secondary:
            gap = 18
            width = min(240, (column.width - gap) // 2)
            primary = pygame.Rect(column.centerx - gap // 2 - width, bottom - height, width, height)
            secondary = pygame.Rect(column.centerx + gap // 2, bottom - height, width, height)
            return primary, secondary
        width = min(300, column.width)
        return pygame.Rect(column.centerx - width // 2, bottom - height, width, height), None

    def _build_scene_frame(
        self,
        content: CompletionContent,
        palette: CompletionPalette,
        scene: CompletionScene,
    ) -> pygame.Surface:
        from .activity_controls import BodyShape, ButtonRole, PillButton

        kit = scene.kit
        painter = kit.painter
        theme = painter.theme
        frame = pygame.Surface((self._width, self._height))
        frame.fill(palette.background)
        card = self._card_rect()

        art = kit.art.image("ui.completion.card", card.size)
        if art is not None:
            frame.blit(art, card.topleft)
        else:
            frame.blit(painter.body(BodyShape.PANEL, card.size, theme.surface, lip=8), card.topleft)

        # Title on the ribbon band at the top of the card art.
        ribbon_center = (card.centerx, card.top + int(card.height * 0.125))
        title = painter.label(content.title, 34, theme.text, max_width=int(card.width * 0.56))
        frame.blit(title, title.get_rect(center=ribbon_center))

        if scene.character is not None:
            cast_h = int(card.height * 0.66)
            cast = kit.art.image(f"character.{scene.character}", cast_h, variant="pose_cheer")
            if cast is not None:
                # Cast masters put the contact shadow centre at y 228/256; stand it
                # on the stage disc of the card art (centre y 402/440).
                stage_y = card.top + int(card.height * 402 / 440)
                left = card.left + int(card.width * 0.21) - cast.get_width() // 2
                frame.blit(cast, (left, stage_y - int(cast_h * 228 / 256)))

        column_left = card.left + int(card.width * 0.38)
        column = pygame.Rect(column_left, card.top, card.right - 36 - column_left, card.height)
        body_y = card.top + int(card.height * 0.25)
        for line in _wrap_lines(painter, content.body_lines[:2], 24, palette.body, column.width)[:3]:
            rendered = painter.label(line, 24, palette.body, role=FontRole.TITLE, max_width=column.width)
            frame.blit(rendered, rendered.get_rect(midtop=(column.centerx, body_y)))
            body_y += rendered.get_height() + 2

        earned = min(content.achievement_count, 8)
        total = min(8, max(earned, scene.star_total or earned))
        if total:
            size = max(36, min(72, int(column.width / (total * 1.12))))
            spacing = int(size * 1.08)
            start_x = column.centerx - (spacing * (total - 1)) // 2
            star_y = card.top + int(card.height * 0.53)
            for index in range(total):
                star = kit.star(size, filled=index < earned)
                lift = -int(size * 0.12) if total >= 3 and index == total // 2 and total % 2 else 0
                frame.blit(star, star.get_rect(center=(start_x + index * spacing, star_y + lift)))

        primary_rect, secondary_rect = self._scene_layout(content.secondary_label is not None)
        if self._explicit_primary:
            primary_rect = self._primary_rect
        self._primary_rect = primary_rect
        self._secondary_rect = secondary_rect
        icon_size = int(primary_rect.height * 0.5)
        primary_icon = kit.glyph(scene.primary_glyph, icon_size) if scene.primary_glyph else None
        buttons: dict[CompletionAction, object] = {
            CompletionAction.PRIMARY: PillButton(
                painter,
                "completion.primary",
                primary_rect,
                label=content.primary_label,
                icon=primary_icon,
                role=ButtonRole.PRIMARY,
            )
        }
        if secondary_rect is not None and content.secondary_label is not None:
            secondary_icon = kit.glyph(scene.secondary_glyph, icon_size) if scene.secondary_glyph else None
            buttons[CompletionAction.SECONDARY] = PillButton(
                painter,
                "completion.secondary",
                secondary_rect,
                label=content.secondary_label,
                icon=secondary_icon,
            )
        self._buttons = buttons
        if self._focused not in buttons:
            self._focused = CompletionAction.PRIMARY
        return frame

    def _compute_primary_rect(self) -> pygame.Rect:
        button_width = min(320, max(220, self._width // 3))
        button_height = 64
        return pygame.Rect(
            self._width // 2 - button_width // 2,
            self._height // 2 + 92,
            button_width,
            button_height,
        )

    def _build_frame(
        self,
        content: CompletionContent,
        palette: CompletionPalette,
    ) -> pygame.Surface:
        # No SRCALPHA: a completion screen replaces the active game presentation
        # rather than dimming a still-running frame underneath it.
        frame = pygame.Surface((self._width, self._height))
        frame.fill(palette.background)

        card_width = min(560, self._width - 96)
        card_height = min(360, self._height - 96)
        card = pygame.Rect(
            self._width // 2 - card_width // 2,
            self._height // 2 - card_height // 2,
            card_width,
            card_height,
        )
        pygame.draw.rect(frame, palette.panel, card, border_radius=30)
        pygame.draw.rect(frame, palette.panel_border, card, width=5, border_radius=30)

        title = self._typography.render(
            content.title,
            FontRole.DISPLAY,
            32,
            palette.title,
        )
        frame.blit(title, (card.centerx - title.get_width() // 2, card.top + 38))

        body_y = card.top + 100
        for line in content.body_lines[:3]:
            rendered = self._typography.render(
                line,
                FontRole.DISPLAY,
                20,
                palette.body,
            )
            frame.blit(
                rendered,
                (card.centerx - rendered.get_width() // 2, body_y),
            )
            body_y += rendered.get_height() + 8

        count = min(content.achievement_count, 8)
        if count:
            spacing = 46
            total_width = (count - 1) * spacing
            start_x = card.centerx - total_width // 2
            achievement_y = max(body_y + 18, card.centery + 26)
            for index in range(count):
                x = start_x + index * spacing
                pygame.draw.circle(frame, palette.achievement, (x, achievement_y), 18)
                pygame.draw.circle(
                    frame,
                    palette.achievement_inner,
                    (x, achievement_y),
                    8,
                )

        pygame.draw.rect(
            frame,
            palette.primary,
            self._primary_rect,
            border_radius=20,
        )
        label = self._typography.render(
            content.primary_label,
            FontRole.DISPLAY,
            22,
            palette.primary_text,
        )
        frame.blit(
            label,
            (
                self._primary_rect.centerx - label.get_width() // 2,
                self._primary_rect.centery - label.get_height() // 2,
            ),
        )
        return frame


def _wrap_lines(painter, lines, size: int, color, width: int) -> list[str]:
    """Greedy word wrap so body copy stays readable instead of shrinking."""

    def measure(text: str) -> int:
        return painter.label(text, size, color, role=FontRole.TITLE).get_width()

    wrapped: list[str] = []
    for line in lines:
        words = line.split()
        if measure(line) <= width or len(words) < 2:
            wrapped.append(line)
            continue
        # Two balanced lines read better than one long line and an orphan.
        best: tuple[int, str, str] | None = None
        for split in range(1, len(words)):
            first, second = " ".join(words[:split]), " ".join(words[split:])
            widest = max(measure(first), measure(second))
            if best is None or widest < best[0]:
                best = (widest, first, second)
        assert best is not None
        wrapped.extend(best[1:])
    return wrapped


class CompletionOverlay(Overlay):
    """Modal ``SurfaceNavigator`` Overlay presenting a prepared completion screen.

    Kit input (pointer / semantic) is routed to the screen; a chosen action is
    forwarded to the Activity-owned callbacks. The Overlay never mutates game
    state itself.
    """

    def __init__(
        self,
        screen: PygameCompletionScreen,
        *,
        on_primary,
        on_secondary=None,
    ) -> None:
        self._screen = screen
        self._on_primary = on_primary
        self._on_secondary = on_secondary

    @property
    def surface_id(self) -> str:
        return "completion"

    @property
    def screen(self) -> PygameCompletionScreen:
        return self._screen

    def handle_event(self, event: object) -> UiEventResult:
        action = self._screen.handle_input(event)  # type: ignore[arg-type]
        if action is CompletionAction.PRIMARY:
            self._on_primary()
            return UiEventResult.HANDLED
        if action is CompletionAction.SECONDARY and self._on_secondary is not None:
            self._on_secondary()
            return UiEventResult.HANDLED
        return UiEventResult.HANDLED

    def draw(self, target: object) -> None:
        assert isinstance(target, pygame.Surface)
        self._screen.draw(target)


__all__ = [
    "CompletionAction",
    "CompletionContent",
    "CompletionOverlay",
    "CompletionScene",
    "CompletionPalette",
    "CompletionTypography",
    "PygameCompletionScreen",
]
