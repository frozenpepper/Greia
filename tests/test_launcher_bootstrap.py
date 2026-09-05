"""Explicit bootstrap without constructor side effects (T37).

The real boot construction path owns one-pass composition in explicit
bootstrap code: object construction performs no Activity discovery, and the
normal (indexed) boot performs no recursive tree validation or package
digest recomputation. Activation-time proof (index digest) and the launch
authority path are preserved.
"""

from __future__ import annotations

import contextlib
import io
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from greia_launcher import main as launcher_main
from greia_launcher import composition as launcher_composition
from greia_platform.activities import (
    ActivityRegistry,
    RuntimeCatalogue,
)
from greia_platform.activity_index import build_index
from greia_platform.trust import ActivitySource, PackageTrust


REPO_ROOT = Path(__file__).resolve().parents[1]


class _NoValidation:
    """Fail if package validation or digest recomputation runs."""

    def __init__(self) -> None:
        self._patches: list = []
        self._forbidden: tuple = ()

    def __enter__(self) -> "_NoValidation":
        import greia_platform.activities as activities

        self._forbidden = (
            mock.patch.object(
                activities.ActivityRegistry,
                "validate_registration",
                side_effect=AssertionError("must not re-validate"),
            ),
            mock.patch.object(
                activities.ActivityRegistry,
                "discover_registrations",
                side_effect=AssertionError("must not re-discover"),
            ),
            mock.patch.object(
                activities.ActivityRegistry,
                "_validate_tree",
                side_effect=AssertionError("must not re-validate trees"),
            ),
            mock.patch(
                "greia_platform.activities.package_digest",
                side_effect=AssertionError("must not recompute digests"),
            ),
        )
        self._patches = [patcher.__enter__() for patcher in self._forbidden]
        return self

    def __exit__(self, *args: object) -> None:
        for patcher in self._forbidden:
            patcher.__exit__(None, None, None)
        self._patches.clear()


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


class LauncherBootstrapTests(unittest.TestCase):
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
        repo_root = REPO_ROOT
        return {
            "GREIA_OS_ROOT": str(repo_root),
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

    def _write_production_index(self, dest: Path) -> tuple[str, int]:
        """Index the real built-in tree (setup only); returns (digest, count)."""

        runtime = RuntimeCatalogue.load(REPO_ROOT / "runtime" / "child-runtime.toml")
        source = ActivitySource(
            REPO_ROOT / "activities", PackageTrust.BUILT_IN, "greia-system"
        )
        registrations = ActivityRegistry(
            (source,), runtime, fail_closed=False
        ).discover_registrations()
        self.assertTrue(len(registrations) > 0)
        build_index(registrations, source=source, runtime=runtime).write_file(dest)
        return registrations[0].package_digest, len(registrations)

    def test_constructor_performs_no_activity_discovery(self) -> None:
        from greia_launcher.presentation import GreiaLauncherPresentation

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            env = self._boot_env(tmp_path, tmp_path / "no-index.json")
            with mock.patch.dict(os.environ, env, clear=False):
                with mock.patch.object(
                    launcher_composition,
                    "compose_boot_content",
                    side_effect=AssertionError("constructor must not compose"),
                ), mock.patch.object(
                    ActivityRegistry,
                    "discover",
                    side_effect=AssertionError("constructor must not discover"),
                ), mock.patch.object(
                    ActivityRegistry,
                    "discover_registrations",
                    side_effect=AssertionError("constructor must not discover"),
                ), mock.patch.object(
                    ActivityRegistry,
                    "_validate_tree",
                    side_effect=AssertionError("constructor must not validate"),
                ), mock.patch(
                    "greia_platform.activities.package_digest",
                    side_effect=AssertionError("constructor must not digest"),
                ):
                    base, base_markers = _capture_markers(
                        launcher_main.LauncherApplication,
                        windowed=True,
                        allow_exit=True,
                        bootstrap=False,
                    )
                    self.assertEqual(base._activities, ())
                    self.assertIsNone(base.registry)
                    self.assertFalse(base._bootstrapped)
                    self.assertEqual(base_markers, [])
                    app, markers = _capture_markers(
                        GreiaLauncherPresentation,
                        windowed=True,
                        allow_exit=True,
                        bootstrap=False,
                    )
                    self.assertEqual(app._activities, ())
                    self.assertIsNone(app.registry)
                    self.assertFalse(app._bootstrapped)
                    self.assertEqual(markers, [])

    def test_normal_boot_performs_no_tree_validation_or_digest(self) -> None:
        from greia_launcher.presentation import GreiaLauncherPresentation

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            index_path = tmp_path / "builtin-index.json"
            expected_digest, expected_count = self._write_production_index(
                index_path
            )
            env = self._boot_env(tmp_path, index_path)
            with mock.patch.dict(os.environ, env, clear=False):
                app = GreiaLauncherPresentation(
                    windowed=True, allow_exit=True, bootstrap=False
                )
                with _NoValidation():
                    _, markers = _capture_markers(app.bootstrap)
                self.assertTrue(app._bootstrapped)
                self.assertEqual(len(app._activities), expected_count)
                self.assertFalse(app._catalogue_error)
                # Marker order preserved on the explicit path.
                self.assertEqual(tuple(markers), BOOT_MARKER_ORDER)
                # Activation proof carried through, never recomputed.
                with _NoValidation():
                    registration = app.registry.registration_for(
                        app._activities[0]
                    )
                    self.assertEqual(
                        registration.package_digest, expected_digest
                    )
                    self.assertEqual(
                        registration.source_id,
                        launcher_main.BUILT_IN_SOURCE_ID,
                    )
                # Launch authority is bound to the same composed set.
                authority = app.runtime_services.permission_broker.issue(
                    registration
                )
                self.assertIsNotNone(authority)
                self.assertIsNotNone(app.supervisor)
                self.assertIsNotNone(app._catalogue)
                # Second bootstrap is a no-op, not a second composition.
                with mock.patch.object(
                    launcher_composition,
                    "compose_boot_content",
                    side_effect=AssertionError("must bootstrap exactly once"),
                ):
                    app.bootstrap()

    def test_explicit_boot_builds_single_runtime_and_catalogue(self) -> None:
        from greia_launcher.presentation import GreiaLauncherPresentation

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            index_path = tmp_path / "builtin-index.json"
            self._write_production_index(index_path)
            env = self._boot_env(tmp_path, index_path)
            with mock.patch.dict(os.environ, env, clear=False):
                import greia_launcher.main as main_module
                import greia_launcher.presentation as presentation_module

                real_main_build = main_module.build_launcher_runtime_services
                real_from_activities = (
                    presentation_module.ActivityCatalogue.from_activities
                )
                runtime_builds: list[str] = []
                catalogue_builds: list[str] = []

                def _counting_main_build(*args: object, **kwargs: object):  # type: ignore[no-untyped-def]
                    runtime_builds.append("main")
                    return real_main_build(*args, **kwargs)  # type: ignore[arg-type]

                def _counting_catalogue(*args: object, **kwargs: object):  # type: ignore[no-untyped-def]
                    catalogue_builds.append("catalogue")
                    return real_from_activities(*args, **kwargs)  # type: ignore[arg-type]

                with (
                    mock.patch.object(
                        main_module,
                        "build_launcher_runtime_services",
                        _counting_main_build,
                    ),
                    mock.patch.object(
                        presentation_module.ActivityCatalogue,
                        "from_activities",
                        _counting_catalogue,
                    ),
                    mock.patch.object(
                        GreiaLauncherPresentation,
                        "_configure_parent_package_source",
                    ) as configure_spy,
                ):
                    app = GreiaLauncherPresentation(
                        windowed=True, allow_exit=True, bootstrap=False
                    )
                    self.assertEqual(runtime_builds, [])
                    self.assertEqual(catalogue_builds, [])
                    app.bootstrap()
                self.assertEqual(runtime_builds, ["main"])
                self.assertEqual(catalogue_builds, ["catalogue"])
                self.assertEqual(configure_spy.call_count, 0)
                source_ids = [
                    source.source_id for source in app.registry._sources
                ]
                self.assertIn("greia-parent-package-service", source_ids)
                self.assertIn(launcher_main.BUILT_IN_SOURCE_ID, source_ids)

    def test_corrupt_index_raises_controlled_failure_without_rescan(self) -> None:
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
                with mock.patch.object(
                    ActivityRegistry,
                    "discover",
                    side_effect=AssertionError("corrupt index must not rescan"),
                ), mock.patch.object(
                    ActivityRegistry,
                    "discover_registrations",
                    side_effect=AssertionError("corrupt index must not rescan"),
                ):
                    buffer = io.StringIO()
                    with contextlib.redirect_stdout(buffer):
                        with self.assertRaises(ActivityIndexError):
                            app.bootstrap()
                    names = [
                        line.split("event=")[1].split()[0]
                        for line in buffer.getvalue().splitlines()
                        if line.startswith("GREIA_BOOT event=")
                    ]
                    # Fail-closed but framed: construct markers still emitted.
                    self.assertIn("launcher_construct_begin", names)
                    self.assertIn("launcher_construct_end", names)
                self.assertFalse(app._bootstrapped)

    def test_missing_index_falls_back_to_validated_scan(self) -> None:
        """Sensitivity control: the no-validation spy above is discriminating."""

        from greia_launcher.presentation import GreiaLauncherPresentation

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            env = self._boot_env(tmp_path, tmp_path / "absent-index.json")
            with mock.patch.dict(os.environ, env, clear=False):
                app = GreiaLauncherPresentation(
                    windowed=True, allow_exit=True, bootstrap=False
                )
                calls: list[str] = []
                import greia_platform.activities as activities

                real_validate = activities.ActivityRegistry._validate_tree

                def _counting_validate(self_obj: object, root: object) -> None:  # type: ignore[no-untyped-def]
                    calls.append(str(root))
                    return real_validate(self_obj, root)  # type: ignore[arg-type]

                with mock.patch.object(
                    activities.ActivityRegistry,
                    "_validate_tree",
                    _counting_validate,
                ):
                    app.bootstrap()
                self.assertTrue(len(calls) > 0)
                self.assertTrue(len(app._activities) > 0)


if __name__ == "__main__":
    raise SystemExit(unittest.main())
