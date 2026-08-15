#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd -- "$SCRIPT_DIR/.." && pwd)"

usage() {
  cat <<'USAGE'
Usage: install-live-hardware-firmware.sh LIVE_ROOT SUITE ARCH

Verify LIVE_ROOT/opt/greia-hardware-support, then install the frozen minimal
broad-firmware cover into the live installer root. Alternative verified
providers remain in the local pool for machine-specific target selection.
Microcode is intentionally excluded from the live installer and is selected for
the installed target instead.
USAGE
}

[[ $# -eq 3 ]] || { usage >&2; exit 2; }
LIVE_ROOT="$(realpath "$1")"
SUITE="$2"
ARCH="$3"
POOL_ROOT="$LIVE_ROOT/opt/greia-hardware-support"
[[ -d "$LIVE_ROOT" ]] || { echo "Live root not found: $LIVE_ROOT" >&2; exit 1; }

mapfile -t firmware_packages < <(
  PYTHONPATH="$PROJECT_ROOT/src" python3 "$PROJECT_ROOT/tools/verify_hardware_support_pool.py" \
    --root "$POOL_ROOT" \
    --suite "$SUITE" \
    --architecture "$ARCH" \
    --list broad-firmware
)

if (( ${#firmware_packages[@]} == 0 )); then
  echo "Hardware support pool contains no broad firmware packages for $SUITE/$ARCH."
  exit 0
fi

source_path="$LIVE_ROOT/run/greia-hardware-support.list"
printf '%s\n' 'deb [trusted=yes] file:/opt/greia-hardware-support ./' > "$source_path"
chmod 0644 "$source_path"
cleanup() {
  rm -f "$source_path"
}
trap cleanup EXIT

APT_LOCAL_OPTIONS=(
  -o Dir::Etc::sourcelist=/run/greia-hardware-support.list
  -o Dir::Etc::sourceparts=-
  -o APT::Get::List-Cleanup=0
  -o Acquire::Languages=none
)

# No network repository is configured for these commands. trusted=yes is
# acceptable only because verify_hardware_support_pool.py has already checked
# every .deb and both repository indexes against the frozen build manifest.
chroot "$LIVE_ROOT" apt-get "${APT_LOCAL_OPTIONS[@]}" update
chroot "$LIVE_ROOT" /usr/bin/env DEBIAN_FRONTEND=noninteractive \
  apt-get "${APT_LOCAL_OPTIONS[@]}" install -y --no-install-recommends \
  "${firmware_packages[@]}"

# The live installer intentionally carries broad firmware for coldplug support;
# package archives remain in /opt/greia-hardware-support for selective target
# installation. Only APT's ordinary cache is cleaned here.
chroot "$LIVE_ROOT" apt-get clean

echo "Installed ${#firmware_packages[@]} broad firmware packages into the live installer."
