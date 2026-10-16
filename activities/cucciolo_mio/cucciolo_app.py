"""Lifecycle, timing and shared-kit input for My Cute Pet (Cucciolo Mio).

First visit: the child adopts a pet (puppy, kitten or guinea pig - shared
library pets) and gives it a picture name tag (spoken from the shared
vocabulary bank when a recording exists). The pet is remembered.

Every visit is one finite day of care in the pet's playroom:

* a need shows only through body language (the library's ``hungry`` /
  ``dirty`` / ``playful`` / ``hurt`` / ``sleepy`` art, plus the pet acting
  it out every few seconds); progress dots run from a sun to a moon;
* the child reads it and taps a care in the picture tray (food bowl, sponge,
  ball, plaster, bed). Right care -> Lilli cheers and the pet goes to the
  room where it happens (kitchen, bathroom, bedroom) and the child does the
  care with a few taps on the pet (bites, scrubs, throws, plaster + cuddles,
  tuck in + lights off). Wrong care -> the pet gently shakes its head ("not
  now"), Lilli thinks, the pet acts its need out again; after a second miss
  the right care glows. Retries are unlimited and nothing ever gets worse;
* idle ~6 s -> Lilli points and the pet acts its need out; later the right
  care glows;
* bedtime always ends the day: lights off, then the shared completion scene.
  The next day adapts from the misses of this one (three rungs).
"""

from __future__ import annotations

from collections import deque
from collections.abc import Callable
from dataclasses import replace
import random
import time

import pygame

from greia_platform.activity_api import activity_stop_requested, mark_activity_ready
from greia_platform.frame_governor import FrameGovernor, FrameKind
from greia_platform.activity_controls import (
    ControlArt,
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
    from .cucciolo_art import CuccioloArt
    from .cucciolo_audio import CuccioloAudio
    from .cucciolo_content import CARES, NAMES_BY_ID, REFERENCE_HEIGHT, REFERENCE_WIDTH, SPECIES_BY_ID, Care, Need, Room
    from .cucciolo_controls import TAG_ICON, CuccioloControls
    from .cucciolo_layout import ADOPT_ICON, HOME_FLOOR, LILLI_HEIGHT, OFFER_POINT, NAME_PET_FLOOR, SPONGE_SPOTS, STAGES, pet_rect
    from .cucciolo_model import CareDay, Offer, Phase, adapt_level
    from .cucciolo_renderer import (
        SLIDE_SECONDS,
        THROW_SECONDS,
        CuccioloRenderer,
        LilliCast,
        SceneMotion,
        SceneView,
        Screen,
    )
    from .cucciolo_services import EventPort, PetProfile, ProgressPort
else:
    from cucciolo_art import CuccioloArt
    from cucciolo_audio import CuccioloAudio
    from cucciolo_content import CARES, NAMES_BY_ID, REFERENCE_HEIGHT, REFERENCE_WIDTH, SPECIES_BY_ID, Care, Need, Room
    from cucciolo_controls import TAG_ICON, CuccioloControls
    from cucciolo_layout import ADOPT_ICON, HOME_FLOOR, LILLI_HEIGHT, OFFER_POINT, NAME_PET_FLOOR, SPONGE_SPOTS, STAGES, pet_rect
    from cucciolo_model import CareDay, Offer, Phase, adapt_level
    from cucciolo_renderer import (
        SLIDE_SECONDS,
        THROW_SECONDS,
        CuccioloRenderer,
        LilliCast,
        SceneMotion,
        SceneView,
        Screen,
    )
    from cucciolo_services import EventPort, PetProfile, ProgressPort

TELL_EVERY = 4.0
DAY_START_CALM = 2.6
NAME_DELAY = 1.2
CHOICE_PAUSE = 0.7
NOT_NOW_LOCK = 0.55
DEMO_DELAY = 0.65
GLOW_SECONDS = 3.2
HAPPY_SECONDS = 1.5
CALM_SECONDS = 2.2
NEXT_NEED_SECONDS = 1.1
BEDTIME_HOLD = 2.0
MAX_SCHEDULED = 32
NIGHT = (37, 59, 89)  # theme ink "navy"
WINDOW_STAR = (112, 150)  # the bedroom wall's night window
# Short settle after the last care action, per care (the action plays first).
FINISH_DELAY: dict[Care, float] = {
    Care.FOOD: 0.45,
    Care.BATH: 0.55,
    Care.BALL: THROW_SECONDS + 0.1,
    Care.PLASTER: 0.6,
    Care.BED: 1.4,
}


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


class CuccioloApp:
    """Coordinate the pet, the care day, kit controls, art, audio and lifecycle."""

    def __init__(
        self,
        *,
        screen: pygame.Surface,
        canvas: PygameReferenceCanvas,
        typography: GreiaTypography,
        resources: LocalizedResources | None,
        audio: CuccioloAudio,
        progress: ProgressPort,
        events: EventPort,
        rng: random.Random | None = None,
        clock: Callable[[], float] = time.monotonic,
        kit: ControlKit | None = None,
        art: CuccioloArt | None = None,
        session_prefix: str | None = None,
    ) -> None:
        self.screen = screen
        self.canvas = canvas
        self.typography = typography
        self.resources = resources
        self.audio = audio
        self.progress = progress
        self.events = events
        self.rng = rng if rng is not None else random.Random()
        self.clock = clock
        self._session_prefix = session_prefix or f"{int(time.time())}"
        self._days_played = 0

        self.profile: PetProfile = progress.load()
        self.selected_species: str | None = self.profile.species
        self.selected_name: str | None = self.profile.name

        # Shared control kit (ADR 0037): play Collection -> ocean accent.
        self.kit = kit if kit is not None else ControlKit(typography, ControlTheme.for_accent("ocean"))
        self.art = art if art is not None else CuccioloArt(art=ControlArt(max_entries=72))
        feedback = CastFeedback("lilli", height=LILLI_HEIGHT, art=self.art.loader, clock=clock)
        self.cast = LilliCast(feedback, self.art, clock)
        self.renderer = CuccioloRenderer(self.art, self.cast)
        self.motion = SceneMotion()
        self.timeline = Timeline(clock)
        self.controls = CuccioloControls(
            self.kit,
            self.art,
            text=lambda key: self._text(key, ""),
            on_species=self._on_species,
            on_name=self._on_name,
            on_confirm=self._on_confirm,
            on_care=self._on_care,
            on_pet=self._on_pet,
        )
        self._surfaces = SurfaceNavigator(self.controls.layer)
        self._input = PygameControlInput(to_logical=canvas.pointer, is_safe=lambda pos: _safe_point(self.screen, pos))
        self.controls.relayout(ControlLayout.for_canvas(canvas, screen.get_size()))

        self.screen_id = Screen.ADOPT
        self.day: CareDay | None = None
        self.room = Room.PLAYROOM
        self.variant = "default"
        self.dim = False
        self._care_shown: Care | None = None  # the care stage still on screen
        self.completion: PygameCompletionScreen | None = None
        self.session_id = ""
        self._running = True
        self.ready_published = False
        self._dirty = True
        self._activated = False
        self._busy = False
        self._last_activity = clock()
        self._hints = IdleHintScheduler(now=self._last_activity)
        if self.profile.adopted:
            self.start_day()
        else:
            self.show_adopt()

    # -- main loop ----------------------------------------------------------------

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
            self.persist()
            self.typography.clear()
        return 0

    def step(self) -> bool:
        """Advance timers; return True while something on screen is moving."""

        now = self.clock()
        if self.timeline.run_due():
            self._dirty = True
        if self.cast.update():
            self._dirty = True
        self.motion.prune(now)
        if self.screen_id is not Screen.END:
            self._maybe_hint(now)
            self._maybe_tell(now)
        if self.controls.layer.invalidation.should_draw:
            self._dirty = True
        if self.screen_id is Screen.END:
            return False
        return self.motion.active(now) or self.cast.animating

    def render(self) -> None:
        surface = self.canvas.surface
        if self.screen_id is not Screen.END:
            self.renderer.draw(
                surface,
                self.view(),
                self.motion,
                self.clock(),
                sun_rect=self.controls.sun_rect,
                moon_rect=self.controls.moon_rect,
                tray_rect=self.controls.tray_rect,
            )
        self._surfaces.draw(surface)

    def view(self) -> SceneView:
        day = self.day
        if self.screen_id is Screen.NAME:
            species = self.selected_species
        else:
            species = self.profile.species
        return SceneView(
            screen=self.screen_id,
            room=self.room,
            species=species,
            variant=self.variant,
            care=self._care_shown,
            steps_done=day.steps_done if day is not None else 0,
            dim=self.dim,
        )

    def persist(self) -> None:
        if self.profile.adopted:
            self.progress.save(self.profile)

    # -- input --------------------------------------------------------------------

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.QUIT:
            self._running = False
            return
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self._running = False
            return
        if event.type == pygame.VIDEORESIZE:
            self._resize()
            return
        if event.type in (pygame.MOUSEMOTION, pygame.FINGERMOTION):
            self._dirty = True  # keep the platform pointer live
        translated = self._input.translate(event)
        if translated is not None:
            self._dispatch(translated)

    def _resize(self) -> None:
        self.screen = pygame.display.get_surface() or self.screen
        self.canvas = PygameReferenceCanvas(self.screen)
        self._input = PygameControlInput(to_logical=self.canvas.pointer, is_safe=lambda pos: _safe_point(self.screen, pos))
        self.controls.relayout(ControlLayout.for_canvas(self.canvas, self.screen.get_size()))
        self._dirty = True

    def _dispatch(self, kit_input) -> bool:
        if not isinstance(kit_input, KitPointer) or kit_input.phase is not PointerPhase.MOVE:
            self._note_activity()
        result = self._surfaces.dispatch(kit_input)
        if self.controls.layer.invalidation.should_draw:
            self._dirty = True
        return result is not UiEventResult.IGNORED

    def tap(self, logical: tuple[int, int]) -> bool:
        """Deliver one complete tap at a logical position (tests/tools)."""

        point = (int(logical[0]), int(logical[1]))
        self._activated = False
        self._dispatch(KitPointer(PointerPhase.DOWN, point))
        self._dispatch(KitPointer(PointerPhase.UP, point))
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

    # -- adoption -----------------------------------------------------------------

    def show_adopt(self) -> None:
        self.screen_id = Screen.ADOPT
        self.room = Room.PLAYROOM
        self.timeline.clear()
        self.motion.reset()
        self.cast.reset()
        self._sync_species_cards()
        self.controls.show_adopt(self.selected_species, self._text("adopt.prompt", ""))
        self.cast.point(2.0)
        self._busy = False
        self._note_activity()
        self._dirty = True

    def _sync_species_cards(self) -> None:
        for card in self.controls.species_cards:
            species = card.control_id.split(".", 1)[1]
            variant = "happy" if species == self.selected_species else "default"
            card.icon = self.art.pet(species, variant, ADOPT_ICON)

    def _on_species(self, species: str) -> None:
        if self.screen_id is not Screen.ADOPT or species not in SPECIES_BY_ID:
            return
        self._activated = True
        self.selected_species = species
        self._sync_species_cards()
        self.controls.show_adopt(species, self._text("adopt.prompt", ""))
        self.controls.layer.focus(f"species.{species}", visible=self.controls.layer.focus_visible)
        card = next(card for card in self.controls.species_cards if card.control_id == f"species.{species}")
        self.motion.add_fx("sparkle", (card.rect.centerx, card.rect.top + 40), self.clock())
        self.audio.play("pick")
        self._dirty = True

    def show_name(self) -> None:
        self.screen_id = Screen.NAME
        self.timeline.clear()
        self.motion.reset()
        self.variant = "happy" if self.selected_name else "default"
        self.controls.show_name(self.selected_name, self._text("name.prompt", ""))
        self.cast.point(2.0)
        self._note_activity()
        self._dirty = True

    def _on_name(self, name: str) -> None:
        if self.screen_id is not Screen.NAME or name not in NAMES_BY_ID:
            return
        self._activated = True
        self.selected_name = name
        self.controls.show_name(name, self._text("name.prompt", ""))
        self.controls.layer.focus(f"name.{name}", visible=self.controls.layer.focus_visible)
        now = self.clock()
        self.variant = "happy"
        self.motion.hop(now)
        pet = pet_rect(NAME_PET_FLOOR)
        self.motion.add_fx("heart_pop", (pet.centerx, pet.top + 40), now)
        if not self.audio.say_name(name):
            self.audio.play("heart")
        self._dirty = True

    def _on_confirm(self) -> None:
        if self.screen_id is Screen.ADOPT and self.selected_species is not None:
            self._activated = True
            self.audio.play("pick")
            self.show_name()
        elif self.screen_id is Screen.NAME and self.selected_name is not None and self.selected_species is not None:
            self._activated = True
            self.profile = replace(self.profile, species=self.selected_species, name=self.selected_name)
            self.persist()
            self.audio.play("heart")
            self.start_day()

    # -- the day ------------------------------------------------------------------

    def start_day(self) -> None:
        profile = self.profile
        assert profile.species is not None and profile.name is not None
        now = self.clock()
        self.timeline.clear()
        self.motion.reset()
        self.cast.reset()
        self.day = CareDay.planned(profile.level, self.rng)
        self._days_played += 1
        self.session_id = f"{self._session_prefix}-{self._days_played}-{self.rng.randrange(1_000_000):06d}"
        self.screen_id = Screen.DAY
        self.room = Room.PLAYROOM
        self.variant = "happy"
        self.dim = False
        self._care_shown = None
        name = NAMES_BY_ID[profile.name]
        self.controls.set_day_length(self.day.total)
        self.controls.show_day(
            profile.species,
            self.day.tray,
            self._text(name.text_key, ""),
            self.art.shared(name.asset_id, TAG_ICON),
        )
        self.controls.set_progress(0)
        self.motion.hop(now)
        self.audio.lilli("ready.go")
        self.timeline.after(NAME_DELAY, lambda: self.audio.say_name(profile.name or ""))
        self._busy = True
        self.timeline.after(DAY_START_CALM - NEXT_NEED_SECONDS, self._calm)
        self.timeline.after(DAY_START_CALM, self._emerge)
        self._note_activity()
        self._dirty = True

    def _calm(self) -> None:
        if self.screen_id is Screen.DAY:
            self.variant = "default"
            self._dirty = True

    def _emerge(self) -> None:
        day = self.day
        if day is None or self.screen_id is not Screen.DAY:
            return
        need = day.emerge()
        if need is None:
            return
        now = self.clock()
        self.variant = need.value
        self.motion.tell(need, now)
        if need is Need.DIRTY:
            self.motion.add_fx("dust_puff", (HOME_FLOOR[0] + 70, HOME_FLOOR[1] - 30), now)
        self.audio.play("chime")
        self.cast.point(1.6)
        self._busy = False
        self._note_activity()
        self._dirty = True

    def _on_care(self, care: Care) -> None:
        day = self.day
        if day is None or self.screen_id is not Screen.DAY or self._busy or day.phase is not Phase.NEED:
            return
        outcome = day.offer(care)
        if outcome.offer is Offer.IGNORED:
            return
        self._activated = True
        now = self.clock()
        tile = self.controls.tray_rect(care)
        if tile is not None:
            self.motion.offer(care, tile.center, OFFER_POINT, now, returns=outcome.offer is Offer.NOT_NOW)
        if outcome.offer is Offer.RIGHT:
            self.motion.glow_until = 0.0
            if tile is not None:
                self.motion.add_fx("sparkle", tile.center, now)
            self.audio.play("pick")
            self.cast.correct()
            self.audio.lilli("praise.general" if outcome.misses == 0 else "encourage.progress")
            self._busy = True
            self.timeline.after(CHOICE_PAUSE, lambda: self._enter_care(care))
        else:
            self.motion.shake_start = now + 0.25  # when the offered care arrives
            self.motion.wobble(care, now)
            self.audio.play("nope")
            self.cast.try_again()
            if outcome.misses % 3 == 1:
                self.audio.lilli("encourage.retry")
            self._busy = True
            self.timeline.after(NOT_NOW_LOCK, self._unlock)
            misses = outcome.misses
            self.timeline.after(DEMO_DELAY, lambda: self._demonstrate(misses))
        self._dirty = True

    def _unlock(self) -> None:
        day = self.day
        if day is not None and day.phase is Phase.NEED:
            self._busy = False
            self._dirty = True

    def _demonstrate(self, misses: int) -> None:
        """After a miss the pet acts its need out again; from the second the right care glows."""

        day = self.day
        if day is None or day.phase is not Phase.NEED or day.current_need is None:
            return
        now = self.clock()
        self.motion.tell(day.current_need, now)
        if misses >= 2 and day.right_care is not None:
            self.motion.glow(day.right_care, now, GLOW_SECONDS)
            self.timeline.after(0.5, lambda: self.cast.point(1.6))
        self._dirty = True

    def _enter_care(self, care: Care) -> None:
        day = self.day
        if day is None or day.phase is not Phase.CARE:
            return
        now = self.clock()
        target_room = CARES[care].room
        self._care_shown = care
        if target_room is not self.room:
            self.motion.slide(self.room, target_room, now)
            self.room = target_room
            self.audio.play("swoosh")
        self.controls.start_care(STAGES[care].target)
        self._busy = True
        self.timeline.after(SLIDE_SECONDS, self._ready_to_care)
        self._dirty = True

    def _ready_to_care(self) -> None:
        self._busy = False
        self.cast.point(1.4)
        self._note_activity()
        self._dirty = True

    def _on_pet(self) -> None:
        day = self.day
        if day is None or self._busy:
            return
        if day.phase is Phase.NEED and day.current_need is not None:
            # Touching the pet: it acts its need out again (never a choice).
            self._activated = True
            self.motion.tell(day.current_need, self.clock())
            self.audio.play("chime")
            self._dirty = True
            return
        if day.phase is not Phase.CARE:
            return
        care = day.right_care
        if care is None or not day.act():
            return
        self._activated = True
        now = self.clock()
        step = day.steps_done
        stage = STAGES[care]
        pet = stage.pet
        if care is Care.FOOD:
            self.motion.bite_start = now
            self.audio.play("munch")
            if stage.prop is not None:
                self.motion.add_fx("sparkle", (stage.prop.centerx, stage.prop.top + 50), now)
        elif care is Care.BATH:
            self.motion.scrub_start = now
            self.motion.scrub_spot = step - 1
            self.motion.add_fx("bubble_pop", SPONGE_SPOTS[(step - 1) % len(SPONGE_SPOTS)], now)
            self.audio.play("bubble")
            if day.care_finished:
                self.variant = "default"
        elif care is Care.BALL:
            self.motion.throw_start = now
            self.audio.play("swoosh")
            self.timeline.after(THROW_SECONDS * 0.5, lambda: self.audio.play("boing"))
            self._busy = True
            self.timeline.after(THROW_SECONDS, self._unlock_care)
        elif care is Care.PLASTER:
            if step == 1:
                self.motion.plaster_start = now
                self.audio.play("stick")
            else:
                self.motion.add_fx("heart_pop", (pet.centerx, pet.top + 70), now)
                self.motion.hop(now)
                self.audio.play("heart")
        elif care is Care.BED:
            if step == 1:
                self.motion.add_fx("sparkle", (pet.centerx + 70, pet.top + 60), now)
                self.audio.play("yawn")
            else:
                self.motion.dim_start = now
                self.dim = True
                self.audio.play("lullaby")
        self._note_activity()
        if day.care_finished:
            self._busy = True
            self.timeline.after(FINISH_DELAY[care], self._finish_care)
        self._dirty = True

    def _unlock_care(self) -> None:
        day = self.day
        if day is not None and day.phase is Phase.CARE and not day.care_finished:
            self._busy = False

    def _finish_care(self) -> None:
        day = self.day
        if day is None:
            return
        care = day.right_care
        need = day.settle()
        if need is None or care is None:
            return
        now = self.clock()
        self.controls.set_progress(len(day.cared))
        self.profile = replace(self.profile, cares=min(1_000_000, self.profile.cares + 1))
        if day.done:
            self.persist()
            self.motion.add_fx("sparkle", WINDOW_STAR, now)  # a star twinkles in the night window
            self.timeline.after(BEDTIME_HOLD, self._complete_day)
            return
        self.persist()
        self.events.cared(
            CARES[care].event_id,
            self.session_id,
            {
                "need": need.value,
                "care": care.value,
                "index": len(day.cared),
                "level": day.level + 1,
                "species": self.profile.species,
                "first_try": day.need_misses == 0,
            },
        )
        self.variant = "happy"
        self.motion.hop(now)
        pet = STAGES[care].pet
        self.motion.add_fx("heart_pop", (pet.centerx, pet.top + 50), now)
        self.audio.play("heart")
        if len(day.cared) == max(1, (day.total - 1) // 2):
            self.timeline.after(0.6, lambda: self.audio.lilli("encourage.progress"))
        self.timeline.after(HAPPY_SECONDS, self._go_home)

    def _go_home(self) -> None:
        day = self.day
        if day is None or self.screen_id is not Screen.DAY:
            return
        now = self.clock()
        if self.room is not Room.PLAYROOM:
            self.motion.slide(self.room, Room.PLAYROOM, now)
            self.room = Room.PLAYROOM
            self.audio.play("swoosh")
        self._care_shown = None
        self.controls.end_care(show_tray=True)
        self.timeline.after(CALM_SECONDS, self._calm)
        self.timeline.after(CALM_SECONDS + NEXT_NEED_SECONDS, self._emerge)
        self._dirty = True

    def _complete_day(self) -> None:
        day = self.day
        if day is None or self.screen_id is not Screen.DAY:
            return
        self.profile = replace(
            self.profile,
            level=adapt_level(day.level, day.misses),
            days=min(1_000_000, self.profile.days + 1),
        )
        self.persist()
        self.events.day_completed(
            self.session_id,
            {
                "needs": day.total,
                "misses": day.misses,
                "first_try": day.first_try,
                "level": day.level + 1,
                "species": self.profile.species,
            },
        )
        self.audio.lilli("celebrate.success")
        self.cast.correct()
        name = NAMES_BY_ID[self.profile.name or "moon"]
        self.completion = PygameCompletionScreen(
            self.typography,
            width=REFERENCE_WIDTH,
            height=REFERENCE_HEIGHT,
            palette=CompletionPalette(background=NIGHT),
            scene=CompletionScene(self.kit, character="lilli", star_total=day.total),
        )
        self.completion.prepare(
            CompletionContent(
                title=self._text("victory.title", "★", {"name": self._text(name.text_key, "")}),
                primary_label=self._text("btn.new_day", "↻"),
                body_lines=(self._text("victory.subtitle", "★"),),
                achievement_count=len(day.cared),
            )
        )
        self._surfaces.push_overlay(CompletionOverlay(self.completion, on_primary=self._restart))
        self.timeline.clear()
        self.controls.show_none()
        self.screen_id = Screen.END
        self._busy = False
        self._dirty = True

    def _restart(self) -> None:
        self._activated = True
        if self.completion is not None:
            self._surfaces.pop_overlay()
            self.completion.clear()
            self.completion = None
        self.start_day()

    # -- hints and life ---------------------------------------------------------------

    def _maybe_hint(self, now: float) -> None:
        if self._busy:
            return
        day = self.day
        need = care = pick = False
        if self.screen_id is Screen.DAY and day is not None:
            need = day.phase is Phase.NEED and day.current_need is not None
            care = day.phase is Phase.CARE
        else:
            pick = self.screen_id in (Screen.ADOPT, Screen.NAME)
        if not (need or care or pick):
            return
        step = self._hints.poll(now, self._last_activity)
        if not step:
            return
        self.cast.point(self._hints.animation_seconds(1.8))
        if need:
            assert day is not None and day.current_need is not None
            self.motion.tell(day.current_need, now)
            if step >= 3 and day.right_care is not None:
                self.motion.glow(day.right_care, now, self._hints.animation_seconds(GLOW_SECONDS))
        elif care:
            self.motion.pet_glow_until = now + self._hints.animation_seconds(2.4)
        else:
            chosen = self.selected_species if self.screen_id is Screen.ADOPT else self.selected_name
            if chosen is not None:
                self.motion.add_fx("sparkle", self.controls.confirm.rect.center, now)
        self._dirty = True

    def _maybe_tell(self, now: float) -> None:
        """While a need waits, the pet acts it out every few seconds (body language)."""

        day = self.day
        if self.screen_id is not Screen.DAY or day is None or day.phase is not Phase.NEED or self._busy:
            return
        need = day.current_need
        if need is not None and now - self.motion.tell_start >= TELL_EVERY:
            self.motion.tell(need, now)
            self._dirty = True

    # -- helpers --------------------------------------------------------------------

    def _text(self, key: str, default: str, variables: dict | None = None) -> str:
        if self.resources is None:
            return default
        try:
            return self.resources.text(key, variables) or default
        except Exception:
            return default


def _safe_point(surface: pygame.Surface, position: tuple[int, int]) -> bool:
    """True inside the play surface and outside the Greia protected region(s)."""

    viewport = activity_viewport_for_surface(surface)
    x, y = position
    if not (0 <= x < viewport.surface.width and 0 <= y < viewport.surface.height):
        return False
    for protected in viewport.protected_regions:
        if protected.x <= x < protected.right and protected.y <= y < protected.bottom:
            return False
    return True


__all__ = ["CuccioloApp", "Timeline"]
