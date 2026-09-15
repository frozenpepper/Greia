#!/usr/bin/env bash
# Persistent host apt/pool caches for Greia image builders. Source from bash
# with set -Eeuo (same convention as lib/safe-cleanup.sh).
#
# Design invariant: the caches live on the build host, outside the produced
# image. Builders MUST bind-mount the host cache at
# <chroot>/var/cache/apt/archives (downloaded .debs) BEFORE debootstrap, and
# <chroot>/var/cache/greia-pool (hardware-support pool downloads) for the
# chroot's lifetime. Mounting the apt cache after debootstrap shadows the base
# .debs on the real filesystem (invisible to du -sx, counted by df) and they
# survive into the image/squashfs. The existing MOUNTS teardown
# (safe_unmount_paths) releases them before compression (installer
# pre-mksquashfs; target cleanup at EXIT, where du -sx -x already excludes the
# bind mount), so cached .debs are never counted and never enter the image.
#
# Never clear the host caches: repeated builds reuse already-downloaded .debs
# instead of re-fetching the whole package set.

GREIA_APT_CACHE="${GREIA_APT_CACHE:-/var/cache/greia-apt}"
GREIA_POOL_CACHE="${GREIA_POOL_CACHE:-/var/cache/greia-pool}"

mount_apt_archives_cache() {
  local chroot="$1"
  [[ -n "${chroot:-}" ]] || { echo "mount_apt_archives_cache: chroot missing." >&2; return 1; }
  local mountpoint="$chroot/var/cache/apt/archives"
  install -d -m 0755 "$GREIA_APT_CACHE"
  install -d -m 0755 "$mountpoint"
  mount --bind "$GREIA_APT_CACHE" "$mountpoint"
  printf '%s\n' "$mountpoint"
}

mount_pool_cache() {
  local chroot="$1"
  [[ -n "${chroot:-}" ]] || { echo "mount_pool_cache: chroot missing." >&2; return 1; }
  local mountpoint="$chroot/var/cache/greia-pool"
  install -d -m 0755 "$GREIA_POOL_CACHE"
  install -d -m 0755 "$mountpoint"
  mount --bind "$GREIA_POOL_CACHE" "$mountpoint"
  printf '%s\n' "$mountpoint"
}
