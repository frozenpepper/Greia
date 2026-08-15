#!/usr/bin/env bash
set -Eeuo pipefail

# Read Greia engineering evidence back from the ext4 installer SD on macOS.
# The physical SD is never mounted read-write or modified by this script.
# Usage: bash tools/mac-extract-greia-sd-evidence.sh /dev/diskN [OUTPUT_DIR]

[[ "$(uname -s)" == "Darwin" ]] || {
  echo "This helper is for macOS." >&2
  exit 2
}
[[ $# -ge 1 && $# -le 2 ]] || {
  echo "Usage: $0 /dev/diskN [OUTPUT_DIR]" >&2
  exit 2
}

DISK="$1"
[[ "$DISK" =~ ^/dev/disk[0-9]+$ ]] || {
  echo "Pass a whole macOS disk such as /dev/disk4, not a partition." >&2
  exit 2
}
PART="${DISK}s1"
RDPART="/dev/r${PART#/dev/}"
OUTPUT_DIR="${2:-$PWD/greia-sd-evidence}"
INSTANCE="greia-builder-x86"

command -v diskutil >/dev/null
command -v limactl >/dev/null || {
  echo "Lima is not installed. Run tools/mac-build-legacy-x86-sd.sh first." >&2
  exit 1
}

diskutil info "$DISK"
diskutil info "$PART" >/dev/null || {
  echo "First Greia installer partition is not visible as $PART." >&2
  exit 1
}

# Ensure the host is not using any filesystem on the SD. This does not erase it.
diskutil unmountDisk "$DISK" >/dev/null || true

TMP="$(mktemp -d -t greia-sd-evidence.XXXXXX)"
cleanup() {
  rm -rf "$TMP"
}
trap cleanup EXIT INT TERM
PART_IMAGE="$TMP/greia-installer-partition.img"

# Read only partition 1 rather than imaging the unused remainder of a larger SD.
sudo dd if="$RDPART" of="$PART_IMAGE" bs=4m

# The builder VM is x86_64 Linux and can mount the ext4 partition image.
limactl shell --start "$INSTANCE" true >/dev/null
limactl copy --backend=scp "$PART_IMAGE" "$INSTANCE:/tmp/greia-installer-partition.img"
limactl shell "$INSTANCE" bash -lc '
  set -Eeuo pipefail
  M=/tmp/greia-evidence-mount
  rm -rf "$M" /tmp/greia-evidence.tar.gz
  mkdir -p "$M"
  cleanup() { sudo umount "$M" 2>/dev/null || true; rmdir "$M" 2>/dev/null || true; }
  trap cleanup EXIT
  sudo mount -o loop,ro /tmp/greia-installer-partition.img "$M"
  if [[ ! -d "$M/greia-evidence" ]]; then
    echo "Greia evidence directory is absent on the SD." >&2
    exit 1
  fi
  tar -czf /tmp/greia-evidence.tar.gz -C "$M" greia-evidence
'

mkdir -p "$OUTPUT_DIR"
limactl copy --backend=scp "$INSTANCE:/tmp/greia-evidence.tar.gz" "$TMP/greia-evidence.tar.gz"
tar -xzf "$TMP/greia-evidence.tar.gz" -C "$OUTPUT_DIR" --strip-components=1

cat <<EOF
Greia SD evidence extracted read-only to:
  $OUTPUT_DIR
EOF
