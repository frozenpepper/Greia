"""Trusted simulator bootstrap for current Pygame/Python Activities.

The runtime adapter executes this file by absolute Greia-owned path, never via
an importable module name resolved from Activity content. Existing Python
Activities still own ``pygame.display.set_mode`` while R7 is open, so this
bootstrap adapts only that renderer call to the selected synthetic viewport.
Simulator identity is not part of the Activity environment contract.
"""

from __future__ import annotations

import argparse
import io
import json
import os
import queue
import runpy
import sys
import threading
import time
import urllib.request
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
    remote_port: int = 0,
) -> Callable[..., Any]:
    """Install the narrow simulator display adapter and return the original call."""

    # Import before the Activity package is added to sys.path. This prevents a
    # package-local pygame module from replacing the trusted renderer dependency
    # used to establish the synthetic surface.
    import pygame
    from greia_platform.system_chrome import ActivitySystemChromeLayout
    from greia_platform.activity_ui import draw_home_symbol, draw_back_symbol

    original = pygame.display.set_mode
    original_flip = pygame.display.flip
    original_update = pygame.display.update
    original_get_events = pygame.event.get

    frame_queue: queue.Queue[bytes] = queue.Queue(maxsize=2)
    last_frame_sent = [0.0]
    last_event_poll = [0.0]
    pending_events: list[Any] = []

    def _frame_worker() -> None:
        while True:
            try:
                png_bytes = frame_queue.get()
                req = urllib.request.Request(
                    f"http://127.0.0.1:{remote_port}/api/frame",
                    data=png_bytes,
                    headers={"Content-Type": "image/png"},
                    method="POST",
                )
                with urllib.request.urlopen(req, timeout=0.5):
                    pass
            except Exception:
                pass

    if remote_port > 0:
        threading.Thread(target=_frame_worker, name="greia-sim-act-frame", daemon=True).start()

    def _maybe_post_frame(surface: pygame.Surface | None) -> None:
        if remote_port <= 0 or surface is None:
            return
        now = time.monotonic()
        if now - last_frame_sent[0] < 0.030:
            return
        last_frame_sent[0] = now
        try:
            from PIL import Image

            data_rgb = pygame.image.tobytes(surface, "RGB")
            img = Image.frombytes("RGB", surface.get_size(), data_rgb)
            buf = io.BytesIO()
            img.save(buf, format="PNG", compress_level=1)
            data = buf.getvalue()
            if not frame_queue.full():
                frame_queue.put_nowait(data)
        except Exception:
            pass

    def _poll_remote_events() -> None:
        if remote_port <= 0:
            return
        now = time.monotonic()
        if now - last_event_poll[0] < 0.015:
            return
        last_event_poll[0] = now
        try:
            req = urllib.request.Request(f"http://127.0.0.1:{remote_port}/api/events")
            with urllib.request.urlopen(req, timeout=0.2) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            raw_list = data.get("events", [])
            for item in raw_list:
                ev_type = item.get("type")
                if ev_type == "key":
                    key_code = _resolve_pygame_key(item.get("key", ""), pygame)
                    action = item.get("action", "press")
                    if key_code is not None:
                        if action in {"down", "press"}:
                            pending_events.append(pygame.event.Event(pygame.KEYDOWN, key=key_code))
                        if action in {"up", "press"}:
                            pending_events.append(pygame.event.Event(pygame.KEYUP, key=key_code))
                elif ev_type == "text":
                    text = str(item.get("text", ""))
                    if text:
                        pending_events.append(pygame.event.Event(pygame.TEXTINPUT, text=text))
                elif ev_type == "mouse":
                    x = int(item.get("x", 0))
                    y = int(item.get("y", 0))
                    action = item.get("action", "click")
                    button = int(item.get("button", 1))
                    pending_events.append(pygame.event.Event(pygame.MOUSEMOTION, pos=(x, y), rel=(0, 0), buttons=(0, 0, 0)))
                    if action in {"down", "click"}:
                        pending_events.append(pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=(x, y), button=button))
                    if action in {"up", "click"}:
                        pending_events.append(pygame.event.Event(pygame.MOUSEBUTTONUP, pos=(x, y), button=button))
        except Exception:
            pass

    def _draw_chrome_overlay(surface: pygame.Surface | None) -> None:
        if surface is None:
            return
        w, h = surface.get_size()
        try:
            chrome = ActivitySystemChromeLayout.for_surface(w, h)
            hb = chrome.home_hitbox
            home_rect = pygame.Rect(hb.x, hb.y, hb.width, hb.height)

            # Drop shadow
            shadow_rect = home_rect.move(0, 3)
            pygame.draw.rect(
                surface,
                (0, 0, 0, 40) if surface.get_flags() & pygame.SRCALPHA else (180, 160, 140),
                shadow_rect,
                border_radius=max(8, home_rect.width // 3),
            )

            # Warm tactile Home button pill
            pygame.draw.rect(
                surface,
                (255, 252, 245),
                home_rect,
                border_radius=max(8, home_rect.width // 3),
            )
            # Subtle top bevel highlight
            highlight_rect = pygame.Rect(home_rect.x + 2, home_rect.y + 2, home_rect.width - 4, home_rect.height // 2)
            pygame.draw.rect(
                surface,
                (255, 255, 255),
                highlight_rect,
                border_top_left_radius=max(6, home_rect.width // 3 - 2),
                border_top_right_radius=max(6, home_rect.width // 3 - 2),
            )
            # Outline
            pygame.draw.rect(
                surface,
                (78, 56, 40),
                home_rect,
                width=max(2, home_rect.width // 24),
                border_radius=max(8, home_rect.width // 3),
            )
            draw_home_symbol(surface, home_rect, (78, 56, 40))

            # If Back button is available, draw Back button pill
            if chrome.back_available:
                bb = chrome.back_hitbox
                back_rect = pygame.Rect(bb.x, bb.y, bb.width, bb.height)
                # Drop shadow
                back_shadow = back_rect.move(0, 3)
                pygame.draw.rect(
                    surface,
                    (0, 0, 0, 40) if surface.get_flags() & pygame.SRCALPHA else (180, 160, 140),
                    back_shadow,
                    border_radius=max(8, back_rect.width // 3),
                )
                pygame.draw.rect(
                    surface,
                    (255, 252, 245),
                    back_rect,
                    border_radius=max(8, back_rect.width // 3),
                )
                pygame.draw.rect(
                    surface,
                    (78, 56, 40),
                    back_rect,
                    width=max(2, back_rect.width // 24),
                    border_radius=max(8, back_rect.width // 3),
                )
                draw_back_symbol(surface, back_rect, (78, 56, 40))

            # Draw cursor on top of all chrome overlays when mouse is focused
            if pygame.mouse.get_focused():
                mx, my = pygame.mouse.get_pos()
                if 0 <= mx < w and 0 <= my < h:
                    cursor_pts = [
                        (mx, my),
                        (mx, my + 18),
                        (mx + 5, my + 14),
                        (mx + 10, my + 21),
                        (mx + 13, my + 19),
                        (mx + 8, my + 12),
                        (mx + 14, my + 12),
                    ]
                    pygame.draw.polygon(surface, (61, 44, 31), cursor_pts)
                    inner_pts = [
                        (mx + 1, my + 2),
                        (mx + 1, my + 15),
                        (mx + 5, my + 12),
                        (mx + 9, my + 18),
                        (mx + 11, my + 17),
                        (mx + 7, my + 11),
                        (mx + 12, my + 11),
                    ]
                    pygame.draw.polygon(surface, (255, 255, 255), inner_pts)
        except Exception:
            pass

    def simulator_flip():
        surface = pygame.display.get_surface()
        _draw_chrome_overlay(surface)
        _maybe_post_frame(surface)
        return original_flip()

    def simulator_update(*args, **kwargs):
        surface = pygame.display.get_surface()
        _draw_chrome_overlay(surface)
        _maybe_post_frame(surface)
        return original_update(*args, **kwargs)

    def simulator_get_events(*args, **kwargs):
        _poll_remote_events()
        events = list(original_get_events(*args, **kwargs))
        if pending_events:
            events.extend(pending_events)
            pending_events.clear()
        surface = pygame.display.get_surface()
        if surface is not None:
            w, h = surface.get_size()
            try:
                chrome = ActivitySystemChromeLayout.for_surface(w, h)
                for event in events:
                    if (
                        event.type in (pygame.MOUSEBUTTONUP, pygame.MOUSEBUTTONDOWN)
                        and getattr(event, "button", None) == 1
                    ):
                        if chrome.home_hitbox.contains(event.pos[0], event.pos[1]):
                            raise SystemExit(0)
            except SystemExit:
                raise
            except Exception:
                pass
        return events

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
    pygame.display.flip = simulator_flip
    pygame.display.update = simulator_update
    pygame.event.get = simulator_get_events
    return original


def _resolve_pygame_key(name: str, pygame: Any) -> int | None:
    name_upper = name.upper()
    named_map = {
        "LEFT": pygame.K_LEFT,
        "RIGHT": pygame.K_RIGHT,
        "UP": pygame.K_UP,
        "DOWN": pygame.K_DOWN,
        "RETURN": pygame.K_RETURN,
        "ENTER": pygame.K_RETURN,
        "ESCAPE": pygame.K_ESCAPE,
        "ESC": pygame.K_ESCAPE,
        "TAB": pygame.K_TAB,
        "SPACE": pygame.K_SPACE,
        "BACKSPACE": pygame.K_BACKSPACE,
    }
    if name_upper in named_map:
        return named_map[name_upper]
    if len(name) == 1:
        return ord(name.lower())
    return None


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


def run_activity(
    entrypoint: Path,
    *,
    target_size: tuple[int, int],
    remote_port: int = 0,
) -> None:
    root_raw = os.environ.get("GREIA_ACTIVITY_ROOT", "").strip()
    if not root_raw:
        raise RuntimeError("simulated Activity launch has no GREIA_ACTIVITY_ROOT")
    root = Path(root_raw).resolve(strict=True)
    path = entrypoint.resolve(strict=True)
    if not path.is_file() or root not in path.parents:
        raise RuntimeError("simulated Activity entrypoint escaped its validated package")

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

    if remote_port > 0:
        install_pygame_display_patch(target_size, remote_port=remote_port)
    else:
        install_pygame_display_patch(target_size)

    runpy.run_path(str(path), run_name="__main__")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="trusted Greia simulator Python bootstrap")
    parser.add_argument("--viewport", required=True)
    parser.add_argument("--remote-port", type=int, default=0)
    parser.add_argument("entrypoint", type=Path)
    args = parser.parse_args(sys.argv[1:] if argv is None else argv)
    run_activity(
        args.entrypoint,
        target_size=_parse_target_viewport(args.viewport),
        remote_port=args.remote_port,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
