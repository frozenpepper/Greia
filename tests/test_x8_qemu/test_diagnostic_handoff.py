"""Guard the offline failed-image holder preflight documented for Session 04."""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from tools.x8_qemu.product import control_runner_text


PROJECT_ROOT = Path(__file__).resolve().parents[2]
WORK_ORDER = PROJECT_ROOT / "docs/testing/2026-10-26_AB_FAILED_IMAGE_DIAGNOSTICS.md"
HOLDER_LOG = "/tmp/greia-ab-failed-image-holders.txt"


def documented_holder_preflight() -> str:
    """Return the exact holder-check fragment, excluding real git/image work."""
    document = WORK_ORDER.read_text(encoding="utf-8")
    start = document.index("# PSmisc 23.7 rejects a standalone --.")
    end = document.index('\n\nmkdir -m 0700 "$DIAG_OUT"', start)
    fragment = document[start:end]
    if HOLDER_LOG not in fragment:
        raise AssertionError("documented holder log path changed; update this focused guard")
    if "fuser -v -- \"$FAILED_IMAGE\"" in fragment:
        raise AssertionError("document reintroduced PSmisc's rejected standalone --")
    return fragment


class DocumentedHolderPreflightTests(unittest.TestCase):
    def _run_fragment(self, mode: str, *, timeout_mode: str = "") -> subprocess.CompletedProcess[str]:
        with tempfile.TemporaryDirectory(prefix="greia-fuser-preflight-") as tmp:
            root = Path(tmp)
            bin_dir = root / "bin"
            bin_dir.mkdir()
            holder_log = root / "holders.txt"

            stubs = {
                "sudo": "#!/bin/sh\nexec \"$@\"\n",
                "env": (
                    "#!/bin/sh\n"
                    "while [ \"$#\" -gt 0 ]; do\n"
                    "  case \"$1\" in *=*) export \"$1\"; shift ;; *) break ;; esac\n"
                    "done\n"
                    "exec \"$@\"\n"
                ),
                "timeout": (
                    "#!/bin/sh\n"
                    "if [ \"${TIMEOUT_MODE:-}\" = timeout ]; then exit 124; fi\n"
                    "shift\n"
                    "exec \"$@\"\n"
                ),
                "fuser": (
                    "#!/bin/sh\n"
                    "case \"${FUSER_MODE:-}\" in\n"
                    "  noholders) exit 1 ;;\n"
                    "  usage) echo 'fuser: invalid option -- -' >&2; echo 'Usage: fuser [options] file...' >&2; exit 1 ;;\n"
                    "  holders) echo \"$2: 1234\" >&2; exit 0 ;;\n"
                    "  *) echo \"unexpected fuser test mode: ${FUSER_MODE:-unset}\" >&2; exit 2 ;;\n"
                    "esac\n"
                ),
            }
            for name, source in stubs.items():
                path = bin_dir / name
                path.write_text(source, encoding="utf-8")
                path.chmod(0o755)

            fragment = documented_holder_preflight().replace(HOLDER_LOG, str(holder_log))
            script = "set -euo pipefail\n" + fragment + "\n"
            env = os.environ.copy()
            env.update(
                {
                    "PATH": f"{bin_dir}{os.pathsep}{env.get('PATH', '')}",
                    "FAILED_IMAGE": str(root / "existing-failed-clone.img"),
                    "FUSER_MODE": mode,
                    "TIMEOUT_MODE": timeout_mode,
                }
            )
            return subprocess.run(
                ["bash", "-c", script],
                cwd=PROJECT_ROOT,
                env=env,
                text=True,
                capture_output=True,
                timeout=10,
            )

    def test_one_and_empty_output_is_the_only_holder_check_pass(self) -> None:
        result = self._run_fragment("noholders")
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_psmisc_usage_error_status_one_with_output_fails_closed(self) -> None:
        result = self._run_fragment("usage")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Holder check did not prove the image is offline", result.stderr)
        self.assertIn("Usage: fuser", result.stderr)

    def test_reported_holder_status_zero_fails_closed(self) -> None:
        result = self._run_fragment("holders")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Failed image is in use; stop.", result.stderr)

    def test_timeout_status_124_fails_closed(self) -> None:
        result = self._run_fragment("noholders", timeout_mode="timeout")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Holder check did not prove the image is offline", result.stderr)


class ControlErrorCaptureTests(unittest.TestCase):
    def _run_capture(self, failure: str = "") -> tuple[subprocess.CompletedProcess[str], str | None, str]:
        with tempfile.TemporaryDirectory(prefix="greia-control-capture-") as tmp:
            root = Path(tmp)
            diag_dir = root / "persist" / "x8-control"
            serial_sink = root / "serial.txt"
            messages = root / "messages.txt"
            bin_dir = root / "bin"
            bin_dir.mkdir()
            real_head = shutil.which("head")
            self.assertIsNotNone(real_head)

            stubs = {
                "mkdir": (
                    "#!/bin/sh\n"
                    "if [ \"${FAIL_CAPTURE:-}\" = mkdir ]; then exit 21; fi\n"
                    "exec /bin/mkdir \"$@\"\n"
                ),
                "chmod": (
                    "#!/bin/sh\n"
                    "if [ \"${FAIL_CAPTURE:-}\" = chmod ]; then exit 22; fi\n"
                    "exec /bin/chmod \"$@\"\n"
                ),
                "mv": (
                    "#!/bin/sh\n"
                    "if [ \"${FAIL_CAPTURE:-}\" = mv ]; then exit 23; fi\n"
                    "exec /bin/mv \"$@\"\n"
                ),
                "sync": "#!/bin/sh\nif [ \"${FAIL_CAPTURE:-}\" = sync ]; then exit 24; fi\nexit 0\n",
                "head": (
                    "#!/bin/sh\n"
                    "if [ \"${FAIL_CAPTURE:-}\" = write ]; then exit 25; fi\n"
                    f"exec {real_head} \"$@\"\n"
                ),
                "timeout": "#!/bin/sh\nshift\nexec \"$@\"\n",
                "systemctl": (
                    "#!/bin/sh\n"
                    "if [ \"${1:-}\" = show ]; then echo 'ActiveState=inactive'; fi\n"
                    "exit 0\n"
                ),
                "journalctl": "#!/bin/sh\necho 'fixture journal line'\nexit 0\n",
            }
            for name, source in stubs.items():
                path = bin_dir / name
                path.write_text(source, encoding="utf-8")
                path.chmod(0o755)

            runner = control_runner_text()
            start = runner.index("control_error() {")
            end = runner.index("\ncontrol_exit() {", start)
            function = runner[start:end]
            function = function.replace("/var/lib/greia-os/x8-control", str(diag_dir))
            function = function.replace("/dev/ttyS0", str(serial_sink))
            script = (
                "set -euo pipefail\n"
                f"PHASE=update-stage\n"
                f"say() {{ printf '%s\\n' \"$*\" >> {str(messages)!r}; }}\n"
                + function
                + "\ncontrol_error 120\n"
            )
            env = os.environ.copy()
            env.update(
                {
                    "PATH": f"{bin_dir}{os.pathsep}{env.get('PATH', '')}",
                    "FAIL_CAPTURE": failure,
                }
            )
            result = subprocess.run(
                ["bash", "-c", script],
                cwd=PROJECT_ROOT,
                env=env,
                text=True,
                capture_output=True,
                timeout=10,
            )
            saved = diag_dir / "service-diagnostics.txt"
            saved_text = saved.read_text(encoding="utf-8") if saved.is_file() else None
            return result, saved_text, messages.read_text(encoding="utf-8")

    def test_success_marker_requires_persist_write_move_and_sync(self) -> None:
        result, saved_text, messages = self._run_capture()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("diagnostics captured before poweroff", messages)
        self.assertNotIn("diagnostic capture failed", messages)
        self.assertIsNotNone(saved_text)
        self.assertIn("fixture journal line", saved_text or "")

    def test_capture_failures_never_claim_diagnostics_were_captured(self) -> None:
        for failure in ("mkdir", "write", "chmod", "mv", "sync"):
            with self.subTest(failure=failure):
                result, _saved_text, messages = self._run_capture(failure)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIn("phase update-stage failed (exit 120)", messages)
                self.assertIn("diagnostic capture failed before poweroff", messages)
                self.assertNotIn("diagnostics captured before poweroff", messages)


if __name__ == "__main__":
    unittest.main()
