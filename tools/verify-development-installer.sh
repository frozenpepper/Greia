#!/usr/bin/env bash
set -Eeuo pipefail

usage() {
  echo "Usage: sudo bash tools/verify-development-installer.sh INSTALLER_IMAGE" >&2
}

[[ $# -eq 1 ]] || { usage; exit 2; }
[[ ${EUID:-$(id -u)} -eq 0 ]] || { echo "Run as root." >&2; exit 1; }
IMAGE="$(realpath "$1")"
[[ -f "$IMAGE" ]] || { echo "Installer image not found: $IMAGE" >&2; exit 1; }

for command_name in losetup mount umount unsquashfs awk grep realpath; do
  command -v "$command_name" >/dev/null || {
    echo "Missing verifier dependency: $command_name" >&2
    exit 1
  }
done

WORK="$(mktemp -d -p "${TMPDIR:-/tmp}" greia-dev-installer-verify.XXXXXX)"
MOUNT="$WORK/media"
LOOP=""
mkdir -p "$MOUNT"
cleanup() {
  local status=$?
  set +e
  if mountpoint -q "$MOUNT" 2>/dev/null; then umount "$MOUNT"; fi
  [[ -z "$LOOP" ]] || losetup -d "$LOOP" 2>/dev/null || true
  rm -rf "$WORK"
  exit "$status"
}
trap cleanup EXIT INT TERM

LOOP="$(losetup --find --show --partscan --read-only "$IMAGE")"
PART="${LOOP}p1"
for _ in {1..20}; do [[ -b "$PART" ]] && break; sleep 0.1; done
[[ -b "$PART" ]] || { echo "Installer partition did not appear." >&2; exit 1; }
mount -o ro,noload "$PART" "$MOUNT"

LIVE="$MOUNT/live/filesystem.squashfs"
TARGET="$MOUNT/payload/pip-rootfs.squashfs"
[[ -r "$LIVE" ]] || { echo "Live installer squashfs is missing." >&2; exit 1; }
[[ -r "$TARGET" ]] || { echo "Installed-system payload squashfs is missing." >&2; exit 1; }

sqcat() {
  unsquashfs -cat "$1" "$2" 2>/dev/null
}

sqhas() {
  unsquashfs -ll "$1" "$2" 2>/dev/null | grep -q -- "$2"
}

check_account() {
  local squash="$1" label="$2" shadow hash
  shadow="$(sqcat "$squash" etc/shadow)" || {
    echo "$label: cannot read /etc/shadow from artifact." >&2
    exit 1
  }
  hash="$(printf '%s\n' "$shadow" | awk -F: '$1=="greia" {print $2; exit}')"
  [[ -n "$hash" && "$hash" != '!'* && "$hash" != '*'* ]] || {
    echo "$label: greia account is missing, locked, or passwordless." >&2
    exit 1
  }
}

check_ssh_runtime() {
  local squash="$1" label="$2" helper unit
  helper="$(sqcat "$squash" usr/local/lib/greia-os/prepare-developer-ssh)" || {
    echo "$label: developer SSH bootstrap helper is missing." >&2
    exit 1
  }
  unit="$(sqcat "$squash" etc/systemd/system/ssh.service.d/10-greia-developer-bootstrap.conf)" || {
    echo "$label: ssh.service developer bootstrap drop-in is missing." >&2
    exit 1
  }
  for required in \
    'AuthenticationMethods password' \
    'PasswordAuthentication yes' \
    'KbdInteractiveAuthentication no' \
    'PermitRootLogin no' \
    'AllowUsers greia' \
    'ssh_host_ed25519_key' \
    'sshd -T'
  do
    printf '%s\n' "$helper" | grep -Fq "$required" || {
      echo "$label: SSH runtime contract is missing: $required" >&2
      exit 1
    }
  done
  printf '%s\n' "$unit" | grep -Fq 'prepare-developer-ssh' || {
    echo "$label: sshd does not run Greia bootstrap before validation." >&2
    exit 1
  }
  printf '%s\n' "$unit" | grep -Fq 'ExecStartPre=/usr/sbin/sshd -t' || {
    echo "$label: sshd syntax validation is missing." >&2
    exit 1
  }
  sqhas "$squash" etc/systemd/system/multi-user.target.wants/ssh.service || {
    echo "$label: ssh.service is not enabled in the artifact." >&2
    exit 1
  }
}

check_network() {
  local squash="$1" label="$2"
  for path in \
    etc/systemd/network/20-greia-wired.network \
    etc/systemd/network/25-greia-wireless.network
  do
    content="$(sqcat "$squash" "$path")" || {
      echo "$label: missing recovery network policy $path" >&2
      exit 1
    }
    printf '%s\n' "$content" | grep -Fq 'DHCP=yes' || {
      echo "$label: $path does not enable DHCP." >&2
      exit 1
    }
  done
}

check_account "$LIVE" "live installer"
check_ssh_runtime "$LIVE" "live installer"
check_network "$LIVE" "live installer"

check_account "$TARGET" "installed-system payload"
check_ssh_runtime "$TARGET" "installed-system payload"
check_network "$TARGET" "installed-system payload"

TARGET_MARKER="$(sqcat "$TARGET" etc/greia-os/developer-remote)" || {
  echo "installed-system payload: developer marker is missing." >&2
  exit 1
}
[[ -n "$TARGET_MARKER" ]] || {
  echo "installed-system payload: developer marker is empty." >&2
  exit 1
}

LIVE_BUILD_INFO="$(sqcat "$LIVE" etc/greia-os/build-info)"
TARGET_BUILD_INFO="$(sqcat "$TARGET" etc/greia-os/build-info)"
printf '%s\n' "$LIVE_BUILD_INFO" | grep -Fq 'PIP_BUILD_PROFILE=' || exit 1
printf '%s\n' "$TARGET_BUILD_INFO" | grep -Fq 'PIP_BUILD_PROFILE=' || exit 1

printf '%s\n' "Developer installer artifact verification: PASS"
printf '%s\n' "- live installer: password-enabled greia account, sshd bootstrap, DHCP policy"
printf '%s\n' "- installed payload: password-enabled greia account, sshd bootstrap, DHCP policy"
printf '%s\n' "- root SSH remains denied; no operator SSH key is required"
