"""Greia lifecycle, input translation and page composition for the encyclopedia."""

from __future__ import annotations

import pygame

from greia_platform.activity_api import (
    activity_stop_requested,
    get_input_profile,
    mark_activity_ready,
)
from greia_platform.activity_ui import is_home_clicked
from greia_platform.input_core import InputEdge, SemanticAction
from greia_platform.localization import LocalizedResources
from greia_platform.pygame_canvas import PygameReferenceCanvas, activity_viewport_for_surface
from greia_platform.pygame_input import PygameInputTranslator
from greia_platform.typography import GreiaTypography

if __package__:
    from .enciclopedia_audio import EncyclopediaAudio
    from .enciclopedia_engine import (
        PageCommand,
        PageContext,
        PageInput,
        PageNavigator,
        PageRegistry,
    )
    from .enciclopedia_services import EncyclopediaPalette, VisualLibrary
else:
    from enciclopedia_audio import EncyclopediaAudio
    from enciclopedia_engine import (
        PageCommand,
        PageContext,
        PageInput,
        PageNavigator,
        PageRegistry,
    )
    from enciclopedia_services import EncyclopediaPalette, VisualLibrary


_COMMANDS = {
    SemanticAction.NAV_UP: PageCommand.UP,
    SemanticAction.NAV_DOWN: PageCommand.DOWN,
    SemanticAction.NAV_LEFT: PageCommand.LEFT,
    SemanticAction.NAV_RIGHT: PageCommand.RIGHT,
    SemanticAction.ACTIVATE: PageCommand.ACTIVATE,
    SemanticAction.CANCEL: PageCommand.BACK,
}


class EncyclopediaApp:
    """Own the Activity loop; page-specific behavior stays in page modules."""

    def __init__(
        self,
        *,
        screen: pygame.Surface,
        resources: LocalizedResources,
        typography: GreiaTypography,
        visuals: VisualLibrary,
        audio: EncyclopediaAudio,
        palette: EncyclopediaPalette,
        registry: PageRegistry,
    ) -> None:
        self.screen = screen
        self.canvas = PygameReferenceCanvas(screen)
        self._running = True
        self._ready_published = False
        self._translator = PygameInputTranslator(get_input_profile())
        self._palette = palette
        context = PageContext(
            host=self,
            resources=resources,
            typography=typography,
            visuals=visuals,
            audio=audio,
            palette=palette,
        )
        self.navigator = PageNavigator(registry, context, root_page_id="home")

    def open_page(self, page_id: str) -> None:
        self.navigator.open(page_id)

    def go_back(self) -> bool:
        return self.navigator.back()

    def run(self) -> int:
        clock = pygame.time.Clock()
        while self._running and not activity_stop_requested():
            dt = min(0.1, clock.tick(30) / 1000.0)
            for event in pygame.event.get():
                self._handle_event(event)
            self.navigator.update(dt)
            self.navigator.draw(self.canvas.surface)
            self._draw_internal_back()
            self.canvas.present(system_chrome=True, pointer=True)
            pygame.display.flip()
            if not self._ready_published:
                mark_activity_ready()
                self._ready_published = True
        return 0

    def _handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.QUIT:
            self._running = False
            return
        if event.type == pygame.VIDEORESIZE:
            self.screen = pygame.display.get_surface() or self.screen
            self.canvas = PygameReferenceCanvas(self.screen)
            return

        if event.type == pygame.MOUSEMOTION:
            logical = self.canvas.pointer(event.pos)
            if logical is not None:
                self.navigator.handle_input(PageInput.pointer_move(logical))
            return

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if is_home_clicked(self.screen, event.pos):
                self._running = False
                return
            if not self._point_in_activity_viewport(event.pos):
                return
            logical = self.canvas.pointer(event.pos)
            if logical is not None:
                if self.navigator.can_go_back and self._internal_back_rect().collidepoint((int(logical[0]), int(logical[1]))):
                    self.go_back()
                    return
                self.navigator.handle_input(PageInput.pointer_press(logical))
            return

        semantic = self._translator.digital(event)
        if semantic is None or semantic.edge is not InputEdge.PRESSED:
            return
        command = _COMMANDS.get(semantic.action)
        if command is None:
            return
        if command is PageCommand.BACK:
            self.go_back()
            return
        self.navigator.handle_input(PageInput.command_event(command))

    @staticmethod
    def _internal_back_rect() -> pygame.Rect:
        # Activity-internal page navigation. This is intentionally placed away
        # from Greia's protected system Home chrome and styled as a book tab,
        # not as a replacement system button.
        return pygame.Rect(894, 90, 78, 58)

    def _draw_internal_back(self) -> None:
        if not self.navigator.can_go_back:
            return
        rect = self._internal_back_rect()
        pygame.draw.rect(
            self.canvas.surface,
            (255, 232, 154),
            rect,
            border_radius=18,
        )
        pygame.draw.rect(
            self.canvas.surface,
            self._palette.ink,
            rect,
            width=3,
            border_radius=18,
        )
        cx, cy = rect.center
        pygame.draw.line(
            self.canvas.surface,
            self._palette.ink,
            (cx + 15, cy),
            (cx - 13, cy),
            6,
        )
        pygame.draw.polygon(
            self.canvas.surface,
            self._palette.ink,
            [(cx - 18, cy), (cx - 2, cy - 14), (cx - 2, cy + 14)],
        )

    def _point_in_activity_viewport(self, pos: tuple[int, int]) -> bool:
        viewport = activity_viewport_for_surface(self.screen)
        x, y = pos
        if not (0 <= x < viewport.surface.width and 0 <= y < viewport.surface.height):
            return False
        return not any(
            region.x <= x < region.right and region.y <= y < region.bottom
            for region in viewport.protected_regions
        )
