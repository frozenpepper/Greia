#!/usr/bin/env bash
set -euo pipefail
output_parent="${1:-$PWD}"
mkdir -p "$output_parent"
timestamp="$(date -u +%Y%m%dT%H%M%SZ)"
work="$(mktemp -d)"
trap 'rm -rf "$work"' EXIT
report="$work/acer-aspire-one-inventory-$timestamp"
mkdir -p "$report"

capture() {
  local name="$1"; shift
  {
    echo "command: $*"
    echo "date_utc: $(date -u +%FT%TZ)"
    echo
    "$@"
  } > "$report/$name.txt" 2>&1 || true
}

capture uname uname -a
capture cpu sh -c 'cat /proc/cpuinfo'
capture memory sh -c 'cat /proc/meminfo'
capture block_devices lsblk -b -o NAME,TYPE,SIZE,MODEL,ROTA,TRAN,FSTYPE,MOUNTPOINTS
capture pci lspci -nnk
capture usb lsusb
capture network ip -details link show
capture routes ip route show table all
capture kernel_modules sh -c 'lsmod | sort'
capture filesystems sh -c 'cat /proc/filesystems'
capture cmdline sh -c 'cat /proc/cmdline'
capture dmesg dmesg --level=emerg,alert,crit,err,warn

{
  for file in /sys/class/drm/*/modes; do
    [[ -r "$file" ]] || continue
    echo "[$file]"
    cat "$file"
  done
} > "$report/display_modes.txt" 2>&1 || true

{
  for key in product_name product_version board_name board_vendor bios_vendor bios_version; do
    file="/sys/class/dmi/id/$key"
    [[ -r "$file" ]] && printf '%s=%s\n' "$key" "$(cat "$file")"
  done
} > "$report/device_identity_without_serials.txt" 2>&1 || true

cat > "$report/README.txt" <<'NOTE'
This bundle intentionally excludes DMI serial numbers and storage serials.
Return the complete archive without editing individual evidence files.
The project must use this evidence to choose i386 versus amd64 and Acer-specific
video, Wi-Fi, storage, and firmware packages before building the reference image.
NOTE

archive="$output_parent/acer-aspire-one-inventory-$timestamp.tar.gz"
tar -C "$work" -czf "$archive" "$(basename "$report")"
echo "$archive"
