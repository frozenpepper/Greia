#!/usr/bin/env bash
set -Eeuo pipefail

PROJECT_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
# shellcheck source=../build/lib/safe-cleanup.sh
source "$PROJECT_ROOT/build/lib/safe-cleanup.sh"

[[ $# -eq 1 ]] || {
  echo "Usage: sudo bash tools/verify-development-target-image.sh IMAGE" >&2
  exit 2
}
[[ ${EUID:-$(id -u)} -eq 0 ]] || { echo "Run as root." >&2; exit 1; }
IMAGE="$(realpath "$1")"
[[ -f "$IMAGE" ]] || { echo "Developer image not found: $IMAGE" >&2; exit 1; }

for command_name in losetup partx blockdev udevadm findmnt mount umount mountpoint awk grep realpath; do
  command -v "$command_name" >/dev/null || {
    echo "Missing verifier dependency: $command_name" >&2
    exit 1
  }
done

WORK="$(mktemp -d -p "${TMPDIR:-/tmp}" greia-dev-target-verify.XXXXXX)"
MOUNT="$WORK/root"
LOOP=""
mkdir -p "$MOUNT"
cleanup() {
  local original_status=$?
  trap - EXIT INT TERM
  set +e
  local cleanup_failed=0
  safe_unmount_paths "$MOUNT" || cleanup_failed=1
  safe_detach_loop "$LOOP" || cleanup_failed=1
  if (( cleanup_failed == 0 )); then
    rm -rf "$WORK"
  else
    echo "Development-target verification cleanup was incomplete; preserving work data for inspection." >&2
    if (( original_status == 0 )); then
      exit 1
    fi
  fi
  exit "$original_status"
}
trap cleanup EXIT INT TERM

LOOP="$(losetup --find --show --partscan --read-only "$IMAGE")"
PART="${LOOP}p1"
for _ in {1..20}; do [[ -b "$PART" ]] && break; sleep 0.1; done
[[ -b "$PART" ]] || { echo "Developer image partition did not appear." >&2; exit 1; }
mount -o ro,noload "$PART" "$MOUNT"

hash="$(awk -F: '$1=="greia" {print $2; exit}' "$MOUNT/etc/shadow")"
[[ -n "$hash" && "$hash" != '!'* && "$hash" != '*'* ]] || {
  echo "Developer target: greia account is missing, locked, or passwordless." >&2
  exit 1
}

HELPER="$MOUNT/usr/local/lib/greia-os/prepare-developer-ssh"
DROPIN="$MOUNT/etc/systemd/system/ssh.service.d/10-greia-developer-bootstrap.conf"
[[ -f "$HELPER" && -f "$DROPIN" ]] || {
  echo "Developer target: SSH bootstrap files are missing." >&2
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
  grep -Fq "$required" "$HELPER" || {
    echo "Developer target: SSH contract is missing: $required" >&2
    exit 1
  }
done

grep -Fq 'prepare-developer-ssh' "$DROPIN" || exit 1
grep -Fq 'ExecStartPre=/usr/sbin/sshd -t' "$DROPIN" || exit 1
[[ -L "$MOUNT/etc/systemd/system/multi-user.target.wants/ssh.service" ]] || {
  echo "Developer target: ssh.service is not enabled." >&2
  exit 1
}
[[ -s "$MOUNT/etc/greia-os/developer-remote" ]] || {
  echo "Developer target: developer marker is missing." >&2
  exit 1
}

# Wired recovery networking is systemd-networkd's job and must keep DHCP.
path="$MOUNT/etc/systemd/network/20-greia-wired.network"
[[ -f "$path" ]] || { echo "Developer target: missing 20-greia-wired.network" >&2; exit 1; }
grep -Fq 'DHCP=yes' "$path" || { echo "Developer target: wired policy lacks DHCP." >&2; exit 1; }

# iwd owns Wi-Fi association/authentication while systemd-networkd owns
# L3/DHCP in the installed target. Pin both halves of that role contract.
iwd_conf="$MOUNT/etc/iwd/main.conf"
[[ -f "$iwd_conf" ]] || { echo "Developer target: missing /etc/iwd/main.conf" >&2; exit 1; }
grep -Fq 'EnableNetworkConfiguration=false' "$iwd_conf" || {
  echo "Developer target: iwd must leave target L3 configuration to networkd." >&2
  exit 1
}
path="$MOUNT/etc/systemd/network/25-greia-wireless.network"
[[ -f "$path" ]] || { echo "Developer target: missing 25-greia-wireless.network" >&2; exit 1; }
awk '
  BEGIN { in_network = 0; found = 0 }
  /^[[:space:]]*\[Network\][[:space:]]*$/ { in_network = 1; next }
  /^[[:space:]]*\[/ { in_network = 0 }
  in_network && /^[[:space:]]*DHCP=yes[[:space:]]*$/ { found = 1 }
  END { exit(found ? 0 : 1) }
' "$path" || {
  echo "Developer target: wireless policy must retain [Network] DHCP=yes behind iwd authentication." >&2
  exit 1
}
if awk '
  BEGIN { in_link = 0; bad = 0 }
  /^[[:space:]]*\[Link\][[:space:]]*$/ { in_link = 1; next }
  /^[[:space:]]*\[/ { in_link = 0 }
  in_link && /^[[:space:]]*Unmanaged=yes[[:space:]]*$/ { bad = 1 }
  END { exit(bad ? 0 : 1) }
' "$path"; then
  echo "Developer target: wireless policy must not mark Wi-Fi Unmanaged while networkd owns DHCP." >&2
  exit 1
fi

# Hardware-recovery target images must preserve the postmortem diagnostic
# channel: tty1 visible, no timed panic reboot, and enough kernel/systemd status
# to identify the failing stage. Normal/release behavior remains conditional in
# this same generator and is not changed by the development marker.
GRUB_POLICY="$MOUNT/etc/grub.d/10_greia_appliance"
[[ -f "$GRUB_POLICY" ]] || {
  echo "Developer target: Greia GRUB policy is missing." >&2
  exit 1
}
for required in \
  'developer-remote' \
  'console_arg="console=tty1"' \
  'panic_arg="panic=0"' \
  'loglevel=4' \
  'systemd.show_status=true' \
  'rd.systemd.show_status=true'
do
  grep -Fq "$required" "$GRUB_POLICY" || {
    echo "Developer target: boot diagnostic contract is missing: $required" >&2
    exit 1
  }
done

# A raw/cloned image must not carry a server private identity. The runtime
# bootstrap creates one Ed25519 host key on the actual booted machine.
if find "$MOUNT/etc/ssh" -maxdepth 1 -type f -name 'ssh_host_*_key' -print -quit | grep -q .; then
  echo "Developer target: sealed image unexpectedly contains an SSH host private key." >&2
  exit 1
fi

printf '%s\n' "Developer target artifact verification: PASS"
printf '%s\n' "- password-enabled greia recovery account"
printf '%s\n' "- ssh.service enabled with runtime effective-policy validation"
printf '%s\n' "- DHCP policies present; root SSH denied by runtime contract"
printf '%s\n' "- tty1 diagnostics with panic=0 (no timed reboot)"
printf '%s\n' "- no cloned SSH host private key"
