#!/usr/bin/env bash
set -Eeuo pipefail

# Build Greia's generic legacy-x86 SD installer from macOS using an isolated
# x86_64 Lima/QEMU Linux VM. This script deliberately does not inspect the
# eventual target PC. Hardware discovery remains Greia/Linux-owned.

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd -- "$SCRIPT_DIR/.." && pwd)"
INSTANCE="greia-builder-x86"
PROFILE="legacy-x86-i686"

[[ "$(uname -s)" == "Darwin" ]] || {
  echo "This helper is for macOS. On Linux run build/build-legacy-x86-sd-installer.sh directly." >&2
  exit 2
}

for command_name in git tar shasum; do
  command -v "$command_name" >/dev/null || {
    echo "Required macOS command is missing: $command_name" >&2
    exit 1
  }
done

if ! command -v brew >/dev/null 2>&1; then
  cat >&2 <<'EOF'
Homebrew is not installed.
Install Homebrew using the official Homebrew installer, then rerun this script:

  /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

Do not replace this with an unofficial package source.
EOF
  exit 20
fi

# Lima's foreign-architecture path requires QEMU; the additional guest agents
# are intentionally installed as well so x86_64 guests are supported on ARM
# Macs. Homebrew treats already-installed formulae idempotently.
brew list lima >/dev/null 2>&1 || brew install lima
brew list qemu >/dev/null 2>&1 || brew install qemu
brew list lima-additional-guestagents >/dev/null 2>&1 || brew install lima-additional-guestagents

cd "$PROJECT_ROOT"
[[ "$(git rev-parse --show-toplevel)" == "$PROJECT_ROOT" ]] || {
  echo "Not running from the Greia Git checkout." >&2
  exit 1
}
[[ "$(git branch --show-current)" == "main" ]] || {
  echo "Greia SD builds must come from branch main." >&2
  exit 1
}
git diff --quiet || { echo "Tracked working-tree changes are present; refusing physical-media build." >&2; exit 1; }
git diff --cached --quiet || { echo "Staged changes are present; refusing physical-media build." >&2; exit 1; }
BUILD_SHA="$(git rev-parse HEAD)"

# Create/start a dedicated x86_64 VM. QEMU is explicit because macOS VZ cannot
# run an Intel guest on an ARM host. --plain also avoids exposing the host tree.
if ! limactl shell "$INSTANCE" true >/dev/null 2>&1; then
  limactl start \
    --name="$INSTANCE" \
    --vm-type=qemu \
    --arch=x86_64 \
    --cpus=4 \
    --memory=8 \
    --disk=40 \
    --plain \
    --tty=false \
    template:default
fi

GUEST_ARCH="$(limactl shell "$INSTANCE" uname -m | tr -d '\r\n')"
[[ "$GUEST_ARCH" == "x86_64" ]] || {
  echo "Lima instance $INSTANCE is not x86_64 (reported: $GUEST_ARCH)." >&2
  echo "Do not build Greia from this instance." >&2
  exit 1
}

HOST_TMP="$(mktemp -d -t greia-mac-build.XXXXXX)"
cleanup() {
  rm -rf "$HOST_TMP"
}
trap cleanup EXIT INT TERM

SOURCE_ARCHIVE="$HOST_TMP/greia-source-${BUILD_SHA}.tar.gz"
git archive --format=tar.gz --prefix=Greia/ -o "$SOURCE_ARCHIVE" "$BUILD_SHA"
limactl copy --backend=scp "$SOURCE_ARCHIVE" "$INSTANCE:/tmp/greia-source.tar.gz"

limactl shell "$INSTANCE" bash -lc '
  set -Eeuo pipefail
  sudo apt-get update
  sudo apt-get install -y \
    ca-certificates \
    debootstrap \
    e2fsprogs \
    git \
    grub-common \
    grub-pc-bin \
    make \
    parted \
    python3 \
    python3-dbus \
    python3-pil \
    python3-pygame \
    rsync \
    squashfs-tools \
    udev \
    util-linux
  rm -rf /tmp/Greia
  tar -xzf /tmp/greia-source.tar.gz -C /tmp
  mkdir -p /tmp/Greia/out/local-evidence
'

limactl shell "$INSTANCE" bash -lc "printf '%s\n' '$BUILD_SHA' > /tmp/Greia/out/local-evidence/source-sha.txt"

# Gate before building physical media. Preserve exact output inside out/.
limactl shell "$INSTANCE" bash -lc '
  set -Eeuo pipefail
  cd /tmp/Greia
  bash tools/run_hardware_enablement_source_gate.sh \
    2>&1 | tee out/local-evidence/hardware-enablement-source-gate.log
'

# Build the generic old-PC family image; no target-machine probe occurs here.
limactl shell "$INSTANCE" bash -lc '
  set -Eeuo pipefail
  cd /tmp/Greia
  sudo bash build/build-legacy-x86-sd-installer.sh out \
    2>&1 | tee out/local-evidence/legacy-x86-installer-build.log
  sudo chown -R "$(id -u):$(id -g)" out
  tar -czf /tmp/greia-final-out.tar.gz -C /tmp/Greia out
'

HOST_RESULT_ROOT="$PROJECT_ROOT/out/mac-legacy-x86-${BUILD_SHA}"
rm -rf "$HOST_RESULT_ROOT"
mkdir -p "$HOST_RESULT_ROOT"
limactl copy --backend=scp "$INSTANCE:/tmp/greia-final-out.tar.gz" "$HOST_TMP/greia-final-out.tar.gz"
tar -xzf "$HOST_TMP/greia-final-out.tar.gz" -C "$HOST_RESULT_ROOT" --strip-components=1

ARTIFACT_PROFILE="${PROFILE#acer-aspire-one-}"
[[ -n "$ARTIFACT_PROFILE" ]] || ARTIFACT_PROFILE="installer"
IMAGE="$HOST_RESULT_ROOT/greia-os-installer-${ARTIFACT_PROFILE}.img"
DIGEST_FILE="$HOST_RESULT_ROOT/greia-os-installer-${ARTIFACT_PROFILE}.sha256"
REPORT="$HOST_RESULT_ROOT/greia-os-installer-${ARTIFACT_PROFILE}-report.txt"
[[ -s "$IMAGE" && -s "$DIGEST_FILE" && -s "$REPORT" ]] || {
  echo "Finished build artifacts are incomplete after copying them back to macOS." >&2
  exit 1
}
EXPECTED_SHA="$(awk 'NR==1 {print $1}' "$DIGEST_FILE")"
ACTUAL_SHA="$(shasum -a 256 "$IMAGE" | awk '{print $1}')"
[[ "$EXPECTED_SHA" == "$ACTUAL_SHA" ]] || {
  echo "Final installer SHA-256 changed during VM-to-Mac transfer." >&2
  echo "expected=$EXPECTED_SHA" >&2
  echo "actual=$ACTUAL_SHA" >&2
  exit 1
}

cat <<EOF

GREIA MAC BUILD: PASS

Repository: frozenpepper/Greia
Branch: main
Source SHA: $BUILD_SHA
Target family: generic legacy-x86 / Debian Bookworm i386 / i686 non-PAE
Target-machine probe used for build selection: NO

Finished image:
  $IMAGE

SHA-256:
  $ACTUAL_SHA

Digest file:
  $DIGEST_FILE

Build report:
  $REPORT

All copied build/evidence artifacts:
  $HOST_RESULT_ROOT

The image already contains:
  /greia-tools/prepare-antix-sd-boot.sh
  /greia-tools/collect-linux-hardware-evidence.sh
  /greia-evidence/

Next: write the .img to the whole SD device. Do not copy the .img as a normal
file and do not choose a disk until macOS has positively identified the SD.
EOF
