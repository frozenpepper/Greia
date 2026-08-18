from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from greia_platform.ui_preferences import (
    InterfaceSize,
    UiPreferences,
    UiPreferencesError,
    UiPreferencesStore,
)


class UiPreferencesTests(unittest.TestCase):
    def test_defaults_are_normal_and_semantic(self) -> None:
        preferences = UiPreferences()
        self.assertEqual(preferences.interface_size, InterfaceSize.NORMAL)
        self.assertEqual(preferences.scale, 1.0)
        self.assertLess(InterfaceSize.COMPACT.scale, 1.0)
        self.assertGreater(InterfaceSize.LARGE.scale, 1.0)

    def test_store_persists_only_curated_interface_sizes(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            store = UiPreferencesStore(Path(temporary))
            updated = store.set_interface_size("large")
            self.assertEqual(updated.interface_size, InterfaceSize.LARGE)
            self.assertEqual(store.read(), updated)
            with self.assertRaises(UiPreferencesError):
                store.set_interface_size("237-percent")

    def test_malformed_or_oversized_state_falls_back_to_normal(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            store = UiPreferencesStore(root)
            root.mkdir(parents=True, exist_ok=True)
            store.path.write_text('{"interface_size":"giant"}', encoding="utf-8")
            self.assertEqual(store.read(), UiPreferences())
            store.path.write_bytes(b"x" * (store.MAX_FILE_BYTES + 1))
            self.assertEqual(store.read(), UiPreferences())

    def test_scale_px_is_bounded(self) -> None:
        large = UiPreferences(interface_size=InterfaceSize.LARGE)
        self.assertGreater(large.scale_px(40), 40)
        self.assertEqual(large.scale_px(40, maximum=42), 42)
        self.assertEqual(large.scale_px(1, minimum=8), 8)

    def test_written_shape_is_small_and_versioned(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            store = UiPreferencesStore(Path(temporary))
            store.set_interface_size(InterfaceSize.COMPACT)
            payload = json.loads(store.path.read_text(encoding="utf-8"))
            self.assertEqual(
                payload,
                {"interface_size": "compact", "schema_version": 1},
            )
            self.assertLess(store.path.stat().st_size, store.MAX_FILE_BYTES)
            self.assertNotEqual(store.version_token(), 0)


if __name__ == "__main__":
    unittest.main()
