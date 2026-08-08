#!/usr/bin/env bash
# Shared destructive-build cleanup helpers. Source from bash with set -Eeuo.

safe_unmount_paths() {
  local paths=("$@")
  local failed=0
  local index path
  for (( index=${#paths[@]}-1; index>=0; index-- )); do
    path="${paths[$index]}"
    [[ -n "$path" ]] || continue
    if mountpoint -q -- "$path"; then
      umount -- "$path" 2>/dev/null || true
    fi
    if mountpoint -q -- "$path"; then
      umount -l -- "$path" 2>/dev/null || true
    fi
    if mountpoint -q -- "$path"; then
      echo "ERROR: mount is still attached; preserving build directory: $path" >&2
      failed=1
    fi
  done
  return "$failed"
}

safe_detach_loop() {
  local loop_device="${1:-}"
  [[ -n "$loop_device" ]] || return 0
  if losetup "$loop_device" >/dev/null 2>&1; then
    losetup -d "$loop_device" 2>/dev/null || true
  fi
  if losetup "$loop_device" >/dev/null 2>&1; then
    echo "ERROR: loop device is still attached: $loop_device" >&2
    return 1
  fi
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
