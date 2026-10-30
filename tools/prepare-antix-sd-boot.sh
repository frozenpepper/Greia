#!/usr/bin/env bash
set -Eeuo pipefail

# Prepare an existing AntiX GRUB installation to boot the Greia live installer
# from the SD card this script is stored on. This does NOT erase/install Greia.
# It also collects one optional engineering evidence report onto the SD.

[[ ${EUID:-$(id -u)} -eq 0 ]] || {
  echo "Run this script with sudo/root from the mounted Greia SD." >&2
  echo "Example: sudo bash /media/.../greia-tools/prepare-antix-sd-boot.sh" >&2
  exit 1
}

SCRIPT_PATH="$(readlink -f "${BASH_SOURCE[0]}")"
TOOLS_DIR="$(dirname "$SCRIPT_PATH")"
MEDIA_ROOT="$(dirname "$TOOLS_DIR")"

required=(findmnt blkid update-grub grep install sync)
for command_name in "${required[@]}"; do
  command -v "$command_name" >/dev/null || {
    echo "Required AntiX command is missing: $command_name" >&2
    exit 1
  }
done

for path in \
  "$MEDIA_ROOT/live/vmlinuz" \
  "$MEDIA_ROOT/live/initrd.img" \
  "$MEDIA_ROOT/live/filesystem.squashfs" \
  "$MEDIA_ROOT/payload/greia-rootfs.squashfs" \
  "$MEDIA_ROOT/payload/greia-rootfs.squashfs.sha256" \
  "$MEDIA_ROOT/.disk/live-uuid"
do
  [[ -s "$path" ]] || {
    echo "Greia installer media is incomplete: missing $path" >&2
    exit 1
  }
done

SOURCE="$(findmnt -n -o SOURCE --target "$MEDIA_ROOT")"
[[ -n "$SOURCE" && -b "$SOURCE" ]] || {
  echo "Could not identify the block device backing the Greia SD mount: $MEDIA_ROOT" >&2
  exit 1
}
SD_UUID="$(blkid -s UUID -o value -- "$SOURCE")"
MEDIA_ID="$(tr -d '\r\n' < "$MEDIA_ROOT/.disk/live-uuid")"
[[ -n "$SD_UUID" && -n "$MEDIA_ID" ]] || {
  echo "Could not read the Greia SD filesystem UUID/live-media identifier." >&2
  exit 1
}

ROOT_SOURCE="$(findmnt -n -o SOURCE / || true)"
printf 'Greia SD mount: %s\n' "$MEDIA_ROOT"
printf 'Greia SD partition: %s\n' "$SOURCE"
printf 'Current AntiX root: %s\n' "$ROOT_SOURCE"
if [[ "$SOURCE" == "$ROOT_SOURCE" ]]; then
  echo "Refusing: the Greia media resolved to the current root filesystem." >&2
  exit 1
fi

# Evidence is deliberately non-authoritative and never controls image/profile
# selection. Failure to collect it does not prevent boot preparation.
EVIDENCE_TOOL="$TOOLS_DIR/collect-linux-hardware-evidence.sh"
if [[ -r "$EVIDENCE_TOOL" ]]; then
  mkdir -p "$MEDIA_ROOT/greia-evidence"
  if evidence_path="$(bash "$EVIDENCE_TOOL" "$MEDIA_ROOT/greia-evidence")"; then
    echo "Hardware evidence saved: $evidence_path"
  else
    echo "WARNING: optional hardware evidence collection failed; continuing." >&2
  fi
fi

[[ -f /boot/grub/grub.cfg ]] || {
  echo "AntiX GRUB2 configuration was not found at /boot/grub/grub.cfg." >&2
  echo "No boot configuration was changed." >&2
  exit 1
}

GRUB_SCRIPT=/etc/grub.d/42_greia_sd
BACKUP=""
if [[ -e "$GRUB_SCRIPT" ]]; then
  BACKUP="${GRUB_SCRIPT}.greia-backup.$(date -u +%Y%m%dT%H%M%SZ)"
  cp -a "$GRUB_SCRIPT" "$BACKUP"
  echo "Existing custom Greia GRUB script backed up to: $BACKUP"
fi

cat > "$GRUB_SCRIPT" <<EOF
#!/bin/sh
exec tail -n +3 \$0

menuentry 'Greia installer from SD' {
    insmod part_msdos
    insmod ext2
    search --no-floppy --fs-uuid --set=root $SD_UUID
    linux /live/vmlinuz boot=live components live-media-path=/live live-media-timeout=30 nopersistence noeject nonetworking silent overlay-size=128M greia.live_media_id=$MEDIA_ID quiet splash loglevel=0 console=tty1 panic=5 systemd.show_status=false rd.systemd.show_status=false systemd.crash_shell=no systemd.crash_chvt=0 udev.log_priority=3 vt.global_cursor_default=0 consoleblank=0
    initrd /live/initrd.img
}
EOF
chmod 0755 "$GRUB_SCRIPT"

if ! update-grub; then
  echo "update-grub failed; restoring the previous custom script state." >&2
  if [[ -n "$BACKUP" && -e "$BACKUP" ]]; then
    mv -f "$BACKUP" "$GRUB_SCRIPT"
  else
    rm -f "$GRUB_SCRIPT"
  fi
  update-grub >/dev/null 2>&1 || true
  exit 1
fi

if ! grep -Fq "Greia installer from SD" /boot/grub/grub.cfg; then
  echo "GRUB regeneration completed but the Greia entry is absent; refusing success." >&2
  exit 1
fi

sync
cat <<EOF

GREIA SD BOOT PREPARATION: PASS

The Acer/PC hardware did NOT choose the installer image; this generic
legacy-x86 media was built before seeing this machine.

Optional hardware evidence (if collection succeeded) is under:
  $MEDIA_ROOT/greia-evidence/

Leave the SD inserted and reboot. At the AntiX GRUB menu choose:
  Greia installer from SD

This preparation step did not erase the internal disk. Destructive disk changes
begin only later inside the Greia graphical installer after its own confirmation.
EOF
