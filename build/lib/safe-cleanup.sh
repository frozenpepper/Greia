#!/usr/bin/env bash
# Shared destructive-build cleanup helpers. Source from bash with set -Eeuo.

safe_udev_settle() {
  udevadm settle --timeout=5 >/dev/null 2>&1 || true
}

safe_unmount_path_tree() {
  local path="$1"
  [[ -n "$path" ]] || return 0
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

safe_detach_loop() {
  local loop_device="${1:-}"
  [[ -n "$loop_device" ]] || return 0
  # losetup --partscan creates kernel partition mappings. Remove them after
  # all filesystems are unmounted so they cannot hold the loop association open.
  partx -d "$loop_device" 2>/dev/null || true
  safe_udev_settle
  # The real Greia image diagnostic found no mounts, holders, open FDs, or
  # residual partx map, yet the loop association survived until its block
  # buffers were flushed. Flush only this known loop before detaching it.
  blockdev --flushbufs "$loop_device" 2>/dev/null || true
  safe_udev_settle
  local attempt
  for attempt in {1..20}; do
    if ! losetup "$loop_device" >/dev/null 2>&1; then return 0; fi
    losetup -d "$loop_device" 2>/dev/null || true
    safe_udev_settle
    if ! losetup "$loop_device" >/dev/null 2>&1; then return 0; fi
    sleep 0.1
  done
  echo "ERROR: loop device is still associated after detach and udev settle: $loop_device" >&2
  return 1
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
