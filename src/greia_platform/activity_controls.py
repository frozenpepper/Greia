"""Shared, theme-driven Activity control kit (ADR 0037).

One small vocabulary replaces the per-Activity buttons, pills, toolbars and HUD
counters that every Activity used to hand-draw:

* ``PillButton`` — rounded action with optional icon + short label;
* ``IconButton`` — round or tile action with one icon (optional caption);
* ``ToolStrip`` — exclusive tool/mode selection made of focusable ``ToolSlot``s;
* ``HudChip`` — non-interactive icon + number counter;
* ``ProgressDots`` — non-interactive round progress (done / current / to do);
* ``PromptBanner`` — icon + short text with an optional replay-voice button.

The kit builds on the existing UI seams instead of introducing a framework:
controls implement ``ui_core.Control``; ``ControlLayer`` is a ``ui_core.Screen``
so it can be routed by ``SurfaceNavigator`` (modal completion Overlays stack on
top of it); keyboard/controller input arrives as ``input_core`` semantic actions
(``PygameControlInput`` uses the standard NAVIGATION mapping, so arrows / D-pad /
left stick move focus and Space / Enter / south face button activate); and
``ControlLayout`` keeps every bar outside the protected Home/Back chrome region
(``ActivitySystemChromeLayout``) at every viewport.

Performance rules (Acer floor): control bodies and labels are rendered once per
(size, state, content) into a hard-bounded LRU cache and replayed as plain blits.
Nothing in ``draw`` constructs fonts, renders text or scales images. Bodies are
supersampled once at build time so pill edges are anti-aliased without per-frame
cost. All state lives in explicitly owned objects; the module keeps no globals.
"""

from __future__ import annotations

from abc import abstractmethod
from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass
from enum import StrEnum
import math
from pathlib import Path
import time
from typing import Protocol, Union, runtime_checkable

import pygame

from .customization import ThemePalette
from .input_core import (
    DEFAULT_INPUT_POLICY,
    ControllerAxis,
    InputEdge,
    InputSource,
    InteractionProfile,
    SemanticAction,
    SemanticInputEvent,
    StandardInputPolicy,
    navigation_direction,
    normalize_stick,
)
from .pygame_input import PygameInputTranslator
from .system_chrome import ActivitySystemChromeLayout
from .typography import FontRole
from .ui_core import BoundedCache, Control, InvalidationTracker, Screen, UiEventResult

Rgb = tuple[int, int, int]

# Artwork constants from GREIA_SVG_AUTHORING_RULES.md §2 (ink contour is the
# cast contour #4B372F, text ink is cocoa #3D2C1F, contact shadow #6A5147).
INK: Rgb = (75, 55, 47)
COCOA: Rgb = (61, 44, 31)
SURFACE: Rgb = (255, 249, 236)
SUNSHINE: Rgb = (255, 194, 52)
WHITE: Rgb = (255, 255, 255)
MUTED: Rgb = (222, 214, 201)


def mix(color: Rgb, other: Rgb, amount: float) -> Rgb:
    """Return the GREIA_SVG_AUTHORING_RULES derived step ``mix(color, other, amount)``."""

    amount = max(0.0, min(1.0, float(amount)))
    return tuple(  # type: ignore[return-value]
        int(round(a * (1.0 - amount) + b * amount)) for a, b in zip(color, other)
    )


def _luminance(color: Rgb) -> float:
    r, g, b = color
    return (0.2126 * r + 0.7152 * g + 0.0722 * b) / 255.0


# --------------------------------------------------------------------------
# Theme
# --------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class ControlTheme:
    """Theme tokens consumed by every kit control.

    Controls are Collection-neutral: neutral controls use the cream ``surface``
    with the cast ``ink`` contour, and only primary/selected/progress elements
    take the ``accent`` token. Choose the accent from ``runtime/theme-defaults``
    tokens (normally the Activity's primary Collection hue) with
    ``ControlTheme.for_accent`` or follow the child's theme with
    ``ControlTheme.from_resolved``.
    """

    accent: Rgb = SUNSHINE
    surface: Rgb = SURFACE
    ink: Rgb = INK
    text: Rgb = COCOA
    focus: Rgb = SUNSHINE
    muted: Rgb = MUTED

    @classmethod
    def for_accent(
        cls,
        token: str,
        *,
        palette: ThemePalette | None = None,
    ) -> "ControlTheme":
        """Return the default kit theme tinted by one named accent token."""

        source = palette if palette is not None else ThemePalette.default_safe()
        try:
            accent = source.accent(token).color
        except Exception as exc:  # CustomizationError is a ValueError subtype
            raise ValueError(f"unknown accent token: {token!r}") from exc
        return cls(accent=tuple(accent))  # type: ignore[arg-type]

    @classmethod
    def from_resolved(cls, theme: object) -> "ControlTheme":
        """Adopt accent/text colours from a ``customization.ResolvedTheme``."""

        accent = getattr(theme, "accent", SUNSHINE)
        text = getattr(theme, "text", COCOA)
        return cls(accent=tuple(accent), text=tuple(text))  # type: ignore[arg-type]

    @property
    def accent_text(self) -> Rgb:
        """Readable label ink on an accent fill (cocoa on light accents)."""

        return self.text if _luminance(self.accent) > 0.58 else WHITE


class BodyShape(StrEnum):
    """Renderer-level body silhouette used by kit controls."""

    PILL = "pill"
    ROUND = "round"
    TILE = "tile"
    PANEL = "panel"


class ButtonRole(StrEnum):
    """Semantic emphasis: neutral cream body or accent-filled primary action."""

    NEUTRAL = "neutral"
    PRIMARY = "primary"


@dataclass(frozen=True, slots=True)
class ControlVisualState:
    """Interaction state of one control.

    ``focused`` is deliberately not part of the cached body: the focus ring is a
    separate cached overlay so focus movement never re-renders bodies.
    """

    hovered: bool = False
    pressed: bool = False
    disabled: bool = False
    selected: bool = False

    @property
    def key(self) -> str:
        if self.disabled:
            return "disabled-selected" if self.selected else "disabled"
        base = "pressed" if self.pressed else "hover" if self.hovered else "normal"
        return f"{base}-selected" if self.selected else base


# --------------------------------------------------------------------------
# Painter (cached, supersampled rendering from theme tokens)
# --------------------------------------------------------------------------


class LabelTypography(Protocol):
    """Narrow typography seam (``GreiaTypography`` satisfies it)."""

    def render(
        self,
        text: str,
        role: FontRole,
        size: int,
        color: Rgb,
    ) -> pygame.Surface: ...


class ControlPainter:
    """Render kit bodies, labels and focus rings once and replay them.

    Bodies follow the Greia SVG recipe in code: one flat fill with a two-stop
    light→base vertical gradient, one ink contour, one upper-left highlight and
    an optional darker "lip" that gives tactile depth (no blur, no filters).
    They are drawn at 2× and smooth-scaled once, so edges are anti-aliased like
    the rsvg-rendered art. Every product is stored in a hard-bounded LRU cache.
    """

    SUPERSAMPLE = 2

    def __init__(
        self,
        typography: LabelTypography,
        theme: ControlTheme = ControlTheme(),
        *,
        max_surfaces: int = 128,
        max_labels: int = 128,
    ) -> None:
        self._typography = typography
        self._theme = theme
        self._surfaces: BoundedCache[tuple, pygame.Surface] = BoundedCache(max_surfaces)
        self._labels: BoundedCache[tuple, pygame.Surface] = BoundedCache(max_labels)
        self.build_count = 0

    @property
    def theme(self) -> ControlTheme:
        return self._theme

    def set_theme(self, theme: ControlTheme) -> None:
        """Swap theme tokens; cached products are released explicitly."""

        if theme != self._theme:
            self._theme = theme
            self._surfaces.clear()

    def clear(self) -> None:
        """Release every cached surface (e.g. after a display/renderer change)."""

        self._surfaces.clear()
        self._labels.clear()

    @property
    def cached_surface_count(self) -> int:
        return len(self._surfaces)

    def cached(self, key: tuple, builder: Callable[[], pygame.Surface]) -> pygame.Surface:
        """Return a cached product, building it at most once while resident."""

        surface = self._surfaces.get(key)
        if surface is None:
            surface = builder()
            self.build_count += 1
            self._surfaces[key] = surface
        return surface

    # -- text --------------------------------------------------------------

    def label(
        self,
        text: str,
        size: int,
        color: Rgb,
        *,
        max_width: int | None = None,
        role: FontRole = FontRole.DISPLAY,
        min_size: int = 11,
    ) -> pygame.Surface:
        """Render one cached single-line label that shrinks (never clips) to fit."""

        size = max(min_size, int(size))
        key = (text, role, size, color, max_width)
        cached = self._labels.get(key)
        if cached is not None:
            return cached
        current = size
        surface = self._typography.render(text, role, current, color)
        while max_width is not None and surface.get_width() > max_width and current > min_size:
            current = max(min_size, int(current * 0.92))
            surface = self._typography.render(text, role, current, color)
        self._labels[key] = surface
        return surface

    # -- colours -----------------------------------------------------------

    def body_fill(self, role: ButtonRole, state: ControlVisualState) -> Rgb:
        theme = self._theme
        base = theme.accent if (role is ButtonRole.PRIMARY or state.selected) else theme.surface
        if state.disabled:
            return mix(base, theme.muted, 0.62)
        if state.pressed:
            return mix(base, theme.ink, 0.10)
        if state.hovered:
            # Neutral cream warms toward the accent; accent fills lighten.
            if base == theme.surface:
                return mix(base, theme.accent, 0.2)
            return mix(base, WHITE, 0.22)
        return base

    def content_color(self, role: ButtonRole, state: ControlVisualState) -> Rgb:
        theme = self._theme
        if state.disabled:
            return mix(theme.text, theme.muted, 0.55)
        if role is ButtonRole.PRIMARY or state.selected:
            return theme.accent_text
        return theme.text

    # -- bodies --------------------------------------------------------------

    def body(
        self,
        shape: BodyShape,
        size: tuple[int, int],
        fill: Rgb,
        *,
        lip: int = 0,
        pressed: bool = False,
        contour: Rgb | None = None,
        contour_width: int | None = None,
        highlight: bool = True,
    ) -> pygame.Surface:
        """Return one cached body surface (``size`` includes the lip band)."""

        width, height = max(2, int(size[0])), max(2, int(size[1]))
        ink = contour if contour is not None else self._theme.ink
        key = ("body", shape, width, height, fill, lip, pressed, ink, contour_width, highlight)
        return self.cached(
            key,
            lambda: self._paint_body(
                shape, width, height, fill, ink, lip, pressed, contour_width, highlight
            ),
        )

    @staticmethod
    def radius_for(shape: BodyShape, width: int, height: int) -> int:
        if shape in {BodyShape.PILL, BodyShape.ROUND}:
            return min(width, height) // 2
        if shape is BodyShape.TILE:
            return max(6, int(min(width, height) * 0.26))
        return max(8, min(28, int(min(width, height) * 0.3)))

    def _paint_body(
        self,
        shape: BodyShape,
        width: int,
        height: int,
        fill: Rgb,
        ink: Rgb,
        lip: int,
        pressed: bool,
        contour_width: int | None,
        highlight: bool,
    ) -> pygame.Surface:
        s = self.SUPERSAMPLE
        big_w, big_h = width * s, height * s
        canvas = pygame.Surface((big_w, big_h), pygame.SRCALPHA)
        lip_px = max(0, int(lip)) * s
        body_h = big_h - lip_px
        stroke = (contour_width if contour_width is not None else max(2, round(min(width, height - lip) * 0.05))) * s
        radius = self.radius_for(shape, width, height - lip) * s
        top = lip_px if pressed else 0
        shade = mix(fill, ink, 0.34)
        if lip_px and not pressed:
            base = pygame.Rect(0, lip_px, big_w, body_h)
            pygame.draw.rect(canvas, ink, base, border_radius=radius)
            pygame.draw.rect(
                canvas,
                shade,
                base.inflate(-2 * stroke, -2 * stroke),
                border_radius=max(1, radius - stroke),
            )
        outer = pygame.Rect(0, top, big_w, body_h)
        pygame.draw.rect(canvas, ink, outer, border_radius=radius)
        inner = outer.inflate(-2 * stroke, -2 * stroke)
        if inner.width > 0 and inner.height > 0:
            inner_radius = max(1, radius - stroke)
            mask = pygame.Surface(inner.size, pygame.SRCALPHA)
            pygame.draw.rect(mask, (255, 255, 255, 255), mask.get_rect(), border_radius=inner_radius)
            gradient = pygame.Surface(inner.size)
            light = mix(fill, WHITE, 0.32)
            span = max(1, inner.height - 1)
            for row in range(inner.height):
                pygame.draw.line(gradient, mix(light, fill, min(1.0, row / (span * 0.8))), (0, row), (inner.width, row))
            mask.blit(gradient, (0, 0), special_flags=pygame.BLEND_RGB_MULT)
            canvas.blit(mask, inner.topleft)
            if highlight and inner.height >= 6 * s:
                gloss = pygame.Surface(inner.size, pygame.SRCALPHA)
                gloss_h = max(2 * s, int(inner.height * 0.17))
                gloss_x = max(stroke, int(min(inner_radius * 0.55, inner.width * 0.18)))
                gloss_w = max(gloss_h, int(inner.width * (0.30 if shape is not BodyShape.ROUND else 0.34)))
                gloss_y = max(stroke // 2, int(inner.height * 0.12))
                pygame.draw.rect(
                    gloss,
                    (255, 255, 255, 105),
                    pygame.Rect(gloss_x, gloss_y, gloss_w, gloss_h),
                    border_radius=gloss_h // 2,
                )
                canvas.blit(gloss, inner.topleft)
        return pygame.transform.smoothscale(canvas, (width, height))

    def focus_ring(self, size: tuple[int, int], radius: int) -> pygame.Surface:
        """Return the cached high-contrast focus ring for a control of ``size``.

        The ring is ink | focus colour | ink so it reads on both light (bakery)
        and dark (night) scenes. It is drawn outside the control by ``pad``.
        """

        width, height = int(size[0]), int(size[1])
        key = ("focus", width, height, int(radius), self._theme.focus, self._theme.ink)
        return self.cached(key, lambda: self._paint_focus_ring(width, height, int(radius)))

    FOCUS_PAD = 7

    def _paint_focus_ring(self, width: int, height: int, radius: int) -> pygame.Surface:
        s = self.SUPERSAMPLE
        pad = self.FOCUS_PAD
        out_w, out_h = (width + 2 * pad) * s, (height + 2 * pad) * s
        ring = pygame.Surface((out_w, out_h), pygame.SRCALPHA)
        outer_radius = (radius + pad) * s
        band = [(self._theme.ink, 0), (self._theme.focus, 2 * s), (self._theme.ink, 6 * s)]
        rect = ring.get_rect()
        for color, inset in band:
            pygame.draw.rect(ring, color, rect.inflate(-2 * inset, -2 * inset), border_radius=max(1, outer_radius - inset))
        hole_inset = 8 * s
        pygame.draw.rect(
            ring,
            (0, 0, 0, 0),
            rect.inflate(-2 * hole_inset, -2 * hole_inset),
            border_radius=max(1, outer_radius - hole_inset),
        )
        return pygame.transform.smoothscale(ring, ((width + 2 * pad), (height + 2 * pad)))

    def star(self, size: int, *, filled: bool) -> pygame.Surface:
        """Vector fallback star (used only when the shared star art is unavailable)."""

        size = max(8, int(size))
        theme = self._theme
        key = ("star", size, filled, theme.ink)

        def build() -> pygame.Surface:
            s = self.SUPERSAMPLE
            big = size * s
            canvas = pygame.Surface((big, big), pygame.SRCALPHA)
            cx = cy = big / 2
            outer, inner = big * 0.47, big * 0.21
            points = []
            for index in range(10):
                angle = -math.pi / 2 + index * math.pi / 5
                r = outer if index % 2 == 0 else inner
                points.append((cx + r * math.cos(angle), cy + r * math.sin(angle) + big * 0.03))
            pygame.draw.polygon(canvas, (251, 191, 36) if filled else mix(theme.muted, WHITE, 0.3), points)
            pygame.draw.polygon(canvas, theme.ink, points, width=max(2, int(big * 0.05)))
            return pygame.transform.smoothscale(canvas, (size, size))

        return self.cached(key, build)


# --------------------------------------------------------------------------
# Shared art (glyphs, stars, cast) through an injectable resolver
# --------------------------------------------------------------------------

VisualResolver = Callable[[str, str], Path]


def _default_visual_resolver(asset_id: str, variant: str) -> Path:
    from .activity_api import get_shared_visual_path

    return get_shared_visual_path(asset_id, variant=variant)


class ControlArt:
    """Load shared kit art (HUD glyphs, stars, cast poses) once per size.

    Art is resolved semantically through the shared-visual catalogue (the
    default resolver is ``activity_api.get_shared_visual_path``); the resolver is
    injectable for tests and trusted surfaces. Missing art degrades to ``None``
    so callers can fall back to vector/text content rather than failing.
    """

    def __init__(
        self,
        resolver: VisualResolver | None = None,
        *,
        max_entries: int = 48,
    ) -> None:
        self._resolver = resolver if resolver is not None else _default_visual_resolver
        self._images: BoundedCache[tuple[str, str, int, int], pygame.Surface | None] = BoundedCache(max_entries)
        self._sources: BoundedCache[tuple[str, str], pygame.Surface | None] = BoundedCache(16)

    def image(
        self,
        asset_id: str,
        size: tuple[int, int] | int,
        *,
        variant: str = "default",
    ) -> pygame.Surface | None:
        """Return the asset scaled once to ``size`` (int = square), or ``None``."""

        width, height = (size, size) if isinstance(size, int) else size
        key = (asset_id, variant, int(width), int(height))
        if key in self._images:
            return self._images[key]
        source = self._source(asset_id, variant)
        result: pygame.Surface | None = None
        if source is not None and width > 0 and height > 0:
            if source.get_size() == (width, height):
                result = source
            else:
                result = pygame.transform.smoothscale(source, (int(width), int(height)))
        self._images[key] = result
        return result

    def fit(
        self,
        asset_id: str,
        height: int,
        *,
        variant: str = "default",
    ) -> pygame.Surface | None:
        """Return the asset scaled to ``height`` keeping its aspect ratio."""

        source = self._source(asset_id, variant)
        if source is None or height <= 0:
            return None
        width = max(1, round(source.get_width() * height / max(1, source.get_height())))
        return self.image(asset_id, (width, int(height)), variant=variant)

    def _source(self, asset_id: str, variant: str) -> pygame.Surface | None:
        key = (asset_id, variant)
        if key in self._sources:
            return self._sources[key]
        surface: pygame.Surface | None
        try:
            surface = pygame.image.load(str(self._resolver(asset_id, variant)))
            if pygame.display.get_surface() is not None:
                surface = surface.convert_alpha()
        except Exception:
            surface = None
        self._sources[key] = surface
        return surface

    def clear(self) -> None:
        self._images.clear()
        self._sources.clear()


# --------------------------------------------------------------------------
# Focus targets and controls
# --------------------------------------------------------------------------


@runtime_checkable
class FocusTarget(Protocol):
    """Anything the ``ControlLayer`` can focus, hit-test and activate.

    Kit controls satisfy it; Activities wrap their own gameplay elements (for
    example the ten windows in La Casa del Dieci) in ``ExternalTarget`` so the
    same spatial focus and focus ring cover the whole screen.
    """

    @property
    def control_id(self) -> str: ...

    @property
    def rect(self) -> pygame.Rect: ...

    @property
    def focusable(self) -> bool: ...

    @property
    def enabled(self) -> bool: ...

    @property
    def focus_radius(self) -> int: ...

    def contains(self, point: tuple[int, int]) -> bool: ...

    def activate(self) -> bool: ...


class ExternalTarget:
    """Activity-drawn focus/activation target (the kit draws only its focus ring)."""

    def __init__(
        self,
        control_id: str,
        rect: pygame.Rect,
        on_activate: Callable[[], object] | None = None,
        *,
        enabled: bool = True,
        focusable: bool = True,
        focus_radius: int = 12,
    ) -> None:
        if not control_id:
            raise ValueError("control_id must not be empty")
        self._control_id = control_id
        self._rect = pygame.Rect(rect)
        self._on_activate = on_activate
        self.enabled = enabled
        self._focusable = focusable
        self._focus_radius = int(focus_radius)

    @property
    def control_id(self) -> str:
        return self._control_id

    @property
    def rect(self) -> pygame.Rect:
        return self._rect.copy()

    @property
    def focusable(self) -> bool:
        return self._focusable and self.enabled

    @focusable.setter
    def focusable(self, value: bool) -> None:
        self._focusable = bool(value)

    @property
    def focus_radius(self) -> int:
        return self._focus_radius

    def contains(self, point: tuple[int, int]) -> bool:
        return self._rect.collidepoint(point)

    def activate(self) -> bool:
        if not self.enabled or self._on_activate is None:
            return False
        self._on_activate()
        return True


class KitControl(Control):
    """Base for kit controls: geometry, interaction state and cached rendering.

    Subclasses implement ``_content_key`` and ``_build``; the base class owns
    state, hit-testing, activation and the cache key so polymorphic controls
    share one rendering contract. Controls are driven by their ``ControlLayer``.
    """

    focusable_by_default = True

    def __init__(
        self,
        painter: ControlPainter,
        control_id: str,
        rect: pygame.Rect | tuple[int, int, int, int],
        *,
        on_activate: Callable[[], object] | None = None,
        enabled: bool = True,
        selected: bool = False,
        visible: bool = True,
    ) -> None:
        if not control_id:
            raise ValueError("control_id must not be empty")
        self._painter = painter
        self._control_id = control_id
        self._rect = pygame.Rect(rect)
        self._on_activate = on_activate
        self.enabled = enabled
        self.selected = selected
        self.visible = visible
        self.hovered = False
        self.pressed = False

    # -- identity / geometry --
    @property
    def control_id(self) -> str:
        return self._control_id

    @property
    def rect(self) -> pygame.Rect:
        return self._rect.copy()

    @rect.setter
    def rect(self, value: pygame.Rect | tuple[int, int, int, int]) -> None:
        self._rect = pygame.Rect(value)

    @property
    def focusable(self) -> bool:
        return self.focusable_by_default and self.visible and self.enabled

    @property
    def focus_radius(self) -> int:
        return ControlPainter.radius_for(self.shape, self._rect.width, self._rect.height - self.lip)

    shape: BodyShape = BodyShape.PILL
    role: ButtonRole = ButtonRole.NEUTRAL

    @property
    def lip(self) -> int:
        """Tactile lip height; non-pressable displays use none."""

        return max(2, round(self._rect.height * 0.07)) if self.focusable_by_default else 0

    def contains(self, point: tuple[int, int]) -> bool:
        return self.visible and self._rect.collidepoint(point)

    def visual_state(self) -> ControlVisualState:
        return ControlVisualState(
            hovered=self.hovered and self.enabled,
            pressed=self.pressed and self.enabled,
            disabled=not self.enabled,
            selected=self.selected,
        )

    # -- behaviour --
    def activate(self) -> bool:
        if not (self.enabled and self.visible) or self._on_activate is None:
            return False
        self._on_activate()
        return True

    def handle_event(self, event: object) -> UiEventResult:
        """Activate on a pressed ACTIVATE/PRIMARY semantic action delivered directly."""

        if (
            isinstance(event, SemanticInputEvent)
            and event.edge is InputEdge.PRESSED
            and event.action in {SemanticAction.ACTIVATE, SemanticAction.PRIMARY}
        ):
            return UiEventResult.HANDLED if self.activate() else UiEventResult.IGNORED
        return UiEventResult.IGNORED

    # -- rendering --
    def render(self) -> pygame.Surface:
        """Return the cached composite for the current state/content."""

        state = self.visual_state()
        key = (
            type(self).__name__,
            self._control_id,
            self._rect.size,
            state.key,
            self._content_key(),
        )
        return self._painter.cached(key, lambda: self._build(state))

    def draw(self, target: object) -> None:
        if not self.visible:
            return
        assert isinstance(target, pygame.Surface)
        target.blit(self.render(), self._rect.topleft)

    @abstractmethod
    def _content_key(self) -> tuple: ...

    @abstractmethod
    def _build(self, state: ControlVisualState) -> pygame.Surface: ...

    # -- shared composition helpers --
    def _body(self, state: ControlVisualState, *, highlight: bool = True) -> pygame.Surface:
        painter = self._painter
        return painter.body(
            self.shape,
            self._rect.size,
            painter.body_fill(self.role, state),
            lip=self.lip,
            pressed=state.pressed,
            highlight=highlight,
        )

    def _face_rect(self, state: ControlVisualState) -> pygame.Rect:
        """Visible face area (shifted down while pressed, above the lip otherwise)."""

        lip = self.lip
        top = lip if state.pressed else 0
        return pygame.Rect(0, top, self._rect.width, self._rect.height - lip)


def _compose_row(
    pieces: Sequence[pygame.Surface],
    gap: int,
) -> pygame.Surface | None:
    pieces = [piece for piece in pieces if piece is not None]
    if not pieces:
        return None
    width = sum(piece.get_width() for piece in pieces) + gap * (len(pieces) - 1)
    height = max(piece.get_height() for piece in pieces)
    row = pygame.Surface((max(1, width), max(1, height)), pygame.SRCALPHA)
    x = 0
    for piece in pieces:
        row.blit(piece, (x, (height - piece.get_height()) // 2))
        x += piece.get_width() + gap
    return row


class PillButton(KitControl):
    """Rounded action with an optional icon and a short (pre-cased) label.

    When ``compact`` is set (by ``ControlLayout.fit`` on narrow screens) the
    label is dropped and the pill shows its icon only — pre-readers act on the
    picture anyway, and nothing is ever clipped.
    """

    def __init__(
        self,
        painter: ControlPainter,
        control_id: str,
        rect: pygame.Rect | tuple[int, int, int, int],
        *,
        label: str = "",
        icon: pygame.Surface | None = None,
        role: ButtonRole = ButtonRole.NEUTRAL,
        on_activate: Callable[[], object] | None = None,
        enabled: bool = True,
        selected: bool = False,
        label_size: int | None = None,
    ) -> None:
        super().__init__(painter, control_id, rect, on_activate=on_activate, enabled=enabled, selected=selected)
        self.role = role
        self.label = label
        self.icon = icon
        self.compact = False
        self.label_size = label_size

    shape = BodyShape.PILL

    def set_content(self, *, label: str | None = None, icon: pygame.Surface | None = None) -> None:
        if label is not None:
            self.label = label
        if icon is not None:
            self.icon = icon

    def _resolved_label_size(self) -> int:
        face_h = self._rect.height - self.lip
        return int(self.label_size or max(12, round(face_h * 0.38)))

    def preferred_width(self) -> int:
        """Width that shows icon + full label at the current height."""

        face_h = self._rect.height - self.lip
        pad = max(14, face_h // 2)
        content = 0
        if self.icon is not None:
            content += self.icon.get_width()
        if self.label:
            label = self._painter.label(self.label, self._resolved_label_size(), self._painter.theme.text)
            content += label.get_width() + (10 if self.icon is not None else 0)
        return max(face_h + 8, content + 2 * pad)

    def compact_width(self) -> int:
        face_h = self._rect.height - self.lip
        if self.icon is None:
            return self.preferred_width()
        return max(face_h + 8, self.icon.get_width() + face_h)

    def _content_key(self) -> tuple:
        return (self.label, id(self.icon), self.compact, self.role, self.label_size)

    def _build(self, state: ControlVisualState) -> pygame.Surface:
        surface = self._body(state).copy()
        face = self._face_rect(state)
        color = self._painter.content_color(self.role, state)
        pad = max(10, face.height // 3)
        pieces: list[pygame.Surface] = []
        icon = self.icon
        if icon is not None:
            if state.disabled:
                icon = icon.copy()
                icon.fill((255, 255, 255, 120), special_flags=pygame.BLEND_RGBA_MULT)
            pieces.append(icon)
        if self.label and not (self.compact and icon is not None):
            available = face.width - 2 * pad - (icon.get_width() + 10 if icon is not None else 0)
            pieces.append(
                self._painter.label(self.label, self._resolved_label_size(), color, max_width=max(20, available))
            )
        row = _compose_row(pieces, 10)
        if row is not None:
            surface.blit(row, row.get_rect(center=face.center))
        return surface


class IconButton(KitControl):
    """Round (or tile) action with one icon and an optional caption below it."""

    def __init__(
        self,
        painter: ControlPainter,
        control_id: str,
        rect: pygame.Rect | tuple[int, int, int, int],
        *,
        icon: pygame.Surface | None,
        caption: str = "",
        shape: BodyShape = BodyShape.ROUND,
        role: ButtonRole = ButtonRole.NEUTRAL,
        on_activate: Callable[[], object] | None = None,
        enabled: bool = True,
        selected: bool = False,
    ) -> None:
        if shape not in {BodyShape.ROUND, BodyShape.TILE}:
            raise ValueError("IconButton shape must be ROUND or TILE")
        super().__init__(painter, control_id, rect, on_activate=on_activate, enabled=enabled, selected=selected)
        self.icon = icon
        self.caption = caption
        self.shape = shape
        self.role = role

    def contains(self, point: tuple[int, int]) -> bool:
        if not super().contains(point):
            return False
        if self.shape is BodyShape.ROUND:
            cx, cy = self._rect.centerx, self._rect.top + (self._rect.height - self.lip) / 2
            radius = min(self._rect.width, self._rect.height - self.lip) / 2 + 6
            return (point[0] - cx) ** 2 + (point[1] - cy) ** 2 <= radius * radius
        return True

    def _content_key(self) -> tuple:
        return (id(self.icon), self.caption, self.shape, self.role)

    def _build(self, state: ControlVisualState) -> pygame.Surface:
        surface = self._body(state).copy()
        face = self._face_rect(state)
        icon = self.icon
        if icon is not None and state.disabled:
            icon = icon.copy()
            icon.fill((255, 255, 255, 110), special_flags=pygame.BLEND_RGBA_MULT)
        if self.caption:
            color = self._painter.content_color(self.role, state)
            caption = self._painter.label(
                self.caption,
                max(12, round(face.height * 0.2)),
                color,
                max_width=face.width - 14,
            )
            gap = 2
            total = (icon.get_height() if icon is not None else 0) + gap + caption.get_height()
            y = face.centery - total // 2
            if icon is not None:
                surface.blit(icon, icon.get_rect(midtop=(face.centerx, y)))
                y += icon.get_height() + gap
            surface.blit(caption, caption.get_rect(midtop=(face.centerx, y)))
        elif icon is not None:
            surface.blit(icon, icon.get_rect(center=face.center))
        return surface


class ToolSlot(PillButton):
    """One selectable slot of a ``ToolStrip`` (pill tab or square tool tile)."""

    def __init__(
        self,
        painter: ControlPainter,
        control_id: str,
        rect: pygame.Rect | tuple[int, int, int, int],
        *,
        tool_id: str,
        label: str = "",
        icon: pygame.Surface | None = None,
        shape: BodyShape = BodyShape.PILL,
        on_activate: Callable[[], object] | None = None,
    ) -> None:
        super().__init__(painter, control_id, rect, label=label, icon=icon, on_activate=on_activate)
        if shape not in {BodyShape.PILL, BodyShape.TILE}:
            raise ValueError("ToolSlot shape must be PILL or TILE")
        self.shape = shape
        self.tool_id = tool_id


class ToolStrip:
    """Exclusive selection of tools/modes (exactly one ``ToolSlot`` selected).

    The strip is a semantic group, not a widget container: its slots are
    ordinary focusable controls added to the ``ControlLayer``. Selecting a slot
    (pointer or ACTIVATE) updates the selection and calls ``on_select(tool_id)``.
    """

    def __init__(
        self,
        painter: ControlPainter,
        strip_id: str,
        tools: Sequence[tuple[str, str, pygame.Surface | None]],
        *,
        rects: Sequence[pygame.Rect] | None = None,
        selected: str | None = None,
        shape: BodyShape = BodyShape.PILL,
        on_select: Callable[[str], object] | None = None,
    ) -> None:
        if not tools:
            raise ValueError("a ToolStrip needs at least one tool")
        ids = [tool_id for tool_id, _, _ in tools]
        if len(set(ids)) != len(ids):
            raise ValueError("tool ids must be unique")
        self.strip_id = strip_id
        self._on_select = on_select
        placeholder = [pygame.Rect(0, 0, 120, 60)] * len(tools)
        geometry = list(rects) if rects is not None else placeholder
        if len(geometry) != len(tools):
            raise ValueError("one rect per tool is required")
        self.slots: tuple[ToolSlot, ...] = tuple(
            ToolSlot(
                painter,
                f"{strip_id}.{tool_id}",
                rect,
                tool_id=tool_id,
                label=label,
                icon=icon,
                shape=shape,
                on_activate=(lambda chosen=tool_id: self.select(chosen, notify=True)),
            )
            for (tool_id, label, icon), rect in zip(tools, geometry)
        )
        self._selected = selected if selected in ids else ids[0]
        self._sync()

    @property
    def selected(self) -> str:
        return self._selected

    @property
    def controls(self) -> tuple[ToolSlot, ...]:
        return self.slots

    def select(self, tool_id: str, *, notify: bool = False) -> None:
        if tool_id not in {slot.tool_id for slot in self.slots}:
            raise ValueError(f"unknown tool: {tool_id!r}")
        self._selected = tool_id
        self._sync()
        if notify and self._on_select is not None:
            self._on_select(tool_id)

    def _sync(self) -> None:
        for slot in self.slots:
            slot.selected = slot.tool_id == self._selected


class HudChip(KitControl):
    """Non-interactive counter: one glyph plus a number (e.g. stars collected)."""

    focusable_by_default = False

    def __init__(
        self,
        painter: ControlPainter,
        control_id: str,
        rect: pygame.Rect | tuple[int, int, int, int],
        *,
        icon: pygame.Surface | None,
        value: int | str = 0,
    ) -> None:
        super().__init__(painter, control_id, rect)
        self.icon = icon
        self.value = value

    def preferred_width(self, *, digits: int = 2) -> int:
        height = self._rect.height
        sample = self._painter.label("8" * digits, max(12, round(height * 0.5)), self._painter.theme.text)
        icon_w = self.icon.get_width() if self.icon is not None else 0
        return int(icon_w + sample.get_width() + height * 0.75)

    def _content_key(self) -> tuple:
        return (str(self.value), id(self.icon))

    def _build(self, state: ControlVisualState) -> pygame.Surface:
        painter = self._painter
        body = painter.body(
            BodyShape.PILL,
            self._rect.size,
            painter.theme.surface,
            contour_width=max(2, round(self._rect.height * 0.045)),
        )
        surface = body.copy()
        height = self._rect.height
        number = painter.label(str(self.value), max(12, round(height * 0.5)), painter.theme.text)
        icon = self.icon
        x = max(6, height // 6)
        if icon is not None:
            surface.blit(icon, icon.get_rect(midleft=(x, height // 2)))
            x += icon.get_width()
        remaining = pygame.Rect(x, 0, self._rect.width - x - height // 4, height)
        surface.blit(number, number.get_rect(center=remaining.center))
        return surface


class ProgressDots(KitControl):
    """Non-interactive round progress: done (accent), current (ringed), to do."""

    focusable_by_default = False

    def __init__(
        self,
        painter: ControlPainter,
        control_id: str,
        rect: pygame.Rect | tuple[int, int, int, int],
        *,
        total: int,
        current: int = 0,
    ) -> None:
        if total < 1:
            raise ValueError("ProgressDots total must be positive")
        super().__init__(painter, control_id, rect)
        self.total = int(total)
        self.current = int(current)

    def set_progress(self, current: int) -> None:
        self.current = max(0, min(self.total, int(current)))

    @staticmethod
    def preferred_width(total: int, height: int) -> int:
        return int(total * height * 0.62 + (total - 1) * height * 0.22 + height * 0.5)

    def _content_key(self) -> tuple:
        return (self.total, self.current)

    def _build(self, state: ControlVisualState) -> pygame.Surface:
        painter = self._painter
        theme = painter.theme
        width, height = self._rect.size
        chip = painter.body(BodyShape.PILL, (width, height), mix(theme.surface, theme.ink, 0.04), contour_width=max(2, round(height * 0.045)), highlight=False)
        surface = chip.copy()
        dot = max(8, int(height * 0.46))
        current_size = max(dot + 4, int(height * 0.62))
        step = (width - height * 0.5) / self.total
        for index in range(self.total):
            cx = int(height * 0.25 + step * (index + 0.5))
            if index < self.current:
                face = painter.body(BodyShape.ROUND, (dot, dot), theme.accent, contour_width=max(2, dot // 9))
            elif index == self.current:
                face = painter.body(BodyShape.ROUND, (current_size, current_size), mix(theme.accent, WHITE, 0.55), contour_width=max(3, current_size // 6))
            else:
                face = painter.body(BodyShape.ROUND, (dot, dot), theme.surface, contour=mix(theme.ink, theme.surface, 0.45), contour_width=max(2, dot // 9), highlight=False)
            surface.blit(face, face.get_rect(center=(cx, height // 2)))
        return surface


class PromptBanner(KitControl):
    """Icon + short text card with an optional replay-voice ``IconButton``.

    The banner itself is display-only; its ``replay`` button is an ordinary
    focusable control (add ``banner.controls`` to the layer). The Activity owns
    the speech cue that replay plays.
    """

    focusable_by_default = False
    shape = BodyShape.PANEL

    def __init__(
        self,
        painter: ControlPainter,
        control_id: str,
        rect: pygame.Rect | tuple[int, int, int, int],
        *,
        text: str = "",
        icon: pygame.Surface | None = None,
        replay_icon: pygame.Surface | None = None,
        on_replay: Callable[[], object] | None = None,
        text_size: int | None = None,
        text_color: Rgb | None = None,
    ) -> None:
        super().__init__(painter, control_id, rect)
        self.text = text
        self.icon = icon
        self.text_size = text_size
        self.text_color = text_color
        self.replay: IconButton | None = None
        if on_replay is not None:
            self.replay = IconButton(
                painter,
                f"{control_id}.replay",
                self._replay_rect(),
                icon=replay_icon,
                on_activate=on_replay,
                role=ButtonRole.PRIMARY,
            )

    @property
    def controls(self) -> tuple[KitControl, ...]:
        return (self, self.replay) if self.replay is not None else (self,)

    @property
    def rect(self) -> pygame.Rect:  # type: ignore[override]
        return self._rect.copy()

    @rect.setter
    def rect(self, value: pygame.Rect | tuple[int, int, int, int]) -> None:
        self._rect = pygame.Rect(value)
        if self.replay is not None:
            self.replay.rect = self._replay_rect()

    def _replay_rect(self) -> pygame.Rect:
        size = max(36, self._rect.height - 12)
        return pygame.Rect(self._rect.right - size - 6, self._rect.centery - size // 2, size, size)

    def set_text(self, text: str, *, icon: pygame.Surface | None = None) -> None:
        self.text = text
        if icon is not None:
            self.icon = icon

    def _text_size(self) -> int:
        return int(self.text_size or max(14, round(self._rect.height * 0.46)))

    def preferred_width(self) -> int:
        height = self._rect.height
        label = self._painter.label(self.text, self._text_size(), self._painter.theme.text) if self.text else None
        width = height // 2 + (label.get_width() if label is not None else 0) + height // 2
        if self.icon is not None:
            width += self.icon.get_width() + 12
        if self.replay is not None:
            width += height + 6
        return width

    def _content_key(self) -> tuple:
        return (self.text, id(self.icon), self.replay is not None, self.text_size, self.text_color)

    def _build(self, state: ControlVisualState) -> pygame.Surface:
        painter = self._painter
        body = painter.body(BodyShape.PANEL, self._rect.size, painter.theme.surface, lip=max(2, self._rect.height // 16))
        surface = body.copy()
        height = self._rect.height
        face = pygame.Rect(height // 3, 0, self._rect.width - height // 3 * 2, height - max(2, height // 16))
        if self.replay is not None:
            face.width -= self.replay.rect.width + 6
        color = self.text_color or painter.theme.text
        pieces: list[pygame.Surface] = []
        if self.icon is not None:
            pieces.append(self.icon)
        if self.text:
            available = face.width - (self.icon.get_width() + 12 if self.icon is not None else 0)
            pieces.append(painter.label(self.text, self._text_size(), color, max_width=max(20, available)))
        row = _compose_row(pieces, 12)
        if row is not None:
            surface.blit(row, row.get_rect(center=face.center))
        return surface


# --------------------------------------------------------------------------
# Input: pointer phases + pygame adapter
# --------------------------------------------------------------------------


class PointerPhase(StrEnum):
    MOVE = "move"
    DOWN = "down"
    UP = "up"
    CANCEL = "cancel"


@dataclass(frozen=True, slots=True)
class KitPointer:
    """Pointer/touch sample already mapped into the layer's logical space."""

    phase: PointerPhase
    position: tuple[int, int]


KitInput = Union[KitPointer, SemanticInputEvent]


class PygameControlInput:
    """Translate Pygame events into kit inputs without opening any device.

    Keyboard and SDL-controller buttons go through the standard NAVIGATION
    mapping (ADR 0020), so Activities with ``pointer`` or ``hybrid`` profiles
    still get a learned focus context for their controls. Left-stick motion is
    converted with Greia's central dead zone and repeat policy. Pointer samples
    are mapped by the injected ``to_logical`` and dropped inside protected
    chrome (``is_safe``), so Home/Back input never reaches the Activity's kit.
    """

    def __init__(
        self,
        *,
        to_logical: Callable[[tuple[int, int]], tuple[float, float] | None] | None = None,
        is_safe: Callable[[tuple[int, int]], bool] | None = None,
        policy: StandardInputPolicy = DEFAULT_INPUT_POLICY,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._translator = PygameInputTranslator(InteractionProfile.NAVIGATION)
        self._to_logical = to_logical
        self._is_safe = is_safe
        self._policy = policy
        self._clock = clock
        self._stick = (0.0, 0.0)
        self._held: SemanticAction | None = None
        self._next_repeat = 0.0

    def translate(self, event: pygame.event.Event) -> KitInput | None:
        semantic = self._translator.digital(event)
        if semantic is not None:
            return semantic
        axis = self._translator.controller_axis(event)
        if axis is not None:
            return self._stick_event(axis.axis, axis.value)
        if event.type == pygame.MOUSEMOTION:
            return self._pointer(PointerPhase.MOVE, event.pos)
        if event.type in {pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP} and getattr(event, "button", 1) == 1:
            phase = PointerPhase.DOWN if event.type == pygame.MOUSEBUTTONDOWN else PointerPhase.UP
            return self._pointer(phase, event.pos)
        return None

    def poll(self) -> SemanticInputEvent | None:
        """Return one repeated stick navigation step when due (call per frame)."""

        if self._held is None:
            return None
        now = self._clock()
        if now < self._next_repeat:
            return None
        self._next_repeat = now + self._policy.navigation_repeat_interval_seconds
        return SemanticInputEvent(self._held, InputEdge.PRESSED, InputSource.CONTROLLER)

    def _pointer(self, phase: PointerPhase, position: tuple[int, int]) -> KitPointer | None:
        if self._is_safe is not None and not self._is_safe(position):
            return KitPointer(PointerPhase.CANCEL, (-1, -1)) if phase is PointerPhase.UP else None
        logical: tuple[float, float] | None = (float(position[0]), float(position[1]))
        if self._to_logical is not None:
            logical = self._to_logical(position)
        if logical is None:
            return KitPointer(PointerPhase.CANCEL, (-1, -1)) if phase is PointerPhase.UP else None
        return KitPointer(phase, (int(logical[0]), int(logical[1])))

    def _stick_event(self, axis: ControllerAxis, value: float) -> SemanticInputEvent | None:
        x, y = self._stick
        if axis is ControllerAxis.LEFT_X:
            x = value
        elif axis is ControllerAxis.LEFT_Y:
            y = value
        else:
            return None
        self._stick = (x, y)
        direction = navigation_direction(
            normalize_stick(x, y, self._policy.stick_dead_zone),
            self._policy.navigation_threshold,
        )
        if direction == self._held:
            return None
        self._held = direction
        if direction is None:
            return None
        self._next_repeat = self._clock() + self._policy.navigation_repeat_delay_seconds
        return SemanticInputEvent(direction, InputEdge.PRESSED, InputSource.CONTROLLER)


# --------------------------------------------------------------------------
# Spatial focus + control layer
# --------------------------------------------------------------------------

_DIRECTIONS = {
    SemanticAction.NAV_LEFT: (-1, 0),
    SemanticAction.NAV_RIGHT: (1, 0),
    SemanticAction.NAV_UP: (0, -1),
    SemanticAction.NAV_DOWN: (0, 1),
    SemanticAction.MOVE_LEFT: (-1, 0),
    SemanticAction.MOVE_RIGHT: (1, 0),
    SemanticAction.MOVE_UP: (0, -1),
    SemanticAction.MOVE_DOWN: (0, 1),
}


def spatial_neighbour(
    current: pygame.Rect,
    candidates: Iterable[tuple[str, pygame.Rect]],
    direction: tuple[int, int],
) -> str | None:
    """Pick the nearest candidate in ``direction`` (deterministic, no wrap).

    A candidate qualifies when its centre lies beyond the current centre along
    the direction. Candidates whose perpendicular span overlaps the current
    control win over diagonal ones; ties break on distance then registration.
    """

    dx, dy = direction
    best: tuple[float, str] | None = None
    cx, cy = current.center
    for control_id, rect in candidates:
        ox, oy = rect.center
        along = (ox - cx) * dx + (oy - cy) * dy
        if along <= 0:
            continue
        if dx:
            overlap = min(current.bottom, rect.bottom) - max(current.top, rect.top)
            perpendicular = abs(oy - cy)
        else:
            overlap = min(current.right, rect.right) - max(current.left, rect.left)
            perpendicular = abs(ox - cx)
        aligned = overlap > 0
        score = along + (perpendicular * 0.6 if aligned else perpendicular * 2.2 + 10_000)
        if best is None or score < best[0]:
            best = (score, control_id)
    return best[1] if best is not None else None


class ControlLayer(Screen):
    """Own a set of focus targets, route kit input and draw kit controls.

    It is a ``ui_core.Screen`` so Activities can host it in a
    ``SurfaceNavigator`` and push modal Overlays (e.g. the completion scene)
    above it. ``handle_event`` accepts ``KitPointer`` and semantic input and
    returns ``HANDLED`` only when the kit consumed the input, leaving everything
    else (gameplay taps, drags) to the Activity.
    """

    TAP_SLOP = 14

    def __init__(
        self,
        painter: ControlPainter,
        targets: Iterable[FocusTarget] = (),
        *,
        layer_id: str = "controls",
        initial_focus: str | None = None,
    ) -> None:
        self._painter = painter
        self._layer_id = layer_id
        self._targets: dict[str, FocusTarget] = {}
        self.invalidation = InvalidationTracker()
        self.focused_id: str | None = None
        self.hovered_id: str | None = None
        self.pressed_id: str | None = None
        self.focus_visible = False
        self.set_targets(targets)
        if initial_focus is not None:
            self.focus(initial_focus)

    @property
    def surface_id(self) -> str:
        return self._layer_id

    # -- registration --
    def set_targets(self, targets: Iterable[FocusTarget]) -> None:
        """Replace the registered targets (order = draw and tie-break order)."""

        replacement: dict[str, FocusTarget] = {}
        for target in targets:
            if target.control_id in replacement:
                raise ValueError(f"duplicate control id: {target.control_id}")
            replacement[target.control_id] = target
        self._targets = replacement
        for attribute in ("focused_id", "hovered_id", "pressed_id"):
            if getattr(self, attribute) not in self._targets:
                setattr(self, attribute, None)
        self._sync_flags()
        self.invalidation.invalidate()

    def target(self, control_id: str) -> FocusTarget:
        return self._targets[control_id]

    @property
    def targets(self) -> tuple[FocusTarget, ...]:
        return tuple(self._targets.values())

    def _focusable(self) -> list[tuple[str, pygame.Rect]]:
        return [(cid, target.rect) for cid, target in self._targets.items() if target.focusable]

    # -- focus --
    def focus(self, control_id: str | None, *, visible: bool | None = None) -> bool:
        if control_id is not None:
            target = self._targets.get(control_id)
            if target is None or not target.focusable:
                return False
        changed = control_id != self.focused_id
        self.focused_id = control_id
        if visible is not None:
            changed = changed or visible != self.focus_visible
            self.focus_visible = visible
        if changed:
            self.invalidation.invalidate()
        return True

    def ensure_focus(self) -> None:
        """Keep focus on a focusable target (first registered as fallback)."""

        current = self._targets.get(self.focused_id) if self.focused_id else None
        if current is not None and current.focusable:
            return
        candidates = self._focusable()
        self.focused_id = candidates[0][0] if candidates else None
        self.invalidation.invalidate()

    def navigate(self, action: SemanticAction) -> bool:
        """Move focus spatially; returns True when the action was consumed."""

        direction = _DIRECTIONS.get(action)
        if direction is None:
            return False
        was_visible = self.focus_visible
        self.focus_visible = True
        current = self._targets.get(self.focused_id) if self.focused_id else None
        if current is None or not current.focusable:
            self.ensure_focus()
            return True
        candidates = [(cid, rect) for cid, rect in self._focusable() if cid != current.control_id]
        nxt = spatial_neighbour(current.rect, candidates, direction)
        if nxt is not None:
            self.focused_id = nxt
            self.invalidation.invalidate()
        elif not was_visible:
            self.invalidation.invalidate()
        return True

    # -- events --
    def handle_event(self, event: object) -> UiEventResult:
        if isinstance(event, KitPointer):
            return self._pointer(event)
        if isinstance(event, SemanticInputEvent):
            if event.edge is not InputEdge.PRESSED:
                return UiEventResult.IGNORED
            if event.action in _DIRECTIONS:
                return UiEventResult.HANDLED if self.navigate(event.action) else UiEventResult.IGNORED
            if event.action in {SemanticAction.ACTIVATE, SemanticAction.PRIMARY}:
                if self.focused_id is None:
                    self.ensure_focus()
                target = self._targets.get(self.focused_id) if self.focused_id else None
                if target is None:
                    return UiEventResult.IGNORED
                self.focus_visible = True
                self.invalidation.invalidate()
                return UiEventResult.HANDLED if target.activate() else UiEventResult.IGNORED
        return UiEventResult.IGNORED

    def hit(self, point: tuple[int, int]) -> FocusTarget | None:
        """Return the topmost enabled target at ``point`` (last registered wins)."""

        for target in reversed(tuple(self._targets.values())):
            if target.enabled and target.contains(point) and _is_interactive(target):
                return target
        return None

    def tap(self, point: tuple[int, int]) -> bool:
        """Convenience: deliver one full DOWN+UP tap; True when it activated."""

        if self.handle_event(KitPointer(PointerPhase.DOWN, point)) is UiEventResult.IGNORED:
            return False
        return self.handle_event(KitPointer(PointerPhase.UP, point)) is UiEventResult.HANDLED

    def _pointer(self, event: KitPointer) -> UiEventResult:
        if event.phase is PointerPhase.CANCEL:
            self._set_pressed(None)
            return UiEventResult.IGNORED
        target = self.hit(event.position)
        target_id = target.control_id if target is not None else None
        if event.phase is PointerPhase.MOVE:
            if target_id != self.hovered_id:
                self.hovered_id = target_id
                self._sync_flags()
                self.invalidation.invalidate()
                return UiEventResult.HANDLED
            return UiEventResult.IGNORED
        if event.phase is PointerPhase.DOWN:
            if target is None:
                return UiEventResult.IGNORED
            self._set_pressed(target_id)
            if target.focusable:
                self.focused_id = target_id
            self.focus_visible = False
            return UiEventResult.HANDLED
        # UP: activate the pressed target when released on it (with tap slop).
        pressed = self._targets.get(self.pressed_id) if self.pressed_id else None
        self._set_pressed(None)
        if pressed is None:
            return UiEventResult.IGNORED
        if pressed.contains(event.position) or pressed.rect.inflate(2 * self.TAP_SLOP, 2 * self.TAP_SLOP).collidepoint(event.position):
            pressed.activate()
        return UiEventResult.HANDLED

    def _set_pressed(self, control_id: str | None) -> None:
        if control_id != self.pressed_id:
            self.pressed_id = control_id
            self._sync_flags()
            self.invalidation.invalidate()

    def _sync_flags(self) -> None:
        for cid, target in self._targets.items():
            if isinstance(target, KitControl):
                target.hovered = cid == self.hovered_id
                target.pressed = cid == self.pressed_id

    # -- drawing --
    def draw(self, target: object) -> None:
        """Draw every visible kit control, then the focus ring (when visible)."""

        assert isinstance(target, pygame.Surface)
        for item in self._targets.values():
            if isinstance(item, KitControl):
                item.draw(target)
        self.draw_focus(target)
        self.invalidation.mark_drawn()

    def draw_focus(self, target: pygame.Surface) -> None:
        if not self.focus_visible or self.focused_id is None:
            return
        item = self._targets.get(self.focused_id)
        if item is None or not item.focusable:
            return
        rect = item.rect
        lip = item.lip if isinstance(item, KitControl) else 0
        face = pygame.Rect(rect.x, rect.y, rect.width, rect.height - lip)
        ring = self._painter.focus_ring(face.size, item.focus_radius)
        pad = ControlPainter.FOCUS_PAD
        target.blit(ring, (face.x - pad, face.y - pad))


def _is_interactive(target: FocusTarget) -> bool:
    if isinstance(target, KitControl):
        return target.focusable_by_default and target.visible
    return True


# --------------------------------------------------------------------------
# Layout outside protected chrome
# --------------------------------------------------------------------------


class Align(StrEnum):
    START = "start"
    CENTER = "center"
    END = "end"


@dataclass(frozen=True, slots=True)
class ControlLayout:
    """Place kit bars in a logical drawing space outside protected chrome.

    ``protected`` is the platform Home/Back region expressed in the same logical
    space the Activity draws in (for a ``PygameReferenceCanvas`` it is mapped
    through the canvas transform, so a 1024×600 reference layout keeps clear of
    the chrome at 480×320 as well). ``scale`` is physical pixels per logical
    pixel, used to keep controls at a touchable physical size.
    """

    width: int
    height: int
    protected: pygame.Rect
    scale: float = 1.0
    margin: int = 12
    gap: int = 10

    MIN_TOUCH_PHYSICAL = 40

    @classmethod
    def for_surface(cls, width: int, height: int, *, margin: int = 12, gap: int = 10) -> "ControlLayout":
        """Layout for an Activity drawing directly at physical resolution."""

        chrome = ActivitySystemChromeLayout.for_surface(width, height).protected_region
        return cls(int(width), int(height), pygame.Rect(chrome.x, chrome.y, chrome.width, chrome.height), 1.0, margin, gap)

    @classmethod
    def for_canvas(
        cls,
        canvas: object,
        physical_size: tuple[int, int],
        *,
        margin: int = 12,
        gap: int = 10,
    ) -> "ControlLayout":
        """Layout for a ``PygameReferenceCanvas`` shown on ``physical_size``."""

        transform = canvas.mapper.transform  # type: ignore[attr-defined]
        logical_w, logical_h = canvas.surface.get_size()  # type: ignore[attr-defined]
        chrome = ActivitySystemChromeLayout.for_surface(*physical_size).protected_region
        top_left = transform.physical_to_logical((chrome.x, chrome.y), reject_outside=False)
        bottom_right = transform.physical_to_logical((chrome.right, chrome.bottom), reject_outside=False)
        left = max(0, int(math.floor(top_left[0])))
        top = max(0, int(math.floor(top_left[1])))
        right = min(logical_w, int(math.ceil(bottom_right[0])))
        bottom = min(logical_h, int(math.ceil(bottom_right[1])))
        protected = pygame.Rect(left, top, max(0, right - left), max(0, bottom - top))
        return cls(int(logical_w), int(logical_h), protected, float(transform.scale), margin, gap)

    def control_height(self, preferred: int, *, maximum: int | None = None) -> int:
        """Preferred height raised to the physical touch floor, then capped."""

        floor = int(math.ceil(self.MIN_TOUCH_PHYSICAL / max(0.01, self.scale)))
        value = max(int(preferred), floor)
        return min(value, int(maximum)) if maximum is not None else value

    def top_bar(self, height: int) -> pygame.Rect:
        """Bar beside the protected chrome, from its right edge to the margin."""

        left = self.protected.right + self.gap + 4
        return pygame.Rect(left, self.margin, max(0, self.width - self.margin - left), int(height))

    def bottom_bar(self, height: int) -> pygame.Rect:
        return pygame.Rect(self.margin, self.height - self.margin - int(height), self.width - 2 * self.margin, int(height))

    def clear_of_chrome(self, rect: pygame.Rect) -> pygame.Rect:
        """Move ``rect`` below the protected region when it would overlap it."""

        rect = pygame.Rect(rect)
        if rect.colliderect(self.protected):
            rect.top = self.protected.bottom + self.gap
        return rect

    def overlaps_chrome(self, rect: pygame.Rect) -> bool:
        return pygame.Rect(rect).colliderect(self.protected)

    @staticmethod
    def fit(available: int, preferred: Sequence[int], minimum: Sequence[int], gap: int) -> tuple[list[int], bool]:
        """Return widths that fit ``available`` and whether compact mode was used."""

        gaps = gap * max(0, len(preferred) - 1)
        if sum(preferred) + gaps <= available:
            return list(preferred), False
        if sum(preferred) * 0.8 + gaps <= available:
            # Slightly narrower: labels shrink to fit (never clip) and stay.
            factor = (available - gaps) / max(1, sum(preferred))
            return [max(1, int(p * factor)) for p in preferred], False
        if sum(minimum) + gaps <= available:
            spare = available - gaps - sum(minimum)
            extra = [p - m for p, m in zip(preferred, minimum)]
            total_extra = sum(extra) or 1
            # Share the spare width proportionally but never exceed preferred.
            widths = [m + min(e, int(spare * e / total_extra)) for m, e in zip(minimum, extra)]
            return widths, True
        factor = max(0.1, (available - gaps) / max(1, sum(minimum)))
        return [max(1, int(m * factor)) for m in minimum], True

    def row(
        self,
        bar: pygame.Rect,
        widths: Sequence[int],
        *,
        align: Align = Align.START,
        gap: int | None = None,
        height: int | None = None,
    ) -> list[pygame.Rect]:
        """Place items of ``widths`` in ``bar`` (vertically centred)."""

        spacing = self.gap if gap is None else int(gap)
        total = sum(widths) + spacing * max(0, len(widths) - 1)
        if align is Align.START:
            x = bar.left
        elif align is Align.END:
            x = bar.right - total
        else:
            x = bar.centerx - total // 2
        item_h = bar.height if height is None else int(height)
        y = bar.centery - item_h // 2
        rects = []
        for width in widths:
            rects.append(pygame.Rect(x, y, int(width), item_h))
            x += int(width) + spacing
        return rects


# --------------------------------------------------------------------------
# Facade
# --------------------------------------------------------------------------


class ControlKit:
    """Small factory/facade that wires painter + art for one Activity surface.

    ``ControlKit`` owns the bounded caches for one logical drawing surface. It
    is not a global: create one per Activity (and drop it on teardown).
    """

    def __init__(
        self,
        typography: LabelTypography,
        theme: ControlTheme = ControlTheme(),
        *,
        art: ControlArt | None = None,
        resolver: VisualResolver | None = None,
    ) -> None:
        self.painter = ControlPainter(typography, theme)
        self.art = art if art is not None else ControlArt(resolver)

    @property
    def theme(self) -> ControlTheme:
        return self.painter.theme

    # -- art --
    def glyph(self, glyph_id: str, size: int) -> pygame.Surface | None:
        """Return a shared HUD glyph (``icon.hud.<id>``) at ``size`` px."""

        return self.art.image(f"icon.hud.{glyph_id}", int(size))

    def star(self, size: int, *, filled: bool = True) -> pygame.Surface:
        """Return the shared star art (or a vector fallback)."""

        image = self.art.image("ui.control.star", int(size), variant="default" if filled else "off")
        return image if image is not None else self.painter.star(size, filled=filled)

    def text_icon(self, text: str, size: int, color: Rgb | None = None) -> pygame.Surface:
        """Render a pictogram/emoji as a cached icon (content, not chrome)."""

        return self.painter.label(text, size, color or self.painter.theme.text)

    # -- controls --
    def pill_button(self, control_id: str, rect: pygame.Rect, **kwargs) -> PillButton:
        return PillButton(self.painter, control_id, rect, **kwargs)

    def icon_button(self, control_id: str, rect: pygame.Rect, **kwargs) -> IconButton:
        return IconButton(self.painter, control_id, rect, **kwargs)

    def tool_strip(self, strip_id: str, tools, **kwargs) -> ToolStrip:
        return ToolStrip(self.painter, strip_id, tools, **kwargs)

    def hud_chip(self, control_id: str, rect: pygame.Rect, **kwargs) -> HudChip:
        return HudChip(self.painter, control_id, rect, **kwargs)

    def progress_dots(self, control_id: str, rect: pygame.Rect, **kwargs) -> ProgressDots:
        return ProgressDots(self.painter, control_id, rect, **kwargs)

    def prompt_banner(self, control_id: str, rect: pygame.Rect, **kwargs) -> PromptBanner:
        return PromptBanner(self.painter, control_id, rect, **kwargs)

    def layer(self, targets: Iterable[FocusTarget] = (), **kwargs) -> ControlLayer:
        return ControlLayer(self.painter, targets, **kwargs)

    def clear(self) -> None:
        self.painter.clear()
        self.art.clear()


__all__ = [
    "Align",
    "BodyShape",
    "ButtonRole",
    "ControlArt",
    "ControlKit",
    "ControlLayer",
    "ControlLayout",
    "ControlPainter",
    "ControlTheme",
    "ControlVisualState",
    "ExternalTarget",
    "FocusTarget",
    "HudChip",
    "IconButton",
    "KitControl",
    "KitInput",
    "KitPointer",
    "PillButton",
    "PointerPhase",
    "ProgressDots",
    "PromptBanner",
    "PygameControlInput",
    "ToolSlot",
    "ToolStrip",
    "mix",
    "spatial_neighbour",
]
