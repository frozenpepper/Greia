"""
Unit and integration tests for tools/visual_authoring_library.py.
"""

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
TOOL_PATH = REPO_ROOT / "tools" / "visual_authoring_library.py"
LIBRARY_DIR = REPO_ROOT / "assets" / "visual" / "authoring_library"

# Import helper functions directly
sys.path.insert(0, str(REPO_ROOT / "tools"))
import visual_authoring_library as val


class VisualAuthoringLibraryTests(unittest.TestCase):
    """Device-host hermetic: unittest.TestCase so the frozen
    `discover -s tests` gate executes real assertions on hosts
    without pytest. Bodies preserve the original pytest-style
    assertions verbatim; pytest `tmp_path` fixtures become
    `tempfile.TemporaryDirectory`."""

    def test_library_parse_and_discovery(self):
        """Verifies that all six generic collection TOMLs parse without error."""
        collections, errors = val.load_library(LIBRARY_DIR)
        assert len(errors) == 0, f"Library load returned errors: {errors}"
        assert len(collections) == 6, f"Expected 6 collections, got {len(collections)}"

        col_ids = {c["collection"]["id"] for c in collections}
        expected_ids = {
            "generic.nature_landscape",
            "generic.interiors_architecture",
            "generic.furniture_storage",
            "generic.everyday_props",
            "generic.making_learning_play",
            "generic.lighting_fx_shadows",
        }
        assert col_ids == expected_ids

    def test_validate_passes_on_current_library(self):
        """Verifies that the canonical authoring library passes full validation."""
        res = subprocess.run([sys.executable, str(TOOL_PATH), "validate", "--json"], capture_output=True, text=True, check=True)
        data = json.loads(res.stdout)
        assert data["valid"] is True
        assert data["errors_count"] == 0
        assert data["collections_count"] == 6
        assert data["total_resources_checked"] > 90

    def test_search_finds_spindle_chair(self):
        """Verifies that searching for 'chair' finds the spindle chair."""
        res = subprocess.run([sys.executable, str(TOOL_PATH), "search", "chair", "--json"], capture_output=True, text=True, check=True)
        items = json.loads(res.stdout)
        found_ids = [i["id"] for i in items]
        assert "furniture.seating.chair.spindle_wood" in found_ids

    def test_preferred_filtering_excludes_candidate_references(self):
        """Verifies that filtering by --status preferred excludes candidate references."""
        # When searching for armchair (candidate reference) with preferred filter
        res = subprocess.run([sys.executable, str(TOOL_PATH), "search", "armchair", "--status", "preferred", "--json"], capture_output=True, text=True, check=True)
        items = json.loads(res.stdout)
        found_ids = [i["id"] for i in items]
        assert "furniture.seating.armchair.soft_reading" not in found_ids

        # Without preferred filter, candidate reference is found
        res_all = subprocess.run([sys.executable, str(TOOL_PATH), "search", "armchair", "--json"], capture_output=True, text=True, check=True)
        items_all = json.loads(res_all.stdout)
        found_all_ids = [i["id"] for i in items_all]
        assert "furniture.seating.armchair.soft_reading" in found_all_ids

    def test_exact_show_returns_metadata(self):
        """Verifies that exact show command returns complete metadata dictionary."""
        res = subprocess.run([sys.executable, str(TOOL_PATH), "show", "furniture.seating.chair.spindle_wood", "--json"], capture_output=True, text=True, check=True)
        item = json.loads(res.stdout)
        assert item["id"] == "furniture.seating.chair.spindle_wood"
        assert item["library_status"] == "preferred"
        assert item["family"] == "furniture"
        assert item["role"] == "chair"
        assert "assets/visual/generic/core_essentials/v0.1/chair_spindle_wood.svg" in item["source_path"]

    def test_duplicate_id_fails_validation(self):
        """Verifies that duplicate asset IDs across files fail validation."""
        with tempfile.TemporaryDirectory() as temporary:
            fake_lib = Path(temporary) / "lib"
            fake_lib.mkdir()

            toml_1 = """
[collection]
id = "generic.col1"
name = "Col 1"
description = "Test col 1"

[[assets]]
id = "dup.item.id"
library_status = "preferred"
source_pack = "test.pack"
source_path = "assets/visual/generic/core_essentials/v0.1/door_timber_closed.svg"
family = "test"
role = "test"
"""

            toml_2 = """
[collection]
id = "generic.col2"
name = "Col 2"
description = "Test col 2"

[[assets]]
id = "dup.item.id"
library_status = "preferred"
source_pack = "test.pack"
source_path = "assets/visual/generic/core_essentials/v0.1/door_timber_closed.svg"
family = "test"
role = "test"
"""

            (fake_lib / "col1.toml").write_text(toml_1.strip())
            (fake_lib / "col2.toml").write_text(toml_2.strip())

            res = subprocess.run([sys.executable, str(TOOL_PATH), "validate", "--library-dir", str(fake_lib), "--json"], capture_output=True, text=True)
            assert res.returncode != 0
            data = json.loads(res.stdout)
            assert data["valid"] is False
            assert any("Duplicate ID 'dup.item.id'" in err for err in data["errors"])

    def test_missing_source_path_fails_validation(self):
        """Verifies that referencing a non-existent source file fails validation."""
        with tempfile.TemporaryDirectory() as temporary:
            fake_lib = Path(temporary) / "lib"
            fake_lib.mkdir()

            toml_missing = """
[collection]
id = "generic.col1"
name = "Col 1"
description = "Test col 1"

[[assets]]
id = "missing.file.item"
library_status = "preferred"
source_pack = "test.pack"
source_path = "assets/visual/non_existent_path_xyz123.svg"
family = "test"
role = "test"
"""
            (fake_lib / "col1.toml").write_text(toml_missing.strip())

            res = subprocess.run([sys.executable, str(TOOL_PATH), "validate", "--library-dir", str(fake_lib), "--json"], capture_output=True, text=True)
            assert res.returncode != 0
            data = json.loads(res.stdout)
            assert data["valid"] is False
            assert any("source file not found on disk" in err for err in data["errors"])


if __name__ == "__main__":
    unittest.main()
