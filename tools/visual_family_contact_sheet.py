"""Deterministic developer-only visual family sheet for actual Greia assets.

Compare canonical core icons, first-party Activity icons and cast expressions
at the same practical 128 / 64 / 48 px scales in one bounded PNG. Source
identity is derived from each existing authoritative manifest/folder. No
art registry, theme tokens, generated source art, or runtime SVG decoding.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
import sys
import tomllib

ROOT = Path(__file__).resolve().parents[1]

BACKGROUND = (244, 242, 234)
PAPER = (255, 254, 250)
INK = (45, 58, 67)
MUTED = (102, 110, 117)
OUTLINE = (215, 214, 204)
TILE_W, TILE_H, COLUMNS = 292, 204, 5
SIZES = (128, 64, 48)
EXPRESSIONS = ("neutral", "happy", "surprised", "blink", "sleepy")
CAST = ("lilli", "leo", "flash", "dani", "tito", "momo")


class VisualFamilyError(ValueError):
    """Invalid source or unsafe output."""


@dataclass(frozen=True, slots=True)
class VisualSample:
    group: str
    key: str
    source: Path


def _checked_source(root: Path, relative: str) -> Path:
    if not isinstance(relative, str) or not relative.startswith("assets/"):
        raise VisualFamilyError(f"invalid visual source path: {relative!r}")
    candidate = (root / relative).resolve(strict=True)
    allowed = (root / "assets").resolve(strict=True)
    if not candidate.is_relative_to(allowed) or candidate.suffix.lower() != ".png":
        raise VisualFamilyError(f"visual source escapes PNG asset tree: {relative}")
    if not candidate.is_file():
        raise VisualFamilyError(f"visual source is not a file: {relative}")
    return candidate


def _activity_icons(root: Path) -> tuple[VisualSample, ...]:
    activities = (root / "activities").resolve(strict=True)
    result = []
    for manifest in sorted(activities.glob("*/activity.toml")):
        package = manifest.parent.resolve(strict=True)
        if package.parent != activities:
            raise VisualFamilyError(f"unsafe Activity package root: {package}")
        icon = package / "assets" / "icon.png"
        if not icon.is_file() or icon.is_symlink():
            raise VisualFamilyError(f"Activity icon missing/unsafe: {icon}")
        result.append(VisualSample("ACTIVITY", package.name, icon))
    return tuple(result)


def collect_samples(root: Path) -> tuple[VisualSample, ...]:
    root = root.resolve(strict=True)
    with (root / "assets" / "catalog" / "core_icons_v1.toml").open("rb") as stream:
        catalog = tomllib.load(stream)
    samples = []
    for item in catalog["icons"]:
        source = _checked_source(root, f"assets/{item['path_128']}")
        samples.append(VisualSample("CORE", item["id"], source))
    samples.extend(_activity_icons(root))
    for person in CAST:
        for emotion in EXPRESSIONS:
            relpath = f"assets/visual/runtime/v1/characters/{person}_{emotion}.png"
            samples.append(VisualSample("CAST", f"{person}.{emotion}", _checked_source(root, relpath)))
    identities = [(item.group, item.key) for item in samples]
    if len(identities) != len(set(identities)):
        raise VisualFamilyError("duplicate source identity in contact sheet")
    return tuple(samples)


def _panel_title(draw, label: str, index: int, y: int) -> None:
    draw.text((26, y + 11), f"{index:02d}  {label}", fill=INK)


def render_sheet(root: Path, output: Path) -> dict[str, int]:
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError as exc:
        raise VisualFamilyError("Pillow required by development-host contact sheet") from exc
    samples = collect_samples(root)
    groups = {name: tuple(item for item in samples if item.group == name)
              for name in ("CORE", "ACTIVITY", "CAST")}
    # Header per group; tile counts determine exact canvas height.
    heights = [(len(items) + COLUMNS - 1) // COLUMNS for items in groups.values()]
    width = TILE_W * COLUMNS + 40
    height = 90 + sum(58 + rows * TILE_H for rows in heights) + 35
    canvas = Image.new("RGB", (width, height), BACKGROUND)
    draw = ImageDraw.Draw(canvas)
    font = ImageFont.load_default()
    draw.text((26, 22), "GREIA / ACTUAL ART FAMILY / 128 - 64 - 48 px", font=font, fill=INK)
    draw.text((26, 45), "Same canvas, same display sizes. Artwork source remains unchanged.", font=font, fill=MUTED)
    y = 90
    for index, (group, items) in enumerate(groups.items(), 1):
        _panel_title(draw, f"{group} / {len(items)} ASSETS", index, y)
        y += 58
        for i, item in enumerate(items):
            x = 20 + (i % COLUMNS) * TILE_W
            ty = y + (i // COLUMNS) * TILE_H
            draw.rounded_rectangle((x, ty, x + TILE_W - 12, ty + TILE_H - 10),
                                   radius=14, fill=PAPER, outline=OUTLINE, width=2)
            title = item.key if len(item.key) <= 32 else item.key[:29] + "..."
            draw.text((x + 13, ty + 10), title, font=font, fill=INK)
            with Image.open(item.source) as image:
                if max(image.size) > 4096:
                    raise VisualFamilyError(f"oversized icon source: {item.source}")
                original = image.convert("RGBA")
                for j, size in enumerate(SIZES):
                    # All sizes are rendered from the same actual source, so
                    # reviewer comparisons do not conflate unrelated masters.
                    thumbnail = original.copy()
                    thumbnail.thumbnail((size, size), Image.Resampling.LANCZOS)
                    slot_x = x + (12, 149, 224)[j]
                    slot_y = ty + 40
                    square = Image.new("RGBA", (size, size), (238, 237, 229, 255))
                    square.alpha_composite(thumbnail,
                        ((size - thumbnail.width) // 2, (size - thumbnail.height) // 2))
                    canvas.paste(square.convert("RGB"), (slot_x, slot_y))
                    draw.text((slot_x + 5, ty + 177), f"{size} px", font=font, fill=MUTED)
        y += ((len(items) + COLUMNS - 1) // COLUMNS) * TILE_H
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.exists() or output.is_symlink():
        raise VisualFamilyError("output already exists; use a fresh evidence path")
    # Refuse to overwrite evidence (also if another job creates it now).
    with output.open("xb") as handle:
        canvas.save(handle, format="PNG", optimize=True)
    return {name.lower(): len(items) for name, items in groups.items()}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Compare Greia's real visual identity on one PNG")
    parser.add_argument("--output", required=True, type=Path, help="new PNG evidence path")
    args = parser.parse_args(argv)
    try:
        counts = render_sheet(ROOT, args.output)
    except (OSError, KeyError, VisualFamilyError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    print(f"Visual family sheet: {args.output} | {counts}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
