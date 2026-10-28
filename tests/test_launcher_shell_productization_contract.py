from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
import pygame

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

from greia_launcher.catalogue_view import ActivityCatalogue, ALL_ACTIVITIES_ID
from greia_launcher.child_shell import GreiaChildShell
from greia_launcher.presentation import GreiaLauncherPresentation


def sample_theme() -> SimpleNamespace:
    return SimpleNamespace(
        background=(245, 240, 230),
        panel=(255, 255, 255),
        accent=(66, 133, 244),
        text=(30, 30, 30),
    )


def sample_activity(
    activity_id: str,
    title: str,
    *categories: str,
    launcher_categories: tuple[str, ...] = ("create",),
    discovery_tags: tuple[str, ...] = (),
) -> SimpleNamespace:
    return SimpleNamespace(
        activity_id=activity_id,
        version="1.0.0",
        title_key=title,
        title=title,
        icon_id="palette",
        categories=categories,
        launcher_categories=launcher_categories,
        discovery_tags=discovery_tags,
        difficulty=1,
        recommended_age_min=None,
        recommended_age_max=None,
        adaptive_difficulty=False,
    )


class LauncherShellProductizationContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        pygame.init()
        pygame.font.init()
        pygame.display.set_mode((1024, 600))

    @classmethod
    def tearDownClass(cls) -> None:
        pygame.quit()

    def _sample_activities(self, count: int = 8, category: str = "create") -> list[SimpleNamespace]:
        activities = []
        for i in range(count):
            activities.append(
                sample_activity(
                    f"org.greia.test_act_{i}",
                    f"Attivit\u00e0 Di Prova {i+1}",
                    "creativity",
                    launcher_categories=(category,),
                )
            )
        return activities

    def test_in_category_header_presents_back_and_category_switcher(self) -> None:
        activities = self._sample_activities(count=6, category="create")
        activities.extend(self._sample_activities(count=4, category="play"))
        catalogue = ActivityCatalogue.from_activities(activities)
        shell = GreiaChildShell()
        shell._mode = "activities"
        shell._activities = tuple(activities)
        shell._catalogue = catalogue
        shell._set_category("create")

        screen = pygame.Surface((1024, 600))
        theme = sample_theme()
        shell._render_activities_content(screen, theme, pygame)

        # 1. Back button hit target exists
        back_targets = [t for t in shell._targets if t.action == "activity_category_back"]
        self.assertEqual(len(back_targets), 1)
        self.assertEqual(back_targets[0].value, ALL_ACTIVITIES_ID)

        # 2. Inactive category chips exist for direct category jumping
        cat_targets = [t for t in shell._targets if t.action == "activity_category"]
        cat_values = {t.value for t in cat_targets}
        self.assertIn("play", cat_values)
        self.assertNotIn("create", cat_values)

    def test_pagination_controls_appear_when_activities_exceed_page_capacity(self) -> None:
        # At 1024x600, columns = 3, rows = 2 => capacity = 6
        activities = self._sample_activities(count=10, category="create")
        catalogue = ActivityCatalogue.from_activities(activities)
        shell = GreiaChildShell()
        shell._mode = "activities"
        shell._activities = tuple(activities)
        shell._catalogue = catalogue
        shell._set_category("create")

        screen = pygame.Surface((1024, 600))
        theme = sample_theme()
        shell._render_activities_content(screen, theme, pygame)

        next_targets = [t for t in shell._targets if t.action == "presented_activity_page_next"]
        self.assertEqual(len(next_targets), 1)

        # Dots are pure visual indicators, not click targets
        page_targets = [t for t in shell._targets if t.action == "presented_activity_page"]
        self.assertEqual(len(page_targets), 0)

    def test_pagination_disappears_when_all_activities_fit_on_single_page(self) -> None:
        activities = self._sample_activities(count=5, category="create")
        catalogue = ActivityCatalogue.from_activities(activities)
        shell = GreiaChildShell()
        shell._mode = "activities"
        shell._activities = tuple(activities)
        shell._catalogue = catalogue
        shell._set_category("create")

        screen = pygame.Surface((1024, 600))
        theme = sample_theme()
        shell._render_activities_content(screen, theme, pygame)

        page_targets = [t for t in shell._targets if t.action in {"presented_activity_page_next", "presented_activity_page"}]
        self.assertEqual(len(page_targets), 0)

    def test_pageup_pagedown_key_navigation_scrolls_pages(self) -> None:
        activities = self._sample_activities(count=12, category="create")
        catalogue = ActivityCatalogue.from_activities(activities)
        shell = GreiaChildShell()
        shell._mode = "activities"
        shell._activities = tuple(activities)
        shell._catalogue = catalogue
        shell._set_category("create")
        shell._selected = 0

        # Press PAGE DOWN
        shell._handle_key(pygame.K_PAGEDOWN, pygame)
        self.assertEqual(shell._selected, 6)

        # Press PAGE DOWN again
        shell._handle_key(pygame.K_PAGEDOWN, pygame)
        self.assertEqual(shell._selected, 11)

        # Press PAGE UP
        shell._handle_key(pygame.K_PAGEUP, pygame)
        self.assertEqual(shell._selected, 5)

    def test_selected_and_launching_visual_states_do_not_crash(self) -> None:
        activities = self._sample_activities(count=4, category="create")
        catalogue = ActivityCatalogue.from_activities(activities)
        shell = GreiaChildShell()
        shell._mode = "activities"
        shell._activities = tuple(activities)
        shell._catalogue = catalogue
        shell._set_category("create")
        shell._selected = 0
        shell._launching_activity_id = activities[0].activity_id

        screen = pygame.Surface((1024, 600))
        theme = sample_theme()
        shell._render_activities_content(screen, theme, pygame)
        self.assertIsNotNone(screen)

    def test_responsive_grid_dimensions(self) -> None:
        activities = self._sample_activities(count=8, category="create")
        catalogue = ActivityCatalogue.from_activities(activities)

        for res in [(1024, 600), (1280, 800), (1366, 768)]:
            shell = GreiaChildShell()
            shell._mode = "activities"
            shell._activities = tuple(activities)
            shell._catalogue = catalogue
            shell._set_category("create")
            screen = pygame.Surface(res)
            theme = sample_theme()
            shell._render_activities_content(screen, theme, pygame)
            act_targets = [t for t in shell._targets if t.action == "presented_activity"]
            self.assertTrue(len(act_targets) > 0)
            for t in act_targets:
                self.assertTrue(screen.get_rect().contains(t.rect))

    def test_profile_picker_carries_localized_parent_hold_hint(self) -> None:
        import json

        source = (REPO_ROOT / "src/greia_launcher/main.py").read_text(encoding="utf-8")
        self.assertIn("_draw_parent_hold_hint", source)
        self.assertIn("parent_hold_hint", source)
        for locale in ("en", "it", "es", "fr"):
            catalog = json.loads(
                (REPO_ROOT / f"src/greia_platform/languages/{locale}/ui.json").read_text(
                    encoding="utf-8"
                )
            )
            self.assertTrue(catalog["shell"]["parent_hold_hint"].strip(), locale)

    def test_profile_picker_pagination_targets_and_navigation(self) -> None:
        from unittest.mock import MagicMock

        shell = GreiaChildShell()
        shell._mode = "profiles"
        shell.profiles = [
            MagicMock(
                profile_id=f"p{i}",
                display_name=f"Child {i}",
                avatar_id="unicorn",
                has_secret=False,
            )
            for i in range(10)
        ]
        shell._profile_selected = 0
        screen = pygame.display.get_surface()
        theme = sample_theme()
        shell._render_profile_picker_content(screen, theme, pygame)

        page_targets = [t for t in shell._targets if t.action == "profile_page"]
        # At 1024x600, page_size is 8 (columns=4, max_rows=2). 10 profiles => 2 pages.
        # Next arrow target has value 8 (first profile on page 1).
        # Dots are visual indicators, so only the arrow navigation target is registered.
        self.assertEqual(len(page_targets), 1)
        self.assertEqual([t.value for t in page_targets], [8])

        # Clicking the next arrow sets selection to profile 8 on page 1
        next_target = page_targets[0]
        shell._handle_click(next_target.rect.center, pygame)
        self.assertEqual(shell._profile_selected, 8)


if __name__ == "__main__":
    unittest.main()
