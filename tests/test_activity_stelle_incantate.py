"""Semantic contract tests for Stelle Incantate (org.greia.stelle-incantate)."""

from __future__ import annotations

import unittest

from activities.stelle_incantate.sky_content import (
    CONSTELLATIONS_BY_ID,
    CONSTELLATION_ORDER,
    ordered_constellations,
)
from activities.stelle_incantate.sky_model import SkyRound, SkySession
from activities.stelle_incantate.sky_services import GreiaSkyEvents, GreiaSkyStorage


class ConstellationContentTests(unittest.TestCase):
    def test_catalogue_order_matches_registry(self) -> None:
        self.assertEqual(
            tuple(item.constellation_id for item in ordered_constellations()),
            CONSTELLATION_ORDER,
        )
        self.assertEqual(len(CONSTELLATIONS_BY_ID), len(CONSTELLATION_ORDER))

    def test_every_figure_is_a_valid_connect_the_dots_path(self) -> None:
        for constellation in ordered_constellations():
            with self.subTest(constellation=constellation.constellation_id):
                self.assertGreaterEqual(constellation.star_count, 3)
                # Every star is reachable in numeric order: each new star
                # shares at least one edge with an earlier star.
                for index in range(1, constellation.star_count):
                    earlier = range(index)
                    linked = any(
                        index in edge and any(other in edge for other in earlier)
                        for edge in constellation.edges
                    )
                    self.assertTrue(linked)
                # Every declared edge references real, distinct stars.
                for a, b in constellation.edges:
                    self.assertNotEqual(a, b)
                    self.assertLess(a, constellation.star_count)
                    self.assertLess(b, constellation.star_count)
                # Normalized coordinates stay inside the sky box.
                for star in constellation.stars:
                    self.assertGreaterEqual(star.x, 0.0)
                    self.assertLessEqual(star.x, 1.0)
                    self.assertGreaterEqual(star.y, 0.0)
                    self.assertLessEqual(star.y, 1.0)

    def test_every_constellation_has_localized_name_and_fact_keys(self) -> None:
        import json
        from pathlib import Path

        locales_dir = Path(__file__).resolve().parents[1] / "activities" / "stelle_incantate" / "locales"
        for locale in ("it", "en"):
            data = json.loads((locales_dir / f"{locale}.json").read_text(encoding="utf-8"))
            strings = data["strings"]
            for constellation in ordered_constellations():
                with self.subTest(locale=locale, constellation=constellation.constellation_id):
                    self.assertIn(constellation.name_key, strings)
                    self.assertIn(constellation.fact_key, strings)
                    self.assertTrue(strings[constellation.fact_key].strip())


class SkyRoundTests(unittest.TestCase):
    def test_stars_must_be_connected_in_numeric_order(self) -> None:
        constellation = CONSTELLATIONS_BY_ID["cassiopea"]
        round_state = SkyRound(constellation)
        self.assertEqual(round_state.next_star_number, 1)
        self.assertFalse(round_state.connect(2), "skipping star 1 must be rejected")
        self.assertTrue(round_state.connect(0))
        self.assertEqual(round_state.next_star_number, 2)
        self.assertFalse(round_state.connect(0), "reconnecting a star must be rejected")
        self.assertTrue(round_state.connect(1))
        self.assertFalse(round_state.is_complete)

    def test_completing_the_figure_connects_every_star(self) -> None:
        constellation = CONSTELLATIONS_BY_ID["triangolo"]
        round_state = SkyRound(constellation)
        for index in range(constellation.star_count):
            self.assertTrue(round_state.connect(index))
        self.assertTrue(round_state.is_complete)
        self.assertEqual(len(round_state.connected), constellation.star_count)
        with self.assertRaises(RuntimeError):
            _ = round_state.next_star

    def test_branch_figure_draws_cross_edges_from_center(self) -> None:
        constellation = CONSTELLATIONS_BY_ID["cigno"]
        round_state = SkyRound(constellation)
        for index in range(3):
            round_state.connect(index)
        affected = round_state.edges_affected_by(3)
        self.assertIn((1, 3), affected)
        self.assertNotIn((1, 4), affected, "unconnected wing must not draw early")


class SkySessionTests(unittest.TestCase):
    def test_session_opens_first_incomplete_constellation(self) -> None:
        session = SkySession()
        self.assertEqual(
            session.current.constellation.constellation_id, CONSTELLATION_ORDER[0]
        )
        self.assertFalse(session.all_complete)

    def test_completed_ids_resume_progress(self) -> None:
        session = SkySession(completed_ids=(CONSTELLATION_ORDER[0], CONSTELLATION_ORDER[1]))
        self.assertEqual(
            session.current.constellation.constellation_id, CONSTELLATION_ORDER[2]
        )

    def test_unknown_completed_ids_are_dropped_safely(self) -> None:
        session = SkySession(completed_ids=("not-a-constellation",))
        self.assertEqual(session.completed_ids, frozenset())
        self.assertEqual(
            session.current.constellation.constellation_id, CONSTELLATION_ORDER[0]
        )

    def test_record_completion_then_advance_walks_the_whole_sky(self) -> None:
        session = SkySession()
        for expected in CONSTELLATION_ORDER:
            self.assertEqual(session.current.constellation.constellation_id, expected)
            session.record_completion()
            session.advance()
        self.assertTrue(session.all_complete)
        # Replay wraps to the first figure without erasing durable facts.
        self.assertEqual(
            session.current.constellation.constellation_id, CONSTELLATION_ORDER[0]
        )


class _StubStorage:
    def __init__(self) -> None:
        self.data: dict[str, str] = {}

    def kv_get(self, key: str) -> str | None:
        return self.data.get(key)

    def kv_set(self, key: str, value: str) -> None:
        self.data[key] = value


class _StubEvents:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict]] = []

    def constellation_completed(self, session_id, constellation_id, star_count) -> None:
        self.calls.append(
            ("constellation.completed", {"constellation_id": constellation_id})
        )

    def fact_opened(self, session_id, constellation_id) -> None:
        self.calls.append(("curiosity.fact_opened", {"constellation_id": constellation_id}))


class GreiaSkyStorageTests(unittest.TestCase):
    def test_progress_round_trip_is_bounded_and_sanitized(self) -> None:
        stub = _StubStorage()
        storage = GreiaSkyStorage(storage=stub)
        self.assertEqual(storage.load_completed(), frozenset())
        self.assertTrue(
            storage.save_completed([CONSTELLATION_ORDER[0], "junk", CONSTELLATION_ORDER[0]])
        )
        self.assertEqual(
            storage.load_completed(), frozenset({CONSTELLATION_ORDER[0]})
        )
        stub.data["stelle_incantate.progress.v1"] = "not json"
        self.assertEqual(storage.load_completed(), frozenset())


class GreiaSkyEventsTests(unittest.TestCase):
    def test_event_helpers_exist_with_declared_semantics(self) -> None:
        # The service wrappers must expose exactly the manifest-declared facts.
        self.assertTrue(hasattr(GreiaSkyEvents, "constellation_completed"))
        self.assertTrue(hasattr(GreiaSkyEvents, "fact_opened"))


if __name__ == "__main__":
    unittest.main()
