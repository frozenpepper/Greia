from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from greia_launcher.visual_assets import load_launcher_assets


class LauncherVisualAssetsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.assets = Path(self.temporary.name) / "assets"
        self.catalog = self.assets / "catalog"
        self.icons = self.assets / "icons"
        self.visual = self.assets / "visual"
        self.catalog.mkdir(parents=True)
        self.icons.mkdir()
        self.visual.mkdir()
        for size in (64, 128, 256):
            (self.icons / f"home-{size}.png").write_bytes(b"png")
        self.core = self.catalog / "core.toml"
        self.core.write_text(
            """
[[icons]]
id = "home"
category = "system"
alt_key = "asset.home"
path_64 = "icons/home-64.png"
path_128 = "icons/home-128.png"
path_256 = "icons/home-256.png"
""".lstrip(),
            encoding="utf-8",
        )

    def write_shared(self, *, path: Path | None = None) -> Path:
        (self.visual / "shadow.png").write_bytes(b"png")
        manifest = path or self.catalog / "shared.toml"
        manifest.write_text(
            """
[[visuals]]
id = "ui.shadow.soft"
kind = "shadow"
role = "grounding"

[visuals.variants]
default = "visual/shadow.png"
""".lstrip(),
            encoding="utf-8",
        )
        return manifest

    def test_missing_optional_shared_catalogue_keeps_core_assets(self) -> None:
        state = load_launcher_assets(self.core, self.catalog / "missing.toml")

        self.assertFalse(state.shared_visuals_available)
        self.assertIsNone(state.shared_visuals_error)
        self.assertEqual(state.catalogue.get("home").asset_id, "home")
        self.assertEqual(state.catalogue.all_visuals(), ())

    def test_valid_shared_catalogue_is_explicitly_merged(self) -> None:
        state = load_launcher_assets(self.core, self.write_shared())

        self.assertTrue(state.shared_visuals_available)
        self.assertIsNone(state.shared_visuals_error)
        self.assertEqual(state.catalogue.get("home").asset_id, "home")
        self.assertEqual(
            state.catalogue.get_visual("ui.shadow.soft").role,
            "grounding",
        )

    def test_invalid_optional_shared_catalogue_falls_back_to_core(self) -> None:
        shared = self.catalog / "shared.toml"
        shared.write_text(
            """
[[visuals]]
id = "ui.shadow.soft"
kind = "not-a-kind"
role = "grounding"

[visuals.variants]
default = "visual/missing.png"
""".lstrip(),
            encoding="utf-8",
        )

        state = load_launcher_assets(self.core, shared)

        self.assertFalse(state.shared_visuals_available)
        self.assertIsNotNone(state.shared_visuals_error)
        self.assertEqual(state.catalogue.get("home").asset_id, "home")
        self.assertEqual(state.catalogue.all_visuals(), ())

    def test_shared_catalogue_from_different_assets_root_falls_back(self) -> None:
        other_assets = Path(self.temporary.name) / "other" / "assets"
        other_catalog = other_assets / "catalog"
        other_visual = other_assets / "visual"
        other_catalog.mkdir(parents=True)
        other_visual.mkdir()
        (other_visual / "shadow.png").write_bytes(b"png")
        shared = other_catalog / "shared.toml"
        shared.write_text(
            """
[[visuals]]
id = "ui.shadow.soft"
kind = "shadow"
role = "grounding"

[visuals.variants]
default = "visual/shadow.png"
""".lstrip(),
            encoding="utf-8",
        )

        state = load_launcher_assets(self.core, shared)

        self.assertFalse(state.shared_visuals_available)
        self.assertIn("different roots", state.shared_visuals_error or "")
        self.assertEqual(state.catalogue.get("home").asset_id, "home")


if __name__ == "__main__":
    unittest.main()
