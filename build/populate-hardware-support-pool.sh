#!/usr/bin/env bash
set -Eeuo pipefail
# Privileged builders must never leave root-owned bytecode in the source
# tree: every Python invocation below inherits this (cf. greia_release.py).
export PYTHONDONTWRITEBYTECODE=1

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd -- "$SCRIPT_DIR/.." && pwd)"

usage() {
  cat <<'USAGE'
Usage: populate-hardware-support-pool.sh LIVE_ROOT SUITE ARCH [TARGET_DPKG_STATUS]

Populate LIVE_ROOT/opt/greia-hardware-support with a bounded download-only
Debian firmware/microcode repository derived from isenkram firmware metadata.
Dependency resolution uses the final target image's dpkg status, not the richer
live installer state, so the frozen repository is sufficient offline.

When TARGET_DPKG_STATUS is omitted, the canonical installer-build layout is
used and var/lib/dpkg/status is read directly from the exact target squashfs
beside LIVE_ROOT.
USAGE
}

[[ $# -ge 3 && $# -le 4 ]] || { usage >&2; exit 2; }
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
# Persistent host pool cache: the installer builder bind-mounts the host cache
# at $POOL_CACHE_IN_CHROOT for the chroot's lifetime so repeated builds reuse
# already-downloaded .debs. POOL_CACHE_HOST defaults to the live-joined path so
# a standalone (unmounted) invocation still reaches the same pool result.
POOL_CACHE_IN_CHROOT="${POOL_CACHE_IN_CHROOT:-/var/cache/greia-pool}"
POOL_CACHE_HOST="${POOL_CACHE_HOST:-$LIVE_ROOT$POOL_CACHE_IN_CHROOT}"
CANDIDATE_MANIFEST="$POOL_ROOT/candidates.json"
AVAILABLE_LIST="$POOL_ROOT/available-candidates.txt"
TARGET_STATUS_IN_CHROOT="$LIVE_ROOT/tmp/greia-target-dpkg-status"
rm -rf "$POOL_ROOT"
install -d -m 0755 "$POOL_DIR/partial"
install -d -m 0755 "$POOL_CACHE_HOST/partial"

if [[ $# -eq 4 ]]; then
  TARGET_DPKG_STATUS="$(realpath "$4")"
  [[ -r "$TARGET_DPKG_STATUS" ]] || { echo "Target dpkg status not found: $TARGET_DPKG_STATUS" >&2; exit 1; }
  install -m 0644 "$TARGET_DPKG_STATUS" "$TARGET_STATUS_IN_CHROOT"
else
  TARGET_PAYLOAD="$(dirname "$LIVE_ROOT")/greia-rootfs.squashfs"
  [[ -r "$TARGET_PAYLOAD" ]] || {
    echo "Canonical target payload not found beside live root: $TARGET_PAYLOAD" >&2
    exit 1
  }
  command -v unsquashfs >/dev/null || {
    echo "unsquashfs is required to inspect the exact target package state" >&2
    exit 1
  }
  unsquashfs -cat "$TARGET_PAYLOAD" var/lib/dpkg/status > "$TARGET_STATUS_IN_CHROOT"
  [[ -s "$TARGET_STATUS_IN_CHROOT" ]] || {
    echo "Could not extract target dpkg status from target payload" >&2
    exit 1
  }
  chmod 0644 "$TARGET_STATUS_IN_CHROOT"
fi

cleanup() {
  rm -f "$TARGET_STATUS_IN_CHROOT"
}
trap cleanup EXIT

# This operation is a standalone APT consumer. Callers are allowed to have
# already applied image-footprint hygiene, which deliberately removes
# /var/lib/apt/lists. Refresh repository metadata here so candidate discovery
# and dependency resolution never depend on a caller's incidental APT state.
APT_NETWORK_OPTIONS=(
  -o Acquire::Retries=3
  -o Acquire::http::Timeout=20
  -o Acquire::https::Timeout=20
)
chroot "$LIVE_ROOT" /usr/bin/env DEBIAN_FRONTEND=noninteractive \
  apt-get "${APT_NETWORK_OPTIONS[@]}" update

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
for package in "${available_packages[@]}"; do
  # Resolve candidates independently. Debian firmware providers can be
  # alternatives or conflict with one another; requiring all candidates in one
  # solver transaction would make the broad media pool less compatible. The
  # persistent pool cache is shared, so dependency .debs accumulate into one
  # local repository instead of being re-fetched on every build.
  chroot "$LIVE_ROOT" /usr/bin/env DEBIAN_FRONTEND=noninteractive \
    apt-get \
      "${APT_NETWORK_OPTIONS[@]}" \
      -o Dir::State::status=/tmp/greia-target-dpkg-status \
      -o Dir::Cache::archives="$POOL_CACHE_IN_CHROOT" \
      --download-only install -y --no-install-recommends \
      "$package"
done
# The broad-firmware cover is installed into the live installer root, not the
# final target. Re-resolve the same candidates against the live root's own
# dpkg state so dependencies that the target image already satisfies but the
# live installer still needs (for example dosfstools) are present in the pool.
for package in "${available_packages[@]}"; do
  chroot "$LIVE_ROOT" /usr/bin/env DEBIAN_FRONTEND=noninteractive \
    apt-get \
      "${APT_NETWORK_OPTIONS[@]}" \
      -o Dir::Cache::archives="$POOL_CACHE_IN_CHROOT" \
      --download-only install -y --no-install-recommends \
      "$package"
done
after_packages="$(chroot "$LIVE_ROOT" dpkg-query -W -f='${Package}\t${Version}\n' | LC_ALL=C sort | sha256sum | awk '{print $1}')"
[[ "$before_packages" == "$after_packages" ]] || {
  echo "Hardware-support pool population changed the live installed package set; refusing build." >&2
  exit 1
}

# Keep only currently-resolvable .debs in the persistent cache, then stage a
# fresh pool from it. Copying (not moving) preserves the host cache for the
# next build. POOL_CACHE_HOST defaults to the live-joined cache path, so a
# standalone invocation without the installer builder's bind-mount stages the
# same pool result from the chroot-local cache.
chroot "$LIVE_ROOT" apt-get -o Dir::Cache::archives="$POOL_CACHE_IN_CHROOT" autoclean
install -d -m 0755 "$POOL_DIR"
shopt -s nullglob
pool_cache_debs=("$POOL_CACHE_HOST"/*.deb)
shopt -u nullglob
(( ${#pool_cache_debs[@]} > 0 )) || {
  echo "Pool cache holds no .debs after download: $POOL_CACHE_HOST" >&2
  exit 1
}
cp -- "${pool_cache_debs[@]}" "$POOL_DIR/"

rm -rf "$POOL_DIR/partial"
python3 "$PROJECT_ROOT/tools/finalize_hardware_support_pool.py" \
  --pool-root "$POOL_ROOT" \
  --candidate-manifest "$CANDIDATE_MANIFEST"

# The candidate manifest and availability list are working intermediates for
# candidate discovery above. Finalization has consumed the manifest, and the
# release archive enforces a fail-closed top-level allowlist
# (manifest.json, Packages, Packages.gz, pool/), so remove the intermediates
# here instead of widening the archive check.
rm -f "$CANDIDATE_MANIFEST" "$AVAILABLE_LIST"

chown -R root:root "$POOL_ROOT"
find "$POOL_ROOT" -type d -exec chmod 0755 '{}' +
find "$POOL_ROOT" -type f -exec chmod 0644 '{}' +

# Restore image hygiene on success. The pool is now self-contained and later
# live-firmware installation uses its own verified local APT source, so remote
# package indexes are no longer required in the composed live root.
rm -rf "$LIVE_ROOT/var/lib/apt/lists/"*

echo "Hardware support pool: $POOL_ROOT"
