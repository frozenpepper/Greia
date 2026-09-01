from __future__ import annotations

from typing import Any, Protocol


class ShellWindowController(Protocol):
    """Backend-private lifecycle hooks for Greia's own Shell window.

    The controller is a trusted launcher collaborator, not an Activity API.
    Implementations may use backend-specific focus/session mechanics while the
    generic launcher remains ignorant of X11, Wayland or future display stacks.

    Hooks are deliberately bounded lifecycle operations: once after Shell
    window creation and once after an Activity returns. They must not introduce
    polling, background workers or per-frame work.
    """

    @property
    def backend_id(self) -> str: ...

    def after_window_created(self, pygame: Any) -> bool: ...

    def after_activity_return(self, pygame: Any) -> bool: ...


class NoopShellWindowController:
    """No-op implementation for tests/backends that need no setup."""

    backend_id = "noop-shell-window"

    def after_window_created(self, pygame: Any) -> bool:
        del pygame
        return True

    def after_activity_return(self, pygame: Any) -> bool:
        del pygame
        return True


__all__ = ["NoopShellWindowController", "ShellWindowController"]
