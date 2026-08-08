from __future__ import annotations

import json
import tempfile
import unittest
from unittest import mock
from pathlib import Path

from PIL import Image

from greia_platform.customization import (
    CustomizationError,
    RemovableImageScanner,
    ThemePalette,
    ThemeStore,
    WallpaperImporter,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULTS = PROJECT_ROOT / "runtime" / "theme-defaults.toml"


class CustomizationTests(unittest.TestCase):
    def test_palette_and_default_theme_load(self) -> None:
        palette = ThemePalette.load(DEFAULTS)
        self.assertGreaterEqual(len(palette.backgrounds), 8)
        self.assertGreaterEqual(len(palette.accents), 8)
        self.assertGreaterEqual(len(palette.texts), 5)
        with tempfile.TemporaryDirectory() as temporary:
            theme = ThemeStore(palette, Path(temporary)).resolve()
        self.assertEqual(theme.preferences.background, palette.default_background)
        self.assertIsNone(theme.wallpaper_path)

    def test_color_choices_persist_and_are_curated(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            store = ThemeStore.load(DEFAULTS, Path(temporary))
            store.set_colors(background="sky", accent="grape", text="navy")
            reloaded = ThemeStore.load(DEFAULTS, Path(temporary)).resolve()
            self.assertEqual(reloaded.preferences.background, "sky")
            self.assertEqual(reloaded.preferences.accent, "grape")
            self.assertEqual(reloaded.preferences.text, "navy")
            with self.assertRaises(CustomizationError):
                store.set_colors(accent="not-a-curated-color")

    def test_malformed_preferences_fall_back_safely(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            state = Path(temporary)
            (state / "theme.json").write_text('{"accent":"broken"}', encoding="utf-8")
            store = ThemeStore.load(DEFAULTS, state)
            self.assertEqual(store.resolve().preferences, store.default_preferences())

    def test_wallpaper_import_is_normalized_bounded_and_resettable(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            media = root / "media"
            mount = media / "sdb1"
            mount.mkdir(parents=True)
            source = mount / "family-photo.png"
            Image.new("RGB", (2400, 1600), (80, 150, 220)).save(source)

            state = root / "customization"
            store = ThemeStore.load(DEFAULTS, state)
            scanner = RemovableImageScanner(media)
            candidates = scanner.scan()
            self.assertEqual(len(candidates), 1)
            target = WallpaperImporter(store, scanner).import_image(candidates[0].path)

            self.assertTrue(target.is_file())
            self.assertLessEqual(target.stat().st_size, WallpaperImporter.MAX_OUTPUT_BYTES)
            with Image.open(target) as imported:
                self.assertLessEqual(imported.width, WallpaperImporter.MAX_DIMENSIONS[0])
                self.assertLessEqual(imported.height, WallpaperImporter.MAX_DIMENSIONS[1])
                self.assertEqual(imported.format, "JPEG")
            self.assertTrue(store.resolve().preferences.wallpaper_enabled)

            store.reset()
            self.assertFalse(target.exists())
            self.assertEqual(store.resolve().preferences, store.default_preferences())

    def test_scanner_ignores_non_images_and_hidden_files(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            media = Path(temporary) / "media"
            mount = media / "mmcblk0p1"
            mount.mkdir(parents=True)
            (mount / "notes.txt").write_text("not an image", encoding="utf-8")
            (mount / ".hidden.jpg").write_bytes(b"not an image")
            self.assertEqual(RemovableImageScanner(media).scan(), ())

    def test_non_boolean_wallpaper_flag_falls_back(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            state = Path(temporary)
            state.joinpath("theme.json").write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "background": "sky",
                        "accent": "grape",
                        "text": "navy",
                        "wallpaper_enabled": "false",
                    }
                ),
                encoding="utf-8",
            )
            store = ThemeStore.load(DEFAULTS, state)
            self.assertEqual(store.resolve().preferences, store.default_preferences())


    def test_clear_wallpaper_deletes_image_but_preserves_colors(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            media = root / "media"
            mount = media / "sdb1"
            mount.mkdir(parents=True)
            source = mount / "picture.png"
            Image.new("RGB", (640, 480), (90, 120, 160)).save(source)
            store = ThemeStore.load(DEFAULTS, root / "state")
            store.set_colors(background="sky", accent="grape", text="navy")
            scanner = RemovableImageScanner(media)
            WallpaperImporter(store, scanner).import_image(source)

            cleared = store.clear_wallpaper()

            self.assertFalse(store.wallpaper_path.exists())
            self.assertFalse(cleared.wallpaper_enabled)
            self.assertEqual((cleared.background, cleared.accent, cleared.text), ("sky", "grape", "navy"))

    def test_scanner_is_bounded_on_large_media_trees(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            media = Path(temporary) / "media"
            mount = media / "sdb1"
            mount.mkdir(parents=True)
            for index in range(20):
                (mount / f"{index:02d}.jpg").write_bytes(b"image")
            scanner = RemovableImageScanner(media, maximum_files=3, maximum_entries=5)

            candidates = scanner.scan()

            self.assertLessEqual(len(candidates), 3)
            self.assertEqual(len(candidates), 3)
            self.assertTrue(all(candidate.path.suffix == ".jpg" for candidate in candidates))

    def test_decompression_bomb_is_reported_as_bounded_customization_error(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            media = root / "media"
            mount = media / "sdb1"
            mount.mkdir(parents=True)
            source = mount / "bomb.png"
            source.write_bytes(b"not decoded")
            importer = WallpaperImporter(
                ThemeStore.load(DEFAULTS, root / "state"),
                RemovableImageScanner(media),
            )
            with mock.patch(
                "PIL.Image.open",
                side_effect=Image.DecompressionBombError("too many pixels"),
            ):
                with self.assertRaisesRegex(CustomizationError, "cannot import wallpaper"):
                    importer.import_image(source)

    def test_import_rejects_source_outside_media_root(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            media = root / "media"
            media.mkdir()
            outside = root / "outside.jpg"
            Image.new("RGB", (20, 20), (10, 20, 30)).save(outside)
            store = ThemeStore.load(DEFAULTS, root / "state")
            scanner = RemovableImageScanner(media)
            with self.assertRaisesRegex(CustomizationError, "outside removable media"):
                WallpaperImporter(store, scanner).import_image(outside)


if __name__ == "__main__":
    unittest.main()
