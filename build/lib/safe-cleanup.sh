#!/usr/bin/env bash
# Shared destructive-build cleanup helpers. Source from bash with set -Eeuo.

safe_unmount_path_tree() {
  local path="$1"
  [[ -n "$path" ]] || return 0
  mountpoint -q -- "$path" || return 0

  local targets=()
  local index target failed=0
  mapfile -t targets < <(findmnt -rn -R -o TARGET --target "$path" 2>/dev/null || true)
  for (( index=${#targets[@]}-1; index>=0; index-- )); do
    target="${targets[$index]}"
    [[ -n "$target" ]] || continue
    case "$target" in
      "$path"|"$path"/*) ;;
      *)
        echo "ERROR: refusing cleanup target outside requested mount tree: $target" >&2
        failed=1
        continue
        ;;
    esac
    if mountpoint -q -- "$target"; then
      umount -- "$target" 2>/dev/null || true
    fi
    if mountpoint -q -- "$target"; then
      umount -l -- "$target" 2>/dev/null || true
    fi
    if mountpoint -q -- "$target"; then
      echo "ERROR: mount is still attached; preserving build directory: $target" >&2
      failed=1
    fi
  done
  return "$failed"
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
  local attempt
  for attempt in {1..20}; do
    if ! losetup "$loop_device" >/dev/null 2>&1; then
      return 0
    fi
    losetup -d "$loop_device" 2>/dev/null || true
    if ! losetup "$loop_device" >/dev/null 2>&1; then
      return 0
    fi
    sleep 0.05
  done
  echo "ERROR: loop device is still attached: $loop_device" >&2
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
