#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd -- "$SCRIPT_DIR/.." && pwd)"

usage() {
  cat <<'USAGE'
Usage: populate-hardware-support-pool.sh LIVE_ROOT SUITE ARCH

Populate LIVE_ROOT/opt/greia-hardware-support with a bounded download-only
Debian firmware/microcode repository derived from isenkram firmware metadata.
The live root must already have apt lists and isenkram-cli installed.
USAGE
}

[[ $# -eq 3 ]] || { usage >&2; exit 2; }
LIVE_ROOT="$(realpath "$1")"
SUITE="$2"
ARCH="$3"
[[ -d "$LIVE_ROOT" ]] || { echo "Live root not found: $LIVE_ROOT" >&2; exit 1; }
[[ -d "$LIVE_ROOT/usr/share/isenkram" ]] || {
  echo "isenkram firmware metadata missing from live root" >&2
  exit 1
}

POOL_ROOT="$LIVE_ROOT/opt/greia-hardware-support"
POOL_DIR="$POOL_ROOT/pool"
CANDIDATE_MANIFEST="$POOL_ROOT/candidates.json"
AVAILABLE_LIST="$POOL_ROOT/available-candidates.txt"
rm -rf "$POOL_ROOT"
install -d -m 0755 "$POOL_DIR/partial"

python3 "$PROJECT_ROOT/tools/build_hardware_support_pool_manifest.py" \
  --isenkram-dir "$LIVE_ROOT/usr/share/isenkram" \
  --suite "$SUITE" \
  --architecture "$ARCH" \
  --output "$CANDIDATE_MANIFEST"

mapfile -t candidate_packages < <(
  python3 - "$CANDIDATE_MANIFEST" <<'PY'
import json
import sys
from pathlib import Path
manifest = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
for package in manifest["candidate_packages"]:
    print(package)
PY
)

available_packages=()
for package in "${candidate_packages[@]}"; do
  if chroot "$LIVE_ROOT" apt-cache show --no-all-versions "$package" >/dev/null 2>&1; then
    available_packages+=("$package")
  fi
done
printf '%s\n' "${available_packages[@]}" > "$AVAILABLE_LIST"

before_packages="$(chroot "$LIVE_ROOT" dpkg-query -W -f='${Package}\t${Version}\n' | LC_ALL=C sort | sha256sum | awk '{print $1}')"
if (( ${#available_packages[@]} > 0 )); then
  chroot "$LIVE_ROOT" /usr/bin/env DEBIAN_FRONTEND=noninteractive \
    apt-get \
      -o Acquire::Retries=3 \
      -o Acquire::http::Timeout=20 \
      -o Acquire::https::Timeout=20 \
      -o Dir::Cache::archives=/opt/greia-hardware-support/pool \
      --download-only install -y --no-install-recommends \
      "${available_packages[@]}"
fi
after_packages="$(chroot "$LIVE_ROOT" dpkg-query -W -f='${Package}\t${Version}\n' | LC_ALL=C sort | sha256sum | awk '{print $1}')"
[[ "$before_packages" == "$after_packages" ]] || {
  echo "Hardware-support pool population changed the live installed package set; refusing build." >&2
  exit 1
}

rm -rf "$POOL_DIR/partial"
python3 "$PROJECT_ROOT/tools/finalize_hardware_support_pool.py" \
  --pool-root "$POOL_ROOT" \
  --candidate-manifest "$CANDIDATE_MANIFEST"

chown -R root:root "$POOL_ROOT"
find "$POOL_ROOT" -type d -exec chmod 0755 '{}' +
find "$POOL_ROOT" -type f -exec chmod 0644 '{}' +

echo "Hardware support pool: $POOL_ROOT"
