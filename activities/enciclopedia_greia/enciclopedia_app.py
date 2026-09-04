"""Greia lifecycle, input translation and page composition for the encyclopedia."""

from __future__ import annotations

import pygame

from greia_platform.activity_api import (
    activity_stop_requested,
    get_input_profile,
    mark_activity_ready,
)
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
            if self.navigator.can_go_back:
                self._draw_back_button(self.canvas.surface)
            self.canvas.present(pointer=True)
            pygame.display.flip()
            if not self._ready_published:
                mark_activity_ready()
                self._ready_published = True
        return 0

    def _draw_back_button(self, surface: pygame.Surface) -> None:
        """Draw tactile Back button at canonical back_hitbox when can_go_back is True."""
        from greia_platform.activity_ui import draw_back_symbol
        from greia_platform.system_chrome import ActivitySystemChromeLayout

        chrome = ActivitySystemChromeLayout.for_surface(
            self.canvas.spec.width,
            self.canvas.spec.height,
            back_available=True,
        )
        bb = chrome.back_hitbox
        back_rect = pygame.Rect(bb.x, bb.y, bb.width, bb.height)
        radius = max(8, back_rect.width // 3)

        # Drop shadow
        shadow_rect = back_rect.move(0, 3)
        pygame.draw.rect(surface, (203, 213, 225), shadow_rect, border_radius=radius)

        # Tactile warm cream pill
        fill_color = (255, 252, 245)
        outline_color = (78, 56, 40)
        pygame.draw.rect(surface, fill_color, back_rect, border_radius=radius)

        # Subtle top highlight
        highlight_rect = pygame.Rect(
            back_rect.x + 2,
            back_rect.y + 2,
            back_rect.width - 4,
            max(2, back_rect.height // 2),
        )
        pygame.draw.rect(
            surface,
            (255, 255, 255),
            highlight_rect,
            border_top_left_radius=max(6, radius - 2),
            border_top_right_radius=max(6, radius - 2),
        )

        # 3px dark outline
        pygame.draw.rect(
            surface,
            outline_color,
            back_rect,
            width=max(2, back_rect.width // 20),
            border_radius=radius,
        )
        draw_back_symbol(surface, back_rect, outline_color)

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
            # Check if user clicked the in-app Back button
            if self.navigator.can_go_back and self._point_in_back_hitbox(event.pos):
                self.go_back()
                return
            if not self._point_in_activity_viewport(event.pos):
                return
            logical = self.canvas.pointer(event.pos)
            if logical is not None:
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

    def _point_in_back_hitbox(self, pos: tuple[int, int]) -> bool:
        from greia_platform.system_chrome import ActivitySystemChromeLayout

        chrome = ActivitySystemChromeLayout.for_surface(
            self.canvas.spec.width,
            self.canvas.spec.height,
            back_available=True,
        )
        logical = self.canvas.pointer(pos)
        if logical is None:
            return False
        lx, ly = logical
        bb = chrome.back_hitbox
        return bb.x <= lx < bb.right and bb.y <= ly < bb.bottom

    def _point_in_activity_viewport(self, pos: tuple[int, int]) -> bool:
        viewport = activity_viewport_for_surface(self.screen)
        x, y = pos
        if not (0 <= x < viewport.surface.width and 0 <= y < viewport.surface.height):
            return False
        return not any(
            region.x <= x < region.right and region.y <= y < region.bottom
            for region in viewport.protected_regions
        )
