#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd -- "$SCRIPT_DIR/.." && pwd)"
OUTPUT_DIR="${1:-$PROJECT_ROOT/out}"
PROFILE="${2:-modern-amd64-dev}"

[[ ${EUID:-$(id -u)} -eq 0 ]] || {
  echo "Run as root: sudo build/build-developer-image.sh [OUTPUT_DIR] [PROFILE]" >&2
  exit 1
}

mkdir -p "$OUTPUT_DIR"
OUTPUT_DIR="$(realpath "$OUTPUT_DIR")"

"$SCRIPT_DIR/build-image.sh" "$PROFILE" "$OUTPUT_DIR"
image="$OUTPUT_DIR/greia-os-${PROFILE}.img"

python3 "$PROJECT_ROOT/tools/provision_developer_image.py" \
  --image "$image" \
  --output-dir "$OUTPUT_DIR" \
  --expected-profile "$PROFILE"

cat <<EOF

Greia developer image ready.
Profile: $PROFILE
Image: $image
SSH user: greiaadmin
Host hint after first boot: greia-dev.local
Private key: $OUTPUT_DIR/greia-os-${PROFILE}-ssh-key
Remote helper example:
  python3 tools/greia_remote.py --host greia-dev.local --key '$OUTPUT_DIR/greia-os-${PROFILE}-ssh-key' status
EOF