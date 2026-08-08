#!/usr/bin/env python3
"""Extract the approved core icon sheet into transparent, labeled PNG assets.

The source sheet is archival input. Runtime code consumes only the generated
individual PNGs and catalogue. The coordinates intentionally live in code so a
future source-sheet replacement is an explicit reviewed change.
"""

from __future__ import annotations

import argparse
import hashlib
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw


@dataclass(frozen=True, slots=True)
class IconSpec:
    asset_id: str
    category: str
    box: tuple[int, int, int, int]


SPECS: tuple[IconSpec, ...] = (
    IconSpec("book", "literacy", (18, 24, 220, 222)),
    IconSpec("robot", "characters", (225, 18, 420, 230)),
    IconSpec("unicorn", "characters", (410, 15, 615, 238)),
    IconSpec("globe", "learning", (606, 10, 820, 235)),
    IconSpec("backpack", "navigation", (790, 15, 1024, 235)),
    IconSpec("palette", "creativity", (5, 210, 225, 430)),
    IconSpec("abc_board", "literacy", (215, 210, 420, 435)),
    IconSpec("music_star", "music", (410, 215, 615, 430)),
    IconSpec("potions", "science", (600, 215, 820, 430)),
    IconSpec("treasure_chest", "rewards", (790, 215, 1024, 430)),
    IconSpec("coins", "rewards", (0, 405, 225, 620)),
    IconSpec("star_trophy", "rewards", (210, 395, 420, 620)),
    IconSpec("map", "adventure", (410, 405, 615, 595)),
    IconSpec("magnifier", "science", (590, 395, 825, 620)),
    IconSpec("puzzle_pieces", "logic", (795, 405, 1024, 620)),
    IconSpec("car", "world", (0, 565, 220, 755)),
    IconSpec("garden", "nature", (205, 565, 430, 790)),
    IconSpec("coin_bag", "rewards", (410, 560, 625, 800)),
    IconSpec("owl", "characters", (590, 560, 825, 800)),
    IconSpec("dinosaur", "characters", (795, 560, 1024, 800)),
    IconSpec("cup_trophy", "rewards", (0, 730, 220, 950)),
    IconSpec("rainbow", "nature", (195, 730, 430, 905)),
    IconSpec("abc_blocks", "literacy", (405, 730, 625, 950)),
    IconSpec("block_puzzle", "logic", (590, 730, 825, 910)),
    IconSpec("medal", "rewards", (795, 730, 1024, 950)),
    IconSpec("puzzle_trophy", "rewards", (0, 890, 225, 1130)),
    IconSpec("wizard", "characters", (205, 890, 430, 1130)),
    IconSpec("green_monster", "characters", (405, 890, 625, 1130)),
    IconSpec("heart", "status", (590, 890, 825, 1130)),
    IconSpec("notebook", "literacy", (790, 905, 1024, 1105)),
    IconSpec("train_blocks", "toys", (0, 1070, 235, 1310)),
    IconSpec("pouch", "rewards", (195, 1070, 395, 1310)),
    IconSpec("lightning", "status", (350, 1090, 470, 1260)),
    IconSpec("small_heart", "status", (445, 1075, 555, 1195)),
    IconSpec("yellow_star", "status", (515, 1100, 630, 1245)),
    IconSpec("pink_star", "status", (465, 1140, 560, 1265)),
    IconSpec("check", "controls", (570, 1045, 725, 1235)),
    IconSpec("x_mark", "controls", (705, 1100, 815, 1235)),
    IconSpec("close_button", "controls", (810, 1090, 1024, 1280)),
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--catalog", type=Path, required=True)
    parser.add_argument("--contact-sheet", type=Path, required=True)
    args = parser.parse_args()

    source = Image.open(args.source).convert("RGB")
    output_root = args.output_root
    output_root.mkdir(parents=True, exist_ok=True)

    generated: list[tuple[IconSpec, dict[int, Path]]] = []
    for spec in SPECS:
        crop = source.crop(spec.box)
        transparent = remove_background(crop)
        transparent = trim_and_square(transparent, size=256, padding=14)
        variants: dict[int, Path] = {}
        for size in (64, 128, 256):
            target_dir = output_root / str(size)
            target_dir.mkdir(parents=True, exist_ok=True)
            target = target_dir / f"{spec.asset_id}.png"
            resized = transparent.resize((size, size), Image.Resampling.LANCZOS)
            resized.save(target, format="PNG", optimize=True)
            variants[size] = target
        generated.append((spec, variants))

    write_catalog(args.catalog, args.source, generated)
    write_contact_sheet(args.contact_sheet, generated)
    return 0


def remove_background(image: Image.Image) -> Image.Image:
    rgb = np.array(image.convert("RGB"))
    height, width = rgb.shape[:2]
    mask = np.zeros((height, width), np.uint8)
    background_model = np.zeros((1, 65), np.float64)
    foreground_model = np.zeros((1, 65), np.float64)
    margin_x = max(2, int(width * 0.025))
    margin_y = max(2, int(height * 0.025))
    rect = (margin_x, margin_y, width - margin_x * 2, height - margin_y * 2)
    cv2.grabCut(rgb, mask, rect, background_model, foreground_model, 7, cv2.GC_INIT_WITH_RECT)
    alpha = np.where((mask == cv2.GC_FGD) | (mask == cv2.GC_PR_FGD), 255, 0).astype(np.uint8)

    # Preserve soft painted edges without retaining broad source-sheet halos.
    alpha = cv2.morphologyEx(alpha, cv2.MORPH_CLOSE, np.ones((3, 3), np.uint8))
    alpha = cv2.GaussianBlur(alpha, (3, 3), 0)
    rgba = np.dstack((rgb, alpha))
    return Image.fromarray(rgba, mode="RGBA")


def trim_and_square(image: Image.Image, *, size: int, padding: int) -> Image.Image:
    alpha = image.getchannel("A")
    bbox = alpha.getbbox()
    if bbox is None:
        raise RuntimeError("background removal produced an empty icon")
    trimmed = image.crop(bbox)
    maximum = size - padding * 2
    scale = min(maximum / trimmed.width, maximum / trimmed.height)
    target = (
        max(1, int(round(trimmed.width * scale))),
        max(1, int(round(trimmed.height * scale))),
    )
    trimmed = trimmed.resize(target, Image.Resampling.LANCZOS)
    canvas = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    x = (size - target[0]) // 2
    y = (size - target[1]) // 2
    canvas.alpha_composite(trimmed, (x, y))
    return canvas


def write_catalog(
    path: Path,
    source_path: Path,
    generated: list[tuple[IconSpec, dict[int, Path]]],
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    digest = hashlib.sha256(source_path.read_bytes()).hexdigest()
    lines = [
        'catalog_id = "greia.core-icons.v1"',
        'catalog_version = "1.0.0"',
        f'source_sha256 = "{digest}"',
        'source_note = "Extracted from the first approved project-generated icon sheet; later regenerated sheets are non-canonical experiments."',
        "",
    ]
    for spec, variants in generated:
        lines.extend(
            [
                "[[icons]]",
                f'id = "{spec.asset_id}"',
                f'category = "{spec.category}"',
                f'alt_key = "asset.{spec.asset_id}"',
                f'path_64 = "icons/core/v1/64/{variants[64].name}"',
                f'path_128 = "icons/core/v1/128/{variants[128].name}"',
                f'path_256 = "icons/core/v1/256/{variants[256].name}"',
                "",
            ]
        )
    path.write_text("\n".join(lines), encoding="utf-8")


def write_contact_sheet(
    path: Path,
    generated: list[tuple[IconSpec, dict[int, Path]]],
) -> None:
    columns = 5
    cell_width = 180
    cell_height = 205
    rows = (len(generated) + columns - 1) // columns
    canvas = Image.new("RGB", (columns * cell_width, rows * cell_height), (250, 247, 239))
    draw = ImageDraw.Draw(canvas)
    for index, (spec, variants) in enumerate(generated):
        column = index % columns
        row = index // columns
        x = column * cell_width
        y = row * cell_height
        icon = Image.open(variants[128]).convert("RGBA")
        canvas.paste(icon, (x + (cell_width - 128) // 2, y + 12), icon)
        text_box = draw.textbbox((0, 0), spec.asset_id)
        text_width = text_box[2] - text_box[0]
        draw.text((x + (cell_width - text_width) // 2, y + 155), spec.asset_id, fill=(48, 39, 30))
        draw.rounded_rectangle(
            (x + 4, y + 4, x + cell_width - 4, y + cell_height - 4),
            radius=8,
            outline=(220, 207, 184),
            width=1,
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(path, format="PNG", optimize=True)


if __name__ == "__main__":
    raise SystemExit(main())
