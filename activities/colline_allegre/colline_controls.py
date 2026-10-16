"""Shared control-kit wiring for Colline Allegre (ADR 0037).

* ``ProgressDots`` — the five courses of the set (display only);
* ``CourseRoad`` — a small road from the start flag to the finish arch with
  the friend waiting there; the mini buggy moves along it (display only);
* ``StarSlots`` — the course's three stars, filled as they are collected;
* the listen ``IconButton`` (Tito says the goal again; Enter / north button);
* the GO and BRAKE pedals: big round kit ``IconButton`` bodies (leaf / coral
  accents, shared ``icon.hud.go`` / ``icon.hud.stop`` glyphs). They are hold
  controls, so the app drives their ``pressed`` state and draws them; they
  are not focus targets (arrows / Space / D-pad / south button drive).

Every body is a kit body rendered once into the kit's bounded caches; the
only per-frame work is blitting and moving the road marker.
"""

from __future__ import annotations

from collections.abc import Callable

import pygame

from greia_platform.activity_controls import (
    BodyShape,
    ButtonRole,
    ControlKit,
    ControlLayer,
    ControlLayout,
    ControlPainter,
    ControlTheme,
    ControlVisualState,
    IconButton,
    KitControl,
    LabelTypography,
    ProgressDots,
    mix,
)

if __package__:
    from .colline_art import CollineArt
    from .colline_content import COURSES_PER_SET, STARS_PER_COURSE
    from .colline_layout import BRAKE_RECT, GO_RECT, LISTEN_SIZE, ROAD_WIDTH, STARS_WIDTH, TOP_BAR_HEIGHT
else:
    from colline_art import CollineArt
    from colline_content import COURSES_PER_SET, STARS_PER_COURSE
    from colline_layout import BRAKE_RECT, GO_RECT, LISTEN_SIZE, ROAD_WIDTH, STARS_WIDTH, TOP_BAR_HEIGHT

ROAD_MIN_WIDTH = 180
PEDAL_GLOW_PAD = 18


class CourseRoad(KitControl):
    """Start flag -> road -> finish arch + friend; a mini buggy shows progress."""

    focusable_by_default = False

    def __init__(self, painter: ControlPainter, control_id: str, rect: pygame.Rect, *, art: CollineArt, kit: ControlKit) -> None:
        super().__init__(painter, control_id, rect)
        self._art = art
        self._kit = kit
        self.friend = "leo"
        self.progress = 0.0

    def _content_key(self) -> tuple:
        return (self.friend,)

    def _track(self) -> tuple[int, int, int]:
        height = self._rect.height
        left = int(height * 0.62)
        right = self._rect.width - int(height * 1.25)
        return left, right, int(height * 0.62)

    def _build(self, state: ControlVisualState) -> pygame.Surface:
        painter = self._painter
        theme = painter.theme
        width, height = self._rect.size
        surface = painter.body(BodyShape.PILL, (width, height), theme.surface, contour_width=max(2, round(height * 0.045))).copy()
        left, right, y = self._track()
        road = mix(theme.ink, theme.surface, 0.55)
        pygame.draw.line(surface, road, (left, y), (right, y), max(4, height // 9))
        for x in range(left + 8, right - 4, 18):
            pygame.draw.line(surface, theme.surface, (x, y), (x + 7, y), 2)
        flag = self._art.flag(True)
        if flag is not None:
            small = pygame.transform.smoothscale(flag, (int(height * 0.8), int(height * 0.8)))
            surface.blit(small, small.get_rect(midbottom=(left - 2, y + int(height * 0.18))))
        arch = self._art.arch()
        if arch is not None:
            small = pygame.transform.smoothscale(arch, (int(height * 0.86), int(height * 0.86)))
            surface.blit(small, small.get_rect(midbottom=(right + 2, y + int(height * 0.2))))
        face = self._art.portrait(self.friend, int(height * 0.86))
        if face is not None:
            surface.blit(face, face.get_rect(midbottom=(width - int(height * 0.42), height - 1)))
        return surface

    def draw(self, target: object) -> None:
        if not self.visible:
            return
        assert isinstance(target, pygame.Surface)
        target.blit(self.render(), self._rect.topleft)
        marker = self._art.mini_buggy(int(self._rect.height * 0.62))
        if marker is not None:
            left, right, y = self._track()
            x = self._rect.left + left + (right - left) * max(0.0, min(1.0, self.progress))
            target.blit(marker, marker.get_rect(midbottom=(int(x), self._rect.top + y + 6)))


class StarSlots(KitControl):
    """The course's stars: filled shared stars for collected, outlines for the rest."""

    focusable_by_default = False

    def __init__(self, painter: ControlPainter, control_id: str, rect: pygame.Rect, *, kit: ControlKit, total: int) -> None:
        super().__init__(painter, control_id, rect)
        self._kit = kit
        self.total = total
        self.count = 0

    def _content_key(self) -> tuple:
        return (self.total, self.count)

    def _build(self, state: ControlVisualState) -> pygame.Surface:
        painter = self._painter
        width, height = self._rect.size
        surface = painter.body(BodyShape.PILL, (width, height), painter.theme.surface, contour_width=max(2, round(height * 0.045))).copy()
        size = int(height * 0.72)
        step = (width - height * 0.4) / self.total
        for index in range(self.total):
            star = self._kit.star(size, filled=index < self.count)
            cx = int(height * 0.2 + step * (index + 0.5))
            surface.blit(star, star.get_rect(center=(cx, height // 2)))
        return surface


class CollineControls:
    """Own the top bar, the pedals and one ``ControlLayer`` (listen + completion)."""

    def __init__(
        self, kit: ControlKit, art: CollineArt, typography: LabelTypography, *, on_listen: Callable[[], object]
    ) -> None:
        self._kit = kit
        self._art = art
        self.progress: ProgressDots = kit.progress_dots(
            "courses", pygame.Rect(0, 0, 200, TOP_BAR_HEIGHT), total=COURSES_PER_SET
        )
        self.road = CourseRoad(kit.painter, "road", pygame.Rect(0, 0, ROAD_WIDTH, TOP_BAR_HEIGHT), art=art, kit=kit)
        self.stars = StarSlots(kit.painter, "stars", pygame.Rect(0, 0, STARS_WIDTH, TOP_BAR_HEIGHT), kit=kit, total=STARS_PER_COURSE)
        self.listen: IconButton = kit.icon_button(
            "listen",
            pygame.Rect(0, 0, LISTEN_SIZE, LISTEN_SIZE),
            icon=kit.glyph("listen", int(LISTEN_SIZE * 0.62)),
            on_activate=on_listen,
        )
        # The pedals read by colour too: GO is leaf green, BRAKE is coral.
        self._go_kit = ControlKit(typography, ControlTheme.for_accent("leaf"), art=kit.art)
        self._brake_kit = ControlKit(typography, ControlTheme.for_accent("coral"), art=kit.art)
        self.go: IconButton = self._go_kit.icon_button(
            "go", GO_RECT, icon=self._go_kit.glyph("go", int(GO_RECT.width * 0.56)), role=ButtonRole.PRIMARY
        )
        self.brake: IconButton = self._brake_kit.icon_button(
            "brake", BRAKE_RECT, icon=self._brake_kit.glyph("stop", int(BRAKE_RECT.width * 0.44)), role=ButtonRole.PRIMARY
        )
        self.layer: ControlLayer = kit.layer((self.progress, self.road, self.stars, self.listen), layer_id="colline.controls")
        self._glow: pygame.Surface | None = None

    def place(self, layout: ControlLayout) -> None:
        """Lay the top bar out beside the protected Home region.

        Only the listen button is interactive, so only it is raised to the
        physical touch floor; the displays keep a compact height so the road
        stays long on small screens.
        """

        listen_size = layout.control_height(LISTEN_SIZE, maximum=84)
        height = min(TOP_BAR_HEIGHT, listen_size)
        bar = layout.top_bar(listen_size)
        top = bar.top + (listen_size - height) // 2
        dots_w = ProgressDots.preferred_width(self.progress.total, height)
        stars_w = int(STARS_WIDTH * height / TOP_BAR_HEIGHT)
        gap = layout.gap
        road_w = bar.width - dots_w - stars_w - listen_size - 3 * gap
        road_w = max(ROAD_MIN_WIDTH, min(int(ROAD_WIDTH * 1.15), road_w))
        x = bar.left
        self.progress.rect = pygame.Rect(x, top, dots_w, height)
        x += dots_w + gap
        self.road.rect = pygame.Rect(x, top, road_w, height)
        x += road_w + gap
        self.stars.rect = pygame.Rect(x, top, stars_w, height)
        self.listen.rect = pygame.Rect(bar.right - listen_size, bar.top, listen_size, listen_size)
        self.layer.invalidation.invalidate()

    def set_course(self, index: int, friend: str) -> None:
        self.progress.set_progress(index)
        self.road.friend = friend
        self.road.progress = 0.0
        self.stars.count = 0
        self.layer.invalidation.invalidate()

    def set_stars(self, count: int) -> None:
        self.stars.count = max(0, min(self.stars.total, count))
        self.layer.invalidation.invalidate()

    def set_playing(self, playing: bool) -> None:
        self.listen.enabled = playing
        for control in (self.progress, self.road, self.stars, self.listen):
            control.visible = playing or control is self.progress
        self.layer.invalidation.invalidate()

    def draw_pedals(self, surface: pygame.Surface, *, go: bool, brake: bool, go_hint: float, brake_hint: float) -> None:
        """Pedals with their held state; a pulsing gold ring when hinted (0..1)."""

        for button, held, hint in ((self.go, go, go_hint), (self.brake, brake, brake_hint)):
            if hint > 0.0:
                glow = self._pedal_glow()
                glow.set_alpha(int(255 * hint))
                surface.blit(glow, glow.get_rect(center=button.rect.center))
                glow.set_alpha(255)
            button.pressed = held
            button.draw(surface)

    def _pedal_glow(self) -> pygame.Surface:
        if self._glow is None:
            size = GO_RECT.width + 2 * PEDAL_GLOW_PAD
            ss = 2
            big = pygame.Surface((size * ss, size * ss), pygame.SRCALPHA)
            center = (size * ss // 2, size * ss // 2)
            pygame.draw.circle(big, (255, 214, 102, 130), center, size * ss // 2)
            pygame.draw.circle(big, (245, 158, 11), center, size * ss // 2 - 6 * ss, width=6 * ss)
            self._glow = pygame.transform.smoothscale(big, (size, size))
        return self._glow


__all__ = ["CollineControls", "CourseRoad", "StarSlots"]
