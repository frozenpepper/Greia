from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Sequence


DEVELOPER_MARKER = Path("/etc/greia-os/developer-remote")
DISPLAY_USER = "greiakid"
DISPLAY_NAME = ":0"
_KEY_RE = re.compile(r"^[A-Za-z0-9_+.:=-]{1,64}$")


class DeveloperInputError(RuntimeError):
    """Raised when development-only GUI input injection must fail closed."""


def _require_developer_root() -> None:
    if os.geteuid() != 0:
        raise DeveloperInputError("developer input helper must run through greia-devctl sudo")
    if not DEVELOPER_MARKER.is_file():
        raise DeveloperInputError("developer remote control is not enabled on this image")


def _run_xdotool(args: Sequence[str]) -> None:
    argv = [
        "runuser",
        "--user",
        DISPLAY_USER,
        "--",
        "/usr/bin/env",
        f"DISPLAY={DISPLAY_NAME}",
        "/usr/bin/xdotool",
        *args,
    ]
    completed = subprocess.run(argv, check=False, capture_output=True, text=True)
    if completed.returncode != 0:
        raise DeveloperInputError(
            f"xdotool failed with status {completed.returncode}: {completed.stderr.strip()}"
        )


def key(keys: Sequence[str]) -> None:
    if not keys or len(keys) > 16:
        raise DeveloperInputError("key accepts between 1 and 16 key expressions")
    for value in keys:
        if not _KEY_RE.fullmatch(value):
            raise DeveloperInputError(f"invalid xdotool key expression: {value!r}")
    _run_xdotool(["key", "--clearmodifiers", *keys])


def mousemove(x: int, y: int) -> None:
    for name, value in (("x", x), ("y", y)):
        if isinstance(value, bool) or value < 0 or value > 16384:
            raise DeveloperInputError(f"mouse {name} coordinate must be between 0 and 16384")
    _run_xdotool(["mousemove", "--sync", str(x), str(y)])


def click(button: int) -> None:
    if isinstance(button, bool) or button < 1 or button > 5:
        raise DeveloperInputError("mouse button must be between 1 and 5")
    _run_xdotool(["click", "--clearmodifiers", str(button)])


def type_text(text: str) -> None:
    if not text or len(text) > 512 or "\x00" in text or "\n" in text or "\r" in text:
        raise DeveloperInputError("typed text must be 1..512 characters on one line")
    _run_xdotool(["type", "--clearmodifiers", "--delay", "10", "--", text])


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Greia development-only GUI input control")
    sub = parser.add_subparsers(dest="command", required=True)
    key_parser = sub.add_parser("key")
    key_parser.add_argument("keys", nargs="+")
    move = sub.add_parser("mousemove")
    move.add_argument("x", type=int)
    move.add_argument("y", type=int)
    click_parser = sub.add_parser("click")
    click_parser.add_argument("button", type=int, nargs="?", default=1)
    type_parser = sub.add_parser("type")
    type_parser.add_argument("text")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        _require_developer_root()
        if args.command == "key":
            key(args.keys)
        elif args.command == "mousemove":
            mousemove(args.x, args.y)
        elif args.command == "click":
            click(args.button)
        elif args.command == "type":
            type_text(args.text)
        else:  # pragma: no cover
            raise DeveloperInputError("unsupported input command")
    except DeveloperInputError as exc:
        print(f"greia-devctl: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
