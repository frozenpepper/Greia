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

    def test_builtin_activity_index_comes_from_canonical_registry(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace = SimulatorWorkspace(REPO, Path(directory) / "state")
            workspace.ensure()
            index, identities = headless._discover_activity_index(
                workspace,
                "org.greia.enciclopedia",
            )
            self.assertEqual(identities[index], "org.greia.enciclopedia")
            self.assertEqual(len(identities), len(set(identities)))

    def test_semantic_launcher_driver_selects_profile_then_target_index(self) -> None:
        child = mock.Mock()
        child.poll.return_value = None
        states = (
            {"mode": "activities", "frame_count": 4},
            {"mode": "activity", "frame_count": 9},
        )
        with mock.patch.object(
            headless,
            "_bridge_key",
            return_value=True,
        ) as bridge_key, mock.patch.object(
            headless,
            "_wait_for_state",
            side_effect=states,
        ) as wait_for_state, mock.patch.object(
            headless.time,
            "sleep",
        ):
            result = headless._send_profile_and_activity_launch(
                child=child,
                target_index=3,
            )

        self.assertEqual(result, states[1])
        self.assertEqual(
            [call.args[0] for call in bridge_key.call_args_list],
            ["RETURN", "RIGHT", "RIGHT", "RIGHT", "RETURN"],
        )
        self.assertEqual(wait_for_state.call_count, 2)

    def test_protected_home_coordinate_uses_platform_chrome_authority(self) -> None:
        viewport = "1024x600"
        x, y = headless._protected_home_center(viewport)
        width, height = parse_viewport(viewport)
        chrome = ActivitySystemChromeLayout.for_surface(width, height)
        self.assertTrue(chrome.home_hitbox.contains(x, y))


if __name__ == "__main__":
    unittest.main()
