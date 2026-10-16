"""Penguin entry: swimming, feathers, worldwide habitats and breeding variety."""

from __future__ import annotations

from dataclasses import dataclass
import math

import pygame
import pygame.gfxdraw

if __package__ and "." in __package__:
    from ..enciclopedia_engine import EncyclopediaPage, PageCommand, PageInput, PageInputKind
    from ..enciclopedia_presentation import (
        TOKEN_SHAPE_FELT_TAG,
        announce_focus_name,
        draw_animal_action_button,
        draw_authored_scene,
        draw_caption_ribbon,
        draw_discovery_token,
        draw_navigation_arrows,
        draw_title,
        encyclopedia_focus_cue,
    )
    from ..enciclopedia_focus_audio import FocusAudioTracker
    from .common import draw_presenter, grid_step
    from .storybook_ink import inked_circle, inked_ellipse, inked_limb, inked_polygon
else:
    from enciclopedia_engine import EncyclopediaPage, PageCommand, PageInput, PageInputKind
    from enciclopedia_presentation import (
        TOKEN_SHAPE_FELT_TAG,
        announce_focus_name,
        draw_animal_action_button,
        draw_authored_scene,
        draw_caption_ribbon,
        draw_discovery_token,
        draw_navigation_arrows,
        draw_title,
        encyclopedia_focus_cue,
    )
    from enciclopedia_focus_audio import FocusAudioTracker
    from pages.common import draw_presenter, grid_step
    from pages.storybook_ink import inked_circle, inked_ellipse, inked_limb, inked_polygon


@dataclass(frozen=True, slots=True)
class PenguinDiscovery:
    discovery_id: str
    caption_key: str
    cue_id: str
    center: tuple[int, int]


DISCOVERIES = (
    PenguinDiscovery("swim", "penguin.swim", "encyclopedia.animals.penguin.swim", (255, 200)),
    PenguinDiscovery("feathers", "penguin.feathers", "encyclopedia.animals.penguin.feathers", (750, 200)),
    PenguinDiscovery("world", "penguin.world", "encyclopedia.animals.penguin.world", (255, 415)),
    PenguinDiscovery("breeding", "penguin.breeding", "encyclopedia.animals.penguin.breeding", (750, 415)),
)

_WORLD_SCENES = ("ice", "temperate", "warm")


def _mound(x0: int, base: int, width: int, height: int) -> list[tuple[int, int]]:
    """Rounded island/headland outline that hides a baked iceberg site."""

    points = []
    for step in range(13):
        t = step / 12
        lift = math.sin(math.pi * t) ** 0.6
        points.append((x0 + int(width * t), base - int(height * lift)))
    return points


class PenguinPage(EncyclopediaPage):
    """Own bounded exhibit states; species diversity remains presentation-only."""

    page_id = "animals.penguin"

    def __init__(self, context) -> None:
        super().__init__(context)

        self._focus_audio = FocusAudioTracker()
        self._time = 0.0
        self._selected = 0
        self._hovered: int | None = None
        self._swimming = False
        self._feather_age = 0.0
        self._world_state = 0
        self._breeding_state = 0
        self._breeding_age = 0.0
        self._caption_key = "penguin.intro"
        self._hotspots = tuple(
            pygame.Rect(cx - 43, cy - 43, 86, 86)
            for cx, cy in (item.center for item in DISCOVERIES)
        )
        self._arrow_left_hit: pygame.Rect = pygame.Rect(0, 0, 0, 0)
        self._arrow_right_hit: pygame.Rect = pygame.Rect(0, 0, 0, 0)
        self._action_hit: pygame.Rect = pygame.Rect(0, 0, 0, 0)

    def on_enter(self) -> None:
        self.context.audio.play("encyclopedia.animals.penguin.intro")
        self._announce_selected()

    def _announce_selected(self) -> None:
        disc = DISCOVERIES[self._selected]
        cue = encyclopedia_focus_cue(disc.discovery_id, "name")
        # Use deduped announce for focus changes
        if not self._focus_audio.announce_once(self.context.audio, cue):
            # Fallback to disc.cue_id if focus cue not yet integrated (will fail silently until audio exists)
            self._focus_audio.announce_once(self.context.audio, disc.cue_id)

    def _set_selected(self, index: int) -> None:
        index = max(0, min(len(DISCOVERIES) - 1, index))
        if index == self._selected:
            return
        self._selected = index
        self._announce_selected()

    def _trigger_main(self) -> None:
        self._swimming = not self._swimming
        self._caption_key = "penguin.swim"
        announce_focus_name(self.context.audio, encyclopedia_focus_cue("animals", "penguin", "swim", "name"))
        self.context.audio.play("encyclopedia.animals.penguin.swim")

    def update(self, dt: float) -> None:
        self._time += dt
        self._feather_age = max(0.0, self._feather_age - dt)
        self._breeding_age = max(0.0, self._breeding_age - dt)

    def handle_input(self, event: PageInput) -> None:
        if event.position is not None and event.kind in {
            PageInputKind.POINTER_MOVE,
            PageInputKind.POINTER_PRESS,
        }:
            point = (int(event.position[0]), int(event.position[1]))
            if event.kind is PageInputKind.POINTER_PRESS:
                if self._action_hit.collidepoint(point):
                    self._trigger_main()
                    return
                if self._arrow_left_hit.collidepoint(point):
                    self._set_selected(self._selected - 1)
                    return
                if self._arrow_right_hit.collidepoint(point):
                    self._set_selected(self._selected + 1)
                    return
            hit = next(
                (index for index, rect in enumerate(self._hotspots) if rect.collidepoint(point)),
                None,
            )
            if event.kind is PageInputKind.POINTER_MOVE and hit is not None and hit != self._selected:
                disc = DISCOVERIES[hit]
                cue = encyclopedia_focus_cue("animals", "penguin", disc.discovery_id, "name")
                self._focus_audio.announce_once(self.context.audio, cue)
            self._hovered = hit
            if event.kind is PageInputKind.POINTER_PRESS and hit is not None:
                self._set_selected(hit)
                self._activate(hit)
            return
        if event.kind is not PageInputKind.COMMAND or event.command is None:
            return
        if event.command is PageCommand.ACTIVATE:
            if DISCOVERIES[self._selected].discovery_id == "swim":
                self._trigger_main()
                return
            self._activate(self._selected)
            return
        prev = self._selected
        self._selected = grid_step(
            self._selected,
            event.command,
            columns=2,
            count=len(DISCOVERIES),
        )
        if self._selected != prev:
            self._announce_selected()

    def _activate(self, index: int) -> None:
        discovery = DISCOVERIES[index]
        self._caption_key = discovery.caption_key
        if discovery.discovery_id == "swim":
            self._swimming = not self._swimming
        elif discovery.discovery_id == "feathers":
            self._feather_age = 4.0
        elif discovery.discovery_id == "world":
            # Habitat variety is the lesson here, so return to the land scene
            # before cycling it; otherwise a swimming view would hide the change.
            self._swimming = False
            self._world_state = (self._world_state + 1) % len(_WORLD_SCENES)
        else:
            self._breeding_state = 1 - self._breeding_state
            self._breeding_age = 4.5
        self.context.audio.play(discovery.cue_id)

    def draw(self, surface: pygame.Surface) -> None:
        authored = draw_authored_scene(
            surface,
            self.context.visuals,
            "encyclopedia.animals.penguin.ice_shore",
        )
        if authored:
            self._draw_habitat_overlay(surface)
        else:
            # Procedural fallback while the authored runtime rendition is absent.
            self._draw_environment(surface)
        draw_title(
            surface,
            self.context.typography,
            self.context.resources.text("penguin.title"),
            self.context.palette.ink,
        )
        self._draw_penguin(surface)
        self._draw_feather_reveal(surface)
        self._draw_breeding_reveal(surface)
        self._draw_hotspots(surface)
        can_left = self._selected > 0
        can_right = self._selected < len(DISCOVERIES) - 1
        self._arrow_left_hit, self._arrow_right_hit = draw_navigation_arrows(
            surface, time=self._time, can_go_left=can_left, can_go_right=can_right
        )
        self._action_hit = draw_animal_action_button(
            surface, (512, 460), animal="penguin", time=self._time, active=True
        )
        self._draw_caption(surface)
        draw_presenter(
            surface,
            self.context.visuals,
            "tito",
            position=(925, 565),
            height=142,
            variant="happy",
            fallback_color=(247, 151, 77),
        )

    def _draw_habitat_overlay(self, surface: pygame.Surface) -> None:
        """Repaint the authored ice shore for the cooler-rock and warm habitats.

        Only the foreground shore and the two small iceberg sites change; sky,
        sea and the penguin stay put so the child sees the same animal living
        in a different place.
        """

        scene = _WORLD_SCENES[self._world_state]
        if scene == "ice":
            return
        if scene == "temperate":
            ground, ground_light, ink = (150, 141, 120), (184, 176, 156), (75, 55, 47)
            for x0 in (160, 712):
                inked_polygon(surface, (96, 150, 92), _mound(x0, 322, 150, 70), ink=(63, 110, 58))
            inked_circle(surface, (89, 150, 86), (95, 380), 34, ink=(63, 110, 58))
            pygame.draw.rect(surface, (120, 84, 56), (89, 405, 12, 30))
        else:
            ground, ground_light, ink = (238, 214, 166), (247, 232, 199), (156, 120, 74)
            pygame.gfxdraw.filled_circle(surface, 865, 130, 40, (255, 210, 94))
            pygame.gfxdraw.aacircle(surface, 865, 130, 40, (255, 210, 94))
            for x0 in (160, 712):
                inked_polygon(surface, (238, 214, 166), _mound(x0, 322, 150, 66), ink=ink)
            # One palm on the outer island edge, clear of the discovery tags.
            inked_limb(surface, (150, 108, 70), [(842, 292), (848, 268), (856, 246)], [8, 7], outline=2)
            for dx, dy in ((-36, 12), (36, 10), (-22, -12), (26, -14), (0, -18)):
                inked_limb(surface, (89, 160, 90), [(856, 246), (856 + dx, 246 + dy)], [8], outline=2)
        shore = [(0, 430), (140, 420), (300, 428), (512, 418), (700, 426), (880, 418), (1024, 428), (1024, 600), (0, 600)]
        inked_polygon(surface, ground, shore, ink=ink)
        pygame.draw.lines(surface, ground_light, False, [(20, 448), (300, 444), (700, 446), (1004, 446)], 4)
        if scene == "temperate":
            for x, y, r in ((70, 470, 26), (140, 480, 18), (880, 468, 28), (950, 482, 18)):
                inked_ellipse(surface, (124, 118, 104), (x - r, y - r // 2, r * 2, r), ink=ink)

    def _draw_environment(self, surface: pygame.Surface) -> None:
        scene = _WORLD_SCENES[self._world_state]
        if self._swimming:
            surface.fill((93, 176, 211))
            pygame.draw.rect(surface, (58, 132, 176), (0, 165, 1024, 435))
            for index in range(7):
                x = 80 + index * 135
                pygame.draw.circle(surface, (171, 220, 235), (x, 260 + (index % 3) * 55), 5)
            return
        if scene == "ice":
            surface.fill((205, 232, 242))
            pygame.draw.rect(surface, (238, 246, 246), (0, 405, 1024, 195))
            pygame.draw.polygon(surface, (220, 239, 244), [(0, 405), (170, 335), (310, 405)])
        elif scene == "temperate":
            surface.fill((191, 224, 228))
            pygame.draw.rect(surface, (87, 159, 184), (0, 435, 1024, 165))
            pygame.draw.polygon(surface, (137, 132, 110), [(0, 485), (180, 380), (390, 485)])
            pygame.draw.circle(surface, (88, 144, 82), (125, 390), 38)
        else:
            surface.fill((226, 230, 185))
            pygame.draw.rect(surface, (91, 169, 196), (0, 445, 1024, 155))
            pygame.draw.ellipse(surface, (203, 176, 113), (-80, 410, 620, 130))
            pygame.draw.circle(surface, (249, 210, 88), (865, 130), 44)

    def _draw_penguin(self, surface: pygame.Surface) -> None:
        dark = (48, 52, 58)
        belly = (255, 251, 235)
        beak = (243, 154, 56)
        if self._swimming:
            cx = 510 + int(math.sin(self._time * 1.0) * 55)
            cy = 330 + int(math.sin(self._time * 1.7) * 18)
            flap = int(math.sin(self._time * 5.0) * 18)
            # Trailing bubbles show the penguin is moving through water.
            for index in range(4):
                bx = cx - 90 - index * 22
                by = cy - 6 + int(math.sin(self._time * 3 + index) * 6)
                pygame.draw.circle(surface, (221, 240, 250), (bx, by), 6 - index, 2)
            inked_limb(surface, beak, [(cx - 68, cy + 10), (cx - 91, cy + 22)], [7], outline=2)
            inked_limb(surface, beak, [(cx - 68, cy - 3), (cx - 90, cy - 15)], [7], outline=2)
            inked_limb(surface, dark, [(cx + 3, cy), (cx + 55, cy + 34 + flap)], [17, 12])
            inked_ellipse(surface, dark, (cx - 72, cy - 34, 144, 68))
            pygame.draw.ellipse(surface, belly, (cx - 48, cy - 8, 92, 36))
            inked_polygon(surface, beak, [(cx + 70, cy - 2), (cx + 94, cy + 2), (cx + 70, cy + 8)], outline=2)
            pygame.draw.circle(surface, (255, 255, 255), (cx + 50, cy - 10), 7)
            pygame.draw.circle(surface, (52, 44, 53), (cx + 52, cy - 10), 4)
            inked_limb(surface, dark, [(cx - 18, cy), (cx - 68, cy - 37 - flap)], [17, 12])
            return
        cx, cy = 510, 340
        waddle = int(math.sin(self._time * 2.1) * 4)
        x = cx + waddle
        pygame.draw.ellipse(surface, (106, 81, 71), (x - 58, 418, 116, 16))
        for fx in (x - 26, x + 26):
            inked_ellipse(surface, beak, (fx - 19, cy + 70, 38, 16), outline=2)
        inked_limb(surface, dark, [(x - 43, cy - 35), (x - 80, cy + 30)], [17, 12])
        inked_limb(surface, dark, [(x + 43, cy - 35), (x + 80, cy + 30)], [17, 12])
        inked_ellipse(surface, dark, (x - 50, cy - 105, 100, 190))
        pygame.draw.ellipse(surface, belly, (x - 35, cy - 58, 70, 120))
        inked_circle(surface, dark, (x, cy - 98), 48)
        pygame.draw.ellipse(surface, belly, (x - 27, cy - 96, 54, 45))
        pygame.draw.ellipse(surface, (106, 112, 122), (x - 30, cy - 132, 24, 12))
        for ex in (-15, 15):
            pygame.draw.circle(surface, (52, 44, 53), (x + ex, cy - 100), 6)
            pygame.draw.circle(surface, (255, 255, 255), (x + ex + 2, cy - 102), 2)
        inked_polygon(surface, beak, [(x - 11, cy - 86), (x + 11, cy - 86), (x, cy - 72)], outline=2)
        pygame.draw.circle(surface, (253, 164, 175), (x - 22, cy - 80), 5)
        pygame.draw.circle(surface, (253, 164, 175), (x + 22, cy - 80), 5)

    def _draw_feather_reveal(self, surface: pygame.Surface) -> None:
        if self._feather_age <= 0:
            return
        panel = pygame.Rect(370, 175, 280, 105)
        shadow = pygame.Surface((panel.width + 10, panel.height + 10), pygame.SRCALPHA)
        pygame.draw.rect(shadow, (40, 28, 20, 28), shadow.get_rect(), border_radius=20)
        surface.blit(shadow, (panel.x - 5, panel.y + 4))
        pygame.draw.rect(surface, (255, 250, 230), panel, border_radius=20)
        pygame.draw.rect(surface, (69, 67, 65), panel, 3, border_radius=20)
        for row in range(3):
            for col in range(7):
                x = 396 + col * 33 + (row % 2) * 15
                y = 198 + row * 25
                pygame.draw.ellipse(surface, (54, 63, 70), (x, y, 25, 42))
                pygame.draw.ellipse(surface, (80, 90, 95, 60), (x + 4, y + 6, 12, 20))
        pygame.draw.rect(surface, (242, 205, 95), (390, 262, 240, 10), border_radius=5)
        pygame.draw.rect(surface, (255, 245, 180, 60), (390, 262, 240, 4), border_radius=5)

    def _draw_breeding_reveal(self, surface: pygame.Surface) -> None:
        if self._breeding_age <= 0:
            return
        if self._breeding_state == 0:
            for index in range(5):
                x = 390 + index * 58
                pygame.draw.ellipse(surface, (47, 56, 64), (x, 350, 32, 65))
                pygame.draw.ellipse(surface, (242, 242, 235), (x + 7, 375, 18, 28))
                pygame.draw.ellipse(surface, (155, 124, 88), (x - 8, 414, 48, 12))
        else:
            x, y = 610, 405
            pygame.draw.ellipse(surface, (47, 56, 64), (x - 28, y - 70, 56, 100))
            pygame.draw.ellipse(surface, (242, 242, 235), (x - 16, y - 40, 32, 52))
            pygame.draw.ellipse(surface, (248, 241, 210), (x - 11, y + 8, 22, 29))
            pygame.draw.line(surface, (236, 156, 53), (x - 19, y + 30), (x - 5, y + 20), 6)
            pygame.draw.line(surface, (236, 156, 53), (x + 19, y + 30), (x + 5, y + 20), 6)

    def _draw_hotspots(self, surface: pygame.Surface) -> None:
        for index, item in enumerate(DISCOVERIES):
            draw_discovery_token(
                surface,
                item.center,
                selected=index == self._selected,
                hovered=index == self._hovered,
                recently_activated=item.caption_key == self._caption_key,
                icon=lambda target, center, item=item: self._draw_icon(
                    target,
                    center,
                    item.discovery_id,
                ),
                token_shape=TOKEN_SHAPE_FELT_TAG,
            )

    def _draw_icon(
        self,
        surface: pygame.Surface,
        center: tuple[int, int],
        discovery_id: str,
    ) -> None:
        cx, cy = center[0], center[1] + 4  # sit below the felt tag's pin
        center = (cx, cy)
        if discovery_id == "swim":
            pygame.draw.ellipse(surface, (52, 86, 108), (cx - 25, cy - 9, 50, 22))
            pygame.draw.line(surface, (52, 86, 108), (cx - 5, cy), (cx - 26, cy - 20), 7)
            pygame.draw.line(surface, (52, 86, 108), (cx + 5, cy), (cx + 26, cy + 20), 7)
        elif discovery_id == "feathers":
            for offset in (-16, 0, 16):
                pygame.draw.ellipse(surface, (50, 58, 64), (cx + offset - 9, cy - 20, 18, 40))
        elif discovery_id == "world":
            pygame.draw.circle(surface, (93, 163, 198), (cx, cy), 22)
            pygame.draw.arc(surface, (115, 153, 83), (cx - 15, cy - 15, 30, 30), 0.2, 2.7, 6)
            pygame.draw.line(surface, (247, 205, 72), (cx - 26, cy + 4), (cx + 26, cy + 4), 3)
        else:
            pygame.draw.ellipse(surface, (248, 241, 210), (cx - 11, cy - 8, 22, 29))
            pygame.draw.line(surface, (236, 156, 53), (cx - 20, cy + 20), (cx - 5, cy + 7), 5)
            pygame.draw.line(surface, (236, 156, 53), (cx + 20, cy + 20), (cx + 5, cy + 7), 5)

    def _draw_caption(self, surface: pygame.Surface) -> None:
        draw_caption_ribbon(
            surface,
            self.context.typography,
            self.context.resources.text(self._caption_key),
        )
