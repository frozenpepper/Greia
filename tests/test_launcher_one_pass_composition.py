"""One-pass source composition for launcher startup (T36, B04 degrade).

Boot resolves configured sources once, loads each source's trusted index
without re-running package validation, resolves cross-source identity/alias
collisions once through the trust-aware degrade resolver (built-in wins over
developer duplicates; any other ambiguous group is rejected and boot
continues degraded), and builds one seeded registry plus one
runtime/catalogue set. Activation-time ``registration_for`` reuses the
index-loaded proof instead of recomputing digests or revalidating trees.
"""

from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from greia_launcher import main as launcher_main
from greia_launcher import composition as launcher_composition
from greia_platform.activities import (
    ActivityRegistry,
    ActivityValidationError,
    RuntimeCatalogue,
    resolve_activity_collisions,
)
from greia_platform.activity_index import ActivityIndexError, build_index
from greia_platform.trust import ActivitySource, PackageTrust


def _write_activity(
    root: Path,
    *,
    activity_id: str,
    legacy_ids: tuple[str, ...] = (),
    api_version: str = "0.1",
) -> Path:
    legacy = ", ".join(f'"{item}"' for item in legacy_ids)
    root.mkdir(parents=True, exist_ok=True)
    root.joinpath("activity.toml").write_text(
        f'''[activity]
id = "{activity_id}"
legacy_ids = [{legacy}]
title_key = "Test Activity"
version = "1.0.0"
icon = "robot"
languages = ["*"]

[presentation]
categories = ["play"]

[education]
categories = ["test"]
difficulty = 1
skills = [{{ id = "test.skill", weight = 1 }}]
events = [{{ id = "probe.completed", kind = "completion" }}]

[runtime]
type = "python"
api_version = "{api_version}"
entrypoint = "main.py"

[input]
profile = "hybrid"

[requirements]
required_capabilities = []
optional_capabilities = []

[permissions]
requested = []

[storage]
schema_version = 1
''',
        encoding="utf-8",
    )
    root.joinpath("main.py").write_text("pass\n", encoding="utf-8")
    return root


def _write_index(
    *,
    source_root: Path,
    source: ActivitySource,
    runtime: RuntimeCatalogue,
    dest: Path,
) -> None:
    """Serialize the production index for a fixture tree (setup only)."""

    registry = ActivityRegistry((source,), runtime, fail_closed=False)
    registrations = registry.discover_registrations()
    build_index(registrations, source=source, runtime=runtime).write_file(dest)


class _NoValidation:
    """Assert no package validation runs inside the wrapped block."""

    def __init__(self, test: unittest.TestCase) -> None:
        self._test = test
        self._patches: list = []

    def __enter__(self) -> "_NoValidation":
        import greia_platform.activities as activities

        self._forbidden = (
            mock.patch.object(
                activities.ActivityRegistry,
                "validate_registration",
                side_effect=AssertionError("must not re-validate"),
            ),
            mock.patch.object(
                activities.ActivityRegistry,
                "discover_registrations",
                side_effect=AssertionError("must not re-discover"),
            ),
            mock.patch.object(
                activities.ActivityRegistry,
                "_validate_tree",
                side_effect=AssertionError("must not re-validate trees"),
            ),
            mock.patch(
                "greia_platform.activities.package_digest",
                side_effect=AssertionError("must not recompute digests"),
            ),
        )
        for patcher in self._forbidden:
            self._patches.append(patcher.__enter__())
        return self

    def __exit__(self, *args: object) -> None:
        for patcher in self._forbidden:
            patcher.__exit__(None, None, None)
        self._patches.clear()


class OnePassCompositionTests(unittest.TestCase):
    def _paths(self, builtin_root: Path, dev_root: Path | None) -> SimpleNamespace:
        return SimpleNamespace(
            activities=builtin_root,
            developer_activities=dev_root,
        )

    def test_builtin_index_loads_without_revalidation_as_one_set(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            builtin_root = Path(tmp) / "builtin"
            dev_root = Path(tmp) / "dev"
            # Missing Parent root: contributes no registrations and performs
            # no scan, so the no-validation spy covers the whole compose.
            parent_root = Path(tmp) / "parent-missing"
            self.assertFalse(parent_root.exists())
            _write_activity(
                builtin_root / "builtin.pkg", activity_id="org.greia.builtin-probe"
            )
            _write_activity(
                dev_root / "dev.pkg", activity_id="org.greia.dev-probe"
            )
            runtime = RuntimeCatalogue.default_safe()
            builtin_source = ActivitySource(
                builtin_root, PackageTrust.BUILT_IN, "greia-system"
            )
            index_path = Path(tmp) / "builtin-index.json"
            _write_index(
                source_root=builtin_root,
                source=builtin_source,
                runtime=runtime,
                dest=index_path,
            )
            marker = Path(tmp) / "no-marker"
            self.assertFalse(marker.exists())
            with mock.patch.dict(
                os.environ,
                {
                    launcher_main.DEVELOPER_MARKER_ENV_VAR: str(marker),
                    launcher_composition.BUILT_IN_INDEX_ENV_VAR: str(index_path),
                    launcher_composition.PARENT_ACTIVITY_ROOT_ENV_VAR: str(
                        parent_root
                    ),
                },
                clear=False,
            ):
                paths = self._paths(builtin_root, dev_root)
                boot_sources = launcher_main.boot_activity_sources(paths)
                # Developer mode off: the gated boot set excludes the dev root
                # even though it is configured.
                self.assertEqual(len(boot_sources), 1)
                with _NoValidation(self):
                    content = launcher_composition.compose_boot_content(
                        runtime, boot_sources
                    )
                ids = [item.activity_id for item in content.activities]
                self.assertEqual(ids, ["org.greia.builtin-probe"])
                self.assertFalse(content.parent_degraded)
                self.assertEqual(len(content.sources), 2)
                self.assertEqual(
                    content.sources[0].source_id, launcher_main.BUILT_IN_SOURCE_ID
                )
                # Single registration set: every manifest resolves through the
                # seeded registry without recomputation.
                with _NoValidation(self):
                    for manifest in content.activities:
                        registration = content.registry.registration_for(manifest)
                        self.assertEqual(
                            registration.manifest.activity_id, manifest.activity_id
                        )
                        self.assertEqual(
                            registration.package_trust, PackageTrust.BUILT_IN
                        )

    def test_parent_index_loads_without_revalidation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            parent_root = Path(tmp) / "parent"
            _write_activity(
                parent_root / "parent.pkg", activity_id="org.greia.parent-probe"
            )
            runtime = RuntimeCatalogue.default_safe()
            source = ActivitySource(
                parent_root,
                PackageTrust.PARENT_TRUSTED_UNSIGNED,
                "greia-parent-package-service",
            )
            index_path = Path(tmp) / "parent-index.json"
            _write_index(
                source_root=parent_root,
                source=source,
                runtime=runtime,
                dest=index_path,
            )
            parent_set = launcher_composition.ParentActiveSet(
                source=source, index_path=index_path
            )
            with _NoValidation(self):
                registrations = launcher_composition.load_parent_registrations(
                    parent_set, runtime
                )
            self.assertEqual(len(registrations), 1)
            registration = registrations[0]
            self.assertEqual(
                registration.manifest.activity_id, "org.greia.parent-probe"
            )
            self.assertEqual(
                registration.package_trust, PackageTrust.PARENT_TRUSTED_UNSIGNED
            )
            self.assertEqual(
                registration.source_id, "greia-parent-package-service"
            )

    def test_cross_source_id_collision_degrades_rejecting_ambiguous_group(self) -> None:
        # B04: the exception-only gate is replaced. A built-in × Parent
        # canonical collision has a single built-in claimant but is NOT the
        # authoritative built-in-wins pattern (other claimant is not
        # DEVELOPER_UNSIGNED), so every member of the ambiguous group is
        # rejected and boot continues degraded with the remainder.
        with tempfile.TemporaryDirectory() as tmp:
            builtin_root = Path(tmp) / "builtin"
            parent_root = Path(tmp) / "parent"
            _write_activity(
                builtin_root / "shared.pkg", activity_id="org.greia.shared"
            )
            _write_activity(
                parent_root / "shared.pkg", activity_id="org.greia.shared"
            )
            runtime = RuntimeCatalogue.default_safe()
            builtin_source = ActivitySource(
                builtin_root, PackageTrust.BUILT_IN, "greia-system"
            )
            index_path = Path(tmp) / "builtin-index.json"
            _write_index(
                source_root=builtin_root,
                source=builtin_source,
                runtime=runtime,
                dest=index_path,
            )
            marker = Path(tmp) / "no-marker"
            with mock.patch.dict(
                os.environ,
                {
                    launcher_main.DEVELOPER_MARKER_ENV_VAR: str(marker),
                    launcher_composition.BUILT_IN_INDEX_ENV_VAR: str(index_path),
                    launcher_composition.PARENT_ACTIVITY_ROOT_ENV_VAR: str(
                        parent_root
                    ),
                },
                clear=False,
            ):
                paths = self._paths(builtin_root, None)
                boot_sources = launcher_main.boot_activity_sources(paths)
                content = launcher_composition.compose_boot_content(
                    runtime, boot_sources
                )
                # Boot continues degraded; the ambiguous identity contributes
                # nothing to the catalogue.
                self.assertTrue(content.degraded)
                self.assertEqual([item.activity_id for item in content.activities], [])
                self.assertEqual(len(content.rejected), 2)
                identities = {item.identity for item in content.conflicts}
                self.assertEqual(identities, {"org.greia.shared"})
                # Neither ambiguous claimant is issuable.
                self.assertEqual(len(content.registry._issued), 0)
                self.assertEqual(content.registry.collision_degraded, True)

    def test_cross_source_alias_collision_degrades_rejecting_ambiguous_group(self) -> None:
        # B04: same degrade rule for the alias direction. A Parent package
        # can never carry legacy aliases itself, but its id shadowing a
        # built-in alias is ambiguous (not built-in × developer), so both
        # sides are rejected and boot continues degraded.
        with tempfile.TemporaryDirectory() as tmp:
            builtin_root = Path(tmp) / "builtin"
            parent_root = Path(tmp) / "parent"
            _write_activity(
                builtin_root / "renamed.pkg",
                activity_id="org.greia.renamed",
                legacy_ids=("org.greia.old",),
            )
            # A Parent package can never carry legacy aliases itself; its id
            # shadowing a built-in alias degrades (both sides rejected).
            _write_activity(
                parent_root / "old.pkg", activity_id="org.greia.old"
            )
            runtime = RuntimeCatalogue.default_safe()
            builtin_source = ActivitySource(
                builtin_root, PackageTrust.BUILT_IN, "greia-system"
            )
            index_path = Path(tmp) / "builtin-index.json"
            _write_index(
                source_root=builtin_root,
                source=builtin_source,
                runtime=runtime,
                dest=index_path,
            )
            marker = Path(tmp) / "no-marker"
            with mock.patch.dict(
                os.environ,
                {
                    launcher_main.DEVELOPER_MARKER_ENV_VAR: str(marker),
                    launcher_composition.BUILT_IN_INDEX_ENV_VAR: str(index_path),
                    launcher_composition.PARENT_ACTIVITY_ROOT_ENV_VAR: str(
                        parent_root
                    ),
                },
                clear=False,
            ):
                paths = self._paths(builtin_root, None)
                boot_sources = launcher_main.boot_activity_sources(paths)
                content = launcher_composition.compose_boot_content(
                    runtime, boot_sources
                )
                self.assertTrue(content.degraded)
                self.assertEqual([item.activity_id for item in content.activities], [])
                self.assertEqual(len(content.rejected), 2)
                identities = {item.identity for item in content.conflicts}
                self.assertEqual(identities, {"org.greia.old"})

    def test_activation_proof_reused_not_recomputed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            builtin_root = Path(tmp) / "builtin"
            parent_root = Path(tmp) / "parent-missing"
            self.assertFalse(parent_root.exists())
            _write_activity(
                builtin_root / "builtin.pkg", activity_id="org.greia.builtin-probe"
            )
            runtime = RuntimeCatalogue.default_safe()
            builtin_source = ActivitySource(
                builtin_root, PackageTrust.BUILT_IN, "greia-system"
            )
            index_path = Path(tmp) / "builtin-index.json"
            _write_index(
                source_root=builtin_root,
                source=builtin_source,
                runtime=runtime,
                dest=index_path,
            )
            expected_digest = build_index(
                ActivityRegistry(
                    (builtin_source,), runtime, fail_closed=False
                ).discover_registrations(),
                source=builtin_source,
                runtime=runtime,
            ).registrations[0].package_digest
            marker = Path(tmp) / "no-marker"
            with mock.patch.dict(
                os.environ,
                {
                    launcher_main.DEVELOPER_MARKER_ENV_VAR: str(marker),
                    launcher_composition.BUILT_IN_INDEX_ENV_VAR: str(index_path),
                    launcher_composition.PARENT_ACTIVITY_ROOT_ENV_VAR: str(
                        parent_root
                    ),
                },
                clear=False,
            ):
                paths = self._paths(builtin_root, None)
                boot_sources = launcher_main.boot_activity_sources(paths)
                with _NoValidation(self):
                    content = launcher_composition.compose_boot_content(
                        runtime, boot_sources
                    )
                    for manifest in content.activities:
                        registration = content.registry.registration_for(
                            manifest
                        )
                        # The validation-time digest recorded in the index is
                        # carried through, never recomputed at activation.
                        self.assertEqual(
                            registration.package_digest, expected_digest
                        )
                        self.assertEqual(
                            registration.source_id,
                            launcher_main.BUILT_IN_SOURCE_ID,
                        )


                        self.assertEqual(
                            registration.source_id,
                            launcher_main.BUILT_IN_SOURCE_ID,
                        )


class TrustAwareDegradeResolverTests(unittest.TestCase):
    """B04: one developer duplicate of a built-in ID never bricks the shell."""

    def _enable_developer(self, tmp: str) -> Path:
        marker = Path(tmp) / "developer-marker"
        marker.write_text("", encoding="utf-8")
        return marker

    def _compose(
        self,
        tmp: str,
        builtin_root: Path,
        dev_root: Path | None,
        index_path: Path,
        parent_root: Path,
        marker: Path,
        runtime: RuntimeCatalogue,
    ):  # type: ignore[no-untyped-def]
        with mock.patch.dict(
            os.environ,
            {
                launcher_main.DEVELOPER_MARKER_ENV_VAR: str(marker),
                launcher_composition.BUILT_IN_INDEX_ENV_VAR: str(index_path),
                launcher_composition.PARENT_ACTIVITY_ROOT_ENV_VAR: str(parent_root),
                "GREIA_DEVELOPER_ACTIVITY_ROOT": str(dev_root) if dev_root else "",
            },
            clear=False,
        ):
            paths = SimpleNamespace(
                activities=builtin_root,
                developer_activities=dev_root,
            )
            boot_sources = launcher_main.boot_activity_sources(paths)
            return launcher_composition.compose_boot_content(runtime, boot_sources)

    def test_builtin_developer_canonical_collision_builtin_wins(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            builtin_root = Path(tmp) / "builtin"
            dev_root = Path(tmp) / "dev"
            parent_root = Path(tmp) / "parent-missing"
            _write_activity(
                builtin_root / "baia.pkg", activity_id="org.greia.baia-delle-orche"
            )
            _write_activity(
                dev_root / "baia.pkg", activity_id="org.greia.baia-delle-orche"
            )
            _write_activity(
                dev_root / "other.pkg", activity_id="org.greia.dev-other"
            )
            runtime = RuntimeCatalogue.default_safe()
            builtin_source = ActivitySource(
                builtin_root, PackageTrust.BUILT_IN, "greia-system"
            )
            index_path = Path(tmp) / "builtin-index.json"
            _write_index(
                source_root=builtin_root,
                source=builtin_source,
                runtime=runtime,
                dest=index_path,
            )
            expected_digest = build_index(
                ActivityRegistry(
                    (builtin_source,), runtime, fail_closed=False
                ).discover_registrations(),
                source=builtin_source,
                runtime=runtime,
            ).registrations[0].package_digest
            marker = self._enable_developer(tmp)
            content = self._compose(
                tmp, builtin_root, dev_root, index_path, parent_root, marker, runtime
            )
            # Boot continues degraded with the built-in accepted.
            self.assertTrue(content.degraded)
            ids = [item.activity_id for item in content.activities]
            self.assertIn("org.greia.baia-delle-orche", ids)
            self.assertIn("org.greia.dev-other", ids)
            self.assertEqual(ids.count("org.greia.baia-delle-orche"), 1)
            # Built-in registration keeps built-in trust and index digest.
            builtin_manifest = next(
                item for item in content.activities
                if item.activity_id == "org.greia.baia-delle-orche"
            )
            builtin_reg = content.registry.registration_for(builtin_manifest)
            self.assertEqual(builtin_reg.package_trust, PackageTrust.BUILT_IN)
            self.assertEqual(builtin_reg.package_digest, expected_digest)
            self.assertEqual(builtin_reg.source_id, launcher_main.BUILT_IN_SOURCE_ID)
            # Every developer claimant rejected with structured evidence.
            self.assertEqual(len(content.rejected), 1)
            self.assertEqual(content.rejected[0].manifest.activity_id,
                             "org.greia.baia-delle-orche")
            self.assertEqual(content.rejected[0].package_trust,
                             PackageTrust.DEVELOPER_UNSIGNED)
            self.assertEqual(len(content.conflicts), 1)
            conflict = content.conflicts[0]
            self.assertEqual(conflict.identity, "org.greia.baia-delle-orche")
            self.assertEqual(conflict.activity_id, "org.greia.baia-delle-orche")
            self.assertEqual(conflict.source_id, "greia-developer-remote")
            self.assertEqual(conflict.package_trust, PackageTrust.DEVELOPER_UNSIGNED)
            self.assertTrue(str(conflict.package_root).endswith("baia.pkg"))
            self.assertTrue(len(conflict.package_digest) == 64)
            # Rejected registration is not issuable.
            with self.assertRaises(ActivityValidationError):
                content.registry.registration_for(content.rejected[0].manifest)

    def test_multiple_developer_duplicates_all_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            builtin_root = Path(tmp) / "builtin"
            dev_root = Path(tmp) / "dev"
            parent_root = Path(tmp) / "parent-missing"
            _write_activity(
                builtin_root / "baia.pkg", activity_id="org.greia.baia-delle-orche"
            )
            _write_activity(
                dev_root / "dup-a.pkg", activity_id="org.greia.baia-delle-orche"
            )
            _write_activity(
                dev_root / "dup-b.pkg", activity_id="org.greia.baia-delle-orche"
            )
            runtime = RuntimeCatalogue.default_safe()
            builtin_source = ActivitySource(
                builtin_root, PackageTrust.BUILT_IN, "greia-system"
            )
            index_path = Path(tmp) / "builtin-index.json"
            _write_index(
                source_root=builtin_root,
                source=builtin_source,
                runtime=runtime,
                dest=index_path,
            )
            marker = self._enable_developer(tmp)
            content = self._compose(
                tmp, builtin_root, dev_root, index_path, parent_root, marker, runtime
            )
            self.assertTrue(content.degraded)
            ids = [item.activity_id for item in content.activities]
            self.assertEqual(ids, ["org.greia.baia-delle-orche"])
            self.assertEqual(len(content.rejected), 2)
            self.assertEqual(len(content.conflicts), 2)
            for rejected in content.rejected:
                with self.assertRaises(ActivityValidationError):
                    content.registry.registration_for(rejected.manifest)

    def test_alias_collision_builtin_wins(self) -> None:
        # Developer canonical ID shadows a built-in legacy alias.
        with tempfile.TemporaryDirectory() as tmp:
            builtin_root = Path(tmp) / "builtin"
            dev_root = Path(tmp) / "dev"
            parent_root = Path(tmp) / "parent-missing"
            _write_activity(
                builtin_root / "renamed.pkg",
                activity_id="org.greia.renamed",
                legacy_ids=("org.greia.old",),
            )
            _write_activity(dev_root / "old.pkg", activity_id="org.greia.old")
            runtime = RuntimeCatalogue.default_safe()
            builtin_source = ActivitySource(
                builtin_root, PackageTrust.BUILT_IN, "greia-system"
            )
            index_path = Path(tmp) / "builtin-index.json"
            _write_index(
                source_root=builtin_root,
                source=builtin_source,
                runtime=runtime,
                dest=index_path,
            )
            marker = self._enable_developer(tmp)
            content = self._compose(
                tmp, builtin_root, dev_root, index_path, parent_root, marker, runtime
            )
            self.assertTrue(content.degraded)
            ids = [item.activity_id for item in content.activities]
            self.assertEqual(ids, ["org.greia.renamed"])
            self.assertEqual(len(content.rejected), 1)
            self.assertEqual(content.conflicts[0].identity, "org.greia.old")
            self.assertEqual(
                content.conflicts[0].package_trust, PackageTrust.DEVELOPER_UNSIGNED
            )
            with self.assertRaises(ActivityValidationError):
                content.registry.registration_for(content.rejected[0].manifest)

    def test_registration_order_cannot_reverse_decision(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            builtin_root = Path(tmp) / "builtin"
            dev_root = Path(tmp) / "dev"
            _write_activity(
                builtin_root / "baia.pkg", activity_id="org.greia.baia-delle-orche"
            )
            _write_activity(
                dev_root / "baia.pkg", activity_id="org.greia.baia-delle-orche"
            )
            runtime = RuntimeCatalogue.default_safe()
            builtin_source = ActivitySource(
                builtin_root, PackageTrust.BUILT_IN, "greia-system"
            )
            dev_source = ActivitySource(
                dev_root, PackageTrust.DEVELOPER_UNSIGNED, "greia-developer-remote"
            )
            builtin_regs = ActivityRegistry(
                (builtin_source,), runtime, fail_closed=False
            ).discover_registrations()
            dev_regs = ActivityRegistry(
                (dev_source,), runtime, fail_closed=False
            ).discover_registrations()
            forward = resolve_activity_collisions((*builtin_regs, *dev_regs))
            reverse = resolve_activity_collisions((*dev_regs, *builtin_regs))
            self.assertEqual(
                [item.manifest.activity_id for item in forward.accepted],
                [item.manifest.activity_id for item in reverse.accepted],
            )
            self.assertEqual(forward.accepted[0].package_trust, PackageTrust.BUILT_IN)
            self.assertEqual(reverse.accepted[0].package_trust, PackageTrust.BUILT_IN)
            self.assertEqual(
                {(item.identity, item.source_id) for item in forward.conflicts},
                {(item.identity, item.source_id) for item in reverse.conflicts},
            )
            # Registry-level order check: sources swapped, same outcome.
            first = ActivityRegistry(
                (builtin_source, dev_source), runtime, fail_closed=False
            ).discover_registrations()
            second = ActivityRegistry(
                (dev_source, builtin_source), runtime, fail_closed=False
            ).discover_registrations()
            self.assertEqual(
                [item.manifest.activity_id for item in first],
                [item.manifest.activity_id for item in second],
            )
            self.assertEqual(first[0].package_trust, PackageTrust.BUILT_IN)

    def test_ambiguous_group_without_builtin_rejects_all(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            dev_root = Path(tmp) / "dev"
            _write_activity(dev_root / "a.pkg", activity_id="org.greia.dupe")
            _write_activity(dev_root / "b.pkg", activity_id="org.greia.dupe")
            runtime = RuntimeCatalogue.default_safe()
            dev_source = ActivitySource(
                dev_root, PackageTrust.DEVELOPER_UNSIGNED, "greia-developer-remote"
            )
            registry = ActivityRegistry((dev_source,), runtime, fail_closed=False)
            accepted = registry.discover_registrations()
            # No single authoritative built-in claimant: boot with remainder.
            self.assertEqual(accepted, ())
            self.assertTrue(registry.collision_degraded)
            self.assertEqual(len(registry.rejected_registrations), 2)
            self.assertEqual(len(registry.collision_conflicts), 2)

    def test_developer_cannot_forge_trust_via_index(self) -> None:
        import json

        with tempfile.TemporaryDirectory() as tmp:
            builtin_root = Path(tmp) / "builtin"
            dev_root = Path(tmp) / "dev"
            _write_activity(
                builtin_root / "real.pkg", activity_id="org.greia.real-probe"
            )
            _write_activity(
                dev_root / "fake.pkg", activity_id="org.greia.fake-probe"
            )
            runtime = RuntimeCatalogue.default_safe()
            dev_source = ActivitySource(
                dev_root, PackageTrust.DEVELOPER_UNSIGNED, "greia-developer-remote"
            )
            dev_regs = ActivityRegistry(
                (dev_source,), runtime, fail_closed=False
            ).discover_registrations()
            dev_index_path = Path(tmp) / "dev-index.json"
            build_index(
                dev_regs, source=dev_source, runtime=runtime
            ).write_file(dev_index_path)
            # Loading developer index data through the built-in source is a
            # forged source/trust binding and must raise (never promote).
            from greia_platform.activity_index import ActivityIndexLoader

            builtin_source = ActivitySource(
                builtin_root, PackageTrust.BUILT_IN, "greia-system"
            )
            with self.assertRaises(ActivityIndexError):
                ActivityIndexLoader.from_runtime(
                    builtin_source, runtime
                ).load_file(dev_index_path)
            # Tampering the stored trust field is also rejected.
            raw = json.loads(dev_index_path.read_text(encoding="utf-8"))
            raw["package_trust"] = "built_in"
            tampered = Path(tmp) / "tampered-index.json"
            tampered.write_text(json.dumps(raw), encoding="utf-8")
            with self.assertRaises(ActivityIndexError):
                ActivityIndexLoader.from_runtime(dev_source, runtime).load_file(
                    tampered
                )
            # Developer packages cannot carry legacy aliases at validation.
            alias_root = dev_root / "alias.pkg"
            _write_activity(
                alias_root, activity_id="org.greia.alias-probe",
                legacy_ids=("org.greia.alias-old",),
            )
            dev_registry = ActivityRegistry((dev_source,), runtime, fail_closed=False)
            accepted = dev_registry.discover_registrations()
            self.assertNotIn(
                "org.greia.alias-probe",
                [item.manifest.activity_id for item in accepted],
            )

    def test_cold_boot_and_rescan_agree(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            builtin_root = Path(tmp) / "builtin"
            dev_root = Path(tmp) / "dev"
            parent_root = Path(tmp) / "parent-missing"
            _write_activity(
                builtin_root / "baia.pkg", activity_id="org.greia.baia-delle-orche"
            )
            _write_activity(
                dev_root / "baia.pkg", activity_id="org.greia.baia-delle-orche"
            )
            _write_activity(dev_root / "other.pkg", activity_id="org.greia.dev-other")
            runtime = RuntimeCatalogue.default_safe()
            builtin_source = ActivitySource(
                builtin_root, PackageTrust.BUILT_IN, "greia-system"
            )
            index_path = Path(tmp) / "builtin-index.json"
            _write_index(
                source_root=builtin_root,
                source=builtin_source,
                runtime=runtime,
                dest=index_path,
            )
            marker = self._enable_developer(tmp)
            content = self._compose(
                tmp, builtin_root, dev_root, index_path, parent_root, marker, runtime
            )
            cold_ids = sorted(item.activity_id for item in content.activities)
            cold_conflicts = sorted(
                (item.identity, item.activity_id, item.source_id)
                for item in content.conflicts
            )
            # Later rescan through the real registry (live validation path).
            rescanned = content.registry.discover_registrations()
            rescan_ids = sorted(item.manifest.activity_id for item in rescanned)
            rescan_conflicts = sorted(
                (item.identity, item.activity_id, item.source_id)
                for item in content.registry.collision_conflicts
            )
            self.assertEqual(cold_ids, rescan_ids)
            self.assertEqual(cold_conflicts, rescan_conflicts)
            # Seeded evidence matches the cold-boot resolution.
            self.assertEqual(
                sorted(item.manifest.activity_id for item in content.rejected),
                sorted(
                    item.manifest.activity_id
                    for item in content.registry.rejected_registrations
                ),
            )

    def test_builtin_index_corruption_still_controlled_failure(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            builtin_root = Path(tmp) / "builtin"
            parent_root = Path(tmp) / "parent-missing"
            _write_activity(
                builtin_root / "real.pkg", activity_id="org.greia.real-probe"
            )
            runtime = RuntimeCatalogue.default_safe()
            index_path = Path(tmp) / "builtin-index.json"
            index_path.write_text("{ not valid json", encoding="utf-8")
            marker = Path(tmp) / "no-marker"
            with mock.patch.dict(
                os.environ,
                {
                    launcher_main.DEVELOPER_MARKER_ENV_VAR: str(marker),
                    launcher_composition.BUILT_IN_INDEX_ENV_VAR: str(index_path),
                    launcher_composition.PARENT_ACTIVITY_ROOT_ENV_VAR: str(
                        parent_root
                    ),
                },
                clear=False,
            ):
                paths = SimpleNamespace(
                    activities=builtin_root, developer_activities=None
                )
                boot_sources = launcher_main.boot_activity_sources(paths)
                with self.assertRaises(ActivityIndexError):
                    launcher_composition.compose_boot_content(runtime, boot_sources)

    def test_developer_source_never_promoted(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            dev_root = Path(tmp) / "dev"
            dev_root.mkdir(parents=True)
            marker = self._enable_developer(tmp)
            with mock.patch.dict(
                os.environ,
                {launcher_main.DEVELOPER_MARKER_ENV_VAR: str(marker)},
                clear=False,
            ):
                source = launcher_main.developer_activity_source(dev_root)
                assert source is not None
                self.assertEqual(source.trust, PackageTrust.DEVELOPER_UNSIGNED)
                self.assertEqual(source.source_id, "greia-developer-remote")


class BootSingleConstructionTests(unittest.TestCase):
    """The composed boot path builds runtime/catalogue exactly once."""

    @classmethod
    def setUpClass(cls) -> None:
        os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
        try:
            import pygame

            pygame.init()
        except Exception:
            pass

    @classmethod
    def tearDownClass(cls) -> None:
        try:
            import pygame

            pygame.quit()
        except Exception:
            pass

    def test_presentation_boot_has_no_second_pass(self) -> None:
        from greia_launcher.presentation import GreiaLauncherPresentation

        repo_root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            dev_root = tmp_path / "dev"
            _write_activity(
                dev_root / "dev.pkg", activity_id="org.greia.dev-probe"
            )
            parent_root = tmp_path / "parent"
            parent_root.mkdir(parents=True)
            missing_marker = tmp_path / "no-marker"
            missing_index = tmp_path / "no-index.json"
            self.assertFalse(missing_marker.exists())
            env = {
                "GREIA_OS_ROOT": str(repo_root),
                "GREIA_PROFILES_DIR": str(tmp_path / "profiles"),
                "GREIA_SYSTEM_SETTINGS_DIR": str(tmp_path / "settings"),
                "GREIA_MEDIA_ROOT": str(tmp_path / "media"),
                "GREIA_ACTIVE_PROFILE_STATUS": str(tmp_path / "active.json"),
                "GREIA_HARDWARE_STATUS": str(tmp_path / "hw.json"),
                "GREIA_MAIN_CREDENTIAL_PATH": str(tmp_path / "cred.json"),
                "GREIA_DEVELOPER_ACTIVITY_ROOT": str(dev_root),
                launcher_main.DEVELOPER_MARKER_ENV_VAR: str(missing_marker),
                launcher_composition.BUILT_IN_INDEX_ENV_VAR: str(missing_index),
                launcher_composition.PARENT_ACTIVITY_ROOT_ENV_VAR: str(
                    parent_root
                ),
                "SDL_VIDEODRIVER": "dummy",
            }
            runtime_builds: list[str] = []
            dev_scans: list[str] = []
            real_glob = Path.glob

            def _spy_glob(
                self: Path, pattern: str, *args: object, **kwargs: object
            ):  # type: ignore[no-untyped-def]
                if pattern == "*/activity.toml":
                    dev_scans.append(self.resolve().as_posix())
                return real_glob(self, pattern, *args, **kwargs)  # type: ignore[arg-type]

            with mock.patch.dict(os.environ, env, clear=False):
                import greia_launcher.main as main_module
                import greia_launcher.presentation as presentation_module
                from greia_platform.activities import RuntimeCatalogue as _RC

                real_main_build = main_module.build_launcher_runtime_services
                real_from_activities = (
                    presentation_module.ActivityCatalogue.from_activities
                )

                def _counting_main_build(*args: object, **kwargs: object):  # type: ignore[no-untyped-def]
                    runtime_builds.append("main")
                    return real_main_build(*args, **kwargs)  # type: ignore[arg-type]

                catalogue_builds: list[str] = []

                def _counting_catalogue(*args: object, **kwargs: object):  # type: ignore[no-untyped-def]
                    catalogue_builds.append("catalogue")
                    return real_from_activities(*args, **kwargs)  # type: ignore[arg-type]

                with (
                    mock.patch.object(
                        Path, "glob", _spy_glob
                    ),
                    mock.patch.object(
                        main_module,
                        "build_launcher_runtime_services",
                        _counting_main_build,
                    ),
                    mock.patch.object(
                        presentation_module.ActivityCatalogue,
                        "from_activities",
                        _counting_catalogue,
                    ),
                    mock.patch.object(
                        GreiaLauncherPresentation,
                        "_configure_parent_package_source",
                    ) as configure_spy,
                ):
                    launcher = GreiaLauncherPresentation(
                        windowed=True, allow_exit=True
                    )
            # Exactly one runtime/catalogue construction on the composed path
            # and no second-pass per-source rebuild.
            self.assertEqual(runtime_builds, ["main"])
            self.assertEqual(catalogue_builds, ["catalogue"])
            self.assertEqual(configure_spy.call_count, 0)
            # The Parent source is part of the single composed set, not added
            # later by a second registry.
            source_ids = [source.source_id for source in launcher.registry._sources]
            self.assertIn("greia-parent-package-service", source_ids)
            self.assertIn(launcher_main.BUILT_IN_SOURCE_ID, source_ids)
            # Developer mode off: the configured dev root is excluded and its
            # tree is never scanned by the composed boot.
            ids = {item.activity_id for item in launcher._activities}
            self.assertNotIn("org.greia.dev-probe", ids)
            dev_prefix = dev_root.resolve().as_posix()
            self.assertFalse(
                any(
                    entry == dev_prefix or entry.startswith(dev_prefix + "/")
                    for entry in dev_scans
                ),
                f"composed boot scanned developer root: {dev_scans}",
            )
            self.assertNotIn(dev_prefix, repr(launcher.registry.discovery_token()))
            self.assertTrue(len(ids) > 0)


if __name__ == "__main__":
    raise SystemExit(unittest.main())
