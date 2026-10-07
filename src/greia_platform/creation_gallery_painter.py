"""Large-card Pygame drawing adapter for the one Greia Creations controller.

Trust, navigation, media reading and deletion remain outside drawing code.
Only visible image previews are decoded and cached in a bounded LRU.
"""
from __future__ import annotations

import io
from dataclasses import dataclass
from typing import Any

from .creation_gallery import CreationFamily, CreationsGalleryController, GalleryMode
from .creation_gallery_layout import CreationGalleryLayout
from .typography import FontRole, GreiaTypography
from .ui_core import BoundedCache


@dataclass(frozen=True, slots=True)
class GalleryHit:
    action: str
    value: object | None
    rect: Any


class CreationsPygamePainter:
    """One renderer for both My Creations and the child selection surface."""

    BACKGROUND = (39, 52, 88)
    INK = (54, 57, 86)
    CREAM = (251, 245, 232)
    LIGHT = (223, 237, 237)
    GREEN = (171, 232, 197)
    CORAL = (255, 193, 177)
    GOLD = (255, 217, 143)

    def __init__(
        self, controller: CreationsGalleryController, *, typography: GreiaTypography,
        locale: str = "it",
    ) -> None:
        self.controller = controller
        self.typography = typography
        self.locale = "it" if locale.startswith("it") else "en"
        self._cache: BoundedCache[tuple[str, int, int], Any] = BoundedCache(5)
        self._targets: list[GalleryHit] = []
        self._last_size: tuple[int, int] | None = None

    @property
    def targets(self) -> tuple[GalleryHit, ...]:
        return tuple(self._targets)

    def close(self) -> None:
        self._cache.clear()
        self._targets.clear()

    def _label(self, it: str, en: str) -> str:
        return it if self.locale == "it" else en

    def _text(self, target: Any, label: str, x: int, y: int, size: int, *, center: bool = False) -> None:
        font = self.typography.font(FontRole.TITLE if size >= 27 else FontRole.CONTROL, size)
        surface = self.typography.surface(font, label, self.INK if center else self.CREAM)
        position = surface.get_rect(center=(x, y)) if center else surface.get_rect(topleft=(x, y))
        target.blit(surface, position)

    @staticmethod
    def _box(rect: Any, pygame: Any) -> Any:
        return pygame.Rect(rect.x, rect.y, rect.width, rect.height)

    def _icon(self, target: Any, name: str, box: Any, pygame: Any, color: tuple[int,int,int] | None = None) -> None:
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
            sign=-1 if name in ("previous","back") else 1
            pygame.draw.lines(target,ink,False,[(cx+sign*r//2,cy-r),(cx-sign*r//2,cy),(cx+sign*r//2,cy+r)],6)
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

    def _button(self, screen: Any, action: str, rect: Any, icon: str, pygame: Any,
                *, fill: tuple[int,int,int] | None = None, value: object = None, enabled: bool = True) -> None:
        target = self._box(rect,pygame)
        pygame.draw.rect(screen,(25,30,55),target.move(0,4),border_radius=18)
        pygame.draw.rect(screen,fill or self.CREAM if enabled else (128,132,151),target,border_radius=18)
        self._icon(screen,icon,target,pygame)
        if enabled:
            self._targets.append(GalleryHit(action,value,target))

    def _art(self, screen: Any, record: Any, rect: Any, pygame: Any) -> None:
        box=self._box(rect,pygame)
        if record.media_type == "image/png":
            inset=box.inflate(-18,-18)
            key=(record.creation_id,inset.width,inset.height)
            image=self._cache.get(key)
            if image is None:
                kind,payload=self.controller.preview(record.creation_id)
                if kind != "image/png":
                    raise ValueError("image preview type mismatch")
                raw=pygame.image.load(io.BytesIO(payload),"preview.png").convert_alpha()
                ratio=min(inset.width/raw.get_width(),inset.height/raw.get_height())
                image=pygame.transform.smoothscale(raw,(max(1,round(raw.get_width()*ratio)),max(1,round(raw.get_height()*ratio))))
                self._cache[key]=image
            screen.blit(image,image.get_rect(center=inset.center))
        elif record.media_type == "audio/wav":
            radius=max(32,min(box.width,box.height)//4)
            pygame.draw.circle(screen,(183,214,242),box.center,radius)
            self._icon(screen,"audio",pygame.Rect(box.centerx-72,box.centery-65,144,130),pygame,(56,93,153))
        else:
            paper=box.inflate(-52,-18)
            pygame.draw.rect(screen,(255,251,239),paper,border_radius=18)
            self._icon(screen,"text",pygame.Rect(paper.centerx-42,paper.y+10,84,82),pygame,(147,111,155))
            for i in range(4):
                yy=paper.y+105+i*25
                if yy < paper.bottom-15:
                    pygame.draw.line(screen,(208,198,181),(paper.left+24,yy),(paper.right-24,yy),4)

    def draw(self, screen: Any, layout: CreationGalleryLayout, pygame: Any) -> None:
        self._targets.clear()
        screen.fill(self.BACKGROUND)
        width,height=screen.get_size()
        pygame.draw.circle(screen,(58,73,113),(width-75,height-32),max(118,height//3))
        page=self.controller.page
        if page.detail_id is not None:
            self._detail(screen,layout,pygame)
        else:
            self._grid(screen,layout,pygame)

    def _grid(self, screen: Any, layout: CreationGalleryLayout, pygame: Any) -> None:
        page=self.controller.page
        title=self._label("Le mie creazioni","My Creations") if self.controller.mode==GalleryMode.LIBRARY else self._label("Scegli una creazione","Choose a creation")
        self._text(screen,title,layout.title.x,layout.title.y,29)
        labels={
            CreationFamily.ALL:("Tutte","All","all"),
            CreationFamily.IMAGE:("Disegni","Pictures","image"),
            CreationFamily.AUDIO:("Voci","Sounds","audio"),
            CreationFamily.TEXT:("Storie","Stories","text"),
        }
        for index,family in enumerate(self.controller.families):
            rect=self._box(layout.tabs[index],pygame)
            highlighted=page.family==family
            pygame.draw.rect(screen,self.CREAM if highlighted else (89,103,143),rect,border_radius=17)
            self._icon(screen,labels[family][2],pygame.Rect(rect.x+3,rect.y+3,42,44),pygame,self.INK if highlighted else self.CREAM)
            self._targets.append(GalleryHit("family",family,rect))
        if not page.items:
            self._text(screen,self._label("Qui nasceranno nuove creazioni!","Your creations will appear here!"),width//2-120,height//2,22)
        for i,record in enumerate(page.items):
            rect=self._box(layout.cards[i],pygame)
            pygame.draw.rect(screen,(20,26,56),rect.move(0,5),border_radius=25)
            pygame.draw.rect(screen,self.CREAM,rect,border_radius=25)
            if page.focused_id == record.creation_id:
                pygame.draw.rect(screen,self.GOLD,rect,width=5,border_radius=25)
            art=rect.inflate(-16,-16)
            art.height-=55
            pygame.draw.rect(screen,self.LIGHT,art,border_radius=18)
            self._art(screen,record,art,pygame)
            if record.title:
                label=record.title[:24]
                font=self.typography.font(FontRole.BODY,20)
                line=self.typography.surface(font,label,self.INK)
                screen.blit(line,(rect.x+18,rect.bottom-53))
            self._targets.append(GalleryHit("open",record.creation_id,rect))
            if record.media_type=="audio/wav":
                play=pygame.Rect(rect.right-81,rect.bottom-82,66,62)
                self._button(screen,"audio",play,"pause" if page.playing_id==record.creation_id else "play",pygame,fill=self.GOLD,value=record.creation_id)
        self._button(screen,"back",layout.back,"back",pygame)
        self._button(screen,"previous",layout.prev_page,"previous",pygame,enabled=page.has_previous)
        self._button(screen,"next",layout.next_page,"next",pygame,enabled=page.has_next)

    def _detail(self, screen: Any, layout: CreationGalleryLayout, pygame: Any) -> None:
        page=self.controller.page
        item=next((item for item in page.items if item.creation_id==page.detail_id),None)
        if item is None:
            return
        rect=self._box(layout.full_preview,pygame)
        pygame.draw.rect(screen,(22,27,56),rect.move(0,5),border_radius=28)
        pygame.draw.rect(screen,self.CREAM,rect,border_radius=28)
        self._art(screen,item,rect.inflate(-22,-22),pygame)
        if item.media_type=="audio/wav":
            self._button(screen,"audio",layout.audio_play,"pause" if page.playing_id==item.creation_id else "play",pygame,fill=self.GOLD,value=item.creation_id)
        self._button(screen,"detail_back",layout.back,"back",pygame)
        if self.controller.mode==GalleryMode.PICKER:
            self._button(screen,"choose",layout.primary,"check",pygame,fill=self.GREEN)
        else:
            self._button(screen,"ask_delete",layout.delete,"trash",pygame,fill=self.CORAL)
        if page.pending_delete_id is not None:
            shield=pygame.Surface(screen.get_size(),pygame.SRCALPHA)
            shield.fill((10,16,38,185))
            screen.blit(shield,(0,0))
            dialog=pygame.Rect(screen.get_width()//2-230,screen.get_height()//2-140,460,220)
            pygame.draw.rect(screen,self.CREAM,dialog,border_radius=28)
            self._icon(screen,"trash",pygame.Rect(dialog.centerx-56,dialog.y+8,112,100),pygame,(170,69,79))
            caption=self._label("Eliminare?","Delete?")
            label=self.typography.surface(self.typography.font(FontRole.TITLE,27),caption,self.INK)
            screen.blit(label,label.get_rect(center=(dialog.centerx,dialog.bottom-55)))
            self._targets.clear()
            self._button(screen,"cancel_delete",layout.cancel,"cancel",pygame,fill=self.GREEN)
            self._button(screen,"confirm_delete",layout.confirm,"trash",pygame,fill=self.CORAL)
