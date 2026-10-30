#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd -- "$SCRIPT_DIR/.." && pwd)"
MEDIA_VERIFIER="$PROJECT_ROOT/tools/verify-live-usb.sh"

usage() {
  cat >&2 <<'EOF'
Usage: sudo bash tools/build-and-flash-development-usb.sh PROFILE USB_DEVICE [OUTPUT_DIR] [--operator-key PUBKEY_FILE]

Builds an explicit Greia development installer, verifies the live and target
SSH/network contracts, writes the physically proven Acer Syslinux/FAT32 layout
with the unchanged canonical writer, then verifies the finished media through a
separate read-only verifier.

PROFILE is an explicit developer profile (*-dev, diagnostic boot console) or
the developer release candidate (legacy-x86-i686-rc: quiet boot, SSH on).
--operator-key installs an operator SSH PUBLIC key for the greia account.

USB_DEVICE IS DESTROYED. Example: /dev/sdd
EOF
}

OPERATOR_KEY_ARGS=()
positional=()
while [[ $# -gt 0 ]]; do
  case "$1" in
    --operator-key)
      [[ $# -ge 2 ]] || { echo "--operator-key requires a PUBKEY_FILE argument." >&2; exit 2; }
      OPERATOR_KEY_ARGS=(--operator-key "$2")
      shift 2
      ;;
    -h|--help) usage; exit 0 ;;
    *) positional+=("$1"); shift ;;
  esac
done
[[ ${#positional[@]} -ge 2 && ${#positional[@]} -le 3 ]] || { usage; exit 2; }
[[ ${EUID:-$(id -u)} -eq 0 ]] || { echo "Run as root." >&2; exit 1; }
PROFILE="${positional[0]}"
DEVICE="${positional[1]}"
OUTPUT_DIR="${positional[2]:-$PROJECT_ROOT/out}"

[[ -b "$DEVICE" ]] || { echo "USB target is not a block device: $DEVICE" >&2; exit 1; }
for command_name in lsblk realpath losetup grep; do
  command -v "$command_name" >/dev/null || { echo "Missing dependency: $command_name" >&2; exit 1; }
done
[[ -x "$MEDIA_VERIFIER" ]] || { echo "Missing executable media verifier: $MEDIA_VERIFIER" >&2; exit 1; }

# Duplicate the most important destructive preflight before spending time on a
# build. build-live-usb.sh performs the authoritative destructive check again
# immediately before wiping the device.
RM="$(lsblk -dn -o RM "$DEVICE" 2>/dev/null | tr -d '[:space:]' || echo 0)"
TYPE="$(lsblk -dn -o TYPE "$DEVICE" 2>/dev/null | tr -d '[:space:]' || echo part)"
if [[ "$RM" != "1" || "$TYPE" != "disk" ]]; then
  echo "Refusing: $DEVICE is not a removable whole disk (RM=$RM TYPE=$TYPE)." >&2
  exit 1
fi
mapfile -t MOUNTED < <(lsblk -nrpo NAME,MOUNTPOINT "$DEVICE" 2>/dev/null | awk 'NF >= 2 && $2 != "" {print $1 " -> " $2}')
if (( ${#MOUNTED[@]} > 0 )); then
  echo "Refusing: USB target has mounted filesystems:" >&2
  printf '  %s\n' "${MOUNTED[@]}" >&2
  exit 1
fi

OUTPUT_DIR="$(mkdir -p "$OUTPUT_DIR" && realpath "$OUTPUT_DIR")"

greia_build_loops() {
  losetup -a 2>/dev/null | grep -Ei 'greia-(build|installer|live|sd|dev|os)' || true
}

PREEXISTING_GREIA_LOOPS="$(greia_build_loops)"
if [[ -n "$PREEXISTING_GREIA_LOOPS" ]]; then
  echo "Refusing: pre-existing Greia build loop devices must be cleared before build+flash:" >&2
  printf '%s\n' "$PREEXISTING_GREIA_LOOPS" >&2
  exit 1
fi

printf '%s\n' "Greia development build+flash target:"
lsblk -dn -o NAME,SIZE,MODEL,SERIAL,TRAN,RM,TYPE "$DEVICE" || true

bash "$PROJECT_ROOT/tools/build-development-installer.sh" "$PROFILE" "$OUTPUT_DIR" ${OPERATOR_KEY_ARGS[@]+"${OPERATOR_KEY_ARGS[@]}"}

PROFILE_PATH="$PROFILE"
if [[ ! -f "$PROFILE_PATH" ]]; then
  PROFILE_PATH="$PROJECT_ROOT/build/profiles/${PROFILE%.toml}.toml"
fi
[[ -r "$PROFILE_PATH" ]] || { echo "Profile disappeared after build: $PROFILE_PATH" >&2; exit 1; }
PROFILE_ID="$(python3 - "$PROFILE_PATH" <<'PY'
import sys, tomllib
from pathlib import Path
raw = tomllib.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
print(raw["profile"]["id"])
PY
)"
ARTIFACT_PROFILE="${PROFILE_ID#acer-aspire-one-}"
[[ -n "$ARTIFACT_PROFILE" ]] || ARTIFACT_PROFILE="installer"
IMAGE="$OUTPUT_DIR/greia-os-installer-${ARTIFACT_PROFILE}.img"
CONSOLE_POLICY="$(python3 "$PROJECT_ROOT/tools/build_profile.py" shell "$PROFILE_PATH" | sed -n "s/^BOOT_CONSOLE_POLICY=//p" | tr -d "'")"
if [[ "$CONSOLE_POLICY" == quiet ]]; then
  BOOT_DIAGNOSTICS="hidden: hold Shift/Alt at USB boot and type 'verbose'; installed GRUB: hold Shift, owner-only diagnostics entry"
else
  BOOT_DIAGNOSTICS="console-tty1"
fi
[[ -f "$IMAGE" ]] || { echo "Verified development installer image is missing: $IMAGE" >&2; exit 1; }

# Do not alter the proven writer to add verification behavior. The postmortem
# records the exact writer mechanics that boot the reference Acer. Verify only
# after that writer has finished and synced the media.
bash "$PROJECT_ROOT/tools/build-live-usb.sh" "$IMAGE" "$DEVICE"
bash "$MEDIA_VERIFIER" "$IMAGE" "$DEVICE"

REMAINING_GREIA_LOOPS="$(greia_build_loops)"
if [[ -n "$REMAINING_GREIA_LOOPS" ]]; then
  echo "Build+flash failed loop-hygiene verification; Greia loop devices remain:" >&2
  printf '%s\n' "$REMAINING_GREIA_LOOPS" >&2
  exit 1
fi

cat <<EOF

Greia development installer BUILD + FLASH complete.
profile=$PROFILE_ID
source_image=$IMAGE
usb_device=$DEVICE
source_artifact_verification=PASS
usb_flash_readback_verification=PASS
loop_hygiene_verification=PASS
boot_writer=postmortem-proven-syslinux-fat32
boot_console_policy=$CONSOLE_POLICY
boot_diagnostics=$BOOT_DIAGNOSTICS
panic_policy=halt-on-panic
ssh_user=greia
ssh_login=password (greia/greia)${OPERATOR_KEY_ARGS[1]:+ or operator public key}; no operator SSH key is required for password login
EOF
