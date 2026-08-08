#!/usr/bin/env python3
"""Typed Greia OS image-profile loader and package resolver.

Build profiles are declarative data. They describe what an OS image contains;
they are deliberately distinct from runtime hardware capability probes.
"""

from __future__ import annotations

import argparse
import json
import re
import shlex
import sys
import tomllib
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Mapping, Sequence


class BuildProfileError(ValueError):
    """Raised when a build profile or package set violates the image contract."""


_SAFE_ID_RE = re.compile(r"^[a-z0-9][a-z0-9._-]*$")
_DEBIAN_PACKAGE_RE = re.compile(r"^[a-z0-9][a-z0-9+.-]*$")
_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_ALLOWED_ARCHITECTURES = frozenset({"i386", "amd64", "arm64"})
_ALLOWED_PLATFORM_FAMILIES = frozenset(
    {"legacy-x86", "standard-x86-64", "arm64", "developer-vm"}
)
_ALLOWED_COMPATIBILITY_CLASSES = frozenset({"C0", "C1", "C2", "C3"})
_ALLOWED_RUNTIME_FAMILIES = frozenset({"python", "web"})
_ALLOWED_CERTIFICATION_STATES = frozenset({"unverified", "experimental", "certified"})

# Runtime families are platform-owned shared adapters. Adding a runtime family
# requires adding its measured package set rather than letting Activities bring
# dependencies into an image.
_RUNTIME_PACKAGE_SETS: Mapping[str, str] = {
    "python": "runtime-python",
    "web": "runtime-web",
}

# Current adapter package mappings. The schema is intentionally broader than
# the Phase 0 builder implementation so future ARM/display builders can reuse
# the same profile model.
_INSTALLED_BOOT_PACKAGE_SETS: Mapping[str, str] = {
    "grub-pc-bios": "boot-grub-pc",
}
_INSTALLER_BOOT_PACKAGE_SETS: Mapping[str, str] = {
    "grub-pc-bios-live": "boot-grub-pc",
}
_BOOT_COVER_PACKAGE_SETS: Mapping[str, str] = {
    "stock-plymouth-provisional": "boot-cover-plymouth",
}
# Empty by design in Phase 0. A future backend must be deliberately registered
# here only after its noninteractive/no-text failure behavior is accepted.
_RELEASE_SAFE_BOOT_COVERS: frozenset[str] = frozenset()
_DISPLAY_PACKAGE_SETS: Mapping[str, str] = {
    "xorg": "display-xorg",
}

_PHASE0_TARGET_ARCHITECTURES = frozenset({"i386", "amd64"})
_PHASE0_TARGET_LAYOUTS = frozenset({"bios-single-ext4"})
_PHASE0_INSTALLED_BOOT_ADAPTERS = frozenset({"grub-pc-bios"})
_PHASE0_INSTALLER_BOOT_ADAPTERS = frozenset({"grub-pc-bios-live"})
_PHASE0_DISPLAY_ADAPTERS = frozenset({"xorg"})


@dataclass(frozen=True, slots=True)
class ProfileIdentity:
    profile_id: str
    certification_state: str
    description: str


@dataclass(frozen=True, slots=True)
class PlatformDefinition:
    family: str
    compatibility_class: str


@dataclass(frozen=True, slots=True)
class BaseDefinition:
    suite: str
    architecture: str
    mirror: str
    security_mirror: str
    support_end_date: str
    kernel_package: str


@dataclass(frozen=True, slots=True)
class ImageDefinition:
    layout: str
    size_mib: int
    hostname: str


@dataclass(frozen=True, slots=True)
class BootDefinition:
    installed_adapter: str
    installer_adapter: str
    cover_backend: str


@dataclass(frozen=True, slots=True)
class DisplayDefinition:
    adapter: str
    video_packages: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class RuntimeDefinition:
    enabled: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class PackageDefinition:
    target_sets: tuple[str, ...]
    installer_sets: tuple[str, ...]
    extra_packages: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ResourceLimits:
    preferred_core_mib: int
    required_core_mib: int
    architecture_review_mib: int


@dataclass(frozen=True, slots=True)
class BuildProfile:
    schema_version: int
    identity: ProfileIdentity
    platform: PlatformDefinition
    base: BaseDefinition
    image: ImageDefinition
    boot: BootDefinition
    display: DisplayDefinition
    runtimes: RuntimeDefinition
    packages: PackageDefinition
    resources: ResourceLimits

    @classmethod
    def load(cls, path: Path) -> "BuildProfile":
        try:
            with path.open("rb") as handle:
                raw = tomllib.load(handle)
        except (OSError, tomllib.TOMLDecodeError) as exc:
            raise BuildProfileError(f"cannot read build profile {path}: {exc}") from exc

        schema_version = _integer(raw, "schema_version", minimum=1, maximum=1)
        profile = _table(raw, "profile")
        platform = _table(raw, "platform")
        base = _table(raw, "base")
        image = _table(raw, "image")
        boot = _table(raw, "boot")
        display = _table(raw, "display")
        runtimes = _table(raw, "runtimes")
        packages = _table(raw, "packages")
        resources = _table(raw, "resources")

        result = cls(
            schema_version=schema_version,
            identity=ProfileIdentity(
                profile_id=_string(profile, "id"),
                certification_state=_string(profile, "certification_state"),
                description=_string(profile, "description"),
            ),
            platform=PlatformDefinition(
                family=_string(platform, "family"),
                compatibility_class=_string(platform, "compatibility_class"),
            ),
            base=BaseDefinition(
                suite=_string(base, "suite"),
                architecture=_string(base, "architecture"),
                mirror=_string(base, "mirror"),
                security_mirror=_string(base, "security_mirror"),
                support_end_date=_string(base, "support_end_date"),
                kernel_package=_string(base, "kernel_package"),
            ),
            image=ImageDefinition(
                layout=_string(image, "layout"),
                size_mib=_integer(image, "size_mib", minimum=512, maximum=65536),
                hostname=_string(image, "hostname"),
            ),
            boot=BootDefinition(
                installed_adapter=_string(boot, "installed_adapter"),
                installer_adapter=_string(boot, "installer_adapter"),
                cover_backend=_string(boot, "cover_backend"),
            ),
            display=DisplayDefinition(
                adapter=_string(display, "adapter"),
                video_packages=_string_list(display, "video_packages"),
            ),
            runtimes=RuntimeDefinition(enabled=_string_list(runtimes, "enabled")),
            packages=PackageDefinition(
                target_sets=_string_list(packages, "target_sets"),
                installer_sets=_string_list(packages, "installer_sets"),
                extra_packages=_string_list(packages, "extra_packages"),
            ),
            resources=ResourceLimits(
                preferred_core_mib=_integer(resources, "preferred_core_mib", minimum=1),
                required_core_mib=_integer(resources, "required_core_mib", minimum=1),
                architecture_review_mib=_integer(resources, "architecture_review_mib", minimum=1),
            ),
        )
        result.validate()
        return result

    def validate(self) -> None:
        _safe_identifier(self.identity.profile_id, "profile.id")
        if self.identity.certification_state not in _ALLOWED_CERTIFICATION_STATES:
            raise BuildProfileError(
                "profile.certification_state must be one of: "
                + ", ".join(sorted(_ALLOWED_CERTIFICATION_STATES))
            )
        if self.platform.family not in _ALLOWED_PLATFORM_FAMILIES:
            raise BuildProfileError(
                "platform.family must be one of: "
                + ", ".join(sorted(_ALLOWED_PLATFORM_FAMILIES))
            )
        if self.platform.compatibility_class not in _ALLOWED_COMPATIBILITY_CLASSES:
            raise BuildProfileError(
                "platform.compatibility_class must be one of: "
                + ", ".join(sorted(_ALLOWED_COMPATIBILITY_CLASSES))
            )
        if self.base.architecture not in _ALLOWED_ARCHITECTURES:
            raise BuildProfileError(
                "base.architecture must be one of: "
                + ", ".join(sorted(_ALLOWED_ARCHITECTURES))
            )
        for name, value in (
            ("base.suite", self.base.suite),
            ("base.kernel_package", self.base.kernel_package),
            ("image.hostname", self.image.hostname),
        ):
            _safe_identifier(value, name)
        for name, value in (
            ("base.mirror", self.base.mirror),
            ("base.security_mirror", self.base.security_mirror),
        ):
            if not value.startswith("https://"):
                raise BuildProfileError(f"{name} must use https://")
        if not _DATE_RE.fullmatch(self.base.support_end_date):
            raise BuildProfileError("base.support_end_date must be YYYY-MM-DD")
        if not self.runtimes.enabled:
            raise BuildProfileError("runtimes.enabled must contain at least one runtime family")
        _unique(self.runtimes.enabled, "runtimes.enabled")
        unknown_runtimes = sorted(set(self.runtimes.enabled) - _ALLOWED_RUNTIME_FAMILIES)
        if unknown_runtimes:
            raise BuildProfileError("unknown runtime families: " + ", ".join(unknown_runtimes))
        _unique(self.packages.target_sets, "packages.target_sets")
        _unique(self.packages.installer_sets, "packages.installer_sets")
        for package_set in (*self.packages.target_sets, *self.packages.installer_sets):
            _safe_identifier(package_set, "package set")
        for package in (
            self.base.kernel_package,
            *self.display.video_packages,
            *self.packages.extra_packages,
        ):
            _safe_package(package)
        if not (
            self.resources.preferred_core_mib
            < self.resources.required_core_mib
            <= self.resources.architecture_review_mib
        ):
            raise BuildProfileError(
                "resource limits must satisfy preferred_core_mib < required_core_mib "
                "<= architecture_review_mib"
            )
        if self.image.size_mib <= self.resources.required_core_mib:
            raise BuildProfileError(
                "image.size_mib must exceed resources.required_core_mib to leave writable headroom"
            )

    def check_phase0_builder_support(self, scope: str) -> None:
        if self.base.architecture not in _PHASE0_TARGET_ARCHITECTURES:
            raise BuildProfileError(
                f"Phase 0 {scope} builder does not implement architecture "
                f"{self.base.architecture!r}; the profile schema supports ARM64 but a board boot adapter "
                "must be implemented deliberately before building it."
            )
        if self.image.layout not in _PHASE0_TARGET_LAYOUTS:
            raise BuildProfileError(
                f"Phase 0 builder does not implement image layout {self.image.layout!r}"
            )
        if self.display.adapter not in _PHASE0_DISPLAY_ADAPTERS:
            raise BuildProfileError(
                f"Phase 0 builder does not implement display adapter {self.display.adapter!r}"
            )
        if scope == "target":
            if self.boot.installed_adapter not in _PHASE0_INSTALLED_BOOT_ADAPTERS:
                raise BuildProfileError(
                    "Phase 0 target builder does not implement installed boot adapter "
                    f"{self.boot.installed_adapter!r}"
                )
        elif scope == "installer":
            if self.boot.installer_adapter not in _PHASE0_INSTALLER_BOOT_ADAPTERS:
                raise BuildProfileError(
                    "Phase 0 installer builder does not implement installer boot adapter "
                    f"{self.boot.installer_adapter!r}"
                )
        else:
            raise BuildProfileError(f"unknown builder scope: {scope}")

    def check_release_eligibility(self) -> None:
        if self.boot.cover_backend not in _RELEASE_SAFE_BOOT_COVERS:
            raise BuildProfileError(
                f"boot cover {self.boot.cover_backend!r} is not registered as release-safe; "
                "a noninteractive branded-only backend must pass its acceptance gate first"
            )

    def package_set_names(self, scope: str) -> tuple[str, ...]:
        if scope == "target":
            names: list[str] = list(self.packages.target_sets)
            names.append(_adapter_package_set(_INSTALLED_BOOT_PACKAGE_SETS, self.boot.installed_adapter, "installed boot"))
            names.append(_adapter_package_set(_BOOT_COVER_PACKAGE_SETS, self.boot.cover_backend, "boot cover"))
            names.append(_adapter_package_set(_DISPLAY_PACKAGE_SETS, self.display.adapter, "display"))
            for runtime in self.runtimes.enabled:
                names.append(_adapter_package_set(_RUNTIME_PACKAGE_SETS, runtime, "runtime"))
        elif scope == "installer":
            names = list(self.packages.installer_sets)
            names.append(_adapter_package_set(_INSTALLER_BOOT_PACKAGE_SETS, self.boot.installer_adapter, "installer boot"))
            names.append(_adapter_package_set(_BOOT_COVER_PACKAGE_SETS, self.boot.cover_backend, "boot cover"))
            names.append(_adapter_package_set(_DISPLAY_PACKAGE_SETS, self.display.adapter, "display"))
        else:
            raise BuildProfileError(f"unknown package scope: {scope}")
        return tuple(dict.fromkeys(names))

    def resolve_packages(self, package_root: Path, scope: str) -> tuple[str, ...]:
        packages: list[str] = []
        for package_set in self.package_set_names(scope):
            path = package_root / f"{package_set}.txt"
            if not path.is_file():
                raise BuildProfileError(
                    f"package set {package_set!r} required by {self.identity.profile_id} is missing: {path}"
                )
            for raw_line in path.read_text(encoding="utf-8").splitlines():
                line = raw_line.strip()
                if not line or line.startswith("#"):
                    continue
                _safe_package(line)
                packages.append(line)
        packages.extend(self.display.video_packages)
        packages.extend(self.packages.extra_packages)
        packages.append(self.base.kernel_package)
        return tuple(dict.fromkeys(packages))

    def declared_manifest(self, scope: str = "target") -> dict[str, object]:
        """Return the architecture declaration embedded in produced images.

        This is intentionally not a hardware capability report. Runtime probes
        remain authoritative for what the current machine can actually do.
        """

        if scope not in {"target", "installer"}:
            raise BuildProfileError(f"unknown manifest scope: {scope}")
        return {
            "schema_version": self.schema_version,
            "artifact_scope": scope,
            "profile": asdict(self.identity),
            "platform": asdict(self.platform),
            "base": {
                "suite": self.base.suite,
                "architecture": self.base.architecture,
                "support_end_date": self.base.support_end_date,
                "kernel_package": self.base.kernel_package,
            },
            "image": asdict(self.image),
            "boot": asdict(self.boot),
            "display": {
                "adapter": self.display.adapter,
                "video_packages": list(self.display.video_packages),
            },
            "runtimes": {"enabled": list(self.runtimes.enabled)},
            "package_sets": {
                "target": list(self.package_set_names("target")),
                "installer": list(self.package_set_names("installer")),
            },
            "resources": asdict(self.resources),
            "contract": {
                "activity_abstraction": "runtime-independent",
                "capabilities_are_runtime_probed": True,
            },
        }

    def shell_assignments(self) -> str:
        fields = {
            "PROFILE_ID": self.identity.profile_id,
            "CERTIFICATION_STATE": self.identity.certification_state,
            "PLATFORM_FAMILY": self.platform.family,
            "COMPATIBILITY_CLASS": self.platform.compatibility_class,
            "SUITE": self.base.suite,
            "ARCH": self.base.architecture,
            "MIRROR": self.base.mirror,
            "SECURITY_MIRROR": self.base.security_mirror,
            "SUPPORT_END_DATE": self.base.support_end_date,
            "KERNEL_PACKAGE": self.base.kernel_package,
            "IMAGE_LAYOUT": self.image.layout,
            "IMAGE_SIZE_MIB": str(self.image.size_mib),
            "HOSTNAME": self.image.hostname,
            "INSTALLED_BOOT_ADAPTER": self.boot.installed_adapter,
            "INSTALLER_BOOT_ADAPTER": self.boot.installer_adapter,
            "BOOT_COVER_BACKEND": self.boot.cover_backend,
            "DISPLAY_ADAPTER": self.display.adapter,
            "VIDEO_PACKAGES": " ".join(self.display.video_packages),
            "RUNTIME_FAMILIES": " ".join(self.runtimes.enabled),
            "EXTRA_PACKAGES": " ".join(self.packages.extra_packages),
            "PREFERRED_LIMIT_MIB": str(self.resources.preferred_core_mib),
            "REQUIRED_LIMIT_MIB": str(self.resources.required_core_mib),
            "ARCHITECTURE_REVIEW_LIMIT_MIB": str(self.resources.architecture_review_mib),
        }
        return "\n".join(f"{key}={shlex.quote(value)}" for key, value in fields.items())


def _adapter_package_set(mapping: Mapping[str, str], adapter: str, kind: str) -> str:
    try:
        return mapping[adapter]
    except KeyError as exc:
        raise BuildProfileError(f"no package-set mapping exists for {kind} adapter {adapter!r}") from exc


def _table(container: Mapping[str, object], key: str) -> Mapping[str, object]:
    value = container.get(key)
    if not isinstance(value, dict):
        raise BuildProfileError(f"{key} must be a table")
    return value


def _string(container: Mapping[str, object], key: str) -> str:
    value = container.get(key)
    if not isinstance(value, str) or not value.strip():
        raise BuildProfileError(f"{key} must be a non-empty string")
    return value.strip()


def _integer(
    container: Mapping[str, object], key: str, *, minimum: int, maximum: int | None = None
) -> int:
    value = container.get(key)
    if not isinstance(value, int) or isinstance(value, bool) or value < minimum:
        raise BuildProfileError(f"{key} must be an integer >= {minimum}")
    if maximum is not None and value > maximum:
        raise BuildProfileError(f"{key} must be an integer <= {maximum}")
    return value


def _string_list(container: Mapping[str, object], key: str) -> tuple[str, ...]:
    value = container.get(key)
    if not isinstance(value, list) or not all(isinstance(item, str) and item.strip() for item in value):
        raise BuildProfileError(f"{key} must be an array of non-empty strings")
    return tuple(item.strip() for item in value)


def _safe_identifier(value: str, field: str) -> None:
    if not _SAFE_ID_RE.fullmatch(value):
        raise BuildProfileError(f"{field} contains unsupported characters: {value!r}")


def _safe_package(value: str) -> None:
    if not _DEBIAN_PACKAGE_RE.fullmatch(value):
        raise BuildProfileError(f"unsafe/invalid Debian package name: {value!r}")


def _unique(values: Sequence[str], field: str) -> None:
    if len(values) != len(set(values)):
        raise BuildProfileError(f"{field} must not contain duplicates")


def _profile_path(profile_arg: str, profile_root: Path) -> Path:
    direct = Path(profile_arg)
    if direct.is_file():
        return direct.resolve()
    name = profile_arg[:-5] if profile_arg.endswith(".toml") else profile_arg
    candidate = profile_root / f"{name}.toml"
    if not candidate.is_file():
        raise BuildProfileError(f"profile not found: {candidate}")
    return candidate.resolve()


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--profile-root",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "build" / "profiles",
    )
    parser.add_argument(
        "--package-root",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "build" / "package-sets",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    for command in ("validate", "shell"):
        child = subparsers.add_parser(command)
        child.add_argument("profile")
    manifest = subparsers.add_parser("manifest")
    manifest.add_argument("profile")
    manifest.add_argument("--scope", choices=("target", "installer"), default="target")
    release = subparsers.add_parser("check-release")
    release.add_argument("profile")
    check = subparsers.add_parser("check-phase0-builder")
    check.add_argument("profile")
    check.add_argument("--scope", choices=("target", "installer"), required=True)
    packages = subparsers.add_parser("packages")
    packages.add_argument("profile")
    packages.add_argument("--scope", choices=("target", "installer"), required=True)
    package_sets = subparsers.add_parser("package-sets")
    package_sets.add_argument("profile")
    package_sets.add_argument("--scope", choices=("target", "installer"), required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        path = _profile_path(args.profile, args.profile_root)
        profile = BuildProfile.load(path)
        if args.command == "validate":
            # Resolve both scopes so profile/package-set drift is caught by normal validation.
            profile.resolve_packages(args.package_root, "target")
            profile.resolve_packages(args.package_root, "installer")
            print(f"PASS profile={profile.identity.profile_id}")
        elif args.command == "shell":
            print(profile.shell_assignments())
        elif args.command == "manifest":
            json.dump(profile.declared_manifest(args.scope), sys.stdout, indent=2, sort_keys=True)
            sys.stdout.write("\n")
        elif args.command == "check-release":
            profile.check_release_eligibility()
            print(f"PASS release profile={profile.identity.profile_id}")
        elif args.command == "check-phase0-builder":
            profile.check_phase0_builder_support(args.scope)
            print(f"PASS phase0-{args.scope} profile={profile.identity.profile_id}")
        elif args.command == "packages":
            for package in profile.resolve_packages(args.package_root, args.scope):
                print(package)
        elif args.command == "package-sets":
            for package_set in profile.package_set_names(args.scope):
                print(package_set)
        else:  # pragma: no cover - argparse protects this
            raise BuildProfileError(f"unknown command: {args.command}")
    except BuildProfileError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
