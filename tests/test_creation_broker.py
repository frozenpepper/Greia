"""Real Unix-socket transport tests for the trusted creations broker.

Exercises exactly the same per-session socket server as Activity storage.
No GUI/Pygame or profile filesystem mount is needed for this focused gate.
"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from greia_launcher.storage_broker import ActivityStorageBroker
from greia_platform.creation_access import CreationSessionAccess
from greia_platform.creation_capacity import VolumeBudget, VolumeUsage
from greia_platform.creation_client import ActivityCreationsClient
from greia_platform.creations import CreationLibrary
from greia_platform.storage_client import ActivityStorageClient, StorageClientError


class _PrivateStorage:
    """Only the production storage operations used by creation exchange."""

    def __init__(self, activity_id: str, files: dict[str, bytes]):
        self.activity_id = activity_id
        self.files = files
        self.policy = SimpleNamespace(
            max_file_bytes=16 * 1024 * 1024,
            max_kv_value_bytes=256 * 1024,
        )

    def file_read(self, name: str) -> bytes:
        if name not in self.files:
            raise ValueError("not a file in this Activity's private storage")
        return self.files[name]


class CreationBrokerTests(unittest.TestCase):
    def setUp(self) -> None:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        capacity = VolumeBudget(
            probe=lambda _: VolumeUsage(8 * 1024**3, 2 * 1024**3, 6 * 1024**3)
        )
        self.library = CreationLibrary(self.root / "child" / "creations", volume_budget=capacity)
        self.runtime_root = self.root / "sockets"
        self.runtime_root.mkdir()
        self.brokers: list[ActivityStorageBroker] = []

    def _start(self, activity_id: str, files: dict[str, bytes], *, producing: bool, consuming: bool):
        storage = _PrivateStorage(activity_id, files)
        suffix = len(self.brokers) + 1
        session_id = f"session{suffix}"
        access = CreationSessionAccess(
            library=self.library,
            storage=storage,
            manifest=SimpleNamespace(
                activity_id=activity_id,
                creations_produces=("text/plain",) if producing else (),
                creations_consumes=("text/plain",) if consuming else (),
            ),
            authority=SimpleNamespace(activity_id=activity_id),
            session_id=session_id,
        )
        broker = ActivityStorageBroker.start(
            storage,
            session_id,
            runtime_root=self.runtime_root,
            sandboxed=False,
        )
        self.brokers.append(broker)
        self.addCleanup(broker.stop)
        client = ActivityCreationsClient(
            ActivityStorageClient(broker.host_socket, broker.session_token)
        )
        return access, broker, client

    def test_broker_denies_unbound_creation_operations(self) -> None:
        access, broker, client = self._start(
            "org.greia.writing", {"draft.txt": b"hello"}, producing=True, consuming=False
        )
        with self.assertRaisesRegex(StorageClientError, "unauthorized"):
            client.publish_private_file(
                "draft.txt", media_type="text/plain", role="story"
            )
        broker.bind_creations(access)
        created = client.publish_private_file(
            "draft.txt", media_type="text/plain", role="story"
        )
        self.assertEqual(created["producer_id"], "org.greia.writing")
        self.assertEqual(self.library.read(created["creation_id"]), b"hello")

        with self.assertRaises(StorageClientError):
            client.storage_session._request("creations.list")
        with self.assertRaises(StorageClientError):
            client.storage_session._request("creations.delete", creation_id=created["creation_id"])

    def test_child_selected_handle_imports_once_and_expires_with_session(self) -> None:
        writer, first, sender = self._start(
            "org.greia.writing", {"draft.txt": b"forest"}, producing=True, consuming=False
        )
        first.bind_creations(writer)
        record = sender.publish_private_file("draft.txt", media_type="text/plain", role="story")

        reader, second, receiver = self._start(
            "org.greia.theatre", {}, producing=False, consuming=True
        )
        second.bind_creations(reader)
        with self.assertRaisesRegex(StorageClientError, "unauthorized"):
            receiver.import_selected(record["creation_id"])
        token = reader.grant_child_selection(record["creation_id"])
        result = receiver.import_selected(token)
        self.assertEqual(result.payload, b"forest")
        self.assertEqual(result.record["creation_id"], record["creation_id"])
        with self.assertRaisesRegex(StorageClientError, "unauthorized"):
            receiver.import_selected(token)

        reader.close()
        with self.assertRaisesRegex(StorageClientError, "unauthorized"):
            receiver.import_selected("forged")

    def test_nonblocking_broker_picker_requires_trusted_child_choice(self) -> None:
        writer, first, publisher = self._start(
            "org.greia.writing", {"draft.txt": b"forest"},
            producing=True, consuming=False,
        )
        first.bind_creations(writer)
        saved = publisher.publish_private_file(
            "draft.txt", media_type="text/plain", role="story"
        )

        reader, second, consumer = self._start(
            "org.greia.theatre", {}, producing=False, consuming=True
        )
        second.bind_creations(reader)
        with self.assertRaisesRegex(StorageClientError, "unauthorized"):
            consumer.request_selection(media_types=("audio/wav",))
        request_id = consumer.request_selection(
            media_types=("text/plain",), roles=("story",)
        )
        pending = second.pending_creation_selection()
        self.assertIsNotNone(pending)
        self.assertEqual(pending.request_id, request_id)
        self.assertEqual(pending.media_types, ("text/plain",))
        self.assertEqual(consumer.poll_selection(request_id).state, "pending")
        with self.assertRaisesRegex(StorageClientError, "unsupported"):
            consumer.storage_session._request(
                "creations.grant", creation_id=saved["creation_id"]
            )
        second.complete_creation_selection(request_id, saved["creation_id"])
        self.assertIsNone(second.pending_creation_selection())
        result = consumer.poll_selection(request_id)
        self.assertEqual(result.state, "ready")
        self.assertTrue(result.selection_token)
        imported = consumer.import_selected(result.selection_token)
        self.assertEqual(imported.payload, b"forest")
        with self.assertRaisesRegex(StorageClientError, "unauthorized"):
            consumer.import_selected(result.selection_token)
        with self.assertRaisesRegex(StorageClientError, "unauthorized"):
            consumer.poll_selection(request_id)

    def test_selection_cancellation_and_unrelated_session_are_denied(self) -> None:
        reader, broker, client = self._start(
            "org.greia.theatre", {}, producing=False, consuming=True
        )
        broker.bind_creations(reader)
        request_id = client.request_selection(media_types=("text/plain",))
        with self.assertRaisesRegex(StorageClientError, "unauthorized"):
            client.poll_selection("forged")
        self.assertTrue(client.cancel_selection(request_id))
        self.assertEqual(client.poll_selection(request_id).state, "cancelled")
        with self.assertRaisesRegex(StorageClientError, "unauthorized"):
            client.poll_selection(request_id)
        second_request = client.request_selection(media_types=("text/plain",))
        broker.stop()
        with self.assertRaises(StorageClientError):
            client.poll_selection(second_request)

    def test_producer_and_reader_permissions_are_independent(self) -> None:
        writer, broker, client = self._start(
            "org.greia.writing", {"draft.txt": b"text"},
            producing=True, consuming=False,
        )
        broker.bind_creations(writer)
        record = client.publish_private_file("draft.txt", media_type="text/plain", role="story")
        with self.assertRaisesRegex(StorageClientError, "unauthorized"):
            client.import_selected(record["creation_id"])


if __name__ == "__main__":
    unittest.main()
