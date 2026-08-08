from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import tomllib
from types import MappingProxyType
from typing import Mapping

from .activities import ActivityRegistration, RuntimeCatalogue
from .trust import PackageTrust


class PermissionDecisionError(ValueError):
    """Raised when trusted launch authority cannot be issued safely."""


@dataclass(frozen=True, slots=True)
class ActivityAuthority:
    """Immutable, platform-issued effective grants for one Activity launch.

    ``requested_*`` values describe package intent. ``effective_capabilities``
    and ``granted_permissions`` are the only values launch/sandbox code may use
    to expose resources. The object is created in the trusted Greia process from
    an ``ActivityRegistration`` produced by the package registry; Activity
    process environment values are merely a descriptive mirror.
    """

    activity_id: str
    package_digest: str
    package_trust: PackageTrust
    requested_capabilities: frozenset[str]
    effective_capabilities: frozenset[str]
    requested_permissions: frozenset[str]
    granted_permissions: frozenset[str]

    def has_capability(self, capability: str) -> bool:
        return capability in self.effective_capabilities

    def has_permission(self, permission: str) -> bool:
        return permission in self.granted_permissions

    @property
    def sdk_features(self) -> frozenset[str]:
        """Features mirrored to the Activity SDK for ergonomics only."""

        return self.effective_capabilities | self.granted_permissions


@dataclass(frozen=True, slots=True)
class PermissionPolicy:
    """Trusted policy inputs used to compute one launch's effective grants.

    R1 deliberately models every authority gate now even though Phase 0 still
    uses static runtime/hardware/build/parent sets. R6 will replace the static
    capability inputs with the Device Capability Service without changing the
    broker/supervisor contract.
    """

    runtime_capabilities: frozenset[str]
    hardware_capabilities: frozenset[str]
    build_allowed_capabilities: frozenset[str]
    build_allowed_permissions: frozenset[str]
    parent_allowed_permissions: frozenset[str]
    privileged_permissions: frozenset[str]
    permission_capability_requirements: Mapping[str, str]
    built_in_grants: Mapping[str, frozenset[str]]

    @classmethod
    def load(cls, path: Path, runtime: RuntimeCatalogue) -> "PermissionPolicy":
        try:
            with path.open("rb") as handle:
                raw = tomllib.load(handle)
        except (OSError, tomllib.TOMLDecodeError) as exc:
            raise PermissionDecisionError(f"invalid permission policy {path}: {exc}") from exc
        if raw.get("schema_version") != 1:
            raise PermissionDecisionError("permission policy schema_version must be 1")
        build = raw.get("build")
        security = raw.get("security")
        if not isinstance(build, dict) or not isinstance(security, dict):
            raise PermissionDecisionError("permission policy requires build and security tables")
        allowed_raw = build.get("allowed_permissions")
        if not isinstance(allowed_raw, list) or not all(isinstance(item, str) for item in allowed_raw):
            raise PermissionDecisionError("build.allowed_permissions must be a string list")
        allowed_permissions = frozenset(allowed_raw)
        unknown = allowed_permissions - runtime.privileged_capabilities
        if unknown:
            raise PermissionDecisionError(
                "permission policy contains unknown privileged permissions: "
                + ", ".join(sorted(unknown))
            )
        built_in_raw = security.get("built_in", {})
        if not isinstance(built_in_raw, dict):
            raise PermissionDecisionError("security.built_in must be a table")
        built_in_grants: dict[str, frozenset[str]] = {}
        for activity_id, grants_raw in built_in_raw.items():
            if not isinstance(activity_id, str) or not isinstance(grants_raw, list) or not all(
                isinstance(item, str) for item in grants_raw
            ):
                raise PermissionDecisionError(
                    "security.built_in entries must map Activity IDs to string lists"
                )
            grants = frozenset(grants_raw)
            unknown_grants = grants - allowed_permissions
            if unknown_grants:
                raise PermissionDecisionError(
                    f"built-in policy for {activity_id} contains permissions outside build policy: "
                    + ", ".join(sorted(unknown_grants))
                )
            built_in_grants[activity_id] = grants
        return cls.phase0(
            runtime,
            build_allowed_permissions=allowed_permissions,
            built_in_grants=built_in_grants,
        )

    @classmethod
    def phase0(
        cls,
        runtime: RuntimeCatalogue,
        *,
        build_allowed_permissions: frozenset[str] | None = None,
        built_in_grants: Mapping[str, frozenset[str]] | None = None,
    ) -> "PermissionPolicy":
        # Phase 0 has no Device Capability Service yet. These sets therefore
        # represent the capabilities the current image/runtime path is prepared
        # to attempt, NOT physical-hardware certification. Device-backed binds
        # remain fail-soft (`--dev-bind-try`) and R6 replaces this static input.
        supported = runtime.allowed_capabilities
        return cls(
            runtime_capabilities=supported,
            hardware_capabilities=supported,
            build_allowed_capabilities=supported,
            build_allowed_permissions=(
                build_allowed_permissions
                if build_allowed_permissions is not None
                else runtime.privileged_capabilities
            ),
            parent_allowed_permissions=(
                build_allowed_permissions
                if build_allowed_permissions is not None
                else runtime.privileged_capabilities
            ),
            privileged_permissions=runtime.privileged_capabilities,
            permission_capability_requirements=MappingProxyType(
                {"removable_media.read": "removable_media.read"}
            ),
            built_in_grants=MappingProxyType(
                dict(built_in_grants)
                if built_in_grants is not None
                else {"workshop_settings": runtime.privileged_capabilities}
            ),
        )


class PermissionBroker:
    """Compute effective Activity grants outside the Activity process.

    The current security policy intentionally grants privileged permissions only
    to packages whose registry source is ``BUILT_IN``. Future signed/parent trust
    states remain deny-by-default until R10 introduces the package trust chain
    and explicit policy for them.
    """

    def __init__(self, policy: PermissionPolicy):
        self._policy = policy

    @classmethod
    def phase0(
        cls, runtime: RuntimeCatalogue, policy_path: Path | None = None
    ) -> "PermissionBroker":
        policy = (
            PermissionPolicy.load(policy_path, runtime)
            if policy_path is not None
            else PermissionPolicy.phase0(runtime)
        )
        return cls(policy)

    def issue(self, registration: ActivityRegistration) -> ActivityAuthority:
        if not isinstance(registration, ActivityRegistration):
            raise PermissionDecisionError(
                "effective grants require an ActivityRegistration issued by the registry"
            )

        manifest = registration.manifest
        requested = frozenset(manifest.capabilities)
        requested_permissions = requested & self._policy.privileged_permissions
        requested_capabilities = requested - self._policy.privileged_permissions

        effective_capabilities = (
            requested_capabilities
            & self._policy.runtime_capabilities
            & self._policy.hardware_capabilities
            & self._policy.build_allowed_capabilities
        )

        policy_permissions = (
            requested_permissions
            & self._policy.build_allowed_permissions
            & self._policy.parent_allowed_permissions
        )

        # Platform security policy: privilege is origin + identity. A package
        # must come from a BUILT_IN source and be explicitly allowlisted for the
        # requested operation. Merely choosing a reserved Activity ID never grants
        # authority to an external package.
        if registration.package_trust is PackageTrust.BUILT_IN:
            security_allowed = self._policy.built_in_grants.get(
                manifest.activity_id, frozenset()
            )
            policy_permissions &= security_allowed
        else:
            policy_permissions = frozenset()

        granted_permissions = frozenset(
            permission
            for permission in policy_permissions
            if self._permission_capability_is_available(permission)
        )

        return ActivityAuthority(
            activity_id=manifest.activity_id,
            package_digest=registration.package_digest,
            package_trust=registration.package_trust,
            requested_capabilities=requested_capabilities,
            effective_capabilities=effective_capabilities,
            requested_permissions=requested_permissions,
            granted_permissions=granted_permissions,
        )

    def _permission_capability_is_available(self, permission: str) -> bool:
        requirement = self._policy.permission_capability_requirements.get(permission)
        if requirement is None:
            return True
        return (
            requirement in self._policy.runtime_capabilities
            and requirement in self._policy.hardware_capabilities
            and requirement in self._policy.build_allowed_capabilities
        )
