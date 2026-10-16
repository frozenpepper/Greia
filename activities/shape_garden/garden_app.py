"""Lifecycle owner for Shape Garden: input routing, library and Creations.

The child drags named shapes from the tray onto a big garden (or taps a tile
to plant one), then moves, resizes, turns, recolours and layers them over a
backdrop of their choice. An optional ghost picture shows faint slots a
matching shape snaps into. There is no right or wrong: Dani points at the
tray when the garden is empty, cheers when a ghost picture is complete or a
picture is shared, and otherwise just watches.

Rules live in ``GardenEditor``; presentation in ``GardenRenderer``; every
button, pot, tile and placed shape is a shared-kit control or target
(ADR 0037), so mouse, touch, keyboard (arrows + Space/Enter; Space on a
shape picks it up, arrows carry it, Space puts it down) and controller
(D-pad focus, left-stick Greia virtual pointer, south button to drag) all
work. Gardens autosave privately; only a deliberate share publishes a
flattened 1024x600 PNG to My Creations, and a child's PNG from My Creations
can become the backdrop.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import math
import time

import pygame

from greia_platform.activity_api import (
    activity_stop_requested,
    emit_activity_event,
    get_theme,
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
from greia_platform.activity_feedback import CastFeedback, CastPose
from greia_platform.activity_ui import ChildUiMetrics, draw_activity_pointer
from greia_platform.frame_governor import FrameGovernor, FrameKind
from greia_platform.input_core import InputEdge, SemanticAction, SemanticInputEvent
from greia_platform.pygame_canvas import PygameReferenceCanvas, activity_viewport_for_surface
from greia_platform.pygame_png import PygamePngError, encode_surface_png
from greia_platform.typography import GreiaTypography
from greia_platform.ui_core import SurfaceNavigator

if __package__:
    from .garden_audio import GardenSounds
    from .garden_content import (
        AUTOSAVE_IDLE_SECONDS,
        BACKDROP_IDS,
        CREATION_PICKER_POLL_SECONDS,
        DANI_HEIGHT,
        DEFAULT_COLOUR,
        FEEDBACK_SECONDS,
        GALLERY_PAGE_SIZE,
        GARDEN_HEIGHT,
        GARDEN_WIDTH,
        GHOST_PICTURES,
        IDLE_HINT_SECONDS,
        LIBRARY_FULL_SECONDS,
        PICTURE_BACKDROP,
        REFERENCE_HEIGHT,
        REFERENCE_WIDTH,
        SHAPE_KINDS,
        SIZE_LEVELS,
        GhostPicture,
    )
    from .garden_controls import GardenControls, GardenSheets, shape_target_id
    from .garden_input import ControllerPointer
    from .garden_model import GardenEditor, GardenState
    from .garden_project_model import GardenProject
    from .garden_project_repository import GardenProjectError, GardenProjectRepository, GardenRecord
    from .garden_renderer import FxBurst, GardenRenderer, decode_picture
else:  # pragma: no cover - direct script fallback
    from garden_audio import GardenSounds
    from garden_content import (
        AUTOSAVE_IDLE_SECONDS,
        BACKDROP_IDS,
        CREATION_PICKER_POLL_SECONDS,
        DANI_HEIGHT,
        DEFAULT_COLOUR,
        FEEDBACK_SECONDS,
        GALLERY_PAGE_SIZE,
        GARDEN_HEIGHT,
        GARDEN_WIDTH,
        GHOST_PICTURES,
        IDLE_HINT_SECONDS,
        LIBRARY_FULL_SECONDS,
        PICTURE_BACKDROP,
        REFERENCE_HEIGHT,
        REFERENCE_WIDTH,
        SHAPE_KINDS,
        SIZE_LEVELS,
        GhostPicture,
    )
    from garden_controls import GardenControls, GardenSheets, shape_target_id
    from garden_input import ControllerPointer
    from garden_model import GardenEditor, GardenState
    from garden_project_model import GardenProject
    from garden_project_repository import GardenProjectError, GardenProjectRepository, GardenRecord
    from garden_renderer import FxBurst, GardenRenderer, decode_picture

DRAG_SLOP = 8
CARRY_STEP = 24
PRAISE_AT = 5
_NAV = {
    SemanticAction.NAV_LEFT: (-1, 0),
    SemanticAction.NAV_RIGHT: (1, 0),
    SemanticAction.NAV_UP: (0, -1),
    SemanticAction.NAV_DOWN: (0, 1),
    SemanticAction.MOVE_LEFT: (-1, 0),
    SemanticAction.MOVE_RIGHT: (1, 0),
    SemanticAction.MOVE_UP: (0, -1),
    SemanticAction.MOVE_DOWN: (0, 1),
}


def _safe_point(surface: pygame.Surface, position: tuple[int, int]) -> bool:
    viewport = activity_viewport_for_surface(surface)
    x, y = position
    if not (0 <= x < viewport.surface.width and 0 <= y < viewport.surface.height):
        return False
    return not any(
        region.x <= x < region.right and region.y <= y < region.bottom
        for region in viewport.protected_regions
    )


class GardenCast:
    """Dani with the shared feedback grammar plus a pointing invitation pose.

    ``CastFeedback`` owns cheer and think; this wrapper adds ``point`` (the
    wordless "try the tray!" cue), drawn only while the friend is idle.
    """

    def __init__(self, feedback: CastFeedback | None, point: pygame.Surface | None, clock) -> None:
        self.feedback = feedback
        self._point = point
        self._clock = clock
        self._point_until = 0.0

    @property
    def pointing(self) -> bool:
        return self._point is not None and self._clock() < self._point_until

    @property
    def pose(self) -> str:
        if self.feedback is not None and self.feedback.pose is not CastPose.IDLE:
            return self.feedback.pose.value
        return "point" if self.pointing else "idle"

    def point(self, seconds: float = 2.4) -> None:
        self._point_until = self._clock() + seconds

    def correct(self) -> None:
        self._point_until = 0.0
        if self.feedback is not None:
            self.feedback.correct()

    def try_again(self) -> None:
        self._point_until = 0.0
        if self.feedback is not None:
            self.feedback.try_again()

    def update(self) -> None:
        if self.feedback is not None:
            self.feedback.update()

    def draw(self, target: pygame.Surface, midbottom: tuple[int, int]) -> None:
        if self.pointing and (self.feedback is None or self.feedback.pose is CastPose.IDLE):
            target.blit(self._point, self._point.get_rect(midbottom=midbottom))  # type: ignore[union-attr]
        elif self.feedback is not None:
            self.feedback.draw(target, midbottom)


@dataclass(slots=True)
class _Press:
    """One pointer press in progress (tray tile or garden shape)."""

    kind: str  # "tray" | "shape" | "grass" | "kit"
    start: tuple[int, int]
    index: int = -1
    offset: tuple[float, float] = (0.0, 0.0)
    moved: bool = False


class GardenApp:
    """Coordinate Shape Garden lifecycle without owning rules or rendering."""

    IMPORT_POLL_SECONDS = CREATION_PICKER_POLL_SECONDS

    def __init__(
        self,
        screen: pygame.Surface | None = None,
        *,
        repository: GardenProjectRepository | None = None,
        creations=None,
        locale: str = "en",
        kit: ControlKit | None = None,
        sounds: GardenSounds | None = None,
        clock=time.monotonic,
    ) -> None:
        pygame.init()
        if screen is None:
            screen = pygame.display.get_surface()
            if screen is None:
                screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
        # The platform pointer is drawn by ``PygameReferenceCanvas.present``.
        pygame.mouse.set_visible(False)
        self.screen = screen
        self.theme = get_theme()
        self.metrics = ChildUiMetrics.for_size(*self.screen.get_size())
        self.canvas = PygameReferenceCanvas(self.screen)
        self.repository = repository
        self.creations = creations
        self._clock = clock
        self.clock = pygame.time.Clock()
        self.running = True
        # Create Collection hue (coral) as the kit accent, like Painting.
        self.kit = kit if kit is not None else ControlKit(GreiaTypography(), ControlTheme.for_accent("coral"))
        self.renderer = GardenRenderer(self.kit)
        self.layout = ControlLayout.for_canvas(self.canvas, self.screen.get_size())
        self.renderer.set_top_bar(self._top_bar())
        self.sounds = sounds if sounds is not None else GardenSounds(locale)
        try:
            feedback: CastFeedback | None = CastFeedback("dani", height=DANI_HEIGHT, art=self.kit.art, clock=clock)
        except ValueError:
            feedback = None
        self.cast = GardenCast(feedback, self.kit.art.image("character.dani", DANI_HEIGHT, variant="pose_point"), clock)

        self.editor = GardenEditor()
        self.colour = DEFAULT_COLOUR
        self.current_id: str | None = None
        self.records: list[GardenRecord] = []
        self.mode = "garden"
        self.dirty = False
        self.save_error = False
        self.last_change = 0.0
        self.picture_surface: pygame.Surface | None = None
        self._saved_picture: str | None = None
        self._pictures: dict[str, pygame.Surface] = {}
        self.gallery_focus = 0
        self.library_full_until = 0.0
        self.pending_delete: str | None = None
        self.carrying = False
        self._press: _Press | None = None
        self._new_drag: str | None = None
        self._drag_point: tuple[int, int] | None = None
        self._fx: list[FxBurst] = []
        self._backdrop_icon: tuple[tuple | None, pygame.Surface | None] = (None, None)
        self._ghost_celebrated = False
        self._praised = False
        now = clock()
        self._last_activity = now
        self._hints = 0
        self._intro_done = False
        self._tray_hint_start = -10.0
        self._slot_hint_start = -10.0
        self._last_frame = now

        self.import_request: str | None = None
        self.import_next_poll = 0.0
        self.import_state = ""
        self.import_feedback_until = 0.0
        self.publish_state = ""
        self.publish_feedback_until = 0.0
        self._last_published_digest: str | None = None

        self.controller_pointer = ControllerPointer(lambda: self.screen.get_size(), lambda: self._view_centre_physical())
        self.controls = GardenControls(
            self.kit,
            self.renderer,
            on_gallery=self._toggle_gallery,
            on_undo=self._undo,
            on_share=self._publish_project,
            on_backdrop=self._open_backdrop_sheet,
            on_ghost=self._open_ghost_sheet,
            on_new=self._press_new,
            on_colour=self._choose_colour,
            on_tool=self._use_tool,
            on_tray=self._tray_activate,
            on_bin=self._bin_selected,
            on_shape=self._shape_activate,
            on_card=self._open_index,
            on_card_delete=self._ask_delete_index,
            on_page=self._gallery_page_step,
            on_delete_focused=self._ask_delete_focused,
        )
        self.controls.relayout()
        self.sheets = GardenSheets(self.kit, self.renderer)
        self.surfaces = SurfaceNavigator(self.controls.layer)
        self._input = PygameControlInput(to_logical=self.canvas.pointer, is_safe=lambda pos: _safe_point(self.screen, pos))
        self._load_library()
        self._refresh_tray()
        self._sync()
        self.controls.layer.focus("tray.circle", visible=False)

    # -- geometry helpers ----------------------------------------------------------

    def _top_bar(self) -> pygame.Rect:
        height = self.layout.control_height(64, maximum=72)
        return self.layout.top_bar(height)

    def _view_centre_physical(self) -> tuple[int, int]:
        transform = self.canvas.mapper.transform
        x, y = transform.logical_to_physical(self.renderer.view.center)
        return int(x), int(y)

    def _logical(self, physical: tuple[int, int]) -> tuple[int, int] | None:
        logical = self.canvas.pointer(physical)
        if logical is None:
            return None
        return int(round(logical[0])), int(round(logical[1]))

    @property
    def state(self) -> GardenState:
        return self.editor.state

    # -- library --------------------------------------------------------------------

    def _load_library(self) -> None:
        if self.repository is None:
            return
        try:
            self.records = self.repository.list_records()
        except (GardenProjectError, RuntimeError, ValueError):
            self.records = []
            self.save_error = True
        if self.records:
            self._open(self.records[0], save_first=False)

    def _open(self, record: GardenRecord, *, save_first: bool = True) -> bool:
        if self.repository is None or (save_first and not self._save()):
            return False
        try:
            project = self.repository.load(record.garden_id)
        except (GardenProjectError, RuntimeError, ValueError):
            self.save_error = True
            return False
        self.current_id = record.garden_id
        self.editor.load(project.state, project.ghost)
        self.picture_surface = self._picture(project.state.picture)
        self._saved_picture = project.state.picture
        if project.state.backdrop == PICTURE_BACKDROP and self.picture_surface is None:
            # The picture could not be read: show paper rather than nothing.
            self.editor.state = GardenState(project.state.shapes, "paper", project.state.picture)
        self.mode = "garden"
        self.dirty = False
        self.carrying = False
        self._ghost_celebrated = self.editor.ghost_complete()
        self._praised = len(self.editor.shapes) >= PRAISE_AT
        self.renderer.invalidate_garden()
        self._sync()
        return True

    def _picture(self, digest: str | None) -> pygame.Surface | None:
        if digest is None or self.repository is None:
            return None
        if digest in self._pictures:
            return self._pictures[digest]
        try:
            surface = decode_picture(self.repository.load_picture(digest))
        except (GardenProjectError, PygamePngError, RuntimeError, ValueError, OSError):
            return None
        if len(self._pictures) >= 2:
            self._pictures.pop(next(iter(self._pictures)))
        self._pictures[digest] = surface
        return surface

    def _save(self) -> bool:
        if not self.dirty:
            return True
        if self.editor.dragging:
            return True  # the drop will mark the garden dirty again
        if self.repository is None:
            self.dirty = False
            return True
        if self.current_id is None and self.state.blank:
            self.dirty = False  # never persist an empty garden
            return True
        project = GardenProject(self.state, self.editor.ghost)
        try:
            if self.current_id is None:
                record = self.repository.create(project)
                self.current_id = record.garden_id
            else:
                record = self.repository.save(self.current_id, project)
        except (GardenProjectError, RuntimeError, ValueError, OSError):
            self.save_error = True
            return False
        self.records = [record, *[r for r in self.records if r.garden_id != record.garden_id]]
        self.renderer.invalidate_thumbnail(record.garden_id)
        self.dirty = False
        self.save_error = False
        if self.state.picture != self._saved_picture:
            self._saved_picture = self.state.picture
            try:
                self.repository.reclaim_pictures(self.records, keep=self.state.picture)
            except (GardenProjectError, RuntimeError):
                pass
        return True

    # -- lifecycle ---------------------------------------------------------------------

    def run(self) -> int:
        ready = False
        # Input and drags redraw; Dani's hints and the tray wave are ambient.
        frames = FrameGovernor(redraw_on_input=True)
        try:
            while self.running and not activity_stop_requested():
                for event in frames.events():
                    self.handle_event(event)
                repeat = self._input.poll()
                if repeat is not None and not self.controller_pointer.active:
                    self._semantic(repeat)
                moved = self._step_frame()
                frame = frames.frame(
                    dirty=moved or self.controls.layer.invalidation.should_draw,
                    animating=bool(self._fx) or self.editor.dragging,
                    ambient=True,
                )
                if frame is FrameKind.FULL or (frame is FrameKind.POINTER and self.controller_pointer.active):
                    self._draw()
                    pygame.display.flip()
                    if not ready:
                        mark_activity_ready()
                        ready = True
                elif frame is FrameKind.POINTER:
                    self.canvas.present_pointer()
                frames.wait(polling=self.controller_pointer.active or self._input.repeating)
        finally:
            if self.editor.dragging:
                self.editor.end_drag()
            self._save()
            self.surfaces.close()
        return 0

    def handle_event(self, event: pygame.event.Event) -> None:
        """Route one Pygame event (pointer, keyboard, controller, window)."""
        if event.type == pygame.QUIT:
            self._save()
            self.running = False
            return
        if event.type == pygame.VIDEORESIZE:
            self._resize()
            return
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self._escape()
            return
        if event.type == pygame.MOUSEBUTTONDOWN and getattr(event, "button", 1) == 1:
            self.controller_pointer.deactivate()
            self.pointer_down(event.pos)
            return
        if event.type == pygame.MOUSEMOTION:
            self.controller_pointer.deactivate()
            self.pointer_motion(event.pos)
            return
        if event.type == pygame.MOUSEBUTTONUP and getattr(event, "button", 1) == 1:
            self.pointer_up(event.pos)
            return
        if self.controller_pointer.handle(event, on_down=self.pointer_down, on_up=self.pointer_up):
            if self.controller_pointer.active:
                self.controls.layer.focus_visible = False
            return
        translated = self._input.translate(event)
        if translated is not None and not isinstance(translated, KitPointer):
            self.controller_pointer.deactivate()
            self._semantic(translated)

    def _resize(self) -> None:
        self.screen = pygame.display.get_surface() or self.screen
        self.metrics = ChildUiMetrics.for_size(*self.screen.get_size())
        self.canvas = PygameReferenceCanvas(self.screen)
        self.layout = ControlLayout.for_canvas(self.canvas, self.screen.get_size())
        self.renderer.set_top_bar(self._top_bar())
        self.controls.relayout()
        self.controller_pointer.reset()
        self._input = PygameControlInput(to_logical=self.canvas.pointer, is_safe=lambda pos: _safe_point(self.screen, pos))

    def _escape(self) -> None:
        if self.surfaces.overlays:
            self._close_sheet()
        elif self.carrying:
            self._put_down()
        elif self.mode == "gallery":
            self._toggle_gallery()
        elif self._save():
            self.running = False

    def _note_activity(self) -> None:
        self._last_activity = self._clock()
        self._hints = 0
        self._tray_hint_start = -10.0
        self._slot_hint_start = -10.0

    # -- keyboard / controller ------------------------------------------------------------

    def _semantic(self, event) -> None:
        self._note_activity()
        if (
            self.carrying
            and isinstance(event, SemanticInputEvent)
            and event.edge is InputEdge.PRESSED
            and not self.surfaces.overlays
        ):
            step = _NAV.get(event.action)
            if step is not None:
                shape = self.editor.selected_shape
                if shape is not None:
                    self.editor.drag_to((shape.x + step[0] * CARRY_STEP, shape.y + step[1] * CARRY_STEP))
                    self._sync(focus_shape=True)  # the focus ring travels with it
                return
            if event.action in {SemanticAction.ACTIVATE, SemanticAction.PRIMARY, SemanticAction.CANCEL}:
                self._put_down()
                return
        self.surfaces.dispatch(event)

    def _shape_activate(self, index: int) -> None:
        """Space/Enter/south on a focused shape: pick it up (arrows carry it)."""
        if self.carrying:
            self._put_down()
            return
        if not 0 <= index < len(self.editor.shapes):
            return
        self.editor.begin_drag(index)
        self.carrying = True
        self.sounds.play("tick")
        self._sync(focus_shape=True)

    def _put_down(self) -> None:
        self.carrying = False
        slot = self.editor.end_drag()
        self._after_drop(slot)
        self._sync(focus_shape=True)

    # -- pointer ----------------------------------------------------------------------------

    def pointer_down(self, physical: tuple[int, int]) -> None:
        if not _safe_point(self.screen, physical):
            return
        point = self._logical(physical)
        if point is None:
            return
        self._note_activity()
        if self.carrying:
            self._put_down()
        if self.surfaces.overlays or self.mode != "garden":
            self._press = _Press("kit", point)
            self.surfaces.dispatch(KitPointer(PointerPhase.DOWN, point))
            return
        tray = self._tray_index_at(point)
        if tray is not None and self.controls.tray[tray].enabled:
            self._press = _Press("tray", point, tray)
            self.surfaces.dispatch(KitPointer(PointerPhase.DOWN, point))
            return
        if self.renderer.view.collidepoint(point):
            index = self.renderer.hit_shape(self.editor.shapes, point)
            if index is None:
                # Empty grass: let go of the selection (never a kit tap, so a
                # near miss cannot pick up a neighbouring shape).
                self.editor.select(None)
                self._press = _Press("grass", point)
                self._sync()
                return
            shape = self.editor.shapes[index]
            garden = self.renderer.to_garden(point)
            self.editor.select(index)
            self._press = _Press("shape", point, index, (shape.x - garden[0], shape.y - garden[1]))
            self.controls.layer.focus(shape_target_id(index), visible=False)
            self._sync()
            return
        self._press = _Press("kit", point)
        self.surfaces.dispatch(KitPointer(PointerPhase.DOWN, point))

    def pointer_motion(self, physical: tuple[int, int]) -> None:
        point = self._logical(physical)
        press = self._press
        if press is None or point is None:
            if point is not None and _safe_point(self.screen, physical):
                self.surfaces.dispatch(KitPointer(PointerPhase.MOVE, point))
            return
        if not press.moved and math.hypot(point[0] - press.start[0], point[1] - press.start[1]) > DRAG_SLOP:
            press.moved = True
            if press.kind == "tray":
                self.surfaces.dispatch(KitPointer(PointerPhase.CANCEL, (-1, -1)))
                self._new_drag = SHAPE_KINDS[press.index]
                self.sounds.play("tick")
            elif press.kind == "shape":
                self.editor.begin_drag(press.index)
        if not press.moved:
            return
        self._drag_point = point
        if press.kind == "shape" and self.editor.dragging:
            garden = self.renderer.to_garden(point)
            self.editor.drag_to((garden[0] + press.offset[0], garden[1] + press.offset[1]))
        elif press.kind == "kit":
            self.surfaces.dispatch(KitPointer(PointerPhase.MOVE, point))

    def pointer_up(self, physical: tuple[int, int]) -> bool:
        press, self._press = self._press, None
        point = self._logical(physical) if _safe_point(self.screen, physical) else None
        drag_point, self._drag_point = self._drag_point, None
        if press is not None and press.kind == "grass":
            return True
        if press is not None and press.kind == "tray" and self._new_drag is not None:
            kind, self._new_drag = self._new_drag, None
            if point is not None and self.renderer.view.collidepoint(point):
                self._plant(kind, self.renderer.to_garden(point))
            return True
        if press is not None and press.kind == "shape":
            if self.editor.dragging:
                target = point or drag_point
                if target is not None and self._is_bin_drop(target):
                    if self.editor.cancel_drag_into_bin():
                        self._removed(target)
                else:
                    self._after_drop(self.editor.end_drag())
                self._sync()
            return True
        if point is None:
            self.surfaces.dispatch(KitPointer(PointerPhase.CANCEL, (-1, -1)))
            return True
        if press is None:
            # A lone release (tools/tests) is a full tap on whatever is there.
            self.surfaces.dispatch(KitPointer(PointerPhase.DOWN, point))
        self.surfaces.dispatch(KitPointer(PointerPhase.UP, point))
        return True

    def tap(self, physical: tuple[int, int]) -> None:
        """Deliver one complete tap at a physical position (tests/tools)."""
        self.pointer_down(physical)
        self.pointer_up(physical)

    def drag(self, start: tuple[int, int], end: tuple[int, int], steps: int = 6) -> None:
        """Deliver one complete pointer drag (tests/tools)."""
        self.pointer_down(start)
        for step in range(1, steps + 1):
            t = step / steps
            self.pointer_motion((int(start[0] + (end[0] - start[0]) * t), int(start[1] + (end[1] - start[1]) * t)))
        self.pointer_up(end)

    def _tray_index_at(self, point: tuple[int, int]) -> int | None:
        for index, rect in enumerate(self.renderer.tray_tiles()):
            if rect.collidepoint(point):
                return index
        return None

    def _is_bin_drop(self, point: tuple[int, int]) -> bool:
        return self.renderer.bin_rect().inflate(16, 16).collidepoint(point) or self.renderer.tray_rect().collidepoint(point)

    # -- garden actions -----------------------------------------------------------------------

    def _tray_activate(self, index: int) -> None:
        """Tap (or Space on) a tray tile: plant that shape in a free spot."""
        keyboard = self.controls.layer.focus_visible
        planted = self._plant(SHAPE_KINDS[index], self.editor.free_spot())
        if planted and keyboard and self.editor.selected is not None:
            # Keyboard/controller: the new shape is picked up straight away so
            # arrows carry it and Space puts it down.
            self.editor.begin_drag(self.editor.selected)
            self.carrying = True
            self._sync(focus_shape=True)

    def _plant(self, kind: str, garden_point: tuple[float, float]) -> bool:
        if self.mode != "garden":
            return False
        result = self.editor.plant(kind, self.colour, garden_point)
        if result is False:
            self.cast.try_again()
            self.sounds.play("tick")
            return False
        shape = self.editor.selected_shape
        self.sounds.pop(kind)
        if shape is not None:
            centre = self.renderer.to_screen((shape.x, shape.y))
            if result is not True:
                self._snapped(centre)
            else:
                self._burst("fx.sparkle", centre, 90)
        self._changed()
        return True

    def _after_drop(self, slot) -> None:
        shape = self.editor.selected_shape
        if slot is not None and shape is not None:
            self._snapped(self.renderer.to_screen((shape.x, shape.y)))
        elif shape is not None:
            self.sounds.pop(shape.kind)
        self._changed()

    def _snapped(self, centre: tuple[int, int]) -> None:
        self.sounds.play("snap")
        self._burst("fx.star_burst", centre, 120)

    def _removed(self, centre: tuple[int, int]) -> None:
        self.sounds.play("swish")
        self._burst("fx.dust_puff", centre, 110)
        self._changed()

    def _bin_selected(self) -> None:
        shape = self.editor.selected_shape
        if shape is None:
            return
        centre = self.renderer.to_screen((shape.x, shape.y))
        self.carrying = False
        if self.editor.dragging:
            if self.editor.cancel_drag_into_bin():
                self._removed(centre)
        elif self.editor.remove_selected():
            self._removed(centre)

    def _use_tool(self, name: str) -> None:
        if self.carrying:
            self._put_down()
        changed = {
            "grow": lambda: self.editor.resize(1),
            "shrink": lambda: self.editor.resize(-1),
            "turn": self.editor.rotate,
            "back": self.editor.send_back,
        }[name]()
        if changed:
            shape = self.editor.selected_shape
            if shape is not None:
                self.sounds.pop(shape.kind)
            self._changed()

    def _choose_colour(self, colour: str) -> None:
        self.colour = colour
        if self.carrying:
            self._put_down()
        recoloured = self.editor.recolour(colour)
        self.sounds.play("tick")
        self._refresh_tray()
        if recoloured:
            self._changed()
        else:
            self._sync()

    def _undo(self) -> None:
        self.carrying = False
        if self.editor.undo():
            self.picture_surface = self._picture(self.state.picture)
            self.sounds.play("swish")
            self._changed()

    def _changed(self) -> None:
        """Common bookkeeping after any garden edit."""
        self.dirty = True
        self.last_change = self._clock()
        self._celebrate_progress()
        self._sync(focus_shape=self.carrying)

    def _celebrate_progress(self) -> None:
        if self.editor.ghost_complete():
            if not self._ghost_celebrated:
                self._ghost_celebrated = True
                self.cast.correct()
                self.sounds.play("chime")
                self.sounds.say("celebrate.success")
                self._burst("fx.confetti", self.renderer.view.center, 260)
        else:
            self._ghost_celebrated = False
        if not self._praised and len(self.editor.shapes) >= PRAISE_AT and self.editor.ghost is None:
            self._praised = True
            self.cast.correct()
            self.sounds.say("encourage.progress")

    # -- toolbar actions ---------------------------------------------------------------------

    def _press_new(self) -> None:
        if not self._save():
            return
        self.carrying = False
        self.sounds.play("tick")
        if self.current_id is None and self.state.blank:
            self.mode = "garden"
            self._sync()
            return
        if self.repository is not None and self.repository.is_full():
            self._show_full_shelf()
            return
        self.current_id = None
        self.editor.load(GardenState())
        self.picture_surface = None
        self._saved_picture = None
        self.mode = "garden"
        self.dirty = False
        self._ghost_celebrated = False
        self._praised = False
        self._intro_done = True
        self._last_activity = self._clock() - IDLE_HINT_SECONDS + 1.0
        self._sync()

    def _show_full_shelf(self) -> None:
        self.library_full_until = self._clock() + LIBRARY_FULL_SECONDS
        self._enter_gallery()

    def _toggle_gallery(self) -> None:
        if self.carrying:
            self._put_down()
        if not self._save():
            return
        self.sounds.play("tick")
        if self.mode == "garden":
            self._enter_gallery()
        else:
            self.mode = "garden"
            self._sync()

    def _enter_gallery(self) -> None:
        self.mode = "gallery"
        self.editor.select(None)
        self.gallery_focus = 0
        for index, record in enumerate(self.records):
            if record.garden_id == self.current_id:
                self.gallery_focus = index
        self._sync()
        if self.records:
            self.controls.layer.focus(f"card.{self.gallery_focus % GALLERY_PAGE_SIZE}", visible=self.controls.layer.focus_visible)

    def _open_index(self, index: int) -> None:
        if 0 <= index < len(self.records):
            self.gallery_focus = index
            if self.records[index].garden_id == self.current_id:
                self.mode = "garden"
                self._sync()
                return
            self.sounds.play("tick")
            self._open(self.records[index])

    def _gallery_page_step(self, direction: int) -> None:
        if not self.records:
            return
        pages = self.renderer.gallery_page_count(len(self.records))
        page = max(0, min(pages - 1, self.gallery_focus // GALLERY_PAGE_SIZE + direction))
        self.gallery_focus = page * GALLERY_PAGE_SIZE
        self.sounds.play("tick")
        self._sync()

    def _ask_delete_index(self, index: int) -> None:
        if 0 <= index < len(self.records):
            self.gallery_focus = index
            self._ask_delete(self.records[index].garden_id)

    def _ask_delete_focused(self) -> None:
        slot = self.controls.focused_card_slot()
        if slot is not None:
            self.gallery_focus = (self.gallery_focus // GALLERY_PAGE_SIZE) * GALLERY_PAGE_SIZE + slot
        if 0 <= self.gallery_focus < len(self.records):
            self._ask_delete(self.records[self.gallery_focus].garden_id)

    def _ask_delete(self, garden_id: str) -> None:
        """Deliberate delete: a big preview, "back" focused first."""
        if self.surfaces.overlays or not self._save():
            return
        self.pending_delete = garden_id
        _panel, preview_rect, _cancel, _confirm = self.renderer.delete_dialog_rects()
        preview = self._render_thumbnail(garden_id, preview_rect.size)
        self.surfaces.push_overlay(self.sheets.delete(preview, on_cancel=self._close_sheet, on_confirm=self._confirm_delete))

    def _confirm_delete(self) -> None:
        garden_id = self.pending_delete
        self._close_sheet()
        if garden_id is None or self.repository is None:
            return
        try:
            removed = self.repository.delete(garden_id)
        except (GardenProjectError, RuntimeError):
            self.save_error = True
            return
        if not removed:
            return
        self.sounds.play("swish")
        self.renderer.invalidate_thumbnail(garden_id)
        self.records = [r for r in self.records if r.garden_id != garden_id]
        if garden_id == self.current_id:
            self.current_id = None
            self.editor.load(GardenState())
            self.picture_surface = None
            self.dirty = False
        self.library_full_until = 0.0
        self.gallery_focus = max(0, min(self.gallery_focus, len(self.records) - 1))
        self._sync()
        self._burst("fx.dust_puff", self.renderer.gallery_area().center, 140)

    # -- sheets ---------------------------------------------------------------------------------

    def _open_backdrop_sheet(self) -> None:
        if self.mode != "garden" or self.surfaces.overlays:
            return
        if self.carrying:
            self._put_down()
        tile = (132, 78)
        size = (tile[0] - 16, tile[1] - 16)
        choices: list[tuple[str, pygame.Surface | None]] = [
            (backdrop, self._framed(self.renderer.backdrops.scaled(backdrop, size))) for backdrop in BACKDROP_IDS
        ]
        if self.picture_surface is not None:
            choices.append((PICTURE_BACKDROP, self._framed(pygame.transform.smoothscale(self.picture_surface, size))))
        if self.creations is not None and self.repository is not None:
            choices.append(("import", self.kit.glyph("import", 52)))
        selected = self.state.backdrop
        self.surfaces.push_overlay(self.sheets.pictures(
            "backdrop", choices, selected, columns=5, tile=tile,
            focus_visible=self.controls.layer.focus_visible,
            on_choose=self._choose_backdrop, on_dismiss=self._close_sheet,
        ))
        self.sounds.play("tick")

    def _choose_backdrop(self, choice: str) -> None:
        self._close_sheet()
        if choice == "import":
            self._request_background()
            return
        picture = self.state.picture if choice == PICTURE_BACKDROP else None
        if self.editor.set_backdrop(choice, picture):
            self.sounds.play("chime")
            self._changed()

    def _open_ghost_sheet(self) -> None:
        if self.mode != "garden" or self.surfaces.overlays:
            return
        if self.carrying:
            self._put_down()
        tile = (132, 86)
        choices: list[tuple[str, pygame.Surface | None]] = [("none", self._ghost_icon(None, (tile[0] - 16, tile[1] - 16)))]
        for picture in GHOST_PICTURES:
            choices.append((picture.ghost_id, self._ghost_icon(picture, (tile[0] - 16, tile[1] - 16))))
        self.surfaces.push_overlay(self.sheets.pictures(
            "ghost", choices, self.editor.ghost or "none", columns=4, tile=tile,
            focus_visible=self.controls.layer.focus_visible,
            on_choose=self._choose_ghost, on_dismiss=self._close_sheet,
        ))
        self.sounds.play("tick")

    def _choose_ghost(self, choice: str) -> None:
        self._close_sheet()
        if self.editor.set_ghost(None if choice == "none" else choice):
            self.sounds.play("chime" if choice != "none" else "tick")
            self._ghost_celebrated = self.editor.ghost_complete()
            self.dirty = True
            self.last_change = self._clock()
            self._slot_hint_start = self._clock() if self.editor.ghost else -10.0
            if self.editor.ghost:
                self.cast.point(2.4)
            self._sync()

    def _ghost_icon(self, picture: GhostPicture | None, size: tuple[int, int]) -> pygame.Surface:
        """Picker card: the ghost picture made of real shapes on cream paper."""
        card = pygame.Surface(size, pygame.SRCALPHA)
        card.fill((255, 251, 235))
        if picture is not None:
            # Fit the picture's own bounds (not the whole garden) into the card.
            half = [SIZE_LEVELS[slot.size] * 0.46 for slot in picture.slots]
            left = min(slot.x - h for slot, h in zip(picture.slots, half))
            right = max(slot.x + h for slot, h in zip(picture.slots, half))
            top = min(slot.y - h for slot, h in zip(picture.slots, half))
            bottom = max(slot.y + h for slot, h in zip(picture.slots, half))
            scale = min((size[0] - 12) / (right - left), (size[1] - 12) / (bottom - top))
            ox = size[0] / 2 - (left + right) / 2 * scale
            oy = size[1] / 2 - (top + bottom) / 2 * scale
            for slot in picture.slots:
                side = max(4, round(SIZE_LEVELS[slot.size] * scale))
                image = self.renderer.shapes.image(slot.kind, slot.colour, side, slot.turn)
                if image is not None:
                    card.blit(image, image.get_rect(center=(round(ox + slot.x * scale), round(oy + slot.y * scale))))
        else:
            image = self.renderer.shapes.image("square", "slot", size[1] * 3 // 4)
            if image is not None:
                card.blit(image, image.get_rect(center=(size[0] // 2, size[1] // 2)))
        pygame.draw.rect(card, (75, 55, 47), card.get_rect(), 2, border_radius=6)
        return card

    @staticmethod
    def _framed(surface: pygame.Surface) -> pygame.Surface:
        framed = surface.copy()
        pygame.draw.rect(framed, (75, 55, 47), framed.get_rect(), 2, border_radius=6)
        return framed

    def _close_sheet(self) -> None:
        self.pending_delete = None
        while self.surfaces.overlays:
            self.surfaces.pop_overlay()

    # -- My Creations ---------------------------------------------------------------------------

    def _request_background(self) -> None:
        if self.creations is None or self.repository is None or self.import_request is not None:
            return
        if not self._save():
            self.import_state = "error"
            self.import_feedback_until = self._clock() + FEEDBACK_SECONDS
            return
        try:
            request_id = self.creations.request_selection(media_types=("image/png",))
        except (RuntimeError, ValueError, OSError):
            self.import_state = "error"
            self.import_feedback_until = self._clock() + FEEDBACK_SECONDS
            return
        self.import_request = request_id
        self.import_state = "pending"
        self.import_next_poll = self._clock() + self.IMPORT_POLL_SECONDS

    def _poll_background(self, now: float) -> None:
        request_id = self.import_request
        if request_id is None or self.creations is None or now < self.import_next_poll:
            return
        self.import_next_poll = now + self.IMPORT_POLL_SECONDS
        try:
            result = self.creations.poll_selection(request_id)
        except (RuntimeError, ValueError, OSError):
            self.import_request = None
            self.import_state = "error"
            self.import_feedback_until = now + FEEDBACK_SECONDS
            return
        state = getattr(result, "state", None)
        if state == "pending":
            return
        self.import_request = None
        if state == "cancelled":
            self.import_state = ""
            return
        token = getattr(result, "selection_token", None)
        if state != "ready" or not isinstance(token, str) or not token:
            self.import_state = "error"
            self.import_feedback_until = now + FEEDBACK_SECONDS
            return
        self.import_state = "imported" if self._accept_background(token) else "error"
        self.import_feedback_until = now + FEEDBACK_SECONDS

    def _accept_background(self, selection_token: str) -> bool:
        """Make one Shell-confirmed PNG the garden backdrop (a private copy).

        The PNG is validated and decoded before anything changes, so a broken
        picture can never leave a half-updated garden.
        """
        if self.creations is None or self.repository is None:
            return False
        try:
            transfer = self.creations.import_selected(selection_token)
            payload = transfer.payload
            if (
                transfer.record.get("media_type") != "image/png"
                or not isinstance(payload, bytes)
                or transfer.record.get("sha256") != hashlib.sha256(payload).hexdigest()
            ):
                raise ValueError("selected backdrop failed integrity validation")
            surface = decode_picture(payload)
            digest = self.repository.store_picture(payload)
        except (GardenProjectError, PygamePngError, RuntimeError, ValueError, OSError):
            return False
        self._pictures[digest] = surface
        self.picture_surface = surface
        self.editor.set_backdrop(PICTURE_BACKDROP, digest)
        self.sounds.play("chime")
        self._changed()
        return self._save()

    def _render_export(self) -> pygame.Surface:
        picture = self.picture_surface if self.state.backdrop == PICTURE_BACKDROP else None
        return self.renderer.composer.compose(self.state, (GARDEN_WIDTH, GARDEN_HEIGHT), picture=picture)

    def _publish_project(self) -> None:
        """Explicit flattened copy into My Creations (never on autosave)."""
        if self.creations is None or self.repository is None:
            return
        if self.carrying:
            self._put_down()
        if not self._save():
            self.publish_state = "error"
            self.publish_feedback_until = self._clock() + FEEDBACK_SECONDS
            return
        if self.state.blank:
            return  # nothing made yet: nothing to share
        try:
            payload = encode_surface_png(self._render_export())
            digest = hashlib.sha256(payload).hexdigest()
            if digest != self._last_published_digest:
                name = self.repository.save_export(payload)
                self.creations.publish_private_file(name, media_type="image/png", role="composition")
                self._last_published_digest = digest
                try:
                    emit_activity_event(
                        "creation.completed",
                        idempotency_key=f"composition-{digest}",
                        payload={"media_type": "image/png", "shape_count": len(self.state.shapes)},
                    )
                except Exception:  # noqa: BLE001
                    # Progress telemetry must never make a successful child
                    # creation publication fail or duplicate the Creation.
                    pass
            self.publish_state = "saved"
            self.cast.correct()
            self.sounds.play("chime")
            self.sounds.say("praise.general")
            self._burst("fx.sparkle", self.controls.share.rect.center, 120)
        except (GardenProjectError, PygamePngError, RuntimeError, ValueError, OSError):
            self.publish_state = "error"
        self.publish_feedback_until = self._clock() + FEEDBACK_SECONDS

    # -- per frame --------------------------------------------------------------------------------

    def _step_frame(self) -> bool:
        """Advance timers and hints; return True when the virtual pointer moved."""
        now = self._clock()
        elapsed = min(0.1, max(0.0, now - self._last_frame))
        self._last_frame = now
        moved = self.controller_pointer.step(elapsed)
        if moved is not None:
            self.pointer_motion(moved)
        if self.dirty and not self.editor.dragging and now - self.last_change >= AUTOSAVE_IDLE_SECONDS:
            self._save()
        self._poll_background(now)
        if self.import_state and self.import_state != "pending" and now >= self.import_feedback_until:
            self.import_state = ""
        if self.publish_state and now >= self.publish_feedback_until:
            self.publish_state = ""
        self.cast.update()
        self._fx = [burst for burst in self._fx if not burst.done]
        self._maybe_hint(now)
        return moved is not None

    def _maybe_hint(self, now: float) -> None:
        """Wordless invitations: Dani points, the tray hops, a hand shows the drag."""
        if self.mode != "garden" or self.surfaces.overlays or self.editor.dragging or self._press is not None:
            return
        idle = now - self._last_activity
        wait = 1.2 if not self._intro_done else IDLE_HINT_SECONDS * (1 if self._hints < 3 else 2)
        if idle < wait:
            return
        if not self.editor.shapes:
            self._tray_hint_start = now
            self.cast.point(2.6)
            if not self._intro_done:
                self.sounds.say("ready.go")
        elif self.editor.next_free_slot() is not None:
            self._slot_hint_start = now
            self.cast.point(2.4)
        else:
            self._last_activity = now
            return
        self._intro_done = True
        self._hints += 1
        self._last_activity = now

    def _burst(self, asset_id: str, center: tuple[int, int], size: int) -> None:
        frames = self.renderer.fx_frames(asset_id, size)
        if frames:
            self._fx = [*self._fx[-2:], FxBurst(frames, center, clock=self._clock)]

    # -- control sync ----------------------------------------------------------------------------

    def _refresh_tray(self) -> None:
        self.controls.set_tray_icons([self.renderer.shapes.image(kind, self.colour, 60) for kind in SHAPE_KINDS])

    def _sync(self, *, focus_shape: bool = False) -> None:
        controls = self.controls
        controls.set_mode(self.mode, share_available=self.creations is not None and self.repository is not None)
        if self.mode == "gallery":
            page = self.gallery_focus // GALLERY_PAGE_SIZE
            controls.sync_gallery(
                page=page,
                page_count=self.renderer.gallery_page_count(len(self.records)),
                cards=self.renderer.gallery_cards(len(self.records), page),
                has_cards=bool(self.records),
            )
            return
        selected = self.editor.selected_shape
        backdrop = self.state.backdrop
        icon_key = (backdrop, self.state.picture if backdrop == PICTURE_BACKDROP else None)
        if icon_key != self._backdrop_icon[0]:
            icon_size = (50, 30)
            if backdrop == PICTURE_BACKDROP and self.picture_surface is not None:
                icon = self._framed(pygame.transform.smoothscale(self.picture_surface, icon_size))
            else:
                icon = self._framed(self.renderer.backdrops.scaled(backdrop if backdrop in BACKDROP_IDS else "paper", icon_size))
            self._backdrop_icon = (icon_key, icon)
        backdrop_icon = self._backdrop_icon[1]
        controls.share.enabled = not self.state.blank and self.publish_state != "error"
        controls.sync_garden(
            shape_rects=[self.renderer.shape_screen_rect(shape) for shape in self.editor.shapes],
            selected=selected is not None,
            can_undo=self.editor.can_undo,
            full=self.editor.full,
            can_grow=selected is not None and selected.size < len(SIZE_LEVELS) - 1,
            can_shrink=selected is not None and selected.size > 0,
            backdrop_icon=backdrop_icon,
        )
        if focus_shape and self.editor.selected is not None:
            controls.layer.focus(shape_target_id(self.editor.selected), visible=controls.layer.focus_visible)

    # -- drawing ------------------------------------------------------------------------------------

    def _status(self) -> str:
        if self.save_error or "error" in (self.import_state, self.publish_state):
            return "error"
        return "saving" if self.dirty else "saved"

    def _draw(self) -> None:
        surface = self.canvas.surface
        now = self._clock()
        renderer = self.renderer
        renderer.draw_static(surface, self.mode)
        if self.mode == "gallery":
            self._draw_gallery(surface)
        else:
            self._draw_garden(surface, now)
        self._draw_layer(surface, now)
        self.cast.draw(surface, renderer.dani_midbottom())
        for burst in self._fx:
            burst.draw(surface)
        if self.mode == "garden" and not self.surfaces.overlays:
            renderer.draw_drag_hint(surface, (now - self._tray_hint_start) / 1.8)
            renderer.draw_status(surface, self._status())
            if self.editor.full:
                renderer.draw_full_badge(surface, renderer.tray_rect())
        for overlay in self.surfaces.overlays:
            overlay.draw(surface)
        virtual = self.controller_pointer.position if self.controller_pointer.active else None
        self.canvas.present(clear=self.theme.background, pointer=virtual is None)
        if virtual is not None:
            draw_activity_pointer(self.screen, virtual)

    def _draw_garden(self, surface: pygame.Surface, now: float) -> None:
        renderer = self.renderer
        editor = self.editor
        skip = editor.selected if editor.dragging else None
        shapes = editor.shapes
        visible = tuple(s for i, s in enumerate(shapes) if i != skip)
        ghost = editor.ghost_picture
        filled = tuple(any(s.matches(slot) for s in visible) for slot in ghost.slots) if ghost is not None else ()
        key = (visible, self.state.backdrop, self.state.picture, editor.ghost, filled, id(self.picture_surface))
        renderer.draw_garden(
            surface, key, GardenState(visible, self.state.backdrop, self.state.picture),
            picture=self.picture_surface, ghost=ghost, filled=filled, skip=None,
        )
        if ghost is not None and now - self._slot_hint_start < 2.4:
            slot = editor.next_free_slot()
            if slot is not None and math.sin((now - self._slot_hint_start) * 7.0) > 0.1:
                # The free slot blinks with the shape it wants, in the tray colour.
                renderer.draw_floating(surface, slot.kind, self.colour, slot.size, slot.turn, renderer.to_screen((slot.x, slot.y)))
        selected = editor.selected_shape
        if selected is not None and editor.dragging:
            if self.carrying or self._drag_point is None or renderer.view.collidepoint(self._drag_point):
                renderer.draw_lifted(surface, selected)
            else:
                # Outside the garden (over the tray or bin) the shape follows
                # the finger, so dropping it there reads as "put it away".
                renderer.draw_floating(surface, selected.kind, selected.colour, selected.size, selected.turn, self._drag_point)
        elif selected is not None:
            renderer.draw_selection(surface, selected, now)
        if self._new_drag is not None and self._drag_point is not None:
            renderer.draw_floating(surface, self._new_drag, self.colour, 2, 0, self._drag_point)
        renderer.draw_pots(surface, self.colour)

    def _draw_gallery(self, surface: pygame.Surface) -> None:
        page = self.gallery_focus // GALLERY_PAGE_SIZE
        cards = self.renderer.gallery_cards(len(self.records), page)
        first = page * GALLERY_PAGE_SIZE
        thumbs = []
        for slot, card in enumerate(cards):
            record = self.records[first + slot]
            size = self.renderer.card_thumb_rect(card).size
            thumbs.append(self.renderer.thumbnail(record.garden_id, lambda gid=record.garden_id, sz=size: self._render_thumbnail(gid, sz)))
        focus_slot = self.controls.focused_card_slot() if self.controls.layer.focus_visible else None
        if focus_slot is None and self.records and self.gallery_focus // GALLERY_PAGE_SIZE == page:
            focus_slot = self.gallery_focus % GALLERY_PAGE_SIZE
        self.renderer.draw_gallery(
            surface, cards, thumbs, focus_slot,
            page=page,
            page_count=self.renderer.gallery_page_count(len(self.records)),
            library_full=self._clock() < self.library_full_until,
        )

    def _render_thumbnail(self, garden_id: str, size: tuple[int, int]) -> pygame.Surface | None:
        if self.repository is None:
            return None
        if garden_id == self.current_id:
            state, ghost = self.state, None
        else:
            try:
                project = self.repository.load(garden_id)
            except (GardenProjectError, RuntimeError, ValueError):
                return None
            state, ghost = project.state, None
        picture = self._picture(state.picture) if state.backdrop == PICTURE_BACKDROP else None
        return self.renderer.composer.compose(state, size, picture=picture, ghost=ghost)

    def _draw_layer(self, surface: pygame.Surface, now: float) -> None:
        """Draw kit controls; during the tray invitation the tiles hop in a wave."""
        hop = now - self._tray_hint_start
        slot_hint = now - self._slot_hint_start
        moved: list[tuple[object, pygame.Rect]] = []
        if self.mode == "garden" and (hop < 1.6 or slot_hint < 2.4):
            free = self.editor.next_free_slot() if slot_hint < 2.4 else None
            for index, button in enumerate(self.controls.tray):
                if free is not None and SHAPE_KINDS[index] != free.kind:
                    continue
                t = (slot_hint if free is not None else hop) - index * (0.0 if free is not None else 0.09)
                lift = int(12 * max(0.0, math.sin(min(math.pi, max(0.0, t * 6.0))))) if free is None else int(8 * abs(math.sin(t * 6.0)))
                if lift:
                    moved.append((button, button.rect))
                    button.rect = button.rect.move(0, -lift)
        self.controls.layer.draw(surface)
        for button, rect in moved:
            button.rect = rect  # type: ignore[attr-defined]


__all__ = ["GardenApp", "GardenCast", "REFERENCE_HEIGHT", "REFERENCE_WIDTH"]
