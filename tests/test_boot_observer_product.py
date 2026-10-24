"""P4.1 boot-observer product proof (disposable fixtures only).

Exercises the production entry point
``greia_platform.boot_observation.observe_and_reconcile_boot`` — the
single platform-owned early-boot observation owner — against disposable
tmpdir fixtures (cmdline + trusted layout + release-identity + grubenv).
No valued disk, loop device, or systemd runtime is contacted.
"""

from __future__ import annotations

import inspect
import json
import tempfile
import unittest
from pathlib import Path

from greia_platform.boot_health import BootHealthError
from greia_platform.boot_observation import (
    BootObservationResult,
    observe_and_reconcile_boot,
)
from greia_platform.grub_ab import GrubEnvBackend


_UUID_A = "11111111-2222-3333-4444-555555555555"
_UUID_A_FS = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
_UUID_B = "22222222-3333-4444-5555-666666666666"
_UUID_B_FS = "bbbbbbbb-cccc-dddd-eeee-ffffffffffff"
_UUID_P = "33333333-4444-5555-6666-777777777777"
_UUID_P_FS = "cccccccc-dddd-eeee-ffff-000000000000"
_UNKNOWN_UUID = "deadbeef-dead-beef-dead-beefdeadbeef"
_INSTALL_SHA = "ab" * 32
_RELEASE = "greia-0.17.0"
_RELEASE_SEQ = 9


def _canonical(payload: dict[str, object]) -> bytes:
    return (json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n").encode()


def _layout_dict(**overrides: object) -> dict[str, object]:
    base: dict[str, object] = {
        "accepted_release_id": "greia-0.16.0",
        "accepted_slot": "A",
        "boot_backend": "grub-ab-v1",
        "boot_control": {"active_slot": "A", "kind": "grub-env-v1"},
        "install_profile": "modern-amd64",
        "install_target_sha256": _INSTALL_SHA,
        "installed_at_unix": 1757000000,
        "layout_id": "modern-gpt-ab-v1",
        "persist": {"filesystem_uuid": _UUID_P_FS, "partuuid": _UUID_P},
        "platform_family": "standard-x86-64",
        "schema_version": 1,
        "slot_bytes": 1024 * 1024 * 1024,
        "system_a": {"filesystem_uuid": _UUID_A_FS, "partuuid": _UUID_A},
        "system_b": {"filesystem_uuid": _UUID_B_FS, "partuuid": _UUID_B},
    }
    base.update(overrides)
    return base


def _single_root_layout_dict() -> dict[str, object]:
    return {
        "accepted_release_id": "greia-0.16.0",
        "accepted_slot": None,
        "boot_backend": "none-v1",
        "boot_control": {"active_slot": None, "kind": "none-v1"},
        "install_profile": "legacy-x86-single",
        "install_target_sha256": _INSTALL_SHA,
        "installed_at_unix": 1757000000,
        "layout_id": "bios-single-ext4",
        "persist": {"filesystem_uuid": _UUID_P_FS, "partuuid": "1234abcd-03"},
        "platform_family": "legacy-x86",
        "schema_version": 1,
        "slot_bytes": 1024 * 1024 * 1024,
        "system_a": {"filesystem_uuid": _UUID_A_FS, "partuuid": "1234abcd-02"},
        "system_b": None,
    }


def _identity_dict(*, slot: str) -> dict[str, object]:
    return {
        "boot_backend": "grub-ab-v1",
        "layout_id": "modern-gpt-ab-v1",
        "release_id": _RELEASE,
        "role": f"system-{slot.lower()}",
        "slot": slot,
    }


class _Rig:
    """Disposable A/B machine: cmdline + layout + identity + grubenv."""

    def __init__(
        self,
        root: Path,
        *,
        booted_partuuid: str = _UUID_B,
        identity_slot: str = "B",
        cmdline_text: str | None = None,
        layout_payload: dict[str, object] | None = None,
        write_layout: bool = True,
    ) -> None:
        self.root = root
        self.cmdline = root / "cmdline"
        self.layout = root / "installed-layout.json"
        self.identity = root / "release-identity.json"
        self.grubenv_dir = root / "boot-control"
        if cmdline_text is None:
            cmdline_text = (
                f"BOOT_IMAGE=/boot/vmlinuz root=PARTUUID={booted_partuuid} ro quiet\n"
            )
        self.cmdline.write_text(cmdline_text, encoding="utf-8")
        if write_layout:
            self.layout.write_bytes(
                _canonical(layout_payload if layout_payload is not None else _layout_dict())
            )
        self.identity.write_bytes(_canonical(_identity_dict(slot=identity_slot)))
        self.backend = GrubEnvBackend.initialize(self.grubenv_dir, default_slot="A")

    def run(self) -> BootObservationResult:
        return observe_and_reconcile_boot(
            cmdline_path=self.cmdline,
            layout_record_path=self.layout,
            release_identity_path=self.identity,
            grubenv_dir=self.grubenv_dir,
        )

    def snapshot(self) -> dict[str, bytes]:
        out: dict[str, bytes] = {}
        for path in sorted(self.root.rglob("*")):
            if path.is_file() and not path.is_symlink():
                out[str(path.relative_to(self.root))] = path.read_bytes()
        return out


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _parse_unit(text: str) -> dict[str, list[str]]:
    current = ""
    out: dict[str, list[str]] = {}
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or line.startswith(";"):
            continue
        if line.startswith("[") and line.endswith("]"):
            current = line[1:-1].strip()
            continue
        if "=" not in line:
            continue
        key, _, value = line.partition("=")
        out.setdefault(f"{current}.{key.strip()}", []).append(value.strip())
    return out


class BootObserverProductTests(unittest.TestCase):
    def test_correct_slot_reconciled_from_kernel_root(self) -> None:
        """Positive path: kernel B -> last_booted B, default untouched."""
        with tempfile.TemporaryDirectory() as directory:
            rig = _Rig(Path(directory))
            # Simulate a staged candidate: one-shot B armed, default A.
            rig.backend.arm_one_shot("B")
            layout_before = rig.layout.read_bytes()
            result = rig.run()
            self.assertTrue(result.reconciled)
            self.assertEqual(result.observed_slot, "B")
            self.assertEqual(result.root_partuuid, _UUID_B)
            self.assertEqual(result.release_id, _RELEASE)
            state = GrubEnvBackend.attach(rig.grubenv_dir).inspect()
            self.assertEqual(state.last_booted_slot, "B")
            self.assertEqual(state.default_slot, "A")
            self.assertIsNone(state.one_shot_slot)
            # No layout-authority mutation.
            self.assertEqual(rig.layout.read_bytes(), layout_before)

    def test_zero_root_partuuid_refuses(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            rig = _Rig(
                Path(directory),
                cmdline_text="BOOT_IMAGE=/boot/vmlinuz ro quiet\n",
            )
            before = rig.snapshot()
            with self.assertRaisesRegex(BootHealthError, "no single root PARTUUID"):
                rig.run()
            self.assertEqual(rig.snapshot(), before)

    def test_multiple_root_partuuid_refuses(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            rig = _Rig(
                Path(directory),
                cmdline_text=(
                    f"BOOT_IMAGE=/boot/vmlinuz root=PARTUUID={_UUID_A} "
                    f"root=PARTUUID={_UUID_B} ro quiet\n"
                ),
            )
            before = rig.snapshot()
            with self.assertRaisesRegex(BootHealthError, "no single root PARTUUID"):
                rig.run()
            self.assertEqual(rig.snapshot(), before)

    def test_unknown_partuuid_refuses(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            rig = _Rig(Path(directory), booted_partuuid=_UNKNOWN_UUID)
            before = rig.snapshot()
            with self.assertRaisesRegex(BootHealthError, "matches no layout slot"):
                rig.run()
            self.assertEqual(rig.snapshot(), before)

    def test_release_identity_slot_mismatch_refuses(self) -> None:
        """Kernel runs B but the booted identity file claims A."""
        with tempfile.TemporaryDirectory() as directory:
            rig = _Rig(Path(directory), booted_partuuid=_UUID_B, identity_slot="A")
            before = rig.snapshot()
            with self.assertRaisesRegex(BootHealthError, "not the PARTUUID-resolved slot"):
                rig.run()
            self.assertEqual(rig.snapshot(), before)

    def test_absent_layout_is_bounded_noop(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            rig = _Rig(root, write_layout=False)
            self.assertFalse(rig.layout.exists())
            before = rig.snapshot()
            result = rig.run()
            self.assertFalse(result.reconciled)
            self.assertIsNone(result.observed_slot)
            self.assertIsNone(result.root_partuuid)
            self.assertIn("absent", result.reason)
            # No fabricated observation and no grubenv write.
            self.assertEqual(rig.snapshot(), before)
            self.assertIsNone(
                GrubEnvBackend.attach(rig.grubenv_dir).inspect().last_booted_slot
            )

    def test_single_root_layout_is_bounded_noop(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            rig = _Rig(
                root,
                cmdline_text="BOOT_IMAGE=/boot/vmlinuz root=PARTUUID=1234abcd-02 ro quiet\n",
                layout_payload=_single_root_layout_dict(),
            )
            identity_single = {
                "boot_backend": "none-v1",
                "layout_id": "bios-single-ext4",
                "release_id": _RELEASE,
                "role": "system-a",
                "slot": "A",
            }
            rig.identity.write_bytes(_canonical(identity_single))
            before = rig.snapshot()
            result = rig.run()
            self.assertFalse(result.reconciled)
            self.assertIsNone(result.observed_slot)
            self.assertIsNone(result.root_partuuid)
            self.assertIn("single-root", result.reason)
            # Single-root stays unavailable: nothing fabricated, nothing written.
            self.assertEqual(rig.snapshot(), before)
            self.assertIsNone(
                GrubEnvBackend.attach(rig.grubenv_dir).inspect().last_booted_slot
            )

    def test_second_run_is_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            rig = _Rig(Path(directory))
            first = rig.run()
            self.assertTrue(first.reconciled)
            grubenv_after_first = (rig.grubenv_dir / "grubenv").read_bytes()
            second = rig.run()
            self.assertTrue(second.reconciled)
            self.assertEqual(second.observed_slot, first.observed_slot)
            self.assertEqual(second.root_partuuid, first.root_partuuid)
            self.assertEqual(
                (rig.grubenv_dir / "grubenv").read_bytes(), grubenv_after_first
            )
            state = GrubEnvBackend.attach(rig.grubenv_dir).inspect()
            self.assertEqual(state.last_booted_slot, "B")
            self.assertEqual(state.default_slot, "A")

    def test_no_journal_health_commit_or_layout_mutation(self) -> None:
        """Success writes only greia_last_booted; nothing else moves."""
        with tempfile.TemporaryDirectory() as directory:
            rig = _Rig(Path(directory))
            layout_before = rig.layout.read_bytes()
            result = rig.run()
            self.assertTrue(result.reconciled)
            state = GrubEnvBackend.attach(rig.grubenv_dir).inspect()
            # No GRUB commit: persistent default is still the accepted slot.
            self.assertEqual(state.default_slot, "A")
            # No layout-authority mutation.
            self.assertEqual(rig.layout.read_bytes(), layout_before)
            # No journal/health/accepted-state residue anywhere under the rig.
            names = [path.name for path in rig.root.rglob("*")]
            self.assertNotIn("boot-journal.json", names)
            self.assertNotIn("boot-healthy-credential.json", names)
            self.assertNotIn("healthy-committing.json", names)
            self.assertNotIn("accepted.json", names)

    def test_entry_point_reuses_owner_mechanism_without_second_parser(self) -> None:
        """Production-proof wiring: one observer + reconcile, no new backend.

        Checked on the AST (attribute/call names), so documenting a
        prohibition in a docstring or comment can never trip the guard.
        """
        import ast

        import greia_platform.boot_observation as owner

        tree = ast.parse(inspect.getsource(owner))
        attrs = {node.attr for node in ast.walk(tree) if isinstance(node, ast.Attribute)}
        names = {node.id for node in ast.walk(tree) if isinstance(node, ast.Name)}
        calls = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                func = node.func
                if isinstance(func, ast.Attribute):
                    calls.add(func.attr)
                elif isinstance(func, ast.Name):
                    calls.add(func.id)
        # The single production observer is constructed and reconciled.
        self.assertIn("ProductionActualBootObserver", names)
        self.assertIn("reconcile", calls)
        self.assertIn("GrubEnvBackend", names)
        # Never infers the slot from the one-shot variable.
        self.assertNotIn("NEXT_ENTRY_KEY", attrs | names)
        self.assertNotIn("observe_booted_slot", calls)
        # Never commits a new persistent default or touches health/journal.
        self.assertNotIn("commit_accepted", calls)
        self.assertNotIn("BootHealthyProtocol", names)
        self.assertNotIn("BootTransactionCoordinator", names)


class BootObserverUnitContractTests(unittest.TestCase):
    def test_shipped_observer_unit_contract(self) -> None:
        """Structured unit contract: ordered before launcher, real entry point."""
        unit_path = (
            _repo_root()
            / "build"
            / "overlay"
            / "etc"
            / "systemd"
            / "system"
            / "greia-boot-observer.service"
        )
        self.assertTrue(unit_path.is_file(), "observer unit must be shipped")
        text = unit_path.read_text(encoding="utf-8")
        directives = _parse_unit(text)
        # Ordered before launcher acceptance ...
        before = directives.get("Unit.Before", [])
        self.assertTrue(
            any("greia-launcher.service" in value for value in before),
            "observer unit must be ordered Before greia-launcher.service",
        )
        # ... and after the boot-control/filesystem state it reads.
        after = directives.get("Unit.After", [])
        self.assertTrue(
            any("local-fs.target" in value for value in after),
            "observer unit must be ordered After local-fs.target",
        )
        required_mounts = " ".join(directives.get("Unit.RequiresMountsFor", [])).split()
        self.assertIn("/run/greia-persist", required_mounts)
        self.assertIn("/etc/greia-os/layout", required_mounts)
        self.assertIn("/boot/grub", required_mounts)
        self.assertIn(
            "GREIA_INSTALLED_LAYOUT_RECORD=/etc/greia-os/layout/installed-layout.json",
            directives.get("Service.Environment", []),
        )
        readonly_binds = {
            path
            for directive in directives.get("Service.BindReadOnlyPaths", [])
            for path in directive.split()
        }
        self.assertIn("/etc/greia-os/layout", readonly_binds)
        self.assertNotIn("/etc/greia-os/installed-layout.json", readonly_binds)
        # References the production observer entry point (module + owner).
        exec_starts = directives.get("Service.ExecStart", [])
        self.assertTrue(exec_starts, "observer unit must declare ExecStart")
        self.assertTrue(
            any("greia_platform.boot_observation" in value for value in exec_starts),
            "observer unit must reference the production observer entry point",
        )
        lowered = text.lower()
        self.assertIn("productionactualbootobserver", lowered)
        self.assertIn("reconcile", lowered)
        # Actually startable: install target present ...
        installs = directives.get("Install.WantedBy", [])
        self.assertTrue(installs, "observer unit must carry [Install] WantedBy=")
        self.assertEqual(directives.get("Service.Type", []), ["oneshot"])

    def test_observer_enabled_in_image_build(self) -> None:
        """Image enablement/ordering: the composition engine starts the observer."""
        build_script = _repo_root() / "build" / "lib" / "compose.sh"
        text = build_script.read_text(encoding="utf-8")
        self.assertIn(
            "greia-boot-observer.service",
            text,
            "image build must enable greia-boot-observer.service",
        )
        enable_index = text.index("greia-boot-observer.service")
        enable_window = text[max(0, enable_index - 400): enable_index + 400]
        self.assertIn("enable", enable_window)
        consumer = (_repo_root() / "build" / "build-image.sh").read_text(encoding="utf-8")
        self.assertIn("--role target", consumer)


if __name__ == "__main__":
    unittest.main()
