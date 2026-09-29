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
import urllib.request
from typing import Any, Protocol, runtime_checkable

#: Loopback only. The Parent API binds 0.0.0.0 for browser pairing, but the
#: on-device panel has no reason to leave the machine.
DEFAULT_PARENT_API_BASE_URL = "http://127.0.0.1:8766"

#: Bounded so a wedged service cannot freeze the child Shell's frame loop. The
#: endpoint is a local PBKDF2 verify, which is deliberately slow by design.
DEFAULT_TIMEOUT_SECONDS = 10.0

#: The pairing endpoint the Parent API already exposes and rate limits.
_BOOTSTRAP_PATH = "/api/v1/pairing/bootstrap"

#: Response bodies are small; refuse to buffer an unbounded one.
_MAX_RESPONSE_BYTES = 64 * 1024


class ParentCredentialUnavailable(RuntimeError):
    """The Parent service could not be asked, so the password is unknown.

    Distinct from a rejected password. Callers must still refuse access.
    """


@runtime_checkable
class ParentPasswordVerifier(Protocol):
    """Narrow dependency the panel needs: is this candidate password correct?"""

    def verify(self, password: str) -> bool:  # pragma: no cover - protocol
        ...


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
        self._endpoint = base_url.rstrip("/") + _BOOTSTRAP_PATH
        self._timeout = timeout_seconds
        self._device_name = device_name

    def verify(self, password: str) -> bool:
        """Return whether the Parent service accepted ``password``.

        Raises :class:`ParentCredentialUnavailable` when no verdict could be
        obtained. The password is only ever placed in the request body.
        """

        body = json.dumps(
            {"password": password, "device_name": self._device_name}
        ).encode("utf-8")
        request = urllib.request.Request(  # noqa: S310 - fixed loopback http URL
            self._endpoint,
            data=body,
            method="POST",
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=self._timeout) as reply:  # noqa: S310
                status = reply.status
                payload = reply.read(_MAX_RESPONSE_BYTES)
        except urllib.error.HTTPError as error:
            # A definite answer from the service: the password was rejected
            # (403) or the attempt budget is spent (429). Both mean "not
            # unlocked", and neither is a reason to claim the check failed.
            if error.code in (403, 429, 400):
                return False
            raise ParentCredentialUnavailable(
                f"parent service returned status {error.code}"
            ) from None
        except urllib.error.URLError:
            raise ParentCredentialUnavailable("parent service is unreachable") from None
        except (TimeoutError, OSError):
            raise ParentCredentialUnavailable("parent service did not respond") from None

        if status != 201:
            raise ParentCredentialUnavailable(
                f"parent service returned unexpected status {status}"
            )
        try:
            decoded: Any = json.loads(payload.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            raise ParentCredentialUnavailable(
                "parent service returned a malformed response"
            ) from None
        if not isinstance(decoded, dict) or not isinstance(
            decoded.get("credential"), str
        ):
            raise ParentCredentialUnavailable(
                "parent service response carried no device credential"
            )
        return True


__all__ = [
    "DEFAULT_PARENT_API_BASE_URL",
    "DEFAULT_TIMEOUT_SECONDS",
    "ParentCredentialClient",
    "ParentCredentialUnavailable",
    "ParentPasswordVerifier",
]
