"""Greia test-suite lanes and test-process hygiene (single owner).

The repository suite has two lanes:

* **fast** (default, ``make test`` / ``make verify``): every unit, contract and
  Activity test that runs in seconds. This is the lane every implementation
  turn must keep green.
* **full** (opt-in, ``make test-full`` / ``make verify-full``): the fast lane
  plus the heavy end-to-end evidence suites listed in :data:`SLOW_TESTS`
  (QEMU-shaped x8 lifecycle/boot-chain/payload rigs, install RSS gates,
  whole-repository Activity/icon/index sweeps). Run it
  before release/install/update/lifecycle work is claimed complete, or when a
  change touches the code those suites exercise. ``make test-slow`` runs only
  the slow entries.

Entries are dotted unittest ids relative to ``tests/`` (module, ``module.Class``
or ``module.Class.test``); a prefix selects everything below it. Naming a
test explicitly (``python3 -m unittest test_x8_qemu.test_lifecycle``) always
runs it: lanes only filter *discovery*.

The same registry drives ``tools/run_tests.py`` (unittest) and
``tests/conftest.py`` (pytest), so there is exactly one list to maintain.
"""

from __future__ import annotations

import os
import unittest
from collections.abc import Iterator

LANE_ENVIRONMENT = "GREIA_TEST_LANE"
LANES = ("fast", "slow", "full")

# Heavy end-to-end evidence suites and whole-repository sweeps. Keep reasons
# short and true; remove an entry once its suite is cheap again. Security and
# fail-closed contracts (installer revalidation, update compatibility, AB
# composition negatives, sandbox, PermissionBroker) stay in the fast lane.
SLOW_TESTS: dict[str, str] = {
    "test_x8_qemu": "x8 QEMU-shaped lifecycle/boot-chain/payload evidence rigs",
    "test_first_party_activity_runtime_policy": "imports every first-party Activity in a curated child runtime",
    "test_install_rss_gate": "install RSS bounds measured over large payloads",
    "test_image_activity_index.ImageActivityIndexTests.test_checked_source_index_consistent":
        "re-validates every Activity package to rebuild the image index",
    "test_build_core_icons.RepositoryCoreIconInventoryTests.test_committed_pngs_match_a_fresh_render":
        "re-renders every committed core icon",
    "test_stage_release_activities.StageReleaseActivitiesTests.test_repository_draft_roster_stages_exact_source_reviewed_candidates":
        "stages the whole repository Activity roster",
    "test_visual_family_contact_sheet": "renders the full visual-family contact sheet",
}


def current_lane() -> str:
    lane = os.environ.get(LANE_ENVIRONMENT, "fast").strip().lower() or "fast"
    if lane not in LANES:
        raise ValueError(f"{LANE_ENVIRONMENT} must be one of {LANES}, not {lane!r}")
    return lane


def is_slow(test_id: str) -> bool:
    """Return whether a dotted unittest id belongs to the slow lane."""
    return any(
        test_id == entry or test_id.startswith(entry + ".") for entry in SLOW_TESTS
    )


def selected(test_id: str, lane: str) -> bool:
    if lane == "full":
        return True
    return is_slow(test_id) == (lane == "slow")


def _iter_tests(suite: unittest.TestSuite) -> Iterator[unittest.TestCase]:
    for item in suite:
        if isinstance(item, unittest.TestSuite):
            yield from _iter_tests(item)
        else:
            yield item


def filter_suite(suite: unittest.TestSuite, lane: str) -> unittest.TestSuite:
    """Keep the tests of ``lane``; import/load failures always stay visible."""
    kept = unittest.TestSuite()
    for test in _iter_tests(suite):
        test_id = test.id()
        if test_id.startswith("unittest.loader.") or selected(test_id, lane):
            kept.addTest(test)
    return kept


def install_test_process_hygiene() -> None:
    """Neutralise host-global side effects that tests cannot observe.

    Durable boot/update writers end with :func:`os.sync`, a *host-wide*
    flush. Inside temporary test trees it proves nothing (no test simulates
    power loss) but costs seconds per call on a busy developer machine and
    stalled whole runs. File-level ``fsync`` + rename + directory sync + the
    writers' re-read verification still execute unchanged.
    """
    os.sync = _no_host_sync
    _pin_source_packages()


# tools/ holds scripts named like the src packages (tools/greia_parent.py,
# tools/greia_simulator.py). Several tests put tools/ at the front of
# sys.path at import time; once discovery has imported them, a later
# ``import greia_parent`` would load the script instead of the package and
# fail depending on discovery order. Importing the real packages first pins
# them in sys.modules.
_SHADOWED_PACKAGES = ("greia_parent", "greia_simulator")


def _pin_source_packages() -> None:
    import importlib

    for name in _SHADOWED_PACKAGES:
        importlib.import_module(name)


def _no_host_sync() -> None:
    return None
