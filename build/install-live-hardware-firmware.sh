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

# Some non-free firmware packages (for example firmware-ipw2x00 and
# firmware-ivtv) gate installation behind a debconf license-acceptance
# question. In this noninteractive build the prompt cannot be shown, so
# pre-seed acceptance for every license template shipped in the frozen pool.
# This is the same decision the live media already makes by carrying the
# broad firmware cover at all.
mapfile -t license_acceptances < <(
  python3 - "$POOL_ROOT" "$SUITE" "$ARCH" <<'PY'
import io
import json
import re
import subprocess
import sys
import tarfile
from pathlib import Path

pool_root = Path(sys.argv[1])
manifest = json.loads((pool_root / "manifest.json").read_text(encoding="utf-8"))
templates = []
for package in manifest.get("packages", []):
    deb = pool_root / "pool" / package["filename"].split("/", 1)[1]
    if not deb.exists():
        continue
    control_tar = subprocess.run(
        ["dpkg-deb", "--ctrl-tarfile", str(deb)],
        check=True,
        stdout=subprocess.PIPE,
    ).stdout
    with tarfile.open(fileobj=io.BytesIO(control_tar), mode="r") as handle:
        member = None
        for candidate in ("./templates", "templates"):
            try:
                member = handle.extractfile(candidate)
            except KeyError:
                continue
            break
        if member is None:
            continue
        text = member.read().decode("utf-8", errors="replace")
    owner = package["package"]
    for match in re.finditer(r"^Template:\s*(\S+)/license/accepted\s*$", text, re.M):
        template = match.group(1)
        if template == owner:
            print(f"{owner} {owner}/license/accepted boolean true")
PY
)
if (( ${#license_acceptances[@]} > 0 )); then
  printf '%s\n' "${license_acceptances[@]}" | chroot "$LIVE_ROOT" debconf-set-selections
fi

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

# Restore full APT list state before anything else runs apt: the local-only
# update above leaves the live root seeing just this pool, so a later plain
# install (for example the early-framebuffer klibc toolchain) would fail
# with "no installation candidate", and autoclean would treat every cached
# bookworm .deb as obsolete and wipe the shared persistent host cache.
# Remove the override first, re-update from the configured sources, and only
# then autoclean. The EXIT trap keeps the removal idempotent.
rm -f "$source_path"
chroot "$LIVE_ROOT" apt-get update
trap - EXIT

# The live installer intentionally carries broad firmware for coldplug support;
# package archives remain in /opt/greia-hardware-support for selective target
# installation. Only APT's ordinary cache is cleaned here; autoclean keeps the
# persistent host .deb cache for the next build.
chroot "$LIVE_ROOT" apt-get autoclean

echo "Installed ${#firmware_packages[@]} broad firmware packages into the live installer."
