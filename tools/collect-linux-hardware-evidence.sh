#!/usr/bin/env bash
set -Eeuo pipefail

# Greia one-shot hardware evidence collector.
#
# This is engineering evidence only. It is NOT used to choose an installer
# image, driver, firmware package, or hardware profile. Greia's runtime hardware
# discovery remains automatic and vendor-neutral.
#
# Usage:
#   ./collect-linux-hardware-evidence.sh OUTPUT_DIRECTORY
#
# The script writes exactly one ordinary text report and prints its path.
# It intentionally avoids DMI/storage/network serial-number collection.

usage() {
  echo "Usage: $0 OUTPUT_DIRECTORY" >&2
}

[[ $# -eq 1 ]] || { usage; exit 2; }
OUTPUT_DIR="$1"
mkdir -p "$OUTPUT_DIR"
OUTPUT_DIR="$(cd "$OUTPUT_DIR" && pwd -P)"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
HOST_SAFE="$(hostname 2>/dev/null | tr -cd 'A-Za-z0-9._-' | cut -c1-48 || true)"
[[ -n "$HOST_SAFE" ]] || HOST_SAFE="linux-machine"
REPORT="$OUTPUT_DIR/greia-hardware-evidence-${HOST_SAFE}-${STAMP}.txt"
TMP="${REPORT}.tmp.$$"

cleanup() {
  rm -f "$TMP"
}
trap cleanup EXIT INT TERM

section() {
  printf '\n\n===== %s =====\n' "$1"
}

run_if_present() {
  local command_name="$1"
  shift
  if command -v "$command_name" >/dev/null 2>&1; then
    "$command_name" "$@" 2>&1 || true
  else
    printf '[not installed: %s]\n' "$command_name"
  fi
}

{
  echo "GREIA_HARDWARE_EVIDENCE_VERSION=1"
  echo "COLLECTED_UTC=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo "PURPOSE=engineering-evidence-only-not-installer-selection"

  section "KERNEL / ARCHITECTURE"
  run_if_present uname -a
  run_if_present lscpu
  printf '\nCPU capability summary:\n'
  if grep -qw pae /proc/cpuinfo 2>/dev/null; then echo 'PAE=yes'; else echo 'PAE=no'; fi
  if grep -qw lm /proc/cpuinfo 2>/dev/null; then echo 'LONG_MODE_64BIT=yes'; else echo 'LONG_MODE_64BIT=no'; fi
  if grep -qw nop /proc/cpuinfo 2>/dev/null; then :; fi
  printf 'MACHINE_ARCH='; uname -m 2>/dev/null || true

  section "PCI DEVICES AND BOUND DRIVERS"
  run_if_present lspci -nnk

  section "USB DEVICES"
  run_if_present lsusb

  section "LOADED KERNEL MODULES"
  run_if_present lsmod

  section "STORAGE TOPOLOGY (NO SERIAL COLUMN)"
  run_if_present lsblk -o NAME,PATH,SIZE,TYPE,RM,RO,FSTYPE,LABEL,MODEL,TRAN,MOUNTPOINTS

  section "NETWORK INTERFACES"
  if command -v ip >/dev/null 2>&1; then
    ip -brief link 2>&1 || true
  else
    echo '[not installed: ip]'
  fi
  run_if_present rfkill list

  section "AUDIO"
  run_if_present aplay -l
  run_if_present arecord -l
  if [[ -r /proc/asound/cards ]]; then cat /proc/asound/cards; fi

  section "DRM / DISPLAY CONNECTORS"
  shopt -s nullglob
  for connector in /sys/class/drm/card*-*; do
    [[ -d "$connector" ]] || continue
    printf '\n-- %s --\n' "$(basename "$connector")"
    [[ -r "$connector/status" ]] && { printf 'status='; cat "$connector/status"; }
    if [[ -r "$connector/modes" ]]; then
      echo 'modes:'
      cat "$connector/modes"
    fi
  done
  shopt -u nullglob

  section "INPUT DEVICE SUMMARY"
  if [[ -r /proc/bus/input/devices ]]; then
    # /proc/bus/input/devices is useful for driver/capability evidence and does
    # not require us to query arbitrary device serial properties through udev.
    cat /proc/bus/input/devices
  else
    echo '[unavailable: /proc/bus/input/devices]'
  fi

  section "POWER / BATTERY"
  shopt -s nullglob
  for supply in /sys/class/power_supply/*; do
    [[ -d "$supply" ]] || continue
    printf '\n-- %s --\n' "$(basename "$supply")"
    for field in type online status capacity; do
      [[ -r "$supply/$field" ]] && { printf '%s=' "$field"; cat "$supply/$field"; }
    done
  done
  shopt -u nullglob

  section "FIRMWARE / DRIVER WARNINGS"
  if command -v dmesg >/dev/null 2>&1; then
    # Keep this bounded and focused. Do not dump the entire boot log, which can
    # contain unrelated identifiers and is not needed for this evidence pass.
    dmesg 2>/dev/null \
      | grep -Ei 'firmware|failed to load|Direct firmware load|microcode|drm|wifi|wlan|bluetooth' \
      | tail -n 300 \
      || true
  else
    echo '[not installed: dmesg]'
  fi

  section "GREIA FAMILY OBSERVATION"
  echo 'This report does not select a Greia image.'
  echo 'Bookworm i386 requires an i686-class CPU; legacy-x86-i686 intentionally does not require PAE.'
  echo 'Hardware/firmware enablement is resolved automatically by the Greia installer/runtime.'
} > "$TMP"

chmod 0644 "$TMP"
mv -f "$TMP" "$REPORT"
trap - EXIT INT TERM
printf '%s\n' "$REPORT"
