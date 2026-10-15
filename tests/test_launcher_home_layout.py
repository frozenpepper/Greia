"""Collection Home / profile picker storybook layout contract.

Geometry is checked renderer-free at the reference viewports; one real
``GreiaChildShell`` render per viewport proves the drawn Home targets match
that geometry, never cover the protected corner controls and that the shared
portal/scene/cast artwork is actually consumed.
"""

from __future__ import annotations

import os
import tempfile
import tomllib
import unittest
from pathlib import Path

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

from greia_launcher.collection_home_presentation import _COLLECTION_PORTAL_HUES
from greia_launcher.home_layout import (
    PORTAL_BODY_FRACTION,
    CollectionHomeLayout,
    greeter_rect,
)
from greia_launcher.profile_chrome_presentation import (
    greeter_character_for,
    profile_portal_hue,
)
from greia_platform.activity_ui import ChildUiMetrics
from greia_platform.responsive_layout import UiRect

import hermetic_volume

VIEWPORTS = ((1024, 600), (800, 480), (480, 320), (1280, 800), (640, 360))
SOURCE_SPEC = REPO_ROOT / "assets" / "catalog" / "shared_visuals_v1_source.toml"


def setUpModule() -> None:
    hermetic_volume.install_for_module()


def _corners(width: int, height: int) -> tuple[UiRect, UiRect]:
    badge = max(62, min(86, height // 7))
    star = max(58, min(76, height // 8))
    return UiRect(14, 10, badge, badge), UiRect(width - star - 14, 10, star + 4, star + 4)


class CollectionHomeLayoutGeometryTests(unittest.TestCase):
    def _layout(self, width: int, height: int) -> CollectionHomeLayout:
        return CollectionHomeLayout.compute(
            width, height, 6, 3, reserved=_corners(width, height)
        )

    def test_six_portals_fit_without_overlap_at_every_reference_viewport(self) -> None:
        for width, height in VIEWPORTS:
            with self.subTest(viewport=(width, height)):
                layout = self._layout(width, height)
                screen = UiRect(0, 0, width, height)
                self.assertEqual((layout.columns, layout.rows), (3, 2))
                shapes = list(layout.hits) + list(layout.labels)
                for rect in shapes:
                    self.assertTrue(screen.contains(rect), rect)
                for i, a in enumerate(layout.hits):
                    for b in layout.hits[i + 1:]:
                        self.assertFalse(a.intersects(b))
                for i, a in enumerate(layout.labels):
                    for j, b in enumerate(layout.labels):
                        if i != j:
                            self.assertFalse(a.intersects(b), "captions collide")
                    for j, portal in enumerate(layout.portals):
                        self.assertFalse(a.intersects(portal), "caption covers a portal")
                for corner in _corners(width, height):
                    for rect in shapes:
                        self.assertFalse(rect.intersects(corner), "covers a corner control")

    def test_portals_are_big_tactile_targets(self) -> None:
        layout = self._layout(1024, 600)
        self.assertGreaterEqual(
            round(layout.portal_width * PORTAL_BODY_FRACTION), 120
        )
        for width, height in VIEWPORTS:
            with self.subTest(viewport=(width, height)):
                layout = self._layout(width, height)
                floor = ChildUiMetrics.for_size(width, height).button_size
                body = round(layout.portal_width * PORTAL_BODY_FRACTION)
                self.assertGreaterEqual(body, max(floor, 64))
                self.assertGreaterEqual(layout.label_font_px, 14)

    def test_greeter_stands_in_free_margin_and_never_covers_targets(self) -> None:
        for width, height in VIEWPORTS:
            with self.subTest(viewport=(width, height)):
                layout = self._layout(width, height)
                if width >= 800:
                    self.assertIsNotNone(layout.greeter)
                if layout.greeter is None:
                    continue
                greeter = layout.greeter
                self.assertTrue(UiRect(0, 0, width, height).contains(greeter))
                for rect in list(layout.hits) + list(layout.labels) + list(
                    _corners(width, height)
                ):
                    self.assertFalse(greeter.intersects(rect))

    def test_greeter_steps_aside_when_margin_is_too_narrow(self) -> None:
        self.assertIsNone(greeter_rect(1024, 600, free_right_edge=40))


class CollectionHomeIdentityTests(unittest.TestCase):
    def test_collection_hues_follow_accepted_recipe_and_are_distinct(self) -> None:
        self.assertEqual(
            {k: v for k, v in _COLLECTION_PORTAL_HUES.items() if k != "my_creations"},
            {
                "create": "coral",
                "play": "ocean",
                "learn": "orange",
                "explore": "leaf",
                "my_greia": "grape",
            },
        )
        self.assertEqual(len(set(_COLLECTION_PORTAL_HUES.values())), 6)
        self.assertNotIn(_COLLECTION_PORTAL_HUES["my_creations"], {"turquoise", "default"})

    def test_every_portal_hue_has_a_catalogued_rendition(self) -> None:
        with SOURCE_SPEC.open("rb") as stream:
            spec = tomllib.load(stream)
        visuals = {item["id"]: item for item in spec["visuals"]}
        variants = {v["name"] for v in visuals["ui.portal.collection"]["variants"]}
        self.assertLessEqual(set(_COLLECTION_PORTAL_HUES.values()) | {"default"}, variants)
        self.assertIn("ui.portal.collection_focus", visuals)
        self.assertIn("bg.meadow_day.home", visuals)
        for item in ("ui.portal.collection", "ui.portal.collection_focus", "bg.meadow_day.home"):
            for variant in visuals[item]["variants"]:
                self.assertTrue((REPO_ROOT / "assets" / variant["output"]).is_file())

    def test_greeter_is_the_profiles_own_cast_friend(self) -> None:
        self.assertEqual(greeter_character_for("unicorn"), "lilli")
        self.assertEqual(greeter_character_for("robot"), "dani")
        self.assertEqual(greeter_character_for("owl"), "leo")
        self.assertEqual(greeter_character_for("green_monster"), "momo")
        self.assertEqual(greeter_character_for("dinosaur"), "leo")
        self.assertEqual(greeter_character_for(None), "leo")

    def test_profile_card_hue_is_stable_per_profile(self) -> None:
        self.assertEqual(profile_portal_hue("abc"), profile_portal_hue("abc"))
        hues = {profile_portal_hue(f"profile-{i}") for i in range(40)}
        self.assertGreater(len(hues), 3)


class CollectionHomeRenderTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        pygame.init()
        pygame.font.init()

    def test_real_home_targets_match_layout_and_use_shared_art(self) -> None:
        from greia_launcher.child_shell import GreiaChildShell

        for width, height in ((1024, 600), (480, 320)):
            with self.subTest(viewport=(width, height)):
                screen = pygame.display.set_mode((width, height))
                shell = GreiaChildShell(windowed=True)
                if shell._visual_cache is None:
                    self.skipTest("shared visuals unavailable in this checkout")
                shell.profiles = shell.profile_store.ensure_initialized()
                shell._activate_profile(shell.profiles[0], pygame)
                shell._draw(screen, pygame)
                targets = [t for t in shell._targets if t.action == "home_collection"]
                self.assertEqual(
                    [t.value for t in targets],
                    [c.collection_id for c in shell._home_collections()],
                )
                switch = next(t for t in shell._targets if t.action == "switch_profile")
                for target in targets:
                    self.assertFalse(target.rect.colliderect(switch.rect))
                    self.assertTrue(screen.get_rect().contains(target.rect))
                self.assertFalse(getattr(shell, "_shared_collection_portal_disabled", False))
                self.assertFalse(getattr(shell, "_shared_scene_disabled", False))
                self.assertFalse(getattr(shell, "_shared_greeter_disabled", False))


if __name__ == "__main__":
    unittest.main()
