from __future__ import annotations

import unittest

from greia_launcher.key_chord import KeyChordTracker


class KeyChordTrackerTests(unittest.TestCase):
    def test_empty_keys_raise_value_error(self) -> None:
        with self.assertRaises(ValueError):
            KeyChordTracker([])
        with self.assertRaises(ValueError):
            KeyChordTracker([115], hold_duration_seconds=0.0)

    def test_single_key_hold_does_not_activate_multi_key_chord(self) -> None:
        tracker = KeyChordTracker({ord("s"), ord("t")}, hold_duration_seconds=5.0)
        self.assertFalse(tracker.is_holding)
        self.assertEqual(tracker.progress(10.0), 0.0)

        tracker.handle_key_down(ord("s"), now=10.0)
        self.assertFalse(tracker.is_holding)
        self.assertFalse(tracker.poll(now=16.0))
        self.assertEqual(tracker.progress(16.0), 0.0)

    def test_both_keys_held_for_duration_activates_and_triggers_once(self) -> None:
        tracker = KeyChordTracker({ord("s"), ord("t")}, hold_duration_seconds=5.0)

        # Press 's' at t=10.0
        self.assertFalse(tracker.handle_key_down(ord("s"), now=10.0))
        # Press 't' at t=12.0 -> Chord begins at t=12.0
        self.assertFalse(tracker.handle_key_down(ord("t"), now=12.0))
        self.assertTrue(tracker.is_holding)

        # At t=14.5, progress is 50%
        self.assertAlmostEqual(tracker.progress(now=14.5), 0.5, places=2)
        self.assertFalse(tracker.poll(now=14.5))

        # At t=17.0 (12.0 + 5.0), activates
        self.assertTrue(tracker.poll(now=17.0))
        self.assertTrue(tracker.is_triggered)

        # Subsequent polls do not re-trigger
        self.assertFalse(tracker.poll(now=18.0))

    def test_releasing_key_resets_chord_progress(self) -> None:
        tracker = KeyChordTracker({ord("s"), ord("t")}, hold_duration_seconds=5.0)

        tracker.handle_key_down(ord("s"), now=10.0)
        tracker.handle_key_down(ord("t"), now=10.0)
        self.assertTrue(tracker.is_holding)
        self.assertAlmostEqual(tracker.progress(now=13.0), 0.6, places=2)

        # Release 's' before 5 seconds elapsed
        tracker.handle_key_up(ord("s"))
        self.assertFalse(tracker.is_holding)
        self.assertEqual(tracker.progress(now=14.0), 0.0)
        self.assertFalse(tracker.poll(now=16.0))

        # Press 's' again -> fresh 5 second window
        tracker.handle_key_down(ord("s"), now=15.0)
        self.assertTrue(tracker.is_holding)
        self.assertFalse(tracker.poll(now=19.0))
        self.assertTrue(tracker.poll(now=20.0))


if __name__ == "__main__":
    unittest.main()
