from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from greia_platform.achievements import (
    AchievementCriterion,
    AchievementDefinition,
    AchievementPolicy,
    LocalizedAchievementText,
    ProfileAchievementService,
)
from greia_platform.history import HistorySummary
from greia_platform.profiles import ChildProfile, ProfileContext


def _copy(it: str, en: str) -> LocalizedAchievementText:
    return LocalizedAchievementText((("it", it), ("en", en)), "it")


def _definition(
    achievement_id: str,
    *,
    threshold: int = 1,
    secret: bool = False,
) -> AchievementDefinition:
    return AchievementDefinition(
        achievement_id=achievement_id,
        category="care",
        tier="bronze",
        icon_id="yellow_star",
        secret=secret,
        title=_copy("Titolo", "Title"),
        description=_copy("Descrizione", "Description"),
        locked_hint=_copy("Suggerimento", "Hint"),
        criteria=(
            AchievementCriterion(
                kind="event_count",
                threshold=float(threshold),
                activity_id="org.greia.test",
                event_id="test.completed",
            ),
        ),
    )


class _HistoryStore:
    def __init__(self, summary: HistorySummary) -> None:
        self._summary = summary

    def summary(self) -> HistorySummary:
        return self._summary


class _HistoryService:
    def __init__(self, summary: HistorySummary) -> None:
        self.summary = summary

    def open(self, _profile: ProfileContext) -> _HistoryStore:
        return _HistoryStore(self.summary)


class _Clock:
    def __init__(self, value: float = 100.0) -> None:
        self.value = value

    def __call__(self) -> float:
        return self.value


def _summary(count: int) -> HistorySummary:
    return HistorySummary(
        reward_balances=(),
        event_counts=(("org.greia.test:test.completed", count),),
        best_scores=(),
        recent_sessions=(),
    )


class AchievementCriterionTests(unittest.TestCase):
    def test_reward_balance_threshold(self) -> None:
        criterion = AchievementCriterion(
            kind="reward_balance",
            reward_id="star",
            threshold=5.0,
        )
        summary = HistorySummary(
            reward_balances=(("star", 5),),
            event_counts=(),
            best_scores=(),
            recent_sessions=(),
        )
        self.assertTrue(criterion.is_met(summary))

    def test_lower_is_better_best_score_can_use_at_most(self) -> None:
        criterion = AchievementCriterion(
            kind="best_score",
            activity_id="org.greia.test",
            event_id="race.finished",
            threshold=60.0,
            comparison="at_most",
        )
        fast = HistorySummary(
            reward_balances=(),
            event_counts=(),
            best_scores=(("org.greia.test:race.finished", 58.4),),
            recent_sessions=(),
        )
        slow = HistorySummary(
            reward_balances=(),
            event_counts=(),
            best_scores=(("org.greia.test:race.finished", 61.0),),
            recent_sessions=(),
        )
        self.assertTrue(criterion.is_met(fast))
        self.assertFalse(criterion.is_met(slow))


class AchievementServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        root = Path(self.temp.name)
        self.profile = ProfileContext(
            profile=ChildProfile(
                profile_id="child",
                display_name="Child",
                avatar_id="yellow_star",
                secret_digest=None,
                mask_secret=True,
            ),
            root=root,
            customization_dir=root / "customization",
            activities_dir=root / "activities",
            storage_dir=root / "storage",
            progress_dir=root / "progress",
        )
        self.clock = _Clock()

    def tearDown(self) -> None:
        self.temp.cleanup()

    def _service(
        self,
        summary: HistorySummary,
        *definitions: AchievementDefinition,
    ) -> ProfileAchievementService:
        policy = AchievementPolicy(1, "it", tuple(definitions))
        return ProfileAchievementService(
            policy,
            _HistoryService(summary),  # type: ignore[arg-type]
            clock=self.clock,
        )

    def test_unlock_is_derived_from_history_once(self) -> None:
        definition = _definition("greia.test.first")
        service = self._service(_summary(1), definition)

        first = service.refresh(self.profile)
        self.assertEqual(
            [entry.definition.achievement_id for entry in first.newly_unlocked],
            ["greia.test.first"],
        )
        self.assertEqual(first.unlocked_count, 1)
        self.assertEqual(first.entries[0].unlocked_at, 100.0)

        self.clock.value = 200.0
        second = service.refresh(self.profile)
        self.assertEqual(second.newly_unlocked, ())
        self.assertEqual(second.entries[0].unlocked_at, 100.0)

    def test_locked_secret_is_hidden_until_earned(self) -> None:
        definition = _definition("greia.test.secret", threshold=2, secret=True)
        service = self._service(_summary(1), definition)
        locked = service.refresh(self.profile)
        self.assertEqual(locked.visible_entries, ())

        service.history_service.summary = _summary(2)  # type: ignore[attr-defined]
        unlocked = service.refresh(self.profile)
        self.assertEqual(len(unlocked.visible_entries), 1)
        self.assertTrue(unlocked.visible_entries[0].unlocked)

    def test_announcement_and_seen_state_are_independent(self) -> None:
        definition = _definition("greia.test.presentation")
        service = self._service(_summary(1), definition)
        snapshot = service.refresh(self.profile)
        entry = snapshot.entries[0]
        self.assertTrue(entry.is_new)
        self.assertEqual(len(snapshot.pending_announcements), 1)

        self.clock.value = 120.0
        service.mark_announced(self.profile, definition.achievement_id)
        announced = service.snapshot(self.profile).entries[0]
        self.assertEqual(announced.announced_at, 120.0)
        self.assertTrue(announced.is_new)

        self.clock.value = 140.0
        service.mark_seen(self.profile, [definition.achievement_id])
        seen = service.snapshot(self.profile).entries[0]
        self.assertEqual(seen.seen_at, 140.0)
        self.assertFalse(seen.is_new)

    def test_missing_state_can_be_reconstructed_from_history(self) -> None:
        definition = _definition("greia.test.recover")
        service = self._service(_summary(1), definition)
        service.refresh(self.profile)
        state_path = self.profile.progress_dir / service.STATE_NAME
        backup_path = self.profile.progress_dir / service.BACKUP_NAME
        state_path.unlink()
        if backup_path.exists():
            backup_path.unlink()

        self.clock.value = 300.0
        rebuilt = service.refresh(self.profile)
        self.assertEqual(rebuilt.unlocked_count, 1)
        self.assertEqual(rebuilt.entries[0].unlocked_at, 300.0)

    def test_localized_copy_uses_exact_base_then_default_locale(self) -> None:
        text = _copy("Ciao", "Hello")
        self.assertEqual(text.resolve("en-US"), "Hello")
        self.assertEqual(text.resolve("it-IT"), "Ciao")
        self.assertEqual(text.resolve("fr-FR"), "Ciao")


if __name__ == "__main__":
    unittest.main()
