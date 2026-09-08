from __future__ import annotations

import json
import stat
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from pathlib import Path

from greia_parent.password_auth import ParentPasswordAttemptLimiter
from greia_parent.production_api import (
    ProductionParentApiApplication,
    ProductionParentApiHTTPServer,
)
from greia_parent.protocol import API_BASE
from greia_platform.wifi import DemoWifiBackend


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class _Clock:
    def __init__(self) -> None:
        self.now = 1000.0

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


class ParentPasswordAuthTests(unittest.TestCase):
    def test_attempt_limiter_is_bounded_clears_on_success_and_expires(self) -> None:
        clock = _Clock()
        limiter = ParentPasswordAttemptLimiter(
            max_failures=2,
            window_seconds=60,
            max_clients=2,
            clock=clock,
        )
        self.assertTrue(limiter.allowed("one"))
        limiter.record_failure("one")
        self.assertTrue(limiter.allowed("one"))
        limiter.record_failure("one")
        self.assertFalse(limiter.allowed("one"))
        limiter.clear("one")
        self.assertTrue(limiter.allowed("one"))
        limiter.record_failure("one")
        limiter.record_failure("one")
        clock.advance(61)
        self.assertTrue(limiter.allowed("one"))
        limiter.record_failure("two")
        limiter.record_failure("three")
        self.assertLessEqual(len(limiter._failures), 2)

    def test_production_startup_deletes_legacy_token_and_protects_password_digest(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            state_dir = root / "parent"
            state_dir.mkdir(parents=True)
            legacy_token = state_dir / "parent-pairing-token"
            legacy_token.write_text("legacy-secret\n", encoding="ascii")
            app = ProductionParentApiApplication(
                PROJECT_ROOT,
                state_dir,
                profiles_dir=root / "profiles",
                hardware_settings_dir=root / "hardware",
                hardware_status_path=root / "hardware-status.json",
                active_profile_status_path=root / "active-profile.json",
                wifi_backend=DemoWifiBackend(),
            )
            self.assertEqual(app.token, "")
            self.assertFalse(legacy_token.exists())
            credential_path = state_dir / "main-credential.json"
            self.assertTrue(credential_path.is_file())
            self.assertEqual(stat.S_IMODE(credential_path.stat().st_mode), 0o600)

    def test_production_http_rate_limits_wrong_password_then_recovers_after_window(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            app = ProductionParentApiApplication(
                PROJECT_ROOT,
                root / "parent",
                profiles_dir=root / "profiles",
                hardware_settings_dir=root / "hardware",
                hardware_status_path=root / "hardware-status.json",
                active_profile_status_path=root / "active-profile.json",
                wifi_backend=DemoWifiBackend(),
            )
            clock = _Clock()
            app.password_attempts = ParentPasswordAttemptLimiter(clock=clock)
            server = ProductionParentApiHTTPServer(("127.0.0.1", 0), app)
            thread = threading.Thread(
                target=server.serve_forever,
                kwargs={"poll_interval": 0.05},
                daemon=True,
            )
            thread.start()
            try:
                url = f"http://127.0.0.1:{server.server_address[1]}{API_BASE}/pairing/bootstrap"

                def post(password: str) -> tuple[int, dict[str, object]]:
                    request = urllib.request.Request(
                        url,
                        data=json.dumps(
                            {"password": password, "device_name": "Test browser"}
                        ).encode("utf-8"),
                        method="POST",
                        headers={"Content-Type": "application/json"},
                    )
                    try:
                        with urllib.request.urlopen(request, timeout=5) as response:
                            return response.status, json.loads(response.read().decode("utf-8"))
                    except urllib.error.HTTPError as exc:
                        return exc.code, json.loads(exc.read().decode("utf-8"))

                for _ in range(5):
                    status, payload = post("wrong")
                    self.assertEqual(status, 403)
                    self.assertEqual(payload["error"]["code"], "authentication_rejected")
                status, payload = post("greia")
                self.assertEqual(status, 429)
                self.assertEqual(payload["error"]["code"], "authentication_rate_limited")

                clock.advance(61)
                status, payload = post("greia")
                self.assertEqual(status, 201)
                self.assertIn("credential", payload)
                self.assertIn("device", payload)
                self.assertTrue(app.password_attempts.allowed("127.0.0.1"))
            finally:
                server.shutdown()
                thread.join(timeout=5)
                server.server_close()


if __name__ == "__main__":
    unittest.main()
