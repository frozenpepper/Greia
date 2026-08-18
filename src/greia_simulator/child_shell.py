"""The actual Greia child shell running against a synthetic developer device."""

from __future__ import annotations

from typing import Any

from greia_launcher.child_shell import GreiaChildShell

from .device import SimulatedDeviceProfile
from .runtime import SimulatorActivitySupervisor, build_simulator_runtime_services


class GreiaSimulatorChildShell(GreiaChildShell):
    """Real launcher/profile/catalogue composition over simulator-only adapters."""

    def __init__(self, device: SimulatedDeviceProfile):
        self.simulated_device = device
        super().__init__(windowed=True, allow_exit=True)

    def _rebuild_runtime_services(self) -> None:
        runtime_services = build_simulator_runtime_services(
            self.runtime,
            self._activities,
            runtime_policy_path=self.paths.runtime_catalogue,
            permission_policy_path=self.paths.permission_policy,
            storage_policy_path=self.paths.storage_policy,
            history_policy_path=self.paths.history_policy,
            progression_policy_path=self.paths.progression_policy,
            device=self.simulated_device,
        )
        supervisor = SimulatorActivitySupervisor(
            runtime_manager=runtime_services.runtime_manager,
            storage_service=runtime_services.storage_service,
            history_service=runtime_services.history_service,
            display_coordinator=None,
        )
        self.runtime_services = runtime_services
        self.supervisor = supervisor

    def _draw(self, screen: Any, pygame: Any) -> None:
        """Keep the real Greia shell on the exact selected synthetic viewport."""

        surface = pygame.display.get_surface()
        target = self.simulated_device.size
        if surface is None or surface.get_size() != target:
            surface = pygame.display.set_mode(target, pygame.RESIZABLE)
            pygame.display.set_caption(
                f"Greia Activity Simulator — {self.simulated_device.viewport}"
            )
            for name in (
                "_icon_cache",
                "_font_cache",
                "_shadow_cache",
                "_decorated_icon_cache",
            ):
                cache = getattr(self, name, None)
                if cache is not None:
                    cache.clear()
            self._activity_scroll_start = 0
        super()._draw(surface, pygame)


def main() -> int:
    device = SimulatedDeviceProfile.from_environment()
    return GreiaSimulatorChildShell(device).run()


if __name__ == "__main__":
    raise SystemExit(main())
