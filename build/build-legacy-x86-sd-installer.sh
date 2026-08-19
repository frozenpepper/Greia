#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd -- "$SCRIPT_DIR/.." && pwd)"
PROFILE="legacy-x86-i686"
PROFILE="${1:-$PROFILE}"
OUTPUT_DIR="${2:-$PROJECT_ROOT/out}"

usage() {
  cat <<'USAGE'
Usage: sudo build/build-legacy-x86-sd-installer.sh [PROFILE] [OUTPUT_DIR]

Build a Greia legacy-x86 graphical installer and place the one-shot AntiX boot
helper plus optional hardware-evidence collector directly on the installer
media. This command intentionally does NOT inspect a target PC before building.

PROFILE defaults to legacy-x86-i686 (the generic release-compatible image).
A developer profile (for example legacy-x86-i686-dev) additionally enables
default-on SSH and mDNS discovery for remote operator access.
USAGE
}

[[ $# -le 2 ]] || { usage >&2; exit 2; }
[[ ${EUID:-$(id -u)} -eq 0 ]] || {
  echo "Run as root: sudo build/build-legacy-x86-sd-installer.sh [OUTPUT_DIR]" >&2
  exit 1
}

mkdir -p "$OUTPUT_DIR"
OUTPUT_DIR="$(realpath "$OUTPUT_DIR")"

# The repository retains generated boot derivatives because they are useful to
# source tests and non-builder consumers, but a physical installer must never
# trust that those generated files are current. Regenerate them from the
# canonical retained full-color frame for the duration of this build so BOTH
# the live installer and the installable target payload consume the same fresh
# RGB artwork. Restore the caller's checkout bytes afterwards, even on failure,
# so building an image does not silently dirty or rewrite source state.
BOOT_GENERATOR="$PROJECT_ROOT/tools/generate_boot_artwork.py"
BOOT_DERIVATIVES=(
  "assets/boot/source/greia-boot-logo.png"
  "assets/boot/static/greia-boot-logo.png"
  "build/overlay/etc/greia-boot/boot-logo.ppm"
  "build/installer-overlay/etc/greia-boot/boot-logo.ppm"
)
BOOT_BACKUP="$(mktemp -d -p "${TMPDIR:-/tmp}" greia-boot-art-backup.XXXXXX)"
BOOT_RESTORED=0

restore_boot_derivatives() {
  local status=$?
  set +e
  if [[ "$BOOT_RESTORED" != "1" ]]; then
    for relative in "${BOOT_DERIVATIVES[@]}"; do
      if [[ -e "$BOOT_BACKUP/$relative" ]]; then
        mkdir -p "$(dirname "$PROJECT_ROOT/$relative")"
        cp -a "$BOOT_BACKUP/$relative" "$PROJECT_ROOT/$relative"
      else
        rm -f "$PROJECT_ROOT/$relative"
      fi
    done
    rm -rf "$BOOT_BACKUP"
    BOOT_RESTORED=1
  fi
  return "$status"
}
trap restore_boot_derivatives EXIT INT TERM

for relative in "${BOOT_DERIVATIVES[@]}"; do
  if [[ -e "$PROJECT_ROOT/$relative" ]]; then
    mkdir -p "$(dirname "$BOOT_BACKUP/$relative")"
    cp -a "$PROJECT_ROOT/$relative" "$BOOT_BACKUP/$relative"
  fi
done

python3 - <<'PY'
try:
    from PIL import Image  # noqa: F401
except ImportError as exc:
    raise SystemExit(
        "The legacy installer build needs host python3-pil to derive canonical boot artwork. "
        "Install python3-pil on the Debian/Ubuntu build host."
    ) from exc
PY
python3 "$BOOT_GENERATOR"

# Guard the exact generated semantics before a multi-minute image build starts.
python3 - "$PROJECT_ROOT" <<'PY'
from pathlib import Path
import sys
from PIL import Image
root = Path(sys.argv[1])
source = Image.open(root / "assets/boot/source/legacy-plymouth-theme/frames/frame_0051.png").convert("RGB")
static = Image.open(root / "assets/boot/static/greia-boot-logo.png").convert("RGB")
if source.size != (222, 600) or static.size != source.size:
    raise SystemExit(f"unexpected canonical boot-art geometry: source={source.size} static={static.size}")
if source.tobytes() != static.tobytes():
    raise SystemExit("generated boot PNG is not pixel-identical to the canonical full-color frame")
if len(set(source.getdata())) < 256:
    raise SystemExit("canonical boot frame unexpectedly lost full-color detail")
PY

"$SCRIPT_DIR/build-installer-image.sh" "$PROFILE" "$OUTPUT_DIR"

# From this point the finished image contains its own copies. Restore the source
# checkout immediately; the later media-finalization phase must not depend on
# generated repository files.
restore_boot_derivatives
trap - EXIT INT TERM

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
install -m 0755 \
  "$PROJECT_ROOT/tools/prepare-antix-sd-boot.sh" \
  "$MOUNT/greia-tools/prepare-antix-sd-boot.sh"
cat > "$MOUNT/greia-tools/README.txt" <<'README'
Greia legacy-x86 SD helper tools
================================

The generic Greia legacy-x86 installer is already selected. Neither helper
chooses an image, driver, kernel flavor, or firmware package.

On a machine currently running AntiX/Linux, mount this Greia SD read-write and
run ONE command from the SD:

  sudo bash <SD-MOUNT>/greia-tools/prepare-antix-sd-boot.sh

That helper:
  * infers the SD device from its own mounted path;
  * verifies the Greia kernel/initrd/live filesystem/payload;
  * runs the optional hardware-evidence collector and writes one report under
    <SD-MOUNT>/greia-evidence/;
  * creates the AntiX GRUB entry for booting this SD;
  * runs update-grub and verifies the entry exists.

The evidence report is for engineering/certification only. No hand-copying
terminal output to another computer is required.
README
chmod 0644 "$MOUNT/greia-tools/README.txt"
sync
umount "$MOUNT"
losetup -d "$LOOP"
LOOP=""

FINAL_SHA="$(sha256sum "$IMAGE" | awk '{print $1}')"
printf '%s  %s\n' "$FINAL_SHA" "$(basename "$IMAGE")" > "$FINAL_DIGEST"
BOOT_SOURCE_SHA="$(sha256sum "$PROJECT_ROOT/assets/boot/source/legacy-plymouth-theme/frames/frame_0051.png" | awk '{print $1}')"

python3 - "$REPORT" "$FINAL_SHA" "$BOOT_SOURCE_SHA" <<'PY'
from pathlib import Path
import sys
path = Path(sys.argv[1])
digest = sys.argv[2]
boot_source_digest = sys.argv[3]
lines = path.read_text(encoding="utf-8").splitlines()
updated = []
seen_sha = False
for line in lines:
    if line.startswith("sha256="):
        updated.append(f"sha256={digest}")
        seen_sha = True
    elif not line.startswith("hardware_evidence_tool=") and not line.startswith("hardware_evidence_output_dir=") and not line.startswith("antix_sd_boot_helper=") and not line.startswith("boot_artwork_source_sha256="):
        updated.append(line)
if not seen_sha:
    raise SystemExit("installer report has no sha256 field")
updated.append(f"boot_artwork_source_sha256={boot_source_digest}")
updated.append("boot_artwork_mode=canonical-full-color-rgb")
updated.append("hardware_evidence_tool=/greia-tools/collect-linux-hardware-evidence.sh")
updated.append("hardware_evidence_output_dir=/greia-evidence")
updated.append("antix_sd_boot_helper=/greia-tools/prepare-antix-sd-boot.sh")
path.write_text("\n".join(updated) + "\n", encoding="utf-8")
PY

cat <<EOF

Greia generic legacy-x86 SD installer ready.
Profile: $PROFILE
Image: $IMAGE
Final SHA-256: $FINAL_SHA
Boot artwork: canonical full-color frame ($BOOT_SOURCE_SHA)
Digest file: $FINAL_DIGEST
Report: $REPORT
AntiX one-shot boot helper on media: /greia-tools/prepare-antix-sd-boot.sh
Optional hardware evidence tool on media: /greia-tools/collect-linux-hardware-evidence.sh
EOF
