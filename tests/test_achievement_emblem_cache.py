from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import pygame

from greia_platform.achievement_art import ActivityAchievementEmblem
from greia_platform.achievements import (
    AchievementDefinition,
    AchievementEntry,
    LocalizedAchievementText,
)
from greia_platform.pygame_achievements import PygameAchievementBadgeRenderer


def _text(value: str) -> LocalizedAchievementText:
    return LocalizedAchievementText((("en", value),), "en")


def _entry(emblem: ActivityAchievementEmblem) -> AchievementEntry:
    return AchievementEntry(
        definition=AchievementDefinition(
            achievement_id="greia.test.emblem-update",
            category="test",
            tier="silver",
            icon_id="yellow_star",
            secret=False,
            title=_text("Badge"),
            description=_text("Description"),
            locked_hint=_text("Hint"),
            criteria=(),
            activity_emblem=emblem,
        ),
        unlocked_at=1.0,
        announced_at=None,
        seen_at=None,
    )


class _IconProvider:
    def __init__(self) -> None:
        self.calls = 0

    def __call__(self, _icon_id: str, size: int, pygame_module):
        self.calls += 1
        return pygame_module.Surface((size, size), pygame_module.SRCALPHA)


class AchievementEmblemCacheTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        pygame.init()

    @classmethod
    def tearDownClass(cls) -> None:
        pygame.quit()

    def test_changed_content_digest_invalidates_same_path_badge_cache(self) -> None:
        provider = _IconProvider()
        renderer = PygameAchievementBadgeRenderer(provider, max_entries=4)
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "emblem.png"
            source = pygame.Surface((64, 64), pygame.SRCALPHA)
            source.fill((20, 140, 210, 255))
            pygame.image.save(source, path)

            first_emblem = ActivityAchievementEmblem(
                activity_id="org.greia.test",
                emblem_id="activity",
                asset_path=path,
                width=64,
                height=64,
                byte_size=path.stat().st_size,
                content_digest="first",
            )
            second_emblem = ActivityAchievementEmblem(
                activity_id="org.greia.test",
                emblem_id="activity",
                asset_path=path,
                width=64,
                height=64,
                byte_size=path.stat().st_size,
                content_digest="second",
            )

            first = renderer.render(_entry(first_emblem), 96)
            repeated = renderer.render(_entry(first_emblem), 96)
            changed = renderer.render(_entry(second_emblem), 96)

        self.assertIs(first, repeated)
        self.assertIsNot(first, changed)
        self.assertEqual(provider.calls, 0)


if __name__ == "__main__":
    unittest.main()
