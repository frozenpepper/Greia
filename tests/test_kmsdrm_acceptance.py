from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from greia_platform.kmsdrm_acceptance import (
    KMSDRMAcceptanceConfig,
    KMSDRMAcceptanceError,
    KMSDRMAcceptanceRunner,
)


class _Version:
    ver = "2.6.1"


class _Surface:
    def __init__(self):
        self.color = (0, 0, 0)

    def get_size(self):
        return (1024, 600)

    def fill(self, color):
        self.color = tuple(color)


class _Display:
    def __init__(self, *, driver: str = "kmsdrm"):
        self.driver = driver
        self.initialized = False
        self.flips = 0
        self.surface = _Surface()

    def init(self):
        self.initialized = True

    def quit(self):
        self.initialized = False

    def set_mode(self, size, flags=0):
        if not self.initialized:
            raise RuntimeError("display not initialized")
        return self.surface

    def get_driver(self):
        return self.driver

    def flip(self):
        self.flips += 1


class _Event:
    def __init__(self):
        self.pumps = 0

    def pump(self):
        self.pumps += 1


class _Image:
    def tostring(self, surface, format_name):
        return bytes(surface.color) * 8


class _StaticImage:
    def tostring(self, surface, format_name):
        return b"unchanged-frame"


class _Pygame:
    FULLSCREEN = 1
    version = _Version()

    def __init__(self, *, driver: str = "kmsdrm", image=None):
        self.display = _Display(driver=driver)
        self.event = _Event()
        self.image = image or _Image()

    def get_sdl_version(self):
        return (2, 32, 4)


class _Clock:
    def __init__(self):
        self.values = iter((10.0, 10.125))

    def __call__(self):
        return next(self.values)


class KMSDRMAcceptanceTests(unittest.TestCase):
    def test_refuses_without_explicit_takeover_acknowledgement(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            runner = KMSDRMAcceptanceRunner(
                KMSDRMAcceptanceConfig(
                    output_path=Path(temporary) / "result.json",
                    acknowledge_display_takeover=False,
                ),
                environment={"SDL_VIDEODRIVER": "kmsdrm"},
                pygame_module=_Pygame(),
            )
            with self.assertRaisesRegex(
                KMSDRMAcceptanceError, "explicit display-takeover acknowledgement"
            ):
                runner.run()

    def test_refuses_x11_or_wayland_transport_authority(self) -> None:
        for environment in (
            {"SDL_VIDEODRIVER": "kmsdrm", "DISPLAY": ":0"},
            {
                "SDL_VIDEODRIVER": "kmsdrm",
                "XAUTHORITY": "/run/greia/xauthority",
            },
            {"SDL_VIDEODRIVER": "kmsdrm", "WAYLAND_DISPLAY": "wayland-0"},
        ):
            with self.subTest(environment=environment):
                with tempfile.TemporaryDirectory() as temporary:
                    pygame = _Pygame()
                    runner = KMSDRMAcceptanceRunner(
                        KMSDRMAcceptanceConfig(
                            output_path=Path(temporary) / "result.json",
                            acknowledge_display_takeover=True,
                        ),
                        environment=environment,
                        pygame_module=pygame,
                    )
                    with self.assertRaisesRegex(
                        KMSDRMAcceptanceError, "refuses X11/Wayland"
                    ):
                        runner.run()
                    self.assertFalse(pygame.display.initialized)

    def test_refuses_when_sdl_selects_any_driver_other_than_kmsdrm(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "result.json"
            pygame = _Pygame(driver="dummy")
            runner = KMSDRMAcceptanceRunner(
                KMSDRMAcceptanceConfig(
                    output_path=output,
                    acknowledge_display_takeover=True,
                ),
                environment={"SDL_VIDEODRIVER": "kmsdrm"},
                pygame_module=pygame,
            )
            with self.assertRaisesRegex(KMSDRMAcceptanceError, "expected 'kmsdrm'"):
                runner.run()
            payload = json.loads(output.read_text(encoding="utf-8"))

        self.assertFalse(payload["ok"])
        self.assertEqual(payload["requested_video_driver"], "kmsdrm")
        self.assertFalse(pygame.display.initialized)

    def test_success_records_actual_driver_surface_and_distinct_rendered_frames(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "result.json"
            pygame = _Pygame()
            runner = KMSDRMAcceptanceRunner(
                KMSDRMAcceptanceConfig(
                    output_path=output,
                    acknowledge_display_takeover=True,
                    frame_count=3,
                ),
                environment={"SDL_VIDEODRIVER": "kmsdrm"},
                pygame_module=pygame,
                clock=_Clock(),
            )
            result = runner.run()
            persisted = json.loads(output.read_text(encoding="utf-8"))

        self.assertTrue(result["ok"])
        self.assertEqual(result["actual_video_driver"], "kmsdrm")
        self.assertEqual(result["surface"], {"width": 1024, "height": 600})
        self.assertEqual(result["frame_count"], 3)
        self.assertEqual(len(set(result["frame_sha256"])), 3)
        self.assertEqual(result["duration_seconds"], 0.125)
        self.assertEqual(result, persisted)
        self.assertEqual(pygame.display.flips, 3)
        self.assertEqual(pygame.event.pumps, 3)
        self.assertFalse(pygame.display.initialized)

    def test_static_rendered_buffer_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "result.json"
            pygame = _Pygame(image=_StaticImage())
            runner = KMSDRMAcceptanceRunner(
                KMSDRMAcceptanceConfig(
                    output_path=output,
                    acknowledge_display_takeover=True,
                    frame_count=3,
                ),
                environment={"SDL_VIDEODRIVER": "kmsdrm"},
                pygame_module=pygame,
            )
            with self.assertRaisesRegex(KMSDRMAcceptanceError, "did not change"):
                runner.run()
            payload = json.loads(output.read_text(encoding="utf-8"))

        self.assertFalse(payload["ok"])
        self.assertEqual(payload["error_type"], "KMSDRMAcceptanceError")
        self.assertEqual(pygame.display.flips, 3)
        self.assertFalse(pygame.display.initialized)

    def test_frame_count_is_strict_integer_and_bounded_before_pygame_initialization(self) -> None:
        for frame_count in (True, 0, 17, 2.0):
            with self.subTest(frame_count=frame_count), tempfile.TemporaryDirectory() as temporary:
                pygame = _Pygame()
                runner = KMSDRMAcceptanceRunner(
                    KMSDRMAcceptanceConfig(
                        output_path=Path(temporary) / "result.json",
                        acknowledge_display_takeover=True,
                        frame_count=frame_count,  # type: ignore[arg-type]
                    ),
                    environment={"SDL_VIDEODRIVER": "kmsdrm"},
                    pygame_module=pygame,
                )
                with self.assertRaisesRegex(
                    KMSDRMAcceptanceError, "integer between 1 and 16"
                ):
                    runner.run()
                self.assertFalse(pygame.display.initialized)


if __name__ == "__main__":
    unittest.main()
