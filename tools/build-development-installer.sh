#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd -- "$SCRIPT_DIR/.." && pwd)"
PROFILE_TOOL="$PROJECT_ROOT/tools/build_profile.py"
PACKAGE_ROOT="$PROJECT_ROOT/build/package-sets"
BUILDER="$PROJECT_ROOT/build/build-installer-image.sh"
VERIFIER="$PROJECT_ROOT/tools/verify-development-installer.sh"

usage() {
  cat >&2 <<'EOF'
Usage: sudo bash tools/build-development-installer.sh PROFILE [OUTPUT_DIR]

Build a Greia development installer only when BOTH the live installer and the
installed-system payload explicitly include the developer-remote capability.
After the canonical build finishes, inspect the produced image and both embedded
squashfs artifacts for the SSH/network recovery contract.
EOF
}

[[ $# -ge 1 && $# -le 2 ]] || { usage; exit 2; }
[[ ${EUID:-$(id -u)} -eq 0 ]] || { echo "Run as root." >&2; exit 1; }

profile_input="$1"
if [[ -f "$profile_input" ]]; then
  PROFILE_PATH="$(realpath "$profile_input")"
else
  PROFILE_PATH="$PROJECT_ROOT/build/profiles/${profile_input%.toml}.toml"
fi
[[ -r "$PROFILE_PATH" ]] || { echo "Profile not found: $PROFILE_PATH" >&2; exit 1; }

python3 "$PROFILE_TOOL" --package-root "$PACKAGE_ROOT" validate "$PROFILE_PATH" >/dev/null
for scope in target installer; do
  sets="$(python3 "$PROFILE_TOOL" --package-root "$PACKAGE_ROOT" package-sets "$PROFILE_PATH" --scope "$scope")"
  printf '%s\n' "$sets" | grep -qx 'developer-remote' || {
    echo "Refusing development installer: $scope scope lacks developer-remote." >&2
    echo "Use an explicit *-dev Greia profile." >&2
    exit 1
  }
done

PROFILE_ID="$(python3 - "$PROFILE_PATH" <<'PY'
import sys, tomllib
from pathlib import Path
raw = tomllib.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
print(raw["profile"]["id"])
PY
)"
[[ "$PROFILE_ID" == *-dev ]] || {
  echo "Refusing development installer: profile id is not explicitly *-dev: $PROFILE_ID" >&2
  exit 1
}

OUTPUT_DIR="${2:-$PROJECT_ROOT/out}"
mkdir -p "$OUTPUT_DIR"
OUTPUT_DIR="$(realpath "$OUTPUT_DIR")"

printf '%s\n' "Building development installer profile: $PROFILE_ID"
bash "$BUILDER" "$PROFILE_PATH" "$OUTPUT_DIR"

IMAGE="$OUTPUT_DIR/greia-os-installer-${PROFILE_ID}.img"
[[ -f "$IMAGE" ]] || {
  echo "Canonical builder completed without expected image: $IMAGE" >&2
  exit 1
}

bash "$VERIFIER" "$IMAGE"

cat <<EOF
Development installer ready: $IMAGE
Live installer host: greia-installer.local
Installed host: use the profile hostname (normally greia-dev.local on Acer dev profiles)
SSH user: greia
SSH login mode: simple password; no operator SSH key required
EOF
