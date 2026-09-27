#!/usr/bin/env bash
# Read-only FAT fsck result policy for tools/verify-live-usb.sh.
#
# The physically proven Syslinux/FAT32 writer (tools/build-live-usb.sh) runs
# `syslinux --install`, which patches the *primary* FAT32 boot sector so it can
# locate /boot/syslinux/ldlinux.sys, and does not update the backup boot sector
# at sector 6. It also leaves minor FAT32 free-cluster/FSInfo accounting drift
# after the large squashfs/payload copies. Both conditions are inherent to the
# proven recipe, are reported by fsck.vfat as non-fatal, and do not indicate
# corruption.
#
# Treating every fsck.vfat exit status 1 as fatal therefore made the read-only
# verifier unable to ever accept media produced by the proven writer.
#
# This policy accepts ONLY those two already-observed benign conditions. It is
# an allowlist: any other diagnostic line fails closed. It never repairs,
# writes to, or re-runs fsck against the device.
#
# Usage:
#   greia_fat_fsck_acceptable <fsck-exit-status> <fsck-output-file>
# Returns 0 when the result is acceptable, 1 when it must fail the verification.

greia_fat_fsck_acceptable() {
  local status="$1" output_file="$2" line

  # Status 0 is clean; status 2 (and anything unexpected) is an invocation,
  # access, or operational failure and is always fatal.
  case "$status" in
    0) return 0 ;;
    1) : ;;
    *) return 1 ;;
  esac

  # Only the benign diagnostics are tolerated. Everything else fails closed.
  while IFS= read -r line || [[ -n "$line" ]]; do
    # Trailing whitespace/CR tolerance without altering content semantics.
    line="${line%$'\r'}"

    # Blank separator lines.
    [[ -z "${line//[[:space:]]/}" ]] && continue

    # Version banner, e.g. "fsck.fat 4.2 (2021-01-31)".
    [[ "$line" =~ ^fsck\.fat[[:space:]] ]] && continue

    # (a) Primary boot sector differs from its backup because Syslinux patched
    #     the primary VBR, plus the wrapped offset dump and its trailer.
    [[ "$line" == "There are differences between boot sector and its backup." ]] && continue
    [[ "$line" == "This is mostly harmless. Differences: (offset:original/backup)" ]] && continue
    [[ "$line" =~ ^[[:space:]]*Not\ automatically\ fixing\ this\.[[:space:]]*$ ]] && continue

    # Wrapped "offset:original/backup" hex dump lines, e.g.
    #   "  3:53/6d, 4:59/6b, ... 10:58/74"
    #   ", 90:fa/0e, 91:fc/1f, ..."
    # Offsets are byte positions in the boot sector and reach three hex digits
    # (e.g. "100:06/56"), so the offset field must allow 1-4 hex digits.
    if [[ "$line" =~ ^[[:space:]]*,?[[:space:]]*[0-9a-fA-F]{1,4}:[0-9a-fA-F]{2}/[0-9a-fA-F]{2}([[:space:]]*,[[:space:]]*[0-9a-fA-F]{1,4}:[0-9a-fA-F]{2}/[0-9a-fA-F]{2})*[[:space:]]*,?[[:space:]]*$ ]]; then
      continue
    fi

    # (b) Stale FAT32 free-cluster / FSInfo accounting.
    [[ "$line" =~ ^Reclaimed[[:space:]][0-9]+[[:space:]]unused[[:space:]]clusters[[:space:]]\([0-9]+[[:space:]]bytes\)\.[[:space:]]*$ ]] && continue
    [[ "$line" == "Checking free cluster summary." ]] && continue
    [[ "$line" =~ ^Free\ cluster\ summary\ wrong[[:space:]]\([0-9]+[[:space:]]vs\.[[:space:]]really[[:space:]]+[0-9]+\)[[:space:]]*$ ]] && continue
    [[ "$line" =~ ^[[:space:]]*Auto-correcting\.[[:space:]]*$ ]] && continue

    # Read-only assurance and the trailing device summary.
    [[ "$line" == "Leaving filesystem unchanged." ]] && continue
    if [[ "$line" =~ ^/[^[:space:]]+:[[:space:]][0-9]+[[:space:]]files,[[:space:]][0-9]+/[0-9]+[[:space:]]clusters[[:space:]]*$ ]]; then
      continue
    fi

    # Anything else is an unrecognised filesystem inconsistency.
    return 1
  done < "$output_file"

  return 0
}
