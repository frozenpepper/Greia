#!/usr/bin/env bash
set -euo pipefail
root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
echo "Source archive-relevant footprint:"
du -sh "$root"
echo
echo "Runtime payload candidates:"
du -sh "$root/src" "$root/activities" "$root/runtime" "$root/assets/icons" "$root/assets/catalog/core_icons_v1.toml" "$root/build/overlay"
