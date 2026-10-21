"""Platform Activity display-request normalization on real and synthetic screens."""

from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from greia_platform.activity_display import (
    VIEWPORT_ENVIRONMENT,
    install_display_request_policy,
    normalize_display_request,
    parse_viewport,
    remember_viewport,
    target_viewport,
)

ROOT = Path(__file__).resolve().parents[1]


class _FakeDisplay:
    def __init__(self, sizes: tuple[tuple[int, int], ...]) -> None:
        self.sizes = sizes
        self.calls: list[tuple[tuple[object, ...], dict[str, object]]] = []
        self._surface = object()

    def get_desktop_sizes(self):
        return self.sizes

    def Info(self):  # noqa: N802 - Pygame API spelling
        raise RuntimeError("no display info")

    def set_mode(self, *args, **kwargs):
        self.calls.append((args, kwargs))
        return self._surface


class _FakePygame:
    def __init__(self, sizes: tuple[tuple[int, int], ...] = ((1280, 800),)) -> None:
        self.display = _FakeDisplay(sizes)


class ViewportParsingTests(unittest.TestCase):
    def test_parse_viewport_accepts_only_bounded_pairs(self) -> None:
        self.assertEqual(parse_viewport("1280x800"), (1280, 800))
        self.assertEqual(parse_viewport(" 800X480 "), (800, 480))
        for value in (None, "", "1280", "1280x", "x800", "abcx800", "1280x0", "319x480", "7681x800"):
            with self.subTest(value=value):
                self.assertIsNone(parse_viewport(value))

    def test_remember_viewport_records_only_valid_shell_sizes(self) -> None:
        environment: dict[str, str] = {}
        remember_viewport((1280, 800), environment=environment)
        self.assertEqual(environment[VIEWPORT_ENVIRONMENT], "1280x800")
        remember_viewport((1, 1), environment=environment)
        self.assertEqual(environment[VIEWPORT_ENVIRONMENT], "1280x800")


class DisplayPolicyTests(unittest.TestCase):
    def test_explicit_session_viewport_wins_over_the_desktop(self) -> None:
        pygame = _FakePygame(((1920, 1080),))
        self.assertEqual(
            target_viewport(pygame, environ={VIEWPORT_ENVIRONMENT: "1280x800"}),
            (1280, 800),
        )

    def test_desktop_size_is_the_fallback(self) -> None:
        pygame = _FakePygame(((1280, 800),))
        self.assertEqual(target_viewport(pygame, environ={}), (1280, 800))

    def test_requested_reference_size_is_replaced_and_flags_are_preserved(self) -> None:
        pygame = _FakePygame(((1280, 800),))
        install_display_request_policy(
            pygame, environ={VIEWPORT_ENVIRONMENT: "1280x800"}
        )
        pygame.display.set_mode((1024, 600), 0x40)
        args, kwargs = pygame.display.calls[-1]
        self.assertEqual(args[0], (1280, 800))
        self.assertEqual(args[1], 0x40)
        self.assertEqual(kwargs["display"], 0)

    def test_no_target_leaves_the_request_untouched(self) -> None:
        size, flags = normalize_display_request((1024, 600), 7, target_size=None)
        self.assertEqual((size, flags), ((1024, 600), 7))

    def test_wrapper_retries_the_legacy_three_argument_form(self) -> None:
        pygame = _FakePygame(((1280, 800),))

        def legacy_set_mode(size, flags=0, depth=0):
            pygame.display.calls.append(((size, flags, depth), {}))
            return object()

        pygame.display.set_mode = legacy_set_mode
        install_display_request_policy(
            pygame, environ={VIEWPORT_ENVIRONMENT: "1280x800"}
        )
        pygame.display.set_mode((1024, 600), 0x40)
        self.assertEqual(pygame.display.calls[-1][0], ((1280, 800), 0x40, 0))


class EntryIntegrationTests(unittest.TestCase):
    def _run(self, *, session: bool, viewport: str | None) -> dict[str, object]:
        with tempfile.TemporaryDirectory() as temporary:
            script = Path(temporary) / "main.py"
            script.write_text(
                "import json, pygame\n"
                "pygame.init()\n"
                "screen = pygame.display.set_mode((1024, 600), pygame.RESIZABLE)\n"
                "print(json.dumps({'size': list(screen.get_size())}))\n",
                encoding="utf-8",
            )
            environment = {
                key: value
                for key, value in os.environ.items()
                if not key.startswith("GREIA_")
            }
            environment.update(
                PYTHONPATH=str(ROOT / "src"),
                PYTHONDONTWRITEBYTECODE="1",
                SDL_VIDEODRIVER="dummy",
                SDL_AUDIODRIVER="dummy",
            )
            if session:
                environment["GREIA_ACTIVITY_SESSION_ID"] = "0123456789abcdef0123456789abcdef"
            if viewport is not None:
                environment[VIEWPORT_ENVIRONMENT] = viewport
            result = subprocess.run(
                [
                    sys.executable,
                    "-P",
                    "-m",
                    "greia_platform.python_activity_entry",
                    str(script),
                ],
                cwd=temporary,
                env=environment,
                capture_output=True,
                text=True,
                timeout=60,
            )
        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads(result.stdout.strip().splitlines()[-1])

    def test_entry_fills_the_recorded_shell_viewport(self) -> None:
        payload = self._run(session=True, viewport="1280x800")
        self.assertEqual(payload["size"], [1280, 800])

    def test_entry_keeps_the_activity_size_outside_a_greia_session(self) -> None:
        payload = self._run(session=False, viewport="1280x800")
        self.assertEqual(payload["size"], [1024, 600])


if __name__ == "__main__":
    unittest.main()
