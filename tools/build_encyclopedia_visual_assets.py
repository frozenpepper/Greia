#!/usr/bin/env python3
"""Build or verify Encyclopedia editable SVG masters as runtime PNGs.

Authoring-only tool. Runtime Greia images never depend on CairoSVG or SVG
rasterization. ``--check`` rebuilds to a temporary directory and byte-compares
against the committed runtime pack. A CairoSVG/toolchain change that alters the
build product therefore requires an intentional rebuild and commit.

The visual migration is deliberately tranche-based. ``golden`` owns the six
accepted golden-master renditions and ``sections`` owns the five E3 section
worlds. The default ``all`` group produces both tranches together. A full
``--check --group all`` additionally requires the runtime directory to contain
exactly those eleven PNGs, preventing stale or abandoned renditions from being
silently carried into exact-SHA Simulator evidence.
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
GOLDEN_MASTER_NAMES = (
    "home_discovery_book",
    "animals_field_table",
    "lion_savanna",
    "saturn_observatory",
    "gears_workbench",
    "pyramids_diorama",
)
SECTION_NAMES = (
    "space_gallery_observatory",
    "earth_gallery_landscape",
    "body_gallery_discovery_room",
    "machines_gallery_workbench",
    "history_gallery_time_trail",
)
NAMES = GOLDEN_MASTER_NAMES + SECTION_NAMES
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


def _selected_names(group: str) -> tuple[str, ...]:
    if group == "golden":
        return GOLDEN_MASTER_NAMES
    if group == "sections":
        return SECTION_NAMES
    return NAMES


def _runtime_png_names() -> set[str]:
    if not RUNTIME.exists():
        return set()
    return {path.name for path in RUNTIME.glob("*.png") if path.is_file()}


def build(names: tuple[str, ...]) -> int:
    total = 0
    for name in names:
        target = _build_one(name, RUNTIME)
        size = target.stat().st_size
        total += size
        print(f"built {target.relative_to(ROOT)} ({size} bytes) sha256={_sha256(target)}")
    print(f"built {len(names)} runtime PNGs ({total} bytes total)")
    return 0


def check(names: tuple[str, ...]) -> int:
    expected = {f"{name}.png" for name in names}
    present = _runtime_png_names()
    missing_names = sorted(expected - present)
    if missing_names:
        for filename in missing_names:
            print(f"MISSING {(RUNTIME / filename).relative_to(ROOT)}")
        return 1

    # Tranche checks intentionally coexist with the other tranche. The full
    # check is the release/review contract and therefore rejects stale extras.
    if names == NAMES:
        unexpected = sorted(present - expected)
        if unexpected:
            for filename in unexpected:
                print(f"UNEXPECTED {(RUNTIME / filename).relative_to(ROOT)}")
            return 1

    with TemporaryDirectory(prefix="greia-encyclopedia-art-") as temporary:
        rebuilt_root = Path(temporary)
        for name in names:
            rebuilt = _build_one(name, rebuilt_root)
            committed = RUNTIME / f"{name}.png"
            if rebuilt.read_bytes() != committed.read_bytes():
                print(
                    f"BUILD-DRIFT {name}: rebuilt_sha256={_sha256(rebuilt)} "
                    f"committed_sha256={_sha256(committed)}"
                )
                return 1
            print(f"PASS {name} sha256={_sha256(committed)}")
    print(f"PASS {len(names)} Encyclopedia runtime PNGs match editable masters")
    return 0


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="rebuild temporarily and verify committed runtime PNGs without modifying them",
    )
    parser.add_argument(
        "--group",
        choices=("all", "golden", "sections"),
        default="all",
        help="build/check all art, only the six golden masters, or only the five E3 section worlds",
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    names = _selected_names(args.group)
    return check(names) if args.check else build(names)


if __name__ == "__main__":
    raise SystemExit(main())
