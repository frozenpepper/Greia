#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd -- "$SCRIPT_DIR/.." && pwd)"
OUTPUT_DIR="${1:-$PROJECT_ROOT/out}"
PROFILE_INPUT="${2:-modern-amd64-dev}"
PROFILE_ID="${PROFILE_INPUT%.toml}"
PROFILE_TOOL="$PROJECT_ROOT/tools/build_profile.py"
PACKAGE_ROOT="$PROJECT_ROOT/build/package-sets"

[[ ${EUID:-$(id -u)} -eq 0 ]] || {
  echo "Run as root: sudo build/build-developer-image.sh [OUTPUT_DIR] [PROFILE]" >&2
  exit 1
}

PROFILE_PATH="$PROJECT_ROOT/build/profiles/${PROFILE_ID}.toml"
[[ -r "$PROFILE_PATH" ]] || { echo "Developer profile not found: $PROFILE_PATH" >&2; exit 1; }
[[ "$PROFILE_ID" == *-dev ]] || {
  echo "Refusing developer build for a non-dev profile: $PROFILE_ID" >&2
  exit 1
}
python3 "$PROFILE_TOOL" --package-root "$PACKAGE_ROOT" validate "$PROFILE_PATH" >/dev/null
sets="$(python3 "$PROFILE_TOOL" --package-root "$PACKAGE_ROOT" package-sets "$PROFILE_PATH" --scope target)"
printf '%s\n' "$sets" | grep -qx 'developer-remote' || {
  echo "Refusing developer build: target profile lacks developer-remote." >&2
  exit 1
}

mkdir -p "$OUTPUT_DIR"
OUTPUT_DIR="$(realpath "$OUTPUT_DIR")"

# The dev profile itself owns the recovery SSH contract. Do NOT run the old
# provision_developer_image.py client-key workflow: it created a separate
# greiaadmin keypair and a second authentication model that is no longer part of
# Greia development. The target builder already provisions the simple greia
# password account and runtime sshd bootstrap for explicit developer profiles.
"$SCRIPT_DIR/build-image.sh" "$PROFILE_ID" "$OUTPUT_DIR"
image="$OUTPUT_DIR/greia-os-${PROFILE_ID}.img"

bash "$PROJECT_ROOT/tools/verify-development-target-image.sh" "$image"

# Remove stale key artifacts from the retired workflow so an old file in out/
# cannot be mistaken for a credential required by the newly built image.
rm -f "$OUTPUT_DIR/greia-os-${PROFILE_ID}-ssh-key" \
      "$OUTPUT_DIR/greia-os-${PROFILE_ID}-ssh-key.pub"

cat <<EOF

Greia developer image ready.
Profile: $PROFILE_ID
Image: $image
SSH user: greia
Host hint after first boot: greia-dev.local
SSH login mode: simple password; no operator SSH key file is generated or required.
EOF
