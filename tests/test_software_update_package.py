from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

from greia_platform.software_update_package import (
    MAX_SOFTWARE_UPDATE_BYTES,
    SOFTWARE_UPDATE_EXTENSION,
    SOFTWARE_UPDATE_MEDIA_TYPE,
    ActivityPackageInput,
    ActivityPackageSource,
    ActivityUpdateScope,
    REQUIRED_PYTHON_ENTRYPOINTS,
    SoftwareUpdateActivity,
    SoftwareUpdateMember,
    SoftwareUpdatePackageError,
    SoftwareUpdatePackageManifest,
    SoftwareUpdateTarget,
    SoftwareUpdateType,
    build_software_update_package,
    ensure_software_update_filename,
    inspect_software_update_package,
    validate_language_resource_tree,
)
from greia_platform.system_updates import (
    MAX_BUNDLE_BYTES,
    build_update_bundle,
)


def _python_root(root: Path) -> Path:
    for family in ("greia_platform", "greia_launcher", "greia_parent", "greia_installer"):
        package = root / "src" / family
        package.mkdir(parents=True)
        (package / "__init__.py").write_text("\n", encoding="utf-8")
    for relative in REQUIRED_PYTHON_ENTRYPOINTS:
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("# required production entrypoint\n", encoding="utf-8")
    for runtime_path in (
        "achievement-policy.toml",
        "activity-launch.toml",
        "alsa/greia-activity-capture.conf",
        "alsa/greia-activity-overrides.conf",
        "audio-settings.toml",
        "child-runtime.toml",
        "hardware-settings.toml",
        "history-policy.toml",
        "permission-policy.toml",
        "profile-defaults.toml",
        "progression-policy.toml",
        "storage-policy.toml",
        "theme-defaults.toml",
    ):
        path = root / "runtime" / runtime_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("# runtime policy\n", encoding="utf-8")
    (root / "runtime" / "parent-app-client.toml").write_text("pinned", encoding="utf-8")
    (root / "runtime" / "parent-app-client.manifest.json").write_text("{}", encoding="utf-8")
    (root / "src" / "greia_simulator").mkdir()
    (root / "src" / "greia_simulator" / "not-in-image.py").write_text("x = 1\n", encoding="utf-8")
    (root / "src" / "greia_platform" / "native.c").write_text("int x;\n", encoding="utf-8")
    (root / "src" / "greia_platform" / "update_logic.py").write_text("VALUE = 7\n", encoding="utf-8")
    (root / "src" / "greia_platform" / "empty.py").write_bytes(b"")
    language = root / "src" / "greia_platform" / "languages" / "en"
    language.mkdir(parents=True)
    (language / "manifest.json").write_text(
        json.dumps({"schema_version": 1, "locale": "en", "name": "English", "native_name": "English", "flag": "🇬🇧", "order": 0}),
        encoding="utf-8",
    )
    (language / "ui.json").write_text(json.dumps({"schema_version": 1, "example": {"hello": "Hello {name}"}}), encoding="utf-8")
    scaffold = root / "src" / "greia_platform" / "languages" / "de"
    scaffold.mkdir(parents=True)
    (scaffold / "ui.json").write_text(json.dumps({"schema_version": 1, "draft": {"title": "Nicht angeboten"}}), encoding="utf-8")
    return root


def _activity_archive(root: Path, activity_id: str, version: str = "1.2.3") -> Path:
    archive_path = root / f"{activity_id}.greiaactivity"
    manifest = f'''[activity]
id = "{activity_id}"
title_key = "activity.test.title"
version = "{version}"
icon = "test-icon"
languages = ["en"]

[education]
categories = ["learn"]
difficulty = 1
skills = [{{ id = "learning.test", weight = 1 }}]
events = []

[runtime]
type = "python"
api_version = "0.1"
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
'''
    with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("activity.toml", manifest)
        archive.writestr("main.py", "from __future__ import annotations\n\ndef main():\n    return None\n")
    return archive_path


def _write_typed_package(
    path: Path,
    manifest: SoftwareUpdatePackageManifest,
    payloads: dict[str, bytes],
) -> None:
    with zipfile.ZipFile(path, "w", allowZip64=True) as archive:
        archive.writestr("manifest.json", manifest.canonical_bytes(), compress_type=zipfile.ZIP_DEFLATED)
        for member, payload in sorted(payloads.items()):
            compression = zipfile.ZIP_STORED if member.startswith("activities/") or member.startswith("full_system/") else zipfile.ZIP_DEFLATED
            archive.writestr(member, payload, compress_type=compression)


def _v3_bundle(root: Path) -> Path:
    payload = root / "payload.ext4.zst"
    payload.write_bytes(b"\x28\xb5\x2f\xfd" + b"small-slot-data" * 32)
    output = root / "greia-0.14.0-test.greiaupdate"
    build_update_bundle(
        payload_path=payload,
        hardware_support_path=None,
        output_path=output,
        version="0.14.0",
        release_id="greia-0.14.0-test",
        platform_family="legacy-x86",
        architecture="i386",
        profile="legacy-x86-i686",
        payload_uncompressed_bytes=4096,
        minimum_slot_bytes=4096,
        persist_read_schema_min=1,
        persist_read_schema_max=1,
        persist_write_schema=1,
    )
    return output


class SoftwareUpdatePackageFormatTests(unittest.TestCase):
    def test_distribution_identity_and_extension(self) -> None:
        self.assertEqual(SOFTWARE_UPDATE_EXTENSION, ".greia_update")
        self.assertEqual(SOFTWARE_UPDATE_MEDIA_TYPE, "application/vnd.greia.software-update+zip")
        self.assertEqual(MAX_SOFTWARE_UPDATE_BYTES, MAX_BUNDLE_BYTES + 1024 * 1024)
        self.assertEqual(ensure_software_update_filename("release.zip"), Path("release.greia_update"))

    def test_python_platform_build_is_complete_allowlisted_snapshot_and_deterministic(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = _python_root(Path(directory) / "project")
            first = build_software_update_package(
                root / "out" / "first.zip",
                version="1.4.0",
                release_id="greia-app-1.4.0",
                python_source_root=root,
            )
            first_path = root / "out" / "first.greia_update"
            second = build_software_update_package(
                root / "out" / "second.greia_update",
                version="1.4.0",
                release_id="greia-app-1.4.0",
                python_source_root=root,
            )
            second_path = root / "out" / "second.greia_update"
            self.assertEqual(first, second)
            self.assertEqual(
                hashlib.sha256(first_path.read_bytes()).hexdigest(),
                hashlib.sha256(second_path.read_bytes()).hexdigest(),
            )
            inspected = inspect_software_update_package(first_path)
            paths = {item.path for item in inspected.manifest.python_files}
            self.assertIn("src/greia_platform/update_logic.py", paths)
            self.assertIn("src/greia_platform/languages/en/manifest.json", paths)
            self.assertIn("src/greia_platform/languages/en/ui.json", paths)
            self.assertNotIn("src/greia_platform/languages/de/ui.json", paths)
            self.assertIn("runtime/child-runtime.toml", paths)
            self.assertNotIn("runtime/parent-app-client.toml", paths)
            self.assertNotIn("runtime/parent-app-client.manifest.json", paths)
            self.assertNotIn("src/greia_platform/native.c", paths)
            self.assertNotIn("src/greia_simulator/not-in-image.py", paths)
            empty_file = next(item for item in inspected.manifest.python_files if item.path.endswith("/empty.py"))
            self.assertEqual(empty_file.size, 0)
            self.assertEqual(empty_file.sha256, hashlib.sha256(b"").hexdigest())
            self.assertEqual(inspected.manifest.type, SoftwareUpdateType.PYTHON_PLATFORM)
            self.assertEqual(inspected.manifest.targets, ())
            self.assertTrue(inspected.manifest.matches_identity({"architecture": "i386"}))
            self.assertGreater(inspected.package_size, 0)
            with self.assertRaisesRegex(SoftwareUpdatePackageError, "already exists"):
                build_software_update_package(
                    first_path,
                    version="1.4.0",
                    release_id="greia-app-1.4.0",
                    python_source_root=root,
                )

    def test_inspector_rejects_arbitrary_json_and_malformed_language_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = _python_root(Path(directory) / "project")
            package = root / "good.greia_update"
            build_software_update_package(package, version="1.4.0", release_id="greia-app-1.4.0", python_source_root=root)
            with zipfile.ZipFile(package) as archive:
                manifest = json.loads(archive.read("manifest.json"))
                payloads = {name: archive.read(name) for name in archive.namelist()[1:]}
            files = manifest["python_platform"]["files"]
            record = next(item for item in files if item["path"].endswith("/languages/en/manifest.json"))
            payloads[record["member"]] = json.dumps({"schema_version": 1, "locale": "it", "name": "English", "native_name": "English", "flag": "x"}).encode()
            record["size"] = len(payloads[record["member"]])
            record["sha256"] = hashlib.sha256(payloads[record["member"]]).hexdigest()
            bad = root / "bad.greia_update"
            _write_raw_package(bad, manifest, payloads)
            with self.assertRaisesRegex(SoftwareUpdatePackageError, "locale must match"):
                inspect_software_update_package(bad)

            files[0]["path"] = "src/greia_platform/anything.json"
            _write_raw_package(bad, manifest, payloads)
            with self.assertRaisesRegex(SoftwareUpdatePackageError, "allowlist"):
                inspect_software_update_package(bad)

    def test_inspector_rejects_mismatched_language_placeholders(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = _python_root(Path(directory) / "project")
            package = root / "good.greia_update"
            build_software_update_package(package, version="1.4.0", release_id="greia-app-1.4.0", python_source_root=root)
            with zipfile.ZipFile(package) as archive:
                manifest = json.loads(archive.read("manifest.json"))
                payloads = {name: archive.read(name) for name in archive.namelist()[1:]}
            record = next(item for item in manifest["python_platform"]["files"] if item["path"].endswith("/languages/en/ui.json"))
            payloads[record["member"]] = json.dumps({"schema_version": 1, "example": {"hello": "Hello"}}).encode()
            record["size"] = len(payloads[record["member"]])
            record["sha256"] = hashlib.sha256(payloads[record["member"]]).hexdigest()
            bad = root / "bad.greia_update"
            _write_raw_package(bad, manifest, payloads)
            # English reference is within this same package; use a sibling locale to
            # exercise the checker that guards translated placeholder contracts.
            files = manifest["python_platform"]["files"]
            translated_manifest = {"schema_version": 1, "locale": "it", "name": "Italian", "native_name": "Italiano", "flag": "🇮🇹"}
            translated_ui = {"schema_version": 1, "example": {"hello": "Ciao {other}"}}
            for filename, value in (("manifest.json", translated_manifest), ("ui.json", translated_ui)):
                path = f"src/greia_platform/languages/it/{filename}"
                member = f"python/{path}"
                content = json.dumps(value).encode()
                files.append({"path": path, "member": member, "size": len(content), "sha256": hashlib.sha256(content).hexdigest()})
                payloads[member] = content
            _write_raw_package(bad, manifest, payloads)
            with self.assertRaisesRegex(SoftwareUpdatePackageError, "placeholder mismatch"):
                inspect_software_update_package(bad)

    def test_language_tree_rejects_more_than_runtime_locale_limit(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            locales = [f"{first}{second}" for first in "abcdefghijklmnopqrstuvwxyz" for second in "abcdefghijklmnopqrstuvwxyz"]
            for index, locale in enumerate(["en", *[item for item in locales if item != "en"][:32]]):
                folder = root / locale
                folder.mkdir()
                (folder / "manifest.json").write_text(
                    json.dumps({"schema_version": 1, "locale": locale, "name": locale, "native_name": locale, "flag": "x", "order": index}),
                    encoding="utf-8",
                )
                (folder / "ui.json").write_text(json.dumps({"schema_version": 1, "example": {"hello": "Hello {name}"}}), encoding="utf-8")
            with self.assertRaisesRegex(SoftwareUpdatePackageError, "runtime limit"):
                validate_language_resource_tree(root)

    def test_language_tree_rejects_invalid_english_format_string(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = _python_root(Path(directory) / "project") / "src/greia_platform/languages"
            ui = json.loads((root / "en/ui.json").read_text("utf-8"))
            ui["example"]["hello"] = "Unclosed {name"
            (root / "en/ui.json").write_text(json.dumps(ui), encoding="utf-8")
            with self.assertRaisesRegex(SoftwareUpdatePackageError, "invalid format string"):
                validate_language_resource_tree(root)

    def test_python_targets_match_exactly_and_default_is_portable(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = _python_root(Path(directory) / "project")
            package = root / "targeted.greia_update"
            build_software_update_package(
                package,
                version="1.4.0",
                release_id="greia-app-1.4.0",
                python_source_root=root,
                targets=(SoftwareUpdateTarget(platform_family="legacy-x86", architecture="i386"),),
            )
            manifest = inspect_software_update_package(package).manifest
            self.assertTrue(manifest.matches_identity({"platform_family": "legacy-x86", "architecture": "i386"}))
            self.assertFalse(manifest.matches_identity({"platform_family": "arm", "architecture": "arm64"}))

    def test_activity_package_reuses_existing_zip_and_binds_id_version_hash(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            activity = _activity_archive(root, "org.greia.painting", "2.0.0")
            package = root / "activities.greia_update"
            build_software_update_package(
                package,
                version="1.4.0",
                release_id="greia-app-1.4.0",
                activity_packages=(ActivityPackageInput("org.greia.painting", activity),),
                activity_scope=ActivityUpdateScope.ONE,
                activity_source=ActivityPackageSource.BUILT_IN,
            )
            inspected = inspect_software_update_package(package)
            item = inspected.manifest.activity_items[0]
            self.assertEqual(item.version, "2.0.0")
            self.assertEqual(item.size, activity.stat().st_size)
            self.assertEqual(item.sha256, hashlib.sha256(activity.read_bytes()).hexdigest())
            self.assertEqual(item.member, "activities/org.greia.painting.greiaactivity")
            with zipfile.ZipFile(package) as archive:
                self.assertEqual(archive.getinfo(item.member).compress_type, zipfile.ZIP_STORED)

    def test_prebuilt_activity_archive_runs_full_runtime_validation_before_output(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            valid = _activity_archive(root, "org.greia.painting")
            invalid = root / "invalid.greiaactivity"
            with zipfile.ZipFile(valid) as source, zipfile.ZipFile(invalid, "w") as target:
                target.writestr("activity.toml", source.read("activity.toml"))
                target.writestr(
                    "main.py",
                    "import subprocess\n\ndef main():\n    return None\n",
                )
            output = root / "invalid.greia_update"
            with self.assertRaisesRegex(SoftwareUpdatePackageError, "subprocess|import"):
                build_software_update_package(
                    output,
                    version="1.4.0",
                    release_id="greia-app-1.4.0",
                    activity_packages=(ActivityPackageInput("org.greia.painting", invalid),),
                    activity_scope=ActivityUpdateScope.ONE,
                    activity_source=ActivityPackageSource.BUILT_IN,
                )
            self.assertFalse(output.exists())

    def test_declared_activity_source_controls_legacy_alias_validation(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            archive_path = _activity_archive(root, "org.greia.painting")
            with zipfile.ZipFile(archive_path) as source:
                manifest = source.read("activity.toml").decode("utf-8")
                main = source.read("main.py")
            archive_path.unlink()
            with zipfile.ZipFile(archive_path, "w") as target:
                target.writestr(
                    "activity.toml",
                    manifest.replace('id = "org.greia.painting"', 'id = "org.greia.painting"\nlegacy_ids = ["legacy.painting"]'),
                )
                target.writestr("main.py", main)
            builtin = root / "builtin.greia_update"
            build_software_update_package(
                builtin,
                version="1.4.0",
                release_id="greia-app-1.4.0",
                activity_packages=(ActivityPackageInput("org.greia.painting", archive_path),),
                activity_scope=ActivityUpdateScope.ONE,
                activity_source=ActivityPackageSource.BUILT_IN,
            )
            parent = root / "parent.greia_update"
            with self.assertRaisesRegex(SoftwareUpdatePackageError, "legacy Activity aliases"):
                build_software_update_package(
                    parent,
                    version="1.4.0",
                    release_id="greia-app-1.4.0",
                    activity_packages=(ActivityPackageInput("org.greia.painting", archive_path),),
                    activity_scope=ActivityUpdateScope.ONE,
                    activity_source=ActivityPackageSource.PARENT,
                )
            self.assertFalse(parent.exists())

    def test_inspector_rejects_runtime_invalid_nested_activity_archive(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            archive_path = _activity_archive(root, "org.greia.painting")
            with zipfile.ZipFile(archive_path) as source:
                manifest_text = source.read("activity.toml").decode("utf-8")
            bad_activity = root / "bad.greiaactivity"
            with zipfile.ZipFile(bad_activity, "w") as target:
                target.writestr("activity.toml", manifest_text)
                target.writestr("main.py", "import subprocess\n")
            payload = bad_activity.read_bytes()
            manifest = SoftwareUpdatePackageManifest(
                type=SoftwareUpdateType.ACTIVITIES,
                version="1.4.0",
                release_id="greia-app-1.4.0",
                activity_scope=ActivityUpdateScope.ONE,
                activity_source=ActivityPackageSource.BUILT_IN,
                activity_items=(SoftwareUpdateActivity(
                    "org.greia.painting",
                    "1.2.3",
                    "activities/org.greia.painting.greiaactivity",
                    len(payload),
                    hashlib.sha256(payload).hexdigest(),
                ),),
            )
            package = root / "bad-inner.greia_update"
            _write_typed_package(package, manifest, {
                "activities/org.greia.painting.greiaactivity": payload,
            })
            with self.assertRaisesRegex(SoftwareUpdatePackageError, "subprocess|import"):
                inspect_software_update_package(package)

    def test_all_scope_requires_exact_installed_built_in_id_set(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            first = _activity_archive(root, "org.greia.painting")
            second = _activity_archive(root, "org.greia.writing")
            items = (
                ActivityPackageInput("org.greia.painting", first),
                ActivityPackageInput("org.greia.writing", second),
            )
            with self.assertRaisesRegex(SoftwareUpdatePackageError, "installed approved built-in Activity index"):
                build_software_update_package(
                    root / "bad.greia_update",
                    version="1.4.0",
                    release_id="greia-app-1.4.0",
                    activity_packages=items,
                    activity_scope=ActivityUpdateScope.ALL,
                    activity_source=ActivityPackageSource.BUILT_IN,
                    approved_activity_ids=frozenset({"org.greia.painting"}),
                )
            build_software_update_package(
                root / "all.greia_update",
                version="1.4.0",
                release_id="greia-app-1.4.0",
                activity_packages=items,
                activity_scope=ActivityUpdateScope.ALL,
                activity_source=ActivityPackageSource.BUILT_IN,
                approved_activity_ids=frozenset({"org.greia.painting", "org.greia.writing"}),
            )

    def test_combined_package_is_one_typed_snapshot_and_parent_source_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = _python_root(Path(directory) / "project")
            activity = _activity_archive(root, "org.greia.painting")
            package = root / "combined.greia_update"
            build_software_update_package(
                package,
                version="1.4.0",
                release_id="greia-app-1.4.0",
                python_source_root=root,
                activity_packages=(ActivityPackageInput("org.greia.painting", activity),),
                activity_scope=ActivityUpdateScope.ONE,
                activity_source=ActivityPackageSource.BUILT_IN,
            )
            inspected = inspect_software_update_package(package)
            self.assertEqual(inspected.manifest.type, SoftwareUpdateType.COMBINED)
            self.assertGreater(len(inspected.manifest.python_files), 0)
            self.assertEqual(len(inspected.manifest.activity_items), 1)
            with zipfile.ZipFile(package) as archive:
                manifest = json.loads(archive.read("manifest.json"))
                self.assertIn("python/src/greia_platform/languages/en/manifest.json", archive.namelist())
                self.assertIn("python/src/greia_platform/languages/en/ui.json", archive.namelist())
            self.assertEqual(set(manifest), {"schema_version", "type", "version", "release_id", "targets", "python_platform", "activities"})
            manifest["activities"]["source"] = "parent"
            with self.assertRaisesRegex(SoftwareUpdatePackageError, "combined packages may only update built-in"):
                SoftwareUpdatePackageManifest.from_json_dict(manifest)

    def test_full_system_wrapper_reuses_v3_and_inner_identity(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            inner = _v3_bundle(root)
            outer = root / "outer.greia_update"
            build_software_update_package(outer, full_system_bundle=inner)
            inspected = inspect_software_update_package(outer)
            self.assertEqual(inspected.manifest.type, SoftwareUpdateType.FULL_SYSTEM)
            self.assertEqual(inspected.manifest.version, "0.14.0")
            self.assertEqual(inspected.manifest.release_id, "greia-0.14.0-test")
            self.assertEqual(inspected.manifest.full_system.member, "full_system/bundle.greiaupdate")
            self.assertEqual(inspected.manifest.targets, ())

    def test_full_system_wrapper_revalidates_inner_payload_digest(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            original = _v3_bundle(root)
            from greia_platform.system_updates import inspect_update_bundle

            original_manifest = inspect_update_bundle(original).manifest
            with zipfile.ZipFile(original) as source:
                payload = bytearray(source.read("payload.ext4.zst"))
            payload[-1] ^= 0x01
            corrupted_inner = root / "corrupted.greiaupdate"
            with zipfile.ZipFile(corrupted_inner, "w", allowZip64=True) as target:
                with zipfile.ZipFile(original) as source:
                    target.writestr("manifest.json", source.read("manifest.json"), compress_type=zipfile.ZIP_STORED)
                target.writestr("payload.ext4.zst", bytes(payload), compress_type=zipfile.ZIP_STORED)
            inner_bytes = corrupted_inner.read_bytes()
            member = SoftwareUpdateMember(
                "full_system/bundle.greiaupdate",
                len(inner_bytes),
                hashlib.sha256(inner_bytes).hexdigest(),
            )
            manifest = SoftwareUpdatePackageManifest(
                type=SoftwareUpdateType.FULL_SYSTEM,
                version=original_manifest.version,
                release_id=original_manifest.release_id,
                full_system=member,
            )
            package = root / "corrupted-wrapper.greia_update"
            _write_typed_package(package, manifest, {member.member: inner_bytes})
            with self.assertRaisesRegex(SoftwareUpdatePackageError, "digest"):
                inspect_software_update_package(package)

    def test_invalid_type_fields_path_digest_and_truncated_zip_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = _python_root(Path(directory) / "project")
            good = root / "good.greia_update"
            build_software_update_package(
                good,
                version="1.4.0",
                release_id="greia-app-1.4.0",
                python_source_root=root,
            )
            with zipfile.ZipFile(good) as archive:
                manifest = json.loads(archive.read("manifest.json"))
                member_names = [item.filename for item in archive.infolist()[1:]]
                payloads = {name: archive.read(name) for name in member_names}
            manifest["type"] = "full_system"
            bad = root / "bad.greia_update"
            _write_raw_package(bad, manifest, payloads)
            with self.assertRaisesRegex(SoftwareUpdatePackageError, "fields do not match"):
                inspect_software_update_package(bad)

            manifest["type"] = "python_platform"
            manifest["python_platform"]["files"][0]["path"] = "src/greia_platform/../../etc/passwd.py"
            _write_raw_package(bad, manifest, payloads)
            with self.assertRaisesRegex(SoftwareUpdatePackageError, "escapes"):
                inspect_software_update_package(bad)

            with zipfile.ZipFile(good) as archive:
                manifest = json.loads(archive.read("manifest.json"))
            manifest["python_platform"]["files"][0]["sha256"] = "0" * 64
            _write_raw_package(bad, manifest, payloads)
            with self.assertRaisesRegex(SoftwareUpdatePackageError, "SHA-256"):
                inspect_software_update_package(bad)

            truncated = root / "truncated.greia_update"
            truncated.write_bytes(b"PK\x03\x04truncated")
            with self.assertRaises(SoftwareUpdatePackageError):
                inspect_software_update_package(truncated)

    def test_full_system_builder_rejects_outer_identity_override(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            inner = _v3_bundle(root)
            with self.assertRaisesRegex(SoftwareUpdatePackageError, "outer version must match"):
                build_software_update_package(
                    root / "wrong.greia_update", full_system_bundle=inner, version="999.0"
                )

    def test_python_tree_walk_error_fails_closed_and_required_entrypoints_are_checked(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = _python_root(Path(directory) / "project")
            missing = root / "src/greia_platform/software_update_apply.py"
            missing.unlink()
            output = root / "missing.greia_update"
            with self.assertRaisesRegex(SoftwareUpdatePackageError, "required production entrypoints"):
                build_software_update_package(
                    output,
                    version="1.4.0",
                    release_id="greia-app-1.4.0",
                    python_source_root=root,
                )
            missing.write_text("pass\n", encoding="utf-8")

            def fail_walk(_root, *, followlinks, onerror):
                onerror(PermissionError("traversal denied"))
                return iter(())

            with patch("greia_platform.software_update_package_builder.os.walk", side_effect=fail_walk):
                with self.assertRaisesRegex(SoftwareUpdatePackageError, "traverse Python source tree"):
                    build_software_update_package(
                        output,
                        version="1.4.0",
                        release_id="greia-app-1.4.0",
                        python_source_root=root,
                    )
            self.assertFalse(output.exists())


def _write_raw_package(path: Path, manifest: dict[str, object], payloads: dict[str, bytes]) -> None:
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(
            "manifest.json",
            json.dumps(manifest, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode(),
        )
        for name, payload in sorted(payloads.items()):
            archive.writestr(name, payload, compress_type=zipfile.ZIP_DEFLATED)


if __name__ == "__main__":
    unittest.main()
