"""Trusted Creations selection protocol: no Pygame or actual profiles required."""
from __future__ import annotations

import unittest

from greia_launcher.creation_selection import CreationSelectionCoordinator, SelectionState
from greia_platform.creation_access import CreationAccessDenied


class FakeAccess:
    def __init__(self):
        self.consumable_media_types = frozenset(("image/png", "audio/wav"))
        self.grants = []

    def grant_child_selection(self, creation_id, *, only_media_types=None, only_roles=None):
        items = {"picture": ("image/png", "drawing"), "song": ("audio/wav", "song")}
        if creation_id not in items:
            raise CreationAccessDenied("unknown creation")
        kind, role = items[creation_id]
        if kind not in self.consumable_media_types:
            raise CreationAccessDenied("undeclared")
        if only_media_types is not None and kind not in only_media_types:
            raise CreationAccessDenied("not requested")
        if only_roles is not None and role not in only_roles:
            raise CreationAccessDenied("wrong role")
        self.grants.append(creation_id)
        return "one-use-handle"


class SelectionCoordinatorTests(unittest.TestCase):
    def setUp(self):
        self.now = 5.0
        self.access = FakeAccess()
        self.chooser = CreationSelectionCoordinator(
            self.access, "session-1", clock=lambda: self.now
        )
        self.chooser.enable_presenter()

    def test_absent_trusted_display_rejects_request_without_waiting(self):
        self.chooser.disable_presenter()
        with self.assertRaisesRegex(CreationAccessDenied, "display"):
            self.chooser.request(media_types=["image/png"])
        self.assertIsNone(self.chooser.trusted_pending())
        self.chooser.enable_presenter()
        request = self.chooser.request(media_types=["image/png"])
        self.chooser.disable_presenter()
        self.assertEqual(
            self.chooser.poll(request.request_id).state,
            SelectionState.CANCELLED,
        )

    def test_Activity_does_not_mint_selected_token(self):
        request = self.chooser.request(media_types=["image/png"], roles=["drawing"])
        self.assertEqual(request.session_id, "session-1")
        self.assertEqual(self.chooser.poll(request.request_id).state, SelectionState.PENDING)
        self.assertEqual(self.access.grants, [])
        self.assertEqual(self.chooser.trusted_pending(), request)
        self.chooser.trusted_complete(request.request_id, "picture")
        self.assertIsNone(self.chooser.trusted_pending())
        self.assertEqual(self.access.grants, ["picture"])
        response = self.chooser.poll(request.request_id)
        self.assertEqual(response.state, SelectionState.READY)
        self.assertEqual(response.selection_token, "one-use-handle")
        with self.assertRaises(CreationAccessDenied):
            self.chooser.poll(request.request_id)

    def test_narrowed_scope_roles_wrong_ids_and_replays_fail(self):
        request = self.chooser.request(media_types=("image/png",), roles=("drawing",))
        with self.assertRaises(CreationAccessDenied):
            self.chooser.trusted_complete(request.request_id, "song")
        with self.assertRaises(CreationAccessDenied):
            self.chooser.trusted_complete("forged", "picture")
        self.assertEqual(self.access.grants, [])
        self.chooser.trusted_complete(request.request_id, "picture")
        with self.assertRaises(CreationAccessDenied):
            self.chooser.trusted_complete(request.request_id, "picture")

    def test_empty_unsupported_duplicates_invalid_roles_fail(self):
        for media in ((), [], ("text/plain",), ("image/png", "image/png"), "image/png"):
            with self.subTest(media=media):
                with self.assertRaises(CreationAccessDenied):
                    self.chooser.request(media_types=media)
        for role in (("story?",), ("drawing", "drawing"), ("x",) * 9, "drawing"):
            with self.subTest(role=role):
                with self.assertRaises(CreationAccessDenied):
                    self.chooser.request(media_types=["image/png"], roles=role)
        self.assertIsNone(self.chooser.trusted_pending())

    def test_pending_request_is_unique_and_must_be_collected(self):
        request = self.chooser.request(media_types=["audio/wav"])
        with self.assertRaises(CreationAccessDenied):
            self.chooser.request(media_types=["audio/wav"])
        self.assertTrue(self.chooser.cancel(request.request_id))
        self.assertIsNone(self.chooser.trusted_pending())
        self.assertEqual(self.chooser.poll(request.request_id).state, SelectionState.CANCELLED)
        newer = self.chooser.request(media_types=["image/png"])
        self.assertNotEqual(newer.request_id, request.request_id)

    def test_deadline_cancellation_stale_requests_and_lifecycle(self):
        request = self.chooser.request(media_types=["image/png"])
        self.now += 181
        self.assertIsNone(self.chooser.trusted_pending())
        with self.assertRaises(CreationAccessDenied):
            self.chooser.trusted_complete(request.request_id, "picture")
        self.assertEqual(self.chooser.poll(request.request_id).state, SelectionState.CANCELLED)
        second = self.chooser.request(media_types=["audio/wav"])
        self.chooser.close()
        self.assertIsNone(self.chooser.trusted_pending())
        with self.assertRaises(CreationAccessDenied):
            self.chooser.poll(second.request_id)
        with self.assertRaises(CreationAccessDenied):
            self.chooser.request(media_types=["audio/wav"])

    def test_abandoned_result_releases_single_picker_slot(self):
        first = self.chooser.request(media_types=["image/png"])
        self.chooser.trusted_complete(first.request_id, "picture")
        with self.assertRaises(CreationAccessDenied):
            self.chooser.request(media_types=["audio/wav"])
        self.now += self.chooser.RESULT_RETENTION_SECONDS + 1
        second = self.chooser.request(media_types=["audio/wav"])
        self.assertNotEqual(second.request_id, first.request_id)
        with self.assertRaises(CreationAccessDenied):
            self.chooser.poll(first.request_id)

    def test_abandoned_timeout_is_not_permanent_busy_state(self):
        first = self.chooser.request(media_types=["image/png"])
        self.now += self.chooser.REQUEST_SECONDS + 1
        self.assertEqual(self.chooser.poll(first.request_id).state, SelectionState.CANCELLED)
        second = self.chooser.request(media_types=["audio/wav"])
        self.now += self.chooser.REQUEST_SECONDS + self.chooser.RESULT_RETENTION_SECONDS + 2
        third = self.chooser.request(media_types=["image/png"])
        self.assertNotEqual(third.request_id, second.request_id)

    def test_trusted_cancel_revokes_without_child_secret(self):
        request = self.chooser.request(media_types=["audio/wav"])
        self.chooser.trusted_cancel(request.request_id)
        with self.assertRaises(CreationAccessDenied):
            self.chooser.trusted_complete(request.request_id, "song")
        self.assertEqual(self.chooser.poll(request.request_id).state, SelectionState.CANCELLED)


if __name__ == "__main__":
    unittest.main()
