#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd -- "$SCRIPT_DIR/.." && pwd)"
# shellcheck source=../build/lib/safe-cleanup.sh
source "$PROJECT_ROOT/build/lib/safe-cleanup.sh"

[[ ${EUID:-$(id -u)} -eq 0 ]] || {
  echo "Run as root." >&2
  exit 1
}

required=(losetup parted partx blockdev udevadm truncate bash)
for command_name in "${required[@]}"; do
  command -v "$command_name" >/dev/null || {
    echo "Missing dependency: $command_name" >&2
    exit 1
  }
done

WORK="$(mktemp -d -p "${TMPDIR:-/tmp}" greia-loop-deleted-backing.XXXXXX)"
IMG="$WORK/probe.img"
READY="$WORK/holder.ready"
LOOP=""
HOLDER_PID=""

cleanup() {
  local original_status=$?
  trap - EXIT INT TERM
  set +e
  local cleanup_failed=0

  if [[ -n "$HOLDER_PID" ]] && kill -0 "$HOLDER_PID" 2>/dev/null; then
    kill "$HOLDER_PID" 2>/dev/null || true
    wait "$HOLDER_PID" 2>/dev/null || true
  fi

  safe_detach_loop "$LOOP" || cleanup_failed=1

  if (( cleanup_failed == 0 )); then
    rm -rf "$WORK"
  fi

  safe_cleanup_exit "$original_status" "$cleanup_failed"     "Deleted-backing loop fixture cleanup was incomplete; preserving evidence."
}
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

truncate -s 64M "$IMG"
parted -s "$IMG" mklabel msdos
parted -s "$IMG" mkpart primary ext4 1MiB 100%

LOOP="$(losetup --find --show --partscan "$IMG")"
PART="${LOOP}p1"

for _ in {1..30}; do
  [[ -b "$PART" ]] && break
  sleep 0.1
done
[[ -b "$PART" ]] || {
  echo "Fixture partition did not appear: $PART" >&2
  exit 1
}

# Hold the partition open long enough for LOOP_CLR_FD to hit the extra-opener
# path. The holder releases automatically; the cleanup helper must then delete
# partition bookkeeping after detach has been requested and observe the parent
# association disappear.
bash -c '
set -Eeuo pipefail
exec 9<"$1"
: > "$2"
sleep 2
' _ "$PART" "$READY" &
HOLDER_PID=$!

for _ in {1..30}; do
  [[ -e "$READY" ]] && break
  sleep 0.1
done
[[ -e "$READY" ]] || {
  echo "Fixture partition holder did not become ready." >&2
  exit 1
}

# Remove the pathname while the loop driver still owns the inode. sysfs should
# now report a deleted backing file, matching the field-failure shape.
rm -f "$IMG"

BACKING_BEFORE="$(safe_loop_backing_file "$LOOP" 2>/dev/null || true)"
[[ "$BACKING_BEFORE" == *"(deleted)"* ]] || {
  echo "Fixture did not reach deleted-backing state: $BACKING_BEFORE" >&2
  exit 1
}

safe_detach_loop "$LOOP"

wait "$HOLDER_PID"
HOLDER_PID=""

LOOP_NAME="${LOOP#/dev/}"
if safe_loop_is_associated "$LOOP"; then
  echo "Fixture loop remains associated after cleanup: $LOOP" >&2
  exit 1
fi
if compgen -G "/sys/class/block/${LOOP_NAME}p[0-9]*" >/dev/null; then
  echo "Fixture partition children remain after cleanup: $LOOP" >&2
  exit 1
fi

echo "DELETED_BACKING_LOOP_CLEANUP=PASS"
echo "loop=$LOOP"
echo "backing_before=$BACKING_BEFORE"

LOOP=""
