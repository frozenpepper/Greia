"""Parent-password verification now happens in the Parent service, not the Shell.

The panel used to verify the typed password itself against
``/var/lib/greia-os/main-credential.json``. That file is 0600 and owned by the
Parent service identity, so as the child identity the read fails, the store
raises, and the panel's blanket ``except Exception`` reported "incorrect
password" for every input. The parent was told their password was wrong when the
system had never checked it.

These tests pin the replacement: the child asks the Parent service that owns the
credential, a rejection stays a rejection, and anything that prevents a verdict
raises so the panel can say so instead of blaming the parent.
"""

from __future__ import annotations

import io
import json
import unittest
import urllib.error
from pathlib import Path

from greia_launcher.parent_credential_client import (
    DEFAULT_PARENT_API_BASE_URL,
    ParentCredentialClient,
    ParentCredentialUnavailable,
    ParentPasswordVerifier,
)


class _Response(io.BytesIO):
    def __init__(self, status: int, payload: bytes) -> None:
        super().__init__(payload)
        self.status = status


class _FakeUrlopen:
    """Stand in for urllib.request.urlopen, recording what was sent."""

    def __init__(self, *, status: int = 201, payload: bytes = b"{}", error: Exception | None = None) -> None:
        self.status = status
        self.payload = payload
        self.error = error
        self.calls: list[tuple[str, bytes, dict[str, str]]] = []

    def __call__(self, request, timeout=None):  # noqa: ANN001 - test double
        self.calls.append(
            (request.full_url, request.data, dict(request.headers))
        )
        if self.error is not None:
            raise self.error
        return _Response(self.status, self.payload)

    @property
    def last_body(self) -> dict[str, object]:
        _url, data, _headers = self.calls[-1]
        return json.loads(data.decode("utf-8"))


def _ok_credential() -> bytes:
    return json.dumps(
        {"device": {"id": "x"}, "credential": "issued-token"}
    ).encode("utf-8")


class ClientSendsTheExistingRateLimitedEndpointTests(unittest.TestCase):
    def test_posts_to_the_pairing_bootstrap_endpoint_on_loopback(self) -> None:
        fake = _FakeUrlopen(payload=_ok_credential())
        client = ParentCredentialClient()
        original = urllib.request.urlopen
        urllib.request.urlopen = fake
        try:
            self.assertTrue(client.verify("greia"))
        finally:
            urllib.request.urlopen = original
        url, data, headers = fake.calls[-1]
        self.assertTrue(url.startswith(DEFAULT_PARENT_API_BASE_URL))
        self.assertTrue(url.endswith("/api/v1/pairing/bootstrap"))
        self.assertEqual(headers["Content-type"], "application/json")
        self.assertEqual(fake.last_body["password"], "greia")

    def test_timeout_is_bounded_and_positive(self) -> None:
        with self.assertRaises(ValueError):
            ParentCredentialClient(timeout_seconds=0)

    def test_base_url_trailing_slash_does_not_double_up(self) -> None:
        client = ParentCredentialClient(base_url="http://127.0.0.1:8766/")
        self.assertNotIn("//api", client._endpoint)


class RejectionStaysARejectionTests(unittest.TestCase):
    def _verify_with_http_error(self, code: int) -> bool:
        fake = _FakeUrlopen(
            error=urllib.error.HTTPError(
                "http://127.0.0.1:8766/api/v1/pairing/bootstrap",
                code,
                "denied",
                {},
                io.BytesIO(b"{}"),
            )
        )
        client = ParentCredentialClient()
        original = urllib.request.urlopen
        urllib.request.urlopen = fake
        try:
            return client.verify("wrong")
        finally:
            urllib.request.urlopen = original

    def test_403_is_a_wrong_password_not_an_outage(self) -> None:
        self.assertFalse(self._verify_with_http_error(403))

    def test_429_rate_limited_is_refused_without_claiming_an_outage(self) -> None:
        self.assertFalse(self._verify_with_http_error(429))

    def test_400_invalid_request_is_refused(self) -> None:
        self.assertFalse(self._verify_with_http_error(400))

    def test_server_error_is_an_outage_not_a_wrong_password(self) -> None:
        with self.assertRaises(ParentCredentialUnavailable):
            self._verify_with_http_error(500)


class CannotCheckIsDistinctFromRejectedTests(unittest.TestCase):
    """Anything preventing a verdict must raise, never return False.

    Returning False here is what told the parent their password was wrong when
    the system had not checked it at all.
    """

    def _verify_with(self, fake: _FakeUrlopen) -> bool:
        client = ParentCredentialClient()
        original = urllib.request.urlopen
        urllib.request.urlopen = fake
        try:
            return client.verify("greia")
        finally:
            urllib.request.urlopen = original

    def test_unreachable_service_raises(self) -> None:
        fake = _FakeUrlopen(
            error=urllib.error.URLError("connection refused")
        )
        with self.assertRaises(ParentCredentialUnavailable):
            self._verify_with(fake)

    def test_timeout_raises(self) -> None:
        with self.assertRaises(ParentCredentialUnavailable):
            self._verify_with(_FakeUrlopen(error=TimeoutError()))

    def test_unexpected_success_status_raises(self) -> None:
        with self.assertRaises(ParentCredentialUnavailable):
            self._verify_with(_FakeUrlopen(status=200, payload=_ok_credential()))

    def test_malformed_json_raises(self) -> None:
        with self.assertRaises(ParentCredentialUnavailable):
            self._verify_with(_FakeUrlopen(status=201, payload=b"not json"))

    def test_success_without_a_device_credential_raises(self) -> None:
        with self.assertRaises(ParentCredentialUnavailable):
            self._verify_with(
                _FakeUrlopen(status=201, payload=json.dumps({"device": {}}).encode())
            )


class SecretHygieneTests(unittest.TestCase):
    def test_no_error_message_embeds_the_candidate_password(self) -> None:
        secret = "correct-horse-battery-staple"
        cases = (
            _FakeUrlopen(error=urllib.error.URLError("refused")),
            _FakeUrlopen(status=500, payload=b"{}"),
            _FakeUrlopen(status=201, payload=b"garbage"),
            _FakeUrlopen(
                error=urllib.error.HTTPError(
                    "u", 500, "boom", {}, io.BytesIO(b"")
                )
            ),
        )
        for fake in cases:
            with self.subTest(case=type(fake.error).__name__ if fake.error else fake.status):
                client = ParentCredentialClient()
                original = urllib.request.urlopen
                urllib.request.urlopen = fake
                try:
                    client.verify(secret)
                except ParentCredentialUnavailable as exc:
                    self.assertNotIn(secret, str(exc))
                except Exception as exc:  # pragma: no cover - defensive
                    self.assertNotIn(secret, str(exc))
                else:
                    self.fail("expected no verdict")
                finally:
                    urllib.request.urlopen = original

    def test_module_source_never_writes_the_password_to_a_log(self) -> None:
        source = (
            Path(__file__).resolve().parents[1]
            / "src"
            / "greia_launcher"
            / "parent_credential_client.py"
        ).read_text(encoding="utf-8")
        for forbidden in ("logging", "print(", "logger"):
            self.assertNotIn(forbidden, source)


class ProtocolCompatibilityTests(unittest.TestCase):
    """The panel depends on a narrow protocol, not on a concrete store."""

    def test_the_digest_store_still_satisfies_it(self) -> None:
        from greia_platform.main_credential import MainCredentialStore

        store = MainCredentialStore(Path("/nonexistent/cred.json"))
        self.assertIsInstance(store, ParentPasswordVerifier)

    def test_client_satisfies_it(self) -> None:
        self.assertIsInstance(ParentCredentialClient(), ParentPasswordVerifier)


class PanelDistinguishesRejectionFromOutageTests(unittest.TestCase):
    """The panel must not report an impossible check as a wrong password."""

    def _attempt(self, verifier: object) -> str | None:
        from greia_launcher import parent_panel as module

        overlay = module.ParentSettingsOverlay(verifier)  # type: ignore[arg-type]
        overlay.state = module.ParentPanelState.AUTH
        overlay.password_text = "greia"
        overlay._attempt_auth(None)
        return overlay._password_problem

    def test_outage_is_reported_as_cannot_check(self) -> None:
        class _Verifier:
            def verify(self, password: str) -> bool:
                raise ParentCredentialUnavailable("unreachable")

        self.assertEqual(
            self._attempt(_Verifier()), _PASSWORD_CHECK_FAILED()
        )

    def test_rejection_reports_no_problem_and_stays_on_auth(self) -> None:
        from greia_launcher import parent_panel as module

        class _Verifier:
            def verify(self, password: str) -> bool:
                return False

        overlay = module.ParentSettingsOverlay(_Verifier())  # type: ignore[arg-type]
        overlay.state = module.ParentPanelState.AUTH
        overlay.password_text = "nope"
        overlay._attempt_auth(None)
        self.assertIsNone(overlay._password_problem)
        self.assertIs(overlay.state, module.ParentPanelState.AUTH)

    def test_unexpected_error_is_also_cannot_check_not_a_wrong_password(self) -> None:
        class _Verifier:
            def verify(self, password: str) -> bool:
                raise RuntimeError("boom")

        self.assertEqual(
            self._attempt(_Verifier()), _PASSWORD_CHECK_FAILED()
        )

    def test_accepted_password_opens_the_panel(self) -> None:
        from greia_launcher import parent_panel as module

        class _Verifier:
            def verify(self, password: str) -> bool:
                return True

        overlay = module.ParentSettingsOverlay(_Verifier())  # type: ignore[arg-type]
        overlay.state = module.ParentPanelState.AUTH
        overlay.password_text = "greia"
        overlay._attempt_auth(None)
        self.assertIs(overlay.state, module.ParentPanelState.PANEL)
        self.assertIsNone(overlay._password_problem)


def _PASSWORD_CHECK_FAILED() -> str:  # noqa: N802 - test helper
    from greia_launcher import parent_panel as module

    return module._PASSWORD_CHECK_FAILED


if __name__ == "__main__":
    unittest.main()
