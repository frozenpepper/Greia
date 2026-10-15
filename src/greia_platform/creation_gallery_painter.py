"""Large-card Pygame drawing adapter for the one Greia Creations controller.

Trust, navigation, media reading and deletion remain outside drawing code.
Only visible image previews are decoded and cached in a bounded LRU.

Shared storybook art (sunshine framed tiles, round control buttons, creation
pictograms, the child's cast friend) is optional and injected by the trusted
host as a bounded visual cache; without it, or when a rendition is missing,
the painter keeps its primitive drawing so My Creations and the picker always
stay usable.
"""
from __future__ import annotations

import io
from dataclasses import dataclass
from typing import Any, Callable

from .creation_gallery import CreationFamily, CreationsGalleryController, GalleryMode
from .creation_gallery_layout import CreationGalleryLayout
from .typography import FontRole, GreiaTypography
from .ui_core import BoundedCache


@dataclass(frozen=True, slots=True)
class GalleryHit:
    action: str
    value: object | None
    rect: Any


# Shared art IDs (assets/catalog/shared_visuals_v1_source.toml).
_FRAME_ASSET = "ui.card.activity_tile"
_FRAME_HUE = "sunshine"  # My Creations' Collection hue
_FOCUS_ASSET = "ui.portal.collection_focus"
_BUTTON_ASSET = "ui.button.round"
_PICTOGRAM_ASSET = "ui.pictogram.creation"
_PORTAL_ASSET = "ui.portal.collection"
# Frame art canvas 288x304: nine-slice insets that keep every rounded corner
# (body rx58, window rx44) intact while edges stretch; cream face x48-240.
_FRAME_SIZE = (288, 304)
_FRAME_INSETS = (90, 90, 90, 104)  # left, top, right, bottom
_FRAME_FACE = (48, 48, 48, 64)  # face inset from left, top, right, bottom
_BUTTON_ART = {  # control kind -> ui.button.round variant
    "back": "default", "detail_back": "default", "cancel": "default",
    "previous": "previous", "next": "next", "play": "play", "pause": "pause",
    "replay": "replay", "check": "check", "trash": "trash",
}
_PICTOGRAMS = {"all": "default", "image": "image", "audio": "audio", "text": "text"}


def nine_slice(source: Any, size: tuple[int, int], insets: tuple[int, int, int, int], pygame: Any) -> Any:
    """Stretch ``source`` to ``size`` keeping its four corners undistorted.

    Composition-time only (callers cache the result); edges and centre are
    smoothscaled once.
    """

    width, height = size
    sw, sh = source.get_size()
    left, top, right, bottom = insets
    out = pygame.Surface((width, height), pygame.SRCALPHA)
    xs = ((0, left, 0, left), (left, sw - right, left, width - right), (sw - right, sw, width - right, width))
    ys = ((0, top, 0, top), (top, sh - bottom, top, height - bottom), (sh - bottom, sh, height - bottom, height))
    for sx0, sx1, dx0, dx1 in xs:
        for sy0, sy1, dy0, dy1 in ys:
            if sx1 <= sx0 or sy1 <= sy0 or dx1 <= dx0 or dy1 <= dy0:
                continue
            piece = source.subsurface((sx0, sy0, sx1 - sx0, sy1 - sy0))
            if (dx1 - dx0, dy1 - dy0) != piece.get_size():
                piece = pygame.transform.smoothscale(piece, (dx1 - dx0, dy1 - dy0))
            out.blit(piece, (dx0, dy0))
    return out


class CreationsPygamePainter:
    """One renderer for both My Creations and the child selection surface."""

    BACKGROUND = (39, 52, 88)
    INK = (54, 57, 86)
    CREAM = (251, 245, 232)
    LIGHT = (223, 237, 237)
    GREEN = (171, 232, 197)
    CORAL = (255, 193, 177)
    GOLD = (255, 217, 143)
    # Storybook tokens (cocoa ink / caption cream / sunshine focus).
    ART_INK = (75, 55, 47)
    ART_CREAM = (255, 251, 235)
    ART_SUN = (255, 194, 52)
    ART_SHADOW = (205, 186, 150)

    def __init__(
        self, controller: CreationsGalleryController, *, typography: GreiaTypography,
        locale: str = "it",
        visual_cache: Any | None = None,
        backdrop: Callable[[tuple[int, int]], Any] | None = None,
        greeter: str | None = None,
        text_transform: Callable[[str], str] | None = None,
    ) -> None:
        self.controller = controller
        self.typography = typography
        self.locale = "it" if locale.startswith("it") else "en"
        self._visual_cache = visual_cache
        self._backdrop = backdrop
        self._greeter = greeter
        self._text_transform = text_transform or (lambda value: value)
        self._art_disabled = visual_cache is None
        self._cache: BoundedCache[tuple[str, int, int], Any] = BoundedCache(5)
        self._frames: BoundedCache[tuple[Any, ...], Any] = BoundedCache(6)
        self._targets: list[GalleryHit] = []
        self._last_size: tuple[int, int] | None = None
        self._on_scene = False

    @property
    def _storybook(self) -> bool:
        """Shared art is usable: framed tiles, round controls, pictograms."""

        return not self._art_disabled

    @property
    def targets(self) -> tuple[GalleryHit, ...]:
        return tuple(self._targets)

    def close(self) -> None:
        self._cache.clear()
        self._frames.clear()
        self._targets.clear()

    def _label(self, it: str, en: str) -> str:
        return self._text_transform(it if self.locale == "it" else en)

    def _text(self, target: Any, label: str, x: int, y: int, size: int, *, center: bool = False) -> None:
        font = self.typography.font(FontRole.TITLE if size >= 27 else FontRole.CONTROL, size)
        color = self.ART_INK if self._storybook else (self.INK if center else self.CREAM)
        surface = self.typography.surface(font, label, color)
        position = surface.get_rect(center=(x, y)) if center else surface.get_rect(topleft=(x, y))
        if center and self._storybook:
            # Captions sit on the same cream pill as every Shell caption.
            import pygame

            self._pill(target, position.inflate(position.height + 8, 10), self.ART_CREAM, pygame)
        target.blit(surface, position)

    @staticmethod
    def _box(rect: Any, pygame: Any) -> Any:
        return pygame.Rect(rect.x, rect.y, rect.width, rect.height)

    # -- optional shared art -------------------------------------------

    def _art(self, asset_id: str, variant: str, size: tuple[int, int], pygame: Any) -> Any | None:
        if self._art_disabled or size[0] < 2 or size[1] < 2:
            return None
        try:
            return self._visual_cache.get(asset_id, variant=variant, size=size)
        except Exception:  # noqa: BLE001 - optional artwork: fall back to primitives
            self._art_disabled = True
            return None

    def _frame(self, rect: Any, pygame: Any, *, focus: bool = False) -> Any | None:
        """A sunshine framed tile (or its focus ring) nine-sliced to ``rect``."""

        key = ("focus" if focus else "frame", rect.width, rect.height)
        cached = self._frames.get(key)
        if cached is not None:
            return cached
        scale = min(1.0, rect.width / 200, rect.height / 214)
        base = (max(8, round(_FRAME_SIZE[0] * scale)), max(8, round(_FRAME_SIZE[1] * scale)))
        source = self._art(_FOCUS_ASSET if focus else _FRAME_ASSET,
                           "default" if focus else _FRAME_HUE, base, pygame)
        if source is None:
            return None
        insets = tuple(max(1, round(value * base[0] / _FRAME_SIZE[0])) for value in _FRAME_INSETS)
        surface = nine_slice(source, rect.size, insets, pygame)  # type: ignore[arg-type]
        self._frames[key] = surface
        return surface

    def _frame_face(self, rect: Any, pygame: Any) -> Any:
        scale = min(1.0, rect.width / 200, rect.height / 214) * 1.0
        k = max(8, round(_FRAME_SIZE[0] * scale)) / _FRAME_SIZE[0]
        left, top, right, bottom = (round(value * k) for value in _FRAME_FACE)
        return pygame.Rect(rect.x + left, rect.y + top, rect.width - left - right, rect.height - top - bottom)

    def _pill(self, screen: Any, rect: Any, fill: tuple[int, int, int], pygame: Any) -> None:
        radius = rect.height // 2
        pygame.draw.rect(screen, self.ART_SHADOW, rect.move(0, 2), border_radius=radius)
        pygame.draw.rect(screen, fill, rect, border_radius=radius)
        pygame.draw.rect(screen, self.ART_INK, rect, width=2, border_radius=radius)

    # -- pictograms and buttons ----------------------------------------

    def _icon(self, target: Any, name: str, box: Any, pygame: Any, color: tuple[int,int,int] | None = None) -> None:
        if name in _PICTOGRAMS:
            side = max(8, min(box.width, box.height))
            art = self._art(_PICTOGRAM_ASSET, _PICTOGRAMS[name], (side, side), pygame)
            if art is not None:
                target.blit(art, art.get_rect(center=box.center))
                return
        ink = color or self.INK
        cx, cy = box.center
        r = max(8, min(box.width, box.height) // 3)
        if name == "image":
            pygame.draw.rect(target, ink, (cx-r, cy-r, 2*r, 2*r), 4, border_radius=6)
            pygame.draw.circle(target, ink, (cx+r//2, cy-r//2), max(3,r//6))
            pygame.draw.lines(target, ink, False, [(cx-r+5,cy+r-6),(cx-r//3,cy),(cx,cy+r//3),(cx+r//2,cy-r//5),(cx+r-5,cy+r-6)], 4)
        elif name == "audio":
            for i, h in enumerate((14, 28, 43, 23, 36, 14)):
                x = cx - 40 + i*16
                pygame.draw.line(target, ink, (x,cy-h//2),(x,cy+h//2),5)
        elif name == "text":
            pygame.draw.rect(target, ink, (cx-r+4,cy-r,2*r-8,2*r),4,border_radius=5)
            for i in range(3):
                yy=cy-r//2+i*r//2
                pygame.draw.line(target, ink,(cx-r+12,yy),(cx+r-12,yy),3)
        elif name == "trash":
            pygame.draw.rect(target, ink,(cx-r//2,cy-r//2,r,r+r//4),4,border_radius=4)
            pygame.draw.line(target, ink,(cx-r//2-4,cy-r//2-8),(cx+r//2+4,cy-r//2-8),5)
        elif name in ("previous","next","back"):
            # Chevron points toward where the control goes.
            sign = -1 if name in ("previous","back") else 1
            pygame.draw.lines(target,ink,False,[(cx-sign*r//2,cy-r),(cx+sign*r//2,cy),(cx-sign*r//2,cy+r)],6)
        elif name == "check":
            pygame.draw.lines(target,ink,False,[(cx-r,cy),(cx-r//4,cy+r//2),(cx+r,cy-r//2)],6)
        elif name == "play":
            pygame.draw.polygon(target,ink,[(cx-r//2,cy-r),(cx+r,cy),(cx-r//2,cy+r)])
        elif name == "pause":
            pygame.draw.rect(target,ink,(cx-r//2,cy-r,11,2*r),border_radius=3)
            pygame.draw.rect(target,ink,(cx+r//2,cy-r,11,2*r),border_radius=3)
        elif name == "all":
            for xx in (-r//2,r//2):
                for yy in (-r//2,r//2):
                    pygame.draw.circle(target,ink,(cx+xx,cy+yy),max(4,r//4))
        elif name == "cancel":
            pygame.draw.line(target,ink,(cx-r//2,cy-r//2),(cx+r//2,cy+r//2),6)
            pygame.draw.line(target,ink,(cx-r//2,cy+r//2),(cx+r//2,cy-r//2),6)
        elif name == "replay":
            pygame.draw.arc(target,ink,(cx-r,cy-r,2*r,2*r),0.50,5.35,5)
            pygame.draw.polygon(target,ink,[(cx+r-1,cy-r//2),(cx+r+5,cy-r),(cx+r//2,cy-r)])

    def _button(self, screen: Any, action: str, rect: Any, icon: str, pygame: Any,
                *, fill: tuple[int,int,int] | None = None, value: object = None, enabled: bool = True) -> None:
        target = self._box(rect,pygame)
        variant = _BUTTON_ART.get(icon)
        art = None
        if variant is not None:
            side = max(8, min(target.height, round(target.width * 120 / 112)))
            art = self._art(_BUTTON_ASSET, variant, (round(side * 112 / 120), side), pygame)
        if art is not None:
            if enabled:
                screen.blit(art, art.get_rect(center=target.center))
            # A disabled storybook control is simply absent (as on Shell pages).
        else:
            pygame.draw.rect(screen,(25,30,55),target.move(0,4),border_radius=18)
            pygame.draw.rect(screen,fill or self.CREAM if enabled else (128,132,151),target,border_radius=18)
            self._icon(screen,icon,target,pygame)
        if enabled:
            self._targets.append(GalleryHit(action,value,target))

    # -- media ----------------------------------------------------------

    def _media(self, screen: Any, record: Any, rect: Any, pygame: Any, *, expanded: bool = False) -> None:
        box=self._box(rect,pygame)
        if record.media_type == "image/png":
            inset=box.inflate(-18,-18) if not self._storybook else box.inflate(-8,-8)
            key=(record.creation_id,inset.width,inset.height,expanded)
            image=self._cache.get(key)
            if image is None:
                if expanded:
                    payload = self.controller.full_image(record.creation_id)
                else:
                    kind,payload=self.controller.preview(record.creation_id)
                    if kind != "image/png":
                        raise ValueError("image preview type mismatch")
                raw=pygame.image.load(io.BytesIO(payload),"preview.png").convert_alpha()
                ratio=min(inset.width/raw.get_width(),inset.height/raw.get_height())
                image=pygame.transform.smoothscale(raw,(max(1,round(raw.get_width()*ratio)),max(1,round(raw.get_height()*ratio))))
                self._cache[key]=image
            screen.blit(image,image.get_rect(center=inset.center))
        elif record.media_type == "audio/wav":
            if self._storybook:
                side = max(24, min(box.width, box.height) * 3 // 4)
                # Expanded: the pictogram steps aside for the big play controls.
                cx = box.x + box.width // 5 if expanded else box.centerx
                self._icon(screen, "audio", pygame.Rect(cx - side // 2, box.centery - side // 2, side, side), pygame)
                return
            radius=max(32,min(box.width,box.height)//4)
            pygame.draw.circle(screen,(183,214,242),box.center,radius)
            self._icon(screen,"audio",pygame.Rect(box.centerx-72,box.centery-65,144,130),pygame,(56,93,153))
        else:
            if self._storybook and not expanded:
                side = max(24, min(box.width, box.height) * 3 // 4)
                self._icon(screen, "text", pygame.Rect(box.centerx - side // 2, box.centery - side // 2, side, side), pygame)
                return
            paper=box.inflate(-52,-18)
            pygame.draw.rect(screen,(255,251,239),paper,border_radius=18)
            if self._storybook:
                pygame.draw.rect(screen, self.ART_INK, paper, width=2, border_radius=18)
            self._icon(screen,"text",pygame.Rect(paper.centerx-42,paper.y+10,84,82),pygame,(147,111,155))
            if expanded:
                kind,payload=self.controller.preview(record.creation_id)
                if kind != "text/plain":
                    raise ValueError("text preview type mismatch")
                excerpt=payload.decode("utf-8").replace("\n"," ").strip()
                font=self.typography.font(FontRole.BODY,22)
                yy=paper.y+110
                for piece in _wrap_words(excerpt, font, paper.width-56)[:6]:
                    if yy+font.get_height()>paper.bottom-12:
                        break
                    visual=self.typography.surface(font,piece,self.ART_INK if self._storybook else self.INK)
                    screen.blit(visual,(paper.left+28,yy))
                    yy+=font.get_linesize()+4
            else:
                for i in range(4):
                    yy=paper.y+105+i*25
                    if yy < paper.bottom-15:
                        pygame.draw.line(screen,(208,198,181),(paper.left+24,yy),(paper.right-24,yy),4)

    # -- screens --------------------------------------------------------

    def draw(self, screen: Any, layout: CreationGalleryLayout, pygame: Any, *, delete_focus: str = "cancel_delete") -> None:
        self._targets.clear()
        width,height=screen.get_size()
        scene = None
        if self._backdrop is not None and not self._art_disabled:
            try:
                scene = self._backdrop((width, height))
            except Exception:  # noqa: BLE001 - decoration only
                scene = None
        self._on_scene = scene is not None
        if scene is not None:
            screen.blit(scene, (0, 0))
        else:
            screen.fill(self.BACKGROUND)
            pygame.draw.circle(screen,(58,73,113),(width-75,height-32),max(118,height//3))
        page=self.controller.page
        if page.detail_id is not None:
            self._detail(screen,layout,pygame, delete_focus=delete_focus)
        else:
            self._grid(screen,layout,pygame)

    def _title(self, screen: Any, layout: CreationGalleryLayout, title: str, pygame: Any) -> None:
        if not self._storybook:
            self._text(screen,title,layout.title.x,layout.title.y,29)
            return
        # The place's identity: a small sunshine portal (My Creations' Home
        # tile) holding the "all creations" pictogram, then the name.
        portal_h = max(40, min(64, layout.title.height + 4))
        portal = pygame.Rect(layout.title.x, layout.title.y - 4, round(portal_h * 288 / 304), portal_h)
        art = self._art(_PORTAL_ASSET, _FRAME_HUE, portal.size, pygame)
        if art is not None:
            screen.blit(art, portal)
            side = portal.width // 2
            self._icon(screen, "all", pygame.Rect(portal.x + portal.width // 2 - side // 2,
                                                  portal.y + round(portal.height * 144 / 304) - side // 2,
                                                  side, side), pygame)
        font = self.typography.font(FontRole.CONTROL, 24)
        label = self.typography.surface(font, title, self.ART_INK)
        pill = label.get_rect()
        pill.inflate_ip(pill.height + 12, 10)
        pill.midleft = (portal.right + 6, portal.centery - 3)
        self._pill(screen, pill, self.ART_CREAM, pygame)
        screen.blit(label, label.get_rect(center=pill.center))

    def _grid(self, screen: Any, layout: CreationGalleryLayout, pygame: Any) -> None:
        page=self.controller.page
        width, height = screen.get_size()
        title=self._label("Le mie creazioni","My Creations") if self.controller.mode==GalleryMode.LIBRARY else self._label("Scegli una creazione","Choose a creation")
        self._title(screen, layout, title, pygame)
        labels={
            CreationFamily.ALL:("Tutte","All","all"),
            CreationFamily.IMAGE:("Disegni","Pictures","image"),
            CreationFamily.AUDIO:("Voci","Sounds","audio"),
            CreationFamily.TEXT:("Storie","Stories","text"),
        }
        for index,family in enumerate(self.controller.families):
            rect=self._box(layout.tabs[index],pygame)
            highlighted=page.family==family
            if self._storybook:
                self._pill(screen, rect, self.ART_SUN if highlighted else self.ART_CREAM, pygame)
                side = rect.height - 8
                self._icon(screen, labels[family][2], pygame.Rect(rect.centerx - side // 2, rect.y + 4, side, side), pygame)
            else:
                pygame.draw.rect(screen,self.CREAM if highlighted else (89,103,143),rect,border_radius=17)
                self._icon(screen,labels[family][2],pygame.Rect(rect.x+3,rect.y+3,42,44),pygame,self.INK if highlighted else self.CREAM)
            self._targets.append(GalleryHit("family",family,rect))
        if not page.items:
            self._empty(screen, layout, pygame)
        for i,record in enumerate(page.items):
            rect=self._box(layout.cards[i],pygame)
            focused = page.focused_id == record.creation_id
            if self._storybook and self._grid_card(screen, rect, record, focused, pygame):
                pass
            else:
                pygame.draw.rect(screen,(20,26,56),rect.move(0,5),border_radius=25)
                pygame.draw.rect(screen,self.CREAM,rect,border_radius=25)
                if focused:
                    pygame.draw.rect(screen,self.GOLD,rect,width=5,border_radius=25)
                art=rect.inflate(-16,-16)
                art.height-=55
                pygame.draw.rect(screen,self.LIGHT,art,border_radius=18)
                self._media(screen,record,art,pygame)
                if record.title:
                    label=record.title[:24]
                    font=self.typography.font(FontRole.BODY,20)
                    line=self.typography.surface(font,label,self.INK)
                    screen.blit(line,(rect.x+18,rect.bottom-53))
            self._targets.append(GalleryHit("open",record.creation_id,rect))
            if record.media_type=="audio/wav":
                play=pygame.Rect(rect.right-81,rect.bottom-82,66,62)
                if self._storybook:
                    face = self._frame_face(pygame.Rect(rect.x, rect.y, rect.width, rect.height - (40 if record.title and rect.height >= 170 else 0)), pygame)
                    play = pygame.Rect(face.right - 66, face.bottom - 70, 60, 64)
                self._button(screen,"audio",play,"pause" if page.playing_id==record.creation_id and page.paused_id!=record.creation_id else "play",pygame,fill=self.GOLD,value=record.creation_id)
        self._button(screen,"back",layout.back,"back",pygame)
        self._button(screen,"previous",layout.prev_page,"previous",pygame,enabled=page.has_previous)
        self._button(screen,"next",layout.next_page,"next",pygame,enabled=page.has_next)

    def _grid_card(self, screen: Any, rect: Any, record: Any, focused: bool, pygame: Any) -> bool:
        """A framed sunshine tile: thumbnail/pictogram in the face, title pill."""

        title_h = 40 if record.title and rect.height >= 170 else 0
        frame_rect = pygame.Rect(rect.x, rect.y, rect.width, rect.height - title_h)
        frame = self._frame(frame_rect, pygame)
        if frame is None:
            return False
        screen.blit(frame, frame_rect)
        face = self._frame_face(frame_rect, pygame)
        self._media(screen, record, face, pygame)
        if focused:
            ring = self._frame(frame_rect, pygame, focus=True)
            if ring is not None:
                screen.blit(ring, frame_rect)
        if record.title:
            font = self.typography.font(FontRole.CONTROL, 19)
            text = record.title[:24]
            label = self.typography.surface(font, self._text_transform(text), self.ART_INK)
            if label.get_width() > rect.width - 30:
                label = pygame.transform.smoothscale(label, (rect.width - 30, label.get_height()))
            pill = label.get_rect().inflate(label.get_height() + 10, 10)
            # Tuck the pill onto the frame's shadow band, close to its tile.
            pill.midtop = (rect.centerx, frame_rect.bottom - 12)
            self._pill(screen, pill, self.ART_SUN if focused else self.ART_CREAM, pygame)
            screen.blit(label, label.get_rect(center=pill.center))
        return True

    def _empty(self, screen: Any, layout: CreationGalleryLayout, pygame: Any) -> None:
        """Make "nothing saved yet" clear to a child who cannot read."""

        page = self.controller.page
        width, height = screen.get_size()
        top = layout.tabs[0].bottom + 18
        bottom = layout.back.y - 12
        cy = (top + bottom) // 2
        radius = max(42, min(86, (bottom - top) // 2 - 2))
        cx = width // 2
        # Empty audio-only or text-only pickers should show the requested
        # kind, not an unrelated image icon to a child who cannot read.
        kind_by_family = {
            CreationFamily.IMAGE: "image",
            CreationFamily.AUDIO: "audio",
            CreationFamily.TEXT: "text",
        }
        if page.family is CreationFamily.ALL and len(self.controller.allowed) == 1:
            only_type = next(iter(self.controller.allowed))
            empty_icon = {
                "image/png": "image",
                "audio/wav": "audio",
                "text/plain": "text",
            }[only_type]
        else:
            empty_icon = kind_by_family.get(page.family, "all")
        caption = self._label("Qui nasceranno nuove creazioni!", "Your creations will appear here!")
        if self._storybook:
            show_caption = width >= 740 and height >= 490
            frame_h = max(90, min(260, bottom - top - (44 if show_caption else 0)))
            frame_w = round(frame_h * 288 / 304)
            frame_rect = pygame.Rect(0, 0, frame_w, frame_h)
            frame_rect.midtop = (cx, top)
            frame = self._frame(frame_rect, pygame)
            if frame is not None:
                screen.blit(frame, frame_rect)
                face = self._frame_face(frame_rect, pygame)
                side = min(face.width, face.height) * 3 // 4
                self._icon(screen, empty_icon, pygame.Rect(face.centerx - side // 2, face.centery - side // 2, side, side), pygame)
                self._sparkles(screen, frame_rect, pygame)
                friend = self._art(f"character.{self._greeter}", "pose_point", (frame_h, frame_h), pygame) if self._greeter else None
                if friend is not None:
                    spot = friend.get_rect(bottomright=(frame_rect.left - 6, frame_rect.bottom + 6))
                    if spot.left >= 4:
                        screen.blit(friend, spot)
                if show_caption:
                    self._text(screen, caption, cx, frame_rect.bottom + 26, 20, center=True)
                return
        pygame.draw.circle(screen,(236,214,173),(cx,cy+4),radius+7)
        pygame.draw.circle(screen,(255,247,224),(cx,cy),radius)
        icon_box = pygame.Rect(cx-radius//2,cy-radius//2,radius,radius)
        self._icon(screen,empty_icon,icon_box,pygame,(98,127,162))
        for offset in (-1,1):
            sx = cx + offset * (radius + 26)
            pygame.draw.circle(screen,(252,209,111),(sx,cy-radius//2),max(4,radius//9))
            pygame.draw.line(screen,(252,209,111),(sx-12,cy-radius//2-13),(sx+10,cy-radius//2+10),3)
        if width >= 740 and height >= 490:
            self._text(screen, caption, cx, min(bottom-26, cy+radius+28), 20, center=True)

    def _sparkles(self, screen: Any, rect: Any, pygame: Any) -> None:
        for sx, sy, r in ((rect.right + 4, rect.top + 18, 12), (rect.right + 22, rect.top + 52, 7)):
            points = [(sx, sy - r), (sx + r // 3, sy - r // 3), (sx + r, sy), (sx + r // 3, sy + r // 3),
                      (sx, sy + r), (sx - r // 3, sy + r // 3), (sx - r, sy), (sx - r // 3, sy - r // 3)]
            pygame.draw.polygon(screen, (251, 191, 36), points)
            pygame.draw.polygon(screen, self.ART_INK, points, width=2)

    def _detail(self, screen: Any, layout: CreationGalleryLayout, pygame: Any, *, delete_focus: str) -> None:
        page=self.controller.page
        item=next((item for item in page.items if item.creation_id==page.detail_id),None)
        if item is None:
            return
        rect=self._box(layout.full_preview,pygame)
        frame = self._frame(rect, pygame) if self._storybook else None
        if frame is not None:
            screen.blit(frame, rect)
            self._media(screen, item, self._frame_face(rect, pygame), pygame, expanded=True)
        else:
            pygame.draw.rect(screen,(22,27,56),rect.move(0,5),border_radius=28)
            pygame.draw.rect(screen,self.CREAM,rect,border_radius=28)
            self._media(screen,item,rect.inflate(-22,-22),pygame,expanded=True)
        if item.media_type=="audio/wav":
            if page.playing_id==item.creation_id:
                duration=float(item.attributes.get("duration_seconds",0))
                player=self.controller.audio_player
                fraction=player.progress(duration) if player is not None and hasattr(player,"progress") else 0.0
                bar=pygame.Rect(rect.x+40,rect.bottom-35,rect.width-80,12)
                if frame is not None:
                    bar = pygame.Rect(rect.x + 70, rect.bottom - 92, rect.width - 140, 14)
                pygame.draw.rect(screen,(176,188,198),bar,border_radius=6)
                pygame.draw.rect(screen,(83,171,166),(bar.x,bar.y,int(bar.width*fraction),bar.height),border_radius=6)
                if frame is not None:
                    pygame.draw.rect(screen, self.ART_INK, bar, width=2, border_radius=7)
            self._button(screen,"audio",layout.audio_play,"pause" if page.playing_id==item.creation_id and page.paused_id!=item.creation_id else "play",pygame,fill=self.GOLD,value=item.creation_id)
            self._button(screen,"replay",layout.audio_replay,"replay",pygame,fill=self.LIGHT,value=item.creation_id)
        self._button(screen,"detail_back",layout.back,"back",pygame)
        if self.controller.mode==GalleryMode.PICKER:
            self._button(screen,"choose",layout.primary,"check",pygame,fill=self.GREEN)
        else:
            self._button(screen,"ask_delete",layout.delete,"trash",pygame,fill=self.CORAL)
        if page.pending_delete_id is not None:
            self._delete_dialog(screen, layout, item, pygame, delete_focus=delete_focus)

    def _delete_dialog(self, screen: Any, layout: CreationGalleryLayout, item: Any, pygame: Any, *, delete_focus: str) -> None:
        shield=pygame.Surface(screen.get_size(),pygame.SRCALPHA)
        shield.fill((10,16,38,185) if not self._on_scene else (61, 44, 31, 150))
        screen.blit(shield,(0,0))
        dialog=pygame.Rect(screen.get_width()//2-230,screen.get_height()//2-140,460,220)
        caption=self._label("Eliminare?","Delete?")
        frame = None
        if self._storybook:
            # Sized to stay clear of the answer buttons on every screen.
            dialog_h = max(120, min(240, layout.cancel.y - 22))
            dialog = pygame.Rect(0, 0, min(520, screen.get_width() - 40), dialog_h)
            dialog.midbottom = (screen.get_width() // 2, layout.cancel.y - 12)
            frame = self._frame(dialog, pygame)
        if frame is not None:
            # The creation itself, small, so the child sees *what* would go.
            screen.blit(frame, dialog)
            face = self._frame_face(dialog, pygame).inflate(-12, -12)
            thumb = pygame.Rect(face.x, face.y, face.width // 2 - 6, face.height)
            self._media(screen, item, thumb, pygame)
            right = pygame.Rect(face.centerx + 6, face.y, face.width // 2 - 6, face.height)
            font = self.typography.font(FontRole.TITLE, 27 if face.height >= 120 else 20)
            label = self.typography.surface(font, caption, self.ART_INK)
            side = max(24, min(right.width, right.height - label.get_height() - 6))
            art = self._art(_BUTTON_ASSET, "trash", (side * 112 // 120, side), pygame)
            if art is not None:
                screen.blit(art, art.get_rect(midtop=(right.centerx, right.y)))
            screen.blit(label, label.get_rect(midbottom=(right.centerx, right.bottom)))
        else:
            pygame.draw.rect(screen,self.CREAM,dialog,border_radius=28)
            self._icon(screen,"trash",pygame.Rect(dialog.centerx-56,dialog.y+8,112,100),pygame,(170,69,79))
            label=self.typography.surface(self.typography.font(FontRole.TITLE,27),caption,self.INK)
            screen.blit(label,label.get_rect(center=(dialog.centerx,dialog.bottom-55)))
        self._targets.clear()
        self._button(screen,"cancel_delete",layout.cancel,"cancel" if frame is None else "back",pygame,fill=self.GREEN)
        self._button(screen,"confirm_delete",layout.confirm,"trash",pygame,fill=self.CORAL)
        # The confirmation is keyboard-operable, but cancellation is the
        # default. Keep the selected action visibly identifiable without
        # relying on its color or a readable label.
        focus_rect = self._box(layout.confirm if delete_focus == "confirm_delete" else layout.cancel, pygame)
        radius = focus_rect.height // 2 if frame is not None else 18
        if frame is not None:
            pygame.draw.rect(screen, self.ART_SUN, focus_rect.inflate(-6, -6), width=4, border_radius=radius)
        pygame.draw.rect(screen, self.INK, focus_rect, width=5, border_radius=radius)


def _wrap_words(text: str, font: Any, max_width: int) -> list[str]:
    """Greedy word wrap by real glyph width (long words are hard-split)."""

    lines: list[str] = []
    current = ""
    for word in text.split():
        candidate = f"{current} {word}".strip()
        if font.size(candidate)[0] <= max_width:
            current = candidate
            continue
        if current:
            lines.append(current)
        while font.size(word)[0] > max_width and len(word) > 1:
            cut = len(word)
            while cut > 1 and font.size(word[:cut])[0] > max_width:
                cut -= 1
            lines.append(word[:cut])
            word = word[cut:]
        current = word
    if current:
        lines.append(current)
    return lines
