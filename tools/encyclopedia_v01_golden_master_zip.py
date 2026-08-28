"""Build the non-committed owner-transfer ZIP for the golden-master review.

Per docs/testing/VISUAL_ACCEPTANCE_EVIDENCE_CONTRACT.md, the owner-transfer
archive must contain the curated 4-6 PNGs plus REVIEW.md and
layout-audit.json, live in the Greia project root, and not be committed
to Git.
"""
from __future__ import annotations

import os
import zipfile
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
REVIEW_DIR = REPO_ROOT / "docs" / "reviews" / "visual" / "2026-08-28_encyclopedia_goldenmaster"
ZIP_NAME = "GREIA_VISUAL_REVIEW_ENCYCLOPEDIA_GOLDEN_MASTER_2026-08-28.zip"


def build_zip() -> Path:
    target = REPO_ROOT / ZIP_NAME
    if target.exists():
        target.unlink()
    with zipfile.ZipFile(target, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for relative in (
            "REVIEW.md",
            "layout-audit.json",
            "contact-sheet-primary.png",
            "screenshots/01-home.png",
            "screenshots/02-lion-activated.png",
            "screenshots/03-home-compact.png",
            "screenshots/04-home-large.png",
        ):
            source = REVIEW_DIR / relative
            if not source.is_file():
                raise SystemExit(f"missing review artifact: {source}")
            archive.write(source, arcname=f"encyclopedia_goldenmaster/{relative}")
    return target


def main() -> int:
    target = build_zip()
    size = target.stat().st_size
    print(f"wrote {target} ({size} bytes)")
    print(f"VISUAL REVIEW ZIP FOR OWNER ATTACHMENT: {target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
