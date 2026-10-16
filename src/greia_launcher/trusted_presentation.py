from __future__ import annotations

from typing import Any

from .activity_policy_presentation import DirectActivityPolicyDiscoveryMixin
from .composition import (
    provisional_installed_display_session,
    provisional_installed_system_chrome,
)
from .launch_timing import ready_timeout_for
from .presentation import GreiaLauncherPresentation, parse_args
from .trusted_chrome_supervisor import TrustedChromeActivitySupervisor


class TrustedGreiaLauncherPresentation(
    DirectActivityPolicyDiscoveryMixin,
    GreiaLauncherPresentation,
):
    """Installed fallback presentation with the same mandatory Home authority.

    `greia-x-session` uses this only if the richer child-shell composition exits.
    It deliberately reuses all presentation/rendering code and replaces only the
    trusted Activity lifecycle composition, so fallback never becomes a second
    graphics architecture or an unprotected Activity path. Parent Activity
    visibility policy is still mandatory through DirectActivityPolicyDiscoveryMixin.
    """

    def _build_bootstrap_supervisor(self, runtime_services: Any) -> Any:
        """Build the trusted-chrome supervisor bound to prepared services.

        Pure construction for the bootstrap coordinator: no Pygame, no live
        launcher mutation. The controller set is read by reference and never
        mutated here.
        """

        installed = self._installed_root()
        return TrustedChromeActivitySupervisor(
            runtime_manager=runtime_services.runtime_manager,
            storage_service=runtime_services.storage_service,
            history_service=runtime_services.history_service,
            display_coordinator=(
                provisional_installed_display_session() if installed else None
            ),
            system_chrome_coordinator=(
                provisional_installed_system_chrome() if installed else None
            ),
            ready_timeout_seconds=ready_timeout_for(runtime_services),
            controller_set=(
                self._shell_input.controllers
                if getattr(self, "_shell_input", None) is not None
                else None
            ),
        )


def main() -> int:
    args = parse_args()
    # Phase 4 order: minimal shell here; run() owns display, first flip,
    # single-worker preparation and intro-end apply.
    return TrustedGreiaLauncherPresentation(
        windowed=args.windowed,
        allow_exit=args.allow_exit,
        bootstrap=False,
    ).run()


if __name__ == "__main__":
    raise SystemExit(main())
