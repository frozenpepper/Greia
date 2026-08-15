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

safe_loop_partition_children_present() {
  local loop_device="${1:-}"
  [[ -n "$loop_device" ]] || return 1
  local loop_name="${loop_device#/dev/}"
  compgen -G "/sys/class/block/${loop_name}p[0-9]*" >/dev/null
}

safe_remove_loop_partitions() {
  local loop_device="${1:-}"
  [[ -n "$loop_device" ]] || return 0
  local attempt
  for attempt in {1..20}; do
    if ! safe_loop_partition_children_present "$loop_device"; then
      return 0
    fi
    # partx modifies kernel partition bookkeeping; a transient busy
    # child must not be ignored and carried into parent loop detach.
    partx -d "$loop_device" >/dev/null 2>&1 || true
    safe_udev_settle
    if ! safe_loop_partition_children_present "$loop_device"; then
      return 0
    fi
    sleep 0.1
  done
  echo "ERROR: loop partition mappings remain after bounded partx teardown: $loop_device" >&2
  return 1
}

safe_loop_is_associated() {
  local loop_device="${1:-}"
  [[ -n "$loop_device" ]] || return 1
  local loop_name="${loop_device#/dev/}"
  local backing_path="/sys/class/block/$loop_name/loop/backing_file"
  [[ -r "$backing_path" ]] || return 1
  local backing
  backing="$(cat "$backing_path" 2>/dev/null || true)"
  [[ -n "$backing" ]]
}

safe_detach_loop() {
  local loop_device="${1:-}"
  [[ -n "$loop_device" ]] || return 0
  # Remove and verify kernel partition children before touching the
  # parent loop. Never suppress a persistent child mapping.
  safe_remove_loop_partitions "$loop_device" || return 1

  blockdev --flushbufs "$loop_device" 2>/dev/null || true
  safe_udev_settle
  local attempt
  for attempt in {1..20}; do
    if ! safe_loop_is_associated "$loop_device"; then
      return 0
    fi
    losetup -d "$loop_device" 2>/dev/null || true
    safe_udev_settle
    if ! safe_loop_is_associated "$loop_device"; then
      return 0
    fi
    sleep 0.1
  done
  echo "ERROR: loop backing file is still associated after detach and udev settle: $loop_device" >&2
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
