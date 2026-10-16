"""Lifecycle, scripted moments and shared-kit input for Little Vet Clinic.

One clinic day is five patients. Each patient walks onto the exam table
showing its problem (muddy fur, a scratched paw, a sore ear, a tummy ache).
The child first *looks* and taps where it hurts, then uses the tool tray in
the ailment's fixed order; the tool flies to the patient and does its job,
and the patient visibly gets better. After the last step (always a cuddle)
the happy patient hops home. There is no answer-revealing UI: the problem
is shown on the patient, never the tool.

Feedback follows ADR 0037: correct = Momo ``pose_cheer`` + FX + care sound;
try again = Momo ``pose_think`` + the patient gently shakes its head, then a
demonstration (the sore place glows / the right tool hops), with unlimited
kind retries. Idle hints are graduated (~6 s -> Momo points and the patient
wiggles; again -> the glow or the hopping tool). The day ends on the shared
cast completion scene and the next day adapts its level.
"""

from __future__ import annotations

from collections import deque
from collections.abc import Callable
from enum import StrEnum
import math
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
    CompletionScene,
    PygameCompletionScreen,
)
from greia_platform.typography import GreiaTypography
from greia_platform.ui_core import SurfaceNavigator, UiEventResult

if __package__:
    from .clinic_art import ClinicArt
    from .clinic_audio import ClinicAudio
    from .clinic_content import PATIENTS_PER_DAY, REFERENCE_HEIGHT, REFERENCE_WIDTH, BodyPart, Tool, level_spec, sore_anchor, tool_target
    from .clinic_controls import ClinicControls, tool_id
    from .clinic_layout import MOMO_HEIGHT, PATIENT_HOME, PATIENT_OFFSTAGE_X, patient_rect, to_screen
    from .clinic_model import CareResult, ClinicDay, ClinicDayFactory, Phase, adapt_level
    from .clinic_renderer import (
        FLIGHT_SECONDS,
        TOOL_HOP_SECONDS,
        WORK_SECONDS,
        ClinicCast,
        ClinicMotion,
        ClinicRenderer,
        ToolFlight,
    )
    from .clinic_services import ClinicEventPort, ClinicProgressPort, ClinicProgressState
else:
    from clinic_art import ClinicArt
    from clinic_audio import ClinicAudio
    from clinic_content import PATIENTS_PER_DAY, REFERENCE_HEIGHT, REFERENCE_WIDTH, BodyPart, Tool, level_spec, sore_anchor, tool_target
    from clinic_controls import ClinicControls, tool_id
    from clinic_layout import MOMO_HEIGHT, PATIENT_HOME, PATIENT_OFFSTAGE_X, patient_rect, to_screen
    from clinic_model import CareResult, ClinicDay, ClinicDayFactory, Phase, adapt_level
    from clinic_renderer import (
        FLIGHT_SECONDS,
        TOOL_HOP_SECONDS,
        WORK_SECONDS,
        ClinicCast,
        ClinicMotion,
        ClinicRenderer,
        ToolFlight,
    )
    from clinic_services import ClinicEventPort, ClinicProgressPort, ClinicProgressState

WALK_IN_SECONDS = 1.1
WALK_OUT_SECONDS = 1.2
FOUND_SECONDS = 0.9
REJECT_LOCK_SECONDS = 0.7
DEMONSTRATE_AFTER = 1.3
HEALED_HOLD_SECONDS = 1.9
MAX_SCHEDULED = 32

# Care effect per tool: (library FX, synthesized sound).
_TOOL_EFFECTS: dict[Tool, tuple[str, str]] = {
    Tool.STETHOSCOPE: ("beat_ring", "heartbeat"),
    Tool.SPONGE: ("bubble_pop", "scrub"),
    Tool.TOWEL: ("sparkle", "fluff"),
    Tool.MEDICINE: ("sparkle", "drip"),
    Tool.BANDAGE: ("check_pop", "stick"),
    Tool.CUDDLE: ("heart_pop", "cuddle"),
}


class AppState(StrEnum):
    PLAYING = "playing"
    TERMINAL = "terminal"


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


class ClinicActivity:
    """Coordinate the clinic day, shared-kit controls, art and lifecycle."""

    def __init__(
        self,
        *,
        screen: pygame.Surface,
        canvas: PygameReferenceCanvas,
        day: ClinicDay,
        factory: ClinicDayFactory,
        typography: GreiaTypography,
        resources: LocalizedResources,
        progress: ClinicProgressPort,
        saved: ClinicProgressState,
        events: ClinicEventPort,
        audio: ClinicAudio,
        clock: Callable[[], float] = time.monotonic,
        kit: ControlKit | None = None,
        art: ClinicArt | None = None,
    ) -> None:
        self.screen = screen
        self.canvas = canvas
        self.day = day
        self.factory = factory
        self.typography = typography
        self.resources = resources
        self.progress = progress
        self.saved = saved
        self.events = events
        self.audio = audio
        self.clock = clock

        # Shared control kit (ADR 0037): play Collection -> ocean accent.
        self.kit = kit if kit is not None else ControlKit(typography, ControlTheme.for_accent("ocean"))
        self.art = art if art is not None else ClinicArt(self.kit.painter)
        feedback = CastFeedback("momo", height=MOMO_HEIGHT, art=self.kit.art, clock=clock)
        self.cast = ClinicCast(feedback, self.art.cast_pose("momo", "pose_point", MOMO_HEIGHT), clock)
        self.renderer = ClinicRenderer(self.art, self.cast, clock=clock)
        self.motion = ClinicMotion()
        self.timeline = Timeline(clock)
        self.controls = ClinicControls(
            self.kit,
            ControlLayout.for_canvas(canvas, screen.get_size()),
            tool_icons=self.art.tile_icons,
            on_part=self._on_part,
            on_tool=self._on_tool,
        )
        self._surfaces = SurfaceNavigator(self.controls.layer)
        self._input = PygameControlInput(to_logical=canvas.pointer, is_safe=lambda pos: _safe_point(self.screen, pos))
        self.completion = PygameCompletionScreen(
            typography,
            width=REFERENCE_WIDTH,
            height=REFERENCE_HEIGHT,
            scene=CompletionScene(self.kit, character="momo", star_total=PATIENTS_PER_DAY),
        )
        self.state = AppState.PLAYING
        self._running = True
        self._ready_published = False
        self._dirty = True
        self._marks_bobbing = False
        self._activated = False
        self._busy = False
        self._last_activity = clock()
        self._hints = IdleHintScheduler(now=self._last_activity)
        self.audio.say("ready.go")
        self._start_patient()

    # -- main loop --------------------------------------------------------------

    def run(self) -> int:
        frames = FrameGovernor()
        try:
            while self._running and not activity_stop_requested():
                for event in frames.events():
                    self._handle_event(event)
                repeat = self._input.poll()
                if repeat is not None:
                    self._dispatch(repeat)
                animating = self.step()
                # The bobbing sore-ear/tummy marks are decoration: on the
                # reference floor they freeze once the child is idle (the
                # 0f560c2e regression declared them essential motion).
                frame = frames.frame(dirty=self._dirty, animating=animating, ambient=self._marks_bobbing)
                if frame is FrameKind.FULL:
                    self.render()
                    self.canvas.present()
                    pygame.display.flip()
                    self._dirty = False
                    if not self._ready_published:
                        mark_activity_ready()
                        self._ready_published = True
                elif frame is FrameKind.POINTER:
                    self.canvas.present_pointer()
                frames.wait(polling=self._input.repeating)
        finally:
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
        if self.state is AppState.PLAYING:
            self._maybe_hint(now)
        if self.controls.layer.invalidation.should_draw:
            self._dirty = True
        # The sore-ear / tummy marks bob gently while a problem is visible:
        # ambient decoration, not essential motion.
        self._marks_bobbing = (
            self.state is AppState.PLAYING and bool(self.day.look.overlays) and self.day.phase is not Phase.DONE
        )
        return self.motion.active(now) or self.cast.animating

    def render(self) -> None:
        surface = self.canvas.surface
        if self.state is AppState.PLAYING:
            self.renderer.draw(surface, self.day, self.motion)
            self.controls.draw(surface, self._tile_offsets())
        else:
            self._surfaces.draw(surface)

    def _tile_offsets(self) -> dict[str, tuple[int, int]]:
        now = self.clock()
        offsets: dict[str, tuple[int, int]] = {}
        if self.motion.tool_hop is not None:
            control_id, start = self.motion.tool_hop
            age = now - start
            if 0.0 <= age < TOOL_HOP_SECONDS:
                offsets[control_id] = (0, -int(16 * abs(math.sin(age * math.pi * 2.5))))
        if self.motion.wobble is not None:
            control_id, start = self.motion.wobble
            age = now - start
            if 0.0 <= age < 0.4:
                offsets[control_id] = (int(9 * (1 - age / 0.4) * (1 if int(age * 40) % 2 else -1)), 0)
        return offsets

    # -- input --------------------------------------------------------------------

    def _handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.QUIT:
            self._running = False
            return
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self._running = False
            return
        if event.type == pygame.VIDEORESIZE:
            self.screen = pygame.display.get_surface() or self.screen
            self.canvas = PygameReferenceCanvas(self.screen)
            self._input = PygameControlInput(
                to_logical=self.canvas.pointer, is_safe=lambda pos: _safe_point(self.screen, pos)
            )
            self.controls.relayout(ControlLayout.for_canvas(self.canvas, self.screen.get_size()))
            self._dirty = True
            return
        translated = self._input.translate(event)
        if translated is not None:
            self._dispatch(translated)

    def _dispatch(self, kit_input) -> bool:
        if not isinstance(kit_input, KitPointer) or kit_input.phase is not PointerPhase.MOVE:
            self._note_activity()
        result = self._surfaces.dispatch(kit_input)
        if self.controls.layer.invalidation.should_draw:
            self._dirty = True
        return result is not UiEventResult.IGNORED

    def tap(self, raw_pos: tuple[int, int]) -> bool:
        """Deliver one complete tap at a physical position (tests/tools)."""

        if not _safe_point(self.screen, raw_pos):
            return False
        logical = self.canvas.pointer(raw_pos)
        if logical is None:
            return False
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

    # -- patient flow ----------------------------------------------------------------

    def _start_patient(self) -> None:
        now = self.clock()
        self.timeline.clear()
        self.motion.clear()
        self.cast.reset()
        self.controls.show_patient(self.day, self.factory.tray(self.day.level))
        self.motion.walk(PATIENT_OFFSTAGE_X, PATIENT_HOME[0], now, WALK_IN_SECONDS)
        self.audio.play("hop")
        self._busy = True
        self._sync()
        self.timeline.after(WALK_IN_SECONDS, self._arrived)
        self._dirty = True

    def _arrived(self) -> None:
        self.day.arrived()
        self.audio.name(self.day.case.species.vocab)
        self.cast.point(1.8)
        self._end_busy()

    def _end_busy(self) -> None:
        self._busy = False
        self._note_activity()
        self._sync()
        self._dirty = True

    def _sync(self) -> None:
        self.controls.sync(self.day, busy=self._busy)

    def _on_part(self, part: BodyPart, spot: tuple[int, int]) -> None:
        if self._busy or self.day.phase is not Phase.FIND:
            return
        self._activated = True
        result = self.day.find(part)
        if result is None:
            return
        now = self.clock()
        if result.correct:
            self.motion.add_fx("check_pop", spot, now)
            self.motion.hop_start = now
            self.audio.play("pop")
            self.cast.correct()
            self._busy = True
            self._sync()
            # Momo then points at the tray: time to care.
            self.timeline.after(FOUND_SECONDS, lambda: (self.cast.point(1.6), self._end_busy()))
        else:
            self._try_again(None)
            self.timeline.after(DEMONSTRATE_AFTER, self._show_sore_place)
        self._dirty = True

    def _on_tool(self, tool: Tool) -> None:
        if self._busy or self.day.phase is not Phase.CARE:
            return
        self._activated = True
        case = self.day.case
        before = self.day.look
        steps_before = self.day.steps_done
        result = self.day.use_tool(tool)
        if result is None:
            return
        if not result.correct:
            self._try_again(tool_id(tool))
            self.timeline.after(DEMONSTRATE_AFTER, self._show_next_tool)
            self._dirty = True
            return
        now = self.clock()
        origin = self.controls.tile_center(tool) or PATIENT_HOME
        dest = to_screen(tool_target(case.species, case.ailment, tool, steps_before))
        self.motion.fly(ToolFlight(tool, now, origin, dest))
        self.motion.freeze_look(before, now + FLIGHT_SECONDS + WORK_SECONDS * 0.5)
        self.motion.tool_hop = None
        self.audio.play("whoosh")
        fx, sound = _TOOL_EFFECTS[tool]
        self.motion.add_fx(fx, dest, now + FLIGHT_SECONDS)
        if tool is Tool.STETHOSCOPE:
            self.motion.add_fx(fx, dest, now + FLIGHT_SECONDS + 0.35)
        self.timeline.after(FLIGHT_SECONDS, lambda: self.audio.play(sound))
        self.events.treatment_applied(result, level=self.day.level)
        self._busy = True
        self._sync()
        done = FLIGHT_SECONDS + WORK_SECONDS
        if result.healed:
            self.timeline.after(done, lambda: self._healed(result))
        else:
            self.timeline.after(done, self._step_done)
        self._dirty = True

    def _step_done(self) -> None:
        self.motion.hop_start = self.clock()
        self.cast.correct()
        self._end_busy()

    def _healed(self, result: CareResult) -> None:
        now = self.clock()
        self.motion.hop_start = now
        top = patient_rect().midtop
        self.motion.add_fx("star_burst", (top[0] - 120, top[1] + 90), now)
        self.motion.add_fx("heart_pop", (top[0] + 120, top[1] + 70), now + 0.25)
        self.audio.play("fanfare")
        self.audio.say("praise.general")
        self.cast.correct()
        self.saved = ClinicProgressState(self.saved.stars + 1, self.saved.level, self.saved.days)
        self.progress.save(self.saved)
        self.events.patient_healed(result, stars=self.saved.stars, level=self.day.level)
        self._sync()
        self.timeline.after(HEALED_HOLD_SECONDS, self._send_home)
        self._dirty = True

    def _send_home(self) -> None:
        self.motion.walk(PATIENT_HOME[0], PATIENT_OFFSTAGE_X, self.clock(), WALK_OUT_SECONDS)
        self.audio.play("hop")
        self.timeline.after(WALK_OUT_SECONDS + 0.15, self._next_patient)
        self._dirty = True

    def _next_patient(self) -> None:
        if self.day.next_patient():
            self._start_patient()
        else:
            self._complete_day()

    def _complete_day(self) -> None:
        summary = self.day.consume_completion()
        if summary is not None:
            next_level = adapt_level(self.day.level, self.day.mistakes)
            self.saved = ClinicProgressState(self.saved.stars, next_level, self.saved.days + 1)
            self.progress.save(self.saved)
            self.events.day_completed(summary)
        self.timeline.clear()
        self.audio.say("celebrate.success")
        self.completion.prepare(
            CompletionContent(
                title=self.resources.text("victory.title"),
                primary_label=self.resources.text("button.play_again"),
                body_lines=(self.resources.text("victory.subtitle"),),
                achievement_count=self.day.healed_count,
            )
        )
        self._surfaces.push_overlay(CompletionOverlay(self.completion, on_primary=self._restart))
        self._sync()
        self.state = AppState.TERMINAL
        self._dirty = True

    def _restart(self) -> None:
        self._activated = True
        level = self.saved.level
        self.day = ClinicDay(self.factory.build(level), level=level)
        self._surfaces.pop_overlay()
        self.completion.clear()
        self.state = AppState.PLAYING
        self.audio.say("ready.go")
        self._start_patient()

    # -- feedback and hints --------------------------------------------------------------

    def _try_again(self, control_id: str | None) -> None:
        now = self.clock()
        if control_id is not None:
            self.motion.wobble = (control_id, now)
        self.motion.shake_start = now
        self.cast.try_again()
        self.audio.play("nope")
        self.audio.say("encourage.retry")
        self._busy = True
        self._sync()
        self.timeline.after(REJECT_LOCK_SECONDS, self._end_busy)

    def _show_sore_place(self) -> None:
        """Demonstration after a wrong look: the sore place glows."""

        if self.day.phase is not Phase.FIND:
            return
        case = self.day.case
        self.motion.add_halo(to_screen(sore_anchor(case.species, case.ailment)), self.clock())
        self.motion.hop_start = self.clock()
        self.cast.point(2.0)
        self._dirty = True

    def _show_next_tool(self) -> None:
        """Demonstration after a wrong tool: the right tool hops in the tray."""

        expected = self.day.expected_tool
        if expected is None:
            return
        self.motion.tool_hop = (tool_id(expected), self.clock())
        center = self.controls.tile_center(expected)
        if center is not None:
            self.motion.add_halo(center, self.clock())
        self.cast.point(2.0)
        self._dirty = True

    def _maybe_hint(self, now: float) -> None:
        phase = self.day.phase
        if self._busy or self.timeline.busy or phase not in {Phase.FIND, Phase.CARE}:
            return
        patience = level_spec(self.day.level).idle_hint_seconds / IdleHintScheduler.DEFAULT_GAPS[0]
        step = self._hints.poll(now, self._last_activity, patience=patience)
        if not step:
            return
        self.cast.point(self._hints.animation_seconds(1.8))
        if step == 1:
            # First nudge: Momo points and the patient wiggles (no answer shown).
            self.motion.hop_start = now
        elif phase is Phase.FIND:
            self._show_sore_place()
        else:
            self._show_next_tool()
        self._dirty = True


def _safe_point(surface: pygame.Surface, position: tuple[int, int]) -> bool:
    """Reject Activity input in Greia's protected system-chrome regions."""

    viewport = activity_viewport_for_surface(surface)
    x, y = position
    if not (0 <= x < viewport.surface.width and 0 <= y < viewport.surface.height):
        return False
    return not any(
        region.x <= x < region.right and region.y <= y < region.bottom
        for region in viewport.protected_regions
    )


__all__ = ["AppState", "ClinicActivity", "Timeline"]
