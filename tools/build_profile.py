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

_PROJECT_ROOT = Path(__file__).resolve().parents[1]
_SRC_ROOT = _PROJECT_ROOT / "src"
if str(_SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(_SRC_ROOT))

from greia_installer.layout import (  # noqa: E402
    LayoutError,
    ProfileSizing,
    minimum_device_bytes_for_profile,
)


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
    "pi-native-tryboot": "boot-pi-native",
}
_INSTALLER_BOOT_PACKAGE_SETS: Mapping[str, str] = {
    "grub-pc-bios-live": "boot-grub-pc",
    "pi-native-live": "boot-pi-native",
}
_BOOT_COVER_PACKAGE_SETS: Mapping[str, str] = {
    "stock-plymouth-provisional": "boot-cover-plymouth",
    # Greia-owned early framebuffer cover. The renderer binary is produced by
    # the builder inside the target root; the package set deliberately contains
    # no external runtime packages for the cover itself.
    "greia-early-framebuffer-v1": "boot-cover-greia-early-framebuffer",
}
# A backend is registered here only after its noninteractive/no-text behavior
# has an executed acceptance record. ``greia-early-framebuffer-v1`` passed the
# 2026-10-28 QEMU visual acceptance for the technical-preview composition
# (branded GRUB/cover on the graphical installer and installed A/B target, no
# Linux console text). Physical Acer visual acceptance remains an
# ordinary-family gate and must not be inferred from QEMU evidence.
_RELEASE_SAFE_BOOT_COVERS: frozenset[str] = frozenset({"greia-early-framebuffer-v1"})
# Boot console policy (greia_platform.boot_contract.BootConsolePolicy). It is
# independent of the developer-remote capability: "diagnostic" keeps tty1
# status output for hardware recovery and needs a developer profile; "quiet"
# is the child-facing appliance boot (release, and the developer RC that keeps
# SSH). When a profile omits it, developer profiles stay diagnostic and every
# other profile is quiet, which is exactly the behaviour before the flag.
_ALLOWED_CONSOLE_POLICIES = frozenset({"quiet", "diagnostic"})
_DEVELOPER_REMOTE_SET = "developer-remote"
_DISPLAY_PACKAGE_SETS: Mapping[str, str] = {
    "xorg": "display-xorg",
}

_PHASE0_TARGET_ARCHITECTURES = frozenset({"i386", "amd64"})
_PHASE0_TARGET_LAYOUTS = frozenset({"bios-single-ext4"})
_PHASE0_INSTALLED_BOOT_ADAPTERS = frozenset({"grub-pc-bios"})
_PHASE0_INSTALLER_BOOT_ADAPTERS = frozenset({"grub-pc-bios-live"})
_PHASE0_DISPLAY_ADAPTERS = frozenset({"xorg"})

# L7-PROFILES typed storage/lifecycle adapters (R0/R1 source gate).
#
# Authority: docs/architecture/UNIVERSAL_GREIA_SETUP_MEDIA_ARCHITECTURE.md
# secs 8-14 (layout authority, A/B target layouts, Pi tryboot, PERSIST
# contract, declarative storage/profile extensions) and secs 23-24
# (regression guards: no single-root+updates, no GRUB Pi backend, no unknown
# ARM fallback, no global allow_mmc shortcut). Numeric floors below are
# generic schema floors only, never exact installed-layout sizing: the exact
# slot/PERSIST bounds are owned by greia_platform.persistent_layout and the
# exact installed-target minimum is owned by
# greia_installer.layout.minimum_device_bytes_for_profile (called from
# _validate_storage_lifecycle). They are tightened by on-device measurement
# later, never loosened by guessing.
_MIB = 1024 * 1024
_MIN_SYSTEM_SLOT_BYTES = 1024 * _MIB
_MAX_SYSTEM_SLOT_BYTES = 2 * 1024 * 1024 * 1024
_MIN_PERSISTENT_BYTES = 256 * _MIB
_ALLOWED_LAYOUT_ADAPTERS = frozenset(
    {
        "bios-single-ext4",
        "legacy-bios-ab-v1",
        "modern-gpt-ab-v1",
        "pi-mbr-tryboot-ab-v1",
    }
)
_AB_LAYOUT_ADAPTERS = frozenset(
    {"legacy-bios-ab-v1", "modern-gpt-ab-v1", "pi-mbr-tryboot-ab-v1"}
)
_PI_LAYOUT_ADAPTERS = frozenset({"pi-mbr-tryboot-ab-v1"})
_X86_LAYOUT_ADAPTERS = frozenset(
    {"bios-single-ext4", "legacy-bios-ab-v1", "modern-gpt-ab-v1"}
)
_ALLOWED_TARGET_POLICIES = frozenset({"pc-internal-v1", "pi-builtin-microsd-v1"})
_ALLOWED_BOOT_BACKENDS = frozenset({"grub-ab-v1", "pi-tryboot-ab-v1", "none-v1"})
_ALLOWED_LIVE_BOOT_ADAPTERS = frozenset({"pc-live-syslinux-v1", "pi-live-usb-v1"})
_ALLOWED_ARM_BOARDS = frozenset({"pi-400-v1", "pi-500-v1"})
_ALLOWED_PLATFORM_BOARDS = frozenset({"none", "pi-400-v1", "pi-500-v1"})


@dataclass(frozen=True, slots=True)
class ProfileIdentity:
    profile_id: str
    certification_state: str
    description: str


@dataclass(frozen=True, slots=True)
class PlatformDefinition:
    family: str
    compatibility_class: str
    board: str


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
    console_policy: str


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
class StorageDefinition:
    layout_adapter: str
    system_slot_bytes: int
    persistent_minimum_bytes: int


@dataclass(frozen=True, slots=True)
class InstallerDefinition:
    target_policy: str


@dataclass(frozen=True, slots=True)
class UpdatesDefinition:
    boot_backend: str
    required: bool


@dataclass(frozen=True, slots=True)
class SetupDefinition:
    live_boot_adapter: str


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
    storage: StorageDefinition
    installer: InstallerDefinition
    updates: UpdatesDefinition
    setup: SetupDefinition

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
        storage = _table(raw, "storage")
        installer_table = _table(raw, "installer")
        updates_table = _table(raw, "updates")
        setup = _table(raw, "setup")
        if "allow_mmc" in installer_table:
            raise BuildProfileError(
                "installer.allow_mmc is not a release target-policy API; "
                "use installer.target_policy"
            )

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
                board=_string(platform, "board"),
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
                console_policy=(
                    _string(boot, "console_policy")
                    if "console_policy" in boot
                    else (
                        "diagnostic"
                        if _DEVELOPER_REMOTE_SET in _string_list(packages, "target_sets")
                        else "quiet"
                    )
                ),
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
            storage=StorageDefinition(
                layout_adapter=_string(storage, "layout_adapter"),
                system_slot_bytes=_integer(storage, "system_slot_bytes", minimum=1),
                persistent_minimum_bytes=_integer(
                    storage, "persistent_minimum_bytes", minimum=1
                ),
            ),
            installer=InstallerDefinition(
                target_policy=_string(installer_table, "target_policy"),
            ),
            updates=UpdatesDefinition(
                boot_backend=_string(updates_table, "boot_backend"),
                required=_boolean(updates_table, "required"),
            ),
            setup=SetupDefinition(
                live_boot_adapter=_string(setup, "live_boot_adapter"),
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
        _safe_identifier(self.platform.board, "platform.board")
        self._validate_console_policy()
        self._validate_storage_lifecycle()

    def _validate_console_policy(self) -> None:
        """The diagnostic console is a developer-image property only."""
        if self.boot.console_policy not in _ALLOWED_CONSOLE_POLICIES:
            raise BuildProfileError(
                "boot.console_policy must be one of: "
                + ", ".join(sorted(_ALLOWED_CONSOLE_POLICIES))
            )
        developer = _DEVELOPER_REMOTE_SET in self.packages.target_sets
        if self.boot.console_policy == "diagnostic" and not developer:
            raise BuildProfileError(
                "boot.console_policy='diagnostic' requires the developer-remote "
                "target package set; release images always boot quietly"
            )

    def _validate_storage_lifecycle(self) -> None:
        """Fail closed on invalid storage/target/update/setup combinations."""
        layout = self.storage.layout_adapter
        if layout not in _ALLOWED_LAYOUT_ADAPTERS:
            raise BuildProfileError(
                "storage.layout_adapter must be one of: "
                + ", ".join(sorted(_ALLOWED_LAYOUT_ADAPTERS))
            )
        if self.installer.target_policy not in _ALLOWED_TARGET_POLICIES:
            raise BuildProfileError(
                "installer.target_policy must be one of: "
                + ", ".join(sorted(_ALLOWED_TARGET_POLICIES))
            )
        if self.updates.boot_backend not in _ALLOWED_BOOT_BACKENDS:
            raise BuildProfileError(
                "updates.boot_backend must be one of: "
                + ", ".join(sorted(_ALLOWED_BOOT_BACKENDS))
            )
        if self.setup.live_boot_adapter not in _ALLOWED_LIVE_BOOT_ADAPTERS:
            raise BuildProfileError(
                "setup.live_boot_adapter must be one of: "
                + ", ".join(sorted(_ALLOWED_LIVE_BOOT_ADAPTERS))
            )
        is_ab = layout in _AB_LAYOUT_ADAPTERS
        is_pi_layout = layout in _PI_LAYOUT_ADAPTERS
        is_arm = self.base.architecture == "arm64" or self.platform.family == "arm64"

        # Single-root layouts are never update-capable targets.
        if not is_ab:
            if self.updates.required:
                raise BuildProfileError(
                    "single-root layout "
                    f"{layout!r} cannot satisfy updates.required=true; "
                    "release-capable installation requires an A/B layout"
                )
            if self.updates.boot_backend != "none-v1":
                raise BuildProfileError(
                    "single-root layout "
                    f"{layout!r} requires updates.boot_backend='none-v1'"
                )
        else:
            if self.updates.boot_backend == "none-v1":
                raise BuildProfileError(
                    f"A/B layout {layout!r} requires a registered updates.boot_backend"
                )
        # Backend/layout family binding. Pi firmware uses native tryboot;
        # GRUB on a Pi layout is a hard failure, not a fallback.
        if is_pi_layout:
            if self.updates.boot_backend == "grub-ab-v1":
                raise BuildProfileError(
                    f"Pi layout {layout!r} cannot pair with GRUB update backend 'grub-ab-v1'; "
                    "Pi uses the native tryboot backend"
                )
            if self.updates.boot_backend != "pi-tryboot-ab-v1":
                raise BuildProfileError(
                    f"Pi layout {layout!r} requires updates.boot_backend='pi-tryboot-ab-v1'"
                )
        elif self.updates.boot_backend == "pi-tryboot-ab-v1":
            raise BuildProfileError(
                f"tryboot backend 'pi-tryboot-ab-v1' requires a Pi layout, not {layout!r}"
            )
        elif is_ab and self.updates.boot_backend != "grub-ab-v1":
            raise BuildProfileError(
                f"x86 A/B layout {layout!r} requires updates.boot_backend='grub-ab-v1'"
            )
        # Architecture/layout binding keeps Pi layouts off x86 and vice versa.
        if is_pi_layout and not (self.base.architecture == "arm64" and self.platform.family == "arm64"):
            raise BuildProfileError(
                f"Pi layout {layout!r} requires base.architecture='arm64' and platform.family='arm64'"
            )
        if not is_pi_layout and is_arm:
            raise BuildProfileError(
                f"x86 layout {layout!r} cannot pair with ARM architecture/family"
            )
        if layout == "modern-gpt-ab-v1" and self.base.architecture != "amd64":
            raise BuildProfileError(
                f"layout {layout!r} requires base.architecture='amd64'"
            )
        # Target policy is the release API; allow_mmc is rejected at load.
        if is_pi_layout:
            if self.installer.target_policy != "pi-builtin-microsd-v1":
                raise BuildProfileError(
                    f"Pi layout {layout!r} requires installer.target_policy='pi-builtin-microsd-v1'"
                )
        elif self.installer.target_policy != "pc-internal-v1":
            raise BuildProfileError(
                f"layout {layout!r} requires installer.target_policy='pc-internal-v1'"
            )
        # Live-boot adapter follows the same family split.
        if is_pi_layout:
            if self.setup.live_boot_adapter != "pi-live-usb-v1":
                raise BuildProfileError(
                    f"Pi layout {layout!r} requires setup.live_boot_adapter='pi-live-usb-v1'"
                )
        elif self.setup.live_boot_adapter != "pc-live-syslinux-v1":
            raise BuildProfileError(
                f"layout {layout!r} requires setup.live_boot_adapter='pc-live-syslinux-v1'"
            )
        # ARM board fallback: unknown/generic ARM never defaults to a known Pi.
        if is_arm:
            if self.platform.board not in _ALLOWED_ARM_BOARDS:
                raise BuildProfileError(
                    f"ARM profile requires an explicit platform.board in "
                    f"{sorted(_ALLOWED_ARM_BOARDS)}; "
                    f"{self.platform.board!r} is not a supported ARM board fallback"
                )
        elif self.platform.board != "none":
            raise BuildProfileError(
                f"x86 profile requires platform.board='none', not {self.platform.board!r}"
            )
        if is_pi_layout and self.platform.board == "none":
            raise BuildProfileError(
                f"Pi layout {layout!r} requires an explicit platform.board, not 'none'"
            )
        # Slot floor covers the L7-RELEASE base release + finalization upper
        # bound; the ceiling matches the build_release minimum_slot bound.
        if self.storage.system_slot_bytes < _MIN_SYSTEM_SLOT_BYTES:
            raise BuildProfileError(
                "storage.system_slot_bytes "
                f"({self.storage.system_slot_bytes}) is below the base release + "
                f"finalization upper bound ({_MIN_SYSTEM_SLOT_BYTES})"
            )
        if self.storage.system_slot_bytes > _MAX_SYSTEM_SLOT_BYTES:
            raise BuildProfileError(
                "storage.system_slot_bytes exceeds the release slot bound "
                f"({_MAX_SYSTEM_SLOT_BYTES})"
            )
        if self.storage.persistent_minimum_bytes < _MIN_PERSISTENT_BYTES:
            raise BuildProfileError(
                "storage.persistent_minimum_bytes "
                f"({self.storage.persistent_minimum_bytes}) is below the PERSIST "
                f"minimum ({_MIN_PERSISTENT_BYTES})"
            )
        # Installed-target capacity: the canonical minimum is owned by the
        # real installer layout adapter
        # (greia_installer.layout.minimum_device_bytes_for_profile:
        # LABEL_RESERVED + fixed partitions + PERSIST minimum from the
        # actual partition model). image.size_mib is deliberately NOT
        # compared against it: it sizes the intermediate single-root build
        # artifact (build/build-image.sh truncates IMAGE_SIZE_MIB for one
        # root filesystem), while installed-disk fit is proven at install
        # time by plan_for_profile. This static gate only proves the
        # profile's storage facts are coherent under the real adapter.
        if is_ab:
            try:
                minimum_device_bytes_for_profile(
                    ProfileSizing(
                        layout_adapter_id=layout,
                        slot_bytes=self.storage.system_slot_bytes,
                        persist_minimum_bytes=self.storage.persistent_minimum_bytes,
                        boot_backend=self.updates.boot_backend,
                    )
                )
            except LayoutError as exc:
                raise BuildProfileError(
                    "storage facts do not yield an installed-target minimum "
                    f"under the real layout adapter: {exc}"
                ) from exc

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
            "profile": {
                "id": self.identity.profile_id,
                "certification_state": self.identity.certification_state,
                "description": self.identity.description,
            },
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
            "storage": asdict(self.storage),
            "installer": asdict(self.installer),
            "updates": asdict(self.updates),
            "setup": asdict(self.setup),
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
            "BOOT_CONSOLE_POLICY": self.boot.console_policy,
            "DISPLAY_ADAPTER": self.display.adapter,
            "VIDEO_PACKAGES": " ".join(self.display.video_packages),
            "RUNTIME_FAMILIES": " ".join(self.runtimes.enabled),
            "EXTRA_PACKAGES": " ".join(self.packages.extra_packages),
            "STORAGE_LAYOUT_ADAPTER": self.storage.layout_adapter,
            "STORAGE_SYSTEM_SLOT_BYTES": str(self.storage.system_slot_bytes),
            "STORAGE_PERSISTENT_MINIMUM_BYTES": str(self.storage.persistent_minimum_bytes),
            "INSTALLER_TARGET_POLICY": self.installer.target_policy,
            "UPDATES_BOOT_BACKEND": self.updates.boot_backend,
            "UPDATES_REQUIRED": "true" if self.updates.required else "false",
            "SETUP_LIVE_BOOT_ADAPTER": self.setup.live_boot_adapter,
            "PLATFORM_BOARD": self.platform.board,
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


def _boolean(container: Mapping[str, object], key: str) -> bool:
    value = container.get(key)
    if not isinstance(value, bool):
        raise BuildProfileError(f"{key} must be a boolean")
    return value


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
