#!/usr/bin/env bash
# Greia OS target image builder (thin role consumer).
#
# This script owns only target-role disk/boot assembly: raw disk
# create/partition/loop/mkfs/mount, the shared composition engine invocation
# for role `target` against the mounted target root, then the target-only
# installed-boot assembly and footprint/size policy. All generic composition
# blocks live in build/lib/compose.sh behind the explicit role-typed
# `compose_root --profile <id> --role target --root <path>` contract, shared
# with the T04 slot producer (and, via role `live-installer`, with T02).
set -Eeuo pipefail
# Privileged builders must never leave root-owned bytecode in the source
# tree: every Python invocation below inherits this (cf. greia_release.py).
export PYTHONDONTWRITEBYTECODE=1

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd -- "$SCRIPT_DIR/.." && pwd)"
# shellcheck source=lib/safe-cleanup.sh
source "$SCRIPT_DIR/lib/safe-cleanup.sh"
# shellcheck source=lib/apt-cache.sh
source "$SCRIPT_DIR/lib/apt-cache.sh"
# shellcheck source=lib/compose.sh
source "$SCRIPT_DIR/lib/compose.sh"

PROFILE_TOOL="$PROJECT_ROOT/tools/build_profile.py"

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

# Full typed profile resolution/validation plus the release gate and
# support-date guard run inside the shared composition engine before any disk
# mutation, so the thin consumer and the slot producer share one
# implementation. This also exports PROFILE_ID, IMAGE_SIZE_MIB and the
# footprint limits used for disk sizing below.
compose_resolve_profile "$PROFILE_PATH" "target" "$PROJECT_ROOT"

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
  trap - EXIT INT TERM
  set +e
  local cleanup_failed=0
  safe_unmount_paths "${MOUNTS[@]}" || cleanup_failed=1
  safe_detach_loop "$LOOP_DEVICE" || cleanup_failed=1
  if (( cleanup_failed == 0 )); then
    safe_remove_build_dir "$BUILD_DIR" || cleanup_failed=1
  fi
  safe_cleanup_exit "$original_status" "$cleanup_failed" \\
    "Build cleanup was incomplete. Inspect resources manually; build data was preserved."
}
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

require_commands=(debootstrap parted blockdev losetup mkfs.ext4 blkid grub-install grub-script-check grub-mkpasswd-pbkdf2 chroot mount umount mountpoint findmnt udevadm rsync python3)
for command_name in "${require_commands[@]}"; do
  command -v "$command_name" >/dev/null || {
    echo "Missing build dependency: $command_name" >&2
    echo "On Debian/Ubuntu: apt install debootstrap parted e2fsprogs grub-pc-bin grub-common rsync" >&2
    exit 1
  }
done

compose_check_host_arch

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

# Compose the target root through the shared engine. The engine owns profile
# validation already performed above (idempotent re-resolve), debootstrap,
# overlay, packages, Greia content, framebuffer, systemd, SSH, metadata and
# hygiene; this consumer keeps only disk identity (UUID), boot assembly and
# the footprint gate. GREIA_ROOT_UUID feeds the engine's fstab and manifest
# UUID lines so the composed root carries the same identity the partition
# assembly measured.
export GREIA_ROOT_UUID="$root_uuid"
export COMPOSE_DECLARED_MANIFEST="$DECLARED_PROFILE_MANIFEST"
compose_root --profile "$PROFILE_PATH" --role target --root "$ROOTFS"

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
if [[ "${COMPOSE_ROLE_SETS:-}" == *developer-remote* ]]; then
  BOOT_CONTRACT_ARGS+=(--developer)
fi
PYTHONPATH="$PROJECT_ROOT/src" python3 -m greia_platform.boot_contract \
  "${BOOT_CONTRACT_ARGS[@]}" "$ROOTFS/boot/grub/grub.cfg"
chroot "$ROOTFS" grub-install --target=i386-pc --boot-directory=/boot --recheck "$LOOP_DEVICE"

# Clone-neutral target state is owned by the shared composition engine
# (compose_prepare_clone_neutral_target in build/lib/compose.sh, run inside
# compose_root for role=target). This thin consumer keeps no second
# implementation so disk-image packaging and release-payload staging share one
# canonical target state; first boot creates the machine ID and SSH host keys
# are generated only when a parent explicitly enables SSH.

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
  echo "security_support_state=$COMPOSE_SECURITY_SUPPORT_STATE"
  echo "security_support_probe_exit=$COMPOSE_SECURITY_SUPPORT_EXIT"
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
