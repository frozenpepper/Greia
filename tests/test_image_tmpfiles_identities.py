"""Every identity named in tmpfiles.d must actually be created by the image.

This file owned a real boot break. greia-os.conf named the group
``greiaprofiles`` while compose.sh created ``pipprofiles`` (the 2026-10-30
rename moved every file to ``greiaprofiles`` in one tranche).
systemd-tmpfiles therefore failed with "Failed to resolve group" and left
/run/greia-os as root:root 0755. Xorg runs as greiakid, so it could not open
/run/greia-os/Xorg.0.log, exited, and greia-launcher.service went into a
restart loop on every boot. The failure is silent in the sense that matters:
the unit reported "active" between restarts and the only visible symptom was
a loop.

Naming a group here must therefore fail the build, not the boot.
"""

from __future__ import annotations

import re
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
TMPFILES = PROJECT_ROOT / "build" / "overlay" / "etc" / "tmpfiles.d" / "greia-os.conf"
COMPOSE = PROJECT_ROOT / "build" / "lib" / "compose.sh"


def _logical_lines(text: str) -> list[str]:
    """Join backslash-continued shell lines into whole commands."""

    joined: list[str] = []
    pending = ""
    for raw in text.splitlines():
        line = raw.rstrip()
        if line.endswith("\\"):
            pending += line[:-1].strip() + " "
            continue
        joined.append(pending + line)
        pending = ""
    if pending:
        joined.append(pending)
    return joined


def _identities_created_by_compose() -> set[str]:
    created: set[str] = {"root"}
    for command in _logical_lines(COMPOSE.read_text(encoding="utf-8")):
        fields = command.split()
        groupadd_indexes = [i for i, f in enumerate(fields) if f.endswith("groupadd")]
        if groupadd_indexes:
            index = max(groupadd_indexes)
            for field in fields[index + 1:]:
                if field.startswith("-") or field.startswith("$"):
                    continue
                created.add(field)
                break
        if "useradd" in command:
            fields = command.split()
            index = max(i for i, f in enumerate(fields) if f.endswith("useradd"))
            created.add(fields[-1])
        for group in re.findall(r"--groups\s+([\w,]+)", command):
            created.update(part for part in group.split(",") if part)
    return created


def _tmpfiles_directories() -> dict[str, tuple[str, str, str]]:
    entries: dict[str, tuple[str, str, str]] = {}
    for line in TMPFILES.read_text(encoding="utf-8").splitlines():
        fields = line.split()
        if len(fields) >= 5 and fields[0] == "d":
            entries[fields[1]] = (fields[2], fields[3], fields[4])
    return entries


class TmpfilesIdentitiesExistTests(unittest.TestCase):
    def _entries_helper(self) -> None:
        """Defined below; see module-level _tmpfiles_directories."""

    def test_every_owner_and_group_named_in_tmpfiles_is_created(self) -> None:
        created = _identities_created_by_compose()
        missing: set[str] = set()
        for number, line in enumerate(
            TMPFILES.read_text(encoding="utf-8").splitlines(), start=1
        ):
            fields = line.split()
            if len(fields) < 5 or fields[0] not in {"d", "f"}:
                continue
            for identity in fields[3:5]:
                if identity not in created:
                    missing.add(f"{identity} (line {number})")
        self.assertEqual(
            missing,
            set(),
            "tmpfiles.d names identities compose.sh never creates; "
            "systemd-tmpfiles will fail and leave these paths unowned",
        )

    def test_child_shell_can_traverse_the_parent_home_to_its_own_tree(self) -> None:
        """greiakid must be able to reach /var/lib/greia-os/activity-packages.

        The launcher runs as greiakid and activity discovery stats that path. With
        the parent home at 0750 greiapel:greiapel, greiakid got EACCES rather
        than ENOENT, discovery raised PermissionError, and the launcher
        restart-looped on every boot. Traversal must be allowed; read access to
        the parent service's own files must not be.
        """

        entries = _tmpfiles_directories()
        mode, owner, _group = entries["/var/lib/greia-os"]
        others = int(mode[-3:], 8)
        self.assertTrue(
            others & 0o001,
            "/var/lib/greia-os must grant other-execute so greiakid can traverse "
            "to the activity package tree",
        )
        self.assertEqual(owner, "greiapanel")
        self.assertFalse(
            others & 0o004,
            "the parent service's home must stay unreadable to others",
        )
        self.assertIn("/var/lib/greia-os/activity-packages", entries)

    def test_parent_package_store_has_one_writer_and_bounded_child_read(self) -> None:
        entries = _tmpfiles_directories()
        mode, owner, group = entries["/var/lib/greia-os/activity-packages"]
        self.assertEqual((owner, group), ("greiapanel", "greiapanel"))
        self.assertEqual(int(mode, 8), 0o755)

    def test_run_directory_is_owned_by_the_identity_that_writes_it(self) -> None:
        """Xorg runs as greiakid and must be able to write its own log there."""

        entries = {
            fields[1]: (fields[3], fields[4])
            for fields in (
                line.split()
                for line in TMPFILES.read_text(encoding="utf-8").splitlines()
            )
            if len(fields) >= 5 and fields[0] == "d"
        }
        owner, _group = entries["/run/greia-os"]
        self.assertEqual(
            owner,
            "greiakid",
            "/run/greia-os must be owned by greiakid or Xorg cannot write "
            "Xorg.0.log and the launcher restart-loops",
        )

    def test_no_file_contradicts_another_declaration_of_the_same_path(self) -> None:
        """A duplicate declaration is applied too, and the later one wins.

        This module only ever read greia-os.conf, so a second file could
        re-declare the same path with a different owner and no test would see
        it. build/overlay/usr/lib/tmpfiles.d/greia-os-runtime.conf did exactly
        that for /run/greia-os: /usr/lib/tmpfiles.d sorts after
        /etc/tmpfiles.d, so root:root 0755 overrode greiakid, Xorg could not
        write its log, and greia-launcher.service restart-looped on a freshly
        installed machine - the same boot break this file exists to prevent.

        Agreeing duplicates (greia-os.conf and greia-runtime.conf both name the
        volatile roots identically) are tolerated; only disagreement is fatal,
        because that is what silently re-owns a path.
        """

        for overlay_name in ("overlay", "installer-overlay"):
            declared: dict[str, set[tuple[str, ...]]] = {}
            overlay_root = PROJECT_ROOT / "build" / overlay_name
            for path in sorted(overlay_root.rglob("tmpfiles.d/*.conf")):
                for fields in (
                    line.split()
                    for line in path.read_text(encoding="utf-8").splitlines()
                ):
                    if len(fields) >= 5 and fields[0] in {"d", "d+"}:
                        declared.setdefault(fields[1], set()).add(tuple(fields[:5]))

            for target, variants in declared.items():
                with self.subTest(overlay=overlay_name, path=target):
                    self.assertLessEqual(
                        len(variants),
                        1,
                        "tmpfiles files disagree about a path they all declare; "
                        f"{overlay_name}:{target} is declared as {sorted(variants)}, "
                        "and the last one applied silently wins",
                    )


if __name__ == "__main__":
    unittest.main()
