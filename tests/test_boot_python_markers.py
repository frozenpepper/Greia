"""Durable proof for Python boot-marker helper + launcher first-frame KPI.

Owned by B03R. Asserts the exact ``GREIA_BOOT event=<name> monotonic_ns=<int>``
line shape, the per-process exactly-once ``intro_first_frame_flipped`` invariant
over the multi-flip intro path, and that the ``print`` shape lives only in the
helper. Must not overlap ``tests/test_boot_markers.py`` (owned by B04).
"""

from __future__ import annotations

import contextlib
import io
import os
import re
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from greia_launcher import boot_intro  # noqa: E402
from greia_platform.boot_markers import emit_boot_marker  # noqa: E402

LINE_RE = re.compile(r"^GREIA_BOOT event=(\S+) monotonic_ns=(\d+)$")


class _FakeSurface:
    def __init__(self, width: int = 222, height: int = 600) -> None:
        self._size = (width, height)

    def get_width(self) -> int:
        return self._size[0]

    def get_height(self) -> int:
        return self._size[1]

    def get_size(self) -> tuple[int, int]:
        return self._size

    def fill(self, *args: object) -> None:
        pass

    def blit(self, *args: object) -> None:
        pass

    def get_rect(self, **kwargs: object) -> SimpleNamespace:
        return SimpleNamespace(center=kwargs.get("center", (0, 0)))


class _FakeDisplay:
    def __init__(self, *, fail: bool = False) -> None:
        self.flips = 0
        self._fail = fail

    def flip(self) -> None:
        if self._fail:
            raise RuntimeError("simulated flip failure")
        self.flips += 1


def _make_fake_pygame(display: _FakeDisplay) -> SimpleNamespace:
    return SimpleNamespace(
        display=display,
        event=SimpleNamespace(pump=lambda: None),
        time=SimpleNamespace(wait=lambda ms: None),
        transform=SimpleNamespace(smoothscale=lambda surface, size: surface),
    )


def _clean_boot_env(marker: Path) -> dict[str, str]:
    env = {
        key: value
        for key, value in os.environ.items()
        if key not in ("GREIA_SKIP_BOOT_INTRO", "GREIA_SKIP_BOOT_HANDOFF")
    }
    env["GREIA_BOOT_INTRO_MARKER"] = str(marker)
    return env


class BootPythonMarkersTest(unittest.TestCase):
    def test_helper_emission_shape(self) -> None:
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            emit_boot_marker("probe_event")
        lines = buffer.getvalue().splitlines()
        self.assertEqual(len(lines), 1)
        match = LINE_RE.match(lines[0])
        self.assertIsNotNone(match)
        assert match is not None
        self.assertEqual(match.group(1), "probe_event")
        self.assertTrue(match.group(2).isdigit())

    def test_print_shape_lives_only_in_helper(self) -> None:
        owners = sorted(
            str(path.relative_to(ROOT))
            for path in (ROOT / "src").rglob("*.py")
            if 'print(f"GREIA_BOOT' in path.read_text(encoding="utf-8")
            or "print(f'GREIA_BOOT" in path.read_text(encoding="utf-8")
        )
        self.assertEqual(owners, ["src/greia_platform/boot_markers.py"])
        leakers = sorted(
            str(path.relative_to(ROOT))
            for path in (ROOT / "src").rglob("*.py")
            if path.name != "boot_markers.py"
            and "GREIA_BOOT event=" in path.read_text(encoding="utf-8")
        )
        self.assertEqual(leakers, [])

    def test_intro_timing_constants_unchanged(self) -> None:
        self.assertEqual(boot_intro.ANIMATION_SECONDS, 5.0)
        self.assertEqual(boot_intro.FINAL_FRAME_HOLD_SECONDS, 2.0)

    def test_first_frame_kpi_exactly_once_over_multi_flip_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            marker = Path(tmp) / "intro-marker"
            frames = [_FakeSurface() for _ in range(3)]
            screen = _FakeSurface(960, 540)
            with mock.patch.dict(os.environ, _clean_boot_env(marker), clear=True), mock.patch.object(
                boot_intro, "ANIMATION_SECONDS", 0.05
            ), mock.patch.object(
                boot_intro, "FINAL_FRAME_HOLD_SECONDS", 0.01
            ), mock.patch.object(
                boot_intro, "_RENDER_INTERVAL_SECONDS", 0.001
            ), mock.patch.object(
                boot_intro, "load_animation_frames", return_value=frames
            ), mock.patch.object(
                boot_intro, "load_logo", return_value=_FakeSurface()
            ):
                boot_intro._FIRST_FRAME_FLIPPED_EMITTED = False

                first_display = _FakeDisplay()
                first_out = io.StringIO()
                with contextlib.redirect_stdout(first_out):
                    boot_intro.run_intro(screen, _make_fake_pygame(first_display))
                first_lines = first_out.getvalue().splitlines()

                # Multi-flip path exercised: handoff + animation + final frame.
                self.assertGreaterEqual(first_display.flips, 3)
                for line in first_lines:
                    self.assertIsNotNone(
                        LINE_RE.match(line), f"unparsable marker line: {line!r}"
                    )
                kpi = [line for line in first_lines if "intro_first_frame_flipped" in line]
                self.assertEqual(len(kpi), 1, f"expected exactly one KPI, got: {first_lines}")
                events = [LINE_RE.match(line).group(1) for line in first_lines]  # type: ignore[union-attr]
                self.assertEqual(events[0], "intro_enter")
                self.assertEqual(events[-1], "intro_end")

                # Second run in the same process emits no second KPI marker.
                second_display = _FakeDisplay()
                second_out = io.StringIO()
                with contextlib.redirect_stdout(second_out):
                    boot_intro.run_intro(screen, _make_fake_pygame(second_display))
                second_lines = second_out.getvalue().splitlines()
                self.assertGreaterEqual(second_display.flips, 1)
                second_kpi = [
                    line for line in second_lines if "intro_first_frame_flipped" in line
                ]
                self.assertEqual(
                    second_kpi, [], f"duplicated KPI on second run: {second_lines}"
                )

    def test_flip_failure_emits_no_kpi(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            marker = Path(tmp) / "intro-marker"
            screen = _FakeSurface(960, 540)
            with mock.patch.dict(os.environ, _clean_boot_env(marker), clear=True), mock.patch.object(
                boot_intro, "load_logo", return_value=_FakeSurface()
            ):
                boot_intro._FIRST_FRAME_FLIPPED_EMITTED = False
                buffer = io.StringIO()
                with contextlib.redirect_stdout(buffer):
                    with self.assertRaises(RuntimeError):
                        boot_intro.run_intro(screen, _make_fake_pygame(_FakeDisplay(fail=True)))
                lines = buffer.getvalue().splitlines()
                events = [LINE_RE.match(line).group(1) for line in lines]  # type: ignore[union-attr]
                self.assertIn("intro_enter", events)
                self.assertIn("intro_end", events)
                self.assertNotIn("intro_first_frame_flipped", events)


if __name__ == "__main__":
    unittest.main()
