"""Shared control-kit wiring for My Cute Pet (ADR 0037).

Every interactive element goes through ``greia_platform.activity_controls``:

* adopt screen - three pet cards (``IconButton`` tiles: library pet art and
  a caption) and a primary check button;
* name screen - four picture name tags (tiles) and the check button;
* the day - the care tray (one picture tile per care, no words), the pet
  itself (``ExternalTarget``: in its home room it acts its need out again,
  while caring each activation is one care action), ``ProgressDots``
  for the day and a display-only name tag (``PromptBanner``).

Keyboard / D-pad / stick focus and the focus ring come from the kit. Focus
never jumps to the right care: it starts on the first tile and then stays
where the child left it.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence

import pygame

from greia_platform.activity_controls import (
    BodyShape,
    ButtonRole,
    ControlKit,
    ControlLayer,
    ControlLayout,
    ExternalTarget,
    IconButton,
    ProgressDots,
    PromptBanner,
)

if __package__:
    from .cucciolo_art import CuccioloArt
    from .cucciolo_content import MAX_DAY_NEEDS, NAMES, SPECIES, TRAY_ORDER, Care
    from .cucciolo_layout import (
        ADOPT_ICON,
        CONFIRM_ICON,
        CONFIRM_RECT,
        HOME_FLOOR,
        NAME_ICON,
        TRAY_ICON,
        adopt_rects,
        name_rects,
        pet_hit_rect,
        tray_rects,
    )
else:
    from cucciolo_art import CuccioloArt
    from cucciolo_content import MAX_DAY_NEEDS, NAMES, SPECIES, TRAY_ORDER, Care
    from cucciolo_layout import (
        ADOPT_ICON,
        CONFIRM_ICON,
        CONFIRM_RECT,
        HOME_FLOOR,
        NAME_ICON,
        TRAY_ICON,
        adopt_rects,
        name_rects,
        pet_hit_rect,
        tray_rects,
    )

BANNER_HEIGHT = 64
DAY_ICON = 44
TAG_ICON = 46


def care_id(care: Care) -> str:
    return f"care.{care.value}"


def species_id(species: str) -> str:
    return f"species.{species}"


def name_id(name: str) -> str:
    return f"name.{name}"


class CuccioloControls:
    """Own the kit controls and the single ``ControlLayer`` of every screen."""

    def __init__(
        self,
        kit: ControlKit,
        art: CuccioloArt,
        *,
        text: Callable[[str], str],
        on_species: Callable[[str], object],
        on_name: Callable[[str], object],
        on_confirm: Callable[[], object],
        on_care: Callable[[Care], object],
        on_pet: Callable[[], object],
    ) -> None:
        self._kit = kit
        self._art = art
        self._on_pet = on_pet
        self.species_cards: tuple[IconButton, ...] = tuple(
            kit.icon_button(
                species_id(species.species_id),
                rect,
                icon=art.pet(species.species_id, "default", ADOPT_ICON),
                shape=BodyShape.TILE,
                on_activate=(lambda s=species.species_id: on_species(s)),
            )
            for species, rect in zip(SPECIES, adopt_rects(len(SPECIES)))
        )
        self.name_tags: tuple[IconButton, ...] = tuple(
            kit.icon_button(
                name_id(name.name_id),
                rect,
                icon=art.shared(name.asset_id, NAME_ICON),
                caption=text(name.text_key),
                shape=BodyShape.TILE,
                on_activate=(lambda n=name.name_id: on_name(n)),
            )
            for name, rect in zip(NAMES, name_rects(len(NAMES)))
        )
        self.confirm: IconButton = kit.icon_button(
            "confirm",
            CONFIRM_RECT,
            icon=kit.glyph("check", CONFIRM_ICON),
            role=ButtonRole.PRIMARY,
            on_activate=on_confirm,
        )
        self.tray: dict[Care, IconButton] = {
            care: kit.icon_button(
                care_id(care),
                pygame.Rect(0, 0, 10, 10),
                icon=None,
                shape=BodyShape.TILE,
                on_activate=(lambda c=care: on_care(c)),
            )
            for care in TRAY_ORDER
        }
        # The pet itself: in its home room tapping it makes it act out its
        # need again; while caring, every tap / ACTIVATE is one care action.
        self.pet = ExternalTarget("pet", pet_hit_rect(HOME_FLOOR), on_pet, focus_radius=40)
        self.progress: ProgressDots = kit.progress_dots("progress", pygame.Rect(0, 0, 120, 40), total=MAX_DAY_NEEDS)
        self.banner: PromptBanner = kit.prompt_banner("banner", pygame.Rect(0, 0, 300, BANNER_HEIGHT))
        self.layer: ControlLayer = kit.layer((), layer_id="cucciolo.controls")
        self.sun_rect = pygame.Rect(0, 0, DAY_ICON, DAY_ICON)
        self.moon_rect = pygame.Rect(0, 0, DAY_ICON, DAY_ICON)
        self._layout: ControlLayout | None = None
        self._tray_species: str | None = None
        self._visible_tray: tuple[Care, ...] = ()

    # -- layout -------------------------------------------------------------------

    def relayout(self, layout: ControlLayout) -> None:
        """Top bar beside the protected chrome: sun, day dots, moon ... name tag."""

        self._layout = layout
        height = layout.control_height(BANNER_HEIGHT, maximum=76)
        bar = layout.top_bar(height)
        self._place_progress(bar, height)
        self._place_banner(bar, height)
        self.layer.invalidation.invalidate()

    def _place_progress(self, bar: pygame.Rect, height: int) -> None:
        dots_h = max(34, int(height * 0.62))
        dots_w = ProgressDots.preferred_width(self.progress.total, dots_h)
        icon = min(DAY_ICON, height)
        self.sun_rect = pygame.Rect(bar.left, bar.centery - icon // 2, icon, icon)
        self.progress.rect = pygame.Rect(self.sun_rect.right + 6, bar.centery - dots_h // 2, dots_w, dots_h)
        self.moon_rect = pygame.Rect(self.progress.rect.right + 6, bar.centery - icon // 2, icon, icon)

    def _place_banner(self, bar: pygame.Rect, height: int) -> None:
        width = max(150, min(self.banner.preferred_width() if self.banner.text else 260, 360))
        left_limit = self.moon_rect.right + 16
        width = min(width, max(120, bar.right - left_limit))
        self.banner.rect = pygame.Rect(bar.right - width, bar.centery - height // 2, width, height)

    def set_day_length(self, total: int) -> None:
        self.progress.total = max(1, int(total))
        self.progress.set_progress(0)
        if self._layout is not None:
            self.relayout(self._layout)

    # -- screens --------------------------------------------------------------------

    def show_adopt(self, selected: str | None, prompt: str) -> None:
        self._set_prompt(prompt, self._art.shared("icon.hud.heart", TAG_ICON))
        for card in self.species_cards:
            card.selected = card.control_id == species_id(selected or "")
        self.confirm.enabled = selected is not None
        self._show((*self.species_cards, self.confirm, self.banner), default=species_id(selected or SPECIES[0].species_id))

    def show_name(self, selected: str | None, prompt: str) -> None:
        self._set_prompt(prompt, self._art.shared("icon.hud.heart", TAG_ICON))
        for tag in self.name_tags:
            tag.selected = tag.control_id == name_id(selected or "")
        self.confirm.enabled = selected is not None
        self._show((*self.name_tags, self.confirm, self.banner), default=name_id(selected or NAMES[0].name_id))

    def show_day(self, species: str, tray: Sequence[Care], name_text: str, name_icon: pygame.Surface | None) -> None:
        """Tray for this day's cares (picture tiles), dots and the name tag."""

        if species != self._tray_species:
            for care, button in self.tray.items():
                button.icon = self._art.care_icon(care, species, TRAY_ICON)
            self._tray_species = species
        self._visible_tray = tuple(tray)
        for button in self.tray.values():
            button.visible = False
            button.enabled = False
        for care, rect in zip(self._visible_tray, tray_rects(len(self._visible_tray))):
            button = self.tray[care]
            button.rect = rect
            button.visible = True
            button.enabled = True
            button.selected = False
        self._set_prompt(name_text, name_icon)
        focused, visible = self.layer.focused_id, self.layer.focus_visible
        self.pet = ExternalTarget("pet", pet_hit_rect(HOME_FLOOR), self._on_pet, focus_radius=40)
        self.layer.set_targets(self._day_targets())
        if focused is None or not self.layer.focus(focused, visible=visible):
            self.layer.focus(care_id(self._visible_tray[0]), visible=visible)
        self.layer.ensure_focus()

    def set_tray_enabled(self, enabled: bool) -> None:
        for care in self._visible_tray:
            self.tray[care].visible = enabled
            self.tray[care].enabled = enabled
        self.layer.invalidation.invalidate()

    def start_care(self, target: pygame.Rect) -> None:
        """While caring the pet is the one target (tap / ACTIVATE = one care action)."""

        self.set_tray_enabled(False)
        visible = self.layer.focus_visible
        self.pet = ExternalTarget("pet", pygame.Rect(target), self._on_pet, focus_radius=40)
        self.layer.set_targets(self._day_targets())
        self.layer.focus("pet", visible=visible)
        self.layer.invalidation.invalidate()

    def end_care(self, *, show_tray: bool) -> None:
        self.pet = ExternalTarget("pet", pet_hit_rect(HOME_FLOOR), self._on_pet, focus_radius=40)
        self.layer.set_targets(self._day_targets())
        self.set_tray_enabled(show_tray)
        if show_tray:
            focused = self.layer.focused_id
            if focused is None or focused == "pet" or not self.layer.focus(focused, visible=self.layer.focus_visible):
                self.layer.focus(care_id(self._visible_tray[0]), visible=self.layer.focus_visible)
        self.layer.invalidation.invalidate()

    def show_none(self) -> None:
        self.layer.set_targets(())

    def set_progress(self, done: int) -> None:
        self.progress.set_progress(done)
        self.layer.invalidation.invalidate()

    def tray_rect(self, care: Care) -> pygame.Rect | None:
        button = self.tray.get(care)
        if button is None or not button.visible:
            return None
        return button.rect

    @property
    def visible_tray(self) -> tuple[Care, ...]:
        return self._visible_tray

    # -- helpers --------------------------------------------------------------------

    def _set_prompt(self, text: str, icon: pygame.Surface | None) -> None:
        self.banner.text = text
        self.banner.icon = icon
        if self._layout is not None:
            height = self.banner.rect.height
            bar = self._layout.top_bar(height)
            self._place_banner(bar, height)
        self.layer.invalidation.invalidate()

    def _day_targets(self) -> tuple:
        return (*(self.tray[c] for c in self._visible_tray), self.pet, self.progress, self.banner)

    def _show(self, targets, *, default: str) -> None:
        visible = self.layer.focus_visible
        self.layer.set_targets(targets)
        self.layer.focus(default, visible=visible)
        self.layer.ensure_focus()


__all__ = ["CuccioloControls", "care_id", "name_id", "species_id"]
