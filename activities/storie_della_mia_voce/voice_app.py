"""Stories of My Voice — Story Cards lifecycle, timing and shared-kit input.

One visit: the child picks a short picture story on Leo's story shelf
(three-card stories first, then four), puts its shuffled cards in order on the
numbered places (tap a card to send it to the next place, or drag it; tap a
placed card to take it back), tells each card with their own voice (a 3-pip
ready beat, then up to 30 s per card; play / redo; skip is allowed) and
watches the story back as a slideshow with their voice. The story is saved
on the My-stories shelf (12 stories, never evicted) and can be shared, card by
card, to My Creations as ``narration`` WAVs for Theatre and Orchestra.

Feedback follows ADR 0037: right order = Leo ``pose_cheer`` + sparkles +
chime; a wrong row = Leo ``pose_think``, the misplaced cards wiggle and go
home while the right ones stay, then Leo points at the place to fill and the
card that belongs there (unlimited, never a penalty). Idle ~6 s -> Leo points
and the next place glows; idle again -> the right card glows too. A finished
story ends on the shared cast completion scene. Without a microphone the
child still orders the pictures and watches them; a "no mic" pictogram
explains why there is no telling step.
"""

from __future__ import annotations

from collections import deque
from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum
import random
import time

import pygame

from greia_platform.activity_api import activity_stop_requested, mark_activity_ready
from greia_platform.frame_governor import FrameGovernor, FrameKind
from greia_platform.activity_controls import (
    ControlKit,
    ControlLayout,
    ControlTheme,
    KitPointer,
    PointerPhase,
    PygameControlInput,
)
from greia_platform.activity_feedback import CastFeedback, IdleHintScheduler
from greia_platform.localization import LocalizedResources
from greia_platform.pygame_canvas import PygameReferenceCanvas, activity_viewport_for_surface
from greia_platform.pygame_completion import (
    CompletionContent,
    CompletionOverlay,
    CompletionPalette,
    CompletionScene,
    PygameCompletionScreen,
)
from greia_platform.typography import GreiaTypography
from greia_platform.ui_core import SurfaceNavigator, UiEventResult

if __package__:
    from .voice_art import StoryArt
    from .voice_audio import StoryAudio
    from .voice_content import (
        COUNTDOWN_SECONDS,
        HOST,
        MAX_RECORDING_SECONDS,
        MAX_SAVED_STORIES,
        MIN_RECORDING_SECONDS,
        REFERENCE_HEIGHT,
        REFERENCE_WIDTH,
        SHELF_PAGE_SIZE,
        STORIES,
        StoryTemplate,
        story_by_id,
    )
    from .voice_controls import StoryControls, StorySheet, StorySheets, shelf_card_id
    from .voice_layout import HOST_HEIGHT, OrderLayout, PickerLayout, ShelfLayout, TellLayout, WatchLayout
    from .voice_microphone import VoiceRecorder
    from .voice_model import OrderingBoard, RecordState, Slideshow, TellingSession
    from .voice_renderer import DragState, Flight, HostCast, Motion, RecordingView, StoryRenderer, card_art
    from .voice_services import DeleteConfirmation, SavedStory, StoryProgress, VoiceEvents, VoiceStorage, VoiceStorageError
else:
    from voice_art import StoryArt
    from voice_audio import StoryAudio
    from voice_content import (
        COUNTDOWN_SECONDS,
        HOST,
        MAX_RECORDING_SECONDS,
        MAX_SAVED_STORIES,
        MIN_RECORDING_SECONDS,
        REFERENCE_HEIGHT,
        REFERENCE_WIDTH,
        SHELF_PAGE_SIZE,
        STORIES,
        StoryTemplate,
        story_by_id,
    )
    from voice_controls import StoryControls, StorySheet, StorySheets, shelf_card_id
    from voice_layout import HOST_HEIGHT, OrderLayout, PickerLayout, ShelfLayout, TellLayout, WatchLayout
    from voice_microphone import VoiceRecorder
    from voice_model import OrderingBoard, RecordState, Slideshow, TellingSession
    from voice_renderer import DragState, Flight, HostCast, Motion, RecordingView, StoryRenderer, card_art
    from voice_services import DeleteConfirmation, SavedStory, StoryProgress, VoiceEvents, VoiceStorage, VoiceStorageError

DRAG_SLOP = 12
CHECK_DELAY = 0.4
WOBBLE_LOOK = 0.55
CELEBRATE_HOLD = 2.3
HALO_SECONDS = 1.8
SHARE_FEEDBACK_SECONDS = 1.2
MAX_SCHEDULED = 64
NAVY = (37, 59, 89)


class Screen(StrEnum):
    PICKER = "picker"
    ORDER = "order"
    TELL = "tell"
    WATCH = "watch"
    SHELF = "shelf"
    DONE = "done"


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
class StoryDraft:
    """A told story that has not reached the shelf yet (e.g. shelf full)."""

    template_id: str
    order: tuple[str, ...]
    recordings: dict[str, bytes]
    durations: dict[str, float]


@dataclass(slots=True)
class WatchState:
    template_id: str
    order: tuple[str, ...]
    recordings: dict[str, bytes]
    slideshow: Slideshow
    story: SavedStory | None
    from_shelf: bool
    voice_ok: bool = False


class StoryApp:
    """Coordinate the story picker, ordering, telling, watching and the shelf."""

    def __init__(
        self,
        *,
        screen: pygame.Surface,
        canvas: PygameReferenceCanvas,
        typography: GreiaTypography,
        resources: LocalizedResources | None,
        audio: StoryAudio,
        recorder: VoiceRecorder,
        storage: VoiceStorage,
        progress: StoryProgress,
        events: VoiceEvents | None = None,
        creations: object | None = None,
        mic_available: bool | None = None,
        rng: random.Random | None = None,
        clock: Callable[[], float] = time.monotonic,
        kit: ControlKit | None = None,
        art: StoryArt | None = None,
    ) -> None:
        self.screen = screen
        self.canvas = canvas
        self.typography = typography
        self.resources = resources
        self.audio = audio
        self.recorder = recorder
        self.storage = storage
        self.progress = progress
        self.events = events if events is not None else VoiceEvents()
        self.creations = creations
        self.rng = rng if rng is not None else random.Random()
        self.clock = clock
        self.mic_ok = recorder.available if mic_available is None else bool(mic_available)

        # Shared control kit (ADR 0037): create Collection -> coral accent.
        self.kit = kit if kit is not None else ControlKit(typography, ControlTheme.for_accent("coral"))
        self.art = art if art is not None else StoryArt(self.kit.painter)
        feedback = CastFeedback(HOST, height=HOST_HEIGHT, art=self.art.loader, clock=clock)
        self.cast = HostCast(feedback, self.art, clock)
        self.renderer = StoryRenderer(self.art, self.cast, clock)
        self.motion = Motion()
        self.timeline = Timeline(clock)
        self.controls = StoryControls(
            self.kit,
            on_picker=self._on_picker_button,
            on_shelf=self.open_shelf,
            on_hint=self._on_hint,
            on_mic=self._on_mic,
            on_play=self._on_play,
            on_redo=self._on_redo,
            on_previous=self._on_previous,
            on_next=self._on_next,
            on_replay=self._on_replay,
            on_share=self._on_share,
            on_page=self._on_page,
            on_delete_focused=self._on_delete_focused,
            on_save_pending=self._on_save_pending,
        )
        self.sheets = StorySheets(self.kit)
        self._surfaces = SurfaceNavigator(self.controls.layer)
        self._input = PygameControlInput(to_logical=canvas.pointer, is_safe=lambda pos: _safe_point(self.screen, pos))
        self._layout_source = ControlLayout.for_canvas(canvas, screen.get_size())
        self.completion = PygameCompletionScreen(
            typography,
            width=REFERENCE_WIDTH,
            height=REFERENCE_HEIGHT,
            palette=CompletionPalette(background=NAVY),
            scene=CompletionScene(self.kit, character=HOST, star_total=4, primary_glyph="new", secondary_glyph="play"),
        )
        self.state = Screen.PICKER
        self.template: StoryTemplate | None = None
        self.board: OrderingBoard | None = None
        self.telling: TellingSession | None = None
        self.watch: WatchState | None = None
        self.pending: StoryDraft | None = None
        self.delete_confirm: DeleteConfirmation | None = None
        self.sheet: StorySheet | None = None
        self.drag: DragState | None = None
        self.record_state = RecordState.IDLE
        self.shelf_page = 0
        self._order_layout: OrderLayout | None = None
        self._tell_layout: TellLayout | None = None
        self._watch_layout: WatchLayout | None = None
        self._shelf_layout: ShelfLayout | None = None
        self._picker_layout: PickerLayout | None = None
        self._countdown_started = 0.0
        self._record_started = 0.0
        self._pips = 0
        self._running = True
        self.ready_published = False
        self._dirty = True
        self._activated = False
        self._busy = False
        self._last_activity = clock()
        self._hints = IdleHintScheduler(now=self._last_activity)
        self._greeted = False
        self.open_picker()

    # -- main loop --------------------------------------------------------------

    def run(self) -> int:
        frames = FrameGovernor()
        try:
            while self._running and not activity_stop_requested():
                for event in frames.events():
                    self.handle_event(event)
                repeat = self._input.poll()
                if repeat is not None:
                    self._dispatch(repeat)
                animating = self.step()
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
        """Close the microphone and keep any told cards (Home mid-story)."""

        if self.record_state is RecordState.RECORDING:
            self._stop_recording()
        self.recorder.stop()
        self.audio.stop_all()
        if self.state is Screen.TELL and self.telling is not None and self.telling.recordings:
            self._commit_telling()
        self.typography.clear()

    def step(self) -> bool:
        """Advance timers; return True while something on screen is moving."""

        now = self.clock()
        if self.timeline.run_due():
            self._dirty = True
        if self.cast.update():
            self._dirty = True
        self.motion.prune(now)
        if self.state is Screen.TELL:
            self._step_recording(now)
        elif self.state is Screen.WATCH:
            self._step_watch(now)
        if self.sheet is None and self.state in {Screen.ORDER, Screen.TELL}:
            self._maybe_hint(now)
        if self.controls.layer.invalidation.should_draw or (self.sheet is not None and self.sheet.layer.invalidation.should_draw):
            self._dirty = True
        recording = self.record_state is not RecordState.IDLE
        showing = self.state is Screen.WATCH and self.watch is not None and not self.watch.slideshow.finished
        voice = self.state is Screen.TELL and self.audio.voice_busy()
        return self.motion.active(now) or self.cast.animating or recording or self.drag is not None or showing or voice

    def render(self) -> None:
        surface = self.canvas.surface
        state = self.state
        if state is Screen.PICKER and self._picker_layout is not None:
            self.renderer.draw_picker(surface, self._picker_layout, mic_ok=self.mic_ok)
        elif state is Screen.ORDER and self.template and self.board and self._order_layout:
            self.renderer.draw_order(surface, self.template, self.board, self._order_layout, self.motion, self.drag)
        elif state is Screen.TELL and self.template and self.telling and self._tell_layout:
            self.renderer.draw_tell(
                surface,
                self.template,
                self.telling.card,
                self.telling.index + 1,
                self._tell_layout,
                self._recording_view(),
                has_voice=self.telling.has(),
                motion=self.motion,
                invite=self.record_state is RecordState.IDLE and not self.telling.has() and not self._busy,
            )
        elif state in {Screen.WATCH, Screen.DONE} and self.watch is not None and self._watch_layout is not None:
            slide = self.watch.slideshow.current
            self.renderer.draw_watch(
                surface,
                card_art(self.watch.template_id, slide.card_id),
                f"{self.watch.template_id}.{slide.card_id}",
                self.watch.slideshow.index + 1,
                self._watch_layout,
                self.motion,
                voiced=slide.voiced,
                playing=self.audio.voice_busy(),
                mic_ok=self.mic_ok,
            )
        elif state is Screen.SHELF and self._shelf_layout is not None:
            stories, cards = self._shelf_page()
            self.renderer.draw_shelf(surface, self._shelf_layout, stories, cards, used=len(self.storage.stories), motion=self.motion)
        self._surfaces.draw(surface)

    # -- input --------------------------------------------------------------------

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.QUIT:
            self._running = False
            return
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE and self.sheet is None:
            self._running = False
            return
        if event.type == pygame.VIDEORESIZE:
            self._resize()
            return
        translated = self._input.translate(event)
        if translated is not None:
            self._dispatch(translated)

    def _resize(self) -> None:
        self.screen = pygame.display.get_surface() or self.screen
        self.canvas = PygameReferenceCanvas(self.screen)
        self._input = PygameControlInput(to_logical=self.canvas.pointer, is_safe=lambda pos: _safe_point(self.screen, pos))
        self._layout_source = ControlLayout.for_canvas(self.canvas, self.screen.get_size())
        self._reshow()
        self._dirty = True

    def _dispatch(self, kit_input) -> bool:
        if not isinstance(kit_input, KitPointer) or kit_input.phase is not PointerPhase.MOVE:
            self._note_activity()
        else:
            self._dirty = True  # keep the Greia pointer (drawn on present) live
        if (
            isinstance(kit_input, KitPointer)
            and self.state is Screen.ORDER
            and self.sheet is None
            and not self._surfaces.overlays
            and self._drag_input(kit_input)
        ):
            self._dirty = True
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

    def drag_to(self, start: tuple[int, int], end: tuple[int, int]) -> bool:
        """Deliver one pointer drag (tests/tools)."""

        self._activated = False
        self._dispatch(KitPointer(PointerPhase.DOWN, start))
        mid = ((start[0] + end[0]) // 2, (start[1] + end[1]) // 2)
        self._dispatch(KitPointer(PointerPhase.MOVE, mid))
        self._dispatch(KitPointer(PointerPhase.MOVE, end))
        self._dispatch(KitPointer(PointerPhase.UP, end))
        return self._activated

    def press(self, key: int) -> bool:
        """Deliver one key press through the shared navigation mapping."""

        self._activated = False
        translated = self._input.translate(pygame.event.Event(pygame.KEYDOWN, key=key, mod=0, unicode=""))
        if translated is not None:
            self._dispatch(translated)
        return self._activated

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

    # -- picker -------------------------------------------------------------------

    def open_picker(self) -> None:
        self._activated = True
        self._leave_overlays()
        self._reset_scene()
        self.state = Screen.PICKER
        self.template = None
        self.board = None
        self.telling = None
        self.watch = None
        self.cast.waving = True
        self._show_picker()
        if not self._greeted:
            self._greeted = True
            self.audio.host("ready.go")
        self._dirty = True

    def _show_picker(self) -> None:
        button = self._layout_source.control_height(64, maximum=80)
        layout = PickerLayout.build(self._layout_source.protected, button=button)
        self._picker_layout = layout
        tile = layout.tiles[0]
        icon_size = (tile.width - 24, tile.height - 30)
        covers = [
            self.art.cover(
                story, icon_size, done=story.story_id in self.progress.done, star=self.kit.star, title=self._text(story.title_key)
            )
            for story in STORIES
        ]
        shelf_icon = self.art.shelf_cover(
            icon_size, len(self.storage.stories), MAX_SAVED_STORIES, title=self._text("ui.my_stories")
        )
        self.controls.show_picker(layout, covers, shelf_icon, self._on_story, focus=self._suggested_story())

    def _suggested_story(self) -> int:
        for index, story in enumerate(STORIES):
            if story.story_id not in self.progress.done:
                return index
        return 0

    def _on_story(self, index: int) -> None:
        if self.state is not Screen.PICKER or not 0 <= index < len(STORIES):
            return
        self._activated = True
        self.start_story(STORIES[index])

    def _on_picker_button(self) -> None:
        self._activated = True
        if self.state is Screen.WATCH and self.watch is not None and self.watch.from_shelf:
            self.open_shelf()
            return
        if self.state is Screen.TELL and self.telling is not None and self.telling.recordings:
            # Leaving mid-telling keeps what was told (never a silent loss).
            self._commit_telling()
        self.open_picker()

    # -- order --------------------------------------------------------------------

    def start_story(self, template: StoryTemplate) -> None:
        self._reset_scene()
        self.template = template
        self.board = OrderingBoard.shuffled(template.card_ids, self.rng)
        self.state = Screen.ORDER
        self.cast.waving = False
        self._show_order()
        now = self.clock()
        self.motion.halos["slot.0"] = now + HALO_SECONDS
        self._show_guide(now)
        self.audio.play("whoosh")
        self.audio.host("ready.go")
        self.cast.point(1.6)
        self._note_activity()
        self._dirty = True

    def _show_order(self) -> None:
        assert self.template is not None and self.board is not None
        button = self._layout_source.control_height(64, maximum=80)
        self._order_layout = OrderLayout.build(self.board.size, self._layout_source.protected, button=button)
        tray_cards = [card for card in self.board.tray if card is not None] + [
            card for card in self.board.slots if card is not None
        ]
        home_order = sorted(tray_cards, key=self.board.tray_index)
        self.controls.show_order(
            self._order_layout,
            home_order,
            on_tray=self._on_tray,
            on_slot=self._on_slot,
            picker_icon=self._picker_icon(),
        )
        self._sync_order()

    def _sync_order(self) -> None:
        if self.board is None or self._order_layout is None:
            return
        self.controls.sync_order(
            tray=self.board.tray, slots=self.board.slots, locked=self.board.locked, busy=self._busy, layout=self._order_layout
        )

    def _tray_rect(self, card: str):
        assert self.board is not None and self._order_layout is not None
        return self._order_layout.tray[self.board.tray_index(card)]

    def _on_tray(self, card: str) -> None:
        board = self.board
        if board is None or self._busy or not board.in_tray(card):
            return
        self._activated = True
        start = self._tray_rect(card)
        slot = board.place(card)
        if slot is None:
            return
        self._moved(card, start, self._order_layout.slots[slot], "pop")

    def _on_slot(self, index: int) -> None:
        board = self.board
        if board is None or self._busy:
            return
        self._activated = True
        if board.slots[index] is None:
            self.motion.halos[f"slot.{index}"] = self.clock() + 0.9
            self._dirty = True
            return
        card = board.take_back(index)
        if card is None:
            return
        self._moved(card, self._order_layout.slots[index], self._tray_rect(card), "unpop")

    def _moved(self, card: str, start, end, sound: str) -> None:
        now = self.clock()
        self.motion.fly(Flight(card, start.copy(), end.copy(), now))
        self.motion.halos.pop(f"card.{card}", None)
        self.audio.play(sound)
        self._after_move()

    def _after_move(self) -> None:
        board = self.board
        assert board is not None
        if board.full:
            self._busy = True
            self.timeline.after(CHECK_DELAY, self._check)
        self._sync_order()
        self._dirty = True

    # drag ------------------------------------------------------------------------

    def _drag_input(self, event: KitPointer) -> bool:
        """Pointer drags of cards; returns True when the event was consumed."""

        board = self.board
        layout = self._order_layout
        if board is None or layout is None:
            return False
        if event.phase is PointerPhase.DOWN:
            if self._busy:
                return False
            hit = self._card_at(event.position)
            if hit is None:
                return False
            card, origin = hit
            self.drag = DragState(card, origin.copy(), event.position, (event.position[0] - origin.x, event.position[1] - origin.y))
            return True
        drag = self.drag
        if drag is None:
            return False
        if event.phase is PointerPhase.MOVE:
            dx = event.position[0] - drag.origin.x - drag.grab[0]
            dy = event.position[1] - drag.origin.y - drag.grab[1]
            drag.position = event.position
            drag.moved = drag.moved or dx * dx + dy * dy > DRAG_SLOP * DRAG_SLOP
            return True
        self.drag = None
        if event.phase is PointerPhase.CANCEL:
            return True
        drag.position = event.position
        source_slot = board.slot_of(drag.card_id)
        if not drag.moved:
            # A tap: same as Space/Enter on the card.
            if source_slot is None:
                self._on_tray(drag.card_id)
            else:
                self._on_slot(source_slot)
            return True
        self._activated = True
        dropped = drag.rect
        target = self._slot_at(event.position, dropped)
        if target is not None and target not in board.locked:
            if board.place(drag.card_id, target) is not None:
                self.audio.play("pop")
                # A swapped-out card simply reappears in its place.
                self.motion.fly(Flight(drag.card_id, dropped, layout.slots[target], self.clock(), 0.16))
                self._after_move()
                return True
        if source_slot is not None and target is None:
            board.take_back(source_slot)
            self.motion.fly(Flight(drag.card_id, dropped, self._tray_rect(drag.card_id), self.clock(), 0.22))
            self.audio.play("unpop")
            self._after_move()
            return True
        # Back where it came from.
        self.motion.fly(Flight(drag.card_id, dropped, drag.origin, self.clock(), 0.2))
        self._dirty = True
        return True

    def _card_at(self, point: tuple[int, int]):
        board, layout = self.board, self._order_layout
        assert board is not None and layout is not None
        for index, rect in enumerate(layout.slots):
            if rect.collidepoint(point) and board.movable(index):
                return board.slots[index], rect
        for index, rect in enumerate(layout.tray):
            card = board.tray[index]
            if card is not None and rect.collidepoint(point):
                return card, rect
        return None

    def _slot_at(self, point: tuple[int, int], dropped) -> int | None:
        layout = self._order_layout
        assert layout is not None
        for index, rect in enumerate(layout.slots):
            if rect.inflate(20, 30).collidepoint(point) or rect.collidepoint(dropped.center):
                return index
        return None

    # check -----------------------------------------------------------------------

    def _check(self) -> None:
        board = self.board
        if board is None or not board.full or self.state is not Screen.ORDER:
            self._busy = False
            return
        wrong = [index for index, card in enumerate(board.slots) if card != board.order[index]]
        if not wrong:
            result = board.check()
            assert result.correct
            self._celebrate_order()
            return
        now = self.clock()
        for index in wrong:
            card = board.slots[index]
            if card is not None:
                self.motion.wobble[card] = now
        self.cast.try_again()
        self.audio.play("boop")
        self.audio.host("encourage.retry")
        self.timeline.after(WOBBLE_LOOK, self._send_home)
        self._dirty = True

    def _send_home(self) -> None:
        board = self.board
        if board is None or self._order_layout is None:
            return
        before = list(board.slots)
        result = board.check()
        now = self.clock()
        for card in result.returned:
            index = before.index(card)
            self.motion.fly(Flight(card, self._order_layout.slots[index], self._tray_rect(card), now, 0.36))
        for index in result.locked:
            rect = self._order_layout.slots[index]
            self.motion.add_fx("check_pop", (rect.left + 8, rect.top + 8), now + 0.1)
        self.audio.play("whoosh")
        self.timeline.after(0.45, self._demonstrate)

    def _demonstrate(self) -> None:
        """After a try-again: Leo points at the place and the card for it."""

        self._busy = False
        board = self.board
        if board is None:
            return
        hint = board.hint()
        if hint is not None:
            slot, card = hint
            until = self.clock() + HALO_SECONDS
            self.motion.halos[f"slot.{slot}"] = until
            self.motion.halos[f"card.{card}"] = until
        self.cast.point(HALO_SECONDS)
        self._note_activity()
        self._sync_order()
        self._dirty = True

    def _celebrate_order(self) -> None:
        assert self.board is not None and self.template is not None and self._order_layout is not None
        now = self.clock()
        for order, rect in enumerate(self._order_layout.slots):
            self.motion.add_fx("sparkle", (rect.right - 20, rect.top + 18), now + 0.12 * order)
        self.cast.correct()
        self.audio.play("chime")
        self.audio.host("celebrate.success")
        self.events.cards_ordered(self.template.story_id, self.board.mistakes)
        self.timeline.after(CELEBRATE_HOLD, self._after_order)
        self._sync_order()
        self._dirty = True

    def _after_order(self) -> None:
        self._busy = False
        if self.mic_ok:
            self.start_telling()
        else:
            assert self.template is not None
            self._start_watch(self.template.story_id, self.template.card_ids, {}, {}, story=None, from_shelf=False)

    # -- tell ---------------------------------------------------------------------

    def start_telling(self) -> None:
        assert self.template is not None
        self._reset_scene()
        self.state = Screen.TELL
        self.telling = TellingSession(self.template.card_ids)
        self.record_state = RecordState.IDLE
        button = self._layout_source.control_height(64, maximum=80)
        self._tell_layout = TellLayout.build(len(self.template.cards), self._layout_source.protected, button=button)
        self.controls.show_tell(self._tell_layout, len(self.template.cards), picker_icon=self._picker_icon())
        self.motion.slide_started = self.clock()
        self.cast.point(1.4)
        self._note_activity()
        self._sync_tell()
        self._dirty = True

    def _sync_tell(self) -> None:
        if self.telling is None:
            return
        self.controls.sync_tell(
            index=self.telling.index,
            count=len(self.telling.order),
            recording=self.record_state is RecordState.RECORDING,
            counting=self.record_state is RecordState.COUNTDOWN,
            has_voice=self.telling.has(),
            last=self.telling.last,
            busy=self._busy,
        )

    def _recording_view(self) -> RecordingView:
        now = self.clock()
        view = RecordingView(limit=MAX_RECORDING_SECONDS)
        if self.record_state is RecordState.COUNTDOWN:
            view.counting = True
            view.countdown_progress = min(0.999, (now - self._countdown_started) / COUNTDOWN_SECONDS)
        elif self.record_state is RecordState.RECORDING:
            view.recording = True
            view.elapsed = now - self._record_started
            view.level = max(0.0, min(1.0, float(self.recorder.live_volume)))
        return view

    def _on_mic(self) -> None:
        if self.state is not Screen.TELL or self.telling is None or self._busy:
            return
        self._activated = True
        if self.record_state is RecordState.IDLE:
            self._begin_countdown()
        elif self.record_state is RecordState.COUNTDOWN:
            self.record_state = RecordState.IDLE
        else:
            self._stop_recording()
        self._sync_tell()
        self._dirty = True

    def _begin_countdown(self) -> None:
        self.audio.stop_all()
        self.record_state = RecordState.COUNTDOWN
        self._countdown_started = self.clock()
        self._pips = 1
        self.audio.play("pip")

    def _step_recording(self, now: float) -> None:
        if self.record_state is RecordState.COUNTDOWN:
            elapsed = now - self._countdown_started
            pips = min(3, int(elapsed / (COUNTDOWN_SECONDS / 3)) + 1)
            if pips > self._pips and elapsed < COUNTDOWN_SECONDS:
                self._pips = pips
                self.audio.play("pip")
            if elapsed >= COUNTDOWN_SECONDS:
                self._start_recording()
        elif self.record_state is RecordState.RECORDING:
            if now - self._record_started >= MAX_RECORDING_SECONDS:
                self._stop_recording()
                self._sync_tell()

    def _start_recording(self) -> None:
        assert self.telling is not None
        self.audio.stop_all()
        self.recorder.start()
        self.record_state = RecordState.RECORDING
        self._record_started = self.clock()
        self.events.recording_started(self.telling.card)
        self._sync_tell()
        self._dirty = True

    def _stop_recording(self) -> None:
        telling = self.telling
        if telling is None or self.record_state is not RecordState.RECORDING:
            self.record_state = RecordState.IDLE
            return
        elapsed = self.clock() - self._record_started
        self.record_state = RecordState.IDLE
        if elapsed < MIN_RECORDING_SECONDS:
            self.recorder.stop()
            self.events.recording_stopped(telling.card, 0.0)
            self.cast.try_again()
            return
        wav = self.recorder.stop(gain=1.6)
        self.events.recording_stopped(telling.card, elapsed if wav else 0.0)
        if not wav:
            self.cast.try_again()
            self.audio.play("boop")
            return
        telling.keep(wav, elapsed)
        self.audio.play("rec_off")
        self.cast.correct()
        # Children love hearing themselves: play the card back once.
        self.timeline.after(0.35, lambda card=telling.card: self._play_told(card))

    def _play_told(self, card: str) -> None:
        if self.state is not Screen.TELL or self.telling is None or self.telling.card != card:
            return
        wav = self.telling.recordings.get(card)
        if wav and self.audio.play_voice(wav):
            self._dirty = True

    def _on_play(self) -> None:
        telling = self.telling
        if telling is None or not telling.has() or self.record_state is not RecordState.IDLE:
            return
        self._activated = True
        if self.audio.play_voice(telling.recordings[telling.card]):
            self.events.recording_replayed(telling.card)
        self._dirty = True

    def _on_redo(self) -> None:
        telling = self.telling
        if telling is None or self.record_state is not RecordState.IDLE:
            return
        self._activated = True
        self.audio.stop_voice()
        telling.forget()
        self._begin_countdown()
        self._sync_tell()
        self._dirty = True

    def _on_previous(self) -> None:
        telling = self.telling
        if telling is None or self.record_state is not RecordState.IDLE:
            return
        self._activated = True
        self.audio.stop_voice()
        if telling.back():
            self.motion.slide_started = self.clock()
            self.audio.play("page")
        self._sync_tell()
        self._dirty = True

    def _on_next(self) -> None:
        telling = self.telling
        if telling is None or self.record_state is not RecordState.IDLE or self._busy:
            return
        self._activated = True
        self.audio.stop_voice()
        if telling.advance():
            self.motion.slide_started = self.clock()
            self.audio.play("page")
            self.cast.point(1.0)
            self._sync_tell()
            self._dirty = True
            return
        self._finish_telling()

    def _finish_telling(self) -> None:
        telling, template = self.telling, self.template
        assert telling is not None and template is not None
        if not telling.recordings:
            # Nothing told: just watch the pictures (nothing blank is saved).
            self._start_watch(template.story_id, telling.order, {}, {}, story=None, from_shelf=False)
            return
        draft = StoryDraft(template.story_id, telling.order, dict(telling.recordings), dict(telling.durations))
        if self.storage.is_full:
            self.pending = draft
            self._open_full_sheet()
            return
        story = self._save(draft)
        if story is None and self.storage.available:
            # The store refused the commit: keep everything and let the child retry.
            self.cast.try_again()
            self.audio.play("boop")
            self._sync_tell()
            self._dirty = True
            return
        self._start_watch(draft.template_id, draft.order, draft.recordings, draft.durations, story=story, from_shelf=False)

    def _commit_telling(self) -> SavedStory | None:
        """Keep the cards told so far as a story (leaving or Home mid-telling)."""

        telling, template = self.telling, self.template
        if telling is None or template is None or not telling.recordings:
            return None
        draft = StoryDraft(template.story_id, telling.order, dict(telling.recordings), dict(telling.durations))
        if self.storage.is_full:
            self.pending = draft  # the shelf offers to save it once there is room
            return None
        story = self._save(draft)
        if story is not None:
            telling.recordings.clear()
            telling.durations.clear()
        return story

    def _save(self, draft: StoryDraft) -> SavedStory | None:
        first = len(self.storage.stories) == 0
        try:
            story = self.storage.save_story(draft.template_id, draft.order, draft.recordings, draft.durations)
        except (VoiceStorageError, ValueError, OSError):
            return None
        if story is None:
            return None
        self.events.story_saved(story.story_id, len(story.recordings))
        if first:
            self.events.first_story_recorded(story.story_id)
        return story

    # -- watch --------------------------------------------------------------------

    def _start_watch(
        self,
        template_id: str,
        order: tuple[str, ...],
        recordings: dict[str, bytes],
        durations: dict[str, float],
        *,
        story: SavedStory | None,
        from_shelf: bool,
    ) -> None:
        self._leave_overlays()
        self._reset_scene()
        self.state = Screen.WATCH
        slideshow = Slideshow(order, durations, set(recordings))
        self.watch = WatchState(template_id, order, recordings, slideshow, story, from_shelf)
        button = self._layout_source.control_height(64, maximum=80)
        self._watch_layout = WatchLayout.build(len(order), self._layout_source.protected, button=button)
        share = story is not None and self.creations is not None
        top_icon = self._shelf_button_icon() if from_shelf else self._picker_icon()
        self.controls.show_watch(self._watch_layout, len(order), top_icon=top_icon, share=share)
        self._begin_slides()

    def _begin_slides(self) -> None:
        watch = self.watch
        assert watch is not None
        now = self.clock()
        watch.slideshow.start(now)
        self._show_slide(now)

    def _show_slide(self, now: float) -> None:
        watch = self.watch
        assert watch is not None
        slide = watch.slideshow.current
        self.motion.slide_started = now
        self.audio.play("page")
        watch.voice_ok = False
        if slide.voiced:
            wav = watch.recordings.get(slide.card_id)
            watch.voice_ok = bool(wav) and self.audio.play_voice(wav)
        self._sync_watch()
        self._dirty = True

    def _sync_watch(self) -> None:
        watch = self.watch
        if watch is None:
            return
        story = watch.story
        self.controls.sync_watch(
            index=watch.slideshow.index if not watch.slideshow.finished else len(watch.order),
            playing=not watch.slideshow.finished,
            shared=bool(story and story.shared),
            share_visible=story is not None and self.creations is not None,
        )

    def _step_watch(self, now: float) -> None:
        watch = self.watch
        if watch is None or watch.slideshow.finished:
            return
        busy = self.audio.voice_busy() if watch.voice_ok else None
        if not watch.slideshow.due(now, voice_busy=busy):
            return
        if watch.slideshow.next(now):
            self._show_slide(now)
            return
        self._sync_watch()
        self._dirty = True
        if not watch.from_shelf:
            self.timeline.after(0.6, self._complete)

    def _on_replay(self) -> None:
        if self.watch is None or not self.watch.slideshow.finished:
            return
        self._activated = True
        self._begin_slides()

    def _on_share(self) -> None:
        watch = self.watch
        if watch is None or watch.story is None or self.creations is None:
            return
        self._activated = True
        story = self.storage.library.get(watch.story.story_id) or watch.story
        if story.shared:
            return
        template = story_by_id(story.template_id)
        title = self._text(template.title_key) if template is not None else ""
        try:
            for number, card in enumerate(story.order, start=1):
                if card not in story.recordings:
                    continue
                filename = self.storage.private_card_wav_name(story, card)
                label = f"{title} {number}".strip() or str(number)
                self.creations.publish_private_file(filename, media_type="audio/wav", role="narration", title=label[:100])
        except (RuntimeError, ValueError, OSError):
            self.cast.try_again()
            self.audio.play("boop")
            self._dirty = True
            return
        updated = self.storage.mark_shared(story.story_id)
        watch.story = updated or story
        if self._watch_layout is not None:
            self.motion.add_fx("check_pop", self._watch_layout.share.center, self.clock())
        self.cast.correct()
        self.audio.play("chime")
        self._sync_watch()
        self._dirty = True

    def _complete(self) -> None:
        watch = self.watch
        if watch is None or self.state is not Screen.WATCH:
            return
        self.progress.mark_done(watch.template_id)
        told = len(watch.recordings)
        total = len(watch.order)
        earned = told if self.mic_ok else total
        self.completion = PygameCompletionScreen(
            self.typography,
            width=REFERENCE_WIDTH,
            height=REFERENCE_HEIGHT,
            palette=CompletionPalette(background=NAVY),
            scene=CompletionScene(self.kit, character=HOST, star_total=total, primary_glyph="new", secondary_glyph="play"),
        )
        self.completion.prepare(
            CompletionContent(
                title=self._text("victory.title"),
                primary_label=self._text("button.new_story"),
                secondary_label=self._text("button.watch_again"),
                achievement_count=earned,
            )
        )
        self._surfaces.push_overlay(CompletionOverlay(self.completion, on_primary=self.open_picker, on_secondary=self._watch_again))
        self.state = Screen.DONE
        self.audio.play("fanfare")
        self.timeline.after(0.5, lambda: self.audio.host("praise.general"))
        self._dirty = True

    def _watch_again(self) -> None:
        self._activated = True
        self._leave_overlays()
        self.state = Screen.WATCH
        self._begin_slides()

    # -- shelf --------------------------------------------------------------------

    def open_shelf(self, focus_story: str | None = None) -> None:
        self._activated = True
        self._leave_overlays()
        self._reset_scene()
        self.state = Screen.SHELF
        self.cast.waving = False
        stories = self.storage.stories
        if focus_story is not None:
            index = next((i for i, story in enumerate(stories) if story.story_id == focus_story), 0)
            self.shelf_page = index // SHELF_PAGE_SIZE
        self.shelf_page = max(0, min(self.shelf_page, self._page_count() - 1))
        self._show_shelf(focus_story)
        if not stories:
            self.cast.point(2.0)
        self._dirty = True

    def _page_count(self) -> int:
        return max(1, (len(self.storage.stories) + SHELF_PAGE_SIZE - 1) // SHELF_PAGE_SIZE)

    def _shelf_page(self):
        layout = self._shelf_layout
        stories = list(self.storage.stories[self.shelf_page * SHELF_PAGE_SIZE : (self.shelf_page + 1) * SHELF_PAGE_SIZE])
        cards = list(layout.cards[: len(stories)]) if layout is not None else []
        return stories, cards

    def _show_shelf(self, focus_story: str | None = None) -> None:
        button = self._layout_source.control_height(64, maximum=80)
        self._shelf_layout = ShelfLayout.build(self._layout_source.protected, button=button)
        stories, cards = self._shelf_page()
        focus = next((i for i, story in enumerate(stories) if story.story_id == focus_story), None)
        self.controls.show_shelf(
            self._shelf_layout,
            cards,
            page=self.shelf_page,
            page_count=self._page_count(),
            on_card=self._on_shelf_card,
            on_card_delete=self._on_shelf_delete,
            pending=self.pending is not None,
            can_save=not self.storage.is_full,
            focus_card=focus,
        )

    def _shelf_story(self, slot: int) -> SavedStory | None:
        stories, _ = self._shelf_page()
        return stories[slot] if 0 <= slot < len(stories) else None

    def _on_shelf_card(self, slot: int) -> None:
        story = self._shelf_story(slot)
        if story is None:
            return
        self._activated = True
        self._start_watch(story.template_id, story.order, story.recordings, story.durations, story=story, from_shelf=True)

    def _on_page(self, delta: int) -> None:
        page = max(0, min(self._page_count() - 1, self.shelf_page + delta))
        if page == self.shelf_page:
            return
        self._activated = True
        self.shelf_page = page
        self._show_shelf()
        self.audio.play("page")
        self._dirty = True

    def _on_delete_focused(self) -> None:
        slot = self.controls.focused_shelf_slot()
        if slot is None:
            stories, _ = self._shelf_page()
            slot = 0 if stories else None
        if slot is not None:
            self._on_shelf_delete(slot)

    def _on_shelf_delete(self, slot: int) -> None:
        story = self._shelf_story(slot)
        if story is None or self.sheet is not None:
            return
        self._activated = True
        self.delete_confirm = DeleteConfirmation(story.story_id, self.clock())
        preview_art = card_art(story.template_id, story.cover_card)
        preview = self.art.card(preview_art, self.sheets.layout.preview.size, key=f"{story.template_id}.{story.cover_card}")
        trash = self.kit.glyph("trash", 56)

        def backdrop(surface: pygame.Surface) -> None:
            self.renderer.draw_sheet(surface, self.sheets.layout, preview, accent=(232, 86, 74), symbol=trash)

        self.sheet = self.sheets.delete(
            draw_backdrop=backdrop,
            on_keep=lambda: self._resolve_delete(DeleteConfirmation.KEEP),
            on_delete=lambda: self._resolve_delete(DeleteConfirmation.DELETE),
        )
        self._surfaces.push_overlay(self.sheet)
        self._dirty = True

    def _resolve_delete(self, choice: str) -> None:
        confirm = self.delete_confirm
        if confirm is None:
            return
        outcome = confirm.resolve(choice, self.clock())
        if outcome is None:
            return  # delete pressed before the dialog armed: ignore
        self._activated = True
        self._close_sheet()
        self.delete_confirm = None
        if outcome == DeleteConfirmation.DELETE and self.storage.delete_story(confirm.target_id):
            self.audio.play("unpop")
            self.shelf_page = max(0, min(self.shelf_page, self._page_count() - 1))
        self._show_shelf()
        self._dirty = True

    def _open_full_sheet(self) -> None:
        draft = self.pending
        assert draft is not None
        first = draft.order[0]
        preview = self.art.card(card_art(draft.template_id, first), self.sheets.layout.preview.size, key=f"{draft.template_id}.{first}")
        meter = self.art.meter((96, 40), MAX_SAVED_STORIES, MAX_SAVED_STORIES)
        shelf_icon = self.art.shelf_icon(80, MAX_SAVED_STORIES, MAX_SAVED_STORIES)

        def backdrop(surface: pygame.Surface) -> None:
            self.renderer.draw_sheet(surface, self.sheets.layout, preview, accent=(232, 86, 74), symbol=meter)

        self.cast.try_again()
        self.sheet = self.sheets.full(
            shelf_icon=shelf_icon,
            draw_backdrop=backdrop,
            on_shelf=self._full_to_shelf,
            on_watch=self._full_watch,
        )
        self._surfaces.push_overlay(self.sheet)
        self._dirty = True

    def _full_to_shelf(self) -> None:
        self._activated = True
        self._close_sheet()
        self.open_shelf()

    def _full_watch(self) -> None:
        self._activated = True
        self._close_sheet()
        draft = self.pending
        if draft is None:
            return
        self._start_watch(draft.template_id, draft.order, draft.recordings, draft.durations, story=None, from_shelf=False)

    def _on_save_pending(self) -> None:
        draft = self.pending
        if draft is None or self.storage.is_full:
            return
        self._activated = True
        story = self._save(draft)
        if story is None:
            self.cast.try_again()
            self._dirty = True
            return
        self.pending = None
        self.shelf_page = 0
        self.open_shelf(focus_story=story.story_id)
        self.motion.halos[f"story.{story.story_id}"] = self.clock() + HALO_SECONDS
        self.cast.correct()
        self.audio.play("chime")

    def _close_sheet(self) -> None:
        if self.sheet is not None and self._surfaces.overlays and self._surfaces.overlays[-1] is self.sheet:
            self._surfaces.pop_overlay()
        self.sheet = None

    # -- hints --------------------------------------------------------------------

    def _maybe_hint(self, now: float) -> None:
        if self._busy or self.timeline.busy or self.drag is not None:
            return
        if self.state is Screen.TELL and self.record_state is not RecordState.IDLE:
            return
        step = self._hints.poll(now, self._last_activity)
        if not step:
            return
        halo = self._hints.animation_seconds(HALO_SECONDS)
        self.cast.point(halo)
        if self.state is Screen.ORDER and self.board is not None:
            hint = self.board.hint()
            if hint is not None:
                slot, card = hint
                until = now + halo
                self.motion.halos[f"slot.{slot}"] = until
                if step == 1:
                    self._show_guide(now)
                if step >= 2:
                    self.motion.halos[f"card.{card}"] = until
        self._dirty = True

    def _show_guide(self, now: float) -> None:
        """Finger glides from the tray up to the places: "move the cards up"."""

        layout = self._order_layout
        if layout is None:
            return
        tray = layout.tray[len(layout.tray) // 2].copy()
        slots = layout.slots[len(layout.slots) // 2].copy()
        tray.centerx = slots.centerx = (layout.tray[0].left + layout.tray[-1].right) // 2
        self.motion.guide = (tray, slots, now)

    def _on_hint(self) -> None:
        if self.board is None or self._busy:
            return
        self._activated = True
        hint = self.board.hint()
        if hint is not None:
            slot, card = hint
            until = self.clock() + HALO_SECONDS
            self.motion.halos[f"slot.{slot}"] = until
            self.motion.halos[f"card.{card}"] = until
        self.cast.point(HALO_SECONDS)
        self._dirty = True

    # -- shared -------------------------------------------------------------------

    def _picker_icon(self) -> pygame.Surface | None:
        return self.art.picture("ui.pictogram.creation", 44)

    def _shelf_button_icon(self) -> pygame.Surface | None:
        return self.art.picture("prop.everyday.book", 46)

    def _reset_scene(self) -> None:
        if self.record_state is RecordState.RECORDING:
            self._stop_recording()
        self.record_state = RecordState.IDLE
        self.audio.stop_voice()
        self.timeline.clear()
        self.motion.clear()
        self.drag = None
        self._busy = False
        self.cast.reset()

    def _leave_overlays(self) -> None:
        while self._surfaces.overlays:
            self._surfaces.pop_overlay()
        self.sheet = None
        self.delete_confirm = None
        if self.completion.is_prepared:
            self.completion.clear()

    def _reshow(self) -> None:
        if self.state is Screen.PICKER:
            self._show_picker()
        elif self.state is Screen.ORDER and self.board is not None:
            self._show_order()
        elif self.state is Screen.TELL and self.template is not None:
            button = self._layout_source.control_height(64, maximum=80)
            self._tell_layout = TellLayout.build(len(self.template.cards), self._layout_source.protected, button=button)
            self.controls.show_tell(self._tell_layout, len(self.template.cards), picker_icon=self._picker_icon())
            self._sync_tell()
        elif self.state in {Screen.WATCH, Screen.DONE} and self.watch is not None:
            button = self._layout_source.control_height(64, maximum=80)
            self._watch_layout = WatchLayout.build(len(self.watch.order), self._layout_source.protected, button=button)
            share = self.watch.story is not None and self.creations is not None
            icon = self._shelf_button_icon() if self.watch.from_shelf else self._picker_icon()
            self.controls.show_watch(self._watch_layout, len(self.watch.order), top_icon=icon, share=share)
            self._sync_watch()
        elif self.state is Screen.SHELF:
            self._show_shelf()


def _safe_point(surface: pygame.Surface, position: tuple[int, int]) -> bool:
    viewport = activity_viewport_for_surface(surface)
    x, y = position
    if not (0 <= x < viewport.surface.width and 0 <= y < viewport.surface.height):
        return False
    for protected in viewport.protected_regions:
        if protected.x <= x < protected.right and protected.y <= y < protected.bottom:
            return False
    return True


__all__ = ["Screen", "StoryApp", "StoryDraft", "Timeline", "shelf_card_id"]
