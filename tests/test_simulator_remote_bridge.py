from __future__ import annotations

import json
import time
import unittest
import urllib.request
from unittest import mock

from greia_simulator.remote_bridge import (
    DEFAULT_REMOTE_PORT,
    SimulatorRemoteBridge,
)
from tools import greia_simulator_ctl


class DummyPygame:
    K_LEFT = 276
    K_RIGHT = 275
    K_UP = 273
    K_DOWN = 274
    K_RETURN = 13
    K_ESCAPE = 27
    K_TAB = 9
    K_SPACE = 32
    K_BACKSPACE = 8
    K_s = 115
    K_t = 116

    KEYDOWN = 768
    KEYUP = 769
    MOUSEMOTION = 1024
    MOUSEBUTTONDOWN = 1025
    MOUSEBUTTONUP = 1026
    TEXTINPUT = 771

    class event:
        @staticmethod
        def Event(event_type: int, **kwargs: object) -> dict[str, object]:
            return {"type": event_type, **kwargs}


class SimulatorRemoteBridgeTests(unittest.TestCase):
    def setUp(self) -> None:
        # Use ephemeral port for testing
        self.bridge = SimulatorRemoteBridge(port=0, host="127.0.0.1")
        self.bridge.start()

    def tearDown(self) -> None:
        self.bridge.stop()

    def test_bridge_starts_and_serves_html_and_state(self) -> None:
        url = self.bridge.url
        self.assertTrue(url.startswith("http://127.0.0.1:"))

        # GET /
        with urllib.request.urlopen(f"{url}/", timeout=5.0) as resp:
            html = resp.read().decode("utf-8")
            self.assertIn("Greia Activity Simulator — Live Canvas", html)
            self.assertEqual(resp.headers.get("Content-Type"), "text/html; charset=utf-8")

        # GET /api/state
        with urllib.request.urlopen(f"{url}/api/state", timeout=5.0) as resp:
            state = json.loads(resp.read().decode("utf-8"))
            self.assertEqual(state["mode"], "profiles")
            self.assertEqual(state["resolution"], [1024, 600])
            self.assertEqual(state["frame_count"], 0)

    def test_key_text_mouse_chord_queuing_and_event_polling(self) -> None:
        url = self.bridge.url

        # POST key
        req = urllib.request.Request(
            f"{url}/api/input/key",
            data=json.dumps({"key": "LEFT", "action": "press"}).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=5.0) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            self.assertTrue(data["ok"])

        # POST text
        req = urllib.request.Request(
            f"{url}/api/input/text",
            data=json.dumps({"text": "greia"}).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=5.0) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            self.assertTrue(data["ok"])

        # POST mouse
        req = urllib.request.Request(
            f"{url}/api/input/mouse",
            data=json.dumps({"x": 400, "y": 300, "action": "click", "button": 1}).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=5.0) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            self.assertTrue(data["ok"])

        # Poll events
        events = self.bridge.poll_events(DummyPygame)
        # We expect: KEYDOWN (LEFT), KEYUP (LEFT), TEXTINPUT ("greia"), MOUSEMOTION, MOUSEBUTTONDOWN, MOUSEBUTTONUP
        types = [e["type"] for e in events]
        self.assertIn(DummyPygame.KEYDOWN, types)
        self.assertIn(DummyPygame.KEYUP, types)
        self.assertIn(DummyPygame.TEXTINPUT, types)
        self.assertIn(DummyPygame.MOUSEBUTTONDOWN, types)

    def test_ctl_tool_dispatch(self) -> None:
        url = self.bridge.url
        # status command
        status_code = greia_simulator_ctl.main(["--url", url, "status"])
        self.assertEqual(status_code, 0)

        # key command
        key_code = greia_simulator_ctl.main(["--url", url, "key", "RETURN"])
        self.assertEqual(key_code, 0)

        # text command
        text_code = greia_simulator_ctl.main(["--url", url, "text", "testuser"])
        self.assertEqual(text_code, 0)

        # click command
        click_code = greia_simulator_ctl.main(["--url", url, "click", "100", "200"])
        self.assertEqual(click_code, 0)

        # chord command
        chord_code = greia_simulator_ctl.main(["--url", url, "chord", "s", "t", "--duration", "0.1"])
        self.assertEqual(chord_code, 0)


if __name__ == "__main__":
    unittest.main()
