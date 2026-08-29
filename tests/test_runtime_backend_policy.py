from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from greia_launcher.runtime_adapter import PythonRuntimeAdapter, RuntimeValidationError
from greia_platform.activities import ActivityManifest
from greia_platform.input_core import InteractionProfile


class PythonRuntimeBackendPolicyTests(unittest.TestCase):
    def _manifest(self, source: str) -> ActivityManifest:
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        root = Path(temp.name)
        (root / "main.py").write_text(source, encoding="utf-8")
        return ActivityManifest(
            activity_id="org.greia.test.backend-policy",
            legacy_ids=(),
            title_key="activity.test.title",
            version="0.1.0",
            runtime_type="python",
            api_version="0.1",
            entrypoint=Path("main.py"),
            icon_id="test",
            categories=("test",),
            skills=(),
            events=(),
            difficulty=1,
            languages=("en",),
            required_capabilities=(),
            optional_capabilities=(),
            requested_permissions=(),
            storage_schema_version=1,
            root=root,
            input_profile=InteractionProfile.HYBRID.value,
        )

    def test_installed_adapter_rejects_backend_environment_access(self) -> None:
        manifest = self._manifest(
            'import os\nbackend = os.getenv("DISPLAY")\n'
        )

        with self.assertRaisesRegex(RuntimeValidationError, "backend-environment"):
            PythonRuntimeAdapter().validate_package(manifest)

    def test_installed_adapter_rejects_pygame_backend_introspection(self) -> None:
        manifest = self._manifest(
            'import pygame\nbackend = pygame.display.get_wm_info()\n'
        )

        with self.assertRaisesRegex(RuntimeValidationError, "backend-introspection"):
            PythonRuntimeAdapter().validate_package(manifest)

    def test_installed_adapter_allows_runtime_neutral_pygame_display_path(self) -> None:
        manifest = self._manifest(
            """
import pygame
screen = pygame.display.set_mode((1024, 600), pygame.FULLSCREEN)
backdrop = pygame.Surface(screen.get_size()).convert()
pygame.display.flip()
"""
        )

        PythonRuntimeAdapter().validate_package(manifest)

    def test_installed_adapter_does_not_pretend_chrome_migration_is_complete(self) -> None:
        manifest = self._manifest(
            """
from greia_platform.activity_ui import is_home_clicked
"""
        )

        # R7.1 blocks new backend authority immediately. Existing cooperative
        # Home/controller usage remains explicit MIGRATION debt until R7.3-R7.5.
        PythonRuntimeAdapter().validate_package(manifest)


if __name__ == "__main__":
    unittest.main()
