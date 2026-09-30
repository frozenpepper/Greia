"""Every identity named in tmpfiles.d must actually be created by the image.

This file owned a real boot break. greia-os.conf named the group
``greiaprofiles``, which compose.sh never creates - it creates ``pipprofiles``.
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
        if "groupadd" in command:
            fields = command.split()
            index = max(i for i, f in enumerate(fields) if f.endswith("groupadd"))
            for field in fields[index + 1:]:
                if field.startswith("-"):
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


class TmpfilesIdentitiesExistTests(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()