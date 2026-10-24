"""Device-owned Parent update jobs and their bounded HTTP contract."""

from __future__ import annotations

import copy
import hashlib
import http.client
import io
import json
import os
import tempfile
import threading
import time
import unittest
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from greia_parent.production_api import (
    ProductionParentApiApplication,
    ProductionParentApiHTTPServer,
)
from greia_parent.protocol import API_BASE, RESOURCES
from greia_parent.update_api import UpdateParentApiApplication
from greia_parent.update_catalog import (
    DeviceUpdateIdentity,
    UpdateCatalogClient,
    UpdateRelease,
)
from greia_parent.update_delivery import UpdateDeliveryError, UpdateDeliveryService
from greia_parent.update_job_store import UpdateJobStore
from greia_platform.system_updates import MIN_INBOX_FREE_BYTES, SystemUpdateInbox, build_update_bundle
from greia_platform.software_update_jobs import SoftwareUpdateJobStore


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PROFILE = "legacy-x86-i686-ab"
RELEASE_ID = "greia-0.14.0"
VERSION = "0.14.0"
INDEX_URL = "https://updates.example.test/greia-updates.json"
_ZSTD = b"\x28\xb5\x2f\xfd"


def _identity() -> DeviceUpdateIdentity:
    return DeviceUpdateIdentity(
        version="0.13.0",
        release_id="greia-0.13.0",
        profile=PROFILE,
        platform_family="legacy-x86",
        architecture="i386",
        board="acer",
    )


def _build_bundle(
    directory: Path,
    *,
    version: str = VERSION,
    release_id: str = RELEASE_ID,
) -> Path:
    payload = directory / "payload.ext4.zst"
    payload.write_bytes(_ZSTD + b"greia-test-payload" * 256)
    output = directory / "device-update.greiaupdate"
    build_update_bundle(
        payload_path=payload,
        hardware_support_path=None,
        output_path=output,
        version=version,
        release_id=release_id,
        platform_family="legacy-x86",
        architecture="i386",
        profile=PROFILE,
        payload_uncompressed_bytes=8 * 1024 * 1024,
        minimum_slot_bytes=8 * 1024 * 1024,
        persist_read_schema_min=1,
        persist_read_schema_max=1,
        persist_write_schema=1,
        release_notes="delivery test",
    )
    return output


def _release(bundle: Path) -> UpdateRelease:
    return UpdateRelease(
        release_id=RELEASE_ID,
        version=VERSION,
        profiles=(PROFILE,),
        target_profile=PROFILE,
        platform_family="legacy-x86",
        architecture="i386",
        board=None,
        url="https://cdn.example.test/updates/device-update.greiaupdate?release=0.14.0",
        size=bundle.stat().st_size,
        sha256=hashlib.sha256(bundle.read_bytes()).hexdigest(),
        published_at="2026-10-23T00:00:00Z",
        notes={"en": "Greia update"},
    )


def _status(*, single_root: bool = False, journal_state: str = "idle") -> dict[str, object]:
    return {
        "status": "OK",
        "restart_pending": False,
        "restart_request_id": None,
        "restart_state": None,
        "identity": {
            "version": "0.13.0",
            "release_id": "greia-0.13.0",
            "profile": PROFILE,
            "platform_family": "legacy-x86",
            "architecture": "i386",
            "board": "acer",
            "current_slot": "A",
        },
        "backend": {"available": True, "kind": "test", "reason": None},
        "layout": {
            "single_root": single_root,
            "slots": ["A", "B"] if not single_root else [],
            "active_slot": "A",
            "accepted_slot": "A",
        },
        "persist": {
            "available": not single_root,
            "schema": 1 if not single_root else None,
            "readable_min": 1 if not single_root else None,
            "readable_max": 1 if not single_root else None,
            "free_bytes": 8 * 1024 * 1024 * 1024 if not single_root else 0,
        },
        "journal": {
            "state": journal_state,
            "release_id": RELEASE_ID if journal_state == "update_staged" else "",
            "trial_slot": "B" if journal_state == "update_staged" else None,
            "decision": "staged" if journal_state == "update_staged" else "none",
        },
        "candidate": {"present": False, "release_id": None, "bundle_sha256": None},
        "activation_available": not single_root,
        "activation_reason": None if not single_root else "single-root layout has no A/B update slots",
    }


class _MemoryResponse(io.BytesIO):
    def __init__(self, content: bytes) -> None:
        super().__init__(content)
        self.status = 200
        self.headers = {"Content-Length": str(len(content))}


class _FakeCatalog:
    def __init__(self, release: UpdateRelease, content: bytes) -> None:
        self.release = release
        self.content = content
        self.open_count = 0
        self.fail_first_download = False
        self.fetch_count = 0
        self.resolve_count = 0

    def fetch(self, channel: str, identity: DeviceUpdateIdentity) -> tuple[UpdateRelease, ...]:
        self.fetch_count += 1
        return (self.release,) if channel == "stable" and identity.profile == PROFILE else ()

    def resolve(self, channel: str, identity: DeviceUpdateIdentity, release_id: str) -> UpdateRelease:
        self.resolve_count += 1
        if release_id != self.release.release_id or identity.profile != PROFILE:
            raise AssertionError("worker requested a release outside the device identity")
        return self.release

    def open_bundle(self, release: UpdateRelease, *, timeout_seconds: float = 30.0):
        self.open_count += 1
        content = self.content
        if self.fail_first_download and self.open_count == 1:
            content = content[: max(1, len(content) // 2)]
        return _MemoryResponse(content)


class _FakePrivilegedClient:
    def __init__(
        self,
        *,
        single_root: bool = False,
        staged_at_start: bool = False,
        block_stage: bool = False,
    ) -> None:
        self._state_lock = threading.Lock()
        self.state = _status(
            single_root=single_root,
            journal_state="update_staged" if staged_at_start else "idle",
        )
        self.calls: list[str] = []
        self.stage_count = 0
        self.restart_count = 0
        self.stage_started = threading.Event()
        self.allow_stage = threading.Event()
        self.stage_finished = threading.Event()
        self.status_wait_seen = threading.Event()
        self.block_stage = block_stage

    def request(self, op: str) -> dict[str, object]:
        with self._state_lock:
            self.calls.append(op)
        if op == "STATUS":
            if self.stage_started.is_set() and not self.stage_finished.is_set():
                self.status_wait_seen.set()
                self.allow_stage.wait(timeout=5)
            with self._state_lock:
                return copy.deepcopy(self.state)
        if op == "RECONCILE":
            return {"status": "OK", "reconciled": True}
        if op == "VERIFY_CURRENT_CANDIDATE":
            return {"status": "VERIFIED"}
        if op == "STAGE_CURRENT_CANDIDATE":
            with self._state_lock:
                self.stage_count += 1
            self.stage_started.set()
            if self.block_stage and not self.allow_stage.wait(timeout=10):
                raise TimeoutError("fake stage timed out")
            with self._state_lock:
                self.state["journal"] = {
                    "state": "update_staged",
                    "release_id": RELEASE_ID,
                    "trial_slot": "B",
                    "decision": "staged",
                }
            self.stage_finished.set()
            return {"status": "STAGED"}
        if op == "REQUEST_RESTART":
            self.restart_count += 1
            return {
                "status": "REFUSED",
                "reason": "profile picker or active child session blocks restart",
                "state": "update_staged",
            }
        raise AssertionError(f"unexpected privileged operation: {op}")


class _LostRestartReplyClient(_FakePrivilegedClient):
    """Model a root fence accepted before the Parent loses its reply."""

    def request(self, op: str) -> dict[str, object]:
        if op != "REQUEST_RESTART":
            return super().request(op)
        with self._state_lock:
            self.calls.append(op)
            self.restart_count += 1
            self.state["restart_pending"] = True
            self.state["restart_request_id"] = "c" * 32
            self.state["restart_state"] = "handoff_pending"
            self.state["journal"] = {
                "state": "one_shot_armed",
                "release_id": RELEASE_ID,
                "trial_slot": "B",
                "decision": "armed",
            }
            count = self.restart_count
        if count == 1:
            raise TimeoutError("lost restart reply after fence was recorded")
        with self._state_lock:
            self.state["restart_state"] = "systemd_accepted"
        return {
            "status": "RESTART_ACCEPTED",
            "request_id": "c" * 32,
            "state": "systemd_accepted",
        }


class _UnavailableWifi:
    def available(self) -> bool:
        return False

    def management_available(self) -> bool:
        return False

    def scan(self):
        raise AssertionError("unavailable Wi-Fi must not scan")

    def connect(self, network, passphrase=""):
        raise AssertionError("unavailable Wi-Fi must not connect")


def _make_app(
    root: Path,
    catalog: object,
    privileged: _FakePrivilegedClient,
    *,
    production: bool = False,
    software_update_enabled: bool = False,
    software_update_job_store: SoftwareUpdateJobStore | None = None,
):
    app_type = ProductionParentApiApplication if production else UpdateParentApiApplication
    kwargs: dict[str, object] = {}
    if production:
        kwargs["wifi_backend"] = _UnavailableWifi()
    environment = {
        "GREIA_SYSTEM_UPDATE_CHANNEL": "stable",
        "GREIA_PARENT_SYSTEM_UPDATE_UPLOAD": "0",
        "GREIA_PARENT_ACTIVITY_INSTALL": "0",
        "GREIA_PARENT_ACTIVITY_PACKAGE_ROOT": str(root / "activity-packages"),
    }
    with patch.dict(os.environ, environment, clear=False):
        return app_type(
            PROJECT_ROOT,
            root / "parent-state",
            hardware_settings_dir=root / "hardware-settings",
            hardware_status_path=root / "hardware-status.json",
            profiles_dir=root / "profiles",
            active_profile_status_path=root / "active-profile.json",
            update_catalog_client=catalog,
            update_privileged_client=privileged,
            software_update_enabled=software_update_enabled,
            software_update_job_store=software_update_job_store,
            **kwargs,
        )


def _wait_for_state(app, expected: str, timeout: float = 5.0) -> dict[str, object]:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        delivery = getattr(app, "update_delivery", app)
        job = delivery.snapshot().get("job")
        if isinstance(job, dict) and job.get("state") == expected:
            return job
        time.sleep(0.01)
    delivery = getattr(app, "update_delivery", app)
    raise AssertionError(f"update job did not reach {expected!r}: {delivery.snapshot()!r}")


class ParentUpdateDeliveryTests(unittest.TestCase):
    def test_software_package_upload_is_durable_before_ack_and_restart_is_separate(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            bundle = _build_bundle(root)
            catalog = _FakeCatalog(_release(bundle), bundle.read_bytes())
            store = SoftwareUpdateJobStore(root / "software-updates")
            store.directory.mkdir()
            app = _make_app(
                root,
                catalog,
                _FakePrivilegedClient(),
                production=True,
                software_update_enabled=True,
                software_update_job_store=store,
            )
            token = app.device_credentials.issue("software package test").token
            server = ProductionParentApiHTTPServer(("127.0.0.1", 0), app)
            server_thread = threading.Thread(target=server.serve_forever, daemon=True)
            server_thread.start()

            def request(path: str, method: str, body: bytes, content_type: str):
                connection = http.client.HTTPConnection("127.0.0.1", server.server_address[1], timeout=15)
                try:
                    connection.request(
                        method,
                        path,
                        body=body,
                        headers={
                            "Authorization": f"Bearer {token}",
                            "Content-Type": content_type,
                        },
                    )
                    response = connection.getresponse()
                    raw = response.read()
                    return response.status, json.loads(raw.decode()) if raw else {}
                finally:
                    connection.close()

            try:
                status, accepted = request(
                    f"{API_BASE}/system/update/package",
                    "POST",
                    b"deferred manifest inspection",
                    "application/vnd.greia.software-update+zip",
                )
                self.assertEqual(status, 202)
                self.assertEqual(accepted["job"]["state"], "queued")
                self.assertTrue(store.candidate_path.is_file())
                self.assertTrue(store.job_path.is_file())
                self.assertTrue(store.pending_path.is_file())
                self.assertEqual(store.candidate_path.read_bytes(), b"deferred manifest inspection")

                status, current = request(
                    f"{API_BASE}/system/update",
                    "GET",
                    b"",
                    "application/json",
                )
                self.assertEqual(status, 200)
                public_job = current["software_update"]["job"]
                self.assertEqual(public_job["job_id"], accepted["job"]["job_id"])
                self.assertNotIn("candidate_generation", public_job)
                self.assertFalse(public_job["restart_available"])
                store.update(str(public_job["job_id"]), "validating", package_type="full_system")
                store.update(str(public_job["job_id"]), "ready_to_restart")
                status, ready_status = request(
                    f"{API_BASE}/system/update",
                    "GET",
                    b"",
                    "application/json",
                )
                self.assertEqual(status, 200)
                self.assertTrue(ready_status["software_update"]["restart_available"])

                status, restarted = request(
                    f"{API_BASE}/system/update/package/restart",
                    "POST",
                    b"{}",
                    "application/json",
                )
                self.assertEqual(status, 202)
                self.assertEqual(restarted["job"]["state"], "ready_to_restart")
                self.assertFalse(restarted["job"]["restart_available"])
                self.assertTrue(store.read_internal()["restart_requested"])
                self.assertTrue(store.pending_path.is_file())
            finally:
                server.shutdown()
                server.server_close()
                server_thread.join(timeout=2)

    def test_software_package_upload_rejects_insufficient_reserved_space_before_staging(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            bundle = _build_bundle(root)
            catalog = _FakeCatalog(_release(bundle), bundle.read_bytes())
            store = SoftwareUpdateJobStore(root / "software-updates")
            store.directory.mkdir()
            app = _make_app(
                root,
                catalog,
                _FakePrivilegedClient(),
                production=True,
                software_update_enabled=True,
                software_update_job_store=store,
            )
            token = app.device_credentials.issue("software package capacity test").token
            server = ProductionParentApiHTTPServer(("127.0.0.1", 0), app)
            server_thread = threading.Thread(target=server.serve_forever, daemon=True)
            server_thread.start()
            body = b"must not be staged without the Parent/data reserve"
            connection = http.client.HTTPConnection("127.0.0.1", server.server_address[1], timeout=15)
            try:
                with patch(
                    "greia_platform.software_update_jobs.shutil.disk_usage",
                    return_value=SimpleNamespace(free=len(body) + MIN_INBOX_FREE_BYTES - 1),
                ):
                    connection.request(
                        "POST",
                        f"{API_BASE}/system/update/package",
                        body=body,
                        headers={
                            "Authorization": f"Bearer {token}",
                            "Content-Type": "application/vnd.greia.software-update+zip",
                        },
                    )
                    response = connection.getresponse()
                    payload = json.loads(response.read().decode())
                self.assertEqual(response.status, 507)
                self.assertEqual(payload["error"]["code"], "insufficient_storage")
                self.assertFalse(store.candidate_path.exists())
                self.assertFalse(store.job_path.exists())
                self.assertFalse(store.pending_path.exists())
                self.assertEqual(list(store.directory.glob(".uploading.*.tmp")), [])
            finally:
                connection.close()
                server.shutdown()
                server.server_close()
                server_thread.join(timeout=2)

    def test_protocol_advertises_check_prepare_restart_routes(self) -> None:
        resources = {item.name: item for item in RESOURCES}
        for name, path in (
            ("system_update_check", f"{API_BASE}/system/update/check"),
            ("system_update_prepare", f"{API_BASE}/system/update/prepare"),
            ("system_update_restart", f"{API_BASE}/system/update/restart"),
        ):
            self.assertEqual(resources[name].path, path)
            self.assertEqual(resources[name].methods, ("POST",))

    def test_catalog_requires_exact_device_compatibility_and_allows_catalogued_https_bundle(self) -> None:
        identity = _identity()
        matching = {
            "release_id": RELEASE_ID,
            "version": VERSION,
            "profiles": [PROFILE],
            "platform_family": "legacy-x86",
            "architecture": "i386",
            "board": "acer",
            "published_at": "2026-10-23T00:00:00Z",
            "notes": {"en": "Greia update"},
            "update": {
                "url": "https://cdn.example.test/releases/greia.greiaupdate?token=opaque",
                "size": 4096,
                "sha256": "a" * 64,
            },
        }
        rows = [
            matching,
            {**matching, "release_id": "wrong-board", "board": "pi400"},
            {**matching, "release_id": "wrong-family", "platform_family": "arm"},
            {**matching, "release_id": "wrong-arch", "architecture": "amd64"},
            {**matching, "release_id": "wrong-profile", "profiles": ["legacy-x86-i686"]},
        ]

        class Response(io.BytesIO):
            pass

        class Opener:
            def open(self, request, timeout=0):
                return Response(
                    json.dumps(
                        {"schema": "greia-updates/1", "greia_os": {"channels": {"stable": rows}}}
                    ).encode()
                )

        catalog = UpdateCatalogClient(INDEX_URL, opener=Opener())
        releases = catalog.fetch("stable", identity)
        self.assertEqual([item.release_id for item in releases], [RELEASE_ID])
        self.assertEqual(releases[0].target_profile, PROFILE)
        self.assertNotIn("url", releases[0].public_dict())

    def test_catalog_offers_only_newer_numeric_versions_and_orders_prereleases(self) -> None:
        identity = DeviceUpdateIdentity(
            version="0.9.0",
            release_id="greia-0.9.0",
            profile=PROFILE,
            platform_family="legacy-x86",
            architecture="i386",
            board="acer",
        )
        template = {
            "profiles": [PROFILE],
            "platform_family": "legacy-x86",
            "architecture": "i386",
            "board": "acer",
            "published_at": "2026-10-23T00:00:00Z",
            "notes": {},
            "update": {"url": "https://cdn.example.test/u", "size": 4096, "sha256": "a" * 64},
        }
        rows = [
            {**template, "release_id": "older", "version": "0.8.99"},
            {**template, "release_id": "same", "version": "0.9"},
            {**template, "release_id": "rc", "version": "0.10.0-rc.1"},
            {**template, "release_id": "stable", "version": "0.10.0"},
            {**template, "release_id": "bad", "version": "unknown"},
        ]

        class Opener:
            def open(self, request, timeout=0):
                return io.BytesIO(
                    json.dumps(
                        {"schema": "greia-updates/1", "greia_os": {"channels": {"stable": rows}}}
                    ).encode()
                )

        catalog = UpdateCatalogClient(INDEX_URL, opener=Opener())
        self.assertEqual(
            [release.release_id for release in catalog.fetch("stable", identity)],
            ["stable", "rc"],
        )
        unknown_identity = DeviceUpdateIdentity(
            version="unknown",
            release_id="unknown",
            profile=PROFILE,
            platform_family="legacy-x86",
            architecture="i386",
            board="acer",
        )
        self.assertEqual(catalog.fetch("stable", unknown_identity), ())

    def test_http_jobs_are_durable_deduplicated_and_status_is_cached_during_stage(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            bundle = _build_bundle(root)
            release = _release(bundle)
            catalog = _FakeCatalog(release, bundle.read_bytes())
            privileged = _FakePrivilegedClient(block_stage=True)
            app = _make_app(root, catalog, privileged, production=True)
            token = app.device_credentials.issue("Update test").token
            server = ProductionParentApiHTTPServer(("127.0.0.1", 0), app)
            server_thread = threading.Thread(target=server.serve_forever, daemon=True)
            server_thread.start()
            base = f"http://127.0.0.1:{server.server_address[1]}"

            def request(path: str, method: str, body: dict[str, object] | None = None):
                connection = http.client.HTTPConnection("127.0.0.1", server.server_address[1], timeout=15)
                payload = json.dumps(body).encode() if body is not None else None
                headers = {"Authorization": f"Bearer {token}"}
                if payload is not None:
                    headers["Content-Type"] = "application/json"
                try:
                    connection.request(method, path, body=payload, headers=headers)
                    response = connection.getresponse()
                    raw = response.read()
                    return response.status, json.loads(raw.decode()) if raw else {}
                finally:
                    connection.close()

            try:
                status, _ = request(f"{API_BASE}/system/update/prepare", "POST", {"release_id": RELEASE_ID, "url": "https://wrong.test"})
                self.assertEqual(status, 400)
                status, _ = request(f"{API_BASE}/system/update/check", "POST", {"url": "https://wrong.test"})
                self.assertEqual(status, 400)

                status, response = request(f"{API_BASE}/system/update/check", "POST", {})
                self.assertEqual(status, 202)
                self.assertEqual(response["job"]["operation"], "check")
                self.assertNotIn("expected", response["job"])
                _wait_for_state(app, "checked")

                status, response = request(
                    f"{API_BASE}/system/update/prepare", "POST", {"release_id": RELEASE_ID}
                )
                self.assertEqual(status, 202)
                prepared_id = response["job"]["job_id"]
                self.assertTrue(privileged.stage_started.wait(3))
                status_calls_before = privileged.calls.count("STATUS")

                # Simulate a simultaneous ordinary Parent request owning the
                # shared lock while root is serially blocked in STAGE.
                result: list[tuple[int, dict[str, object]]] = []
                server.request_lock.acquire()
                get_thread = threading.Thread(
                    target=lambda: result.append(request(f"{API_BASE}/system/update", "GET")),
                    daemon=True,
                )
                try:
                    get_thread.start()
                    get_thread.join(timeout=1.0)
                    self.assertFalse(get_thread.is_alive(), "cached update status waited behind a Parent lock")
                finally:
                    server.request_lock.release()
                self.assertEqual(result[0][0], 200)
                status_payload = result[0][1]
                self.assertEqual(status_payload["delivery"]["job"]["state"], "staging")
                self.assertEqual(privileged.calls.count("STATUS"), status_calls_before)
                self.assertNotIn("url", status_payload["delivery"]["catalog"]["releases"][0])

                system_status, system_payload = request(f"{API_BASE}/system", "GET")
                self.assertEqual(system_status, 200)
                os_identity = system_payload["os"]
                self.assertTrue(
                    {"version", "release_id", "profile", "platform_family", "architecture", "board", "channel"}
                    <= set(os_identity)
                )
                self.assertEqual(privileged.calls.count("STATUS"), status_calls_before)

                status, duplicate = request(
                    f"{API_BASE}/system/update/prepare", "POST", {"release_id": RELEASE_ID}
                )
                self.assertEqual(status, 202)
                self.assertEqual(duplicate["job"]["job_id"], prepared_id)
                self.assertEqual(privileged.stage_count, 1)
                with self.assertRaisesRegex(UpdateDeliveryError, "using the receive inbox"):
                    with app.update_delivery.manual_upload_lease():
                        pass

                privileged.allow_stage.set()
                _wait_for_state(app, "ready_to_restart")
                self.assertEqual(privileged.stage_count, 1)
                # An already-prepared update must remain restartable when
                # online catalog delivery is later disabled.
                app.system_update_online_enabled = False
                status, restart = request(f"{API_BASE}/system/update/restart", "POST", {})
                self.assertEqual(status, 202)
                self.assertEqual(restart["job"]["state"], "restart_pending")
                _wait_for_state(app, "ready_to_restart")
                self.assertEqual(privileged.restart_count, 1)
                self.assertEqual(app.update_delivery.snapshot()["job"]["operation"], "prepare")
            finally:
                privileged.allow_stage.set()
                server.shutdown()
                server.server_close()
                server_thread.join(timeout=3)

    def test_interrupted_staging_recovers_from_journal_without_a_second_stage(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            bundle = _build_bundle(root)
            release = _release(bundle)
            content = bundle.read_bytes()
            state_dir = root / "state"
            inbox = SystemUpdateInbox(state_dir)
            staging = inbox.create_receive_staging(len(content))
            staging.write_bytes(content)
            inbox.receive_staged(staging)

            store = UpdateJobStore(state_dir)
            now = datetime.now(timezone.utc).isoformat()
            store.update_check(
                {
                    "channel": "stable",
                    "checked_at": now,
                    "releases": [release.public_dict()],
                }
            )
            store.update_readiness(
                {
                    "observed_at": now,
                    "activation_available": True,
                    "activation_reason": "A/B update is ready",
                    "installed_version": "0.13.0",
                }
            )
            store.update_job(
                {
                    "job_id": "a" * 32,
                    "operation": "prepare",
                    "state": "staging",
                    "release_id": RELEASE_ID,
                    "version": VERSION,
                    "expected": release.public_dict(),
                    "created_at": now,
                    "updated_at": now,
                    "downloaded_bytes": len(content),
                    "total_bytes": len(content),
                    "error_code": None,
                    "error_message": None,
                }
            )
            catalog = _FakeCatalog(release, content)
            privileged = _FakePrivilegedClient(staged_at_start=True)
            with privileged._state_lock:
                privileged.state["candidate"] = {
                    "present": True,
                    "release_id": RELEASE_ID,
                    "bundle_sha256": release.sha256,
                }
            service = UpdateDeliveryService(
                state_dir,
                inbox,
                catalog=catalog,  # type: ignore[arg-type]
                privileged=privileged,
            )
            deadline = time.monotonic() + 3
            while time.monotonic() < deadline:
                job = service.snapshot()["job"]
                if isinstance(job, dict) and job.get("state") == "ready_to_restart":
                    break
                time.sleep(0.01)
            else:
                self.fail(f"recovered job did not finish: {service.snapshot()!r}")
            self.assertEqual(privileged.stage_count, 0)
            self.assertEqual(service.snapshot()["job"]["state"], "ready_to_restart")
            self.assertFalse(inbox.candidate_path.exists())

    def test_staged_recovery_preserves_candidate_when_root_identity_or_digest_differs(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            bundle = _build_bundle(root)
            release = _release(bundle)
            other_directory = root / "other"
            other_directory.mkdir()
            other_bundle = _build_bundle(
                other_directory,
                version="0.15.0",
                release_id="greia-0.15.0",
            )
            other_digest = hashlib.sha256(other_bundle.read_bytes()).hexdigest()
            state_dir = root / "state"
            inbox = SystemUpdateInbox(state_dir)
            staging = inbox.create_receive_staging(other_bundle.stat().st_size)
            staging.write_bytes(other_bundle.read_bytes())
            inbox.receive_staged(staging)

            store = UpdateJobStore(state_dir)
            now = datetime.now(timezone.utc).isoformat()
            store.update_job(
                {
                    "job_id": "e" * 32,
                    "operation": "prepare",
                    "state": "staging",
                    "release_id": RELEASE_ID,
                    "version": VERSION,
                    "expected": release.public_dict(),
                    "created_at": now,
                    "updated_at": now,
                    "downloaded_bytes": other_bundle.stat().st_size,
                    "total_bytes": other_bundle.stat().st_size,
                    "error_code": None,
                    "error_message": None,
                }
            )
            privileged = _FakePrivilegedClient(staged_at_start=True)
            with privileged._state_lock:
                privileged.state["candidate"] = {
                    "present": True,
                    "release_id": "greia-0.15.0",
                    "bundle_sha256": other_digest,
                }
            service = UpdateDeliveryService(
                state_dir,
                inbox,
                catalog=_FakeCatalog(release, bundle.read_bytes()),  # type: ignore[arg-type]
                privileged=privileged,
            )

            recovered = _wait_for_state(service, "ready_to_restart")
            self.assertEqual(recovered["release_id"], RELEASE_ID)
            self.assertEqual(privileged.stage_count, 0)
            self.assertTrue(inbox.candidate_path.exists())
            self.assertEqual(inbox.candidate_path.read_bytes(), other_bundle.read_bytes())

    def test_lost_stage_reply_discards_only_the_root_identified_staged_candidate(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            bundle = _build_bundle(root)
            release = _release(bundle)

            class LostStageReplyClient(_FakePrivilegedClient):
                def request(self, op: str) -> dict[str, object]:
                    if op != "STAGE_CURRENT_CANDIDATE":
                        return super().request(op)
                    with self._state_lock:
                        self.stage_count += 1
                        self.state["journal"] = {
                            "state": "update_staged",
                            "release_id": RELEASE_ID,
                            "trial_slot": "B",
                            "decision": "staged",
                        }
                        self.state["candidate"] = {
                            "present": True,
                            "release_id": RELEASE_ID,
                            "bundle_sha256": release.sha256,
                        }
                    raise TimeoutError("stage completed but its Parent reply was lost")

            privileged = LostStageReplyClient()
            app = _make_app(root, _FakeCatalog(release, bundle.read_bytes()), privileged)
            app.check_system_update()
            _wait_for_state(app, "checked")
            app.prepare_system_update(RELEASE_ID)

            _wait_for_state(app, "ready_to_restart")
            self.assertEqual(privileged.stage_count, 1)
            self.assertFalse(app.update_inbox.candidate_path.exists())

    def test_restart_queued_while_prepare_worker_exits_is_dispatched_once(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            bundle = _build_bundle(root)
            release = _release(bundle)
            privileged = _FakePrivilegedClient()
            app = _make_app(root, _FakeCatalog(release, bundle.read_bytes()), privileged)
            app.check_system_update()
            _wait_for_state(app, "checked")

            prepare_is_done = threading.Event()
            allow_prepare_worker_to_exit = threading.Event()
            run_prepare = app.update_delivery._run_prepare

            def finish_but_hold_worker(job: dict[str, object]) -> None:
                run_prepare(job)
                prepare_is_done.set()
                if not allow_prepare_worker_to_exit.wait(timeout=5):
                    raise TimeoutError("test did not release prepare worker")

            app.update_delivery._run_prepare = finish_but_hold_worker  # type: ignore[method-assign]
            app.prepare_system_update(RELEASE_ID)
            self.assertTrue(prepare_is_done.wait(timeout=5))
            self.assertEqual(app.update_delivery.snapshot()["job"]["state"], "ready_to_restart")

            queued = app.request_system_update_restart()
            self.assertEqual(queued["state"], "restart_pending")
            self.assertEqual(privileged.restart_count, 0)
            allow_prepare_worker_to_exit.set()

            _wait_for_state(app, "ready_to_restart")
            self.assertEqual(privileged.restart_count, 1)
            self.assertEqual(app.update_delivery.snapshot()["job"]["operation"], "prepare")

    def test_lost_restart_reply_exposes_only_an_explicit_idempotent_retry(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            bundle = _build_bundle(root)
            release = _release(bundle)
            privileged = _LostRestartReplyClient()
            app = _make_app(root, _FakeCatalog(release, bundle.read_bytes()), privileged)
            app.check_system_update()
            _wait_for_state(app, "checked")
            app.prepare_system_update(RELEASE_ID)
            _wait_for_state(app, "ready_to_restart")

            app.request_system_update_restart()
            recovered = _wait_for_state(app, "ready_to_restart")
            self.assertEqual(privileged.restart_count, 1)
            self.assertEqual(recovered["restart_request_id"], "c" * 32)
            self.assertTrue(app.system_update_payload()["restart_available"])

            retry = app.request_system_update_restart()
            self.assertEqual(retry["state"], "restart_pending")
            deadline = time.monotonic() + 3
            while time.monotonic() < deadline:
                job = app.update_delivery.snapshot()["job"]
                if (
                    isinstance(job, dict)
                    and job.get("state") == "restart_pending"
                    and job.get("restart_state") == "systemd_accepted"
                ):
                    break
                time.sleep(0.01)
            self.assertEqual(privileged.restart_count, 2)
            self.assertEqual(job["restart_request_id"], "c" * 32)
            self.assertEqual(job["restart_state"], "systemd_accepted")

    def test_parent_restart_recovery_reconciles_handoff_without_rebooting_again(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            release = _release(_build_bundle(root))
            state_dir = root / "state"
            store = UpdateJobStore(state_dir)
            now = datetime.now(timezone.utc).isoformat()
            store.update_job(
                {
                    "job_id": "d" * 32,
                    "operation": "restart",
                    "state": "restart_pending",
                    "release_id": RELEASE_ID,
                    "version": VERSION,
                    "expected": release.public_dict(),
                    "restart_dispatch_pending": False,
                    "restart_request_id": "c" * 32,
                    "created_at": now,
                    "updated_at": now,
                    "downloaded_bytes": 0,
                    "total_bytes": 0,
                    "error_code": None,
                    "error_message": None,
                }
            )
            privileged = _FakePrivilegedClient()
            with privileged._state_lock:
                privileged.state["restart_pending"] = True
                privileged.state["restart_request_id"] = "c" * 32
                privileged.state["restart_state"] = "handoff_pending"
                privileged.state["journal"] = {
                    "state": "one_shot_armed",
                    "release_id": RELEASE_ID,
                    "trial_slot": "B",
                    "decision": "armed",
                }
            service = UpdateDeliveryService(
                state_dir,
                SystemUpdateInbox(state_dir),
                catalog=_FakeCatalog(release, b""),  # type: ignore[arg-type]
                privileged=privileged,
            )
            _wait_for_state(service, "ready_to_restart")
            self.assertEqual(privileged.restart_count, 0)
            self.assertEqual(service.snapshot()["job"]["restart_request_id"], "c" * 32)

    def test_single_root_readiness_fails_closed_even_when_catalog_has_a_release(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            bundle = _build_bundle(root)
            release = _release(bundle)
            privileged = _FakePrivilegedClient(single_root=True)
            app = _make_app(root, _FakeCatalog(release, bundle.read_bytes()), privileged)
            app.check_system_update()
            _wait_for_state(app, "checked")
            payload = app.system_update_payload()
            self.assertFalse(payload["activation_available"])
            self.assertFalse(payload["prepare_available"])
            self.assertFalse(payload["delivery"]["readiness"]["available"])
            with self.assertRaisesRegex(UpdateDeliveryError, "not currently ready"):
                app.prepare_system_update(RELEASE_ID)
            self.assertEqual(privileged.stage_count, 0)

    def test_interrupted_download_is_cleaned_up_and_can_be_retried(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            bundle = _build_bundle(root)
            release = _release(bundle)
            catalog = _FakeCatalog(release, bundle.read_bytes())
            catalog.fail_first_download = True
            privileged = _FakePrivilegedClient()
            app = _make_app(root, catalog, privileged)
            app.check_system_update()
            _wait_for_state(app, "checked")

            first = app.prepare_system_update(RELEASE_ID)
            _wait_for_state(app, "failed")
            self.assertNotEqual(first["job_id"], "")
            self.assertFalse(app.update_inbox.uploading_path.exists())

            second = app.prepare_system_update(RELEASE_ID)
            self.assertNotEqual(second["job_id"], first["job_id"])
            _wait_for_state(app, "ready_to_restart")
            self.assertEqual(catalog.open_count, 2)
            self.assertEqual(privileged.stage_count, 1)

    def test_catalog_matched_manual_upload_uses_the_same_verify_and_stage_job(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            bundle = _build_bundle(root)
            content = bundle.read_bytes()
            release = _release(bundle)
            catalog = _FakeCatalog(release, content)
            privileged = _FakePrivilegedClient()
            app = _make_app(root, catalog, privileged)
            app.check_system_update()
            _wait_for_state(app, "checked")

            with app.update_delivery.manual_upload_lease():
                staging = app.update_inbox.create_receive_staging(len(content))
                staging.write_bytes(content)
                app.update_inbox.receive_staged(staging)
            with privileged._state_lock:
                privileged.state["candidate"] = {
                    "present": True,
                    "release_id": RELEASE_ID,
                    "bundle_sha256": release.sha256,
                }

            app.prepare_system_update(RELEASE_ID)
            _wait_for_state(app, "ready_to_restart")
            self.assertEqual(catalog.open_count, 0)
            self.assertEqual(privileged.stage_count, 1)


if __name__ == "__main__":
    unittest.main()
