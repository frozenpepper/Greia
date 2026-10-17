#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path
import sys

_SRC = Path(__file__).resolve().parents[1] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from greia_launcher.runtime_adapter import (
    PythonRuntimeAdapter,
    PythonRuntimePolicy,
    RuntimeLaunchAdapter,
    WebRuntimeAdapter,
)
from greia_platform.activities import ActivityRegistry, RuntimeCatalogue, package_digest
from greia_platform.activity_backend_policy import (
    assert_python_activity_backend_independent,
)
from greia_platform.trust import ActivitySource, PackageTrust


def validation_source(activity_root: Path, project_root: Path) -> ActivitySource:
    """Return the platform-owned source identity for standalone validation.

    Repository-bundled Activities are Greia built-ins and may legitimately carry
    trusted compatibility aliases. An arbitrary package passed to this tool stays
    developer-unsigned; merely invoking the validator must never upgrade trust.
    """

    root = activity_root.resolve(strict=True)
    bundled_root = (project_root / "activities").resolve(strict=True)
    if root.parent == bundled_root:
        return ActivitySource(bundled_root, PackageTrust.BUILT_IN, "greia-system")
    return ActivitySource(root.parent, PackageTrust.DEVELOPER_UNSIGNED, "standalone-validation")


def runtime_adapters(runtime_path: Path) -> dict[str, RuntimeLaunchAdapter]:
    """Runtime adapters configured exactly as launch composition configures them.

    The Python adapter carries the curated :class:`PythonRuntimePolicy` from
    ``child-runtime.toml``, so packaging validation rejects the same imports,
    shadowing modules and forbidden files that the launcher refuses at start
    (otherwise an Activity can validate here and still fail to launch).
    """

    adapters = (
        PythonRuntimeAdapter(policy=PythonRuntimePolicy.load(runtime_path)),
        WebRuntimeAdapter(),
    )
    return {adapter.runtime_type: adapter for adapter in adapters}


def main() -> int:
    project_root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description="Validate one curated Greia OS activity package.")
    parser.add_argument("activity", type=Path)
    parser.add_argument(
        "--runtime",
        type=Path,
        default=project_root / "runtime" / "child-runtime.toml",
    )
    args = parser.parse_args()
    root = args.activity.resolve(strict=True)
    runtime = RuntimeCatalogue.load(args.runtime)
    source = validation_source(root, project_root)
    registry = ActivityRegistry([source], runtime)
    manifest = registry.validate_registration(root, source).manifest
    # Runtime package policy: the import allow/deny roots, forbidden files and
    # suffixes, dynamic imports and backend independence (RuntimeValidationError).
    runtime_adapters(args.runtime)[manifest.runtime_type].validate_package(manifest)
    if manifest.runtime_type == "python":
        # R7 hard gate: SDL/Pygame rendering remains valid, but Activity source
        # may not select/probe/own X11, Wayland, DRM/KMS or raw host input.
        # Existing cooperative Home/controller debt is inventory-only until its
        # dedicated R7 migration wave removes it.
        assert_python_activity_backend_independent(root)
    print(f"PASS {manifest.activity_id} {manifest.version}")
    print(f"sha256 {package_digest(root)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
