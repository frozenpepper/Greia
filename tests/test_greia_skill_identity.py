"""Prevent Greia OS/Activity agent skill files from being swapped again.

An earlier GitHub-only documentation update accidentally wrote the entire
OS task-router file under the Activity path and vice versa. This guard
inspects the checked-out files as content, not GitHub metadata.
"""
from __future__ import annotations

from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]

SKILLS = {
    "greia-os-work": ("# Greia OS Work", "Parent"),
    "greia-activity-authoring": ("# Greia Activity Authoring", "Activity"),
}


def _frontmatter_name(text: str) -> str:
    parts = text.split("---", 2)
    if len(parts) != 3 or parts[0].strip():
        raise AssertionError("expected YAML frontmatter at file start")
    names = [
        line.partition(":")[2].strip()
        for line in parts[1].splitlines()
        if line.startswith("name:")
    ]
    if len(names) != 1:
        raise AssertionError("skill frontmatter must contain exactly one name")
    return names[0]


class GreiaInstalledSkillIdentityTests(unittest.TestCase):
    def test_each_installed_skill_matches_its_path_and_role(self) -> None:
        for slug, (heading, role) in SKILLS.items():
            with self.subTest(slug=slug):
                path = ROOT / "skills" / slug / "SKILL.md"
                text = path.read_text(encoding="utf-8")
                self.assertEqual(_frontmatter_name(text), slug)
                self.assertIn(heading, text)
                self.assertIn(role, text)
                self.assertGreater(len(text), 500)

    def test_activity_skill_owns_localization_authoring_rules(self) -> None:
        activity = (ROOT / "skills/greia-activity-authoring/SKILL.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("locales/es.json", activity)
        self.assertIn("audio", activity)
        self.assertIn("phonics", activity)

    def test_os_skill_owns_parent_locale_controls(self) -> None:
        os_text = (ROOT / "skills/greia-os-work/SKILL.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("ParentSettingsOverlay", os_text)
        self.assertIn("panel_localization.py", os_text)


if __name__ == "__main__":
    unittest.main()
