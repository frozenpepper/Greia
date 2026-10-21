"""Lifecycle and interaction flow for Leo's Post.

One experience: make a picture postcard for a cast friend and send it.

1. **Friend** — tap one of the six canonical friends (their own stamp goes on
   the back);
2. **Front** — a shared wallpaper, or a picture from My Creations (Painting
   drawings, Shape Garden compositions, Teatrino posters) through the trusted
   platform picker;
3. **Stickers** — tap to place (they land on pleasant free spots), drag to
   move, drag off the card to remove; undo removes the last one;
4. **Message** (optional) — the card turns over; type with a keyboard or tap
   picture-words; a Writing page can be brought in. Child text is kept
   exactly as typed. Pre-readers simply skip this step.

**Send** folds the card into a paper plane that flies into Leo's mailbox, then
the friend receives it and cheers with their own approved voice. Sent cards
live in the postbox (paged big cards, deliberate delete with a preview, a
pictorial full-shelf sheet instead of eviction) and can be shared to My
Creations (the picture, plus the message as plain text for Writing).

Every control is a shared-kit control (ADR 0037): pointer, touch, keyboard
(arrows + Space/Enter; Tab toggles between typing and the controls while
writing) and controller (D-pad/stick + south) share one focus ring. Nothing
is placed in the protected Home/Back region; the platform pointer is drawn by
``PygameReferenceCanvas.present``. The unsent card survives Home.
"""

from __future__ import annotations

from collections import deque
from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum
import hashlib
import random
import time

import pygame

from greia_platform.activity_feedback import IdleHintScheduler
from greia_platform.activity_api import activity_stop_requested, mark_activity_ready
from greia_platform.frame_governor import FrameGovernor, FrameKind
from greia_platform.activity_controls import (
    ButtonRole,
    ControlKit,
    ControlLayout,
    ControlTheme,
    KitPointer,
    PointerPhase,
    PygameControlInput,
)
from greia_platform.input_core import InputEdge, SemanticAction, SemanticInputEvent
from greia_platform.localization import LocalizedResources
from greia_platform.pygame_canvas import PygameReferenceCanvas, activity_viewport_for_surface
from greia_platform.pygame_png import PygamePngError, decode_png_surface, encode_surface_png
from greia_platform.typography import GreiaTypography
from greia_platform.ui_core import BoundedCache, SurfaceNavigator, UiEventResult

if __package__:
    from .postcard_art import INK, PAPER, PostcardArt
    from .postcard_audio import PostcardAudio
    from .postcard_content import (
        CARD_PICTURE_SIZE,
        FRIENDS,
        FRONT_PICTURE_ROLES,
        HOST,
        MAX_SAVED_CARDS,
        MESSAGE_EMOJI,
        MESSAGE_TEXT_ROLES,
        POSTBOX_PAGE_SIZE,
        REFERENCE_HEIGHT,
        REFERENCE_WIDTH,
        SCENES,
        SHARE_ROLE,
        STICKERS,
        friend as friend_info,
    )
    from .postcard_controls import STEPS, PostcardControls, PostcardSheet, PostcardSheets, TrayItem
    from .postcard_layout import CardViewLayout, ComposerLayout, DeliveredLayout, PostboxLayout, SheetLayout
    from .postcard_model import CardFront, PostcardDraft, PostcardLibrary, SavedPostcard
    from .postcard_renderer import FLIP_SECONDS, SEND_SECONDS, CastActor, FxBurst, Motion, PostcardRenderer
    from .postcard_services import EventPort, StoragePort
else:
    from postcard_art import INK, PAPER, PostcardArt
    from postcard_audio import PostcardAudio
    from postcard_content import (
        CARD_PICTURE_SIZE,
        FRIENDS,
        FRONT_PICTURE_ROLES,
        HOST,
        MAX_SAVED_CARDS,
        MESSAGE_EMOJI,
        MESSAGE_TEXT_ROLES,
        POSTBOX_PAGE_SIZE,
        REFERENCE_HEIGHT,
        REFERENCE_WIDTH,
        SCENES,
        SHARE_ROLE,
        STICKERS,
        friend as friend_info,
    )
    from postcard_controls import STEPS, PostcardControls, PostcardSheet, PostcardSheets, TrayItem
    from postcard_layout import CardViewLayout, ComposerLayout, DeliveredLayout, PostboxLayout, SheetLayout
    from postcard_model import CardFront, PostcardDraft, PostcardLibrary, SavedPostcard
    from postcard_renderer import FLIP_SECONDS, SEND_SECONDS, CastActor, FxBurst, Motion, PostcardRenderer
    from postcard_services import EventPort, StoragePort

HALO_SECONDS = 1.8
ADVANCE_DELAY = 0.45
DRAFT_SAVE_IDLE = 2.5
PICKER_POLL_SECONDS = 0.12
FEEDBACK_SECONDS = 2.0
CARET_BLINK = 0.5
MAX_SCHEDULED = 32
DRAG_SLOP = 10


class Screen(StrEnum):
    COMPOSER = "composer"
    SENDING = "sending"
    DELIVERED = "delivered"
    POSTBOX = "postbox"
    CARD = "card"


class Timeline:
    """Tiny bounded scheduler for the scripted moments."""

    def __init__(self, clock: Callable[[], float]) -> None:
        self._clock = clock
        self._entries: deque[tuple[float, Callable[[], object]]] = deque(maxlen=MAX_SCHEDULED)

    def after(self, delay: float, action: Callable[[], object]) -> None:
        self._entries.append((self._clock() + delay, action))

    def run_due(self) -> bool:
        now = self._clock()
        due = [entry for entry in self._entries if entry[0] <= now]
        if not due:
            return False
        for entry in due:
            self._entries.remove(entry)
        for _, action in sorted(due, key=lambda entry: entry[0]):
            action()
        return True

    @property
    def busy(self) -> bool:
        return bool(self._entries)

    def clear(self) -> None:
        self._entries.clear()


@dataclass(slots=True)
class StickerDrag:
    index: int
    start: tuple[int, int]
    position: tuple[int, int]
    grab: tuple[int, int]
    moved: bool = False


class PostcardActivity:
    """Coordinate the composer, the flight, delivery, the postbox and sharing."""

    def __init__(
        self,
        *,
        screen: pygame.Surface,
        canvas: PygameReferenceCanvas,
        typography: GreiaTypography,
        resources: LocalizedResources | None,
        storage: StoragePort,
        events: EventPort,
        audio: PostcardAudio,
        rng: random.Random | None = None,
        creations=None,
        library: PostcardLibrary | None = None,
        draft: PostcardDraft | None = None,
        draft_picture: bytes | None = None,
        clock: Callable[[], float] = time.monotonic,
        wall_clock: Callable[[], float] = time.time,
        kit: ControlKit | None = None,
        art: PostcardArt | None = None,
    ) -> None:
        self.screen = screen
        self.canvas = canvas
        self.typography = typography
        self.resources = resources
        self.storage = storage
        self.events = events
        self.audio = audio
        self.rng = rng if rng is not None else random.Random()
        self.creations = creations
        self.clock = clock
        self._wall_clock = wall_clock

        # Shared control kit (ADR 0037): Create Collection -> coral accent.
        self.kit = kit if kit is not None else ControlKit(typography, ControlTheme.for_accent("coral"))
        self.art = art if art is not None else PostcardArt(self.kit.painter)
        self.renderer = PostcardRenderer(self.art, typography, clock)
        self.motion = Motion()
        self.timeline = Timeline(clock)
        self.host = CastActor(HOST, self.art, clock, height=196, point_left=True)
        self.friend_actor: CastActor | None = None
        self.controls = PostcardControls(
            self.kit,
            on_step=self._on_step,
            on_send=self._on_send,
            on_postbox=self.open_postbox,
            on_new_card=self._on_new_card,
            on_page=self._on_page,
            on_delete_focused=self._on_delete_focused,
            on_back=self._on_back,
            on_flip=self._on_flip,
            on_share=self._on_share,
            on_delete_open=self._on_delete_open,
        )
        self._surfaces = SurfaceNavigator(self.controls.layer)
        self._input = PygameControlInput(to_logical=canvas.pointer, is_safe=lambda pos: _safe_point(self.screen, pos))
        self._layout_source = ControlLayout.for_canvas(canvas, screen.get_size())

        # Library is the authority; load once (never per frame).
        self.library = library if library is not None else storage.load()
        self.draft = draft if draft is not None else PostcardDraft()
        self.draft_picture_png: bytes | None = None
        self.draft_picture: pygame.Surface | None = None
        self._picture_token = 0
        if draft_picture is not None and self.draft.front is not None and self.draft.front.is_picture:
            if not self._set_draft_picture(draft_picture):
                self.draft.front = None
        self._pictures: BoundedCache[str, pygame.Surface | None] = BoundedCache(8)

        self.state = Screen.COMPOSER
        self.step = "friend"
        self.sheet: PostcardSheet | None = None
        self.drag: StickerDrag | None = None
        self.delete_target: str | None = None
        self.open_card_id: str | None = None
        self.card_back = False
        self.delivered: SavedPostcard | None = None
        self.postbox_page = 0
        self.toolbar_focus = False
        self._swallow_text = ""
        self._text_input_on = False

        # Trusted My Creations exchange (text and picture share one slot).
        self.shared_request: str | None = None
        self.shared_kind = ""
        self.shared_next_poll = 0.0
        self.shared_state = ""
        self.shared_feedback_until = 0.0
        self._shared_card_ids: set[str] = set()

        self._running = True
        self.ready_published = False
        self._dirty = True
        self._activated = False
        self._last_activity = clock()
        self._hints = IdleHintScheduler(now=self._last_activity)
        self._caret_on = True
        self._caret_flip = clock()
        self._draft_saved_revision = self.draft.revision
        self._draft_changed_at = clock()
        self._layouts: dict[str, object] = {}
        self._build_layouts()
        start = "friend"
        if self.draft.recipient_id is not None:
            start = "picture" if self.draft.front is None else "stickers"
        self._enter_composer(start)
        if self.draft.is_blank:
            # Pictorial opening (no voice line exists yet): Leo points at the
            # friends and the tray glows once.
            self.timeline.after(1.0, self._opening_hint)

    def _opening_hint(self) -> None:
        if self.state is Screen.COMPOSER and self.sheet is None and self.draft.recipient_id is None:
            self.host.point(HALO_SECONDS)
            self.audio.leo_says("who_is_it_for")  # "Who is it for?"
            self.motion.halos["tray"] = self.clock() + HALO_SECONDS
            self._dirty = True

    # -- main loop ------------------------------------------------------------------

    def run(self) -> int:
        frames = FrameGovernor()
        try:
            while self._running and not activity_stop_requested():
                for event in frames.events():
                    self.handle_event(event)
                repeat = self._input.poll()
                if repeat is not None:
                    self._dispatch(repeat)
                animating = self.step_frame()
                frame = frames.frame(dirty=self._dirty, animating=animating)
                if frame is FrameKind.FULL:
                    self.render()
                    self.canvas.present()
                    pygame.display.flip()
                    self._dirty = False
                    if not self.ready_published:
                        mark_activity_ready()
                        self.ready_published = True
                elif frame is FrameKind.POINTER:
                    self.canvas.present_pointer()
                frames.wait(polling=self._input.repeating)
        finally:
            self.shutdown()
        return 0

    def shutdown(self) -> None:
        """Keep the unsent card (Home mid-card) and release audio/text input."""

        self._persist_draft(force=True)
        self.audio.stop()
        self._set_text_input(False)
        self._surfaces.close()

    def step_frame(self) -> bool:
        """Advance timers; return True while something on screen is moving."""

        now = self.clock()
        if self.timeline.run_due():
            self._dirty = True
        if self.host.update():
            self._dirty = True
        if self.friend_actor is not None and self.friend_actor.update():
            self._dirty = True
        self.motion.prune(now)
        if self._step_shared(now):
            self._dirty = True
        if self.state is Screen.COMPOSER and self.sheet is None:
            self._maybe_hint(now)
            if self.step == "message" and not self.toolbar_focus and now - self._caret_flip >= CARET_BLINK:
                self._caret_on = not self._caret_on
                self._caret_flip = now
                self._dirty = True
        if self.draft.revision != self._draft_saved_revision and now - self._draft_changed_at >= DRAFT_SAVE_IDLE:
            self._persist_draft()
        if self.controls.layer.invalidation.should_draw or (self.sheet is not None and self.sheet.layer.invalidation.should_draw):
            self._dirty = True
        sending = self.state is Screen.SENDING
        friend = self.friend_actor is not None and self.friend_actor.animating
        return self.motion.active(now) or self.host.animating or friend or sending or self.drag is not None

    # -- rendering --------------------------------------------------------------------

    def render(self) -> None:
        surface = self.canvas.surface
        state = self.state
        if state is Screen.COMPOSER:
            layout = self.composer_layout
            drag = None
            skip = None
            if self.drag is not None and self.drag.moved:
                skip = self.drag.index
                drag = (self._sticker_image(self.draft.stickers[self.drag.index].sticker_id), self.drag.position)
            showing_back = self.step == "message"
            self.renderer.draw_composer(
                surface,
                layout,
                face=self._draft_face(layout.card.size, skip=skip),
                back=self._back(self.draft.recipient_id, self.draft.stamp_id, layout.card.size) if showing_back else None,
                showing_back=showing_back,
                text=self.draft.text,
                cursor=self.draft.cursor if (showing_back and self._caret_on and not self.toolbar_focus and self.sheet is None) else None,
                motion=self.motion,
                host=self.host,
                drag=drag,
                done_steps=self._done_steps(),
                postbox_count=self.library.count,
            )
        elif state is Screen.SENDING:
            layout = self.composer_layout
            self.renderer.draw_sending(
                surface, layout, self.motion, self.host, self.library.count, blank_face=self._draft_face(layout.card.size),
            )
        elif state is Screen.DELIVERED and self.delivered is not None and self.friend_actor is not None:
            layout = self.delivered_layout
            self.renderer.draw_delivered(
                surface,
                layout,
                face=self._saved_face(self.delivered, layout.card.size),
                face_key=self.delivered.card_id,
                friend=self.friend_actor,
                motion=self.motion,
            )
        elif state is Screen.POSTBOX:
            layout = self.postbox_layout
            cards = self._page_cards()
            faces = [
                (rect, self._saved_face(card, rect.size), card.recipient_id, bool(card.text.strip()))
                for rect, card in zip(layout.cards, cards)
            ]
            self.renderer.draw_postbox(
                surface,
                layout,
                faces,
                page=self.postbox_page,
                page_count=self._page_count(),
                focus_slot=self.controls.focused_card_slot() if self.controls.layer.focus_visible else None,
                full=self.library.is_full,
                empty_icon=None,
            )
        elif state is Screen.CARD:
            card = self._open_card()
            if card is not None and self.friend_actor is not None:
                layout = self.card_layout
                self.renderer.draw_card_view(
                    surface,
                    layout,
                    face=self._saved_face(card, layout.card.size),
                    back=self._back(card.recipient_id, card.stamp_id, layout.card.size),
                    showing_back=self.card_back,
                    text=card.text,
                    friend=self.friend_actor,
                    motion=self.motion,
                )
        self._surfaces.draw(surface)
        if state is Screen.COMPOSER and self.sheet is None:
            self.renderer.draw_composer_overlays(surface)
        if state is Screen.SENDING:
            self.renderer.draw_flight(surface, self.composer_layout, self.motion)
        if state in (Screen.COMPOSER, Screen.POSTBOX):
            # Delivery and card-view bursts are drawn with their friend.
            for burst in self.motion.bursts:
                burst.draw(surface)
        self.controls.layer.invalidation.mark_drawn()

    # -- input ---------------------------------------------------------------------------

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.QUIT:
            self._running = False
            return
        if event.type == pygame.VIDEORESIZE:
            self._resize()
            return
        if event.type == pygame.TEXTINPUT:
            self._text_input(event.text)
            return
        if event.type == pygame.KEYDOWN:
            self._swallow_text = ""
            if event.key == pygame.K_ESCAPE:
                self._escape()
                return
            if self._typing_active():
                # Writing: keys keep their text meaning; Tab reaches the controls.
                if event.key == pygame.K_TAB:
                    self._set_toolbar_focus(True)
                else:
                    self._edit_key(event)
                return
            if self.state is Screen.COMPOSER and self.step == "message" and self.toolbar_focus and event.key == pygame.K_TAB:
                self._set_toolbar_focus(False)
                return
        elif event.type == pygame.KEYUP and self._typing_active():
            return
        translated = self._input.translate(event)
        if translated is None:
            return
        consumed = self._dispatch(translated)
        if consumed and event.type == pygame.KEYDOWN:
            # A key a control consumed must not also type: SDL sends that
            # key's TEXTINPUT (e.g. Space) right after its KEYDOWN.
            self._swallow_text = getattr(event, "unicode", "") or ""

    def _typing_active(self) -> bool:
        return (
            self.state is Screen.COMPOSER
            and self.step == "message"
            and self.sheet is None
            and not self.toolbar_focus
        )

    def _edit_key(self, event: pygame.event.Event) -> bool:
        key = event.key
        draft = self.draft
        if key == pygame.K_BACKSPACE:
            changed = draft.backspace()
        elif key == pygame.K_DELETE:
            changed = draft.delete_forward()
        elif key == pygame.K_LEFT:
            changed = draft.move_left()
        elif key == pygame.K_RIGHT:
            changed = draft.move_right()
        elif key in (pygame.K_HOME, pygame.K_UP):
            draft.move_home()
            changed = True
        elif key in (pygame.K_END, pygame.K_DOWN):
            draft.move_end()
            changed = True
        elif key in (pygame.K_RETURN, pygame.K_KP_ENTER):
            changed = False  # one short message: Enter never adds lines
        else:
            return False
        if changed:
            self._typed()
        return True

    def _text_input(self, text: str) -> None:
        swallow, self._swallow_text = self._swallow_text, ""
        if swallow and text == swallow:
            return
        if self.state is Screen.COMPOSER and self.step == "message" and self.sheet is None and self.toolbar_focus:
            # Typing returns from the controls to the message.
            self._set_toolbar_focus(False)
        if not self._typing_active():
            return
        if self.draft.insert(text):
            self.audio.play("tick")
            self._typed()

    def _typed(self) -> None:
        self._note_activity()
        self._caret_on = True
        self._caret_flip = self.clock()
        self._draft_touched()
        self._refresh_step_icons()
        self._dirty = True

    def _escape(self) -> None:
        if self.sheet is not None:
            self.sheet.dismiss()
        elif self.state is Screen.COMPOSER and self.step == "message" and self.toolbar_focus:
            self._set_toolbar_focus(False)
        elif self.state is Screen.CARD:
            self.open_postbox()
        elif self.state in (Screen.POSTBOX, Screen.DELIVERED):
            self._enter_composer(self.step if self.state is Screen.POSTBOX else "friend")
        elif self.state is Screen.SENDING:
            self._show_delivered()
        else:
            self._running = False
        self._dirty = True

    def _resize(self) -> None:
        self.screen = pygame.display.get_surface() or self.screen
        self.canvas = PygameReferenceCanvas(self.screen, hires=True)
        self._input = PygameControlInput(to_logical=self.canvas.pointer, is_safe=lambda pos: _safe_point(self.screen, pos))
        self._layout_source = ControlLayout.for_canvas(self.canvas, self.screen.get_size())
        self._build_layouts()
        self._close_sheet()
        self.drag = None
        self._reshow()
        self._dirty = True

    def _dispatch(self, kit_input) -> bool:
        """Route one kit input; True when something consumed it."""

        if not isinstance(kit_input, KitPointer) or kit_input.phase is not PointerPhase.MOVE:
            self._note_activity()
        else:
            self._dirty = True  # keep the Greia pointer (drawn on present) live
        if self.state is Screen.SENDING:
            return False
        if isinstance(kit_input, KitPointer):
            if self.sheet is None and self.state is Screen.COMPOSER and self._drag_input(kit_input):
                self._dirty = True
                return True
            if (
                kit_input.phase is PointerPhase.DOWN
                and self.state is Screen.COMPOSER
                and self.step == "message"
                and self.sheet is None
                and self.composer_layout.card.collidepoint(kit_input.position)
            ):
                # Tapping the message goes back to writing it.
                self._set_toolbar_focus(False)
        elif isinstance(kit_input, SemanticInputEvent) and kit_input.edge is InputEdge.PRESSED and self.sheet is None:
            if kit_input.action is SemanticAction.CANCEL:
                self._escape()
                return True
            if self._typing_active():
                # A controller press while writing first reveals the controls.
                self._set_toolbar_focus(True)
                return True
        result = self._surfaces.dispatch(kit_input)
        if self.controls.layer.invalidation.should_draw or self.sheet is not None:
            self._dirty = True
        return result is not UiEventResult.IGNORED

    def tap(self, logical: tuple[int, int]) -> bool:
        """Deliver one complete tap at a logical position (tests/tools)."""

        point = (int(logical[0]), int(logical[1]))
        self._activated = False
        self._dispatch(KitPointer(PointerPhase.DOWN, point))
        self._dispatch(KitPointer(PointerPhase.UP, point))
        return self._activated

    def drag_to(self, start: tuple[int, int], end: tuple[int, int]) -> None:
        """Deliver one pointer drag (tests/tools)."""

        self._dispatch(KitPointer(PointerPhase.DOWN, start))
        mid = ((start[0] + end[0]) // 2, (start[1] + end[1]) // 2)
        self._dispatch(KitPointer(PointerPhase.MOVE, mid))
        self._dispatch(KitPointer(PointerPhase.MOVE, end))
        self._dispatch(KitPointer(PointerPhase.UP, end))

    def press(self, key: int, *, text: str = "") -> None:
        """Deliver one key press (+ its text) as SDL would (tests/tools)."""

        self.handle_event(pygame.event.Event(pygame.KEYDOWN, key=key, mod=0, unicode=text))
        if text:
            self.handle_event(pygame.event.Event(pygame.TEXTINPUT, text=text))

    def _note_activity(self) -> None:
        self._last_activity = self.clock()
        self._hints.reset(self._last_activity)

    def _text(self, key: str) -> str:
        if self.resources is None:
            return ""
        try:
            return self.resources.text(key)
        except Exception:
            return ""

    def _set_toolbar_focus(self, active: bool) -> None:
        if active == self.toolbar_focus:
            return
        self.toolbar_focus = active
        layer = self.controls.layer
        if active:
            if layer.focused_id is None or not layer.focus(layer.focused_id, visible=True):
                layer.focus("step.message", visible=True)
        else:
            layer.focus_visible = False
            layer.invalidation.invalidate()
            self._caret_on = True
            self._caret_flip = self.clock()
        self._dirty = True

    def _set_text_input(self, active: bool) -> None:
        if active == self._text_input_on:
            return
        self._text_input_on = active
        try:
            if active:
                pygame.key.start_text_input()
            else:
                pygame.key.stop_text_input()
        except pygame.error:
            pass

    # -- layouts ------------------------------------------------------------------------

    def _build_layouts(self) -> None:
        source = self._layout_source
        protected = source.protected
        button = source.control_height(84, maximum=92)
        self._layouts = {
            "composer": ComposerLayout.build(protected, button=button),
            "postbox": PostboxLayout.build(protected, button=button),
            "card": CardViewLayout.build(protected, button=button),
            "delivered": DeliveredLayout.build(protected, button=button),
            "sheet": SheetLayout.build(protected),
        }
        self.sheets = PostcardSheets(self.kit, self._layouts["sheet"])

    @property
    def composer_layout(self) -> ComposerLayout:
        return self._layouts["composer"]  # type: ignore[return-value]

    @property
    def postbox_layout(self) -> PostboxLayout:
        return self._layouts["postbox"]  # type: ignore[return-value]

    @property
    def card_layout(self) -> CardViewLayout:
        return self._layouts["card"]  # type: ignore[return-value]

    @property
    def delivered_layout(self) -> DeliveredLayout:
        return self._layouts["delivered"]  # type: ignore[return-value]

    def _reshow(self) -> None:
        if self.state is Screen.COMPOSER:
            self._show_composer(keep_focus=True)
        elif self.state is Screen.POSTBOX:
            self._show_postbox()
        elif self.state is Screen.CARD:
            self.controls.show_card(self.card_layout, shared_available=self.creations is not None)
        elif self.state is Screen.DELIVERED:
            self.controls.show_delivered(self.delivered_layout, mailbox_icon=self._mailbox_icon(70))
        else:
            self.controls.hide_all()

    # -- composer ------------------------------------------------------------------------

    def _enter_composer(self, step: str) -> None:
        self._close_sheet()
        self.timeline.clear()
        self.state = Screen.COMPOSER
        self.friend_actor = None
        self.motion.bursts.clear()
        self.step = step
        self.toolbar_focus = False
        self._set_text_input(step == "message")
        self._show_composer(focus=None)
        self._dirty = True

    def _on_step(self, step: str) -> None:
        if self.state is not Screen.COMPOSER or step not in STEPS:
            return
        self._activated = True
        if step == self.step:
            self._show_composer(keep_focus=True)
            return
        self._go_step(step)

    def _go_step(self, step: str, *, focus_tray: bool = False) -> None:
        previous = self.step
        to_back = step == "message" and previous != "message"
        to_front = previous == "message" and step != "message"
        if to_back or to_front:
            size = self.composer_layout.card.size
            face = self._draft_face(size)
            back = self._back(self.draft.recipient_id, self.draft.stamp_id, size)
            start, end = (face, back) if to_back else (back, face)
            self.motion.flip_frames = self.renderer.flip_frames(start, end)
            self.motion.flip_start = self.clock()
            self.audio.play("flip")
        else:
            self.audio.play("tick")
        if step == "picture" and previous == "friend":
            self.audio.leo_says("pick_picture")  # "Pick a picture!"
        self.step = step
        self.toolbar_focus = False
        self._set_text_input(step == "message")
        items = self._tray_items()
        first = items[0].control_id if items else None
        visible = self.controls.layer.focus_visible
        self._show_composer(focus=first if (focus_tray or visible) else f"step.{step}", keep_focus=False)
        if step == "message" and visible and not focus_tray:
            # Keyboard players arrive ready to type; the ring hides until Tab.
            self.controls.layer.focus_visible = False
        self._dirty = True

    def _show_composer(self, *, focus: str | None = None, keep_focus: bool = True) -> None:
        items = self._tray_items()
        self.controls.show_composer(
            self.composer_layout,
            self.step,
            items,
            step_icons=self._step_icons(),
            mailbox_icon=self._mailbox_icon(80),
            focus=focus,
            keep_focus=keep_focus,
        )
        self.renderer.remember_tray({item.control_id: control.rect for item, control in zip(items, self.controls.tray)})
        self.controls.send.enabled = True

    def _refresh_step_icons(self) -> None:
        icons = self._step_icons()
        for slot in self.controls.steps.slots:
            slot.icon = icons.get(slot.tool_id)
        self.controls.layer.invalidation.invalidate()

    def _tray_items(self) -> list[TrayItem]:
        step = self.step
        if step == "friend":
            return [
                TrayItem(
                    f"friend.{info.friend_id}",
                    self.art.cast(info.friend_id, "happy", 78),
                    (lambda chosen=info.friend_id: self._choose_friend(chosen)),
                    selected=self.draft.recipient_id == info.friend_id,
                )
                for info in FRIENDS
            ]
        if step == "picture":
            items = [
                TrayItem(
                    f"scene.{info.scene_id}",
                    self.art.scene_tile(info.scene_id, 76),
                    (lambda chosen=info.scene_id: self._choose_scene(chosen)),
                    selected=self.draft.front == CardFront.scene(info.scene_id),
                )
                for info in SCENES
            ]
            if self.creations is not None:
                chosen = self.draft.front is not None and self.draft.front.is_picture and self.draft_picture is not None
                icon = (
                    self.art.picture_tile(self.draft_picture, 76, self._picture_token)
                    if chosen and self.draft_picture is not None
                    else self.kit.glyph("import", 56)
                )
                items.append(TrayItem("picture.import", icon, self._request_shared_picture, selected=chosen,
                                      enabled=self.shared_request is None))
            return items
        if step == "stickers":
            full = self.draft.stickers_full
            items = [
                TrayItem(
                    f"sticker.{info.sticker_id}",
                    self.art.sticker_image(info.sticker_id, 62),
                    (lambda chosen=info.sticker_id: self._add_sticker(chosen)),
                    enabled=not full,
                )
                for info in STICKERS
            ]
            items.append(TrayItem("sticker.undo", self.kit.glyph("undo", 50), self._undo_sticker, enabled=bool(self.draft.stickers)))
            return items
        items = [
            TrayItem(f"emoji.{index}", self.kit.text_icon(cluster, 46), (lambda chosen=cluster: self._type_emoji(chosen)))
            for index, cluster in enumerate(MESSAGE_EMOJI)
        ]
        items.append(TrayItem("message.erase", self.kit.glyph("undo", 50), self._erase_one, enabled=bool(self.draft.text)))
        if self.creations is not None:
            items.append(TrayItem("message.import", self.kit.glyph("import", 54), self._request_shared_text,
                                  enabled=self.shared_request is None))
        return items

    def _step_icons(self) -> dict[str, pygame.Surface | None]:
        draft = self.draft
        friend_icon = (
            self.art.cast(draft.recipient_id, "happy", 62)
            if draft.recipient_id is not None
            else self.art.cast(HOST, "pose_think", 62)
        )
        if draft.front is None:
            picture_icon = self.kit.glyph("page", 52)
        elif draft.front.is_picture and self.draft_picture is not None:
            picture_icon = self.art.picture_tile(self.draft_picture, 62, self._picture_token)
        elif draft.front.scene_id is not None:
            picture_icon = self.art.scene_tile(draft.front.scene_id, 62)
        else:
            picture_icon = self.kit.glyph("page", 52)
        stickers = draft.stickers
        sticker_icon = self.art.sticker_image(stickers[-1].sticker_id if stickers else "star", 54)
        message_icon = self.art.picture("prop.everyday.pencil", 58)
        return {"friend": friend_icon, "picture": picture_icon, "stickers": sticker_icon, "message": message_icon}

    def _done_steps(self) -> set[str]:
        done = set()
        if self.draft.recipient_id is not None:
            done.add("friend")
        if self.draft.front is not None:
            done.add("picture")
        if self.draft.stickers:
            done.add("stickers")
        if self.draft.text.strip():
            done.add("message")
        return done

    def _choose_friend(self, friend_id: str) -> None:
        self._activated = True
        changed = self.draft.set_recipient(friend_id)
        self.audio.play("pop")
        self._draft_touched()
        self._show_composer(keep_focus=True)
        if changed and self.draft.front is None:
            self._advance("picture")
        self._dirty = True

    def _choose_scene(self, scene_id: str) -> None:
        self._activated = True
        changed = self.draft.set_front(CardFront.scene(scene_id))
        self.audio.play("pop")
        self._draft_touched()
        self._show_composer(keep_focus=True)
        if changed and not self.draft.stickers:
            self._advance("stickers")
        self._dirty = True

    def _advance(self, step: str) -> None:
        """Move on to the next step after a short beat (the choice is seen first)."""

        def go() -> None:
            if self.state is Screen.COMPOSER and self.sheet is None and self.step != step:
                self._go_step(step, focus_tray=self.controls.layer.focus_visible)

        self.timeline.after(ADVANCE_DELAY, go)

    def _add_sticker(self, sticker_id: str) -> None:
        self._activated = True
        index = self.draft.add_sticker(sticker_id)
        if index is None:
            self.host.try_again()
            self.motion.halos["tray:sticker.undo"] = self.clock() + HALO_SECONDS
            self._dirty = True
            return
        self.audio.play("pop")
        placed = self.draft.stickers[index]
        self._burst("sparkle", self._sticker_centre(placed.x, placed.y))
        self._draft_touched()
        self._show_composer(keep_focus=True)
        self._dirty = True

    def _undo_sticker(self) -> None:
        self._activated = True
        if self.draft.pop_sticker():
            self.audio.play("swish")
            self._draft_touched()
            self._show_composer(keep_focus=True)
            self._dirty = True

    def _type_emoji(self, cluster: str) -> None:
        self._activated = True
        if self.draft.insert(cluster):
            self.audio.play("pop")
            self._typed()
            self._show_composer(keep_focus=True)

    def _erase_one(self) -> None:
        self._activated = True
        if self.draft.backspace():
            self.audio.play("tick")
            self._typed()
            self._show_composer(keep_focus=True)

    def _draft_touched(self) -> None:
        self._draft_changed_at = self.clock()
        self._refresh_step_icons()

    # -- sticker dragging ---------------------------------------------------------------

    def _card_inner(self) -> pygame.Rect:
        card = self.composer_layout.card
        return self.art.card_inner(card.size).move(card.topleft)

    def _sticker_centre(self, x: float, y: float) -> tuple[int, int]:
        inner = self._card_inner()
        return (inner.left + round(x * inner.width), inner.top + round(y * inner.height))

    def _sticker_image(self, sticker_id: str) -> pygame.Surface | None:
        return self.art.sticker_image(sticker_id, self.art.sticker_height(self._card_inner().height))

    def _sticker_at(self, point: tuple[int, int]) -> int | None:
        radius = self.art.sticker_height(self._card_inner().height) * 0.5
        for index in range(len(self.draft.stickers) - 1, -1, -1):
            placed = self.draft.stickers[index]
            cx, cy = self._sticker_centre(placed.x, placed.y)
            if (point[0] - cx) ** 2 + (point[1] - cy) ** 2 <= radius * radius:
                return index
        return None

    def _drag_input(self, event: KitPointer) -> bool:
        """Pointer drags of placed stickers (front showing, nothing flipping)."""

        if self.step == "message" or self.motion.flip_frames:
            return False
        if event.phase is PointerPhase.DOWN:
            if self.controls.layer.hit(event.position) is not None:
                return False
            index = self._sticker_at(event.position)
            if index is None:
                return False
            placed = self.draft.stickers[index]
            cx, cy = self._sticker_centre(placed.x, placed.y)
            self.drag = StickerDrag(index, event.position, (cx, cy), (event.position[0] - cx, event.position[1] - cy))
            return True
        drag = self.drag
        if drag is None:
            return False
        if event.phase is PointerPhase.MOVE:
            dx, dy = event.position[0] - drag.start[0], event.position[1] - drag.start[1]
            if drag.moved or dx * dx + dy * dy > DRAG_SLOP * DRAG_SLOP:
                drag.moved = True
                drag.position = (event.position[0] - drag.grab[0], event.position[1] - drag.grab[1])
            return True
        if event.phase in (PointerPhase.UP, PointerPhase.CANCEL):
            self.drag = None
            if not drag.moved or event.phase is PointerPhase.CANCEL:
                return True
            inner = self._card_inner()
            centre = (event.position[0] - drag.grab[0], event.position[1] - drag.grab[1])
            if inner.inflate(20, 20).collidepoint(centre):
                self.draft.move_sticker(drag.index, (centre[0] - inner.left) / inner.width, (centre[1] - inner.top) / inner.height)
                self.audio.play("tick")
            else:
                self.draft.remove_sticker(drag.index)
                self.audio.play("swish")
                self._burst("dust_puff", centre)
            self._draft_touched()
            self._show_composer(keep_focus=True)
            return True
        return False

    # -- send / deliver ------------------------------------------------------------------

    def _missing_step(self) -> str | None:
        if self.draft.recipient_id is None:
            return "friend"
        if self.draft.front is None:
            return "picture"
        return None

    def _on_send(self) -> None:
        if self.state is not Screen.COMPOSER or self.sheet is not None:
            return
        self._activated = True
        missing = self._missing_step()
        if missing is not None:
            # Demonstrate what is still needed: Leo thinks, the step opens,
            # the tray glows. Unlimited, kind retry.
            self.host.try_again()
            if self.step != missing:
                self._go_step(missing)
            until = self.clock() + HALO_SECONDS
            self.motion.halos[f"step.{missing}"] = until
            self.motion.halos["tray"] = until
            self._dirty = True
            return
        if self.library.is_full:
            self._open_full_sheet()
            return
        card = self._save_card()
        if card is None:
            self.host.try_again()
            self._dirty = True
            return
        self._start_flight(card)

    def _save_card(self) -> SavedPostcard | None:
        draft = self.draft
        assert draft.recipient_id is not None and draft.front is not None
        now = int(self._wall_clock())
        card_id = f"card-{now}-{self.rng.randrange(1_000_000):06d}"
        card = SavedPostcard(card_id, now, draft.recipient_id, draft.stamp_id, draft.text, draft.front, draft.stickers)
        pictures = None
        if card.front.is_picture:
            if not self.draft_picture_png:
                return None
            pictures = {card_id: self.draft_picture_png}
        if not self.library.add(card):
            return None
        if not self.storage.save(self.library, new_pictures=pictures):
            self.library.delete(card_id)
            return None
        if self.draft_picture is not None and card.front.is_picture:
            self._pictures[card_id] = self.draft_picture
        try:
            self.events.postcard_created(card)
        except Exception:
            pass
        return card

    def _start_flight(self, card: SavedPostcard) -> None:
        layout = self.composer_layout
        face = self._saved_face(card, layout.card.size)
        self.delivered = card
        self.state = Screen.SENDING
        self.motion.halos.clear()
        self.motion.flip_frames = ()
        self.motion.send_frames = self.renderer.send_frames(face)
        self.motion.send_start = self.clock()
        self._set_text_input(False)
        self.audio.play("whoosh")
        self.audio.leo_says("off_it_goes")  # "Off it goes!" as the card flies
        self.timeline.after(SEND_SECONDS - 0.5, self._landed)
        self.timeline.after(SEND_SECONDS + 0.15, self._show_delivered)
        # The postcard is saved: the draft starts over (and is forgotten).
        self.draft.reset()
        self._set_draft_picture(None)
        self.storage.clear_draft()
        self._draft_saved_revision = self.draft.revision
        # The controls stay put (input is held while it flies) and are ready
        # for the next card; the mailbox tile is drawn by the flight itself.
        self.step = "friend"
        self.toolbar_focus = False
        self._show_composer(focus="step.friend", keep_focus=False)
        self.controls.mailbox.visible = False
        self._dirty = True

    def _landed(self) -> None:
        if self.state is not Screen.SENDING:
            return
        self.audio.play("drop")
        self.host.correct()

    def _show_delivered(self) -> None:
        card = self.delivered
        if card is None or self.state is Screen.DELIVERED:
            return
        self.timeline.clear()
        self.state = Screen.DELIVERED
        self.motion.send_frames = ()
        self.friend_actor = CastActor(
            card.recipient_id, self.art, self.clock, height=self.delivered_layout.friend_height, hold_seconds=2.6,
        )
        self.controls.mailbox.visible = True
        self.friend_actor.correct()
        self.timeline.after(0.25, lambda: self.audio.friend_reacts(card.recipient_id))
        mid = self.delivered_layout.friend_midbottom
        height = self.delivered_layout.friend_height
        for delay, offset in ((0.0, (-110, -height + 40)), (0.35, (120, -height + 90)), (0.7, (-40, -height - 10))):
            self.timeline.after(delay, lambda o=offset: self._burst("heart_pop", (mid[0] + o[0], mid[1] + o[1])))
        self.controls.show_delivered(self.delivered_layout, mailbox_icon=self._mailbox_icon(70))
        self._dirty = True

    def _on_new_card(self) -> None:
        self._activated = True
        if self.state is Screen.DELIVERED:
            self.delivered = None
            self._enter_composer("friend")
            return
        start = "friend" if self.draft.recipient_id is None else ("picture" if self.draft.front is None else "stickers")
        self._enter_composer(start)

    # -- postbox ---------------------------------------------------------------------------

    def open_postbox(self, focus_card: str | None = None) -> None:
        self._activated = True
        self._close_sheet()
        self._persist_draft()
        focus_card = focus_card or (self.delivered.card_id if self.state is Screen.DELIVERED and self.delivered else None)
        self.timeline.clear()
        self.state = Screen.POSTBOX
        self.friend_actor = None
        self.drag = None
        self._set_text_input(False)
        self.toolbar_focus = False
        self.motion.bursts.clear()
        focus_slot = None
        if focus_card is not None:
            index = self.library.index_of(focus_card)
            if index is not None:
                self.postbox_page = index // POSTBOX_PAGE_SIZE
                focus_slot = index % POSTBOX_PAGE_SIZE
        self.postbox_page = max(0, min(self.postbox_page, self._page_count() - 1))
        self._show_postbox(focus_slot)
        self.audio.play("tick")
        self._dirty = True

    def _page_count(self) -> int:
        return max(1, -(-self.library.count // POSTBOX_PAGE_SIZE))

    def _page_cards(self) -> list[SavedPostcard]:
        first = self.postbox_page * POSTBOX_PAGE_SIZE
        return list(self.library.cards[first : first + POSTBOX_PAGE_SIZE])

    def _show_postbox(self, focus_slot: int | None = None) -> None:
        layout = self.postbox_layout
        cards = self._page_cards()
        self.controls.show_postbox(
            layout,
            layout.cards[: len(cards)],
            on_card=self._on_postbox_card,
            on_card_delete=self._on_postbox_delete,
            page=self.postbox_page,
            page_count=self._page_count(),
            used=self.library.count,
            capacity=MAX_SAVED_CARDS,
            mailbox_icon=self._mailbox_icon(44),
            focus_card=focus_slot,
        )

    def _postbox_card(self, slot: int) -> SavedPostcard | None:
        cards = self._page_cards()
        return cards[slot] if 0 <= slot < len(cards) else None

    def _on_postbox_card(self, slot: int) -> None:
        card = self._postbox_card(slot)
        if card is None:
            return
        self._activated = True
        self.open_card(card.card_id)

    def _on_page(self, delta: int) -> None:
        page = max(0, min(self._page_count() - 1, self.postbox_page + delta))
        if page == self.postbox_page:
            return
        self._activated = True
        self.postbox_page = page
        self._show_postbox(0 if self.controls.layer.focus_visible else None)
        self.audio.play("tick")
        self._dirty = True

    def _on_delete_focused(self) -> None:
        slot = self.controls.focused_card_slot()
        if slot is None:
            slot = 0 if self._page_cards() else None
        if slot is not None:
            self._on_postbox_delete(slot)

    def _on_postbox_delete(self, slot: int) -> None:
        card = self._postbox_card(slot)
        if card is not None:
            self._ask_delete(card)

    # -- one card -----------------------------------------------------------------------------

    def open_card(self, card_id: str) -> None:
        card = self.library.get(card_id)
        if card is None:
            return
        self.timeline.clear()
        self.state = Screen.CARD
        self.open_card_id = card_id
        self.card_back = False
        self.motion.flip_frames = ()
        self.motion.bursts.clear()
        self.friend_actor = CastActor(card.recipient_id, self.art, self.clock, height=self.card_layout.friend_height)
        self.controls.show_card(self.card_layout, shared_available=self.creations is not None, focus="flip")
        self.audio.play("tick")
        self._dirty = True

    def _open_card(self) -> SavedPostcard | None:
        return self.library.get(self.open_card_id) if self.open_card_id else None

    def _on_back(self) -> None:
        self._activated = True
        self.open_postbox(self.open_card_id)

    def _on_flip(self) -> None:
        card = self._open_card()
        if card is None:
            return
        self._activated = True
        size = self.card_layout.card.size
        face = self._saved_face(card, size)
        back = self._back(card.recipient_id, card.stamp_id, size)
        start, end = (back, face) if self.card_back else (face, back)
        self.motion.flip_frames = self.renderer.flip_frames(start, end)
        self.motion.flip_start = self.clock()
        self.card_back = not self.card_back
        self.audio.play("flip")
        self._dirty = True

    def _on_share(self) -> None:
        card = self._open_card()
        if card is None:
            return
        self._activated = True
        self._publish_saved_postcard(card)
        actor = self.friend_actor
        if self.shared_state == "saved":
            if actor is not None:
                actor.correct()
            self._burst("sparkle", self.card_layout.share.center)
        elif self.shared_state == "error" and actor is not None:
            actor.try_again()
        self._dirty = True

    def _on_delete_open(self) -> None:
        card = self._open_card()
        if card is not None:
            self._activated = True
            self._ask_delete(card)

    # -- sheets --------------------------------------------------------------------------------

    def _ask_delete(self, card: SavedPostcard) -> None:
        if self.sheet is not None:
            return
        self._activated = True
        self.delete_target = card.card_id
        layout = self.sheets.layout
        preview = self._saved_face(card, layout.preview.size)
        trash = self.kit.glyph("trash", 56)

        def backdrop(surface: pygame.Surface) -> None:
            self.renderer.draw_sheet(surface, layout, preview, symbol=trash)

        self.sheet = self.sheets.delete(draw_backdrop=backdrop, on_keep=self._keep_card, on_delete=self._confirm_delete)
        self._surfaces.push_overlay(self.sheet)
        self._dirty = True

    def _keep_card(self) -> None:
        self._activated = True
        self.delete_target = None
        self._close_sheet()
        self._dirty = True

    def _confirm_delete(self) -> None:
        card_id = self.delete_target
        self._activated = True
        self.delete_target = None
        self._close_sheet()
        if card_id is None:
            return
        before = self.library.cards
        if not self.library.delete(card_id):
            return
        if not self.storage.save(self.library):
            # Commit deletion before presenting it as successful.
            self.library = PostcardLibrary(before)
            self.host.try_again()
            self._dirty = True
            return
        self._shared_card_ids.discard(card_id)
        self.audio.play("swish")
        self.open_card_id = None
        self.state = Screen.POSTBOX
        self.friend_actor = None
        self.postbox_page = max(0, min(self.postbox_page, self._page_count() - 1))
        self._show_postbox(0 if self._page_cards() else None)
        self._dirty = True

    def _open_full_sheet(self) -> None:
        layout = self.sheets.layout
        preview = self._draft_face(layout.preview.size)
        meter = self.art.meter((200, 40), MAX_SAVED_CARDS, MAX_SAVED_CARDS)

        def backdrop(surface: pygame.Surface) -> None:
            self.renderer.draw_sheet(surface, layout, preview, symbol=meter)

        self.host.try_again()
        self.sheet = self.sheets.full(
            mailbox_icon=self._mailbox_icon(76),
            draw_backdrop=backdrop,
            on_postbox=self._full_to_postbox,
            on_keep=self._keep_card,
        )
        self._surfaces.push_overlay(self.sheet)
        self._dirty = True

    def _full_to_postbox(self) -> None:
        self._activated = True
        self._close_sheet()
        self.open_postbox()

    def _close_sheet(self) -> None:
        if self.sheet is not None and self._surfaces.overlays and self._surfaces.overlays[-1] is self.sheet:
            self._surfaces.pop_overlay()
        self.sheet = None

    # -- hints -----------------------------------------------------------------------------------

    def _maybe_hint(self, now: float) -> None:
        if self.timeline.busy or self.drag is not None or self.shared_request is not None:
            return
        if self.step == "message" and self.draft.text:
            return  # writing is unhurried
        step = self._hints.poll(now, self._last_activity)
        if not step:
            return
        halo = self._hints.animation_seconds(HALO_SECONDS)
        until = now + halo
        missing = self._missing_step()
        self.host.point(halo)
        if missing is None:
            self.motion.halos["send"] = until
        elif missing != self.step:
            self.motion.halos[f"step.{missing}"] = until
        else:
            self.motion.halos["tray"] = until
        self._dirty = True

    # -- My Creations: pictures, text, sharing --------------------------------------------------

    def _step_shared(self, now: float) -> bool:
        changed = False
        if self.shared_request is not None and now >= self.shared_next_poll:
            if self.shared_kind == "picture":
                changed = self._poll_shared_picture(now) or changed
            else:
                changed = self._poll_shared_text(now) or changed
        if self.shared_state and self.shared_state != "pending" and now >= self.shared_feedback_until:
            self.shared_state = ""
            changed = True
        return changed

    def _start_request(self, kind: str, media_types: tuple[str, ...], roles: tuple[str, ...]) -> None:
        if self.creations is None or self.shared_request is not None:
            return
        self._activated = True
        try:
            request_id = self.creations.request_selection(media_types=media_types, roles=roles)
        except (RuntimeError, ValueError, OSError):
            self.shared_state = "error"
            self.shared_feedback_until = self.clock() + FEEDBACK_SECONDS
            self.host.try_again()
            return
        self.shared_request = request_id
        self.shared_kind = kind
        self.shared_state = "pending"
        self.shared_next_poll = self.clock() + PICKER_POLL_SECONDS
        if self.state is Screen.COMPOSER:
            self._show_composer(keep_focus=True)

    def _request_shared_text(self) -> None:
        self._start_request("text", ("text/plain",), MESSAGE_TEXT_ROLES)

    def _request_shared_picture(self) -> None:
        self._start_request("picture", ("image/png",), FRONT_PICTURE_ROLES)

    def _poll_result(self, now: float):
        """Poll the open picker; returns (finished, token or None)."""

        request_id = self.shared_request
        if request_id is None or self.creations is None:
            return True, None
        self.shared_next_poll = now + PICKER_POLL_SECONDS
        try:
            result = self.creations.poll_selection(request_id)
        except (RuntimeError, ValueError, OSError):
            self.shared_request = None
            self.shared_state = "error"
            self.shared_feedback_until = now + FEEDBACK_SECONDS
            return True, None
        state = getattr(result, "state", None)
        if state == "pending":
            return False, None
        self.shared_request = None
        if state == "cancelled":
            self.shared_state = ""
            return True, None
        token = getattr(result, "selection_token", None)
        if state != "ready" or not isinstance(token, str) or not token:
            self.shared_state = "error"
            self.shared_feedback_until = now + FEEDBACK_SECONDS
            return True, None
        return True, token

    def _poll_shared_text(self, now: float) -> bool:
        finished, token = self._poll_result(now)
        if not finished:
            return False
        if token is not None:
            if self._accept_shared_text(token):
                self.shared_state = "imported"
                self.audio.play("chime")
                self.host.correct()
                self._typed()
            else:
                self.shared_state = "error"
                self.host.try_again()
            self.shared_feedback_until = now + FEEDBACK_SECONDS
        self._after_request()
        return True

    def _poll_shared_picture(self, now: float) -> bool:
        finished, token = self._poll_result(now)
        if not finished:
            return False
        if token is not None:
            if self._accept_shared_picture(token):
                self.shared_state = "imported"
                self.audio.play("chime")
                self.host.correct()
                self._draft_touched()
                if self.state is Screen.COMPOSER and self.step == "picture" and not self.draft.stickers:
                    self._advance("stickers")
            else:
                self.shared_state = "error"
                self.host.try_again()
            self.shared_feedback_until = now + FEEDBACK_SECONDS
        self._after_request()
        return True

    def _after_request(self) -> None:
        if self.state is Screen.COMPOSER:
            self._show_composer(keep_focus=True)
        self._dirty = True

    def _accept_shared_text(self, selection_token: str) -> bool:
        """Bring a Writing page (or a postcard message) into the message."""

        if self.creations is None:
            return False
        try:
            transfer = self.creations.import_selected(selection_token)
            payload = transfer.payload
            if (
                transfer.record.get("media_type") != "text/plain"
                or transfer.record.get("role") not in set(MESSAGE_TEXT_ROLES)
                or not isinstance(payload, bytes)
                or transfer.record.get("sha256") != hashlib.sha256(payload).hexdigest()
            ):
                raise ValueError("selected text failed integrity validation")
            text = payload.decode("utf-8", errors="strict")
            self.draft.replace_text(text)
        except (RuntimeError, ValueError, OSError, UnicodeError):
            return False
        self._caret_on = True
        self._caret_flip = self.clock()
        return True

    def _accept_shared_picture(self, selection_token: str) -> bool:
        """Use a Shell-confirmed PNG as the card front (an independent copy)."""

        if self.creations is None:
            return False
        try:
            transfer = self.creations.import_selected(selection_token)
            payload = transfer.payload
            if (
                transfer.record.get("media_type") != "image/png"
                or transfer.record.get("role") not in set(FRONT_PICTURE_ROLES)
                or not isinstance(payload, bytes)
                or transfer.record.get("sha256") != hashlib.sha256(payload).hexdigest()
            ):
                raise ValueError("selected picture failed integrity validation")
            # Decode before touching the draft: a corrupt picture never
            # replaces the current front.
            surface = decode_png_surface(payload, CARD_PICTURE_SIZE, background=PAPER)
            stored = encode_surface_png(surface)
        except (RuntimeError, ValueError, OSError, PygamePngError):
            return False
        self._set_draft_picture(stored, surface)
        self.draft.set_front(CardFront.picture())
        return True

    def _set_draft_picture(self, png: bytes | None, surface: pygame.Surface | None = None) -> bool:
        if png is None:
            self.draft_picture_png = None
            self.draft_picture = None
            self._picture_token += 1
            return True
        if surface is None:
            try:
                surface = decode_png_surface(png, CARD_PICTURE_SIZE, background=PAPER)
            except PygamePngError:
                return False
        self.draft_picture_png = png
        self.draft_picture = surface
        self._picture_token += 1
        return True

    def _publish_saved_postcard(self, card: SavedPostcard) -> None:
        """Explicit copy into My Creations: the picture, plus the message text."""

        if self.creations is None:
            return
        self.shared_feedback_until = self.clock() + FEEDBACK_SECONDS
        if card.card_id in self._shared_card_ids:
            self.shared_state = "saved"
            return
        try:
            picture = encode_surface_png(self._flat_face(card))
            name = self.storage.private_card_png_name(card.card_id, picture)
            self.creations.publish_private_file(name, media_type="image/png", role=SHARE_ROLE)
            if card.text.strip():
                text_name = self.storage.private_card_text_name(card.card_id)
                self.creations.publish_private_file(
                    text_name, media_type="text/plain", role=SHARE_ROLE, title=card.text[:100],
                )
        except (RuntimeError, ValueError, OSError, UnicodeError, PygamePngError):
            self.shared_state = "error"
            return
        self._shared_card_ids.add(card.card_id)
        self.shared_state = "saved"
        self.audio.play("chime")

    # -- prepared surfaces -------------------------------------------------------------------------

    def _mailbox_icon(self, size: int) -> pygame.Surface | None:
        return self.kit.glyph("mailbox", size)

    def _draft_face(self, size: tuple[int, int], *, skip: int | None = None) -> pygame.Surface:
        draft = self.draft
        key = ("draft", draft.front, draft.stickers, self._picture_token)
        return self.art.card(key, draft.front, self.draft_picture, draft.stickers, size, skip=skip)

    def _card_picture(self, card: SavedPostcard) -> pygame.Surface | None:
        if not card.front.is_picture:
            return None
        if card.card_id in self._pictures:
            return self._pictures[card.card_id]
        try:
            surface: pygame.Surface | None = decode_png_surface(
                self.storage.load_picture(card.card_id), CARD_PICTURE_SIZE, background=PAPER,
            )
        except (RuntimeError, ValueError, OSError, PygamePngError):
            surface = None
        self._pictures[card.card_id] = surface
        return surface

    def _saved_face(self, card: SavedPostcard, size: tuple[int, int]) -> pygame.Surface:
        return self.art.card(("saved", card.card_id), card.front, self._card_picture(card), card.stickers, size)

    def _flat_face(self, card: SavedPostcard) -> pygame.Surface:
        """The card front as a plain rectangular picture (for My Creations)."""

        size = CARD_PICTURE_SIZE
        face = self.art.card(("flat", card.card_id), card.front, self._card_picture(card), card.stickers, size)
        flat = pygame.Surface(size)
        flat.fill(PAPER)
        flat.blit(face, (0, 0))
        return flat

    def _back(self, recipient_id: str | None, stamp_id: str, size: tuple[int, int]) -> pygame.Surface:
        label = None
        name = ""
        if recipient_id is not None:
            name = self._text(friend_info(recipient_id).name_key)
            if name:
                label = self.kit.painter.label(name, max(14, size[1] // 11), INK, max_width=round(size[0] * 0.34))
        return self.art.back(recipient_id, stamp_id, label, name, size)

    def _burst(self, name: str, centre: tuple[int, int]) -> None:
        frames = self.art.fx_frames(name)
        if frames:
            self.motion.add_burst(FxBurst(frames, centre, clock=self.clock))
            self._dirty = True

    # -- draft persistence ---------------------------------------------------------------------------

    def _persist_draft(self, *, force: bool = False) -> None:
        if not force and self.draft.revision == self._draft_saved_revision:
            return
        picture = self.draft_picture_png if (self.draft.front is not None and self.draft.front.is_picture) else None
        try:
            self.storage.save_draft(self.draft, picture)
        except Exception:
            return
        self._draft_saved_revision = self.draft.revision


def _safe_point(surface: pygame.Surface, position: tuple[int, int]) -> bool:
    viewport = activity_viewport_for_surface(surface)
    x, y = position
    if not (0 <= x < viewport.surface.width and 0 <= y < viewport.surface.height):
        return False
    for protected in viewport.protected_regions:
        if protected.x <= x < protected.right and protected.y <= y < protected.bottom:
            return False
    return True


__all__ = ["PostcardActivity", "Screen", "StickerDrag", "Timeline"]
