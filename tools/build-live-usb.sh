#!/usr/bin/env bash
set -Eeuo pipefail
# Build a syslinux/FAT32 live USB from a Greia installer image.
#
# The reference Acer BIOS does not execute GRUB's MBR from a USB stick but
# does execute the antiX-style syslinux MBR+VBR on an active FAT32 partition
# (see docs/INSTALLATION_USB_BOOT_POSTMORTEM.md). This tool turns an already
# built `greia-os-installer-*.img` into that media layout on a removable USB
# device, copying the live kernel/initrd/root, the installable payload and the
# live-media identity marker.
#
# It verifies the FINAL removable media after writing. A successful source
# image is not enough: a stale/partial USB flash must never be reported ready.
#
# Usage: sudo tools/build-live-usb.sh <installer.img> <device>
#   <installer.img>  path to a built greia-os-installer-*.img
#   <device>         the whole removable USB device (e.g. /dev/sdd) to overwrite

PROJECT_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"

usage() {
  cat <<'USAGE'
Usage: sudo tools/build-live-usb.sh <installer.img> <device>

Builds a syslinux/FAT32 live USB from a Greia installer image.
This DESTROYS the target device. Only pass a removable USB whole-disk device.
USAGE
}

[[ $# -eq 2 ]] || { usage >&2; exit 2; }
[[ ${EUID:-$(id -u)} -eq 0 ]] || { echo "Run as root." >&2; exit 1; }

IMAGE="$(realpath "$1")"
DEVICE="$2"

required=(
  awk cmp cp dd find fsck.vfat install losetup lsblk mkfs.vfat mount mountpoint
  parted partprobe realpath sed sgdisk sha256sum sync syslinux umount wipefs
)
for command_name in "${required[@]}"; do
  command -v "$command_name" >/dev/null || {
    echo "Missing dependency: $command_name" >&2
    exit 1
  }
done

[[ -f "$IMAGE" && -s "$IMAGE" ]] || { echo "Installer image is missing or empty: $IMAGE" >&2; exit 1; }
[[ -b "$DEVICE" ]] || { echo "Target is not a block device: $DEVICE" >&2; exit 1; }

# The target must be a removable whole disk (no partitions passed, RM=1).
DEV_NAME="${DEVICE#/dev/}"
RM="$(lsblk -dn -o RM "/dev/$DEV_NAME" 2>/dev/null | tr -d '[:space:]' || echo 0)"
TYPE="$(lsblk -dn -o TYPE "/dev/$DEV_NAME" 2>/dev/null | tr -d '[:space:]' || echo part)"
if [[ "$RM" != "1" || "$TYPE" != "disk" ]]; then
  echo "Refusing: $DEVICE is not a removable whole-disk device (RM=$RM TYPE=$TYPE)." >&2
  exit 1
fi

# Do not helpfully unmount something the operator is actively using. Refuse
# instead, so the destructive boundary remains explicit and reviewable.
mapfile -t MOUNTED_CHILDREN < <(
  lsblk -nrpo NAME,MOUNTPOINT "$DEVICE" 2>/dev/null \
    | awk 'NF >= 2 && $2 != "" {print $1 " -> " $2}'
)
if (( ${#MOUNTED_CHILDREN[@]} > 0 )); then
  echo "Refusing: target device has mounted filesystems:" >&2
  printf '  %s\n' "${MOUNTED_CHILDREN[@]}" >&2
  exit 1
fi

WORK="$(mktemp -d -p "${TMPDIR:-/tmp}" greia-live-usb.XXXXXX)"
IMG_MOUNT="$WORK/img"
USB_MOUNT="$WORK/usb"
EXPECTED_CFG="$WORK/syslinux.cfg"
IMG_LOOP=""
USB_MOUNTED=0
mkdir -p "$IMG_MOUNT" "$USB_MOUNT"

cleanup() {
  local status=$?
  trap - EXIT INT TERM
  set +e
  if [[ "$USB_MOUNTED" == "1" ]] || mountpoint -q "$USB_MOUNT" 2>/dev/null; then
    umount "$USB_MOUNT" >/dev/null 2>&1 || true
  fi
  if mountpoint -q "$IMG_MOUNT" 2>/dev/null; then
    umount "$IMG_MOUNT" >/dev/null 2>&1 || true
  fi
  if [[ -n "$IMG_LOOP" ]]; then
    losetup -d "$IMG_LOOP" >/dev/null 2>&1 || true
  fi
  rm -rf "$WORK"
  exit "$status"
}
trap cleanup EXIT INT TERM

# Mount the installer image partition read-only to source the live files. Do not
# replay/modify its ext journal just because it is being used as flash input.
IMG_LOOP="$(losetup --find --show --partscan --read-only "$IMAGE")"
IMG_PART="${IMG_LOOP}p1"
for _ in {1..30}; do [[ -b "$IMG_PART" ]] && break; sleep 0.2; done
[[ -b "$IMG_PART" ]] || { echo "Installer image partition did not appear." >&2; exit 1; }
mount -o ro,noload "$IMG_PART" "$IMG_MOUNT"

# Extract the live media id from the image's own marker.
LIVE_MEDIA_ID="$(tr -d '\r\n' < "$IMG_MOUNT/.disk/live-uuid" 2>/dev/null || true)"
[[ "$LIVE_MEDIA_ID" =~ ^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$ ]] || {
  echo "Installer image is missing a valid .disk/live-uuid." >&2
  exit 1
}

# Refuse incomplete source images before touching the USB.
for required_source in \
  live/vmlinuz \
  live/initrd.img \
  live/filesystem.squashfs \
  payload/pip-rootfs.squashfs \
  payload/pip-rootfs.squashfs.sha256
do
  [[ -s "$IMG_MOUNT/$required_source" ]] || {
    echo "Installer image is incomplete: missing $required_source" >&2
    exit 1
  }
done

sed "s/LIVE_MEDIA_ID/$LIVE_MEDIA_ID/" \
  "$PROJECT_ROOT/build/live-syslinux/syslinux.cfg.in" > "$EXPECTED_CFG"

# Wipe and create one active FAT32 partition starting at sector 2048.
wipefs --all --force "$DEVICE" >/dev/null 2>&1 || true
sgdisk --zap-all "$DEVICE" >/dev/null 2>&1 || true
partprobe "$DEVICE" >/dev/null 2>&1 || true
parted -s "$DEVICE" mklabel msdos
parted -s "$DEVICE" mkpart primary fat32 2048s 100%
parted -s "$DEVICE" set 1 boot on
partprobe "$DEVICE"
sleep 1
# Whole-disk device names ending in a digit (mmc/nvme style) use p1; sdX uses 1.
case "$DEVICE" in
  *[0-9]) USB_PART="${DEVICE}p1" ;;
  *) USB_PART="${DEVICE}1" ;;
esac
[[ -b "$USB_PART" ]] || { echo "USB partition did not appear: $USB_PART" >&2; exit 1; }
mkfs.vfat -F 32 -n GREIA "$USB_PART"

mount "$USB_PART" "$USB_MOUNT"
USB_MOUNTED=1

# Lay out the live media per the postmortem recipe: live files at partition
# root, installable payload under payload/, identity/build metadata under .disk/.
install -m 0644 "$IMG_MOUNT/live/vmlinuz" "$USB_MOUNT/vmlinuz"
install -m 0644 "$IMG_MOUNT/live/initrd.img" "$USB_MOUNT/initrd.img"
install -m 0644 "$IMG_MOUNT/live/filesystem.squashfs" "$USB_MOUNT/filesystem.squashfs"
install -d -m 0755 "$USB_MOUNT/payload"
install -m 0644 "$IMG_MOUNT/payload/"* "$USB_MOUNT/payload/"
install -d -m 0755 "$USB_MOUNT/.disk"
printf '%s\n' "$LIVE_MEDIA_ID" > "$USB_MOUNT/.disk/live-uuid"
chmod 0644 "$USB_MOUNT/.disk/live-uuid"
if [[ -f "$IMG_MOUNT/.disk/installer-image-profile.json" ]]; then
  install -m 0644 "$IMG_MOUNT/.disk/installer-image-profile.json" \
    "$USB_MOUNT/.disk/installer-image-profile.json"
fi

# Syslinux: VBR on the partition, MBR on the device. Stock SYSLINUX prints its
# own copyright line before config parsing; the form-feed-only DISPLAY file
# clears that unavoidable line immediately once syslinux.cfg is available.
install -d -m 0755 "$USB_MOUNT/boot/syslinux"
if [[ -d /usr/lib/syslinux/modules/bios ]]; then
  cp /usr/lib/syslinux/modules/bios/*.c32 "$USB_MOUNT/boot/syslinux/" 2>/dev/null || true
fi
install -m 0644 \
  "$PROJECT_ROOT/build/live-syslinux/clear.msg" \
  "$USB_MOUNT/boot/syslinux/clear.msg"
install -m 0644 "$EXPECTED_CFG" "$USB_MOUNT/boot/syslinux/syslinux.cfg"
syslinux --install --directory /boot/syslinux "$USB_PART"
[[ -s "$USB_MOUNT/boot/syslinux/ldlinux.sys" ]] || {
  echo "Syslinux installation did not create ldlinux.sys." >&2
  exit 1
}

sync
umount "$USB_MOUNT"
USB_MOUNTED=0

# Install only the standard Syslinux bootstrap area, preserving the partition
# table bytes after offset 440.
dd if=/usr/lib/syslinux/mbr/mbr.bin of="$DEVICE" bs=440 count=1 conv=fsync 2>/dev/null
sync
partprobe "$DEVICE" 2>/dev/null || true

# FAT integrity must be clean before we trust a read-back comparison.
fsck.vfat -n "$USB_PART" >/dev/null || {
  echo "Final USB FAT32 filesystem did not pass read-only fsck." >&2
  exit 1
}

# Verify the media that will actually be unplugged and booted, not merely the
# source image. Re-mount read-only and compare every boot-critical copied byte.
mount -o ro "$USB_PART" "$USB_MOUNT"
USB_MOUNTED=1
for mapping in \
  "live/vmlinuz:vmlinuz" \
  "live/initrd.img:initrd.img" \
  "live/filesystem.squashfs:filesystem.squashfs"
do
  source_rel="${mapping%%:*}"
  usb_rel="${mapping#*:}"
  cmp -s "$IMG_MOUNT/$source_rel" "$USB_MOUNT/$usb_rel" || {
    echo "USB read-back mismatch: $usb_rel" >&2
    exit 1
  }
done

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
cmp -s "$PROJECT_ROOT/build/live-syslinux/clear.msg" "$USB_MOUNT/boot/syslinux/clear.msg" || {
  echo "USB read-back mismatch: boot/syslinux/clear.msg" >&2
  exit 1
}
[[ "$(tr -d '\r\n' < "$USB_MOUNT/.disk/live-uuid")" == "$LIVE_MEDIA_ID" ]] || {
  echo "USB read-back mismatch: live media identity" >&2
  exit 1
}
[[ -s "$USB_MOUNT/boot/syslinux/ldlinux.sys" ]] || {
  echo "USB read-back lost Syslinux ldlinux.sys." >&2
  exit 1
}

umount "$USB_MOUNT"
USB_MOUNTED=0

# Verify that the bytes actually written into the device's MBR bootstrap area
# match Syslinux. cmp stops after the first 440 bytes and never reads partition
# table/signature bytes that are intentionally device-specific.
cmp -n 440 /usr/lib/syslinux/mbr/mbr.bin "$DEVICE" || {
  echo "USB MBR bootstrap read-back does not match Syslinux mbr.bin." >&2
  exit 1
}

IMAGE_SHA="$(sha256sum "$IMAGE" | awk '{print $1}')"
LIVE_SHA="$(sha256sum "$IMG_MOUNT/live/filesystem.squashfs" | awk '{print $1}')"
PAYLOAD_SHA="$(sha256sum "$IMG_MOUNT/payload/pip-rootfs.squashfs" | awk '{print $1}')"

echo "Greia syslinux/FAT32 live USB ready on $DEVICE"
echo "  usb_flash_verification=PASS"
echo "  source_installer_sha256=$IMAGE_SHA"
echo "  live_filesystem_sha256=$LIVE_SHA"
echo "  target_payload_sha256=$PAYLOAD_SHA"
echo "  live_media_id=$LIVE_MEDIA_ID"
echo "  bootloader=syslinux (VBR) + mbr.bin (MBR)"
echo "  NOTE: device may be re-detected; identify it before unplugging."
