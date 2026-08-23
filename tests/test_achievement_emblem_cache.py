from __future__ import annotations

import hashlib
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
    emblem: ActivityAchievementEmblem,
    *,
    unlocked: bool = True,
    achievement_id: str = "greia.test.emblem-update",
) -> AchievementEntry:
    return AchievementEntry(
        definition=AchievementDefinition(
            achievement_id=achievement_id,
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
        unlocked_at=1.0 if unlocked else None,
        announced_at=None,
        seen_at=None,
    )


def _metadata(path: Path) -> tuple[int, str]:
    data = path.read_bytes()
    return len(data), hashlib.sha256(data).hexdigest()


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
            first_size, first_digest = _metadata(path)
            first_emblem = ActivityAchievementEmblem(
                activity_id="org.greia.test",
                emblem_id="activity",
                asset_path=path,
                width=64,
                height=64,
                byte_size=first_size,
                content_digest=first_digest,
            )

            first = renderer.render(_entry(first_emblem), 96)
            repeated = renderer.render(_entry(first_emblem), 96)

            source.fill((30, 190, 90, 255))
            pygame.image.save(source, path)
            second_size, second_digest = _metadata(path)
            self.assertNotEqual(first_digest, second_digest)
            second_emblem = ActivityAchievementEmblem(
                activity_id="org.greia.test",
                emblem_id="activity",
                asset_path=path,
                width=64,
                height=64,
                byte_size=second_size,
                content_digest=second_digest,
            )
            changed = renderer.render(_entry(second_emblem), 96)

        self.assertIs(first, repeated)
        self.assertIsNot(first, changed)
        self.assertEqual(provider.calls, 0)

    def test_locked_badge_never_reads_or_reveals_activity_emblem(self) -> None:
        provider = _IconProvider()
        renderer = PygameAchievementBadgeRenderer(provider)
        emblem = ActivityAchievementEmblem(
            activity_id="org.greia.test",
            emblem_id="private-until-earned",
            asset_path=Path("/missing/locked-emblem.png"),
            width=64,
            height=64,
            byte_size=100,
            content_digest="not-used-while-locked",
        )

        badge = renderer.render(
            _entry(
                emblem,
                unlocked=False,
                achievement_id="greia.test.locked-art",
            ),
            96,
        )

        self.assertEqual(provider.calls, 0)
        self.assertEqual(badge.get_size(), (96, 96))

    def test_unadmitted_changed_bytes_fail_soft_to_platform_icon(self) -> None:
        provider = _IconProvider()
        renderer = PygameAchievementBadgeRenderer(provider)
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "emblem.png"
            source = pygame.Surface((64, 64), pygame.SRCALPHA)
            source.fill((20, 140, 210, 255))
            pygame.image.save(source, path)
            admitted_size, admitted_digest = _metadata(path)
            emblem = ActivityAchievementEmblem(
                activity_id="org.greia.test",
                emblem_id="activity",
                asset_path=path,
                width=64,
                height=64,
                byte_size=admitted_size,
                content_digest=admitted_digest,
            )

            # Mutate the package after policy admission without presenting a new
            # fingerprint. The renderer must refuse these bytes and use icon_id.
            source.fill((220, 80, 70, 255))
            pygame.image.save(source, path)
            badge = renderer.render(
                _entry(emblem, achievement_id="greia.test.mutated-art"),
                96,
            )

        self.assertEqual(provider.calls, 1)
        self.assertEqual(badge.get_size(), (96, 96))


if __name__ == "__main__":
    unittest.main()
