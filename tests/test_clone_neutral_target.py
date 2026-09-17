"""Clone-neutral target state is composer-owned (T02 Repair B).

Single policy: ``compose_prepare_clone_neutral_target`` in
``build/lib/compose.sh`` runs inside ``compose_root`` for ``role=target`` so
the thin disk-image consumer and the release-payload staging path share one
canonical target state. The producer carries no second implementation and the
developer-image surface stays explicit.
"""

from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ENGINE = PROJECT_ROOT / "build/lib/compose.sh"
CONSUMER = PROJECT_ROOT / "build/build-image.sh"
PRODUCER = PROJECT_ROOT / "tools/build_release.py"
WORKFLOW = PROJECT_ROOT / "docs/development/GREIA_SYSTEM_UPDATE_RELEASE_WORKFLOW.md"


class CloneNeutralTargetTests(unittest.TestCase):
    def test_composer_owns_all_four_clone_neutral_checks(self) -> None:
        engine = ENGINE.read_text()
        self.assertIn("compose_prepare_clone_neutral_target() {", engine)
        self.assertIn(': > "$rootfs/etc/machine-id"', engine)
        self.assertIn('"$rootfs/var/lib/dbus/machine-id"', engine)
        self.assertIn('"$rootfs/var/lib/systemd/random-seed"', engine)
        self.assertIn('"$rootfs"/etc/ssh/ssh_host_*', engine)
        # Single definition: no duplicate implementation inside the composer.
        self.assertEqual(
            engine.count("compose_prepare_clone_neutral_target() {"),
            1,
        )

    def test_compose_root_applies_neutrality_for_target_only(self) -> None:
        engine = ENGINE.read_text()
        call = 'compose_prepare_clone_neutral_target "$rootfs"'
        self.assertIn(call, engine)
        # The call is guarded to the target role; the live-installer role
        # stays role-specific with a code-comment justification.
        call_pos = engine.index(call)
        window = engine[max(0, call_pos - 600):call_pos]
        self.assertIn('"$role" == "target"', window)
        # Live-installer exclusion is justified in code comments near the
        # single owner (definition through call site).
        defined_pos = engine.index("compose_prepare_clone_neutral_target() {")
        owner_region = engine[defined_pos:call_pos + 400]
        self.assertIn("live-installer", owner_region)
        # Ordered after developer provisioning and footprint hygiene so no
        # composer step after it can reintroduce clone identity.
        provision = engine.index('compose_maybe_provision_developer_ssh "$rootfs" "$role"')
        hygiene = engine.index('compose_footprint_hygiene "$rootfs"')
        self.assertLess(provision, call_pos)
        self.assertLess(hygiene, call_pos)
        # Live-installer exclusion is justified in code comments.
        self.assertIn("live-installer role is intentionally excluded", engine)

    def test_thin_consumer_carries_no_duplicate_cleanup(self) -> None:
        consumer = CONSUMER.read_text()
        self.assertIn('compose_root --profile "$PROFILE_PATH" --role target', consumer)
        self.assertNotIn(': > "$ROOTFS/etc/machine-id"', consumer)
        self.assertNotIn('rm -f "$ROOTFS/etc/ssh/ssh_host_"*', consumer)
        self.assertNotIn("var/lib/dbus/machine-id", consumer)
        self.assertNotIn("var/lib/systemd/random-seed", consumer)
        self.assertNotIn("machine-id", consumer)
        # The removal leaves a pointer to the single owner.
        self.assertIn("compose_prepare_clone_neutral_target", consumer)

    def test_payload_producer_path_cannot_bypass_target_policy(self) -> None:
        producer = PRODUCER.read_text()
        # No second implementation in the payload producer: it inherits the
        # composed target state instead of fixing up identity itself.
        self.assertNotIn("machine-id", producer)
        self.assertNotIn("ssh_host_", producer)
        self.assertNotIn("random-seed", producer)
        # The documented release flow routes payload staging through the
        # composed target root (role target), never around it.
        workflow = WORKFLOW.read_text()
        self.assertIn("composed target root", workflow)
        self.assertIn("role `target`", workflow)
        self.assertIn("--staging-dir", workflow)
        engine = ENGINE.read_text()
        self.assertIn("T04 slot producer", engine)

    def test_developer_image_behavior_stays_explicit(self) -> None:
        engine = ENGINE.read_text()
        # Developer provisioning is still explicit and gated.
        self.assertIn("compose_provision_developer_ssh_target() {", engine)
        self.assertIn('if [[ "$role_sets" == *developer-remote* ]]', engine)
        self.assertIn("etc/greia-os/developer-remote", engine)
        self.assertIn("etc/sudoers.d/greia-developer-remote", engine)
        self.assertIn("greia:greia", engine)
        # The neutral-target function removes only identity bytes; it never
        # touches the developer marker, sudoers rule or sshd config.
        start = engine.index("compose_prepare_clone_neutral_target() {")
        end = engine.index("# Main entry point", start)
        body = engine[start:end]
        self.assertNotIn("developer-remote", body)
        self.assertNotIn("sudoers", body)
        self.assertNotIn("sshd_config", body)
        self.assertNotIn("chpasswd", body)
        self.assertNotIn("AllowUsers", body)

    def test_neutral_function_produces_clone_neutral_state(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "rootfs"
            (root / "etc/ssh").mkdir(parents=True)
            (root / "var/lib/dbus").mkdir(parents=True)
            (root / "var/lib/systemd").mkdir(parents=True)
            (root / "etc/greia-os").mkdir(parents=True)
            (root / "etc/sudoers.d").mkdir(parents=True)
            (root / "etc/machine-id").write_text("cloned-identity\n")
            (root / "var/lib/dbus/machine-id").write_text("cloned\n")
            (root / "var/lib/systemd/random-seed").write_text("cloned\n")
            (root / "etc/ssh/ssh_host_rsa_key").write_text("cloned\n")
            (root / "etc/ssh/ssh_host_rsa_key.pub").write_text("cloned\n")
            (root / "etc/ssh/ssh_host_ed25519_key").write_text("cloned\n")
            (root / "etc/ssh/ssh_host_ecdsa_key").write_text("cloned\n")
            # Developer explicit surface that must survive neutralization.
            (root / "etc/greia-os/developer-remote").write_text("profile=x\n")
            (root / "etc/sudoers.d/greia-developer-remote").write_text("rule\n")
            script = (
                f'set -euo pipefail; source "{ENGINE}"; '
                f'compose_prepare_clone_neutral_target "{root}"'
            )
            completed = subprocess.run(
                ["bash", "-c", script],
                capture_output=True,
                text=True,
            )
            self.assertEqual(completed.returncode, 0, msg=completed.stderr)
            self.assertTrue((root / "etc/machine-id").is_file())
            self.assertEqual((root / "etc/machine-id").read_text(), "")
            self.assertFalse((root / "var/lib/dbus/machine-id").exists())
            self.assertFalse((root / "var/lib/systemd/random-seed").exists())
            self.assertEqual(list((root / "etc/ssh").glob("ssh_host_*")), [])
            self.assertEqual(
                (root / "etc/greia-os/developer-remote").read_text(),
                "profile=x\n",
            )
            self.assertEqual(
                (root / "etc/sudoers.d/greia-developer-remote").read_text(),
                "rule\n",
            )


if __name__ == "__main__":
    unittest.main()
