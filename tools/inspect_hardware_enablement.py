#!/usr/bin/env python3
"""Inspect Greia hardware discovery and support recommendations as bounded JSON.

This tool is observational only. It never installs packages or changes hardware
state. Automatic-package output is suppressed unless the resolver reports a
complete inventory/resolution pass.
"""

from __future__ import annotations

import argparse
import json
import platform
from pathlib import Path

from greia_platform.hardware_enablement import (
    CompositeHardwareSupportResolver,
    IsenkramHardwareSupportResolver,
    LinuxSysfsHardwareInventory,
    X86MicrocodeResolver,
)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sysfs-devices", type=Path, default=Path("/sys/devices"))
    parser.add_argument("--inventory-only", action="store_true")
    parser.add_argument("--pretty", action="store_true")
    return parser


def main() -> int:
    args = _parser().parse_args()
    inventory = LinuxSysfsHardwareInventory(args.sysfs_devices).snapshot()

    payload: dict[str, object] = {
        "schema_version": 1,
        "machine": platform.machine() or "unknown",
        "inventory": {
            "token": inventory.token,
            "device_count": len(inventory.devices),
            "truncated": inventory.truncated,
            "scan_errors": inventory.scan_errors,
            "devices": [
                {
                    "sysfs_path": device.sysfs_path,
                    "subsystem": device.subsystem,
                    "modalias": device.modalias,
                    "driver": device.driver,
                }
                for device in inventory.devices
            ],
        },
    }

    if not args.inventory_only:
        resolvers = [IsenkramHardwareSupportResolver()]
        if platform.machine().lower() in {"i386", "i486", "i586", "i686", "x86_64", "amd64"}:
            resolvers.append(X86MicrocodeResolver())
        plan = CompositeHardwareSupportResolver(tuple(resolvers)).resolve(inventory)
        payload["support"] = {
            "complete": plan.complete,
            # Fail closed: recommendations remain visible for diagnosis, but
            # automatic output is empty until the whole automatic plan is complete.
            "automatic_packages": list(plan.automatic_packages if plan.complete else ()),
            "advisory_packages": list(plan.advisory_packages),
            "diagnostics": list(plan.diagnostics),
            "recommendations": [
                {
                    "package": item.package,
                    "kind": item.kind.value,
                    "disposition": item.disposition.value,
                    "source": item.source,
                }
                for item in plan.recommendations
            ],
        }

    print(json.dumps(payload, sort_keys=True, indent=2 if args.pretty else None))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
