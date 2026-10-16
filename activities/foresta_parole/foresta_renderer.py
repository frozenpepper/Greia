"""Forest scene presentation for The Word Forest.

Draw order: cached glade → letters in the air (they drop out from behind the
canopy) → letters already caught peeking from the basket → basket → Leo →
canopy band → hanging picture sign (picture; after a catch the word with its
first letter in colour) → kit controls → FX.

All images come pre-scaled from ``ForestArt``; per frame there are only blits,
a per-letter alpha for leaving letters and integer offsets. No text is drawn
while the child is choosing: the prompt is the picture and the voice.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final, Sequence

import pygame

from greia_platform.activity_controls import BodyShape, ControlKit
from greia_platform.child_text import display_text
from greia_platform.pygame_blit import PreparedSurfaces

if __package__:
    from .foresta_art import INK, ForestArt, accent
    from .foresta_controls import BASKET_SIZE, FRUIT_SIZE, LEO_HEIGHT, LEO_MIDBOTTOM, ForestLayout
    from .foresta_model import FallingLetter, FallState, WordCard
else:
    from foresta_art import INK, ForestArt, accent  # type: ignore[no-redef]
    from foresta_controls import BASKET_SIZE, FRUIT_SIZE, LEO_HEIGHT, LEO_MIDBOTTOM, ForestLayout  # type: ignore[no-redef]
    from foresta_model import FallingLetter, FallState, WordCard  # type: ignore[no-redef]


SIGN_FILL: Final = (255, 248, 228)
PEEK_SIZE: Final = 50
SPARKLE_SIZE: Final = 150
WORD_SIZE: Final = 40


@dataclass(frozen=True, slots=True)
class SceneState:
    """Everything the renderer needs for one frame (built by the app)."""

    card: WordCard | None
    letters: Sequence[FallingLetter] = ()
    basket_x: float = 640.0
    caught: Sequence[WordCard] = ()
    revealed: bool = False
    speaking: bool = False
    hint: bool = False
    pulse_phase: int = 0
    leo_pointing: bool = False
    sparkle: tuple[tuple[int, int], float] | None = None
    bump: tuple[tuple[int, int], float] | None = None
    finale: float | None = None


class ForestRenderer:
    """Render the forest; geometry comes from ``ForestLayout``."""

    def __init__(self, art: ForestArt) -> None:
        self._fast = PreparedSurfaces(max_entries=96)  # RLE copies of per-frame sprites (pygame_blit)
        self._art = art
        self.cast = None  # CastFeedback, injected by the app (shares the kit art cache)
        self.kit: ControlKit | None = None
        self._point = art.cast_pose("leo", "pose_point", LEO_HEIGHT)
        self._words: dict[tuple, pygame.Surface] = {}

    @property
    def art(self) -> ForestArt:
        return self._art

    # -- cached pieces ---------------------------------------------------------------
    def _sign_body(self, rect: pygame.Rect) -> pygame.Surface | None:
        if self.kit is None:
            return None
        return self.kit.painter.body(BodyShape.PANEL, (rect.width, rect.height + 8), SIGN_FILL, lip=8, contour_width=5, highlight=False)

    def word_surface(self, card: WordCard, width: int) -> pygame.Surface:
        """The word with its first letter in colour (built once per word)."""

        key = (card.word, card.color, int(width))
        cached = self._words.get(key)
        if cached is not None:
            return cached
        if len(self._words) >= 12:
            self._words.clear()
        text = display_text(card.word)
        size = WORD_SIZE
        while True:
            head = self._art.letters.glyph(text[:1], size, accent(card.color))
            tail = self._art.letters.glyph(text[1:], size, INK, outline=False) if len(text) > 1 else None
            total = head.get_width() + (tail.get_width() if tail is not None else 0)
            if total <= width or size <= 18:
                break
            size -= 3
        height = max(head.get_height(), tail.get_height() if tail is not None else 0)
        surface = pygame.Surface((total, height), pygame.SRCALPHA)
        surface.blit(head, (0, (height - head.get_height()) // 2))
        if tail is not None:
            # The outlined capital carries a small contour pad; tuck the rest in.
            pad = max(1, int(size * 0.07))
            surface.blit(tail, (head.get_width() - pad, (height - tail.get_height()) // 2))
        self._words[key] = surface
        return surface

    # -- frame --------------------------------------------------------------------------
    def draw_scene(self, target: pygame.Surface, geometry: ForestLayout, state: SceneState, *, draw_controls) -> None:
        target.blit(self._fast(self._art.background), (0, 0))
        self._draw_letters(target, state, front=False)
        basket_rect = self._basket_rect(geometry, state.basket_x)
        self._draw_peeking(target, basket_rect, state.caught)
        self._draw_letters(target, state, front=True)
        basket = self._art.private("basket", BASKET_SIZE)
        if basket is not None:
            target.blit(self._fast(basket), basket_rect)
        else:
            pygame.draw.rect(target, (184, 119, 53), basket_rect.inflate(-20, -30), border_radius=16)
        self._draw_leo(target, state)
        if self._art.canopy is not None:
            target.blit(self._fast(self._art.canopy), (0, 0))
        self._draw_sign(target, geometry, state)
        draw_controls(target)
        self._draw_fx(target, state)

    def sprite_regions(self, geometry: ForestLayout, state: SceneState) -> list[pygame.Rect] | None:
        """Logical rectangles ``draw_scene`` may change between two frames.

        Covers the letters in the air (with glow), the basket with the
        letters peeking over its rim, Leo while he moves or points, and the
        sign while it speaks or pulses.  Returns None while an FX burst or
        the finale plays: the caller renders a full frame.  Callers union
        these with the previous frame's rectangles (vacated pixels) and
        render a full frame whenever the card/reveal/catch tally changes.
        """

        if state.sparkle is not None or state.bump is not None or state.finale is not None:
            return None
        regions: list[pygame.Rect] = []
        glow_side = int(FRUIT_SIZE * 1.7 * 1.08) + 8
        plain_side = FRUIT_SIZE + 12
        for letter in state.letters:
            side = glow_side if letter.glow else plain_side
            rect = pygame.Rect(0, 0, side, side)
            rect.center = (int(round(letter.x)), int(round(letter.y)))
            regions.append(rect)
        basket = self._basket_rect(geometry, state.basket_x)
        regions.append(basket.inflate(16, 16).union(basket.move(0, -(PEEK_SIZE + 24))))
        cast = self.cast
        if state.leo_pointing or (cast is not None and cast.animating):
            leo = pygame.Rect(0, 0, int(LEO_HEIGHT * 1.6), int(LEO_HEIGHT * 1.3))
            leo.midbottom = (LEO_MIDBOTTOM[0], LEO_MIDBOTTOM[1] + 8)
            regions.append(leo)
        if state.speaking or state.hint:
            sign = geometry.sign
            side = int(max(sign.width, sign.height) * 1.25 * 1.05) + 8
            glow = pygame.Rect(0, 0, side, side)
            glow.center = sign.center
            regions.append(glow.union(sign.inflate(16, 24)))
        return regions

    @staticmethod
    def _basket_rect(geometry: ForestLayout, x: float) -> pygame.Rect:
        rect = pygame.Rect(0, 0, *BASKET_SIZE)
        rect.midbottom = (int(round(x)), geometry.basket_bottom)
        return rect

    def _draw_letters(self, target: pygame.Surface, state: SceneState, *, front: bool) -> None:
        """Caught letters sink into the basket (drawn behind its front); the rest in front."""

        for letter in state.letters:
            sinking = letter.state is FallState.CAUGHT
            if sinking == front:
                continue
            fruit = self._art.fruit(letter.char, FRUIT_SIZE, letter.color)
            centre = (int(round(letter.x)), int(round(letter.y)))
            if letter.glow and letter.state is FallState.FALLING:
                pulse = 1.0 + 0.08 * (state.pulse_phase % 2)
                glow = self._art.glow(int(FRUIT_SIZE * 1.7 * pulse))
                target.blit(self._fast(glow), glow.get_rect(center=centre))
            fade = letter.fade
            if fade < 0.999:
                faded = self._fast.faded(fruit, fade)
                if faded is not None:
                    target.blit(faded, fruit.get_rect(center=centre))
            else:
                target.blit(self._fast(fruit), fruit.get_rect(center=centre))

    def _draw_peeking(self, target: pygame.Surface, basket: pygame.Rect, caught: Sequence[WordCard]) -> None:
        """Letters caught this round peek over the rim (a tangible tally)."""

        count = len(caught)
        if not count:
            return
        mouth_y = basket.top + int(basket.height * 34 / 160)
        span = basket.width - 60
        step = span / max(1, count - 1) if count > 1 else 0
        for index, card in enumerate(caught):
            x = basket.centerx if count == 1 else int(basket.left + 30 + index * step)
            lift = 12 if index % 2 else 0
            fruit = self._art.fruit(card.letter, PEEK_SIZE, card.color)
            target.blit(self._fast(fruit), fruit.get_rect(midbottom=(x, mouth_y + 22 - lift)))

    def _draw_leo(self, target: pygame.Surface, state: SceneState) -> None:
        cast = self.cast
        if state.leo_pointing and self._point is not None and (cast is None or not cast.animating):
            target.blit(self._fast(self._point), self._point.get_rect(midbottom=LEO_MIDBOTTOM))
            return
        if cast is not None:
            cast.draw(target, LEO_MIDBOTTOM)

    def _draw_sign(self, target: pygame.Surface, geometry: ForestLayout, state: SceneState) -> None:
        sign = geometry.sign
        if state.speaking or state.hint:
            pulse = 1.0 + (0.05 * (state.pulse_phase % 2) if state.hint else 0.0)
            glow = self._art.glow(int(max(sign.width, sign.height) * 1.25 * pulse))
            target.blit(self._fast(glow), glow.get_rect(center=sign.center))
        body = self._sign_body(sign)
        if body is not None:
            target.blit(self._fast(body), sign.topleft)
        else:
            pygame.draw.rect(target, SIGN_FILL, sign, border_radius=28)
            pygame.draw.rect(target, INK, sign, width=4, border_radius=28)
        card = state.card
        if card is None:
            if state.finale is not None:
                self._draw_recap(target, geometry, state.caught)
            return
        lift = -6 if state.speaking else 0
        # Big and centred while the child is choosing; smaller above the word after.
        box = geometry.picture if state.revealed else geometry.stage
        side = box.width if state.revealed else min(box.width, box.height) - 14
        picture = self._art.picture(card.picture, side)
        if picture is not None:
            target.blit(self._fast(picture), picture.get_rect(center=box.move(0, lift).center))
        if state.revealed:
            word = self.word_surface(card, geometry.word.width)
            target.blit(self._fast(word), word.get_rect(center=geometry.word.center))

    def _draw_recap(self, target: pygame.Surface, geometry: ForestLayout, caught: Sequence[WordCard]) -> None:
        """Finale: the round's letters, in two rows of three, on the sign."""

        inner = geometry.sign.inflate(-24, -28)
        columns = 3
        rows = max(1, (len(caught) + columns - 1) // columns)
        cell = min(inner.width // columns, inner.height // max(2, rows))
        for index, card in enumerate(caught):
            row, column = divmod(index, columns)
            centre = (
                inner.centerx + (column - 1) * cell,
                inner.centery + int((row - (rows - 1) / 2) * cell),
            )
            fruit = self._art.fruit(card.letter, int(cell * 0.92), card.color)
            target.blit(self._fast(fruit), fruit.get_rect(center=centre))

    def _draw_fx(self, target: pygame.Surface, state: SceneState) -> None:
        if state.sparkle is not None:
            position, t = state.sparkle
            # One cached size; the burst rises and fades (no per-frame scaling).
            burst = self._art.fx("fx.star_burst", SPARKLE_SIZE)
            if burst is not None:
                faded = self._fast.faded(burst, max(0.0, 1.0 - t))
                if faded is not None:
                    target.blit(faded, burst.get_rect(center=(position[0], position[1] - int(30 * t))))
        if state.bump is not None:
            position, t = state.bump
            puff = self._art.fx("fx.dust_puff", 96)
            if puff is not None:
                faded = self._fast.faded(puff, 220 / 255 * max(0.0, 1.0 - t))
                if faded is not None:
                    target.blit(faded, puff.get_rect(center=(position[0], position[1] - int(20 * t))))
        if state.finale is not None:
            # Two confetti bursts drifting down over the glade (one cached size each).
            for (x, y0), size, delay in (((520, 230), 280, 0.0), ((820, 200), 220, 0.35)):
                t = state.finale - delay
                if t < 0:
                    continue
                confetti = self._art.fx("fx.confetti", size)
                if confetti is not None:
                    target.blit(self._fast(confetti), confetti.get_rect(center=(x, y0 + int(min(t, 2.5) * 40))))


__all__ = ["ForestRenderer", "SceneState"]
