from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from greia_platform.kmsdrm_serial_handoff import (
    KMSDRMSerialHandoffError,
    KMSDRMSerialHandoffRunner,
    SerialHandoffConfig,
)


class _Version:
    ver = "2.6.1"


class _Surface:
    def __init__(self):
        self.color = (0, 0, 0)

    def get_size(self):
        return (800, 600)

    def fill(self, color):
        self.color = color


class _Display:
    def __init__(self, driver: str = "kmsdrm"):
        self.driver = driver
        self.init_count = 0
        self.quit_count = 0
        self.flip_count = 0

    def init(self):
        self.init_count += 1

    def quit(self):
        self.quit_count += 1

    def set_mode(self, size, flags=0):
        return _Surface()

    def get_driver(self):
        return self.driver

    def flip(self):
        self.flip_count += 1


class _Event:
    def __init__(self):
        self.pumps = 0

    def pump(self):
        self.pumps += 1


class _Image:
    @staticmethod
    def tostring(surface, format_name):
        return bytes(surface.color) * 32


class _Pygame:
    FULLSCREEN = 1

    def __init__(self, driver: str = "kmsdrm"):
        self.display = _Display(driver)
        self.event = _Event()
        self.image = _Image()
        self.version = _Version()

    @staticmethod
    def get_sdl_version():
        return (2, 26, 5)


def _clean_payload(frame_count: int = 3) -> dict[str, object]:
    return {
        "schema_version": 1,
        "ok": True,
        "requested_video_driver": "kmsdrm",
        "actual_video_driver": "kmsdrm",
        "surface": {"width": 800, "height": 600},
        "frame_count": frame_count,
        "frame_sha256": [f"{index + 1:064x}" for index in range(frame_count)],
    }


def _crash_payload() -> dict[str, object]:
    return {
        "schema_version": 1,
        "ok": True,
        "actual_video_driver": "kmsdrm",
        "surface": {"width": 800, "height": 600},
        "frame_sha256": "a" * 64,
        "intentional_abrupt_exit": True,
    }


class _Children:
    def __init__(
        self,
        *,
        clean_return: int = 0,
        crash_return: int = 23,
        clean_payload: dict[str, object] | None = None,
        crash_payload: dict[str, object] | None = None,
    ):
        self.clean_return = clean_return
        self.crash_return = crash_return
        self.clean_payload = clean_payload or _clean_payload()
        self.crash_payload = crash_payload or _crash_payload()
        self.calls: list[tuple[object, ...]] = []

    def run_clean(self, output_path: Path, *, frame_count: int):
        self.calls.append(("clean", frame_count))
        output_path.write_text(json.dumps(self.clean_payload), encoding="utf-8")
        return subprocess.CompletedProcess(["clean"], self.clean_return, "", "")

    def run_crash(self, marker_path: Path):
        self.calls.append(("crash",))
        marker_path.write_text(json.dumps(self.crash_payload), encoding="utf-8")
        return subprocess.CompletedProcess(["crash"], self.crash_return, "", "")


class SerialHandoffTests(unittest.TestCase):
    def _runner(self, root: Path, *, pygame=None, children=None, environment=None):
        return KMSDRMSerialHandoffRunner(
            SerialHandoffConfig(
                output_path=root / "result.json",
                acknowledge_display_takeover=True,
            ),
            environment=environment
            or {
                "SDL_VIDEODRIVER": "kmsdrm",
                "DISPLAY": "",
                "WAYLAND_DISPLAY": "",
            },
            pygame_module=pygame or _Pygame(),
            child_runner=children or _Children(),
        )

    def test_clean_and_crash_handoffs_reacquire_shell(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            pygame = _Pygame()
            children = _Children()
            result = self._runner(root, pygame=pygame, children=children).run()
            persisted = json.loads((root / "result.json").read_text(encoding="utf-8"))

        self.assertTrue(result["ok"])
        self.assertTrue(result["recovery"]["clean_child_reacquired"])
        self.assertTrue(result["recovery"]["crash_child_reacquired"])
        self.assertEqual(children.calls, [("clean", 3), ("crash",)])
        self.assertEqual(pygame.display.init_count, 3)
        self.assertEqual(pygame.display.quit_count, 3)
        self.assertEqual(pygame.display.flip_count, 3)
        self.assertEqual(pygame.event.pumps, 3)
        self.assertEqual(persisted["crash_child"]["return_code"], 23)
        self.assertEqual(
            result["shell_after_crash"]["actual_video_driver"], "kmsdrm"
        )

    def test_refuses_non_kmsdrm_environment_before_display_init(self):
        with tempfile.TemporaryDirectory() as temporary:
            pygame = _Pygame()
            runner = self._runner(
                Path(temporary),
                pygame=pygame,
                environment={"SDL_VIDEODRIVER": "x11"},
            )
            with self.assertRaisesRegex(KMSDRMSerialHandoffError, "SDL_VIDEODRIVER"):
                runner.run()
        self.assertEqual(pygame.display.init_count, 0)

    def test_refuses_x11_or_wayland_transport_before_display_init(self):
        for name in ("DISPLAY", "WAYLAND_DISPLAY"):
            with self.subTest(name=name), tempfile.TemporaryDirectory() as temporary:
                pygame = _Pygame()
                runner = self._runner(
                    Path(temporary),
                    pygame=pygame,
                    environment={"SDL_VIDEODRIVER": "kmsdrm", name: "unexpected"},
                )
                with self.assertRaisesRegex(KMSDRMSerialHandoffError, "transport"):
                    runner.run()
                self.assertEqual(pygame.display.init_count, 0)

    def test_refuses_wrong_shell_driver_and_releases_display(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            pygame = _Pygame("x11")
            with self.assertRaisesRegex(KMSDRMSerialHandoffError, "expected 'kmsdrm'"):
                self._runner(root, pygame=pygame).run()
            failure = json.loads((root / "result.json").read_text(encoding="utf-8"))
        self.assertFalse(failure["ok"])
        self.assertEqual(pygame.display.quit_count, 1)

    def test_clean_child_failure_fails_closed_before_reacquire(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            pygame = _Pygame()
            with self.assertRaisesRegex(KMSDRMSerialHandoffError, "clean child"):
                self._runner(
                    root, pygame=pygame, children=_Children(clean_return=1)
                ).run()
            failure = json.loads((root / "result.json").read_text(encoding="utf-8"))
        self.assertFalse(failure["ok"])
        self.assertEqual(pygame.display.init_count, 1)
        self.assertEqual(pygame.display.quit_count, 1)

    def test_crash_child_must_use_intentional_abrupt_exit(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            pygame = _Pygame()
            with self.assertRaisesRegex(KMSDRMSerialHandoffError, "intentional abrupt-exit"):
                self._runner(
                    root, pygame=pygame, children=_Children(crash_return=1)
                ).run()
        self.assertEqual(pygame.display.init_count, 2)
        self.assertEqual(pygame.display.quit_count, 2)

    def test_malformed_crash_child_hash_is_rejected(self):
        malformed = _crash_payload()
        malformed["frame_sha256"] = "not-a-digest"
        with tempfile.TemporaryDirectory() as temporary:
            with self.assertRaisesRegex(KMSDRMSerialHandoffError, "frame hash"):
                self._runner(
                    Path(temporary), children=_Children(crash_payload=malformed)
                ).run()

    def test_missing_acknowledgement_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            runner = KMSDRMSerialHandoffRunner(
                SerialHandoffConfig(
                    output_path=Path(temporary) / "result.json",
                    acknowledge_display_takeover=False,
                ),
                environment={"SDL_VIDEODRIVER": "kmsdrm"},
                pygame_module=_Pygame(),
                child_runner=_Children(),
            )
            with self.assertRaisesRegex(KMSDRMSerialHandoffError, "acknowledgement"):
                runner.run()


if __name__ == "__main__":
    unittest.main()
