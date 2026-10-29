from __future__ import annotations

import ast
import os
import subprocess
import sys
import tomllib
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Callable, Mapping, Protocol, Sequence

from greia_platform.activities import ActivityManifest
from greia_platform.activity_backend_policy import (
    BackendFindingSeverity,
    scan_python_source,
)
from greia_platform.bytecode_cache import (
    PYCACHE_PREFIX_ENVIRONMENT,
    TrustedBytecodePrefix,
)
from greia_platform.device_capabilities import DeviceCapabilityService
from greia_platform.trust import PackageTrust

from .launch_validation_cache import LaunchValidationCache

from .lifecycle import (
    ActivityControlChannel,
    ActivityLifecycleControl,
    ProcessHandle,
    signal_process_group,
)


PRODUCTION_ROOT = Path("/opt/greia-os")
#: Platform-owned interpreter entry; see greia_platform.python_activity_entry.
PYTHON_ACTIVITY_ENTRY_MODULE = "greia_platform.python_activity_entry"
#: SDL hint the curated Pygame runtime always sets for Activities: present the
#: window surface through SDL's plain software framebuffer instead of SDL 2.26's
#: X11 "texture framebuffer" (a GL renderer streaming each frame through a
#: texture). Measured on the reference Atom N270 / GMA 950 (Acer re-sweep at
#: 0f560c2e, docs/reviews/acer/2026-10-16_ACER_ACTIVITY_SWEEP.md R.2):
#: ``set_mode`` 0.7-1.2 s -> 0.03-0.15 s, about 70 MB less RSS per process
#: (Mesa/libGL is never loaded) and half the per-flip cost. Software surfaces
#: are what Pygame Activities draw into anyway; the dummy/KMSDRM/desktop
#: drivers simply honour or ignore the hint.
SDL_SOFTWARE_FRAMEBUFFER_ENVIRONMENT = ("SDL_FRAMEBUFFER_ACCELERATION", "0")
_PLATFORM_OWNED_ENVIRONMENT = frozenset(
    {
        "DISPLAY",
        "HOME",
        "LANG",
        "LC_ALL",
        "PATH",
        "PULSE_SERVER",
        "PYTHONPATH",
        "SDL_AUDIODRIVER",
        "SDL_VIDEODRIVER",
        "WAYLAND_DISPLAY",
        "XAUTHORITY",
        "XDG_CACHE_HOME",
        "XDG_CONFIG_HOME",
        "XDG_DATA_HOME",
        "XDG_RUNTIME_DIR",
    }
)


class RuntimeAdapterError(ValueError):
    """Base error for runtime-specific validation or launch preparation."""


class RuntimeUnavailableError(RuntimeAdapterError):
    pass


class RuntimeValidationError(RuntimeAdapterError):
    pass


class RuntimeCompatibilityError(RuntimeAdapterError):
    pass


@dataclass(frozen=True, slots=True)
class RuntimeCommand:
    command: tuple[str, ...]
    cwd: Path
    environment: tuple[tuple[str, str], ...] = ()


@dataclass(frozen=True, slots=True)
class RuntimeInvocation:
    command: tuple[str, ...]
    cwd: Path | None
    environment: tuple[tuple[str, str], ...]


@dataclass(frozen=True, slots=True)
class RuntimeLifecycleBinding:
    control: ActivityLifecycleControl
    environment: tuple[tuple[str, str], ...] = ()


class RuntimeExitKind(StrEnum):
    NORMAL = "normal"
    CRASH = "crash"


@dataclass(frozen=True, slots=True)
class RuntimeExit:
    return_code: int
    kind: RuntimeExitKind


@dataclass(frozen=True, slots=True)
class RuntimeLifecycleSupport:
    """Optional lifecycle features exposed by one runtime family."""

    pause: bool = False
    checkpoint: bool = False


@dataclass(frozen=True, slots=True)
class RuntimeCompatibility:
    runtime_type: str
    device_snapshot_token: str
    available_capabilities: frozenset[str]
    required_capabilities: frozenset[str]
    optional_capabilities: frozenset[str]
    missing_required_capabilities: frozenset[str]
    effective_optional_capabilities: frozenset[str]

    @property
    def compatible(self) -> bool:
        return not self.missing_required_capabilities


@dataclass(frozen=True, slots=True)
class RuntimeLaunchPreparation:
    command: RuntimeCommand
    compatibility: RuntimeCompatibility
    lifecycle_support: RuntimeLifecycleSupport


class RuntimeLaunchAdapter(Protocol):
    """Runtime-specific behavior below Greia's common Activity services."""

    runtime_type: str
    lifecycle_support: RuntimeLifecycleSupport
    required_device_capabilities: frozenset[str]

    def validate_package(self, manifest: ActivityManifest) -> None: ...

    def command_for(self, manifest: ActivityManifest) -> RuntimeCommand: ...

    def create_lifecycle_binding(
        self,
        session_id: str,
        host_activity_data: Path,
        child_activity_data: Path,
    ) -> RuntimeLifecycleBinding: ...

    def launch(self, invocation: RuntimeInvocation) -> ProcessHandle: ...

    def collect_exit(self, process: ProcessHandle) -> RuntimeExit | None: ...

    def force_stop(self, process: ProcessHandle) -> None: ...

    def cleanup(self, process: ProcessHandle) -> None: ...


ProcessFactory = Callable[..., ProcessHandle]


@dataclass(frozen=True, slots=True)
class PythonRuntimePolicy:
    allowed_import_roots: frozenset[str]
    forbidden_import_roots: frozenset[str]
    forbidden_file_names: frozenset[str]
    forbidden_path_names: frozenset[str]
    forbidden_suffixes: frozenset[str]

    @classmethod
    def load(cls, path: Path) -> "PythonRuntimePolicy":
        try:
            with path.open("rb") as handle:
                raw = tomllib.load(handle)
        except (OSError, tomllib.TOMLDecodeError) as exc:
            raise RuntimeValidationError(f"invalid Python runtime policy {path}: {exc}") from exc
        python = raw.get("python")
        if not isinstance(python, dict):
            raise RuntimeValidationError("runtime catalogue requires a [python] table")
        allowed = _string_set(python, "allowed_import_roots")
        forbidden = _string_set(python, "forbidden_import_roots")
        overlap = allowed & forbidden
        if overlap:
            raise RuntimeValidationError(
                "Python import roots cannot be both allowed and forbidden: "
                + ", ".join(sorted(overlap))
            )
        return cls(
            allowed_import_roots=allowed,
            forbidden_import_roots=forbidden,
            forbidden_file_names=_casefolded_string_set(
                python, "forbidden_file_names"
            ),
            forbidden_path_names=_casefolded_string_set(
                python, "forbidden_path_names"
            ),
            forbidden_suffixes=_casefolded_string_set(
                python, "forbidden_suffixes"
            ),
        )


class PythonRuntimeAdapter:
    """The one curated Python runtime family below the common Activity contracts.

    Launch command: ``<python3> -P -m greia_platform.python_activity_entry
    <main.py>``. The platform entry applies the curated interpreter start-up
    policy before any Activity import, then runs the script as ``__main__``.

    Bytecode: Activities never write bytecode (``PYTHONDONTWRITEBYTECODE``).
    When the trusted launcher itself runs with the image-owned, root-owned
    read-only ``sys.pycache_prefix`` (see ``greia_platform.bytecode_cache``),
    the same prefix is handed to the Activity so platform/stdlib/built-in
    Activity modules load precompiled, hash-checked bytecode. An absent or
    untrusted prefix is simply not passed on.
    """

    runtime_type = "python"
    lifecycle_support = RuntimeLifecycleSupport()
    required_device_capabilities = frozenset()

    def __init__(
        self,
        python_executable: Path | None = None,
        *,
        policy: PythonRuntimePolicy | None = None,
        process_factory: ProcessFactory = subprocess.Popen,
        bytecode_prefix: TrustedBytecodePrefix | None = None,
    ):
        self._python_executable = python_executable
        self._policy = policy
        self._process_factory = process_factory
        self._bytecode_prefix = (
            bytecode_prefix if bytecode_prefix is not None else TrustedBytecodePrefix()
        )

    def validate_package(self, manifest: ActivityManifest) -> None:
        """Full source/import/path-safety validation of one Python package.

        One directory walk applies the path policy and lists the ``.py``
        sources; each source is read and parsed once and walked once
        (``scan_python_source``) for backend independence, the curated import
        allowlist and dynamic-import rejection. Launch-time reuse of a passed
        validation is decided above this method by ``LaunchValidationCache``.
        """
        if manifest.runtime_type != self.runtime_type:
            raise RuntimeValidationError(
                f"Python adapter cannot validate runtime {manifest.runtime_type!r}"
            )
        launch_path = manifest.launch_path
        if launch_path.suffix.casefold() != ".py" or not launch_path.is_file():
            raise RuntimeValidationError(f"Python entrypoint is not a .py file: {launch_path}")
        policy = self._policy
        if policy is not None:
            reserved_modules = {name.casefold() for name in policy.allowed_import_roots}
            try:
                top_level = tuple(manifest.root.iterdir())
            except OSError as exc:
                raise RuntimeValidationError(f"cannot inspect Python Activity package: {exc}") from exc
            for path in top_level:
                module_name = path.name.casefold() if path.is_dir() else path.stem.casefold()
                if module_name in reserved_modules:
                    raise RuntimeValidationError(
                        f"Activity package may not shadow curated module {module_name!r}: {path.name}"
                    )
        sources = _python_package_sources(manifest.root, policy)
        local_roots: dict[str, bool] = {}
        for path in sources:
            try:
                tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            except (OSError, UnicodeDecodeError, SyntaxError) as exc:
                raise RuntimeValidationError(f"cannot parse Python source {path}: {exc}") from exc

            scan = scan_python_source(path, tree)
            backend_blockers = tuple(
                finding
                for finding in scan.findings
                if finding.severity is BackendFindingSeverity.BLOCKER
            )
            if backend_blockers:
                rendered = "; ".join(
                    f"{finding.path}:{finding.line} [{finding.code}] {finding.detail}"
                    for finding in backend_blockers
                )
                raise RuntimeValidationError(
                    "Activity source must be display/input-backend independent: "
                    + rendered
                )

            for node in scan.import_and_call_nodes:
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        self._validate_import_root(
                            alias.name.split(".", 1)[0], path, manifest, local_roots
                        )
                elif isinstance(node, ast.ImportFrom):
                    if not node.level and node.module:
                        self._validate_import_root(
                            node.module.split(".", 1)[0], path, manifest, local_roots
                        )
                elif isinstance(node, ast.Call) and _is_dynamic_import_call(node):
                    raise RuntimeValidationError(
                        f"dynamic Python imports are forbidden: {path}:{node.lineno}"
                    )

    def _validate_import_root(
        self,
        root_name: str,
        path: Path,
        manifest: ActivityManifest,
        local_roots: dict[str, bool] | None = None,
    ) -> None:
        policy = self._policy
        if policy is None:
            # Unit/development fallback preserves syntax, backend independence
            # and dynamic-import rejection. Production/build composition also
            # injects the curated PythonRuntimePolicy from child-runtime.toml.
            return
        if root_name in policy.forbidden_import_roots:
            raise RuntimeValidationError(f"forbidden Python import {root_name!r} in {path}")
        local = local_roots.get(root_name) if local_roots is not None else None
        if local is None:
            local = (manifest.root / f"{root_name}.py").is_file() or (
                manifest.root / root_name
            ).is_dir()
            if local_roots is not None:
                local_roots[root_name] = local
        if local:
            return
        if root_name not in policy.allowed_import_roots:
            raise RuntimeValidationError(
                f"Python import {root_name!r} is outside the curated child runtime in {path}"
            )

    def command_for(self, manifest: ActivityManifest) -> RuntimeCommand:
        environment: list[tuple[str, str]] = [
            ("PYTHONNOUSERSITE", "1"),
            ("PYTHONDONTWRITEBYTECODE", "1"),
            SDL_SOFTWARE_FRAMEBUFFER_ENVIRONMENT,
        ]
        prefix = self._bytecode_prefix.for_current_process()
        if prefix is not None:
            environment.append((PYCACHE_PREFIX_ENVIRONMENT, str(prefix)))
        return RuntimeCommand(
            command=(
                str(self.resolve_interpreter()),
                # -P: never prepend the Activity working directory before the
                # platform entry runs; the entry sets sys.path[0] itself.
                "-P",
                "-m",
                PYTHON_ACTIVITY_ENTRY_MODULE,
                str(manifest.launch_path),
            ),
            cwd=manifest.root,
            environment=tuple(environment),
        )

    def create_lifecycle_binding(
        self,
        session_id: str,
        host_activity_data: Path,
        child_activity_data: Path,
    ) -> RuntimeLifecycleBinding:
        control = ActivityControlChannel.create_for_session(
            session_id, host_activity_data, child_activity_data
        )
        return RuntimeLifecycleBinding(
            control=control,
            environment=(
                ("GREIA_ACTIVITY_READY_PATH", str(control.child_ready_path)),
                ("GREIA_ACTIVITY_STOP_PATH", str(control.child_stop_path)),
            ),
        )

    def launch(self, invocation: RuntimeInvocation) -> ProcessHandle:
        try:
            return self._process_factory(
                list(invocation.command),
                cwd=invocation.cwd,
                env=dict(invocation.environment),
                shell=False,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                close_fds=True,
                start_new_session=True,
            )
        except OSError as exc:
            raise RuntimeAdapterError(f"Python runtime process launch failed: {exc}") from exc

    def collect_exit(self, process: ProcessHandle) -> RuntimeExit | None:
        return_code = process.poll()
        if return_code is None:
            return None
        return RuntimeExit(
            return_code=return_code,
            kind=RuntimeExitKind.NORMAL if return_code == 0 else RuntimeExitKind.CRASH,
        )

    def force_stop(self, process: ProcessHandle) -> None:
        signal_process_group(process, force=True)

    def cleanup(self, process: ProcessHandle) -> None:
        if process.poll() is None:
            self.force_stop(process)

    def resolve_interpreter(self) -> Path:
        if self._python_executable is not None:
            return self._python_executable
        configured = os.environ.get("GREIA_CHILD_PYTHON")
        if configured:
            return Path(configured)
        installed_root = Path(
            os.environ.get("GREIA_OS_ROOT", str(PRODUCTION_ROOT))
        )
        system_python = Path("/usr/bin/python3")
        from .installed_root import is_installed_root

        if is_installed_root(installed_root) and system_python.exists():
            return system_python
        return Path(sys.executable)


class RuntimeManager:
    """Single trusted runtime adapter catalogue and compatibility authority.

    Device truth comes only from the injected DeviceCapabilityService. Activity
    environment variables are never consulted. Storage, sessions, progression,
    rewards, package trust and parent policy deliberately remain outside this
    manager.
    """

    def __init__(
        self,
        adapters: Sequence[RuntimeLaunchAdapter] | Mapping[str, RuntimeLaunchAdapter],
        device_capabilities: DeviceCapabilityService,
        *,
        validation_cache: LaunchValidationCache | None = None,
    ):
        values = tuple(adapters.values()) if isinstance(adapters, Mapping) else tuple(adapters)
        by_type: dict[str, RuntimeLaunchAdapter] = {}
        for adapter in values:
            runtime_type = getattr(adapter, "runtime_type", None)
            if not _runtime_type(runtime_type):
                raise RuntimeAdapterError("runtime adapter has invalid runtime_type")
            if runtime_type in by_type:
                raise RuntimeAdapterError(f"duplicate runtime adapter: {runtime_type}")
            by_type[runtime_type] = adapter
        if not by_type:
            raise RuntimeAdapterError("at least one runtime adapter is required")
        self._adapters = by_type
        self._device_capabilities = device_capabilities
        self._validation_cache = (
            validation_cache if validation_cache is not None else LaunchValidationCache()
        )

    @property
    def runtime_types(self) -> frozenset[str]:
        return frozenset(self._adapters)

    def adapter_for(self, runtime_type: str) -> RuntimeLaunchAdapter:
        adapter = self._adapters.get(runtime_type)
        if adapter is None:
            raise RuntimeUnavailableError(f"runtime adapter is unavailable: {runtime_type}")
        return adapter

    def validate_package(self, manifest: ActivityManifest) -> None:
        self.adapter_for(manifest.runtime_type).validate_package(manifest)

    def compatibility_for(self, manifest: ActivityManifest) -> RuntimeCompatibility:
        adapter = self.adapter_for(manifest.runtime_type)
        snapshot = self._device_capabilities.snapshot()
        required = frozenset(manifest.required_capabilities) | frozenset(
            getattr(adapter, "required_device_capabilities", frozenset())
        )
        optional = frozenset(manifest.optional_capabilities)
        missing = required - snapshot.capabilities
        return RuntimeCompatibility(
            runtime_type=manifest.runtime_type,
            device_snapshot_token=snapshot.token,
            available_capabilities=snapshot.capabilities,
            required_capabilities=required,
            optional_capabilities=optional,
            missing_required_capabilities=missing,
            effective_optional_capabilities=optional & snapshot.capabilities,
        )

    def create_lifecycle_binding(
        self,
        preparation: RuntimeLaunchPreparation,
        session_id: str,
        host_activity_data: Path,
        child_activity_data: Path,
    ) -> RuntimeLifecycleBinding:
        adapter = self.adapter_for(preparation.compatibility.runtime_type)
        binding = adapter.create_lifecycle_binding(
            session_id, host_activity_data, child_activity_data
        )
        try:
            _validate_lifecycle_binding(binding, session_id)
        except RuntimeAdapterError:
            try:
                binding.control.cleanup()
            except Exception:
                pass
            raise
        return binding

    def launch(
        self, preparation: RuntimeLaunchPreparation, invocation: RuntimeInvocation
    ) -> ProcessHandle:
        adapter = self.adapter_for(preparation.compatibility.runtime_type)
        return adapter.launch(invocation)

    def collect_exit(
        self, preparation: RuntimeLaunchPreparation, process: ProcessHandle
    ) -> RuntimeExit | None:
        adapter = self.adapter_for(preparation.compatibility.runtime_type)
        return adapter.collect_exit(process)

    def force_stop(
        self, preparation: RuntimeLaunchPreparation, process: ProcessHandle
    ) -> None:
        self.adapter_for(preparation.compatibility.runtime_type).force_stop(process)

    def cleanup(
        self, preparation: RuntimeLaunchPreparation, process: ProcessHandle
    ) -> None:
        self.adapter_for(preparation.compatibility.runtime_type).cleanup(process)

    def prepare_launch(
        self,
        manifest: ActivityManifest,
        *,
        expected_device_snapshot_token: str | None = None,
        package_trust: PackageTrust | None = None,
    ) -> RuntimeLaunchPreparation:
        """Validate, check compatibility and build the runtime command.

        ``package_trust`` is the platform-assigned trust from the launch
        authority. It only decides whether ``LaunchValidationCache`` may reuse
        an earlier successful validation of an unchanged read-only built-in
        tree; ``None`` (or any non-built-in trust) always validates fully.
        """
        adapter = self.adapter_for(manifest.runtime_type)
        self._validation_cache.validate(adapter, manifest, package_trust)
        compatibility = self.compatibility_for(manifest)
        if (
            expected_device_snapshot_token is not None
            and compatibility.device_snapshot_token != expected_device_snapshot_token
        ):
            raise RuntimeCompatibilityError(
                "device capability snapshot changed after launch authority was issued"
            )
        if not compatibility.compatible:
            raise RuntimeCompatibilityError(
                "Activity/runtime requires unavailable device capabilities: "
                + ", ".join(sorted(compatibility.missing_required_capabilities))
            )
        runtime_command = adapter.command_for(manifest)
        _validate_runtime_command(runtime_command, manifest)
        return RuntimeLaunchPreparation(
            command=runtime_command,
            compatibility=compatibility,
            lifecycle_support=adapter.lifecycle_support,
        )


def _validate_lifecycle_binding(
    binding: RuntimeLifecycleBinding, expected_session_id: str
) -> None:
    if binding.control.session_id != expected_session_id:
        raise RuntimeValidationError(
            "runtime lifecycle binding changed the platform session identity"
        )
    environment = binding.environment
    if not isinstance(environment, tuple):
        raise RuntimeValidationError("runtime lifecycle environment must be immutable")
    allowed_activity_names = {
        "GREIA_ACTIVITY_READY_PATH",
        "GREIA_ACTIVITY_STOP_PATH",
    }
    seen: set[str] = set()
    for item in environment:
        if (
            not isinstance(item, tuple)
            or len(item) != 2
            or not isinstance(item[0], str)
            or not isinstance(item[1], str)
        ):
            raise RuntimeValidationError(
                "runtime lifecycle environment entries must be text pairs"
            )
        name, value = item
        if (
            not _environment_name(name)
            or "\x00" in value
            or len(value) > 8192
            or (name not in allowed_activity_names and not name.startswith("GREIA_RUNTIME_"))
        ):
            raise RuntimeValidationError(
                "runtime lifecycle environment contains an invalid entry"
            )
        if name == "GREIA_ACTIVITY_SESSION_ID":
            raise RuntimeValidationError(
                "runtime lifecycle binding may not replace platform session identity"
            )
        if name in seen:
            raise RuntimeValidationError(
                f"runtime lifecycle environment duplicates {name!r}"
            )
        seen.add(name)


def _validate_runtime_command(
    runtime_command: RuntimeCommand, manifest: ActivityManifest
) -> None:
    command = runtime_command.command
    if (
        not isinstance(command, tuple)
        or not command
        or not all(isinstance(item, str) and item and "\x00" not in item for item in command)
    ):
        raise RuntimeValidationError("runtime command must be non-empty NUL-free text")

    try:
        package_root = manifest.root.resolve(strict=True)
        working_directory = runtime_command.cwd.resolve(strict=True)
    except OSError as exc:
        raise RuntimeValidationError(f"runtime working directory is unavailable: {exc}") from exc
    if not working_directory.is_dir():
        raise RuntimeValidationError("runtime working directory is not a directory")
    if working_directory != package_root and package_root not in working_directory.parents:
        raise RuntimeValidationError("runtime working directory escapes Activity package root")

    environment = runtime_command.environment
    if not isinstance(environment, tuple):
        raise RuntimeValidationError("runtime environment must be an immutable tuple")
    seen: set[str] = set()
    for item in environment:
        if (
            not isinstance(item, tuple)
            or len(item) != 2
            or not isinstance(item[0], str)
            or not isinstance(item[1], str)
        ):
            raise RuntimeValidationError("runtime environment entries must be text pairs")
        name, value = item
        if not _environment_name(name) or "\x00" in value or len(value) > 8192:
            raise RuntimeValidationError("runtime environment contains an invalid entry")
        if name in seen:
            raise RuntimeValidationError(f"runtime environment duplicates {name!r}")
        if (
            name.startswith("GREIA_")
            or name.startswith("XDG_")
            or name in _PLATFORM_OWNED_ENVIRONMENT
        ):
            raise RuntimeValidationError(
                f"runtime environment may not override platform-owned name {name!r}"
            )
        seen.add(name)


def _environment_name(value: str) -> bool:
    if not value or len(value) > 128 or value[0].isdigit():
        return False
    return all(character.isascii() and (character.isalnum() or character == "_") for character in value)


def _string_set(container: Mapping[str, object], key: str) -> frozenset[str]:
    value = container.get(key)
    if not isinstance(value, list) or not value or not all(
        isinstance(item, str) and item.strip() for item in value
    ):
        raise RuntimeValidationError(f"python.{key} must be a non-empty string list")
    normalized = tuple(item.strip() for item in value)
    if len(set(normalized)) != len(normalized):
        raise RuntimeValidationError(f"python.{key} must not contain duplicates")
    return frozenset(normalized)


def _casefolded_string_set(
    container: Mapping[str, object], key: str
) -> frozenset[str]:
    value = container.get(key, [])
    if not isinstance(value, list) or not all(
        isinstance(item, str) and item.strip() for item in value
    ):
        raise RuntimeValidationError(f"python.{key} must be a string list")
    normalized = tuple(item.strip().casefold() for item in value)
    if len(set(normalized)) != len(normalized):
        raise RuntimeValidationError(f"python.{key} must not contain duplicates")
    return frozenset(normalized)


def _python_package_sources(
    root: Path, policy: PythonRuntimePolicy | None
) -> list[Path]:
    """Apply the package path policy and return the sorted ``*.py`` paths.

    One ``os.scandir`` walk replaces ``rglob("*")`` plus per-path
    exists/is_dir/is_file calls and a second ``rglob("*.py")``. Semantics
    match the previous pair: symlinked directories are reported but not
    descended into, ``__pycache__`` subtrees skip the name/suffix policy (but
    their sources are still parsed), broken links are ignored by the policy,
    and every entry whose name matches ``*.py`` is returned for parsing.
    """

    sources: list[Path] = []
    stack: list[tuple[str, bool]] = [(str(root), False)]
    try:
        while stack:
            directory, in_pycache = stack.pop()
            with os.scandir(directory) as entries:
                for entry in entries:
                    name = entry.name
                    entry_in_pycache = in_pycache or name == "__pycache__"
                    try:
                        is_dir = entry.is_dir()
                    except OSError:
                        is_dir = False
                    if policy is not None and not entry_in_pycache:
                        folded = name.casefold()
                        if is_dir:
                            if folded in policy.forbidden_path_names:
                                raise RuntimeValidationError(
                                    f"forbidden Python package directory: {name}"
                                )
                        else:
                            try:
                                is_file = entry.is_file()
                            except OSError:
                                is_file = False
                            if is_file:
                                if folded in policy.forbidden_file_names:
                                    raise RuntimeValidationError(
                                        f"forbidden Python package file: {name}"
                                    )
                                if Path(name).suffix.casefold() in policy.forbidden_suffixes:
                                    raise RuntimeValidationError(
                                        f"forbidden Python package suffix: {entry.path}"
                                    )
                    if name.endswith(".py"):
                        sources.append(Path(entry.path))
                    if is_dir and not entry.is_symlink():
                        stack.append((entry.path, entry_in_pycache))
    except OSError as exc:
        raise RuntimeValidationError(f"cannot inspect Python Activity package: {exc}") from exc
    sources.sort()
    return sources


def _is_dynamic_import_call(node: ast.Call) -> bool:
    function = node.func
    if isinstance(function, ast.Name):
        return function.id == "__import__"
    if isinstance(function, ast.Attribute) and isinstance(function.value, ast.Name):
        return function.value.id == "importlib" and function.attr in {"import_module", "reload"}
    return False


def _runtime_type(value: object) -> bool:
    if not isinstance(value, str) or not value or len(value) > 64:
        return False
    allowed = set("abcdefghijklmnopqrstuvwxyz0123456789._-")
    return value[0].isalnum() and value[-1].isalnum() and all(c in allowed for c in value)


from .web_runtime import WebRuntimeAdapter, WebRuntimePolicy
