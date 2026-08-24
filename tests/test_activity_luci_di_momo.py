from __future__ import annotations

from pathlib import Path
import random
import sys
import tomllib
import unittest


ROOT = Path(__file__).resolve().parents[1]
ACTIVITY_ROOT = ROOT / "activities" / "luci_di_momo"
for path in (ROOT / "src", ACTIVITY_ROOT):
    value = str(path)
    if value not in sys.path:
        sys.path.insert(0, value)

from firefly_model import (  # noqa: E402
    AttemptSummary,
    FireflyRoundFactory,
    FireflySession,
    HISTORY_LIMIT,
    MIN_CENTER_SEPARATION,
    adapt_level,
)
from firefly_services import FireflyProgress, GreiaFireflyProgress  # noqa: E402


class FireflyRoundFactoryTests(unittest.TestCase):
    def test_seed_is_deterministic_and_rounds_obey_bounds(self) -> None:
        first = FireflyRoundFactory(random.Random(12345)).build_set(4)
        second = FireflyRoundFactory(random.Random(12345)).build_set(4)
        self.assertEqual(first, second)
        self.assertEqual(len(first), 5)
        for round_ in first:
            self.assertIn(round_.quantity, round_.choice_values)
            self.assertEqual(len(set(round_.choice_values)), 3)
            self.assertEqual(len(round_.positions), round_.quantity)
            for index, point in enumerate(round_.positions):
                for other in round_.positions[index + 1:]:
                    dx = point[0] - other[0]
                    dy = point[1] - other[1]
                    self.assertGreaterEqual((dx * dx + dy * dy) ** 0.5, MIN_CENTER_SEPARATION)

    def test_each_level_uses_planned_quantity_and_reveal_bounds(self) -> None:
        expected = {
            1: (1, 3, 1600),
            2: (1, 4, 1400),
            3: (1, 5, 1200),
            4: (1, 5, 1100),
        }
        for level, (low, high, reveal) in expected.items():
            rounds = FireflyRoundFactory(random.Random(level)).build_set(level)
            self.assertTrue(all(low <= item.quantity <= high for item in rounds))
            self.assertTrue(all(item.reveal_ms == reveal for item in rounds))


class FireflySessionTests(unittest.TestCase):
    def _session(self) -> FireflySession:
        rounds = FireflyRoundFactory(random.Random(77)).build_set(2)
        return FireflySession(rounds, level=2)

    def test_wrong_answer_and_replay_do_not_advance_round(self) -> None:
        session = self._session()
        current = session.current_round
        assert current is not None
        wrong = next(value for value in current.choice_values if value != current.quantity)

        result = session.choose(wrong)
        self.assertFalse(result.correct)
        self.assertEqual(session.round_index, 0)
        self.assertIs(session.current_round, current)

        session.mark_replay()
        self.assertEqual(session.round_index, 0)
        self.assertIs(session.current_round, current)

        result = session.choose(current.quantity)
        self.assertTrue(result.correct)
        self.assertTrue(result.used_replay)
        self.assertFalse(result.first_attempt_success)
        self.assertEqual(session.round_index, 1)

    def test_completion_payload_is_one_shot(self) -> None:
        session = self._session()
        while not session.is_complete:
            current = session.current_round
            assert current is not None
            session.choose(current.quantity)

        payload = session.consume_completion()
        self.assertIsNotNone(payload)
        assert payload is not None
        self.assertEqual(payload["level"], 2)
        self.assertEqual(payload["first_attempt_count"], 5)
        self.assertIsNone(session.consume_completion())


class AdaptationTests(unittest.TestCase):
    def test_level_moves_only_from_bounded_recent_evidence(self) -> None:
        strong = [AttemptSummary(True, 0, False) for _ in range(HISTORY_LIMIT)]
        self.assertEqual(adapt_level(2, strong), 3)

        scaffolded = [AttemptSummary(False, 2, False) for _ in range(3)]
        self.assertEqual(adapt_level(3, scaffolded), 2)

        mixed = [AttemptSummary(True, 0, False), AttemptSummary(False, 1, True)]
        self.assertEqual(adapt_level(2, mixed), 2)


class _Storage:
    def __init__(self, value=None) -> None:
        self.value = value
        self.saved = None

    def kv_get(self, key):
        return self.value

    def kv_set(self, key, value):
        self.saved = value


class ProgressTests(unittest.TestCase):
    def test_malformed_storage_recovers_and_save_is_bounded(self) -> None:
        storage = _Storage({"schema_version": 1, "level": 99, "history": ["bad"]})
        repo = GreiaFireflyProgress(storage)
        self.assertEqual(repo.load(), FireflyProgress())

        history = [AttemptSummary(i % 2 == 0, i % 3, False) for i in range(20)]
        repo.save(4, history)
        self.assertIsNotNone(storage.saved)
        self.assertEqual(storage.saved["level"], 4)
        self.assertEqual(len(storage.saved["history"]), HISTORY_LIMIT)


class ManifestTests(unittest.TestCase):
    def test_manifest_declares_exact_completion_and_adaptive_range(self) -> None:
        manifest = tomllib.loads((ACTIVITY_ROOT / "activity.toml").read_text(encoding="utf-8"))
        self.assertEqual(manifest["activity"]["id"], "org.greia.luci-di-momo")
        self.assertEqual(manifest["activity"]["languages"], ["it", "en"])
        self.assertEqual(manifest["input"]["profile"], "pointer")
        self.assertEqual(manifest["education"]["difficulty_min"], 1)
        self.assertEqual(manifest["education"]["difficulty_max"], 4)
        self.assertEqual(
            manifest["education"]["events"],
            [{"id": "firefly.garden_completed", "kind": "completion"}],
        )


if __name__ == "__main__":
    unittest.main()
