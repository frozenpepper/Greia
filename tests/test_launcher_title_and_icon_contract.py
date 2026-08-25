import os
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

import pygame
from PIL import Image

from greia_launcher.activity_icon import ActivityIconError, package_icon_path
from greia_launcher.title_presentation import (
    CARD_TITLE_DISPLAY_CAP,
    cap_title_for_card,
    contain_fit_icon_surface,
    render_activity_card_label,
    render_full_title_disclosure_surface,
    split_title_two_lines,
)
from greia_platform.activities import ActivityRegistry, RuntimeCatalogue
from greia_platform.activity_assets import package_icon_path as platform_package_icon_path
from greia_platform.trust import ActivitySource, PackageTrust
from greia_platform.typography import FontRole, FontSpec, GreiaTypography, grapheme_spans


class LauncherTitleAndIconContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        os.environ["SDL_VIDEODRIVER"] = "dummy"
        pygame.init()
        pygame.font.init()
        cls.typography = GreiaTypography()
        cls.font = cls.typography.font(FontRole.TITLE, 17)

    # =========================================================================
    # 1. Title Presentation Contract Tests
    # =========================================================================

    def test_short_title_remains_single_line_when_it_fits(self) -> None:
        lines = split_title_two_lines("Writing", self.font, max_width=180)
        self.assertEqual(lines, ("Writing",))

    def test_medium_title_wraps_to_two_lines_rather_than_premature_ellipsis(self) -> None:
        title = "Costruiamo Ponti"
        lines = split_title_two_lines(title, self.font, max_width=80)
        self.assertEqual(len(lines), 2)
        self.assertEqual(" ".join(lines), title)
        self.assertEqual(lines, ("Costruiamo", "Ponti"))
        self.assertNotIn("…", lines[0])
        self.assertNotIn("…", lines[1])

    def test_memory_meraviglie_wraps_into_balanced_lines(self) -> None:
        title = "Memory delle Meraviglie"
        lines = split_title_two_lines(title, self.font, max_width=130)
        self.assertEqual(len(lines), 2)
        self.assertEqual(" ".join(lines), title)
        self.assertEqual(lines, ("Memory delle", "Meraviglie"))

    def test_defensive_48_grapheme_card_cap(self) -> None:
        long_title = "This is a deliberately extremely long activity name that exceeds forty-eight graphemes easily"
        spans = grapheme_spans(long_title)
        self.assertGreater(len(spans), 48)

        capped = cap_title_for_card(long_title, max_graphemes=CARD_TITLE_DISPLAY_CAP)
        capped_spans = grapheme_spans(capped.rstrip("…"))
        self.assertLessEqual(len(capped_spans), 48)
        self.assertTrue(capped.endswith("…"))

    def test_multilingual_and_emoji_grapheme_safety(self) -> None:
        complex_title = "Giardino Magico 🌸✨ e Cuccioli 🐶🐾"
        spans = grapheme_spans(complex_title)
        self.assertTrue(any(s.emoji for s in spans))
        lines = split_title_two_lines(complex_title, self.font, max_width=160)
        self.assertLessEqual(len(lines), 2)
        # Verify no broken surrogate or incomplete grapheme clusters
        for line in lines:
            self.assertEqual(line, line.encode("utf-8").decode("utf-8"))

    def test_rendered_card_label_never_exceeds_bounds(self) -> None:
        max_w = 110
        max_h = 44
        label_surf = render_activity_card_label(
            "Orchestra degli Animali Straordinari",
            max_width=max_w,
            max_height=max_h,
            font_provider=lambda sz: self.typography.font(FontRole.TITLE, sz),
            color=(40, 40, 40),
            preferred_size=20,
            pygame=pygame,
            min_size=14,
        )
        self.assertLessEqual(label_surf.get_width(), max_w)
        self.assertLessEqual(label_surf.get_height(), max_h)

    def test_two_line_label_fits_even_when_preferred_size_below_min_size(self) -> None:
        # Regression: a preferred size below min_size used to skip every fit
        # check and clip two-line text past the card label band.
        max_h = 26
        label_surf = render_activity_card_label(
            "Memory delle Meraviglie",
            max_width=120,
            max_height=max_h,
            font_provider=lambda sz: self.typography.font(FontRole.TITLE, sz),
            color=(40, 40, 40),
            preferred_size=12,
            pygame=pygame,
            min_size=14,
        )
        self.assertLessEqual(label_surf.get_height(), max_h)
        self.assertGreater(label_surf.get_height(), 0)

    def test_two_line_label_compresses_leading_instead_of_overflowing_band(self) -> None:
        # Even when the smallest allowed font stacks two full lines taller than
        # the band, the rendered surface must stay inside it (leading is
        # compressed) so glyphs never cross the card border.
        for title in ("Rompicapi della Foresta Incantata", "GIORNO NOTTE"):
            with self.subTest(title=title):
                surf = render_activity_card_label(
                    title,
                    max_width=100,
                    max_height=30,
                    font_provider=lambda sz: self.typography.font(FontRole.TITLE, sz),
                    color=(40, 40, 40),
                    preferred_size=14,
                    pygame=pygame,
                    min_size=10,
                )
                self.assertLessEqual(surf.get_height(), 30)
                self.assertGreater(surf.get_width(), 0)

    def test_full_title_disclosure_preserves_complete_uncapped_title(self) -> None:
        long_title = "Super Avventura Spaziale dei Draghetti nel Regno delle Fiabe Incantate"
        theme = SimpleNamespace(panel=(250, 246, 238), accent=(239, 77, 83), text=(33, 37, 41))
        pill = render_full_title_disclosure_surface(
            long_title,
            font=self.font,
            theme=theme,
            max_width=300,
            pygame=pygame,
        )
        self.assertGreater(pill.get_width(), 50)
        self.assertGreater(pill.get_height(), 20)

    # =========================================================================
    # 2. Icon Rendering & Contain-Fit Contract Tests
    # =========================================================================

    def test_non_square_package_icon_is_contain_fitted_without_distortion(self) -> None:
        # Create non-square surface 200x100 (2:1 aspect ratio)
        non_square = pygame.Surface((200, 100), pygame.SRCALPHA)
        non_square.fill((255, 0, 0, 255))
        size = 64
        fitted = contain_fit_icon_surface(non_square, size, pygame, safe_padding_ratio=0.12)
        self.assertEqual(fitted.get_size(), (size, size))

        # Check that top/bottom borders have transparent padding
        self.assertEqual(fitted.get_at((size // 2, 0)), (0, 0, 0, 0))
        self.assertEqual(fitted.get_at((size // 2, size - 1)), (0, 0, 0, 0))

    def test_contain_fit_reserves_safe_padding(self) -> None:
        square = pygame.Surface((100, 100), pygame.SRCALPHA)
        square.fill((0, 255, 0, 255))
        size = 80
        fitted = contain_fit_icon_surface(square, size, pygame, safe_padding_ratio=0.11)
        self.assertEqual(fitted.get_size(), (size, size))
        # 11% of 80 is ~8.8px padding on each edge
        self.assertEqual(fitted.get_at((0, 0)), (0, 0, 0, 0))
        self.assertEqual(fitted.get_at((size - 1, size - 1)), (0, 0, 0, 0))
        self.assertGreaterEqual(fitted.get_at((size // 2, size // 2))[1], 250)

    def test_invalid_package_icon_fails_soft_via_platform_validator(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            corrupt = root / "assets" / "icon.png"
            corrupt.parent.mkdir()
            corrupt.write_bytes(b"corrupt-data")
            manifest = SimpleNamespace(root=root, icon_id="package:assets/icon.png")
            with self.assertRaises(ActivityIconError):
                platform_package_icon_path(manifest)

    # =========================================================================
    # 3. First-Party Icon Audit & Validation Tests
    # =========================================================================

    def test_all_first_party_activities_have_unique_package_owned_icons(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        activities_dir = repo_root / "activities"
        runtime = RuntimeCatalogue.load(repo_root / "runtime" / "child-runtime.toml")
        source = ActivitySource(activities_dir, PackageTrust.BUILT_IN, "greia-system")
        registry = ActivityRegistry([source], runtime)
        discovered = registry.discover()

        self.assertGreaterEqual(len(discovered), 19)
        declared_icons = {}
        icon_file_digests = {}

        for act in discovered:
            self.assertTrue(
                act.icon_id.startswith("package:"),
                f"Activity {act.activity_id} must declare package-owned icon (got {act.icon_id})",
            )
            icon_path = package_icon_path(act)
            self.assertIsNotNone(icon_path, f"Missing icon for {act.activity_id}")
            self.assertTrue(icon_path.exists(), f"Icon file does not exist: {icon_path}")

            # Verify image dimensions
            im = Image.open(icon_path)
            self.assertEqual(im.size, (256, 256), f"Icon for {act.activity_id} must be 256x256")
            self.assertEqual(im.mode, "RGBA", f"Icon for {act.activity_id} must be RGBA")

            # Check uniqueness of icon file content
            digest = icon_path.read_bytes()
            self.assertNotIn(
                digest,
                icon_file_digests,
                f"Duplicate icon detected between {act.activity_id} and {icon_file_digests.get(digest)}",
            )
            icon_file_digests[digest] = act.activity_id
            declared_icons[act.activity_id] = act.icon_id

        self.assertEqual(len(icon_file_digests), len(discovered))


if __name__ == "__main__":
    unittest.main()
