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


def _entry(
    *,
    unlocked: bool,
    tier: str = "gold",
    secret: bool = False,
    achievement_id: str = "greia.test.badge",
    activity_emblem: ActivityAchievementEmblem | None = None,
) -> AchievementEntry:
    definition = AchievementDefinition(
        achievement_id=achievement_id,
        category="test",
        tier=tier,
        icon_id="yellow_star",
        secret=secret,
        title=_text("Badge"),
        description=_text("Description"),
        locked_hint=_text("Hint"),
        criteria=(),
        activity_emblem=activity_emblem,
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

    def test_each_unlocked_award_family_uses_semantic_icon_once(self) -> None:
        provider = _IconProvider()
        renderer = PygameAchievementBadgeRenderer(provider)

        medal = renderer.render(
            _entry(unlocked=True, tier="silver", achievement_id="greia.test.medal"),
            96,
        )
        trophy = renderer.render(
            _entry(unlocked=True, tier="gold", achievement_id="greia.test.trophy"),
            96,
        )
        special = renderer.render(
            _entry(unlocked=True, tier="special", achievement_id="greia.test.special"),
            96,
        )

        self.assertEqual(provider.calls, 3)
        self.assertEqual(medal.get_size(), (96, 96))
        self.assertEqual(trophy.get_size(), (96, 96))
        self.assertEqual(special.get_size(), (96, 96))
        self.assertIsNot(medal, trophy)
        self.assertIsNot(trophy, special)

    def test_secret_gold_uses_special_family_but_keeps_bounded_cache(self) -> None:
        provider = _IconProvider()
        renderer = PygameAchievementBadgeRenderer(provider, max_entries=4)
        entry = _entry(
            unlocked=True,
            tier="gold",
            secret=True,
            achievement_id="greia.test.constellation",
        )

        first = renderer.render(entry, 110)
        second = renderer.render(entry, 110)

        self.assertIs(first, second)
        self.assertEqual(provider.calls, 1)
        self.assertEqual(first.get_size(), (110, 110))

    def test_admitted_activity_emblem_replaces_fallback_icon_and_is_cached(self) -> None:
        provider = _IconProvider()
        renderer = PygameAchievementBadgeRenderer(provider, max_entries=4)
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "emblem.png"
            source = pygame.Surface((64, 64), pygame.SRCALPHA)
            source.fill((0, 0, 0, 0))
            pygame.draw.circle(source, (42, 190, 110), (32, 32), 24)
            pygame.image.save(source, path)
            emblem = ActivityAchievementEmblem(
                activity_id="org.greia.test-activity",
                emblem_id="activity",
                asset_path=path,
                width=64,
                height=64,
                byte_size=path.stat().st_size,
            )
            entry = _entry(
                unlocked=True,
                tier="silver",
                achievement_id="greia.test.activity-art",
                activity_emblem=emblem,
            )

            first = renderer.render(entry, 96)
            second = renderer.render(entry, 96)

        self.assertIs(first, second)
        self.assertEqual(provider.calls, 0)
        self.assertEqual(first.get_size(), (96, 96))


if __name__ == "__main__":
    unittest.main()
