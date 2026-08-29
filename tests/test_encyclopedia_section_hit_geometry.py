from __future__ import annotations

import ast
from itertools import combinations
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
PAGES = ROOT / "activities" / "enciclopedia_greia" / "pages"
LOGICAL_SIZE = (1024, 600)
MIN_AUTHORED_HIT_WIDTH = 120
MIN_AUTHORED_HIT_HEIGHT = 100


class EncyclopediaSectionHitGeometryTests(unittest.TestCase):
    @staticmethod
    def _assignment(tree: ast.Module, name: str) -> ast.AST:
        for node in tree.body:
            if isinstance(node, ast.Assign) and any(
                isinstance(target, ast.Name) and target.id == name
                for target in node.targets
            ):
                return node.value
        raise AssertionError(f"missing module assignment: {name}")

    @classmethod
    def _target_rects(
        cls,
        path: Path,
        assignment_name: str,
        *,
        center_arg: int,
        size_arg: int,
    ) -> dict[str, tuple[int, int, int, int]]:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        value = cls._assignment(tree, assignment_name)
        if not isinstance(value, (ast.Tuple, ast.List)):
            raise AssertionError(f"{assignment_name} must be a literal tuple/list")

        result: dict[str, tuple[int, int, int, int]] = {}
        for item in value.elts:
            if not isinstance(item, ast.Call):
                raise AssertionError(f"{assignment_name} items must be constructor calls")
            target_id = str(ast.literal_eval(item.args[0]))
            center_x, center_y = (int(v) for v in ast.literal_eval(item.args[center_arg]))
            width, height = (int(v) for v in ast.literal_eval(item.args[size_arg]))
            result[target_id] = (
                center_x - width // 2,
                center_y - height // 2,
                width,
                height,
            )
        return result

    @staticmethod
    def _overlap(
        first: tuple[int, int, int, int],
        second: tuple[int, int, int, int],
    ) -> bool:
        ax, ay, aw, ah = first
        bx, by, bw, bh = second
        return not (
            ax + aw <= bx
            or bx + bw <= ax
            or ay + ah <= by
            or by + bh <= ay
        )

    def _assert_authored_hit_family(
        self,
        rects: dict[str, tuple[int, int, int, int]],
    ) -> None:
        logical_width, logical_height = LOGICAL_SIZE
        for target_id, (x, y, width, height) in rects.items():
            with self.subTest(target=target_id, check="size"):
                self.assertGreaterEqual(width, MIN_AUTHORED_HIT_WIDTH)
                self.assertGreaterEqual(height, MIN_AUTHORED_HIT_HEIGHT)
            with self.subTest(target=target_id, check="surface-bounds"):
                self.assertGreaterEqual(x, 0)
                self.assertGreaterEqual(y, 0)
                self.assertLessEqual(x + width, logical_width)
                self.assertLessEqual(y + height, logical_height)

        for (first_id, first), (second_id, second) in combinations(rects.items(), 2):
            with self.subTest(first=first_id, second=second_id, check="non-overlap"):
                self.assertFalse(
                    self._overlap(first, second),
                    f"authored hit regions overlap: {first_id}={first}, {second_id}={second}",
                )

    def test_body_authored_exhibit_hit_regions_are_large_bounded_and_disjoint(self) -> None:
        rects = self._target_rects(
            PAGES / "body.py",
            "BODY_TARGETS",
            center_arg=2,
            size_arg=4,
        )
        self.assertEqual(set(rects), {"senses", "teeth", "lungs", "heart", "bones"})
        self._assert_authored_hit_family(rects)

    def test_machines_authored_object_hit_regions_are_large_bounded_and_disjoint(self) -> None:
        rects = self._target_rects(
            PAGES / "machines.py",
            "MACHINE_TARGETS",
            center_arg=2,
            size_arg=3,
        )
        self.assertEqual(set(rects), {"gears", "magnet", "bicycle", "airplane", "bridge"})
        self._assert_authored_hit_family(rects)


if __name__ == "__main__":
    unittest.main()
