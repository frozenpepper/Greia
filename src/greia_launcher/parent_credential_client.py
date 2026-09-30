"""Parent-password verification for the on-device Parent panel.

The Parent password is owned by the Parent service identity and stored as a
0600 PBKDF2 digest that the child identity cannot read. The panel used to verify
the typed password itself against that file, which could never succeed: as
``greiakid`` the read fails, ``MainCredentialStore._read`` raises, and the
panel's blanket ``except Exception`` reported the failure to the parent as
"incorrect password" for every possible input.

Verification therefore happens where the credential lives. The panel asks the
Parent service over its existing, already rate-limited pairing endpoint, which
verifies the digest as ``greiapel`` and issues a device token. The child never
reads the digest, and no second password store or socket is introduced.

The distinction that matters is between *rejected* and *cannot check*. A wrong
password returns ``False``. An unreachable service, a timeout, a malformed
reply or any unexpected status raises :class:`ParentCredentialUnavailable`, so
the panel can say the check could not be performed instead of accusing the
parent of typing the wrong thing. The caller must fail closed either way.

Nothing here logs, echoes or retains the candidate password, and no error
message ever embeds it.
"""

from __future__ import annotations

import json
import urllib.error
from dataclasses import dataclass
import urllib.request
from typing import Any, Protocol, runtime_checkable

#: Loopback only. The Parent API binds 0.0.0.0 for browser pairing, but the
#: on-device panel has no reason to leave the machine.
DEFAULT_PARENT_API_BASE_URL = "http://127.0.0.1:8766"

#: Bounded so a wedged service cannot freeze the child Shell's frame loop. The
#: endpoint is a local PBKDF2 verify, which is deliberately slow by design.
DEFAULT_TIMEOUT_SECONDS = 10.0

#: The pairing endpoint the Parent API already exposes and rate limits.
API_BASE = "/api/v1"
_BOOTSTRAP_PATH = f"{API_BASE}/pairing/bootstrap"

#: Statuses that are a definite "no" from the password bootstrap: the password
#: was rejected, the attempt budget is spent, or the request was malformed. Every
#: other non-success status is an unknown outcome, not a rejected password.
_DEFINITE_REJECTIONS = frozenset({400, 403, 429})

#: Response bodies are small; refuse to buffer an unbounded one.
_MAX_RESPONSE_BYTES = 64 * 1024


class ParentCredentialUnavailable(RuntimeError):
    """The Parent service could not be asked, so the password is unknown.

    Distinct from a rejected password. Callers must still refuse access.
    """


@runtime_checkable
class ParentPasswordVerifier(Protocol):
    """Narrow dependency the panel needs: is this candidate password correct?

    Exactly one member, deliberately. It is the whole surface the panel needs to
    unlock, and keeping it minimal is what lets the digest-backed store satisfy
    it in tests while production uses the Parent service. A wider protocol here
    silently stopped accepting the store when a method was once written into this
    body by mistake.
    """

    def verify(self, password: str) -> bool:  # pragma: no cover - protocol
        ...


@dataclass(frozen=True, slots=True)
class ChildAccount:
    """A child profile as the panel needs to show it."""

    profile_id: str
    display_name: str
    avatar_id: str
    approximate_age: int | None


@dataclass(frozen=True, slots=True)
class ParentSession:
    """An authenticated Parent API session.

    Holding the issued device token is what lets the panel manage child accounts
    and change the Parent password *through the service that owns them*, instead
    of writing those state files as the child identity. The token is the
    credential; it is never logged and never leaves this process.
    """

    token: str
    device_id: str


@dataclass(frozen=True, slots=True)
class ParentRequestFailed(RuntimeError):
    """The Parent service refused a well-formed request.

    ``reason`` is the service's own bounded message, safe to show a parent.
    """

    reason: str


class ParentCredentialClient:
    """Verify a Parent password through the Parent service that owns it."""

    def __init__(
        self,
        *,
        base_url: str = DEFAULT_PARENT_API_BASE_URL,
        timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
        device_name: str = "greia-on-device",
    ) -> None:
        if timeout_seconds <= 0.0:
            raise ValueError("timeout_seconds must be positive")
        self._base = base_url.rstrip("/")
        self._endpoint = self._base + _BOOTSTRAP_PATH
        self._timeout = timeout_seconds
        self._device_name = device_name

    def authenticate(self, password: str) -> ParentSession:
        """Verify the password and keep the issued device token.

        The device token is the Parent API's own authorisation mechanism, already
        rate limited and already scoped per device. Using it means the panel
        never needs read access to the Parent's credential file, which is the
        defect that made every password look wrong in the first place.
        """

        status, decoded = self._request(
            "POST",
            _BOOTSTRAP_PATH,
            {"password": password, "device_name": self._device_name},
            authenticated=False,
        )
        if status != 201:
            raise ParentCredentialUnavailable(
                f"parent service returned unexpected status {status}"
            )
        return _session_from(decoded)

    def verify(self, password: str) -> bool:
        """Return whether the Parent service accepted ``password``.

        Raises :class:`ParentCredentialUnavailable` when no verdict could be
        obtained. The password is only ever placed in the request body.
        """

        status, decoded = self._request(
            "POST",
            _BOOTSTRAP_PATH,
            {"password": password, "device_name": self._device_name},
            authenticated=False,
        )
        if status in _DEFINITE_REJECTIONS:
            # The service answered, and the answer was "no": a rejected password,
            # a rate-limited attempt budget, or a malformed request. Only these
            # are allowed to read as "wrong password" to the parent.
            return False
        if status != 201:
            # Anything else is not a verdict. Reporting it as a wrong password is
            # the lie this whole client exists to avoid.
            raise ParentCredentialUnavailable(
                f"parent service returned unexpected status {status}"
            )
        _session_from(decoded)
        return True

    def list_child_accounts(self, session: ParentSession) -> list[ChildAccount]:
        """Return the child profiles the Parent service reports."""

        _status, decoded = self._request(
            "GET", f"{API_BASE}/profiles", None, authenticated=True, session=session
        )
        # GET /api/v1/profiles answers with a bare JSON array, verified against
        # the running service. An assumed {"profiles": [...]} envelope is what
        # this replaced after the first live call returned the array directly.
        entries = decoded
        if isinstance(decoded, dict):
            entries = decoded.get("profiles")
        if not isinstance(entries, list):
            raise ParentCredentialUnavailable("profiles response was not a list")
        accounts: list[ChildAccount] = []
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            profile_id = entry.get("profile_id")
            if not isinstance(profile_id, str):
                continue
            age = entry.get("approximate_age")
            accounts.append(
                ChildAccount(
                    profile_id=profile_id,
                    display_name=str(entry.get("display_name", "")),
                    avatar_id=str(entry.get("avatar_id", "")),
                    approximate_age=age if isinstance(age, int) else None,
                )
            )
        return accounts

    def add_child_account(
        self,
        session: ParentSession,
        *,
        display_name: str,
        avatar_id: str,
        approximate_age: int | None = None,
    ) -> ChildAccount:
        """Create a child profile through the service that owns the store."""

        body: dict[str, Any] = {"display_name": display_name, "avatar_id": avatar_id}
        if approximate_age is not None:
            body["approximate_age"] = approximate_age
        _status, decoded = self._request(
            "POST", f"{API_BASE}/profiles", body, authenticated=True, session=session
        )
        if not isinstance(decoded, dict) or not isinstance(
            decoded.get("profile_id"), str
        ):
            raise ParentCredentialUnavailable("created profile had no id")
        return ChildAccount(
            profile_id=str(decoded["profile_id"]),
            display_name=str(decoded.get("display_name", display_name)),
            avatar_id=str(decoded.get("avatar_id", avatar_id)),
            approximate_age=decoded.get("approximate_age")
            if isinstance(decoded.get("approximate_age"), int)
            else None,
        )

    def rename_child_account(
        self, session: ParentSession, profile_id: str, display_name: str
    ) -> ChildAccount:
        """Rename a child profile through the service that owns the store.

        Validation, including the policy's name-length bound, stays in the
        service. The panel deliberately cannot enforce it alone: the limit lives
        in the same profile policy the service validates against.
        """

        _status, decoded = self._request(
            "PUT",
            f"{API_BASE}/profiles/{profile_id}",
            {"display_name": display_name},
            authenticated=True,
            session=session,
        )
        if not isinstance(decoded, dict) or not isinstance(
            decoded.get("profile_id"), str
        ):
            raise ParentCredentialUnavailable("renamed profile had no id")
        return ChildAccount(
            profile_id=str(decoded["profile_id"]),
            display_name=str(decoded.get("display_name", display_name)),
            avatar_id=str(decoded.get("avatar_id", "")),
            approximate_age=decoded.get("approximate_age")
            if isinstance(decoded.get("approximate_age"), int)
            else None,
        )

    def remove_child_account(self, session: ParentSession, profile_id: str) -> None:
        """Delete a child profile; the service enforces its own guards.

        It refuses to delete the active child and the final remaining profile,
        and it revalidates that the profile's data path is a managed directory
        rather than a symlink. That is why this goes through the service instead
        of the panel touching profile storage as the child identity.
        """

        self._request(
            "DELETE",
            f"{API_BASE}/profiles/{profile_id}",
            None,
            authenticated=True,
            session=session,
        )

    def change_parent_password(
        self, session: ParentSession, current_password: str, new_password: str
    ) -> None:
        """Rotate the Parent password through the service that owns it."""

        self._request(
            "POST",
            f"{API_BASE}/parent-password",
            {"current_password": current_password, "new_password": new_password},
            authenticated=True,
            session=session,
        )

    def _request(
        self,
        method: str,
        path: str,
        body: dict[str, Any] | None,
        *,
        authenticated: bool,
        session: ParentSession | None = None,
    ) -> tuple[int, Any]:
        """Perform one bounded Parent API call.

        Returns ``(status, decoded)`` for a definite answer. Raises
        :class:`ParentCredentialUnavailable` when no verdict could be obtained,
        which is the distinction the panel needs in order to stop telling a
        parent their password is wrong when the service is merely unreachable.
        """

        if authenticated and session is None:
            raise ValueError("an authenticated request needs a session")
        url = f"{self._base}{path}"
        data = json.dumps(body).encode("utf-8") if body is not None else None
        headers = {"Accept": "application/json"}
        if data is not None:
            headers["Content-Type"] = "application/json"
        if session is not None:
            headers["Authorization"] = f"Bearer {session.token}"
        request = urllib.request.Request(  # noqa: S310 - fixed loopback http URL
            url, data=data, method=method, headers=headers
        )
        try:
            with urllib.request.urlopen(request, timeout=self._timeout) as reply:  # noqa: S310
                status = reply.status
                payload = reply.read(_MAX_RESPONSE_BYTES)
        except urllib.error.HTTPError as error:
            detail = _bounded_reason(error)
            if error.code in (400, 403, 404, 409, 429):
                if method == "POST" and path == _BOOTSTRAP_PATH:
                    # Password bootstrap: a definite rejection, not an outage.
                    return error.code, detail
                raise ParentRequestFailed(detail) from None
            raise ParentCredentialUnavailable(
                f"parent service returned status {error.code}"
            ) from None
        except urllib.error.URLError:
            raise ParentCredentialUnavailable("parent service is unreachable") from None
        except (TimeoutError, OSError):
            raise ParentCredentialUnavailable("parent service did not respond") from None
        if not payload:
            return status, {}
        try:
            return status, json.loads(payload.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            raise ParentCredentialUnavailable(
                "parent service returned a malformed response"
            ) from None


__all__ = [
    "API_BASE",
    "DEFAULT_PARENT_API_BASE_URL",
    "DEFAULT_TIMEOUT_SECONDS",
    "ChildAccount",
    "ParentCredentialClient",
    "ParentCredentialUnavailable",
    "ParentPasswordVerifier",
    "ParentRequestFailed",
    "ParentSession",
]


def _session_from(decoded: Any) -> ParentSession:
    """Build a session from a bootstrap reply, refusing anything malformed."""

    if not isinstance(decoded, dict):
        raise ParentCredentialUnavailable("parent service reply was not an object")
    token = decoded.get("credential")
    device = decoded.get("device")
    device_id = device.get("device_id") if isinstance(device, dict) else None
    if not isinstance(token, str) or not token:
        raise ParentCredentialUnavailable("parent service issued no credential")
    return ParentSession(token=token, device_id=str(device_id or ""))


def _bounded_reason(error: urllib.error.HTTPError) -> str:
    """A short, safe explanation from the service, for display to a parent."""

    try:
        raw = error.read(_MAX_RESPONSE_BYTES).decode("utf-8", "replace")
        payload = json.loads(raw)
    except Exception:  # noqa: BLE001 - any failure falls back to the status line
        return f"request refused ({error.code})"
    if isinstance(payload, dict):
        # The API nests it: {"error": {"code": ..., "message": ...}}. A flat
        # lookup silently produced the generic fallback and hid real reasons
        # such as "unknown profile avatar: fox" from the parent.
        error_field = payload.get("error")
        if isinstance(error_field, dict):
            message = error_field.get("message")
            if isinstance(message, str) and message:
                return message[:200]
            code = error_field.get("code")
            if isinstance(code, str) and code:
                return code[:200]
        if isinstance(error_field, str) and error_field:
            return error_field[:200]
        for key in ("message", "detail"):
            value = payload.get(key)
            if isinstance(value, str) and value:
                return value[:200]
    return f"request refused ({error.code})"
