"""Lifecycle and interaction flow for Fluffy Monsters.

One experience: build a fluffy monster friend, name it, keep it.

1. **Build** — ten picture drawers on the right (body, colour, pattern, eyes,
   mouth, horns/ears, arms, feet, accessory, name tag). The open drawer shows
   big tiles on the right, each a real preview of *this* friend wearing that
   part (drawers and tiles sit side by side: one short pointer move). Every
   pick pops onto the friend, who boings and giggles; tickling the
   friend makes it laugh; it blinks on its own. Undo and a surprise dice sit
   in the top bar.
2. **Name** — the name-tag drawer offers big syllable bubbles (up to three),
   an eraser and a dice for a ready-made silly name. No typing is needed.
3. **Save** — enabled once something was really chosen (no blank saves). The
   friend hops onto the stage, Momo cheers with an approved voice line and
   confetti falls; then a new friend, the gallery, or sharing.

The gallery shows every saved friend (up to 24, paged big cards, never evicted).
Opening one shows it big; it can be shared to My Creations as an 800x600 PNG
(role ``picture``, so Painting, Shape Garden, Teatrino and Leo's Post can use
it) or deliberately deleted from a preview sheet. The friend being built
survives Home.

Every control is a shared-kit control (ADR 0037): pointer, touch, keyboard
(arrows + Space/Enter) and controller (D-pad/stick + south) share one focus
ring. Nothing is placed in the protected Home/Back region; the platform pointer
is drawn by ``PygameReferenceCanvas.present``.
"""

from __future__ import annotations

from collections.abc import Callable
from enum import StrEnum
import random
import time
import uuid

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
from greia_platform.activity_feedback import IdleHintScheduler
from greia_platform.input_core import InputEdge, SemanticAction, SemanticInputEvent
from greia_platform.localization import LocalizedResources
from greia_platform.pygame_canvas import PygameReferenceCanvas, activity_viewport_for_surface
from greia_platform.pygame_png import PygamePngError, encode_surface_png
from greia_platform.typography import GreiaTypography
from greia_platform.ui_core import SurfaceNavigator, UiEventResult

if __package__:
    from .monster_art import MonsterArt
    from .monster_audio import HOST, MonsterAudio
    from .monster_content import (
        CATEGORY_ORDER,
        GALLERY_PAGE_SIZE,
        MAX_SAVED_PORTRAITS,
        OPTIONS,
        SHARE_ROLE,
        SYLLABLES,
        Category,
    )
    from .monster_controls import NAME_DRAWER, MonsterControls, MonsterSheet, MonsterSheets, TileSpec
    from .monster_layout import FriendLayout, GalleryLayout, SheetLayout, StudioLayout
    from .monster_model import MonsterEditor, MonsterGallery, MonsterRecipe
    from .monster_renderer import CastActor, Effects, FriendMotion, MonsterRenderer, body_rect
    from .monster_services import EventPort, StoragePort
else:
    from monster_art import MonsterArt
    from monster_audio import HOST, MonsterAudio
    from monster_content import (
        CATEGORY_ORDER,
        GALLERY_PAGE_SIZE,
        MAX_SAVED_PORTRAITS,
        OPTIONS,
        SHARE_ROLE,
        SYLLABLES,
        Category,
    )
    from monster_controls import NAME_DRAWER, MonsterControls, MonsterSheet, MonsterSheets, TileSpec
    from monster_layout import FriendLayout, GalleryLayout, SheetLayout, StudioLayout
    from monster_model import MonsterEditor, MonsterGallery, MonsterRecipe
    from monster_renderer import CastActor, Effects, FriendMotion, MonsterRenderer, body_rect
    from monster_services import EventPort, StoragePort

HALO_SECONDS = 1.8
DRAFT_SAVE_IDLE = 2.5
FEEDBACK_SECONDS = 2.0
DRAWER_IDS: tuple[str, ...] = (*(category.value for category in CATEGORY_ORDER), NAME_DRAWER)
SQUISH_CATEGORIES = frozenset({Category.BODY_SHAPE, Category.BODY_COLOR, Category.PATTERN})


class Screen(StrEnum):
    STUDIO = "studio"
    GALLERY = "gallery"
    FRIEND = "friend"
    CELEBRATE = "celebrate"


# Back-compatible alias (the first release called the screens "view modes").
ViewMode = Screen


def _safe_point(screen: pygame.Surface, pos: tuple[int, int]) -> bool:
    """Platform Home/Back belongs to trusted chrome; never handle input there."""

    viewport = activity_viewport_for_surface(screen)
    x, y = pos
    if not (0 <= x < viewport.surface.width and 0 <= y < viewport.surface.height):
        return False
    return not any(r.x <= x < r.right and r.y <= y < r.bottom for r in viewport.protected_regions)


class MonsterActivity:
    """Coordinate the studio, the celebration, the gallery and sharing."""

    def __init__(
        self,
        *,
        screen: pygame.Surface,
        canvas: PygameReferenceCanvas,
        typography: GreiaTypography,
        resources: LocalizedResources | None,
        storage: StoragePort,
        events: EventPort,
        audio: MonsterAudio,
        rng: random.Random | None = None,
        creations=None,
        gallery: MonsterGallery | None = None,
        draft: MonsterRecipe | None = None,
        clock: Callable[[], float] = time.monotonic,
        wall_clock: Callable[[], float] = time.time,
        kit: ControlKit | None = None,
        art: MonsterArt | None = None,
    ) -> None:
        self.screen = screen
        self.canvas = canvas
        self.typography = typography
        self.resources = resources
        self.storage = storage
        self.events = events
        self.audio = audio
        self.rng = rng if rng is not None else random.Random()
        self.creations = creations
        self.clock = clock
        self._wall_clock = wall_clock

        # Shared control kit (ADR 0037): Create Collection -> coral accent.
        self.kit = kit if kit is not None else ControlKit(typography, ControlTheme.for_accent("coral"))
        self.art = art if art is not None else MonsterArt()
        self.renderer = MonsterRenderer(self.art, self.kit.painter, self.kit.art, clock)
        self.motion = FriendMotion(clock, self.rng)
        self.effects = Effects()
        self.host = CastActor(HOST, self.kit.art, clock, height=150)
        self.big_host = CastActor(HOST, self.kit.art, clock, height=200)
        self.controls = MonsterControls(
            self.kit,
            on_undo=self._on_undo,
            on_surprise=self._on_surprise,
            on_save=self._on_save,
            on_gallery=self.open_gallery,
            on_drawer=self._on_drawer,
            on_tickle=self._on_tickle,
            on_back=self._on_back,
            on_new=self._on_new,
            on_page=self._on_page,
            on_share=self._on_share,
            on_delete=self._on_delete,
        )
        self._surfaces = SurfaceNavigator(self.controls.layer)
        self._input = PygameControlInput(to_logical=canvas.pointer, is_safe=lambda pos: _safe_point(self.screen, pos))
        self._layout_source = ControlLayout.for_canvas(canvas, screen.get_size())

        # The gallery is the authority; load once (never per frame).
        self.gallery = gallery if gallery is not None else storage.load_gallery()
        self.editor = MonsterEditor(draft, blank=False) if draft is not None else MonsterEditor()
        self.drawer = Category.BODY_SHAPE.value
        self.state = Screen.STUDIO
        self.page = 0
        self.open_id: str | None = None
        self.celebrating: MonsterRecipe | None = None
        self.sheet: MonsterSheet | None = None
        self.delete_target: str | None = None

        self.shared_state = ""
        self.shared_until = 0.0
        self._shared_ids: set[str] = set()

        self._running = True
        self.ready_published = False
        self._dirty = True
        self._activated = False
        self._last_activity = clock()
        self._hints = IdleHintScheduler(IdleHintScheduler.DEFAULT_GAPS[:2], now=self._last_activity)
        self._draft_revision = self.editor.revision
        self._draft_changed_at = clock()
        self._hello_at: float | None = clock() + 0.8
        self._layouts: dict[str, object] = {}
        self._build_layouts()
        self._show_studio(focus=None)

    # -- main loop --------------------------------------------------------------------------

    def run(self) -> int:
        frames = FrameGovernor()
        try:
            while self._running and not activity_stop_requested():
                for event in frames.events():
                    self.handle_event(event)
                repeat = self._input.poll()
                if repeat is not None:
                    self._dispatch(repeat)
                animating = self.step_frame()
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
        """Keep the friend being built (Home mid-build) and release audio."""

        self._persist_draft(force=True)
        self.audio.stop()
        self._surfaces.close()

    def step_frame(self) -> bool:
        """Advance timers; return True while something on screen is moving."""

        now = self.clock()
        if self._hello_at is not None and now >= self._hello_at:
            self._hello_at = None
            self._opening()
        for actor in (self.host, self.big_host):
            if actor.update():
                self._dirty = True
        if self.motion.changed():
            self._dirty = True
        self.effects.prune(now)
        if self.shared_state and now >= self.shared_until:
            self.shared_state = ""
        if self.state is Screen.STUDIO and self.sheet is None:
            self._maybe_hint(now)
        if self.editor.revision != self._draft_revision and now - self._draft_changed_at >= DRAFT_SAVE_IDLE:
            self._persist_draft()
        layer_dirty = self.controls.layer.invalidation.should_draw
        if layer_dirty or (self.sheet is not None and self.sheet.layer.invalidation.should_draw):
            self._dirty = True
        actors = self.host.animating or self.big_host.animating
        return self.effects.active(now) or self.motion.reacting or actors

    # -- rendering ----------------------------------------------------------------------------

    def render(self) -> None:
        surface = self.canvas.surface
        frame = self.motion.frame()
        if self.state is Screen.STUDIO:
            layout = self.studio_layout
            self.renderer.draw_studio(
                surface, layout, self.editor.recipe, frame, self.host, self.effects, name_drawer=self.drawer == NAME_DRAWER,
            )
        elif self.state is Screen.GALLERY:
            layout = self.gallery_layout
            self.renderer.draw_gallery(
                surface,
                layout,
                self._page_recipes(),
                page=self.page,
                page_count=self.gallery.page_count(GALLERY_PAGE_SIZE),
                focus_slot=self.controls.focused_card() if self.controls.layer.focus_visible else None,
            )
        else:
            recipe = self._shown_recipe()
            if recipe is not None:
                host = self.big_host if self.state is Screen.CELEBRATE else None
                self.renderer.draw_friend_view(surface, self.friend_layout, recipe, frame, host)
        self.renderer.draw_halos(surface, self.effects, self._halo_rects())
        self._surfaces.draw(surface)
        self.renderer.draw_effects(surface, self.effects)
        self.controls.layer.invalidation.mark_drawn()

    def _halo_rects(self) -> dict[str, pygame.Rect]:
        layout = self.studio_layout
        return {"tray": layout.tray, "save": layout.save, "drawers": layout.drawers[0].unionall(layout.drawers[1:])}

    # -- input -----------------------------------------------------------------------------------

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.QUIT:
            self._running = False
            return
        if event.type == pygame.VIDEORESIZE:
            self._resize()
            return
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self._escape()
            return
        translated = self._input.translate(event)
        if translated is not None:
            self._dispatch(translated)

    def _escape(self) -> None:
        self._note_activity()
        if self.sheet is not None:
            self.sheet.dismiss()
        elif self.state is Screen.FRIEND:
            self.open_gallery()
        elif self.state is Screen.GALLERY:
            self._enter_studio()
        elif self.state is Screen.CELEBRATE:
            self._on_new()
        else:
            self._running = False
        self._dirty = True

    def _resize(self) -> None:
        self.screen = pygame.display.get_surface() or self.screen
        self.canvas = PygameReferenceCanvas(self.screen)
        self._input = PygameControlInput(to_logical=self.canvas.pointer, is_safe=lambda pos: _safe_point(self.screen, pos))
        self._layout_source = ControlLayout.for_canvas(self.canvas, self.screen.get_size())
        self._build_layouts()
        self._close_sheet()
        self._reshow()
        self._dirty = True

    def _dispatch(self, kit_input) -> bool:
        """Route one kit input; True when something consumed it."""

        if not isinstance(kit_input, KitPointer) or kit_input.phase is not PointerPhase.MOVE:
            self._note_activity()
        else:
            self._dirty = True  # keep the Greia pointer (drawn on present) live
        if isinstance(kit_input, SemanticInputEvent) and kit_input.edge is InputEdge.PRESSED and self.sheet is None:
            if kit_input.action is SemanticAction.CANCEL:
                self._escape()
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

    def press(self, key: int) -> None:
        """Deliver one key press + release as SDL would (tests/tools)."""

        self.handle_event(pygame.event.Event(pygame.KEYDOWN, key=key, mod=0, unicode=""))
        self.handle_event(pygame.event.Event(pygame.KEYUP, key=key, mod=0, unicode=""))

    def _note_activity(self) -> None:
        self._last_activity = self.clock()
        self._hints.reset(self._last_activity)

    # -- layouts ---------------------------------------------------------------------------------

    def _build_layouts(self) -> None:
        source = self._layout_source
        protected = source.protected
        button = source.control_height(80, maximum=84)
        self._layouts = {
            "studio": StudioLayout.build(protected, button=button),
            "gallery": GalleryLayout.build(protected, button=button),
            "friend": FriendLayout.build(protected, button=button),
            "sheet": SheetLayout.build(protected),
        }
        self.sheets = MonsterSheets(self.kit, self._layouts["sheet"])  # type: ignore[arg-type]

    @property
    def studio_layout(self) -> StudioLayout:
        return self._layouts["studio"]  # type: ignore[return-value]

    @property
    def gallery_layout(self) -> GalleryLayout:
        return self._layouts["gallery"]  # type: ignore[return-value]

    @property
    def friend_layout(self) -> FriendLayout:
        return self._layouts["friend"]  # type: ignore[return-value]

    def _reshow(self) -> None:
        if self.state is Screen.STUDIO:
            self._show_studio(focus=None)
        elif self.state is Screen.GALLERY:
            self._show_gallery()
        else:
            self._show_friend()

    # -- studio ------------------------------------------------------------------------------------

    def _enter_studio(self) -> None:
        self._close_sheet()
        self.state = Screen.STUDIO
        self.open_id = None
        self.celebrating = None
        self.motion.stop()
        self.effects.bursts.clear()
        self._show_studio(focus=None)
        self._dirty = True

    def _show_studio(self, *, focus: str | None, keep_focus: bool = True) -> None:
        layout = self.studio_layout
        recipe = self.editor.recipe
        icon_size = round(layout.drawers[0].width * 0.74)
        icons: dict[str, tuple[pygame.Surface | None, object]] = {}
        for category in CATEGORY_ORDER:
            icons[category.value] = (
                self.art.drawer_icon(category, recipe, icon_size),
                ("drawer", category.value, recipe.body_shape, recipe.body_color, icon_size),
            )
        icons[NAME_DRAWER] = (self.art.ui("name_tag", icon_size), ("drawer", NAME_DRAWER, icon_size))
        self.controls.show_studio(
            layout,
            drawer_ids=DRAWER_IDS,
            drawer_icons=icons,
            active=self.drawer,
            tiles=self._tiles(),
            surprise_icon=self.kit.art.image("prop.vocab.dice", round(layout.surprise.width * 0.7)),
            gallery_icon=self._gallery_icon(round(layout.gallery.width * 0.72)),
            can_undo=self.editor.can_undo,
            can_save=not self.editor.is_blank,
            monster_rect=body_rect(layout.monster_midbottom, layout.monster_height),
            focus=focus,
            keep_focus=keep_focus,
        )

    def _gallery_icon(self, size: int) -> pygame.Surface | None:
        return self.art.ui("gallery", size)

    def _tiles(self) -> list[TileSpec]:
        layout = self.studio_layout
        if self.drawer == NAME_DRAWER:
            rects = layout.tiles(len(SYLLABLES) + 2)
            size = round(rects[0].width * 0.78)
            tiles = [
                TileSpec(
                    f"syllable.{index}",
                    self.renderer.syllable_icon(syllable, index, size),
                    ("syllable", index, size),
                    (lambda chosen=index: self._on_syllable(chosen)),
                )
                for index, syllable in enumerate(SYLLABLES)
            ]
            tiles.append(TileSpec("name.erase", self.kit.glyph("eraser", round(size * 0.8)), ("erase", size), self._on_erase))
            tiles.append(TileSpec("name.dice", self.kit.art.image("prop.vocab.dice", round(size * 0.9)), ("dice", size), self._on_random_name))
            return tiles
        category = Category(self.drawer)
        options = OPTIONS[category]
        rects = layout.tiles(len(options))
        size = rects[0].width - 10
        recipe = self.editor.recipe
        current = recipe.get(category)
        tiles = []
        for item in options:
            candidate = recipe.with_choice(category, item.option_id)
            tiles.append(
                TileSpec(
                    f"option.{category.value}.{item.option_id}",
                    self.art.preview(candidate, category, size),
                    ("option", candidate.parts_key, category.value, size),
                    (lambda chosen=item.option_id, cat=category: self._on_option(cat, chosen)),
                    selected=item.option_id == current,
                )
            )
        return tiles

    def _on_drawer(self, drawer_id: str) -> None:
        self._activated = True
        if drawer_id == self.drawer:
            return
        self.drawer = drawer_id
        self.audio.play("tick")
        self._show_studio(focus=f"drawer.{drawer_id}", keep_focus=False)
        self._dirty = True

    def _on_option(self, category: Category, option_id: str) -> None:
        self._activated = True
        if not self.editor.choose(category, option_id):
            self.motion.react("boing")
            self._dirty = True
            return
        self._changed(category)
        self._show_studio(focus=f"option.{category.value}.{option_id}", keep_focus=False)

    def _changed(self, category: Category | None) -> None:
        self._draft_touched()
        self.motion.react("boing")
        self.audio.play("squish" if category in SQUISH_CATEGORIES else "boing")
        layout = self.studio_layout
        body = body_rect(layout.monster_midbottom, layout.monster_height)
        self.effects.bursts.append(self.renderer.burst("sparkle", (body.right - 10, body.top + 40)))
        self._dirty = True

    def _on_syllable(self, index: int) -> None:
        self._activated = True
        if not self.editor.add_syllable(SYLLABLES[index]):
            # Three syllables is the longest name: Momo thinks, nothing breaks.
            self.host.try_again()
            self._dirty = True
            return
        self.audio.play(f"syllable.{index}")
        self._draft_touched()
        self.motion.react("boing")
        self._show_studio(focus=f"syllable.{index}", keep_focus=False)
        self._dirty = True

    def _on_erase(self) -> None:
        self._activated = True
        if self.editor.erase_syllable():
            self.audio.play("swish")
            self._draft_touched()
            self._show_studio(focus="name.erase", keep_focus=False)
            self._dirty = True

    def _on_random_name(self) -> None:
        self._activated = True
        self.editor.random_name(self.rng)
        self.audio.play("rattle")
        self._draft_touched()
        self.motion.react("giggle")
        self._show_studio(focus="name.dice", keep_focus=False)
        self._dirty = True

    def _on_undo(self) -> None:
        self._activated = True
        if self.editor.undo():
            self._draft_touched()
            self.motion.react("boing")
            self.audio.play("swish")
            self._show_studio(focus="undo" if self.editor.can_undo else None)
            self._dirty = True

    def _on_surprise(self) -> None:
        self._activated = True
        if self.editor.surprise(self.rng):
            self._changed(None)
            self.audio.play("rattle")
            self.host.correct()
            self._show_studio(focus="surprise", keep_focus=False)

    def _on_tickle(self) -> None:
        self._activated = True
        self.motion.react("giggle")
        self.audio.play("giggle")
        rect = self.controls.monster.rect
        self.effects.bursts.append(self.renderer.burst("heart_pop", (rect.centerx, rect.top + 30)))
        self._dirty = True

    def _on_save(self) -> None:
        self._activated = True
        if self.editor.is_blank:
            self._hint(force=True)
            return
        if self.gallery.is_full:
            self._open_full_sheet()
            return
        recipe = self.editor.recipe.with_identity(self.editor.recipe.portrait_id, int(self._wall_clock()))
        candidate = MonsterGallery(self.gallery.recipes)
        if not candidate.add(recipe):
            recipe = recipe.with_identity(str(uuid.uuid4()), recipe.created_at)
            if not candidate.add(recipe):
                return
        # Commit storage first: a failed save leaves the friend and gallery
        # untouched and never announces a creation.
        if not self.storage.save_gallery(candidate):
            self.host.try_again()
            self._dirty = True
            return
        self.gallery = candidate
        self.events.portrait_created(recipe.portrait_id, recipe)
        self.editor = MonsterEditor()
        self.drawer = Category.BODY_SHAPE.value
        self._draft_revision = self.editor.revision
        self.storage.save_draft(None)
        self._celebrate(recipe)

    def _celebrate(self, recipe: MonsterRecipe) -> None:
        self._close_sheet()
        self.state = Screen.CELEBRATE
        self.celebrating = recipe
        self.open_id = recipe.portrait_id
        self.audio.play("chime")
        self.audio.host_says("saved")
        self.big_host.correct()
        self.motion.react("hop")
        layout = self.friend_layout
        self.effects.bursts.append(self.renderer.burst("confetti", (layout.stage.centerx - 270, layout.stage.top + 110)))
        self.effects.bursts.append(self.renderer.burst("confetti", (layout.stage.centerx + 270, layout.stage.top + 96)))
        self._show_friend()
        self._dirty = True

    def _on_new(self) -> None:
        self._activated = True
        self._enter_studio()

    # -- gallery -----------------------------------------------------------------------------------

    def open_gallery(self) -> None:
        self._activated = True
        self._close_sheet()
        self.state = Screen.GALLERY
        self.motion.stop()
        self.effects.bursts.clear()
        focus = None
        if self.open_id is not None:
            index = self.gallery.index_of(self.open_id)
            if index is not None:
                self.page = index // GALLERY_PAGE_SIZE
                focus = index % GALLERY_PAGE_SIZE
        self.page = max(0, min(self.page, self.gallery.page_count(GALLERY_PAGE_SIZE) - 1))
        self.open_id = None
        self.celebrating = None
        self.audio.play("tick")
        self._show_gallery(focus)
        self._dirty = True

    def _page_recipes(self) -> tuple[MonsterRecipe, ...]:
        return self.gallery.page(self.page, GALLERY_PAGE_SIZE)

    def _show_gallery(self, focus_card: int | None = None) -> None:
        layout = self.gallery_layout
        recipes = self._page_recipes()
        self.controls.show_gallery(
            layout,
            layout.cards[: len(recipes)],
            on_card=self._on_card,
            page=self.page,
            page_count=self.gallery.page_count(GALLERY_PAGE_SIZE),
            used=self.gallery.count,
            capacity=MAX_SAVED_PORTRAITS,
            gallery_icon=self._gallery_icon(round(layout.chip.height * 0.8)),
            focus_card=focus_card,
        )

    def _on_page(self, step: int) -> None:
        self._activated = True
        pages = self.gallery.page_count(GALLERY_PAGE_SIZE)
        page = max(0, min(pages - 1, self.page + step))
        if page != self.page:
            self.page = page
            self.audio.play("tick")
            self._show_gallery(0)
            self.controls.layer.focus("page.next" if step > 0 else "page.previous", visible=self.controls.layer.focus_visible)
            self._dirty = True

    def _on_card(self, slot: int) -> None:
        self._activated = True
        recipes = self._page_recipes()
        if slot >= len(recipes):
            return
        self.open_id = recipes[slot].portrait_id
        self.state = Screen.FRIEND
        self.audio.play("boing")
        self.motion.react("boing")
        self._show_friend()
        self._dirty = True

    def _on_back(self) -> None:
        self._activated = True
        if self.state is Screen.FRIEND:
            self.open_gallery()
        else:
            self._enter_studio()

    # -- one friend --------------------------------------------------------------------------------

    def _shown_recipe(self) -> MonsterRecipe | None:
        if self.state is Screen.CELEBRATE:
            return self.celebrating
        return self.gallery.get(self.open_id) if self.open_id is not None else None

    def _show_friend(self) -> None:
        layout = self.friend_layout
        self.controls.show_friend(
            layout,
            share_available=self.creations is not None,
            celebrating=self.state is Screen.CELEBRATE,
            gallery_icon=self._gallery_icon(round(max(layout.gallery.width, 84) * 0.72)),
            monster_rect=body_rect(layout.monster_midbottom, layout.monster_height),
        )

    def _on_share(self) -> None:
        self._activated = True
        recipe = self._shown_recipe()
        if recipe is None or self.creations is None:
            return
        self.shared_until = self.clock() + FEEDBACK_SECONDS
        actor = self.big_host if self.state is Screen.CELEBRATE else None
        if recipe.portrait_id not in self._shared_ids:
            try:
                picture = encode_surface_png(self.renderer.picture(recipe))
                name = self.storage.private_png_name(recipe.portrait_id, picture)
                self.creations.publish_private_file(name, media_type="image/png", role=SHARE_ROLE, title=recipe.name[:100])
            except (RuntimeError, ValueError, OSError, PygamePngError):
                self.shared_state = "error"
                if actor is not None:
                    actor.try_again()
                self.audio.play("swish")
                self._dirty = True
                return
            self._shared_ids.add(recipe.portrait_id)
        self.shared_state = "saved"
        self.audio.play("chime")
        self.audio.host_says("shared")
        if actor is not None:
            actor.correct()
        self.motion.react("giggle")
        self.effects.bursts.append(self.renderer.burst("star_burst", self.friend_layout.share.center))
        self._dirty = True

    def _on_delete(self) -> None:
        self._activated = True
        recipe = self._shown_recipe()
        if recipe is None or self.sheet is not None:
            return
        self.delete_target = recipe.portrait_id
        layout = self.sheets.layout
        preview = self.art.portrait(recipe, layout.preview.height)

        def backdrop(surface: pygame.Surface) -> None:
            self.renderer.draw_sheet(surface, layout, preview)

        self.sheet = self.sheets.delete(draw_backdrop=backdrop, on_keep=self._keep, on_delete=self._confirm_delete)
        self._surfaces.push_overlay(self.sheet)
        self._dirty = True

    def _keep(self) -> None:
        self._activated = True
        self.delete_target = None
        self._close_sheet()
        self._dirty = True

    def _confirm_delete(self) -> None:
        self._activated = True
        portrait_id = self.delete_target
        self.delete_target = None
        self._close_sheet()
        if portrait_id is None:
            return
        candidate = MonsterGallery(self.gallery.recipes)
        if not candidate.delete(portrait_id):
            return
        # Commit the deletion before presenting it as done.
        if not self.storage.save_gallery(candidate):
            self.motion.react("boing")
            self._dirty = True
            return
        self.gallery = candidate
        self._shared_ids.discard(portrait_id)
        self.audio.play("swish")
        self.open_id = None
        self.state = Screen.GALLERY
        self.page = max(0, min(self.page, self.gallery.page_count(GALLERY_PAGE_SIZE) - 1))
        self._show_gallery(0 if self._page_recipes() else None)
        self._dirty = True

    # -- sheets ----------------------------------------------------------------------------------

    def _open_full_sheet(self) -> None:
        layout = self.sheets.layout
        preview = self.art.portrait(self.editor.recipe, layout.preview.height)

        def backdrop(surface: pygame.Surface) -> None:
            self.renderer.draw_sheet(surface, layout, preview)

        self.host.try_again()
        self.sheet = self.sheets.full(
            gallery_icon=self._gallery_icon(76), draw_backdrop=backdrop, on_gallery=self._full_to_gallery, on_keep=self._keep,
        )
        self._surfaces.push_overlay(self.sheet)
        self._dirty = True

    def _full_to_gallery(self) -> None:
        self._close_sheet()
        self.open_gallery()

    def _close_sheet(self) -> None:
        if self.sheet is not None:
            self._surfaces.pop_overlay()
            self.sheet = None
            self.controls.layer.invalidation.invalidate()

    # -- hints and the host ------------------------------------------------------------------------

    def _opening(self) -> None:
        if self.state is not Screen.STUDIO or not self.editor.is_blank:
            return
        self.audio.host_says("hello")
        self.host.point(HALO_SECONDS)
        self.effects.halos["drawers"] = self.clock() + HALO_SECONDS
        self._dirty = True

    def _maybe_hint(self, now: float) -> None:
        step = self._hints.poll(now, self._last_activity)
        if step:
            self._hint(step)

    def _hint(self, step: int = 1, *, force: bool = False) -> None:
        """Graduated idle help: point at the choices, then at Save (+ voice)."""

        now = self.clock()
        target = "tray" if self.editor.is_blank else "save"
        halo = self._hints.animation_seconds(HALO_SECONDS)
        self.host.point(halo)
        self.effects.halos[target] = now + halo
        if step >= 2 and not force and not self.editor.is_blank:
            self.audio.host_says("nudge")
        self._dirty = True

    # -- drafts ------------------------------------------------------------------------------------

    def _draft_touched(self) -> None:
        self._draft_changed_at = self.clock()

    def _persist_draft(self, *, force: bool = False) -> None:
        if not force and self.editor.revision == self._draft_revision:
            return
        if self.storage.save_draft(None if self.editor.is_blank else self.editor.recipe):
            self._draft_revision = self.editor.revision


__all__ = ["DRAWER_IDS", "MonsterActivity", "Screen", "ViewMode"]
