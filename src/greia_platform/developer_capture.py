from __future__ import annotations

import argparse
import io
import os
import sys
from typing import Sequence


class DeveloperCaptureError(RuntimeError):
    """Raised when a development-only display capture cannot be produced."""


def capture_legacy_x11_png(display: str = ":0") -> bytes:
    """Capture the current X11 screen as PNG for development evidence.

    This is deliberately a compatibility implementation, not an R7 display
    architecture decision. The caller is expected to execute as the Greia
    display-session user so no X authority is delegated to the SSH account.
    """

    if not display or len(display) > 64 or any(ch.isspace() for ch in display):
        raise DeveloperCaptureError("display selector is invalid")
    os.environ["DISPLAY"] = display
    try:
        from PIL import ImageGrab

        image = ImageGrab.grab(xdisplay=display)
    except Exception as exc:  # Pillow/XCB/backend failures are runtime evidence.
        raise DeveloperCaptureError(f"X11 screenshot capture failed: {exc}") from exc
    output = io.BytesIO()
    image.save(output, format="PNG")
    payload = output.getvalue()
    if len(payload) < 8 or payload[:8] != b"\x89PNG\r\n\x1a\n":
        raise DeveloperCaptureError("capture backend did not produce PNG data")
    return payload


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Greia development-only display capture")
    parser.add_argument("--display", default=":0")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        payload = capture_legacy_x11_png(args.display)
    except DeveloperCaptureError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    sys.stdout.buffer.write(payload)
    sys.stdout.buffer.flush()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
