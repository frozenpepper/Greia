"""Application coordinator, event loop and lifecycle for Sottomarino Giramondo.

Binds the model, Captain Leo, voice cues, the cockpit presenter and the
shared control kit (focus, pointer/touch, keyboard and controller) to the
platform Activity lifecycle. Publishes ``mark_activity_ready()`` after the
first presented frame.

Free play comes first: steering, lights, sonar, bubbles, horn, alarm and
diving through three zones. Captain Leo's spoken orders are optional
invitations (hint after ~6 s, never failed, fade when ignored); three
followed orders earn a star.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
import random
import time
from typing import Any, Optional

import pygame

from greia_platform.activity_api import (
    activity_stop_requested,
    emit_activity_event,
    get_profile_locale,
    mark_activity_ready,
)
from greia_platform.activity_controls import (
    ControlKit,
    ControlLayout,
    ControlTheme,
    KitPointer,
    PointerPhase,
    PygameControlInput,
)
from greia_platform.input_core import InputEdge, InteractionProfile, PhysicalControl, SemanticAction, SemanticInputEvent
from greia_platform.localization import (
    ActivityLocaleSupport,
    LocalizationError,
    LocalizedResources,
    resolve_activity_locale,
)
from greia_platform.pygame_canvas import (
    PygameReferenceCanvas,
    activity_viewport_for_surface,
)
from greia_platform.pygame_input import PygameInputTranslator
from greia_platform.typography import GreiaTypography
from greia_platform.ui_core import SurfaceNavigator, UiEventResult
from greia_platform.frame_governor import FrameGovernor, FrameKind

if __package__:
    from .sub_art import PORTHOLE_CENTER_X, PORTHOLE_CENTER_Y, PORTHOLE_RADIUS, SubmarineArt
    from .sub_audio import SpeechPriority, SpeechQueue, SubmarineAudio
    from .sub_cast import SubmarineCaptain
    from .sub_cockpit_view import (
        BUTTON_RECTS,
        CAPTAIN_HEIGHT,
        CAPTAIN_MIDBOTTOM,
        DASHBOARD_TOP,
        LEVER_HIT_RECT,
        LEVER_TRAVEL,
        WHEEL_CENTER,
        WHEEL_HIT_RADIUS,
        CockpitPresenter,
        in_porthole,
        project,
    )
    from .sub_controls import BannerContent, SubmarineControls
    from .sub_model import (
        ENCOUNTER_HELPERS,
        REFERENCE_HEIGHT,
        REFERENCE_WIDTH,
        EncounterType,
        OrderState,
        SubmarineModel,
    )
    from .sub_services import SubmarineProgressStore
else:
    from sub_art import PORTHOLE_CENTER_X, PORTHOLE_CENTER_Y, PORTHOLE_RADIUS, SubmarineArt
    from sub_audio import SpeechPriority, SpeechQueue, SubmarineAudio
    from sub_cast import SubmarineCaptain
    from sub_cockpit_view import (
        BUTTON_RECTS,
        CAPTAIN_HEIGHT,
        CAPTAIN_MIDBOTTOM,
        DASHBOARD_TOP,
        LEVER_HIT_RECT,
        LEVER_TRAVEL,
        WHEEL_CENTER,
        WHEEL_HIT_RADIUS,
        CockpitPresenter,
        in_porthole,
        project,
    )
    from sub_controls import BannerContent, SubmarineControls
    from sub_model import (
        ENCOUNTER_HELPERS,
        REFERENCE_HEIGHT,
        REFERENCE_WIDTH,
        EncounterType,
        OrderState,
        SubmarineModel,
    )
    from sub_services import SubmarineProgressStore

# Letter shortcuts kept from the original cockpit.
_KEY_BUTTONS = {
    pygame.K_w: "ahead",
    pygame.K_x: "stop",
    pygame.K_l: "light",
    pygame.K_s: "sonar",
    pygame.K_b: "bubbles",
    pygame.K_h: "horn",
}
# Direct piloting (game-style "directional" control, as before the kit pass).
_PILOT_BUTTONS = {
    SemanticAction.NAV_LEFT: "steer_left",
    SemanticAction.NAV_RIGHT: "steer_right",
    SemanticAction.NAV_UP: "surface",
    SemanticAction.NAV_DOWN: "dive",
    SemanticAction.MOVE_LEFT: "steer_left",
    SemanticAction.MOVE_RIGHT: "steer_right",
    SemanticAction.MOVE_UP: "surface",
    SemanticAction.MOVE_DOWN: "dive",
}
# Controller shoulders walk the cockpit focus ring (keyboard: Tab / Shift+Tab).
_SHOULDER_STEPS = {
    PhysicalControl.CONTROLLER_LEFT_SHOULDER: -1,
    PhysicalControl.CONTROLLER_RIGHT_SHOULDER: +1,
}
_CONTROLLER_BUTTON_DOWN = getattr(pygame, "CONTROLLERBUTTONDOWN", -1)
_ENCOUNTER_CUES = {
    EncounterType.OCTOPUS_HUG: ("voice.encounter.octopus", "octopus"),
    EncounterType.SHARK_WAVE: ("voice.encounter.shark", "shark"),
}
# Kinds whose recorded name uses the older underscore cue id.
_UNDERSCORE_NAME_CUES = frozenset({"coral", "kelp", "krill"})
CONTROL_ACCENT = "ocean"
SAVE_INTERVAL_SECONDS = 10.0
KEY_HINT_START_SECONDS = 8.0  # keyboard hint shown at start (ADR 0037 §4b)
_MAX_FX = 6


class _Effect:
    """One shared ``fx.*`` flipbook playing at a point (bounded list)."""

    def __init__(self, frames: list[pygame.Surface], center: tuple[int, int], duration: float = 0.6) -> None:
        self.frames = frames
        self.center = center
        self.duration = duration
        self.age = 0.0

    @property
    def done(self) -> bool:
        return self.age >= self.duration or not self.frames

    def draw(self, surface: pygame.Surface) -> None:
        if self.done:
            return
        index = min(len(self.frames) - 1, int(self.age / self.duration * len(self.frames)))
        frame = self.frames[index]
        surface.blit(frame, frame.get_rect(center=self.center))


class SubmarineApp:
    """Main application lifecycle coordinator for Sottomarino Giramondo."""

    def __init__(
        self,
        *,
        rng: Optional[random.Random] = None,
        clock: Callable[[], float] = time.monotonic,
        store: Optional[SubmarineProgressStore] = None,
    ) -> None:
        screen = pygame.display.get_surface()
        if screen is None:
            pygame.init()
            screen = pygame.display.set_mode((REFERENCE_WIDTH, REFERENCE_HEIGHT), pygame.NOFRAME)
        self.screen = screen
        self.canvas = PygameReferenceCanvas(screen, hires=True)
        # Opaque (no alpha channel) so colour-keyed layers blit solidly, in the
        # display's own format: a 24-bit canvas forced SDL's slowest blit and
        # conversion paths (~65 ms a frame on the Atom reference floor).
        canvas_surface = pygame.Surface((REFERENCE_WIDTH, REFERENCE_HEIGHT), 0, 32)
        self.canvas.surface = canvas_surface.convert() if pygame.display.get_surface() is not None else canvas_surface
        self._clock = clock

        self.store = store if store is not None else SubmarineProgressStore()
        self.model = SubmarineModel(rng=rng, log=self.store.load())
        self.art = SubmarineArt()
        self.audio = SubmarineAudio()
        self.typography = GreiaTypography()
        self.presenter = CockpitPresenter(self.art, self.typography)
        self._init_localization()

        self.kit = ControlKit(self.typography, ControlTheme.for_accent(CONTROL_ACCENT))
        self.controls = SubmarineControls(
            self.kit,
            ControlLayout.for_canvas(self.canvas, screen.get_size()),
            on_button=self.press,
            on_porthole=self._porthole_action,
            on_replay=self._replay,
            clock=clock,
        )
        # Keyboard hint (arrows + Space) under the pilot cluster: shown at start.
        self.controls.keys.show(KEY_HINT_START_SECONDS)
        self._keys_changed = True
        self._seen_order_hint: Optional[str] = None
        self._surfaces = SurfaceNavigator(self.controls.layer)
        self._input = self._make_input()
        # Physical shoulder buttons only (translated by the platform; no device access).
        self._physical = PygameInputTranslator(InteractionProfile.NAVIGATION)
        self.captain = SubmarineCaptain(self.kit.art, height=CAPTAIN_HEIGHT, clock=clock)
        self.speech = SpeechQueue()
        self._effects: list[_Effect] = []

        self._running = True
        self._ready_published = False
        self._frame_clock = pygame.time.Clock()
        self._dragging_wheel = False
        self._dragging_lever = False
        self._seen_order: Optional[OrderState] = None
        self._seen_encounter = EncounterType.NONE
        self._seen_fact_serial = 0
        self._dirty = False
        self._last_save = clock()
        self._sync_controls()

    # ------------------------------------------------------------------
    # Localization and voice
    # ------------------------------------------------------------------

    def _init_localization(self) -> None:
        pkg_root = Path(__file__).parent
        support = ActivityLocaleSupport.localized(("it", "en", "es", "fr"), default_ui_locale="it")
        context = resolve_activity_locale(get_profile_locale(), support)
        self.resources = LocalizedResources(pkg_root, context)

    def _text(self, key: str) -> str:
        try:
            return self.resources.text(key).strip()
        except LocalizationError:
            return ""

    def _speak_now(self, cue_key: str) -> bool:
        try:
            path = self.resources.audio_path(cue_key)
        except (LocalizationError, ValueError):
            return False
        return path is not None and self.audio.play_voice(path)

    def _speak_cue(self, cue_key: str, priority: SpeechPriority = SpeechPriority.NORMAL, *, force: bool = False) -> None:
        self.speech.push(cue_key, priority, force=force)

    @staticmethod
    def creature_cue(kind: str) -> str:
        return f"voice.creature_{kind}" if kind in _UNDERSCORE_NAME_CUES else f"voice.creature.{kind}"

    # ------------------------------------------------------------------
    # Pointer safety
    # ------------------------------------------------------------------

    def _is_safe(self, physical: tuple[int, int]) -> bool:
        viewport = activity_viewport_for_surface(self.screen)
        x, y = physical
        if not (0 <= x < viewport.surface.width and 0 <= y < viewport.surface.height):
            return False
        return not any(r.x <= x < r.right and r.y <= y < r.bottom for r in viewport.protected_regions)

    def _safe_pointer(self, physical: tuple[int, int]) -> tuple[float, float] | None:
        """Physical point -> logical cockpit point, or None (outside / Home/Back)."""

        if not self._is_safe(physical):
            return None
        return self.canvas.pointer(physical)

    def _make_input(self) -> PygameControlInput:
        return PygameControlInput(to_logical=self.canvas.pointer, is_safe=self._is_safe)

    # ------------------------------------------------------------------
    # Instruments
    # ------------------------------------------------------------------

    def press(self, btn_name: str) -> None:
        """One cockpit control press (tap, focus + Space/south, or shortcut)."""

        self.audio.play("click")
        order_followed = False
        if btn_name == "dive":
            self.model.change_depth(+1)
            emit_activity_event("submarine.instrument_used", payload={"instrument": "dive"})
        elif btn_name == "surface":
            self.model.change_depth(-1)
            emit_activity_event("submarine.instrument_used", payload={"instrument": "surface"})
        elif btn_name in ("steer_left", "left"):
            self.model.steer(-1.0, 0.0)
            order_followed = self.model.check_action("left")
        elif btn_name in ("steer_right", "right"):
            self.model.steer(1.0, 0.0)
            order_followed = self.model.check_action("right")
        elif btn_name in ("ahead", "forward"):
            self.model.set_speed(0.8)
            self.audio.play("engine_shift")
            order_followed = self.model.check_action("ahead")
        elif btn_name in ("stop", "halt"):
            self.model.set_speed(0.0)
            self.audio.play("engine_shift")
            order_followed = self.model.check_action("stop")
        elif btn_name == "light":
            self.model.toggle_lights()
            self.audio.play("light")
            order_followed = self.model.check_action("light")
            if not order_followed:
                self._speak_cue("voice.btn.light")
            if self.model.encounter.active_type == EncounterType.SHARK_WAVE:
                self._resolve_encounter("shark")
            emit_activity_event("submarine.instrument_used", payload={"instrument": "light"})
        elif btn_name == "sonar":
            self.model.trigger_sonar()
            self.audio.play("sonar")
            order_followed = self.model.check_action("sonar")
            if not order_followed:
                self._speak_cue("voice.btn.sonar")
            emit_activity_event("submarine.instrument_used", payload={"instrument": "sonar"})
        elif btn_name == "bubbles":
            self.model.trigger_bubbles()
            self.audio.play("bubbles")
            order_followed = self.model.check_action("bubbles")
            if not order_followed:
                self._speak_cue("voice.btn.bubbles")
            if self.model.encounter.active_type == EncounterType.OCTOPUS_HUG:
                self._resolve_encounter("octopus")
            emit_activity_event("submarine.instrument_used", payload={"instrument": "bubbles"})
        elif btn_name == "horn":
            self.audio.play("horn")
            order_followed = self.model.check_action("horn")
            if not order_followed:
                self._speak_cue("voice.btn.horn")
            # The friendly horn greets either visitor (as it always did).
            self._resolve_encounter(_ENCOUNTER_CUES.get(self.model.encounter.active_type, ("", "encounter"))[1])
            emit_activity_event("submarine.instrument_used", payload={"instrument": "horn"})
        elif btn_name in ("action", "alarm"):
            order_followed = self.model.check_action("horn")
            if not self._resolve_encounter("encounter"):
                self.audio.play("alert")
                if not order_followed:
                    self._speak_cue("voice.btn.alarm")
            emit_activity_event("submarine.instrument_used", payload={"instrument": "alarm"})

        if order_followed:
            self._order_followed(btn_name)
        else:
            self.model.note_other_instrument()

    # Compatibility name used by older tools/tests.
    _handle_button_press = press

    def _resolve_encounter(self, creature: str) -> bool:
        if not self.model.resolve_encounter():
            return False
        self.audio.play("celebrate")
        self.speech.drop(SpeechPriority.NORMAL)
        self._speak_cue("voice.encounter.solved", SpeechPriority.URGENT, force=True)
        self.captain.cheer()
        self._add_fx("heart_pop", (PORTHOLE_CENTER_X, PORTHOLE_CENTER_Y), 150)
        emit_activity_event("submarine.encounter_resolved", payload={"creature": creature})
        return True

    def _order_followed(self, btn_name: str) -> None:
        order_id = self.model.current_order.order_id
        self.audio.play("celebrate")
        self.speech.drop(SpeechPriority.NORMAL)
        self._speak_cue("voice.order.compliment", SpeechPriority.URGENT, force=True)
        self.captain.cheer()
        rect = BUTTON_RECTS.get(btn_name)
        if rect is not None:
            self._add_fx("sparkle", rect.center, 110)
        emit_activity_event("submarine.order_completed", payload={"order": order_id})
        if self.model.record_order_followed():
            self._add_fx("star_burst", self.controls.stars.rect.center, 150)
            self._add_fx("star_burst", (PORTHOLE_CENTER_X, PORTHOLE_CENTER_Y), 220)
            self._dirty = True
            self._save()
        self._sync_controls()

    def _check_order_state(self, action: str) -> None:
        """Drag gestures follow orders through the sub's state."""

        if self.model.check_action(action):
            self._order_followed("steer_left" if action == "left" else "steer_right" if action == "right" else action)

    def _porthole_action(self) -> None:
        """Keyboard/controller press on the glass: bubbles + name the nearest creature."""

        self._tap_porthole((PORTHOLE_CENTER_X, PORTHOLE_CENTER_Y), nearest=True)

    def _tap_porthole(self, point: tuple[float, float], *, nearest: bool = False) -> None:
        dx = (point[0] - PORTHOLE_CENTER_X) / PORTHOLE_RADIUS
        dy = (point[1] - PORTHOLE_CENTER_Y) / PORTHOLE_RADIUS
        self.model.trigger_bubbles(at=(dx, dy))
        self.audio.play("bubbles")
        self._add_fx("bubble_pop", (int(point[0]), int(point[1])), 90)
        kind = self.presenter.creature_at(point)
        if kind is None and nearest:
            kind = self._nearest_creature()
        if self.model.encounter.active_type == EncounterType.OCTOPUS_HUG:
            self._resolve_encounter("octopus")
        elif kind is not None and self.model.trigger_species_fact(kind):
            self._seen_fact_serial = self.model.active_fact.serial
            self._speak_cue(self.creature_cue(kind), SpeechPriority.NORMAL, force=True)
            if self.model.active_fact.cue_key:
                self._speak_cue(self.model.active_fact.cue_key, SpeechPriority.LOW, force=True)
                self.captain.talk(6.0)

    def _nearest_creature(self) -> Optional[str]:
        best: Optional[tuple[float, str]] = None
        for ent in self.model.entities:
            if ent.kind == "bubble":
                continue
            sx, sy, _scale = project(ent)
            if not in_porthole((sx, sy), margin=10):
                continue
            score = ent.z + abs(sx - PORTHOLE_CENTER_X) / 600.0
            if best is None or score < best[0]:
                best = (score, ent.kind)
        return best[1] if best is not None else None

    def _replay(self) -> None:
        """Replay what the banner is about (order, visitor or creature)."""

        model = self.model
        if model.encounter_waiting():
            cue = _ENCOUNTER_CUES[model.encounter.active_type][0]
        elif model.current_order.active:
            cue = model.current_order.cue_key if model.current_order.waiting else "voice.order.compliment"
        elif model.active_fact.display_timer > 0:
            cue = model.active_fact.cue_key or self.creature_cue(model.active_fact.species)
        else:
            return
        self.audio.stop_voice()
        self.speech.clear()
        self._speak_cue(cue, SpeechPriority.URGENT, force=True)

    # ------------------------------------------------------------------
    # Effects
    # ------------------------------------------------------------------

    def _add_fx(self, fx_id: str, center: tuple[int, int], size: int) -> None:
        frames = self.art.fx_frames(fx_id, size)
        if not frames:
            return
        self._effects.append(_Effect(frames, center))
        del self._effects[:-_MAX_FX]

    # ------------------------------------------------------------------
    # Event routing
    # ------------------------------------------------------------------

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.QUIT:
            self._running = False
            return
        if self.controls.keys.observe_event(event):
            self._keys_changed = True
        if event.type in (pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP, pygame.MOUSEMOTION) and getattr(event, "touch", False):
            # SDL mirrors touch as synthetic mouse input; the FINGER* event is used.
            return
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self._running = False
                return
            if event.key == pygame.K_TAB:
                backwards = bool(getattr(event, "mod", 0) & pygame.KMOD_SHIFT)
                self.controls.cycle_focus(-1 if backwards else +1)
                return
            button = _KEY_BUTTONS.get(event.key)
            if button is not None:
                self.press(button)
                return
        elif event.type == _CONTROLLER_BUTTON_DOWN:
            physical = self._physical.physical_digital(event)
            step = _SHOULDER_STEPS.get(physical[0]) if physical is not None else None
            if step is not None:
                self.controls.cycle_focus(step)
                return
        elif event.type == pygame.WINDOWFOCUSLOST:
            self._end_drags()
            return
        elif event.type == pygame.VIDEORESIZE:
            self._handle_resize()
            return
        elif event.type in (pygame.FINGERDOWN, pygame.FINGERUP, pygame.FINGERMOTION):
            width, height = self.screen.get_size()
            phase = {
                pygame.FINGERDOWN: PointerPhase.DOWN,
                pygame.FINGERUP: PointerPhase.UP,
                pygame.FINGERMOTION: PointerPhase.MOVE,
            }[event.type]
            self.pointer(phase, (int(event.x * width), int(event.y * height)))
            return
        translated = self._input.translate(event)
        if translated is not None:
            self._route(translated)

    def _handle_resize(self) -> None:
        new_screen = pygame.display.get_surface()
        if new_screen is None:
            return
        self.screen = new_screen
        surface = self.canvas.surface
        self.canvas = PygameReferenceCanvas(new_screen, hires=True)
        self.canvas.surface = surface
        self._input = self._make_input()
        self.controls.relayout(ControlLayout.for_canvas(self.canvas, new_screen.get_size()))
        self._end_drags()

    def pointer(self, phase: PointerPhase, position: tuple[int, int]) -> None:
        """Deliver one physical pointer/touch sample."""

        logical = self._safe_pointer(position)
        if logical is None:
            if phase in (PointerPhase.UP, PointerPhase.CANCEL):
                self._route(KitPointer(PointerPhase.CANCEL, (-1, -1)))
            elif phase is PointerPhase.MOVE:
                self._end_drags()
            return
        self._route(KitPointer(phase, (int(logical[0]), int(logical[1]))))

    def tap(self, position: tuple[int, int]) -> None:
        """One complete tap at a physical position (touch, tools, tests)."""

        self.pointer(PointerPhase.DOWN, position)
        self.pointer(PointerPhase.UP, position)

    def _route(self, kit_input: Any) -> None:
        if isinstance(kit_input, SemanticInputEvent) and self._pilot(kit_input):
            return
        if isinstance(kit_input, KitPointer):
            if kit_input.phase in (PointerPhase.UP, PointerPhase.CANCEL):
                self._end_drags()
            elif kit_input.phase is PointerPhase.MOVE and (self._dragging_wheel or self._dragging_lever):
                self._drag(kit_input.position)
                return
        result = self._surfaces.dispatch(kit_input)
        if result is UiEventResult.IGNORED and isinstance(kit_input, KitPointer) and kit_input.phase is PointerPhase.DOWN:
            point = kit_input.position
            if self.controls.blocks_play(point):
                return
            self.controls.layer.focus_visible = False
            self._pointer_down(point)

    def _pilot(self, event: SemanticInputEvent) -> bool:
        """Game-style piloting: arrows / D-pad / left stick fly the sub directly.

        Left/right steer, up surfaces, down dives (held stick repeats through
        the platform's repeat policy). Space / Enter / south press the alarm,
        unless Tab or a shoulder button has shown the cockpit focus ring, in
        which case they press the focused control (handled by the kit layer).
        """

        if event.edge is not InputEdge.PRESSED:
            return False
        button = _PILOT_BUTTONS.get(event.action)
        if button is not None:
            self.press(button)
            return True
        if event.action in (SemanticAction.ACTIVATE, SemanticAction.PRIMARY) and not self.controls.layer.focus_visible:
            self.press("action")
            return True
        return False

    def _pointer_down(self, point: tuple[int, int]) -> None:
        x, y = point
        wx, wy = WHEEL_CENTER
        if (x - wx) ** 2 + (y - wy) ** 2 <= WHEEL_HIT_RADIUS ** 2:
            self._dragging_wheel = True
            self.press("steer_left" if x < wx else "steer_right")
        elif LEVER_HIT_RECT.collidepoint(point):
            self._dragging_lever = True
            self.press("ahead" if y < LEVER_HIT_RECT.centery else "stop")
        elif in_porthole(point):
            self._tap_porthole(point)

    def _drag(self, point: tuple[int, int]) -> None:
        if self._dragging_wheel:
            dx = (point[0] - WHEEL_CENTER[0]) / 60.0
            self.model.heading = max(-1.0, min(1.0, dx))
            if dx < -0.3:
                self._check_order_state("left")
            elif dx > 0.3:
                self._check_order_state("right")
        if self._dragging_lever:
            # Top of the slot = full ahead, bottom = stop.
            frac = 1.0 - max(0.0, min(1.0, (point[1] - (LEVER_HIT_RECT.top + 10)) / LEVER_TRAVEL))
            self.model.set_speed(frac)
            if frac > 0.4:
                self._check_order_state("ahead")
            elif frac <= 0.2:
                self._check_order_state("stop")

    def _end_drags(self) -> None:
        self._dragging_wheel = False
        self._dragging_lever = False

    # ------------------------------------------------------------------
    # Frame
    # ------------------------------------------------------------------

    def advance(self, dt: float) -> None:
        """Simulate one frame: stick repeat, model, voice, Leo, banner, autosave."""

        repeat = self._input.poll()
        if repeat is not None:
            self._route(repeat)
        model = self.model
        discovered, _completed = model.update(dt)
        for kind in discovered:
            self._speak_cue(self.creature_cue(kind), SpeechPriority.NORMAL)
            emit_activity_event("submarine.creature_discovered", payload={"creature": kind})
            self._dirty = True

        fact = model.active_fact
        if fact.serial != self._seen_fact_serial:
            self._seen_fact_serial = fact.serial
            if fact.cue_key:
                self._speak_cue(fact.cue_key, SpeechPriority.LOW)
                self.captain.talk(6.0)

        order = model.current_order
        if order.active and order is not self._seen_order:
            self._seen_order = order
            self._speak_cue(order.cue_key, SpeechPriority.URGENT)
        if model.encounter.active_type != self._seen_encounter:
            self._seen_encounter = model.encounter.active_type
            cue = _ENCOUNTER_CUES.get(self._seen_encounter)
            if cue is not None:
                self.audio.play("alert")
                self._speak_cue(cue[0], SpeechPriority.URGENT)

        # Captain Leo's order hint (~6 s idle) also shows which keys fly the sub.
        hinted_order = order.order_id if order.waiting and order.hinted else None
        if hinted_order is not None and hinted_order != self._seen_order_hint:
            self.controls.keys.demonstrate()
            self._keys_changed = True
        self._seen_order_hint = hinted_order
        if self.controls.keys.update():
            self._keys_changed = True
        self.captain.present(order.waiting or model.encounter_waiting(), pointing=order.waiting and order.hinted)
        self.captain.update(dt)
        self.speech.update(dt, self.audio.is_voice_busy(), self._speak_now)
        for effect in self._effects:
            effect.age += dt
        self._effects = [effect for effect in self._effects if not effect.done]
        self._sync_controls()

        now = self._clock()
        if self._dirty and now - self._last_save >= SAVE_INTERVAL_SECONDS:
            self._save()

    def banner_key(self) -> Optional[tuple]:
        """Identity of what the banner should show (cheap, every frame)."""

        model = self.model
        if model.encounter_waiting():
            return ("encounter", model.encounter.active_type.value)
        order = model.current_order
        if order.active:
            if order.solved:
                return ("order_done", order.order_id)
            return ("order_hint" if order.hinted else "order", order.order_id)
        fact = model.active_fact
        if fact.display_timer > 0 and fact.species:
            return ("creature", fact.species, fact.serial)
        return None

    def banner_content(self) -> Optional[BannerContent]:
        """What the prompt banner should say right now (built on change only)."""

        model = self.model
        art = self.art
        if model.encounter_waiting():
            enc = model.encounter.active_type
            creature = _ENCOUNTER_CUES[enc][1]
            badges = [art.instrument_badge(name, 34) for name in (*ENCOUNTER_HELPERS[enc], "action")]
            icon = art.picture_row([art.picture(creature, 40), *badges])
            return BannerContent(("encounter", enc.value), self._text("hud.encounter"), icon)
        order = model.current_order
        if order.active:
            if order.solved:
                return BannerContent(("order_done", order.order_id), self._text("hud.order_done"), self.kit.glyph("check", 36))
            if order.hinted:
                return BannerContent(
                    ("order_hint", order.order_id),
                    self._text(f"btn.{order.target}"),
                    art.picture_row([self.kit.glyph("listen", 34), art.instrument_badge(order.target, 36)]),
                )
            return BannerContent(("order", order.order_id), self._text("hud.order"), self.kit.glyph("listen", 36))
        fact = model.active_fact
        if fact.display_timer > 0 and fact.species:
            return BannerContent(
                ("creature", fact.species, fact.serial),
                self._text(f"creature.{fact.species}"),
                art.picture(fact.species, 42),
            )
        return None

    def _sync_controls(self) -> None:
        if self.banner_key() != self.controls.banner_key:
            self.controls.show_banner(self.banner_content())
        self.controls.set_progress(self.model.log.stars, self.model.orders_in_set)

    def draw(self) -> None:
        surface = self.canvas.surface
        layer = self.controls.layer
        hot = layer.hovered_id if layer.hovered_id in BUTTON_RECTS else None
        pressed = layer.pressed_id if layer.pressed_id in BUTTON_RECTS else None
        self.presenter.render(surface, self.model, self.resources, hot, pressed_button=pressed)
        # Leo rises from behind the console edge.
        surface.set_clip(pygame.Rect(0, 0, REFERENCE_WIDTH, DASHBOARD_TOP + 4))
        self.captain.draw(surface, CAPTAIN_MIDBOTTOM)
        surface.set_clip(None)
        for effect in self._effects:
            effect.draw(surface)
        self.controls.draw(surface)
        self.canvas.present()

    def _save(self) -> None:
        self._last_save = self._clock()
        self._dirty = False
        self.store.save(self.model.log)

    def run(self) -> int:
        # Input redraws at full rate; the sea and Leo are ambient, presented
        # at a reduced rate once the child has been idle.
        frames = FrameGovernor(redraw_on_input=True)
        last_time = time.monotonic()
        while self._running and not activity_stop_requested():
            now = time.monotonic()
            dt = min(0.1, max(0.001, now - last_time))
            last_time = now
            for event in frames.events():
                self.handle_event(event)
                if not self._running:
                    break
            if not self._running:
                break
            self.advance(dt)
            key_deadline = self.controls.keys.deadline()
            if key_deadline is not None:
                frames.wake_at(key_deadline)
            frame = frames.frame(dirty=self._keys_changed, ambient=True)
            self._keys_changed = False
            if frame is FrameKind.FULL:
                self.draw()
                pygame.display.flip()
                if not self._ready_published:
                    mark_activity_ready()
                    self._ready_published = True
            elif frame is FrameKind.POINTER:
                self.canvas.present_pointer()
            frames.wait()
        self.audio.stop_voice()
        if self._dirty:
            self._save()
        return 0
