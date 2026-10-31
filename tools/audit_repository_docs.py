#!/usr/bin/env python3
"""Read-only repository Markdown link and documentation inventory audit.

Run from any directory:
    python3 tools/audit_repository_docs.py --scope maintained
    python3 tools/audit_repository_docs.py --scope all

Includes all tracked Markdown docs in the selected scope, not just root entry
pages. Older internal plans and operator reports are no longer published at the
current branch head. The maintained scope covers public instructions and
reusable public test specifications. Never deletes files.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
import re
import subprocess
from urllib.parse import unquote, urlsplit


ROOT = Path(__file__).resolve().parents[1]
_LINK = re.compile(r"!?(?:\[[^\]\n]*\])\(([^)\n]+)\)")
_HISTORICAL_PREFIXES = ("docs/plans/",)
_HISTORICAL_TESTING = "docs/testing/"


@dataclass(frozen=True)
class BrokenLink:
    source: Path
    line: int
    target: str


def tracked_markdown(root: Path) -> tuple[Path, ...]:
    """Use tracked files only; don't inspect local user's untracked evidence."""
    if (root / ".git").exists():
        result = subprocess.run(
            ["git", "-C", str(root), "ls-files", "-z", "--", "*.md"],
            check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        )
        paths = [Path(item.decode("utf-8")) for item in result.stdout.split(b"\0") if item]
    else:
        paths = [path.relative_to(root) for path in root.rglob("*.md")]
    return tuple(sorted(path for path in paths if (root / path).is_file()))


def maintained(path: Path) -> bool:
    name = path.as_posix()
    if name.startswith(_HISTORICAL_PREFIXES):
        return False
    if name.startswith(_HISTORICAL_TESTING):
        return name in {
            "docs/testing/HARDWARE_COMPATIBILITY_MATRIX.md",
            "docs/testing/VISUAL_ACCEPTANCE_EVIDENCE_CONTRACT.md",
        }
    return True


def targets(text: str):
    """Yield repo-relative Markdown links outside fenced code blocks."""
    fence = None
    for number, line in enumerate(text.splitlines(), 1):
        stripped = line.lstrip()
        mark = re.match(r"^(`{3,}|~{3,})", stripped)
        if mark:
            token = mark.group(1)
            if fence is None:
                fence = token[0]
            elif token[0] == fence:
                fence = None
            continue
        if fence:
            continue
        for match in _LINK.finditer(line):
            raw = match.group(1).strip()
            if raw.startswith("<") and ">" in raw:
                raw = raw[1:raw.index(">")]
            else:
                raw = raw.split(" ", 1)[0]
            raw = raw.strip()
            if raw and not raw.startswith("#"):
                url = urlsplit(raw)
                if not url.scheme and not url.netloc and url.path:
                    yield number, unquote(url.path), raw


def audit(root: Path, scope: str = "maintained") -> tuple[int, tuple[BrokenLink, ...]]:
    documents = tracked_markdown(root)
    if scope == "maintained":
        documents = tuple(doc for doc in documents if maintained(doc))
    elif scope != "all":
        raise ValueError("scope must be maintained or all")
    failures: list[BrokenLink] = []
    for source in documents:
        for number, target, original in targets((root / source).read_text(encoding="utf-8")):
            candidate = (root / source.parent / target).resolve()
            if not candidate.is_relative_to(root.resolve()) or not candidate.exists():
                failures.append(BrokenLink(source, number, original))
    return len(documents), tuple(failures)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scope", choices=("maintained", "all"), default="maintained")
    args = parser.parse_args()
    count, problems = audit(ROOT, args.scope)
    print(f"Markdown link inventory: {count} documents inspected; "
          f"{len(problems)} unresolved repository links ({args.scope}).")
    for issue in problems[:100]:
        print(f"{issue.source}:{issue.line}: {issue.target}")
    if len(problems) > 100:
        print(f"... {len(problems) - 100} more unresolved links")
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
