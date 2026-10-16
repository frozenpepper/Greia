"""Shared real-subprocess supervision leg for simulator integration tests.

These tests launch one real Python Activity child through the production
``ProfileVisualActivitySupervisor`` (dummy SDL), wait for READY, request a
graceful stop and assert a clean terminal result.

Two rules keep them honest on a loaded developer host:

* waits are condition-driven with generous *bounded* deadlines (and the
  supervisor under test gets matching ready/graceful-stop windows), so a busy
  machine makes the leg slower rather than red. Product READY/stop timing is
  owned by the dedicated launch-performance tests, not by these;
* every launched child is force-stopped and reaped through ``addCleanup``, so
  a failing assertion can never orphan a ``greia_simulator/python_activity.py``
  process that outlives the test run.
"""

from __future__ import annotations

import os
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]

READY_WAIT_SECONDS = 90.0
GRACEFUL_STOP_SECONDS = 30.0
STOP_WAIT_SECONDS = 60.0
REAP_WAIT_SECONDS = 10.0
POLL_INTERVAL_SECONDS = 0.02

DUMMY_SDL_ENVIRONMENT = {
    "SDL_VIDEODRIVER": "dummy",
    "SDL_AUDIODRIVER": "dummy",
    "PYGAME_HIDE_SUPPORT_PROMPT": "1",
}


def load_tolerant_supervisor(**kwargs: object):
    """Return the production supervisor with load-tolerant lifecycle windows."""
    from greia_launcher.child_shell import ProfileVisualActivitySupervisor

    kwargs.setdefault("ready_timeout_seconds", READY_WAIT_SECONDS)
    kwargs.setdefault("graceful_stop_seconds", GRACEFUL_STOP_SECONDS)
    return ProfileVisualActivitySupervisor(**kwargs)


def reap_on_cleanup(testcase: unittest.TestCase, supervisor, session) -> None:
    """Always force-stop and reap ``session``'s child when the test ends."""

    def reap() -> None:
        if session.result is not None:
            return
        from greia_launcher.lifecycle import ActivityExitReason

        try:
            supervisor.force_stop(session, ActivityExitReason.FORCED_STOP)
            deadline = time.monotonic() + REAP_WAIT_SECONDS
            while session.result is None and time.monotonic() < deadline:
                supervisor.poll(session)
                time.sleep(POLL_INTERVAL_SECONDS)
        except Exception:  # noqa: BLE001 - cleanup must reach the hard kill below
            pass
        process = session.process
        if process is not None and process.poll() is None:
            process.kill()
            wait = getattr(process, "wait", None)
            if callable(wait):
                wait(timeout=REAP_WAIT_SECONDS)

    testcase.addCleanup(reap)


def wait_until_ready(testcase: unittest.TestCase, supervisor, session) -> None:
    deadline = time.monotonic() + READY_WAIT_SECONDS
    while (
        session.result is None
        and session.ready_at is None
        and time.monotonic() < deadline
    ):
        supervisor.poll(session)
        time.sleep(POLL_INTERVAL_SECONDS)
    testcase.assertIsNone(session.result, session.result)
    testcase.assertIsNotNone(
        session.ready_at, f"no READY within {READY_WAIT_SECONDS:.0f}s"
    )


def stop_gracefully(testcase: unittest.TestCase, supervisor, session):
    result = supervisor.request_stop(session)
    deadline = time.monotonic() + STOP_WAIT_SECONDS
    while result is None and time.monotonic() < deadline:
        time.sleep(POLL_INTERVAL_SECONDS)
        result = supervisor.poll(session)
    testcase.assertIsNotNone(result, f"no exit within {STOP_WAIT_SECONDS:.0f}s")
    assert result is not None
    testcase.assertTrue(result.ready)
    testcase.assertTrue(result.succeeded, result)
    return result


def supervise_builtin_activity(testcase: unittest.TestCase, activity_id: str) -> None:
    """Start a built-in Activity in the simulator runtime, see READY, stop cleanly."""
    from greia_launcher.composition import build_launcher_runtime_services
    from greia_launcher.runtime_adapter import PythonRuntimePolicy
    from greia_platform.activities import ActivityRegistry, RuntimeCatalogue
    from greia_platform.trust import ActivitySource, PackageTrust
    from greia_simulator.device import DEFAULT_CAPABILITIES, SimulatedDeviceProfile
    from greia_simulator.runtime import SimulatorPythonRuntimeAdapter
    from greia_simulator.workspace import SimulatorWorkspace

    runtime_policy = ROOT / "runtime" / "child-runtime.toml"
    runtime = RuntimeCatalogue.load(runtime_policy)
    # Honor TMPDIR (device /tmp is noexec); broker defaults handle sun_path
    # length with a /tmp fallback. T02-SPAWN-HYGIENE.
    base = Path(testcase.enterContext(tempfile.TemporaryDirectory()))
    workspace = SimulatorWorkspace(ROOT, base / "state")
    device = SimulatedDeviceProfile(1024, 600, DEFAULT_CAPABILITIES)
    adapter = SimulatorPythonRuntimeAdapter(
        device, policy=PythonRuntimePolicy.load(runtime_policy)
    )
    source = ActivitySource(ROOT / "activities", PackageTrust.BUILT_IN, "builtin")
    registrations = ActivityRegistry([source], runtime).discover_registrations()
    registration = next(
        r for r in registrations if r.manifest.activity_id == activity_id
    )
    services = build_launcher_runtime_services(
        runtime,
        tuple(r.manifest for r in registrations),
        runtime_policy_path=runtime_policy,
        permission_policy_path=ROOT / "runtime" / "permission-policy.toml",
        storage_policy_path=ROOT / "runtime" / "storage-policy.toml",
        history_policy_path=ROOT / "runtime" / "history-policy.toml",
        progression_policy_path=ROOT / "runtime" / "progression-policy.toml",
        hal=device.to_hal(),
        runtime_adapters=(adapter,),
    )
    profile = workspace.profile_store().context(workspace.profiles()[0].profile_id)
    authority = services.permission_broker.issue(registration)
    supervisor = load_tolerant_supervisor(
        runtime_manager=services.runtime_manager,
        storage_service=services.storage_service,
        history_service=services.history_service,
        display_coordinator=None,
    )
    environment = workspace.environment()
    environment.update(DUMMY_SDL_ENVIRONMENT)
    with mock.patch.dict(os.environ, environment, clear=False):
        session = supervisor.start(registration.manifest, profile, authority)
        reap_on_cleanup(testcase, supervisor, session)
        wait_until_ready(testcase, supervisor, session)
        stop_gracefully(testcase, supervisor, session)
