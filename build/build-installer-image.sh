#!/usr/bin/env bash
# Greia OS live-installer image builder (thin role consumer).
#
# This script owns only live-installer media assembly: target-build
# delegation and squashfs payload/digest, the live root composed through the
# shared composition engine for role `live-installer`, plus the live-only
# steps that remain here by construction — pool cache + hardware-support
# pool + live firmware, live-media-id, installer-ab.env/A-B bundle handling,
# live squashfs, MBR media assembly and live GRUB. All generic composition
# blocks (profile resolve/validate, debootstrap, virtual mounts, package
# install, installer overlay, Greia content subset, early framebuffer, base
# SSH + developer provision, metadata, hygiene) live in
# build/lib/compose.sh behind the explicit role-typed composition contract,
# shared with the target role consumer (build/build-image.sh).
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
PACKAGE_SET_ROOT="$SCRIPT_DIR/package-sets"

usage() {
  cat <<'USAGE'
Usage: sudo build/build-installer-image.sh PROFILE [OUTPUT_DIR] [--release-bundle PATH]

Builds a BIOS-bootable USB image that starts the graphical Greia OS
installer automatically and carries a compressed target-system payload.
For A/B target profiles the release bundle is a required explicit input:
pass --release-bundle with the validated unsigned deterministic
.greiaupdate v3 release artifact. GREIA_AB_RELEASE_BUNDLE_SRC remains
available as an explicit override (tests/harness), but normal production
composition must use the --release-bundle flag.
Run only on a Debian/Ubuntu x86 build host or VM.
USAGE
}

RELEASE_BUNDLE_FLAG=""
positional=()
while [[ $# -gt 0 ]]; do
  case "$1" in
    --release-bundle)
      [[ $# -ge 2 ]] || { echo "--release-bundle requires a PATH argument." >&2; exit 2; }
      RELEASE_BUNDLE_FLAG="$2"
      shift 2
      ;;
    --release-bundle=*)
      RELEASE_BUNDLE_FLAG="${1#--release-bundle=}"
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    --)
      shift
      while [[ $# -gt 0 ]]; do positional+=("$1"); shift; done
      ;;
    -*)
      echo "Unknown option: $1" >&2
      usage >&2
      exit 2
      ;;
    *)
      positional+=("$1")
      shift
      ;;
  esac
done
[[ ${#positional[@]} -ge 1 && ${#positional[@]} -le 2 ]] || { usage >&2; exit 2; }
[[ ${EUID:-$(id -u)} -eq 0 ]] || { echo "Run as root." >&2; exit 1; }

profile_input="${positional[0]}"
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
# mutation, so the live-installer consumer and the target consumer share one
# implementation. This also exports PROFILE_ID and the installer-scope
# package-set inputs used below.
compose_resolve_profile "$PROFILE_PATH" "live-installer" "$PROJECT_ROOT"

# A/B release-bundle authority: one explicit typed input, validated before
# any disk mutation. Precedence is the --release-bundle flag, then the
# GREIA_AB_RELEASE_BUNDLE_SRC explicit override (retained for tests and
# harness wiring). Nothing searches directories; nothing hardcodes a
# release path. The bundle is inspected here (v3 validity + profile
# identity match) and re-asserted byte-identical at USB assembly below.
AB_RELEASE_SRC=""
if [[ -n "$RELEASE_BUNDLE_FLAG" ]]; then
  AB_RELEASE_SRC="$RELEASE_BUNDLE_FLAG"
elif [[ -n "${GREIA_AB_RELEASE_BUNDLE_SRC:-}" ]]; then
  AB_RELEASE_SRC="${GREIA_AB_RELEASE_BUNDLE_SRC}"
fi
if [[ "$STORAGE_LAYOUT_ADAPTER" == *-ab-v1 ]]; then
  [[ -n "$AB_RELEASE_SRC" ]] || {
    echo "A/B installer build refused: pass --release-bundle with the unsigned deterministic .greiaupdate v3 release artifact." >&2
    exit 1
  }
  [[ -f "$AB_RELEASE_SRC" && ! -L "$AB_RELEASE_SRC" ]] || {
    echo "A/B installer build refused: release bundle is not a regular file: $AB_RELEASE_SRC" >&2
    exit 1
  }
  AB_RELEASE_PROFILE="$(PYTHONPATH="$PROJECT_ROOT/src" python3 - "$AB_RELEASE_SRC" <<'PY'
import sys
sys.path.insert(0, "src")
from greia_platform.system_updates import inspect_update_bundle
print(inspect_update_bundle(sys.argv[1]).manifest.profile)
PY
)" || {
    echo "A/B installer build refused: release bundle failed v3 inspection: $AB_RELEASE_SRC" >&2
    exit 1
  }
  [[ "$AB_RELEASE_PROFILE" == "$PROFILE_ID" ]] || {
    echo "A/B installer build refused: bundle profile $AB_RELEASE_PROFILE does not match image profile $PROFILE_ID." >&2
    exit 1
  }
  echo "A/B release bundle validated: profile $AB_RELEASE_PROFILE."
fi
export AB_RELEASE_SRC

OUTPUT_DIR="${positional[1]:-$PROJECT_ROOT/out}"
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
USB_ESP_MOUNT="$BUILD_DIR/usb-esp"
TARGET_LOOP=""
USB_LOOP=""
MOUNTS=()

cleanup() {
  local original_status=$?
  trap - EXIT INT TERM
  set +e
  local cleanup_failed=0
  safe_unmount_paths "${MOUNTS[@]}" || cleanup_failed=1
  safe_detach_loop "$TARGET_LOOP" || cleanup_failed=1
  safe_detach_loop "$USB_LOOP" || cleanup_failed=1
  if (( cleanup_failed == 0 )); then
    safe_remove_build_dir "$BUILD_DIR" || cleanup_failed=1
  fi
  safe_cleanup_exit "$original_status" "$cleanup_failed" "Installer-image cleanup was incomplete. Inspect resources manually; build data was preserved."
}
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

required=(debootstrap parted partx blockdev losetup mkfs.ext4 blkid mkfs.vfat grub-install grub-script-check grub-mkpasswd-pbkdf2 chroot mount umount mountpoint findmnt udevadm rsync mksquashfs python3 dpkg-deb)
for command_name in "${required[@]}"; do
  command -v "$command_name" >/dev/null || {
    echo "Missing build dependency: $command_name" >&2
    echo "Install: debootstrap parted e2fsprogs dosfstools grub-pc-bin grub-efi-ia32-bin grub-efi-amd64-bin grub-common rsync squashfs-tools" >&2
    exit 1
  }
done
# The ESP gets both EFI GRUB images; fail before the long build instead of
# after it when the host lacks the -bin packages that own these module dirs.
for efi_module_dir in /usr/lib/grub/i386-efi /usr/lib/grub/x86_64-efi; do
  [[ -f "$efi_module_dir/modinfo.sh" ]] || {
    echo "Missing build dependency: GRUB modules in $efi_module_dir." >&2
    echo "Install: grub-efi-ia32-bin grub-efi-amd64-bin" >&2
    exit 1
  }
done

compose_check_host_arch

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
target_payload_sha256="$payload_sha256"
safe_unmount_paths "$TARGET_MOUNT" || {
  echo "Cannot detach target payload filesystem." >&2
  exit 1
}
MOUNTS=()
safe_detach_loop "$TARGET_LOOP" || {
  echo "Cannot detach target payload loop device; preserving build data for inspection." >&2
  exit 1
}
TARGET_LOOP=""

# Compose the live installer root through the shared engine with live-only
# inserts at their required positions. The engine owns profile validation
# (already performed above, idempotent re-resolve), debootstrap, overlay,
# packages, Greia content, framebuffer, systemd, SSH, metadata and hygiene;
# this consumer keeps only the live-installer-specific assembly around it:
# pool cache, live-media-id (before the package install so the kernel
# postinst initramfs hook embeds it), hardware-support pool + live firmware
# (after packages, before initramfs), payload linkage, A/B facts, live
# squashfs, MBR media assembly and live GRUB.
#
# The live installer environment is allowed to be substantially larger than
# the installed target because broad hardware support belongs on removable
# installation media, not permanently on low-storage child devices.
# The live root must not gain target-only Activity content or the full target
# asset set: the engine's live-installer content subset installs only src +
# runtime + icons + fonts.
export COMPOSE_DECLARED_MANIFEST="$INSTALLER_PROFILE_MANIFEST"
# The live root is a live medium, never a fixed-UUID installed root: ensure
# the engine skips the installed fstab identity path.
unset GREIA_ROOT_UUID || true
# Persistent host apt + pool caches: bind-mount BEFORE the live debootstrap so
# base downloads land in the persistent host caches instead of the real live
# directory (a post-debootstrap mount would shadow them and they would survive
# into the squashfs). Released by cleanup() and the explicit pre-mksquashfs
# safe_unmount_paths before compression; never clear the caches.
compose_mount_apt_cache "$LIVE_ROOT"
LIVE_POOL_CACHE_MOUNT="$(mount_pool_cache "$LIVE_ROOT")"; MOUNTS+=("$LIVE_POOL_CACHE_MOUNT")
compose_debootstrap "$LIVE_ROOT"
compose_apply_overlay "$LIVE_ROOT" "live-installer"
# The A/B install copies the branded GRUB theme/logo from the live root onto
# the boot-control partition. This thin live-root consumer does not run
# compose_root, so install the same canonical assets here.
compose_install_boot_branding "$LIVE_ROOT" "$PROJECT_ROOT" || exit 1
compose_write_build_info "$LIVE_ROOT" "live-installer"
compose_write_boot_console_policy "$LIVE_ROOT"
# The live installer is a second Debian root carrying the target payload
# reference: record the expected payload digest and the target manifest
# beside the live build-info before any package install.
install -m 0644 "$TARGET_PAYLOAD_DIGEST" "$LIVE_ROOT/etc/greia-os/expected-payload.sha256"
install -m 0644 "$TARGET_PROFILE_MANIFEST" "$LIVE_ROOT/etc/greia-os/target-image-profile.json"
compose_write_sources_hostname_hosts "$LIVE_ROOT" "live-installer"
compose_mount_virtual "$LIVE_ROOT"

# The live-media UUID must exist before the kernel package postinst runs
# update-initramfs during the apt install below. The shared composer owns this
# invariant so direct live-root composition and this installer consumer cannot
# drift on ordering or identity semantics.
compose_prepare_live_media_identity "$LIVE_ROOT"
live_media_id="$COMPOSE_LIVE_MEDIA_ID"

compose_install_packages "$LIVE_ROOT" "live-installer"

# ADR 0021: freeze a broad signed Debian firmware/microcode repository on the
# installer while APT metadata is current, then install the verified firmware
# class into the live root for reliable coldplug. The final target later gets
# only machine-specific packages selected from the same frozen repository.
# Local-only install with no network; pool populate before live firmware
# before initramfs before squashfs.
"$SCRIPT_DIR/populate-hardware-support-pool.sh" "$LIVE_ROOT" "$SUITE" "$ARCH"
"$SCRIPT_DIR/install-live-hardware-firmware.sh" "$LIVE_ROOT" "$SUITE" "$ARCH"
cp "$LIVE_ROOT/opt/greia-hardware-support/manifest.json" "$HARDWARE_SUPPORT_REPORT"
# The installer-authorized support bound is the verified INSTALLED total
# (unpacked slot footprint), never compressed transfer bytes: fresh-install
# capacity authorizes at most the whole frozen pool, while the machine
# selection enforced at install time can only come in under it.
hardware_support_pool_bytes="$(python3 - "$HARDWARE_SUPPORT_REPORT" <<'PY'
import json
import sys
from pathlib import Path
print(json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))["total_installed_bytes"])
PY
)"
hardware_support_package_count="$(python3 - "$HARDWARE_SUPPORT_REPORT" <<'PY'
import json
import sys
from pathlib import Path
print(json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))["package_count"])
PY
)"

compose_install_greia_content "$LIVE_ROOT" "live-installer"
compose_build_early_framebuffer "$LIVE_ROOT"
# Same engine step as the target role (compose_root runs it for both roles);
# the explicit failure checks inside make a missing module stop the build.
compose_build_audio_endpoint_plugin "$LIVE_ROOT"
compose_configure_systemd "$LIVE_ROOT" "live-installer"
compose_configure_ssh_base "$LIVE_ROOT"
# Owner-authorized live-installer recovery account. Provision the ordinary
# login, then keep the service disabled until the installer toggle starts it.
compose_provision_developer_ssh_live "$LIVE_ROOT"
systemctl --root="$LIVE_ROOT" disable ssh.service
# The UI controls ssh.service, so no independent socket may start it.
systemctl --root="$LIVE_ROOT" mask ssh.socket
compose_maybe_provision_developer_ssh "$LIVE_ROOT" "live-installer"
compose_footprint_prune "$LIVE_ROOT"
compose_write_metadata_manifests "$LIVE_ROOT" "live-installer"
# The engine's base-system manifest carries the exact resolved package/kernel
# base; append the live-only hardware-support pool size so the produced
# medium records the frozen repository it carries.
{
  echo "hardware_support_pool_packages=$hardware_support_package_count"
  echo "hardware_support_pool_bytes=$hardware_support_pool_bytes"
} >> "$LIVE_ROOT/etc/greia-os/base-system-manifest"
# Live-role probe outcome for the USB/media report below (mirrors the target
# consumer carrying the engine result into its footprint report).
live_support_status_exit="$COMPOSE_SECURITY_SUPPORT_EXIT"
live_security_support_state="$COMPOSE_SECURITY_SUPPORT_STATE"
cp "$LIVE_ROOT/etc/greia-os/package-manifest.tsv" "$OUTPUT_DIR/greia-os-installer-${PROFILE_ID}-live-package-manifest.tsv"
cp "$LIVE_ROOT/etc/greia-os/base-system-manifest" "$OUTPUT_DIR/greia-os-installer-${PROFILE_ID}-live-base-system-manifest.txt"
cp "$LIVE_ROOT/etc/greia-os/security-support-status.txt" "$OUTPUT_DIR/greia-os-installer-${PROFILE_ID}-live-security-support-status.txt"
compose_footprint_hygiene "$LIVE_ROOT"
# Read-only bytecode prefix for the live installer too (greia-installer.service
# carries PYTHONPYCACHEPREFIX): the Atom otherwise cold-compiles the installer
# UI into the 128 MiB RAM overlay on every boot. Runs after hygiene so nothing
# deletes it; the module check re-asserts the plugin survived pruning.
compose_precompile_bytecode "$LIVE_ROOT"
compose_verify_audio_endpoint_plugin "$LIVE_ROOT"

# POSTR1-P2: immutable image-owned A/B release facts (installer-ab.env).
# For A/B target profiles the installer medium carries one small typed
# config at /etc/greia-os/installer-ab.env, generated here from the same
# image profile/release build — never hand-maintained. The shipped
# greia-install-transaction.service loads it through EnvironmentFile and
# greia_installer.composition parses/validates it centrally. Single-root
# recovery profiles ship no A/B facts (the unit's EnvironmentFile entry is
# optional and Python refuses an A/B profile with missing facts fail-closed).
# Build-time assertion (P2 requirement 2): the referenced unsigned v3 release
# bundle must actually be present on the installer medium, otherwise the
# build fails here — before any disk mutation.
if [[ "$STORAGE_LAYOUT_ADAPTER" == *-ab-v1 ]]; then
  echo "A/B target profile ($STORAGE_LAYOUT_ADAPTER): generating installer A/B release facts."
  # AB_RELEASE_SRC was resolved and v3-validated (regular file, profile
  # identity match) before any disk mutation above; re-assert presence
  # here since the env-override form could theoretically change mid-build.
  [[ -n "${AB_RELEASE_SRC:-}" ]] || {
    echo "A/B installer build refused: validated --release-bundle input missing." >&2
    exit 1
  }
  [[ -f "$AB_RELEASE_SRC" && ! -L "$AB_RELEASE_SRC" ]] || {
    echo "A/B installer build refused: release bundle is not a regular file: $AB_RELEASE_SRC" >&2
    exit 1
  }
  # The bundle itself travels in the USB payload beside the target
  # squashfs (copied at USB assembly below) and is re-asserted there.
  # Dedicated GRUB secret for the installed target's fixed boot entries. This
  # is deliberately distinct from the USB boot-menu recovery hash generated
  # at USB assembly: sharing one secret would let the installer recovery
  # code unlock the installed system's GRUB.
  AB_GRUB_SECURITY_ROOT="$BUILD_DIR/installer-ab-grub-security"
  AB_GRUB_RECOVERY_CODE="$OUTPUT_DIR/greia-os-installer-${PROFILE_ID}-ab-grub-recovery-code.txt"
  mkdir -p "$AB_GRUB_SECURITY_ROOT"
  PYTHONPATH="$PROJECT_ROOT/src" python3 -m greia_platform.grub_security \
    "$AB_GRUB_SECURITY_ROOT" --copy-code-to "$AB_GRUB_RECOVERY_CODE"
  ab_grub_hash="$(cat "$AB_GRUB_SECURITY_ROOT/etc/greia-os/grub-recovery.pbkdf2")"
  [[ -n "$ab_grub_hash" ]] || { echo "A/B installer build refused: GRUB secret generation failed." >&2; exit 1; }
  if [[ "${COMPOSE_ROLE_SETS:-}" == *developer-remote* ]]; then
    ab_developer=1
  else
    ab_developer=0
  fi
  cat > "$LIVE_ROOT/etc/greia-os/installer-ab.env" <<ABENV
# Greia OS installer A/B release facts (generated, do not hand-edit).
# Profile $PROFILE_ID / layout $STORAGE_LAYOUT_ADAPTER / backend $UPDATES_BOOT_BACKEND.
GREIA_AB_RELEASE_BUNDLE=/run/live/medium/payload/greia-release.greiaupdate
GREIA_AB_GRUB_PASSWORD_HASH=$ab_grub_hash
GREIA_AB_DEVELOPER=$ab_developer
GREIA_AB_SUPPORT_INSTALLED_BYTES=$hardware_support_pool_bytes
ABENV
  chmod 0644 "$LIVE_ROOT/etc/greia-os/installer-ab.env"
  chown root:root "$LIVE_ROOT/etc/greia-os/installer-ab.env"
  # Re-assert exactly what the medium now carries.
  [[ -s "$LIVE_ROOT/etc/greia-os/installer-ab.env" ]] || {
    echo "A/B installer build refused: generated installer-ab.env is missing." >&2
    exit 1
  }
  cp "$LIVE_ROOT/etc/greia-os/installer-ab.env" "$OUTPUT_DIR/greia-os-installer-${PROFILE_ID}-installer-ab.env"
  chmod 0644 "$OUTPUT_DIR/greia-os-installer-${PROFILE_ID}-installer-ab.env"
else
  # Single-root recovery media carry no A/B facts by construction.
  rm -f "$LIVE_ROOT/etc/greia-os/installer-ab.env"
fi

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
# A/B media also carry the full release bundle in the USB payload: size it
# or the bundle copy fails with ENOSPC once bundles outgrow the headroom.
if [[ "$STORAGE_LAYOUT_ADAPTER" == *-ab-v1 ]]; then
  [[ -n "${AB_RELEASE_SRC:-}" && -f "${AB_RELEASE_SRC:-}" ]] || {
    echo "A/B installer build refused: validated release bundle missing for media sizing." >&2
    exit 1
  }
  payload_mib="$(( payload_mib + ($(stat -c %s "$AB_RELEASE_SRC") + 1048575) / 1048576 ))"
fi
# + the 64 MiB EFI System Partition (Intel Mac / UEFI boot, UNPROVEN / LAB).
image_mib="$(( payload_mib + 256 + 64 ))"
(( image_mib < 1024 )) && image_mib=1024
rm -f "$OUTPUT_IMAGE" "$REPORT"
truncate -s "${image_mib}M" "$OUTPUT_IMAGE"
# One MBR table serves both firmware families (UNPROVEN / LAB on real Macs):
#   p1 64 MiB FAT32 type 0xEF (EFI System Partition) - read by EFI firmware
#   p2 ext4 root, active (boot flag)                 - read by BIOS grub-pc
# The BIOS path is exactly what it was (msdos, active root partition, GRUB
# embedded in the 1 MiB gap); the ESP only adds the EFI path. A pure GPT or a
# sgdisk hybrid MBR was rejected: it would change how legacy BIOSes (the Acer
# reference) see the stick.
parted -s "$OUTPUT_IMAGE" mklabel msdos
parted -s "$OUTPUT_IMAGE" mkpart primary fat32 1MiB 65MiB
parted -s "$OUTPUT_IMAGE" set 1 esp on
parted -s "$OUTPUT_IMAGE" mkpart primary ext4 65MiB 100%
parted -s "$OUTPUT_IMAGE" set 2 boot on
USB_LOOP="$(losetup --find --show --partscan "$OUTPUT_IMAGE")"
USB_ESP_PART="${USB_LOOP}p1"
USB_PART="${USB_LOOP}p2"
for _ in {1..20}; do [[ -b "$USB_ESP_PART" ]] && break; sleep 0.2; done
[[ -b "$USB_ESP_PART" ]] || { echo "Installer image EFI partition did not appear." >&2; exit 1; }
mkfs.vfat -F 32 -n GREIA_EFI "$USB_ESP_PART"
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
# POSTR1-P2: the unsigned v3 A/B release bundle travels in the USB payload beside
# the target squashfs and is re-asserted here — the installer-ab.env reference
# above must resolve on the booted medium.
if [[ "$STORAGE_LAYOUT_ADAPTER" == *-ab-v1 ]]; then
  [[ -n "${AB_RELEASE_SRC:-}" && -f "$AB_RELEASE_SRC" && ! -L "$AB_RELEASE_SRC" ]] || {
    echo "A/B installer build refused: release bundle missing for USB payload." >&2
    exit 1
  }
  cp "$AB_RELEASE_SRC" "$USB_MOUNT/payload/greia-release.greiaupdate"
  chmod 0644 "$USB_MOUNT/payload/greia-release.greiaupdate"
  [[ -s "$USB_MOUNT/payload/greia-release.greiaupdate" ]] || {
    echo "A/B installer build refused: release bundle missing on the installer medium." >&2
    exit 1
  }
  ab_bundle_sha256="$(sha256sum "$USB_MOUNT/payload/greia-release.greiaupdate" | awk '{print $1}')"
else
  ab_bundle_sha256="none-legacy-single-root"
fi
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
PYTHONPATH="$PROJECT_ROOT/src" python3 -m greia_platform.grub_security \
  "$INSTALLER_GRUB_SECURITY_ROOT" --copy-code-to "$INSTALLER_RECOVERY_CODE"
installer_grub_hash="$(cat "$INSTALLER_GRUB_SECURITY_ROOT/etc/greia-os/grub-recovery.pbkdf2")"
install -m 0644 "$PROJECT_ROOT/assets/boot/static/greia-boot-logo.png" \
  "$USB_MOUNT/boot/grub/greia-boot-logo.png"
# Single source of the live kernel command line. The BIOS and EFI GRUB images
# both read this one grub.cfg (EFI images are built with --boot-directory on
# the ext4 root), so the two boot paths cannot drift apart.
LIVE_KERNEL_CMDLINE="boot=live components live-media-path=/live live-media-timeout=15 nopersistence noeject nonetworking silent overlay-size=128M greia.live_media_id=$live_media_id quiet splash loglevel=0 console=tty1 panic=0 systemd.show_status=false rd.systemd.show_status=false systemd.crash_shell=no systemd.crash_chvt=0 udev.log_priority=3 vt.global_cursor_default=0 consoleblank=0"
cat > "$USB_MOUNT/boot/grub/grub.cfg" <<GRUB
set timeout=0
set timeout_style=hidden
set default=0
set pager=0
if loadfont unicode ; then
  set gfxmode=auto
  insmod all_video
  insmod gfxterm
  terminal_output gfxterm
fi
insmod png
background_image /boot/grub/greia-boot-logo.png
set superusers="greia"
export superusers
password_pbkdf2 greia $installer_grub_hash
menuentry "Install Greia OS" --unrestricted --id greia-installer {
  search --no-floppy --fs-uuid --set=root $usb_root_uuid
  linux /live/vmlinuz $LIVE_KERNEL_CMDLINE
  initrd /live/initrd.img
}
GRUB
grub-script-check "$USB_MOUNT/boot/grub/grub.cfg"
PYTHONPATH="$PROJECT_ROOT/src" python3 -m greia_platform.boot_contract --live-installer "$USB_MOUNT/boot/grub/grub.cfg"
grub-install --target=i386-pc --boot-directory="$USB_MOUNT/boot" --recheck "$USB_LOOP"
# EFI: removable-path images on the ESP, no NVRAM writes (build host firmware
# must stay untouched). 32-bit EFI Macs (2006-2007) read BOOTIA32.EFI, 64-bit
# EFI machines BOOTX64.EFI. LAB question: whether x64 EFI GRUB can start the
# i686 kernel on 2008+ Macs; the fallback is Option -> "Windows" (CSM/BIOS).
install -d "$USB_ESP_MOUNT"
mount "$USB_ESP_PART" "$USB_ESP_MOUNT"
MOUNTS+=("$USB_ESP_MOUNT")
# The FAT32 EFI partition doubles as the parent-readable failure log area.
# A failed install cannot be expected to provide working SSH or target logs.
# A duplicate live-media ID guards against accidentally writing another disk
# when the installer mounts GREIA_EFI to save its diagnostic report.
install -d "$USB_ESP_MOUNT/.disk" "$USB_ESP_MOUNT/greia-logs"
printf '%s\n' "$live_media_id" > "$USB_ESP_MOUNT/.disk/live-uuid"
chmod 0644 "$USB_ESP_MOUNT/.disk/live-uuid"
for efi_target in i386-efi x86_64-efi; do
  grub-install --target="$efi_target" --removable --no-nvram --efi-directory="$USB_ESP_MOUNT" \
    --boot-directory="$USB_MOUNT/boot" --no-uefi-secure-boot
done
[[ -s "$USB_ESP_MOUNT/EFI/BOOT/BOOTIA32.EFI" && -s "$USB_ESP_MOUNT/EFI/BOOT/BOOTX64.EFI" ]] || {
  echo "Installer EFI images were not written to the EFI System Partition." >&2
  exit 1
}
sync
safe_unmount_paths "$USB_ESP_MOUNT" "$USB_MOUNT" || { echo "Cannot detach completed installer filesystem." >&2; exit 1; }
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
  echo "storage_layout_adapter=$STORAGE_LAYOUT_ADAPTER"
  echo "updates_boot_backend=$UPDATES_BOOT_BACKEND"
  echo "installer_ab_env=/etc/greia-os/installer-ab.env"
  echo "installer_ab_bundle_sha256=${ab_bundle_sha256:-none-legacy-single-root}"
  echo "live_media_id=$live_media_id"
  echo "live_media_marker=/.disk/live-uuid"
  echo "boot_cover_backend=$BOOT_COVER_BACKEND"
  echo "boot_console_policy=$BOOT_CONSOLE_POLICY"
  echo "installer_profile_manifest=$INSTALLER_PROFILE_REPORT"
  echo "installer_profile_manifest_sha256=$(sha256sum "$INSTALLER_PROFILE_MANIFEST" | awk '{print $1}')"
  echo "payload_profile_manifest=$PAYLOAD_PROFILE_REPORT"
  echo "payload_profile_manifest_sha256=$(sha256sum "$TARGET_PROFILE_MANIFEST" | awk '{print $1}')"
  echo "hardware_support_manifest=$HARDWARE_SUPPORT_REPORT"
  echo "hardware_support_manifest_sha256=$(sha256sum "$HARDWARE_SUPPORT_REPORT" | awk '{print $1}')"
  echo "hardware_support_pool_packages=$hardware_support_package_count"
  echo "hardware_support_pool_bytes=$hardware_support_pool_bytes"
  echo "installer_grub_user=greia"
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
