#!/usr/bin/env bash
set -Eeuo pipefail

# Read-only verification for a Greia Syslinux/FAT32 live USB.
#
# IMPORTANT: this tool is deliberately separate from build-live-usb.sh.
# The latter is the physically proven Acer media writer documented in
# docs/engineering/boot/INSTALLATION_USB_BOOT_POSTMORTEM.md. Safety/read-back checks must not
# mutate that firmware-sensitive recipe merely to make verification convenient.
#
# Usage:
#   sudo bash tools/verify-live-usb.sh <installer.img> <whole-usb-device>

PROJECT_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
# shellcheck source=tools/verify-live-usb-fsck-policy.sh
source "$PROJECT_ROOT/tools/verify-live-usb-fsck-policy.sh"
# shellcheck source=../build/lib/safe-cleanup.sh
source "$PROJECT_ROOT/build/lib/safe-cleanup.sh"
# shellcheck source=../build/lib/live-syslinux.sh
source "$PROJECT_ROOT/build/lib/live-syslinux.sh"
# shellcheck source=../build/lib/installer-image-root.sh
source "$PROJECT_ROOT/build/lib/installer-image-root.sh"

usage() {
  cat >&2 <<'EOF'
Usage: sudo bash tools/verify-live-usb.sh <installer.img> <whole-usb-device>

Verifies an already-written Greia Syslinux/FAT32 USB read-only.
It never partitions, formats, installs Syslinux, or writes to the device.
EOF
}

[[ $# -eq 2 ]] || { usage; exit 2; }
[[ ${EUID:-$(id -u)} -eq 0 ]] || { echo "Run as root." >&2; exit 1; }

IMAGE="$(realpath "$1")"
DEVICE="$2"

required=(awk cmp find fsck.vfat losetup partx blockdev blkid udevadm findmnt lsblk mount mountpoint parted realpath sed sort umount)
for command_name in "${required[@]}"; do
  command -v "$command_name" >/dev/null || {
    echo "Missing dependency: $command_name" >&2
    exit 1
  }
done

[[ -f "$IMAGE" && -s "$IMAGE" ]] || {
  echo "Installer image is missing or empty: $IMAGE" >&2
  exit 1
}
[[ -b "$DEVICE" ]] || {
  echo "USB target is not a block device: $DEVICE" >&2
  exit 1
}

DEV_NAME="${DEVICE#/dev/}"
RM="$(lsblk -dn -o RM "/dev/$DEV_NAME" 2>/dev/null | tr -d '[:space:]' || echo 0)"
TYPE="$(lsblk -dn -o TYPE "/dev/$DEV_NAME" 2>/dev/null | tr -d '[:space:]' || echo part)"
if [[ "$RM" != "1" || "$TYPE" != "disk" ]]; then
  echo "Refusing verification: $DEVICE is not a removable whole disk (RM=$RM TYPE=$TYPE)." >&2
  exit 1
fi

case "$DEVICE" in
  *[0-9]) USB_PART="${DEVICE}p1" ;;
  *) USB_PART="${DEVICE}1" ;;
esac
[[ -b "$USB_PART" ]] || {
  echo "Expected first USB partition is missing: $USB_PART" >&2
  exit 1
}

# The proven recipe requires partition 1 to be active/bootable.
PART1_FLAGS="$(parted -sm "$DEVICE" print 2>/dev/null | awk -F: '$1 == "1" {print $7}')"
case ",$PART1_FLAGS," in
  *,boot,*|*,boot,*) ;;
  *)
    echo "USB partition 1 is not marked bootable: flags=$PART1_FLAGS" >&2
    exit 1
    ;;
esac

WORK="$(mktemp -d -p "${TMPDIR:-/tmp}" greia-live-usb-verify.XXXXXX)"
IMG_MOUNT="$WORK/image"
USB_MOUNT="$WORK/usb"
EXPECTED_CFG="$WORK/syslinux.cfg"
FSCK_OUT="$WORK/fsck.out"
IMG_LOOP=""
mkdir -p "$IMG_MOUNT" "$USB_MOUNT"

cleanup() {
  local original_status=$?
  trap - EXIT INT TERM
  set +e
  local cleanup_failed=0
  safe_unmount_paths "$IMG_MOUNT" "$USB_MOUNT" || cleanup_failed=1
  safe_detach_loop "$IMG_LOOP" || cleanup_failed=1
  if (( cleanup_failed == 0 )); then
    rm -rf "$WORK"
  fi
  safe_cleanup_exit "$original_status" "$cleanup_failed" "Live-USB verification cleanup was incomplete; preserving work data for inspection."
}
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

# Read-only filesystem check. fsck.vfat -n never repairs/writes.
#
# Status 1 is NOT automatically fatal: the proven Syslinux writer patches the
# primary FAT32 VBR (so it can find /boot/syslinux/ldlinux.sys) without
# updating the backup boot sector, and leaves minor free-cluster/FSInfo drift
# after the large squashfs/payload copies. fsck.vfat reports both and calls
# them harmless, so treating every status 1 as fatal made this verifier unable
# to accept any media produced by the proven writer.
#
# The policy is a narrow allowlist for exactly those two conditions and fails
# closed on any other diagnostic. LC_ALL=C keeps the classifier stable.
set +e
LC_ALL=C fsck.vfat -n "$USB_PART" > "$FSCK_OUT" 2>&1
FSCK_STATUS=$?
set -e

if ! greia_fat_fsck_acceptable "$FSCK_STATUS" "$FSCK_OUT"; then
  {
    echo "USB FAT32 filesystem did not pass read-only fsck (status=$FSCK_STATUS)."
    sed 's/^/  fsck: /' "$FSCK_OUT"
  } >&2
  exit 1
fi
if [[ "$FSCK_STATUS" -eq 1 ]]; then
  echo "  fsck_note=accepted post-Syslinux FAT32 metadata conditions only"
fi

IMG_LOOP="$(losetup --find --show --partscan --read-only "$IMAGE")"
IMG_PART="$(greia_installer_root_partition "$IMG_LOOP")" || {
  echo "Installer image ext4 root partition did not appear." >&2
  exit 1
}
mount -o ro,noload "$IMG_PART" "$IMG_MOUNT"
mount -o ro "$USB_PART" "$USB_MOUNT"

LIVE_MEDIA_ID="$(tr -d '\r\n' < "$IMG_MOUNT/.disk/live-uuid" 2>/dev/null || true)"
[[ "$LIVE_MEDIA_ID" =~ ^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$ ]] || {
  echo "Source installer image has no valid .disk/live-uuid." >&2
  exit 1
}
[[ "$(tr -d '\r\n' < "$USB_MOUNT/.disk/live-uuid" 2>/dev/null || true)" == "$LIVE_MEDIA_ID" ]] || {
  echo "USB live-media identity does not match installer image." >&2
  exit 1
}

LIVE_CONSOLE_POLICY="$(greia_live_console_policy "$IMG_MOUNT")"
SYSLINUX_TEMPLATE="$(greia_live_syslinux_template "$PROJECT_ROOT" "$LIVE_CONSOLE_POLICY")"
sed "s/LIVE_MEDIA_ID/$LIVE_MEDIA_ID/" \
  "$SYSLINUX_TEMPLATE" > "$EXPECTED_CFG"

# Guard the accepted Acer recovery diagnostics contract from the postmortems.
# Every template must never auto-reboot a panic (panic=0 everywhere).
if grep -Eq 'panic=[1-9][0-9]*' "$EXPECTED_CFG"; then
  echo "Refusing: Syslinux template auto-reboots on panic." >&2
  exit 1
fi
# The quiet release-candidate path clears the stock SYSLINUX banner with the
# owner-approved one-byte form-feed display file (2026-10-18 decision). It is
# presentation-only and must never appear on the diagnostic template, whose
# whole purpose is observable early output.
clear_display_lines="$(grep -c '^DISPLAY /boot/syslinux/clear\.msg$' "$EXPECTED_CFG" || true)"
if grep -q '^DISPLAY ' "$EXPECTED_CFG" && [[ "$clear_display_lines" != "1" ]]; then
  echo "Refusing: Syslinux template uses a display file other than the approved clear.msg." >&2
  exit 1
fi
# Kernel APPEND line of one LABEL block.
label_append() {
  awk -v want="$1" '
    $1 == "LABEL" { label = $2; next }
    label == want && $1 == "APPEND" { sub(/^[[:space:]]*APPEND[[:space:]]+/, ""); print; exit }
  ' "$EXPECTED_CFG"
}
require_diagnostic_append() {
  local append="$1" what="$2"
  for required in console=tty1 panic=0 loglevel=4 systemd.show_status=true; do
    [[ " $append " == *" $required "* ]] || {
      echo "Refusing: $what is not observable (missing $required)." >&2
      exit 1
    }
  done
  if [[ " $append " =~ [[:space:]](console=null|quiet|splash|loglevel=0)[[:space:]] ]]; then
    echo "Refusing: $what reintroduces hidden recovery behavior." >&2
    exit 1
  fi
}
# console=null is fatal on the Debian 686 kernel (no ttynull driver): PID 1
# gets no /dev/console, live-boot dies on `exec 6>&1` and the kernel panics
# silently on the Syslinux banner (2026-10-17 RC). No entry may carry it.
if grep -Eq '^[[:space:]]*APPEND.*[[:space:]]console=(null)?([[:space:]]|$)' "$EXPECTED_CFG"; then
  echo "Refusing: a Syslinux entry uses console=null (no ttynull driver; silent panic)." >&2
  exit 1
fi
case "$LIVE_CONSOLE_POLICY" in
  diagnostic)
    # The developer recovery USB must expose tty1 and must not suppress the
    # early evidence that distinguishes Syslinux/kernel/initramfs/live-boot
    # failures.
    require_diagnostic_append "$(label_append live)" "diagnostic Syslinux template"
    grep -q 'console=tty1' "$EXPECTED_CFG" || exit 1
    if grep -q '^DISPLAY ' "$EXPECTED_CFG"; then
      echo "Refusing: diagnostic Syslinux template must keep its boot output observable." >&2
      exit 1
    fi
    ;;
  quiet)
    # Release-candidate media: the default entry is silent, and the hidden
    # LABEL verbose (Shift/Alt at boot, PROMPT 0 semantics) keeps today's full
    # diagnostic arguments reachable. The stock SYSLINUX banner is cleared by
    # the approved display file; the payload must carry its exact one byte.
    default_append="$(label_append live)"
    for required in quiet splash loglevel=0 console=tty1 panic=0 vt.global_cursor_default=0 systemd.show_status=false; do
      [[ " $default_append " == *" $required "* ]] || {
        echo "Refusing: quiet Syslinux default entry lacks $required." >&2
        exit 1
      }
    done
    grep -qx 'PROMPT 0' "$EXPECTED_CFG" || { echo "Refusing: quiet template must keep PROMPT 0." >&2; exit 1; }
    require_diagnostic_append "$(label_append verbose)" "quiet template's verbose recovery entry"
    [[ "$clear_display_lines" == "1" ]] || {
      echo "Refusing: quiet template must reference the approved clear.msg display file." >&2
      exit 1
    }
    [[ -s "$USB_MOUNT/boot/syslinux/clear.msg" ]] || {
      echo "Refusing: quiet media is missing boot/syslinux/clear.msg." >&2
      exit 1
    }
    cmp -s "$PROJECT_ROOT/build/live-syslinux/clear.msg" \
      "$USB_MOUNT/boot/syslinux/clear.msg" || {
      echo "USB read-back mismatch: boot/syslinux/clear.msg" >&2
      exit 1
    }
    ;;
esac

for mapping in \
  "live/vmlinuz:vmlinuz" \
  "live/initrd.img:initrd.img" \
  "live/filesystem.squashfs:filesystem.squashfs"
do
  source_rel="${mapping%%:*}"
  usb_rel="${mapping#*:}"
  [[ -s "$IMG_MOUNT/$source_rel" && -s "$USB_MOUNT/$usb_rel" ]] || {
    echo "Missing boot-critical file during verification: $usb_rel" >&2
    exit 1
  }
  cmp -s "$IMG_MOUNT/$source_rel" "$USB_MOUNT/$usb_rel" || {
    echo "USB read-back mismatch: $usb_rel" >&2
    exit 1
  }
done

[[ -d "$IMG_MOUNT/payload" && -d "$USB_MOUNT/payload" ]] || {
  echo "Installer payload directory is missing." >&2
  exit 1
}
while IFS= read -r payload_name; do
  [[ -n "$payload_name" ]] || continue
  cmp -s "$IMG_MOUNT/payload/$payload_name" "$USB_MOUNT/payload/$payload_name" || {
    echo "USB read-back mismatch: payload/$payload_name" >&2
    exit 1
  }
done < <(find "$IMG_MOUNT/payload" -maxdepth 1 -type f -printf '%f\n' | LC_ALL=C sort)

cmp -s "$EXPECTED_CFG" "$USB_MOUNT/boot/syslinux/syslinux.cfg" || {
  echo "USB read-back mismatch: boot/syslinux/syslinux.cfg" >&2
  exit 1
}
[[ -s "$USB_MOUNT/boot/syslinux/ldlinux.sys" ]] || {
  echo "USB is missing Syslinux ldlinux.sys." >&2
  exit 1
}

# Verify only the 440-byte Syslinux bootstrap area; the following partition-table
# bytes are device-specific and must not be compared against mbr.bin.
cmp -n 440 /usr/lib/syslinux/mbr/mbr.bin "$DEVICE" >/dev/null || {
  echo "USB MBR bootstrap does not match Syslinux mbr.bin." >&2
  exit 1
}

echo "Greia live USB read-only verification: PASS"
echo "  usb_readback_verification=PASS"
echo "  bootloader=syslinux (MBR+VBR)"
echo "  live_media_id=$LIVE_MEDIA_ID"
echo "  live_console_policy=$LIVE_CONSOLE_POLICY"
if [[ "$LIVE_CONSOLE_POLICY" == quiet ]]; then
  echo "  diagnostic_console=hidden LABEL verbose (hold Shift/Alt at boot, type verbose)"
else
  echo "  diagnostic_console=tty1"
fi
echo "  panic_policy=halt-on-panic"
