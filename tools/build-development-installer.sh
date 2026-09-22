#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd -- "$SCRIPT_DIR/.." && pwd)"
PROFILE_TOOL="$PROJECT_ROOT/tools/build_profile.py"
PACKAGE_ROOT="$PROJECT_ROOT/build/package-sets"
CANONICAL_BUILDER="$PROJECT_ROOT/build/build-installer-image.sh"
LEGACY_BUILDER="$PROJECT_ROOT/build/build-legacy-x86-sd-installer.sh"
VERIFIER="$PROJECT_ROOT/tools/verify-development-installer.sh"

usage() {
  cat >&2 <<'EOF'
Usage: sudo bash tools/build-development-installer.sh PROFILE [OUTPUT_DIR] [--release-bundle PATH]

Build a Greia development installer only when BOTH the live installer and the
installed-system payload explicitly include the developer-remote capability.
Legacy-x86 profiles are routed through the physically proven legacy installer
builder without changing its boot-critical artwork/media recipe. Afterward the
finished image and both embedded squashfs artifacts are checked for the
SSH/network recovery contract.
For A/B target profiles pass --release-bundle (forwarded to the installer
builder with the validated .greiaupdate v3 artifact).
EOF
}

RELEASE_BUNDLE_ARGS=()
positional=()
while [[ $# -gt 0 ]]; do
  case "$1" in
    --release-bundle)
      [[ $# -ge 2 ]] || { echo "--release-bundle requires a PATH argument." >&2; exit 2; }
      RELEASE_BUNDLE_ARGS=(--release-bundle "$2")
      shift 2
      ;;
    --release-bundle=*)
      RELEASE_BUNDLE_ARGS=(--release-bundle "${1#--release-bundle=}")
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    --)
      shift
      while [[ $# -gt 0 ]]; do positional+=("$1"); shift; done
      ;;
    -*)
      echo "Unknown option: $1" >&2
      usage
      exit 2
      ;;
    *)
      positional+=("$1")
      shift
      ;;
  esac
done

[[ ${#positional[@]} -ge 1 && ${#positional[@]} -le 2 ]] || { usage; exit 2; }
[[ ${EUID:-$(id -u)} -eq 0 ]] || { echo "Run as root." >&2; exit 1; }

profile_input="${positional[0]}"
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

readarray -t PROFILE_FACTS < <(python3 - "$PROFILE_PATH" <<'PY'
import sys, tomllib
from pathlib import Path
raw = tomllib.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
print(raw["profile"]["id"])
print(raw["platform"]["family"])
print(raw["image"]["hostname"])
PY
)
PROFILE_ID="${PROFILE_FACTS[0]}"
PLATFORM_FAMILY="${PROFILE_FACTS[1]}"
TARGET_HOSTNAME="${PROFILE_FACTS[2]}"
[[ "$PROFILE_ID" == *-dev ]] || {
  echo "Refusing development installer: profile id is not explicitly *-dev: $PROFILE_ID" >&2
  exit 1
}

OUTPUT_DIR="${positional[1]:-$PROJECT_ROOT/out}"
mkdir -p "$OUTPUT_DIR"
OUTPUT_DIR="$(realpath "$OUTPUT_DIR")"

printf '%s\n' "Building development installer profile: $PROFILE_ID"
case "$PLATFORM_FAMILY" in
  legacy-x86)
    # Reference Acer hardware is proven through this legacy builder and the
    # Syslinux/FAT32 writer documented in INSTALLATION_USB_BOOT_POSTMORTEM.md.
    # Do not insert boot-art or console-cleanup experiments into this front door
    # without a new physical acceptance pass.
    bash "$LEGACY_BUILDER" "$PROFILE_ID" "$OUTPUT_DIR" ${RELEASE_BUNDLE_ARGS[@]+"${RELEASE_BUNDLE_ARGS[@]}"}
    ;;
  *)
    # Other families currently use the generic builder. Their physical boot
    # evidence remains profile-specific; the post-build SSH verifier still runs.
    bash "$CANONICAL_BUILDER" "$PROFILE_PATH" "$OUTPUT_DIR" ${RELEASE_BUNDLE_ARGS[@]+"${RELEASE_BUNDLE_ARGS[@]}"}
    ;;
esac

IMAGE="$OUTPUT_DIR/greia-os-installer-${PROFILE_ID}.img"
[[ -f "$IMAGE" ]] || {
  echo "Installer builder completed without expected image: $IMAGE" >&2
  exit 1
}

bash "$VERIFIER" "$IMAGE"

cat <<EOF
Development installer ready: $IMAGE
Live installer host: greia-installer.local
Installed host: ${TARGET_HOSTNAME}.local
SSH user: greia
SSH login mode: simple password; no operator SSH key required
EOF
