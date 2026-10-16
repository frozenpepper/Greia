"""Lifecycle owner for My Greia.

Composes the model, the customization port, shared control kit, art,
live Home preview, audio and renderer; routes pointer/keyboard/controller
input through the kit; persists every choice immediately through the
platform services; and publishes READY after the first presented frame.
Redraw is event-driven (dirty flag) with a short animation window for the
friend's cheer and the sparkle burst.
"""

from __future__ import annotations

from collections.abc import Callable
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
from greia_platform.input_core import InputEdge, SemanticAction, SemanticInputEvent
from greia_platform.localization import LocalizationError, LocalizedResources
from greia_platform.pygame_canvas import PygameReferenceCanvas, activity_viewport_for_surface
from greia_platform.ui_core import SurfaceNavigator, UiEventResult

if not __package__:
    __package__ = "activities.workshop_settings"  # type: ignore[assignment]

try:
    from .workshop_art import MyGreiaArt
    from .workshop_audio import MyGreiaAudio
    from .workshop_content import HOME_PORTALS, TABS, Tab
    from .workshop_controls import MyGreiaControls
    from .workshop_model import ChoiceKind, MyGreiaModel, Transition
    from .workshop_preview import HomePreview, greeter_for
    from .workshop_renderer import MyGreiaRenderer
    from .workshop_services import CustomizationPort
except ImportError:
    from workshop_art import MyGreiaArt  # type: ignore[no-redef]
    from workshop_audio import MyGreiaAudio  # type: ignore[no-redef]
    from workshop_content import HOME_PORTALS, TABS, Tab  # type: ignore[no-redef]
    from workshop_controls import MyGreiaControls  # type: ignore[no-redef]
    from workshop_model import ChoiceKind, MyGreiaModel, Transition  # type: ignore[no-redef]
    from workshop_preview import HomePreview, greeter_for  # type: ignore[no-redef]
    from workshop_renderer import MyGreiaRenderer  # type: ignore[no-redef]
    from workshop_services import CustomizationPort  # type: ignore[no-redef]


def _safe_point(surface: pygame.Surface, position: tuple[int, int]) -> bool:
    viewport = activity_viewport_for_surface(surface)
    x, y = position
    if not (0 <= x < viewport.surface.width and 0 <= y < viewport.surface.height):
        return False
    for protected in viewport.protected_regions:
        if protected.x <= x < protected.right and protected.y <= y < protected.bottom:
            return False
    return True


class MyGreiaApp:
    """Coordinate My Greia: choices in, saved look + live Home preview out."""

    def __init__(
        self,
        *,
        screen: pygame.Surface,
        canvas: PygameReferenceCanvas,
        typography,
        resources: LocalizedResources,
        services: CustomizationPort,
        audio: MyGreiaAudio | None = None,
        clock: Callable[[], float] = time.monotonic,
        kit: ControlKit | None = None,
        art: MyGreiaArt | None = None,
    ) -> None:
        self.screen = screen
        self.canvas = canvas
        self.typography = typography
        self.resources = resources
        self.services = services
        self.clock = clock
        state = services.load()
        self.choices = state.choices
        self.text_color = state.text_color
        self.custom_path = state.custom_wallpaper
        self.model = MyGreiaModel(state.look, custom_available=state.custom_wallpaper is not None)
        self.kit = kit if kit is not None else ControlKit(typography, self._control_theme())
        self.art = art if art is not None else MyGreiaArt(self.kit, typography)
        self.audio = audio if audio is not None else MyGreiaAudio(resources, clock=clock)
        self.preview = HomePreview(self.kit, self.art, typography, self._home_labels(), clock=clock)
        self.controls = MyGreiaControls(
            self.kit,
            self.art,
            ControlLayout.for_canvas(canvas, screen.get_size()),
            self.choices,
            on_tab=self._on_tab,
            on_choice=self._on_choice,
            on_undo=self._on_undo,
        )
        self.controls.custom_path = self.custom_path
        self.controls.show(self.model.tab, self.model.look, custom=self.model.custom_available)
        self.renderer = MyGreiaRenderer(self.kit, self.art, self.preview, self.controls)
        self._surfaces = SurfaceNavigator(self.controls.layer)
        self._input = PygameControlInput(to_logical=canvas.pointer, is_safe=lambda pos: _safe_point(self.screen, pos))
        self._running = True
        self._ready_published = False
        self._dirty = True
        self._activated = False
        self.last_feedback: str | None = None

    # -- composition helpers ------------------------------------------------------

    def _control_theme(self) -> ControlTheme:
        return ControlTheme(accent=self.choices.accent(self.model.look.accent), text=self.text_color)

    def _home_labels(self) -> dict[str, str]:
        labels: dict[str, str] = {}
        for collection, _hue, _icon, _box in HOME_PORTALS:
            try:
                labels[collection] = self.resources.text(f"home.{collection}")
            except LocalizationError:
                labels[collection] = ""
        return labels

    # -- main loop ------------------------------------------------------------------

    def run(self) -> int:
        frames = FrameGovernor()
        self.audio.welcome()
        try:
            while self._running and not activity_stop_requested():
                for event in frames.events():
                    self._handle_event(event)
                repeat = self._input.poll()
                if repeat is not None:
                    self._dispatch(repeat)
                animating = self.step()
                frame = frames.frame(dirty=self._dirty, animating=animating)
                if frame is FrameKind.FULL:
                    self.render()
                    self.present()
                    pygame.display.flip()
                    self._dirty = False
                    if not self._ready_published:
                        # READY means a usable child frame is on screen.
                        mark_activity_ready()
                        self._ready_published = True
                elif frame is FrameKind.POINTER:
                    self.canvas.present_pointer()
                frames.wait(polling=self._input.repeating)
        finally:
            self.audio.stop_speech()
            self.typography.clear()
        return 0

    def step(self) -> bool:
        if self.preview.update(self.model.look):
            self._dirty = True
        if self.controls.layer.invalidation.should_draw:
            self._dirty = True
        return self.preview.animating

    def render(self) -> None:
        self.renderer.draw(self.canvas.surface, self.model, self.choices, custom=self.custom_path)

    def present(self) -> None:
        """Show the reference canvas; bars (if any) take the room colour."""

        room = self.choices.background(self.model.look.background)
        self.canvas.present(clear=room, smooth=True)

    # -- input ----------------------------------------------------------------------

    def _handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.QUIT:
            self._running = False
            return
        if event.type == pygame.VIDEORESIZE:
            self.resize(pygame.display.get_surface() or self.screen)
            return
        if event.type == pygame.KEYDOWN and event.key == pygame.K_TAB:
            step = -1 if event.mod & pygame.KMOD_SHIFT else 1
            self._on_tab(self._neighbour_tab(step), from_keyboard=True)
            return
        if event.type == pygame.MOUSEMOTION:
            self._dirty = True  # the Greia pointer is drawn with each frame
        translated = self._input.translate(event)
        if translated is not None:
            self._dispatch(translated)

    def resize(self, screen: pygame.Surface) -> None:
        self.screen = screen
        self.canvas = PygameReferenceCanvas(self.screen)
        self._input = PygameControlInput(to_logical=self.canvas.pointer, is_safe=lambda pos: _safe_point(self.screen, pos))
        self.controls.relayout(ControlLayout.for_canvas(self.canvas, self.screen.get_size()))
        self._dirty = True

    def _dispatch(self, kit_input) -> bool:
        if (
            isinstance(kit_input, SemanticInputEvent)
            and kit_input.edge is InputEdge.PRESSED
            and kit_input.action is SemanticAction.CANCEL
        ):
            self._on_cancel()
            return True
        result = self._surfaces.dispatch(kit_input)
        if self.controls.layer.invalidation.should_draw:
            self._dirty = True
        return result is not UiEventResult.IGNORED

    def _on_cancel(self) -> None:
        """Back out of the choices to the tabs; from the tabs, leave."""

        if self.controls.focus_in_tiles():
            self.controls.focus_current_tab()
            self._dirty = True
        else:
            self._running = False

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

    def tap_control(self, control_id: str) -> bool:
        """Tap the centre of a kit control (tests/tools; physical == logical at 1024x600)."""

        rect = self.controls.layer.target(control_id).rect
        transform = self.canvas.mapper.transform
        x, y = transform.logical_to_physical((rect.centerx, rect.centery))
        return self.tap((int(round(x)), int(round(y))))

    def press(self, key: int) -> bool:
        """Deliver one key press (tests/tools)."""

        self._activated = False
        event = pygame.event.Event(pygame.KEYDOWN, key=key, mod=0, unicode="")
        self._handle_event(event)
        return self._activated

    # -- choices --------------------------------------------------------------------

    def _neighbour_tab(self, step: int) -> Tab:
        index = TABS.index(self.model.tab)
        return TABS[(index + step) % len(TABS)]

    def _on_tab(self, tab: Tab, *, from_keyboard: bool = False) -> None:
        self._activated = True
        if self.model.set_tab(tab):
            self.controls.show(tab, self.model.look, custom=self.model.custom_available)
            self.audio.play("tab")
        if from_keyboard:
            self.controls.focus_current_tab()
        self._dirty = True

    def _on_choice(self, kind: ChoiceKind, value: str) -> None:
        self._activated = True
        transition = self.model.propose(kind, value)
        if transition is None:
            # Already chosen: the friend still waves back.
            self.preview.celebrate(self.model.look, (kind,))
            self.audio.play("pick")
            self.last_feedback = "same"
            self._dirty = True
            return
        self._apply(transition, undo=False)

    def _on_undo(self) -> None:
        self._activated = True
        transition = self.model.propose_undo()
        if transition is None:
            return
        self._apply(transition, undo=True)

    def _apply(self, transition: Transition, *, undo: bool) -> None:
        applied = self.services.apply(transition.before, transition.after)
        if undo:
            self.model.commit_undo(applied)
        else:
            self.model.commit(transition, applied)
        look = self.model.look
        changed = look.changed_kinds(transition.before)
        if not changed:
            # The platform refused (e.g. storage full): gentle think, no loss.
            self.preview.think(look)
            self.last_feedback = "refused"
            self._dirty = True
            return
        if ChoiceKind.ACCENT in changed:
            self.kit.painter.set_theme(self._control_theme())
        if self.custom_path is not None and not self.model.custom_available:
            self.custom_path = None
            self.controls.custom_path = None
            if self.model.tab is Tab.PICTURES:
                self.controls.show(Tab.PICTURES, look, custom=False, keep_focus=True)
        self.controls.sync(look, can_undo=self.model.can_undo)
        self.preview.celebrate(look, changed)
        self.audio.play("undo" if undo else "pick")
        self.audio.react(greeter_for(look.avatar), avatar_changed=ChoiceKind.AVATAR in changed)
        self.last_feedback = "undo" if undo else "changed"
        self._dirty = True


__all__ = ["MyGreiaApp"]
