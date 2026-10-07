"""Session-scoped creation grant tests without Greia GUI dependencies."""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from greia_platform.creation_access import CreationAccessDenied, CreationSessionAccess
from greia_platform.creation_capacity import VolumeBudget, VolumeUsage
from greia_platform.creations import CreationLibrary


class PrivateStorage:
    def __init__(self, activity_id, files):
        self.activity_id = activity_id
        self.files = files

    def file_read(self, path):
        if path not in self.files:
            raise ValueError("no file in private namespace")
        return self.files[path]


class CreationAccessTests(unittest.TestCase):
    def setUp(self):
        t = tempfile.TemporaryDirectory()
        self.addCleanup(t.cleanup)
        budget = VolumeBudget(probe=lambda _: VolumeUsage(8*1024**3,2*1024**3,6*1024**3))
        self.library = CreationLibrary(Path(t.name)/"profile"/"creations", volume_budget=budget)
        self.time = 100.0
        self.reader_manifest = SimpleNamespace(activity_id="org.greia.theatre", creations_produces=(), creations_consumes=("text/plain",))
        self.producer_manifest = SimpleNamespace(activity_id="org.greia.writing", creations_produces=("text/plain",), creations_consumes=())
        self.writer = self.access(self.producer_manifest, PrivateStorage("org.greia.writing", {"draft.txt":b"hello"}), "writer-session")
        self.reader = self.access(self.reader_manifest, PrivateStorage("org.greia.theatre", {}), "reader-session")

    def access(self, manifest, storage, session):
        return CreationSessionAccess(library=self.library, storage=storage, manifest=manifest,
                                     authority=SimpleNamespace(activity_id=manifest.activity_id),
                                     session_id=session, clock=lambda: self.time)

    def test_publish_from_private_storage_not_arbitrary_other_activity(self):
        rec = self.writer.publish_private_file(filename="draft.txt", media_type="text/plain", role="story")
        self.assertEqual(rec.producer_id, "org.greia.writing")
        with self.assertRaises(ValueError):
            self.writer.publish_private_file(filename="../other.txt", media_type="text/plain", role="story")
        with self.assertRaises(CreationAccessDenied):
            self.reader.publish_private_file(filename="draft.txt", media_type="text/plain", role="story")

    def test_child_grant_required_not_guessable_or_reusable(self):
        rec = self.writer.publish_private_file(filename="draft.txt", media_type="text/plain", role="story")
        with self.assertRaises(CreationAccessDenied):
            self.reader.import_selected(rec.creation_id)
        with self.assertRaises(CreationAccessDenied):
            self.writer.grant_child_selection(rec.creation_id)
        ticket = self.reader.grant_child_selection(rec.creation_id)
        self.assertEqual(self.reader.import_selected(ticket).payload, b"hello")
        with self.assertRaises(CreationAccessDenied):
            self.reader.import_selected(ticket)

    def test_grants_cannot_cross_sessions_or_live_past_close(self):
        rec = self.writer.publish_private_file(filename="draft.txt", media_type="text/plain", role="story")
        ticket = self.reader.grant_child_selection(rec.creation_id)
        other = self.access(self.reader_manifest, PrivateStorage("org.greia.theatre", {}), "other-session")
        with self.assertRaises(CreationAccessDenied):
            other.import_selected(ticket)
        self.reader.close()
        with self.assertRaises(CreationAccessDenied):
            self.reader.import_selected(ticket)
        with self.assertRaises(CreationAccessDenied):
            self.reader.grant_child_selection(rec.creation_id)

    def test_grants_expire_and_are_type_scoped(self):
        rec = self.writer.publish_private_file(filename="draft.txt", media_type="text/plain", role="story")
        token = self.reader.grant_child_selection(rec.creation_id)
        self.time = 221.0
        with self.assertRaises(CreationAccessDenied):
            self.reader.import_selected(token)
        wrong = self.access(SimpleNamespace(activity_id="org.greia.picture", creations_produces=(), creations_consumes=("image/png",)),
                            PrivateStorage("org.greia.picture", {}), "picture")
        with self.assertRaises(CreationAccessDenied):
            wrong.grant_child_selection(rec.creation_id)

    def test_trusted_launch_identity_must_match_private_storage(self):
        with self.assertRaises(ValueError):
            self.access(self.producer_manifest, PrivateStorage("org.greia.other", {}), "writer")
        with self.assertRaises(ValueError):
            CreationSessionAccess(library=self.library, storage=PrivateStorage("org.greia.writing",{}),
                manifest=self.producer_manifest, authority=SimpleNamespace(activity_id="org.greia.other"),session_id="wrong")

    def test_no_activity_enumeration_or_delete_methods(self):
        self.assertFalse(hasattr(self.reader, "list"))
        self.assertFalse(hasattr(self.reader, "delete"))
        self.assertFalse(hasattr(self.reader, "read"))


if __name__ == "__main__":
    unittest.main()
