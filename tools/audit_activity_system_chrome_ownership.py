#!/usr/bin/env python3
"""Inventory Activity-side ownership of Greia Home/Back chrome during R7.

This is a migration audit, not the production navigation implementation.  The
trusted launcher/simulator owns real system chrome.  The audit finds remaining
first-party Python code that imports/calls the retired cooperative helpers or
still asks PygameReferenceCanvas to render system chrome.

Run with ``--strict`` when zero remaining migration debt is required.  Until the
catalogue migration is complete, the default reporting mode exits successfully
so the tool can be used to inventory debt without weakening unrelated gates.
"""

from __future__ import annotations

import argparse
import ast
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable


LEGACY_HELPERS = frozenset({"draw_system_chrome_overlay", "is_home_clicked"})


@dataclass(frozen=True, slots=True)
class Finding:
    path: str
    line: int
    kind: str
    symbol: str


def scan_python_source(path: Path, *, root: Path | None = None) -> tuple[Finding, ...]:
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(path))
    base = root.resolve() if root is not None else path.parent.resolve()
    try:
        display_path = str(path.resolve().relative_to(base))
    except ValueError:
        display_path = str(path)

    findings: list[Finding] = []
    imported_legacy_names: set[str] = set()

    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module == "greia_platform.activity_ui":
            for alias in node.names:
                if alias.name in LEGACY_HELPERS:
                    imported_legacy_names.add(alias.asname or alias.name)
                    findings.append(
                        Finding(
                            display_path,
                            node.lineno,
                            "legacy_helper_import",
                            alias.name,
                        )
                    )

        if isinstance(node, ast.Call):
            called_name: str | None = None
            if isinstance(node.func, ast.Name):
                called_name = node.func.id
            elif isinstance(node.func, ast.Attribute):
                called_name = node.func.attr
            if called_name in LEGACY_HELPERS or called_name in imported_legacy_names:
                findings.append(
                    Finding(
                        display_path,
                        node.lineno,
                        "legacy_helper_call",
                        called_name,
                    )
                )

            if isinstance(node.func, ast.Attribute) and node.func.attr == "present":
                for keyword in node.keywords:
                    if keyword.arg != "system_chrome":
                        continue
                    findings.append(
                        Finding(
                            display_path,
                            keyword.value.lineno,
                            "legacy_canvas_chrome_request",
                            "system_chrome",
                        )
                    )

    return tuple(
        sorted(
            set(findings),
            key=lambda item: (item.path, item.line, item.kind, item.symbol),
        )
    )


def scan_activity_tree(activity_root: Path) -> tuple[Finding, ...]:
    root = activity_root.resolve()
    findings: list[Finding] = []
    for path in sorted(root.rglob("*.py")):
        if any(part in {"__pycache__", ".venv", "venv"} for part in path.parts):
            continue
        findings.extend(scan_python_source(path, root=root.parent))
    return tuple(findings)


def _render_text(findings: Iterable[Finding]) -> str:
    items = tuple(findings)
    if not items:
        return "Activity system chrome ownership audit: blockers=0\n"
    lines = [f"Activity system chrome ownership audit: blockers={len(items)}"]
    lines.extend(
        f"{item.path}:{item.line}: {item.kind}: {item.symbol}"
        for item in items
    )
    return "\n".join(lines) + "\n"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Inventory first-party Activity ownership of retired Home/Back helpers"
    )
    parser.add_argument(
        "--activities",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "activities",
    )
    parser.add_argument("--json", action="store_true", dest="json_output")
    parser.add_argument(
        "--strict",
        action="store_true",
        help="return exit status 1 when any migration blocker remains",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    findings = scan_activity_tree(args.activities)
    if args.json_output:
        print(
            json.dumps(
                {
                    "schema_version": 1,
                    "blockers": len(findings),
                    "findings": [asdict(item) for item in findings],
                },
                indent=2,
                sort_keys=True,
            )
        )
    else:
        print(_render_text(findings), end="")
    return 1 if args.strict and findings else 0


if __name__ == "__main__":
    raise SystemExit(main())
