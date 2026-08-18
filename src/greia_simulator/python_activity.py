"""Simulator bootstrap for current Pygame/Python Activities.

Production Greia deliberately keeps display ownership below the Activity
contract. Existing Python Activities still open their SDL/Pygame display
surface directly while R7 is open. The simulator therefore adapts that one
renderer call *inside the simulator child process only*: fullscreen/physical
requests are converted to the selected synthetic viewport. All Greia SDK,
lifecycle, storage, history and permission behavior remains real.
"""

from __future__ import annotations

import os
import runpy
import sys
from pathlib import Path
from typing import Any, Callable

from .device import parse_viewport


def normalize_display_request(
    requested_size: tuple[int, int] | list[int] | None,
    flags: int,
    *,
    target_size: tuple[int, int],
    fullscreen_flag: int,
) -> tuple[tuple[int, int], int]:
    """Force a Pygame display request onto the exact synthetic viewport."""

    del requested_size
    return target_size, int(flags) & ~int(fullscreen_flag)


def install_pygame_display_patch(
    target_size: tuple[int, int],
) -> Callable[..., Any]:
    """Install the narrow simulator display adapter and return the original call."""

    import pygame

    original = pygame.display.set_mode

    def simulator_set_mode(
        size=(0, 0),
        flags=0,
        depth=0,
        display=0,
        vsync=0,
    ):
        normalized_size, normalized_flags = normalize_display_request(
            size,
            flags,
            target_size=target_size,
            fullscreen_flag=pygame.FULLSCREEN,
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

    pygame.display.set_mode = simulator_set_mode
    return original


def run_activity(entrypoint: Path) -> None:
    root_raw = os.environ.get("GREIA_ACTIVITY_ROOT", "").strip()
    if not root_raw:
        raise RuntimeError("simulated Activity launch has no GREIA_ACTIVITY_ROOT")
    root = Path(root_raw).resolve(strict=True)
    path = entrypoint.resolve(strict=True)
    if not path.is_file() or root not in path.parents:
        raise RuntimeError("simulated Activity entrypoint escaped its validated package")

    target = parse_viewport(os.environ.get("GREIA_SIMULATOR_VIEWPORT", "1024x600"))
    install_pygame_display_patch(target)

    package_path = str(root)
    if package_path not in sys.path:
        sys.path.insert(0, package_path)
    runpy.run_path(str(path), run_name="__main__")


def main(argv: list[str] | None = None) -> int:
    arguments = list(sys.argv[1:] if argv is None else argv)
    if len(arguments) != 1:
        raise SystemExit("usage: python -m greia_simulator.python_activity ENTRYPOINT")
    run_activity(Path(arguments[0]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
