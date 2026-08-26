"""Application coordinator, lifecycle and input loop for Il Viaggio del Delfino.

The app owns composition and the child-facing loop only: domain simulation
lives in ``delfino_model``, presentation in ``delfino_renderer``/``delfino_art``,
audio in ``delfino_audio`` and platform seams in ``delfino_services``.
"""

from __future__ import annotations

from pathlib import Path
import random
import time

import pygame

from greia_platform.activity_api import (
    activity_stop_requested,
    get_profile_locale,
    get_theme,
    mark_activity_ready,
)
from greia_platform.activity_ui import is_home_clicked
from greia_platform.localization import (
    ActivityLocaleSupport,
    LocalizedResources,
    resolve_activity_locale,
)
from greia_platform.pygame_canvas import (
    PygameReferenceCanvas,
    activity_viewport_for_surface,
)
from greia_platform.pygame_completion import (
    CompletionContent,
    PygameCompletionScreen,
)
from greia_platform.typography import GreiaTypography

try:
    from delfino_art import DelfinoArtLibrary
    from delfino_audio import PygameDelfinoAudio
    from delfino_content import (
        CHAPTERS,
        FACT_IDS,
        TOTAL_JOURNEY_X,
        caption_key,
    )
    from delfino_model import JourneyState, REFERENCE_HEIGHT, REFERENCE_WIDTH
    from delfino_renderer import HudView, TITO_RECT, DelfinoRenderer
    from delfino_services import GreiaDelfinoEvents, GreiaDelfinoStorage
except ImportError:  # repository/package import context
    from .delfino_art import DelfinoArtLibrary
    from .delfino_audio import PygameDelfinoAudio
    from .delfino_content import (
        CHAPTERS,
        FACT_IDS,
        TOTAL_JOURNEY_X,
        caption_key,
    )
    from .delfino_model import JourneyState, REFERENCE_HEIGHT, REFERENCE_WIDTH
    from .delfino_renderer import HudView, TITO_RECT, DelfinoRenderer
    from .delfino_services import GreiaDelfinoEvents, GreiaDelfinoStorage


WELCOME_FACT_ID = "presenter.welcome"
#: Caption stays visible at least this long even for very short clips.
MIN_FACT_SECONDS = 4.5
#: Celebration banner lifetime in seconds.
BANNER_SECONDS = 3.2


def _is_safe_point(surface: pygame.Surface, position: tuple[int, int]) -> bool:
    """Reject pointers inside Greia's protected system-chrome region."""

    vp = activity_viewport_for_surface(surface)
    x, y = position
    if not (0 <= x < vp.surface.width and 0 <= y < vp.surface.height):
        return False
    for protected in vp.protected_regions:
        if protected.x <= x < protected.right and protected.y <= y < protected.bottom:
            return False
    return True


class DelfinoJourneyApp:
    """Greia Activity application for Il Viaggio del Delfino."""

    def __init__(self) -> None:
        screen = pygame.display.get_surface()
        if screen is None:
            pygame.init()
            screen = pygame.display.set_mode(
                (REFERENCE_WIDTH, REFERENCE_HEIGHT), pygame.FULLSCREEN
            )
        self.screen = screen
        self.canvas = PygameReferenceCanvas(screen)
        pygame.mouse.set_visible(False)

        self.world = JourneyState()
        self.art = DelfinoArtLibrary()
        self.audio = PygameDelfinoAudio()
        self.typography = GreiaTypography()
        self.renderer = DelfinoRenderer(self.art, self.typography)
        self.events_service = GreiaDelfinoEvents()
        self.storage = GreiaDelfinoStorage()
        self.completion_screen: PygameCompletionScreen | None = None

        self._resources: LocalizedResources | None = None
        self._active_locale = "it"
        self._init_localization()
        if self._resources is not None:
            self.audio.bind_resources(self._resources)

        # Eagerly prepare every localized runtime asset so celebration
        # moments (star pickups, chapter banners) never hitch on the
        # low-resource reference hardware: voice decodes, banner fonts and
        # fact caption panels are all built before the first frame.
        self.audio.preload_voice([WELCOME_FACT_ID] + list(FACT_IDS))
        for chapter in CHAPTERS:
            self.renderer.warm_banner(self._text(chapter.name_key))
        for fact_id in FACT_IDS:
            self.renderer.warm_caption(self._caption_for(fact_id))
        self.renderer.warm_caption(self._caption_for(WELCOME_FACT_ID))

        loaded = self.storage.load_progress()
        self._lifetime_pearls_base = loaded["total_pearls"]
        self.best_journey_score = loaded["best_journey_score"]

        #: Shuffle-bag so facts never repeat until the pool is exhausted.
        self._fact_bag: list[str] = []
        self._last_fact: str | None = None
        self._active_fact: str | None = None
        self._fact_until = 0.0
        self._banner_until = 0.0
        self._banner_text: str | None = None
        self._rng = random.Random()

    # -------------------------------------------------------- localization

    def _init_localization(self) -> None:
        package_root = Path(__file__).parent
        support = ActivityLocaleSupport.localized(("it", "en"), default_ui_locale="it")
        try:
            profile_lang = get_profile_locale()
            context = resolve_activity_locale(profile_lang, support)
            self._resources = LocalizedResources(package_root, context) if context else None
            self._active_locale = context.selected.language if context else "it"
        except Exception:
            self._resources = None
            self._active_locale = "it"

    def _text(self, key: str, variables: dict[str, object] | None = None) -> str:
        if self._resources is not None:
            try:
                return self._resources.text(key, variables)
            except Exception:
                pass
        return ""

    # -------------------------------------------------------------- journey

    def start_new_journey(self) -> None:
        self.world.start_journey(self._rng)
        self.completion_screen = None
        self._banner_text = None
        self._banner_until = 0.0
        self._dismiss_fact()

    def _persist(self) -> None:
        self.storage.save_progress(
            self._lifetime_pearls_base + self.world.session_pearls,
            self.best_journey_score,
        )

    def _handle_world_event(self, event: str) -> None:
        if event == "pearl_collected":
            self.audio.play("pearl")
        elif event == "starfish_collected":
            self.audio.play("star")
            # Special treasure: Tito shares a curiosity fact — but only when
            # no fact is already speaking, so cues always finish and extra
            # stars still score.
            if self._active_fact is None:
                self._present_fact()
        elif event == "splash_out":
            self.audio.play("splash")
        elif event == "splash_in":
            self.audio.play("splash")
        elif event == "jelly_bounce":
            self.audio.play("boing")
        elif event == "chapter_completed":
            number = self.world.chapters_completed
            self.events_service.chapter_completed(number)
            if number < len(CHAPTERS):
                self.audio.play("victory")
                self._banner_text = self._text(CHAPTERS[number - 1].name_key)
                self._banner_until = time.monotonic() + BANNER_SECONDS
        elif event == "journey_finished":
            self.audio.play("victory")
            score = int(self.world.chapter_value)
            if score > self.best_journey_score:
                self.best_journey_score = score
            self.events_service.journey_score(score)
            self._prepare_completion(score)
        # splash/pearl/etc. never touch durable state here; persistence happens
        # on chapter boundaries, journey end and exit.

    def _prepare_completion(self, score: int) -> None:
        title = self._text("completion.title")
        replay = self._text("completion.replay")
        body = self._text("completion.body", {"count": self.world.session_pearls})
        self.completion_screen = PygameCompletionScreen(self.typography)
        self.completion_screen.prepare(
            CompletionContent(title=title or "BRAVO!", primary_label=replay or "ANCORA!", body_lines=(body,))
        )
        self._persist()

    # ----------------------------------------------------------------- facts

    def _caption_for(self, fact_id: str) -> str:
        key = (
            f"{WELCOME_FACT_ID}.caption"
            if fact_id == WELCOME_FACT_ID
            else caption_key(fact_id)
        )
        return self._text(key)

    def _toggle_fact(self) -> None:
        if self._active_fact is not None:
            self._dismiss_fact()
            return
        self._present_fact()

    def _present_fact(self) -> None:
        """Start a new Tito fact cue, replacing any active one."""

        fact_id = self._draw_from_bag()
        duration = self.audio.play_voice(fact_id)
        self._active_fact = fact_id
        self._fact_until = time.monotonic() + max(MIN_FACT_SECONDS, duration) + 0.8
        self.events_service.fact_opened(fact_id)

    def _dismiss_fact(self) -> None:
        if self._active_fact is not None:
            self.audio.stop_voice()
            self._active_fact = None
            self._fact_until = 0.0

    def _draw_from_bag(self) -> str:
        """Shuffle-bag selection that avoids immediate repetition."""

        if not self._fact_bag:
            self._fact_bag = list(FACT_IDS)
            self._rng.shuffle(self._fact_bag)
            if self._fact_bag and self._fact_bag[0] == self._last_fact and len(self._fact_bag) > 1:
                self._fact_bag[0], self._fact_bag[1] = self._fact_bag[1], self._fact_bag[0]
        fact_id = self._fact_bag.pop(0)
        self._last_fact = fact_id
        return fact_id

    # -------------------------------------------------------------- lifecycle

    def run(self) -> int:
        screen = self.screen
        canvas = self.canvas
        clock = pygame.time.Clock()
        theme = get_theme()

        self.start_new_journey()
        # Greet the swimmer once with Tito's short welcome cue.
        self._toggle_welcome()

        running = True
        ready_published = False
        previous_time = time.monotonic()

        while running and not activity_stop_requested():
            now = time.monotonic()
            dt = min(0.1, max(0.001, now - previous_time))
            previous_time = now

            running = self._handle_events(screen, canvas, running, dt)

            if self.completion_screen is None:
                for event in self.world.update(dt, self._rng):
                    self._handle_world_event(event)
                if self._banner_text and now > self._banner_until:
                    self._banner_text = None
                if self._active_fact and now > self._fact_until:
                    self._active_fact = None

                surf = canvas.surface
                self.renderer.render_world(surf, self.world)
                fraction = min(1.0, self.world.dolphin.x / TOTAL_JOURNEY_X)
                self.renderer.draw_hud(
                    surf,
                    HudView(
                        pearls_count=self.world.session_pearls,
                        journey_fraction=fraction,
                        banner_text=self._banner_text,
                        fact_caption=(
                            self._caption_for(self._active_fact)
                            if self._active_fact
                            else None
                        ),
                        tito_speaking=self._active_fact is not None,
                    ),
                )
            else:
                # Terminal frame: no live simulation under the opaque overlay.
                surf = canvas.surface
                surf.fill((24, 82, 134))
                assert self.completion_screen is not None
                self.completion_screen.draw(surf)

            canvas.present(clear=theme.background)
            pygame.display.flip()

            if not ready_published:
                mark_activity_ready()
                ready_published = True

            clock.tick(30)

        self._persist()
        self.audio.shutdown()
        pygame.quit()
        return 0

    def _toggle_welcome(self) -> None:
        duration = self.audio.play_voice(WELCOME_FACT_ID)
        self._active_fact = WELCOME_FACT_ID
        self._fact_until = time.monotonic() + max(MIN_FACT_SECONDS, duration) + 0.8

    # ------------------------------------------------------------------ input

    def _handle_events(
        self,
        screen: pygame.Surface,
        canvas: PygameReferenceCanvas,
        running: bool,
        dt: float,
    ) -> bool:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key in (pygame.K_UP, pygame.K_w):
                    self.world.dolphin.steer(-26.0)
                elif event.key in (pygame.K_DOWN, pygame.K_s):
                    self.world.dolphin.steer(26.0)
                elif event.key in (pygame.K_SPACE, pygame.K_RETURN, pygame.K_KP_ENTER):
                    if self.completion_screen is None:
                        self.world.dolphin.trigger_dash()
                        self.audio.play("whoosh")
                    else:
                        self._replay()
            elif event.type == pygame.MOUSEMOTION:
                if self.completion_screen is None and _is_safe_point(screen, event.pos):
                    logical = canvas.pointer(event.pos)
                    if logical is not None:
                        _, ly = logical
                        self.world.dolphin.target_y = ly
            elif event.type == pygame.VIDEORESIZE:
                new_screen = pygame.display.get_surface()
                if new_screen is not None:
                    self.screen = new_screen
                    self.canvas = PygameReferenceCanvas(new_screen)
            elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                if is_home_clicked(screen, event.pos):
                    running = False
                    continue
                if not _is_safe_point(screen, event.pos):
                    continue
                logical = canvas.pointer(event.pos)
                if logical is None:
                    continue
                lx, ly = logical
                if self.completion_screen is not None:
                    assert self.completion_screen is not None
                    if self.completion_screen.primary_contains((lx, ly)):
                        self._replay()
                elif TITO_RECT.collidepoint(lx, ly):
                    self.audio.play("pop")
                    self._toggle_fact()
                else:
                    self.world.dolphin.trigger_dash()
                    self.audio.play("whoosh")

        # Continuous keyboard steering (semantic directional profile).
        keys = pygame.key.get_pressed()
        step = 430.0 * dt
        if keys[pygame.K_UP] or keys[pygame.K_w]:
            self.world.dolphin.steer(-step)
        elif keys[pygame.K_DOWN] or keys[pygame.K_s]:
            self.world.dolphin.steer(step)
        return running

    def _replay(self) -> None:
        # Lifetime pearls already persisted at journey end; refresh the base
        # so the new session adds on top of the stored value.
        self._lifetime_pearls_base = self.storage.load_progress()["total_pearls"]
        self.start_new_journey()
        self._toggle_welcome()


def main() -> int:
    app = DelfinoJourneyApp()
    return app.run()


if __name__ == "__main__":
    raise SystemExit(main())
