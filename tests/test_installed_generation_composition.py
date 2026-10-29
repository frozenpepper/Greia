"""The release generation pointer must select all installed runtime policies."""

import os
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from greia_launcher import event_broker, installed_root, storage_broker
from greia_launcher.child_shell import GreiaChildShell
from greia_launcher.runtime_adapter import PythonRuntimeAdapter
from greia_launcher.supervisor import ActivitySupervisor


class InstalledGenerationCompositionTests(unittest.TestCase):
    def test_generation_symlink_selects_installed_security_and_ui(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            generation = root / "greia-software" / "generations" / "base"
            generation.mkdir(parents=True)
            link = root / "greia-os"
            link.symlink_to(generation, target_is_directory=True)
            env = {"GREIA_OS_ROOT": str(link)}
            with mock.patch.object(installed_root, "INSTALLED_APPLICATION_ROOT", link), \
                 mock.patch.dict(os.environ, env, clear=False):
                shell = object.__new__(GreiaChildShell)
                shell.paths = SimpleNamespace(root=link.resolve())
                self.assertTrue(shell._installed_root())
                self.assertIsNotNone(shell._system_chrome_coordinator())
                self.assertIsNotNone(shell._display_session_coordinator())
                supervisor = object.__new__(ActivitySupervisor)
                supervisor._require_sandbox_override = None
                self.assertTrue(supervisor._sandbox_required())
                self.assertEqual(PythonRuntimeAdapter().resolve_interpreter(), Path("/usr/bin/python3"))
                self.assertEqual(storage_broker._default_runtime_root(), Path("/run/greia-os/storage"))
                self.assertEqual(event_broker._default_runtime_root(), Path("/run/greia-os/events"))
                self.assertFalse(installed_root.is_installed_root(root / "checkout"))


if __name__ == "__main__":
    unittest.main()
