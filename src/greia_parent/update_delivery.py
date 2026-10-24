"""Durable, unprivileged owner for one Greia system-update operation.

The worker owns catalog lookup and network transfer. It receives bytes through
the existing single-candidate inbox, then asks the typed root service to
verify and stage that current candidate. HTTP handlers only queue work or read
the bounded snapshot; they never wait for network transfer or slot staging.
"""

from __future__ import annotations

import threading
import time
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator, Mapping, Protocol
from uuid import uuid4

from greia_platform.system_updates import (
    MIN_INBOX_FREE_BYTES,
    SystemUpdateInbox,
)

from greia_parent.update_catalog import (
    DeviceUpdateIdentity,
    UpdateCatalogClient,
    UpdateCatalogError,
    UpdateRelease,
)
from greia_parent.update_bundle_transfer import UpdateBundleReceiver
from greia_parent.update_job_store import (
    ACTIVE_STATES,
    READY_STATES,
    UpdateDeliveryError,
    UpdateJobStore,
)


READINESS_MAX_AGE_SECONDS = 300.0
RESTART_STATUS_ATTEMPTS = 3
RESTART_STATUS_RETRY_SECONDS = 0.25

_ACTIVE_STATES = ACTIVE_STATES
_READY_STATES = READY_STATES


class PrivilegedUpdateClient(Protocol):
    """Typed AF_UNIX update client; requests contain an operation only."""

    def request(self, op: str) -> dict[str, object]: ...


class _UnavailableUpdateClient:
    def request(self, op: str) -> dict[str, object]:
        raise UpdateDeliveryError("Greia system-update service is unavailable")


class UpdateDeliveryService:
    """Own the device-side check/download/verify/stage/restart job lifecycle."""

    def __init__(
        self,
        state_dir: Path,
        inbox: SystemUpdateInbox,
        *,
        catalog: UpdateCatalogClient,
        privileged: PrivilegedUpdateClient | None = None,
        channel: str = "stable",
    ) -> None:
        if channel not in {"stable", "dev"}:
            raise UpdateDeliveryError("Greia update channel is invalid")
        self.inbox = inbox
        self.catalog = catalog
        self.receiver = UpdateBundleReceiver(inbox, catalog)
        self.privileged = privileged or _default_privileged_client()
        self.channel = channel
        self.store = UpdateJobStore(state_dir)
        self._inbox_lock = threading.Lock()
        self._worker_lock = threading.Lock()
        self._worker: threading.Thread | None = None
        self._recover_persisted_job()

    def snapshot(self) -> dict[str, object]:
        """Return cached status without touching the privileged service."""

        state = self.store.snapshot()
        readiness = state.get("readiness")
        now = time.time()
        public_readiness: dict[str, object] = {
            "available": False,
            "reason": "Greia update readiness has not been checked",
            "observed_at": None,
            "stale": True,
            "installed_version": None,
        }
        if isinstance(readiness, dict):
            observed_at = readiness.get("observed_at")
            age = _age_seconds(observed_at, now)
            public_readiness = {
                "available": readiness.get("activation_available") is True,
                "reason": _public_activation_reason(readiness.get("activation_reason")),
                "observed_at": observed_at,
                "stale": age is None or age > READINESS_MAX_AGE_SECONDS,
                "installed_version": _bounded_text(readiness.get("installed_version"), 64),
            }
            if public_readiness["stale"] is True:
                public_readiness["available"] = False
                public_readiness["reason"] = "Greia update readiness is stale; check again"

        last_check = state.get("last_check")
        public_check: dict[str, object] = {
            "checked_at": None,
            "channel": self.channel,
            "releases": [],
        }
        if isinstance(last_check, dict) and last_check.get("channel") == self.channel:
            public_check = {
                "checked_at": last_check.get("checked_at"),
                "channel": self.channel,
                "releases": list(last_check.get("releases", [])),
            }

        return {
            "job": state.get("job"),
            "readiness": public_readiness,
            "catalog": public_check,
        }

    def check(self) -> dict[str, object]:
        """Queue one short catalog/readiness check; return without network I/O."""

        existing = self._job()
        if isinstance(existing, dict) and existing.get("operation") == "check" and existing.get("state") == "checking":
            return existing
        if _job_blocks_new_operation(existing):
            raise UpdateDeliveryError("another Greia system update operation is active")
        job = _new_job("check", None, None, None)
        job = self._queue_job_with_inbox_claim(job)
        self._start_worker(job["job_id"])
        return job

    def prepare(self, release_id: str) -> dict[str, object]:
        """Queue a catalog-selected release; the worker re-resolves it."""

        if not isinstance(release_id, str) or not release_id or len(release_id) > 96:
            raise UpdateDeliveryError("release_id is invalid")
        existing = self._job()
        if isinstance(existing, dict) and existing.get("release_id") == release_id:
            if existing.get("state") in _ACTIVE_STATES | _READY_STATES:
                return existing
        if _job_blocks_new_operation(existing):
            raise UpdateDeliveryError("another Greia system update operation is active")
        snapshot = self.store.snapshot()
        check = snapshot.get("last_check")
        if not isinstance(check, dict) or check.get("channel") != self.channel:
            raise UpdateDeliveryError("check for Greia updates before preparing a release")
        releases = check.get("releases")
        selected = next(
            (
                row
                for row in releases
                if isinstance(row, dict) and row.get("release_id") == release_id
            ),
            None,
        ) if isinstance(releases, list) else None
        if not isinstance(selected, dict):
            raise UpdateDeliveryError("release_id was not returned by the latest Greia update check")
        readiness = snapshot.get("readiness")
        if not _readiness_ready(readiness, now=time.time()):
            raise UpdateDeliveryError("this Greia device is not currently ready for an A/B update")
        job = _new_job(
            "prepare",
            release_id,
            _bounded_text(selected.get("version"), 64),
            selected,
        )
        job = self._queue_job_with_inbox_claim(job)
        self._start_worker(job["job_id"])
        return job

    def request_restart(self) -> dict[str, object]:
        """Queue explicit Parent restart authorization through Greia's broker."""

        existing = self._job()
        if not isinstance(existing, dict) or existing.get("state") != "ready_to_restart":
            raise UpdateDeliveryError("Greia has no staged update ready to restart")
        job = dict(existing)
        job.update(
            {
                "operation": "restart",
                "state": "restart_pending",
                "restart_dispatch_pending": True,
                "updated_at": _timestamp(),
                "error_code": None,
                "error_message": None,
            }
        )
        self.store.update_job(job)
        self._start_worker(job["job_id"])
        return job

    @contextmanager
    def manual_upload_lease(self) -> Iterator[None]:
        """Exclude file upload while an online operation owns the fixed inbox."""

        if not self._inbox_lock.acquire(blocking=False):
            raise UpdateDeliveryError("another Greia update is using the receive inbox")
        try:
            if _job_blocks_new_operation(self._job()):
                raise UpdateDeliveryError("another Greia system update operation is active")
            yield
        finally:
            self._inbox_lock.release()

    def _queue_job_with_inbox_claim(self, job: Mapping[str, object]) -> dict[str, object]:
        if not self._inbox_lock.acquire(blocking=False):
            raise UpdateDeliveryError("another Greia update is using the receive inbox")
        try:
            existing = self._job()
            same_operation = (
                isinstance(existing, dict)
                and existing.get("operation") == job.get("operation")
                and existing.get("release_id") == job.get("release_id")
                and existing.get("state") in _ACTIVE_STATES | _READY_STATES
            )
            if same_operation:
                return existing
            if _job_blocks_new_operation(existing):
                raise UpdateDeliveryError("another Greia system update operation is active")
            self.store.update_job(job)
            return dict(job)
        finally:
            self._inbox_lock.release()

    def _recover_persisted_job(self) -> None:
        job = self._job()
        if not isinstance(job, dict):
            return
        state = job.get("state")
        operation = job.get("operation")
        if operation == "check" and state == "checking":
            job["state"] = "checking"
            job["updated_at"] = _timestamp()
            self.store.update_job(job)
            self._start_worker(job["job_id"])
        elif operation == "prepare" and state in {"queued", "downloading", "receiving", "verifying", "staging"}:
            job["state"] = "queued"
            job["updated_at"] = _timestamp()
            self.store.update_job(job)
            self._start_worker(job["job_id"])
        elif operation == "restart" and state == "restart_pending":
            # A restart request may have crossed the reboot boundary even when
            # its reply was lost. Reconcile only; never issue a second reboot
            # automatically after Parent process recovery.
            self._start_worker(job["job_id"], recovered_state="restart_pending")

    def _start_worker(self, job_id: object, *, recovered_state: str | None = None) -> None:
        if not isinstance(job_id, str):
            return
        with self._worker_lock:
            if self._worker is not None and self._worker.is_alive():
                return
            worker = threading.Thread(
                target=self._run,
                args=(job_id, recovered_state),
                name="greia-system-update-delivery",
                daemon=True,
            )
            self._worker = worker
            worker.start()

    def _run(self, job_id: str, recovered_state: str | None) -> None:
        try:
            job = self._job()
            if not isinstance(job, dict) or job.get("job_id") != job_id:
                return
            operation = job.get("operation")
            if operation == "check":
                self._run_check(job)
            elif operation == "prepare":
                self._run_prepare(job)
            elif operation == "restart":
                self._run_restart(job, recovered_state)
        except UpdateDeliveryError as exc:
            self._fail(job_id, _error_code(exc), str(exc))
        except UpdateCatalogError:
            self._fail(job_id, "catalog_unavailable", "Greia could not verify the update catalog")
        except Exception:
            self._fail(job_id, "operation_failed", "Greia could not complete the update operation")
        finally:
            with self._worker_lock:
                if self._worker is threading.current_thread():
                    self._worker = None
            pending = self._job()
            dispatch_pending_restart = (
                isinstance(pending, dict)
                and pending.get("operation") == "restart"
                and pending.get("state") == "restart_pending"
                and pending.get("restart_dispatch_pending") is True
            )
            if isinstance(pending, dict) and (
                pending.get("state") in _ACTIVE_STATES or dispatch_pending_restart
            ):
                self._start_worker(pending.get("job_id"))

    def _run_check(self, job: dict[str, object]) -> None:
        status = self._request_status(reconcile=False)
        readiness = _readiness_record(status)
        self.store.update_readiness(readiness)
        identity = DeviceUpdateIdentity.from_status(status)
        releases = self.catalog.fetch(self.channel, identity)
        public_releases = [release.public_dict() for release in releases]
        check = {
            "channel": self.channel,
            "checked_at": _timestamp(),
            "releases": public_releases,
        }
        self.store.update_check(check)
        job.update(
            {
                "state": "checked",
                "updated_at": _timestamp(),
                "release_count": len(public_releases),
                "error_code": None,
                "error_message": None,
            }
        )
        self.store.update_job(job)

    def _run_prepare(self, job: dict[str, object]) -> None:
        release_id = job.get("release_id")
        if not isinstance(release_id, str):
            raise UpdateDeliveryError("selected Greia release is invalid")
        with self._inbox_lock:
            status = self._request_status(reconcile=True)
            readiness = _readiness_record(status)
            self.store.update_readiness(readiness)
            if not readiness["activation_available"]:
                raise UpdateDeliveryError(
                    _public_activation_reason(readiness.get("activation_reason"))
                    or "this Greia device is not ready for an A/B update"
                )
            identity = DeviceUpdateIdentity.from_status(status)
            release = self.catalog.resolve(self.channel, identity, release_id)
            expected = job.get("expected")
            if not isinstance(expected, dict) or not _same_release_summary(expected, release):
                raise UpdateDeliveryError("selected Greia release changed; check again")

            journal = _journal_summary(status)
            if _journal_matches(journal, release_id, {"update_staged"}):
                self._discard_staged_candidate(status, release, identity)
                self._mark_ready(job, status)
                return
            candidate = _candidate_summary(status)
            candidate_matches_status = (
                candidate.get("present") is True
                and candidate.get("release_id") == release_id
                and candidate.get("bundle_sha256") == release.sha256
            )
            # This also lets an existing manual upload enter the exact same
            # verify/stage engine, but only when root status and the inbox file
            # both identify the catalog-selected bytes.
            if candidate_matches_status and self.receiver.candidate_matches(release, identity):
                self._set_job(job, "verifying")
            else:
                self.receiver.receive(
                    release,
                    identity,
                    lambda state, **fields: self._set_job(job, state, **fields),
                )

            self._set_job(job, "verifying")
            verified = self._privileged_request("VERIFY_CURRENT_CANDIDATE")
            if verified.get("status") != "VERIFIED":
                raise UpdateDeliveryError("Greia updater did not verify the current update candidate")
            self._set_job(job, "staging")
            try:
                staged = self._privileged_request("STAGE_CURRENT_CANDIDATE")
            except UpdateDeliveryError as exc:
                # The service may have completed the inactive-slot write before
                # its reply was lost. Resolve that outcome once before any retry.
                try:
                    status = self._request_status(reconcile=True)
                except UpdateDeliveryError as status_exc:
                    raise UpdateDeliveryError(
                        "Greia stage result is unknown; retry only after status reconciliation"
                    ) from status_exc
                if _journal_matches(_journal_summary(status), release_id, {"update_staged"}):
                    self.store.update_readiness(_readiness_record(status))
                    self._discard_staged_candidate(status, release, identity)
                    self._mark_ready(job, status)
                    return
                raise UpdateDeliveryError("Greia updater did not complete inactive-slot staging") from exc
            if staged.get("status") != "STAGED":
                raise UpdateDeliveryError("Greia updater did not stage the current update candidate")
            # The stage operation may take minutes. Only now make another
            # privileged request, after the root service's serialized request
            # has completed, so readers never contend with STAGE.
            status = self._request_status(reconcile=False)
            self.store.update_readiness(_readiness_record(status))
            if not _journal_matches(_journal_summary(status), release_id, {"update_staged"}):
                raise UpdateDeliveryError("Greia did not confirm the staged update journal")
            self._discard_staged_candidate(status, release, identity)
            self._mark_ready(job, status)

    def _run_restart(self, job: dict[str, object], recovered_state: str | None) -> None:
        if recovered_state == "restart_pending":
            self._reconcile_restart_outcome(job)
            return

        current = self._job()
        if not isinstance(current, dict) or current.get("state") != "restart_pending":
            return
        self._set_job(current, "restart_pending", restart_dispatch_pending=False)
        try:
            response = self._privileged_request("REQUEST_RESTART", allow_refused=True)
        except Exception:
            # The service may have recorded the restart fence before its reply
            # was lost. Reconcile STATUS in this already-owned worker; retry is
            # surfaced only as an explicit Parent action through the root's
            # idempotent REQUEST_RESTART operation.
            self._reconcile_restart_outcome(current)
            return
        if response.get("status") == "RESTART_ACCEPTED":
            current["restart_request_id"] = _bounded_text(response.get("request_id"), 64)
            current["restart_state"] = _restart_state(response.get("state"))
            if not current["restart_request_id"]:
                self._reconcile_restart_outcome(current)
            else:
                self._set_job(current, "restart_pending")
        elif response.get("status") == "REFUSED":
            current["restart_request_id"] = _bounded_text(response.get("request_id"), 64)
            current["restart_state"] = _restart_state(response.get("state"))
            self._make_restart_retry_available(
                current,
                code="restart_refused",
                message=_bounded_text(response.get("reason"), 256),
            )
        else:
            self._reconcile_restart_outcome(current)

    def _reconcile_restart_outcome(self, job: dict[str, object]) -> None:
        """Bound restart-result reconciliation without blocking Parent reads.

        This runs only in the existing delivery worker. It never calls
        REQUEST_RESTART itself: when root proves that a one-shot handoff is
        still pending, it exposes the staged job for a human-triggered retry
        through root's idempotent restart authority.
        """

        job_id = job.get("job_id")
        release_id = _bounded_text(job.get("release_id"), 96)
        last_error: UpdateDeliveryError | None = None
        for attempt in range(RESTART_STATUS_ATTEMPTS):
            try:
                status = self._request_status(reconcile=False)
            except UpdateDeliveryError as exc:
                last_error = exc
                if attempt + 1 < RESTART_STATUS_ATTEMPTS:
                    time.sleep(RESTART_STATUS_RETRY_SECONDS * (attempt + 1))
                continue

            try:
                self.store.update_readiness(_readiness_record(status))
            except UpdateDeliveryError:
                # Journal/restart-state reconciliation below remains useful
                # even if installed identity readiness has become unavailable.
                pass
            current = self._job()
            if not isinstance(current, dict) or current.get("job_id") != job_id:
                return
            root_request_id = _bounded_text(status.get("restart_request_id"), 64)
            if root_request_id:
                current["restart_request_id"] = root_request_id
            root_restart_state = _restart_state(status.get("restart_state"))
            if root_restart_state is not None:
                current["restart_state"] = root_restart_state
            journal = _journal_summary(status)
            journal_state = _bounded_text(journal.get("state"), 64).casefold()
            if _journal_matches(journal, release_id, {"accepted"}):
                self._set_job(current, "updated")
                return
            if _journal_matches(journal, release_id, {"rolled_back", "failed"}):
                self._set_job(current, "rolled_back")
                return

            restart_pending = status.get("restart_pending")
            safe_retry = (
                restart_pending is False
                and journal_state in {"update_staged", "one_shot_armed"}
            ) or (
                restart_pending is True
                and root_restart_state == "handoff_pending"
                and journal_state == "one_shot_armed"
            )
            if safe_retry:
                self._make_restart_retry_available(
                    current,
                    code="restart_retry_available",
                    message="Greia still needs a restart. Choose Restart again to retry safely.",
                )
                return

            if restart_pending is True and root_restart_state == "systemd_accepted":
                self._set_job(
                    current,
                    "restart_pending",
                    error_code="restart_accepted_pending",
                    error_message="Greia accepted the restart request and is waiting to reboot.",
                )
                return

            if attempt + 1 < RESTART_STATUS_ATTEMPTS:
                time.sleep(RESTART_STATUS_RETRY_SECONDS * (attempt + 1))

        current = self._job()
        if not isinstance(current, dict) or current.get("job_id") != job_id:
            return
        if last_error is not None:
            # No authoritative reply arrived, so do not invent a root result.
            # A human may retry the same selector-free/idempotent root action.
            self._make_restart_retry_available(
                current,
                code="restart_result_unknown",
                message="Greia could not confirm the restart. Choose Restart again to retry safely.",
            )
        else:
            self._set_job(
                current,
                "restart_pending",
                error_code="restart_result_unknown",
                error_message="Greia could not confirm whether the restart handoff completed.",
            )

    def _make_restart_retry_available(
        self,
        job: dict[str, object],
        *,
        code: str,
        message: str,
    ) -> None:
        job["operation"] = "prepare"
        self._set_job(
            job,
            "ready_to_restart",
            error_code=code,
            error_message=message,
        )

    def _request_status(self, *, reconcile: bool) -> dict[str, object]:
        status = self._privileged_request("STATUS")
        if status.get("status") != "OK":
            raise UpdateDeliveryError("Greia system-update service did not return authoritative status")
        if reconcile:
            journal = _journal_summary(status)
            if journal.get("state") in {"update_staged", "one_shot_armed", "candidate_booting"}:
                self._privileged_request("RECONCILE")
                status = self._privileged_request("STATUS")
                if status.get("status") != "OK":
                    raise UpdateDeliveryError("Greia system-update status could not be reconciled")
        return status

    def _discard_staged_candidate(
        self,
        status: Mapping[str, object],
        release: UpdateRelease,
        identity: DeviceUpdateIdentity,
    ) -> bool:
        """Clean only a root-identified candidate belonging to this staged release."""

        if not _journal_matches(_journal_summary(status), release.release_id, {"update_staged"}):
            return False
        candidate = _candidate_summary(status)
        if (
            candidate.get("present") is not True
            or candidate.get("release_id") != release.release_id
        ):
            return False
        recorded_digest = candidate.get("bundle_sha256")
        if not isinstance(recorded_digest, str) or recorded_digest != release.sha256:
            return False
        return self.receiver.discard_staged_candidate(release, identity, recorded_digest)

    def _privileged_request(
        self,
        operation: str,
        *,
        allow_refused: bool = False,
    ) -> dict[str, object]:
        try:
            response = self.privileged.request(operation)
        except Exception as exc:
            raise UpdateDeliveryError("Greia system-update service is unavailable") from exc
        if not isinstance(response, dict):
            raise UpdateDeliveryError("Greia system-update service response is invalid")
        if response.get("status") == "REFUSED" and not allow_refused:
            raise UpdateDeliveryError(_bounded_text(response.get("reason"), 256) or "Greia refused the update operation")
        return response

    def _mark_ready(self, job: dict[str, object], status: Mapping[str, object]) -> None:
        journal = _journal_summary(status)
        job["journal_state"] = journal.get("state")
        job["candidate_slot"] = journal.get("trial_slot")
        self._set_job(job, "ready_to_restart")

    def _set_job(
        self,
        job: dict[str, object],
        state: str,
        *,
        error_code: str | None = None,
        error_message: str | None = None,
        **fields: object,
    ) -> None:
        current = self._job()
        if not isinstance(current, dict) or current.get("job_id") != job.get("job_id"):
            return
        updated = dict(current)
        updated.update(job)
        updated.update(fields)
        updated.update(
            {
                "state": state,
                "updated_at": _timestamp(),
                "error_code": error_code,
                "error_message": _bounded_text(error_message, 256) if error_message else None,
            }
        )
        self.store.update_job(updated)
        job.clear()
        job.update(updated)

    def _fail(self, job_id: str, code: str, message: str) -> None:
        job = self._job()
        if not isinstance(job, dict) or job.get("job_id") != job_id:
            return
        if job.get("state") == "restart_pending":
            # Unknown restart outcomes need explicit journal reconciliation.
            return
        self._set_job(job, "failed", error_code=code, error_message=message)

    def _job(self) -> dict[str, object] | None:
        job = self.store.snapshot().get("job")
        return dict(job) if isinstance(job, dict) else None


def _default_privileged_client() -> PrivilegedUpdateClient:
    try:
        from greia_platform.update_client import UpdatePrivilegedClient

        return UpdatePrivilegedClient()
    except (ImportError, OSError, TypeError):
        return _UnavailableUpdateClient()


def _new_job(
    operation: str,
    release_id: str | None,
    version: str | None,
    expected: Mapping[str, object] | None,
) -> dict[str, object]:
    now = _timestamp()
    return {
        "job_id": uuid4().hex,
        "operation": operation,
        "state": "checking" if operation == "check" else "queued",
        "release_id": release_id,
        "version": version,
        "expected": dict(expected) if expected is not None else None,
        "created_at": now,
        "updated_at": now,
        "downloaded_bytes": 0,
        "total_bytes": 0,
        "error_code": None,
        "error_message": None,
    }


def _readiness_record(status: Mapping[str, object]) -> dict[str, object]:
    if status.get("status") != "OK":
        raise UpdateDeliveryError("Greia system-update status is not authoritative")
    try:
        identity = DeviceUpdateIdentity.from_status(status)
    except UpdateCatalogError as exc:
        raise UpdateDeliveryError(str(exc)) from exc
    backend = status.get("backend")
    layout = status.get("layout")
    persist = status.get("persist")
    activation = status.get("activation_available") is True
    reason = _bounded_text(status.get("activation_reason"), 256)
    if not isinstance(backend, Mapping) or backend.get("available") is not True:
        activation = False
        reason = reason or _bounded_text(backend.get("reason") if isinstance(backend, Mapping) else None, 256)
    if not isinstance(layout, Mapping) or layout.get("single_root") is not False:
        activation = False
        reason = reason or "Greia requires an installed A/B layout"
    slots = layout.get("slots") if isinstance(layout, Mapping) else None
    if not isinstance(slots, list) or not {"A", "B"}.issubset(set(slots)):
        activation = False
        reason = reason or "Greia A/B layout is incomplete"
    if not isinstance(persist, Mapping) or persist.get("available") is not True:
        activation = False
        reason = reason or "Greia PERSIST state is unavailable"
    else:
        schema = persist.get("schema")
        read_min = persist.get("readable_min")
        read_max = persist.get("readable_max")
        schema_values_valid = all(
            isinstance(value, int) and not isinstance(value, bool)
            for value in (schema, read_min, read_max)
        )
        if not schema_values_valid or not (read_min <= schema <= read_max):  # type: ignore[operator]
            activation = False
            reason = reason or "Greia PERSIST schema is not readable"
    free_bytes = persist.get("free_bytes") if isinstance(persist, Mapping) else None
    if isinstance(free_bytes, bool) or not isinstance(free_bytes, int) or free_bytes < MIN_INBOX_FREE_BYTES:
        activation = False
        reason = reason or "Greia PERSIST has insufficient free space"
    return {
        "observed_at": _timestamp(),
        "activation_available": activation,
        "activation_reason": reason or ("A/B update is ready" if activation else "Greia update readiness is unavailable"),
        "installed_version": identity.version,
        "identity": {
            "release_id": identity.release_id,
            "profile": identity.profile,
            "platform_family": identity.platform_family,
            "architecture": identity.architecture,
            "board": identity.board,
        },
        "backend": dict(backend) if isinstance(backend, Mapping) else {},
        "layout": dict(layout) if isinstance(layout, Mapping) else {},
        "persist": dict(persist) if isinstance(persist, Mapping) else {},
        "journal": dict(status.get("journal")) if isinstance(status.get("journal"), Mapping) else {},
        "candidate": dict(status.get("candidate")) if isinstance(status.get("candidate"), Mapping) else {},
    }


def _same_release_summary(expected: Mapping[str, object], release: UpdateRelease) -> bool:
    return (
        expected.get("release_id") == release.release_id
        and expected.get("version") == release.version
        and expected.get("profile") == release.target_profile
        and expected.get("platform_family") == release.platform_family
        and expected.get("architecture") == release.architecture
        and expected.get("board") == release.board
        and expected.get("size") == release.size
        and expected.get("sha256") == release.sha256
    )


def _candidate_summary(status: Mapping[str, object]) -> Mapping[str, object]:
    value = status.get("candidate")
    return value if isinstance(value, Mapping) else {}


def _journal_summary(status: Mapping[str, object]) -> Mapping[str, object]:
    value = status.get("journal")
    return value if isinstance(value, Mapping) else {}


def _journal_matches(journal: Mapping[str, object], release_id: str, states: set[str]) -> bool:
    return (
        _bounded_text(journal.get("release_id"), 96) == release_id
        and _bounded_text(journal.get("state"), 64).casefold() in states
    )


def _restart_state(value: object) -> str | None:
    """Accept only the root-owned restart fence states exposed by STATUS."""

    if isinstance(value, str) and value in {"handoff_pending", "systemd_accepted"}:
        return value
    return None


def _readiness_ready(value: object, *, now: float) -> bool:
    if not isinstance(value, Mapping) or value.get("activation_available") is not True:
        return False
    age = _age_seconds(value.get("observed_at"), now)
    return age is not None and age <= READINESS_MAX_AGE_SECONDS


def _job_blocks_new_operation(value: object) -> bool:
    return isinstance(value, Mapping) and value.get("state") in _ACTIVE_STATES | _READY_STATES


def _timestamp() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _age_seconds(value: object, now: float) -> float | None:
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    return max(0.0, now - parsed.timestamp())


def _bounded_text(value: object, limit: int) -> str:
    return value[:limit] if isinstance(value, str) else ""


def _error_code(exc: UpdateDeliveryError) -> str:
    message = str(exc).casefold()
    if "catalog" in message or "release" in message:
        return "catalog_or_release_rejected"
    if "space" in message:
        return "insufficient_space"
    if "checksum" in message:
        return "checksum_mismatch"
    if "service" in message or "updater" in message:
        return "updater_unavailable"
    return "update_failed"


def _public_activation_reason(value: object) -> str:
    """Keep local paths and service diagnostics out of the Parent wire API."""

    reason = _bounded_text(value, 256).strip()
    folded = reason.casefold()
    if "single" in folded or "layout" in folded or "slot" in folded:
        return "This Greia installation is not ready for an A/B update."
    if "persist" in folded or "schema" in folded:
        return "Greia's saved system state is not ready for this update."
    if "space" in folded or "capacity" in folded:
        return "Greia needs more free space before it can prepare this update."
    if not reason or "/" in reason or "\\" in reason:
        return "Greia update readiness is unavailable."
    return reason
