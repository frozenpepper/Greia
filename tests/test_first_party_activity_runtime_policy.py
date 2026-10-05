"""First-party Activities must satisfy the curated child Python runtime policy.

Activity-specific unit suites exercise gameplay and rendering, but they can pass
while an Activity imports a module the production child runtime does not permit.
Keep this gate close to the runtime adapter so every bundled Python Activity is
checked against the same policy used by project validation and build composition.
"""

from __future__ import annotations

import unittest
from pathlib import Path

from greia_launcher.runtime_adapter import PythonRuntimeAdapter, PythonRuntimePolicy
from greia_platform.activities import ActivityRegistry, RuntimeCatalogue
from greia_platform.trust import ActivitySource, PackageTrust


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RUNTIME_PATH = PROJECT_ROOT / "runtime" / "child-runtime.toml"


class FirstPartyActivityRuntimePolicyTests(unittest.TestCase):
    def test_every_python_activity_satisfies_curated_runtime_policy(self) -> None:
        runtime = RuntimeCatalogue.load(RUNTIME_PATH)
        policy = PythonRuntimePolicy.load(RUNTIME_PATH)
        adapter = PythonRuntimeAdapter(policy=policy)
        activities = ActivityRegistry(
            [
                ActivitySource(
                    PROJECT_ROOT / "activities",
                    PackageTrust.BUILT_IN,
                    "greia-system",
                )
            ],
            runtime,
        ).discover()

        python_activities = [activity for activity in activities if activity.runtime_type == "python"]
        self.assertTrue(python_activities, "expected at least one bundled Python Activity")

        for activity in python_activities:
            with self.subTest(activity=activity.activity_id):
                adapter.validate_package(activity)


if __name__ == "__main__":
    unittest.main()
