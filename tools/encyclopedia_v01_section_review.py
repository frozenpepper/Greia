"""Build the curated Encyclopedia E3 Home + six-section visual review set.

Input is produced by ``tools/encyclopedia_v01_section_review_capture.py``.
The tool copies the seven reference frames into one bounded review directory and
builds a single contact sheet. It does not score or approve the artwork; the
result remains Simulator evidence for owner/maintainer visual review.
"""
from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


PAGES: tuple[tuple[str, str, str], ...] = (
    ("Home", "home", "01-home.png"),
    ("Animals", "animals", "02-animals.png"),
    ("Space", "space", "03-space.png"),
    ("Earth & Nature", "earth", "04-earth.png"),
    ("Body", "body", "05-body.png"),
    ("Machines", "machines", "06-machines.png"),
    ("History", "history", "07-history.png"),
)


def _font(size: int, *, bold: bool = False) -> ImageFont.ImageFont:
    candidates = (
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf"
        if bold
        else "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
        if bold
        else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    )
    for path in candidates:
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            continue
    return ImageFont.load_default()


def _source(evidence_root: Path, tag: str, filename: str) -> Path:
    path = evidence_root / tag / "screenshots" / filename
    if not path.is_file():
        raise SystemExit(f"missing E3 Simulator capture: {path}")
    return path


def _copy_reference_frames(evidence_root: Path, output_root: Path) -> None:
    shots = output_root / "screenshots"
    shots.mkdir(parents=True, exist_ok=True)
    for _label, tag, filename in PAGES:
        source = _source(evidence_root, tag, filename)
        target = shots / filename
        with Image.open(source) as image:
            image.convert("RGB").save(target, format="PNG")
        print(f"wrote {target} ({target.stat().st_size} bytes)")


def _build_contact_sheet(evidence_root: Path, output: Path) -> None:
    cell_w, cell_h = 480, 282
    label_h = 28
    pad = 12
    title_h = 42
    cols, rows = 4, 2
    sheet_w = pad + (cell_w + pad) * cols
    sheet_h = title_h + pad + (cell_h + label_h + pad) * rows
    sheet = Image.new("RGB", (sheet_w, sheet_h), (255, 250, 239))
    draw = ImageDraw.Draw(sheet)
    draw.text(
        (pad, 8),
        "Encyclopedia E3 — Home + six section worlds",
        fill=(61, 44, 31),
        font=_font(22, bold=True),
    )

    for index, (label, tag, filename) in enumerate(PAGES):
        source = _source(evidence_root, tag, filename)
        with Image.open(source) as opened:
            image = opened.convert("RGB")
        image.thumbnail((cell_w, cell_h), Image.LANCZOS)

        col = index % cols
        row = index // cols
        x = pad + col * (cell_w + pad)
        y = title_h + pad + row * (cell_h + label_h + pad)
        px = x + (cell_w - image.width) // 2
        py = y + (cell_h - image.height) // 2
        sheet.paste(image, (px, py))

        label_box = (x, y + cell_h, x + cell_w, y + cell_h + label_h)
        draw.rounded_rectangle(label_box, radius=8, fill=(244, 250, 247))
        font = _font(16, bold=True)
        bbox = draw.textbbox((0, 0), label, font=font)
        text_w = bbox[2] - bbox[0]
        draw.text(
            (x + (cell_w - text_w) // 2, y + cell_h + 4),
            label,
            fill=(61, 44, 31),
            font=font,
        )

    output.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(output, format="PNG")
    print(f"wrote {output} ({output.stat().st_size} bytes)")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evidence-root", required=True)
    parser.add_argument(
        "--output-root",
        default="docs/reviews/visual/2026-08-29_encyclopedia_e3_sections/runtime",
    )
    args = parser.parse_args(argv)

    evidence_root = Path(args.evidence_root).expanduser()
    output_root = Path(args.output_root).expanduser()
    _copy_reference_frames(evidence_root, output_root)
    _build_contact_sheet(evidence_root, output_root / "contact-sheet.png")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
