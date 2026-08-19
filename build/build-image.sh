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
Usage: sudo build/build-image.sh PROFILE [OUTPUT_DIR]

PROFILE may be a profile name from build/profiles without .toml, or a TOML path.
The script creates a raw BIOS-bootable disk image. It must run on a Debian or
Ubuntu build host as root and requires debootstrap, parted, losetup, mkfs.ext4,
and grub-install.
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

# Parse/validate declarative profile data before any disk mutation. The helper
# emits only shell-quoted assignments from a typed schema; the profile itself
# is never sourced or executed.
profile_assignments="$(python3 "$PROFILE_TOOL" shell "$PROFILE_PATH")"
eval "$profile_assignments"
python3 "$PROFILE_TOOL" --package-root "$PACKAGE_SET_ROOT" validate "$PROFILE_PATH" >/dev/null
python3 "$PROFILE_TOOL" check-phase0-builder "$PROFILE_PATH" --scope target >/dev/null

# Boot-cover release eligibility follows the declared boot adapter rather than
# a builder-global assumption so a future accepted backend can be selected per
# image family. No backend is release-safe until its physical acceptance gate
# passes.
if [[ "${PIP_RELEASE_BUILD:-0}" == "1" ]]; then
  if ! release_error="$(python3 "$PROFILE_TOOL" check-release "$PROFILE_PATH" 2>&1)"; then
    echo "Release build refused: $release_error" >&2
    exit 1
  fi
fi

current_build_date="$(date -u +%F)"
if [[ "$current_build_date" > "$SUPPORT_END_DATE" ]]; then
  echo "Profile $PROFILE_ID passed its declared security-support end date $SUPPORT_END_DATE; refusing build." >&2
  exit 1
fi

OUTPUT_DIR="${2:-$PROJECT_ROOT/out}"
mkdir -p "$OUTPUT_DIR"
OUTPUT_DIR="$(realpath "$OUTPUT_DIR")"
IMAGE="$OUTPUT_DIR/greia-os-${PROFILE_ID}.img"
REPORT="$OUTPUT_DIR/greia-os-${PROFILE_ID}-footprint.txt"
RECOVERY_CODE_REPORT="$OUTPUT_DIR/greia-os-${PROFILE_ID}-grub-recovery-code.txt"
PROFILE_MANIFEST_REPORT="$OUTPUT_DIR/greia-os-${PROFILE_ID}-image-profile.json"
BUILD_DIR="$(mktemp -d -p "${TMPDIR:-/tmp}" greia-build.XXXXXX)"
ROOTFS="$BUILD_DIR/rootfs"
DECLARED_PROFILE_MANIFEST="$BUILD_DIR/image-profile.json"
python3 "$PROFILE_TOOL" manifest "$PROFILE_PATH" --scope target > "$DECLARED_PROFILE_MANIFEST"
LOOP_DEVICE=""
MOUNTS=()

cleanup() {
  local original_status=$?
  set +e
  local cleanup_failed=0
  safe_unmount_paths "${MOUNTS[@]}" || cleanup_failed=1
  safe_detach_loop "$LOOP_DEVICE" || cleanup_failed=1
  if (( cleanup_failed == 0 )); then
    safe_remove_build_dir "$BUILD_DIR" || cleanup_failed=1
  fi
  if (( cleanup_failed != 0 )); then
    echo "Build cleanup was incomplete. Inspect and detach resources manually; no recursive deletion was attempted." >&2
    if (( original_status == 0 )); then
      return 1
    fi
  fi
  return "$original_status"
}
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

require_commands=(debootstrap parted partx blockdev losetup mkfs.ext4 blkid grub-install grub-script-check grub-mkpasswd-pbkdf2 chroot mount umount mountpoint findmnt udevadm rsync python3)
for command_name in "${require_commands[@]}"; do
  command -v "$command_name" >/dev/null || {
    echo "Missing build dependency: $command_name" >&2
    echo "On Debian/Ubuntu: apt install debootstrap parted e2fsprogs grub-pc-bin grub-common rsync" >&2
    exit 1
  }
done

host_arch="$(uname -m)"
case "$ARCH:$host_arch" in
  i386:x86_64|i386:i?86|amd64:x86_64) ;;
  *)
    echo "Profile architecture $ARCH cannot be executed safely on build host $host_arch." >&2
    echo "Use an x86_64 Debian/Ubuntu VM for Acer and modern image builds." >&2
    exit 1
    ;;
esac

rm -f "$IMAGE" "$REPORT" "$RECOVERY_CODE_REPORT" "$PROFILE_MANIFEST_REPORT"
truncate -s "${IMAGE_SIZE_MIB}M" "$IMAGE"
parted -s "$IMAGE" mklabel msdos
parted -s "$IMAGE" mkpart primary ext4 1MiB 100%
parted -s "$IMAGE" set 1 boot on
LOOP_DEVICE="$(losetup --find --show --partscan "$IMAGE")"
partition="${LOOP_DEVICE}p1"
for _ in {1..20}; do
  [[ -b "$partition" ]] && break
  sleep 0.2
done
[[ -b "$partition" ]] || { echo "Loop partition did not appear: $partition" >&2; exit 1; }
mkfs.ext4 -q -F -m 1 -L PIP_ROOT "$partition"
root_uuid="$(blkid -s UUID -o value -- "$partition")"
[[ "$root_uuid" =~ ^[0-9a-fA-F-]{32,36}$ ]] || { echo "Could not read a valid root filesystem UUID." >&2; exit 1; }
mkdir -p "$ROOTFS"
mount "$partition" "$ROOTFS"
MOUNTS+=("$ROOTFS")

echo "Bootstrapping Debian $SUITE $ARCH..."
[[ -r "$DEBIAN_ARCHIVE_KEYRING" ]] || { echo "Pinned Debian archive keyring is missing: $DEBIAN_ARCHIVE_KEYRING" >&2; exit 1; }
debootstrap --arch="$ARCH" --variant=minbase --include=ca-certificates --keyring="$DEBIAN_ARCHIVE_KEYRING" --force-check-gpg "$SUITE" "$ROOTFS" "$MIRROR"
resolved_arch="$(chroot "$ROOTFS" /usr/bin/dpkg --print-architecture)"
[[ "$resolved_arch" == "$ARCH" ]] || { echo "Bootstrapped architecture $resolved_arch does not match profile $ARCH." >&2; exit 1; }

# Apply size policy before installing the runtime package set.
# Repository checkout ownership is never target-filesystem authority.
# Static appliance overlay files are installed as root regardless of the UID/GID
# of the developer or CI checkout that produced the image.
rsync -a --chown=root:root "$PROJECT_ROOT/build/overlay/" "$ROOTFS/"
[[ "$(stat -c '%u:%g' "$ROOTFS")" == "0:0" ]] || {
  echo "Greia overlay changed target root ownership away from root:root." >&2
  exit 1
}
PROJECT_VERSION="$(tr -d '\r\n' < "$PROJECT_ROOT/VERSION")"
[[ -n "$PROJECT_VERSION" ]] || { echo "VERSION is empty." >&2; exit 1; }
install -d -m 0755 "$ROOTFS/etc/greia-os"
cat > "$ROOTFS/etc/greia-os/build-info" <<BUILDINFO
GREIA_OS_VERSION=$PROJECT_VERSION
PIP_RUNTIME_API=0.1
PIP_BUILD_PHASE=phase0
PIP_BUILD_PROFILE=$PROFILE_ID
PIP_PLATFORM_FAMILY=$PLATFORM_FAMILY
PIP_COMPATIBILITY_CLASS=$COMPATIBILITY_CLASS
PIP_RUNTIME_FAMILIES=$RUNTIME_FAMILIES
PIP_DISPLAY_ADAPTER=$DISPLAY_ADAPTER
PIP_BOOT_ADAPTER=$INSTALLED_BOOT_ADAPTER
PIP_BOOT_COVER_BACKEND=$BOOT_COVER_BACKEND
BUILDINFO
install -m 0644 "$DECLARED_PROFILE_MANIFEST" "$ROOTFS/etc/greia-os/image-profile.json"

cat > "$ROOTFS/etc/apt/sources.list" <<SOURCES
deb $MIRROR $SUITE main non-free-firmware
deb $MIRROR $SUITE-updates main non-free-firmware
deb $SECURITY_MIRROR $SUITE-security main non-free-firmware
SOURCES
printf '%s\n' "$HOSTNAME" > "$ROOTFS/etc/hostname"
cat > "$ROOTFS/etc/hosts" <<HOSTS
127.0.0.1 localhost
127.0.1.1 $HOSTNAME
::1 localhost ip6-localhost ip6-loopback
HOSTS

for virtual in dev proc sys run; do
  mkdir -p "$ROOTFS/$virtual"
done
mount --rbind /dev "$ROOTFS/dev"; MOUNTS+=("$ROOTFS/dev"); mount --make-rslave "$ROOTFS/dev"
mount -t proc proc "$ROOTFS/proc"; MOUNTS+=("$ROOTFS/proc")
mount --rbind /sys "$ROOTFS/sys"; MOUNTS+=("$ROOTFS/sys"); mount --make-rslave "$ROOTFS/sys"
# /run is tmpfs at runtime; a fresh mount avoids carrying the build host's
# desktop-session mounts (gvfs/portal under /run/user/1000) into the chroot,
# which would keep the build busy and block teardown. Seed a resolver stub so
# chroot apt/DNS still works while sharing the host network namespace.
mount -t tmpfs tmpfs "$ROOTFS/run"; MOUNTS+=("$ROOTFS/run")
install -d -m 0755 "$ROOTFS/run/systemd/resolve"
cat /etc/resolv.conf > "$ROOTFS/run/systemd/resolve/stub-resolv.conf" 2>/dev/null || true

APT_ACQUIRE_OPTIONS=(
  -o Acquire::Retries=3
  -o Acquire::http::Timeout=20
  -o Acquire::https::Timeout=20
)

package_output="$(python3 "$PROFILE_TOOL" --package-root "$PACKAGE_SET_ROOT" packages "$PROFILE_PATH" --scope target)"
mapfile -t packages <<< "$package_output"
(( ${#packages[@]} > 0 )) || { echo "Resolved target package set is empty." >&2; exit 1; }

printf 'grub-pc grub-pc/install_devices_empty boolean true\n' | chroot "$ROOTFS" debconf-set-selections
chroot "$ROOTFS" /usr/bin/env DEBIAN_FRONTEND=noninteractive apt-get "${APT_ACQUIRE_OPTIONS[@]}" update
# Greia intentionally pre-seeds appliance conffiles in the overlay. dpkg's
# conffile prompt is independent of debconf, so make product ownership explicit.
chroot "$ROOTFS" /usr/bin/env DEBIAN_FRONTEND=noninteractive \
  apt-get "${APT_ACQUIRE_OPTIONS[@]}" -o Dpkg::Options::=--force-confold install -y --no-install-recommends "${packages[@]}"

# Appliance users have no passwords. pipprofiles owns the bounded profile
# registry/tree shared by the launcher and typed parent profile controls;
# pipsettings owns only bounded input/display preference state.
chroot "$ROOTFS" groupadd --system pipsettings
chroot "$ROOTFS" groupadd --system pipprofiles
chroot "$ROOTFS" useradd --system --create-home --home-dir /var/lib/greia-kid \
  --shell /usr/sbin/nologin --user-group --groups pipsettings,pipprofiles greiakid
chroot "$ROOTFS" useradd --system --create-home --home-dir /var/lib/greia-os \
  --shell /usr/sbin/nologin --user-group --groups pipsettings,pipprofiles greiapanel
chroot "$ROOTFS" useradd --create-home --home-dir /var/lib/greia-admin \
  --shell /bin/bash --groups sudo greiaadmin
chroot "$ROOTFS" passwd --lock greiaadmin
# The managed greia account is the owner-approved development/admin SSH and
# Greia Parents identity. Base images keep it locked and SSH disabled; explicit
# developer provisioning sets the greia/greia login on dev images only.
chroot "$ROOTFS" useradd --create-home --home-dir /var/lib/greia \
  --shell /bin/bash --groups sudo greia
chroot "$ROOTFS" passwd --lock greia

install -d -m 0755 "$ROOTFS/opt/greia-os"
rsync -a --delete --exclude '__pycache__' \
  "$PROJECT_ROOT/src" "$PROJECT_ROOT/activities" "$PROJECT_ROOT/runtime" \
  "$ROOTFS/opt/greia-os/"
install -d -m 0755 "$ROOTFS/opt/greia-os/assets"
rsync -a --delete \
  --exclude 'source/' \
  --exclude '*contact_sheet*' \
  "$PROJECT_ROOT/assets/" "$ROOTFS/opt/greia-os/assets/"

install -d -m 0755 "$ROOTFS/usr/lib/python3/dist-packages"
printf '%s\n' '/opt/greia-os/src' > "$ROOTFS/usr/lib/python3/dist-packages/pip_os.pth"
chown -R root:root "$ROOTFS/opt/greia-os"
chmod -R a-w "$ROOTFS/opt/greia-os"

# Root filesystem and volatile working storage.
cat > "$ROOTFS/etc/fstab" <<FSTAB
UUID=$root_uuid / ext4 defaults,noatime,errors=remount-ro 0 1
tmpfs /tmp tmpfs nosuid,nodev,noexec,mode=1777,size=64M 0 0
tmpfs /var/tmp tmpfs nosuid,nodev,noexec,mode=1777,size=32M 0 0
FSTAB

# Build the Greia-owned early framebuffer boot cover for the TARGET
# architecture inside the target root. The binary is compiled with the target
# klibc toolchain so the build host architecture is never authoritative. The
# build-only libklibc-dev package is removed again before package-manifest and
# footprint capture so it cannot leak into the final image.
build_early_framebuffer() {
  local rootfs="$1"
  # klcc needs the matching native compiler (e.g. i686-linux-gnu-gcc) which is
  # provided by the gcc package; install it together with libklibc-dev so the
  # target toolchain can actually compile. Both are removed again afterwards.
  chroot "$rootfs" /usr/bin/env DEBIAN_FRONTEND=noninteractive \
    apt-get "${APT_ACQUIRE_OPTIONS[@]}" -o Dpkg::Options::=--force-confold \
    install -y --no-install-recommends libklibc-dev gcc >/dev/null
  install -d -m 0755 "$rootfs/usr/lib/greia-boot"
  # Stage the renderer source into the target root so the target toolchain
  # compiles it with target headers. klcc is a gcc wrapper that links against
  # klibc; its path differs across Debian/Ubuntu, so locate it inside the root.
  install -d -m 0755 "$rootfs/usr/src/greia-boot"
  cp "$PROJECT_ROOT/build/early-boot/greia-fb-splash.c" \
    "$rootfs/usr/src/greia-boot/greia-fb-splash.c"
  local klcc_path
  klcc_path="$(chroot "$rootfs" /bin/sh -c 'command -v klcc')" || {
    echo "klcc not found in target root after libklibc-dev install." >&2
    exit 1
  }
  chroot "$rootfs" "$klcc_path" -static -Os -s \
    -o /usr/lib/greia-boot/greia-fb-splash \
    /usr/src/greia-boot/greia-fb-splash.c
  rm -rf "$rootfs/usr/src/greia-boot"
  chmod 0755 "$rootfs/usr/lib/greia-boot/greia-fb-splash"
  # Verify the produced binary matches the target architecture before it can
  # ever reach an initramfs. The target is a chroot; readelf must run outside.
  elf_machine="$(readelf -h "$rootfs/usr/lib/greia-boot/greia-fb-splash" 2>/dev/null \
    | awk '/Machine:/{print $2, $3}')"
  case "$ARCH" in
    i386)
      [ "$elf_machine" = "Intel 80386" ] || {
        echo "Early framebuffer helper architecture ($elf_machine) does not match i386 target." >&2
        exit 1
      }
      ;;
    amd64)
      [ "$elf_machine" = "Advanced Micro" ] || [ "$elf_machine" = "AMD x86-64" ] || {
        echo "Early framebuffer helper architecture ($elf_machine) does not match amd64 target." >&2
        exit 1
      }
      ;;
  esac
  chroot "$rootfs" /usr/bin/env DEBIAN_FRONTEND=noninteractive \
    apt-get "${APT_ACQUIRE_OPTIONS[@]}" -y remove --purge libklibc-dev gcc >/dev/null
  chroot "$rootfs" apt-get -y autoremove >/dev/null 2>&1 || true
}

build_early_framebuffer "$ROOTFS"

systemctl --root="$ROOTFS" enable \
  greia-first-boot.service greia-launcher.service greia-parent.service \
  systemd-networkd.service systemd-resolved.service iwd.service avahi-daemon.service
systemctl --root="$ROOTFS" mask \
  getty@.service autovt@.service console-getty.service debug-shell.service \
  emergency.service rescue.service console-shell.service kbrequest.target \
  getty@tty1.service getty@tty2.service getty@tty3.service \
  getty@tty4.service getty@tty5.service getty@tty6.service
systemctl --root="$ROOTFS" set-default graphical.target

# The base image builder fails closed: SSH disabled, no password minted, the
# managed greia account locked. For an explicit developer-remote profile the
# owner policy requires the greia/greia development login to be reachable after
# install, so the builder provisions it here (root stays denied). This makes the
# owner-approved developer image reproducible instead of depending on a separate
# manual provisioning step. Normal/release profiles remain closed.
systemctl --root="$ROOTFS" disable ssh.service 2>/dev/null || true
install -d -m 0755 "$ROOTFS/etc/ssh/sshd_config.d"
cat > "$ROOTFS/etc/ssh/sshd_config.d/20-greia-parent.conf" <<'SSH'
PasswordAuthentication no
KbdInteractiveAuthentication no
AuthenticationMethods publickey
PermitRootLogin no
X11Forwarding no
AllowTcpForwarding no
PermitTunnel no
SSH

provision_developer_ssh() {
  local rootfs="$1"
  # The greia account already exists in build-image.sh (created and locked);
  # unlock it and set the owner-approved development password.
  chroot "$rootfs" /usr/sbin/passwd -u greia
  printf 'greia:greia\n' | chroot "$rootfs" /usr/sbin/chpasswd
  cat > "$rootfs/etc/ssh/sshd_config.d/00-greia-security-floor.conf" <<'FLOOR'
# Target development security floor (owner-approved greia/greia).
# Enables the development/test SSH identity greia/greia; root stays denied.
PasswordAuthentication yes
KbdInteractiveAuthentication yes
PermitRootLogin no
AuthenticationMethods publickey,password
DenyUsers root
AllowUsers greia
FLOOR
  chmod 0644 "$rootfs/etc/ssh/sshd_config.d/00-greia-security-floor.conf"
  systemctl --root="$rootfs" enable ssh.service
  # Developer marker: keeps the installed boot observable (console=tty1,
  # panic=30) via grub.d/10_greia_appliance and identifies this image as a
  # developer/test build.
  install -d -m 0755 "$rootfs/etc/greia-os"
  printf '%s\n' "profile=$PROFILE_ID" > "$rootfs/etc/greia-os/developer-remote"
  chmod 0644 "$rootfs/etc/greia-os/developer-remote"
}

target_sets="$(python3 "$PROFILE_TOOL" --package-root "$PACKAGE_SET_ROOT" package-sets "$PROFILE_PATH" --scope target 2>/dev/null)"
if [[ "$target_sets" == *developer-remote* ]]; then
  echo "Developer target profile: enabling greia/greia SSH (root denied)."
  provision_developer_ssh "$ROOTFS"
fi

# Record the exact package/kernel base actually resolved by APT. Profiles use
# Debian suite names and meta-packages, so this manifest is the authoritative
# identity of a produced image until snapshot-pinned builds are introduced.
install -d -m 0755 "$ROOTFS/etc/greia-os"
chroot "$ROOTFS" dpkg-query -W -f='${Package}\t${Version}\t${Architecture}\t${Installed-Size}\n' \
  | LC_ALL=C sort > "$ROOTFS/etc/greia-os/package-manifest.tsv"
{
  echo "profile=$PROFILE_ID"
  echo "certification_state=$CERTIFICATION_STATE"
  echo "platform_family=$PLATFORM_FAMILY"
  echo "compatibility_class=$COMPATIBILITY_CLASS"
  echo "image_layout=$IMAGE_LAYOUT"
  echo "installed_boot_adapter=$INSTALLED_BOOT_ADAPTER"
  echo "display_adapter=$DISPLAY_ADAPTER"
  echo "enabled_runtime_families=$RUNTIME_FAMILIES"
  echo "suite=$SUITE"
  echo "architecture=$ARCH"
  echo "kernel_meta_package=$KERNEL_PACKAGE"
  echo "declared_support_end_date=$SUPPORT_END_DATE"
  echo "root_filesystem_uuid=$root_uuid"
  echo "debian_version=$(cat "$ROOTFS/etc/debian_version")"
  echo "resolved_kernel_packages=$(chroot "$ROOTFS" dpkg-query -W -f='${Package}=${Version} ' 'linux-image-*' 2>/dev/null || true)"
  echo "resolved_xorg_packages=$(chroot "$ROOTFS" dpkg-query -W -f='${Package}=${Version} ' 'xserver-xorg-*' 2>/dev/null || true)"
} > "$ROOTFS/etc/greia-os/base-system-manifest"
support_status_exit=0
chroot "$ROOTFS" check-support-status --no-heading \
  > "$ROOTFS/etc/greia-os/security-support-status.txt" 2>&1 || support_status_exit=$?
if (( support_status_exit != 0 )); then
  security_support_state="probe-failed"
  echo "WARNING: Debian security-support probe failed with exit $support_status_exit; the image must not be released until reviewed." >&2
elif [[ -s "$ROOTFS/etc/greia-os/security-support-status.txt" ]]; then
  security_support_state="alerts-present"
  echo "WARNING: Debian reports packages with limited or ended security support; inspect security-support-status.txt before testing or release." >&2
else
  security_support_state="no-alerts"
fi
{
  echo "build_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo "mirror=$MIRROR"
  echo "security_mirror=$SECURITY_MIRROR"
  echo "security_support_state=$security_support_state"
  echo "security_support_probe_exit=$support_status_exit"
} >> "$ROOTFS/etc/greia-os/base-system-manifest"
chmod 0644 "$ROOTFS/etc/greia-os/package-manifest.tsv" \
  "$ROOTFS/etc/greia-os/base-system-manifest" \
  "$ROOTFS/etc/greia-os/security-support-status.txt"

# Avoid package/cache growth and persistent logs on the 7 GB reference disk.
chroot "$ROOTFS" apt-get clean
rm -rf "$ROOTFS/var/lib/apt/lists/"* "$ROOTFS/var/cache/apt/archives/"*.deb
find "$ROOTFS" -xdev -type d -name __pycache__ -prune -exec rm -rf '{}' +
find "$ROOTFS/var/log" -type f -exec truncate -s 0 '{}' +

# Generate a per-image recovery credential. Normal boot remains automatic;
# GRUB command/edit access requires this root-only code.
printf '%s\n' "$root_uuid" > "$ROOTFS/etc/greia-os/root-filesystem-uuid"
chmod 0644 "$ROOTFS/etc/greia-os/root-filesystem-uuid"
PYTHONPATH="$PROJECT_ROOT/src" python3 -m greia_platform.grub_security "$ROOTFS" --copy-code-to "$RECOVERY_CODE_REPORT"
# Only the appliance scripts may generate boot entries. This prevents update-grub
# from reintroducing recovery, alternate-init, or unauthenticated entries.
find "$ROOTFS/etc/grub.d" -maxdepth 1 -type f -exec chmod a-x '{}' +
chmod 0755 "$ROOTFS/etc/grub.d/00_header"   "$ROOTFS/etc/grub.d/01_greia_auth" "$ROOTFS/etc/grub.d/10_greia_appliance"
# GRUB presents the canonical white Greia frame while the kernel/initramfs
# loads. The PNG is the same derivative used by the early framebuffer cover
# and launcher intro, so the child sees one continuous branded frame.
install -d -m 0755 "$ROOTFS/boot/grub"
install -m 0644 "$PROJECT_ROOT/assets/boot/static/greia-boot-logo.png" \
  "$ROOTFS/boot/grub/greia-boot-logo.png"
chroot "$ROOTFS" update-initramfs -u -k all
chroot "$ROOTFS" update-grub
chroot "$ROOTFS" grub-script-check /boot/grub/grub.cfg
BOOT_CONTRACT_ARGS=()
if [[ "$target_sets" == *developer-remote* ]]; then
  BOOT_CONTRACT_ARGS+=(--developer)
fi
PYTHONPATH="$PROJECT_ROOT/src" python3 -m greia_platform.boot_contract \
  "${BOOT_CONTRACT_ARGS[@]}" "$ROOTFS/boot/grub/grub.cfg"
chroot "$ROOTFS" grub-install --target=i386-pc --boot-directory=/boot --recheck "$LOOP_DEVICE"

# Raw images and installer payloads are cloned. Leave all identity material empty;
# first boot creates the machine ID, while SSH keys are generated only when a
# parent explicitly enables SSH.
: > "$ROOTFS/etc/machine-id"
rm -f "$ROOTFS/var/lib/dbus/machine-id" "$ROOTFS/var/lib/systemd/random-seed"
rm -f "$ROOTFS/etc/ssh/ssh_host_"*

sync
installed_bytes="$(du -sx --block-size=1 "$ROOTFS" | awk '{print $1}')"
filesystem_used_bytes="$(df -B1 --output=used "$ROOTFS" | awk 'NR == 2 { gsub(/[[:space:]]/, "", $1); print $1 }')"
[[ "$filesystem_used_bytes" =~ ^[0-9]+$ ]] || { echo "Could not measure filesystem-used bytes." >&2; exit 1; }
accounted_bytes="$installed_bytes"
if (( filesystem_used_bytes > accounted_bytes )); then
  accounted_bytes="$filesystem_used_bytes"
fi
installed_mib="$(( installed_bytes / 1024 / 1024 ))"
filesystem_used_mib="$(( filesystem_used_bytes / 1024 / 1024 ))"
accounted_mib="$(( accounted_bytes / 1024 / 1024 ))"
{
  echo "profile=$PROFILE_ID"
  echo "certification_state=$CERTIFICATION_STATE"
  echo "platform_family=$PLATFORM_FAMILY"
  echo "compatibility_class=$COMPATIBILITY_CLASS"
  echo "image_layout=$IMAGE_LAYOUT"
  echo "installed_boot_adapter=$INSTALLED_BOOT_ADAPTER"
  echo "display_adapter=$DISPLAY_ADAPTER"
  echo "enabled_runtime_families=$RUNTIME_FAMILIES"
  echo "suite=$SUITE"
  echo "architecture=$ARCH"
  echo "kernel_meta_package=$KERNEL_PACKAGE"
  echo "declared_support_end_date=$SUPPORT_END_DATE"
  echo "root_filesystem_uuid=$root_uuid"
  echo "debian_version=$(cat "$ROOTFS/etc/debian_version")"
  echo "resolved_kernel_packages=$(chroot "$ROOTFS" dpkg-query -W -f='${Package}=${Version} ' 'linux-image-*' 2>/dev/null || true)"
  echo "image_size_mib=$IMAGE_SIZE_MIB"
  echo "installed_bytes=$installed_bytes"
  echo "filesystem_used_bytes=$filesystem_used_bytes"
  echo "accounted_bytes=$accounted_bytes"
  echo "installed_mib=$installed_mib"
  echo "filesystem_used_mib=$filesystem_used_mib"
  echo "accounted_mib=$accounted_mib"
  echo "preferred_limit_mib=$PREFERRED_LIMIT_MIB"
  echo "required_limit_mib=$REQUIRED_LIMIT_MIB"
  echo "architecture_review_limit_mib=$ARCHITECTURE_REVIEW_LIMIT_MIB"
  echo "declared_profile_manifest=$PROFILE_MANIFEST_REPORT"
  echo "declared_profile_manifest_sha256=$(sha256sum "$DECLARED_PROFILE_MANIFEST" | awk '{print $1}')"
  echo "boot_cover_backend=$BOOT_COVER_BACKEND"
  echo "security_support_state=$security_support_state"
  echo "security_support_probe_exit=$support_status_exit"
  echo "grub_recovery_code=$RECOVERY_CODE_REPORT"
  echo
  echo "Largest top-level paths:"
  du -x --block-size=1M --max-depth=2 "$ROOTFS" 2>/dev/null | sort -nr | head -40
  echo
  echo "Installed packages:"
  chroot "$ROOTFS" dpkg-query -W -f='${Installed-Size}\t${Package}\t${Version}\n' | sort -nr
} > "$REPORT"

required_limit_bytes=$((REQUIRED_LIMIT_MIB * 1024 * 1024))
preferred_limit_bytes=$((PREFERRED_LIMIT_MIB * 1024 * 1024))
if (( accounted_bytes >= required_limit_bytes )); then
  echo "FAIL: accounted installed filesystem use is ${accounted_mib} MiB (file data ${installed_mib} MiB, filesystem used ${filesystem_used_mib} MiB); profile $PROFILE_ID requires <${REQUIRED_LIMIT_MIB} MiB." >&2
  exit 1
fi
if (( accounted_bytes > preferred_limit_bytes )); then
  echo "WARNING: accounted installed filesystem use is ${accounted_mib} MiB; profile preferred target is <=${PREFERRED_LIMIT_MIB} MiB." >&2
fi

install -m 0644 "$DECLARED_PROFILE_MANIFEST" "$PROFILE_MANIFEST_REPORT"
sync
echo "Created: $IMAGE"
echo "Declared image profile: $PROFILE_MANIFEST_REPORT"
echo "Footprint: $REPORT"
echo "Root-only GRUB recovery code: $RECOVERY_CODE_REPORT"
echo "Installed files: ${installed_mib} MiB"
echo "Filesystem used: ${filesystem_used_mib} MiB"
echo "Budgeted/accounted: ${accounted_mib} MiB"
