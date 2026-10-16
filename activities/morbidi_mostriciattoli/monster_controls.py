"""Shared control-kit wiring for Fluffy Monsters (ADR 0037).

Every interactive element is a kit control (or an ``ExternalTarget`` for the
monster itself) in one ``ControlLayer``, so pointer, touch, keyboard and
controller share one focus ring and activation. No control shows words:

* studio — undo, surprise (dice), save, gallery; ten picture drawers (nine
  part drawers + the name tag) and the option tiles of the open drawer, each a
  real preview of the friend wearing that part; the friend can be tickled;
* gallery — back, new friend, a count chip, saved friends as cards, page arrows;
* friend — back, share to My Creations, delete; after a save: new friend +
  gallery (+ share).

Sheets (delete, gallery full) are modal ``Overlay``s with their own layer;
backing out is always the safe choice.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass

import pygame

from greia_platform.activity_controls import (
    BodyShape,
    ButtonRole,
    ControlKit,
    ControlLayer,
    ExternalTarget,
    HudChip,
    IconButton,
    KitPointer,
    PointerPhase,
)
from greia_platform.input_core import InputEdge, SemanticAction, SemanticInputEvent
from greia_platform.ui_core import Overlay, UiEventResult

if __package__:
    from .monster_layout import FriendLayout, GalleryLayout, SheetLayout, StudioLayout
else:
    from monster_layout import FriendLayout, GalleryLayout, SheetLayout, StudioLayout

NAME_DRAWER = "name"


class PictureTile(IconButton):
    """An icon button whose cached rendering is keyed by an explicit token.

    Previews are rebuilt whenever the monster changes; keying the kit cache by
    ``token`` (instead of the icon object's identity) can never replay a stale
    picture after the old surface is released.
    """

    def __init__(self, *args, token: object = None, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.token = token

    def _content_key(self) -> tuple:
        return (self.token, self.caption, self.shape, self.role)


@dataclass(frozen=True, slots=True)
class TileSpec:
    """One option tile in the tray."""

    control_id: str
    icon: pygame.Surface | None
    token: object
    on_activate: Callable[[], object]
    selected: bool = False
    role: ButtonRole = ButtonRole.NEUTRAL


class MonsterControls:
    """Own the kit controls and the main ``ControlLayer`` for every screen."""

    def __init__(
        self,
        kit: ControlKit,
        *,
        on_undo: Callable[[], object],
        on_surprise: Callable[[], object],
        on_save: Callable[[], object],
        on_gallery: Callable[[], object],
        on_drawer: Callable[[str], object],
        on_tickle: Callable[[], object],
        on_back: Callable[[], object],
        on_new: Callable[[], object],
        on_page: Callable[[int], object],
        on_share: Callable[[], object],
        on_delete: Callable[[], object],
    ) -> None:
        self._kit = kit
        self._on_drawer = on_drawer

        def tile(control_id: str, callback, *, shape=BodyShape.TILE, role=ButtonRole.NEUTRAL) -> PictureTile:
            return PictureTile(kit.painter, control_id, pygame.Rect(0, 0, 64, 64), icon=None, shape=shape, role=role, on_activate=callback)

        self.undo = tile("undo", on_undo)
        self.surprise = tile("surprise", on_surprise)
        self.save = tile("save", on_save, role=ButtonRole.PRIMARY)
        self.gallery = tile("gallery", on_gallery)
        self.back = tile("back", on_back)
        self.new = tile("new", on_new, role=ButtonRole.PRIMARY)
        self.page_previous = tile("page.previous", lambda: on_page(-1))
        self.page_next = tile("page.next", lambda: on_page(1))
        self.share = tile("share", on_share)
        self.delete = tile("delete", on_delete)
        self.friend_gallery = tile("friend.gallery", on_gallery)
        self.chip: HudChip = kit.hud_chip("gallery.count", pygame.Rect(0, 0, 150, 60), icon=None, value=0)
        self._on_tickle = on_tickle
        self.monster = ExternalTarget("monster", pygame.Rect(0, 0, 10, 10), on_tickle, focus_radius=40)
        self.drawers: list[PictureTile] = []
        self.tray: list[PictureTile] = []
        self.cards: list[ExternalTarget] = []
        self.layer: ControlLayer = kit.layer((), layer_id="monsters.controls")
        self.screen = "studio"

    # -- helpers ---------------------------------------------------------------------------

    def glyph(self, name: str, size: int) -> pygame.Surface | None:
        return self._kit.glyph(name, size)

    def _place(self, control: PictureTile, rect: pygame.Rect, icon: str | pygame.Surface | None, ratio: float = 0.6) -> None:
        control.rect = rect
        if isinstance(icon, str):
            control.icon = self._kit.glyph(icon, int(min(rect.width, rect.height) * ratio))
            control.token = ("glyph", icon, rect.size)
        else:
            control.icon = icon
            # Non-glyph icons here are fixed pictures (dice, gallery frame): the
            # control id and size identify their content.
            control.token = ("icon", control.control_id, None if icon is None else icon.get_size())
        control.visible = True
        control.enabled = True

    def _set(self, targets: Sequence, focus: str | None, *, keep_focus: bool = False) -> None:
        previous = self.layer.focused_id
        visible = self.layer.focus_visible
        self.layer.set_targets(targets)
        ids = {target.control_id for target in targets}
        if keep_focus and previous in ids:
            self.layer.focus(previous, visible=visible)
        elif focus is not None and focus in ids:
            self.layer.focus(focus, visible=visible)
        self.layer.ensure_focus()
        self.layer.invalidation.invalidate()

    # -- studio ----------------------------------------------------------------------------

    def show_studio(
        self,
        layout: StudioLayout,
        *,
        drawer_ids: Sequence[str],
        drawer_icons: dict[str, tuple[pygame.Surface | None, object]],
        active: str,
        tiles: Sequence[TileSpec],
        surprise_icon: pygame.Surface | None,
        gallery_icon: pygame.Surface | None,
        can_undo: bool,
        can_save: bool,
        monster_rect: pygame.Rect,
        focus: str | None = None,
        keep_focus: bool = True,
    ) -> None:
        self.screen = "studio"
        self._monster(monster_rect)
        self._place(self.undo, layout.undo, "undo")
        self.undo.enabled = can_undo
        self._place(self.surprise, layout.surprise, surprise_icon)
        self._place(self.save, layout.save, "save", 0.56)
        self.save.enabled = can_save
        self._place(self.gallery, layout.gallery, gallery_icon)
        self.drawers = []
        for drawer_id, rect in zip(drawer_ids, layout.drawers):
            icon, token = drawer_icons.get(drawer_id, (None, None))
            control = PictureTile(
                self._kit.painter,
                f"drawer.{drawer_id}",
                rect,
                icon=icon,
                token=token,
                shape=BodyShape.TILE,
                selected=drawer_id == active,
                on_activate=(lambda chosen=drawer_id: self._on_drawer(chosen)),
            )
            self.drawers.append(control)
        rects = layout.tiles(len(tiles))
        self.tray = [
            PictureTile(
                self._kit.painter,
                spec.control_id,
                rect,
                icon=spec.icon,
                token=spec.token,
                shape=BodyShape.TILE,
                role=spec.role,
                selected=spec.selected,
                on_activate=spec.on_activate,
            )
            for spec, rect in zip(tiles, rects)
        ]
        targets = [self.undo, self.surprise, self.save, self.gallery, *self.drawers, self.monster, *self.tray]
        self._set(targets, focus, keep_focus=keep_focus and focus is None)

    def _monster(self, rect: pygame.Rect) -> None:
        """The friend itself is a focus target: activating it tickles."""

        self.monster = ExternalTarget("monster", rect, self._on_tickle, focus_radius=40)

    def tray_control(self, control_id: str) -> PictureTile | None:
        for control in self.tray:
            if control.control_id == control_id:
                return control
        return None

    # -- gallery ---------------------------------------------------------------------------

    def show_gallery(
        self,
        layout: GalleryLayout,
        cards: Sequence[pygame.Rect],
        *,
        on_card: Callable[[int], object],
        page: int,
        page_count: int,
        used: int,
        capacity: int,
        gallery_icon: pygame.Surface | None,
        focus_card: int | None = None,
    ) -> None:
        self.screen = "gallery"
        self._place(self.back, layout.back, "arrow_left", 0.5)
        self.chip.rect = layout.chip
        self.chip.icon = gallery_icon
        self.chip.value = f"{used}/{capacity}"
        self.cards = [
            ExternalTarget(f"card.{slot}", rect, (lambda chosen=slot: on_card(chosen)), focus_radius=22)
            for slot, rect in enumerate(cards)
        ]
        self._place(self.page_previous, layout.previous, "arrow_left", 0.5)
        self._place(self.page_next, layout.next, "arrow_right", 0.5)
        self.page_previous.visible = self.page_next.visible = page_count > 1
        self.page_previous.enabled = page > 0
        self.page_next.enabled = page < page_count - 1
        targets = [self.back, self.chip, *self.cards, self.page_previous, self.page_next]
        focus = f"card.{focus_card}" if focus_card is not None and focus_card < len(cards) else None
        self._set(targets, focus or ("card.0" if cards else "back"))

    def focused_card(self) -> int | None:
        focused = self.layer.focused_id
        if focused and focused.startswith("card."):
            return int(focused.split(".")[1])
        return None

    # -- one friend ----------------------------------------------------------------------------

    def show_friend(
        self,
        layout: FriendLayout,
        *,
        share_available: bool,
        celebrating: bool,
        gallery_icon: pygame.Surface | None,
        monster_rect: pygame.Rect,
        focus: str | None = None,
    ) -> None:
        self.screen = "celebrate" if celebrating else "friend"
        self._monster(monster_rect)
        self._place(self.share, layout.share, "share", 0.58)
        self.share.visible = share_available
        targets: list = []
        if celebrating:
            self._place(self.new, layout.new, "new", 0.56)
            self._place(self.friend_gallery, layout.gallery, gallery_icon)
            targets = [self.monster, *([self.share] if share_available else []), self.friend_gallery, self.new]
            default = "new"
        else:
            self._place(self.back, layout.back, "arrow_left", 0.5)
            self._place(self.delete, layout.delete, "trash", 0.56)
            targets = [self.back, self.monster, *([self.share] if share_available else []), self.delete]
            default = "monster"
        self._set(targets, focus or default)

    def hide_all(self) -> None:
        self._set([], None)


class MonsterSheet(Overlay):
    """Small modal sheet: its own ``ControlLayer`` above a drawn backdrop.

    A pointer press and release outside ``panel`` (or CANCEL — Escape / east
    face button) chooses the safe option, so a child can always back out.
    """

    def __init__(
        self,
        sheet_id: str,
        layer: ControlLayer,
        panel: pygame.Rect,
        *,
        on_dismiss: Callable[[], object],
        draw_backdrop: Callable[[pygame.Surface], object],
    ) -> None:
        self._id = sheet_id
        self.layer = layer
        self.panel = pygame.Rect(panel)
        self._on_dismiss = on_dismiss
        self._draw_backdrop = draw_backdrop
        self._outside_down = False

    @property
    def surface_id(self) -> str:
        return self._id

    def dismiss(self) -> None:
        self._on_dismiss()

    def handle_event(self, event: object) -> UiEventResult:
        if isinstance(event, KitPointer):
            inside = self.panel.collidepoint(event.position) or self.layer.hit(event.position) is not None
            if event.phase is PointerPhase.DOWN:
                self._outside_down = not inside
                if not inside:
                    return UiEventResult.HANDLED
            elif event.phase is PointerPhase.UP and self._outside_down:
                self._outside_down = False
                if not inside:
                    self._on_dismiss()
                return UiEventResult.HANDLED
            self.layer.handle_event(event)
            return UiEventResult.HANDLED
        if isinstance(event, SemanticInputEvent) and event.edge is InputEdge.PRESSED and event.action is SemanticAction.CANCEL:
            self._on_dismiss()
            return UiEventResult.HANDLED
        self.layer.handle_event(event)
        return UiEventResult.HANDLED

    def draw(self, target: object) -> None:
        assert isinstance(target, pygame.Surface)
        self._draw_backdrop(target)
        self.layer.draw(target)


class MonsterSheets:
    """Build the delete and gallery-full sheets from kit controls (word-free)."""

    def __init__(self, kit: ControlKit, layout: SheetLayout) -> None:
        self._kit = kit
        self.layout = layout

    def _two(self, sheet_id: str, left_icon, right_icon, *, on_left, on_right, focus: str) -> ControlLayer:
        layout = self.layout
        left = PictureTile(self._kit.painter, f"{sheet_id}.keep", layout.left, icon=left_icon, token=(sheet_id, "keep"), shape=BodyShape.TILE, on_activate=on_left)
        right = PictureTile(
            self._kit.painter, f"{sheet_id}.confirm", layout.right, icon=right_icon, token=(sheet_id, "confirm"),
            shape=BodyShape.TILE, role=ButtonRole.PRIMARY, on_activate=on_right,
        )
        layer = self._kit.layer([left, right], layer_id=f"monsters.{sheet_id}")
        layer.focus(f"{sheet_id}.{focus}", visible=True)
        return layer

    def delete(self, *, draw_backdrop, on_keep, on_delete) -> MonsterSheet:
        layer = self._two(
            "delete", self._kit.glyph("arrow_left", 60), self._kit.glyph("trash", 60),
            on_left=on_keep, on_right=on_delete, focus="keep",
        )
        return MonsterSheet("monsters.delete", layer, self.layout.panel, on_dismiss=on_keep, draw_backdrop=draw_backdrop)

    def full(self, *, gallery_icon, draw_backdrop, on_gallery, on_keep) -> MonsterSheet:
        layer = self._two(
            "full", self._kit.glyph("arrow_left", 60), gallery_icon,
            on_left=on_keep, on_right=on_gallery, focus="confirm",
        )
        return MonsterSheet("monsters.full", layer, self.layout.panel, on_dismiss=on_keep, draw_backdrop=draw_backdrop)


__all__ = [
    "MonsterControls",
    "MonsterSheet",
    "MonsterSheets",
    "NAME_DRAWER",
    "PictureTile",
    "TileSpec",
]
