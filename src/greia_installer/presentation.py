"""Installer look: Greia meadow, shared cast, kit controls, prepared layers.

The installer is parent-facing but must feel like the same product as the
child Shell. This module owns *how installer pages look* and nothing about
what they do: page state, disk safety, transaction calls and hit-target keys
stay in :mod:`greia_installer.main`. It reuses, rather than re-implements:

- the Shell's meadow backdrop (``bg.meadow_day.home``) and the shared mascot
  (``character.leo`` poses) through the canonical shared-visual catalogue;
- the shared Activity control kit painter (ADR 0037 ``ControlPainter``) for
  pill buttons, panels, round step dots and focus rings, so installer
  controls have the same ink contour, two-stop fill and highlight as Shell
  and Activity controls;
- the palette tokens of ``GREIA_SVG_AUTHORING_RULES.md`` §2.

The live installer image deliberately stages a small asset subset, so every
piece of art is optional: without the shared catalogue the meadow is painted
procedurally once and the owl core icon stands in for Leo.

Performance (Atom reference floor): a page's static chrome (backdrop, card,
step dots, mascot, title) is composed once into one opaque *prepared layer*
per (page, viewport) and cached in a hard-bounded LRU; a frame then costs one
opaque full-screen blit plus cached control bodies and cached text. Nothing
here scales images, builds fonts or rasterizes text per frame.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from greia_platform import boot_animation
from greia_platform.activity_controls import (
    COCOA,
    INK,
    MUTED,
    SUNSHINE,
    SURFACE,
    WHITE,
    BodyShape,
    ControlPainter,
    ControlTheme,
    mix,
)
from greia_platform.boot_logo import canonical_boot_logo
from greia_platform.typography import FontRole
from greia_platform.ui_core import BoundedCache

Rgb = tuple[int, int, int]

# Palette (GREIA_SVG_AUTHORING_RULES.md §2 tokens and derived steps only).
CREAM: Rgb = (247, 235, 203)
SKY: Rgb = (207, 234, 247)
CORAL: Rgb = (244, 111, 97)
LEAF: Rgb = (89, 184, 106)
BURGUNDY: Rgb = (106, 48, 64)
FOREST: Rgb = (40, 81, 58)
#: Destructive fill: coral shaded toward ink so white labels stay readable.
DANGER: Rgb = mix(CORAL, INK, 0.3)
DANGER_PRESSED: Rgb = mix(CORAL, INK, 0.55)
#: Soft inset field (rows, list items) on the cream card.
FIELD: Rgb = mix(SURFACE, CREAM, 0.7)
HINT: Rgb = mix(COCOA, SURFACE, 0.38)
WARNING_FIELD: Rgb = mix(CORAL, WHITE, 0.82)

#: The parent's journey, as shown by the step dots. Page names, not enums, so
#: this module never imports installer state.
STEP_LABELS: tuple[str, ...] = ("Keyboard", "Disk", "Pointer", "Screen", "Wi-Fi", "Install")
_STEP_BY_PAGE = {
    "LAYOUT": 1,
    "TARGET": 2,
    "POINTER": 3,
    "DISPLAY": 4,
    "SETTINGS": 4,
    "WIFI": 5,
    "CONFIRM": 6,
    "INSTALLING": 6,
    "ERROR": 6,
}


def step_for_page(page_name: str) -> int | None:
    """1-based step shown for an installer page, or ``None`` (no dots)."""

    return _STEP_BY_PAGE.get(page_name)


@dataclass(frozen=True, slots=True)
class PageFrame:
    """Measured regions of one installer page at one viewport size.

    ``main`` is the card content box: page content flows from ``main.top``
    and the navigation row is centred on ``main.bottom - 40`` (the contract
    the pointer page's vertical budget is written against).
    """

    size: tuple[int, int]
    header: Any
    card: Any
    main: Any
    side: Any


def page_frame(pygame: Any, size: tuple[int, int], *, steps: bool = True) -> PageFrame:
    """Lay out header, mascot column and card for ``size`` (pure geometry)."""

    width, height = size
    margin = max(10, min(26, int(width * 0.022)))
    header_h = max(34, min(48, int(height * 0.08))) if steps else margin
    side_w = max(120, min(250, int(width * 0.215)))
    card = pygame.Rect(
        side_w,
        header_h,
        width - side_w - margin,
        height - header_h - margin,
    )
    pad = max(14, min(26, int(card.width * 0.03)))
    main = pygame.Rect(
        card.left + pad,
        card.top + max(10, pad - 6),
        card.width - 2 * pad,
        card.height - max(10, pad - 6) - 2,
    )
    side = pygame.Rect(margin, header_h, side_w - 2 * margin, card.height)
    header = pygame.Rect(card.left, 0, card.width, header_h)
    return PageFrame(size, header, card, main, side)


class InstallerArt:
    """Fail-soft, bounded loader for the installer's shared artwork."""

    _SHARED_CATALOGUE = Path("assets/catalog/shared_visuals_v1.toml")
    _OWL_ICON = Path("assets/icons/core/v1/256/owl.png")

    def __init__(self, root: Path, *, max_entries: int = 16) -> None:
        self.root = Path(root)
        self._catalogue: Any = None
        self._catalogue_failed = False
        self._surfaces: BoundedCache[tuple, Any] = BoundedCache(max_entries)

    def _shared_path(self, asset_id: str, variant: str) -> Path | None:
        if self._catalogue_failed:
            return None
        if self._catalogue is None:
            try:
                from greia_platform.assets import AssetCatalogue

                self._catalogue = AssetCatalogue.load(self.root / self._SHARED_CATALOGUE)
            except Exception:  # noqa: BLE001 - optional art
                self._catalogue_failed = True
                return None
        try:
            path = self._catalogue.get_visual(asset_id).path_for(variant)
        except Exception:  # noqa: BLE001
            return None
        return path if path.is_file() else None

    def _cached(self, key: tuple, build: Callable[[], Any]) -> Any:
        if key in self._surfaces:
            return self._surfaces[key]
        try:
            surface = build()
        except Exception:  # noqa: BLE001 - optional art never breaks a page
            surface = None
        self._surfaces[key] = surface
        return surface

    def backdrop(self, pygame: Any, size: tuple[int, int]) -> Any:
        """Opaque meadow for ``size``: the Shell backdrop, else painted."""

        def build() -> Any:
            path = self._shared_path("bg.meadow_day.home", "default")
            if path is not None:
                image = pygame.image.load(str(path))
                scale = max(size[0] / image.get_width(), size[1] / image.get_height())
                scaled = pygame.transform.smoothscale(
                    image,
                    (max(1, round(image.get_width() * scale)), max(1, round(image.get_height() * scale))),
                )
                # The landscape is a transparent layer over the theme's cream
                # background, exactly as the Shell composes it.
                surface = pygame.Surface(size)
                surface.fill(CREAM)
                surface.blit(scaled, scaled.get_rect(center=(size[0] // 2, size[1] // 2)))
                return _display(surface, alpha=False)
            return _display(_painted_meadow(pygame, size), alpha=False)

        return self._cached(("backdrop", size), build)

    def character(self, pygame: Any, pose: str, size: int) -> Any:
        """Leo in ``pose`` at ``size``², or the owl core icon."""

        def build() -> Any:
            path = self._shared_path("character.leo", pose) or (self.root / self._OWL_ICON)
            image = pygame.image.load(str(path))
            return _display(pygame.transform.smoothscale(image, (size, size)), alpha=True)

        return self._cached(("character", pose, size), build)

    def icon(self, pygame: Any, icon_id: str, size: int) -> Any:
        def build() -> Any:
            image = pygame.image.load(str(self.root / "assets/icons/core/v1/256" / f"{icon_id}.png"))
            return _display(pygame.transform.smoothscale(image, (size, size)), alpha=True)

        return self._cached(("icon", icon_id, size), build)

    def logo_poster(self, pygame: Any, box: tuple[int, int]) -> Any:
        """The animation's final full-colour frame, fitted into ``box``."""

        def build() -> Any:
            frames = boot_animation.frame_paths(boot_animation.candidate_frame_directories(self.root))
            if frames:
                image = pygame.image.load(str(frames[-1]))
            else:
                path = canonical_boot_logo(self.root)
                if path is None:
                    return None
                image = pygame.image.load(str(path))
                if image.get_width() > image.get_height():
                    # The static canvas centres the 222x600 artwork on white;
                    # crop that column instead of shrinking the white margins.
                    crop_w = int(image.get_height() * 222 / 600)
                    rect = pygame.Rect(0, 0, crop_w, image.get_height())
                    rect.centerx = image.get_width() // 2
                    image = image.subsurface(rect).copy()
            scale = min(box[0] / image.get_width(), box[1] / image.get_height())
            size = (max(1, int(image.get_width() * scale)), max(1, int(image.get_height() * scale)))
            scaled = pygame.transform.smoothscale(image.convert_alpha() if pygame.display.get_surface() else image, size)
            return _rounded(pygame, scaled, radius=max(8, size[0] // 9))

        return self._cached(("logo", box), build)

    def clear(self) -> None:
        self._surfaces.clear()


def _display(surface: Any, *, alpha: bool) -> Any:
    try:
        return surface.convert_alpha() if alpha else surface.convert()
    except Exception:  # noqa: BLE001 - no display yet (tests/tooling)
        return surface


def _rounded(pygame: Any, image: Any, *, radius: int) -> Any:
    """``image`` with rounded corners and a 3 px ink contour (built once)."""

    w, h = image.get_size()
    out = pygame.Surface((w, h), pygame.SRCALPHA)
    mask = pygame.Surface((w, h), pygame.SRCALPHA)
    pygame.draw.rect(mask, (255, 255, 255, 255), mask.get_rect(), border_radius=radius)
    out.blit(image, (0, 0))
    out.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
    pygame.draw.rect(out, INK, out.get_rect(), width=3, border_radius=radius)
    return _display(out, alpha=True)


def _painted_meadow(pygame: Any, size: tuple[int, int]) -> Any:
    """Procedural stand-in for the Shell meadow (no shared art staged)."""

    width, height = size
    surface = pygame.Surface(size)
    sky_top, sky_low = mix(CREAM, WHITE, 0.35), CREAM
    horizon = int(height * 0.56)
    for y in range(horizon + 1):
        pygame.draw.line(surface, mix(sky_top, sky_low, y / max(1, horizon)), (0, y), (width, y))
    far = mix(SKY, CREAM, 0.25)
    pygame.draw.ellipse(surface, far, (-width * 0.2, horizon - height * 0.12, width * 0.8, height * 0.4))
    pygame.draw.ellipse(surface, far, (width * 0.35, horizon - height * 0.09, width * 0.9, height * 0.36))
    mid = mix(LEAF, WHITE, 0.42)
    contour = mix(LEAF, INK, 0.45)
    hill = pygame.Rect(-int(width * 0.3), horizon - int(height * 0.04), int(width * 1.6), int(height * 0.9))
    pygame.draw.ellipse(surface, mid, hill)
    pygame.draw.ellipse(surface, contour, hill, width=3)
    ground = pygame.Rect(-int(width * 0.2), horizon + int(height * 0.12), int(width * 1.4), int(height))
    pygame.draw.ellipse(surface, mix(LEAF, WHITE, 0.2), ground)
    pygame.draw.ellipse(surface, contour, ground, width=3)
    sun = (int(width * 0.88), int(height * 0.2))
    pygame.draw.circle(surface, mix(SUNSHINE, WHITE, 0.25), sun, max(12, height // 20))
    pygame.draw.circle(surface, mix(SUNSHINE, INK, 0.35), sun, max(12, height // 20), width=2)
    return surface


class InstallerLook:
    """Renderer for installer pages; owns the painter, art and layer cache."""

    LAYER_CACHE = 6
    NAV_HEIGHT = 50

    def __init__(self, root: Path, typography: Any) -> None:
        self.typography = typography
        self.art = InstallerArt(root)
        self.painter = ControlPainter(typography, ControlTheme(), max_surfaces=96, max_labels=96)
        self._layers: BoundedCache[tuple, Any] = BoundedCache(self.LAYER_CACHE)

    def clear(self) -> None:
        self._layers.clear()
        self.painter.clear()
        self.art.clear()

    # -- prepared page layer ------------------------------------------------

    def page_base(
        self,
        screen: Any,
        pygame: Any,
        frame: PageFrame,
        *,
        title: str,
        title_size: int,
        title_color: Rgb = COCOA,
        step: int | None = None,
        pose: str | None = None,
        poster: bool = False,
    ) -> int:
        """Blit the cached static layer; return the y below the title."""

        key = (frame.size, title, title_size, title_color, step, pose, poster)
        layer = self._layers.get(key)
        if layer is None:
            layer = self._compose_base(pygame, frame, title, title_size, title_color, step, pose, poster)
            self._layers[key] = layer
        screen.blit(layer[0], (0, 0))
        return layer[1]

    def _compose_base(
        self,
        pygame: Any,
        frame: PageFrame,
        title: str,
        title_size: int,
        title_color: Rgb,
        step: int | None,
        pose: str | None,
        poster: bool,
    ) -> tuple[Any, int]:
        surface = pygame.Surface(frame.size)
        backdrop = self.art.backdrop(pygame, frame.size)
        if backdrop is not None:
            surface.blit(backdrop, (0, 0))
        else:
            surface.fill(CREAM)
        card = self.painter.body(
            BodyShape.PANEL, frame.card.size, SURFACE, contour_width=3, highlight=False
        )
        surface.blit(card, frame.card.topleft)
        if step is not None:
            self._draw_steps(surface, pygame, frame.header, step)
        if poster:
            image = self.art.logo_poster(pygame, frame.side.size)
            if image is not None:
                surface.blit(image, image.get_rect(center=frame.side.center))
        elif pose is not None:
            size = int(min(frame.side.width, frame.side.height * 0.55))
            image = self.art.character(pygame, pose, size)
            if image is not None:
                rect = image.get_rect(midbottom=(frame.side.centerx, frame.side.bottom - 4))
                surface.blit(image, rect)
        title_surface = self.label(title, title_size, title_color, max_width=frame.main.width, role=FontRole.TITLE)
        surface.blit(title_surface, title_surface.get_rect(midtop=(frame.main.centerx, frame.main.top)))
        return _display(surface, alpha=False), frame.main.top + title_surface.get_height()

    def _draw_steps(self, surface: Any, pygame: Any, header: Any, current: int) -> None:
        count = len(STEP_LABELS)
        dot = max(20, min(30, header.height - 14))
        gap = max(14, min(30, dot))
        label = self.label(STEP_LABELS[current - 1], max(14, dot - 8), COCOA, role=FontRole.CONTROL)
        row_w = count * dot + (count - 1) * gap
        total = row_w + 12 + label.get_width()
        left = header.centerx - total // 2
        cy = header.centery + 1
        pygame.draw.line(surface, INK, (left + dot // 2, cy), (left + row_w - dot // 2, cy), 3)
        for index in range(count):
            number = index + 1
            x = left + index * (dot + gap)
            done, now = number < current, number == current
            fill = SUNSHINE if (done or now) else SURFACE
            size = dot if now else dot - 6
            body = self.painter.body(BodyShape.ROUND, (size, size), fill, contour_width=2 if not now else 3)
            rect = body.get_rect(center=(x + dot // 2, cy))
            surface.blit(body, rect)
            if done:
                _check_mark(pygame, surface, rect.inflate(-size // 3, -size // 3), INK)
            else:
                digit = self.label(str(number), max(11, size - 10), COCOA if now else HINT, role=FontRole.CONTROL)
                surface.blit(digit, digit.get_rect(center=rect.center))
        surface.blit(label, label.get_rect(midleft=(left + row_w + 12, cy)))

    # -- controls -------------------------------------------------------------

    def label(
        self,
        text: str,
        size: int,
        color: Rgb,
        *,
        max_width: int | None = None,
        role: FontRole = FontRole.CONTROL,
    ) -> Any:
        """Cached, translated single line that shrinks (never clips) to fit."""

        return self.painter.label(text, size, color, max_width=max_width, role=role, min_size=12)

    def pill(
        self,
        screen: Any,
        rect: Any,
        label: str,
        *,
        fill: Rgb = SURFACE,
        text_color: Rgb = COCOA,
        size: int = 22,
        enabled: bool = True,
    ) -> Any:
        """Kit pill button (ink contour, lip, highlight) with a fitted label."""

        if not enabled:
            fill = mix(fill, MUTED, 0.62)
            text_color = mix(COCOA, MUTED, 0.55)
        body = self.painter.body(BodyShape.PILL, rect.size, fill, lip=4)
        screen.blit(self.painter.presentable(body, screen), rect.topleft)
        image = self.label(label, size, text_color, max_width=rect.width - 28)
        screen.blit(image, image.get_rect(center=(rect.centerx, rect.centery - 2)))
        return rect

    def panel(self, screen: Any, rect: Any, fill: Rgb, *, contour: Rgb = INK, width: int = 2) -> None:
        """Rounded inset card/field body from the kit painter."""

        body = self.painter.body(
            BodyShape.PANEL, rect.size, fill, contour=contour, contour_width=width, highlight=False
        )
        screen.blit(self.painter.presentable(body, screen), rect.topleft)

    def tile(self, screen: Any, rect: Any, fill: Rgb, *, contour: Rgb = INK, width: int = 2) -> None:
        body = self.painter.body(
            BodyShape.TILE, rect.size, fill, contour=contour, contour_width=width, highlight=True
        )
        screen.blit(self.painter.presentable(body, screen), rect.topleft)

    def focus(self, screen: Any, rect: Any, *, shape: BodyShape = BodyShape.PANEL) -> None:
        radius = self.painter.radius_for(shape, rect.width, rect.height)
        ring = self.painter.focus_ring(rect.size, radius)
        pad = self.painter.FOCUS_PAD
        screen.blit(self.painter.presentable(ring, screen), (rect.left - pad, rect.top - pad))

    def toggle(self, screen: Any, rect: Any, value: bool) -> None:
        track = self.painter.body(BodyShape.PILL, rect.size, LEAF if value else MUTED, contour_width=2)
        screen.blit(self.painter.presentable(track, screen), rect.topleft)
        knob_d = rect.height - 8
        knob = self.painter.body(BodyShape.ROUND, (knob_d, knob_d), WHITE, contour_width=2)
        x = rect.right - 4 - knob_d if value else rect.left + 4
        screen.blit(self.painter.presentable(knob, screen), (x, rect.top + 4))

    def progress(self, screen: Any, pygame: Any, rect: Any, fraction: float, *, busy_tick: int | None = None) -> None:
        """Kit progress track; ``busy_tick`` adds a moving dot while work runs."""

        track = self.painter.body(BodyShape.PILL, rect.size, FIELD, contour_width=3, highlight=False)
        screen.blit(self.painter.presentable(track, screen), rect.topleft)
        inner = rect.inflate(-10, -10)
        filled = int(inner.width * max(0.0, min(1.0, fraction)))
        if filled >= inner.height:
            body = self.painter.body(BodyShape.PILL, (filled, inner.height), SUNSHINE, contour_width=2)
            screen.blit(self.painter.presentable(body, screen), inner.topleft)
        if busy_tick is not None:
            # A small dot travels along the unfilled track so a long blocking
            # step never looks frozen (the copy phase reports no fraction).
            span = max(1, inner.width - filled - inner.height)
            steps = 12
            position = busy_tick % (2 * steps)
            position = position if position <= steps else 2 * steps - position
            x = inner.left + filled + int(span * position / steps)
            dot = self.painter.body(BodyShape.ROUND, (inner.height, inner.height), mix(SUNSHINE, WHITE, 0.35), contour_width=2)
            screen.blit(self.painter.presentable(dot, screen), (x, inner.top))

    def disk_glyph(self, screen: Any, pygame: Any, rect: Any, *, danger: bool = False) -> None:
        """Kit-style internal-disk glyph (tile body, platter, read arm)."""

        self.tile(screen, rect, mix(SKY, WHITE, 0.2) if not danger else WARNING_FIELD)
        inner = rect.inflate(-rect.width // 4, -rect.height // 4)
        radius = min(inner.width, inner.height) // 2
        center = (inner.centerx - radius // 6, inner.centery)
        pygame.draw.circle(screen, mix(SKY, INK, 0.25), center, radius)
        pygame.draw.circle(screen, INK, center, radius, width=2)
        pygame.draw.circle(screen, SURFACE, center, max(2, radius // 4))
        pygame.draw.circle(screen, INK, center, max(2, radius // 4), width=2)
        arm_end = (inner.right - 2, inner.top + 4)
        pygame.draw.line(screen, INK, (center[0] + radius // 2, center[1] + radius // 3), arm_end, 4)
        pygame.draw.circle(screen, CORAL if danger else SUNSHINE, arm_end, 5)
        pygame.draw.circle(screen, INK, arm_end, 5, width=2)

    def signal(self, screen: Any, pygame: Any, rect: Any, level: int) -> None:
        """Four rising bars, ``level`` (0-4) of them filled."""

        bars = 4
        gap = 3
        bar_w = max(4, (rect.width - gap * (bars - 1)) // bars)
        for index in range(bars):
            h = int(rect.height * (index + 1) / bars)
            bar = pygame.Rect(rect.left + index * (bar_w + gap), rect.bottom - h, bar_w, h)
            pygame.draw.rect(screen, COCOA if index < level else MUTED, bar, border_radius=2)

    def check_mark(self, screen: Any, pygame: Any, rect: Any, color: Rgb = INK) -> None:
        _check_mark(pygame, screen, rect, color)


def _check_mark(pygame: Any, surface: Any, rect: Any, color: Rgb) -> None:
    points = [
        (rect.left, rect.top + rect.height * 0.55),
        (rect.left + rect.width * 0.38, rect.bottom),
        (rect.right, rect.top),
    ]
    pygame.draw.lines(surface, color, False, points, max(2, rect.width // 5))


def keycap(look: InstallerLook, screen: Any, rect: Any, character: str, size: int) -> None:
    """One big drawn keyboard key showing ``character`` (layout probe)."""

    look.tile(screen, rect, SURFACE, width=3)
    image = look.label(character, size, COCOA, role=FontRole.DISPLAY)
    screen.blit(image, image.get_rect(center=(rect.centerx, rect.centery - 3)))
