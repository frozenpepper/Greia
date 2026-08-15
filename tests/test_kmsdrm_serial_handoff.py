from __future__ import annotations

import json
import math
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
        self.color = tuple(color)


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


class _StaticImage:
    @staticmethod
    def tostring(surface, format_name):
        return b"static-shell-frame"


class _Pygame:
    FULLSCREEN = 1

    def __init__(self, driver: str = "kmsdrm", image=None):
        self.display = _Display(driver)
        self.event = _Event()
        self.image = image or _Image()
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
        self.clean_payload = clean_payload if clean_payload is not None else _clean_payload()
        self.crash_payload = crash_payload if crash_payload is not None else _crash_payload()
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
    def _runner(
        self,
        root: Path,
        *,
        pygame=None,
        children=None,
        environment=None,
        child_timeout_seconds=15.0,
        clean_child_frames=3,
    ):
        return KMSDRMSerialHandoffRunner(
            SerialHandoffConfig(
                output_path=root / "result.json",
                acknowledge_display_takeover=True,
                child_timeout_seconds=child_timeout_seconds,
                clean_child_frames=clean_child_frames,
            ),
            environment=environment
            or {
                "SDL_VIDEODRIVER": "kmsdrm",
                "DISPLAY": "",
                "XAUTHORITY": "",
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
            len(
                {
                    result["shell_initial"]["frame_sha256"],
                    result["shell_after_clean"]["frame_sha256"],
                    result["shell_after_crash"]["frame_sha256"],
                }
            ),
            3,
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

    def test_refuses_x11_or_wayland_transport_authority_before_display_init(self):
        for name, value in (
            ("DISPLAY", ":0"),
            ("XAUTHORITY", "/run/greia/xauthority"),
            ("WAYLAND_DISPLAY", "wayland-0"),
        ):
            with self.subTest(name=name), tempfile.TemporaryDirectory() as temporary:
                pygame = _Pygame()
                runner = self._runner(
                    Path(temporary),
                    pygame=pygame,
                    environment={"SDL_VIDEODRIVER": "kmsdrm", name: value},
                )
                with self.assertRaisesRegex(KMSDRMSerialHandoffError, "transport authority"):
                    runner.run()
                self.assertEqual(pygame.display.init_count, 0)

    def test_timeout_and_frame_configuration_are_strict_and_finite(self):
        bad_timeouts = (True, 0, -1, 121, math.inf, math.nan, "15")
        for value in bad_timeouts:
            with self.subTest(timeout=value), tempfile.TemporaryDirectory() as temporary:
                pygame = _Pygame()
                runner = self._runner(
                    Path(temporary),
                    pygame=pygame,
                    child_timeout_seconds=value,
                )
                with self.assertRaisesRegex(KMSDRMSerialHandoffError, "finite number"):
                    runner.run()
                self.assertEqual(pygame.display.init_count, 0)

        for value in (True, 0, 17, 3.0):
            with self.subTest(frames=value), tempfile.TemporaryDirectory() as temporary:
                pygame = _Pygame()
                runner = self._runner(
                    Path(temporary),
                    pygame=pygame,
                    clean_child_frames=value,
                )
                with self.assertRaisesRegex(KMSDRMSerialHandoffError, "integer between"):
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

    def test_clean_child_frame_count_must_match_request_exactly(self):
        payload = _clean_payload(4)
        with tempfile.TemporaryDirectory() as temporary:
            with self.assertRaisesRegex(KMSDRMSerialHandoffError, "rendered-frame evidence"):
                self._runner(
                    Path(temporary),
                    children=_Children(clean_payload=payload),
                    clean_child_frames=3,
                ).run()

    def test_clean_child_hashes_must_be_valid_and_change(self):
        malformed = _clean_payload()
        malformed["frame_sha256"] = ["1" * 64, "not-a-hash", "3" * 64]
        duplicate = _clean_payload()
        duplicate["frame_sha256"] = ["a" * 64, "a" * 64, "a" * 64]

        cases = (
            (malformed, "frame hash is invalid"),
            (duplicate, "did not change"),
        )
        for payload, message in cases:
            with self.subTest(message=message), tempfile.TemporaryDirectory() as temporary:
                with self.assertRaisesRegex(KMSDRMSerialHandoffError, message):
                    self._runner(
                        Path(temporary), children=_Children(clean_payload=payload)
                    ).run()

    def test_clean_child_surface_is_validated(self):
        payload = _clean_payload()
        payload["surface"] = {"width": 0, "height": 600}
        with tempfile.TemporaryDirectory() as temporary:
            with self.assertRaisesRegex(KMSDRMSerialHandoffError, "surface dimensions"):
                self._runner(
                    Path(temporary), children=_Children(clean_payload=payload)
                ).run()

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

    def test_static_shell_buffers_fail_recovery_evidence(self):
        with tempfile.TemporaryDirectory() as temporary:
            pygame = _Pygame(image=_StaticImage())
            with self.assertRaisesRegex(
                KMSDRMSerialHandoffError, "three distinct rendered buffers"
            ):
                self._runner(Path(temporary), pygame=pygame).run()
        self.assertEqual(pygame.display.init_count, 3)
        self.assertEqual(pygame.display.quit_count, 3)

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
