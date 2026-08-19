from __future__ import annotations

import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

os.environ["SDL_VIDEODRIVER"] = "dummy"
import pygame

from greia_launcher.theme import LauncherThemeController
from greia_platform.customization import ResolvedTheme, ThemePreferences, ThemeStore
from greia_platform.pygame_effects import (
    PygameDepthStyle,
    clear_effects_cache,
    make_rounded_shadow,
)
from greia_platform.typography import FontRole, GreiaTypography

THEMES_TOML = Path("runtime/theme-defaults.toml")


class UiPerformanceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        pygame.init()
        pygame.font.init()
        cls.screen = pygame.display.set_mode((400, 300))

    def test_rounded_shadow_is_cached_and_reused(self) -> None:
        clear_effects_cache()
        style = PygameDepthStyle(shadow_alpha=50, radius=12)
        shadow1 = make_rounded_shadow((120, 80), pygame, style=style)
        shadow2 = make_rounded_shadow((120, 80), pygame, style=style)
        self.assertIs(shadow1, shadow2)

        clear_effects_cache()
        shadow3 = make_rounded_shadow((120, 80), pygame, style=style)
        self.assertIsNot(shadow1, shadow3)
        self.assertEqual(shadow1.get_size(), shadow3.get_size())

    def test_typography_render_pure_text_fast_path(self) -> None:
        typography = GreiaTypography()
        color = (30, 30, 30)
        surface = typography.render("Hello Greia", FontRole.BODY, 24, color)
        self.assertIsInstance(surface, pygame.Surface)
        self.assertGreater(surface.get_width(), 0)
        self.assertGreater(surface.get_height(), 0)

    def test_theme_controller_reuses_wallpaper_without_per_frame_stat(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            wallpaper_file = temp_path / "test_wallpaper.png"
            test_surface = pygame.Surface((800, 600))
            pygame.image.save(test_surface, str(wallpaper_file))

            theme_store = ThemeStore.load(THEMES_TOML, temp_path / "profile_theme")
            controller = LauncherThemeController(theme_store)

            resolved = ResolvedTheme(
                preferences=ThemePreferences(
                    schema_version=1,
                    background="peach",
                    accent="gold",
                    text="ink",
                    wallpaper_enabled=True,
                ),
                background=(255, 255, 255),
                panel=(240, 240, 240),
                accent=(0, 0, 0),
                text=(17, 17, 17),
                accent_text=(255, 255, 255),
                wallpaper_path=wallpaper_file,
            )
            with patch.object(LauncherThemeController, "theme", new_callable=lambda: property(lambda self: resolved)):
                controller.draw_background(self.screen, pygame)
                cached_surf = controller._wallpaper_surface
                self.assertIsNotNone(cached_surf)

                with patch("pathlib.Path.stat") as mock_stat:
                    controller.draw_background(self.screen, pygame)
                    mock_stat.assert_not_called()
                    self.assertIs(controller._wallpaper_surface, cached_surf)


if __name__ == "__main__":
    unittest.main()
