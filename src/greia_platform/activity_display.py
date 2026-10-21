"""Platform-owned normalization of Activity display requests.

Current Python Activities still call ``pygame.display.set_mode`` themselves
while the R7 display/session migration remains open.  The real surface belongs
to the platform, not to an Activity: a first-party Activity authored on the
1024x600 reference canvas must fill a 1280x800 panel instead of opening a
smaller window on top of the Shell.  A smaller window is not merely cosmetic;
the uncovered Shell window keeps its old pixels and its hidden pointer, which
looks like a rendering/input fault around the Activity.

The trusted entry point installs this narrow adapter when an Activity is
launched by a Greia session.  It rewrites only the requested display size to
the session viewport and leaves the Activity's Pygame flags alone.  The
Simulator has its own synthetic-viewport adapter; this module is the
production counterpart.
"""

from __future__ import annotations

import os
from typing import Any, Callable, Mapping, MutableMapping

#: Platform-owned session viewport passed from the Shell to the Activity entry.
VIEWPORT_ENVIRONMENT = "GREIA_ACTIVITY_VIEWPORT"

_MIN_WIDTH = 320
_MAX_WIDTH = 7680
_MIN_HEIGHT = 240
_MAX_HEIGHT = 4320


def parse_viewport(value: str | None) -> tuple[int, int] | None:
    """Parse one bounded ``WIDTHxHEIGHT`` session viewport, or return None."""

    if not isinstance(value, str):
        return None
    left, separator, right = value.strip().lower().partition("x")
    if not separator or not left.isdigit() or not right.isdigit():
        return None
    width = int(left)
    height = int(right)
    if not (_MIN_WIDTH <= width <= _MAX_WIDTH and _MIN_HEIGHT <= height <= _MAX_HEIGHT):
        return None
    return width, height


def remember_viewport(
    size: tuple[int, int],
    *,
    environment: MutableMapping[str, str] | None = None,
) -> None:
    """Record the current Shell surface size for the next Activity launch."""

    width, height = int(size[0]), int(size[1])
    if not (_MIN_WIDTH <= width <= _MAX_WIDTH and _MIN_HEIGHT <= height <= _MAX_HEIGHT):
        return
    target = os.environ if environment is None else environment
    target[VIEWPORT_ENVIRONMENT] = f"{width}x{height}"


def current_display_size(pygame: Any, display_index: int = 0) -> tuple[int, int] | None:
    """Return the real desktop size without requiring the platform to own SDL."""

    try:
        sizes = pygame.display.get_desktop_sizes()
    except Exception:
        sizes = ()
    if sizes:
        index = display_index if 0 <= display_index < len(sizes) else 0
        try:
            width, height = (int(value) for value in sizes[index])
        except (TypeError, ValueError):
            width = height = 0
        if _MIN_WIDTH <= width <= _MAX_WIDTH and _MIN_HEIGHT <= height <= _MAX_HEIGHT:
            return width, height
    try:
        info = pygame.display.Info()
        width, height = int(info.current_w), int(info.current_h)
    except Exception:
        return None
    if _MIN_WIDTH <= width <= _MAX_WIDTH and _MIN_HEIGHT <= height <= _MAX_HEIGHT:
        return width, height
    return None


def target_viewport(
    pygame: Any,
    *,
    environ: Mapping[str, str] | None = None,
    display_index: int = 0,
) -> tuple[int, int] | None:
    """Resolve the platform viewport, preferring the Shell's recorded size."""

    environment = os.environ if environ is None else environ
    configured = parse_viewport(environment.get(VIEWPORT_ENVIRONMENT))
    if configured is not None:
        return configured
    return current_display_size(pygame, display_index)


def normalize_display_request(
    requested_size: Any,
    flags: int,
    *,
    target_size: tuple[int, int] | None,
) -> tuple[Any, int]:
    """Replace a requested window size with the platform target size.

    Flags are deliberately preserved: an Activity that asks for ``FULLSCREEN``
    stays fullscreen; one that asks for ``RESIZABLE`` gets a window exactly the
    size of the session surface.  The platform never stretches the logical
    canvas here; ``PygameReferenceCanvas``/``ChildUiMetrics`` still own the
    reference-to-physical mapping.
    """

    if target_size is None:
        return requested_size, int(flags)
    return target_size, int(flags)


def install_display_request_policy(
    pygame: Any,
    *,
    environ: Mapping[str, str] | None = None,
) -> Callable[..., Any]:
    """Wrap ``pygame.display.set_mode`` to fill the current session viewport.

    Returns the original ``set_mode`` call.  The wrapper is intentionally
    last-call safe: the launch cover wraps whatever function it finds, so the
    cover's hidden/shown calls still pass through this normalization.
    """

    display = pygame.display
    original = display.set_mode

    def set_mode(size=(0, 0), flags=0, depth=0, display=0, vsync=0):
        target = target_viewport(pygame, environ=environ, display_index=display)
        normalized_size, normalized_flags = normalize_display_request(
            size, flags, target_size=target
        )
        try:
            return original(
                normalized_size,
                normalized_flags,
                depth,
                display=display,
                vsync=vsync,
            )
        except TypeError:
            return original(normalized_size, normalized_flags, depth)

    display.set_mode = set_mode
    return original
