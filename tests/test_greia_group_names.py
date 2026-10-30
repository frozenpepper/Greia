"""The image uses only the Greia technical group names.

``greiaprofiles`` (profile tree) and ``greiasettings`` (bounded settings)
replaced the prototype ``pip*`` group names on 2026-10-30, together with the
``greia-rootfs.squashfs`` installer payload and other ``pip-`` build names. Greia is pre-release and
does not migrate old images, so any surviving ``pip*`` group name in shipped
source would be a split identity like the 2026-10-01 /run/greia-os boot loop.
"""

from __future__ import annotations

import re
import subprocess
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SHIPPED = ("src", "build", "tools", "activities")
OLD_GROUP = re.compile(
    r"\bpip(?:profiles|settings)\b"
    r"|pip-(?:rootfs|initrd-check|runtime-audit-|install-target)|pip_os\.pth"
)


class GreiaGroupNameTests(unittest.TestCase):
    def test_no_prototype_group_names_in_shipped_source(self) -> None:
        result = subprocess.run(
            ["git", "-C", str(PROJECT_ROOT), "ls-files", "-z", "--", *SHIPPED],
            check=True, capture_output=True,
        )
        offenders = []
        for item in result.stdout.split(b"\0"):
            path = PROJECT_ROOT / item.decode("utf-8")
            if not item or not path.is_file():
                continue
            try:
                text = path.read_text(encoding="utf-8")
            except (UnicodeDecodeError, OSError):
                continue
            if OLD_GROUP.search(text):
                offenders.append(item.decode("utf-8"))
        self.assertEqual([], offenders)

    def test_image_creates_the_greia_groups(self) -> None:
        compose = (PROJECT_ROOT / "build" / "lib" / "compose.sh").read_text(encoding="utf-8")
        self.assertIn("groupadd --system greiasettings", compose)
        self.assertIn("groupadd --system greiaprofiles", compose)


if __name__ == "__main__":
    unittest.main()
