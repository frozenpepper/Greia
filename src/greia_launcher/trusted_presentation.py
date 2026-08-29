from __future__ import annotations

from .composition import (
    build_launcher_runtime_services,
    provisional_installed_display_session,
    provisional_installed_system_chrome,
)
from .main import _development_hal
from .presentation import GreiaLauncherPresentation, parse_args
from .trusted_chrome_supervisor import TrustedChromeActivitySupervisor


class TrustedGreiaLauncherPresentation(GreiaLauncherPresentation):
    """Installed fallback presentation with the same mandatory Home authority.

    `greia-x-session` uses this only if the richer child-shell composition exits.
    It deliberately reuses all presentation/rendering code and replaces only the
    trusted Activity lifecycle composition, so fallback never becomes a second
    graphics architecture or an unprotected Activity path.
    """

    def _rebuild_runtime_services(self) -> None:
        development_hal = None if self._installed_root() else _development_hal()
        runtime_services = build_launcher_runtime_services(
            self.runtime,
            self._activities,
            runtime_policy_path=self.paths.runtime_catalogue,
            permission_policy_path=self.paths.permission_policy,
            storage_policy_path=self.paths.storage_policy,
            history_policy_path=self.paths.history_policy,
            progression_policy_path=self.paths.progression_policy,
            hal=development_hal,
        )
        installed = self._installed_root()
        supervisor = TrustedChromeActivitySupervisor(
            runtime_manager=runtime_services.runtime_manager,
            storage_service=runtime_services.storage_service,
            history_service=runtime_services.history_service,
            display_coordinator=(
                provisional_installed_display_session() if installed else None
            ),
            system_chrome_coordinator=(
                provisional_installed_system_chrome() if installed else None
            ),
        )
        self.runtime_services = runtime_services
        self.supervisor = supervisor


def main() -> int:
    args = parse_args()
    return TrustedGreiaLauncherPresentation(
        windowed=args.windowed,
        allow_exit=args.allow_exit,
    ).run()


if __name__ == "__main__":
    raise SystemExit(main())
