"""Thin bootstrap for Teatrino delle Fiabe."""

from __future__ import annotations

if __package__:
    from .teatrino_app import TeatrinoApp
else:
    from teatrino_app import TeatrinoApp


def main() -> int:
    """Run the puppet theater through its lifecycle owner."""

    return TeatrinoApp().run()


if __name__ == "__main__":
    raise SystemExit(main())
