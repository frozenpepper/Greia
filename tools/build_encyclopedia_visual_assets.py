#!/usr/bin/env python3
"""Build Encyclopedia editable SVG masters into economical runtime PNGs.

Authoring-only tool. Runtime Greia images never depend on CairoSVG or SVG
rasterization. Install CairoSVG in the maintainer environment when rebuilding.
"""
from __future__ import annotations

from pathlib import Path

try:
    import cairosvg
except ImportError as exc:  # pragma: no cover - maintainer setup guard
    raise SystemExit(
        "CairoSVG is required only to rebuild Encyclopedia visual assets"
    ) from exc

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "activities" / "enciclopedia_greia" / "assets" / "source"
RUNTIME = ROOT / "activities" / "enciclopedia_greia" / "assets" / "runtime"
NAMES = (
    "home_discovery_book",
    "animals_field_table",
    "lion_savanna",
    "saturn_observatory",
    "gears_workbench",
    "pyramids_diorama",
)


def main() -> int:
    RUNTIME.mkdir(parents=True, exist_ok=True)
    for name in NAMES:
        source = SOURCE / f"{name}.svg"
        target = RUNTIME / f"{name}.png"
        cairosvg.svg2png(
            url=str(source),
            write_to=str(target),
            output_width=1024,
            output_height=600,
        )
        print(f"built {target.relative_to(ROOT)} ({target.stat().st_size} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
