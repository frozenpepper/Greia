"""Frame composition for Colline Allegre (blits only).

``Camera`` follows the buggy (x locked, y smoothed and clamped), ``SceneMotion``
is the small bounded set of running animations (FX, mushroom squashes, flags
going up, the "slow down" sign glowing, the finish celebration) and
``DriverCast`` turns the shared ``CastFeedback`` grammar into the pose Tito
shows in his seat (cheer, think, point, surprised in the air). Every surface
comes prepared from ``CollineArt``; nothing here decodes, scales or renders
text, and nothing calls ``set_alpha`` per frame (fades are baked
``FadeSteps``; see ``greia_platform.pygame_blit``).
"""

from __future__ import annotations

from collections import deque
from collections.abc import Callable
from dataclasses import dataclass, field
import math

import pygame

from greia_platform.activity_feedback import CastFeedback, CastPose
from greia_platform.pygame_blit import FadeSteps

if __package__:
    from .colline_art import CollineArt
    from .colline_content import REFERENCE_HEIGHT, REFERENCE_WIDTH, STARS_PER_COURSE
    from .colline_layout import (
        CAMERA_ANCHOR_X,
        CAMERA_ANCHOR_Y,
        CAMERA_Y_FOLLOW,
        CAMERA_Y_MAX,
        CAMERA_Y_MIN,
        CHUNK_WIDTH,
        FRIEND_OFFSET,
        PICNIC_OFFSET,
    )
    from .colline_model import CourseRun
else:
    from colline_art import CollineArt
    from colline_content import REFERENCE_HEIGHT, REFERENCE_WIDTH, STARS_PER_COURSE
    from colline_layout import (
        CAMERA_ANCHOR_X,
        CAMERA_ANCHOR_Y,
        CAMERA_Y_FOLLOW,
        CAMERA_Y_MAX,
        CAMERA_Y_MIN,
        CHUNK_WIDTH,
        FRIEND_OFFSET,
        PICNIC_OFFSET,
    )
    from colline_model import CourseRun

FX_FRAME_SECONDS = 0.12
MAX_FX = 16
SQUASH_SECONDS = 0.35
FLAG_POP_SECONDS = 0.5
CELEBRATE_SECONDS = 3.4
RESULT_STAR_SIZE = 58
SURPRISED_AIR_SECONDS = 0.45
FLAG_BEHIND = 92


class Camera:
    """Keeps the buggy a third of the way in; follows hills smoothly."""

    def __init__(self) -> None:
        self.x = 0.0
        self.y = 0.0

    def snap(self, run: CourseRun) -> None:
        veh = run.vehicle
        self.x = self._clamp_x(run, veh.x - CAMERA_ANCHOR_X)
        self.y = max(CAMERA_Y_MIN, min(CAMERA_Y_MAX, veh.y - CAMERA_ANCHOR_Y))

    def follow(self, run: CourseRun, dt: float) -> None:
        veh = run.vehicle
        self.x = self._clamp_x(run, veh.x - CAMERA_ANCHOR_X)
        target = max(CAMERA_Y_MIN, min(CAMERA_Y_MAX, veh.y - CAMERA_ANCHOR_Y))
        self.y += (target - self.y) * min(1.0, CAMERA_Y_FOLLOW * dt)

    def settled(self, run: CourseRun) -> bool:
        """True once the smooth vertical follow has caught up (sub-pixel)."""

        target = max(CAMERA_Y_MIN, min(CAMERA_Y_MAX, run.vehicle.y - CAMERA_ANCHOR_Y))
        return abs(target - self.y) < 0.5

    @staticmethod
    def _clamp_x(run: CourseRun, x: float) -> float:
        return max(0.0, min(run.layout.length - REFERENCE_WIDTH, x))


class DriverCast:
    """Tito in the driver's seat: the shared cheer/think grammar plus point."""

    def __init__(self, feedback: CastFeedback, clock: Callable[[], float]) -> None:
        self.feedback = feedback
        self._clock = clock
        self._point_until = 0.0

    @property
    def pointing(self) -> bool:
        return self._clock() < self._point_until and self.feedback.pose is CastPose.IDLE

    @property
    def animating(self) -> bool:
        return self.feedback.animating or self.pointing

    def correct(self) -> None:
        self._point_until = 0.0
        self.feedback.correct()

    def try_again(self) -> None:
        self._point_until = 0.0
        self.feedback.try_again()

    def point(self, seconds: float) -> None:
        self.feedback.reset()
        self._point_until = self._clock() + seconds

    def reset(self) -> None:
        self._point_until = 0.0
        self.feedback.reset()

    def update(self) -> bool:
        changed = self.feedback.update()
        if self._point_until and self._clock() >= self._point_until:
            self._point_until = 0.0
            changed = True
        return changed

    def pose(self, run: CourseRun) -> str:
        pose = self.feedback.pose
        if pose is CastPose.CHEER:
            return "pose_cheer"
        if pose is CastPose.THINK:
            return "pose_think"
        if self.pointing:
            return "pose_point"
        veh = run.vehicle
        if run.tumbling or (veh.airborne and veh.air_time > SURPRISED_AIR_SECONDS):
            return "surprised"
        return "happy"


@dataclass(slots=True)
class SceneMotion:
    """Running animations, each bounded and pruned by time (world coordinates)."""

    fx: deque = field(default_factory=lambda: deque(maxlen=MAX_FX))
    squashes: dict[float, float] = field(default_factory=dict)
    flag_pops: dict[float, float] = field(default_factory=dict)
    sign_hint: tuple[int, float] | None = None  # (drop index, until)
    celebrate: float | None = None
    result_stars: int = 0

    def reset(self) -> None:
        self.fx.clear()
        self.squashes.clear()
        self.flag_pops.clear()
        self.sign_hint = None
        self.celebrate = None
        self.result_stars = 0

    def add_fx(self, name: str, world: tuple[float, float], start: float) -> None:
        self.fx.append((name, world, start))

    def prune(self, now: float) -> None:
        self.squashes = {k: v for k, v in self.squashes.items() if now - v < SQUASH_SECONDS}
        self.flag_pops = {k: v for k, v in self.flag_pops.items() if now - v < FLAG_POP_SECONDS}
        if self.sign_hint is not None and self.sign_hint[1] <= now:
            self.sign_hint = None
        while self.fx and now - self.fx[0][2] > 3 * FX_FRAME_SECONDS + 1.0:
            self.fx.popleft()

    def active(self, now: float) -> bool:
        return bool(
            self.fx or self.squashes or self.flag_pops or self.sign_hint is not None
            or (self.celebrate is not None and now - self.celebrate < CELEBRATE_SECONDS + 1.0)
        )


@dataclass(frozen=True, slots=True)
class SceneView:
    run: CourseRun
    friend: str
    camera_x: float
    camera_y: float


class CollineRenderer:
    """Draw one frame of the course from a ``SceneView``."""

    def __init__(self, art: CollineArt, driver: DriverCast) -> None:
        self._art = art
        self._driver = driver
        self._shadow = FadeSteps(self._make_shadow(), steps=8)

    @staticmethod
    def _make_shadow() -> pygame.Surface:
        shadow = pygame.Surface((150, 22), pygame.SRCALPHA)
        pygame.draw.ellipse(shadow, (106, 81, 71, 46), shadow.get_rect())
        return shadow

    def draw(self, surface: pygame.Surface, view: SceneView, motion: SceneMotion, now: float) -> None:
        run = view.run
        layout = run.layout
        cam_x, cam_y = view.camera_x, view.camera_y
        self._art.backdrop(layout.spec.biome).draw(surface, cam_x, cam_y)
        self._ground(surface, run, cam_x, cam_y)
        self._signs(surface, run, motion, cam_x, cam_y, now)
        self._finish(surface, view, motion, cam_x, cam_y, now)
        self._flags(surface, run, motion, cam_x, cam_y, now)
        self._mushrooms(surface, run, motion, cam_x, cam_y, now)
        self._stars(surface, run, cam_x, cam_y, now)
        self._vehicle(surface, run, cam_x, cam_y)
        self._fx(surface, motion, cam_x, cam_y, now)
        self._result(surface, run, motion, cam_x, cam_y, now)

    # -- world ---------------------------------------------------------------------------

    def _ground(self, surface: pygame.Surface, run: CourseRun, cam_x: float, cam_y: float) -> None:
        layout = run.layout
        first = max(0, int(cam_x // CHUNK_WIDTH))
        last = int((cam_x + REFERENCE_WIDTH) // CHUNK_WIDTH)
        for index in range(first, last + 1):
            chunk = self._art.chunk(layout, index)
            x = int(index * CHUNK_WIDTH - cam_x)
            y = int(chunk.top - cam_y)
            surface.blit(chunk.surface, (x, y))
            solid = y + chunk.surface.get_height()
            if solid < REFERENCE_HEIGHT:
                surface.fill(chunk.fill, pygame.Rect(x, solid, CHUNK_WIDTH, REFERENCE_HEIGHT - solid))

    def _signs(self, surface, run: CourseRun, motion: SceneMotion, cam_x, cam_y, now: float) -> None:
        if motion.sign_hint is None:
            return
        index = motion.sign_hint[0]
        if not 0 <= index < len(run.layout.drops):
            return
        drop = run.layout.drops[index]
        pulse = 0.55 + 0.45 * math.sin(now * 6.0)
        glow = self._art.sign_glow().at(pulse)
        if glow is None:
            return
        ground = run.layout.height(drop.sign_x)
        surface.blit(glow, glow.get_rect(midtop=(int(drop.sign_x - cam_x), int(ground - 128 - cam_y))))

    def _finish(self, surface, view: SceneView, motion: SceneMotion, cam_x, cam_y, now: float) -> None:
        run = view.run
        layout = run.layout
        fx = layout.finish_x
        if fx - cam_x > REFERENCE_WIDTH + 400:
            return
        arch = self._art.arch()
        if arch is not None:
            ground = layout.height(fx)
            surface.blit(arch, arch.get_rect(midbottom=(int(fx - cam_x), int(ground - cam_y + 10))))
        picnic = self._art.picnic()
        if picnic is not None:
            px = fx + PICNIC_OFFSET
            surface.blit(picnic, picnic.get_rect(midbottom=(int(px - cam_x), int(layout.height(px) - cam_y + 12))))
        friend_x = fx + FRIEND_OFFSET
        if run.finished:
            variant = "pose_cheer" if motion.celebrate is not None and now - motion.celebrate < CELEBRATE_SECONDS else "happy"
        elif run.vehicle.x > fx - 900:
            variant = "pose_wave"
        else:
            variant = "happy"
        friend = self._art.friend(view.friend, variant)
        if friend is not None:
            hop = 0
            if variant == "pose_cheer":
                hop = -int(abs(math.sin((now - (motion.celebrate or now)) * 5.0)) * 12)
            ground = layout.height(friend_x)
            surface.blit(friend, friend.get_rect(midbottom=(int(friend_x - cam_x), int(ground - cam_y + 12 + hop))))

    def _flags(self, surface, run: CourseRun, motion: SceneMotion, cam_x, cam_y, now: float) -> None:
        for flag_x in run.layout.checkpoints:
            # The pole stands just behind the spot where the buggy restarts.
            sx = flag_x - FLAG_BEHIND - cam_x
            if not -80 <= sx <= REFERENCE_WIDTH + 80:
                continue
            image = self._art.flag(flag_x in run.passed_flags)
            if image is None:
                continue
            ground = run.layout.height(flag_x - FLAG_BEHIND)
            dy = 0
            started = motion.flag_pops.get(flag_x)
            if started is not None:
                dy = -int(math.sin(math.pi * min(1.0, (now - started) / FLAG_POP_SECONDS)) * 14)
            surface.blit(image, image.get_rect(midbottom=(int(sx), int(ground - cam_y + 8 + dy))))

    def _mushrooms(self, surface, run: CourseRun, motion: SceneMotion, cam_x, cam_y, now: float) -> None:
        for pad_x in run.layout.pads:
            sx = pad_x - cam_x
            if not -80 <= sx <= REFERENCE_WIDTH + 80:
                continue
            squash = 0.0
            started = motion.squashes.get(pad_x)
            if started is not None:
                squash = math.sin(math.pi * min(1.0, (now - started) / SQUASH_SECONDS))
            image = self._art.mushroom(squash)
            if image is None:
                continue
            ground = run.layout.height(pad_x)
            surface.blit(image, image.get_rect(midbottom=(int(sx), int(ground - cam_y + 10))))

    def _stars(self, surface, run: CourseRun, cam_x, cam_y, now: float) -> None:
        image = self._art.star()
        if image is None:
            return
        for star in run.stars:
            if star.collected:
                continue
            sx = star.x - cam_x
            if not -40 <= sx <= REFERENCE_WIDTH + 40:
                continue
            bob = math.sin(now * 3.0 + star.x * 0.01) * 5.0
            surface.blit(image, image.get_rect(center=(int(sx), int(star.y - cam_y + bob))))

    def _vehicle(self, surface, run: CourseRun, cam_x, cam_y) -> None:
        veh = run.vehicle
        ground = run.layout.height(veh.x)
        gap = max(0.0, ground - (veh.y + 55.0))
        shadow = self._shadow.at(max(0.25, 1.0 - gap / 260.0)) if gap < 260 else None
        if shadow is not None:
            surface.blit(shadow, shadow.get_rect(center=(int(veh.x - cam_x), int(ground - cam_y + 4))))
        body = self._art.vehicle(self._driver.pose(run), veh.angle)
        surface.blit(body, body.get_rect(center=(int(veh.x - cam_x), int(veh.y - cam_y))))
        wheel = self._art.wheel(veh.wheel_spin)
        for hub in veh.wheels:
            surface.blit(wheel, wheel.get_rect(center=(int(hub.hub_x - cam_x), int(hub.hub_y - cam_y))))

    def _fx(self, surface, motion: SceneMotion, cam_x, cam_y, now: float) -> None:
        for name, world, start in motion.fx:
            if now < start:
                continue
            frames = self._art.fx_frames(name)
            if not frames:
                continue
            index = int((now - start) / FX_FRAME_SECONDS)
            if index >= len(frames) + 2:
                continue
            frame = frames[min(index, len(frames) - 1)]
            surface.blit(frame, frame.get_rect(center=(int(world[0] - cam_x), int(world[1] - cam_y))))

    def _result(self, surface, run: CourseRun, motion: SceneMotion, cam_x, cam_y, now: float) -> None:
        """After the finish: the course's three star slots pop in above the picnic."""

        if motion.celebrate is None:
            return
        layout = run.layout
        cx = layout.finish_x + PICNIC_OFFSET - cam_x
        cy = layout.height(layout.finish_x + PICNIC_OFFSET) - cam_y - 190
        gap = RESULT_STAR_SIZE + 12
        for slot in range(STARS_PER_COURSE):
            appear = motion.celebrate + 0.5 + 0.3 * slot
            if now < appear:
                continue
            filled = slot < motion.result_stars
            image = self._art.star(RESULT_STAR_SIZE) if filled else self._art.star_off(RESULT_STAR_SIZE)
            if image is None:
                continue
            t = min(1.0, (now - appear) / 0.25)
            lift = int((1.0 - t) * 18)
            x = int(cx + (slot - (STARS_PER_COURSE - 1) / 2) * gap)
            surface.blit(image, image.get_rect(center=(x, int(cy + lift))))


__all__ = [
    "CELEBRATE_SECONDS",
    "Camera",
    "CollineRenderer",
    "DriverCast",
    "SceneMotion",
    "SceneView",
]
