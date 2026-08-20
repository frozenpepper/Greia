#!/usr/bin/env bash
set -Eeuo pipefail

[[ $# -eq 1 ]] || {
  echo "Usage: sudo bash tools/verify-development-target-image.sh IMAGE" >&2
  exit 2
}
[[ ${EUID:-$(id -u)} -eq 0 ]] || { echo "Run as root." >&2; exit 1; }
IMAGE="$(realpath "$1")"
[[ -f "$IMAGE" ]] || { echo "Developer image not found: $IMAGE" >&2; exit 1; }

for command_name in losetup mount umount mountpoint awk grep realpath; do
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
  local status=$?
  trap - EXIT INT TERM
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

for network in 20-greia-wired.network 25-greia-wireless.network; do
  path="$MOUNT/etc/systemd/network/$network"
  [[ -f "$path" ]] || { echo "Developer target: missing $network" >&2; exit 1; }
  grep -Fq 'DHCP=yes' "$path" || { echo "Developer target: $network lacks DHCP." >&2; exit 1; }
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
printf '%s\n' "- no cloned SSH host private key"
