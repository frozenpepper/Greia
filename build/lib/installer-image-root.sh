#!/usr/bin/env bash
# Find the ext4 root partition of a Greia installer image loop device.
#
# The pre-EFI installer image carried the root filesystem as partition 1.
# Since the 2026-10-21 EFI media work the MBR image is p1 = 64 MiB FAT32 ESP
# and p2 = ext4 root. Consumers (live-USB writer and read-only verifiers) must
# locate the root by filesystem type instead of assuming a partition number,
# and must still work with the historical single-partition images.

# Print the first ext4 partition of the loop device, waiting briefly for udev.
greia_installer_root_partition() {
  local loop="$1"
  local candidate fstype
  local attempts="${2:-150}"
  while (( attempts-- > 0 )); do
    for candidate in "${loop}p"*; do
      [[ -b "$candidate" ]] || continue
      fstype="$(blkid -o value -s TYPE "$candidate" 2>/dev/null | tr -d '[:space:]')"
      if [[ "$fstype" == "ext4" ]]; then
        printf '%s\n' "$candidate"
        return 0
      fi
    done
    sleep 0.2
  done
  return 1
}
