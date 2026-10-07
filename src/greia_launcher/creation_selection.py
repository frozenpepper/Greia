"""Trusted non-blocking selection transaction for an Activity session.

Activity clients can ask for compatible media and poll a status, but cannot
browse, choose an artifact, or mint a read grant. Only a trusted Shell picker
can complete the request. The pending request belongs to one session and is
bounded to prevent unattended clients from filling platform memory.
"""
from __future__ import annotations

import secrets
import threading
import time
from dataclasses import dataclass
from enum import StrEnum
from typing import Callable

from greia_platform.creation_access import CreationAccessDenied, CreationSessionAccess


class SelectionState(StrEnum):
    PENDING = "pending"
    READY = "ready"
    CANCELLED = "cancelled"


@dataclass(frozen=True, slots=True)
class SelectionRequest:
    request_id: str
    session_id: str
    media_types: tuple[str, ...]
    roles: tuple[str, ...]
    created_at: float


@dataclass(frozen=True, slots=True)
class SelectionStatus:
    state: SelectionState
    selection_token: str | None = None


class CreationSelectionCoordinator:
    """One outstanding request for the broker's one authenticated Activity."""

    REQUEST_SECONDS = 180.0
    MAX_ROLES = 8

    def __init__(
        self,
        access: CreationSessionAccess,
        session_id: str,
        *,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        if not session_id:
            raise ValueError("selection session identity required")
        self._access = access
        self._session_id = session_id
        self._clock = clock
        self._lock = threading.Lock()
        self._request: SelectionRequest | None = None
        self._result = SelectionStatus(SelectionState.PENDING)
        self._closed = False

    @staticmethod
    def _parse_media_types(raw: object, allowed: frozenset[str]) -> tuple[str, ...]:
        if not isinstance(raw, (list, tuple)) or not 1 <= len(raw) <= 3:
            raise CreationAccessDenied("a bounded, non-empty media set is required")
        if any(not isinstance(item, str) for item in raw):
            raise CreationAccessDenied("media types must be text")
        values = tuple(raw)
        if len(set(values)) != len(values) or not set(values).issubset(allowed):
            raise CreationAccessDenied("requested media is outside the Activity declaration")
        return values

    @classmethod
    def _parse_roles(cls, raw: object) -> tuple[str, ...]:
        if raw is None:
            return ()
        if not isinstance(raw, (list, tuple)) or len(raw) > cls.MAX_ROLES:
            raise CreationAccessDenied("invalid semantic role filter")
        if any(
            not isinstance(role, str)
            or not 1 <= len(role) <= 48
            or not all(c.isascii() and (c.isalnum() or c in "._-") for c in role)
            for role in raw
        ):
            raise CreationAccessDenied("invalid semantic role")
        roles = tuple(raw)
        if len(set(roles)) != len(roles):
            raise CreationAccessDenied("duplicate semantic role")
        return roles

    def _require_open(self) -> None:
        if self._closed:
            raise CreationAccessDenied("selection session has ended")

    def _expire(self) -> None:
        if (
            self._request is not None
            and self._result.state is SelectionState.PENDING
            and self._clock() - self._request.created_at >= self.REQUEST_SECONDS
        ):
            self._result = SelectionStatus(SelectionState.CANCELLED)

    def request(self, *, media_types: object, roles: object = None) -> SelectionRequest:
        with self._lock:
            self._require_open()
            allowed = self._access.consumable_media_types
            kinds = self._parse_media_types(media_types, allowed)
            selected_roles = self._parse_roles(roles)
            self._expire()
            if self._request is not None:
                raise CreationAccessDenied("previous selection has not been collected")
            self._request = SelectionRequest(
                request_id=secrets.token_urlsafe(24),
                session_id=self._session_id,
                media_types=kinds,
                roles=selected_roles,
                created_at=self._clock(),
            )
            self._result = SelectionStatus(SelectionState.PENDING)
            return self._request

    def poll(self, request_id: str) -> SelectionStatus:
        with self._lock:
            self._require_open()
            self._expire()
            if self._request is None or self._request.request_id != request_id:
                raise CreationAccessDenied("no matching selection request")
            result = self._result
            if result.state is not SelectionState.PENDING:
                self._request = None
                self._result = SelectionStatus(SelectionState.PENDING)
            return result

    def cancel(self, request_id: str) -> bool:
        with self._lock:
            self._require_open()
            if self._request is None or self._request.request_id != request_id:
                raise CreationAccessDenied("no matching selection request")
            if self._result.state is not SelectionState.PENDING:
                return False
            self._result = SelectionStatus(SelectionState.CANCELLED)
            return True

    def trusted_pending(self) -> SelectionRequest | None:
        """Shell-only: never serialize this via a child-facing broker operation."""
        with self._lock:
            if self._closed:
                return None
            self._expire()
            if self._result.state is SelectionState.PENDING:
                return self._request
            return None

    def trusted_complete(self, request_id: str, creation_id: str) -> None:
        """Shell-only: the child has confirmed a specific visible artifact."""
        with self._lock:
            self._require_open()
            self._expire()
            req = self._request
            if req is None or req.request_id != request_id:
                raise CreationAccessDenied("stale selection confirmation")
            if self._result.state is not SelectionState.PENDING:
                raise CreationAccessDenied("selection is no longer pending")
            token = self._access.grant_child_selection(
                creation_id,
                only_media_types=frozenset(req.media_types),
                only_roles=frozenset(req.roles) if req.roles else None,
            )
            self._result = SelectionStatus(SelectionState.READY, token)

    def trusted_cancel(self, request_id: str) -> None:
        """Shell-only: back/home/timeout of the authoritative child picker."""
        self.cancel(request_id)

    def close(self) -> None:
        with self._lock:
            self._closed = True
            self._request = None
            self._result = SelectionStatus(SelectionState.CANCELLED)
