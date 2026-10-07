from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol


@dataclass(frozen=True, slots=True)
class ShellActivityModalLease:
    """Exact trusted ownership proof for temporarily presenting Shell over Activity."""

    session_id: str
    generation: int
    activity_pid: int
    shell_window_id: int
    activity_window_id: int


class ShellWindowController(Protocol):
    """Backend-private lifecycle hooks for Greia's own Shell window.

    Ordinary focus repair and temporary trusted modal presentation share this
    backend boundary because both operate on the same Shell native window.
    Activity code never receives native window IDs or modal leases.
    """

    @property
    def backend_id(self) -> str: ...

    def after_window_created(self, pygame: Any) -> bool: ...

    def after_activity_return(self, pygame: Any) -> bool: ...

    def prepare_activity_modal(
        self,
        pygame: Any,
        *,
        session_id: str,
        activity_pid: int,
    ) -> ShellActivityModalLease | None: ...

    def show_activity_modal(self, lease: ShellActivityModalLease) -> bool: ...

    def dismiss_activity_modal(self, lease: ShellActivityModalLease) -> bool: ...

    def abandon_activity_modal(self, lease: ShellActivityModalLease) -> None: ...


class NoopShellWindowController:
    """Backend-neutral development hook with no trusted modal implementation."""

    backend_id = "noop-shell-window"

    def after_window_created(self, pygame: Any) -> bool:
        del pygame
        return True

    def after_activity_return(self, pygame: Any) -> bool:
        del pygame
        return True

    def prepare_activity_modal(
        self,
        pygame: Any,
        *,
        session_id: str,
        activity_pid: int,
    ) -> ShellActivityModalLease | None:
        del pygame, session_id, activity_pid
        # Fail closed: a host window with no selected trusted backend must not
        # claim it can cover or restore a live Activity.
        return None

    def show_activity_modal(self, lease: ShellActivityModalLease) -> bool:
        del lease
        return False

    def dismiss_activity_modal(self, lease: ShellActivityModalLease) -> bool:
        del lease
        return False

    def abandon_activity_modal(self, lease: ShellActivityModalLease) -> None:
        del lease


__all__ = [
    "NoopShellWindowController",
    "ShellActivityModalLease",
    "ShellWindowController",
]
