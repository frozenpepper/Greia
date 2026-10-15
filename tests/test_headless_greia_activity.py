"""Focused Activity capture is an actual producer->owned-bridge->PNG contract.

This suite recreates the historical error where the Python Activity bootstrap
acted only as a bridge client while the tool never started a bridge server.
It uses one disposable tiny Pygame activity, not Greia Shell or user profiles.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path
import struct
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "headless_greia_activity.py"
SPEC = importlib.util.spec_from_file_location("headless_greia_activity_under_test", TOOL)
assert SPEC is not None and SPEC.loader is not None
headless = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = headless
SPEC.loader.exec_module(headless)


class HeadlessActivityCaptureTests(unittest.TestCase):
    def test_invalid_source_fails_before_creating_bridge_or_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            with patch.object(headless, "SimulatorRemoteBridge") as bridge:
                code = headless._probe(
                    activity_main=path / "missing.py",
                    locale="it", viewport="1024x600",
                    survival_seconds=0.1, screenshot_prefix=path / "out",
                    click=None, key=None,
                )
                self.assertEqual(code, 2)
                bridge.assert_not_called()

    def test_existing_evidence_is_not_overwritten(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            activity = path / "main.py"
            activity.write_text("pass", encoding="utf-8")
            artifact = path / "capture-01-first-frame.png"
            artifact.write_bytes(b"old evidence")
            with patch.object(headless, "SimulatorRemoteBridge") as bridge:
                result = headless._probe(
                    activity_main=activity, locale="it", viewport="1024x600",
                    survival_seconds=0.1, screenshot_prefix=path / "capture",
                    click=None, key=None,
                )
            self.assertEqual(result, 2)
            self.assertEqual(artifact.read_bytes(), b"old evidence")
            bridge.assert_not_called()

    def test_real_activity_bootstrap_publishes_frames_to_owned_bridge(self) -> None:
        # This test crosses the real Pygame/Supervisor-compatible bootstrap.
        # A mocked bridge cannot catch the absent-listener failure.
        import pygame
        with tempfile.TemporaryDirectory(prefix="greia-hl-probe-test-") as directory:
            root = Path(directory)
            activity = root / "minimal_game.py"
            activity.write_text(
                "import time\n"
                "import pygame\n"
                "pygame.init()\n"
                "screen = pygame.display.set_mode((1024, 600))\n"
                "deadline = time.monotonic() + 12.0\n"
                "running = True\n"
                "while running and time.monotonic() < deadline:\n"
                "    # SDL turns the probe's SIGTERM into pygame.QUIT; like every\n"
                "    # real Activity, honour it so the stop is graceful.\n"
                "    for event in pygame.event.get():\n"
                "        if event.type == pygame.QUIT:\n"
                "            running = False\n"
                "    screen.fill((40, 90, 130))\n"
                "    pygame.display.flip()\n"
                "    time.sleep(0.08)\n",
                encoding="utf-8",
            )
            prefix = root / "capture"
            result = headless.main([
                "--activity-main", str(activity),
                "--locale", "en",
                "--viewport", "800x480",
                "--survival-seconds", "0.5",
                "--screenshot-prefix", str(prefix),
                "--click-x", "440",
                "--click-y", "300",
            ])
            self.assertEqual(result, 0)
            first = root / "capture-01-first-frame.png"
            post = root / "capture-02-post.png"
            log = root / "capture-child.log"
            for file in (first, post):
                self.assertTrue(file.is_file(), file)
                data = file.read_bytes()
                self.assertTrue(data.startswith(headless.PNG_SIGNATURE))
                self.assertEqual(struct.unpack_from(">II", data, 16), (800, 480))
            self.assertTrue(log.is_file())
            self.assertNotIn("Traceback (most recent call last)", log.read_text(errors="replace"))


if __name__ == "__main__":
    unittest.main()
