from __future__ import annotations

import json
import tempfile
import threading
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from greia_platform.software_update_jobs import (
    MAX_STALE_UPLOADS_PER_RECEIVE,
    SoftwareUpdateCapacityError,
    SoftwareUpdateJobError,
    SoftwareUpdateJobStore,
    software_update_bootstrap_available,
)
from greia_platform.system_updates import MIN_INBOX_FREE_BYTES


class SoftwareUpdateJobStoreTests(unittest.TestCase):
    def test_receive_lease_reaps_crash_leftover_but_never_an_active_upload(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            store = SoftwareUpdateJobStore(directory)
            crashed_upload = directory / f".uploading.{'a' * 32}.tmp"
            crashed_upload.write_bytes(b"partial bytes left by a stopped Parent")

            with store.receive_lease():
                self.assertFalse(crashed_upload.exists())

            first = SoftwareUpdateJobStore(directory)
            second = SoftwareUpdateJobStore(directory)
            active_upload = directory / f".uploading.{'b' * 32}.tmp"
            ready = threading.Event()
            release = threading.Event()

            def hold_live_upload() -> None:
                with first.receive_lease():
                    active_upload.write_bytes(b"still being received")
                    ready.set()
                    release.wait(timeout=5)

            worker = threading.Thread(target=hold_live_upload)
            worker.start()
            self.assertTrue(ready.wait(timeout=2))
            try:
                with self.assertRaisesRegex(SoftwareUpdateJobError, "upload is active"):
                    with second.receive_lease():
                        self.fail("second process entered the live receive lease")
                self.assertTrue(active_upload.exists())
            finally:
                release.set()
                worker.join(timeout=2)
            self.assertFalse(worker.is_alive())
            with second.receive_lease():
                self.assertFalse(active_upload.exists())

    def test_receive_reaper_is_bounded_and_preserves_unrecognized_files(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            store = SoftwareUpdateJobStore(directory)
            for index in range(MAX_STALE_UPLOADS_PER_RECEIVE + 1):
                (directory / f".uploading.{index:032x}.tmp").write_bytes(b"stale")
            unrelated = directory / ".uploading.not-a-uuid.tmp"
            unrelated.write_bytes(b"keep")

            with self.assertRaisesRegex(SoftwareUpdateJobError, "too many abandoned"):
                with store.receive_lease():
                    self.fail("receive lease should refuse an over-bound cleanup")
            self.assertTrue(unrelated.exists())
            self.assertEqual(len(list(directory.glob(".uploading.*.tmp"))), MAX_STALE_UPLOADS_PER_RECEIVE + 2)

    def test_receive_reaps_prejob_candidate_orphan_but_preserves_active_candidate(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            store = SoftwareUpdateJobStore(directory)
            old_staging = directory / f".uploading.{'1' * 32}.tmp"
            old_staging.write_bytes(b"previous package")
            old_job = store.accept_received(old_staging, len(b"previous package"))
            store.update(str(old_job["job_id"]), "failed", error_code="rejected")

            # Simulate process death immediately after replacing the fixed
            # candidate but before atomically publishing the new job record.
            orphan_staging = directory / f".uploading.{'2' * 32}.tmp"
            orphan_staging.write_bytes(b"orphaned package bytes")
            orphan_staging.replace(store.candidate_path)
            self.assertEqual(store.snapshot()["state"], "failed")
            with store.receive_lease():
                self.assertFalse(store.candidate_path.exists())

            active_staging = directory / f".uploading.{'3' * 32}.tmp"
            active_staging.write_bytes(b"currently authorized package")
            active_job = store.accept_received(
                active_staging,
                len(b"currently authorized package"),
            )
            with store.receive_lease():
                self.assertTrue(store.candidate_path.exists())
                self.assertEqual(store.read_internal()["job_id"], active_job["job_id"])

    def test_receive_preflight_preserves_the_minimum_parent_data_reserve(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            store = SoftwareUpdateJobStore(directory)
            package_bytes = 4096
            with patch(
                "greia_platform.software_update_jobs.shutil.disk_usage",
                return_value=SimpleNamespace(free=package_bytes + MIN_INBOX_FREE_BYTES - 1),
            ):
                with self.assertRaises(SoftwareUpdateCapacityError):
                    store.require_receive_capacity(package_bytes)
            self.assertEqual(list(directory.iterdir()), [])

            with patch(
                "greia_platform.software_update_jobs.shutil.disk_usage",
                return_value=SimpleNamespace(free=package_bytes + MIN_INBOX_FREE_BYTES),
            ):
                store.require_receive_capacity(package_bytes)

    def test_upload_is_published_as_candidate_job_then_pending_marker(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            staging = directory / ".uploading.test.tmp"
            staging.write_bytes(b"bounded package bytes")
            store = SoftwareUpdateJobStore(directory)

            accepted = store.accept_received(staging, len(b"bounded package bytes"))

            self.assertRegex(str(accepted["job_id"]), r"^[0-9a-f]{32}$")
            self.assertEqual(accepted["state"], "queued")
            self.assertTrue(accepted["activation_requested"])
            self.assertEqual(accepted["package_bytes"], len(b"bounded package bytes"))
            self.assertEqual(store.candidate_path.read_bytes(), b"bounded package bytes")
            self.assertEqual(store.pending_path.read_text().strip(), accepted["job_id"])
            envelope = json.loads(store.job_path.read_text())
            self.assertEqual(envelope["schema_version"], 1)
            self.assertEqual(envelope["job"]["job_id"], accepted["job_id"])

    def test_job_progress_is_publicly_whitelisted_and_full_system_restart_is_explicit(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            staging = directory / ".uploading.test.tmp"
            staging.write_bytes(b"package")
            store = SoftwareUpdateJobStore(directory)
            accepted = store.accept_received(staging, 7)
            job_id = str(accepted["job_id"])
            store.update(
                job_id,
                "validating",
                package_type="full_system",
                version="0.17.0",
                release_id="greia-0.17.0",
                package_sha256="a" * 64,
                candidate_generation="private-path-not-public",
            )
            self.assertNotIn("candidate_generation", store.snapshot())
            store.update(job_id, "ready_to_restart")
            self.assertTrue(store.snapshot()["restart_available"])
            self.assertFalse(store.pending_path.exists())

            restarted = store.request_restart()

            self.assertEqual(restarted["state"], "ready_to_restart")
            self.assertFalse(restarted["restart_available"])
            self.assertTrue(store.pending_path.exists())
            self.assertTrue(store.read_internal()["restart_requested"])
            store.update(job_id, "restarting")
            store.update(job_id, "applied")
            self.assertFalse(store.pending_path.exists())

    def test_invalid_job_transitions_and_non_full_system_restart_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            staging = directory / ".uploading.test.tmp"
            staging.write_bytes(b"package")
            store = SoftwareUpdateJobStore(directory)
            accepted = store.accept_received(staging, 7)
            job_id = str(accepted["job_id"])
            with self.assertRaises(SoftwareUpdateJobError):
                store.update(job_id, "ready_to_restart", package_type="activities")
            with self.assertRaises(SoftwareUpdateJobError):
                store.request_restart()
            store.update(job_id, "failed", error_code="invalid_package")
            with self.assertRaises(SoftwareUpdateJobError):
                store.update(job_id, "applied")

    def test_bootstrap_capability_requires_exact_marker_and_regular_helper(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            marker = root / "bootstrap.json"
            helper = root / "bootstrap.py"
            helper.write_text("BOOTSTRAP_VERSION = 1\n")
            marker.write_text('{"schema_version":1}\n')
            self.assertTrue(software_update_bootstrap_available(marker, helper))
            marker.write_text('{"schema_version":1,"extra":true}\n')
            self.assertFalse(software_update_bootstrap_available(marker, helper))
            marker.write_text('{"schema_version":1}\n')
            helper.write_text("BOOTSTRAP_VERSION = 2\n")
            self.assertFalse(software_update_bootstrap_available(marker, helper))
            helper.write_text("BOOTSTRAP_VERSION = 1\n")
            symlink = root / "helper-link.py"
            symlink.symlink_to(helper)
            self.assertFalse(software_update_bootstrap_available(marker, symlink))


if __name__ == "__main__":
    unittest.main()
