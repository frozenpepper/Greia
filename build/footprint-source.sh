#!/usr/bin/env bash
set -euo pipefail
root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"

echo "Source archive-relevant footprint:"
if git -C "$root" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  python3 - "$root" <<'PY'
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

root = Path(sys.argv[1])
tracked = subprocess.check_output(
    ["git", "-C", str(root), "ls-files", "-z"],
).split(b"\0")

total = 0
for raw in tracked:
    if not raw:
        continue
    path = root / raw.decode("utf-8", errors="surrogateescape")
    try:
        total += path.stat().st_size
    except FileNotFoundError:
        # A tracked path can be transiently absent only in a dirty checkout;
        # verification elsewhere will report that state. Footprint reporting
        # should describe the files that are actually present.
        continue

units = ("B", "KiB", "MiB", "GiB", "TiB")
value = float(total)
unit = units[0]
for unit in units:
    if value < 1024 or unit == units[-1]:
        break
    value /= 1024
print(f"{value:.1f} {unit}\ttracked source files ({total} bytes)")
PY
else
  # Exported source trees normally contain no ignored build/evidence state.
  # Retain a useful fallback when .git metadata is deliberately absent.
  du -sh "$root"
fi

echo
echo "Runtime payload candidates:"
du -sh "$root/src" "$root/activities" "$root/runtime" "$root/assets/icons" "$root/assets/catalog/core_icons_v1.toml" "$root/build/overlay"
