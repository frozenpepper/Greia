from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from greia_platform.system_chrome import ActivitySystemChromeLayout
from greia_simulator.device import parse_viewport
from greia_simulator.workspace import SimulatorWorkspace


REPO = Path(__file__).resolve().parents[1]
TOOL = REPO / "tools" / "headless_greia_simulator.py"

spec = importlib.util.spec_from_file_location("headless_greia_simulator_under_test", TOOL)
assert spec is not None and spec.loader is not None
headless = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = headless
spec.loader.exec_module(headless)


class HeadlessGreiaSimulatorTests(unittest.TestCase):
    def test_builtin_activity_dir_is_detected_and_identity_is_read(self) -> None:
        activity = REPO / "activities" / "enciclopedia_greia"
        self.assertTrue(headless._is_builtin_activity_dir(activity))
        self.assertEqual(
            headless._activity_id_from_dir(activity),
            "org.greia.enciclopedia",
        )

    def test_builtin_activity_is_not_republished_as_developer_unsigned(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            activity = REPO / "activities" / "enciclopedia_greia"
            with mock.patch.object(
                SimulatorWorkspace,
                "load_activity",
                side_effect=AssertionError("built-in Activity must not be republished"),
            ) as loader:
                workspace, target_id = headless._prepare_workspace(
                    Path(directory) / "state",
                    activity,
                    None,
                )
            try:
                loader.assert_not_called()
                self.assertEqual(target_id, "org.greia.enciclopedia")
                self.assertFalse(any(workspace.developer_root.iterdir()))
            finally:
                workspace.release_lock()

    def test_builtin_activity_rejects_conflicting_explicit_identity(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(ValueError, "disagrees"):
                headless._prepare_workspace(
                    Path(directory) / "state",
                    REPO / "activities" / "enciclopedia_greia",
                    "org.greia.shape-garden",
                )

    def test_encyclopedia_route_comes_from_child_visible_collection_hierarchy(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace = SimulatorWorkspace(REPO, Path(directory) / "state")
            workspace.ensure()
            route, identities = headless._discover_launch_route(
                workspace,
                "org.greia.enciclopedia",
                locale="it",
            )
            self.assertIn("org.greia.enciclopedia", identities)
            self.assertEqual(route.activity_id, "org.greia.enciclopedia")
            self.assertIn(route.collection_id, {"learn", "explore"})
            self.assertGreaterEqual(route.home_collection_index, 0)
            self.assertGreaterEqual(route.activity_index, 0)
            if route.subcollection_id is None:
                self.assertIsNone(route.subcollection_index)
            else:
                self.assertIsNotNone(route.subcollection_index)
                assert route.subcollection_index is not None
                self.assertGreaterEqual(route.subcollection_index, 0)
            self.assertGreater(route.navigation_cost, 0)
            self.assertIn("org.greia.enciclopedia", route.describe())

    def test_semantic_launcher_driver_follows_collection_first_route(self) -> None:
        child = mock.Mock()
        child.poll.return_value = None
        route = headless.ShellLaunchRoute(
            activity_id="org.example.target",
            collection_id="explore",
            home_collection_index=2,
            subcollection_id="nature",
            subcollection_index=1,
            activity_index=3,
        )

        # profile transition; 2 home-right frames; enter Collection;
        # 1 group-right frame; enter group; 3 Activity-right frames; Activity frame.
        states = [
            {"mode": "activities", "frame_count": count}
            for count in range(2, 11)
        ]
        states.append({"mode": "activity", "frame_count": 11})

        with mock.patch.object(
            headless,
            "_bridge_key",
            return_value=True,
        ) as bridge_key, mock.patch.object(
            headless,
            "_wait_for_state",
            side_effect=states,
        ) as wait_for_state:
            result = headless._send_profile_and_activity_launch(
                child=child,
                route=route,
            )

        self.assertEqual(result, states[-1])
        self.assertEqual(
            [call.args[0] for call in bridge_key.call_args_list],
            [
                "RETURN",                 # choose child profile
                "RIGHT", "RIGHT",        # select Explore on Collection Home
                "RETURN",                 # enter Explore
                "RIGHT",                  # select Nature group
                "RETURN",                 # enter Nature
                "RIGHT", "RIGHT", "RIGHT",  # select target Activity
                "RETURN",                 # launch through real supervisor path
            ],
        )
        self.assertEqual(wait_for_state.call_count, 10)

    def test_semantic_launcher_driver_supports_direct_collection_without_group(self) -> None:
        child = mock.Mock()
        child.poll.return_value = None
        route = headless.ShellLaunchRoute(
            activity_id="org.example.target",
            collection_id="learn",
            home_collection_index=1,
            subcollection_id=None,
            subcollection_index=None,
            activity_index=2,
        )
        states = [
            {"mode": "activities", "frame_count": 2},
            {"mode": "activities", "frame_count": 3},
            {"mode": "activities", "frame_count": 4},
            {"mode": "activities", "frame_count": 5},
            {"mode": "activities", "frame_count": 6},
            {"mode": "activity", "frame_count": 7},
        ]
        with mock.patch.object(
            headless,
            "_bridge_key",
            return_value=True,
        ) as bridge_key, mock.patch.object(
            headless,
            "_wait_for_state",
            side_effect=states,
        ):
            result = headless._send_profile_and_activity_launch(
                child=child,
                route=route,
            )
        self.assertEqual(result, states[-1])
        self.assertEqual(
            [call.args[0] for call in bridge_key.call_args_list],
            ["RETURN", "RIGHT", "RETURN", "RIGHT", "RIGHT", "RETURN"],
        )

    def test_protected_home_coordinate_uses_platform_chrome_authority(self) -> None:
        viewport = "1024x600"
        x, y = headless._protected_home_center(viewport)
        width, height = parse_viewport(viewport)
        chrome = ActivitySystemChromeLayout.for_surface(width, height)
        self.assertTrue(chrome.home_hitbox.contains(x, y))


if __name__ == "__main__":
    unittest.main()
