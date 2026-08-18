from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from greia_platform.customization import ThemeStore
from greia_platform.theme_snapshot import (
    MAX_THEME_SNAPSHOT_BYTES,
    ThemeSnapshotError,
    decode_theme_snapshot,
    encode_theme_snapshot,
)


ROOT = Path(__file__).resolve().parents[1]
DEFAULTS = ROOT / "runtime" / "theme-defaults.toml"


class ThemeSnapshotTests(unittest.TestCase):
    def test_round_trip_preserves_resolved_colors_without_wallpaper_authority(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            store = ThemeStore.load(DEFAULTS, Path(temporary))
            store.set_colors(background="lavender", accent="grape", text="plum")
            source = store.resolve()
            encoded = encode_theme_snapshot(source)
            resolved = decode_theme_snapshot(encoded)

        self.assertLessEqual(len(encoded.encode("utf-8")), MAX_THEME_SNAPSHOT_BYTES)
        self.assertEqual(resolved.background, source.background)
        self.assertEqual(resolved.panel, source.panel)
        self.assertEqual(resolved.accent, source.accent)
        self.assertEqual(resolved.text, source.text)
        self.assertEqual(resolved.accent_text, source.accent_text)
        self.assertEqual(resolved.preferences.background, "lavender")
        self.assertFalse(resolved.preferences.wallpaper_enabled)
        self.assertIsNone(resolved.wallpaper_path)

    def test_invalid_snapshot_fails_closed(self) -> None:
        with self.assertRaises(ThemeSnapshotError):
            decode_theme_snapshot("not-json")
        with self.assertRaises(ThemeSnapshotError):
            decode_theme_snapshot('{"schema_version":1,"background":"../escape"}')
        with self.assertRaises(ThemeSnapshotError):
            decode_theme_snapshot("x" * (MAX_THEME_SNAPSHOT_BYTES + 1))


if __name__ == "__main__":
    unittest.main()
