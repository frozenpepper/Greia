from __future__ import annotations

import ast
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Iterable


class ActivityBackendPolicyError(ValueError):
    """Raised when Activity source depends on host display/input backends."""


class BackendFindingSeverity(StrEnum):
    BLOCKER = "blocker"
    MIGRATION = "migration"


@dataclass(frozen=True, slots=True)
class BackendPolicyFinding:
    """One structured Activity/backend-independence finding.

    BLOCKER findings are forbidden immediately. MIGRATION findings identify
    currently accepted compatibility debt that R7 must remove before closure.
    Keeping the two classes explicit lets Greia stop *new* backend coupling
    without pretending the existing cooperative Home/controller paths are
    already migrated.
    """

    path: Path
    line: int
    severity: BackendFindingSeverity
    code: str
    detail: str


_FORBIDDEN_IMPORT_ROOTS = frozenset(
    {
        "evdev",
        "libinput",
        "pywayland",
        "xcffib",
        "xlib",
    }
)
_FORBIDDEN_ENVIRONMENT_KEYS = frozenset(
    {
        "DISPLAY",
        "SDL_VIDEODRIVER",
        "WAYLAND_DISPLAY",
        "XAUTHORITY",
    }
)
_FORBIDDEN_DEVICE_PREFIXES = ("/dev/input", "/dev/dri")
_FORBIDDEN_COMMANDS = frozenset({"xinput", "xrandr", "xdotool"})
_FORBIDDEN_NATIVE_LIBRARIES = frozenset(
    {
        "drm",
        "gbm",
        "libdrm",
        "libgbm",
        "libwayland-client",
        "libx11",
        "wayland-client",
        "x11",
    }
)
_MIGRATION_CHROME_SYMBOLS = frozenset(
    {
        "ActivitySystemChromeLayout",
        "draw_system_chrome_overlay",
        "is_home_clicked",
    }
)
_MIGRATION_CHROME_MODULES = frozenset(
    {
        "greia_platform.activity_ui",
        "greia_platform.pygame_ui",
        "greia_platform.system_chrome",
    }
)


def scan_python_activity_backend_policy(activity_root: Path) -> tuple[BackendPolicyFinding, ...]:
    """Inspect Python Activity source without executing it.

    The scanner is intentionally AST-based. Ordinary SDL/Pygame rendering,
    display creation, event polling, caching and dirty-render techniques are
    valid and must not be mistaken for X11/Wayland coupling.
    """

    root = activity_root.resolve()
    findings: list[BackendPolicyFinding] = []
    for path in sorted(root.rglob("*.py")):
        if "__pycache__" in path.parts:
            continue
        try:
            source = path.read_text(encoding="utf-8")
            tree = ast.parse(source, filename=str(path))
        except (OSError, UnicodeDecodeError, SyntaxError) as exc:
            raise ActivityBackendPolicyError(
                f"cannot inspect Activity backend policy for {path}: {exc}"
            ) from exc
        findings.extend(_scan_tree(path, tree))
    return tuple(
        sorted(
            findings,
            key=lambda item: (
                str(item.path),
                item.line,
                item.severity.value,
                item.code,
                item.detail,
            ),
        )
    )


def assert_python_activity_backend_independent(activity_root: Path) -> None:
    """Fail when Activity source contains forbidden backend authority."""

    blockers = tuple(
        finding
        for finding in scan_python_activity_backend_policy(activity_root)
        if finding.severity is BackendFindingSeverity.BLOCKER
    )
    if not blockers:
        return
    rendered = "; ".join(
        f"{finding.path}:{finding.line} [{finding.code}] {finding.detail}"
        for finding in blockers
    )
    raise ActivityBackendPolicyError(
        "Activity source must be display/input-backend independent: " + rendered
    )


def migration_findings(activity_root: Path) -> tuple[BackendPolicyFinding, ...]:
    """Return R7 compatibility debt without weakening the hard blocker gate."""

    return tuple(
        finding
        for finding in scan_python_activity_backend_policy(activity_root)
        if finding.severity is BackendFindingSeverity.MIGRATION
    )


def _scan_tree(path: Path, tree: ast.AST) -> Iterable[BackendPolicyFinding]:
    findings: list[BackendPolicyFinding] = []
    aliases = _import_aliases(tree)
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                root = alias.name.split(".", 1)[0].casefold()
                if root in _FORBIDDEN_IMPORT_ROOTS:
                    findings.append(
                        _finding(
                            path,
                            node,
                            BackendFindingSeverity.BLOCKER,
                            "backend-import",
                            f"direct backend/device import {alias.name!r} is platform-owned",
                        )
                    )
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            root = module.split(".", 1)[0].casefold()
            if not node.level and root in _FORBIDDEN_IMPORT_ROOTS:
                findings.append(
                    _finding(
                        path,
                        node,
                        BackendFindingSeverity.BLOCKER,
                        "backend-import",
                        f"direct backend/device import {module!r} is platform-owned",
                    )
                )
            if module in _MIGRATION_CHROME_MODULES:
                for alias in node.names:
                    if alias.name in _MIGRATION_CHROME_SYMBOLS:
                        findings.append(
                            _finding(
                                path,
                                node,
                                BackendFindingSeverity.MIGRATION,
                                "activity-system-chrome",
                                f"Activity-side {alias.name} must move to trusted R7 chrome",
                            )
                        )
            if module == "pygame":
                for alias in node.names:
                    if alias.name == "joystick":
                        findings.append(
                            _finding(
                                path,
                                node,
                                BackendFindingSeverity.MIGRATION,
                                "raw-controller",
                                "direct pygame.joystick ownership must migrate to Greia input authority",
                            )
                        )
        elif isinstance(node, ast.Subscript):
            key = _environment_subscript_key(node, aliases)
            if key in _FORBIDDEN_ENVIRONMENT_KEYS:
                findings.append(
                    _finding(
                        path,
                        node,
                        BackendFindingSeverity.BLOCKER,
                        "backend-environment",
                        f"Activity source must not read or set platform-owned {key}",
                    )
                )
        elif isinstance(node, ast.Call):
            env_key = _environment_call_key(node, aliases)
            if env_key in _FORBIDDEN_ENVIRONMENT_KEYS:
                findings.append(
                    _finding(
                        path,
                        node,
                        BackendFindingSeverity.BLOCKER,
                        "backend-environment",
                        f"Activity source must not read or set platform-owned {env_key}",
                    )
                )
            command = _static_process_command(node, aliases)
            if command in _FORBIDDEN_COMMANDS:
                findings.append(
                    _finding(
                        path,
                        node,
                        BackendFindingSeverity.BLOCKER,
                        "backend-command",
                        f"host display/input command {command!r} is platform-owned",
                    )
                )
            library = _static_native_library_probe(node, aliases)
            if library is not None and library.casefold() in _FORBIDDEN_NATIVE_LIBRARIES:
                findings.append(
                    _finding(
                        path,
                        node,
                        BackendFindingSeverity.BLOCKER,
                        "backend-native-library",
                        f"native backend library {library!r} is platform-owned",
                    )
                )
        elif isinstance(node, ast.Constant) and isinstance(node.value, str):
            literal = node.value
            for prefix in _FORBIDDEN_DEVICE_PREFIXES:
                if literal == prefix or literal.startswith(prefix + "/"):
                    findings.append(
                        _finding(
                            path,
                            node,
                            BackendFindingSeverity.BLOCKER,
                            "raw-device-path",
                            f"Activity source must not address platform-owned device path {prefix}",
                        )
                    )
        elif isinstance(node, (ast.Attribute, ast.Name)) and _resolved_chain(
            node, aliases
        )[:2] == ("pygame", "joystick"):
            findings.append(
                _finding(
                    path,
                    node,
                    BackendFindingSeverity.MIGRATION,
                    "raw-controller",
                    "direct pygame.joystick ownership must migrate to Greia input authority",
                )
            )
    return _deduplicate(findings)


def _import_aliases(tree: ast.AST) -> dict[str, tuple[str, ...]]:
    """Resolve simple import aliases so policy cannot be bypassed by renaming imports."""

    aliases: dict[str, tuple[str, ...]] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                target = tuple(alias.name.split("."))
                if alias.asname:
                    aliases[alias.asname] = target
                else:
                    root = target[0]
                    aliases[root] = (root,)
        elif isinstance(node, ast.ImportFrom) and not node.level and node.module:
            module = tuple(node.module.split("."))
            for alias in node.names:
                if alias.name == "*":
                    continue
                local = alias.asname or alias.name
                aliases[local] = module + (alias.name,)
    return aliases


def _environment_subscript_key(
    node: ast.Subscript,
    aliases: dict[str, tuple[str, ...]],
) -> str | None:
    if _resolved_chain(node.value, aliases) != ("os", "environ"):
        return None
    return _constant_text(node.slice)


def _environment_call_key(
    node: ast.Call,
    aliases: dict[str, tuple[str, ...]],
) -> str | None:
    chain = _resolved_chain(node.func, aliases)
    if chain in {
        ("os", "getenv"),
        ("os", "putenv"),
        ("os", "unsetenv"),
        ("os", "environ", "get"),
        ("os", "environ", "pop"),
        ("os", "environ", "setdefault"),
    }:
        return _first_text_argument(node)
    if chain == ("os", "environ", "update") and node.args:
        mapping = node.args[0]
        if isinstance(mapping, ast.Dict):
            for key in mapping.keys:
                text = _constant_text(key)
                if text in _FORBIDDEN_ENVIRONMENT_KEYS:
                    return text
    return None


def _static_process_command(
    node: ast.Call,
    aliases: dict[str, tuple[str, ...]],
) -> str | None:
    chain = _resolved_chain(node.func, aliases)
    if chain not in {
        ("os", "system"),
        ("subprocess", "Popen"),
        ("subprocess", "call"),
        ("subprocess", "check_call"),
        ("subprocess", "check_output"),
        ("subprocess", "run"),
    }:
        return None
    if not node.args:
        return None
    command = node.args[0]
    if isinstance(command, (ast.List, ast.Tuple)) and command.elts:
        text = _constant_text(command.elts[0])
    else:
        text = _constant_text(command)
    if not text:
        return None
    return Path(text.split()[0]).name.casefold()


def _static_native_library_probe(
    node: ast.Call,
    aliases: dict[str, tuple[str, ...]],
) -> str | None:
    chain = _resolved_chain(node.func, aliases)
    if chain not in {
        ("ctypes", "CDLL"),
        ("ctypes", "PyDLL"),
        ("ctypes", "cdll", "LoadLibrary"),
        ("ctypes", "util", "find_library"),
    }:
        return None
    value = _first_text_argument(node)
    if value is None:
        return None
    name = Path(value).name.casefold()
    if name.startswith("lib") and ".so" in name:
        name = name.split(".so", 1)[0]
    return name


def _resolved_chain(
    node: ast.AST,
    aliases: dict[str, tuple[str, ...]],
) -> tuple[str, ...]:
    chain = _attribute_chain(node)
    if not chain:
        return ()
    target = aliases.get(chain[0])
    if target is None:
        return chain
    return target + chain[1:]


def _attribute_chain(node: ast.AST) -> tuple[str, ...]:
    parts: list[str] = []
    current = node
    while isinstance(current, ast.Attribute):
        parts.append(current.attr)
        current = current.value
    if isinstance(current, ast.Name):
        parts.append(current.id)
        return tuple(reversed(parts))
    return ()


def _first_text_argument(node: ast.Call) -> str | None:
    if not node.args:
        return None
    return _constant_text(node.args[0])


def _constant_text(node: ast.AST | None) -> str | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    return None


def _finding(
    path: Path,
    node: ast.AST,
    severity: BackendFindingSeverity,
    code: str,
    detail: str,
) -> BackendPolicyFinding:
    return BackendPolicyFinding(
        path=path,
        line=max(1, int(getattr(node, "lineno", 1))),
        severity=severity,
        code=code,
        detail=detail,
    )


def _deduplicate(findings: Iterable[BackendPolicyFinding]) -> tuple[BackendPolicyFinding, ...]:
    unique: dict[tuple[Path, int, BackendFindingSeverity, str, str], BackendPolicyFinding] = {}
    for finding in findings:
        key = (
            finding.path,
            finding.line,
            finding.severity,
            finding.code,
            finding.detail,
        )
        unique[key] = finding
    return tuple(unique.values())


__all__ = [
    "ActivityBackendPolicyError",
    "BackendFindingSeverity",
    "BackendPolicyFinding",
    "assert_python_activity_backend_independent",
    "migration_findings",
    "scan_python_activity_backend_policy",
]
