#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd -- "$SCRIPT_DIR/.." && pwd)"
# shellcheck source=lib/safe-cleanup.sh
source "$SCRIPT_DIR/lib/safe-cleanup.sh"

PROFILE_TOOL="$PROJECT_ROOT/tools/build_profile.py"
PACKAGE_SET_ROOT="$SCRIPT_DIR/package-sets"
DEBIAN_ARCHIVE_KEYRING="$PROJECT_ROOT/build/trust/debian-archive-keyring-2025.1.gpg"

usage() {
  cat <<'USAGE'
Usage: sudo build/build-installer-image.sh PROFILE [OUTPUT_DIR]

Builds a BIOS-bootable USB image that starts the graphical Greia OS
installer automatically and carries a compressed target-system payload.
Run only on a Debian/Ubuntu x86 build host or VM.
USAGE
}

[[ $# -ge 1 && $# -le 2 ]] || { usage >&2; exit 2; }
[[ ${EUID:-$(id -u)} -eq 0 ]] || { echo "Run as root." >&2; exit 1; }

profile_input="$1"
if [[ -f "$profile_input" ]]; then
  PROFILE_PATH="$(realpath "$profile_input")"
else
  PROFILE_PATH="$SCRIPT_DIR/profiles/${profile_input%.toml}.toml"
fi
[[ -r "$PROFILE_PATH" ]] || { echo "Profile not found: $PROFILE_PATH" >&2; exit 1; }
[[ "$PROFILE_PATH" == *.toml ]] || {
  echo "Build profiles are declarative TOML; executable .env profiles are no longer accepted: $PROFILE_PATH" >&2
  exit 1
}
profile_assignments="$(python3 "$PROFILE_TOOL" shell "$PROFILE_PATH")"
eval "$profile_assignments"
python3 "$PROFILE_TOOL" --package-root "$PACKAGE_SET_ROOT" validate "$PROFILE_PATH" >/dev/null
python3 "$PROFILE_TOOL" check-phase0-builder "$PROFILE_PATH" --scope installer >/dev/null
if [[ "${PIP_RELEASE_BUILD:-0}" == "1" ]]; then
  if ! release_error="$(python3 "$PROFILE_TOOL" check-release "$PROFILE_PATH" 2>&1)"; then
    echo "Release build refused: $release_error" >&2
    exit 1
  fi
fi

OUTPUT_DIR="${2:-$PROJECT_ROOT/out}"
mkdir -p "$OUTPUT_DIR"
OUTPUT_DIR="$(realpath "$OUTPUT_DIR")"
OUTPUT_IMAGE="$OUTPUT_DIR/greia-os-installer-${PROFILE_ID}.img"
REPORT="$OUTPUT_DIR/greia-os-installer-${PROFILE_ID}-report.txt"
INSTALLER_PROFILE_REPORT="$OUTPUT_DIR/greia-os-installer-${PROFILE_ID}-image-profile.json"
PAYLOAD_PROFILE_REPORT="$OUTPUT_DIR/greia-os-${PROFILE_ID}-payload-image-profile.json"
HARDWARE_SUPPORT_REPORT="$OUTPUT_DIR/greia-os-installer-${PROFILE_ID}-hardware-support.json"
BUILD_DIR="$(mktemp -d -p "${TMPDIR:-/tmp}" greia-installer-build.XXXXXX)"
INSTALLER_PROFILE_MANIFEST="$BUILD_DIR/installer-image-profile.json"
python3 "$PROFILE_TOOL" manifest "$PROFILE_PATH" --scope installer > "$INSTALLER_PROFILE_MANIFEST"
TARGET_OUT="$BUILD_DIR/target-out"
TARGET_MOUNT="$BUILD_DIR/target-root"
LIVE_ROOT="$BUILD_DIR/live-root"
USB_MOUNT="$BUILD_DIR/usb"
TARGET_LOOP=""
USB_LOOP=""
MOUNTS=()

cleanup() {
  local original_status=$?
  set +e
  local cleanup_failed=0
  safe_unmount_paths "${MOUNTS[@]}" || cleanup_failed=1
  safe_detach_loop "$TARGET_LOOP" || cleanup_failed=1
  safe_detach_loop "$USB_LOOP" || cleanup_failed=1
  if (( cleanup_failed == 0 )); then
    safe_remove_build_dir "$BUILD_DIR" || cleanup_failed=1
  fi
  if (( cleanup_failed != 0 )); then
    echo "Installer-image cleanup was incomplete. Inspect resources manually; build data was preserved." >&2
    if (( original_status == 0 )); then
      return 1
    fi
  fi
  return "$original_status"
}
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

required=(debootstrap parted partx blockdev losetup mkfs.ext4 blkid grub-install grub-script-check grub-mkpasswd-pbkdf2 chroot mount umount mountpoint findmnt udevadm rsync mksquashfs python3 dpkg-deb)
for command_name in "${required[@]}"; do
  command -v "$command_name" >/dev/null || {
    echo "Missing build dependency: $command_name" >&2
    echo "Install: debootstrap parted e2fsprogs grub-pc-bin grub-common rsync squashfs-tools" >&2
    exit 1
  }
done

host_arch="$(uname -m)"
case "$ARCH:$host_arch" in
  i386:x86_64|i386:i?86|amd64:x86_64) ;;
  *)
    echo "Profile architecture $ARCH cannot be executed safely on build host $host_arch." >&2
    echo "Use an x86_64 Debian/Ubuntu VM for installer image builds." >&2
    exit 1
    ;;
esac

mkdir -p "$TARGET_OUT" "$TARGET_MOUNT" "$LIVE_ROOT" "$USB_MOUNT"
"$SCRIPT_DIR/build-image.sh" "$PROFILE_PATH" "$TARGET_OUT"
TARGET_IMAGE="$TARGET_OUT/greia-os-${PROFILE_ID}.img"
TARGET_FOOTPRINT="$TARGET_OUT/greia-os-${PROFILE_ID}-footprint.txt"
TARGET_PROFILE_MANIFEST="$TARGET_OUT/greia-os-${PROFILE_ID}-image-profile.json"
[[ -r "$TARGET_PROFILE_MANIFEST" ]] || { echo "Target image profile manifest missing." >&2; exit 1; }
cp "$TARGET_FOOTPRINT" "$OUTPUT_DIR/greia-os-${PROFILE_ID}-payload-footprint.txt"
cp "$TARGET_PROFILE_MANIFEST" "$PAYLOAD_PROFILE_REPORT"
TARGET_LOOP="$(losetup --find --show --partscan "$TARGET_IMAGE")"
TARGET_PART="${TARGET_LOOP}p1"
for _ in {1..20}; do [[ -b "$TARGET_PART" ]] && break; sleep 0.2; done
[[ -b "$TARGET_PART" ]] || { echo "Target image partition did not appear." >&2; exit 1; }
mount -o ro,noload "$TARGET_PART" "$TARGET_MOUNT"
MOUNTS+=("$TARGET_MOUNT")
TARGET_PAYLOAD="$BUILD_DIR/pip-rootfs.squashfs"
TARGET_PAYLOAD_DIGEST="$BUILD_DIR/pip-rootfs.squashfs.sha256"
mksquashfs "$TARGET_MOUNT" "$TARGET_PAYLOAD" -comp xz -b 256K -noappend >/dev/null
payload_sha256="$(sha256sum "$TARGET_PAYLOAD" | awk '{print $1}')"
printf '%s  %s\n' "$payload_sha256" 'pip-rootfs.squashfs' > "$TARGET_PAYLOAD_DIGEST"
umount "$TARGET_MOUNT"
MOUNTS=()
losetup -d "$TARGET_LOOP"
TARGET_LOOP=""

# Build the live installer environment. It is allowed to be substantially
# larger than the installed target because broad hardware support belongs on
# removable installation media, not permanently on low-storage child devices.
[[ -r "$DEBIAN_ARCHIVE_KEYRING" ]] || { echo "Pinned Debian archive keyring is missing: $DEBIAN_ARCHIVE_KEYRING" >&2; exit 1; }
debootstrap --arch="$ARCH" --variant=minbase --include=ca-certificates --keyring="$DEBIAN_ARCHIVE_KEYRING" --force-check-gpg "$SUITE" "$LIVE_ROOT" "$MIRROR"
live_arch="$(chroot "$LIVE_ROOT" /usr/bin/dpkg --print-architecture)"
[[ "$live_arch" == "$ARCH" ]] || { echo "Live root architecture $live_arch does not match profile $ARCH." >&2; exit 1; }
# Repository checkout ownership is never live-image filesystem authority.
rsync -a --chown=root:root "$SCRIPT_DIR/installer-overlay/" "$LIVE_ROOT/"
[[ "$(stat -c '%u:%g' "$LIVE_ROOT")" == "0:0" ]] || {
  echo "Greia installer overlay changed live root ownership away from root:root." >&2
  exit 1
}
cat > "$LIVE_ROOT/etc/apt/sources.list" <<SOURCES
deb $MIRROR $SUITE main non-free-firmware
deb $MIRROR $SUITE-updates main non-free-firmware
deb $SECURITY_MIRROR $SUITE-security main non-free-firmware
SOURCES
printf '%s\n' greia-installer > "$LIVE_ROOT/etc/hostname"
cat > "$LIVE_ROOT/etc/hosts" <<'HOSTS'
127.0.0.1 localhost
127.0.1.1 greia-installer
::1 localhost ip6-localhost ip6-loopback
HOSTS
for virtual in dev proc sys run; do mkdir -p "$LIVE_ROOT/$virtual"; done
mount --rbind /dev "$LIVE_ROOT/dev"; MOUNTS+=("$LIVE_ROOT/dev"); mount --make-rslave "$LIVE_ROOT/dev"
mount -t proc proc "$LIVE_ROOT/proc"; MOUNTS+=("$LIVE_ROOT/proc")
mount --rbind /sys "$LIVE_ROOT/sys"; MOUNTS+=("$LIVE_ROOT/sys"); mount --make-rslave "$LIVE_ROOT/sys"
# /run is always tmpfs at runtime; a fresh mount here avoids carrying the
# build host's desktop-session mounts (for example gvfs/portal under
# /run/user/1000) into the live root, which would keep the build busy and
# block teardown. Seed a resolver stub so chroot apt/DNS still works while
# the build shares the host network namespace.
mount -t tmpfs tmpfs "$LIVE_ROOT/run"; MOUNTS+=("$LIVE_ROOT/run")
install -d -m 0755 "$LIVE_ROOT/run/systemd/resolve"
cat /etc/resolv.conf > "$LIVE_ROOT/run/systemd/resolve/stub-resolv.conf" 2>/dev/null || true

# The live-media UUID must exist before the kernel package postinst runs
# update-initramfs during the apt install below: the installer overlay's
# greia-live-media-id initramfs hook embeds it and fails closed when absent.
install -d -m 0755 "$LIVE_ROOT/etc/greia-os"
live_media_id="$(python3 - <<'PYUUID'
import uuid
print(uuid.uuid4())
PYUUID
)"
[[ "$live_media_id" =~ ^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$ ]] || {
  echo "Generated live-media identifier is invalid." >&2
  exit 1
}
printf '%s\n' "$live_media_id" > "$LIVE_ROOT/etc/greia-os/live-media-id"
chmod 0644 "$LIVE_ROOT/etc/greia-os/live-media-id"

APT_ACQUIRE_OPTIONS=(
  -o Acquire::Retries=3
  -o Acquire::http::Timeout=20
  -o Acquire::https::Timeout=20
)

package_output="$(python3 "$PROFILE_TOOL" --package-root "$PACKAGE_SET_ROOT" packages "$PROFILE_PATH" --scope installer)"
mapfile -t packages <<< "$package_output"
(( ${#packages[@]} > 0 )) || { echo "Resolved installer package set is empty." >&2; exit 1; }
chroot "$LIVE_ROOT" /usr/bin/env DEBIAN_FRONTEND=noninteractive apt-get "${APT_ACQUIRE_OPTIONS[@]}" update
# Keep intentionally pre-seeded Greia conffiles without any dpkg prompt.
chroot "$LIVE_ROOT" /usr/bin/env DEBIAN_FRONTEND=noninteractive \
  apt-get "${APT_ACQUIRE_OPTIONS[@]}" -o Dpkg::Options::=--force-confold install -y --no-install-recommends "${packages[@]}"

# ADR 0021: freeze a broad signed Debian firmware/microcode repository on the
# installer while APT metadata is current, then install the verified firmware
# class into the live root for reliable coldplug. The final target later gets
# only machine-specific packages selected from the same frozen repository.
"$SCRIPT_DIR/populate-hardware-support-pool.sh" "$LIVE_ROOT" "$SUITE" "$ARCH"
"$SCRIPT_DIR/install-live-hardware-firmware.sh" "$LIVE_ROOT" "$SUITE" "$ARCH"
cp "$LIVE_ROOT/opt/greia-hardware-support/manifest.json" "$HARDWARE_SUPPORT_REPORT"
hardware_support_pool_bytes="$(python3 - "$HARDWARE_SUPPORT_REPORT" <<'PY'
import json
import sys
from pathlib import Path
print(json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))["total_bytes"])
PY
)"
hardware_support_package_count="$(python3 - "$HARDWARE_SUPPORT_REPORT" <<'PY'
import json
import sys
from pathlib import Path
print(json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))["package_count"])
PY
)"

install -d -m 0755 "$LIVE_ROOT/opt/greia-os"
rsync -a --delete --exclude '__pycache__' "$PROJECT_ROOT/src" "$PROJECT_ROOT/runtime" "$LIVE_ROOT/opt/greia-os/"
install -d -m 0755 "$LIVE_ROOT/opt/greia-os/assets/icons/core/v1/256"
rsync -a "$PROJECT_ROOT/assets/icons/core/v1/256/" "$LIVE_ROOT/opt/greia-os/assets/icons/core/v1/256/"
install -d -m 0755 "$LIVE_ROOT/usr/lib/python3/dist-packages"
printf '%s\n' /opt/greia-os/src > "$LIVE_ROOT/usr/lib/python3/dist-packages/pip_os.pth"
chown -R root:root "$LIVE_ROOT/opt/greia-os"
chmod -R a-w "$LIVE_ROOT/opt/greia-os"

GREIA_PLYMOUTH_THEME="$PROJECT_ROOT/build/overlay/etc/plymouth/themes/greia"

test -f "$GREIA_PLYMOUTH_THEME/greia.plymouth"
test -f "$GREIA_PLYMOUTH_THEME/greia.script"
test -f "$GREIA_PLYMOUTH_THEME/frames/frame_0000.png"
test -f "$GREIA_PLYMOUTH_THEME/frames/frame_0051.png"

install -d -m 0755 "$LIVE_ROOT/usr/share/plymouth/themes/greia"
rsync -a --delete \
  "$GREIA_PLYMOUTH_THEME/" \
  "$LIVE_ROOT/usr/share/plymouth/themes/greia/"

chroot "$LIVE_ROOT" plymouth-set-default-theme greia
systemctl --root="$LIVE_ROOT" enable greia-installer.service
systemctl --root="$LIVE_ROOT" mask getty@.service autovt@.service console-getty.service debug-shell.service emergency.service rescue.service console-shell.service kbrequest.target getty@tty1.service getty@tty2.service getty@tty3.service getty@tty4.service getty@tty5.service getty@tty6.service plymouth-quit.service plymouth-quit-wait.service
systemctl --root="$LIVE_ROOT" set-default graphical.target

# Development-only remote access to the live installer. A developer profile
# gets default-on SSH with the operator password greia/greia and mDNS hostname
# greia-installer-dev.local so the running installer can be reached remotely.
# Normal/release profiles keep the installer closed (no SSH).
installer_sets="$(python3 "$PROFILE_TOOL" --package-root "$PACKAGE_SET_ROOT" package-sets "$PROFILE_PATH" --scope installer)"
is_dev_profile=0
while IFS= read -r set_name; do
  if [[ "$set_name" == "developer-remote" ]]; then
    is_dev_profile=1
  fi
done <<< "$installer_sets"

if (( is_dev_profile == 1 )); then
  printf '%s\n' greia-installer-dev > "$LIVE_ROOT/etc/hostname"
  sed -i 's/^127\.0\.1\.1.*/127.0.1.1 greia-installer-dev/' "$LIVE_ROOT/etc/hosts"
  systemctl --root="$LIVE_ROOT" enable ssh.service
  chroot "$LIVE_ROOT" useradd --create-home --home-dir /home/greia \
    --shell /bin/bash --groups sudo greia || true
  printf 'greia:%s\n' '$6$greia$TEhNljS36HiJeyK9YiqY73aN2tQMksMsa0hKREgRmgwnd4IzVmzTU0hpcgR13HN9kfEiMzv.4GxWGgIl.AQsc/' \
    > "$LIVE_ROOT/tmp/greia-passwd-entry"
  printf 'root:%s\n' '$6$greia$TEhNljS36HiJeyK9YiqY73aN2tQMksMsa0hKREgRmgwnd4IzVmzTU0hpcgR13HN9kfEiMzv.4GxWGgIl.AQsc/' \
    >> "$LIVE_ROOT/tmp/greia-passwd-entry"
  chroot "$LIVE_ROOT" chpasswd -e < "$LIVE_ROOT/tmp/greia-passwd-entry" 2>/dev/null || true
  rm -f "$LIVE_ROOT/tmp/greia-passwd-entry"
  install -d -m 0755 "$LIVE_ROOT/etc/ssh/sshd_config.d"
  cat > "$LIVE_ROOT/etc/ssh/sshd_config.d/20-greia-parent.conf" <<'SSH'
PasswordAuthentication yes
KbdInteractiveAuthentication no
PermitRootLogin yes
AllowUsers greia root
X11Forwarding no
AllowTcpForwarding no
PermitTunnel no
SSH
fi

# The live installer is a second Debian root, not merely a wrapper around the
# target payload. Record and audit its exact resolved package/kernel base too.
PROJECT_VERSION="$(tr -d '\r\n' < "$PROJECT_ROOT/VERSION")"
[[ -n "$PROJECT_VERSION" ]] || { echo "VERSION is empty." >&2; exit 1; }
install -d -m 0755 "$LIVE_ROOT/etc/greia-os"
install -m 0644 "$TARGET_PAYLOAD_DIGEST" "$LIVE_ROOT/etc/greia-os/expected-payload.sha256"
cat > "$LIVE_ROOT/etc/greia-os/build-info" <<BUILDINFO
GREIA_OS_VERSION=$PROJECT_VERSION
PIP_RUNTIME_API=0.1
PIP_BUILD_PHASE=phase0-live-installer
PIP_BUILD_PROFILE=$PROFILE_ID
PIP_PLATFORM_FAMILY=$PLATFORM_FAMILY
PIP_COMPATIBILITY_CLASS=$COMPATIBILITY_CLASS
PIP_RUNTIME_FAMILIES=$RUNTIME_FAMILIES
PIP_DISPLAY_ADAPTER=$DISPLAY_ADAPTER
PIP_BOOT_ADAPTER=$INSTALLER_BOOT_ADAPTER
PIP_BOOT_COVER_BACKEND=$BOOT_COVER_BACKEND
BUILDINFO
install -m 0644 "$INSTALLER_PROFILE_MANIFEST" "$LIVE_ROOT/etc/greia-os/image-profile.json"
install -m 0644 "$TARGET_PROFILE_MANIFEST" "$LIVE_ROOT/etc/greia-os/target-image-profile.json"
chroot "$LIVE_ROOT" dpkg-query -W -f='${Package}\t${Version}\t${Architecture}\t${Installed-Size}\n' \
  | LC_ALL=C sort > "$LIVE_ROOT/etc/greia-os/package-manifest.tsv"
{
  echo "profile=$PROFILE_ID"
  echo "certification_state=$CERTIFICATION_STATE"
  echo "platform_family=$PLATFORM_FAMILY"
  echo "compatibility_class=$COMPATIBILITY_CLASS"
  echo "image_layout=$IMAGE_LAYOUT"
  echo "installer_boot_adapter=$INSTALLER_BOOT_ADAPTER"
  echo "display_adapter=$DISPLAY_ADAPTER"
  echo "enabled_runtime_families=$RUNTIME_FAMILIES"
  echo "suite=$SUITE"
  echo "architecture=$ARCH"
  echo "kernel_meta_package=$KERNEL_PACKAGE"
  echo "declared_support_end_date=$SUPPORT_END_DATE"
  echo "debian_version=$(cat "$LIVE_ROOT/etc/debian_version")"
  echo "resolved_kernel_packages=$(chroot "$LIVE_ROOT" dpkg-query -W -f='${Package}=${Version} ' 'linux-image-*' 2>/dev/null || true)"
  echo "resolved_xorg_packages=$(chroot "$LIVE_ROOT" dpkg-query -W -f='${Package}=${Version} ' 'xserver-xorg-*' 2>/dev/null || true)"
  echo "hardware_support_pool_packages=$hardware_support_package_count"
  echo "hardware_support_pool_bytes=$hardware_support_pool_bytes"
  echo "build_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo "mirror=$MIRROR"
  echo "security_mirror=$SECURITY_MIRROR"
} > "$LIVE_ROOT/etc/greia-os/base-system-manifest"
live_support_status_exit=0
chroot "$LIVE_ROOT" check-support-status --no-heading \
  > "$LIVE_ROOT/etc/greia-os/security-support-status.txt" 2>&1 || live_support_status_exit=$?
if (( live_support_status_exit != 0 )); then
  live_security_support_state="probe-failed"
  echo "WARNING: live-installer security-support probe failed with exit $live_support_status_exit." >&2
elif [[ -s "$LIVE_ROOT/etc/greia-os/security-support-status.txt" ]]; then
  live_security_support_state="alerts-present"
  echo "WARNING: live installer includes packages with limited or ended security support." >&2
else
  live_security_support_state="no-alerts"
fi
{
  echo "security_support_state=$live_security_support_state"
  echo "security_support_probe_exit=$live_support_status_exit"
} >> "$LIVE_ROOT/etc/greia-os/base-system-manifest"
chmod 0644 "$LIVE_ROOT/etc/greia-os/build-info" \
  "$LIVE_ROOT/etc/greia-os/package-manifest.tsv" \
  "$LIVE_ROOT/etc/greia-os/base-system-manifest" \
  "$LIVE_ROOT/etc/greia-os/security-support-status.txt"
cp "$LIVE_ROOT/etc/greia-os/package-manifest.tsv" "$OUTPUT_DIR/greia-os-installer-${PROFILE_ID}-live-package-manifest.tsv"
cp "$LIVE_ROOT/etc/greia-os/base-system-manifest" "$OUTPUT_DIR/greia-os-installer-${PROFILE_ID}-live-base-system-manifest.txt"
cp "$LIVE_ROOT/etc/greia-os/security-support-status.txt" "$OUTPUT_DIR/greia-os-installer-${PROFILE_ID}-live-security-support-status.txt"

chroot "$LIVE_ROOT" apt-get clean
rm -rf "$LIVE_ROOT/var/lib/apt/lists/"* "$LIVE_ROOT/var/cache/apt/archives/"*.deb
find "$LIVE_ROOT" -xdev -type d -name __pycache__ -prune -exec rm -rf '{}' +
chroot "$LIVE_ROOT" update-initramfs -u -k all
kernel_name="$(find "$LIVE_ROOT/boot" -maxdepth 1 -type f -name 'vmlinuz-*' -printf '%f\n' | sort -V | tail -1)"
[[ -n "$kernel_name" ]] || { echo "Live kernel missing." >&2; exit 1; }
kernel_version="${kernel_name#vmlinuz-}"
KERNEL_PATH="$LIVE_ROOT/boot/$kernel_name"
INITRD_PATH="$LIVE_ROOT/boot/initrd.img-$kernel_version"
[[ -r "$KERNEL_PATH" && -r "$INITRD_PATH" ]] || { echo "Matching live kernel/initrd missing for $kernel_version." >&2; exit 1; }
INITRD_CHECK_DIR="$LIVE_ROOT/tmp/pip-initrd-check"
rm -rf "$INITRD_CHECK_DIR"
chroot "$LIVE_ROOT" unmkinitramfs "/boot/initrd.img-$kernel_version" /tmp/pip-initrd-check
mapfile -t embedded_uuid_files < <(find "$INITRD_CHECK_DIR" -type f -path '*/conf/uuid.conf' -print)
(( ${#embedded_uuid_files[@]} == 1 )) || {
  echo "Expected exactly one embedded live-media UUID; found ${#embedded_uuid_files[@]}." >&2
  exit 1
}
embedded_live_media_id="$(tr -d '\r\n' < "${embedded_uuid_files[0]}")"
[[ "$embedded_live_media_id" == "$live_media_id" ]] || {
  echo "Embedded live-media UUID does not match the image identifier." >&2
  exit 1
}
rm -rf "$INITRD_CHECK_DIR"

# Release chroot mounts before compressing. Never compress across a live bind.
safe_unmount_paths "${MOUNTS[@]}" || { echo "Cannot detach live-root mounts." >&2; exit 1; }
MOUNTS=()
LIVE_SQUASH="$BUILD_DIR/live-filesystem.squashfs"
mksquashfs "$LIVE_ROOT" "$LIVE_SQUASH" -comp xz -b 256K -noappend >/dev/null

payload_mib="$(( ($(stat -c %s "$TARGET_PAYLOAD") + $(stat -c %s "$LIVE_SQUASH") + 1048575) / 1048576 ))"
image_mib="$(( payload_mib + 256 ))"
(( image_mib < 1024 )) && image_mib=1024
rm -f "$OUTPUT_IMAGE" "$REPORT"
truncate -s "${image_mib}M" "$OUTPUT_IMAGE"
parted -s "$OUTPUT_IMAGE" mklabel msdos
parted -s "$OUTPUT_IMAGE" mkpart primary ext4 1MiB 100%
parted -s "$OUTPUT_IMAGE" set 1 boot on
USB_LOOP="$(losetup --find --show --partscan "$OUTPUT_IMAGE")"
USB_PART="${USB_LOOP}p1"
for _ in {1..20}; do [[ -b "$USB_PART" ]] && break; sleep 0.2; done
[[ -b "$USB_PART" ]] || { echo "Installer image partition did not appear." >&2; exit 1; }
mkfs.ext4 -q -F -m 0 -L PIP_INSTALL "$USB_PART"
usb_root_uuid="$(blkid -s UUID -o value -- "$USB_PART")"
[[ "$usb_root_uuid" =~ ^[0-9a-fA-F-]{32,36}$ ]] || { echo "Could not read installer filesystem UUID." >&2; exit 1; }
mount "$USB_PART" "$USB_MOUNT"
MOUNTS+=("$USB_MOUNT")
install -d "$USB_MOUNT/live" "$USB_MOUNT/payload" "$USB_MOUNT/boot/grub" "$USB_MOUNT/.disk"
cp "$LIVE_SQUASH" "$USB_MOUNT/live/filesystem.squashfs"
cp "$KERNEL_PATH" "$USB_MOUNT/live/vmlinuz"
cp "$INITRD_PATH" "$USB_MOUNT/live/initrd.img"
cp "$TARGET_PAYLOAD" "$USB_MOUNT/payload/pip-rootfs.squashfs"
cp "$TARGET_PAYLOAD_DIGEST" "$USB_MOUNT/payload/pip-rootfs.squashfs.sha256"
# Removable installer media carries only declarative, non-executable build
# metadata. The old shell-sourced profile.env representation is intentionally
# gone so profile selection cannot become a code-execution/configuration seam.
cp "$TARGET_PROFILE_MANIFEST" "$USB_MOUNT/payload/target-image-profile.json"
cp "$INSTALLER_PROFILE_MANIFEST" "$USB_MOUNT/.disk/installer-image-profile.json"
printf '%s\n' "$live_media_id" > "$USB_MOUNT/.disk/live-uuid"
chmod 0644 "$USB_MOUNT/.disk/live-uuid"
INSTALLER_GRUB_SECURITY_ROOT="$BUILD_DIR/installer-grub-security"
INSTALLER_RECOVERY_CODE="$OUTPUT_DIR/greia-os-installer-${PROFILE_ID}-grub-recovery-code.txt"
mkdir -p "$INSTALLER_GRUB_SECURITY_ROOT"
PYTHONPATH="$PROJECT_ROOT/src" python3 -m greia_platform.grub_security   "$INSTALLER_GRUB_SECURITY_ROOT" --copy-code-to "$INSTALLER_RECOVERY_CODE"
installer_grub_hash="$(cat "$INSTALLER_GRUB_SECURITY_ROOT/etc/greia-os/grub-recovery.pbkdf2")"
cat > "$USB_MOUNT/boot/grub/grub.cfg" <<GRUB
set timeout=0
set timeout_style=hidden
set default=0
set pager=0
set superusers="greia-recovery"
export superusers
password_pbkdf2 greia-recovery $installer_grub_hash
menuentry "Install Greia OS" --unrestricted --id greia-installer {
  search --no-floppy --fs-uuid --set=root $usb_root_uuid
  linux /live/vmlinuz boot=live components live-media-path=/live live-media-timeout=15 nopersistence noeject silent overlay-size=128M greia.live_media_id=$live_media_id quiet splash loglevel=0 console=null panic=5 systemd.show_status=false rd.systemd.show_status=false systemd.crash_shell=no systemd.crash_chvt=0 udev.log_priority=3 vt.global_cursor_default=0 consoleblank=0
  initrd /live/initrd.img
}
GRUB
grub-script-check "$USB_MOUNT/boot/grub/grub.cfg"
PYTHONPATH="$PROJECT_ROOT/src" python3 -m greia_platform.boot_contract --live-installer "$USB_MOUNT/boot/grub/grub.cfg"
grub-install --target=i386-pc --boot-directory="$USB_MOUNT/boot" --recheck "$USB_LOOP"
sync
safe_unmount_paths "$USB_MOUNT" || { echo "Cannot detach completed installer filesystem." >&2; exit 1; }
MOUNTS=()
safe_detach_loop "$USB_LOOP" || { echo "Cannot detach completed installer loop device." >&2; exit 1; }
USB_LOOP=""

install -m 0644 "$INSTALLER_PROFILE_MANIFEST" "$INSTALLER_PROFILE_REPORT"

{
  echo "profile=$PROFILE_ID"
  echo "certification_state=$CERTIFICATION_STATE"
  echo "platform_family=$PLATFORM_FAMILY"
  echo "compatibility_class=$COMPATIBILITY_CLASS"
  echo "image_layout=$IMAGE_LAYOUT"
  echo "installer_boot_adapter=$INSTALLER_BOOT_ADAPTER"
  echo "display_adapter=$DISPLAY_ADAPTER"
  echo "enabled_runtime_families=$RUNTIME_FAMILIES"
  echo "architecture=$ARCH"
  echo "declared_support_end_date=$SUPPORT_END_DATE"
  echo "installer_image_mib=$image_mib"
  echo "live_squash_bytes=$(stat -c %s "$LIVE_SQUASH")"
  echo "target_payload_bytes=$(stat -c %s "$TARGET_PAYLOAD")"
  echo "target_payload_sha256=$payload_sha256"
  echo "embedded_payload_digest=/etc/greia-os/expected-payload.sha256"
  echo "live_media_id=$live_media_id"
  echo "live_media_marker=/.disk/live-uuid"
  echo "boot_cover_backend=$BOOT_COVER_BACKEND"
  echo "installer_profile_manifest=$INSTALLER_PROFILE_REPORT"
  echo "installer_profile_manifest_sha256=$(sha256sum "$INSTALLER_PROFILE_MANIFEST" | awk '{print $1}')"
  echo "payload_profile_manifest=$PAYLOAD_PROFILE_REPORT"
  echo "payload_profile_manifest_sha256=$(sha256sum "$TARGET_PROFILE_MANIFEST" | awk '{print $1}')"
  echo "hardware_support_manifest=$HARDWARE_SUPPORT_REPORT"
  echo "hardware_support_manifest_sha256=$(sha256sum "$HARDWARE_SUPPORT_REPORT" | awk '{print $1}')"
  echo "hardware_support_pool_packages=$hardware_support_package_count"
  echo "hardware_support_pool_bytes=$hardware_support_pool_bytes"
  echo "installer_grub_recovery_code=$INSTALLER_RECOVERY_CODE"
  echo "live_security_support_state=$live_security_support_state"
  echo "live_security_support_probe_exit=$live_support_status_exit"
  echo "live_package_manifest=$OUTPUT_DIR/greia-os-installer-${PROFILE_ID}-live-package-manifest.tsv"
  echo "live_base_system_manifest=$OUTPUT_DIR/greia-os-installer-${PROFILE_ID}-live-base-system-manifest.txt"
  echo "live_security_support_report=$OUTPUT_DIR/greia-os-installer-${PROFILE_ID}-live-security-support-status.txt"
  echo "payload_footprint_report=$OUTPUT_DIR/greia-os-${PROFILE_ID}-payload-footprint.txt"
  echo "output=$OUTPUT_IMAGE"
  echo "sha256=$(sha256sum "$OUTPUT_IMAGE" | awk '{print $1}')"
} > "$REPORT"

echo "Created graphical installer image: $OUTPUT_IMAGE"
echo "Hardware support manifest: $HARDWARE_SUPPORT_REPORT"
echo "Report: $REPORT"