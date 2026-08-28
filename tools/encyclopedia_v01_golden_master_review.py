"""Build the 2026-08-28 Encyclopedia golden-master contact sheet and curated set.

Inputs (already captured by tools/encyclopedia_v01_golden_master_capture.py):
  tmp/encyclopedia-goldenmaster-2026-08-28/primary/{home,animals,lion,saturn,gears,pyramids}/screenshots/*.png
  tmp/encyclopedia-goldenmaster-2026-08-28/compact/compact/screenshots/*.png
  tmp/encyclopedia-goldenmaster-2026-08-28/large/large/screenshots/*.png

Outputs (committed under docs/reviews/visual/2026-08-28_encyclopedia_goldenmaster/):
  screenshots/01-home.png            1024x600 reference view
  screenshots/02-lion-activated.png  1024x600 representative interaction state
  screenshots/03-home-compact.png    compact (1024x600 + interface-size=compact) row
  screenshots/04-home-large.png      larger (1280x800) row
  contact-sheet-primary.png          3x2 contact sheet of the six primary screens
"""
from __future__ import annotations

import argparse
import os
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


PRIMARY_DIR = Path("tmp/encyclopedia-goldenmaster-2026-08-28/primary")
COMPACT_DIR = Path("tmp/encyclopedia-goldenmaster-2026-08-28/compact/compact")
LARGE_DIR = Path("tmp/encyclopedia-goldenmaster-2026-08-28/large/large")
OUT_DIR = Path("docs/reviews/visual/2026-08-28_encyclopedia_goldenmaster")
SHOTS = OUT_DIR / "screenshots"


PRIMARY_PAGES: tuple[tuple[str, str], ...] = (
    ("Home", "home/screenshots/01-home.png"),
    ("Animals", "animals/screenshots/02-animals.png"),
    ("Lion (initial)", "lion/screenshots/03-lion-initial.png"),
    ("Saturn (initial)", "saturn/screenshots/05-saturn-initial.png"),
    ("Gears (initial)", "gears/screenshots/07-gears-initial.png"),
    ("Pyramids (initial)", "pyramids/screenshots/09-pyramids-initial.png"),
)


def _open(path: Path) -> Image.Image:
    return Image.open(path).convert("RGB")


def _thumbnail(image: Image.Image, max_size: tuple[int, int]) -> Image.Image:
    image.thumbnail(max_size, Image.LANCZOS)
    return image


def _label_strip(width: int, height: int, label: str) -> Image.Image:
    strip = Image.new("RGB", (width, height), (244, 250, 247))
    draw = ImageDraw.Draw(strip)
    try:
        font = ImageFont.truetype(
            "/System/Library/Fonts/Supplemental/Arial.ttf", 16
        )
    except OSError:
        font = ImageFont.load_default()
    bbox = draw.textbbox((0, 0), label, font=font)
    text_width = bbox[2] - bbox[0]
    draw.text(
        ((width - text_width) // 2, 2),
        label,
        fill=(61, 44, 31),
        font=font,
    )
    return strip


def build_contact_sheet(out_path: Path) -> None:
    cell_w, cell_h = 480, 282
    label_h = 26
    pad = 12
    cols, rows = 3, 2
    sheet_w = pad + (cell_w + pad) * cols
    sheet_h = pad + (cell_h + label_h + pad) * rows
    sheet = Image.new("RGB", (sheet_w, sheet_h), (255, 250, 239))
    draw = ImageDraw.Draw(sheet)
    try:
        title_font = ImageFont.truetype(
            "/System/Library/Fonts/Supplemental/Arial Bold.ttf", 22
        )
    except OSError:
        title_font = ImageFont.load_default()
    draw.text((pad, 4), "Encyclopedia v0.1 golden-master 1024x600 contact sheet",
              fill=(61, 44, 31), font=title_font)

    for index, (label, relative) in enumerate(PRIMARY_PAGES):
        col = index % cols
        row = index // cols
        x = pad + col * (cell_w + pad)
        y = 40 + row * (cell_h + label_h + pad)
        source = PRIMARY_DIR / relative
        if not source.is_file():
            raise SystemExit(f"missing primary capture: {source}")
        thumb = _open(source)
        thumb.thumbnail((cell_w, cell_h), Image.LANCZOS)
        sheet.paste(thumb, (x + (cell_w - thumb.width) // 2,
                            y + (cell_h - thumb.height) // 2))
        strip = _label_strip(cell_w, label_h, label)
        sheet.paste(strip, (x, y + cell_h))

    sheet.save(out_path, format="PNG")
    print(f"wrote {out_path} ({out_path.stat().st_size} bytes)")


def build_curated_set() -> None:
    SHOTS.mkdir(parents=True, exist_ok=True)
    sources = {
        "01-home.png": PRIMARY_DIR / "home" / "screenshots" / "01-home.png",
        "02-lion-activated.png": PRIMARY_DIR / "lion" / "screenshots" / "03-lion-activated.png",
        "03-home-compact.png": COMPACT_DIR / "screenshots" / "01-home.png",
        "04-home-large.png": LARGE_DIR / "screenshots" / "01-home.png",
    }
    for dest_name, source in sources.items():
        if not source.is_file():
            raise SystemExit(f"missing curated source: {source}")
        target = SHOTS / dest_name
        with Image.open(source) as image:
            image.save(target, format="PNG")
        print(f"wrote {target} ({target.stat().st_size} bytes)")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    args = parser.parse_args()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    SHOTS.mkdir(parents=True, exist_ok=True)
    build_curated_set()
    build_contact_sheet(OUT_DIR / "contact-sheet-primary.png")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
