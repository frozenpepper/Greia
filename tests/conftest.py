"""pytest adapter for the Greia test lanes (``tests/suite_lanes.py``).

The canonical runner is ``make test`` (``tools/run_tests.py``); this keeps an
ad-hoc ``pytest tests`` run on the same lane and process hygiene. Set
``GREIA_TEST_LANE=full`` to include the heavy evidence suites.
"""

from __future__ import annotations

import sys
from pathlib import Path

_TESTS = Path(__file__).resolve().parent
for _path in (str(_TESTS.parent / "src"), str(_TESTS)):
    if _path not in sys.path:
        sys.path.insert(0, _path)

import suite_lanes  # noqa: E402

suite_lanes.install_test_process_hygiene()


def _dotted(nodeid: str) -> str:
    path, _, rest = nodeid.partition("::")
    module = path.removeprefix("tests/").removesuffix(".py").replace("/", ".")
    return ".".join([module, *[part for part in rest.split("::") if part]])


def pytest_collection_modifyitems(config, items) -> None:
    lane = suite_lanes.current_lane()
    if lane == "full" or config.args and any("::" in arg for arg in config.args):
        return
    kept, dropped = [], []
    for item in items:
        (kept if suite_lanes.selected(_dotted(item.nodeid), lane) else dropped).append(item)
    if dropped:
        config.hook.pytest_deselected(items=dropped)
        items[:] = kept
