"""Composition root for Sottomarino Giramondo (org.greia.sottomarino-giramondo)."""

from __future__ import annotations

try:
    from sub_app import SubmarineApp
except ImportError:
    from .sub_app import SubmarineApp


def main() -> int:
    app = SubmarineApp()
    return app.run()


if __name__ == "__main__":
    raise SystemExit(main())
