#!/usr/bin/env python3
"""Profile the production launcher draw path at a chosen viewport.

This is the measurement instrument for launcher frame-pacing work. It runs the
real ``GreiaChildShell`` presentation under SDL's dummy video driver and times
the exact phases that dominate perceived Shell responsiveness:

  A  theme background alone (fill + wallpaper)
  B  steady cached frame (cache hit, pointer parked, flip included)
  C  hover transition frames (pointer alternating between two cards)
  D  full rebuild frames (scene cache invalidated every frame)

Run it on the reference hardware (or any host) with:

  PYTHONPATH=src python3 tools/profile_launcher_draw.py

The numbers describe software-rendered Pygame behavior for the tested source
tree and display driver only; they are developer diagnostics and never physical
device acceptance evidence by themselves.
"""
from __future__ import annotations

import os
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ.setdefault("GREIA_OS_ROOT", str(REPO_ROOT))
_STATE_DIR = os.environ.get("GREIA_PROFILE_BENCH_STATE", "/tmp/greia-launcher-profile")
os.environ.setdefault("GREIA_PROFILES_DIR", os.path.join(_STATE_DIR, "profiles"))
os.environ.setdefault(
    "GREIA_ACTIVE_PROFILE_STATUS", os.path.join(_STATE_DIR, "active-profile.json")
)
os.environ.setdefault("GREIA_SKIP_BOOT_HANDOFF", "1")

import pygame  # noqa: E402


def _timed(label: str, func, seconds: float) -> float:
    count = 0
    start = time.perf_counter()
    while True:
        func()
        count += 1
        elapsed = time.perf_counter() - start
        if elapsed >= seconds:
            break
    per_ms = elapsed / count * 1000.0
    print(f"{label:<44} {per_ms:8.2f} ms/frame   ({count} frames, {1000.0/per_ms:6.1f} fps)")
    return per_ms


def main() -> int:
    Path(os.environ["GREIA_PROFILES_DIR"]).mkdir(parents=True, exist_ok=True)

    from greia_launcher.child_shell import GreiaChildShell

    pygame.init()
    pygame.font.init()
    screen = pygame.display.set_mode((1024, 600))
    app = GreiaChildShell(windowed=True, allow_exit=True)
    app.profiles = app.profile_store.ensure_initialized()
    if not app.profiles:
        print("no profiles available; cannot enter child mode", file=sys.stderr)
        return 2
    app._activate_profile(app.profiles[0], pygame)
    app._synthetic_pointer_active = True
    category_id = next(
        (
            collection.collection_id
            for collection in app._catalogue.collections
            if collection.collection_id != "all" and collection.items
        ),
        None,
    )
    if category_id is None:
        print("no populated collection available", file=sys.stderr)
        return 2
    app._set_category(category_id)
    app._draw(screen, pygame)  # warm every cache once

    def background() -> None:
        app.theme_controller.draw_background(screen, pygame)

    def steady() -> None:
        app._targets.clear()
        theme = app.theme_controller.draw_background(screen, pygame)
        app._draw_activities(screen, theme, pygame)
        app._draw_pointer(screen, pygame)
        pygame.display.flip()

    swap_state = {"index": 0}

    def hover_swap() -> None:
        points = [
            target.rect.center
            for target in app._cached_activities_targets
            if target.action == "presented_activity"
        ]
        if len(points) < 2:
            points = [(200, 200), (600, 300)]
        swap_state["index"] ^= 1
        app._pointer_position = points[swap_state["index"]]
        steady()

    def rebuild() -> None:
        app._cached_activities_key = None
        steady()

    print(f"category={app._category_id} cards={len(app._presented_activities)}")
    _timed("A background (fill+wallpaper)", background, 2.0)
    _timed("B steady cached frame (+flip)", steady, 2.0)
    _timed("C hover transition frame (+flip)", hover_swap, 4.0)
    _timed("D full rebuild frame (+flip)", rebuild, 4.0)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
