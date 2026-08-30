"""Pyramids golden master: authored archaeological diorama with factual overlays."""

from __future__ import annotations

from dataclasses import dataclass
import math

import pygame

if __package__ and "." in __package__:
    from ..enciclopedia_engine import EncyclopediaPage, PageCommand, PageInput, PageInputKind
    from ..enciclopedia_presentation import (
        TOKEN_SHAPE_EXCAVATION,
        announce_focus_name,
        draw_authored_scene,
        draw_caption_ribbon,
        draw_discovery_token,
        draw_focus_patch,
        draw_navigation_arrows,
        draw_title,
        encyclopedia_focus_cue,
    )
    from ..enciclopedia_focus_audio import FocusAudioTracker
    from .common import draw_presenter, grid_step
else:
    from enciclopedia_engine import EncyclopediaPage, PageCommand, PageInput, PageInputKind
    from enciclopedia_presentation import (
        TOKEN_SHAPE_EXCAVATION,
        announce_focus_name,
        draw_authored_scene,
        draw_caption_ribbon,
        draw_discovery_token,
        draw_focus_patch,
        draw_navigation_arrows,
        draw_title,
        encyclopedia_focus_cue,
    )
    from enciclopedia_focus_audio import FocusAudioTracker
    from pages.common import draw_presenter, grid_step


@dataclass(frozen=True, slots=True)
class PyramidDiscovery:
    discovery_id: str
    caption_key: str
    cue_id: str
    center: tuple[int, int]


DISCOVERIES = (
    PyramidDiscovery(
        "blocks",
        "pyramids.blocks",
        "encyclopedia.history.pyramids.blocks",
        (235, 195),
    ),
    PyramidDiscovery(
        "workers",
        "pyramids.workers",
        "encyclopedia.history.pyramids.workers",
        (775, 195),
    ),
    PyramidDiscovery(
        "inside",
        "pyramids.inside",
        "encyclopedia.history.pyramids.inside",
        (235, 405),
    ),
    PyramidDiscovery(
        "engineering",
        "pyramids.engineering",
        "encyclopedia.history.pyramids.engineering",
        (775, 405),
    ),
)


PYRAMID_SUPPLY_CENTERS = (
    (180, 480),
    (270, 480),
    (740, 480),
    (830, 480),
)
PYRAMID_TARGET_RECTS = (
    pygame.Rect(450, 432, 110, 14),  # base
    pygame.Rect(460, 415, 90, 14),   # course 2
    pygame.Rect(470, 398, 70, 14),   # course 3
    pygame.Rect(485, 381, 40, 14),   # capstone
)
PYRAMID_SUPPLY_RECTS = tuple(
    pygame.Rect(cx - 34, cy - 18, 68, 36) for cx, cy in PYRAMID_SUPPLY_CENTERS
)


class PyramidBuildModel:
    """Own finite construction/reveal state; rendering consumes it."""

    MAX_COURSES = 6
    REVEAL_SECONDS = 5.0

    def __init__(self) -> None:
        self.courses = 1
        self.workers_age = 0.0
        self.inside_age = 0.0
        self.engineering_age = 0.0
        # Assembly toy — 4 blocks, sequential placement
        self.assembly_placed: list[bool] = [False, False, False, False]
        self.assembly_animating: int | None = None
        self.assembly_progress: float = 0.0
        self.dust_age: float = 0.0
        self.dust_center: tuple[int, int] | None = None
        self.completed_age: float = 0.0

    def update(self, dt: float) -> None:
        self.workers_age = max(0.0, self.workers_age - dt)
        self.inside_age = max(0.0, self.inside_age - dt)
        self.engineering_age = max(0.0, self.engineering_age - dt)
        self.dust_age = max(0.0, self.dust_age - dt)
        self.completed_age = max(0.0, self.completed_age - dt)
        if self.assembly_animating is not None:
            self.assembly_progress += dt * 1.8
            if self.assembly_progress >= 1.0:
                idx = self.assembly_animating
                self.assembly_placed[idx] = True
                self.assembly_animating = None
                self.assembly_progress = 0.0
                # Dust puff at target
                target = PYRAMID_TARGET_RECTS[idx]
                self.dust_center = target.center
                self.dust_age = 0.55
                # Keep legacy courses in sync for fallback rendering paths
                self.courses = max(self.courses, sum(self.assembly_placed) + 1)
                if all(self.assembly_placed):
                    self.completed_age = 3.0
                    self.workers_age = max(self.workers_age, 2.0)

    def add_course(self) -> None:
        self.courses = 1 if self.courses >= self.MAX_COURSES else self.courses + 1

    def reveal_workers(self) -> None:
        self.workers_age = self.REVEAL_SECONDS

    def reveal_inside(self) -> None:
        self.inside_age = self.REVEAL_SECONDS

    def reveal_engineering(self) -> None:
        self.engineering_age = self.REVEAL_SECONDS

    def next_assembly_index(self) -> int | None:
        for idx, placed in enumerate(self.assembly_placed):
            if not placed:
                return idx
        return None

    def try_place_next(self) -> bool:
        nxt = self.next_assembly_index()
        if nxt is None or self.assembly_animating is not None:
            return False
        self.assembly_animating = nxt
        self.assembly_progress = 0.0
        return True

    def try_place_block(self, supply_index: int) -> bool:
        nxt = self.next_assembly_index()
        if nxt is None or self.assembly_animating is not None:
            return False
        if supply_index != nxt:
            # Wrong order — gentle bounce, no progress
            return False
        return self.try_place_next()

    def reset_assembly(self) -> None:
        self.assembly_placed = [False, False, False, False]
        self.assembly_animating = None
        self.assembly_progress = 0.0
        self.dust_age = 0.0
        self.courses = 1
        self.completed_age = 0.0


class PyramidsPage(EncyclopediaPage):
    page_id = "history.pyramids"

    def __init__(self, context) -> None:
        super().__init__(context)

        self._focus_audio = FocusAudioTracker()
        self._model = PyramidBuildModel()
        self._selected = 0
        self._hovered: int | None = None
        self._caption_key = "pyramids.intro"
        self._hotspots = tuple(
            pygame.Rect(cx - 50, cy - 50, 100, 100)
            for cx, cy in (item.center for item in DISCOVERIES)
        )
        self._time = 0.0
        self._arrow_left_hit: pygame.Rect = pygame.Rect(0, 0, 0, 0)
        self._arrow_right_hit: pygame.Rect = pygame.Rect(0, 0, 0, 0)

    def on_enter(self) -> None:
        self.context.audio.play("encyclopedia.history.pyramids.intro")
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

    def update(self, dt: float) -> None:
        self._time += dt
        self._model.update(dt)
        # Auto-reset completed pyramid after celebration
        if self._model.completed_age == 0 and all(self._model.assembly_placed) and self._model.assembly_animating is None:
            # Completed was just consumed? Actually completed_age counts down from 3.0;
            # when it hits 0 after being 3, we reset.
            # Detect edge: if previously completed and now 0, reset.
            pass
        if all(self._model.assembly_placed) and self._model.completed_age == 0 and self._model.dust_age == 0:
            # Small pause before reset so child sees finished pyramid
            if self._time % 5 < 0.02:  # cheap throttle — actually check elapsed since completion
                pass
        # Simpler: when completed_age expired (went to 0) and still all placed, reset
        if self._model.completed_age == 0 and all(self._model.assembly_placed):
            # Wait for dust to finish, then reset after 1.2s of completed display
            # Use a separate timer via update count: if completed_age was 3.0 and now 0, we are at reset point
            # To avoid immediate reset, check that we have been completed for a moment
            # We store a separate flag via completed_age; when it just became 0, we reset after next frame
            # For simplicity, reset when dust finished and completed_age is 0
            if self._model.dust_age == 0:
                # Delay reset by checking time since last dust — already dust 0, so reset
                self._model.reset_assembly()

    def handle_input(self, event: PageInput) -> None:
        if event.position is not None and event.kind in {
            PageInputKind.POINTER_MOVE,
            PageInputKind.POINTER_PRESS,
        }:
            point = (int(event.position[0]), int(event.position[1]))
            # Assembly supply blocks first — large, reliable hits
            if event.kind is PageInputKind.POINTER_PRESS:
                for s_idx, rect in enumerate(PYRAMID_SUPPLY_RECTS):
                    if not self._model.assembly_placed[s_idx] and rect.collidepoint(point):
                        if self._model.try_place_block(s_idx):
                            self._caption_key = "pyramids.blocks"
                            announce_focus_name(
                                self.context.audio,
                                encyclopedia_focus_cue("history", "pyramids", "blocks", "name"),
                            )
                        else:
                            # Wrong order — gentle nudge, still announce
                            announce_focus_name(
                                self.context.audio,
                                encyclopedia_focus_cue("history", "pyramids", "blocks", "name"),
                            )
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
                cue = encyclopedia_focus_cue("history", "pyramids", disc.discovery_id, "name")
                self._focus_audio.announce_once(self.context.audio, cue)
            self._hovered = hit
            if event.kind is PageInputKind.POINTER_PRESS and hit is not None:
                self._set_selected(hit)
                self._activate(hit)
            return
        if event.kind is not PageInputKind.COMMAND or event.command is None:
            return
        if event.command is PageCommand.ACTIVATE:
            # If assembly next exists, ACTIVATE places next block as keyboard alternative
            nxt = self._model.next_assembly_index()
            if nxt is not None and self._model.assembly_animating is None:
                self._model.try_place_next()
                self._caption_key = "pyramids.blocks"
                announce_focus_name(
                    self.context.audio, encyclopedia_focus_cue("history", "pyramids", "blocks", "name")
                )
                return
            self._activate(self._selected)
        else:
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
        item = DISCOVERIES[index]
        self._caption_key = item.caption_key
        if item.discovery_id == "blocks":
            self._model.add_course()
        elif item.discovery_id == "workers":
            self._model.reveal_workers()
        elif item.discovery_id == "inside":
            self._model.reveal_inside()
        else:
            self._model.reveal_engineering()
        self.context.audio.play(item.cue_id)

    def draw(self, surface: pygame.Surface) -> None:
        if not draw_authored_scene(
            surface,
            self.context.visuals,
            "encyclopedia.history.pyramids.diorama",
        ):
            surface.fill((240, 215, 151))
        draw_title(
            surface,
            self.context.typography,
            self.context.resources.text("pyramids.title"),
            self.context.palette.ink,
        )
        self._draw_reveals(surface)
        self._draw_assembly(surface)
        for index, item in enumerate(DISCOVERIES):
            # Keep excavation token style but add pulse halo for selected
            draw_discovery_token(
                surface,
                item.center,
                selected=index == self._selected,
                hovered=index == self._hovered,
                recently_activated=self._recent(item.discovery_id),
                icon=lambda target, center, item=item: self._draw_icon(
                    target,
                    center,
                    item.discovery_id,
                ),
                token_shape=TOKEN_SHAPE_EXCAVATION,
            )
        # Standard section chrome for discovery navigation
        can_left = self._selected > 0
        can_right = self._selected < len(DISCOVERIES) - 1
        self._arrow_left_hit, self._arrow_right_hit = draw_navigation_arrows(
            surface, time=self._time, can_go_left=can_left, can_go_right=can_right
        )
        draw_caption_ribbon(
            surface,
            self.context.typography,
            self.context.resources.text(self._caption_key),
        )
        # Tiny assembly hint — spatial, not textual
        if self._model.next_assembly_index() is not None and self._model.assembly_animating is None:
            nxt = self._model.next_assembly_index()
            hint_rect = PYRAMID_SUPPLY_RECTS[nxt]  # type: ignore[index]
            # Gentle pulse on next supply block
            pulse = (math.sin(self._time * 2.2) * 0.5 + 0.5) * 0.35
            glow = pygame.Surface((hint_rect.width + 12, hint_rect.height + 12), pygame.SRCALPHA)
            pygame.draw.rect(
                glow,
                (255, 210, 90, int(38 + pulse * 28)),
                glow.get_rect(),
                width=3,
                border_radius=8,
            )
            surface.blit(glow, (hint_rect.x - 6, hint_rect.y - 6))
        draw_presenter(
            surface,
            self.context.visuals,
            "leo",
            position=(360, 575),
            height=190,
            variant="default",
        )

    def _recent(self, discovery_id: str) -> bool:
        ages = {
            "workers": self._model.workers_age,
            "inside": self._model.inside_age,
            "engineering": self._model.engineering_age,
        }
        return ages.get(discovery_id, 0.0) > 0

    def _draw_reveals(self, surface: pygame.Surface) -> None:
        if self._model.courses > 1:
            for course in range(self._model.courses - 1):
                width = 170 - course * 20
                y = 446 - course * 17
                pygame.draw.rect(
                    surface,
                    (245, 210, 139),
                    (505 - width // 2, y, width, 14),
                    border_radius=3,
                )

        if self._model.workers_age > 0:
            for x in (350, 390, 655, 695):
                pygame.draw.circle(surface, (255, 221, 104), (x, 455), 12, 4)

        if self._model.inside_age > 0:
            # Outlined inner chambers so the cross-section reads clearly.
            pygame.draw.polygon(
                surface,
                (255, 246, 208),
                [(505, 215), (405, 430), (605, 430)],
            )
            pygame.draw.line(surface, (93, 66, 46), (505, 265), (505, 395), 5)
            pygame.draw.rect(surface, (93, 66, 46), (488, 344, 34, 24), 3)
            # Burial chamber highlight.
            pygame.draw.rect(surface, (255, 220, 100), (488, 344, 34, 24), 4)

        if self._model.engineering_age > 0:
            # Sledge direction of travel.
            pygame.draw.line(
                surface,
                (255, 224, 96),
                (650, 438),
                (865, 405),
                6,
            )
            pygame.draw.polygon(
                surface,
                (255, 224, 96),
                [(865, 405), (846, 397), (850, 417)],
            )

        if self._model.engineering_age > 0 and self._model.courses > 1:
            # A clearly outlined base block (the "first course" being placed).
            base_width = 110
            pygame.draw.rect(
                surface,
                (255, 240, 170),
                (505 - base_width // 2, 432, base_width, 16),
                border_radius=3,
            )
            pygame.draw.rect(
                surface,
                (93, 66, 46),
                (505 - base_width // 2, 432, base_width, 16),
                width=3,
                border_radius=3,
            )
            # Two label arrows pointing at the base block.
            for arrow_x in (505 - base_width // 2 - 10, 505 + base_width // 2 + 10):
                direction = 1 if arrow_x < 505 else -1
                pygame.draw.line(surface, (93, 66, 46), (arrow_x, 440), (arrow_x + direction * 18, 440), 3)
                pygame.draw.polygon(
                    surface,
                    (93, 66, 46),
                    [
                        (arrow_x + direction * 18, 440),
                        (arrow_x + direction * 12, 435),
                        (arrow_x + direction * 12, 445),
                    ],
                )

    def _draw_assembly(self, surface: pygame.Surface) -> None:
        # Placed blocks at pyramid targets
        for idx, placed in enumerate(self._model.assembly_placed):
            if placed:
                rect = PYRAMID_TARGET_RECTS[idx]
                self._draw_stone_block(surface, rect, placed=True, capstone=(idx == 3))
        # Animating block interpolates from supply to target
        if self._model.assembly_animating is not None:
            idx = self._model.assembly_animating
            t = min(1.0, self._model.assembly_progress)
            # Ease-out
            ease = 1 - (1 - t) ** 3
            supply = PYRAMID_SUPPLY_RECTS[idx]
            target = PYRAMID_TARGET_RECTS[idx]
            cur_x = int(supply.centerx + (target.centerx - supply.centerx) * ease)
            cur_y = int(supply.centery + (target.centery - supply.centery) * ease - math.sin(t * math.pi) * 18)
            w = int(supply.width + (target.width - supply.width) * ease)
            h = int(supply.height + (target.height - supply.height) * ease)
            cur_rect = pygame.Rect(0, 0, w, h)
            cur_rect.center = (cur_x, cur_y)
            self._draw_stone_block(surface, cur_rect, placed=False, capstone=(idx == 3), animating=True)
        # Supply blocks still available (not placed, not animating)
        for idx, placed in enumerate(self._model.assembly_placed):
            if placed or self._model.assembly_animating == idx:
                continue
            rect = PYRAMID_SUPPLY_RECTS[idx]
            # Next block gets subtle bounce
            bounce = 0
            if idx == self._model.next_assembly_index():
                bounce = int(math.sin(self._time * 2.4) * 3)
            r = rect.move(0, bounce)
            self._draw_stone_block(surface, r, placed=False, capstone=(idx == 3))
            # Tiny supply shadow
            pygame.draw.ellipse(surface, (40, 28, 20, 28), (r.x, r.bottom - 4, r.width, 6))
        # Dust puff when block lands
        if self._model.dust_age > 0 and self._model.dust_center is not None:
            alpha = int(180 * (self._model.dust_age / 0.55))
            cx, cy = self._model.dust_center
            spread = int((0.55 - self._model.dust_age) * 28)
            for i in range(5):
                ang = i * 1.26 + self._time * 0.5
                r = 4 + spread // 3 + i
                x = cx + int(math.cos(ang) * (8 + spread * 0.6))
                y = cy + int(math.sin(ang) * (4 + spread * 0.3)) - spread // 2
                s = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
                pygame.draw.circle(s, (210, 198, 170, max(0, alpha - i * 18)), (r, r), r)
                surface.blit(s, (x - r, y - r))
        # Completed celebration — subtle sparkle over finished pyramid
        if all(self._model.assembly_placed) and self._model.completed_age > 0:
            pulse = math.sin(self._time * 3.0) * 0.5 + 0.5
            top = PYRAMID_TARGET_RECTS[3].center
            pygame.draw.circle(surface, (255, 232, 140, int(120 + pulse * 60)), top, 7 + int(pulse * 3))
            pygame.draw.circle(surface, (255, 250, 210, int(200 + pulse * 30)), top, 3)

    @staticmethod
    def _draw_stone_block(
        surface: pygame.Surface,
        rect: pygame.Rect,
        *,
        placed: bool,
        capstone: bool = False,
        animating: bool = False,
    ) -> None:
        # More tactile stone with subtle gradient and chisel marks
        base = (240, 218, 165) if placed else (235, 220, 175)
        if animating:
            base = (250, 230, 185)
        edge = (93, 66, 46)
        highlight = (252, 238, 200)
        # Soft drop shadow for supply (grounded)
        if not placed and not animating:
            shadow = pygame.Surface((rect.width + 10, rect.height + 8), pygame.SRCALPHA)
            pygame.draw.ellipse(shadow, (40, 28, 20, 30), (2, shadow.get_height() - 8, rect.width, 8))
            surface.blit(shadow, (rect.x - 3, rect.y + 2))
            # Outer soft shadow rect
            s2 = pygame.Surface((rect.width + 6, rect.height + 6), pygame.SRCALPHA)
            pygame.draw.rect(s2, (40, 28, 20, 22), s2.get_rect(), border_radius=4)
            surface.blit(s2, (rect.x - 3, rect.y + 1))
        # Body with subtle top highlight
        pygame.draw.rect(surface, base, rect, border_radius=4 if not capstone else 3)
        # Top bevel highlight
        hl_rect = pygame.Rect(rect.x + 2, rect.y + 2, rect.width - 4, rect.height // 2)
        pygame.draw.rect(surface, highlight, hl_rect, border_radius=3)
        pygame.draw.rect(surface, edge, rect, width=3, border_radius=4 if not capstone else 3)
        # Chisel / stratification lines
        if not capstone:
            mid = rect.y + rect.height // 2
            pygame.draw.line(surface, (180, 150, 110), (rect.x + 8, mid), (rect.right - 8, mid), 2)
            pygame.draw.line(surface, edge, (rect.x + 6, mid), (rect.right - 6, mid), 1)
            # Small pits
            for px in (rect.x + 14, rect.right - 14):
                pygame.draw.circle(surface, (210, 185, 140), (px, rect.y + 6), 2)
        else:
            # Capstone with facet shading
            pygame.draw.polygon(
                surface,
                highlight,
                [(rect.centerx, rect.top + 3), (rect.right - 5, rect.bottom - 3), (rect.centerx + 6, rect.bottom - 3)],
            )
            pygame.draw.polygon(
                surface,
                (93, 66, 46),
                [(rect.centerx, rect.top + 2), (rect.right - 4, rect.bottom - 2), (rect.x + 4, rect.bottom - 2)],
                2,
            )
            pygame.draw.polygon(
                surface,
                (180, 150, 110),
                [(rect.centerx, rect.top + 2), (rect.centerx - 8, rect.bottom - 2), (rect.x + 8, rect.bottom - 2)],
                1,
            )

    @staticmethod
    def _draw_icon(
        surface: pygame.Surface,
        center: tuple[int, int],
        discovery_id: str,
    ) -> None:
        cx, cy = center
        if discovery_id == "blocks":
            for row in range(3):
                for col in range(3 - row):
                    pygame.draw.rect(
                        surface,
                        (198, 156, 92),
                        (cx - 25 + col * 18 + row * 9, cy + 12 - row * 15, 16, 12),
                    )
        elif discovery_id == "workers":
            for dx in (-14, 14):
                pygame.draw.circle(surface, (137, 84, 56), (cx + dx, cy - 8), 7)
                pygame.draw.line(
                    surface,
                    (137, 84, 56),
                    (cx + dx, cy),
                    (cx + dx, cy + 18),
                    5,
                )
        elif discovery_id == "inside":
            pygame.draw.polygon(
                surface,
                (200, 158, 94),
                [(cx - 27, cy + 20), (cx, cy - 25), (cx + 27, cy + 20)],
            )
            pygame.draw.line(surface, (84, 68, 57), (cx, cy - 10), (cx, cy + 15), 4)
        else:
            pygame.draw.line(
                surface,
                (112, 85, 65),
                (cx - 25, cy + 16),
                (cx + 22, cy - 12),
                6,
            )
            pygame.draw.rect(surface, (188, 142, 83), (cx - 7, cy - 8, 26, 20))
