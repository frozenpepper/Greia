#!/usr/bin/env bash
# Session 03 release-root composition adapter.
#
# Owns only the lifecycle around the existing shared composition engine:
#   target root -> bounded teardown -> live-installer root -> hardware-support
#   pool while the live chroot environment is still mounted -> bounded teardown.
#
# No package/composition logic is duplicated here. This script is an
# implementation detail of tools/greia_release.py.
set -Eeuo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd -- "$SCRIPT_DIR/.." && pwd)"
# shellcheck source=lib/safe-cleanup.sh
source "$SCRIPT_DIR/lib/safe-cleanup.sh"
# shellcheck source=lib/apt-cache.sh
source "$SCRIPT_DIR/lib/apt-cache.sh"
# shellcheck source=lib/compose.sh
source "$SCRIPT_DIR/lib/compose.sh"

usage() {
  cat <<'USAGE'
Usage: sudo build/compose-release-profile.sh PROFILE TARGET_ROOT LIVE_ROOT

Compose one Greia release profile through the shared target/live-installer
engine and populate LIVE_ROOT/opt/greia-hardware-support while the live chroot
runtime is still available. The caller owns payload/bundle packaging.
USAGE
}

[[ $# -eq 3 ]] || { usage >&2; exit 2; }
[[ ${EUID:-$(id -u)} -eq 0 ]] || { echo "Run as root." >&2; exit 1; }

PROFILE_INPUT="$1"
TARGET_ROOT="$2"
LIVE_ROOT="$3"

mkdir -p "$TARGET_ROOT" "$LIVE_ROOT"
TARGET_ROOT="$(realpath "$TARGET_ROOT")"
LIVE_ROOT="$(realpath "$LIVE_ROOT")"
[[ "$TARGET_ROOT" != "$LIVE_ROOT" ]] || {
  echo "Target and live roots must be different directories." >&2
  exit 1
}

# Release orchestration always starts from empty scratch roots. Refuse stale
# contents rather than merging a previous failed build into a new release.
[[ -z "$(find "$TARGET_ROOT" -mindepth 1 -maxdepth 1 -print -quit)" ]] || {
  echo "Target release root is not empty: $TARGET_ROOT" >&2
  exit 1
}
[[ -z "$(find "$LIVE_ROOT" -mindepth 1 -maxdepth 1 -print -quit)" ]] || {
  echo "Live release root is not empty: $LIVE_ROOT" >&2
  exit 1
}

MOUNTS=()
cleanup() {
  local original_status=$?
  trap - EXIT INT TERM
  set +e
  safe_unmount_paths "${MOUNTS[@]}"
  local cleanup_status=$?
  if (( cleanup_status != 0 )); then
    echo "Release-root composition cleanup left a live mount; preserving scratch roots." >&2
    if (( original_status == 0 )); then
      exit 1
    fi
  fi
  exit "$original_status"
}
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

# Target and live roles share compose_root, but target mounts are not useful
# while composing the live root. Tear them down before the second role instead
# of keeping two chroot environments live simultaneously.
compose_root \
  --profile "$PROFILE_INPUT" \
  --role target \
  --root "$TARGET_ROOT" \
  --project-root "$PROJECT_ROOT"

safe_unmount_paths "${MOUNTS[@]}"
MOUNTS=()

compose_root \
  --profile "$PROFILE_INPUT" \
  --role live-installer \
  --root "$LIVE_ROOT" \
  --project-root "$PROJECT_ROOT"

TARGET_DPKG_STATUS="$TARGET_ROOT/var/lib/dpkg/status"
[[ -r "$TARGET_DPKG_STATUS" ]] || {
  echo "Composed target dpkg status is missing: $TARGET_DPKG_STATUS" >&2
  exit 1
}

# The pool downloader uses /var/cache/greia-pool inside the live chroot.
# Keep the cache on the build host exactly like the installer-image builder.
LIVE_POOL_CACHE_MOUNT="$(mount_pool_cache "$LIVE_ROOT")"
MOUNTS+=("$LIVE_POOL_CACHE_MOUNT")

# compose_resolve_profile for the live role has already populated SUITE/ARCH.
POOL_CACHE_IN_CHROOT="/var/cache/greia-pool" \
POOL_CACHE_HOST="$GREIA_POOL_CACHE" \
  "$SCRIPT_DIR/populate-hardware-support-pool.sh" \
    "$LIVE_ROOT" "$SUITE" "$ARCH" "$TARGET_DPKG_STATUS"

[[ -r "$LIVE_ROOT/opt/greia-hardware-support/manifest.json" ]] || {
  echo "Hardware-support pool finalization did not produce manifest.json." >&2
  exit 1
}
