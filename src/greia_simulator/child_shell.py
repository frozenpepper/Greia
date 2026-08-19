"""The real Greia child shell running against one synthetic developer device."""

from __future__ import annotations

import argparse
import signal
import time
from contextlib import contextmanager
from typing import Any, Iterator

from greia_launcher.child_shell import GreiaChildShell
from greia_launcher.lifecycle import ActivityExitReason
from greia_launcher.runtime_adapter import PythonRuntimePolicy

from .device import (
    DEFAULT_CAPABILITIES,
    SimulatedDeviceProfile,
    parse_viewport,
)
from .runtime import SimulatorPythonRuntimeAdapter


class _SimulatorShutdownRequested(BaseException):
    """Unwind the Shell to its normal cleanup boundary on control-plane SIGTERM."""


class GreiaSimulatorChildShell(GreiaChildShell):
    """Real Greia child Shell with only HAL/runtime/display host variation."""

    def __init__(self, device: SimulatedDeviceProfile):
        self.simulated_device = device
        super().__init__(windowed=True, allow_exit=True)

    def _runtime_hal(self):
        return self.simulated_device.to_hal()

    def _runtime_adapters(self):
        return (
            SimulatorPythonRuntimeAdapter(
                self.simulated_device,
                policy=PythonRuntimePolicy.load(self.paths.runtime_catalogue),
            ),
        )

    def run(self) -> int:
        """Run normal Shell code and normalize external Stop/Restart lifecycle."""

        previous = signal.getsignal(signal.SIGTERM)

        def request_shutdown(_signum, _frame) -> None:
            # Raising only unwinds normal Python code; all lifecycle work happens
            # after the production Shell's finally block, never inside the signal
            # callback itself.
            raise _SimulatorShutdownRequested()

        signal.signal(signal.SIGTERM, request_shutdown)
        try:
            with self._locked_shell_surface():
                try:
                    return super().run()
                except _SimulatorShutdownRequested:
                    self._shutdown_active_bounded()
                    return 0
        finally:
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

    @contextmanager
    def _locked_shell_surface(self) -> Iterator[None]:
        """Keep the Shell at the synthetic viewport without touching its caches.

        This is temporary desktop SDL compatibility while the shared R7 display
        backend matures. The ordinary Shell run loop remains responsible for
        resize observation/cache invalidation; the simulator does not reach into
        private presentation state.
        """

        import pygame

        original = pygame.display.set_mode
        target = self.simulated_device.size

        def locked_set_mode(
            size=(0, 0),
            flags=0,
            depth=0,
            display=0,
            vsync=0,
        ) -> Any:
            del size
            normalized_flags = (int(flags) | int(pygame.RESIZABLE)) & ~int(
                pygame.FULLSCREEN
            )
            try:
                surface = original(
                    target,
                    normalized_flags,
                    depth,
                    display=display,
                    vsync=vsync,
                )
            except TypeError:
                surface = original(target, normalized_flags, depth)
            pygame.display.set_caption(
                f"Greia Activity Simulator — {self.simulated_device.viewport}"
            )
            return surface

        pygame.display.set_mode = locked_set_mode
        try:
            yield
        finally:
            pygame.display.set_mode = original


def _parse_capabilities(values: list[str]) -> frozenset[str]:
    if not values:
        return DEFAULT_CAPABILITIES
    return frozenset(item.strip() for item in values if item.strip())


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Greia synthetic-device child Shell")
    parser.add_argument("--viewport", default="1024x600")
    parser.add_argument("--capability", action="append", default=[])
    args = parser.parse_args(argv)
    width, height = parse_viewport(args.viewport)
    device = SimulatedDeviceProfile(
        width,
        height,
        _parse_capabilities(args.capability),
    )
    return GreiaSimulatorChildShell(device).run()


if __name__ == "__main__":
    raise SystemExit(main())
