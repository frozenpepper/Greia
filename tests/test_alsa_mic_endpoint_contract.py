"""Contract tests for the Greia-owned ALSA microphone endpoint (ADR 0031).

Physical review: 2026-10-17_ACER_MIC_NOISE_FILTER.md (archived; see git history).
These are source contracts; they cannot prove the module opens on hardware.
"""

from __future__ import annotations

import os
import re
import shutil
import stat
import subprocess
import tempfile
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ASOUND_CONF = PROJECT_ROOT / "build" / "overlay" / "etc" / "asound.conf"
OVERRIDES = PROJECT_ROOT / "runtime" / "alsa" / "greia-activity-overrides.conf"
CAPTURE_VIEW = PROJECT_ROOT / "runtime" / "alsa" / "greia-activity-capture.conf"
PROBE = (
    PROJECT_ROOT
    / "build"
    / "overlay"
    / "usr"
    / "local"
    / "lib"
    / "greia-os"
    / "greia-audio-endpoint-probe"
)
MAKEFILE = PROJECT_ROOT / "src" / "greia_platform" / "audio_alsa" / "Makefile"
MODULE = "libasound_module_pcm_greia_mic_light.so"


def _config_body(path: Path) -> str:
    """Return the ALSA configuration without comments."""

    return "\n".join(
        line.split("#", 1)[0] for line in path.read_text(encoding="utf-8").splitlines()
    )


class AlsaEndpointConfigurationTests(unittest.TestCase):
    def test_module_is_named_by_bare_file_name(self) -> None:
        body = _config_body(ASOUND_CONF)
        match = re.search(r'pcm_type\.greia_denoise\s*\{\s*lib\s+"([^"]+)"', body)
        self.assertIsNotNone(match, "pcm_type.greia_denoise must name its module")
        # A bare name resolves to alsa-lib's compiled plugin directory for the
        # running architecture; an absolute multiarch path only fits one.
        self.assertEqual(MODULE, match.group(1))

    def test_no_multiarch_path_or_card_index_is_hard_coded(self) -> None:
        for path in (ASOUND_CONF, OVERRIDES):
            body = _config_body(path)
            self.assertNotIn("-linux-gnu", body, path)
            self.assertNotRegex(body, r"CARD=\d", path)
            self.assertNotRegex(body, r'"(plug)?hw:\d', path)

    def test_capture_slave_follows_alsa_default_card(self) -> None:
        body = _config_body(ASOUND_CONF)
        self.assertIn('"plughw:CARD="', body)
        self.assertIn("name defaults.pcm.card", body)
        self.assertIn("name defaults.pcm.device", body)

    def test_transport_contract_stays_pinned(self) -> None:
        body = _config_body(ASOUND_CONF)
        endpoint = body[body.index("pcm.greia_mic_light") :]
        for token in ("type greia_denoise", "format S16_LE", "channels 1", "rate 48000"):
            self.assertIn(token, endpoint)

    def test_routed_activity_view_reuses_the_single_endpoint_definition(self) -> None:
        body = _config_body(OVERRIDES)
        # The denoise stage and physical slave are defined once, in
        # /etc/asound.conf; routed Activities reference that endpoint.
        self.assertNotIn("type greia_denoise", body)
        self.assertNotIn("plughw", body)
        self.assertEqual(2, body.count('capture.pcm "greia_mic_light"'))
        self.assertEqual(2, body.count('"dmix:CARD="'))
        self.assertIn("defaults.namehint.extended off", body)
        self.assertIn('pcm.!sysdefault "greia_routed_audio"', body)

    def test_routed_view_loads_system_configuration_before_overrides(self) -> None:
        body = _config_body(CAPTURE_VIEW)
        # alsa.conf loads /etc/asound.conf, which defines greia_mic_light.
        self.assertLess(
            body.index("/usr/share/alsa/alsa.conf"),
            body.index("/opt/greia-os/runtime/alsa/greia-activity-overrides.conf"),
        )


class MakefileTests(unittest.TestCase):
    def test_install_dir_comes_from_the_compiler_without_arch_fallback(self) -> None:
        text = _config_body(MAKEFILE)
        self.assertIn("-print-multiarch", text)
        self.assertNotIn("dpkg-architecture", text)
        self.assertNotIn("i386-linux-gnu", text)
        self.assertIn('test -n "$(MULTIARCH)"', text)


class EndpointProbeTests(unittest.TestCase):
    """Run the real probe script against fake ``arecord``/``timeout`` tools."""

    def _run(self, arecord_body: str) -> tuple[subprocess.CompletedProcess[str], Path]:
        workspace = Path(tempfile.mkdtemp(prefix="greia-probe-"))
        self.addCleanup(shutil.rmtree, workspace, True)
        bin_dir = workspace / "bin"
        bin_dir.mkdir()
        run_dir = workspace / "run"
        tools = {
            "arecord": "#!/bin/sh\n" + arecord_body,
            # Mirrors coreutils timeout's argv: DURATION COMMAND [ARG]...
            "timeout": '#!/bin/sh\nshift\nexec "$@"\n',
        }
        for name, body in tools.items():
            tool = bin_dir / name
            tool.write_text(body, encoding="utf-8")
            tool.chmod(tool.stat().st_mode | stat.S_IXUSR)
        run_dir.mkdir()
        # Stale markers from an earlier probe must never survive a failure.
        (run_dir / "lightweight-ready").write_text("", encoding="utf-8")
        (run_dir / "advanced-ready").write_text("", encoding="utf-8")
        environment = {
            "PATH": f"{bin_dir}{os.pathsep}/usr/bin{os.pathsep}/bin",
            "GREIA_AUDIO_RUN_DIR": str(run_dir),
        }
        result = subprocess.run(
            ["sh", str(PROBE)],
            env=environment,
            text=True,
            capture_output=True,
            check=False,
            timeout=30,
        )
        return result, run_dir

    def test_working_endpoint_writes_marker_and_logs(self) -> None:
        result, run_dir = self._run('echo "$@" > "$GREIA_AUDIO_RUN_DIR/argv"\nexit 0\n')
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertTrue((run_dir / "lightweight-ready").is_file())
        self.assertFalse((run_dir / "advanced-ready").exists())
        self.assertIn("greia_mic_light ready", result.stderr)
        argv = (run_dir / "argv").read_text(encoding="utf-8")
        self.assertIn("-D greia_mic_light", argv)
        self.assertIn("-d 1", argv)

    def test_missing_module_removes_marker_and_logs_reason(self) -> None:
        result, run_dir = self._run(
            'echo "Cannot open shared library ' + MODULE + '" >&2\nexit 1\n'
        )
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertFalse((run_dir / "lightweight-ready").exists())
        self.assertFalse((run_dir / "advanced-ready").exists())
        self.assertIn("greia_mic_light unavailable (exit 1)", result.stderr)
        self.assertIn("Cannot open shared library", result.stderr)

    def test_stalled_capture_is_reported_as_timeout(self) -> None:
        result, run_dir = self._run("exit 124\n")
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertFalse((run_dir / "lightweight-ready").exists())
        self.assertIn("did not finish within 10s", result.stderr)

    def test_probe_bounds_the_capture_with_timeout(self) -> None:
        text = PROBE.read_text(encoding="utf-8")
        self.assertRegex(text, r'timeout "\$PROBE_SECONDS" arecord')


if __name__ == "__main__":
    unittest.main()
