#!/usr/bin/env bash
set -Eeuo pipefail

# Read-only verification for a Greia Syslinux/FAT32 live USB.
#
# IMPORTANT: this tool is deliberately separate from build-live-usb.sh.
# The latter is the physically proven Acer media writer documented in
# docs/INSTALLATION_USB_BOOT_POSTMORTEM.md. Safety/read-back checks must not
# mutate that firmware-sensitive recipe merely to make verification convenient.
#
# Usage:
#   sudo bash tools/verify-live-usb.sh <installer.img> <whole-usb-device>

PROJECT_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"

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

required=(awk cmp find fsck.vfat losetup lsblk mount mountpoint parted realpath sed sort umount)
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

# Read-only filesystem check. fsck.vfat -n never repairs/writes.
fsck.vfat -n "$USB_PART" >/dev/null || {
  echo "USB FAT32 filesystem did not pass read-only fsck." >&2
  exit 1
}

WORK="$(mktemp -d -p "${TMPDIR:-/tmp}" greia-live-usb-verify.XXXXXX)"
IMG_MOUNT="$WORK/image"
USB_MOUNT="$WORK/usb"
EXPECTED_CFG="$WORK/syslinux.cfg"
IMG_LOOP=""
mkdir -p "$IMG_MOUNT" "$USB_MOUNT"

cleanup() {
  local status=$?
  trap - EXIT INT TERM
  set +e
  if mountpoint -q "$USB_MOUNT" 2>/dev/null; then umount "$USB_MOUNT"; fi
  if mountpoint -q "$IMG_MOUNT" 2>/dev/null; then umount "$IMG_MOUNT"; fi
  if [[ -n "$IMG_LOOP" ]]; then losetup -d "$IMG_LOOP" >/dev/null 2>&1 || true; fi
  rm -rf "$WORK"
  exit "$status"
}
trap cleanup EXIT INT TERM

IMG_LOOP="$(losetup --find --show --partscan --read-only "$IMAGE")"
IMG_PART="${IMG_LOOP}p1"
for _ in {1..30}; do
  [[ -b "$IMG_PART" ]] && break
  sleep 0.2
done
[[ -b "$IMG_PART" ]] || {
  echo "Installer image partition did not appear." >&2
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

sed "s/LIVE_MEDIA_ID/$LIVE_MEDIA_ID/" \
  "$PROJECT_ROOT/build/live-syslinux/syslinux.cfg.in" > "$EXPECTED_CFG"

# Guard the accepted Acer development diagnostics contract from the postmortem.
# A future consoleless production path may be introduced separately only after
# physical acceptance; the current reference-hardware development USB remains
# observable so early failures are not converted into grey-screen reboot loops.
grep -q 'console=tty1' "$EXPECTED_CFG" || {
  echo "Refusing: current Syslinux template is not observable (missing console=tty1)." >&2
  exit 1
}
if grep -q 'console=null\|DISPLAY .*clear\.msg' "$EXPECTED_CFG"; then
  echo "Refusing: current Syslinux template reintroduces the rejected silent/clear-screen experiment." >&2
  exit 1
fi

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
echo "  diagnostic_console=tty1"
