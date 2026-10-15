#!/usr/bin/env python3
"""Build (or check) the core semantic icon PNGs from their reviewed SVG masters.

``assets/catalog/core_icons_v1.toml`` is hand-maintained: icon IDs, alt keys
and the 64/128/256 output paths are a stable contract (saved profiles store
avatar IDs, Collections and Activities store icon IDs). Every entry names its
flat-vector master with ``source_svg`` (authored under
``docs/design/GREIA_SVG_AUTHORING_RULES.md``). This build-time tool rasterizes
each master with ``rsvg-convert`` into the entry's ``path_64``/``path_128``/
``path_256``. It never rewrites the catalogue, and runtime code never decodes
SVG.

``--check`` writes nothing: it renders into a temporary directory and compares
the decoded RGBA pixels with the committed PNGs, so a stale PNG (an SVG edited
without a rebuild, or a hand-edited PNG) fails. Both modes first verify the
inventory: every entry has an existing master that passes the forbidden-
construct lint (rules section 9), and no uncatalogued SVG master or PNG sits in
the core icon directories.
"""

from __future__ import annotations

import argparse
import os
import re
import shutil
import struct
import subprocess
import tempfile
import tomllib
from dataclasses import dataclass
from pathlib import Path


class CoreIconBuildError(ValueError):
    pass


SIZES: tuple[int, ...] = (64, 128, 256)
SOURCE_DIR = Path("source/icons/core/v1")
OUTPUT_DIR = Path("icons/core/v1")
_PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
# GREIA_SVG_AUTHORING_RULES.md section 9 (forbidden constructs), verbatim.
_FORBIDDEN_SVG = re.compile(
    r'<image|data:|<text|<tspan|<filter|fe[A-Z]|<mask|<pattern|<style|<script'
    r'|foreignObject|<animate|blend-mode|skew|href="[^#]|xlink:href="[^#]'
    r"|sodipodi|inkscape:"
)


@dataclass(frozen=True, slots=True)
class Rendition:
    size: int
    output: Path


@dataclass(frozen=True, slots=True)
class CoreIconSpec:
    """One catalogued core icon: its SVG master and its three PNG renditions."""

    asset_id: str
    source: Path
    renditions: tuple[Rendition, ...]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--assets-root", type=Path, default=Path("assets"))
    parser.add_argument(
        "--catalog", type=Path, default=Path("assets/catalog/core_icons_v1.toml")
    )
    parser.add_argument(
        "--rasterizer",
        default=os.environ.get("GREIA_RSVG_CONVERT", "rsvg-convert"),
        help="build-host SVG rasterizer; defaults to rsvg-convert",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="verify committed PNGs match a fresh render; writes nothing",
    )
    parser.add_argument(
        "--tolerance",
        type=int,
        default=2,
        help="--check: largest allowed per-channel difference (0-255); "
        "absorbs anti-aliasing noise between librsvg builds",
    )
    args = parser.parse_args(argv)

    assets_root = args.assets_root.resolve(strict=True)
    specs = load_specs(args.catalog.resolve(strict=True), assets_root)
    verify_inventory(specs, assets_root)
    rasterizer = _resolve_rasterizer(args.rasterizer)
    if args.check:
        stale = check_all(specs, rasterizer, args.tolerance)
        if stale:
            for line in stale:
                print(f"stale: {line}")
            print(
                f"{len(stale)} core icon rendition(s) differ from their SVG masters; "
                "rebuild with tools/build_core_icons.py"
            )
            return 1
        print(f"core icons up to date: {len(specs)} icons x {len(SIZES)} sizes")
        return 0
    build_all(specs, rasterizer)
    print(f"built {len(specs)} core icons x {len(SIZES)} sizes")
    return 0


def load_specs(catalog: Path, assets_root: Path) -> tuple[CoreIconSpec, ...]:
    assets_root = assets_root.resolve(strict=True)
    try:
        raw = tomllib.loads(catalog.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError) as exc:
        raise CoreIconBuildError(f"cannot read core icon catalogue: {exc}") from exc
    entries = raw.get("icons")
    if not isinstance(entries, list) or not entries:
        raise CoreIconBuildError("core icon catalogue must define [[icons]]")
    specs: list[CoreIconSpec] = []
    seen: set[str] = set()
    for entry in entries:
        if not isinstance(entry, dict):
            raise CoreIconBuildError("invalid [[icons]] entry")
        asset_id = _text(entry, "id")
        if asset_id in seen:
            raise CoreIconBuildError(f"duplicate core icon id: {asset_id}")
        seen.add(asset_id)
        source_text = entry.get("source_svg")
        if not isinstance(source_text, str) or not source_text:
            raise CoreIconBuildError(f"core icon {asset_id!r} has no source_svg master")
        source = _contained(assets_root, source_text, "source_svg")
        if source.parent != (assets_root / SOURCE_DIR).resolve() or source.suffix != ".svg":
            raise CoreIconBuildError(
                f"core icon {asset_id!r} master must be {SOURCE_DIR}/<id>.svg"
            )
        renditions = []
        for size in SIZES:
            output = _contained(assets_root, _text(entry, f"path_{size}"), f"path_{size}")
            if output.parent != (assets_root / OUTPUT_DIR / str(size)).resolve():
                raise CoreIconBuildError(
                    f"core icon {asset_id!r} path_{size} must live in {OUTPUT_DIR}/{size}/"
                )
            renditions.append(Rendition(size, output))
        specs.append(CoreIconSpec(asset_id, source, tuple(renditions)))
    return tuple(specs)


def verify_inventory(specs: tuple[CoreIconSpec, ...], assets_root: Path) -> None:
    """Fail on missing/unlinted masters and on uncatalogued masters or PNGs."""

    assets_root = assets_root.resolve(strict=True)
    for spec in specs:
        if not spec.source.is_file():
            raise CoreIconBuildError(f"missing SVG master for {spec.asset_id!r}: {spec.source}")
        lint_svg(spec.source)
    declared_sources = {spec.source for spec in specs}
    for svg in sorted((assets_root / SOURCE_DIR).glob("*.svg")):
        if svg.resolve() not in declared_sources:
            raise CoreIconBuildError(f"uncatalogued core icon master: {svg.name}")
    declared_outputs = {r.output for spec in specs for r in spec.renditions}
    for size in SIZES:
        for png in sorted((assets_root / OUTPUT_DIR / str(size)).glob("*.png")):
            if png.resolve() not in declared_outputs:
                raise CoreIconBuildError(
                    f"uncatalogued core icon PNG: {OUTPUT_DIR}/{size}/{png.name}"
                )


def lint_svg(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    match = _FORBIDDEN_SVG.search(text)
    if match is not None:
        raise CoreIconBuildError(
            f"{path.name}: forbidden SVG construct {match.group(0)!r} "
            "(GREIA_SVG_AUTHORING_RULES.md section 9)"
        )


def build_all(specs: tuple[CoreIconSpec, ...], rasterizer: Path) -> None:
    for spec in specs:
        for rendition in spec.renditions:
            temporary = rendition.output.with_name(
                f".{rendition.output.name}.tmp-{os.getpid()}"
            )
            try:
                render(rasterizer, spec.source, rendition.size, temporary)
                os.replace(temporary, rendition.output)
            finally:
                temporary.unlink(missing_ok=True)


def check_all(
    specs: tuple[CoreIconSpec, ...], rasterizer: Path, tolerance: int
) -> list[str]:
    if not 0 <= tolerance <= 255:
        raise CoreIconBuildError("--tolerance must be between 0 and 255")
    stale: list[str] = []
    with tempfile.TemporaryDirectory(prefix="greia-core-icons-") as scratch:
        for spec in specs:
            for rendition in spec.renditions:
                fresh = Path(scratch) / f"{spec.asset_id}_{rendition.size}.png"
                render(rasterizer, spec.source, rendition.size, fresh)
                delta = _max_channel_delta(fresh, rendition.output)
                if delta is None or delta > tolerance:
                    reason = "unreadable/mismatched" if delta is None else f"max delta {delta}"
                    stale.append(f"{spec.asset_id} @{rendition.size} ({reason})")
    return stale


def render(rasterizer: Path, source: Path, size: int, output: Path) -> None:
    command = [
        str(rasterizer),
        "--width",
        str(size),
        "--height",
        str(size),
        "--output",
        str(output),
        str(source),
    ]
    try:
        subprocess.run(command, check=True)
    except subprocess.CalledProcessError as exc:
        raise CoreIconBuildError(f"rasterizer failed for {source.name} @{size}") from exc
    _verify_png(output, size)


def _max_channel_delta(fresh: Path, committed: Path) -> int | None:
    try:
        from PIL import Image, ImageChops
    except ImportError as exc:
        raise CoreIconBuildError("--check needs Pillow on the build host") from exc
    try:
        with Image.open(fresh) as a_raw, Image.open(committed) as b_raw:
            if b_raw.mode != "RGBA" or a_raw.size != b_raw.size:
                return None
            difference = ImageChops.difference(a_raw.convert("RGBA"), b_raw)
            return max(high for _low, high in difference.getextrema())
    except OSError:
        return None


def _verify_png(path: Path, size: int) -> None:
    try:
        data = path.read_bytes()
    except OSError as exc:
        raise CoreIconBuildError(f"rasterizer did not create output: {path}") from exc
    if len(data) < 24 or data[:8] != _PNG_SIGNATURE or data[12:16] != b"IHDR":
        raise CoreIconBuildError(f"rasterizer output is not a PNG: {path}")
    if struct.unpack(">II", data[16:24]) != (size, size):
        raise CoreIconBuildError(f"rasterizer output for {path.name} is not {size}x{size}")


def _resolve_rasterizer(value: str) -> Path:
    path = Path(value)
    found = str(path.expanduser()) if path.parent != Path(".") else shutil.which(value)
    if found is None or not Path(found).is_file():
        raise CoreIconBuildError(
            "rsvg-convert is required on the build host to render core icons; "
            "install librsvg (Debian/Ubuntu: librsvg2-bin) or pass --rasterizer"
        )
    return Path(found).resolve(strict=True)


def _contained(root: Path, relative: str, label: str) -> Path:
    candidate = (root / relative).resolve()
    if root not in candidate.parents:
        raise CoreIconBuildError(f"{label} escapes assets root: {relative}")
    return candidate


def _text(entry: dict[str, object], key: str) -> str:
    value = entry.get(key)
    if not isinstance(value, str) or not value:
        raise CoreIconBuildError(f"{key} must be a non-empty string")
    return value


if __name__ == "__main__":
    raise SystemExit(main())
