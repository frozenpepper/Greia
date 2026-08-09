#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd -- "$SCRIPT_DIR/.." && pwd)"
PROFILE="modern-amd64-dev"
OUTPUT_DIR="${1:-$PROJECT_ROOT/out}"

[[ ${EUID:-$(id -u)} -eq 0 ]] || {
  echo "Run as root: sudo build/build-developer-image.sh [OUTPUT_DIR]" >&2
  exit 1
}

mkdir -p "$OUTPUT_DIR"
OUTPUT_DIR="$(realpath "$OUTPUT_DIR")"

"$SCRIPT_DIR/build-image.sh" "$PROFILE" "$OUTPUT_DIR"
image="$OUTPUT_DIR/greia-os-${PROFILE}.img"

python3 "$PROJECT_ROOT/tools/provision_developer_image.py" \
  --image "$image" \
  --output-dir "$OUTPUT_DIR"

cat <<EOF

Greia developer image ready.
Image: $image
SSH user: greiaadmin
Host hint after first boot: greia-dev.local
Private key: $OUTPUT_DIR/greia-os-${PROFILE}-ssh-key
Remote helper example:
  python3 tools/greia_remote.py --host greia-dev.local --key '$OUTPUT_DIR/greia-os-${PROFILE}-ssh-key' status
EOF
