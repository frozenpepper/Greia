"""Bounded ambient animation for the child's Collection Home.

``HomeAnimator`` is the single owner of everything that moves on Home: the
child's cast greeter (greeting, blinking, tap reactions, falling asleep), up
to three falling apples from the meadow tree, a sun sparkle burst and the two
slowly drifting sky clouds. It is deliberately *not* an animation framework
(ADR 0018): it knows exactly these few effects, holds at most
``MAX_EFFECTS`` of them, and owns every pre-scaled sprite they use.

Performance contract (Atom N270 reference floor):

* sprites are fetched through the shared visual cache once per layout and
  held here; a tick never constructs, scales, converts or alpha-modifies a
  surface;
* a tick only reports the small screen rectangles whose pixels changed; the
  Shell restores those rects from its cached Home frame, redraws the sprites
  clipped to them and calls ``pygame.display.update(rects)``;
* frames are paced at most ``EFFECT_FPS`` while something moves and
  ``DRIFT_FPS`` while only clouds drift;
* the *awake window* is ``AWAKE_SECONDS`` after the last child input. After it
  every effect has stopped and :meth:`seconds_until_due` returns ``None``: the
  Shell loop is back to zero redraws. The one exception is the single
  ``sleepy`` pose swap ``SLEEP_AFTER_SECONDS`` after the last input.

Public seam for other Shell presentation (for example the achievement
ceremony): :meth:`react` makes the greeter react (``"surprised"``,
``"happy"``, ``"cheer"``, ``"wave"``) without speech and without granting
anything. Interactions here never grant stars or badges.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
import math
from pathlib import Path
from typing import Any, Callable, Iterable, Sequence

from greia_platform.responsive_layout import UiRect

from .home_scenery import (
    APPLE_SIZE,
    CLOUD_PUFF_SCALE,
    DUST_SIZE,
    SPARKLE_SIZE,
    CloudSpec,
    HomeSceneryLayout,
)


# (surface, x, y). Plain tuples: comparing two frames' item lists is how the
# animator finds the pixels that changed.
DrawItem = tuple[Any, int, int]
SpriteLoader = Callable[[str, str, tuple[int, int]], Any]

EFFECT_FPS = 24
DRIFT_FPS = 12
AWAKE_SECONDS = 20.0
SLEEP_AFTER_SECONDS = 60.0
MAX_EFFECTS = 6
MAX_APPLES = 3

_REST_POSE = "default"
_GREETER_POSES = ("default", "blink", "happy", "surprised", "sleepy", "pose_wave", "pose_cheer")
_BLINK_PERIOD = 4.8
_BLINK_SECONDS = 0.18
_HOP_SECONDS = 0.5
_HOP_PIXELS = 28


@dataclass(frozen=True, slots=True)
class GreeterReaction:
    """A short pose sequence with an optional parabolic hop.

    ``poses`` are ``(start_offset_seconds, pose)`` in ascending order; the
    reaction ends after ``duration`` and the greeter returns to rest.
    """

    poses: tuple[tuple[float, str], ...]
    duration: float
    hop: bool = False

    def pose_at(self, elapsed: float) -> str:
        pose = self.poses[0][1]
        for offset, candidate in self.poses:
            if elapsed >= offset:
                pose = candidate
        return pose

    def next_pose_change(self, elapsed: float) -> float:
        """Seconds from reaction start to the next pose swap or the end."""

        for offset, _ in self.poses:
            if offset > elapsed:
                return offset
        return self.duration


# Named reactions. ``tap_*`` alternate between greeter taps.
REACTIONS: dict[str, GreeterReaction] = {
    "greet": GreeterReaction(((0.0, "pose_cheer"),), 2.4),
    "wake": GreeterReaction(((0.0, "surprised"), (0.45, "pose_cheer")), 1.5),
    "tap_wave": GreeterReaction(
        ((0.0, "surprised"), (0.12, "pose_wave"), (0.5, "pose_cheer")), 1.3, hop=True
    ),
    "tap_happy": GreeterReaction(
        ((0.0, "surprised"), (0.12, "happy"), (0.5, "pose_cheer")), 1.3, hop=True
    ),
    "glance": GreeterReaction(((0.0, "surprised"),), 0.4),
    "surprised": GreeterReaction(((0.0, "surprised"),), 0.6),
    "happy": GreeterReaction(((0.0, "happy"),), 0.9),
    "cheer": GreeterReaction(((0.0, "happy"), (0.15, "pose_cheer")), 1.5, hop=True),
    "wave": GreeterReaction(((0.0, "pose_wave"),), 1.2),
}
PUBLIC_REACTIONS = frozenset({"surprised", "happy", "cheer", "wave"})


class VoiceRateLimiter:
    """At most ``max_per_window`` clips per sliding window, ``cooldown`` apart."""

    def __init__(
        self, *, cooldown: float = 3.0, window: float = 60.0, max_per_window: int = 4
    ) -> None:
        self.cooldown = cooldown
        self.window = window
        self._played: deque[float] = deque(maxlen=max_per_window)

    def allows(self, now: float) -> bool:
        if self._played and now - self._played[-1] < self.cooldown:
            return False
        if len(self._played) == self._played.maxlen and now - self._played[0] < self.window:
            return False
        return True

    def record(self, now: float) -> None:
        self._played.append(now)


class HomeGreeterVoice:
    """Speech for greeter taps using only accepted shared character takes.

    The first tap on a character in this Shell process plays that
    character's accepted self-introduction; later taps rotate the accepted
    ``praise.general`` / ``ready.go`` takes. Playback goes through the
    launcher's single spoken-label channel and never interrupts a clip that is
    already playing. System volume/mute apply because the same mixer output is
    used. No TTS, no new recordings.
    """

    CUES = ("praise.general", "ready.go")

    def __init__(
        self,
        project_root: Path,
        player: Any,
        locale: Callable[[], str],
        *,
        limiter: VoiceRateLimiter | None = None,
    ) -> None:
        self._root = Path(project_root)
        self._player = player
        self._locale = locale
        self.limiter = limiter if limiter is not None else VoiceRateLimiter()
        self._introduced: set[str] = set()
        self._turn = 0

    def _next_clip(self, character: str) -> Path | None:
        from greia_platform.localization import (
            LocalizationError,
            shared_character_audio_path,
            shared_character_intro_path,
        )

        try:
            locale = self._locale()
            if character not in self._introduced:
                self._introduced.add(character)
                intro = shared_character_intro_path(self._root, character, locale)
                if intro is not None:
                    return intro
            cue = self.CUES[self._turn % len(self.CUES)]
            take = self._turn // len(self.CUES)
            self._turn += 1
            return shared_character_audio_path(self._root, character, cue, locale, take=take)
        except (LocalizationError, OSError, ValueError):
            return None

    def speak(self, character: str, now: float, pygame: Any) -> bool:
        if not self.limiter.allows(now):
            return False
        is_busy = getattr(self._player, "is_busy", None)
        if is_busy is not None and is_busy():
            return False
        clip = self._next_clip(character)
        if clip is None:
            return False
        if self._player.play_if_idle(clip, pygame):
            self.limiter.record(now)
            return True
        return False


class _TimedEffect:
    """Base for short, self-retiring scenery effects (start time + script)."""

    duration = 0.0

    def __init__(self, started: float) -> None:
        self.started = started

    def finished(self, now: float) -> bool:
        return now - self.started >= self.duration

    def items(self, now: float, out: list[DrawItem]) -> None:  # pragma: no cover - abstract
        raise NotImplementedError

    def next_change(self, now: float) -> float:  # pragma: no cover - abstract
        raise NotImplementedError


class FallingApple(_TimedEffect):
    """An apple drops from the tree, puffs dust, rests, then sparkles away."""

    FALL = 0.45
    DUST_FRAME = 0.12
    REST = 2.0
    SPARKLE = 0.16
    duration = FALL + REST + SPARKLE

    def __init__(
        self,
        started: float,
        spot: tuple[int, int],
        ground_y: int,
        apple: Any,
        dust: Sequence[Any],
        sparkle: Any,
    ) -> None:
        super().__init__(started)
        self._apple = apple
        self._dust = tuple(dust)
        self._sparkle = sparkle
        aw, ah = apple.get_size()
        self._x = spot[0] - aw // 2
        self._y0 = spot[1] - ah // 2
        self._y1 = ground_y - ah + max(1, ah // 8)

    def items(self, now: float, out: list[DrawItem]) -> None:
        t = now - self.started
        aw, ah = self._apple.get_size()
        if t < self.FALL:
            progress = t / self.FALL
            y = self._y0 + int(round((self._y1 - self._y0) * progress * progress))
            out.append((self._apple, self._x, y))
            return
        settle = t - self.FALL
        if settle < self.REST:
            frame = int(settle / self.DUST_FRAME)
            if frame < len(self._dust):
                dust = self._dust[frame]
                dw, dh = dust.get_size()
                out.append((dust, self._x + aw // 2 - dw // 2, self._y1 + ah - dh + dh // 5))
            out.append((self._apple, self._x, self._y1))
            return
        sw, sh = self._sparkle.get_size()
        out.append(
            (self._sparkle, self._x + aw // 2 - sw // 2, self._y1 + ah // 2 - sh // 2)
        )

    def next_change(self, now: float) -> float:
        t = now - self.started
        if t < self.FALL:
            return now
        settle = t - self.FALL
        frames_end = len(self._dust) * self.DUST_FRAME
        if settle < frames_end:
            return self.started + self.FALL + (int(settle / self.DUST_FRAME) + 1) * self.DUST_FRAME
        if settle < self.REST:
            return self.started + self.FALL + self.REST
        return self.started + self.duration


class SparkleBurst(_TimedEffect):
    """Three twinkling sparkles around a point (two alternating frames)."""

    FRAME = 0.12
    duration = 0.48

    def __init__(
        self, started: float, center: tuple[int, int], radius: int, frames: Sequence[Any]
    ) -> None:
        super().__init__(started)
        self._frames = tuple(frames)
        sw, sh = self._frames[0].get_size()
        self._spots = tuple(
            (
                center[0] + int(round(radius * math.cos(angle))) - sw // 2,
                center[1] + int(round(radius * math.sin(angle))) - sh // 2,
            )
            for angle in (-2.4, -0.5, 1.4)
        )

    def items(self, now: float, out: list[DrawItem]) -> None:
        tick = int((now - self.started) / self.FRAME)
        for index, (x, y) in enumerate(self._spots):
            frame = self._frames[(tick + index) % len(self._frames)]
            out.append((frame, x, y))

    def next_change(self, now: float) -> float:
        tick = int((now - self.started) / self.FRAME) + 1
        return min(self.started + tick * self.FRAME, self.started + self.duration)


class _Cloud:
    """One drifting cloud with its normal and puffed sprites."""

    PUFF_SECONDS = 0.35

    def __init__(self, spec: CloudSpec, sweep: UiRect, scale: float, normal: Any, puffed: Any):
        self.spec = spec
        self._scale = scale
        self._normal = normal
        self._puffed = puffed
        self._cx = sweep.x + sweep.width // 2
        self._cy = sweep.y + sweep.height // 2
        self.puff_until = -1.0

    def rect_at(self, drift: float) -> UiRect:
        w, h = self._normal.get_size()
        x = self._cx + int(round(self.spec.offset_at(drift) * self._scale)) - w // 2
        return UiRect(x, self._cy - h // 2, w, h)

    def item(self, now: float, drift: float) -> DrawItem:
        rect = self.rect_at(drift)
        if now < self.puff_until:
            pw, ph = self._puffed.get_size()
            return (
                self._puffed,
                rect.x + rect.width // 2 - pw // 2,
                rect.y + rect.height // 2 - ph // 2,
            )
        return (self._normal, rect.x, rect.y)


@dataclass(slots=True)
class _Greeter:
    rect: UiRect
    character: str
    sprites: dict[str, Any]
    focus_ring: Any = None
    reaction: GreeterReaction | None = None
    reaction_started: float = 0.0
    taps: int = 0


class HomeAnimator:
    """Owner of the Home greeter and ambient scenery effects (see module doc).

    Lifecycle: the Shell calls :meth:`place_greeter` / :meth:`layout_scenery`
    when it rebuilds its cached Home frame, :meth:`update` with the current
    time and last-input time before presenting, :meth:`draw` after blitting
    the cached frame (full redraws), and :meth:`dirty_rects` /
    :meth:`draw_dirty` for incremental frames. :meth:`reset` drops all live
    state (profile change, display resize).
    """

    def __init__(self, load_sprite: SpriteLoader, *, voice: HomeGreeterVoice | None = None):
        self._load = load_sprite
        self.voice = voice
        self._greeter: _Greeter | None = None
        self._scenery: HomeSceneryLayout | None = None
        self._clouds: tuple[_Cloud, ...] = ()
        self._effects: list[_TimedEffect] = []
        self._apple_sprite: Any = None
        self._dust: tuple[Any, ...] = ()
        self._sparkles: tuple[Any, ...] = ()
        self._items: list[DrawItem] = []
        self._presented: list[DrawItem] = []
        self._last_input = -math.inf
        self._last_update: float | None = None
        self._last_frame = -math.inf
        self._drift = 0.0
        self._blink_epoch = 0.0
        self._sleeping = False
        self._next_apple = 0
        self._focused = False
        self._drifting = True
        # Set by taps/reactions: the next frame is due immediately.
        self._changed = False

    # ------------------------------------------------------------ placement
    @property
    def greeter_rect(self) -> UiRect | None:
        return self._greeter.rect if self._greeter is not None else None

    @property
    def greeter_character(self) -> str | None:
        return self._greeter.character if self._greeter is not None else None

    def place_greeter(self, rect: UiRect, character: str, now: float) -> bool:
        """Adopt the greeter slot chosen by the Home layout.

        Sprites are loaded once per (character, size). Re-placing the same
        character at the same rect (every cache rebuild) keeps the current
        reaction, so hovering portals never restarts the greeting. Returns
        False when the artwork is unavailable (caller falls back to a static
        baked greeter).
        """

        current = self._greeter
        if current is not None and current.character == character and current.rect == rect:
            return True
        size = (rect.width, rect.height)
        sprites: dict[str, Any] = {}
        for pose in _GREETER_POSES:
            sprites[pose] = self._load(f"character.{character}", pose, size)
        # Keyboard/controller focus wears the same ring art as a focused
        # portal (optional: without it the waving pose alone shows focus).
        ring_w = rect.width
        ring_h = int(round(rect.width * 304 / 288))
        try:
            ring = self._load("ui.portal.collection_focus", "default", (ring_w, ring_h))
        except Exception:  # noqa: BLE001 - optional decoration, fail soft
            ring = None
        self._greeter = _Greeter(rect, character, sprites, ring)
        self._presented = []
        if current is None or current.character != character:
            self._start_reaction("greet", now)
            self._blink_epoch = now
        return True

    def clear_greeter(self) -> None:
        self._greeter = None

    def set_focused(self, focused: bool) -> None:
        """Keyboard/controller focus is on the greeter (ring + waving pose)."""

        if bool(focused) != self._focused:
            self._changed = True
        self._focused = bool(focused)

    def layout_scenery(self, scenery: HomeSceneryLayout | None) -> None:
        """Adopt scenery geometry (``None`` = child wallpaper, no meadow)."""

        if scenery == self._scenery:
            return
        self._scenery = scenery
        self._effects.clear()
        self._presented = []
        self._clouds = ()
        if scenery is None:
            return
        scale = scenery.cover.scale
        if scenery.tree_hit is not None:
            apple = max(8, int(round(APPLE_SIZE * scale)))
            dust = max(8, int(round(DUST_SIZE * scale)))
            self._apple_sprite = self._load("prop.food.apple", "default", (apple, apple))
            self._dust = tuple(
                self._load("fx.dust_puff", variant, (dust, dust))
                for variant in ("default", "frame_2")
            )
        if scenery.tree_hit is not None or scenery.sun_center is not None:
            sparkle = max(8, int(round(SPARKLE_SIZE * scale)))
            self._sparkles = tuple(
                self._load("fx.sparkle", variant, (sparkle, sparkle))
                for variant in ("default", "frame_2")
            )
        clouds = []
        for spec, sweep in scenery.clouds:
            w = max(8, int(round(spec.size[0] * scale)))
            h = max(4, int(round(spec.size[1] * scale)))
            normal = self._load(spec.asset_id, "default", (w, h))
            puffed = self._load(
                spec.asset_id,
                "default",
                (int(round(w * CLOUD_PUFF_SCALE)), int(round(h * CLOUD_PUFF_SCALE))),
            )
            clouds.append(_Cloud(spec, sweep, scale, normal, puffed))
        self._clouds = tuple(clouds)

    def reset(self) -> None:
        self._greeter = None
        self._scenery = None
        self._clouds = ()
        self._effects.clear()
        self._items = []
        self._presented = []
        self._sleeping = False

    # ----------------------------------------------------------- hit-testing
    def hit(self, pos: tuple[int, int]) -> str | None:
        """Return the scenery under ``pos`` (smallest first), or ``None``.

        The Shell calls this only after its own targets missed, so portals,
        the profile badge and the star always win.
        """

        x, y = pos
        greeter = self._greeter
        if greeter is not None:
            r = greeter.rect
            # The art's transparent margins are not the character: use the
            # central ~70 % of the square.
            inset_x, inset_y = r.width * 15 // 100, r.height * 10 // 100
            if r.x + inset_x <= x < r.right - inset_x and r.y + inset_y <= y < r.bottom:
                return "greeter"
        for index, cloud in enumerate(self._clouds):
            r = cloud.rect_at(self._drift)
            if r.x <= x < r.right and r.y + r.height // 5 <= y < r.bottom - r.height // 6:
                return f"cloud:{index}"
        scenery = self._scenery
        if scenery is not None and scenery.sun_center is not None:
            dx, dy = x - scenery.sun_center[0], y - scenery.sun_center[1]
            if dx * dx + dy * dy <= scenery.sun_hit_radius ** 2:
                return "sun"
        if scenery is not None and scenery.tree_hit is not None:
            t = scenery.tree_hit
            # Ellipse inscribed in the crown box.
            cx, cy = t.x + t.width / 2, t.y + t.height / 2
            if ((x - cx) / (t.width / 2)) ** 2 + ((y - cy) / (t.height / 2)) ** 2 <= 1.0:
                return "tree"
        return None

    # ---------------------------------------------------------- interaction
    def tap(self, target: str, now: float, pygame: Any = None) -> bool:
        """React to a child tap/activation on ``target`` (from :meth:`hit`)."""

        self.note_input(now)
        self._changed = True
        greeter = self._greeter
        if target == "greeter" and greeter is not None:
            greeter.taps += 1
            self._start_reaction("tap_wave" if greeter.taps % 2 else "tap_happy", now)
            if self.voice is not None and pygame is not None:
                self.voice.speak(greeter.character, now, pygame)
            return True
        if target == "tree" and self._scenery is not None and self._scenery.tree_hit is not None:
            apples = sum(isinstance(e, FallingApple) for e in self._effects)
            if apples < MAX_APPLES and len(self._effects) < MAX_EFFECTS - 1:
                spots = self._scenery.apple_spots
                spot = spots[self._next_apple % len(spots)]
                self._next_apple += 1
                self._effects.append(
                    FallingApple(
                        now,
                        spot,
                        self._scenery.apple_ground_y,
                        self._apple_sprite,
                        self._dust,
                        self._sparkles[0],
                    )
                )
            self._start_reaction("glance", now, only_if_resting=True)
            return True
        if target == "sun" and self._scenery is not None and self._scenery.sun_center is not None:
            if not any(isinstance(e, SparkleBurst) for e in self._effects) and len(
                self._effects
            ) < MAX_EFFECTS - 1:
                radius = int(round(self._scenery.sun_hit_radius * 1.1))
                self._effects.append(
                    SparkleBurst(now, self._scenery.sun_center, radius, self._sparkles)
                )
            self._start_reaction("happy", now, only_if_resting=True)
            return True
        if target.startswith("cloud:"):
            index = int(target.split(":", 1)[1])
            if 0 <= index < len(self._clouds):
                self._clouds[index].puff_until = now + _Cloud.PUFF_SECONDS
                self._start_reaction("glance", now, only_if_resting=True)
                return True
        return False

    def react(self, kind: str, now: float) -> bool:
        """Make the greeter react for another Shell presentation.

        ``kind`` is one of ``"surprised"``, ``"happy"``, ``"cheer"``,
        ``"wave"``. No speech is played (the caller owns its own audio
        moment) and nothing is granted. Returns False for unknown kinds or
        when no greeter is placed.
        """

        if kind not in PUBLIC_REACTIONS or self._greeter is None:
            return False
        self.note_input(now)
        self._start_reaction(kind, now)
        self._changed = True
        return True

    def note_input(self, now: float) -> None:
        """Record child input; wakes a sleeping greeter."""

        if now > self._last_input:
            self._last_input = now

    def _start_reaction(self, name: str, now: float, *, only_if_resting: bool = False) -> None:
        greeter = self._greeter
        if greeter is None:
            return
        if only_if_resting and self._reaction_alive(now):
            return
        greeter.reaction = REACTIONS[name]
        greeter.reaction_started = now

    def _reaction_alive(self, now: float) -> bool:
        greeter = self._greeter
        return (
            greeter is not None
            and greeter.reaction is not None
            and now - greeter.reaction_started < greeter.reaction.duration
        )

    # ----------------------------------------------------------------- time
    def awake(self, now: float) -> bool:
        return now - self._last_input < AWAKE_SECONDS

    @property
    def effect_count(self) -> int:
        """Live effects including a running greeter reaction (≤ MAX_EFFECTS)."""

        reacting = self._greeter is not None and self._greeter.reaction is not None
        return len(self._effects) + (1 if reacting else 0)

    def update(
        self, now: float, last_input: float | None = None, *, drift: bool = True
    ) -> None:
        """Advance clocks and compose this moment's sprites (no drawing).

        ``drift=False`` holds the clouds still (for example while another
        Shell moment, such as the achievement ceremony, owns the screen).
        """

        if last_input is not None and last_input > self._last_input:
            self._last_input = last_input
        previous = self._last_update if self._last_update is not None else now
        self._last_update = now
        self._drifting = drift
        if drift and self.awake(now) and self._clouds:
            self._drift += min(0.25, max(0.0, now - previous))
        self._effects = [effect for effect in self._effects if not effect.finished(now)]

        greeter = self._greeter
        if greeter is not None:
            asleep = now - self._last_input >= SLEEP_AFTER_SECONDS
            if self._sleeping and not asleep:
                self._sleeping = False
                # A tap that woke the greeter keeps its own reaction.
                self._start_reaction("wake", now, only_if_resting=True)
                self._blink_epoch = now
            elif asleep and not self._reaction_alive(now):
                self._sleeping = True
            if greeter.reaction is not None and not self._reaction_alive(now):
                greeter.reaction = None

        items: list[DrawItem] = []
        for cloud in self._clouds:
            items.append(cloud.item(now, self._drift))
        for effect in self._effects:
            effect.items(now, items)
        if greeter is not None:
            if self._focused and greeter.focus_ring is not None:
                ring = greeter.focus_ring
                rw, rh = ring.get_size()
                items.append(
                    (
                        ring,
                        greeter.rect.x + greeter.rect.width // 2 - rw // 2,
                        greeter.rect.bottom - rh + rh // 40,
                    )
                )
            items.append(self._greeter_item(greeter, now))
        self._items = items
        self._changed = False

    def _greeter_item(self, greeter: _Greeter, now: float) -> DrawItem:
        dy = 0
        reaction = greeter.reaction
        if reaction is not None:
            elapsed = now - greeter.reaction_started
            pose = reaction.pose_at(elapsed)
            if reaction.hop and elapsed < _HOP_SECONDS:
                dy = -int(round(_HOP_PIXELS * math.sin(math.pi * elapsed / _HOP_SECONDS)))
        elif self._sleeping:
            pose = "sleepy"
        elif self._focused:
            pose = "pose_wave"
        elif self.awake(now) and (now - self._blink_epoch) % _BLINK_PERIOD >= _BLINK_PERIOD - _BLINK_SECONDS:
            pose = "blink"
        else:
            pose = _REST_POSE
        return (greeter.sprites[pose], greeter.rect.x, greeter.rect.y + dy)

    def next_change(self, now: float) -> float | None:
        """Absolute time of the next visual change, or ``None`` when static."""

        candidates: list[float] = [now] if self._changed else []
        for effect in self._effects:
            candidates.append(effect.next_change(now))
        greeter = self._greeter
        awake = self.awake(now)
        if greeter is not None:
            if greeter.reaction is not None:
                elapsed = now - greeter.reaction_started
                if greeter.reaction.hop and elapsed < _HOP_SECONDS:
                    candidates.append(now)
                else:
                    candidates.append(
                        greeter.reaction_started + greeter.reaction.next_pose_change(elapsed)
                    )
            elif not self._sleeping:
                if awake and not self._focused:
                    phase = (now - self._blink_epoch) % _BLINK_PERIOD
                    start = _BLINK_PERIOD - _BLINK_SECONDS
                    wait = (start - phase) if phase < start else (_BLINK_PERIOD - phase)
                    candidates.append(now + wait)
                candidates.append(self._last_input + SLEEP_AFTER_SECONDS)
        if awake and self._drifting and self._clouds:
            # Paced from the last presented frame (not from ``now``, which
            # would push the drift frame forward forever).
            candidates.append(max(now, self._last_frame + 1.0 / DRIFT_FPS))
        for cloud in self._clouds:
            if cloud.puff_until > now:
                candidates.append(cloud.puff_until)
        return min(candidates) if candidates else None

    def seconds_until_due(self, now: float) -> float | None:
        """Seconds until the next frame should be presented (``None`` = idle).

        Continuous motion is capped at ``EFFECT_FPS``; nothing is ever due
        sooner than one effect frame after the previous presented frame.
        """

        change = self.next_change(now)
        if change is None:
            return None
        due = max(change, self._last_frame + 1.0 / EFFECT_FPS)
        return max(0.0, due - now)

    # -------------------------------------------------------------- drawing
    def draw(self, surface: Any) -> None:
        """Draw every live sprite (full-frame path, after the cached Home)."""

        for sprite, x, y in self._items:
            surface.blit(sprite, (x, y))
        self._presented = self._items

    def dirty_rects(self, pygame: Any) -> list[Any]:
        """Merged screen rects whose pixels differ from the presented frame."""

        if self._items == self._presented:
            return []
        old = {(id(s), x, y): (s, x, y) for s, x, y in self._presented}
        new = {(id(s), x, y): (s, x, y) for s, x, y in self._items}
        rects = [
            pygame.Rect(x, y, *sprite.get_size())
            for key, (sprite, x, y) in old.items()
            if key not in new
        ]
        rects.extend(
            pygame.Rect(x, y, *sprite.get_size())
            for key, (sprite, x, y) in new.items()
            if key not in old
        )
        return _merge(rects)

    def draw_dirty(self, surface: Any, rects: Sequence[Any], restore: Any) -> None:
        """Restore ``rects`` from ``restore`` and redraw sprites clipped to them.

        ``rects`` must be disjoint (as returned by :meth:`dirty_rects`) so a
        translucent sprite edge is never blended twice.
        """

        previous_clip = surface.get_clip()
        try:
            for rect in rects:
                surface.set_clip(rect)
                surface.blit(restore, rect.topleft, rect)
                for sprite, x, y in self._items:
                    w, h = sprite.get_size()
                    if x < rect.right and rect.x < x + w and y < rect.bottom and rect.y < y + h:
                        surface.blit(sprite, (x, y))
        finally:
            surface.set_clip(previous_clip)
        self._presented = self._items

    def mark_frame(self, now: float) -> None:
        self._last_frame = now


def _merge(rects: list[Any]) -> list[Any]:
    """Union overlapping/touching rects until the set is disjoint (tiny n)."""

    merged = list(rects)
    changed = True
    while changed:
        changed = False
        for i in range(len(merged)):
            for j in range(i + 1, len(merged)):
                if merged[i].colliderect(merged[j]):
                    merged[i] = merged[i].union(merged[j])
                    del merged[j]
                    changed = True
                    break
            if changed:
                break
    return merged


def clip_rects(rects: Iterable[Any], bounds: Any) -> list[Any]:
    """Clip rects to the screen, dropping empty ones."""

    out = []
    for rect in rects:
        clipped = rect.clip(bounds)
        if clipped.width > 0 and clipped.height > 0:
            out.append(clipped)
    return out
