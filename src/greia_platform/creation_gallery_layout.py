"""Pure, responsive hit geometry shared by My Creations and trusted picker.

No pygame: input, focus and renderer adapters share these exact rectangles.
The mandatory platform Home/Back corner is never occupied by gallery UI.
"""
from __future__ import annotations
from dataclasses import dataclass
from .system_chrome import ActivitySystemChromeLayout, UiRect


@dataclass(frozen=True, slots=True)
class CreationGalleryLayout:
    title: UiRect
    tabs: tuple[UiRect, ...]
    cards: tuple[UiRect, ...]
    prev_page: UiRect
    next_page: UiRect
    back: UiRect
    primary: UiRect
    delete: UiRect
    confirm: UiRect
    cancel: UiRect
    full_preview: UiRect
    audio_play: UiRect
    audio_replay: UiRect

    @classmethod
    def for_surface(cls, width: int, height: int, *, tabs: int = 4) -> 'CreationGalleryLayout':
        if width < 480 or height < 320 or not 1 <= tabs <= 4:
            raise ValueError('unsupported child gallery display geometry')
        chrome = ActivitySystemChromeLayout.for_surface(width, height, back_available=True)
        margin = max(14, min(28, round(width*0.022)))
        gap = max(12, min(22, round(width*0.019)))
        header_left = chrome.protected_region.right + 18
        title = UiRect(header_left, 14, max(1,width-header_left-margin), 58)
        tabs_top = max(chrome.protected_region.bottom+8, 82)
        tab_gap = max(6,min(16,width//90))
        tab_w = min(148,(width-2*margin-(tabs-1)*tab_gap)//tabs)
        tab_start = (width-(tabs*tab_w+(tabs-1)*tab_gap))//2
        tab_rects=tuple(UiRect(tab_start+i*(tab_w+tab_gap),tabs_top,tab_w,50) for i in range(tabs))
        gallery_top = tabs_top+64
        footer_top = height-74
        usable_w=width-2*margin
        columns = 3 if width >= 1300 else 2 if width>=740 else 1
        card_w=(usable_w-gap*(columns-1))//columns
        card_h=max(90,footer_top-gallery_top-11)
        cards=tuple(UiRect(margin+i*(card_w+gap),gallery_top,card_w,card_h) for i in range(columns))
        # Footer controls deliberately reserve big non-overlapping touch targets.
        control=64
        back=UiRect(margin, height-69, control, 58)
        prev=UiRect(max(margin+control+gap,width//2-108),height-69,64,58)
        nex=UiRect(min(width-margin-2*control-gap,width//2+44),height-69,64,58)
        primary=UiRect(width-margin-168,height-69,168,58)
        detail_top=tabs_top+10
        detail_bottom=height-92
        preview=UiRect(margin+12, detail_top, width-2*(margin+12),max(100,detail_bottom-detail_top))
        delete=UiRect(width-margin-78,height-78,70,66)
        confirm=UiRect(width//2+24,height-80,max(110,min(220,width//3)),67)
        cancel=UiRect(width//2-max(130,min(240,width//3)),height-80,max(110,min(220,width//3)),67)
        play=UiRect(width//2-60,height//2-56,120,112)
        replay=UiRect(min(width-margin-72, width//2+82), height//2-39,72,76)
        return cls(title,tab_rects,cards,prev,nex,back,primary,delete,confirm,cancel,preview,play,replay)
