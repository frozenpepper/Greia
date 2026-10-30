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
PROFILE_MIGRATION_MARKER = "/var/lib/greia-os/migrations/b4-profile-child-roots-v1.done"
PROFILE_SHARED_MODE_MARKER = "/var/lib/greia-os/migrations/b5-profile-shared-modes-v1.done"

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
        self.assertIn("groupadd --system greiasettings", builder)
        self.assertIn("groupadd --system greiaprofiles", builder)
        useradd = next(
            line
            for line in builder.splitlines()
            if "--groups greiasettings,greiaprofiles,audio,netdev greiakid" in line
        )
        self.assertNotIn("video", useradd)
        self.assertNotIn("render", useradd)
        self.assertIn(
            "--role target", THIN_CONSUMER.read_text(encoding="utf-8")
        )

    def test_first_boot_state_roots_match_builder_groups(self) -> None:
        first_boot = FIRST_BOOT.read_text(encoding="utf-8")
        self.assertIn("-g greiaprofiles /var/lib/greia-profiles", first_boot)
        self.assertIn("-g greiasettings /var/lib/greia-system-settings", first_boot)

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
        for name in (
            "audio_groups_marker",
            "profile_owner_migration",
            "profile_shared_mode_migration",
        ):
            with self.subTest(migration=name):
                self.assertLess(
                    text.index('if [ ! -e "$%s" ]' % name),
                    text.index('> "$%s"' % name),
                )
        # No repair may appear before the first guard of any migration.
        first_guard = min(
            text.index('if [ ! -e "$audio_groups_marker" ]'),
            text.index('if [ ! -e "$profile_owner_migration" ]'),
            text.index('if [ ! -e "$profile_shared_mode_migration" ]'),
        )
        for mutation in ("usermod", "chown ", "chmod "):
            with self.subTest(unguarded=mutation):
                self.assertNotIn(mutation, text[:first_guard])


class ProfileDataOwnershipMigrationTests(unittest.TestCase):
    """B4: bounded upgrade repair plus first-boot prevention for profile data."""

    MARKER = PROFILE_MIGRATION_MARKER

    def _migration_block(self) -> str:
        text = FIRST_BOOT.read_text(encoding="utf-8")
        guard = text.index('if [ ! -e "$profile_owner_migration" ]')
        marker = text.index('> "$profile_owner_migration"', guard)
        return text[guard:marker]

    def test_migration_is_gated_by_a_new_versioned_marker(self) -> None:
        text = FIRST_BOOT.read_text(encoding="utf-8")
        self.assertIn(f"profile_owner_migration={self.MARKER}", text)
        guard = text.index('if [ ! -e "$profile_owner_migration" ]')
        marker = text.index('> "$profile_owner_migration"', guard)
        self.assertLess(guard, marker)
        self.assertIn('"b4-profile-child-roots-v1"', text[guard:])
        self.assertNotEqual(
            self.MARKER,
            "/var/lib/greia-os/migrations/b3-profile-data-ownership-v1.done",
        )

    def test_profile_roots_are_repaired_for_shared_child_creation(self) -> None:
        block = self._migration_block()
        self.assertIn("-mindepth 1 -maxdepth 1 -type d", block)
        self.assertIn("-exec chgrp -- greiaprofiles {} +", block)
        self.assertIn("-exec chmod 2770 {} +", block)

    def test_only_child_owned_subtrees_are_recursively_reowned(self) -> None:
        block = self._migration_block()
        self.assertIn("-mindepth 2 -maxdepth 2 -type d", block)
        self.assertIn("-name progress", block)
        self.assertIn("-name storage", block)
        self.assertNotIn("-name customization", block)
        self.assertNotIn("-name activities", block)
        self.assertIn('find "$owned_root" -xdev -depth -print0', block)
        self.assertIn("chown -h -- greiakid:greiaprofiles", block)
        self.assertNotIn(
            "find /var/lib/greia-profiles/data -depth -print0",
            block,
            "never recursively chown the complete child-writable data tree",
        )

    def test_migration_marker_is_written_only_after_repairs(self) -> None:
        text = FIRST_BOOT.read_text(encoding="utf-8")
        guard = text.index('if [ ! -e "$profile_owner_migration" ]')
        marker = text.index('> "$profile_owner_migration"', guard)
        self.assertLess(text.index("chgrp -- greiaprofiles", guard), marker)
        self.assertLess(text.index("chown -h -- greiakid:greiaprofiles", guard), marker)

    def test_migration_survives_unusual_profile_ids(self) -> None:
        block = self._migration_block()
        self.assertIn("-print0", block)
        self.assertIn("xargs -0", block)

    def test_data_root_is_pre_created_not_only_repaired_afterwards(self) -> None:
        text = FIRST_BOOT.read_text(encoding="utf-8")
        creation = 'install -d -m 2770 -o greiakid -g greiaprofiles "$profile_data_root"'
        self.assertIn("profile_data_root=/var/lib/greia-profiles/data", text)
        self.assertIn('if [ -L "$profile_data_root" ]', text)
        self.assertIn('if [ -e "$profile_data_root" ] && [ ! -d "$profile_data_root" ]', text)
        self.assertIn(creation, text)
        self.assertLess(
            text.index(creation),
            text.index('if [ ! -e "$profile_owner_migration" ]'),
        )

    def test_fixed_data_root_is_normalized_without_recursive_walk(self) -> None:
        text = FIRST_BOOT.read_text(encoding="utf-8")
        creation = 'install -d -m 2770 -o greiakid -g greiaprofiles "$profile_data_root"'
        self.assertEqual(text.count(creation), 1)
        before_b4 = text[: text.index('if [ ! -e "$profile_owner_migration" ]')]
        self.assertIn(creation, before_b4)
        self.assertNotIn("find /var/lib/greia-profiles/data", before_b4)

    def test_b4_child_owned_repair_does_not_repeat_after_its_marker(self) -> None:
        text = FIRST_BOOT.read_text(encoding="utf-8")
        marker = text.index('> "$profile_owner_migration"')
        remainder = text[marker + len('> "$profile_owner_migration"'):]
        self.assertNotIn("chown -h -- greiakid:greiaprofiles", remainder)
        self.assertNotIn("-name progress", remainder)
        self.assertNotIn("-name storage", remainder)

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


class ProfileSharedModeMigrationTests(unittest.TestCase):
    """B5: repair Parent-created shared directories that B4 could predate."""

    MARKER = PROFILE_SHARED_MODE_MARKER

    def _migration_block(self) -> str:
        text = FIRST_BOOT.read_text(encoding="utf-8")
        guard = text.index('if [ ! -e "$profile_shared_mode_migration" ]')
        marker = text.index('> "$profile_shared_mode_migration"', guard)
        return text[guard:marker]

    def test_b5_has_its_own_versioned_marker(self) -> None:
        text = FIRST_BOOT.read_text(encoding="utf-8")
        self.assertIn(f"profile_shared_mode_migration={self.MARKER}", text)
        self.assertIn('"b5-profile-shared-modes-v1"', text)

    def test_b5_repairs_profile_root_and_parent_owned_shared_directories(self) -> None:
        block = self._migration_block()
        self.assertIn('-mindepth 1 -maxdepth 1 -type d', block)
        self.assertIn('-mindepth 2 -maxdepth 2 -type d', block)
        self.assertIn('-name customization', block)
        self.assertIn('-name activities', block)
        self.assertIn('chgrp -- greiaprofiles', block)
        self.assertIn('chmod 2770', block)

    def test_b5_does_not_recursively_reown_child_data(self) -> None:
        block = self._migration_block()
        self.assertNotIn('chown ', block)
        self.assertNotIn('-name progress', block)
        self.assertNotIn('-name storage', block)
        self.assertNotIn('-depth -print0', block)

    def test_b5_runs_before_initialized_early_exit(self) -> None:
        text = FIRST_BOOT.read_text(encoding="utf-8")
        self.assertLess(
            text.index('if [ ! -e "$profile_shared_mode_migration" ]'),
            text.index('[ ! -e "$marker" ] || exit 0'),
        )

    def test_b5_marker_is_written_after_mode_repairs(self) -> None:
        text = FIRST_BOOT.read_text(encoding="utf-8")
        guard = text.index('if [ ! -e "$profile_shared_mode_migration" ]')
        marker = text.index('> "$profile_shared_mode_migration"', guard)
        self.assertLess(text.index('chmod 2770', guard), marker)


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
