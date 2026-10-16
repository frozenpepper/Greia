"""Baia delle Orche — shared control-kit wiring (ADR 0037).

* bottom bar (right of Tito's corner): a ``ToolStrip`` of the four modes
  (Feed / Cuddle / Play / Song, labelled), then two round ``IconButton``
  actions: Day/Night and Tito (tells the next orca fact); neither changes
  the mode;
* Feed mode shows a small food ``ToolStrip`` in the sky (herring, salmon,
  squid): picking one drops it straight into the bay;
* Song mode turns the four sea bells into focus targets (``ExternalTarget``);
* top bar: the optional invitation ``PromptBanner`` (picture + short text and
  a hint button), its ``ProgressDots`` and ``HudChip`` counters;
* the water joins focus traversal through ``BayCursor``: keyboard and
  controller users steer a cursor and press Space/Enter/south to act there,
  exactly like a tap;
* a display-only ``KeyboardHint`` (arrows + Space keycaps) sits in the sky
  under the counters (top-right, above the water the orcas swim in): it
  teaches that the arrows move the cursor and Space acts, and the drawn key
  lights while the real key is held (ADR 0037 §4b). It is drawn into the
  app's cached HUD overlay and is not a focus or touch target.

The app owns what each control does; every control stays outside the
protected Home/Back region.
"""

from __future__ import annotations

from collections.abc import Callable
import math
import time

import pygame

from greia_platform.activity_controls import (
    Align,
    BodyShape,
    ControlKit,
    ControlLayer,
    ControlLayout,
    ExternalTarget,
    HudChip,
    IconButton,
    ProgressDots,
    PromptBanner,
    ToolStrip,
)
from greia_platform.activity_keyboard_hint import KeyboardHint, KeyCap
from greia_platform.localization import LocalizationError

try:
    from orca_assets import OrcaAssetCache
    from orca_content import (
        BELL_CENTERS,
        BELL_SIZE,
        MISSIONS_PER_STAR,
        MODE_IDS,
        ORCA_LOOKS,
        REFERENCE_HEIGHT,
        REFERENCE_WIDTH,
        FoodType,
        Tool,
    )
except ImportError:
    from .orca_assets import OrcaAssetCache
    from .orca_content import (
        BELL_CENTERS,
        BELL_SIZE,
        MISSIONS_PER_STAR,
        MODE_IDS,
        ORCA_LOOKS,
        REFERENCE_HEIGHT,
        REFERENCE_WIDTH,
        FoodType,
        Tool,
    )

BAY_ID = "bay"
DAY_NIGHT_ID = "daynight"
TITO_ID = "tito"
CAST_HEIGHT = 150
CAST_MIDBOTTOM = (66, REFERENCE_HEIGHT)
# Tito stands in the bottom-left corner; the toolbar starts to his right.
_TOOLBAR_LEFT = 132
_ICON = 40
_ROUND_ICON = 46
_FOOD_TILE = 64
# Arrows move the water cursor, Space acts there (orca_app).
KEY_HINT_KEYS = frozenset({KeyCap.UP, KeyCap.DOWN, KeyCap.LEFT, KeyCap.RIGHT, KeyCap.SPACE})
KEY_HINT_KEY = 32  # logical keycap height (legible for 4-7 year olds, still unobtrusive)
KEY_HINT_MIN_PHYSICAL = 26  # never drawn smaller than this on screen
KEY_HINT_GAP = 10  # under the top bar


class BayCursor:
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
        return BAY_ID

    @property
    def rect(self) -> pygame.Rect:
        x, y = self._position()
        return pygame.Rect(x - 26, y - 26, 52, 52)

    @property
    def focusable(self) -> bool:
        return True

    @property
    def focus_radius(self) -> int:
        return 26

    def contains(self, point: tuple[int, int]) -> bool:
        return False

    def activate(self) -> bool:
        self._on_activate()
        return True


class OrcaControls:
    """Own the bay's kit controls and their ``ControlLayer``."""

    def __init__(
        self,
        kit: ControlKit,
        resources,
        layout: ControlLayout,
        assets: OrcaAssetCache,
        *,
        cursor: Callable[[], tuple[int, int]],
        on_mode: Callable[[int], object],
        on_food: Callable[[FoodType, tuple[int, int]], object],
        on_bell: Callable[[int], object],
        on_day_night: Callable[[], object],
        on_tito: Callable[[], object],
        on_bay: Callable[[], object],
        on_hint: Callable[[], object],
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._kit = kit
        self.keys: KeyboardHint = kit.keyboard_hint("keys", pygame.Rect(0, 0, 10, 10), active=KEY_HINT_KEYS, clock=clock)
        self._resources = resources
        self._assets = assets
        self._on_mode = on_mode
        self._on_food = on_food
        self._night: bool | None = None
        self._mission_key: tuple[str, str, str] | None = None
        self._mission_icons: dict[tuple[str, str, str], pygame.Surface | None] = {}

        self.modes: ToolStrip = kit.tool_strip(
            "mode",
            [
                (MODE_IDS[Tool.FEED], self._label("tool.feed"), assets.food(FoodType.SALMON.value, _ICON)),
                (MODE_IDS[Tool.CUDDLE], self._label("tool.cuddle"), kit.glyph("heart", _ICON)),
                (MODE_IDS[Tool.PLAY], self._label("tool.play"), assets.shared_fit("prop.everyday.ball", (_ICON, _ICON))),
                (MODE_IDS[Tool.SONG], self._label("tool.sing"), assets.shared_fit("fx.note_burst", (_ICON + 6, _ICON))),
            ],
            on_select=self._select_mode,
        )
        self.foods: ToolStrip = kit.tool_strip(
            "food",
            [(food.value, "", assets.food(food.value, _FOOD_TILE - 18)) for food in FoodType],
            shape=BodyShape.TILE,
            selected=FoodType.SALMON.value,
            on_select=self._select_food,
        )
        for slot in self.foods.slots:
            slot.compact = True
        # One-shot actions are round buttons beside the four labelled modes.
        self.day_night: IconButton = kit.icon_button(
            DAY_NIGHT_ID,
            pygame.Rect(0, 0, 66, 66),
            icon=assets.shared_fit("prop.nature.sun", (_ROUND_ICON, _ROUND_ICON)),
            on_activate=on_day_night,
        )
        self.tito: IconButton = kit.icon_button(
            TITO_ID,
            pygame.Rect(0, 0, 66, 66),
            icon=kit.art.fit("character.tito", _ROUND_ICON + 4, variant="happy"),
            on_activate=on_tito,
        )
        self.bells: tuple[ExternalTarget, ...] = tuple(
            ExternalTarget(
                f"bell.{index}",
                pygame.Rect(cx - BELL_SIZE // 2, cy - BELL_SIZE // 2, BELL_SIZE, BELL_SIZE),
                (lambda chosen=index: on_bell(chosen)),
                focus_radius=BELL_SIZE // 2,
            )
            for index, (cx, cy) in enumerate(BELL_CENTERS)
        )
        self.mission: PromptBanner = kit.prompt_banner(
            "mission",
            pygame.Rect(0, 0, 420, 60),
            replay_icon=kit.glyph("hint", 30),
            on_replay=on_hint,
            text_size=24,
        )
        self.dots: ProgressDots = kit.progress_dots("mission.dots", pygame.Rect(0, 0, 96, 40), total=MISSIONS_PER_STAR)
        self.fed: HudChip = kit.hud_chip("hud.fed", pygame.Rect(0, 0, 110, 52), icon=assets.food(FoodType.SALMON.value, 34))
        self.cuddles: HudChip = kit.hud_chip("hud.cuddles", pygame.Rect(0, 0, 110, 52), icon=kit.glyph("heart", 34))
        self.stars: HudChip = kit.hud_chip("hud.stars", pygame.Rect(0, 0, 110, 52), icon=kit.star(36))
        self.stars.visible = False
        self.bay = BayCursor(cursor, on_bay)
        self.layer: ControlLayer = kit.layer(
            (
                self.bay,
                *self.bells,
                *self.foods.controls,
                *self.mission.controls,
                self.dots,
                self.fed,
                self.cuddles,
                self.stars,
                *self.modes.controls,
                self.day_night,
                self.tito,
            ),
            layer_id="orca.controls",
            initial_focus=BAY_ID,
        )
        self._layout = layout
        self.set_mission(None, None, None, 0)
        self.sync_mode(Tool.FEED)
        self.relayout(layout)

    # -- helpers -----------------------------------------------------------

    def _label(self, key: str) -> str:
        if self._resources is None:
            return ""
        try:
            return self._resources.text(key).strip()
        except LocalizationError:
            return ""

    def _select_mode(self, mode_id: str) -> None:
        for index, name in MODE_IDS.items():
            if name == mode_id:
                self._on_mode(index)
                return

    def _select_food(self, food_id: str) -> None:
        for slot in self.foods.slots:
            if slot.tool_id == food_id:
                self._on_food(FoodType(food_id), (slot.rect.centerx, slot.rect.bottom + 8))
                return

    # -- geometry ----------------------------------------------------------

    def relayout(self, layout: ControlLayout) -> None:
        """Bottom: modes + day/night + Tito right of his corner. Top: banner, dots, chips."""

        self._layout = layout
        height = layout.control_height(66, maximum=86)
        bar = layout.bottom_bar(height)
        bar = pygame.Rect(_TOOLBAR_LEFT, bar.top, layout.width - layout.margin - _TOOLBAR_LEFT, height)
        gap = 10
        self.tito.rect = pygame.Rect(bar.right - height, bar.top, height, height)
        self.day_night.rect = pygame.Rect(self.tito.rect.left - gap - height, bar.top, height, height)
        modes = pygame.Rect(bar.left, bar.top, self.day_night.rect.left - gap * 2 - bar.left, height)
        slots = list(self.modes.slots)
        for slot in slots:
            slot.rect = pygame.Rect(0, 0, 10, height)
        preferred = [max(128, slot.preferred_width()) for slot in slots]
        minimum = [slot.compact_width() for slot in slots]
        widths, compact = layout.fit(modes.width, preferred, minimum, gap)
        for slot, rect in zip(slots, layout.row(modes, widths, align=Align.CENTER, gap=gap)):
            slot.rect = rect
            slot.compact = compact

        top_h = layout.control_height(58, maximum=74)
        top = layout.top_bar(top_h)
        # On very small screens the invitation picture needs the room more
        # than the running counters do (the star chip always stays).
        roomy = layout.scale >= 0.7
        self.fed.visible = roomy
        self.cuddles.visible = roomy
        chip_h = max(40, top_h - 8)
        right = top.right
        for chip in (self.stars, self.cuddles, self.fed):
            if not chip.visible:
                continue
            chip.rect = pygame.Rect(0, 0, 10, chip_h)
            width = chip.preferred_width(digits=3 if chip is not self.stars else 2)
            chip.rect = pygame.Rect(right - width, top.centery - chip_h // 2, width, chip_h)
            right = chip.rect.left - 10
        dots_h = max(26, round(top_h * 0.56))
        dots_w = ProgressDots.preferred_width(MISSIONS_PER_STAR, dots_h)
        banner_w = max(160, min(560, right - 6 - dots_w - 12 - top.left))
        self.mission.rect = pygame.Rect(top.left, top.top, banner_w, top_h)
        self.dots.rect = pygame.Rect(self.mission.rect.right + 12, top.centery - dots_h // 2, dots_w, dots_h)

        key = max(KEY_HINT_KEY, math.ceil(KEY_HINT_MIN_PHYSICAL / max(0.01, layout.scale)))
        width, height = KeyboardHint.preferred_size(KEY_HINT_KEYS, key=key)
        self.keys.rect = pygame.Rect(top.right - width, top.bottom + KEY_HINT_GAP, width, height)

        tile = layout.control_height(_FOOD_TILE, maximum=86)
        tray_w = tile * len(self.foods.slots) + 12 * (len(self.foods.slots) - 1)
        tray_top = top.bottom + 14
        for index, slot in enumerate(self.foods.slots):
            slot.rect = pygame.Rect(REFERENCE_WIDTH // 2 - tray_w // 2 + index * (tile + 12), tray_top, tile, tile)
        self.layer.invalidation.invalidate()

    @property
    def keys_look(self) -> tuple:
        """What the keyboard hint shows (part of the cached HUD overlay key)."""

        return (self.keys.visible, self.keys.lit if self.keys.visible else frozenset())

    @property
    def toolbar_top(self) -> int:
        return min(control.rect.top for control in (*self.modes.slots, self.day_night, self.tito))

    @property
    def bay_bounds(self) -> pygame.Rect:
        """Area where taps/cursor act (between the top bar and the toolbar)."""

        top = self.mission.rect.bottom + 6
        bottom = self.toolbar_top - 6
        return pygame.Rect(0, top, REFERENCE_WIDTH, max(1, bottom - top))

    def blocks_play(self, point: tuple[int, int]) -> bool:
        """True when a tap lands on a visible display-only HUD element."""

        for control in (self.mission, self.dots, self.fed, self.cuddles, self.stars):
            if control.visible and control.rect.collidepoint(point):
                return True
        return False

    # -- state mirrors (only rebuild when something changed) ----------------

    def sync_mode(self, mode: int) -> None:
        mode_id = MODE_IDS.get(mode)
        if mode_id is not None and mode_id != self.modes.selected:
            self.modes.select(mode_id)
        feeding = mode == Tool.FEED
        for slot in self.foods.slots:
            slot.visible = feeding
        singing = mode == Tool.SONG
        for bell in self.bells:
            bell.enabled = singing
        self.layer.ensure_focus()
        self.layer.invalidation.invalidate()

    def sync_food(self, food: FoodType) -> None:
        if food.value != self.foods.selected:
            self.foods.select(food.value)
            slot = self.modes.slots[Tool.FEED]
            slot.icon = self._assets.food(food.value, _ICON)
            self.layer.invalidation.invalidate()

    def sync_day_night(self, night: bool) -> None:
        if night == self._night:
            return
        self._night = night
        art = "prop.vocab.moon" if night else "prop.nature.sun"
        self.day_night.icon = self._assets.shared_fit(art, (_ROUND_ICON, _ROUND_ICON))
        self.layer.invalidation.invalidate()

    def set_counters(self, fed: int, cuddles: int, stars: int) -> None:
        changed = False
        for chip, value in ((self.fed, fed), (self.cuddles, cuddles), (self.stars, stars)):
            if chip.value != value:
                chip.value = value
                changed = True
        visible = stars > 0
        if visible != self.stars.visible:
            self.stars.visible = visible
            self.relayout(self._layout)
        if changed:
            self.layer.invalidation.invalidate()

    def set_mission(self, kind: str | None, orca_id: str | None, food: str | None, done: int) -> None:
        """Show (or hide) the invitation banner; content is built once per mission."""

        visible = kind is not None and orca_id is not None
        self.mission.visible = visible
        if self.mission.replay is not None:
            self.mission.replay.visible = visible
        self.dots.visible = visible
        self.dots.set_progress(done)
        if visible:
            key = (str(kind), str(orca_id), str(food or ""))
            if key != self._mission_key:
                self._mission_key = key
                self.mission.set_text(self._label(f"mission.{kind}.{orca_id}"), icon=self._mission_icon(key))
        else:
            self._mission_key = None
        self.layer.ensure_focus()
        self.layer.invalidation.invalidate()

    def _mission_icon(self, key: tuple[str, str, str]) -> pygame.Surface | None:
        if key in self._mission_icons:
            return self._mission_icons[key]
        kind, orca_id, food = key
        look = ORCA_LOOKS.get(orca_id)
        orca = self._assets.fitted(look.art, (70, 44)) if look is not None else None
        extra: pygame.Surface | None = None
        if kind == "feed" and food:
            extra = self._assets.food(food, 40)
        elif kind == "jump":
            extra = self._assets.shared_fit("fx.splash", (40, 40))
        icon = orca
        if orca is not None and extra is not None:
            icon = pygame.Surface((orca.get_width() + extra.get_width() + 6, max(46, orca.get_height(), extra.get_height())), pygame.SRCALPHA)
            icon.blit(orca, (0, (icon.get_height() - orca.get_height()) // 2))
            icon.blit(extra, (orca.get_width() + 6, (icon.get_height() - extra.get_height()) // 2))
        if len(self._mission_icons) > 24:
            self._mission_icons.clear()
        self._mission_icons[key] = icon
        return icon


__all__ = [
    "BAY_ID",
    "BayCursor",
    "CAST_HEIGHT",
    "CAST_MIDBOTTOM",
    "DAY_NIGHT_ID",
    "OrcaControls",
    "TITO_ID",
]
