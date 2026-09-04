from __future__ import annotations

import os
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

from greia_platform.activities import (
    ActivityManifest,
    ActivityRegistry,
    ActivitySource,
    PackageTrust,
    RuntimeCatalogue,
)
from greia_platform.device_capabilities import DeviceCapabilityService
from greia_launcher.runtime_adapter import (
    RuntimeExitKind,
    RuntimeInvocation,
    RuntimeManager,
    RuntimeUnavailableError,
    RuntimeValidationError,
)
from greia_launcher.web_runtime import (
    WebRuntimeAdapter,
    WebRuntimePolicy,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RUNTIME_PATH = PROJECT_ROOT / "build" / "package-sets" / "child-runtime.toml"


def _make_web_manifest(
    root: Path,
    *,
    entrypoint: str = "index.html",
    activity_id: str = "org.greia.test-web",
    runtime_type: str = "web",
    required_capabilities: tuple[str, ...] = ("display", "pointer"),
) -> ActivityManifest:
    root.mkdir(parents=True, exist_ok=True)
    launch_path = root / entrypoint
    if not launch_path.exists() and entrypoint.endswith((".html", ".htm")):
        launch_path.write_text("<!doctype html><html><body>Test</body></html>", encoding="utf-8")

    return ActivityManifest(
        activity_id=activity_id,
        legacy_ids=(),
        title_key="title",
        version="0.1.0",
        runtime_type=runtime_type,
        api_version="0.1",
        entrypoint=Path(entrypoint),
        icon_id="default",
        categories=("play",),
        skills=(),
        events=(),
        difficulty=1,
        languages=("it",),
        required_capabilities=required_capabilities,
        optional_capabilities=(),
        requested_permissions=(),
        storage_schema_version=1,
        root=root,
    )


class WebRuntimeAdapterTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp_dir.name)
        self.fake_browser = self.root / "bin" / "fake-chromium"
        self.fake_browser.parent.mkdir(parents=True, exist_ok=True)
        self.fake_browser.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
        self.fake_browser.chmod(0o755)

    def tearDown(self) -> None:
        self.tmp_dir.cleanup()

    def test_validate_package_valid_html(self) -> None:
        adapter = WebRuntimeAdapter(self.fake_browser)
        manifest = _make_web_manifest(self.root / "act1")
        adapter.validate_package(manifest)

    def test_validate_package_rejects_wrong_runtime_type(self) -> None:
        adapter = WebRuntimeAdapter(self.fake_browser)
        manifest = _make_web_manifest(self.root / "act2", runtime_type="python")
        with self.assertRaisesRegex(RuntimeValidationError, "Web adapter cannot validate"):
            adapter.validate_package(manifest)

    def test_validate_package_rejects_non_html_entrypoint(self) -> None:
        adapter = WebRuntimeAdapter(self.fake_browser)
        (self.root / "act3").mkdir(parents=True, exist_ok=True)
        (self.root / "act3" / "main.py").write_text("print(1)", encoding="utf-8")
        manifest = _make_web_manifest(self.root / "act3", entrypoint="main.py")
        with self.assertRaisesRegex(RuntimeValidationError, "is not an HTML file"):
            adapter.validate_package(manifest)

    def test_validate_package_rejects_missing_entrypoint(self) -> None:
        adapter = WebRuntimeAdapter(self.fake_browser)
        (self.root / "act4").mkdir(parents=True, exist_ok=True)
        manifest = _make_web_manifest(self.root / "act4", entrypoint="missing.html")
        (self.root / "act4" / "missing.html").unlink(missing_ok=True)
        with self.assertRaisesRegex(RuntimeValidationError, "is not an HTML file"):
            adapter.validate_package(manifest)

    def test_validate_package_rejects_escaping_symlink(self) -> None:
        adapter = WebRuntimeAdapter(self.fake_browser)
        act_root = self.root / "act5"
        act_root.mkdir(parents=True, exist_ok=True)
        outside_file = self.root / "secret.txt"
        outside_file.write_text("secret", encoding="utf-8")
        symlink = act_root / "escape_link"
        symlink.symlink_to(outside_file)

        manifest = _make_web_manifest(act_root)
        with self.assertRaisesRegex(RuntimeValidationError, "escapes package root"):
            adapter.validate_package(manifest)

    def test_validate_package_rejects_forbidden_binary(self) -> None:
        adapter = WebRuntimeAdapter(self.fake_browser)
        act_root = self.root / "act6"
        act_root.mkdir(parents=True, exist_ok=True)
        (act_root / "evil.so").write_text("binary", encoding="utf-8")

        manifest = _make_web_manifest(act_root)
        with self.assertRaisesRegex(RuntimeValidationError, "forbidden binary"):
            adapter.validate_package(manifest)

    def test_validate_package_rejects_forbidden_file_name(self) -> None:
        adapter = WebRuntimeAdapter(self.fake_browser)
        act_root = self.root / "act7"
        act_root.mkdir(parents=True, exist_ok=True)
        (act_root / "package.json").write_text("{}", encoding="utf-8")

        manifest = _make_web_manifest(act_root)
        with self.assertRaisesRegex(RuntimeValidationError, "forbidden file name"):
            adapter.validate_package(manifest)

    def test_resolve_browser_configured_executable(self) -> None:
        adapter = WebRuntimeAdapter(self.fake_browser)
        self.assertEqual(adapter.resolve_browser(), self.fake_browser)

    def test_resolve_browser_configured_missing_raises_unavailable(self) -> None:
        adapter = WebRuntimeAdapter(self.root / "nonexistent-browser")
        with self.assertRaisesRegex(RuntimeUnavailableError, "configured web browser does not exist"):
            adapter.resolve_browser()

    def test_resolve_browser_via_env_var(self) -> None:
        adapter = WebRuntimeAdapter()
        with patch.dict(os.environ, {"GREIA_WEB_BROWSER": str(self.fake_browser)}):
            self.assertEqual(adapter.resolve_browser(), self.fake_browser)

    def test_resolve_browser_none_found_raises_unavailable(self) -> None:
        adapter = WebRuntimeAdapter()
        with patch.dict(os.environ, {}, clear=True):
            with patch("shutil.which", return_value=None):
                with patch("sys.platform", "linux"):
                    with self.assertRaisesRegex(RuntimeUnavailableError, "no supported kiosk web browser found"):
                        adapter.resolve_browser()

    def test_command_for_chromium_kiosk_args(self) -> None:
        chromium_path = self.root / "bin" / "chromium"
        chromium_path.write_text("", encoding="utf-8")
        chromium_path.chmod(0o755)

        adapter = WebRuntimeAdapter(chromium_path)
        manifest = _make_web_manifest(self.root / "act8")
        runtime_command = adapter.command_for(manifest)

        self.assertEqual(runtime_command.cwd, manifest.root)
        self.assertIn("--kiosk", runtime_command.command)
        self.assertIn("--incognito", runtime_command.command)
        self.assertIn("--no-first-run", runtime_command.command)
        self.assertTrue(any(arg.startswith("file://") for arg in runtime_command.command))

    def test_command_for_cog_kiosk_args(self) -> None:
        cog_path = self.root / "bin" / "cog"
        cog_path.write_text("", encoding="utf-8")
        cog_path.chmod(0o755)

        adapter = WebRuntimeAdapter(cog_path)
        manifest = _make_web_manifest(self.root / "act9")
        runtime_command = adapter.command_for(manifest)

        self.assertEqual(runtime_command.cwd, manifest.root)
        self.assertIn("--platform=wl", runtime_command.command)
        self.assertTrue(any(arg.startswith("file://") for arg in runtime_command.command))

    def test_command_for_firefox_kiosk_args(self) -> None:
        ff_path = self.root / "bin" / "firefox-esr"
        ff_path.write_text("", encoding="utf-8")
        ff_path.chmod(0o755)

        adapter = WebRuntimeAdapter(ff_path)
        manifest = _make_web_manifest(self.root / "act10")
        runtime_command = adapter.command_for(manifest)

        self.assertEqual(runtime_command.cwd, manifest.root)
        self.assertIn("--kiosk", runtime_command.command)
        self.assertIn("--private-window", runtime_command.command)

    def test_lifecycle_binding(self) -> None:
        adapter = WebRuntimeAdapter(self.fake_browser)
        host_dir = self.root / "host_data"
        child_dir = self.root / "child_data"
        binding = adapter.create_lifecycle_binding("session123", host_dir, child_dir)

        self.assertEqual(binding.control.session_id, "session123")
        env_dict = dict(binding.environment)
        self.assertIn("GREIA_ACTIVITY_READY_PATH", env_dict)
        self.assertIn("GREIA_ACTIVITY_STOP_PATH", env_dict)

    def test_launch_and_collect_exit(self) -> None:
        mock_process = Mock()
        mock_process.poll.return_value = 0
        factory = Mock(return_value=mock_process)

        adapter = WebRuntimeAdapter(self.fake_browser, process_factory=factory)
        invocation = RuntimeInvocation(
            command=("browser", "--kiosk", "file://index.html"),
            cwd=self.root,
            environment=(),
        )
        handle = adapter.launch(invocation)
        factory.assert_called_once()
        self.assertEqual(handle, mock_process)

        exit_info = adapter.collect_exit(handle)
        self.assertIsNotNone(exit_info)
        self.assertEqual(exit_info.return_code, 0)
        self.assertEqual(exit_info.kind, RuntimeExitKind.NORMAL)

    def test_runtime_manager_multi_adapter_routing(self) -> None:
        web_adapter = WebRuntimeAdapter(self.fake_browser)
        python_mock = Mock()
        python_mock.runtime_type = "python"
        python_mock.required_device_capabilities = frozenset()

        manager = RuntimeManager(
            [python_mock, web_adapter],
            DeviceCapabilityService.static({"display", "pointer"}, source_id="test"),
        )
        self.assertIn("python", manager.runtime_types)
        self.assertIn("web", manager.runtime_types)

        web_manifest = _make_web_manifest(self.root / "act_routing")
        prep = manager.prepare_launch(web_manifest)
        self.assertEqual(prep.compatibility.runtime_type, "web")
        self.assertTrue(prep.compatibility.compatible)
        self.assertIn("--kiosk", prep.command.command)


if __name__ == "__main__":
    unittest.main()
