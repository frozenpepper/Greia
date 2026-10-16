"""Piccola Serra -- scene drawing and short-lived motion state.

``SceneView`` is what the child currently *sees* (it lags the model while a
moment plays: the can pours, then the soil darkens, then the plant grows).
``SerraMotion`` holds the bounded, time-stamped effects. ``SerraRenderer``
only blits prepared surfaces from ``SerraArt``; per-frame work is blits,
small alpha fades of sprite-sized surfaces and a few vector halos -- no
decoding, scaling or text rendering.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
import math

import pygame

from greia_platform.activity_feedback import CastFeedback, CastPose

if __package__:
    from .serra_art import SerraArt
    from .serra_content import Care, Need, Stage
    from .serra_layout import (
        BASKET_MIDBOTTOM,
        CAN_POUR_POS,
        CLOCK_POS,
        CLOTH_POS,
        PANE_RECT,
        PLANT_TOPLEFT,
        POT_POS,
        SAUCER_CENTER,
        SUN_CENTER,
        TITO_MIDBOTTOM,
        slot_rects,
    )
else:
    from serra_art import SerraArt
    from serra_content import Care, Need, Stage
    from serra_layout import (
        BASKET_MIDBOTTOM,
        CAN_POUR_POS,
        CLOCK_POS,
        CLOTH_POS,
        PANE_RECT,
        PLANT_TOPLEFT,
        POT_POS,
        SAUCER_CENTER,
        SUN_CENTER,
        TITO_MIDBOTTOM,
        slot_rects,
    )

MAX_FX = 8
MAX_FLIGHTS = 6
PLANT_FADE = 0.55
OVERLAY_FADE = 0.6
CLOTH_SECONDS = 0.8
POUR_SECONDS = 1.1
CLOCK_SECONDS = 1.3
SUN_SECONDS = 1.0
BASKET_SECONDS = 0.8
HALO_SECONDS = 2.2
FLIGHT_SECONDS = 0.7
BASKET_SIZE = 96
HARVEST_ITEM = 54


class Tween:
    """A value moving from ``start`` to ``end`` over ``seconds`` (ease in-out)."""

    __slots__ = ("start", "end", "begin", "seconds")

    def __init__(self, value: float = 0.0) -> None:
        self.start = self.end = float(value)
        self.begin = 0.0
        self.seconds = 0.0

    def to(self, value: float, now: float, seconds: float) -> None:
        self.start = self.value(now)
        self.end = float(value)
        self.begin = now
        self.seconds = max(0.0, seconds)

    def set(self, value: float) -> None:
        self.start = self.end = float(value)
        self.seconds = 0.0

    def value(self, now: float) -> float:
        if self.seconds <= 0 or now >= self.begin + self.seconds:
            return self.end
        t = max(0.0, (now - self.begin) / self.seconds)
        t = t * t * (3 - 2 * t)
        return self.start + (self.end - self.start) * t

    def moving(self, now: float) -> bool:
        return self.seconds > 0 and now < self.begin + self.seconds


@dataclass(slots=True)
class PlantView:
    """The plant picture on screen (stage + look) and its soil overlay."""

    plant_id: str | None = None
    stage: Stage = Stage.SEED
    variant: str = "default"
    overlay: Need | None = None


@dataclass(slots=True)
class SceneView:
    plant: PlantView = field(default_factory=PlantView)
    previous: PlantView | None = None
    plant_fade_start: float = -10.0
    overlay_previous: Need | None = None
    overlay_fade_start: float = -10.0
    cloth: Tween = field(default_factory=Tween)      # 0 = rolled up (sunny), 1 = down (shaded)
    basket: list[str] = field(default_factory=list)  # harvested plant ids
    board: bool = False
    order: tuple[Stage, ...] = ()
    placed: int = 0
    plant_hop: float = -10.0


@dataclass(slots=True)
class Flight:
    image: pygame.Surface
    start: tuple[float, float]
    end: tuple[float, float]
    begin: float
    seconds: float = FLIGHT_SECONDS
    arc: float = 120.0
    on_land: Callable[[], object] | None = None


@dataclass(slots=True)
class SerraMotion:
    """Bounded time-stamped effects (all cleared between plants/visits)."""

    fx: list[tuple[str, tuple[float, float], float, int]] = field(default_factory=list)
    flights: list[Flight] = field(default_factory=list)
    pour: float = -10.0
    pour_seconds: float = POUR_SECONDS
    clock: float = -10.0
    sun: float = -10.0
    basket_shake: float = -10.0
    symptom: tuple[Need, float] | None = None
    tool: tuple[str, float] | None = None
    slot_pulse: float = -10.0

    def add_fx(self, name: str, position: tuple[float, float], now: float, size: int) -> None:
        if len(self.fx) >= MAX_FX:
            self.fx.pop(0)
        self.fx.append((name, position, now, int(size)))

    def fly(self, flight: Flight) -> None:
        if len(self.flights) >= MAX_FLIGHTS:
            dropped = self.flights.pop(0)
            if dropped.on_land is not None:
                dropped.on_land()
        self.flights.append(flight)

    def land_due(self, now: float) -> None:
        """Finish flights that arrived (their callbacks update the scene)."""

        landed = [flight for flight in self.flights if now >= flight.begin + flight.seconds]
        for flight in landed:
            self.flights.remove(flight)
            if flight.on_land is not None:
                flight.on_land()

    def busy(self, now: float) -> bool:
        return bool(self.flights) or now < self.pour + self.pour_seconds or now < self.clock + CLOCK_SECONDS

    def clear(self) -> None:
        self.fx.clear()
        self.flights.clear()
        self.pour = self.clock = self.sun = self.basket_shake = self.slot_pulse = -10.0
        self.symptom = None
        self.tool = None


class TitoCast:
    """Tito in the greenhouse: shared cheer/think grammar plus a pointing pose."""

    def __init__(self, feedback: CastFeedback, point: pygame.Surface | None, clock: Callable[[], float]) -> None:
        self.feedback = feedback
        self._point = point
        self._clock = clock
        self._point_until = 0.0

    @property
    def pointing(self) -> bool:
        return self._point is not None and self._clock() < self._point_until

    @property
    def pose(self) -> str:
        if self.feedback.pose is CastPose.IDLE and self.pointing:
            return "point"
        return self.feedback.pose.value

    def point(self, seconds: float = 1.8) -> None:
        self.feedback.reset()
        self._point_until = self._clock() + seconds

    def correct(self) -> None:
        self._point_until = 0.0
        self.feedback.correct()

    def try_again(self) -> None:
        self._point_until = 0.0
        self.feedback.try_again()

    def reset(self) -> None:
        self._point_until = 0.0
        self.feedback.reset()

    def update(self) -> bool:
        return self.feedback.update() or self.pointing

    def draw(self, target: pygame.Surface, midbottom: tuple[int, int]) -> None:
        if self.feedback.pose is CastPose.IDLE and self.pointing and self._point is not None:
            target.blit(self._point, self._point.get_rect(midbottom=midbottom))
            return
        self.feedback.draw(target, midbottom)


def _blit_faded(surface: pygame.Surface, image: pygame.Surface, center: tuple[int, int], strength: float) -> None:
    """Blit a cached glow at ``strength`` (0..1) without allocating per frame."""

    alpha = max(0, min(255, int(255 * strength)))
    if alpha <= 0:
        return
    image.set_alpha(alpha)
    surface.blit(image, image.get_rect(center=center))
    image.set_alpha(255)


def symptom_anchor(need: Need) -> pygame.Rect:
    """Where a need shows (the halo of an idle/try-again hint)."""

    if need is Need.DARK:
        return PANE_RECT.inflate(30, 30)
    if need is Need.RIPE:
        return pygame.Rect(362, 70, 300, 240)
    return pygame.Rect(412, 300, 200, 84)


class SerraRenderer:
    """Draw the greenhouse, the plant, Tito, effects and the ordering board."""

    def __init__(self, art: SerraArt, cast: TitoCast) -> None:
        self.art = art
        self.cast = cast
        self.board_rect = pygame.Rect(330, 96, 670, 360)

    # -- frame --------------------------------------------------------------

    def draw(self, surface: pygame.Surface, view: SceneView, motion: SerraMotion, now: float) -> None:
        self._backdrop(surface, view, now)
        self._sun(surface, motion, now)
        self._cloth(surface, view, now)
        self._symptom_halo(surface, motion, now)
        self._basket(surface, view, motion, now)
        self.cast.draw(surface, TITO_MIDBOTTOM)
        if view.board:
            self._board(surface, view, motion, now)
        else:
            self._pot_and_plant(surface, view, now)
            self._saucer_water(surface, view)
            self._pour(surface, motion, now)
            self._clock(surface, motion, now)
        self._fx(surface, motion, now)
        self._flights(surface, motion, now)

    # -- greenhouse ---------------------------------------------------------------

    def _backdrop(self, surface: pygame.Surface, view: SceneView, now: float) -> None:
        shade = view.cloth.value(now)
        if shade <= 0.0:
            surface.blit(self.art.backdrop(True), (0, 0))
            return
        if shade >= 1.0:
            surface.blit(self.art.backdrop(False), (0, 0))
            return
        # Only while the cloth moves: cross-fade the two composed moods.
        surface.blit(self.art.backdrop(False), (0, 0))
        sunny = self.art.backdrop(True)
        sunny.set_alpha(int(255 * (1.0 - shade)))
        surface.blit(sunny, (0, 0))
        sunny.set_alpha(255)

    def _cloth(self, surface: pygame.Surface, view: SceneView, now: float) -> None:
        shade = view.cloth.value(now)
        cloth = self.art.cloth()
        if cloth is None or shade <= 0.0:
            return
        height = max(1, int(cloth.get_height() * shade))
        # Reveal from the hem upward so the hem always leads the cloth.
        area = pygame.Rect(0, cloth.get_height() - height, cloth.get_width(), height)
        surface.blit(cloth, CLOTH_POS, area)

    def _sun(self, surface: pygame.Surface, motion: SerraMotion, now: float) -> None:
        t = now - motion.sun
        if not 0 <= t < SUN_SECONDS:
            return
        pulse = math.sin(math.pi * t / SUN_SECONDS)
        _blit_faded(surface, self.art.halo((190, 190)), SUN_CENTER, pulse)

    def _symptom_halo(self, surface: pygame.Surface, motion: SerraMotion, now: float) -> None:
        if motion.symptom is None:
            return
        need, begin = motion.symptom
        t = now - begin
        if not 0 <= t < HALO_SECONDS:
            return
        rect = symptom_anchor(need)
        pulse = 0.55 + 0.45 * math.sin(t * 2 * math.pi / 0.9)
        _blit_faded(surface, self.art.halo(rect.size), rect.center, pulse)

    def _basket(self, surface: pygame.Surface, view: SceneView, motion: SerraMotion, now: float) -> None:
        basket = self.art.art.image("icon.hud.basket", BASKET_SIZE)
        midbottom = BASKET_MIDBOTTOM
        dx = 0
        t = now - motion.basket_shake
        if 0 <= t < BASKET_SECONDS:
            dx = int(6 * math.sin(t * 2 * math.pi * 3.5) * (1 - t / BASKET_SECONDS))
        # Harvest peeks out of the basket (up to three, fanned).
        offsets = ((-22, -54), (20, -58), (0, -66))
        for index, plant_id in enumerate(view.basket[-3:]):
            item = self.art.harvest(plant_id, HARVEST_ITEM)
            if item is not None:
                ox, oy = offsets[index]
                surface.blit(item, item.get_rect(center=(midbottom[0] + ox + dx, midbottom[1] + oy)))
        if basket is not None:
            surface.blit(basket, basket.get_rect(midbottom=(midbottom[0] + dx, midbottom[1])))

    # -- the pot ------------------------------------------------------------------------

    def _pot_and_plant(self, surface: pygame.Surface, view: SceneView, now: float) -> None:
        art = self.art
        back = art.pot(False)
        if back is not None:
            surface.blit(back, POT_POS)
        hop = 0
        t = now - view.plant_hop
        if 0 <= t < 0.45:
            hop = -int(10 * math.sin(math.pi * t / 0.45))
        fade = min(1.0, max(0.0, (now - view.plant_fade_start) / PLANT_FADE))
        if view.previous is not None and fade < 1.0:
            self._plant_image(surface, view.previous, 255, hop)
            self._plant_image(surface, view.plant, int(255 * fade), hop)
        else:
            self._plant_image(surface, view.plant, 255, hop)
        self._overlay(surface, view, now)
        front = art.pot(True)
        if front is not None:
            surface.blit(front, POT_POS)

    def _plant_image(self, surface: pygame.Surface, plant: PlantView, alpha: int, hop: int) -> None:
        if plant.plant_id is None or alpha <= 0:
            return
        image = self.art.plant(plant.plant_id, plant.stage, plant.variant)
        if image is None:
            return
        position = (PLANT_TOPLEFT[0], PLANT_TOPLEFT[1] + hop)
        if alpha >= 255:
            surface.blit(image, position)
            return
        image.set_alpha(alpha)
        surface.blit(image, position)
        image.set_alpha(255)

    def _overlay(self, surface: pygame.Surface, view: SceneView, now: float) -> None:
        fade = min(1.0, max(0.0, (now - view.overlay_fade_start) / OVERLAY_FADE))
        if view.overlay_previous is not None and fade < 1.0:
            self._overlay_image(surface, view.overlay_previous, int(255 * (1 - fade)))
        if view.plant.overlay is not None:
            self._overlay_image(surface, view.plant.overlay, int(255 * fade))

    def _overlay_image(self, surface: pygame.Surface, need: Need, alpha: int) -> None:
        image = self.art.overlay(need)
        if image is None or alpha <= 0:
            return
        if alpha >= 255:
            surface.blit(image, PLANT_TOPLEFT)
            return
        image.set_alpha(alpha)
        surface.blit(image, PLANT_TOPLEFT)
        image.set_alpha(255)

    def _saucer_water(self, surface: pygame.Surface, view: SceneView) -> None:
        """Too much water also spills into the saucer (flat ocean ellipse)."""

        if view.plant.overlay is not Need.SOGGY:
            return
        rect = pygame.Rect(0, 0, 176, 14)
        rect.center = (SAUCER_CENTER[0], SAUCER_CENTER[1] - 2)
        pygame.draw.ellipse(surface, (146, 189, 232), rect)
        pygame.draw.ellipse(surface, (74, 125, 179), rect, 2)

    def _pour(self, surface: pygame.Surface, motion: SerraMotion, now: float) -> None:
        t = now - motion.pour
        if not 0 <= t < motion.pour_seconds:
            return
        can = self.art.tilted_can(150)
        if can is None:
            return
        lift = int(8 * math.sin(min(1.0, t / 0.25) * math.pi / 2))
        surface.blit(can, can.get_rect(center=(CAN_POUR_POS[0], CAN_POUR_POS[1] - lift)))
        drop = self.art.drop(22)
        if drop is None:
            return
        spout = (CAN_POUR_POS[0] - 74, CAN_POUR_POS[1] + 36)
        for index in range(5):
            phase = (t * 2.2 + index / 5) % 1.0
            x = spout[0] - 22 * phase + (index % 2) * 10 - 5
            y = spout[1] + 130 * phase
            surface.blit(drop, drop.get_rect(center=(int(x), int(y))))

    def _clock(self, surface: pygame.Surface, motion: SerraMotion, now: float) -> None:
        t = now - motion.clock
        if not 0 <= t < CLOCK_SECONDS:
            return
        clock = self.art.care_icon(Care.WAIT, 120)
        if clock is None:
            return
        hop = -int(8 * abs(math.sin(t * math.pi * 3)))
        surface.blit(clock, clock.get_rect(center=(CLOCK_POS[0], CLOCK_POS[1] + hop)))

    # -- effects -------------------------------------------------------------------------

    def _fx(self, surface: pygame.Surface, motion: SerraMotion, now: float) -> None:
        alive = []
        for name, position, begin, size in motion.fx:
            frames = self.art.fx_frames(name, size)
            if not frames:
                continue
            elapsed = now - begin
            index = int(elapsed / 0.16)
            if index >= len(frames):
                continue
            alive.append((name, position, begin, size))
            frame = frames[index]
            surface.blit(frame, frame.get_rect(center=(int(position[0]), int(position[1]))))
        motion.fx[:] = alive

    def _flights(self, surface: pygame.Surface, motion: SerraMotion, now: float) -> None:
        for flight in motion.flights:
            t = min(1.0, max(0.0, (now - flight.begin) / flight.seconds))
            x = flight.start[0] + (flight.end[0] - flight.start[0]) * t
            y = flight.start[1] + (flight.end[1] - flight.start[1]) * t - flight.arc * math.sin(math.pi * t)
            surface.blit(flight.image, flight.image.get_rect(center=(int(x), int(y))))

    # -- ordering board --------------------------------------------------------------------

    def board_slots(self, board: pygame.Rect, count: int) -> list[pygame.Rect]:
        return slot_rects(board, count)

    def _board(self, surface: pygame.Surface, view: SceneView, motion: SerraMotion, now: float) -> None:
        slots = slot_rects(self.board_rect, len(view.order))
        if not slots:
            return
        panel = slots[0].unionall(slots[1:]).inflate(56, 56)
        surface.blit(self.art.board(panel.size), panel.topleft)
        arrow = self.art.arrow(26)
        for index, rect in enumerate(slots):
            filled = index < view.placed
            surface.blit(self.art.slot(rect.size, filled=filled), rect.topleft)
            if filled and view.plant.plant_id is not None:
                picture = self.art.stage_card(view.plant.plant_id, view.order[index], int(rect.width * 0.74))
                if picture is not None:
                    surface.blit(picture, picture.get_rect(center=(rect.centerx, rect.centery - 2)))
            elif index == view.placed:
                t = now - motion.slot_pulse
                if 0 <= t < HALO_SECONDS:
                    pulse = 0.55 + 0.45 * math.sin(t * 2 * math.pi / 0.9)
                    _blit_faded(surface, self.art.halo((rect.width + 24, rect.height + 24)), rect.center, pulse)
            if index < len(slots) - 1:
                surface.blit(arrow, arrow.get_rect(center=(rect.right + 17, rect.centery)))


__all__ = [
    "Flight",
    "PlantView",
    "SceneView",
    "SerraMotion",
    "SerraRenderer",
    "TitoCast",
    "Tween",
    "symptom_anchor",
]
