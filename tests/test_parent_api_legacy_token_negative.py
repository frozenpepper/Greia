from __future__ import annotations

import json
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from pathlib import Path

from greia_parent.api_server import ParentApiApplication, ParentApiHTTPServer
from greia_parent.protocol import API_BASE


PROJECT_ROOT = Path(__file__).resolve().parents[1]
JsonPayload = dict[str, object] | list[object]


def _app(root: Path) -> ParentApiApplication:
    return ParentApiApplication(
        PROJECT_ROOT,
        root / "parent",
        profiles_dir=root / "profiles",
        hardware_settings_dir=root / "hardware",
        hardware_status_path=root / "hardware-status.json",
        active_profile_status_path=root / "active-profile.json",
    )


def _request(
    method: str,
    url: str,
    *,
    headers: dict[str, str] | None = None,
    body: dict[str, object] | None = None,
) -> tuple[int, JsonPayload]:
    data = json.dumps(body).encode("utf-8") if body is not None else None
    request = urllib.request.Request(url, data=data, method=method)
    if body is not None:
        request.add_header("Content-Type", "application/json")
    for name, value in (headers or {}).items():
        request.add_header(name, value)
    try:
        with urllib.request.urlopen(request, timeout=5) as response:
            return response.status, json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", "replace")
        try:
            payload: JsonPayload = json.loads(raw)
        except ValueError:
            payload = {"raw": raw}
        return exc.code, payload


def _error_code(payload: JsonPayload) -> str | None:
    if not isinstance(payload, dict):
        return None
    error = payload.get("error")
    if not isinstance(error, dict):
        return None
    code = error.get("code")
    return code if isinstance(code, str) else None


class ParentApiLegacyTokenNegativeTests(unittest.TestCase):
    def test_api_v1_rejects_every_retired_shared_token_transport(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            state_dir = root / "parent"
            state_dir.mkdir(parents=True)
            legacy_token = "L" * 48
            token_path = state_dir / "parent-pairing-token"
            token_path.write_text(legacy_token + "\n", encoding="ascii")

            app = _app(root)
            self.assertFalse(token_path.exists())

            server = ParentApiHTTPServer(("127.0.0.1", 0), app)
            port = server.server_address[1]
            thread = threading.Thread(
                target=server.serve_forever,
                kwargs={"poll_interval": 0.05},
                daemon=True,
            )
            thread.start()
            try:
                protected = f"http://127.0.0.1:{port}{API_BASE}/devices"
                retired_attempts = (
                    {"X-Pip-Token": legacy_token},
                    {"Cookie": f"greia_parent={legacy_token}"},
                )
                for headers in retired_attempts:
                    with self.subTest(headers=headers):
                        status, payload = _request("GET", protected, headers=headers)
                        self.assertEqual(status, 401)
                        self.assertEqual(_error_code(payload), "pairing_required")

                status, payload = _request(
                    "GET",
                    protected + f"?token={legacy_token}",
                )
                self.assertEqual(status, 401)
                self.assertEqual(_error_code(payload), "pairing_required")

                status, payload = _request(
                    "POST",
                    f"http://127.0.0.1:{port}{API_BASE}/pairing/bootstrap",
                    body={
                        "pairing_token": legacy_token,
                        "device_name": "Legacy browser",
                    },
                )
                self.assertEqual(status, 400)
                self.assertEqual(_error_code(payload), "invalid_request")
                self.assertEqual(app.devices_payload(), [])
            finally:
                server.shutdown()
                thread.join(timeout=5)
                server.server_close()

    def test_api_v1_accepts_only_current_device_credential_transports(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            app = _app(root)
            issued = app.bootstrap_device("greia", "Accepted browser")
            credential = str(issued["credential"])

            server = ParentApiHTTPServer(("127.0.0.1", 0), app)
            port = server.server_address[1]
            thread = threading.Thread(
                target=server.serve_forever,
                kwargs={"poll_interval": 0.05},
                daemon=True,
            )
            thread.start()
            try:
                protected = f"http://127.0.0.1:{port}{API_BASE}/devices"
                for headers in (
                    {"Authorization": f"Bearer {credential}"},
                    {"Cookie": f"greia_parent_device={credential}"},
                ):
                    with self.subTest(headers=tuple(headers)):
                        status, payload = _request("GET", protected, headers=headers)
                        self.assertEqual(status, 200)
                        self.assertIsInstance(payload, list)
                        assert isinstance(payload, list)
                        self.assertEqual(len(payload), 1)
                        device = payload[0]
                        self.assertIsInstance(device, dict)
                        assert isinstance(device, dict)
                        self.assertEqual(device.get("display_name"), "Accepted browser")
            finally:
                server.shutdown()
                thread.join(timeout=5)
                server.server_close()


if __name__ == "__main__":
    unittest.main()
