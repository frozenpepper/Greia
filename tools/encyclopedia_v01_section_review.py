"""Build the curated Encyclopedia E3 Home + six-section visual review set.

Input is produced by ``tools/encyclopedia_v01_section_review_capture.py``.
The tool accepts only a PASS capture manifest for the exact seven-page review
scope and complete eleven-PNG Activity runtime-art inventory. The manifest must
bind every runtime PNG both to a SHA-256 digest and to the exact committed Git
blob captured from HEAD. The builder preserves that integrity metadata in the
curated review directory, copies the seven reference frames, and builds one
contact sheet. It does not score or approve the artwork; the result remains
Simulator evidence for owner/maintainer visual review.
"""
from __future__ import annotations

import argparse
import json
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
EXPECTED_TAGS = tuple(tag for _label, tag, _filename in PAGES)
EXPECTED_RUNTIME_ART = {
    "home_discovery_book.png",
    "animals_field_table.png",
    "lion_savanna.png",
    "saturn_observatory.png",
    "gears_workbench.png",
    "pyramids_diorama.png",
    "space_gallery_observatory.png",
    "earth_gallery_landscape.png",
    "body_gallery_discovery_room.png",
    "machines_gallery_workbench.png",
    "history_gallery_time_trail.png",
}


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


def _is_lower_hex(value: object, length: int) -> bool:
    return (
        isinstance(value, str)
        and len(value) == length
        and all(character in "0123456789abcdef" for character in value)
    )


def _load_capture_manifest(evidence_root: Path) -> tuple[dict[str, object], str]:
    manifest_path = evidence_root / "capture-manifest.json"
    source_sha_path = evidence_root / "source-sha.txt"
    if not manifest_path.is_file():
        raise SystemExit(f"missing E3 capture manifest: {manifest_path}")
    if not source_sha_path.is_file():
        raise SystemExit(f"missing E3 source SHA: {source_sha_path}")

    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SystemExit(f"invalid E3 capture manifest: {exc}") from exc
    if not isinstance(manifest, dict):
        raise SystemExit("invalid E3 capture manifest: root must be an object")

    source_sha = source_sha_path.read_text(encoding="utf-8").strip()
    if manifest.get("status") != "PASS":
        raise SystemExit("E3 capture manifest is not PASS")
    if manifest.get("source_sha") != source_sha or not _is_lower_hex(source_sha, 40):
        raise SystemExit("E3 capture source SHA metadata disagrees")

    selected = tuple(manifest.get("selected_jobs", ()))
    completed = tuple(manifest.get("completed_jobs", ()))
    if selected != EXPECTED_TAGS or completed != EXPECTED_TAGS:
        raise SystemExit(
            "E3 capture manifest must contain exactly Home plus all six sections"
        )

    hashes = manifest.get("runtime_art_sha256")
    if not isinstance(hashes, dict) or set(hashes) != EXPECTED_RUNTIME_ART:
        raise SystemExit("E3 capture manifest does not describe the complete 11-PNG art pack")
    for filename, digest in hashes.items():
        if not isinstance(filename, str) or not _is_lower_hex(digest, 64):
            raise SystemExit("E3 capture manifest contains an invalid runtime-art digest")

    git_blobs = manifest.get("runtime_art_git_blobs")
    if not isinstance(git_blobs, dict) or set(git_blobs) != EXPECTED_RUNTIME_ART:
        raise SystemExit(
            "E3 capture manifest does not bind the complete runtime-art pack to Git"
        )
    for filename, blob_sha in git_blobs.items():
        if not isinstance(filename, str) or not _is_lower_hex(blob_sha, 40):
            raise SystemExit("E3 capture manifest contains an invalid runtime-art Git blob")

    return manifest, source_sha


def _copy_integrity_metadata(
    evidence_root: Path,
    output_root: Path,
    *,
    manifest: dict[str, object],
    source_sha: str,
) -> None:
    output_root.mkdir(parents=True, exist_ok=True)
    (output_root / "source-sha.txt").write_text(source_sha + "\n", encoding="utf-8")
    (output_root / "capture-manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


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
    manifest, source_sha = _load_capture_manifest(evidence_root)
    _copy_integrity_metadata(
        evidence_root,
        output_root,
        manifest=manifest,
        source_sha=source_sha,
    )
    _copy_reference_frames(evidence_root, output_root)
    _build_contact_sheet(evidence_root, output_root / "contact-sheet.png")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
