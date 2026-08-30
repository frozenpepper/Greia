from __future__ import annotations

import ast
import importlib.util
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
ACTIVITY_ROOT = ROOT / "activities" / "painting"


def _load_painting_module():
    # Prefer package import for decomposed Activities so sibling modules
    # resolve via relative imports (mirrors test_core_creation_activities).
    try:
        import importlib

        mod = importlib.import_module("activities.painting.main")
        sys.modules["painting_test_mod"] = mod
        return mod
    except Exception:
        pass
    spec = importlib.util.spec_from_file_location(
        "activities.painting.main",
        ACTIVITY_ROOT / "main.py",
        submodule_search_locations=[str(ACTIVITY_ROOT)],
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load painting main.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules["painting_test_mod"] = mod
    sys.modules["activities.painting.main"] = mod
    if "activities.painting" not in sys.modules:
        import types

        pkg_mod = types.ModuleType("activities.painting")
        pkg_mod.__path__ = [str(ACTIVITY_ROOT)]  # type: ignore[attr-defined]
        sys.modules["activities.painting"] = pkg_mod
    spec.loader.exec_module(mod)
    return mod


class PaintingContractTests(unittest.TestCase):
    def test_painting_manifest_contract(self) -> None:
        manifest_path = ACTIVITY_ROOT / "activity.toml"
        self.assertTrue(manifest_path.exists(), "activity.toml must exist")
        text = manifest_path.read_text(encoding="utf-8")
        self.assertIn('id = "org.greia.painting"', text)
        self.assertIn('entrypoint = "main.py"', text)
        self.assertIn('profile = "pointer"', text)

    def test_forbidden_imports_absent_from_activity(self) -> None:
        main_path = ACTIVITY_ROOT / "main.py"
        self.assertTrue(main_path.exists(), "main.py must exist")
        tree = ast.parse(main_path.read_text(encoding="utf-8"), filename=str(main_path))
        forbidden = {"os", "sys"}
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    self.assertNotIn(alias.name.split(".")[0], forbidden, f"Forbidden import: {alias.name}")
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    self.assertNotIn(node.module.split(".")[0], forbidden, f"Forbidden import from: {node.module}")

    def test_runtime_assets_exist(self) -> None:
        runtime_dir = ACTIVITY_ROOT / "assets" / "runtime"
        self.assertTrue(runtime_dir.exists(), "assets/runtime directory must exist")
        required_assets = [
            "tool_gallery.png",
            "tool_undo.png",
            "tool_new.png",
            "tool_eraser.png",
            "brush_small.png",
            "brush_medium.png",
            "brush_large.png",
            "canvas_card_frame.png",
            "color_well_dish.png",
        ]
        for asset_name in required_assets:
            p = runtime_dir / asset_name
            self.assertTrue(p.exists(), f"Runtime asset missing: {asset_name}")
            self.assertGreater(p.stat().st_size, 0, f"Runtime asset is empty: {asset_name}")

    def test_color_and_brush_definitions(self) -> None:
        mod = _load_painting_module()
        self.assertEqual(len(mod.COLORS), 10, "Painting must have 10 standard child colors")
        self.assertEqual(len(mod.BRUSH_SIZES), 3, "Painting must have 3 standard brush sizes")
        self.assertEqual(mod.MAX_UNDO_STROKES, 24, "Painting must support 24 undo strokes")
        self.assertEqual(mod.MAX_PAINTINGS, 48, "Painting must support up to 48 paintings")


if __name__ == "__main__":
    unittest.main()
