"""Stage presentation for Teatrino delle Fiabe.

Pure drawing over prepared art: the composed stage background, the rod
puppets (picking the cast variant that matches each puppet's moment), the
curtains and valance in front, the playboard tray, the record ring, the
"3-2-1" curtain ritual and the sheet backdrops. Nothing here decodes, scales
or renders text per frame; posters are composed on demand and cached by the
app.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
import math

import pygame

from greia_platform.activity_controls import BodyShape, ControlKit, mix
from greia_platform.pygame_png import PygamePngError, decode_png_surface
from greia_platform.ui_core import BoundedCache

if __package__:
    from .teatrino_art import TeatrinoArt, draw_rod
    from .teatrino_content import DEFAULT_SCENE, PUPPETS_BY_ID, REFERENCE_HEIGHT, REFERENCE_WIDTH, SCENE_IDS
    from .teatrino_layout import FOOTLIGHTS_BOTTOM, TheatreLayout
    from .teatrino_model import Puppet, Stage
else:
    from teatrino_art import TeatrinoArt, draw_rod
    from teatrino_content import DEFAULT_SCENE, PUPPETS_BY_ID, REFERENCE_HEIGHT, REFERENCE_WIDTH, SCENE_IDS
    from teatrino_layout import FOOTLIGHTS_BOTTOM, TheatreLayout
    from teatrino_model import Puppet, Stage

APRON = (122, 58, 69)
REC_RED = (226, 76, 70)
GOLD = (255, 194, 52)
INK = (75, 55, 47)
DIM = (30, 22, 36, 170)
PANEL_FILL = (255, 251, 240)
# Posters always use the 1024x600 stage geometry (floor lifted to the tray).
POSTER_FLOOR_DY = 496 - FOOTLIGHTS_BOTTOM


def puppet_variant(puppet: Puppet) -> str | None:
    """The cast variant for this instant (non-cast puppets ignore it)."""

    if puppet.held:
        return "pose_wave"
    if puppet.reaction:
        return puppet.reaction
    if puppet.jumping:
        return "pose_cheer"
    if puppet.bow_timer > 0.0:
        return "happy"
    if puppet.mouth_open:
        return "surprised"
    return None


class TheatreRenderer:
    """Draw the stage screen and the sheet backdrops."""

    def __init__(self, art: TeatrinoArt, kit: ControlKit, layout: TheatreLayout, *, clock: Callable[[], float]) -> None:
        self.art = art
        self.kit = kit
        self.layout = layout
        self._clock = clock
        self._dim: pygame.Surface | None = None

    def relayout(self, layout: TheatreLayout) -> None:
        self.layout = layout

    # -- stage ---------------------------------------------------------------

    def draw_puppet(self, target: pygame.Surface, puppet: Puppet, *, rod_bottom: int) -> pygame.Rect | None:
        look = self.art.look(puppet.puppet_id)
        if look is None:
            return None
        image, (ax, ay) = look.posed(puppet_variant(puppet), puppet.tilt, puppet.flip)
        x = int(puppet.x)
        y = int(puppet.y - puppet.jump_offset() + puppet.talk_offset() + puppet.bow_dip() - (8 if puppet.held else 0))
        rod_top_y = y + (look.rod_y - look.anchor[1])
        if puppet.held:
            halo = self.art.halo((look.half_width * 2 + 60, look.half_height * 2 + 56))
            target.blit(halo, halo.get_rect(center=(x, y)))
        draw_rod(target, (x, rod_top_y), rod_bottom)
        rect = image.get_rect(topleft=(x - ax, y - ay))
        target.blit(image, rect)
        return rect

    def draw_stage(
        self,
        target: pygame.Surface,
        background: pygame.Surface,
        stage: Stage,
        *,
        curtain: float = 0.0,
    ) -> None:
        """Background, puppets, the main curtain (``curtain`` 0 open .. 1 closed), front."""

        target.blit(background, (0, 0))
        rod_bottom = self.layout.tray.top + 6
        for puppet in stage.puppets:
            self.draw_puppet(target, puppet, rod_bottom=rod_bottom)
        if curtain > 0.0:
            self.draw_curtain(target, curtain)
        for piece, position in self.art.front_pieces():
            target.blit(piece, position)
        pygame.draw.rect(target, APRON, self.layout.tray)

    def draw_curtain(self, target: pygame.Surface, closed: float) -> None:
        left, right = self.art.curtain_halves()
        width = left.get_width()
        closed = max(0.0, min(1.0, closed))
        # Ease so the curtain glides in and settles softly.
        eased = 1.0 - (1.0 - closed) ** 2
        offset = int(width * (1.0 - eased))
        target.blit(left, (-offset, 0))
        target.blit(right, (REFERENCE_WIDTH - width + offset, 0))

    def draw_countdown(self, target: pygame.Surface, remaining: int, beat: float) -> None:
        """Three gold lamps on the closed curtain; one goes out per beat."""

        cy = (self.layout.bounds.top + self.layout.bounds.bottom) // 2
        spacing = 92
        for index in range(3):
            lit = index < remaining
            cx = REFERENCE_WIDTH // 2 + (index - 1) * spacing
            radius = 30
            if lit and index == remaining - 1:
                radius = int(30 + 8 * math.sin(math.pi * min(1.0, beat)))
            pygame.draw.circle(target, INK, (cx, int(cy)), radius + 4)
            if not lit:
                # A lamp that has gone out: a dim glass bulb in its gold socket.
                pygame.draw.circle(target, GOLD, (cx, int(cy)), radius)
                pygame.draw.circle(target, mix(APRON, INK, 0.25), (cx, int(cy)), radius - 7)
                continue
            pygame.draw.circle(target, GOLD, (cx, int(cy)), radius)
            if lit:
                pygame.draw.circle(target, (255, 240, 190), (cx - radius // 3, int(cy) - radius // 3), max(4, radius // 4))

    def draw_rec_ring(self, target: pygame.Surface, rect: pygame.Rect, progress: float, level: float) -> None:
        """Time ring around the stop button plus a soft voice-level glow."""

        face = pygame.Rect(rect.x, rect.y, rect.width, rect.height - max(2, round(rect.height * 0.07)))
        ring = face.inflate(14, 14)
        level = max(0.0, min(1.0, level))
        if level > 0.05:
            glow = ring.inflate(int(6 + 18 * level), int(6 + 18 * level))
            pygame.draw.rect(target, mix(REC_RED, (255, 255, 255), 0.55), glow, width=max(3, int(4 + 6 * level)), border_radius=glow.height // 3)
        pygame.draw.rect(target, INK, ring, width=7, border_radius=ring.height // 3)
        pygame.draw.rect(target, mix(REC_RED, (255, 255, 255), 0.7), ring.inflate(-2, -2), width=3, border_radius=ring.height // 3)
        # The elapsed part of the ring, clockwise from the top centre.
        progress = max(0.0, min(1.0, progress))
        if progress > 0.0:
            _ring_progress(target, ring, progress, REC_RED, 6)

    def draw_hint(self, target: pygame.Surface, rect: pygame.Rect) -> None:
        """Gentle golden pulse behind a control the child might try next."""

        phase = 0.5 + 0.5 * math.sin(self._clock() * 5.0)
        halo = self.art.halo((rect.width + 40, rect.height + 40))
        halo.set_alpha(int(110 + 145 * phase))
        target.blit(halo, halo.get_rect(center=rect.center))

    # -- sheets ----------------------------------------------------------------

    def draw_dim(self, target: pygame.Surface) -> None:
        if self._dim is None:
            self._dim = pygame.Surface((REFERENCE_WIDTH, REFERENCE_HEIGHT), pygame.SRCALPHA)
            self._dim.fill(DIM)
        target.blit(self._dim, (0, 0))

    def draw_panel(self, target: pygame.Surface, panel: pygame.Rect) -> None:
        body = self.kit.painter.body(BodyShape.PANEL, panel.size, PANEL_FILL, lip=5, contour_width=4, highlight=False)
        target.blit(body, panel.topleft)

    def draw_picture(self, target: pygame.Surface, picture: pygame.Surface | None, rect: pygame.Rect) -> None:
        """A poster in a gold stage frame."""

        frame = rect.inflate(16, 16)
        pygame.draw.rect(target, INK, frame.inflate(6, 6), border_radius=18)
        pygame.draw.rect(target, GOLD, frame, border_radius=16)
        if picture is not None:
            target.blit(picture, picture.get_rect(center=rect.center))
        pygame.draw.rect(target, INK, rect.inflate(4, 4), width=3, border_radius=6)

    # -- posters -----------------------------------------------------------------

    def poster(
        self,
        background: pygame.Surface,
        line_up: Sequence[dict],
        size: tuple[int, int],
    ) -> pygame.Surface:
        """The stage with its puppets as one picture at ``size``.

        ``background`` has the floor in its natural place (``floor_dy`` 0);
        puppets recorded on the live stage (floor lifted to the tray) are
        shifted down by the same amount, and the apron is drawn over their
        rods, exactly like a real theatre seen from the audience.
        """

        canvas = background.copy()
        shift = -POSTER_FLOOR_DY
        for item in line_up:
            puppet = Puppet(str(item.get("id", "")), float(item.get("x", 512)), float(item.get("y", 300)) + shift)
            puppet.flip = bool(item.get("flip", False))
            self.draw_puppet(canvas, puppet, rod_bottom=REFERENCE_HEIGHT)
        apron = self.art.apron()
        if apron is not None:
            canvas.blit(apron[0], apron[1])
        for piece, position in self.art.front_pieces():
            canvas.blit(piece, position)
        if canvas.get_size() == tuple(size):
            return canvas
        return pygame.transform.smoothscale(canvas, (int(size[0]), int(size[1])))


POSTER_ASPECT = REFERENCE_WIDTH / REFERENCE_HEIGHT
# Cards and the curtain call frame the stage opening (same aspect as the
# stage) so the puppets read larger; a shared poster keeps the whole stage.
POSTER_CROP = pygame.Rect(100, 40, 824, 483)


class PosterStudio:
    """Compose show posters (library cards, curtain call, My Creations).

    A poster is drawn from the show's small index entry (scene, custom
    backdrop digest and the puppets' line-up as the curtain closed), never
    from the large frame file. Posters are cached per show and size
    (bounded); the full-size share copy is never cached.
    """

    def __init__(self, art: TeatrinoArt, renderer: "TheatreRenderer", repository, *, limit: int = 18) -> None:
        self.art = art
        self.renderer = renderer
        self.repository = repository
        self._cache: BoundedCache[tuple, pygame.Surface] = BoundedCache(limit)

    def for_show(self, show_item: dict, size: tuple[int, int], *, cache: bool = True, crop: bool = True) -> pygame.Surface:
        key = (show_item.get("id"), int(size[0]), int(size[1]), crop)
        if cache:
            cached = self._cache.get(key)
            if cached is not None:
                return cached
        custom = None
        digest = ""
        if show_item.get("has_custom_backdrop"):
            custom = decode_backdrop(self.repository.load_show_backdrop(str(show_item.get("id"))))
            digest = str(show_item.get("backdrop_sha256") or "")
        scene = show_item.get("backdrop")
        line_up = show_item.get("poster")
        if not isinstance(line_up, list) or not line_up:
            actors = [a for a in show_item.get("actors", []) if a in PUPPETS_BY_ID][:6]
            count = max(1, len(actors))
            line_up = [
                {"id": actor, "x": 300 + 424 * (index + 0.5) / count, "y": 330}
                for index, actor in enumerate(actors)
            ]
        scene_id = scene if scene in SCENE_IDS else DEFAULT_SCENE
        if crop:
            full = self.stage(scene_id, custom, digest, line_up, (REFERENCE_WIDTH, REFERENCE_HEIGHT))
            poster = pygame.transform.smoothscale(full.subsurface(POSTER_CROP), (int(size[0]), int(size[1])))
        else:
            poster = self.stage(scene_id, custom, digest, line_up, size)
        if cache:
            self._cache[key] = poster
        return poster

    def stage(
        self,
        scene_id: str,
        custom: pygame.Surface | None,
        custom_key: str,
        line_up: Sequence[dict],
        size: tuple[int, int],
    ) -> pygame.Surface:
        background = self.art.stage_background(scene_id, custom, custom_key=custom_key, floor_dy=0)
        return self.renderer.poster(background, line_up, size)

    def clear(self) -> None:
        self._cache.clear()


def decode_backdrop(payload: bytes | None) -> pygame.Surface | None:
    """A saved/imported PNG at stage size, or None when it cannot be used."""

    if payload is None:
        return None
    try:
        return decode_png_surface(payload, (REFERENCE_WIDTH, REFERENCE_HEIGHT))
    except (PygamePngError, RuntimeError, ValueError, OSError):
        return None


def picture_size(card: pygame.Rect, fill: float = 0.84) -> tuple[int, int]:
    """Largest stage-shaped picture that sits inside a kit tile's face."""

    lip = max(2, round(card.height * 0.07))
    width = int(card.width * fill)
    height = int((card.height - lip) * fill)
    if width / max(1, height) > POSTER_ASPECT:
        width = int(height * POSTER_ASPECT)
    else:
        height = int(width / POSTER_ASPECT)
    return (max(8, width), max(8, height))


def rounded(surface: pygame.Surface) -> pygame.Surface:
    """Soft-cornered, ink-outlined copy of a picture (built once per use)."""

    width, height = surface.get_size()
    radius = max(4, min(width, height) // 6)
    result = pygame.Surface((width, height), pygame.SRCALPHA)
    result.blit(surface, (0, 0))
    mask = pygame.Surface((width, height), pygame.SRCALPHA)
    pygame.draw.rect(mask, (255, 255, 255, 255), mask.get_rect(), border_radius=radius)
    result.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
    pygame.draw.rect(result, INK, result.get_rect(), width=3, border_radius=radius)
    return result


def _ring_progress(target: pygame.Surface, rect: pygame.Rect, progress: float, color, width: int) -> None:
    """Draw ``progress`` of a rounded-rect outline as dots (cheap, no arcs)."""

    perimeter_steps = 72
    count = int(perimeter_steps * progress)
    cx, cy = rect.center
    rx, ry = rect.width / 2, rect.height / 2
    for step in range(count + 1):
        angle = -math.pi / 2 + 2 * math.pi * step / perimeter_steps
        # Superellipse point: follows a rounded rectangle closely.
        c, s = math.cos(angle), math.sin(angle)
        px = cx + rx * math.copysign(abs(c) ** 0.5, c)
        py = cy + ry * math.copysign(abs(s) ** 0.5, s)
        pygame.draw.circle(target, color, (int(px), int(py)), width // 2 + 1)


__all__ = [
    "POSTER_ASPECT",
    "POSTER_FLOOR_DY",
    "PosterStudio",
    "TheatreRenderer",
    "decode_backdrop",
    "picture_size",
    "puppet_variant",
    "rounded",
]
