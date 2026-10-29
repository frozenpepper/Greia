"""P4-BOOTSTRAP acceptance: coordinator, lifecycle guard, atomic apply.

Covers what the earlier T37 tests do not: the explicit ``LauncherBootstrap``
coordinator with its immutable ``PreparedLauncherState``, the guarded boot
lifecycle (CREATED → DISPLAY_READY → FIRST_FRAME_VISIBLE → PREPARING_RUNTIME
→ INTERACTIVE_READY → RUNNING), fail-closed exactly-once publication,
cheap-construction source assertions, a pygame-free preparation proof, and
the untouched intro contract (no display/timing change in this task).
"""

from __future__ import annotations

import contextlib
import dataclasses
import inspect
import io
import os
import re
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

from greia_launcher import main as launcher_main
from greia_launcher import composition as launcher_composition
from greia_launcher.bootstrap import (
    BootLifecycleError,
    BootLifecycleGuard,
    BootLifecycleState,
    LauncherBootstrap,
    PreparedLauncherState,
)
from greia_platform.activities import (
    ActivityRegistry,
    RuntimeCatalogue,
)
from greia_platform.activity_index import build_index
from greia_platform.trust import ActivitySource, PackageTrust


REPO_ROOT = Path(__file__).resolve().parents[1]

BOOT_MARKER_ORDER = (
    "launcher_construct_begin",
    "activity_sources_begin",
    "activity_sources_end",
    "activity_discover_begin",
    "activity_discover_end",
    "activity_runtime_build_begin",
    "activity_runtime_build_end",
    "history_prepare_begin",
    "history_prepare_end",
    "launcher_interactive_ready",
    "launcher_construct_end",
)


def _capture_markers(callable_obj, *args, **kwargs):
    buffer = io.StringIO()
    with contextlib.redirect_stdout(buffer):
        result = callable_obj(*args, **kwargs)
    names = [
        line.split("event=")[1].split()[0]
        for line in buffer.getvalue().splitlines()
        if line.startswith("GREIA_BOOT event=")
    ]
    return result, names


class BootLifecycleGuardTests(unittest.TestCase):
    def test_full_async_chain_is_legal(self) -> None:
        guard = BootLifecycleGuard()
        self.assertIs(guard.state, BootLifecycleState.CREATED)
        guard.mark_display_ready()
        self.assertIs(guard.state, BootLifecycleState.DISPLAY_READY)
        guard.mark_first_frame_visible()
        self.assertIs(guard.state, BootLifecycleState.FIRST_FRAME_VISIBLE)
        guard.begin_preparing_runtime()
        self.assertIs(guard.state, BootLifecycleState.PREPARING_RUNTIME)
        guard.mark_interactive_ready()
        self.assertIs(guard.state, BootLifecycleState.INTERACTIVE_READY)
        guard.mark_running()
        self.assertIs(guard.state, BootLifecycleState.RUNNING)

    def test_transitional_sync_edge_is_legal(self) -> None:
        guard = BootLifecycleGuard()
        guard.begin_preparing_runtime()
        guard.mark_interactive_ready()
        guard.mark_running()
        self.assertIs(guard.state, BootLifecycleState.RUNNING)

    def test_illegal_transitions_fail_loudly(self) -> None:
        illegal = [
            (BootLifecycleState.CREATED, BootLifecycleState.FIRST_FRAME_VISIBLE),
            (BootLifecycleState.CREATED, BootLifecycleState.INTERACTIVE_READY),
            (BootLifecycleState.CREATED, BootLifecycleState.RUNNING),
            (BootLifecycleState.DISPLAY_READY, BootLifecycleState.CREATED),
            (BootLifecycleState.DISPLAY_READY, BootLifecycleState.PREPARING_RUNTIME),
            (BootLifecycleState.DISPLAY_READY, BootLifecycleState.INTERACTIVE_READY),
            (BootLifecycleState.FIRST_FRAME_VISIBLE, BootLifecycleState.DISPLAY_READY),
            (BootLifecycleState.FIRST_FRAME_VISIBLE, BootLifecycleState.INTERACTIVE_READY),
            (BootLifecycleState.FIRST_FRAME_VISIBLE, BootLifecycleState.RUNNING),
            (BootLifecycleState.PREPARING_RUNTIME, BootLifecycleState.CREATED),
            (BootLifecycleState.PREPARING_RUNTIME, BootLifecycleState.RUNNING),
            (
                BootLifecycleState.PREPARING_RUNTIME,
                BootLifecycleState.FIRST_FRAME_VISIBLE,
            ),
            (BootLifecycleState.INTERACTIVE_READY, BootLifecycleState.PREPARING_RUNTIME),
            (BootLifecycleState.INTERACTIVE_READY, BootLifecycleState.CREATED),
            (BootLifecycleState.RUNNING, BootLifecycleState.INTERACTIVE_READY),
            (BootLifecycleState.RUNNING, BootLifecycleState.CREATED),
        ]
        for start, target in illegal:
            with self.subTest(start=start.value, target=target.value):
                guard = BootLifecycleGuard(initial=start)
                with self.assertRaises(BootLifecycleError):
                    guard.transition(target)
                # Failed transition leaves the guard exactly where it was.
                self.assertIs(guard.state, start)

    def test_reset_only_from_preparing(self) -> None:
        guard = BootLifecycleGuard()
        guard.begin_preparing_runtime()
        guard.reset_to_created()
        self.assertIs(guard.state, BootLifecycleState.CREATED)
        for start in (
            BootLifecycleState.CREATED,
            BootLifecycleState.DISPLAY_READY,
            BootLifecycleState.FIRST_FRAME_VISIBLE,
            BootLifecycleState.INTERACTIVE_READY,
            BootLifecycleState.RUNNING,
        ):
            with self.subTest(start=start.value):
                reset_guard = BootLifecycleGuard(initial=start)
                with self.assertRaises(BootLifecycleError):
                    reset_guard.reset_to_created()


class BootstrapCoordinatorTests(unittest.TestCase):
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

    def _write_production_index(self, dest: Path) -> int:
        runtime = RuntimeCatalogue.load(REPO_ROOT / "runtime" / "child-runtime.toml")
        source = ActivitySource(
            REPO_ROOT / "activities", PackageTrust.BUILT_IN, "greia-system"
        )
        registrations = ActivityRegistry(
            (source,), runtime, fail_closed=False
        ).discover_registrations()
        self.assertTrue(len(registrations) > 0)
        build_index(registrations, source=source, runtime=runtime).write_file(dest)
        return len(registrations)

    def test_child_shell_coordinator_single_build_and_marker_order(self) -> None:
        from greia_launcher.child_shell import GreiaChildShell

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            index_path = tmp_path / "builtin-index.json"
            expected_count = self._write_production_index(index_path)
            env = self._boot_env(tmp_path, index_path)
            with mock.patch.dict(os.environ, env, clear=False):
                import greia_launcher.bootstrap as bootstrap_module
                import greia_launcher.main as main_module
                import greia_launcher.presentation as presentation_module

                real_build = main_module.build_launcher_runtime_services
                real_catalogue = (
                    presentation_module.ActivityCatalogue.from_activities
                )
                real_compose = launcher_composition.compose_boot_content
                runtime_builds: list[str] = []
                catalogue_builds: list[str] = []
                compose_calls: list[str] = []

                def _counting_build(*args: object, **kwargs: object):  # type: ignore[no-untyped-def]
                    runtime_builds.append("services")
                    return real_build(*args, **kwargs)  # type: ignore[arg-type]

                def _counting_catalogue(*args: object, **kwargs: object):  # type: ignore[no-untyped-def]
                    catalogue_builds.append("catalogue")
                    return real_catalogue(*args, **kwargs)  # type: ignore[arg-type]

                def _counting_compose(*args: object, **kwargs: object):  # type: ignore[no-untyped-def]
                    compose_calls.append("compose")
                    return real_compose(*args, **kwargs)  # type: ignore[arg-type]

                with (
                    mock.patch.object(
                        main_module,
                        "build_launcher_runtime_services",
                        _counting_build,
                    ),
                    mock.patch.object(
                        presentation_module.ActivityCatalogue,
                        "from_activities",
                        _counting_catalogue,
                    ),
                    mock.patch.object(
                        bootstrap_module,
                        "compose_boot_content",
                        _counting_compose,
                    ),
                    mock.patch.object(
                        GreiaChildShell,
                        "_configure_parent_package_source",
                    ) as configure_spy,
                ):
                    app = GreiaChildShell(
                        windowed=True, allow_exit=True, bootstrap=False
                    )
                    self.assertIs(
                        app._boot_lifecycle.state, BootLifecycleState.CREATED
                    )
                    _, markers = _capture_markers(app.bootstrap)
                self.assertEqual(tuple(markers), BOOT_MARKER_ORDER)
                self.assertEqual(compose_calls, ["compose"])
                self.assertEqual(runtime_builds, ["services"])
                self.assertEqual(catalogue_builds, ["catalogue"])
                self.assertEqual(configure_spy.call_count, 0)
                self.assertTrue(app._bootstrapped)
                self.assertIs(
                    app._boot_lifecycle.state, BootLifecycleState.INTERACTIVE_READY
                )
                self.assertEqual(len(app._activities), expected_count)
                self.assertIsNotNone(app.supervisor)
                self.assertIsNotNone(app._catalogue)
                self.assertFalse(app._catalogue_error)
                # One authoritative registration set: single registry, single
                # runtime service set, single presentation catalogue.
                self.assertIs(app.registry, app.registry)
                source_ids = [s.source_id for s in app.registry._sources]
                self.assertIn("greia-parent-package-service", source_ids)
                self.assertIn(launcher_main.BUILT_IN_SOURCE_ID, source_ids)
                # Running state is reachable only through the guard.
                app._enter_running_state()
                self.assertIs(app._boot_lifecycle.state, BootLifecycleState.RUNNING)
                # Second bootstrap is a no-op, not a second composition.
                with mock.patch.object(
                    bootstrap_module,
                    "compose_boot_content",
                    side_effect=AssertionError("must bootstrap exactly once"),
                ):
                    app.bootstrap()

    def test_prepare_returns_immutable_state_without_touching_app(self) -> None:
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
                self.assertIsInstance(state, PreparedLauncherState)
                # Immutable: frozen dataclass rejects reassignment.
                with self.assertRaises(dataclasses.FrozenInstanceError):
                    state.parent_degraded = not state.parent_degraded  # type: ignore[misc]
                # Coordinator mutated nothing live: the app is still an
                # untouched pre-frame shell.
                self.assertFalse(app._bootstrapped)
                self.assertIsNone(app.registry)
                self.assertEqual(app._activities, ())
                self.assertIsNone(app.runtime_services)
                self.assertIsNone(app.supervisor)
                self.assertIsNone(app._catalogue)
                self.assertIs(app._boot_lifecycle.state, BootLifecycleState.CREATED)
                # The sealed set is complete: one registry, one service set,
                # one catalogue, history-derived recovery evidence.
                self.assertEqual(len(state.activities), len(state.registrations))
                self.assertGreater(len(state.activities), 0)
                self.assertIsNotNone(state.runtime_services)
                self.assertIsNotNone(state.supervisor)
                self.assertIsNotNone(state.catalogue)
                self.assertIsInstance(state.history_recovery_failures, frozenset)

    def test_installed_generation_pointer_selects_focus_and_chrome(self) -> None:
        from greia_launcher import installed_root
        from greia_launcher.child_shell import GreiaChildShell
        from greia_launcher.shell_window_legacy_x import LegacyXShellWindowController

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            index_path = tmp_path / "builtin-index.json"
            self._write_production_index(index_path)
            link = tmp_path / "greia-os"
            link.symlink_to(REPO_ROOT, target_is_directory=True)
            env = self._boot_env(tmp_path, index_path)
            env["GREIA_OS_ROOT"] = str(link)
            with mock.patch.object(installed_root, "INSTALLED_APPLICATION_ROOT", link), \
                 mock.patch.dict(os.environ, env, clear=False):
                app = GreiaChildShell(windowed=True, allow_exit=True, bootstrap=False)
                state = LauncherBootstrap(app.paths).prepare_runtime(
                    build_services=app._build_bootstrap_services,
                    build_supervisor=app._build_bootstrap_supervisor,
                    build_catalogue=app._bootstrap_catalogue_builder(),
                )
                self.assertTrue(state.installed)
                self.assertIsInstance(state.shell_window_backend, LegacyXShellWindowController)
                self.assertTrue(state.supervisor._sandbox_required())
                self.assertIsNotNone(state.supervisor._system_chrome_coordinator)

    def test_prepare_performs_no_pygame_work(self) -> None:
        """Sensitivity control: preparation must survive without pygame."""

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            index_path = tmp_path / "builtin-index.json"
            self._write_production_index(index_path)
            env = self._boot_env(tmp_path, index_path)
            with mock.patch.dict(os.environ, env, clear=False):
                app = launcher_main.LauncherApplication(
                    windowed=True, allow_exit=True, bootstrap=False
                )
                coordinator = LauncherBootstrap(app.paths)
                with mock.patch.dict(sys.modules, {"pygame": None}):
                    state = coordinator.prepare_runtime(
                        build_services=app._build_bootstrap_services,
                        build_supervisor=app._build_bootstrap_supervisor,
                        build_catalogue=app._bootstrap_catalogue_builder(),
                    )
                self.assertGreater(len(state.activities), 0)

    def test_constructors_are_cheap_source_assertion(self) -> None:
        """Constructors must contain no discovery/composition/IO/subprocess."""

        from greia_launcher.presentation import GreiaLauncherPresentation

        forbidden = (
            r"compose_boot_content",
            r"RuntimeCatalogue\.load",
            r"ProfileStore\.load",
            r"ensure_initialized",
            r"recover_unfinished",
            r"build_launcher_runtime_services",
            r"from_activities",
            r"ActivityIndexLoader",
            r"load_built_in_registrations",
            r"load_parent_registrations",
            r"validate_registration",
            r"discover_registrations",
            r"\.discover\b",
            r"discover\(",
            r"package_digest",
            r"subprocess",
            r"Popen",
            r"rglob",
            r"os\.walk",
            r"\bwalk\b\(",
            r"pygame",
            r"xrandr",
            r"xinput",
        )
        for cls in (launcher_main.LauncherApplication, GreiaLauncherPresentation):
            with self.subTest(cls=cls.__name__):
                source = inspect.getsource(cls.__init__)
                hits = [expr for expr in forbidden if re.search(expr, source)]
                self.assertEqual(hits, [], f"cheap constructor violated by {hits}")

    def test_constructors_perform_no_heavy_work_and_are_bounded(self) -> None:
        from greia_launcher.child_shell import GreiaChildShell
        from greia_launcher.presentation import GreiaLauncherPresentation
        from greia_platform.audio import AudioService

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            env = self._boot_env(tmp_path, tmp_path / "no-index.json")
            with mock.patch.dict(os.environ, env, clear=False):
                with mock.patch.object(
                    launcher_composition,
                    "compose_boot_content",
                    side_effect=AssertionError("constructor must not compose"),
                ), mock.patch.object(
                    AudioService,
                    "load",
                    side_effect=AssertionError("constructor must not load audio"),
                ):
                    started = time.monotonic()
                    constructed = []
                    for _ in range(2):
                        constructed.append(
                            launcher_main.LauncherApplication(
                                windowed=True, allow_exit=True, bootstrap=False
                            )
                        )
                        constructed.append(
                            GreiaLauncherPresentation(
                                windowed=True, allow_exit=True, bootstrap=False
                            )
                        )
                        constructed.append(
                            GreiaChildShell(
                                windowed=True, allow_exit=True, bootstrap=False
                            )
                        )
                    elapsed = time.monotonic() - started
                # Measurable and bounded: six full shell constructions stay
                # far below any budget that real discovery would consume.
                self.assertLess(elapsed, 10.0)
                for app in constructed:
                    self.assertFalse(app._bootstrapped)
                    self.assertIsNone(app.registry)
                    self.assertEqual(app._activities, ())
                    self.assertIsNone(app.runtime_services)
                    self.assertIsNone(app.supervisor)
                    self.assertIs(
                        app._boot_lifecycle.state, BootLifecycleState.CREATED
                    )

    def test_preparation_failure_is_controlled_without_half_state(self) -> None:
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
                buffer = io.StringIO()
                with contextlib.redirect_stdout(buffer):
                    with self.assertRaises(ActivityIndexError):
                        app.bootstrap()
                names = [
                    line.split("event=")[1].split()[0]
                    for line in buffer.getvalue().splitlines()
                    if line.startswith("GREIA_BOOT event=")
                ]
                self.assertIn("launcher_construct_begin", names)
                self.assertIn("launcher_construct_end", names)
                # Fail-closed: nothing half-populated is observable and the
                # guard is back at CREATED so the failure is retryable.
                self.assertFalse(app._bootstrapped)
                self.assertIsNone(app.registry)
                self.assertEqual(app._activities, ())
                self.assertIsNone(app.runtime_services)
                self.assertIsNone(app.supervisor)
                self.assertIsNone(app._catalogue)
                self.assertIs(app._boot_lifecycle.state, BootLifecycleState.CREATED)
                # Retry on the same instance succeeds once the index is valid.
                self._write_production_index(index_path)
                app.bootstrap()
                self.assertTrue(app._bootstrapped)
                self.assertIs(
                    app._boot_lifecycle.state, BootLifecycleState.INTERACTIVE_READY
                )

    def test_prepared_state_consumed_exactly_once(self) -> None:
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
                app.bootstrap()
                coordinator = LauncherBootstrap(app.paths)
                second = coordinator.prepare_runtime(
                    build_services=app._build_bootstrap_services,
                    build_supervisor=app._build_bootstrap_supervisor,
                    build_catalogue=app._bootstrap_catalogue_builder(),
                )
                with self.assertRaises(BootLifecycleError):
                    app.apply_prepared_state(second)
                # The first publication is untouched by the rejected apply.
                self.assertTrue(app._bootstrapped)
                self.assertIs(
                    app._boot_lifecycle.state, BootLifecycleState.INTERACTIVE_READY
                )
                # Applying without preparing is equally loud.
                fresh = GreiaLauncherPresentation(
                    windowed=True, allow_exit=True, bootstrap=False
                )
                with self.assertRaises(BootLifecycleError):
                    fresh.apply_prepared_state(second)
                with self.assertRaises(BootLifecycleError):
                    fresh.apply_prepared_state("not-a-state")  # type: ignore[arg-type]
                # Unbootstrapped running entry is loud, never silent drift.
                with self.assertRaises(BootLifecycleError):
                    fresh._enter_running_state()

    def test_trusted_fallback_keeps_trusted_supervisor(self) -> None:
        from greia_launcher.trusted_chrome_supervisor import (
            TrustedChromeActivitySupervisor,
        )
        from greia_launcher.trusted_presentation import (
            TrustedGreiaLauncherPresentation,
        )

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            index_path = tmp_path / "builtin-index.json"
            self._write_production_index(index_path)
            env = self._boot_env(tmp_path, index_path)
            with mock.patch.dict(os.environ, env, clear=False):
                app = TrustedGreiaLauncherPresentation(
                    windowed=True, allow_exit=True, bootstrap=False
                )
                app.bootstrap()
                self.assertTrue(app._bootstrapped)
                self.assertIsInstance(
                    app.supervisor, TrustedChromeActivitySupervisor
                )
                self.assertIsNotNone(app._catalogue)
                self.assertIs(
                    app._boot_lifecycle.state, BootLifecycleState.INTERACTIVE_READY
                )

    def test_intro_contract_untouched(self) -> None:
        from greia_launcher import boot_intro

        self.assertEqual(boot_intro.ANIMATION_SECONDS, 5.0)
        self.assertEqual(boot_intro.FINAL_FRAME_HOLD_SECONDS, 2.0)
        self.assertEqual(
            boot_intro.TARGET_INTRO_SECONDS, boot_intro.ANIMATION_SECONDS
        )
        self.assertEqual(
            boot_intro.MAX_INTRO_SECONDS,
            boot_intro.ANIMATION_SECONDS + boot_intro.FINAL_FRAME_HOLD_SECONDS,
        )
        source = inspect.getsource(boot_intro)
        for token in (
            "LauncherBootstrap",
            "PreparedLauncherState",
            "prepare_runtime",
            "BootLifecycle",
        ):
            self.assertNotIn(token, source)
        signature = inspect.signature(boot_intro.run_intro)
        self.assertIn("marker", signature.parameters)


if __name__ == "__main__":
    raise SystemExit(unittest.main())
