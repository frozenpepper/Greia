#!/usr/bin/env bash
# Greia OS shared composition engine (A5 / ADR 0036 §5).
#
# One composition implementation with explicit artifact roles. The engine
# composes a root filesystem into a caller-provided directory:
#
#   compose_root --profile <id-or-path> --role target --root <path>
#   compose_root --profile <id-or-path> --role live-installer --root <path>
#
# Partitioning, mkfs, mounting, installed-boot assembly and media assembly
# remain the role consumer's responsibility (build/build-image.sh for the
# target role; build/build-installer-image.sh for live-installer, owned by
# T02; the T04 slot producer composes a target root through this engine).
#
# Role-specific package sets, overlays, Greia content, systemd lists and
# metadata are declarative role inputs below (compose_role_*), never forked
# script bodies.
#
# When sourced, this file defines the compose_* functions. When executed
# directly, it runs compose_root with the given arguments.
set -Eeuo pipefail

_COMPOSE_SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
_COMPOSE_BUILD_DIR="$(cd -- "$_COMPOSE_SCRIPT_DIR/.." && pwd)"
_COMPOSE_PROJECT_ROOT_DEFAULT="$(cd -- "$_COMPOSE_BUILD_DIR/.." && pwd)"
# shellcheck source=safe-cleanup.sh
source "$_COMPOSE_SCRIPT_DIR/safe-cleanup.sh"
# shellcheck source=apt-cache.sh
source "$_COMPOSE_SCRIPT_DIR/apt-cache.sh"

COMPOSE_VALID_ROLES=("target" "live-installer")

# Declarative role inputs. Architecture/board differences are profile and
# adapter data, never role branches here.
compose_assert_role() {
  local role="${1:-}"
  case "$role" in
    target|live-installer) ;;
    *)
      echo "Unknown composition role: '$role' (expected: target|live-installer)." >&2
      return 1
      ;;
  esac
}

# Package-scope input for tools/build_profile.py (target|installer).
compose_role_scope() {
  local role="$1"
  compose_assert_role "$role" || return 1
  if [[ "$role" == "target" ]]; then
    printf '%s\n' "target"
  else
    printf '%s\n' "installer"
  fi
}

# Overlay input: the role-selected appliance overlay directory.
compose_role_overlay_dir() {
  local role="$1"
  local project_root="${2:-$_COMPOSE_PROJECT_ROOT_DEFAULT}"
  compose_assert_role "$role" || return 1
  if [[ "$role" == "target" ]]; then
    printf '%s\n' "$project_root/build/overlay"
  else
    printf '%s\n' "$project_root/build/installer-overlay"
  fi
}

# Build-phase input recorded in build-info metadata.
compose_role_build_phase() {
  local role="$1"
  compose_assert_role "$role" || return 1
  if [[ "$role" == "target" ]]; then
    printf '%s\n' "phase0"
  else
    printf '%s\n' "phase0-live-installer"
  fi
}

# Whether the role composes the appliance user/group set (target only; the
# live-installer root carries no child appliance accounts).
compose_role_manages_appliance_users() {
  local role="$1"
  compose_assert_role "$role" || return 1
  [[ "$role" == "target" ]]
}

compose_usage() {
  cat <<'USAGE'
Usage: compose_root --profile <id-or-path> --role <target|live-installer> --root <path>

Composes a Greia OS root filesystem into the caller-provided root path.
The caller owns partitioning, mkfs, mounting, boot assembly and media
assembly. Must run on a Debian/Ubuntu build host as root for chroot/apt
steps (debootstrap, package install, users, systemd enablement).
USAGE
}

# Resolve + validate the declarative profile for a role. Sets the typed
# profile variables (PROFILE_ID, ARCH, SUITE, MIRROR, ...) in the caller
# environment and enforces the release gate + support-date guard before any
# root mutation. Idempotent per profile+role (guarded by _COMPOSE_RESOLVED).
compose_resolve_profile() {
  local profile_input="$1"
  local role="$2"
  local project_root="${3:-$_COMPOSE_PROJECT_ROOT_DEFAULT}"
  compose_assert_role "$role" || return 1
  local scope
  scope="$(compose_role_scope "$role")"
  local profile_tool="$project_root/tools/build_profile.py"
  local package_set_root="$project_root/build/package-sets"
  local profile_path
  if [[ -f "$profile_input" ]]; then
    profile_path="$(realpath "$profile_input")"
  else
    profile_path="$project_root/build/profiles/${profile_input%.toml}.toml"
  fi
  [[ -r "$profile_path" ]] || { echo "Profile not found: $profile_path" >&2; return 1; }
  [[ "$profile_path" == *.toml ]] || {
    echo "Build profiles are declarative TOML; executable .env profiles are no longer accepted: $profile_path" >&2
    return 1
  }
  if [[ "${_COMPOSE_RESOLVED:-}" == "$profile_path|$role" ]]; then
    return 0
  fi

  # Parse/validate declarative profile data before any root mutation. The
  # helper emits only shell-quoted assignments from a typed schema; the
  # profile itself is never sourced or executed.
  local profile_assignments
  profile_assignments="$(python3 "$profile_tool" shell "$profile_path")"
  eval "$profile_assignments"
  python3 "$profile_tool" --package-root "$package_set_root" validate "$profile_path" >/dev/null
  python3 "$profile_tool" check-phase0-builder "$profile_path" --scope "$scope" >/dev/null

  # Boot-cover release eligibility follows the declared boot adapter rather
  # than a builder-global assumption so a future accepted backend can be
  # selected per image family. No backend is release-safe until its physical
  # acceptance gate passes.
  local release_error=""
  if [[ "${PIP_RELEASE_BUILD:-0}" == "1" ]]; then
    if ! release_error="$(python3 "$profile_tool" check-release "$profile_path" 2>&1)"; then
      echo "Release build refused: $release_error" >&2
      return 1
    fi
  fi

  local current_build_date
  current_build_date="$(date -u +%F)"
  if [[ "$current_build_date" > "$SUPPORT_END_DATE" ]]; then
    echo "Profile $PROFILE_ID passed its declared security-support end date $SUPPORT_END_DATE; refusing build." >&2
    return 1
  fi

  COMPOSE_PROFILE_PATH="$profile_path"
  COMPOSE_PROFILE_TOOL="$profile_tool"
  COMPOSE_PACKAGE_SET_ROOT="$package_set_root"
  COMPOSE_PROJECT_ROOT="$project_root"
  _COMPOSE_RESOLVED="$profile_path|$role"
  export COMPOSE_PROFILE_PATH COMPOSE_PROFILE_TOOL COMPOSE_PACKAGE_SET_ROOT COMPOSE_PROJECT_ROOT
}

# Composition-command probe (disk/boot assembly commands such as parted,
# losetup, mkfs.ext4 and grub-install remain the role consumer's probe).
compose_require_composition_commands() {
  local require_commands=(debootstrap chroot mount umount mountpoint findmnt udevadm rsync python3 dpkg-deb readelf)
  local command_name
  for command_name in "${require_commands[@]}"; do
    command -v "$command_name" >/dev/null || {
      echo "Missing build dependency: $command_name" >&2
      echo "On Debian/Ubuntu: apt install debootstrap parted e2fsprogs grub-pc-bin grub-common rsync" >&2
      return 1
    }
  done
}

compose_check_host_arch() {
  local host_arch
  host_arch="$(uname -m)"
  case "$ARCH:$host_arch" in
    i386:x86_64|i386:i?86|amd64:x86_64) ;;
    *)
      echo "Profile architecture $ARCH cannot be executed safely on build host $host_arch." >&2
      echo "Use an x86_64 Debian/Ubuntu VM for Acer and modern image builds." >&2
      return 1
      ;;
  esac
}

# Debootstrap + architecture verification. The persistent host apt cache
# must already be bind-mounted BEFORE this call so base downloads land in
# the persistent host cache instead of the real target directory.
compose_debootstrap() {
  local rootfs="$1"
  local project_root="${COMPOSE_PROJECT_ROOT:-$_COMPOSE_PROJECT_ROOT_DEFAULT}"
  local debian_keyring="$project_root/build/trust/debian-archive-keyring-2025.1.gpg"
  echo "Bootstrapping Debian $SUITE $ARCH..."
  [[ -r "$debian_keyring" ]] || { echo "Pinned Debian archive keyring is missing: $debian_keyring" >&2; return 1; }
  DEBIAN_ARCHIVE_KEYRING="$debian_keyring"
  debootstrap --arch="$ARCH" --variant=minbase --include=ca-certificates --keyring="$DEBIAN_ARCHIVE_KEYRING" --force-check-gpg "$SUITE" "$rootfs" "$MIRROR"
  local resolved_arch
  resolved_arch="$(chroot "$rootfs" /usr/bin/dpkg --print-architecture)"
  [[ "$resolved_arch" == "$ARCH" ]] || { echo "Bootstrapped architecture $resolved_arch does not match profile $ARCH." >&2; return 1; }
}

# Persistent host apt cache (bind-mounted BEFORE debootstrap by the caller
# ordering) plus virtual mounts + resolver stub. Appends every mount to the
# caller's MOUNTS array for bounded teardown via safe_unmount_paths.
# Persistent host apt cache: bind-mount BEFORE debootstrap so the base
# downloads land in the persistent host cache instead of the real target
# directory. A post-debootstrap mount would shadow debootstrap's .debs on the
# real filesystem (invisible to du -sx, counted by df) and they would survive
# into the image. Released by cleanup() (safe_unmount_paths); never clear the
# host cache.
compose_mount_apt_cache() {
  local rootfs="$1"
  local apt_mount
  apt_mount="$(mount_apt_archives_cache "$rootfs")"
  MOUNTS+=("$apt_mount")
}

compose_mount_virtual() {
  local rootfs="$1"
  local virtual
  for virtual in dev proc sys run; do
    mkdir -p "$rootfs/$virtual"
  done
  mount --rbind /dev "$rootfs/dev"; MOUNTS+=("$rootfs/dev"); mount --make-rslave "$rootfs/dev"
  mount -t proc proc "$rootfs/proc"; MOUNTS+=("$rootfs/proc")
  mount --rbind /sys "$rootfs/sys"; MOUNTS+=("$rootfs/sys"); mount --make-rslave "$rootfs/sys"
  # /run is tmpfs at runtime; a fresh mount avoids carrying the build host's
  # desktop-session mounts (gvfs/portal under /run/user/1000) into the chroot,
  # which would keep the build busy and block teardown. Seed a resolver stub
  # so chroot apt/DNS still works while sharing the host network namespace.
  mount -t tmpfs tmpfs "$rootfs/run"; MOUNTS+=("$rootfs/run")
  install -d -m 0755 "$rootfs/run/systemd/resolve"
  cat /etc/resolv.conf > "$rootfs/run/systemd/resolve/stub-resolv.conf" 2>/dev/null || true
  # NOTE: the persistent apt cache is already bind-mounted above (before
  # debootstrap); no second mount here. Released by cleanup().
}

compose_apt_options() {
  APT_ACQUIRE_OPTIONS=(
    -o Acquire::Retries=3
    -o Acquire::http::Timeout=20
    -o Acquire::https::Timeout=20
  )
}

# Live-installer media identity must exist before any kernel package postinst
# can invoke update-initramfs. The installer overlay ships a fail-closed
# greia-live-media-id hook that embeds this value in conf/uuid.conf, so the
# identity prerequisite belongs to the shared live-role composition layer,
# not to one particular image consumer.
#
# Idempotent by design: the root itself is the identity authority. A repeated
# call preserves its existing valid identifier; a fresh root gets a fresh UUID.
# COMPOSE_LIVE_MEDIA_ID is output only, for consumers that need to reuse the
# exact value when assembling the outer boot medium.
compose_prepare_live_media_identity() {
  local rootfs="$1"
  local identity_path="$rootfs/etc/greia-os/live-media-id"
  local live_media_id=""

  install -d -m 0755 "$rootfs/etc/greia-os"
  if [[ -s "$identity_path" ]]; then
    live_media_id="$(tr -d '\r\n' < "$identity_path")"
  else
    live_media_id="$(python3 - <<'PYUUID'
import uuid
print(uuid.uuid4())
PYUUID
)"
  fi

  [[ "$live_media_id" =~ ^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$ ]] || {
    echo "Live-media identifier is invalid: $live_media_id" >&2
    return 1
  }

  printf '%s\n' "$live_media_id" > "$identity_path"
  chmod 0644 "$identity_path"
  chown root:root "$identity_path"
  COMPOSE_LIVE_MEDIA_ID="$live_media_id"
  export COMPOSE_LIVE_MEDIA_ID
}

# Package-set resolution + install for the role scope. Keeps intentionally
# pre-seeded Greia conffiles without any dpkg prompt.
compose_install_packages() {
  local rootfs="$1"
  local role="$2"
  local scope
  scope="$(compose_role_scope "$role")"
  compose_apt_options
  local package_output
  package_output="$(python3 "$COMPOSE_PROFILE_TOOL" --package-root "$COMPOSE_PACKAGE_SET_ROOT" packages "$COMPOSE_PROFILE_PATH" --scope "$scope")"
  local packages=()
  mapfile -t packages <<< "$package_output"
  (( ${#packages[@]} > 0 )) || { echo "Resolved $scope package set is empty." >&2; return 1; }
  if [[ "$role" == "target" ]]; then
    printf 'grub-pc grub-pc/install_devices_empty boolean true\n' | chroot "$rootfs" debconf-set-selections
  fi
  chroot "$rootfs" /usr/bin/env DEBIAN_FRONTEND=noninteractive apt-get "${APT_ACQUIRE_OPTIONS[@]}" update
  # Greia intentionally pre-seeds appliance conffiles in the overlay. dpkg's
  # conffile prompt is independent of debconf, so make product ownership explicit.
  chroot "$rootfs" /usr/bin/env DEBIAN_FRONTEND=noninteractive \
    apt-get "${APT_ACQUIRE_OPTIONS[@]}" -o Dpkg::Options::=--force-confold install -y --no-install-recommends "${packages[@]}"
}

# The installed static Parent client must be readable by greiapanel even when
# a checkout or pin update created directories with a restrictive umask.
compose_normalize_parent_client_permissions() {
  local parent_web="$1/usr/share/greia-parent-app"
  [[ -d "$parent_web" && ! -L "$parent_web" ]] || {
    echo "Greia Parent web runtime is missing or is a symlink." >&2; return 1;
  }
  find "$parent_web" -type d -exec chmod 0755 {} + || return 1
  find "$parent_web" -type f -exec chmod 0644 {} + || return 1
}

# Role-selected overlay. Repository checkout ownership is never
# target-filesystem authority: static appliance overlay files are installed
# as root regardless of the UID/GID of the developer or CI checkout.
compose_apply_overlay() {
  local rootfs="$1"
  local role="$2"
  local overlay_dir
  overlay_dir="$(compose_role_overlay_dir "$role" "${COMPOSE_PROJECT_ROOT:-$_COMPOSE_PROJECT_ROOT_DEFAULT}")"
  rsync -a --chown=root:root "$overlay_dir/" "$rootfs/"
  if [[ "$role" == "target" ]]; then
    compose_normalize_parent_client_permissions "$rootfs" || return 1
    [[ "$(stat -c '%u:%g' "$rootfs")" == "0:0" ]] || {
      echo "Greia overlay changed target root ownership away from root:root." >&2
      return 1
    }
  else
    [[ "$(stat -c '%u:%g' "$rootfs")" == "0:0" ]] || {
      echo "Greia installer overlay changed live root ownership away from root:root." >&2
      return 1
    }
  fi
}

# Canonical GRUB presentation assets. The theme itself comes from the role
# overlay; the PNG is generated artwork kept under assets/boot/static and must
# be installed into both the target slot and the live installer root so the
# A/B boot-control menu can carry the same branded first frame.
compose_install_boot_branding() {
  local rootfs="$1"
  local project_root="${2:-${COMPOSE_PROJECT_ROOT:-$_COMPOSE_PROJECT_ROOT_DEFAULT}}"
  local source="$project_root/assets/boot/static/greia-boot-logo.png"
  [[ -f "$source" && ! -L "$source" ]] || {
    echo "Canonical boot artwork is missing or unsafe: $source" >&2
    return 1
  }
  install -d -m 0755 "$rootfs/boot/grub"
  install -m 0644 "$source" "$rootfs/boot/grub/greia-boot-logo.png"
  # The live-installer overlay intentionally does not carry the target GRUB
  # theme, but the A/B boot-control copy is sourced from the live root. Install
  # the same canonical theme into both roles so the branded menu is complete.
  local theme="$project_root/build/overlay/boot/grub/greia-theme.txt"
  [[ -f "$theme" && ! -L "$theme" ]] || {
    echo "Canonical boot theme is missing or unsafe: $theme" >&2
    return 1
  }
  install -m 0644 "$theme" "$rootfs/boot/grub/greia-theme.txt"
}

compose_write_build_info() {
  local rootfs="$1"
  local role="$2"
  local project_root="${COMPOSE_PROJECT_ROOT:-$_COMPOSE_PROJECT_ROOT_DEFAULT}"
  local boot_adapter
  if [[ "$role" == "target" ]]; then
    boot_adapter="$INSTALLED_BOOT_ADAPTER"
  else
    boot_adapter="$INSTALLER_BOOT_ADAPTER"
  fi
  local project_version
  project_version="$(tr -d '\r\n' < "$project_root/VERSION")"
  [[ -n "$project_version" ]] || { echo "VERSION is empty." >&2; return 1; }
  PROJECT_VERSION="$project_version"
  install -d -m 0755 "$rootfs/etc/greia-os"
  cat > "$rootfs/etc/greia-os/build-info" <<BUILDINFO
GREIA_OS_VERSION=$project_version
PIP_RUNTIME_API=0.1
PIP_BUILD_PHASE=$(compose_role_build_phase "$role")
PIP_BUILD_PROFILE=$PROFILE_ID
PIP_PLATFORM_FAMILY=$PLATFORM_FAMILY
PIP_COMPATIBILITY_CLASS=$COMPATIBILITY_CLASS
PIP_RUNTIME_FAMILIES=$RUNTIME_FAMILIES
PIP_DISPLAY_ADAPTER=$DISPLAY_ADAPTER
PIP_BOOT_ADAPTER=$boot_adapter
PIP_BOOT_COVER_BACKEND=$BOOT_COVER_BACKEND
BUILDINFO
  local declared_manifest="${COMPOSE_DECLARED_MANIFEST:-}"
  if [[ -n "$declared_manifest" && -r "$declared_manifest" ]]; then
    install -m 0644 "$declared_manifest" "$rootfs/etc/greia-os/image-profile.json"
  else
    python3 "$COMPOSE_PROFILE_TOOL" manifest "$COMPOSE_PROFILE_PATH" --scope "$(compose_role_scope "$role")" > "$rootfs/etc/greia-os/image-profile.json"
  fi
}

# Boot console policy (profile boot.console_policy: quiet|diagnostic). The
# installed GRUB generator (/etc/grub.d/10_greia_appliance) reads it; it is
# deliberately separate from the developer-remote marker so an image can keep
# SSH while booting quietly (release candidate). Written for both roles so the
# live root records the policy its USB template was chosen with.
compose_write_boot_console_policy() {
  local rootfs="$1"
  case "${BOOT_CONSOLE_POLICY:-}" in
    quiet|diagnostic) ;;
    *) echo "Unknown boot console policy: '${BOOT_CONSOLE_POLICY:-}'." >&2; return 1 ;;
  esac
  install -d -m 0755 "$rootfs/etc/greia-os"
  printf '%s\n' "$BOOT_CONSOLE_POLICY" > "$rootfs/etc/greia-os/boot-console-policy"
  chmod 0644 "$rootfs/etc/greia-os/boot-console-policy"
  chown root:root "$rootfs/etc/greia-os/boot-console-policy"
}

compose_write_sources_hostname_hosts() {
  local rootfs="$1"
  local role="$2"
  local hostname_value="$HOSTNAME"
  if [[ "$role" == "live-installer" ]]; then
    hostname_value="greia-installer"
  fi
  cat > "$rootfs/etc/apt/sources.list" <<SOURCES
deb $MIRROR $SUITE main non-free-firmware
deb $MIRROR $SUITE-updates main non-free-firmware
deb $SECURITY_MIRROR $SUITE-security main non-free-firmware
SOURCES
  printf '%s\n' "$hostname_value" > "$rootfs/etc/hostname"
  if [[ "$role" == "target" ]]; then
    cat > "$rootfs/etc/hosts" <<HOSTS
127.0.0.1 localhost
127.0.1.1 $hostname_value
::1 localhost ip6-localhost ip6-loopback
HOSTS
  else
    cat > "$rootfs/etc/hosts" <<'HOSTS'
127.0.0.1 localhost
127.0.1.1 greia-installer
::1 localhost ip6-localhost ip6-loopback
HOSTS
  fi
}

# Appliance users have no passwords. pipprofiles owns the bounded profile
# registry/tree shared by the launcher and typed parent profile controls;
# pipsettings owns only bounded input/display preference state.
# Target role only; the live-installer root carries no appliance accounts.
#
# netdev: iwd's shipped system-bus policy lets only root and group netdev talk
# to net.connman.iwd, so the Shell (greiakid) and Parent (greiapanel) need it
# to scan and join Wi-Fi (Acer parity audit A1, 2026-10-17). The launcher and
# Parent units also grant it through SupplementaryGroups=, which is what the
# running services actually use; the account membership keeps the identity
# self-describing. groupadd -f: netdev may already exist from a package.
#
# The group names stay pipsettings/pipprofiles on purpose: tmpfiles, first
# boot, the installer engine and the verifiers all use them, and the
# 2026-10-01 /run/greia-os boot loop came from one place using another name.
# A rename needs one coordinated tranche with a migration.
compose_create_users_groups() {
  local rootfs="$1"
  chroot "$rootfs" groupadd --system pipsettings
  chroot "$rootfs" groupadd --system pipprofiles
  chroot "$rootfs" groupadd --system -f netdev
  chroot "$rootfs" useradd --system --create-home --home-dir /var/lib/greia-kid \
    --shell /usr/sbin/nologin --user-group --groups pipsettings,pipprofiles,audio,netdev greiakid
  chroot "$rootfs" useradd --system --create-home --home-dir /var/lib/greia-os \
    --shell /usr/sbin/nologin --user-group --groups pipsettings,pipprofiles,netdev greiapanel
  chroot "$rootfs" useradd --create-home --home-dir /var/lib/greia-admin \
    --shell /bin/bash --groups sudo greiaadmin
  chroot "$rootfs" passwd --lock greiaadmin
  # The managed greia account is the owner-approved development/admin SSH and
  # Greia Parents identity. Base images keep it locked and SSH disabled; explicit
  # developer provisioning sets the greia/greia login on dev images only.
  chroot "$rootfs" useradd --create-home --home-dir /var/lib/greia \
    --shell /bin/bash --groups sudo greia
  chroot "$rootfs" passwd --lock greia
  # iwd owns Wi-Fi credentials in /var/lib/iwd (root-only, 0700). Create it
  # explicitly so an installer-side Wi-Fi hand-off can write
  # <target>/var/lib/iwd/<network>.psk (root:root 0600) before first boot and
  # iwd on the installed system picks it up at start.
  install -d -m 0700 -o root -g root "$rootfs/var/lib/iwd"
}

# Greia content installation (role-selected). Target installs the curated
# built-in Activity tree + runtime + assets + deterministic index; the
# live-installer root installs the installer runtime subset.
compose_install_greia_content() {
  local rootfs="$1"
  local role="$2"
  local project_root="${COMPOSE_PROJECT_ROOT:-$_COMPOSE_PROJECT_ROOT_DEFAULT}"
  if [[ "$role" == "target" ]]; then
    compose_install_target_content "$rootfs" "$project_root"
  else
    compose_install_live_content "$rootfs" "$project_root"
  fi
}

# Install only the shared-asset subtree the child runtime reads. SVG masters,
# candidate packs, source sheets and developer previews live in the repository
# for authoring/build tooling but must never occupy installed C0 space. The
# allowlist mirrors the runtime readers: fonts, core-icon PNGs + catalogues,
# boot logo/frames, audio banks, the scene definition and the generated
# runtime PNG renditions under visual/runtime/. Anything new that the runtime
# reads must be added here AND to tests/test_build_runtime_assets_contract.py.
compose_install_runtime_assets() {
  local rootfs="$1"
  local project_root="$2"
  local application_root="${3:-$rootfs/opt/greia-os}"
  install -d -m 0755 "$application_root/assets"
  # Hide canonical references on the sender only: --delete must also remove
  # references leaked into a reused staging root by older composition rules.
  rsync -a --delete \
    --exclude 'source/' \
    --filter 'H /audio/characters/canonical/' \
    --exclude '*contact_sheet*' \
    --include '/audio/***' \
    --include '/boot/***' \
    --include '/catalog/' \
    --include '/catalog/*.toml' \
    --include '/fonts/***' \
    --include '/icons/***' \
    --include '/scenes/***' \
    --include '/visual/' \
    --include '/visual/runtime/***' \
    --exclude '*' \
    "$project_root/assets/" "$application_root/assets/"
}

compose_install_target_content() {
  local rootfs="$1"
  local project_root="$2"
  local generations_root="$rootfs/opt/greia-software/generations"
  local application_root="$generations_root/base"
  local installed_activity_root="$application_root/activities"

  install -d -m 0755 "$generations_root"
  if [[ -e "$rootfs/opt/greia-os" && ! -L "$rootfs/opt/greia-os" ]]; then
    if [[ -n "$(find "$rootfs/opt/greia-os" -mindepth 1 -maxdepth 1 -print -quit)" ]]; then
      echo "Refusing to replace a non-empty target /opt/greia-os during generation composition." >&2
      return 1
    fi
    rmdir "$rootfs/opt/greia-os"
  elif [[ -L "$rootfs/opt/greia-os" ]]; then
    echo "Refusing to compose over an existing /opt/greia-os generation pointer." >&2
    return 1
  fi
  install -d -m 0755 "$application_root"

  # Source/runtime are common to development and release target images.
  # Activities are deliberately composed separately below so an official
  # release can never fall back to "whatever happens to be in activities/".
  rsync -a --delete --exclude '__pycache__' \
    "$project_root/src" "$project_root/runtime" \
    "$application_root/"

  if [[ "${PIP_RELEASE_BUILD:-0}" == "1" ]]; then
    # P6 release authority: official release composition must come from the
    # single reviewed declarative roster. stage_release_activities.py refuses
    # draft/empty policy, validates exact ID↔package identity through the
    # ActivityRegistry, rejects symlinks, and atomically publishes this output.
    if ! PYTHONPATH="$project_root/src" python3 \
      "$project_root/tools/stage_release_activities.py" \
      --selection "$project_root/build/first-party-release-activities.toml" \
      --activities "$project_root/activities" \
      --runtime "$project_root/runtime/child-runtime.toml" \
      --output "$installed_activity_root"; then
      echo "Approved first-party Activity release staging failed; refusing release image." >&2
      return 1
    fi
  else
    # Development/test targets intentionally keep every source Activity so P7
    # review, simulator work, and independent installer/first-boot debugging do
    # not depend on an unfinished release roster.
    rsync -a --delete --exclude '__pycache__' \
      "$project_root/activities/" "$installed_activity_root/"
  fi

  # 2A built-in trust boundary: validate the *installed* Activity tree, not a
  # parallel repository path. This makes content and index one transaction and
  # prevents release selection from being bypassed after staging.
  PYTHONPATH="$project_root/src" python3 - \
    "$project_root" "$installed_activity_root" <<'GREIA_BUILTIN_GATE_EOF'
import sys
from pathlib import Path

project = Path(sys.argv[1])
source_root = Path(sys.argv[2])
sys.path.insert(0, str(project / "src"))

from greia_platform.activities import (
    ActivityRegistry,
    ActivityValidationError,
    RuntimeCatalogue,
)
from greia_platform.activity_tree_cleanup import _is_junk_name
from greia_platform.trust import ActivitySource, PackageTrust

if source_root.is_symlink() or not source_root.is_dir():
    print("Installed built-in Activity root is unsafe or missing.", file=sys.stderr)
    sys.exit(1)

junk_hits = []
symlink_hits = []
for path in sorted(source_root.rglob("*")):
    if path.is_symlink():
        symlink_hits.append(str(path.relative_to(source_root)))
        continue
    name = path.name
    if name == "__pycache__" or "__pycache__" in path.parts:
        continue
    if _is_junk_name(name):
        junk_hits.append(str(path.relative_to(source_root)))

if symlink_hits:
    print("Installed built-in Activity tree contains symlinks:", file=sys.stderr)
    for hit in symlink_hits:
        print(f"  {hit}", file=sys.stderr)
    sys.exit(1)

if junk_hits:
    print("Installed built-in Activity tree carries curated host/editor noise:", file=sys.stderr)
    for hit in junk_hits:
        print(f"  {hit}", file=sys.stderr)
    sys.exit(1)

runtime = RuntimeCatalogue.load(project / "runtime" / "child-runtime.toml")
source = ActivitySource(source_root, PackageTrust.BUILT_IN, "greia-system")
try:
    registry = ActivityRegistry((source,), runtime)
    registry.discover_registrations()
except ActivityValidationError as exc:
    print(f"Built-in Activity validation failed: {exc}", file=sys.stderr)
    sys.exit(1)
GREIA_BUILTIN_GATE_EOF

  compose_install_runtime_assets "$rootfs" "$project_root" "$application_root"

  # T33 built-in index: generate from the exact installed Activity directory.
  # In a release build this is the approved staged subset; in ordinary
  # development/test images it is the full source tree copied above.
  local index_staging
  index_staging="$(mktemp "${TMPDIR:-/tmp}/activity-index.XXXXXX")"
  local generation_index="$application_root/activity-index-v1.json"
  local image_index="$rootfs/usr/share/greia/activity-index-v1.json"
  if ! PYTHONPATH="$project_root/src" python3 "$project_root/tools/build_activity_index.py" \
    --activities "$installed_activity_root" \
    --runtime "$project_root/runtime/child-runtime.toml" \
    --output "$index_staging"; then
    echo "Built-in Activity index generation failed; refusing image." >&2
    rm -f "$index_staging" "$index_staging.tmp" "$image_index"
    return 1
  fi
  install -D -m 0644 "$index_staging" "$generation_index"
  rm -f "$index_staging" "$index_staging.tmp"

  install -d -m 0755 "$rootfs/usr/lib/python3/dist-packages" \
    "$rootfs/usr/share/greia"
  printf '%s\n' '/opt/greia-os/src' > "$rootfs/usr/lib/python3/dist-packages/pip_os.pth"
  ln -s greia-software/generations/base "$rootfs/opt/greia-os"
  ln -s ../../../opt/greia-os/activity-index-v1.json "$image_index"
  chown -R root:root "$generations_root"
  chmod -R a-w "$application_root"
  chmod 0755 "$generations_root"
}

compose_install_live_content() {
  local rootfs="$1"
  local project_root="$2"
  install -d -m 0755 "$rootfs/opt/greia-os"
  rsync -a --delete --exclude '__pycache__' "$project_root/src" "$project_root/runtime" "$rootfs/opt/greia-os/"
  install -d -m 0755 "$rootfs/opt/greia-os/assets/icons/core/v1/256"
  rsync -a "$project_root/assets/icons/core/v1/256/" "$rootfs/opt/greia-os/assets/icons/core/v1/256/"
  install -d -m 0755 "$rootfs/opt/greia-os/assets/fonts"
  rsync -a "$project_root/assets/fonts/" "$rootfs/opt/greia-os/assets/fonts/"
  # Installer look and boot intro (src/greia_installer/presentation.py,
  # boot_intro.py, greia_platform.boot_animation/boot_chime): the 52 logo
  # frames + static canvas, the boot chime, and the shared-visual catalogue
  # with its runtime renditions (bg.meadow_day.home, character.leo). The
  # catalogue loader resolves every catalogued path strictly, so the whole
  # visual/runtime tree ships (about 10 MiB, live medium only, never the
  # installed target budget); a partial subset would make the catalogue fail
  # and silently fall back to the procedural meadow.
  rsync -a --exclude 'source/' --exclude '*contact_sheet*' \
    --include '/boot/' --include '/boot/frames/***' --include '/boot/static/***' \
    --include '/audio/' --include '/audio/system/' \
    --include '/audio/system/greia-boot-chime.wav' \
    --include '/catalog/' --include '/catalog/shared_visuals_v1.toml' \
    --include '/visual/' --include '/visual/runtime/***' \
    --exclude '*' \
    "$project_root/assets/" "$rootfs/opt/greia-os/assets/"
  install -d -m 0755 "$rootfs/usr/lib/python3/dist-packages"
  printf '%s\n' /opt/greia-os/src > "$rootfs/usr/lib/python3/dist-packages/pip_os.pth"
  chown -R root:root "$rootfs/opt/greia-os"
  chmod -R a-w "$rootfs/opt/greia-os"
}

# Root filesystem table. The filesystem UUID is disk identity owned by the
# caller (partition/mkfs assembly); pass it via GREIA_ROOT_UUID. Single-owner
# policy: this shell seam only forwards to greia_platform.fstab, the one
# canonical renderer also used by the installer engine and SlotFinalizer.
compose_write_fstab() {
  local rootfs="$1"
  local root_uuid="${GREIA_ROOT_UUID:-}"
  [[ -n "$root_uuid" ]] || { echo "compose_write_fstab: GREIA_ROOT_UUID is not set." >&2; return 1; }
  local project_root="${COMPOSE_PROJECT_ROOT:-$_COMPOSE_PROJECT_ROOT_DEFAULT}"
  PYTHONPATH="$project_root/src" python3 - "$rootfs" "$root_uuid" <<'GREIA_FSTAB_EOF'
import os
import sys
from pathlib import Path

from greia_platform.fstab import FSTAB_FILE_MODE, render_fstab

rootfs = Path(sys.argv[1])
root_uuid = sys.argv[2]
try:
    text = render_fstab(root_uuid)
except ValueError as exc:
    print(f"compose_write_fstab: {exc}", file=sys.stderr)
    sys.exit(1)
target = rootfs / "etc/fstab"
target.parent.mkdir(parents=True, exist_ok=True)
target.write_text(text, encoding="ascii")
os.chmod(target, FSTAB_FILE_MODE)
GREIA_FSTAB_EOF
}

compose_build_audio_endpoint_plugin() {
  local rootfs="$1"
  local project_root="${COMPOSE_PROJECT_ROOT:-$_COMPOSE_PROJECT_ROOT_DEFAULT}"
  # The greia_mic_light ALSA ExtPlugin is what makes microphone processing
  # real. Without it /etc/asound.conf still defines the PCM, but opening it
  # fails, the availability probe declines to write its marker, and noise
  # cancelling silently falls back to off.
  #
  # Built with the target toolchain inside the root, like the framebuffer
  # renderer, because the module must match the image's ABI. The compiler and
  # headers are development-only and are removed again afterwards.
  #
  # Every step returns explicitly: callers run this as `... || return 1`,
  # which disables `set -e` for the whole function body. That is how earlier
  # images shipped without the module (2026-10-17 mic review §2): the compile
  # failed (libc6-dev missing), dpkg-architecture was absent (empty multiarch)
  # and only the final purge's status counted.
  local build_packages=(gcc libc6-dev libasound2-dev libspeexdsp-dev)
  compose_apt_options
  chroot "$rootfs" /usr/bin/env DEBIAN_FRONTEND=noninteractive \
    apt-get "${APT_ACQUIRE_OPTIONS[@]}" update || return 1
  chroot "$rootfs" /usr/bin/env DEBIAN_FRONTEND=noninteractive \
    apt-get "${APT_ACQUIRE_OPTIONS[@]}" -o Dpkg::Options::=--force-confold \
    install -y --no-install-recommends "${build_packages[@]}" >/dev/null || return 1
  install -d -m 0755 "$rootfs/usr/src/greia-audio" || return 1
  cp "$project_root/src/greia_platform/audio_alsa/greia_mic_light.c" \
    "$rootfs/usr/src/greia-audio/greia_mic_light.c" || return 1
  local multiarch
  multiarch="$(chroot "$rootfs" gcc -print-multiarch)" || return 1
  [[ -n "$multiarch" ]] || { echo "Cannot determine the target multiarch triplet." >&2; return 1; }
  chroot "$rootfs" /bin/sh -c \
    'cd /usr/src/greia-audio && gcc -O2 -Wall -fPIC -shared -o greia_mic_light.so greia_mic_light.c -lasound -lspeexdsp -lm' \
    || { echo "greia_mic_light ALSA plugin failed to compile." >&2; return 1; }
  local module="$rootfs/usr/lib/$multiarch/alsa-lib/libasound_module_pcm_greia_mic_light.so"
  install -D -m 0755 "$rootfs/usr/src/greia-audio/greia_mic_light.so" "$module" || return 1
  rm -rf "$rootfs/usr/src/greia-audio"
  chroot "$rootfs" /usr/bin/env DEBIAN_FRONTEND=noninteractive \
    apt-get "${APT_ACQUIRE_OPTIONS[@]}" -y remove --purge "${build_packages[@]}" >/dev/null || return 1
  chroot "$rootfs" apt-get -y autoremove >/dev/null 2>&1 || true
  compose_verify_audio_endpoint_plugin "$rootfs" || return 1
}

# Fail the build when the microphone plugin is missing or built for the wrong
# architecture. Also used by consumers after later steps (apt autoremove,
# footprint pruning) so nothing can silently delete it again.
compose_verify_audio_endpoint_plugin() {
  local rootfs="$1"
  local module="" module_count=0 found
  while IFS= read -r found; do
    module_count=$((module_count + 1))
    module="$found"
  done < <(find "$rootfs/usr/lib" -mindepth 3 -maxdepth 3 -type f \
    -path '*/alsa-lib/libasound_module_pcm_greia_mic_light.so' 2>/dev/null)
  (( module_count == 1 )) || {
    echo "Expected exactly one greia_mic_light ALSA module under $rootfs/usr/lib/<multiarch>/alsa-lib; found $module_count." >&2
    return 1
  }
  [[ -s "$module" ]] || { echo "greia_mic_light ALSA module is empty: $module" >&2; return 1; }
  local elf_machine
  elf_machine="$(readelf -h "$module" 2>/dev/null | awk '/Machine:/{print $2, $3}')"
  case "$ARCH" in
    i386)
      [[ "$elf_machine" == "Intel 80386" ]] || {
        echo "greia_mic_light module architecture ($elf_machine) does not match i386 target." >&2
        return 1
      }
      ;;
    amd64)
      [[ "$elf_machine" == "Advanced Micro" || "$elf_machine" == "AMD x86-64" ]] || {
        echo "greia_mic_light module architecture ($elf_machine) does not match amd64 target." >&2
        return 1
      }
      ;;
  esac
  echo "greia_mic_light ALSA module: ${module#"$rootfs"} ($elf_machine)"
}

# Build the Greia-owned early framebuffer boot cover for the TARGET
# architecture inside the composed root. The binary is compiled with the target
# klibc toolchain so the build host architecture is never authoritative. The
# build-only libklibc-dev package is removed again before package-manifest and
# footprint capture so it cannot leak into the final image.
compose_build_early_framebuffer() {
  local rootfs="$1"
  local project_root="${COMPOSE_PROJECT_ROOT:-$_COMPOSE_PROJECT_ROOT_DEFAULT}"
  compose_apt_options
  local rootfs_arg="$rootfs"
  build_early_framebuffer() {
    local rootfs="$1"
    # klcc needs the matching native compiler (e.g. i686-linux-gnu-gcc) which is
    # provided by the gcc package; install it together with libklibc-dev so the
    # target toolchain can actually compile. Both are removed again afterwards.
    # Own the list state first: an earlier live-root step may have updated
    # from a restricted source set, and this install must resolve from the
    # configured archives regardless of what ran before.
    chroot "$rootfs" /usr/bin/env DEBIAN_FRONTEND=noninteractive \
      apt-get "${APT_ACQUIRE_OPTIONS[@]}" update
    chroot "$rootfs" /usr/bin/env DEBIAN_FRONTEND=noninteractive \
      apt-get "${APT_ACQUIRE_OPTIONS[@]}" -o Dpkg::Options::=--force-confold \
      install -y --no-install-recommends libklibc-dev gcc >/dev/null
    install -d -m 0755 "$rootfs/usr/lib/greia-boot"
    # Stage the renderer source into the target root so the target toolchain
    # compiles it with target headers. klcc is a gcc wrapper that links against
    # klibc; its path differs across Debian/Ubuntu, so locate it inside the root.
    install -d -m 0755 "$rootfs/usr/src/greia-boot"
    cp "$project_root/build/early-boot/greia-fb-splash.c" \
      "$rootfs/usr/src/greia-boot/greia-fb-splash.c"
    local klcc_path
    klcc_path="$(chroot "$rootfs" /bin/sh -c 'command -v klcc')" || {
      echo "klcc not found in target root after libklibc-dev install." >&2
      return 1
    }
    chroot "$rootfs" "$klcc_path" -static -Os -s \
      -o /usr/lib/greia-boot/greia-fb-splash \
      /usr/src/greia-boot/greia-fb-splash.c
    rm -rf "$rootfs/usr/src/greia-boot"
    chmod 0755 "$rootfs/usr/lib/greia-boot/greia-fb-splash"
    # Verify the produced binary matches the target architecture before it can
    # ever reach an initramfs. The target is a chroot; readelf must run outside.
    local elf_machine
    elf_machine="$(readelf -h "$rootfs/usr/lib/greia-boot/greia-fb-splash" 2>/dev/null \
      | awk '/Machine:/{print $2, $3}')"
    case "$ARCH" in
      i386)
        [ "$elf_machine" = "Intel 80386" ] || {
          echo "Early framebuffer helper architecture ($elf_machine) does not match i386 target." >&2
          return 1
        }
        ;;
      amd64)
        [ "$elf_machine" = "Advanced Micro" ] || [ "$elf_machine" = "AMD x86-64" ] || {
          echo "Early framebuffer helper architecture ($elf_machine) does not match amd64 target." >&2
          return 1
        }
        ;;
    esac
    chroot "$rootfs" /usr/bin/env DEBIAN_FRONTEND=noninteractive \
      apt-get "${APT_ACQUIRE_OPTIONS[@]}" -y remove --purge libklibc-dev gcc >/dev/null
    chroot "$rootfs" apt-get -y autoremove >/dev/null 2>&1 || true
  }
  build_early_framebuffer "$rootfs_arg"
}

# The live installer runs as Debian's nobody/nogroup but systemd also
# resolves every SupplementaryGroups= name *before* ExecStartPre. The
# minimal debootstrap + installer package set does not guarantee netdev (and
# potentially other device-access groups). If any one is absent, systemd
# rejects greia-installer.service with status=216/GROUP and the splash is
# left on screen forever. Target users/groups are created separately by
# compose_create_users_groups; this is the live-installer-only counterpart.
# Read the actual unit declaration to avoid a second drifting group list.
compose_create_live_installer_groups() {
  local rootfs="$1"
  local unit="$rootfs/etc/systemd/system/greia-installer.service"
  local names name
  [[ -f "$unit" ]] || { echo "Missing live installer service: $unit" >&2; return 1; }
  [[ -x "$rootfs/usr/sbin/groupadd" ]] || {
    echo "Missing groupadd in live installer root (passwd package)." >&2
    return 1
  }
  names="$(sed -n 's/^SupplementaryGroups=//p' "$unit")"
  [[ -n "$names" ]] || {
    echo "Live installer supplementary group declaration is empty." >&2
    return 1
  }
  for name in $names; do
    [[ "$name" =~ ^[a-z_][a-z0-9_-]*$ ]] || {
      echo "Invalid live installer supplementary group: $name" >&2
      return 1
    }
    chroot "$rootfs" /usr/sbin/groupadd --system --force "$name" || return 1
  done
}

# System service composition (declarative per-role enable/mask lists).
compose_configure_systemd() {
  local rootfs="$1"
  local role="$2"
  if [[ "$role" == "target" ]]; then
    # The audio endpoint probe ships as a target-overlay file, so the exec bit is
    # not carried across. Without it the oneshot failed with 203/EXEC, never
    # wrote the endpoint readiness markers, and the audio service reported both
    # processing endpoints unavailable - so microphone processing silently fell
    # back to off and noise cancelling did nothing at all. Only the target role
    # ships the probe and enables greia-audio-endpoints.service; the installer
    # overlay has no such file, so this must stay inside the target branch.
    chmod 0755 "$rootfs/usr/local/lib/greia-os/greia-audio-endpoint-probe"
    chmod 0755 "$rootfs/usr/local/lib/greia-os/software-update-bootstrap.py"
    install -d -m 0755 "$rootfs/etc/greia-os"
    printf '%s\n' '{"schema_version":1}' \
      > "$rootfs/etc/greia-os/software-update-bootstrap.json"
    chmod 0644 "$rootfs/etc/greia-os/software-update-bootstrap.json"
    chown root:root "$rootfs/etc/greia-os/software-update-bootstrap.json"
    local target_services=(
      greia-first-boot.service
      greia-software-update-apply.timer
      greia-launcher.service
      greia-parent.service
      greia-boot-health.socket
      greia-system-update.socket
      greia-parent-ssh.socket
      greia-audio-endpoints.service
      greia-microphone-level.socket
      systemd-networkd.service
      systemd-resolved.service
      iwd.service
      avahi-daemon.service
    )
    # The early boot observer resolves semantic A/B slot identity from the
    # installed-layout + release-identity records. Single-root layouts have no
    # such records or slot identity, so enabling the observer there makes the
    # unit fail in namespace setup before its process starts.
    if [[ "$STORAGE_LAYOUT_ADAPTER" == *-ab-v1 ]]; then
      target_services+=(greia-boot-observer.service)
      # TAKEOVER-4/D55: without this timer a candidate that boots but never
      # becomes healthy stays on the candidate slot forever instead of
      # rolling back to the accepted slot after the health deadline.
      target_services+=(greia-candidate-recovery.timer)
    fi
    systemctl --root="$rootfs" enable "${target_services[@]}"
    systemctl --root="$rootfs" mask \
      getty@.service autovt@.service console-getty.service debug-shell.service \
      emergency.service rescue.service console-shell.service kbrequest.target \
      getty@tty1.service getty@tty2.service getty@tty3.service \
      getty@tty4.service getty@tty5.service getty@tty6.service
    systemctl --root="$rootfs" set-default graphical.target
  else
    # Ensure the live root can resolve the UI's supplementary groups before
    # enabling the unit; otherwise first boot fails at GROUP (216/GROUP).
    compose_create_live_installer_groups "$rootfs" || return 1
    systemctl --root="$rootfs" enable greia-installer.service greia-installer-finish.path
    systemctl --root="$rootfs" mask getty@.service autovt@.service console-getty.service debug-shell.service emergency.service rescue.service console-shell.service kbrequest.target getty@tty1.service getty@tty2.service getty@tty3.service getty@tty4.service getty@tty5.service getty@tty6.service
    systemctl --root="$rootfs" set-default graphical.target
  fi
}

# The base builder fails closed: SSH disabled, no password minted, the
# managed greia account locked. For an explicit developer-remote profile the
# owner policy requires the greia/greia development login to be reachable after
# install, so the builder provisions it here (root stays denied).
compose_configure_ssh_base() {
  local rootfs="$1"
  systemctl --root="$rootfs" disable ssh.service 2>/dev/null || true
  install -d -m 0755 "$rootfs/etc/ssh/sshd_config.d"
  cat > "$rootfs/etc/ssh/sshd_config.d/20-greia-parent.conf" <<'SSH'
PasswordAuthentication no
KbdInteractiveAuthentication no
AuthenticationMethods publickey
PermitRootLogin no
X11Forwarding no
AllowTcpForwarding no
PermitTunnel no
SSH
}

# Developer provisioning (role-selected floors; root stays denied in both).
compose_provision_developer_ssh() {
  local rootfs="$1"
  local role="$2"
  if [[ "$role" == "target" ]]; then
    compose_provision_developer_ssh_target "$rootfs"
  else
    compose_provision_developer_ssh_live "$rootfs"
  fi
}

compose_provision_developer_ssh_target() {
  local rootfs="$1"
  # The greia account already exists in the target composition (created and
  # locked). Set the owner-approved password first, then unlock (unlocking a
  # locked and passwordless account is refused by passwd; after chpasswd it
  # is allowed).
  printf 'greia:greia\n' | chroot "$rootfs" /usr/sbin/chpasswd
  chroot "$rootfs" /usr/bin/passwd -u greia
  # Write BOTH sshd drop-ins consistently (prepare-developer-ssh regenerates
  # them on every sshd start with the same password policy, plus key login when
  # an operator key is installed). `publickey,password` would mean BOTH methods,
  # so the build-time floor uses plain `password`. sshd_config.d is included in
  # glob order and the first value wins; the base builder writes 20-greia-parent.conf
  # with PasswordAuthentication no / AuthenticationMethods publickey, which
  # would otherwise defeat the developer floor. The dev floor must be coherent
  # across every included file so the greia/greia password login works.
  cat > "$rootfs/etc/ssh/sshd_config.d/00-greia-security-floor.conf" <<'FLOOR'
# Target development security floor (owner-approved greia/greia).
# Enables the development/test SSH identity greia/greia; root stays denied.
PasswordAuthentication yes
KbdInteractiveAuthentication no
PermitRootLogin no
AuthenticationMethods password
DenyUsers root
AllowUsers greia
FLOOR
  chmod 0644 "$rootfs/etc/ssh/sshd_config.d/00-greia-security-floor.conf"
  cat > "$rootfs/etc/ssh/sshd_config.d/20-greia-parent.conf" <<'DEVSSH'
# Development target SSH policy (owner-approved greia/greia).
PasswordAuthentication yes
KbdInteractiveAuthentication no
PermitRootLogin no
AuthenticationMethods password
AllowUsers greia
X11Forwarding no
AllowTcpForwarding no
PermitTunnel no
DEVSSH
  chmod 0644 "$rootfs/etc/ssh/sshd_config.d/20-greia-parent.conf"
  systemctl --root="$rootfs" enable ssh.service
  # Developer marker: identifies this image as a developer/test build (SSH,
  # greia-devctl, developer Activity source). The boot console is chosen
  # separately by /etc/greia-os/boot-console-policy (diagnostic for -dev
  # profiles, quiet for the release candidate); panic=0 in every policy.
  install -d -m 0755 "$rootfs/etc/greia-os"
  printf '%s\n' "profile=$PROFILE_ID" > "$rootfs/etc/greia-os/developer-remote"
  chmod 0644 "$rootfs/etc/greia-os/developer-remote"
  # Bounded developer privilege: the SSH-reachable greia identity may run only
  # greia-devctl as root without a password. Development images only; the base
  # path writes no sudoers file. Validated below with visudo -cf semantics.
  install -d -m 0755 "$rootfs/etc/sudoers.d"
  cat > "$rootfs/etc/sudoers.d/greia-developer-remote" <<'SUDOERS'
# Development-image only: privileged operations stay inside greia-devctl.
greia ALL=(root) NOPASSWD: /usr/local/sbin/greia-devctl
SUDOERS
  chown root:root "$rootfs/etc/sudoers.d/greia-developer-remote"
  chmod 0440 "$rootfs/etc/sudoers.d/greia-developer-remote"
  chroot "$rootfs" /usr/sbin/visudo -cf /etc/sudoers.d/greia-developer-remote
}

compose_provision_developer_ssh_live() {
  local rootfs="$1"
  # Create the managed greia development account if absent.
  if ! chroot "$rootfs" /usr/bin/id -u greia >/dev/null 2>&1; then
    chroot "$rootfs" /usr/sbin/useradd --create-home --home-dir /var/lib/greia \
      --shell /bin/bash --groups sudo greia
  fi
  printf 'greia:greia\n' | chroot "$rootfs" /usr/sbin/chpasswd
  # Rewrite the shared security floor so the owner-approved greia/greia login
  # works while root stays denied. This is the dev-image floor from the
  # provisioning tools, applied at build time for developer profiles.
  cat > "$rootfs/etc/ssh/sshd_config.d/00-greia-security-floor.conf" <<'FLOOR'
# Live-installer development security floor (owner-approved greia/greia).
# Enables the development/test SSH identity greia/greia; root stays denied.
PasswordAuthentication yes
KbdInteractiveAuthentication no
PermitRootLogin no
AuthenticationMethods password
DenyUsers root
AllowUsers greia
FLOOR
  chmod 0644 "$rootfs/etc/ssh/sshd_config.d/00-greia-security-floor.conf"
  # Also make the later-sorted 20-greia-parent.conf consistent. sshd_config.d
  # is included in glob order with first-value-wins; the base builder writes
  # 20-greia-parent.conf with PasswordAuthentication no / publickey-only, which
  # would otherwise defeat the developer floor.
  cat > "$rootfs/etc/ssh/sshd_config.d/20-greia-parent.conf" <<'DEVSSH'
# Development live-installer SSH policy (owner-approved greia/greia).
PasswordAuthentication yes
KbdInteractiveAuthentication no
PermitRootLogin no
AuthenticationMethods password
AllowUsers greia
X11Forwarding no
AllowTcpForwarding no
PermitTunnel no
DEVSSH
  chmod 0644 "$rootfs/etc/ssh/sshd_config.d/20-greia-parent.conf"
  systemctl --root="$rootfs" enable ssh.service
}

compose_write_developer_display_endpoint() {
  local rootfs="$1"
  local role="$2"
  local display_user
  compose_assert_role "$role" || return 1
  if [[ "$role" == "target" ]]; then
    display_user="greiakid"
  else
    display_user="root"
  fi
  install -d -m 0755 "$rootfs/etc/greia-os"
  printf '{"user":"%s","display":":0"}\n' "$display_user" \
    > "$rootfs/etc/greia-os/developer-display.json"
  chown root:root "$rootfs/etc/greia-os/developer-display.json"
  chmod 0644 "$rootfs/etc/greia-os/developer-display.json"
}

# Developer target images keep a bounded persistent journal so a first-boot
# failure or boot loop survives the reboot that follows it (premortem §0.2:
# the volatile journal left nothing to read after the 2026-10-07 loop).
# Release images keep the volatile journal from the overlay.
compose_configure_developer_journal() {
  local rootfs="$1"
  install -d -m 0755 "$rootfs/etc/systemd/journald.conf.d"
  cat > "$rootfs/etc/systemd/journald.conf.d/20-greia-developer-persistent.conf" <<'JOURNAL'
# Developer/RC images only (written by build/lib/compose.sh): keep the journal
# across reboots, bounded so it can never fill the 7 GB reference disk.
[Journal]
Storage=persistent
SystemMaxUse=48M
SystemKeepFree=256M
SystemMaxFileSize=8M
MaxRetentionSec=14day
JOURNAL
  chmod 0644 "$rootfs/etc/systemd/journald.conf.d/20-greia-developer-persistent.conf"
  install -d -m 2755 -o root -g root "$rootfs/var/log/journal"
  chroot "$rootfs" chgrp systemd-journal /var/log/journal 2>/dev/null || true
}

# Optional operator PUBLIC key for key-only agent access to developer images.
# Input: GREIA_OPERATOR_AUTHORIZED_KEY_FILE (a host path, never committed).
# Installed root-owned at /etc/ssh/greia-operator-keys/greia, which the runtime
# SSH bootstrap (prepare-developer-ssh) lists in AuthorizedKeysFile, so it
# survives reboots and sshd restarts. Password login stays available.
compose_install_operator_key() {
  local rootfs="$1"
  local developer="$2"
  local source="${GREIA_OPERATOR_AUTHORIZED_KEY_FILE:-}"
  [[ -n "$source" ]] || return 0
  [[ "$developer" == "1" ]] || {
    echo "GREIA_OPERATOR_AUTHORIZED_KEY_FILE is set but profile $PROFILE_ID has no developer-remote set; refusing." >&2
    return 1
  }
  local project_root="${COMPOSE_PROJECT_ROOT:-$_COMPOSE_PROJECT_ROOT_DEFAULT}"
  install -d -m 0755 -o root -g root "$rootfs/etc/ssh/greia-operator-keys" || return 1
  python3 -I "$project_root/build/lib/operator_key.py" \
    "$source" "$rootfs/etc/ssh/greia-operator-keys/greia" || return 1
  chown root:root "$rootfs/etc/ssh/greia-operator-keys/greia" || return 1
  chmod 0644 "$rootfs/etc/ssh/greia-operator-keys/greia" || return 1
}

compose_maybe_provision_developer_ssh() {
  local rootfs="$1"
  local role="$2"
  local scope
  scope="$(compose_role_scope "$role")"
  local role_sets
  role_sets="$(python3 "$COMPOSE_PROFILE_TOOL" --package-root "$COMPOSE_PACKAGE_SET_ROOT" package-sets "$COMPOSE_PROFILE_PATH" --scope "$scope" 2>/dev/null)"
  if [[ "$role_sets" == *developer-remote* ]]; then
    if [[ "$role" == "target" ]]; then
      echo "Developer target profile: enabling greia/greia SSH (root denied)."
    else
      echo "Developer installer profile: enabling greia/greia SSH (root denied)."
    fi
    compose_provision_developer_ssh "$rootfs" "$role" || return 1
    compose_write_developer_display_endpoint "$rootfs" "$role" || return 1
    if [[ "$role" == "target" ]]; then
      compose_configure_developer_journal "$rootfs" || return 1
    fi
    compose_install_operator_key "$rootfs" 1 || return 1
  else
    compose_install_operator_key "$rootfs" 0 || return 1
  fi
  COMPOSE_ROLE_SETS="$role_sets"
}

# POSTR1-P5 footprint composition reduction (build-hygiene only; no
# Phase-0 product scope removed).
compose_footprint_prune() {
  local rootfs="$1"
  compose_apt_options
  chroot "$rootfs" /usr/bin/env DEBIAN_FRONTEND=noninteractive \
    apt-get "${APT_ACQUIRE_OPTIONS[@]}" -y purge --auto-remove binutils >/dev/null
  chroot "$rootfs" apt-get -y autoremove >/dev/null 2>&1 || true
  rm -f "$rootfs"/usr/lib/gcc/*/*/cc1
  if [[ -d "$rootfs/usr/share/locale" ]]; then
    find "$rootfs/usr/share/locale" -mindepth 1 -maxdepth 1 -type d ! -name 'en*' -exec rm -rf '{}' +
  fi
  if [[ -d "$rootfs/usr/share/man" ]]; then
    find "$rootfs/usr/share/man" -mindepth 1 -exec rm -rf '{}' +
  fi
  if [[ -d "$rootfs/usr/share/info" ]]; then
    find "$rootfs/usr/share/info" -mindepth 1 -exec rm -rf '{}' +
  fi
  if [[ -d "$rootfs/usr/share/doc" ]]; then
    find "$rootfs/usr/share/doc" -mindepth 1 -maxdepth 1 -type d \
      -exec find '{}' -maxdepth 1 -type f ! -name copyright -delete ';'
  fi
}

# Record the exact package/kernel base actually resolved by APT. Profiles use
# Debian suite names and meta-packages, so this manifest is the authoritative
# identity of a produced image until snapshot-pinned builds are introduced.
compose_write_metadata_manifests() {
  local rootfs="$1"
  local role="$2"
  install -d -m 0755 "$rootfs/etc/greia-os"
  chroot "$rootfs" dpkg-query -W -f='${Package}\t${Version}\t${Architecture}\t${Installed-Size}\n' \
    | LC_ALL=C sort > "$rootfs/etc/greia-os/package-manifest.tsv"
  {
    echo "profile=$PROFILE_ID"
    echo "certification_state=$CERTIFICATION_STATE"
    echo "platform_family=$PLATFORM_FAMILY"
    echo "compatibility_class=$COMPATIBILITY_CLASS"
    echo "image_layout=$IMAGE_LAYOUT"
    if [[ "$role" == "target" ]]; then
      echo "installed_boot_adapter=$INSTALLED_BOOT_ADAPTER"
    else
      echo "installer_boot_adapter=$INSTALLER_BOOT_ADAPTER"
    fi
    echo "display_adapter=$DISPLAY_ADAPTER"
    echo "enabled_runtime_families=$RUNTIME_FAMILIES"
    echo "suite=$SUITE"
    echo "architecture=$ARCH"
    echo "kernel_meta_package=$KERNEL_PACKAGE"
    echo "declared_support_end_date=$SUPPORT_END_DATE"
    if [[ -n "${GREIA_ROOT_UUID:-}" ]]; then
      echo "root_filesystem_uuid=$GREIA_ROOT_UUID"
    fi
    echo "debian_version=$(cat "$rootfs/etc/debian_version")"
    echo "resolved_kernel_packages=$(chroot "$rootfs" dpkg-query -W -f='${Package}=${Version} ' 'linux-image-*' 2>/dev/null || true)"
    echo "resolved_xorg_packages=$(chroot "$rootfs" dpkg-query -W -f='${Package}=${Version} ' 'xserver-xorg-*' 2>/dev/null || true)"
  } > "$rootfs/etc/greia-os/base-system-manifest"
  local support_status_exit=0
  chroot "$rootfs" check-support-status --no-heading \
    > "$rootfs/etc/greia-os/security-support-status.txt" 2>&1 || support_status_exit=$?
  local security_support_state
  if (( support_status_exit != 0 )); then
    security_support_state="probe-failed"
    echo "WARNING: Debian security-support probe failed with exit $support_status_exit; the image must not be released until reviewed." >&2
  elif [[ -s "$rootfs/etc/greia-os/security-support-status.txt" ]]; then
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
  } >> "$rootfs/etc/greia-os/base-system-manifest"
  chmod 0644 "$rootfs/etc/greia-os/package-manifest.tsv" \
    "$rootfs/etc/greia-os/base-system-manifest" \
    "$rootfs/etc/greia-os/security-support-status.txt"
  COMPOSE_SECURITY_SUPPORT_STATE="$security_support_state"
  COMPOSE_SECURITY_SUPPORT_EXIT="$support_status_exit"
}

# Avoid package/cache growth and persistent logs on the 7 GB reference disk.
# autoclean keeps the persistent host .deb cache (bind-mounted above) for the
# next build; only APT lists are dropped from the image.
compose_footprint_hygiene() {
  local rootfs="$1"
  chroot "$rootfs" apt-get autoclean
  rm -rf "$rootfs/var/lib/apt/lists/"*
  find "$rootfs" -xdev -type d -name __pycache__ -prune -exec rm -rf '{}' +
  find "$rootfs/var/log" -type f -exec truncate -s 0 '{}' +
}

# Image-owned, read-only Python bytecode prefix (greia_platform.bytecode_cache),
# built for the target AND the live-installer root.
# Footprint hygiene above deletes every in-tree __pycache__ and Greia processes
# never write bytecode, so without this every Shell start and Activity launch
# recompiled ~200+ modules (~3.2 s per launch on the Atom N270 reference).
# Runs after hygiene so nothing deletes the prefix, and INSIDE the chroot so
# the target interpreter (bytecode is CPython-version specific) writes
# checked-hash bytecode for the exact runtime paths under
# /usr/lib/greia/pycache. Activity folders stay bytecode-free; the launcher,
# Parent and Activity runtime read the prefix via PYTHONPYCACHEPREFIX.
# -B keeps the tool's own stdlib imports from recreating in-tree __pycache__.
compose_precompile_bytecode() {
  local rootfs="$1"
  local project_root="${COMPOSE_PROJECT_ROOT:-$_COMPOSE_PROJECT_ROOT_DEFAULT}"
  if ! chroot "$rootfs" /usr/bin/env -i PATH=/usr/sbin:/usr/bin:/sbin:/bin \
      /usr/bin/python3 -I -B - --greia-root /opt/greia-os \
      < "$project_root/tools/precompile_greia_bytecode.py"; then
    echo "Greia bytecode precompilation failed; refusing image." >&2
    return 1
  fi
}

# Clone-neutral target state (single owner for role=target).
# Raw images and installer/update payloads are cloned: leave all clone/machine
# identity material empty here so disk-image packaging and the release-payload
# staging path share one canonical target state. First boot creates the
# machine ID (overlay first-boot via systemd-machine-id-setup), while SSH host
# keys are generated only when a parent explicitly enables SSH
# (greia-enable-ssh via ssh-keygen -A). Runs after developer SSH provisioning
# on purpose: developer images keep their explicit greia/greia login, marker,
# sudoers and sshd config; only host-key bytes stay absent in every target
# root, base or developer. The live-installer role is intentionally excluded
# here: the live root is an ephemeral live medium, never a cloned installed
# target; installed identity is personalized at install time by
# src/greia_installer/engine.py (_personalize_target).
compose_prepare_clone_neutral_target() {
  local rootfs="$1"
  mkdir -p "$rootfs/etc"
  : > "$rootfs/etc/machine-id"
  rm -f "$rootfs/var/lib/dbus/machine-id" "$rootfs/var/lib/systemd/random-seed"
  rm -f "$rootfs"/etc/ssh/ssh_host_*
}

# Main entry point: compose a role root into a caller-provided directory.
# Partitioning, mkfs, mounting, installed-boot assembly and media assembly
# remain the caller's responsibility.
compose_root() {
  local profile_input=""
  local role=""
  local rootfs=""
  local project_root="$_COMPOSE_PROJECT_ROOT_DEFAULT"
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --profile) profile_input="${2:-}"; shift 2 ;;
      --role) role="${2:-}"; shift 2 ;;
      --root) rootfs="${2:-}"; shift 2 ;;
      --project-root) project_root="${2:-}"; shift 2 ;;
      -h|--help) compose_usage; return 0 ;;
      *) echo "Unknown compose_root argument: $1" >&2; compose_usage >&2; return 2 ;;
    esac
  done
  [[ -n "$profile_input" && -n "$role" && -n "$rootfs" ]] || {
    echo "compose_root requires --profile, --role and --root." >&2
    compose_usage >&2
    return 2
  }
  compose_assert_role "$role" || return 1
  [[ "$EUID" -eq 0 ]] || { echo "Run as root." >&2; return 1; }
  compose_resolve_profile "$profile_input" "$role" "$project_root" || return 1
  compose_require_composition_commands || return 1
  compose_check_host_arch || return 1
  mkdir -p "$rootfs"
  # The caller provides the root path; when it is not yet a mount, MOUNTS
  # starts empty and this engine appends only its own composition mounts.
  if [[ -z "${MOUNTS+x}" ]]; then
    MOUNTS=()
  fi
  compose_mount_apt_cache "$rootfs" || return 1
  compose_debootstrap "$rootfs" || return 1
  compose_apply_overlay "$rootfs" "$role" || return 1
  compose_install_boot_branding "$rootfs" "$project_root" || return 1
  compose_write_build_info "$rootfs" "$role" || return 1
  compose_write_boot_console_policy "$rootfs" || return 1
  compose_write_sources_hostname_hosts "$rootfs" "$role" || return 1
  if [[ "$role" == "live-installer" ]]; then
    compose_prepare_live_media_identity "$rootfs" || return 1
  fi
  compose_mount_virtual "$rootfs" || return 1
  compose_install_packages "$rootfs" "$role" || return 1
  if compose_role_manages_appliance_users "$role"; then
    compose_create_users_groups "$rootfs" || return 1
  fi
  compose_install_greia_content "$rootfs" "$role" || return 1
  if [[ -n "${GREIA_ROOT_UUID:-}" ]]; then
    compose_write_fstab "$rootfs" || return 1
  fi
  compose_build_early_framebuffer "$rootfs" || return 1
  compose_build_audio_endpoint_plugin "$rootfs" || return 1
  compose_configure_systemd "$rootfs" "$role" || return 1
  compose_configure_ssh_base "$rootfs" || return 1
  compose_maybe_provision_developer_ssh "$rootfs" "$role" || return 1
  compose_footprint_prune "$rootfs" || return 1
  compose_write_metadata_manifests "$rootfs" "$role" || return 1
  compose_footprint_hygiene "$rootfs" || return 1
  # Both roles: the live installer previously cold-compiled the Shell-import
  # class (~7.6 s on the Atom) into its RAM overlay on every boot.
  compose_precompile_bytecode "$rootfs" || return 1
  compose_verify_audio_endpoint_plugin "$rootfs" || return 1
  # Clone-neutral target state is composer-owned so both the thin disk-image
  # consumer and the release-payload staging path share it. The live-installer
  # role stays role-specific (see compose_prepare_clone_neutral_target).
  if [[ "$role" == "target" ]]; then
    compose_prepare_clone_neutral_target "$rootfs" || return 1
  fi
}

if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
  # Direct execution is a public composition seam. Unlike sourced consumers,
  # it has no outer image-builder cleanup trap, so it must own the mounts it
  # creates. Sourced callers keep their existing lifecycle unchanged.
  MOUNTS=()
  _compose_direct_cleanup() {
    local original_status=$?
    trap - EXIT INT TERM
    set +e
    safe_unmount_paths "${MOUNTS[@]}"
    local cleanup_status=$?
    if (( cleanup_status != 0 && original_status == 0 )); then
      exit 1
    fi
    exit "$original_status"
  }
  trap _compose_direct_cleanup EXIT
  trap 'exit 130' INT
  trap 'exit 143' TERM
  compose_root "$@"
fi
