from __future__ import annotations

import ast
from pathlib import Path
import tomllib
import unittest


ROOT = Path(__file__).resolve().parents[1]
ACTIVITIES = ROOT / "activities"


def _call_name(node: ast.Call) -> tuple[str, ...]:
    parts: list[str] = []
    value: ast.expr = node.func
    while isinstance(value, ast.Attribute):
        parts.append(value.attr)
        value = value.value
    if isinstance(value, ast.Name):
        parts.append(value.id)
    return tuple(reversed(parts))


def _entrypoints() -> tuple[Path, ...]:
    result: list[Path] = []
    for manifest_path in sorted(ACTIVITIES.glob("*/activity.toml")):
        with manifest_path.open("rb") as handle:
            raw = tomllib.load(handle)
        runtime = raw.get("runtime", {})
        if not isinstance(runtime, dict):
            continue
        entrypoint = runtime.get("entrypoint")
        if not isinstance(entrypoint, str) or not entrypoint:
            continue
        path = manifest_path.parent / entrypoint
        if path.suffix == ".py":
            result.append(path)
    return tuple(result)


class FirstPartyActivityReadinessTests(unittest.TestCase):
    def test_ready_is_published_only_after_a_frame_presentation(self) -> None:
        checked: list[str] = []
        for path in _entrypoints():
            source = path.read_text(encoding="utf-8")
            if "mark_activity_ready" not in source:
                continue
            tree = ast.parse(source, filename=str(path))
            parents: dict[ast.AST, ast.AST] = {}
            for parent in ast.walk(tree):
                for child in ast.iter_child_nodes(parent):
                    parents[child] = parent

            ready_calls = [
                node
                for node in ast.walk(tree)
                if isinstance(node, ast.Call)
                and _call_name(node) == ("mark_activity_ready",)
            ]
            self.assertEqual(
                len(ready_calls),
                1,
                f"{path.relative_to(ROOT)} must publish READY exactly once in source",
            )
            ready = ready_calls[0]

            function: ast.FunctionDef | ast.AsyncFunctionDef | None = None
            cursor: ast.AST | None = ready
            while cursor is not None:
                if isinstance(cursor, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    function = cursor
                    break
                cursor = parents.get(cursor)
            self.assertIsNotNone(
                function,
                f"{path.relative_to(ROOT)} READY call must live inside its launch function",
            )
            assert function is not None

            presentations = [
                node
                for node in ast.walk(function)
                if isinstance(node, ast.Call)
                and _call_name(node) in {
                    ("pygame", "display", "flip"),
                    ("pygame", "display", "update"),
                }
            ]
            self.assertTrue(
                presentations,
                f"{path.relative_to(ROOT)} publishes READY without a display presentation",
            )
            self.assertLess(
                min(node.lineno for node in presentations),
                ready.lineno,
                f"{path.relative_to(ROOT)} must present its first usable frame before READY",
            )
            checked.append(path.parent.name)

        self.assertEqual(
            set(checked),
            {"painting", "shape_garden", "workshop_settings", "writing"},
            "new/removed first-party Python Activities must explicitly reconcile readiness coverage",
        )


if __name__ == "__main__":
    unittest.main()
