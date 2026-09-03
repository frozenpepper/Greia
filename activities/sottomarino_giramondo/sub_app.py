"""Application Coordinator, Event Loop, and Lifecycle for Sottomarino Giramondo.

Binds model updates, audio cues, presentation rendering, and pointer/keyboard
interaction to the platform activity lifecycle. Publishes mark_activity_ready()
after the first successful presented frame.
"""

from __future__ import annotations

from pathlib import Path
import time
from typing import Optional

import pygame

from greia_platform.activity_api import (
    activity_stop_requested,
    emit_activity_event,
    get_profile_locale,
    get_storage,
    mark_activity_ready,
)
from greia_platform.localization import (
    ActivityLocaleSupport,
    LocalizedResources,
    resolve_activity_locale,
)
from greia_platform.pygame_canvas import (
    PygameReferenceCanvas,
    activity_viewport_for_surface,
)
from greia_platform.typography import GreiaTypography

if __package__:
    from .sub_art import (
        PORTHOLE_CENTER_X,
        PORTHOLE_CENTER_Y,
        PORTHOLE_RADIUS,
        SubmarineArt,
    )
    from .sub_audio import SubmarineAudio
    from .sub_cockpit_view import BUTTON_RECTS, CockpitPresenter
    from .sub_model import (
        REFERENCE_HEIGHT,
        REFERENCE_WIDTH,
        SubmarineModel,
    )
else:
    from sub_art import (
        PORTHOLE_CENTER_X,
        PORTHOLE_CENTER_Y,
        PORTHOLE_RADIUS,
        SubmarineArt,
    )
    from sub_audio import SubmarineAudio
    from sub_cockpit_view import BUTTON_RECTS, CockpitPresenter
    from sub_model import (
        REFERENCE_HEIGHT,
        REFERENCE_WIDTH,
        SubmarineModel,
    )


class SubmarineApp:
    """Main application lifecycle coordinator for Sottomarino Giramondo."""

    def __init__(self) -> None:
        screen = pygame.display.get_surface()
        if screen is None:
            pygame.init()
            screen = pygame.display.set_mode((REFERENCE_WIDTH, REFERENCE_HEIGHT), pygame.FULLSCREEN)
        self.screen = screen
        self.canvas = PygameReferenceCanvas(screen)
        # Ensure 24-bit depth without alpha channel so blitted masks and porthole render solidly
        self.canvas.surface = pygame.Surface((REFERENCE_WIDTH, REFERENCE_HEIGHT), 0, 24)

        self.model = SubmarineModel()
        self.art = SubmarineArt()
        self.audio = SubmarineAudio()
        self.typography = GreiaTypography()
        self.presenter = CockpitPresenter(self.art, self.typography)

        self._init_localization()
        self._ready_published = False
        self._clock = pygame.time.Clock()
        self._hot_button: Optional[str] = None
        self._last_encounter_type: str = "none"
        self._voice_queue: list[str] = []
        self._voice_cooldown: float = 0.0

    def _init_localization(self) -> None:
        pkg_root = Path(__file__).parent
        requested = get_profile_locale()
        support = ActivityLocaleSupport.localized(
            ("it", "en"),
            default_ui_locale="it",
        )
        context = resolve_activity_locale(requested, support)
        self.resources = LocalizedResources(pkg_root, context)

    def _speak_cue(self, cue_key: str) -> None:
        """Enqueue or safely speak a localized audio cue sequentially."""
        if not cue_key:
            return
        if cue_key not in self._voice_queue:
            self._voice_queue.append(cue_key)

    def _update_speech_queue(self, dt: float) -> None:
        """Process queued speech clips sequentially so sentences never speak over each other."""
        if self._voice_cooldown > 0:
            self._voice_cooldown -= dt
            return

        if self.audio.is_voice_busy():
            return

        if self._voice_queue:
            next_cue = self._voice_queue.pop(0)
            try:
                cue = self.resources.audio_cue(next_cue)
                if self.audio.play_voice(cue.path):
                    # Minimum pause after each sentence before next cue
                    self._voice_cooldown = 0.4
            except Exception:
                pass

    def _handle_button_press(self, btn_name: str) -> None:
        self.audio.play("click")

        # Check if this button action fulfills the Captain's order
        order_solved = False
        if btn_name in ("steer_left", "left"):
            self.model.steer(-1.0, 0.0)
            order_solved = self.model.check_action("left")
            emit_activity_event("submarine.maneuver", payload={"action": "steer_left"})
        elif btn_name in ("steer_right", "right"):
            self.model.steer(1.0, 0.0)
            order_solved = self.model.check_action("right")
            emit_activity_event("submarine.maneuver", payload={"action": "steer_right"})
        elif btn_name in ("ahead", "forward"):
            self.model.set_speed(0.8)
            self.audio.play("engine_shift")
            order_solved = self.model.check_action("ahead")
            emit_activity_event("submarine.maneuver", payload={"action": "ahead"})
        elif btn_name in ("stop", "halt"):
            self.model.set_speed(0.0)
            self.audio.play("engine_shift")
            order_solved = self.model.check_action("stop")
            emit_activity_event("submarine.maneuver", payload={"action": "stop"})
        elif btn_name == "light":
            self.model.toggle_lights()
            self.audio.play("light")
            self._speak_cue("voice.btn.light")
            order_solved = self.model.check_action("light")
            emit_activity_event("submarine.instrument_used", payload={"instrument": "light"})
        elif btn_name == "sonar":
            self.model.trigger_sonar()
            self.audio.play("sonar")
            self._speak_cue("voice.btn.sonar")
            order_solved = self.model.check_action("sonar")
            emit_activity_event("submarine.instrument_used", payload={"instrument": "sonar"})
        elif btn_name == "bubbles":
            self.model.trigger_bubbles()
            self.audio.play("bubbles")
            self._speak_cue("voice.btn.bubbles")
            order_solved = self.model.check_action("bubbles")
            emit_activity_event("submarine.instrument_used", payload={"instrument": "bubbles"})
        elif btn_name == "horn":
            self.model.trigger_horn()
            self.audio.play("horn")
            self._speak_cue("voice.btn.horn")
            order_solved = self.model.check_action("horn")
            if self.model.resolve_encounter():
                self.audio.play("celebrate")
                self._speak_cue("voice.encounter.solved")
                emit_activity_event("submarine.encounter_resolved", payload={"creature": "encounter"})
            emit_activity_event("submarine.instrument_used", payload={"instrument": "horn"})
        elif btn_name == "action":
            if self.model.resolve_encounter():
                self.audio.play("celebrate")
                self._speak_cue("voice.encounter.solved")
                emit_activity_event("submarine.encounter_resolved", payload={"creature": "encounter"})
            else:
                self.audio.play("alert")
                self._speak_cue("voice.btn.action")

        if order_solved:
            self.audio.play("celebrate")
            self._speak_cue("voice.order.compliment")
            emit_activity_event("submarine.order_completed", payload={"order": self.model.current_order.order_id})

    def run(self) -> int:
        running = True
        last_time = time.monotonic()

        while running and not activity_stop_requested():
            now = time.monotonic()
            dt = min(0.1, max(0.001, now - last_time))
            last_time = now

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                    break
                elif event.type == pygame.KEYDOWN:
                    if event.key in (pygame.K_ESCAPE, pygame.K_q):
                        running = False
                        break
                    elif event.key == pygame.K_UP:
                        self._handle_button_press("ahead")
                    elif event.key == pygame.K_DOWN:
                        self._handle_button_press("stop")
                    elif event.key == pygame.K_LEFT:
                        self._handle_button_press("steer_left")
                    elif event.key == pygame.K_RIGHT:
                        self._handle_button_press("steer_right")
                    elif event.key == pygame.K_SPACE:
                        self._handle_button_press("action")
                    elif event.key == pygame.K_l:
                        self._handle_button_press("light")
                    elif event.key == pygame.K_s:
                        self._handle_button_press("sonar")
                    elif event.key == pygame.K_b:
                        self._handle_button_press("bubbles")
                    elif event.key == pygame.K_h:
                        self._handle_button_press("horn")

                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    pt = self.canvas.pointer(event.pos)
                    if pt is not None:
                        clicked_btn = False
                        for name, rect in BUTTON_RECTS.items():
                            if rect.collidepoint(pt[0], pt[1]):
                                self._handle_button_press(name)
                                clicked_btn = True
                                break

                        # Direct click/tap on Ship Rudder Wheel (cx=135, cy=235, radius=72)
                        if not clicked_btn and (pt[0] - 135)**2 + (pt[1] - 235)**2 <= 72**2:
                            self._dragging_wheel = True
                            if pt[0] < 135:
                                self._handle_button_press("steer_left")
                            else:
                                self._handle_button_press("steer_right")
                            clicked_btn = True

                        # Direct click/tap on Throttle Lever (tcx=890, tcy=215, box w=90, h=150)
                        if not clicked_btn and (845 <= pt[0] <= 935 and 140 <= pt[1] <= 290):
                            self._dragging_lever = True
                            if pt[1] < 215:
                                self._handle_button_press("ahead")
                            else:
                                self._handle_button_press("stop")
                            clicked_btn = True

                        # Tap inside porthole generates bubbles at tap location
                        if not clicked_btn and (pt[0] - PORTHOLE_CENTER_X)**2 + (pt[1] - PORTHOLE_CENTER_Y)**2 <= PORTHOLE_RADIUS**2:
                            self.model.trigger_bubbles()
                            self.audio.play("bubbles")

                elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                    self._dragging_wheel = False
                    self._dragging_lever = False

                elif event.type == pygame.MOUSEMOTION:
                    pt = self.canvas.pointer(event.pos)
                    self._hot_button = None
                    if pt is not None:
                        for name, rect in BUTTON_RECTS.items():
                            if rect.collidepoint(pt[0], pt[1]):
                                self._hot_button = name
                                break

                        # Dragging rudder wheel
                        if getattr(self, "_dragging_wheel", False):
                            # Steer relative to wheel center (cx=135)
                            dx = (pt[0] - 135) / 60.0
                            self.model.heading = max(-1.0, min(1.0, dx))
                            if dx < -0.3:
                                self.model.check_action("left")
                            elif dx > 0.3:
                                self.model.check_action("right")

                        # Dragging throttle lever
                        if getattr(self, "_dragging_lever", False):
                            # Speed based on lever Y position (top = 1.0 ahead, bottom = 0.0 stop)
                            # Box goes from y=150 to y=270
                            frac = 1.0 - max(0.0, min(1.0, (pt[1] - 150) / 120.0))
                            self.model.set_speed(frac)
                            if frac > 0.4:
                                self.model.check_action("ahead")
                            elif frac <= 0.2:
                                self.model.check_action("stop")

            # Advance model state
            discovered, completed_ev = self.model.update(dt)
            for d in discovered:
                self._speak_cue(f"voice.creature.{d}")
                # Also speak an educational fact about this species
                if self.model.active_fact.cue_key:
                    self._speak_cue(self.model.active_fact.cue_key)
                emit_activity_event("submarine.creature_discovered", payload={"creature": d})

            # Check if a new Captain order has arrived
            ord_state = self.model.current_order
            if ord_state.active and not ord_state.solved and ord_state.timer == 0.0:
                # First frame of new order
                if not hasattr(self, "_last_order_id") or self._last_order_id != ord_state.order_id:
                    self._last_order_id = ord_state.order_id
                    if ord_state.cue_key:
                        self._speak_cue(ord_state.cue_key)

            # Check if a new encounter has just appeared
            curr_enc = self.model.encounter.active_type.value
            if curr_enc != self._last_encounter_type:
                if curr_enc == "octopus_hug":
                    self._speak_cue("voice.encounter.octopus")
                elif curr_enc == "shark_wave":
                    self._speak_cue("voice.encounter.shark")
                self._last_encounter_type = curr_enc

            if completed_ev:
                emit_activity_event(completed_ev)

            # Update voice speech queue sequentially
            self._update_speech_queue(dt)

            # Render frame
            self.canvas.surface.fill((0, 0, 0))
            self.presenter.render(self.canvas.surface, self.model, self.resources, self._hot_button)
            self.canvas.present()
            pygame.display.flip()

            # Lifecycle READY declaration on first usable frame
            if not self._ready_published:
                mark_activity_ready()
                self._ready_published = True

            self._clock.tick(30)

        return 0
