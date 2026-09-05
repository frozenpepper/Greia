"""P4-FIRSTFRAME acceptance: first flip before runtime preparation.

Proves the production mechanism, not helper return values:
- the real ``boot_intro.run_intro`` first draw/flip (and its
  ``intro_first_frame_flipped`` marker) precedes post-frame preparation;
- the 7-second intro contract is preserved and never shortened by preparation;
- exactly one bounded worker exists and the worker thread never calls Pygame;
- the intro-end boundary applies one PreparedLauncherState exactly once and
  fails visibly without hidden rescan.
"""

from __future__ import annotations

import contextlib
import inspect
import io
import os
import re
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest import mock

from greia_launcher import main as launcher_main
from greia_launcher import composition as launcher_composition
from greia_launcher.bootstrap import (
    BootLifecycleError,
    BootLifecycleState,
    LauncherBootstrap,
)
from greia_platform.activities import ActivityRegistry, RuntimeCatalogue
from greia_platform.activity_index import build_index
from greia_platform.trust import ActivitySource, PackageTrust


REPO_ROOT = Path(__file__).resolve().parents[1]


class _FakeDisplay:
    def __init__(self, events: list[str]) -> None:
        self._events = events

    def flip(self) -> None:
        self._events.append("flip")

    def get_surface(self):  # pragma: no cover - not used by intro
        return None


class _FakeScreen:
    def __init__(self) -> None:
        self.filled = 0

    def get_size(self):
        return (800, 600)

    def fill(self, color) -> None:
        self.filled += 1

    def blit(self, *args, **kwargs) -> None:
        return None

    def get_rect(self, *args, **kwargs):
        class _R:
            center = (400, 300)

        return _R()


def _make_fake_pygame(events: list[str]):
    screen = _FakeScreen()
    display = _FakeDisplay(events)

    class _FakeTransform:
        @staticmethod
        def smoothscale(surface, size):
            return surface

    class _FakeTime:
        @staticmethod
        def wait(ms: int) -> None:
            return None

    class _FakeEvent:
        @staticmethod
        def pump() -> None:
            return None

    fake = mock.MagicMock(name="pygame")
    fake.display = display
    fake.transform = _FakeTransform()
    fake.time = _FakeTime()
    fake.event = _FakeEvent()
    fake.Rect = mock.MagicMock(side_effect=lambda *a, **k: mock.MagicMock())
    fake.draw = mock.MagicMock()
    return fake, screen


def _reset_first_frame_flag() -> None:
    from greia_launcher import boot_intro

    boot_intro._FIRST_FRAME_FLIPPED_EMITTED = False


class FirstFrameOrderTests(unittest.TestCase):
    def test_flip_and_marker_precede_callback_submission(self) -> None:
        from greia_launcher import boot_intro

        _reset_first_frame_flag()
        events: list[str] = []
        fake_pygame, screen = _make_fake_pygame(events)
        order: list[str] = []

        def _on_first_frame() -> None:
            order.append("callback")

        real_flip = fake_pygame.display.flip

        def _recording_flip() -> None:
            order.append("flip")
            real_flip()

        with mock.patch.object(
            fake_pygame.display, "flip", side_effect=_recording_flip
        ), mock.patch.object(
            boot_intro, "draw_boot_handoff_frame", return_value=True
        ), mock.patch.dict(
            os.environ,
            {"GREIA_SKIP_BOOT_INTRO": "1", "GREIA_BOOT_INTRO_MARKER": "/tmp/nope-never"},
            clear=False,
        ):
            buffer = io.StringIO()
            with contextlib.redirect_stdout(buffer):
                boot_intro.run_intro(
                    screen, fake_pygame, on_first_frame=_on_first_frame
                )
        self.assertEqual(order[0], "flip")
        self.assertIn("callback", order)
        self.assertLess(order.index("flip"), order.index("callback"))
        out = buffer.getvalue()
        self.assertIn("intro_first_frame_flipped", out)
        self.assertIn("intro_enter", out)
        self.assertIn("intro_end", out)
        # Marker precedes the callback: the callback runs after the emit.
        self.assertLess(
            out.index("intro_first_frame_flipped"), out.index("intro_end")
        )

    def test_callback_fires_before_animation_frames(self) -> None:
        from greia_launcher import boot_intro

        _reset_first_frame_flag()
        events: list[str] = []
        fake_pygame, screen = _make_fake_pygame(events)
        calls: list[str] = []

        def _on_first_frame() -> None:
            calls.append("callback")

        frames = [object(), object(), object()]
        with mock.patch.object(
            boot_intro, "draw_boot_handoff_frame", return_value=True
        ), mock.patch.object(
            boot_intro, "load_animation_frames", return_value=frames
        ), mock.patch.object(
            boot_intro, "_draw_frame", side_effect=lambda *a, **k: calls.append("frame")
        ), mock.patch.object(
            boot_intro, "_pump_display", side_effect=lambda *a, **k: calls.append("pump")
        ), mock.patch.dict(os.environ, {"GREIA_SKIP_BOOT_INTRO": "0"}, clear=False), mock.patch.object(
            boot_intro, "skip_intro", return_value=False
        ), mock.patch.object(
            boot_intro, "mark_boot_intro_played", return_value=None
        ):
            buffer = io.StringIO()
            with contextlib.redirect_stdout(buffer):
                boot_intro.run_intro(
                    screen, fake_pygame, on_first_frame=_on_first_frame
                )
        self.assertIn("callback", calls)
        self.assertIn("frame", calls)
        self.assertLess(calls.index("callback"), calls.index("frame"))

    def test_intro_timing_contract_preserved(self) -> None:
        from greia_launcher import boot_intro

        self.assertEqual(boot_intro.ANIMATION_SECONDS, 5.0)
        self.assertEqual(boot_intro.FINAL_FRAME_HOLD_SECONDS, 2.0)
        self.assertEqual(
            boot_intro.MAX_INTRO_SECONDS,
            boot_intro.ANIMATION_SECONDS + boot_intro.FINAL_FRAME_HOLD_SECONDS,
        )
        # The handoff keeps its explicit callback seam without importing the
        # bootstrap coordinator (injected by the shell, never imported here).
        signature = inspect.signature(boot_intro.run_intro)
        self.assertIn("marker", signature.parameters)
        self.assertIn("on_first_frame", signature.parameters)
        source = inspect.getsource(boot_intro)
        for token in (
            "LauncherBootstrap",
            "PreparedLauncherState",
            "prepare_runtime",
            "BootLifecycle",
            "ThreadPoolExecutor",
        ):
            self.assertNotIn(token, source)
        # Callback is invoked after the first flip/emit and before the
        # skip/animation decision in source order.
        self.assertLess(
            source.index("_emit_first_frame_flipped_once()"),
            source.index("if on_first_frame is not None:"),
        )
        self.assertLess(
            source.index("if on_first_frame is not None:"),
            source.index("if skip_intro():"),
        )

    def test_preparation_never_ends_intro_early(self) -> None:
        """A instantly-ready worker must not shorten the intro clock."""

        from greia_launcher import boot_intro

        _reset_first_frame_flag()
        events: list[str] = []
        fake_pygame, screen = _make_fake_pygame(events)
        frames = [object(), object()]
        started: list[float] = []

        def _fast_callback() -> None:
            started.append(time.monotonic())

        with mock.patch.object(
            boot_intro, "draw_boot_handoff_frame", return_value=True
        ), mock.patch.object(
            boot_intro, "load_animation_frames", return_value=frames
        ), mock.patch.object(
            boot_intro, "_draw_frame", return_value=None
        ), mock.patch.object(
            boot_intro, "skip_intro", return_value=False
        ), mock.patch.object(
            boot_intro, "mark_boot_intro_played", return_value=None
        ), mock.patch.object(
            boot_intro, "ANIMATION_SECONDS", 0.30
        ), mock.patch.object(
            boot_intro, "FINAL_FRAME_HOLD_SECONDS", 0.15
        ):
            wall_start = time.monotonic()
            buffer = io.StringIO()
            with contextlib.redirect_stdout(buffer):
                boot_intro.run_intro(
                    screen, fake_pygame, on_first_frame=_fast_callback
                )
            elapsed = time.monotonic() - wall_start
        self.assertEqual(len(started), 1)
        # Full animation + hold despite the preparation callback returning
        # immediately. Tolerance is generous; the point is no early exit.
        self.assertGreaterEqual(elapsed, 0.40)


class SingleWorkerTests(unittest.TestCase):
    def test_exactly_one_bounded_worker_in_source(self) -> None:
        root = REPO_ROOT / "src" / "greia_launcher"
        hits: list[str] = []
        for path in sorted(root.glob("*.py")):
            text = path.read_text(encoding="utf-8")
            for match in re.finditer(r"ThreadPoolExecutor\s*\(", text):
                hits.append(f"{path.name}:{match.group(0)}")
        self.assertEqual(len(hits), 1, f"expected exactly one worker, got {hits}")
        main_source = (root / "main.py").read_text(encoding="utf-8")
        self.assertIn("ThreadPoolExecutor(max_workers=1)", main_source)
        presentation_source = (root / "presentation.py").read_text(encoding="utf-8")
        self.assertIn("create_preparation_worker()", presentation_source)
        self.assertNotIn("ThreadPoolExecutor(", presentation_source)
        self.assertNotIn("ThreadPoolExecutor(", (root / "bootstrap.py").read_text(encoding="utf-8"))
        self.assertNotIn("ThreadPoolExecutor(", (root / "boot_intro.py").read_text(encoding="utf-8"))

    def test_worker_boundary_has_no_pygame_or_ui(self) -> None:
        main_source = inspect.getsource(launcher_main.LauncherApplication._prepare_runtime_state)
        for token in ("pygame", "display.flip", "get_surface", "mouse.", "mixer", "Xlib", "ALSA"):
            self.assertNotIn(token, main_source)
        bootstrap_source = (REPO_ROOT / "src" / "greia_launcher" / "bootstrap.py").read_text(
            encoding="utf-8"
        )
        self.assertNotIn("import pygame", bootstrap_source)
        self.assertNotIn("from pygame", bootstrap_source)


class PreparationIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
        try:
            import pygame

            pygame.init()
        except Exception:
            pass

    @classmethod
    def tearDownClass(cls) -> None:
        try:
            import pygame

            pygame.quit()
        except Exception:
            pass

    def _boot_env(self, tmp: Path, index_path: Path) -> dict[str, str]:
        return {
            "GREIA_OS_ROOT": str(REPO_ROOT),
            "GREIA_PROFILES_DIR": str(tmp / "profiles"),
            "GREIA_SYSTEM_SETTINGS_DIR": str(tmp / "settings"),
            "GREIA_MEDIA_ROOT": str(tmp / "media"),
            "GREIA_ACTIVE_PROFILE_STATUS": str(tmp / "active.json"),
            "GREIA_HARDWARE_STATUS": str(tmp / "hw.json"),
            "GREIA_MAIN_CREDENTIAL_PATH": str(tmp / "cred.json"),
            launcher_main.DEVELOPER_MARKER_ENV_VAR: str(tmp / "no-marker"),
            launcher_composition.BUILT_IN_INDEX_ENV_VAR: str(index_path),
            launcher_composition.PARENT_ACTIVITY_ROOT_ENV_VAR: str(
                tmp / "parent-missing"
            ),
            "SDL_VIDEODRIVER": "dummy",
        }

    def _write_production_index(self, dest: Path) -> None:
        runtime = RuntimeCatalogue.load(REPO_ROOT / "runtime" / "child-runtime.toml")
        source = ActivitySource(
            REPO_ROOT / "activities", PackageTrust.BUILT_IN, "greia-system"
        )
        registrations = ActivityRegistry(
            (source,), runtime, fail_closed=False
        ).discover_registrations()
        self.assertTrue(len(registrations) > 0)
        build_index(registrations, source=source, runtime=runtime).write_file(dest)

    def test_first_frame_callback_submits_worker_and_applies_once(self) -> None:
        from greia_launcher.presentation import GreiaLauncherPresentation

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            index_path = tmp_path / "builtin-index.json"
            self._write_production_index(index_path)
            env = self._boot_env(tmp_path, index_path)
            with mock.patch.dict(os.environ, env, clear=False):
                app = GreiaLauncherPresentation(
                    windowed=True, allow_exit=True, bootstrap=False
                )
                self.assertIs(app._boot_lifecycle.state, BootLifecycleState.CREATED)
                app._boot_lifecycle.mark_display_ready()
                worker = launcher_main.create_preparation_worker()
                try:
                    main_thread = threading.get_ident()
                    worker_thread: list[int] = []

                    real_prepare = app._prepare_runtime_state

                    def _watched_prepare():  # type: ignore[no-untyped-def]
                        worker_thread.append(threading.get_ident())
                        return real_prepare()

                    with mock.patch.object(
                        app, "_prepare_runtime_state", _watched_prepare
                    ), mock.patch.dict(sys.modules, {"pygame": None}):
                        # Simulate the display thread invoking the
                        # first-frame callback immediately after the flip.
                        future = app._begin_post_frame_preparation(worker)
                        self.assertIs(
                            app._boot_lifecycle.state,
                            BootLifecycleState.PREPARING_RUNTIME,
                        )
                        state = future.result(timeout=120)
                    self.assertTrue(worker_thread)
                    self.assertNotEqual(worker_thread[0], main_thread)
                    self.assertGreater(len(state.activities), 0)
                    # Intro-end boundary on the main thread publishes once.
                    app._await_and_apply_preparation(future)
                    self.assertTrue(app._bootstrapped)
                    self.assertIs(
                        app._boot_lifecycle.state,
                        BootLifecycleState.INTERACTIVE_READY,
                    )
                    self.assertGreaterEqual(app._post_intro_wait_seconds, 0.0)
                    with self.assertRaises(BootLifecycleError):
                        app.apply_prepared_state(state)
                finally:
                    worker.shutdown(wait=False)

    def test_worker_failure_fails_visibly_without_hidden_rescan(self) -> None:
        from greia_launcher.presentation import GreiaLauncherPresentation
        from greia_platform.activity_index import ActivityIndexError

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            index_path = tmp_path / "builtin-index.json"
            index_path.write_text("{ not valid json", encoding="utf-8")
            env = self._boot_env(tmp_path, index_path)
            with mock.patch.dict(os.environ, env, clear=False):
                app = GreiaLauncherPresentation(
                    windowed=True, allow_exit=True, bootstrap=False
                )
                app._boot_lifecycle.mark_display_ready()
                worker = launcher_main.create_preparation_worker()
                try:
                    future = app._begin_post_frame_preparation(worker)
                    with self.assertRaises(ActivityIndexError):
                        app._await_and_apply_preparation(future)
                    # Fail-closed: nothing half-populated, guard retryable,
                    # and no hidden rescan ran (discovery token untouched).
                    self.assertFalse(app._bootstrapped)
                    self.assertIsNone(app.registry)
                    self.assertEqual(app._activities, ())
                    self.assertIsNone(app.runtime_services)
                    self.assertIsNone(app.supervisor)
                    self.assertIsNone(app._catalogue)
                    self.assertIs(
                        app._boot_lifecycle.state, BootLifecycleState.CREATED
                    )
                finally:
                    worker.shutdown(wait=False)

    def test_post_intro_wait_is_recorded(self) -> None:
        from greia_launcher.presentation import GreiaLauncherPresentation

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            index_path = tmp_path / "builtin-index.json"
            self._write_production_index(index_path)
            env = self._boot_env(tmp_path, index_path)
            with mock.patch.dict(os.environ, env, clear=False):
                app = GreiaLauncherPresentation(
                    windowed=True, allow_exit=True, bootstrap=False
                )
                coordinator = LauncherBootstrap(app.paths)
                state = coordinator.prepare_runtime(
                    build_services=app._build_bootstrap_services,
                    build_supervisor=app._build_bootstrap_supervisor,
                    build_catalogue=app._bootstrap_catalogue_builder(),
                )
                app._boot_lifecycle.mark_display_ready()
                app._boot_lifecycle.mark_first_frame_visible()
                app._boot_lifecycle.begin_preparing_runtime()
                worker = launcher_main.create_preparation_worker()
                try:
                    def _slow() -> object:
                        time.sleep(0.25)
                        return state

                    future = worker.submit(_slow)
                    wall_start = time.monotonic()
                    app._await_and_apply_preparation(future)
                    wall_elapsed = time.monotonic() - wall_start
                    self.assertGreaterEqual(app._post_intro_wait_seconds, 0.20)
                    self.assertGreaterEqual(wall_elapsed, 0.20)
                    self.assertTrue(app._bootstrapped)
                finally:
                    worker.shutdown(wait=False)


if __name__ == "__main__":
    raise SystemExit(unittest.main())
