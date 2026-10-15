"""Acquario Magico — shared control-kit wiring (ADR 0037).

* bottom bar: a ``ToolStrip`` (Creatures / Feed / Bubbles) plus a Day/Night
  ``PillButton`` toggle — toggling day and night never changes the tool;
* top bar: the optional mission ``PromptBanner`` (picture + short text, with a
  hint button), its ``ProgressDots`` and a stars ``HudChip``;
* the tank itself joins focus traversal through ``TankCursor``: keyboard and
  controller users steer a cursor in the water and press Space/Enter/south
  to act there, exactly like a tap.

Rules stay in the session/mission director; the app owns what each control
does. Every control lives outside the protected Home/Back region.
"""

from __future__ import annotations

from collections.abc import Callable

import pygame

from greia_platform.activity_controls import (
    Align,
    ButtonRole,
    ControlKit,
    ControlLayer,
    ControlLayout,
    HudChip,
    PillButton,
    ProgressDots,
    PromptBanner,
    ToolStrip,
)
from greia_platform.localization import LocalizationError

if __package__:
    from .acquarium_assets import AquariumAssetCache
    from .acquarium_content import (
        MISSIONS_PER_PEARL,
        REFERENCE_HEIGHT,
        REFERENCE_WIDTH,
        SPECIES,
        SPECIES_BY_ID,
        TOOL_IDS,
        ToolIndex,
    )
else:
    from acquarium_assets import AquariumAssetCache
    from acquarium_content import (
        MISSIONS_PER_PEARL,
        REFERENCE_HEIGHT,
        REFERENCE_WIDTH,
        SPECIES,
        SPECIES_BY_ID,
        TOOL_IDS,
        ToolIndex,
    )

TANK_ID = "tank"
DAY_NIGHT_ID = "daynight"
CAST_HEIGHT = 150
CAST_MIDBOTTOM = (66, REFERENCE_HEIGHT)
# Tito stands in the bottom-left corner; the toolbar starts to his right.
_TOOLBAR_LEFT = 128
_ICON = 40


class TankCursor:
    """Focus target for the water: the kit draws its focus ring as the cursor.

    It is never hit by pointer input (taps act where they land); keyboard and
    controller activation acts at the cursor through ``on_activate``.
    """

    def __init__(self, position: Callable[[], tuple[int, int]], on_activate: Callable[[], object]) -> None:
        self._position = position
        self._on_activate = on_activate
        self.enabled = True

    @property
    def control_id(self) -> str:
        return TANK_ID

    @property
    def rect(self) -> pygame.Rect:
        x, y = self._position()
        return pygame.Rect(x - 24, y - 24, 48, 48)

    @property
    def focusable(self) -> bool:
        return True

    @property
    def focus_radius(self) -> int:
        return 24

    def contains(self, point: tuple[int, int]) -> bool:
        return False

    def activate(self) -> bool:
        self._on_activate()
        return True


class AquariumControls:
    """Own the aquarium's kit controls and their ``ControlLayer``."""

    def __init__(
        self,
        kit: ControlKit,
        resources,
        layout: ControlLayout,
        assets: AquariumAssetCache,
        *,
        cursor: Callable[[], tuple[int, int]],
        on_tool: Callable[[int], object],
        on_day_night: Callable[[], object],
        on_tank: Callable[[], object],
        on_hint: Callable[[], object],
    ) -> None:
        self._kit = kit
        self._resources = resources
        self._assets = assets
        self._on_tool = on_tool
        self._glow_mode: bool | None = None
        self._spawn_species: str | None = None
        self._mission_key: tuple[str, str] | None = None
        self._mission_icons: dict[tuple[str, str], pygame.Surface | None] = {}

        self.tools: ToolStrip = kit.tool_strip(
            "tool",
            [
                (TOOL_IDS[ToolIndex.SPAWN], self._label("tool.add_fish"), self._species_icon(SPECIES[0]["id"])),
                (TOOL_IDS[ToolIndex.FEED], self._label("tool.feed"), assets.scaled("fish_food.png", _ICON, _ICON)),
                (TOOL_IDS[ToolIndex.BUBBLES], self._label("tool.bubbles"), self._bubbles_icon()),
            ],
            on_select=self._select_tool,
        )
        self.day_night: PillButton = kit.pill_button(
            DAY_NIGHT_ID,
            pygame.Rect(0, 0, 160, 64),
            label=self._label("tool.day"),
            icon=assets.shared_fit("prop.nature.sun", (_ICON, _ICON)),
            on_activate=on_day_night,
        )
        self.mission: PromptBanner = kit.prompt_banner(
            "mission",
            pygame.Rect(0, 0, 420, 60),
            replay_icon=kit.glyph("hint", 30),
            on_replay=on_hint,
            text_size=24,
        )
        self.dots: ProgressDots = kit.progress_dots("mission.dots", pygame.Rect(0, 0, 96, 40), total=MISSIONS_PER_PEARL)
        self.stars: HudChip = kit.hud_chip("hud.stars", pygame.Rect(0, 0, 110, 52), icon=kit.star(36))
        self.tank = TankCursor(cursor, on_tank)
        self.layer: ControlLayer = kit.layer(
            (
                self.tank,
                *self.mission.controls,
                self.dots,
                self.stars,
                *self.tools.controls,
                self.day_night,
            ),
            layer_id="acquario.controls",
            initial_focus=TANK_ID,
        )
        self._layout = layout
        self.set_mission(None, None, 0)
        self.set_stars(0)
        self.relayout(layout)

    # -- helpers -----------------------------------------------------------

    def _label(self, key: str) -> str:
        if self._resources is None:
            return ""
        try:
            return self._resources.text(key).strip()
        except LocalizationError:
            return ""

    def _species_icon(self, species_id: str, box: tuple[int, int] = (46, _ICON)) -> pygame.Surface | None:
        species = SPECIES_BY_ID[species_id]
        return self._assets.creature(species, "default", box)

    def _bubbles_icon(self) -> pygame.Surface:
        icon = pygame.Surface((_ICON + 4, _ICON), pygame.SRCALPHA)
        for size, pos in ((22, (0, 14)), (16, (24, 2)), (12, (28, 24))):
            bubble = self._assets.bubble(size)
            if bubble is not None:
                icon.blit(bubble, pos)
        return icon

    def _select_tool(self, tool_id: str) -> None:
        for index, name in TOOL_IDS.items():
            if name == tool_id:
                self._on_tool(index)
                return

    # -- geometry ----------------------------------------------------------

    def relayout(self, layout: ControlLayout) -> None:
        """Bottom: tools + day/night right of Tito. Top: mission, dots, stars."""

        self._layout = layout
        height = layout.control_height(66, maximum=86)
        bar = layout.bottom_bar(height)
        bar = pygame.Rect(_TOOLBAR_LEFT, bar.top, layout.width - layout.margin - _TOOLBAR_LEFT, height)
        controls = [*self.tools.slots, self.day_night]
        for control in controls:
            control.rect = pygame.Rect(0, 0, 10, height)
        preferred = [max(150, control.preferred_width()) for control in controls]
        minimum = [control.compact_width() for control in controls]
        widths, compact = layout.fit(bar.width, preferred, minimum, 14)
        for control, rect in zip(controls, layout.row(bar, widths, align=Align.CENTER, gap=14)):
            control.rect = rect
            control.compact = compact

        top_h = layout.control_height(58, maximum=74)
        top = layout.top_bar(top_h)
        chip_h = max(40, top_h - 8)
        self.stars.rect = pygame.Rect(0, 0, 10, chip_h)
        chip_w = self.stars.preferred_width(digits=2)
        self.stars.rect = pygame.Rect(top.right - chip_w, top.centery - chip_h // 2, chip_w, chip_h)
        dots_h = max(26, round(top_h * 0.56))
        dots_w = ProgressDots.preferred_width(MISSIONS_PER_PEARL, dots_h)
        # The stars chip is hidden until the first pearl; give its room to the banner.
        right = self.stars.rect.left - 16 if self.stars.visible else top.right
        banner_w = max(160, min(600, right - dots_w - 12 - top.left))
        self.mission.rect = pygame.Rect(top.left, top.top, banner_w, top_h)
        self.dots.rect = pygame.Rect(self.mission.rect.right + 12, top.centery - dots_h // 2, dots_w, dots_h)
        self.layer.invalidation.invalidate()

    @property
    def tank_bounds(self) -> pygame.Rect:
        """Water area where taps/cursor act (between the top bar and the toolbar)."""

        top = max(self.mission.rect.bottom, self.stars.rect.bottom) + 6
        bottom = min(control.rect.top for control in (*self.tools.slots, self.day_night)) - 6
        return pygame.Rect(0, top, REFERENCE_WIDTH, max(1, bottom - top))

    def blocks_play(self, point: tuple[int, int]) -> bool:
        """True when a tap lands on a visible display-only HUD element."""

        for control in (self.mission, self.dots, self.stars):
            if control.visible and control.rect.collidepoint(point):
                return True
        return False

    # -- state mirrors (only rebuild when something changed) ----------------

    def sync_tool(self, tool_index: int) -> None:
        tool_id = TOOL_IDS.get(tool_index)
        if tool_id is not None and tool_id != self.tools.selected:
            self.tools.select(tool_id)
            self.layer.invalidation.invalidate()

    def sync_spawn_species(self, species_index: int) -> None:
        species_id = SPECIES[species_index % len(SPECIES)]["id"]
        if species_id == self._spawn_species:
            return
        self._spawn_species = species_id
        slot = self.tools.slots[ToolIndex.SPAWN]
        slot.icon = self._species_icon(species_id)
        self.layer.invalidation.invalidate()

    def sync_day_night(self, glow_mode: bool) -> None:
        if glow_mode == self._glow_mode:
            return
        self._glow_mode = glow_mode
        if glow_mode:
            self.day_night.label = self._label("tool.night")
            self.day_night.icon = self._assets.shared_fit("prop.vocab.moon", (_ICON, _ICON))
        else:
            self.day_night.label = self._label("tool.day")
            self.day_night.icon = self._assets.shared_fit("prop.nature.sun", (_ICON, _ICON))
        self.layer.invalidation.invalidate()

    def set_mission(self, kind: str | None, species_id: str | None, done: int) -> None:
        """Show (or hide) the invitation banner; content is built once per mission."""

        visible = kind is not None and species_id is not None
        self.mission.visible = visible
        if self.mission.replay is not None:
            self.mission.replay.visible = visible
        self.dots.visible = visible
        self.dots.set_progress(done)
        if visible:
            key = (str(kind), str(species_id))
            if key != self._mission_key:
                self._mission_key = key
                self.mission.set_text(self._label(f"mission.{kind}.{species_id}"), icon=self._mission_icon(key))
        else:
            self._mission_key = None
        self.layer.ensure_focus()
        self.layer.invalidation.invalidate()

    def _mission_icon(self, key: tuple[str, str]) -> pygame.Surface | None:
        if key in self._mission_icons:
            return self._mission_icons[key]
        kind, species_id = key
        creature = self._species_icon(species_id, (58, 46))
        icon: pygame.Surface | None = creature
        if kind == "feed" and creature is not None:
            food = self._assets.scaled("fish_food.png", 36, 36)
            icon = pygame.Surface((creature.get_width() + 40, max(46, creature.get_height())), pygame.SRCALPHA)
            if food is not None:
                icon.blit(food, (0, (icon.get_height() - 36) // 2))
            icon.blit(creature, (40, (icon.get_height() - creature.get_height()) // 2))
        if len(self._mission_icons) > 2 * len(SPECIES):
            self._mission_icons.clear()
        self._mission_icons[key] = icon
        return icon

    def set_stars(self, stars: int) -> None:
        visible = stars > 0
        if visible != self.stars.visible:
            self.stars.visible = visible
            self.relayout(self._layout)
        if self.stars.value != stars:
            self.stars.value = stars
            self.layer.invalidation.invalidate()


__all__ = ["AquariumControls", "CAST_HEIGHT", "CAST_MIDBOTTOM", "DAY_NIGHT_ID", "TANK_ID", "TankCursor"]
