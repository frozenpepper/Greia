"""The real Greia child shell running against one synthetic developer device."""

from __future__ import annotations

import argparse
import os
import signal
import time
from typing import Any

from greia_launcher.child_shell import GreiaChildShell
from greia_launcher.lifecycle import ActivityExitReason
from greia_launcher.runtime_adapter import PythonRuntimePolicy

from .device import (
    DEFAULT_CAPABILITIES,
    SimulatedDeviceProfile,
    parse_viewport,
)
from .remote_bridge import DEFAULT_REMOTE_PORT, SimulatorRemoteBridge
from .runtime import SimulatorPythonRuntimeAdapter


class _SimulatorShutdownRequested(BaseException):
    """Unwind the Shell to its normal cleanup boundary on control-plane SIGTERM."""


class GreiaSimulatorChildShell(GreiaChildShell):
    """Real Greia child Shell with only HAL/runtime/window host variation."""

    def __init__(
        self,
        device: SimulatedDeviceProfile,
        *,
        remote_port: int | None = DEFAULT_REMOTE_PORT,
        enable_remote: bool = True,
    ):
        self.simulated_device = device
        self._remote_bridge = (
            SimulatorRemoteBridge(port=remote_port or DEFAULT_REMOTE_PORT)
            if enable_remote
            else None
        )
        super().__init__(windowed=True, allow_exit=True)

    @property
    def remote_url(self) -> str | None:
        bridge = getattr(self, "_remote_bridge", None)
        return bridge.url if bridge is not None else None

    def _runtime_hal(self):
        return self.simulated_device.to_hal()

    def _runtime_adapters(self):
        remote_port = (
            self._remote_bridge.port if self._remote_bridge is not None else 0
        )
        return (
            SimulatorPythonRuntimeAdapter(
                self.simulated_device,
                policy=PythonRuntimePolicy.load(self.paths.runtime_catalogue),
                remote_port=remote_port,
            ),
        )

    def _initial_display_request(self, pygame: Any) -> tuple[tuple[int, int], int]:
        return (self.simulated_device.size, pygame.RESIZABLE)

    def _resize_display_request(
        self, event: Any, pygame: Any
    ) -> tuple[tuple[int, int], int] | None:
        del event
        # Host window drags do not mutate the synthetic physical device. The
        # normal Shell display/cache path receives the same exact viewport again.
        return (self.simulated_device.size, pygame.RESIZABLE)

    def _display_caption(self) -> str:
        bridge_info = f" • Web: {self.remote_url}" if self.remote_url else ""
        return f"Greia Activity Simulator — {self.simulated_device.viewport}{bridge_info}"

    def _poll_input_hooks(self, pygame: Any) -> None:
        if getattr(self, "_remote_bridge", None) is not None:
            for ev in self._remote_bridge.poll_events(pygame):
                pygame.event.post(ev)

    def _on_frame_presented(self, screen: Any, pygame: Any) -> None:
        if getattr(self, "_remote_bridge", None) is not None:
            self._remote_bridge.capture_frame(screen, pygame, mode=self._mode)

    def run(self) -> int:
        """Run normal Shell code and normalize external Stop/Restart lifecycle."""

        previous = signal.getsignal(signal.SIGTERM)

        def request_shutdown(_signum, _frame) -> None:
            # Raising only unwinds normal Python code; all lifecycle work happens
            # after the production Shell's finally block, never inside the signal
            # callback itself.
            raise _SimulatorShutdownRequested()

        signal.signal(signal.SIGTERM, request_shutdown)
        if self._remote_bridge is not None:
            self._remote_bridge.start()

        try:
            try:
                return super().run()
            except _SimulatorShutdownRequested:
                self._shutdown_active_bounded()
                return 0
        finally:
            if self._remote_bridge is not None:
                self._remote_bridge.stop()
            signal.signal(signal.SIGTERM, previous)

    def _shutdown_active_bounded(self) -> None:
        session = self.supervisor.active_session
        if session is None:
            return

        result = self.supervisor.request_stop(session)
        graceful_deadline = time.monotonic() + 1.75
        while result is None and time.monotonic() < graceful_deadline:
            time.sleep(0.02)
            result = self.supervisor.poll(session)
        if result is not None:
            return

        result = self.supervisor.force_stop(
            session,
            ActivityExitReason.SYSTEM_SHUTDOWN,
        )
        forced_deadline = time.monotonic() + 0.75
        while result is None and time.monotonic() < forced_deadline:
            time.sleep(0.02)
            result = self.supervisor.poll(session)


def _parse_capabilities(values: list[str]) -> frozenset[str]:
    if not values:
        return DEFAULT_CAPABILITIES
    return frozenset(item.strip() for item in values if item.strip())


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Greia synthetic-device child Shell")
    parser.add_argument("--viewport", default="1024x600")
    parser.add_argument("--capability", action="append", default=[])
    parser.add_argument("--remote-port", type=int, default=DEFAULT_REMOTE_PORT)
    parser.add_argument("--no-remote", action="store_true", default=False)
    parser.add_argument("--headless", action="store_true", default=False, help="Run without opening a GUI window")
    parser.add_argument("--language", "--locale", default=None, help="Language code (e.g. it, en, es)")
    args = parser.parse_args(argv)

    if args.headless or os.environ.get("GREIA_SIMULATOR_HEADLESS") == "1":
        os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
        os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

    if args.language:
        os.environ["GREIA_PROFILE_LOCALE"] = args.language
        os.environ["GREIA_DEVICE_LOCALE"] = args.language

    if "GREIA_OS_ROOT" not in os.environ:
        from pathlib import Path
        from .workspace import SimulatorWorkspace

        repo_root = Path(__file__).resolve().parents[2]
        state_root = Path.home() / ".greia-simulator"
        workspace = SimulatorWorkspace(repo_root=repo_root, state_root=state_root)
        workspace.ensure()
        for k, v in workspace.environment().items():
            os.environ.setdefault(k, v)
    os.environ.setdefault("PYTHONDONTWRITEBYTECODE", "1")

    width, height = parse_viewport(args.viewport)
    device = SimulatedDeviceProfile(
        width,
        height,
        _parse_capabilities(args.capability),
    )
    return GreiaSimulatorChildShell(
        device,
        remote_port=args.remote_port,
        enable_remote=not args.no_remote,
    ).run()


if __name__ == "__main__":
    raise SystemExit(main())
