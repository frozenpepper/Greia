#!/usr/bin/env python3
"""Build or verify Encyclopedia editable SVG masters as runtime PNGs.

Authoring-only tool. Runtime Greia images never depend on CairoSVG or SVG
rasterization. ``--check`` rebuilds to a temporary directory and byte-compares
against the committed runtime pack. A CairoSVG/toolchain change that alters the
build product therefore requires an intentional rebuild and commit.
"""
from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
from tempfile import TemporaryDirectory

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
REFERENCE_SIZE = (1024, 600)


def _build_one(name: str, target_root: Path) -> Path:
    source = SOURCE / f"{name}.svg"
    target = target_root / f"{name}.png"
    target_root.mkdir(parents=True, exist_ok=True)
    cairosvg.svg2png(
        url=str(source),
        write_to=str(target),
        output_width=REFERENCE_SIZE[0],
        output_height=REFERENCE_SIZE[1],
    )
    return target


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build() -> int:
    total = 0
    for name in NAMES:
        target = _build_one(name, RUNTIME)
        size = target.stat().st_size
        total += size
        print(f"built {target.relative_to(ROOT)} ({size} bytes) sha256={_sha256(target)}")
    print(f"built {len(NAMES)} runtime PNGs ({total} bytes total)")
    return 0


def check() -> int:
    missing = [
        RUNTIME / f"{name}.png"
        for name in NAMES
        if not (RUNTIME / f"{name}.png").is_file()
    ]
    if missing:
        for path in missing:
            print(f"MISSING {path.relative_to(ROOT)}")
        return 1

    with TemporaryDirectory(prefix="greia-encyclopedia-art-") as temporary:
        rebuilt_root = Path(temporary)
        for name in NAMES:
            rebuilt = _build_one(name, rebuilt_root)
            committed = RUNTIME / f"{name}.png"
            if rebuilt.read_bytes() != committed.read_bytes():
                print(
                    f"BUILD-DRIFT {name}: rebuilt_sha256={_sha256(rebuilt)} "
                    f"committed_sha256={_sha256(committed)}"
                )
                return 1
            print(f"PASS {name} sha256={_sha256(committed)}")
    print(f"PASS {len(NAMES)} Encyclopedia runtime PNGs match editable masters")
    return 0


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="rebuild temporarily and verify committed runtime PNGs without modifying them",
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    return check() if args.check else build()


if __name__ == "__main__":
    raise SystemExit(main())
