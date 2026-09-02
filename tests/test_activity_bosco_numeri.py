"""Unit tests for Il Bosco dei Numeri di Tito (org.greia.bosco-numeri)."""

from __future__ import annotations

import unittest
from pathlib import Path

from activities.bosco_numeri.bosco_content import NUMBERS_1_TO_10, ForestItemKind
from activities.bosco_numeri.bosco_model import BoscoModel


class TestBoscoNumeri(unittest.TestCase):
    """Test suite verifying mathematical domain logic, input handling, and timers."""

    def test_model_initialization(self) -> None:
        model = BoscoModel(current_number=1)
        self.assertEqual(model.current_number, 1)
        self.assertEqual(len(model.items), 1)
        self.assertEqual(model.counted_count, 0)
        self.assertFalse(model.celebrating)
        self.assertEqual(model.tito_mood, "neutral")

        # Verify 10-frame slots
        slots = model._calculate_ten_frame_slots()
        self.assertEqual(len(slots), 10)

    def test_setup_numbers_1_to_10(self) -> None:
        model = BoscoModel()
        for n in range(1, 11):
            model.setup_number(n)
            self.assertEqual(model.current_number, n)
            self.assertEqual(len(model.items), n)
            self.assertEqual(model.counted_count, 0)
            self.assertEqual(model.items[0].kind, NUMBERS_1_TO_10[n - 1].kind)

    def test_tap_counting_sequence(self) -> None:
        model = BoscoModel(current_number=3)
        # Tap first item
        outcome, num = model.handle_tap(model.items[0].x, model.items[0].y)
        self.assertEqual(outcome, "counted")
        self.assertEqual(num, 1)
        self.assertEqual(model.counted_count, 1)
        self.assertEqual(model.items[0].order_counted, 1)

        # Tap second item
        outcome, num = model.handle_tap(model.items[1].x, model.items[1].y)
        self.assertEqual(outcome, "counted")
        self.assertEqual(num, 2)
        self.assertEqual(model.counted_count, 2)

        # Tap already counted item
        outcome, num = model.handle_tap(model.items[0].x, model.items[0].y)
        self.assertEqual(outcome, "already_counted")

        # Tap empty space
        outcome, num = model.handle_tap(999.0, 999.0)
        self.assertEqual(outcome, "miss")

    def test_celebration_delay_prevents_audio_overlap(self) -> None:
        model = BoscoModel(current_number=2)
        model.handle_tap(model.items[0].x, model.items[0].y)
        self.assertFalse(model.pending_celebration)
        self.assertFalse(model.celebrating)

        # Tap final item
        model.handle_tap(model.items[1].x, model.items[1].y)
        self.assertTrue(model.pending_celebration)
        self.assertEqual(model.celebration_delay, 1.0)
        self.assertFalse(model.celebrating)

        # Update 0.5s: still pending (number audio playing)
        model.update(0.5)
        self.assertTrue(model.pending_celebration)
        self.assertFalse(model.celebrating)

        # Update another 0.6s (total > 1.0s): celebration erupts!
        model.update(0.6)
        self.assertFalse(model.pending_celebration)
        self.assertTrue(model.celebrating)
        self.assertEqual(model.tito_mood, "happy")
        self.assertEqual(model.total_completed, 1)

    def test_guess_challenge_mode(self) -> None:
        model = BoscoModel()
        model.setup_guess_round(target=7)
        self.assertEqual(model.guess_target, 7)
        self.assertIn(7, model.guess_options)
        self.assertEqual(len(model.guess_options), 3)

        # Wrong answer
        wrong_choice = [c for c in model.guess_options if c != 7][0]
        result = model.handle_guess_tap(wrong_choice)
        self.assertFalse(result)
        self.assertEqual(model.guess_wobble_card, wrong_choice)
        self.assertEqual(model.tito_mood, "surprised")

        # Correct answer
        result = model.handle_guess_tap(7)
        self.assertTrue(result)
        self.assertTrue(model.guess_solved)
        self.assertEqual(model.tito_mood, "happy")

    def test_next_prev_number_wrap(self) -> None:
        model = BoscoModel(current_number=10)
        model.next_number()
        self.assertEqual(model.current_number, 1)

        model.prev_number()
        self.assertEqual(model.current_number, 10)


if __name__ == "__main__":
    unittest.main()
