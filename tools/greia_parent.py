#!/usr/bin/env python3
"""Repository entry point for the Greia Parents Web App."""

from __future__ import annotations

import argparse
import os
import sys
import webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "src"
TOOLS = str(Path(__file__).resolve().parent)

while TOOLS in sys.path:
    sys.path.remove(TOOLS)
if str(SOURCE) not in sys.path:
    sys.path.insert(0, str(SOURCE))

from greia_parent.update_api import UpdateParentApiApplication, UpdateParentApiHTTPServer  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Greia Parents Web App")
    parser.add_argument("--bind", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8766)
    parser.add_argument(
        "--root",
        type=Path,
        default=Path(os.environ.get("GREIA_OS_ROOT", str(ROOT))),
    )
    default_dev_dir = Path.home() / ".greia" / "parent_app"
    parser.add_argument(
        "--state-dir",
        type=Path,
        default=Path(os.environ.get("GREIA_STATE_DIR", str(default_dev_dir / "state"))),
    )
    parser.add_argument(
        "--profiles-dir",
        type=Path,
        default=Path(os.environ.get("GREIA_PROFILES_DIR", str(default_dev_dir / "profiles"))),
    )
    parser.add_argument(
        "--hardware-settings-dir",
        type=Path,
        default=Path(
            os.environ.get(
                "GREIA_SYSTEM_SETTINGS_DIR",
                str(default_dev_dir / "hardware"),
            )
        ),
    )
    parser.add_argument(
        "--hardware-status-path",
        type=Path,
        default=Path(
            os.environ.get(
                "GREIA_HARDWARE_STATUS",
                str(default_dev_dir / "hardware-status.json"),
            )
        ),
    )
    parser.add_argument(
        "--active-profile-status-path",
        type=Path,
        default=Path(
            os.environ.get(
                "GREIA_ACTIVE_PROFILE_STATUS",
                str(default_dev_dir / "active-profile.json"),
            )
        ),
    )
    parser.add_argument("--no-open", action="store_true", help="Do not open browser automatically")

    args = parser.parse_args(argv)

    args.state_dir.mkdir(parents=True, exist_ok=True)
    args.profiles_dir.mkdir(parents=True, exist_ok=True)
    args.hardware_settings_dir.mkdir(parents=True, exist_ok=True)
    args.hardware_status_path.parent.mkdir(parents=True, exist_ok=True)
    args.active_profile_status_path.parent.mkdir(parents=True, exist_ok=True)

    app = UpdateParentApiApplication(
        args.root,
        args.state_dir,
        hardware_settings_dir=args.hardware_settings_dir,
        hardware_status_path=args.hardware_status_path,
        profiles_dir=args.profiles_dir,
        active_profile_status_path=args.active_profile_status_path,
    )

    pairing_url = f"http://{args.bind}:{args.port}/pair?token={app.token}"
    print(f"Greia Parents server listening on http://{args.bind}:{args.port}")
    print(f"Pairing URL: {pairing_url}")
    print(f"Token: {app.token}")

    if not args.no_open:
        webbrowser.open(pairing_url)

    server = UpdateParentApiHTTPServer((args.bind, args.port), app)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
