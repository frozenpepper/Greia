"""Keyboard affordance for Activities: drawn keycaps that light with real keys.

Greia runs on laptops. A child who meets a game with on-screen buttons should
also discover that the arrow keys and Space work. ``KeyboardHint`` is the shared
ADR 0037 control for that: it draws the keys that act in this Activity as
keycaps (an inverted-T arrow cluster, Space and optionally Enter) from the
shared ``ui.keycap.*`` art, dims arrows that do nothing here, and lights a
keycap while its real key (or the matching controller D-pad / south button)
is held, so the child sees the mapping. It carries no text and no brand
symbols, so it is language-neutral.

Typical use beside a mouse-first cluster::

    size = KeyboardHint.preferred_size({KeyCap.LEFT, KeyCap.RIGHT, KeyCap.SPACE}, key=44)
    cluster = layout.cluster([(96, 96), (96, 96)], hint_size=size)
    hint = kit.keyboard_hint("keys", cluster.hint, active={KeyCap.LEFT, KeyCap.RIGHT, KeyCap.SPACE})
    hint.show(8.0)                   # at start; again from each idle-hint step
    ...
    if hint.observe_event(event):    # every Pygame event, before gameplay
        frames.invalidate()
    if hint.update():                # once per loop iteration
        frames.invalidate()
    deadline = hint.deadline()       # wake the governed loop for a lit/hide timer
    if deadline is not None:
        frames.wake_at(deadline)

Cost (Acer floor): each keycap is scaled once per (key, state, size) by
``ControlArt``; a visual state (set of lit keys) composes those surfaces once
into the painter's bounded cache, so ``draw`` is one blit. Nothing rasterises
SVG at runtime and no font is used. Missing art degrades to painter-drawn
keycaps with the same geometry.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable
from enum import StrEnum
import time

import pygame

from .activity_controls import (
    INK,
    BodyShape,
    ControlArt,
    ControlPainter,
    ControlVisualState,
    KitControl,
)
from .input_core import (
    InputEdge,
    PhysicalControl,
    SemanticAction,
    SemanticInputEvent,
)
from .pygame_input import PygameInputTranslator


class KeyCap(StrEnum):
    """Keys the hint can draw; values are the ``ui.keycap.<value>`` art ids."""

    UP = "arrow_up"
    DOWN = "arrow_down"
    LEFT = "arrow_left"
    RIGHT = "arrow_right"
    SPACE = "space"
    ENTER = "enter"


ARROW_KEYS = frozenset({KeyCap.UP, KeyCap.DOWN, KeyCap.LEFT, KeyCap.RIGHT})

# Physical controls (keyboard keys and their brand-neutral controller twins)
# that light a keycap. Controller D-pad lights the arrows and the south face
# button lights Space, because the standard mappings (ADR 0020) give them the
# same meaning.
_PHYSICAL_KEYCAPS: dict[PhysicalControl, KeyCap] = {
    PhysicalControl.KEY_UP: KeyCap.UP,
    PhysicalControl.KEY_DOWN: KeyCap.DOWN,
    PhysicalControl.KEY_LEFT: KeyCap.LEFT,
    PhysicalControl.KEY_RIGHT: KeyCap.RIGHT,
    PhysicalControl.KEY_SPACE: KeyCap.SPACE,
    PhysicalControl.KEY_ENTER: KeyCap.ENTER,
    PhysicalControl.CONTROLLER_DPAD_UP: KeyCap.UP,
    PhysicalControl.CONTROLLER_DPAD_DOWN: KeyCap.DOWN,
    PhysicalControl.CONTROLLER_DPAD_LEFT: KeyCap.LEFT,
    PhysicalControl.CONTROLLER_DPAD_RIGHT: KeyCap.RIGHT,
    PhysicalControl.CONTROLLER_FACE_SOUTH: KeyCap.SPACE,
}

_SEMANTIC_KEYCAPS: dict[SemanticAction, KeyCap] = {
    SemanticAction.MOVE_UP: KeyCap.UP,
    SemanticAction.MOVE_DOWN: KeyCap.DOWN,
    SemanticAction.MOVE_LEFT: KeyCap.LEFT,
    SemanticAction.MOVE_RIGHT: KeyCap.RIGHT,
    SemanticAction.NAV_UP: KeyCap.UP,
    SemanticAction.NAV_DOWN: KeyCap.DOWN,
    SemanticAction.NAV_LEFT: KeyCap.LEFT,
    SemanticAction.NAV_RIGHT: KeyCap.RIGHT,
    SemanticAction.PRIMARY: KeyCap.SPACE,
}

# Space bar aspect (art is 240x96 against 96x96 keys).
SPACE_ASPECT = 2.5
DIMMED_ALPHA = 90


class KeyboardHint(KitControl):
    """Display-only keycap hint that lights the drawn key while the real key is held.

    ``active`` names the keys that act in this Activity. Arrows are drawn as a
    full inverted-T cluster whenever any arrow acts (non-acting arrows are
    dimmed, so a left/right game still looks like the keyboard the child
    sees); Space and Enter are drawn only when they act. Lighting is driven by
    the semantic input layer: ``observe`` takes brand-neutral
    ``PhysicalControl`` edges, ``observe_event`` a raw Pygame event (through
    ``PygameInputTranslator.physical_digital``), ``observe_semantic`` a
    ``SemanticInputEvent``. A tap stays lit for at least ``lit_hold`` seconds
    so it is visible. A key press also reveals the hint for ``show_seconds``.
    ``demonstrate`` lights the acting keys one after another (an idle-hint
    step: "these keys work too").
    """

    focusable_by_default = False

    def __init__(
        self,
        painter: ControlPainter,
        control_id: str,
        rect: pygame.Rect | tuple[int, int, int, int],
        *,
        art: ControlArt,
        active: Iterable[KeyCap | str],
        lit_hold: float = 0.2,
        show_seconds: float = 6.0,
        demo_step: float = 0.45,
        clock: Callable[[], float] = time.monotonic,
        visible: bool = False,
    ) -> None:
        super().__init__(painter, control_id, rect, visible=visible)
        self.active = frozenset(KeyCap(key) for key in active)
        if not self.active:
            raise ValueError("a keyboard hint needs at least one acting key")
        self._art = art
        self._clock = clock
        self.lit_hold = float(lit_hold)
        self.show_seconds = float(show_seconds)
        self.demo_step = float(demo_step)
        self._held: set[KeyCap] = set()
        self._lit_until: dict[KeyCap, float] = {}
        self._hide_at: float | None = None
        self._pinned = False
        self._demo: tuple[KeyCap, ...] = ()
        self._demo_started = 0.0
        self._translator = PygameInputTranslator("navigation")
        self._settle()

    # -- geometry ----------------------------------------------------------
    @staticmethod
    def drawn_keys(active: Iterable[KeyCap | str]) -> tuple[KeyCap, ...]:
        """Keys that are drawn for ``active`` (all four arrows if any arrow acts)."""

        keys = {KeyCap(key) for key in active}
        drawn: list[KeyCap] = []
        if keys & ARROW_KEYS:
            drawn.extend((KeyCap.UP, KeyCap.LEFT, KeyCap.DOWN, KeyCap.RIGHT))
        if KeyCap.SPACE in keys:
            drawn.append(KeyCap.SPACE)
        if KeyCap.ENTER in keys:
            drawn.append(KeyCap.ENTER)
        return tuple(drawn)

    @staticmethod
    def preferred_size(active: Iterable[KeyCap | str], *, key: int = 44, gap: int | None = None) -> tuple[int, int]:
        """Logical size of the hint for ``active`` keys drawn ``key`` px tall."""

        key = int(key)
        spacing = max(2, key // 10) if gap is None else int(gap)
        drawn = KeyboardHint.drawn_keys(active)
        has_arrows = KeyCap.UP in drawn
        width = 0
        if has_arrows:
            width += 3 * key + 2 * spacing
        for extra in (KeyCap.SPACE, KeyCap.ENTER):
            if extra in drawn:
                width += (spacing * 3 if width else 0) + (round(key * SPACE_ASPECT) if extra is KeyCap.SPACE else key)
        height = 2 * key + spacing if has_arrows else key
        return int(width), int(height)

    def key_rects(self) -> dict[KeyCap, pygame.Rect]:
        """Keycap rectangles relative to the control's top-left corner."""

        width, height = self._rect.size
        drawn = self.drawn_keys(self.active)
        has_arrows = KeyCap.UP in drawn
        # Solve the key size that fits the rect (inverse of preferred_size).
        key = height if not has_arrows else int((height) / 2.1)
        while key > 4 and self.preferred_size(self.active, key=key)[0] > width:
            key -= 1
        while key > 4 and self.preferred_size(self.active, key=key)[1] > height:
            key -= 1
        spacing = max(2, key // 10)
        used_w, used_h = self.preferred_size(self.active, key=key)
        x = (width - used_w) // 2
        bottom = (height + used_h) // 2
        rects: dict[KeyCap, pygame.Rect] = {}
        if has_arrows:
            rects[KeyCap.UP] = pygame.Rect(x + key + spacing, bottom - 2 * key - spacing, key, key)
            for index, cap in enumerate((KeyCap.LEFT, KeyCap.DOWN, KeyCap.RIGHT)):
                rects[cap] = pygame.Rect(x + index * (key + spacing), bottom - key, key, key)
            x += 3 * key + 2 * spacing + spacing * 3
        if KeyCap.SPACE in drawn:
            space_w = round(key * SPACE_ASPECT)
            rects[KeyCap.SPACE] = pygame.Rect(x, bottom - key, space_w, key)
            x += space_w + spacing * 3
        if KeyCap.ENTER in drawn:
            rects[KeyCap.ENTER] = pygame.Rect(x, bottom - key, key, key)
        return rects

    # -- input -------------------------------------------------------------
    def observe(self, control: PhysicalControl, edge: InputEdge) -> bool:
        """Light/unlight the keycap for one physical edge; True if the look changed."""

        return self._observe_cap(_PHYSICAL_KEYCAPS.get(control), edge)

    def observe_event(self, event: pygame.event.Event) -> bool:
        """Observe a raw Pygame keyboard/controller event (never consumes it)."""

        translated = self._translator.physical_digital(event)
        if translated is None:
            return False
        control, edge, _source = translated
        return self.observe(control, edge)

    def observe_semantic(self, event: SemanticInputEvent) -> bool:
        """Observe a semantic action (MOVE_*/NAV_* → arrows, PRIMARY → Space).

        ``ACTIVATE`` lights Enter when Enter is drawn, otherwise Space.
        """

        cap = _SEMANTIC_KEYCAPS.get(event.action)
        if event.action is SemanticAction.ACTIVATE:
            cap = KeyCap.ENTER if KeyCap.ENTER in self.active else KeyCap.SPACE
        return self._observe_cap(cap, event.edge)

    def _observe_cap(self, cap: KeyCap | None, edge: InputEdge) -> bool:
        if cap is None or cap not in self.active:
            return False
        before = self._settled
        now = self._clock()
        if edge is InputEdge.PRESSED:
            self._held.add(cap)
            self._lit_until[cap] = now + self.lit_hold
            self._demo = ()
            self.show(self.show_seconds)
        else:
            self._held.discard(cap)
        return self._settle() != before

    # -- visibility / demonstration --------------------------------------------
    def show(self, seconds: float | None = None) -> None:
        """Reveal the hint; hide again after ``seconds`` (``None`` = stay)."""

        if seconds is None:
            self._pinned = True
            self._hide_at = None
        elif not (self.visible and self._pinned):
            until = self._clock() + float(seconds)
            if not self.visible or self._hide_at is None:
                self._hide_at = until
            else:
                self._hide_at = max(until, self._hide_at)
        self.visible = True

    def hide(self) -> None:
        self.visible = False
        self._hide_at = None
        self._pinned = False
        self._demo = ()

    def demonstrate(self) -> None:
        """Idle-hint step: show the hint and light each acting key in turn once."""

        order = [cap for cap in self.drawn_keys(self.active) if cap in self.active]
        self._demo = tuple(order)
        self._demo_started = self._clock()
        self.show(max(self.show_seconds, self.demo_step * len(order) + 1.0))

    @property
    def lit(self) -> frozenset[KeyCap]:
        now = self._clock()
        lit = set(self._held)
        lit.update(cap for cap, until in self._lit_until.items() if until > now)
        if self._demo:
            index = int((now - self._demo_started) / max(0.05, self.demo_step))
            if 0 <= index < len(self._demo):
                lit.add(self._demo[index])
        return frozenset(lit)

    @property
    def animating(self) -> bool:
        """True while a timed change is pending (lit hold or demonstration)."""

        now = self._clock()
        return bool(self._demo) or any(until > now for until in self._lit_until.values())

    def deadline(self) -> float | None:
        """Next clock time at which the hint's look changes on its own."""

        candidates: list[float] = []
        now = self._clock()
        candidates.extend(until for until in self._lit_until.values() if until > now)
        if self._demo:
            step = max(0.05, self.demo_step)
            index = int((now - self._demo_started) / step)
            if index < len(self._demo):
                candidates.append(self._demo_started + (index + 1) * step)
        # A held key keeps the hint up (a child may hold an arrow to steer), so
        # the hide time is not a deadline then; a past one must not spin the loop.
        if self.visible and self._hide_at is not None and not self._held:
            candidates.append(max(self._hide_at, now))
        return min(candidates) if candidates else None

    def update(self) -> bool:
        """Advance timers (call once per loop); True if the look changed."""

        before = self._settled
        now = self._clock()
        self._lit_until = {cap: until for cap, until in self._lit_until.items() if until > now}
        if self._demo and now - self._demo_started >= max(0.05, self.demo_step) * len(self._demo):
            self._demo = ()
        if self.visible and self._hide_at is not None and now >= self._hide_at and not self._held:
            self.visible = False
            self._hide_at = None
        return self._settle() != before

    # The look last reported to the loop; ``update``/``observe`` compare against it.
    _settled: tuple[bool, frozenset[KeyCap]] = (False, frozenset())

    def _settle(self) -> tuple[bool, frozenset[KeyCap]]:
        self._settled = (self.visible, self.lit if self.visible else frozenset())
        return self._settled

    # -- rendering ------------------------------------------------------------
    def _content_key(self) -> tuple:
        return (tuple(sorted(self.active)), tuple(sorted(self.lit)))

    def _build(self, state: ControlVisualState) -> pygame.Surface:
        surface = pygame.Surface(self._rect.size, pygame.SRCALPHA)
        lit = self.lit
        for cap, rect in self.key_rects().items():
            image = self._keycap(cap, rect.size, lit=cap in lit)
            if cap not in self.active:
                image = image.copy()
                image.fill((255, 255, 255, DIMMED_ALPHA), special_flags=pygame.BLEND_RGBA_MULT)
            surface.blit(image, rect.topleft)
        return surface

    def draw(self, target: object) -> None:
        self._settle()
        super().draw(target)

    def _keycap(self, cap: KeyCap, size: tuple[int, int], *, lit: bool) -> pygame.Surface:
        image = self._art.image(f"ui.keycap.{cap.value}", size, variant="lit" if lit else "default")
        if image is not None:
            return image
        return self._painter.cached(("keycap-fallback", cap.value, size, lit), lambda: self._fallback(cap, size, lit))

    def _fallback(self, cap: KeyCap, size: tuple[int, int], lit: bool) -> pygame.Surface:
        """Vector keycap with the same geometry as the art (art missing)."""

        painter = self._painter
        fill = (255, 194, 52) if lit else (255, 251, 235)
        lip = max(2, round(size[1] * (0.08 if lit else 0.14)))
        body = painter.body(BodyShape.TILE, size, fill, lip=lip, pressed=lit)
        surface = body.copy()
        w, h = size
        cx, cy = w // 2, (h - lip) // 2 + (lip if lit else 0)
        r = max(3, h // 5)
        if cap in ARROW_KEYS:
            points = {
                KeyCap.UP: [(cx, cy - r), (cx + r, cy + r // 2), (cx - r, cy + r // 2)],
                KeyCap.DOWN: [(cx, cy + r), (cx + r, cy - r // 2), (cx - r, cy - r // 2)],
                KeyCap.LEFT: [(cx - r, cy), (cx + r // 2, cy - r), (cx + r // 2, cy + r)],
                KeyCap.RIGHT: [(cx + r, cy), (cx - r // 2, cy - r), (cx - r // 2, cy + r)],
            }[cap]
            pygame.draw.polygon(surface, INK, points)
        elif cap is KeyCap.SPACE:
            line = max(2, h // 14)
            half = w // 4
            pygame.draw.lines(surface, INK, False, [(cx - half, cy - r // 2), (cx - half, cy + r // 2), (cx + half, cy + r // 2), (cx + half, cy - r // 2)], line)
        else:
            line = max(2, h // 14)
            pygame.draw.lines(surface, INK, False, [(cx + r, cy - r), (cx + r, cy + r // 3), (cx - r, cy + r // 3)], line)
            pygame.draw.polygon(surface, INK, [(cx - r - line, cy + r // 3), (cx - r // 3, cy - r // 3), (cx - r // 3, cy + r)])
        return surface


__all__ = ["ARROW_KEYS", "KeyCap", "KeyboardHint"]
