#!/usr/bin/env python3
"""Build or verify Encyclopedia editable SVG masters as runtime PNGs.

Authoring-only tool. Runtime Greia images never depend on CairoSVG or SVG
rasterization. ``--check`` rebuilds to a temporary directory and byte-compares
against the committed runtime pack. A CairoSVG/toolchain change that alters the
build product therefore requires an intentional rebuild and commit.

The visual migration is deliberately tranche-based. ``golden`` owns the six
accepted golden-master renditions, ``sections`` owns the five E3 section
worlds and each ``e4_*`` group owns one E4 entry-migration batch. The default
``all`` group produces every tranche together. A full ``--check --group all``
additionally requires the runtime directory to contain exactly those PNGs,
preventing stale or abandoned renditions from being silently carried into
exact-SHA Simulator evidence.

Every Encyclopedia scene is a flattened full-screen backdrop and must therefore
build as an opaque RGB PNG. Transparent character sprites remain separate shared
assets. A page whose hero has live moving parts (the E4 airplane) may instead
own one transparent *sprite sheet*: ``assets/source/sprites/<name>.svg`` builds
to ``assets/runtime/sprites/<name>.png`` (RGBA, exact declared size) inside its
tranche group, so the opaque-scene contract and its exact scene count stay
untouched. Rejecting alpha-bearing scene renditions here keeps the low-resource
runtime free to use display-optimized opaque surfaces without silently flattening
an unintended transparent master.

Canonical rasterization environment (byte-reproducibility contract)
-------------------------------------------------------------------
The committed PNGs are reproduced byte-for-byte only by the **Homebrew**
libcairo (1.18.x at ``/opt/homebrew/lib``) through CairoSVG/cairocffi. Other
libcairo builds (for example MacPorts at ``/opt/local/lib``) differ in
anti-aliasing for some masters, so ``--check`` would report false BUILD-DRIFT.
On macOS run, for both build and ``--check``::

    DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/lib \\
        python3 tools/build_encyclopedia_visual_assets.py --check --group all

If libcairo cannot be loaded the tool exits with a clear message instead of a
traceback.
"""
from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
import struct
from tempfile import TemporaryDirectory

try:
    import cairosvg
except (ImportError, OSError) as exc:  # pragma: no cover - maintainer setup guard
    # cairocffi raises OSError (not ImportError) when libcairo is not found.
    raise SystemExit(
        "CairoSVG and a loadable libcairo are required only to rebuild "
        "Encyclopedia visual assets (the committed PNGs are reproduced by the "
        "Homebrew libcairo; on macOS run with "
        "DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/lib). "
        f"Load error: {str(exc).splitlines()[0]}"
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
# E4 entry-migration batches. Each batch is its own all-or-nothing tranche
# (a partial batch pack is forbidden) and is selectable with ``--group``.
# Parallel batches append their own key; never reorder or rename existing keys.
E4_GROUPS: dict[str, tuple[str, ...]] = {
    "e4_machines": (
        "magnet_lab",
        "bicycle_park",
        "airplane_sky",
        "bridge_river",
    ),
    "e4_history": (
        "dinosaurs_valley",
        "fossils_dig_site",
        "mammoth_tundra",
        "cave_paintings_wall",
    ),
    "e4_nature": (
        "elephant_waterhole",
        "octopus_reef",
        "bee_meadow",
        "penguin_ice_shore",
        "frog_pond",
        "volcano_cross_section",
        "rain_water_cycle",
        "ocean_depths",
        "tree_hillside",
        "rainbow_shower",
    ),
    "e4_space": (
        "sun_solar_observatory",
        "mercury_sunside_observatory",
        "venus_cloud_observatory",
        "earth_home_observatory",
        "moon_night_observatory",
        "mars_red_observatory",
        "jupiter_giant_observatory",
        "uranus_tilted_observatory",
        "neptune_windy_observatory",
    ),
    "e4_body": (
        "heart_discovery_room",
        "lungs_discovery_room",
        "bones_xray_room",
        "teeth_dental_room",
        "senses_mirror_room",
    ),
}
E4_NAMES = tuple(name for names in E4_GROUPS.values() for name in names)
NAMES = GOLDEN_MASTER_NAMES + SECTION_NAMES + E4_NAMES
REFERENCE_SIZE = (1024, 600)
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
PNG_COLOR_TYPE_RGB = 2
PNG_COLOR_TYPE_RGBA = 6

# Transparent part sheets composited live by one page: name -> (tranche group,
# exact pixel size). They live in ``sprites/`` sub-directories so they never
# mix with the flattened opaque scenes above.
SPRITE_SOURCE = SOURCE / "sprites"
SPRITE_RUNTIME = RUNTIME / "sprites"
SPRITE_SHEETS: dict[str, tuple[str, tuple[int, int]]] = {
    "airplane_parts": ("e4_machines", (512, 384)),
}


def _validate_runtime_png(path: Path) -> None:
    data = path.read_bytes()
    if len(data) < 26 or not data.startswith(PNG_SIGNATURE):
        raise RuntimeError(f"invalid PNG rendition: {path}")
    width, height = struct.unpack(">II", data[16:24])
    if (width, height) != REFERENCE_SIZE:
        raise RuntimeError(
            f"wrong Encyclopedia rendition size for {path}: "
            f"{width}x{height}, expected {REFERENCE_SIZE[0]}x{REFERENCE_SIZE[1]}"
        )
    color_type = data[25]
    if color_type != PNG_COLOR_TYPE_RGB:
        raise RuntimeError(
            f"Encyclopedia scene rendition must be opaque RGB: {path} "
            f"PNG color_type={color_type}, expected {PNG_COLOR_TYPE_RGB}"
        )


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
    _validate_runtime_png(target)
    return target


def _validate_sprite_png(path: Path, size: tuple[int, int]) -> None:
    data = path.read_bytes()
    if len(data) < 26 or not data.startswith(PNG_SIGNATURE):
        raise RuntimeError(f"invalid PNG sprite sheet: {path}")
    if struct.unpack(">II", data[16:24]) != size:
        raise RuntimeError(f"wrong Encyclopedia sprite sheet size for {path}: expected {size}")
    if data[25] != PNG_COLOR_TYPE_RGBA:
        raise RuntimeError(
            f"Encyclopedia sprite sheet must be transparent RGBA: {path} "
            f"PNG color_type={data[25]}, expected {PNG_COLOR_TYPE_RGBA}"
        )


def _build_sprite(name: str, target_root: Path) -> Path:
    size = SPRITE_SHEETS[name][1]
    target = target_root / f"{name}.png"
    target_root.mkdir(parents=True, exist_ok=True)
    cairosvg.svg2png(
        url=str(SPRITE_SOURCE / f"{name}.svg"),
        write_to=str(target),
        output_width=size[0],
        output_height=size[1],
    )
    _validate_sprite_png(target, size)
    return target


def _selected_sprites(group: str) -> tuple[str, ...]:
    return tuple(
        name
        for name, (owner, _size) in SPRITE_SHEETS.items()
        if group == "all" or owner == group
    )


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _selected_names(group: str) -> tuple[str, ...]:
    if group == "golden":
        return GOLDEN_MASTER_NAMES
    if group == "sections":
        return SECTION_NAMES
    if group in E4_GROUPS:
        return E4_GROUPS[group]
    return NAMES


SPRITE_NAMES = {"earth_planet_sprite.png"}


def _runtime_png_names() -> set[str]:
    if not RUNTIME.exists():
        return set()
    return {
        path.name
        for path in RUNTIME.glob("*.png")
        if path.is_file() and path.name not in SPRITE_NAMES
    }



def build(names: tuple[str, ...], sprites: tuple[str, ...] = ()) -> int:
    total = 0
    for name in names:
        target = _build_one(name, RUNTIME)
        size = target.stat().st_size
        total += size
        print(f"built {target.relative_to(ROOT)} ({size} bytes) sha256={_sha256(target)}")
    print(f"built {len(names)} runtime PNGs ({total} bytes total)")
    for name in sprites:
        target = _build_sprite(name, SPRITE_RUNTIME)
        print(
            f"built {target.relative_to(ROOT)} ({target.stat().st_size} bytes) "
            f"sha256={_sha256(target)}"
        )
    if sprites:
        print(f"built {len(sprites)} sprite sheets")
    return 0


def check_sprites(sprites: tuple[str, ...], *, exact: bool) -> int:
    present = (
        {path.stem for path in SPRITE_RUNTIME.glob("*.png") if path.is_file()}
        if SPRITE_RUNTIME.exists()
        else set()
    )
    for name in sorted(set(sprites) - present):
        print(f"MISSING {(SPRITE_RUNTIME / f'{name}.png').relative_to(ROOT)}")
        return 1
    if exact:
        for name in sorted(present - set(sprites)):
            print(f"UNEXPECTED {(SPRITE_RUNTIME / f'{name}.png').relative_to(ROOT)}")
            return 1
    with TemporaryDirectory(prefix="greia-encyclopedia-sprites-") as temporary:
        for name in sprites:
            rebuilt = _build_sprite(name, Path(temporary))
            committed = SPRITE_RUNTIME / f"{name}.png"
            _validate_sprite_png(committed, SPRITE_SHEETS[name][1])
            if rebuilt.read_bytes() != committed.read_bytes():
                print(
                    f"BUILD-DRIFT sprite {name}: rebuilt_sha256={_sha256(rebuilt)} "
                    f"committed_sha256={_sha256(committed)}"
                )
                return 1
            print(f"PASS sprite {name} sha256={_sha256(committed)}")
    if sprites:
        print(f"PASS {len(sprites)} Encyclopedia sprite sheets match editable masters")
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
            _validate_runtime_png(committed)
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
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="rebuild temporarily and verify committed runtime PNGs without modifying them",
    )
    parser.add_argument(
        "--group",
        choices=("all", "golden", "sections") + tuple(E4_GROUPS),
        default="all",
        help=(
            "build/check all art, only the six golden masters, only the five E3 "
            "section worlds, or one E4 entry batch"
        ),
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    names = _selected_names(args.group)
    sprites = _selected_sprites(args.group)
    if not args.check:
        return build(names, sprites)
    return check(names) or check_sprites(sprites, exact=args.group == "all")


if __name__ == "__main__":
    raise SystemExit(main())
