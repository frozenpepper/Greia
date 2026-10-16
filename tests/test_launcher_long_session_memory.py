"""Long-session memory regression for the child Shell's launch -> Home cycle.

The Acer re-sweep (2026-10-16) saw the Shell's RSS climb about 2 MB per
Activity launch. A local reproduction against the real Shell found no
unbounded Python-heap or Surface leak; the growth was caches filling plus
display-sized surfaces that stayed resident behind Home for no reason.

This drives the real ``GreiaChildShell`` presentation stack through Collection
page -> launch -> return -> Home cycles with an in-process supervisor double
(no Activity subprocess) and asserts that, once each Activity has been seen,
further launches neither grow the traced Python heap nor the retained Pygame
surface pixels. Source test only: no Simulator, VM or hardware claim.
"""

from __future__ import annotations

import gc
import os
import tempfile
import time
import tracemalloc
import unittest
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
TMP_DIR = tempfile.mkdtemp()
os.environ["GREIA_PROFILES_DIR"] = os.path.join(TMP_DIR, "profiles")
os.environ["GREIA_SYSTEM_SETTINGS_DIR"] = os.path.join(TMP_DIR, "settings")
os.environ["GREIA_MEDIA_ROOT"] = os.path.join(TMP_DIR, "media")
os.environ["GREIA_ACTIVE_PROFILE_STATUS"] = os.path.join(TMP_DIR, "active-profile.json")
os.environ["GREIA_HARDWARE_STATUS"] = os.path.join(TMP_DIR, "hardware-status.json")
os.environ["GREIA_MAIN_CREDENTIAL_PATH"] = os.path.join(TMP_DIR, "parent-credential.json")
os.environ["GREIA_OS_ROOT"] = str(REPO_ROOT)
os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"

import pygame

from greia_launcher.catalogue_view import ALL_ACTIVITIES_ID, ActivityFolder
from greia_launcher.lifecycle import (
    ActivityExitReason,
    ActivityResult,
    ActivitySessionState,
)

import hermetic_volume

DISTINCT_ACTIVITIES = 10
MEASURED_CYCLES = 24
# Allowances are far below one leaked display-sized surface (2.4 MB at
# 1024x600) or ~10 KB per cycle of Python heap, yet tolerate LRU churn.
MAX_TRACED_GROWTH_BYTES = 256 * 1024
MAX_SURFACE_PIXEL_GROWTH_BYTES = 512 * 1024


def setUpModule() -> None:
    hermetic_volume.install_for_module()


class _ReadyControl:
    def ready(self) -> bool:
        return True


@dataclass
class _Session:
    activity_id: str
    session_id: str
    state: ActivitySessionState = ActivitySessionState.RUNNING
    control: _ReadyControl = field(default_factory=_ReadyControl)
    result: ActivityResult | None = None


class _InstantSupervisor:
    """Supervisor double: READY then a graceful Home stop on the first poll."""

    def __init__(self) -> None:
        self.started: list[str] = []

    @property
    def active_session(self) -> None:
        return None

    def start(self, manifest: Any, profile: Any, authority: Any) -> _Session:
        self.started.append(manifest.activity_id)
        return _Session(manifest.activity_id, f"s{len(self.started)}")

    def poll(self, session: _Session) -> ActivityResult:
        now = time.monotonic()
        session.state = ActivitySessionState.EXITED
        session.result = ActivityResult(
            activity_id=session.activity_id,
            session_id=session.session_id,
            return_code=0,
            exit_reason=ActivityExitReason.GRACEFUL_STOP,
            ready=True,
            started_at=now,
            ready_at=now,
            ended_at=now,
        )
        return session.result

    def force_stop(self, session: _Session, reason: Any = None) -> ActivityResult:
        return self.poll(session)


def _retained_surface_bytes() -> int:
    """Pixel bytes of every Pygame Surface reachable from a tracked container."""

    gc.collect()
    seen: dict[int, int] = {}
    for owner in gc.get_objects():
        for item in gc.get_referents(owner):
            if isinstance(item, pygame.Surface) and id(item) not in seen:
                try:
                    seen[id(item)] = item.get_width() * item.get_height() * item.get_bytesize()
                except pygame.error:
                    # A display Surface left behind by an earlier test that quit
                    # the display no longer owns pixels; it retains nothing.
                    seen[id(item)] = 0
    return sum(seen.values())


class ShellLaunchCycleMemoryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        pygame.init()
        pygame.font.init()

    def _shell(self):
        from greia_launcher.child_shell import GreiaChildShell

        screen = pygame.display.set_mode((1024, 600))
        shell = GreiaChildShell(windowed=True)
        if shell._visual_cache is None:
            self.skipTest("shared visuals unavailable in this checkout")
        shell.profiles = shell.profile_store.ensure_initialized()
        # The profile picker is what a child sees first.
        shell._draw(screen, pygame)
        shell._activate_profile(shell.profiles[0], pygame)
        shell.supervisor = _InstantSupervisor()
        # The pre-launch card wiggle is pure timing; keep the cycle fast.
        shell._LAUNCH = replace(shell._LAUNCH, duration_seconds=0.001)
        return shell, screen

    @staticmethod
    def _launch_routes(shell) -> list[tuple[str, str | None, int, str]]:
        """Visible (Collection, group/folder, index, activity_id) routes."""

        routes: list[tuple[str, str | None, int, str]] = []
        seen: set[str] = set()
        for collection in shell._home_collections():
            cid = collection.collection_id
            if cid == shell.CREATIONS_COLLECTION_ID:
                continue
            shell._set_category(cid)
            groups = [group.collection_id for group in shell._adaptive_groups()]
            folders = [
                entry.folder_id
                for entry in shell._presented_activities
                if isinstance(entry, ActivityFolder)
            ]
            for group in [None, *groups, *folders]:
                if group is not None:
                    shell._open_subcollection(group)
                for index, entry in enumerate(tuple(shell._presented_activities)):
                    if isinstance(entry, ActivityFolder):
                        continue
                    if entry.activity_id not in seen:
                        seen.add(entry.activity_id)
                        routes.append((cid, group, index, entry.activity_id))
                shell._set_category(cid)
        shell._set_category(ALL_ACTIVITIES_ID)
        return routes

    def _cycle(self, shell, screen, route) -> None:
        cid, group, index, activity_id = route
        shell._set_category(cid)
        if group is not None:
            shell._open_subcollection(group)
        shell._draw(screen, pygame)
        shell._selected = index
        shell._launch_selected(pygame)
        self.assertEqual(shell.supervisor.started[-1], activity_id)
        shell._draw(screen, pygame)  # back on the originating page
        shell._set_category(ALL_ACTIVITIES_ID)
        shell._draw(screen, pygame)  # Home

    def test_repeated_launches_do_not_grow_shell_memory(self) -> None:
        shell, screen = self._shell()
        routes = self._launch_routes(shell)[:DISTINCT_ACTIVITIES]
        self.assertGreaterEqual(len(routes), 5)

        # Warm-up: every Activity in the working set is seen once, filling its
        # (bounded) icon/card/title caches.
        for route in routes:
            self._cycle(shell, screen, route)

        tracemalloc.start()
        try:
            gc.collect()
            traced_before = tracemalloc.get_traced_memory()[0]
            surfaces_before = _retained_surface_bytes()
            for cycle in range(MEASURED_CYCLES):
                self._cycle(shell, screen, routes[cycle % len(routes)])
            gc.collect()
            traced_after = tracemalloc.get_traced_memory()[0]
            surfaces_after = _retained_surface_bytes()
        finally:
            tracemalloc.stop()

        self.assertEqual(len(shell.supervisor.started), len(routes) + MEASURED_CYCLES)
        self.assertLess(
            traced_after - traced_before,
            MAX_TRACED_GROWTH_BYTES,
            f"Python heap grew {traced_after - traced_before} B over {MEASURED_CYCLES} launches",
        )
        self.assertLess(
            surfaces_after - surfaces_before,
            MAX_SURFACE_PIXEL_GROWTH_BYTES,
            f"retained surfaces grew {surfaces_after - surfaces_before} B over {MEASURED_CYCLES} launches",
        )

    def test_display_sized_transients_are_released_behind_home(self) -> None:
        shell, screen = self._shell()
        self.assertIsNone(shell._cached_profiles_surface)
        route = self._launch_routes(shell)[0]
        self._cycle(shell, screen, route)
        # The composed wait screen is dropped once its launch returns.
        self.assertIsNone(getattr(shell, "_launch_overlay_cache", None))
        self.assertIsNone(shell._cached_profiles_surface)
        cache = shell._visual_cache
        self.assertIsNotNone(cache.max_total_pixels)
        self.assertLessEqual(cache.cached_pixels, cache.max_total_pixels)


if __name__ == "__main__":
    unittest.main()
