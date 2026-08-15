#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd -- "$SCRIPT_DIR/.." && pwd)"
PROFILE="legacy-x86-i686"
OUTPUT_DIR="${1:-$PROJECT_ROOT/out}"

usage() {
  cat <<'USAGE'
Usage: sudo build/build-legacy-x86-sd-installer.sh [OUTPUT_DIR]

Build the generic Greia legacy-x86/i686 graphical installer and place the
one-shot Linux hardware-evidence collector directly on the installer media.
This command intentionally does NOT inspect a target PC before building.
USAGE
}

[[ $# -le 1 ]] || { usage >&2; exit 2; }
[[ ${EUID:-$(id -u)} -eq 0 ]] || {
  echo "Run as root: sudo build/build-legacy-x86-sd-installer.sh [OUTPUT_DIR]" >&2
  exit 1
}

mkdir -p "$OUTPUT_DIR"
OUTPUT_DIR="$(realpath "$OUTPUT_DIR")"

"$SCRIPT_DIR/build-installer-image.sh" "$PROFILE" "$OUTPUT_DIR"

IMAGE="$OUTPUT_DIR/greia-os-installer-${PROFILE}.img"
REPORT="$OUTPUT_DIR/greia-os-installer-${PROFILE}-report.txt"
FINAL_DIGEST="$OUTPUT_DIR/greia-os-installer-${PROFILE}.sha256"
[[ -f "$IMAGE" && -f "$REPORT" ]] || {
  echo "Canonical installer build did not produce the expected image/report." >&2
  exit 1
}

required=(losetup mount umount mountpoint sync python3 sha256sum install)
for command_name in "${required[@]}"; do
  command -v "$command_name" >/dev/null || {
    echo "Missing post-build dependency: $command_name" >&2
    exit 1
  }
done

WORK="$(mktemp -d -p "${TMPDIR:-/tmp}" greia-sd-finalize.XXXXXX)"
MOUNT="$WORK/media"
LOOP=""
mkdir -p "$MOUNT"

cleanup() {
  local status=$?
  set +e
  if [[ -n "$LOOP" ]]; then
    if mountpoint -q "$MOUNT"; then umount "$MOUNT"; fi
    losetup -d "$LOOP" 2>/dev/null || true
  fi
  rmdir "$MOUNT" 2>/dev/null || true
  rmdir "$WORK" 2>/dev/null || true
  return "$status"
}
trap cleanup EXIT INT TERM

LOOP="$(losetup --find --show --partscan "$IMAGE")"
PART="${LOOP}p1"
for _ in {1..30}; do
  [[ -b "$PART" ]] && break
  sleep 0.2
done
[[ -b "$PART" ]] || {
  echo "Installer image partition did not appear during SD finalization." >&2
  exit 1
}

mount "$PART" "$MOUNT"
install -d -m 0755 "$MOUNT/greia-tools" "$MOUNT/greia-evidence"
install -m 0755 \
  "$PROJECT_ROOT/tools/collect-linux-hardware-evidence.sh" \
  "$MOUNT/greia-tools/collect-linux-hardware-evidence.sh"
cat > "$MOUNT/greia-tools/README.txt" <<'README'
Greia engineering hardware evidence
===================================

This tool is OPTIONAL evidence collection. It is not needed to choose or boot
this installer and it does not select drivers/packages.

From an existing Linux installation after mounting this installer partition
read-write at /mnt/greia-sd, run:

  sudo bash /mnt/greia-sd/greia-tools/collect-linux-hardware-evidence.sh \
      /mnt/greia-sd/greia-evidence

The script writes one timestamped .txt report under /greia-evidence on this SD.
No hand-copying terminal output is required.
README
chmod 0644 "$MOUNT/greia-tools/README.txt"
sync
umount "$MOUNT"
losetup -d "$LOOP"
LOOP=""

FINAL_SHA="$(sha256sum "$IMAGE" | awk '{print $1}')"
printf '%s  %s\n' "$FINAL_SHA" "$(basename "$IMAGE")" > "$FINAL_DIGEST"

python3 - "$REPORT" "$FINAL_SHA" <<'PY'
from pathlib import Path
import sys
path = Path(sys.argv[1])
digest = sys.argv[2]
lines = path.read_text(encoding="utf-8").splitlines()
updated = []
seen_sha = False
for line in lines:
    if line.startswith("sha256="):
        updated.append(f"sha256={digest}")
        seen_sha = True
    elif not line.startswith("hardware_evidence_tool=") and not line.startswith("hardware_evidence_output_dir="):
        updated.append(line)
if not seen_sha:
    raise SystemExit("installer report has no sha256 field")
updated.append("hardware_evidence_tool=/greia-tools/collect-linux-hardware-evidence.sh")
updated.append("hardware_evidence_output_dir=/greia-evidence")
path.write_text("\n".join(updated) + "\n", encoding="utf-8")
PY

cat <<EOF

Greia generic legacy-x86 SD installer ready.
Profile: $PROFILE
Image: $IMAGE
Final SHA-256: $FINAL_SHA
Digest file: $FINAL_DIGEST
Report: $REPORT
Optional Linux evidence tool on media: /greia-tools/collect-linux-hardware-evidence.sh
EOF
