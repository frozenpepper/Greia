"""Past-headroom volumes must degrade read-side consumers, never crash the Shell.

Writers stay fail-closed (no history/creation growth past the platform budget);
read-side/presentation consumers show a neutral state. The developer Simulator
models its own synthetic device volume instead of the host disk.
"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from greia_launcher.achievement_presentation import AchievementLibraryMixin
from greia_launcher.main import LauncherApplication
from greia_platform.achievements import (
    AchievementPolicy,
    ProfileAchievementService,
)
from greia_platform.creation_capacity import (
    VolumeBudget,
    VolumeCapacityPolicy,
    VolumeUsage,
)
from greia_platform.activities import ActivityRegistry, RuntimeCatalogue
from greia_platform.trust import ActivitySource, PackageTrust
from greia_platform.history import (
    HistoryCapacityError,
    HistoryError,
    HistoryPolicy,
    PlatformHistoryService,
    ProgressionPolicy,
)
from greia_platform.profiles import ProfileStore
from greia_simulator.child_shell import GreiaSimulatorChildShell
from greia_simulator.volume import (
    DEFAULT_SIMULATED_OS_BASELINE_BYTES,
    DEFAULT_SIMULATED_VOLUME_BYTES,
    SimulatedVolumeProbe,
    simulated_volume_budget,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
_GIB = 1024**3


def _usage(total: int, used: int) -> VolumeUsage:
    return VolumeUsage(total, used, total - used)


def _budget(total: int, used: int) -> VolumeBudget:
    return VolumeBudget(
        VolumeCapacityPolicy(), probe=lambda _root: _usage(total, used)
    )


ROOMY = _budget(1024 * _GIB, _GIB)
FULL = _budget(10 * _GIB, 9 * _GIB)  # 90% used: past the 75% ceiling


class _Fixture(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        profiles = ProfileStore.load(
            PROJECT_ROOT / "runtime" / "profile-defaults.toml",
            Path(self._tmp.name) / "profiles",
        )
        first = profiles.ensure_initialized()[0]
        self.context = profiles.context(first.profile_id)
        self.history_policy = HistoryPolicy.load(
            PROJECT_ROOT / "runtime" / "history-policy.toml"
        )
        self.progression = ProgressionPolicy(schema_version=1, rules=())

    def _service(self, budget: VolumeBudget) -> PlatformHistoryService:
        return PlatformHistoryService(
            self.history_policy, self.progression, volume_budget=budget
        )


class HistoryReadSideTests(_Fixture):
    def test_new_database_refused_past_headroom_with_capacity_error(self) -> None:
        with self.assertRaises(HistoryCapacityError):
            self._service(FULL).open(self.context)
        # Still a HistoryError so existing callers keep failing closed.
        self.assertTrue(issubclass(HistoryCapacityError, HistoryError))
        self.assertFalse(self.context.progress_dir.joinpath("history.sqlite3").exists())

    def test_existing_database_opens_for_reads_past_headroom(self) -> None:
        self._service(ROOMY).open(self.context)
        store = self._service(FULL).open(self.context)
        self.assertEqual(store.summary().event_counts, ())

    def test_existing_database_still_refuses_writes_past_headroom(self) -> None:
        self._service(ROOMY).open(self.context)
        full_store = self._service(FULL).open(self.context)
        runtime = RuntimeCatalogue.load(PROJECT_ROOT / "runtime" / "child-runtime.toml")
        source = ActivitySource(
            PROJECT_ROOT / "activities", PackageTrust.BUILT_IN, "greia-system"
        )
        manifest = ActivityRegistry([source], runtime).discover()[0]
        with self.assertRaises(HistoryCapacityError):
            full_store.start_session(
                manifest, session_id="s" * 8, package_digest="0" * 64
            )


class AchievementDegradationTests(_Fixture):
    def _achievements(self, budget: VolumeBudget) -> ProfileAchievementService:
        return ProfileAchievementService(_policy(), self._service(budget))

    def test_refresh_returns_neutral_snapshot_and_logs_once(self) -> None:
        service = self._achievements(FULL)
        with self.assertLogs("greia_platform.achievements", "WARNING") as logs:
            first = service.refresh(self.context)
            second = service.refresh(self.context)
        self.assertEqual(first.unlocked_count, 0)
        self.assertEqual(second.unlocked_count, 0)
        self.assertEqual(len(logs.records), 1)

    def test_non_capacity_history_errors_are_not_swallowed(self) -> None:
        class _Broken:
            def open(self, _profile):
                raise HistoryError("history database is unavailable or corrupt")

        service = ProfileAchievementService(_policy(), _Broken())
        with self.assertRaises(HistoryError):
            service.refresh(self.context)


def _policy() -> AchievementPolicy:
    return AchievementPolicy(1, "en", ())


class _Presenter(AchievementLibraryMixin):
    """Presentation mixin without Pygame/Shell construction."""

    def __init__(self, service, profile) -> None:  # noqa: D401 - test double
        self.runtime_services = SimpleNamespace(achievement_service=service)
        self._active_profile = profile
        self._achievement_snapshot = None


class AchievementPresentationTests(unittest.TestCase):
    def test_history_error_keeps_shell_alive_with_bounded_retry(self) -> None:
        calls: list[int] = []

        class _Service:
            def refresh(self, _profile):
                calls.append(1)
                raise HistoryError("history database is unavailable or corrupt")

        presenter = _Presenter(_Service(), object())
        with self.assertLogs("greia_launcher.achievement_presentation", "WARNING") as logs:
            for _ in range(60):  # one simulated second of per-frame draw polling
                self.assertIsNone(presenter._refresh_achievements())
        self.assertEqual(len(calls), 1)
        self.assertEqual(len(logs.records), 1)
        # An explicit transition boundary (profile activation) retries at once.
        presenter._achievement_retry_at = 0.0
        presenter._refresh_achievements()
        self.assertEqual(len(calls), 2)


class SimulatorVolumeTests(unittest.TestCase):
    def test_probe_models_baseline_plus_workspace_bytes(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            (root / "a" / "b").mkdir(parents=True)
            (root / "a" / "one.bin").write_bytes(b"x" * 1000)
            (root / "a" / "b" / "two.bin").write_bytes(b"y" * 234)
            (root / "link").symlink_to(root / "a")  # never double counted
            probe = SimulatedVolumeProbe(
                root, total_bytes=_GIB, os_baseline_bytes=1000
            )
            usage = probe(root / "anything")
            self.assertEqual(usage.total_bytes, _GIB)
            self.assertEqual(usage.used_bytes, 1000 + 1234)
            self.assertEqual(usage.free_bytes, _GIB - 2234)

    def test_missing_root_and_oversized_tree_are_clamped(self) -> None:
        probe = SimulatedVolumeProbe(
            Path("/nonexistent-greia-sim-root"), total_bytes=2000, os_baseline_bytes=500
        )
        self.assertEqual(probe(Path("/")).used_bytes, 500)
        with tempfile.TemporaryDirectory() as raw:
            (Path(raw) / "big").write_bytes(b"z" * 5000)
            usage = SimulatedVolumeProbe(
                Path(raw), total_bytes=2000, os_baseline_bytes=500
            )(Path(raw))
            self.assertEqual((usage.used_bytes, usage.free_bytes), (2000, 0))

    def test_defaults_allow_child_growth_under_production_policy(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            budget = simulated_volume_budget(Path(raw))
            self.assertEqual(
                budget.usage(Path(raw)).total_bytes, DEFAULT_SIMULATED_VOLUME_BYTES
            )
            self.assertEqual(
                budget.usage(Path(raw)).used_bytes, DEFAULT_SIMULATED_OS_BASELINE_BYTES
            )
            self.assertEqual(budget.policy, VolumeCapacityPolicy())
            budget.require_growth(Path(raw), 64 * 1024 * 1024)

    def test_simulated_volume_is_independent_of_host_and_shell_wiring(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            stub = SimpleNamespace(paths=SimpleNamespace(profiles_dir=Path(raw)))
            budget = GreiaSimulatorChildShell._runtime_volume_budget(stub)
            self.assertIsInstance(budget, VolumeBudget)
            self.assertEqual(
                budget.usage(Path(raw)).total_bytes, DEFAULT_SIMULATED_VOLUME_BYTES
            )
        # Production shells keep the default (host-measured) budget.
        self.assertIsNone(LauncherApplication._runtime_volume_budget(object()))


if __name__ == "__main__":
    unittest.main()
