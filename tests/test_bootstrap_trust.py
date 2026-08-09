from __future__ import annotations

import hashlib
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
KEYRING = ROOT / "build/trust/debian-archive-keyring-2025.1.gpg"
PROVENANCE = ROOT / "build/trust/debian-archive-keyring-2025.1.provenance"


class BootstrapTrustTests(unittest.TestCase):
    def test_pinned_keyring_has_matching_recorded_digest(self) -> None:
        self.assertTrue(KEYRING.is_file())
        self.assertGreater(KEYRING.stat().st_size, 1024)
        facts = dict(
            line.split("=", 1)
            for line in PROVENANCE.read_text(encoding="utf-8").splitlines()
            if "=" in line
        )
        digest = hashlib.sha256(KEYRING.read_bytes()).hexdigest()
        self.assertEqual(facts["extracted_keyring_sha256"], digest)
        self.assertEqual(
            facts["upstream_package_sha256"],
            "9ea7778e443144ca490668737a8ab22dd3e748bb99e805e22ec055abeb3c7fac",
        )
        self.assertTrue(facts["upstream_url"].startswith("https://deb.debian.org/"))

    def test_both_builders_force_release_signature_verification(self) -> None:
        for name in ("build/build-image.sh", "build/build-installer-image.sh"):
            text = (ROOT / name).read_text(encoding="utf-8")
            self.assertIn("DEBIAN_ARCHIVE_KEYRING=", text)
            self.assertIn('--keyring="$DEBIAN_ARCHIVE_KEYRING"', text)
            self.assertIn("--force-check-gpg", text)
            self.assertIn("Pinned Debian archive keyring is missing", text)
            self.assertNotIn("--no-check-gpg", text)
            self.assertNotIn("--no-check-sig", text)


if __name__ == "__main__":
    unittest.main()
