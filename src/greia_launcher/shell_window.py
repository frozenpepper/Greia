from __future__ import annotations

from typing import Any, Protocol


class ShellWindowController(Protocol):
    """Backend-private setup for Greia's own Shell window.

    The controller is a trusted launcher collaborator, not an Activity API.
    Implementations may use backend-specific focus/session mechanics while the
    generic launcher remains ignorant of X11, Wayland or future display stacks.

    This hook is intentionally one-shot: it runs after the Shell SDL window is
    created. It must not introduce a polling loop or per-frame work.
    """

    @property
    def backend_id(self) -> str: ...

    def after_window_created(self, pygame: Any) -> bool: ...


class NoopShellWindowController:
    """No-op implementation for tests/backends that need no setup."""

    backend_id = "noop-shell-window"

    def after_window_created(self, pygame: Any) -> bool:
        del pygame
        return True


__all__ = ["NoopShellWindowController", "ShellWindowController"]
