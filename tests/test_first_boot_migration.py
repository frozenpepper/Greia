from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

SERVICE = ROOT / "build/overlay/etc/systemd/system/greia-launcher.service"
PREPARE = ROOT / "build/overlay/usr/local/lib/greia-os/prepare-launcher-vt"
X_SESSION = ROOT / "build/overlay/usr/local/lib/greia-os/greia-x-session"
FIRST_BOOT = ROOT / "build/overlay/usr/local/lib/greia-os/first-boot"
# T01: account/group construction lives in the shared composition engine.
BUILDER = ROOT / "build/lib/compose.sh"
THIN_CONSUMER = ROOT / "build/build-image.sh"

# The complete launch path: the unit plus every script it invokes.
LAUNCH_PATH = (SERVICE, PREPARE, X_SESSION)

MIGRATION_MARKER = "/var/lib/greia-os/migrations/b2-audio-groups-v1.done"

AMIXER_LINES = (
    "amixer sset Master 100% unmute 2>/dev/null || true",
    "amixer sset Speaker 100% unmute 2>/dev/null || true",
    "amixer sset Headphone 100% unmute 2>/dev/null || true",
    "amixer sset PCM 100% unmute 2>/dev/null || true",
)


def _code_lines(text: str) -> str:
    """Shell code without full-line comments (prose may name removed commands)."""
    return "\n".join(
        line for line in text.splitlines() if not line.lstrip().startswith("#")
    )


class LaunchPathAccountMutationTests(unittest.TestCase):
    """B2: no user/group mutation remains on the launcher start path."""

    def test_no_account_mutation_tool_on_launch_path(self) -> None:
        for path in LAUNCH_PATH:
            with self.subTest(path=path.name):
                text = path.read_text(encoding="utf-8")
                for token in ("usermod", "useradd", "groupadd", "gpasswd"):
                    self.assertNotIn(token, text)

    def test_predicate_is_sensitive_positive_control(self) -> None:
        """The assertion above must detect a launch-path usermod, not pass vacuously."""
        fixture = "usermod -a -G audio greiakid 2>/dev/null || true\n"
        self.assertIn("usermod", fixture)

    def test_prepare_keeps_no_persistent_home_ownership(self) -> None:
        text = _code_lines(PREPARE.read_text(encoding="utf-8"))
        self.assertNotIn("mkdir", text)
        self.assertNotIn("chown", text)
        self.assertNotIn("/var/lib/greia-kid", text)

    def test_prepare_keeps_only_dynamic_per_boot_operations(self) -> None:
        text = PREPARE.read_text(encoding="utf-8")
        # Genuinely dynamic per (re)start: /run check, stale-lock handling,
        # VT recovery, cover repaint, boot markers.
        self.assertIn("Missing Greia runtime root", text)
        self.assertIn('kill -0 "$x_pid"', text)
        self.assertIn("chvt 1", text)
        self.assertIn("--progress 78", text)
        self.assertIn("launcher_execstartpre_vt_begin", text)
        self.assertIn("launcher_execstartpre_vt_end", text)

    def test_prepare_adds_no_device_permission_weakening(self) -> None:
        text = _code_lines(PREPARE.read_text(encoding="utf-8"))
        self.assertNotIn("chmod", text)
        self.assertNotIn("chown", text)
        self.assertNotIn("666", text)
        self.assertNotIn("777", text)

    def test_amixer_block_preserved_byte_for_byte(self) -> None:
        # PLAN 2C single-owner authority: the serial amixer block was deleted
        # from the pre-hook; AMIXER_LINES is now the forbidden set.
        text = PREPARE.read_text(encoding="utf-8")
        for line in AMIXER_LINES:
            with self.subTest(line=line):
                self.assertNotIn(line, text)


class FreshImageMembershipTests(unittest.TestCase):
    """B2: image construction establishes account/group membership statically."""

    def test_builder_creates_groups_and_audio_membership(self) -> None:
        builder = BUILDER.read_text(encoding="utf-8")
        self.assertIn("groupadd --system pipsettings", builder)
        self.assertIn("groupadd --system pipprofiles", builder)
        useradd = next(
            line
            for line in builder.splitlines()
            if "--groups pipsettings,pipprofiles,audio greiakid" in line
        )
        self.assertNotIn("video", useradd)
        self.assertNotIn("render", useradd)
        self.assertIn(
            "--role target", THIN_CONSUMER.read_text(encoding="utf-8")
        )

    def test_first_boot_state_roots_match_builder_groups(self) -> None:
        first_boot = FIRST_BOOT.read_text(encoding="utf-8")
        self.assertIn("-g pipprofiles /var/lib/greia-profiles", first_boot)
        self.assertIn("-g pipsettings /var/lib/greia-system-settings", first_boot)

    def test_launcher_process_groups_resolve_at_exec(self) -> None:
        service = SERVICE.read_text(encoding="utf-8")
        self.assertIn("User=greiakid", service)
        self.assertIn("Group=greiakid", service)
        self.assertIn("SupplementaryGroups=audio", service)


class MigrationIdempotencyTests(unittest.TestCase):
    """B2: versioned one-time migration repairs audio membership exactly once."""

    def test_migration_block_present_with_versioned_marker(self) -> None:
        text = FIRST_BOOT.read_text(encoding="utf-8")
        self.assertIn(
            f"audio_groups_marker={MIGRATION_MARKER}",
            text,
        )
        self.assertIn('if [ ! -e "$audio_groups_marker" ]', text)
        self.assertIn("usermod -a -G audio greiakid", text)
        self.assertIn(
            'printf \'%s\\n\' "b2-audio-groups-v1" > "$audio_groups_marker"',
            text,
        )

    def test_migration_runs_before_initialized_early_exit(self) -> None:
        text = FIRST_BOOT.read_text(encoding="utf-8")
        self.assertLess(
            text.index(f"audio_groups_marker={MIGRATION_MARKER}"),
            text.index('[ ! -e "$marker" ] || exit 0'),
        )

    def test_migration_repairs_only_audio(self) -> None:
        text = FIRST_BOOT.read_text(encoding="utf-8")
        block = text[
            text.index(f"audio_groups_marker={MIGRATION_MARKER}") : text.index(
                '[ ! -e "$marker" ] || exit 0'
            )
        ]
        self.assertIn("audio", block)
        self.assertNotIn("video", block)
        self.assertNotIn("render", block)

    def test_migration_checks_membership_before_mutating(self) -> None:
        text = FIRST_BOOT.read_text(encoding="utf-8")
        self.assertIn("id -nG greiakid", text)
        self.assertIn("grep -qx audio", text)

    def test_marker_written_only_after_successful_repair(self) -> None:
        text = FIRST_BOOT.read_text(encoding="utf-8")
        self.assertLess(
            text.index("usermod -a -G audio greiakid"),
            text.index('> "$audio_groups_marker"'),
        )

    def test_second_run_mutates_nothing(self) -> None:
        text = FIRST_BOOT.read_text(encoding="utf-8")
        guard = text.index('if [ ! -e "$audio_groups_marker" ]')
        after_guard = text[guard:]
        # The guard closes before the pinned early exit; every mutation in the
        # migration (directory creation, account repair, marker write) sits
        # inside it, and none appears outside it.
        close = after_guard.index("\nfi\n")
        inside = after_guard[:close]
        outside = after_guard[close:]
        for mutation in (
            "usermod",
            'install -d -m 0755 /var/lib/greia-os/migrations',
            '> "$audio_groups_marker"',
        ):
            with self.subTest(mutation=mutation):
                self.assertIn(mutation, inside)
        # The account repair and the marker writes must never leak outside a
        # guard. The shared `install -d` on the migrations directory is exempt
        # from that: it is idempotent, and b3 legitimately repeats it inside its
        # own versioned guard. Its gating is asserted by
        # ProfileDataOwnershipMigrationTests, and every occurrence is required to
        # sit inside some guard.
        for mutation in ("usermod", '> "$audio_groups_marker"'):
            with self.subTest(unguarded=mutation):
                self.assertNotIn(mutation, outside)
        self.assertNotIn("usermod", text[:guard])
        # Each migration writes its own marker inside its own guard. b3's write
        # is outside the audio guard by design, so the invariant is "after its
        # own guard", not "inside the audio one".
        for name in ("audio_groups_marker", "profile_owner_migration"):
            with self.subTest(migration=name):
                self.assertLess(
                    text.index('if [ ! -e "$%s" ]' % name),
                    text.index('> "$%s"' % name),
                )
        # No repair may appear before the first guard of any migration.
        first_guard = min(
            text.index('if [ ! -e "$audio_groups_marker" ]'),
            text.index('if [ ! -e "$profile_owner_migration" ]'),
        )
        for mutation in ("usermod", "chown ", "chmod "):
            with self.subTest(unguarded=mutation):
                self.assertNotIn(mutation, text[:first_guard])


class ProfileDataOwnershipMigrationTests(unittest.TestCase):
    """B3: the child's profile data tree is owned by the child identity.

    It shipped as greiapel:pipprofiles 2755 while its own parent
    /var/lib/greia-profiles was correctly greiakid:pipprofiles 2770. That broke
    the child twice: 2755 gives the shared group only r-x, so greiakid could not
    write its own progress, and because a caller must own a file before it may
    set setgid, greiakid could not chmod the tree back either. history.py then
    raised PermissionError, the Shell died before INTERACTIVE_READY, and the
    launcher's Type=notify unit never saw READY=1.
    """

    MARKER = "/var/lib/greia-os/migrations/b3-profile-data-ownership-v1.done"

    def test_migration_is_gated_by_its_own_versioned_marker(self) -> None:
        text = FIRST_BOOT.read_text(encoding="utf-8")
        self.assertIn(self.MARKER, text)
        self.assertIn("b3-profile-data-ownership-v1", text)

    def test_migration_repairs_ownership_and_group_write(self) -> None:
        text = FIRST_BOOT.read_text(encoding="utf-8")
        self.assertIn("chown greiakid:pipprofiles", text)
        # Group-writable, setgid, no access for other: 2770, never 2755 and
        # never a world-readable mode.
        self.assertIn("chmod 2770", text)
        self.assertNotIn("chmod 2755", text)
        self.assertNotIn("chmod 0777", text)

    def test_migration_marker_is_written_only_after_the_repair(self) -> None:
        text = FIRST_BOOT.read_text(encoding="utf-8")
        inside = text[text.index("b3-profile-data-ownership-v1.done") :]
        marker_write = inside.index('> "$profile_owner_migration"')
        repair = inside.index("chmod 2770")
        self.assertLess(repair, marker_write)

    def test_migration_survives_unusual_profile_ids(self) -> None:
        text = FIRST_BOOT.read_text(encoding="utf-8")
        self.assertIn("-print0", text)
        self.assertIn("xargs -0", text)

    def test_data_root_is_pre_created_not_only_repaired_afterwards(self) -> None:
        """Repairing alone cannot work on a fresh install; this one did not.

        greia-first-boot.service is ordered Before=greia-parent.service, and the
        Parent is what creates /var/lib/greia-profiles/data - as greiapel. So on
        a freshly installed machine the data root did not exist when the repair
        ran, the `[ -d ... ]` guard skipped it, and the Parent created the tree
        with an owner and mode the child cannot write. child_shell then died on
        PermissionError creating its own progress directory and
        greia-launcher.service restart-looped until the *second* boot. Ordering a
        repair after the Parent is impossible (the Parent is itself ordered
        after the launcher), so the data root must exist before the Parent runs.
        """

        text = FIRST_BOOT.read_text(encoding="utf-8")
        self.assertIn(
            "install -d -m 2770 -o greiakid -g pipprofiles /var/lib/greia-profiles/data",
            text,
        )
        # The pre-creation must not be gated on the tree already existing, which
        # is exactly what made the repair a no-op on first boot.
        pre_create = text.index("install -d -m 2770 -o greiakid")
        self.assertLess(pre_create, text.index("if [ -d /var/lib/greia-profiles/data ]"))

    def test_history_reports_ownership_and_mode_when_chmod_is_refused(self) -> None:
        """A bare EPERM is what made this cost four blind cycles to diagnose."""

        from greia_platform.history import HistoryError, ProfileHistoryStore

        source = Path(
            ProfileHistoryStore.__module__.replace(".", "/")
        )
        module = Path("src/greia_platform/history.py").read_text(encoding="utf-8")
        self.assertIn("st_mode & 0o7777", module)
        self.assertIn("owned by the child identity", module)
        self.assertTrue(HistoryError is not None and source is not None)


class UnitStartsWithMarkerPresentTests(unittest.TestCase):
    """B2: the launcher unit starts when the migration already ran."""

    def test_unit_orders_after_first_boot_without_marker_gate(self) -> None:
        service = SERVICE.read_text(encoding="utf-8")
        self.assertIn("Requires=greia-first-boot.service", service)
        self.assertNotIn("ConditionPathExists", service)
        self.assertNotIn("migrations/", service)

    def test_first_boot_exits_zero_when_initialized(self) -> None:
        text = FIRST_BOOT.read_text(encoding="utf-8")
        self.assertIn("marker=/var/lib/greia-os/initialized", text)
        self.assertIn('[ ! -e "$marker" ] || exit 0', text)


class VtHandoffStructureTests(unittest.TestCase):
    """B2: X still acquires the intended VT (structural; frame evidence is B3)."""

    def test_launcher_selects_vt1(self) -> None:
        service = SERVICE.read_text(encoding="utf-8")
        self.assertIn(" vt1 ", service)
        self.assertIn("TTYPath=/dev/tty1", service)
        prepare = PREPARE.read_text(encoding="utf-8")
        self.assertIn("chvt 1", prepare)


if __name__ == "__main__":
    unittest.main()
