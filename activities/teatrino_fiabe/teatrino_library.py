"""The saved-shows shelf: poster cards, paging, deliberate delete, full shelf.

Custody rules (P7 section 1.7, Phase-0 creation contract):

* every saved show is reachable (paged 3x2 poster cards, page arrows);
* the shelf never evicts: when it is full, recording opens this sheet with
  every shelf dot lit and Lilli thinking, and nothing is removed;
* deleting is deliberate: a small trash badge (pointer) or the trash tile
  for the focused card (keyboard/controller) opens a confirmation showing
  the show's poster, with "keep" focused and "delete" armed only after a
  short moment, so a double tap or a stray Enter can never delete.
"""

from __future__ import annotations

from collections.abc import Callable

import pygame

from greia_platform.activity_controls import ButtonRole, ControlKit
from greia_platform.ui_core import SurfaceNavigator

if __package__:
    from .teatrino_controls import LibraryControls, TheatreSheet, dialog_layer
    from .teatrino_layout import DialogLayout, GridLayout, TheatreLayout
    from .teatrino_model import DeleteConfirmation, ShowRepository
    from .teatrino_renderer import POSTER_ASPECT, PosterStudio, TheatreRenderer, picture_size, rounded
else:
    from teatrino_controls import LibraryControls, TheatreSheet, dialog_layer
    from teatrino_layout import DialogLayout, GridLayout, TheatreLayout
    from teatrino_model import DeleteConfirmation, ShowRepository
    from teatrino_renderer import POSTER_ASPECT, PosterStudio, TheatreRenderer, picture_size, rounded

COLUMNS, ROWS = 3, 2
PAGE_SIZE = COLUMNS * ROWS
LIBRARY_ID = "teatrino.library"
DELETE_ID = "teatrino.delete"


class ShowLibrary:
    """Own the shows sheet and its delete confirmation on the app's navigator."""

    def __init__(
        self,
        repository: ShowRepository,
        *,
        kit: ControlKit,
        renderer: TheatreRenderer,
        posters: PosterStudio,
        surfaces: SurfaceNavigator,
        layout: Callable[[], TheatreLayout],
        clock: Callable[[], float],
        play: Callable[[str], object],
        on_watch: Callable[[dict], object],
        on_record: Callable[[], object],
        draw_host: Callable[[pygame.Surface, tuple[int, int]], object],
    ) -> None:
        self.repository = repository
        self.kit = kit
        self.renderer = renderer
        self.posters = posters
        self.surfaces = surfaces
        self._layout = layout
        self._clock = clock
        self._play = play
        self._on_watch = on_watch
        self._on_record = on_record
        self._draw_host = draw_host
        self.shows: list[dict] = repository.list_shows()
        self.page = 0
        self.confirm: DeleteConfirmation | None = None
        self.controls: LibraryControls | None = None
        self.full = False
        self._delete_sheet: TheatreSheet | None = None

    # -- state ------------------------------------------------------------------

    @property
    def is_open(self) -> bool:
        return any(o.surface_id == LIBRARY_ID for o in self.surfaces.overlays)

    @property
    def pages(self) -> int:
        return max(1, (len(self.shows) + PAGE_SIZE - 1) // PAGE_SIZE)

    def refresh(self) -> None:
        self.shows = self.repository.list_shows()
        self.page = min(self.page, self.pages - 1)

    # -- open / close -----------------------------------------------------------

    def open(self, *, full: bool = False) -> None:
        self.refresh()
        self.full = full
        grid = GridLayout.build(self._layout(), columns=COLUMNS, rows=ROWS, aspect=POSTER_ASPECT * 1.04)
        controls = LibraryControls(
            self.kit,
            grid,
            on_close=self.close,
            on_open=self._open_index,
            on_delete=self.request_delete_index,
            on_delete_focused=self.request_delete_focused,
            on_page=self.page_step,
            on_record=self._record,
        )
        self.controls = controls
        self.sync()
        sheet = TheatreSheet(
            LIBRARY_ID,
            controls.layer,
            grid.panel,
            on_dismiss=self.close,
            draw_backdrop=lambda target: self._draw_backdrop(target, grid),
            draw_front=lambda target: self._draw_front(target, grid),
        )
        self.surfaces.push_overlay(sheet)

    def close(self) -> None:
        while self.surfaces.overlays and self.surfaces.overlays[-1].surface_id in (LIBRARY_ID, DELETE_ID):
            self.surfaces.pop_overlay()
        self.confirm = None
        self._delete_sheet = None
        self.controls = None
        self.full = False

    def sync(self) -> None:
        controls = self.controls
        if controls is None:
            return
        first = self.page * PAGE_SIZE
        size = picture_size(controls.grid.cards[0])
        posters = [rounded(self.posters.for_show(item, size)) for item in self.shows[first : first + PAGE_SIZE]]
        controls.sync(posters, first_index=first, page=self.page, pages=self.pages, count=len(self.shows))

    # -- actions ----------------------------------------------------------------------

    def _open_index(self, index: int) -> None:
        if 0 <= index < len(self.shows):
            show = self.shows[index]
            self.close()
            self._on_watch(show)

    def _record(self) -> None:
        self.close()
        self._on_record()

    def page_step(self, direction: int) -> None:
        page = max(0, min(self.pages - 1, self.page + direction))
        if page != self.page:
            self.page = page
            self._play("pop")
            self.sync()

    def request_delete_focused(self) -> None:
        slot = self.controls.focused_slot() if self.controls is not None else None
        self.request_delete_index(self.page * PAGE_SIZE + (slot or 0))

    def request_delete_index(self, index: int) -> None:
        if 0 <= index < len(self.shows) and self.confirm is None:
            self.request_delete(self.shows[index])

    def request_delete(self, show_item: dict) -> None:
        """Open the confirmation dialog; nothing is removed by this call."""

        self._play("pop")
        self.confirm = DeleteConfirmation(show_item["id"], self._clock())
        dialog = DialogLayout.build(self._layout(), buttons=2, width=640, height=430)
        picture = self.posters.for_show(show_item, dialog.picture.size)
        layer = dialog_layer(
            self.kit,
            dialog,
            [
                ("delete.keep", "arrow_left", ButtonRole.NEUTRAL, lambda: self.resolve(DeleteConfirmation.KEEP)),
                ("delete.confirm", "trash", ButtonRole.PRIMARY, lambda: self.resolve(DeleteConfirmation.DELETE)),
            ],
            layer_id="teatrino.delete.controls",
            focus="delete.keep",
        )
        layer.focus("delete.keep", visible=True)
        layer.target("delete.confirm").enabled = False  # armed after a short moment
        sheet = TheatreSheet(
            DELETE_ID,
            layer,
            dialog.panel,
            on_dismiss=lambda: self.resolve(DeleteConfirmation.KEEP),
            draw_backdrop=lambda target: self._draw_dialog(target, dialog, picture),
        )
        self._delete_sheet = sheet
        self.surfaces.push_overlay(sheet)

    def sync_arming(self, now: float) -> bool:
        """Enable the delete button once the dialog is armed; True when changed."""

        confirm, sheet = self.confirm, self._delete_sheet
        if confirm is None or sheet is None:
            return False
        target = sheet.layer.target("delete.confirm")
        armed = confirm.armed(now)
        if target.enabled == armed:
            return False
        target.enabled = armed
        sheet.layer.invalidation.invalidate()
        return True

    def after_input(self) -> None:
        """Mirror the kit's focus into the confirmation model."""

        if self.confirm is not None and self._delete_sheet is not None:
            focused = self._delete_sheet.layer.focused_id
            self.confirm.focus = DeleteConfirmation.DELETE if focused == "delete.confirm" else DeleteConfirmation.KEEP

    def resolve(self, choice: str) -> None:
        """Apply the child's choice in the dialog (keep is always safe)."""

        confirm = self.confirm
        if confirm is None:
            return
        outcome = confirm.resolve(choice, self._clock())
        if outcome is None:
            return  # delete pressed before the dialog armed: ignore
        self.confirm = None
        if self.surfaces.overlays and self.surfaces.overlays[-1].surface_id == DELETE_ID:
            self.surfaces.pop_overlay()
        self._delete_sheet = None
        if outcome != DeleteConfirmation.DELETE:
            self._play("pop")
            return
        self._play("poof")
        self.repository.delete_show(confirm.target_id)
        self.refresh()
        self.full = False
        self.sync()

    # -- drawing ------------------------------------------------------------------

    def _draw_backdrop(self, target: pygame.Surface, grid: GridLayout) -> None:
        self.renderer.draw_dim(target)
        self.renderer.draw_panel(target, grid.panel)

    def _draw_front(self, target: pygame.Surface, grid: GridLayout) -> None:
        if self.full:
            self._draw_host(target, (grid.close.left - 70, grid.header.bottom + 8))

    def _draw_dialog(self, target: pygame.Surface, dialog: DialogLayout, picture: pygame.Surface | None) -> None:
        self.renderer.draw_dim(target)
        self.renderer.draw_panel(target, dialog.panel)
        self.renderer.draw_picture(target, picture, dialog.picture)


__all__ = ["COLUMNS", "DELETE_ID", "LIBRARY_ID", "PAGE_SIZE", "ROWS", "ShowLibrary"]
