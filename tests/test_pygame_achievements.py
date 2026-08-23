from __future__ import annotations

import unittest

import pygame

from greia_platform.achievements import (
    AchievementDefinition,
    AchievementEntry,
    LocalizedAchievementText,
)
from greia_platform.pygame_achievements import PygameAchievementBadgeRenderer


def _text(value: str) -> LocalizedAchievementText:
    return LocalizedAchievementText((("en", value),), "en")


def _entry(*, unlocked: bool) -> AchievementEntry:
    definition = AchievementDefinition(
        achievement_id="greia.test.badge",
        category="test",
        tier="gold",
        icon_id="yellow_star",
        secret=False,
        title=_text("Badge"),
        description=_text("Description"),
        locked_hint=_text("Hint"),
        criteria=(),
    )
    return AchievementEntry(
        definition=definition,
        unlocked_at=10.0 if unlocked else None,
        announced_at=None,
        seen_at=None,
    )


class _IconProvider:
    def __init__(self) -> None:
        self.calls = 0

    def __call__(self, _icon_id: str, size: int, pygame_module):
        self.calls += 1
        surface = pygame_module.Surface((size, size), pygame_module.SRCALPHA)
        pygame_module.draw.circle(
            surface,
            (255, 215, 60),
            (size // 2, size // 2),
            max(1, size // 3),
        )
        return surface


class AchievementBadgeRendererTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        pygame.init()

    @classmethod
    def tearDownClass(cls) -> None:
        pygame.quit()

    def test_same_semantic_badge_is_one_cache_entry(self) -> None:
        provider = _IconProvider()
        renderer = PygameAchievementBadgeRenderer(provider, max_entries=4)
        entry = _entry(unlocked=True)

        first = renderer.render(entry, 96)
        second = renderer.render(entry, 96)

        self.assertIs(first, second)
        self.assertEqual(provider.calls, 1)
        self.assertEqual(first.get_size(), (96, 96))

    def test_locked_badge_does_not_request_reward_icon(self) -> None:
        provider = _IconProvider()
        renderer = PygameAchievementBadgeRenderer(provider)
        locked = renderer.render(_entry(unlocked=False), 80)
        self.assertEqual(provider.calls, 0)
        self.assertEqual(locked.get_size(), (80, 80))

    def test_size_is_bounded_and_never_full_screen(self) -> None:
        provider = _IconProvider()
        renderer = PygameAchievementBadgeRenderer(provider)
        badge = renderer.render(_entry(unlocked=True), 10_000)
        self.assertEqual(badge.get_size(), (220, 220))
        self.assertTrue(badge.get_flags() & pygame.SRCALPHA)


if __name__ == "__main__":
    unittest.main()
