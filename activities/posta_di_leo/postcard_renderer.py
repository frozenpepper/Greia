"""Presentation renderer for Posta di Leo."""

from __future__ import annotations

from typing import Final

import pygame

from greia_platform.localization import LocalizationError, LocalizedResources
from greia_platform.system_chrome import ActivitySystemChromeLayout
from greia_platform.typography import FontRole, GreiaTypography, grapheme_boundaries

if __package__:
    from .postcard_art import POSTCARD_BG, POSTCARD_BORDER, PostcardArt
    from .postcard_content import RECIPIENTS, STAMPS, Recipient, Stamp
    from .postcard_model import MAX_GRAPHEMES, MAX_SAVED_CARDS, PostcardDraft, PostcardLibrary, SavedPostcard
else:
    from postcard_art import POSTCARD_BG, POSTCARD_BORDER, PostcardArt
    from postcard_content import RECIPIENTS, STAMPS, Recipient, Stamp
    from postcard_model import MAX_GRAPHEMES, MAX_SAVED_CARDS, PostcardDraft, PostcardLibrary, SavedPostcard


REFERENCE_WIDTH: Final = 1024
REFERENCE_HEIGHT: Final = 600

POSTCARD_RECT: Final[pygame.Rect] = pygame.Rect(80, 110, 864, 395)
SEND_BTN_RECT: Final[pygame.Rect] = pygame.Rect(80, 525, 200, 52)
GALLERY_BTN_RECT: Final[pygame.Rect] = pygame.Rect(310, 525, 280, 52)
CLEAR_BTN_RECT: Final[pygame.Rect] = pygame.Rect(620, 525, 180, 52)
SHARED_IMPORT_BTN_RECT: Final[pygame.Rect] = pygame.Rect(820, 525, 124, 52)
SHARED_SHARE_BTN_RECT: Final[pygame.Rect] = pygame.Rect(742, 485, 170, 48)
# Child-visible controls start clear of the trusted Home/Back region, which
# the platform reserves in full (both slots) so layout never jumps by context.
_CHROME_CLEAR_X: Final = ActivitySystemChromeLayout.for_surface(1024, 600).protected_region.right + 18
BACK_TO_EDITOR_RECT: Final[pygame.Rect] = pygame.Rect(_CHROME_CLEAR_X, 24, 240, 52)


# Handwriting lane inside the postcard: width left of the stamp divider.
MESSAGE_LANE_WIDTH: Final = 480
MODAL_MESSAGE_LANE_WIDTH: Final = 560
MAX_MESSAGE_LINES: Final = 5


class PostcardRenderer:
    """Render postcard composer, text editor, stamp picker, and gallery."""

    def __init__(
        self,
        art: PostcardArt,
        typography: GreiaTypography,
        resources: LocalizedResources,
    ) -> None:
        self._art = art
        self._typography = typography
        self._resources = resources
        # One-entry wrap cache: the draft changes at most once per keystroke,
        # not once per frame, so re-measuring every frame would be waste.
        self._wrap_key: tuple[str, FontRole, int, int] | None = None
        self._wrap_value: tuple[tuple[int, int], ...] = ()

    def _wrapped_spans(
        self, text: str, role: FontRole, size: int, max_width: int
    ) -> tuple[tuple[int, int], ...]:
        """Split ``text`` into ``(start, end)`` line spans that fit ``max_width``.

        Breaks prefer the last space; a word wider than the lane is broken at
        a grapheme boundary so emoji/accent clusters are never split.
        """
        key = (text, role, size, max_width)
        if key == self._wrap_key:
            return self._wrap_value
        bounds = grapheme_boundaries(text)
        spans: list[tuple[int, int]] = []
        start = 0
        last_space = -1
        prev = 0
        for bound in bounds[1:]:
            if self._typography.measure(text[start:bound].rstrip(), role, size).width > max_width and prev > start:
                end = last_space + 1 if last_space > start else prev
                spans.append((start, end))
                start = end
                last_space = -1
            if text[bound - 1] == " ":
                last_space = bound - 1
            prev = bound
        if start < len(text) or not spans:
            spans.append((start, len(text)))
        self._wrap_key = key
        self._wrap_value = tuple(spans)
        return self._wrap_value

    def draw_editor(
        self,
        target: pygame.Surface,
        draft: PostcardDraft,
        library: PostcardLibrary,
        *,
        cursor_visible: bool = True,
        shared_available: bool = False,
        shared_state: str = "",
    ) -> None:
        target.blit(self._art.background, (0, 0))

        # 1. Top Recipient Bar
        self._draw_recipient_bar(target, draft.recipient_id)

        # 2. Main Postcard Canvas
        self._draw_postcard_canvas(target, draft, cursor_visible=cursor_visible)

        # 3. Bottom Toolbar
        self._draw_editor_toolbar(
            target,
            library,
            shared_available=shared_available,
            shared_state=shared_state,
        )

    def draw_gallery(
        self,
        target: pygame.Surface,
        library: PostcardLibrary,
        *,
        selected_card_id: str | None = None,
        confirm_delete: bool = False,
        shared_available: bool = False,
        shared_state: str = "",
    ) -> None:
        target.blit(self._art.background, (0, 0))

        # Top Return Button
        pygame.draw.rect(target, (2, 132, 199), BACK_TO_EDITOR_RECT, border_radius=22)
        pygame.draw.rect(target, (56, 189, 248), BACK_TO_EDITOR_RECT, width=2, border_radius=22)
        b_txt = self._typography.render(
            self._resources.text("button.write"),
            FontRole.TITLE,
            20,
            (255, 255, 255),
        )
        target.blit(
            b_txt,
            (
                BACK_TO_EDITOR_RECT.centerx - b_txt.get_width() // 2,
                BACK_TO_EDITOR_RECT.centery - b_txt.get_height() // 2,
            ),
        )

        # Header Badge
        header = f"{self._resources.text('button.saved')} ({library.count}/{MAX_SAVED_CARDS})"
        h_surf = self._typography.render(header, FontRole.TITLE, 24, (254, 240, 138))
        target.blit(h_surf, (REFERENCE_WIDTH // 2 + 110 - h_surf.get_width() // 2, 34))

        # Grid of saved cards (4 columns x 3 rows)
        if library.count == 0:
            # Pictogram first so a pre-reader understands the empty mailbox.
            empty_icon = self._typography.render("📭", FontRole.DISPLAY, 72, (148, 163, 184))
            target.blit(empty_icon, (REFERENCE_WIDTH // 2 - empty_icon.get_width() // 2, 220))
            try:
                empty_caption = self._resources.text("gallery.empty")
            except LocalizationError:
                empty_caption = ""
            if empty_caption:
                empty_txt = self._typography.render(empty_caption, FontRole.BODY, 24, (100, 116, 139))
                target.blit(empty_txt, (REFERENCE_WIDTH // 2 - empty_txt.get_width() // 2, 320))
            return

        for idx, card in enumerate(library.cards):
            card_rect = self.gallery_card_rect_at(idx)
            is_selected = (card.card_id == selected_card_id)
            self._draw_thumbnail_card(target, card_rect, card, is_selected=is_selected)

        # Single Card Full Modal / Confirm Delete
        if selected_card_id is not None:
            card = library.get(selected_card_id)
            if card is not None:
                self._draw_card_modal(
                    target,
                    card,
                    confirm_delete=confirm_delete,
                    shared_available=shared_available,
                    shared_state=shared_state,
                )

    def draw_full_dialog(self, target: pygame.Surface) -> None:
        """Render polite full-mailbox sheet."""
        overlay = pygame.Surface((REFERENCE_WIDTH, REFERENCE_HEIGHT), pygame.SRCALPHA)
        overlay.fill((15, 23, 42, 200))
        target.blit(overlay, (0, 0))

        sheet = pygame.Rect(REFERENCE_WIDTH // 2 - 260, REFERENCE_HEIGHT // 2 - 140, 520, 280)
        pygame.draw.rect(target, (255, 251, 235), sheet, border_radius=28)
        pygame.draw.rect(target, (217, 119, 6), sheet, width=4, border_radius=28)

        t_surf = self._typography.render(
            self._resources.text("dialog.full_title"),
            FontRole.DISPLAY,
            28,
            (180, 83, 9),
        )
        target.blit(t_surf, (sheet.centerx - t_surf.get_width() // 2, sheet.top + 32))

        lines = self._resources.text("dialog.full_body").split("\n")
        for i, line in enumerate(lines):
            b_surf = self._typography.render(
                line,
                FontRole.BODY,
                20,
                (71, 85, 105),
            )
            target.blit(b_surf, (sheet.centerx - b_surf.get_width() // 2, sheet.top + 85 + i * 30))

        ok_rect = pygame.Rect(sheet.centerx - 90, sheet.bottom - 74, 180, 50)
        pygame.draw.rect(target, (2, 132, 199), ok_rect, border_radius=18)
        ok_txt = self._typography.render("OK", FontRole.TITLE, 22, (255, 255, 255))
        target.blit(
            ok_txt,
            (ok_rect.centerx - ok_txt.get_width() // 2, ok_rect.centery - ok_txt.get_height() // 2),
        )

    # --- Interaction hit testing ---
    def recipient_at(self, point: tuple[int, int]) -> str | None:
        for idx, r in enumerate(RECIPIENTS):
            rect = self.recipient_rect_at(idx)
            if rect.collidepoint(point):
                return r.recipient_id
        return None

    def recipient_rect_at(self, index: int) -> pygame.Rect:
        cx = 180 + index * 130
        cy = 55
        return pygame.Rect(cx - 40, cy - 35, 80, 70)

    def stamp_at(self, point: tuple[int, int]) -> str | None:
        for idx, s in enumerate(STAMPS):
            rect = self.stamp_rect_at(idx)
            if rect.collidepoint(point):
                return s.stamp_id
        return None

    def stamp_rect_at(self, index: int) -> pygame.Rect:
        # 6 stamps arranged 3x2 on top-right of postcard
        col = index % 3
        row = index // 3
        x = POSTCARD_RECT.left + 580 + col * 84
        y = POSTCARD_RECT.top + 28 + row * 84
        return pygame.Rect(x, y, 72, 72)

    def send_contains(self, point: tuple[int, int]) -> bool:
        return SEND_BTN_RECT.collidepoint(point)

    def gallery_contains(self, point: tuple[int, int]) -> bool:
        return GALLERY_BTN_RECT.collidepoint(point)

    def clear_contains(self, point: tuple[int, int]) -> bool:
        return CLEAR_BTN_RECT.collidepoint(point)

    def shared_import_contains(self, point: tuple[int, int]) -> bool:
        return SHARED_IMPORT_BTN_RECT.collidepoint(point)

    def share_btn_rect(self) -> pygame.Rect:
        return SHARED_SHARE_BTN_RECT.copy()

    def back_to_editor_contains(self, point: tuple[int, int]) -> bool:
        return BACK_TO_EDITOR_RECT.collidepoint(point)

    def gallery_card_rect_at(self, index: int) -> pygame.Rect:
        col = index % 5
        row = index // 5
        w, h = 160, 100
        x = 92 + col * 175
        y = 100 + row * 115
        return pygame.Rect(x, y, w, h)

    def gallery_card_at(self, point: tuple[int, int], count: int) -> int | None:
        for idx in range(count):
            rect = self.gallery_card_rect_at(idx)
            if rect.collidepoint(point):
                return idx
        return None

    def delete_btn_rect(self) -> pygame.Rect:
        return pygame.Rect(REFERENCE_WIDTH // 2 - 190, 485, 170, 48)

    def cancel_btn_rect(self) -> pygame.Rect:
        return pygame.Rect(REFERENCE_WIDTH // 2 + 20, 485, 170, 48)

    def close_modal_rect(self) -> pygame.Rect:
        return pygame.Rect(REFERENCE_WIDTH // 2 - 80, 485, 160, 48)

    # --- Internal drawing helpers ---
    def _draw_recipient_bar(self, target: pygame.Surface, selected_id: str) -> None:
        for idx, r in enumerate(RECIPIENTS):
            rect = self.recipient_rect_at(idx)
            is_selected = (r.recipient_id == selected_id)

            # Avatar background circle
            if is_selected:
                pygame.draw.circle(target, (254, 240, 138), (rect.centerx, rect.top + 28), 34)
                pygame.draw.circle(target, (234, 179, 8), (rect.centerx, rect.top + 28), 32)
            else:
                pygame.draw.circle(target, (51, 65, 85), (rect.centerx, rect.top + 28), 30)

            # Avatar image
            avatar = self._art.get_avatar(r.recipient_id)
            target.blit(avatar, (rect.centerx - 32, rect.top - 4))

            # Recipient name label
            name = self._resources.text(r.name_key)
            color = (254, 240, 138) if is_selected else (203, 213, 225)
            n_surf = self._typography.render(name, FontRole.BODY, 16, color)
            target.blit(n_surf, (rect.centerx - n_surf.get_width() // 2, rect.bottom - 12))

    def _draw_postcard_canvas(
        self,
        target: pygame.Surface,
        draft: PostcardDraft,
        *,
        cursor_visible: bool = True,
    ) -> None:
        # Paper card background
        pygame.draw.rect(target, POSTCARD_BG, POSTCARD_RECT, border_radius=24)
        pygame.draw.rect(target, POSTCARD_BORDER, POSTCARD_RECT, width=4, border_radius=24)

        # Central vertical divider line
        divider_x = POSTCARD_RECT.left + 540
        pygame.draw.line(
            target,
            (203, 213, 225),
            (divider_x, POSTCARD_RECT.top + 24),
            (divider_x, POSTCARD_RECT.bottom - 24),
            3,
        )

        # 1. Left Side: Ruled writing lines and text
        line_y_start = POSTCARD_RECT.top + 60
        line_spacing = 60
        for i in range(5):
            ly = line_y_start + i * line_spacing
            pygame.draw.line(
                target,
                (241, 245, 249),
                (POSTCARD_RECT.left + 30, ly),
                (divider_x - 30, ly),
                2,
            )

        # Render draft message text (child-authored: shown exactly as typed),
        # wrapped onto the ruled lines so it never runs under the stamps.
        text_rect = pygame.Rect(POSTCARD_RECT.left + 30, POSTCARD_RECT.top + 30, MESSAGE_LANE_WIDTH, 320)
        if draft.text:
            spans = self._wrapped_spans(draft.text, FontRole.DISPLAY, 32, MESSAGE_LANE_WIDTH)
            cursor_line, cursor_x = 0, 0
            for index, (a, b) in enumerate(spans[:MAX_MESSAGE_LINES]):
                line = draft.text[a:b].rstrip()
                ly = line_y_start + index * line_spacing
                if line:
                    txt_surf = self._typography.render(line, FontRole.DISPLAY, 32, (30, 41, 59))
                    target.blit(txt_surf, (text_rect.left, ly - txt_surf.get_height() + 6))
                if a <= draft.cursor <= b:
                    cursor_line = index
                    before = draft.text[a:draft.cursor]
                    cursor_x = (
                        self._typography.measure(before, FontRole.DISPLAY, 32).width if before else 0
                    )
            if cursor_visible:
                cy = line_y_start + min(cursor_line, MAX_MESSAGE_LINES - 1) * line_spacing
                pygame.draw.line(
                    target,
                    (2, 132, 199),
                    (text_rect.left + cursor_x, cy - 38),
                    (text_rect.left + cursor_x, cy + 4),
                    3,
                )
        else:
            ph_surf = self._typography.render(
                self._resources.text("prompt.message"),
                FontRole.BODY,
                24,
                (148, 163, 184),
            )
            target.blit(ph_surf, (text_rect.left + 8, line_y_start - ph_surf.get_height() + 6))
            if cursor_visible:
                pygame.draw.line(
                    target,
                    (2, 132, 199),
                    (text_rect.left, line_y_start - 38),
                    (text_rect.left, line_y_start + 4),
                    3,
                )

        # 2. Right Side: Stamps and Address
        for idx, s in enumerate(STAMPS):
            s_rect = self.stamp_rect_at(idx)
            is_selected = (s.stamp_id == draft.stamp_id)
            self._art.draw_stamp(target, s_rect, s, is_selected=is_selected)

        # Address Box
        addr_y = POSTCARD_RECT.top + 220
        to_label = f"{self._resources.text('prompt.to')} {self._resources.text(f'recipient.{draft.recipient_id}')}"
        to_surf = self._typography.render(to_label, FontRole.TITLE, 26, (120, 53, 15))
        target.blit(to_surf, (divider_x + 30, addr_y))

        # Avatar on address
        avatar = self._art.get_avatar(draft.recipient_id)
        target.blit(avatar, (POSTCARD_RECT.right - 90, addr_y - 10))

        # Address lines
        for i in range(2):
            aly = addr_y + 60 + i * 40
            pygame.draw.line(
                target,
                (203, 213, 225),
                (divider_x + 30, aly),
                (POSTCARD_RECT.right - 30, aly),
                2,
            )

    def _draw_editor_toolbar(
        self,
        target: pygame.Surface,
        library: PostcardLibrary,
        *,
        shared_available: bool,
        shared_state: str,
    ) -> None:
        # Send Button
        pygame.draw.rect(target, (22, 163, 74), SEND_BTN_RECT, border_radius=20)
        pygame.draw.rect(target, (134, 239, 172), SEND_BTN_RECT, width=3, border_radius=20)
        s_txt = self._typography.render(
            self._resources.text("button.send"),
            FontRole.TITLE,
            22,
            (255, 255, 255),
        )
        target.blit(
            s_txt,
            (SEND_BTN_RECT.centerx - s_txt.get_width() // 2, SEND_BTN_RECT.centery - s_txt.get_height() // 2),
        )

        # Gallery Button
        pygame.draw.rect(target, (2, 132, 199), GALLERY_BTN_RECT, border_radius=20)
        pygame.draw.rect(target, (56, 189, 248), GALLERY_BTN_RECT, width=2, border_radius=20)
        g_label = f"{self._resources.text('button.saved')} ({library.count})"
        g_txt = self._typography.render(g_label, FontRole.TITLE, 20, (255, 255, 255))
        target.blit(
            g_txt,
            (
                GALLERY_BTN_RECT.centerx - g_txt.get_width() // 2,
                GALLERY_BTN_RECT.centery - g_txt.get_height() // 2,
            ),
        )

        # Clear Button
        pygame.draw.rect(target, (225, 29, 72), CLEAR_BTN_RECT, border_radius=20)
        c_txt = self._typography.render(
            self._resources.text("button.clear"),
            FontRole.TITLE,
            18,
            (255, 255, 255),
        )
        target.blit(
            c_txt,
            (CLEAR_BTN_RECT.centerx - c_txt.get_width() // 2, CLEAR_BTN_RECT.centery - c_txt.get_height() // 2),
        )

        if shared_available:
            state_color = (
                (16, 185, 129)
                if shared_state in {"pending", "imported", "saved"}
                else (220, 38, 38)
                if shared_state == "error"
                else (2, 132, 199)
            )
            pygame.draw.rect(
                target,
                (235, 247, 255),
                SHARED_IMPORT_BTN_RECT,
                border_radius=18,
            )
            pygame.draw.rect(
                target,
                state_color,
                SHARED_IMPORT_BTN_RECT,
                width=3,
                border_radius=18,
            )
            cx, cy = SHARED_IMPORT_BTN_RECT.center
            # Page + downward arrow: bring a saved text creation into draft.
            pygame.draw.rect(
                target,
                (30, 41, 59),
                (cx - 28, cy - 15, 30, 34),
                width=3,
                border_radius=4,
            )
            pygame.draw.line(
                target, state_color, (cx + 18, cy - 15), (cx + 18, cy + 10), 4
            )
            pygame.draw.lines(
                target,
                state_color,
                False,
                [(cx + 9, cy + 2), (cx + 18, cy + 11), (cx + 27, cy + 2)],
                4,
            )

    def _draw_thumbnail_card(
        self,
        target: pygame.Surface,
        rect: pygame.Rect,
        card: SavedPostcard,
        *,
        is_selected: bool = False,
    ) -> None:
        pygame.draw.rect(target, POSTCARD_BG, rect, border_radius=14)
        if is_selected:
            pygame.draw.rect(target, (56, 189, 248), rect, width=4, border_radius=14)
        else:
            pygame.draw.rect(target, (217, 119, 6), rect, width=2, border_radius=14)

        # Stamp in miniature
        stamp_obj = next((s for s in STAMPS if s.stamp_id == card.stamp_id), STAMPS[0])
        s_mini = pygame.Rect(rect.right - 44, rect.top + 8, 36, 36)
        self._art.draw_stamp(target, s_mini, stamp_obj)

        # Recipient avatar in miniature
        avatar = self._art.get_avatar(card.recipient_id)
        scaled_av = pygame.transform.scale(avatar, (32, 32))
        target.blit(scaled_av, (rect.left + 10, rect.top + 10))

        # Text preview
        snippet = card.text if card.text else "💌"
        t_surf = self._typography.render(snippet[:14], FontRole.BODY, 16, (30, 41, 59))
        target.blit(t_surf, (rect.left + 10, rect.bottom - 28))

    def _draw_card_modal(
        self,
        target: pygame.Surface,
        card: SavedPostcard,
        *,
        confirm_delete: bool = False,
        shared_available: bool = False,
        shared_state: str = "",
    ) -> None:
        overlay = pygame.Surface((REFERENCE_WIDTH, REFERENCE_HEIGHT), pygame.SRCALPHA)
        overlay.fill((15, 23, 42, 210))
        target.blit(overlay, (0, 0))

        modal_rect = pygame.Rect(REFERENCE_WIDTH // 2 - 320, 100, 640, 360)
        draft = PostcardDraft(recipient_id=card.recipient_id, stamp_id=card.stamp_id, text=card.text)

        # Draw full card inside modal
        pygame.draw.rect(target, POSTCARD_BG, modal_rect, border_radius=20)
        pygame.draw.rect(target, POSTCARD_BORDER, modal_rect, width=4, border_radius=20)

        # Stamp
        stamp_obj = next((s for s in STAMPS if s.stamp_id == card.stamp_id), STAMPS[0])
        s_rect = pygame.Rect(modal_rect.right - 90, modal_rect.top + 20, 70, 70)
        self._art.draw_stamp(target, s_rect, stamp_obj, is_selected=True)

        # Recipient label & avatar
        to_label = f"{self._resources.text('prompt.to')} {self._resources.text(f'recipient.{card.recipient_id}')}"
        to_surf = self._typography.render(to_label, FontRole.TITLE, 24, (120, 53, 15))
        target.blit(to_surf, (modal_rect.left + 30, modal_rect.top + 30))

        avatar = self._art.get_avatar(card.recipient_id)
        target.blit(avatar, (modal_rect.left + 30 + to_surf.get_width() + 15, modal_rect.top + 16))

        # Message Text
        # Child-authored text is shown exactly as written; a stamp-only card
        # simply shows its stamp (no fixed-language placeholder sentence).
        if card.text:
            for index, (a, b) in enumerate(
                self._wrapped_spans(card.text, FontRole.DISPLAY, 30, MODAL_MESSAGE_LANE_WIDTH)[:MAX_MESSAGE_LINES]
            ):
                line = card.text[a:b].rstrip()
                if line:
                    m_surf = self._typography.render(line, FontRole.DISPLAY, 30, (30, 41, 59))
                    target.blit(m_surf, (modal_rect.left + 40, modal_rect.top + 130 + index * 42))

        # Modal Controls
        if confirm_delete:
            del_rect = self.delete_btn_rect()
            pygame.draw.rect(target, (225, 29, 72), del_rect, border_radius=18)
            d_txt = self._typography.render(
                self._resources.text("button.delete"),
                FontRole.TITLE,
                20,
                (255, 255, 255),
            )
            target.blit(
                d_txt,
                (del_rect.centerx - d_txt.get_width() // 2, del_rect.centery - d_txt.get_height() // 2),
            )

            can_rect = self.cancel_btn_rect()
            pygame.draw.rect(target, (51, 65, 85), can_rect, border_radius=18)
            c_txt = self._typography.render(
                self._resources.text("button.cancel"),
                FontRole.TITLE,
                20,
                (255, 255, 255),
            )
            target.blit(
                c_txt,
                (can_rect.centerx - c_txt.get_width() // 2, can_rect.centery - c_txt.get_height() // 2),
            )
        else:
            del_rect = self.delete_btn_rect()
            pygame.draw.rect(target, (225, 29, 72), del_rect, border_radius=18)
            d_txt = self._typography.render(
                self._resources.text("button.delete"),
                FontRole.TITLE,
                20,
                (255, 255, 255),
            )
            target.blit(
                d_txt,
                (del_rect.centerx - d_txt.get_width() // 2, del_rect.centery - d_txt.get_height() // 2),
            )

            if shared_available and card.text.strip():
                share_rect = self.share_btn_rect()
                share_color = (
                    (16, 185, 129)
                    if shared_state == "saved"
                    else (220, 38, 38)
                    if shared_state == "error"
                    else (2, 132, 199)
                )
                pygame.draw.rect(
                    target, (235, 247, 255), share_rect, border_radius=18
                )
                pygame.draw.rect(
                    target,
                    share_color,
                    share_rect,
                    width=3,
                    border_radius=18,
                )
                cx, cy = share_rect.center
                pygame.draw.rect(
                    target,
                    (30, 41, 59),
                    (cx - 24, cy - 10, 30, 28),
                    width=3,
                    border_radius=4,
                )
                pygame.draw.line(
                    target,
                    share_color,
                    (cx + 18, cy + 12),
                    (cx + 18, cy - 13),
                    4,
                )
                pygame.draw.lines(
                    target,
                    share_color,
                    False,
                    [
                        (cx + 9, cy - 5),
                        (cx + 18, cy - 14),
                        (cx + 27, cy - 5),
                    ],
                    4,
                )

            close_rect = self.cancel_btn_rect()
            pygame.draw.rect(target, (2, 132, 199), close_rect, border_radius=18)
            cl_txt = self._typography.render("CHIUDI", FontRole.TITLE, 20, (255, 255, 255))
            target.blit(
                cl_txt,
                (
                    close_rect.centerx - cl_txt.get_width() // 2,
                    close_rect.centery - cl_txt.get_height() // 2,
                ),
            )
