#!/usr/bin/env python3
"""Run the Greia unittest suite in one lane (see ``tests/suite_lanes.py``).

    python3 tools/run_tests.py                # fast lane (make test)
    python3 tools/run_tests.py --lane full    # everything (make test-full)
    python3 tools/run_tests.py --lane slow    # only the heavy evidence suites
    python3 tools/run_tests.py -v test_history test_x8_qemu.test_payload

Explicit test names bypass lane filtering. The runner installs the shared
test-process hygiene and always prints the slowest tests so regressions in
suite time are visible in every run.
"""

from __future__ import annotations

import argparse
import sys
import unittest
from pathlib import Path

REPOSITORY = Path(__file__).resolve().parents[1]
TESTS = REPOSITORY / "tests"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--lane", choices=("fast", "slow", "full"), default=None)
    parser.add_argument("-v", "--verbose", action="store_true")
    parser.add_argument("-f", "--failfast", action="store_true")
    parser.add_argument("--durations", type=int, default=15)
    parser.add_argument("names", nargs="*", help="explicit unittest names")
    arguments = parser.parse_args(argv)

    # Running this file puts tools/ first on sys.path, where helper scripts
    # (e.g. tools/greia_parent.py) would shadow the real packages.
    tools = Path(__file__).resolve().parent
    sys.path[:] = [entry for entry in sys.path if Path(entry or ".").resolve() != tools]
    # Match `python3 -m unittest discover -s tests` from the repository root:
    # the root (for `tools.x8_qemu...`), src/ and tests/ are importable.
    for path in (str(REPOSITORY), str(REPOSITORY / "src"), str(TESTS)):
        if path not in sys.path:
            sys.path.insert(0, path)
    import suite_lanes

    suite_lanes.install_test_process_hygiene()
    loader = unittest.TestLoader()
    if arguments.names:
        suite = loader.loadTestsFromNames(arguments.names)
    else:
        lane = arguments.lane or suite_lanes.current_lane()
        discovered = loader.discover(str(TESTS), top_level_dir=str(TESTS))
        suite = suite_lanes.filter_suite(discovered, lane)
        print(f"Greia test lane: {lane} ({suite.countTestCases()} tests)", flush=True)

    options: dict[str, object] = {
        "verbosity": 2 if arguments.verbose else 1,
        "failfast": arguments.failfast,
    }
    if sys.version_info >= (3, 12):
        options["durations"] = arguments.durations
    result = unittest.TextTestRunner(**options).run(suite)
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    raise SystemExit(main())
