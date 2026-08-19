#!/usr/bin/env python3
"""CLI utility to interact with and control the running Greia Activity Simulator."""
from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path


DEFAULT_URL = "http://127.0.0.1:8767"


def request_json(url: str, method: str = "GET", data: dict | None = None) -> dict:
    req = urllib.request.Request(url, method=method)
    if data is not None:
        body = json.dumps(data).encode("utf-8")
        req.add_header("Content-Type", "application/json")
        req.data = body
    with urllib.request.urlopen(req, timeout=5.0) as resp:
        return json.loads(resp.read().decode("utf-8"))


def get_bytes(url: str) -> bytes:
    with urllib.request.urlopen(url, timeout=5.0) as resp:
        return resp.read()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Greia Activity Simulator Control Tool")
    parser.add_argument("--url", default=DEFAULT_URL, help="Simulator remote bridge URL")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # status
    subparsers.add_parser("status", help="Get current simulator state")

    # screenshot
    p_screen = subparsers.add_parser("screenshot", help="Capture screenshot to file")
    p_screen.add_argument("output", nargs="?", default="screenshot.png", help="Output PNG path")

    # key
    p_key = subparsers.add_parser("key", help="Send key event")
    p_key.add_argument("key_name", help="Key name (LEFT, RIGHT, UP, DOWN, RETURN, ESCAPE, TAB, SPACE, etc.)")
    p_key.add_argument("--action", choices=["press", "down", "up"], default="press", help="Key action")

    # text
    p_text = subparsers.add_parser("text", help="Send text input")
    p_text.add_argument("text", help="Text to type")

    # click
    p_click = subparsers.add_parser("click", help="Send mouse click")
    p_click.add_argument("x", type=int, help="X coordinate")
    p_click.add_argument("y", type=int, help="Y coordinate")
    p_click.add_argument("--button", type=int, default=1, help="Mouse button (1=left, 3=right)")

    # move
    p_move = subparsers.add_parser("move", help="Send mouse move")
    p_move.add_argument("x", type=int, help="X coordinate")
    p_move.add_argument("y", type=int, help="Y coordinate")

    # chord
    p_chord = subparsers.add_parser("chord", help="Hold keys simultaneously for a duration")
    p_chord.add_argument("keys", nargs="+", help="Keys to hold (e.g. 's' 't')")
    p_chord.add_argument("--duration", type=float, default=5.0, help="Hold duration in seconds")

    args = parser.parse_args(argv)

    try:
        if args.command == "status":
            state = request_json(f"{args.url}/api/state")
            print(json.dumps(state, indent=2))
            return 0

        if args.command == "screenshot":
            png_bytes = get_bytes(f"{args.url}/api/frame")
            output_path = Path(args.output).resolve()
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_bytes(png_bytes)
            print(f"Screenshot saved to: {output_path} ({len(png_bytes)} bytes)")
            return 0

        if args.command == "key":
            resp = request_json(
                f"{args.url}/api/input/key",
                method="POST",
                data={"key": args.key_name, "action": args.action},
            )
            print(f"Key {args.key_name} ({args.action}): {resp}")
            return 0

        if args.command == "text":
            resp = request_json(
                f"{args.url}/api/input/text",
                method="POST",
                data={"text": args.text},
            )
            print(f"Text '{args.text}': {resp}")
            return 0

        if args.command == "click":
            resp = request_json(
                f"{args.url}/api/input/mouse",
                method="POST",
                data={"x": args.x, "y": args.y, "action": "click", "button": args.button},
            )
            print(f"Click ({args.x}, {args.y}): {resp}")
            return 0

        if args.command == "move":
            resp = request_json(
                f"{args.url}/api/input/mouse",
                method="POST",
                data={"x": args.x, "y": args.y, "action": "move", "button": 0},
            )
            print(f"Move ({args.x}, {args.y}): {resp}")
            return 0

        if args.command == "chord":
            resp = request_json(
                f"{args.url}/api/input/chord",
                method="POST",
                data={"keys": args.keys, "duration": args.duration},
            )
            print(f"Chord {args.keys} for {args.duration}s: {resp}")
            return 0

    except urllib.error.URLError as exc:
        print(f"Error connecting to simulator at {args.url}: {exc}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
