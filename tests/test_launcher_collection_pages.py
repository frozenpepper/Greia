"""Storybook Collection pages, theme folders and the launch wait screen.

Geometry is checked renderer-free at the reference viewports (including the
repair-clearance contract the hover/launch tile repair depends on). Real
``GreiaChildShell`` renders prove the drawn targets, the mixed folder page
(every Activity reachable exactly once, one level deep), folder navigation
and the localized storybook launch overlay. Source tests only: no Simulator,
VM or hardware claim.
"""

from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

REPO_ROOT = Path(__file__).resolve().parents[1]
TMP_DIR = tempfile.mkdtemp()
os.environ["GREIA_PROFILES_DIR"] = os.path.join(TMP_DIR, "profiles")
os.environ["GREIA_SYSTEM_SETTINGS_DIR"] = os.path.join(TMP_DIR, "settings")
os.environ["GREIA_MEDIA_ROOT"] = os.path.join(TMP_DIR, "media")
os.environ["GREIA_ACTIVE_PROFILE_STATUS"] = os.path.join(TMP_DIR, "active-profile.json")
os.environ["GREIA_HARDWARE_STATUS"] = os.path.join(TMP_DIR, "hardware-status.json")
os.environ["GREIA_MAIN_CREDENTIAL_PATH"] = os.path.join(TMP_DIR, "parent-credential.json")
os.environ["GREIA_OS_ROOT"] = str(REPO_ROOT)
os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"

import pygame

from greia_launcher.catalogue_view import (
    FOLDER_THEME_IDS,
    ActivityCatalogue,
    ActivityFolder,
)
from greia_launcher.collection_hues import collection_hue
from greia_launcher.collection_page_layout import (
    CARD_REPAIR_PAD,
    CollectionPageLayout,
    collection_grid_shape,
    page_dot_positions,
)
from greia_launcher.home_layout import achievement_button_rect, usage_pill_band
from greia_launcher.title_presentation import (
    render_full_title_disclosure_surface,
    wrap_title_lines,
)
from greia_platform.activity_discovery import AdaptiveCollectionPlanner
from greia_platform.responsive_layout import UiRect

import hermetic_volume

VIEWPORTS = ((1024, 600), (800, 480), (480, 320), (1280, 800))


def setUpModule() -> None:
    hermetic_volume.install_for_module()


def _layout(width: int, height: int) -> tuple[CollectionPageLayout, UiRect]:
    badge_size = max(62, min(86, height // 7))
    badge = UiRect(14, 10, badge_size, badge_size)
    star = max(58, min(76, height // 8))
    return (
        CollectionPageLayout.compute(width, height, profile_badge=badge, right_reserve=star + 28),
        badge,
    )


def _sample(activity_id: str, *tags: str, collections: tuple[str, ...] = ("play",)) -> SimpleNamespace:
    return SimpleNamespace(
        activity_id=activity_id,
        version="1.0.0",
        title_key=activity_id,
        title=activity_id,
        icon_id="palette",
        categories=("creativity",),
        launcher_categories=collections,
        discovery_tags=tags,
        difficulty=1,
        recommended_age_min=None,
        recommended_age_max=None,
        adaptive_difficulty=False,
    )


class CollectionPageLayoutTests(unittest.TestCase):
    def test_cards_are_big_and_inside_the_screen(self) -> None:
        for width, height in VIEWPORTS:
            with self.subTest(viewport=(width, height)):
                layout, _badge = _layout(width, height)
                self.assertEqual((layout.columns, layout.rows), collection_grid_shape(width, height))
                screen = UiRect(0, 0, width, height)
                for rect in layout.hits + (layout.previous, layout.next, layout.dots, layout.back):
                    self.assertTrue(screen.contains(rect), rect)
                minimum = 150 if (width, height) == (1024, 600) else 90
                self.assertGreaterEqual(layout.card_width, minimum)
        self.assertEqual(_layout(1024, 600)[0].capacity, 6)
        self.assertEqual(_layout(480, 320)[0].capacity, 3)

    def test_repair_regions_never_touch_other_owners(self) -> None:
        """A card's hover/launch repair restores hit.inflate(CARD_REPAIR_PAD)."""

        for width, height in VIEWPORTS:
            with self.subTest(viewport=(width, height)):
                layout, badge = _layout(width, height)
                others = [layout.header_band, layout.previous, layout.next, layout.dots, badge]
                for index, hit in enumerate(layout.hits):
                    region = UiRect(
                        hit.x - CARD_REPAIR_PAD[0] // 2,
                        hit.y - CARD_REPAIR_PAD[1] // 2,
                        hit.width + CARD_REPAIR_PAD[0],
                        hit.height + CARD_REPAIR_PAD[1],
                    )
                    for other in others:
                        self.assertFalse(region.intersects(other), (hit, other))
                    for neighbour_index, neighbour in enumerate(layout.hits):
                        if neighbour_index != index:
                            self.assertFalse(region.intersects(neighbour), (hit, neighbour))

    def test_page_dots_are_bounded(self) -> None:
        self.assertEqual(page_dot_positions(1, 0), (0, 0))
        self.assertEqual(page_dot_positions(6, 5), (6, 5))
        count, active = page_dot_positions(40, 39)
        self.assertEqual((count, active), (12, 11))


LONG_TITLES = (
    "Super Avventura Spaziale dei Draghetti nel Regno delle Fiabe Incantate",
    "La bottega delle meraviglie di Greia e dei suoi amici",
    "Supercalifragilistichespiralidosissimo",
    "Enciclopedia di Greia",
    "The Great Adventure of the Tiny Dragon in Storybook Land",
    "Ok",
)


class TitleDisclosureGeometryTests(unittest.TestCase):
    """The hover title must never cover another caption or protected chrome."""

    @classmethod
    def setUpClass(cls) -> None:
        pygame.init()
        pygame.font.init()

    def test_tooltip_covers_only_its_own_caption_at_every_card_position(self) -> None:
        theme = SimpleNamespace(panel=(250, 246, 238), accent=(239, 77, 83), text=(33, 37, 41))
        for width, height in VIEWPORTS:
            layout, badge = _layout(width, height)
            screen = UiRect(0, 0, width, height)
            star = achievement_button_rect(width, height)
            usage = usage_pill_band(width, height, left_limit=layout.back.right)
            font_px = max(12, min(15, layout.label_font_px))
            font = pygame.font.Font(None, font_px + 4)
            chrome = [
                layout.header_band,
                layout.back,
                layout.previous,
                layout.next,
                layout.dots,
                badge,
                star,
                usage,
            ]
            for index in range(layout.capacity):
                zone = layout.title_disclosure_zone(index)
                self.assertEqual(zone.cover, layout.labels[index])
                for title in LONG_TITLES:
                    with self.subTest(viewport=(width, height), card=index, title=title[:18]):
                        pill = render_full_title_disclosure_surface(
                            title,
                            font=font,
                            theme=theme,
                            max_width=zone.bounds.width,
                            pygame=pygame,
                            max_lines=2,
                            min_size=(zone.cover.width, zone.cover.height),
                        )
                        rect = zone.place(*pill.get_size())
                        self.assertTrue(screen.contains(rect), rect)
                        self.assertLessEqual(rect.width, zone.bounds.width)
                        self.assertGreaterEqual(rect.width, zone.cover.width)
                        # Hides its own caption entirely (no stale text peeks out).
                        self.assertTrue(rect.contains(zone.cover), (rect, zone.cover))
                        for other_index, other in enumerate(layout.labels):
                            if other_index != index:
                                self.assertFalse(rect.intersects(other), (index, other_index))
                        for other_index, hit in enumerate(layout.cards):
                            if other_index != index:
                                self.assertFalse(rect.intersects(hit), (index, other_index))
                        # Never above the caption: its own card art stays visible.
                        self.assertGreaterEqual(rect.y, layout.cards[index].bottom)
                        for protected in chrome:
                            self.assertFalse(rect.intersects(protected), (rect, protected))

    def test_long_titles_wrap_to_at_most_two_lines_with_ellipsis(self) -> None:
        font = pygame.font.Font(None, 20)
        for title in LONG_TITLES:
            for usable in (60, 110, 180):
                with self.subTest(title=title[:18], usable=usable):
                    lines = wrap_title_lines(font, title, usable, 2)
                    self.assertLessEqual(len(lines), 2)
                    for line in lines:
                        self.assertLessEqual(font.size(line)[0], usable)
        short = wrap_title_lines(font, "Ok", 180, 2)
        self.assertEqual(short, ["Ok"])
        self.assertTrue(wrap_title_lines(font, LONG_TITLES[0], 110, 2)[-1].endswith("\u2026"))

    def test_tooltip_surface_is_cached_per_title_and_size(self) -> None:
        theme = SimpleNamespace(panel=(250, 246, 238), accent=(239, 77, 83), text=(33, 37, 41))
        font = pygame.font.Font(None, 20)
        first = render_full_title_disclosure_surface(
            LONG_TITLES[1], font=font, theme=theme, max_width=160, pygame=pygame, max_lines=2
        )
        again = render_full_title_disclosure_surface(
            LONG_TITLES[1], font=font, theme=theme, max_width=160, pygame=pygame, max_lines=2
        )
        self.assertIs(first, again)


class ThemeFolderPlanningTests(unittest.TestCase):
    def test_folder_needs_enough_members_and_never_swallows_the_page(self) -> None:
        planner = AdaptiveCollectionPlanner()
        two = [_sample("a", "sea"), _sample("b", "sea"), _sample("c")]
        self.assertEqual(planner.plan_theme_folders("play", two, folder_theme_ids=("sea",)).folders, ())
        only_sea = [_sample(f"s{i}", "sea") for i in range(4)]
        self.assertEqual(planner.plan_theme_folders("play", only_sea, folder_theme_ids=("sea",)).folders, ())
        mixed = only_sea + [_sample("x"), _sample("y", "nature")]
        plan = planner.plan_theme_folders("play", mixed, folder_theme_ids=("sea",))
        self.assertEqual([f.group_id for f in plan.folders], ["sea"])
        self.assertEqual([a.activity_id for a in plan.folders[0].activities], ["s0", "s1", "s2", "s3"])
        self.assertEqual([a.activity_id for a in plan.direct], ["x", "y"])

    def test_catalogue_page_lists_folder_first_and_every_activity_once(self) -> None:
        items = [_sample(f"s{i}", "sea") for i in range(3)] + [_sample(f"p{i}") for i in range(5)]
        catalogue = ActivityCatalogue.from_activities(items)
        entries = catalogue.page_entries("play")
        self.assertIsInstance(entries[0], ActivityFolder)
        self.assertEqual(entries[0].folder_id, "sea")
        reachable = [a.activity_id for a in entries[0].items] + [
            e.activity_id for e in entries[1:]
        ]
        self.assertEqual(sorted(reachable), sorted(a.activity_id for a in items))
        self.assertEqual(len(reachable), len(set(reachable)))
        # One level deep: a folder's contents are Activities, never folders.
        self.assertFalse(any(isinstance(a, ActivityFolder) for a in entries[0].items))
        self.assertIs(catalogue.subcollection("play", "sea"), entries[0].group)
        # The Collection itself still owns every Activity.
        self.assertEqual(len(catalogue.collection("play").items), 8)
        self.assertIn("sea", FOLDER_THEME_IDS)

    def test_without_folders_the_page_is_the_collection(self) -> None:
        items = [_sample(f"p{i}") for i in range(9)]
        catalogue = ActivityCatalogue.from_activities(items)
        self.assertEqual(catalogue.page_entries("play"), catalogue.collection("play").items)


class _ShellCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        pygame.init()
        pygame.font.init()

    def _shell(self, size: tuple[int, int] = (1024, 600)):
        from greia_launcher.child_shell import GreiaChildShell

        screen = pygame.display.set_mode(size)
        shell = GreiaChildShell(windowed=True)
        if shell._visual_cache is None:
            self.skipTest("shared visuals unavailable in this checkout")
        shell.profiles = shell.profile_store.ensure_initialized()
        shell._activate_profile(shell.profiles[0], pygame)
        return shell, screen

    def _use_catalogue(self, shell, items) -> None:
        shell._catalogue = ActivityCatalogue.from_activities(items)
        shell._set_category("play")
        shell._cached_activities_key = None


class CollectionPageRenderTests(_ShellCase):
    def test_storybook_page_targets_and_art(self) -> None:
        for size in VIEWPORTS:
            with self.subTest(viewport=size):
                shell, screen = self._shell(size)
                shell._set_category("play")
                shell._draw(screen, pygame)
                self.assertFalse(shell._collection_page_disabled)
                cards = [t for t in shell._targets if t.action == "presented_activity"]
                layout = shell._collection_page_layout
                self.assertEqual(len(cards), min(layout.capacity, len(shell._presented_activities)))
                self.assertEqual(
                    [t.rect.topleft for t in cards],
                    [(h.x, h.y) for h in layout.hits[: len(cards)]],
                )
                self.assertTrue(any(t.action == "activity_category_back" for t in shell._targets))
                self.assertTrue(any(t.action == "activity_category" for t in shell._targets))

    def test_hover_title_never_overlaps_neighbouring_captions(self) -> None:
        """Rendered check: hovering a card leaves every other caption pixel-identical."""

        for size in ((1024, 600), (800, 480)):
            shell, screen = self._shell(size)
            items = [_sample(f"org.test.long{i}", collections=("play",)) for i in range(6)]
            for item, title in zip(items, LONG_TITLES):
                item.title_key = title
            self._use_catalogue(shell, items)
            shell._synthetic_pointer_active = False
            shell._pointer_position = (0, 0)
            shell._draw(screen, pygame)
            layout = shell._collection_page_layout

            def captions(skip: int) -> list[bytes]:
                return [
                    pygame.image.tobytes(screen.subsurface(pygame.Rect(l.x, l.y, l.width, l.height)), "RGB")
                    for i, l in enumerate(layout.labels)
                    if i != skip
                ]

            for index in range(layout.capacity):
                with self.subTest(viewport=size, card=index):
                    shell._synthetic_pointer_active = False
                    shell._pointer_position = (0, 0)
                    shell._cached_activities_key = None
                    shell._draw(screen, pygame)
                    before = captions(index)
                    hit = layout.hits[index]
                    shell._synthetic_pointer_active = True
                    shell._pointer_position = (hit.x + hit.width // 2, hit.y + hit.height // 3)
                    shell._cached_activities_key = None
                    shell._draw(screen, pygame)
                    # Boolean compare: a bytes diff of full captions is enormous.
                    self.assertTrue(before == captions(index), "another caption was covered")

    def test_installed_sea_activities_share_one_folder(self) -> None:
        shell, screen = self._shell()
        folders = shell._catalogue.folders_for("explore")
        self.assertEqual([f.collection_id for f in folders], ["sea"])
        self.assertEqual(
            {a.activity_id for a in folders[0].items},
            {
                "org.greia.acquario-magico",
                "org.greia.baia-delle-orche",
                "org.greia.sottomarino-giramondo",
                "org.greia.viaggio-delfino",
            },
        )
        shell._set_category("explore")
        shell._draw(screen, pygame)
        self.assertIsInstance(shell._presented_activities[0], ActivityFolder)

    def test_missing_card_art_falls_back_to_the_proven_page(self) -> None:
        shell, screen = self._shell()
        shell._set_category("play")
        real_get = shell._visual_cache.get

        def broken(asset_id, **kwargs):
            if asset_id == "ui.card.activity_tile":
                raise FileNotFoundError(asset_id)
            return real_get(asset_id, **kwargs)

        shell._visual_cache.get = broken
        try:
            shell._draw(screen, pygame)
        finally:
            shell._visual_cache.get = real_get
        self.assertTrue(shell._collection_page_disabled)
        self.assertTrue(any(t.action == "presented_activity" for t in shell._targets))
        self.assertEqual(
            len([t for t in shell._targets if t.action == "activity_category_back"]), 1
        )

    def test_page_hue_follows_the_collection(self) -> None:
        self.assertEqual(collection_hue("play"), "ocean")
        self.assertEqual(collection_hue("explore", group_id="sea"), "leaf")
        self.assertEqual(collection_hue("play", group_id="music"), "default")


class ThemeFolderShellTests(_ShellCase):
    def _folder_shell(self):
        shell, screen = self._shell()
        items = [_sample(f"org.test.sea{i}", "sea") for i in range(3)] + [
            _sample(f"org.test.p{i}") for i in range(4)
        ]
        self._use_catalogue(shell, items)
        return shell, screen

    def test_folder_tile_opens_one_level_and_back_restores_focus(self) -> None:
        shell, screen = self._folder_shell()
        shell._draw(screen, pygame)
        entries = shell._presented_activities
        self.assertIsInstance(entries[0], ActivityFolder)
        self.assertEqual(len(entries), 5)
        launched: list[object] = []
        shell._launch_selected = lambda pg: launched.append(shell._selected)  # type: ignore[method-assign]
        shell._selected = 0
        shell._handle_key(pygame.K_RETURN, pygame)
        self.assertEqual(shell._subcollection_id, "sea")
        self.assertEqual([a.activity_id for a in shell._presented_activities],
                         ["org.test.sea0", "org.test.sea1", "org.test.sea2"])
        self.assertEqual(launched, [])
        shell._draw(screen, pygame)
        self.assertFalse(any(
            isinstance(e, ActivityFolder) for e in shell._presented_activities
        ))
        shell._handle_key(pygame.K_BACKSPACE, pygame)
        self.assertIsNone(shell._subcollection_id)
        self.assertEqual(shell._selected, 0)
        self.assertIsInstance(shell._presented_activities[shell._selected], ActivityFolder)

    def test_clicking_a_folder_opens_it_and_never_launches(self) -> None:
        shell, screen = self._folder_shell()
        shell._draw(screen, pygame)
        folder_target = next(
            t for t in shell._targets if t.action == "presented_activity" and t.value == 0
        )
        shell._handle_click(folder_target.rect.center, pygame)
        self.assertEqual(shell._subcollection_id, "sea")
        self.assertIsNone(shell._last_result)

    def test_folder_is_spoken_as_its_theme_not_as_an_activity(self) -> None:
        shell, screen = self._folder_shell()
        shell._draw(screen, pygame)
        identity, _clip = shell._speakable_for_target(("presented_activity", 0))
        self.assertEqual(identity, "collection:sea")
        # Activity cards keep their own (package) narration path.
        self.assertNotEqual(
            shell._speakable_for_target(("presented_activity", 1)), ("collection:sea", None)
        )


class StorybookLaunchOverlayTests(_ShellCase):
    def test_overlay_is_localized_composed_once_and_animated_cheaply(self) -> None:
        from greia_launcher.launch_feedback import launch_feedback

        shell, screen = self._shell()
        shell._set_category("play")
        shell._selected = 0
        calls: list[int] = []
        compose = shell._compose_launch_overlay

        def counted(*args, **kwargs):
            calls.append(1)
            return compose(*args, **kwargs)

        shell._compose_launch_overlay = counted  # type: ignore[method-assign]
        text = launch_feedback(shell._active_locale).overlay
        shell._draw_launch_overlay(pygame, text=text)
        shell._draw_launch_overlay(pygame, text=text)
        self.assertEqual(len(calls), 1)
        self.assertFalse(getattr(shell, "_storybook_launch_disabled", False))
        key, _composed = shell._launch_overlay_cache
        self.assertIn(shell._child_display_text(text), key)


if __name__ == "__main__":
    unittest.main()
