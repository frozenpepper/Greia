#!/usr/bin/env bash
set -Eeuo pipefail
# Build a syslinux/FAT32 live USB from a Greia installer image.
#
# The reference Acer BIOS does not execute GRUB's MBR from a USB stick but
# does execute the antiX-style syslinux MBR+VBR on an active FAT32 partition
# (see docs/engineering/boot/INSTALLATION_USB_BOOT_POSTMORTEM.md). This tool turns an already
# built `greia-os-installer-*.img` into that media layout on a removable USB
# device, copying the live kernel/initrd/root, the installable payload and the
# live-media identity marker.
#
# Usage: sudo tools/build-live-usb.sh <installer.img> <device>
#   <installer.img>  path to a built greia-os-installer-*.img
#   <device>         the whole removable USB device (e.g. /dev/sdd) to overwrite

PROJECT_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
# shellcheck source=../build/lib/safe-cleanup.sh
source "$PROJECT_ROOT/build/lib/safe-cleanup.sh"
# shellcheck source=../build/lib/live-syslinux.sh
source "$PROJECT_ROOT/build/lib/live-syslinux.sh"
# shellcheck source=../build/lib/installer-image-root.sh
source "$PROJECT_ROOT/build/lib/installer-image-root.sh"

usage() {
  cat <<'USAGE'
Usage: sudo tools/build-live-usb.sh <installer.img> <device>

Builds a syslinux/FAT32 live USB from a Greia installer image.
This DESTROYS the target device. Only pass a removable USB whole-disk device.
USAGE
}

[[ $# -eq 2 ]] || { usage >&2; exit 2; }
[[ ${EUID:-$(id -u)} -eq 0 ]] || { echo "Run as root." >&2; exit 1; }

IMAGE="$1"
DEVICE="$2"

required=(losetup partx blockdev blkid udevadm findmnt partprobe wipefs sgdisk parted mkfs.vfat syslinux sync mount umount mountpoint cp dd)
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

WORK="$(mktemp -d -p "${TMPDIR:-/tmp}" greia-live-usb.XXXXXX)"
IMG_MOUNT="$WORK/img"
USB_MOUNT="$WORK/usb"
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
  safe_cleanup_exit "$original_status" "$cleanup_failed" "Live-USB writer cleanup was incomplete; preserving work data for inspection."
}
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

# Mount the installer image ext4 root read-only to source the live files.
IMG_LOOP="$(losetup --find --show --partscan "$IMAGE")"
IMG_PART="$(greia_installer_root_partition "$IMG_LOOP")" || {
  echo "Installer image ext4 root partition did not appear." >&2
  exit 1
}
mount -o ro "$IMG_PART" "$IMG_MOUNT"

# Extract the live media id from the image's own marker.
LIVE_MEDIA_ID="$(tr -d '\r\n' < "$IMG_MOUNT/.disk/live-uuid" 2>/dev/null || true)"
[[ "$LIVE_MEDIA_ID" =~ ^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$ ]] || {
  echo "Installer image is missing a valid .disk/live-uuid." >&2
  exit 1
}
# Console policy comes from the image's own declared manifest (quiet RC media
# vs the diagnostic developer template); resolve it before wiping anything.
LIVE_CONSOLE_POLICY="$(greia_live_console_policy "$IMG_MOUNT")"
SYSLINUX_TEMPLATE="$(greia_live_syslinux_template "$PROJECT_ROOT" "$LIVE_CONSOLE_POLICY")"
[[ -r "$SYSLINUX_TEMPLATE" ]] || { echo "Syslinux template missing: $SYSLINUX_TEMPLATE" >&2; exit 1; }

# Wipe and create one active FAT32 partition starting at sector 2048.
wipefs --all --force "$DEVICE" >/dev/null 2>&1 || true
sgdisk --zap-all "$DEVICE" >/dev/null 2>&1 || true
partprobe "$DEVICE" >/dev/null 2>&1 || true
parted -s "$DEVICE" mklabel msdos
parted -s "$DEVICE" mkpart primary fat32 2048s 100%
parted -s "$DEVICE" set 1 boot on
partprobe "$DEVICE"
sleep 1
USB_PART="${DEVICE}1"
[[ -b "$USB_PART" ]] || { echo "USB partition did not appear: $USB_PART" >&2; exit 1; }
mkfs.vfat -F 32 -n GREIA "$USB_PART"

mount "$USB_PART" "$USB_MOUNT"

# Lay out the live media per the postmortem recipe: live files at partition
# root, installable payload under payload/, identity marker under .disk/.
install -m 0644 "$IMG_MOUNT/live/vmlinuz" "$USB_MOUNT/vmlinuz"
install -m 0644 "$IMG_MOUNT/live/initrd.img" "$USB_MOUNT/initrd.img"
install -m 0644 "$IMG_MOUNT/live/filesystem.squashfs" "$USB_MOUNT/filesystem.squashfs"
install -d -m 0755 "$USB_MOUNT/payload"
install -m 0644 "$IMG_MOUNT/payload/"* "$USB_MOUNT/payload/"
install -d -m 0755 "$USB_MOUNT/.disk"
printf '%s\n' "$LIVE_MEDIA_ID" > "$USB_MOUNT/.disk/live-uuid"
chmod 0644 "$USB_MOUNT/.disk/live-uuid"

# syslinux: VBR on the partition, MBR on the device.
install -d -m 0755 "$USB_MOUNT/boot/syslinux"
if [ -d /usr/lib/syslinux/modules/bios ]; then
  cp /usr/lib/syslinux/modules/bios/*.c32 "$USB_MOUNT/boot/syslinux/" 2>/dev/null || true
fi
sed "s/LIVE_MEDIA_ID/$LIVE_MEDIA_ID/" \
  "$SYSLINUX_TEMPLATE" \
  > "$USB_MOUNT/boot/syslinux/syslinux.cfg"
chmod 0644 "$USB_MOUNT/boot/syslinux/syslinux.cfg"
# The quiet template consumes the owner-approved one-byte form-feed display
# file so the stock SYSLINUX banner cannot stay on screen through the quiet
# kernel/initramfs phase. The diagnostic template must not reference it; its
# media simply does not carry the file. Keep the writer template-driven so the
# presentation decision stays in the config, not here.
if grep -q '^DISPLAY /boot/syslinux/clear\.msg$' "$USB_MOUNT/boot/syslinux/syslinux.cfg"; then
  [[ -s "$PROJECT_ROOT/build/live-syslinux/clear.msg" ]] || {
    echo "Syslinux clear display file missing: $PROJECT_ROOT/build/live-syslinux/clear.msg" >&2
    exit 1
  }
  install -m 0644 "$PROJECT_ROOT/build/live-syslinux/clear.msg" \
    "$USB_MOUNT/boot/syslinux/clear.msg"
fi
syslinux --install --directory /boot/syslinux "$USB_PART"

sync
umount "$USB_MOUNT"
dd if=/usr/lib/syslinux/mbr/mbr.bin of="$DEVICE" bs=440 count=1 2>/dev/null
sync
partprobe "$DEVICE" 2>/dev/null || true

echo "Greia syslinux/FAT32 live USB ready on $DEVICE"
echo "  live_media_id=$LIVE_MEDIA_ID"
echo "  live_console_policy=$LIVE_CONSOLE_POLICY"
echo "  bootloader=syslinux (VBR) + mbr.bin (MBR)"
echo "  NOTE: device may be re-detected; identify it before unplugging."
