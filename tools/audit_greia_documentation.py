#!/usr/bin/env python3
"""Audit repository Markdown documentation, including historical records.

Usage:
    python3 tools/audit_greia_documentation.py
    python3 tools/audit_greia_documentation.py --strict

The default scans every tracked/source Markdown path, reporting broken relative
links in current manuals separately from historical docs. --strict returns
nonzero only for broken links in current docs. It never changes a file.
Source-code paths mentioned in prose are not considered Markdown links.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
import re
from urllib.parse import unquote, urlsplit


ROOT = Path(__file__).resolve().parents[1]
LINK = re.compile(r"!?(?:\[[^\]\n]*\])\((<[^>]+>|[^)\s]+)(?:\s+[\"'][^\"']+[\"'])?\)")
FENCED = re.compile(r"^\s*(`{3,}|~{3,})")
DATED = re.compile(r"^20\d\d-\d\d-\d\d[_-]")


@dataclass(frozen=True)
class LinkIssue:
    source: str
    line: int
    destination: str
    resolved: str
    historical: bool


def is_historical(path: Path, root: Path = ROOT) -> bool:
    parts = path.relative_to(root).parts
    if len(parts) >= 2 and parts[0] == "docs":
        if parts[1] in {"archive", "reviews"}:
            return True
        # Dated test runbooks may be old snapshots; plans stay live while
        # their owner-authorized workstream is active, despite dated names.
        if parts[1] == "testing" and (
            any(DATED.match(part) for part in parts[2:])
        ):
            return True
    return False


def markdown_files(root: Path = ROOT) -> list[Path]:
    """Skip generated and vendored dependencies, not historical docs."""
    bases = [root / "docs", root / "skills", root / "website"]
    files = list(root.glob("*.md"))
    for base in bases:
        if base.is_dir():
            files.extend(base.rglob("*.md"))
    return sorted({
        path for path in files if not any(
            part in {"node_modules", ".git", "tmp", "out", "__pycache__"}
            for part in path.relative_to(root).parts
        )
    })


def _markdown_without_fences(content: str) -> list[tuple[int, str]]:
    lines: list[tuple[int, str]] = []
    fence_char = ""
    fence_width = 0
    for line_num, line in enumerate(content.splitlines(), 1):
        match = FENCED.match(line)
        if match:
            delimiter = match.group(1)
            if not fence_char:
                fence_char, fence_width = delimiter[0], len(delimiter)
            elif delimiter[0] == fence_char and len(delimiter) >= fence_width:
                fence_char, fence_width = "", 0
            continue
        if not fence_char:
            lines.append((line_num, line))
    return lines


def scan(root: Path = ROOT) -> tuple[int, list[LinkIssue]]:
    """Return count of docs scanned and broken repo-local Markdown links."""
    issues: list[LinkIssue] = []
    docs = markdown_files(root)
    for path in docs:
        content = path.read_text(encoding="utf-8")
        for line_number, line in _markdown_without_fences(content):
            for match in LINK.finditer(line):
                raw = match.group(1).strip("<>")
                url = urlsplit(raw)
                if url.scheme or url.netloc or not url.path:
                    continue
                target = unquote(url.path)
                if target.startswith("/"):
                    # An absolute URL-path is for a website or device, not repo.
                    continue
                resolved = (path.parent / target).resolve()
                if resolved.is_relative_to(root.resolve()) and resolved.exists():
                    continue
                issues.append(LinkIssue(
                    source=path.relative_to(root).as_posix(),
                    line=line_number,
                    destination=raw,
                    resolved=(
                        resolved.relative_to(root.resolve()).as_posix()
                        if resolved.is_relative_to(root.resolve())
                        else "(outside repository)"
                    ),
                    historical=is_historical(path, root),
                ))
    return len(docs), issues


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--strict", action="store_true",
                        help="fail only for current (nonhistorical) broken links")
    args = parser.parse_args()
    total, issues = scan()
    current = [issue for issue in issues if not issue.historical]
    historical = [issue for issue in issues if issue.historical]
    for issue in issues:
        label = "HISTORICAL" if issue.historical else "CURRENT"
        print(f"{label}: {issue.source}:{issue.line} -> {issue.destination} "
              f"(missing: {issue.resolved})")
    print(f"Audited {total} Markdown files; "
          f"{len(current)} current broken links, "
          f"{len(historical)} historical broken links.")
    print("Old evidence is reported, never automatically deleted or rewritten.")
    return 1 if args.strict and current else 0


if __name__ == "__main__":
    raise SystemExit(main())
