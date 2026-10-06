#!/usr/bin/env bash
# Shared destructive-build cleanup helpers. Source from bash with set -Eeuo.

safe_udev_settle() {
  udevadm settle --timeout=5 >/dev/null 2>&1 || true
}

safe_unmount_path_tree() {
  local path="$1"
  [[ -n "$path" ]] || return 0

  # findmnt --target resolves an arbitrary non-mount path to the filesystem
  # containing it (usually /). Never recurse from that containing filesystem:
  # callers frequently invoke cleanup after an explicit successful umount.
  mountpoint -q -- "$path" || return 0

  local targets=()
  local index target attempt
  mapfile -t targets < <(findmnt -rn -R -o TARGET --target "$path" 2>/dev/null || true)
  for (( index=${#targets[@]}-1; index>=0; index-- )); do
    target="${targets[$index]}"
    [[ -n "$target" ]] || continue
    case "$target" in
      "$path"|"$path"/*) ;;
      *) echo "ERROR: refusing cleanup target outside requested mount tree: $target" >&2; return 1 ;;
    esac
    for attempt in {1..20}; do
      mountpoint -q -- "$target" || break
      sync
      umount -- "$target" 2>/dev/null || true
      mountpoint -q -- "$target" || break
      sleep 0.1
    done
    if mountpoint -q -- "$target"; then
      echo "ERROR: mount remains busy after bounded normal-unmount retries: $target" >&2
      return 1
    fi
  done
  safe_udev_settle
}

safe_unmount_paths() {
  local paths=("$@")
  local failed=0
  local index path
  for (( index=${#paths[@]}-1; index>=0; index-- )); do
    path="${paths[$index]}"
    [[ -n "$path" ]] || continue
    safe_unmount_path_tree "$path" || failed=1
  done
  return "$failed"
}

safe_loop_partition_children_present() {
  local loop_device="${1:-}"
  [[ -n "$loop_device" ]] || return 1
  local loop_name="${loop_device#/dev/}"
  compgen -G "/sys/class/block/${loop_name}p[0-9]*" >/dev/null
}

safe_loop_backing_file() {
  local loop_device="${1:-}"
  [[ -n "$loop_device" ]] || return 1
  local loop_name="${loop_device#/dev/}"
  local backing_path="/sys/class/block/$loop_name/loop/backing_file"
  [[ -r "$backing_path" ]] || return 1
  local backing
  backing="$(cat "$backing_path" 2>/dev/null || true)"
  [[ -n "$backing" ]] || return 1
  printf '%s\n' "$backing"
}

safe_loop_is_associated() {
  safe_loop_backing_file "${1:-}" >/dev/null 2>&1
}

safe_detach_loop() {
  local loop_device="${1:-}"
  [[ -n "$loop_device" ]] || return 0

  # losetup --detach uses lazy device destruction. Partition minors created by
  # --partscan may remain until the parent detach has been requested, so partx
  # removal is not a prerequisite. Request detach, then wait until BOTH the
  # parent association and partition children are gone. Pin the original
  # backing identity so a reused loop number can never be detached by mistake.
  local expected_backing=""
  local current_backing=""
  local attempt

  expected_backing="$(safe_loop_backing_file "$loop_device" 2>/dev/null || true)"
  if [[ -z "$expected_backing" ]]; then
    for attempt in {1..50}; do
      if ! safe_loop_partition_children_present "$loop_device"; then
        return 0
      fi
      safe_udev_settle
      sleep 0.1
    done
    echo "ERROR: stale loop partition children remain without a parent association: $loop_device" >&2
    return 1
  fi

  blockdev --flushbufs "$loop_device" 2>/dev/null || true

  for attempt in {1..50}; do
    current_backing="$(safe_loop_backing_file "$loop_device" 2>/dev/null || true)"

    if [[ -z "$current_backing" ]]; then
      safe_udev_settle
      if ! safe_loop_partition_children_present "$loop_device"; then
        return 0
      fi
      sleep 0.1
      continue
    fi

    if [[ "$current_backing" != "$expected_backing" ]]; then
      echo "ERROR: refusing loop cleanup after device reuse: $loop_device now maps $current_backing, expected $expected_backing" >&2
      return 1
    fi

    losetup -d "$loop_device" 2>/dev/null || true
    safe_udev_settle

    current_backing="$(safe_loop_backing_file "$loop_device" 2>/dev/null || true)"
    if [[ -z "$current_backing" ]] && ! safe_loop_partition_children_present "$loop_device"; then
      return 0
    fi
    if [[ -n "$current_backing" && "$current_backing" != "$expected_backing" ]]; then
      echo "ERROR: refusing loop cleanup after device reuse: $loop_device now maps $current_backing, expected $expected_backing" >&2
      return 1
    fi
    sleep 0.1
  done

  current_backing="$(safe_loop_backing_file "$loop_device" 2>/dev/null || true)"
  echo "ERROR: loop detach did not fully settle: $loop_device backing=${current_backing:-none} partition_children=$(safe_loop_partition_children_present "$loop_device" && echo present || echo none)" >&2
  return 1
}

safe_cleanup_exit() {
  local original_status="${1:-0}"
  local cleanup_failed="${2:-0}"
  local message="${3:-Cleanup was incomplete; preserving work data for inspection.}"
  local final_status="$original_status"

  if (( cleanup_failed != 0 )); then
    echo "$message" >&2
    if (( final_status == 0 )); then
      final_status=1
    fi
  fi

  # Intended for EXIT-trap cleanup handlers after they clear EXIT/INT/TERM.
  # exit, rather than return, makes cleanup failure authoritative.
  exit "$final_status"
}
safe_remove_build_dir() {
  local build_dir="$1"
  [[ -n "$build_dir" && "$build_dir" != "/" ]] || return 1
  if findmnt -rn -R "$build_dir" 2>/dev/null | grep -q .; then
    echo "ERROR: refusing to remove build tree with live mounts: $build_dir" >&2
    return 1
  fi
  rm -rf --one-file-system -- "$build_dir"
}
