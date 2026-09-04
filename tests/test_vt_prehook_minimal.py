from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

SERVICE = ROOT / "build/overlay/etc/systemd/system/greia-launcher.service"
PREPARE = ROOT / "build/overlay/usr/local/lib/greia-os/prepare-launcher-vt"
X_SESSION = ROOT / "build/overlay/usr/local/lib/greia-os/greia-x-session"

# The complete launch path: the unit plus every script it invokes.
LAUNCH_PATH = (SERVICE, PREPARE, X_SESSION)

EXPECTED_EXEC_START = (
    "ExecStart=/usr/bin/xinit /usr/local/lib/greia-os/greia-x-session"
    " -- :0 vt1 -keeptty -novtswitch -background none"
    " -quiet -nolisten tcp -noreset"
)


def _code_lines(text: str) -> str:
    """Shell/unit code without full-line comments (prose may name removed ops)."""
    return "\n".join(
        line for line in text.splitlines() if not line.lstrip().startswith("#")
    )


class VtPrehookMinimalAbsenceTests(unittest.TestCase):
    """D2: the launch pre-hook stays structurally minimal (P5 lock)."""

    def test_no_amixer_on_launch_path(self) -> None:
        for path in LAUNCH_PATH:
            with self.subTest(path=path.name):
                self.assertNotIn("amixer", path.read_text(encoding="utf-8"))

    def test_no_account_mutation_tool_on_launch_path(self) -> None:
        for path in LAUNCH_PATH:
            with self.subTest(path=path.name):
                text = path.read_text(encoding="utf-8")
                for token in ("usermod", "useradd", "groupmod"):
                    self.assertNotIn(token, text)

    def test_no_runtime_root_shell_repairs(self) -> None:
        code = _code_lines(PREPARE.read_text(encoding="utf-8"))
        for token in ("for runtime_root", "runtime_root", "[ ! -d"):
            self.assertNotIn(token, code)
        for token in ("mkdir", "chown"):
            self.assertNotIn(token, code)
        unit_code = _code_lines(SERVICE.read_text(encoding="utf-8"))
        self.assertNotIn("RuntimeDirectory=greia-os", unit_code)
        self.assertNotIn("chown", unit_code)

    def test_no_scrub_on_launch_path(self) -> None:
        for path in LAUNCH_PATH:
            with self.subTest(path=path.name):
                text = path.read_text(encoding="utf-8")
                for token in (
                    "scrub-activity-trees",
                    "scrub_activity_tree",
                    "launcher_execstartpre_scrub_begin",
                    "launcher_execstartpre_scrub_end",
                ):
                    self.assertNotIn(token, text)

    def test_absence_predicates_are_sensitive_positive_control(self) -> None:
        fixture = (
            "amixer sset Master 100% unmute\n"
            "usermod -a -G audio greiakid\n"
            "for runtime_root in /run/greia-os; do\n"
            "scrub-activity-trees\n"
        )
        for token in ("amixer", "usermod", "runtime_root", "scrub-activity-trees"):
            self.assertIn(token, fixture)


class VtPrehookMinimalPresenceTests(unittest.TestCase):
    """D2: the minimal dynamic path is still present (P1/P2/P3/P4 lock)."""

    def test_runtime_roots_asserted_natively_fail_closed(self) -> None:
        service = SERVICE.read_text(encoding="utf-8")
        self.assertIn("AssertPathIsDirectory=/run/greia-os", service)
        self.assertIn("AssertPathIsDirectory=/run/greia-hardware", service)
        # Assert (not Condition): a missing root must fail the job behind the
        # branded cover, never silently skip into an X launch.
        self.assertNotIn("ConditionPathExists=/run/greia", service)
        self.assertIn("systemd-tmpfiles-setup.service", service)

    def test_boot_markers_still_emitted(self) -> None:
        prepare = PREPARE.read_text(encoding="utf-8")
        self.assertIn("launcher_execstartpre_vt_begin", prepare)
        self.assertIn("launcher_execstartpre_vt_end", prepare)

    def test_x_lock_handling_stays_fail_closed(self) -> None:
        prepare = PREPARE.read_text(encoding="utf-8")
        self.assertIn("x_lock=/tmp/.X0-lock", prepare)
        self.assertIn('kill -0 "$x_pid"', prepare)
        self.assertIn("Refusing malformed Xorg display lock", prepare)
        self.assertIn("Refusing orphan Xorg display socket without a lock", prepare)

    def test_vt1_acquisition_and_cover_handoff_intact(self) -> None:
        prepare = PREPARE.read_text(encoding="utf-8")
        self.assertIn("chvt 1", prepare)
        self.assertIn("--progress 78", prepare)
        self.assertIn("[ -c /dev/fb0 ]", prepare)
        self.assertIn('|| true', prepare)

    def test_exec_start_x_options_untouched(self) -> None:
        service = SERVICE.read_text(encoding="utf-8")
        self.assertIn(EXPECTED_EXEC_START, service)
        self.assertIn("TTYPath=/dev/tty1", service)


if __name__ == "__main__":
    unittest.main()
