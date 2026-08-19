"""Trusted simulator bootstrap for current Pygame/Python Activities.

The runtime adapter executes this file by absolute Greia-owned path, never via
an importable module name resolved from Activity content. Existing Python
Activities still own ``pygame.display.set_mode`` while R7 is open, so this
bootstrap adapts only that renderer call to the selected synthetic viewport.
Simulator identity is not part of the Activity environment contract.
"""

from __future__ import annotations

import argparse
import os
import runpy
import sys
from pathlib import Path
from typing import Any, Callable


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

    # Import before the Activity package is added to sys.path. This prevents a
    # package-local pygame module from replacing the trusted renderer dependency
    # used to establish the synthetic surface.
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


def _parse_target_viewport(value: str) -> tuple[int, int]:
    """Validate the adapter-owned command argument without importing packages."""

    left, separator, right = value.strip().lower().partition("x")
    if not separator or not left.isdigit() or not right.isdigit():
        raise ValueError("trusted simulator viewport must use WIDTHxHEIGHT")
    width = int(left)
    height = int(right)
    if not 320 <= width <= 7680 or not 240 <= height <= 4320:
        raise ValueError("trusted simulator viewport is outside supported bounds")
    return width, height


def run_activity(entrypoint: Path, *, target_size: tuple[int, int]) -> None:
    root_raw = os.environ.get("GREIA_ACTIVITY_ROOT", "").strip()
    if not root_raw:
        raise RuntimeError("simulated Activity launch has no GREIA_ACTIVITY_ROOT")
    root = Path(root_raw).resolve(strict=True)
    path = entrypoint.resolve(strict=True)
    if not path.is_file() or root not in path.parents:
        raise RuntimeError("simulated Activity entrypoint escaped its validated package")

    install_pygame_display_patch(target_size)

    # Defensive cleanup for stale callers/older workspaces. Simulator identity
    # is private launch plumbing, never an Activity-facing feature flag.
    for name in tuple(os.environ):
        if name.startswith("GREIA_SIMULATOR"):
            os.environ.pop(name, None)

    # ActivitySupervisor deliberately strips inherited PYTHONPATH. Re-establish
    # only the Greia-owned source root required by the curated Activity runtime,
    # and keep it ahead of Activity content so trusted platform modules cannot be
    # shadowed even if a future validation regression misses a reserved name.
    trusted_source = str(Path(__file__).resolve().parents[1])
    package_path = str(root)
    sys.path[:] = [
        item
        for item in sys.path
        if item not in {trusted_source, package_path}
    ]
    sys.path.insert(0, package_path)
    sys.path.insert(0, trusted_source)
    runpy.run_path(str(path), run_name="__main__")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="trusted Greia simulator Python bootstrap")
    parser.add_argument("--viewport", required=True)
    parser.add_argument("entrypoint", type=Path)
    args = parser.parse_args(sys.argv[1:] if argv is None else argv)
    run_activity(args.entrypoint, target_size=_parse_target_viewport(args.viewport))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
