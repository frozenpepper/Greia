#!/usr/bin/env bash
set -Eeuo pipefail

usage() {
  echo "Usage: sudo build/write-image.sh IMAGE /dev/DEVICE --erase-device [--expand-root]" >&2
  echo "Only removable/hot-plug USB or MMC media are accepted." >&2
}
[[ $# -ge 3 && $# -le 4 && "$3" == "--erase-device" ]] || { usage; exit 2; }
[[ ${4:-} == "" || ${4:-} == "--expand-root" ]] || { usage; exit 2; }
[[ ${EUID:-$(id -u)} -eq 0 ]] || { echo "Run as root." >&2; exit 1; }
for command_name in python3 lsblk findmnt umount dd sync realpath stat; do
  command -v "$command_name" >/dev/null || { echo "Missing required command: $command_name" >&2; exit 1; }
done

image="$(realpath "$1")"
device="$(realpath "$2")"
expand_root=false
[[ ${4:-} == "--expand-root" ]] && expand_root=true
[[ -f "$image" ]] || { echo "Image not found: $image" >&2; exit 1; }
[[ -b "$device" ]] || { echo "Not a block device: $device" >&2; exit 1; }
[[ "$device" =~ ^/dev/(sd[a-z]+|vd[a-z]+|nvme[0-9]+n[0-9]+|mmcblk[0-9]+)$ ]] || {
  echo "Refusing unexpected whole-device name: $device" >&2
  exit 1
}

probe_device() {
  local require_unmounted="$1"
  python3 - "$device" "$image" "$require_unmounted" <<'PY'
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

device = os.path.realpath(sys.argv[1])
image = Path(sys.argv[2])
require_unmounted = sys.argv[3] == "yes"

def output(*args: str) -> str:
    return subprocess.run(args, check=True, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE).stdout.strip()

try:
    raw = output(
        "lsblk", "--json", "--bytes", "-o",
        "PATH,TYPE,SIZE,RM,HOTPLUG,TRAN,MODEL,SERIAL,WWN,MOUNTPOINTS", device,
    )
    tree = json.loads(raw).get("blockdevices", [])
except (subprocess.CalledProcessError, json.JSONDecodeError) as exc:
    raise SystemExit(f"Cannot inspect target device: {exc}")
if len(tree) != 1:
    raise SystemExit("Target device inspection returned an unexpected device tree")
root = tree[0]
if os.path.realpath(str(root.get("path", ""))) != device or root.get("type") != "disk":
    raise SystemExit("Target must be one whole disk, not a partition or mapper volume")
try:
    device_size = int(root.get("size") or 0)
    image_size = image.stat().st_size
except (OSError, TypeError, ValueError) as exc:
    raise SystemExit(f"Cannot measure image/target: {exc}")
if image_size <= 0 or device_size <= 0 or image_size > device_size:
    raise SystemExit(
        f"Image does not fit target (image={image_size} bytes, target={device_size} bytes)"
    )
transport = str(root.get("tran") or "").lower()
removable = bool(root.get("rm"))
hotplug = bool(root.get("hotplug"))
media_eligible = removable or hotplug or transport in {"usb", "mmc"} or device.startswith("/dev/mmcblk")
if not media_eligible:
    raise SystemExit("Refusing non-removable internal disk; this writer is only for USB/SD media")

# Resolve every block-device ancestor of the running root, including LVM and
# device-mapper stacks. A simple SOURCE string comparison is not sufficient.
try:
    root_source = output("findmnt", "-nro", "SOURCE", "/")
except subprocess.CalledProcessError:
    root_source = ""
if root_source.startswith("/dev/"):
    try:
        ancestors = output("lsblk", "-srno", "PATH", root_source).splitlines()
    except subprocess.CalledProcessError:
        ancestors = [root_source]
    if device in {os.path.realpath(item.strip()) for item in ancestors if item.strip()}:
        raise SystemExit("Refusing the disk that backs the running root filesystem")

mountpoints: list[str] = []
def walk(node: dict) -> None:
    values = node.get("mountpoints") or []
    if isinstance(values, str):
        values = [values]
    for value in values:
        if isinstance(value, str) and value:
            mountpoints.append(value)
    for child in node.get("children") or []:
        if isinstance(child, dict):
            walk(child)
walk(root)
if require_unmounted and mountpoints:
    raise SystemExit("Target still has mounted filesystems: " + ", ".join(mountpoints))
identity = {
    "path": device,
    "size": device_size,
    "model": str(root.get("model") or "").strip(),
    "serial": str(root.get("serial") or "").strip(),
    "wwn": str(root.get("wwn") or "").strip(),
    "transport": transport,
    "removable": removable,
    "hotplug": hotplug,
}
fingerprint = hashlib.sha256(json.dumps(identity, sort_keys=True).encode()).hexdigest()
print("FINGERPRINT=" + fingerprint)
print("SIZE=" + str(device_size))
print("MODEL=" + identity["model"].replace("\n", " "))
print("TRANSPORT=" + transport)
for mountpoint in sorted(set(mountpoints), key=lambda item: (-len(item), item)):
    print("MOUNT=" + mountpoint.replace("\n", " "))
PY
}

mapfile -t initial_probe < <(probe_device no)
fingerprint=""
mountpoints=()
for line in "${initial_probe[@]}"; do
  case "$line" in
    FINGERPRINT=*) fingerprint="${line#FINGERPRINT=}" ;;
    MOUNT=*) mountpoints+=("${line#MOUNT=}") ;;
  esac
done
[[ -n "$fingerprint" ]] || { echo "Target fingerprint was not produced." >&2; exit 1; }

lsblk -o NAME,SIZE,MODEL,TRAN,RM,HOTPLUG,MOUNTPOINTS "$device"
echo
echo "THIS ERASES ALL DATA ON $device."
read -r -p "Type the exact device path to continue: " confirmation
[[ "$confirmation" == "$device" ]] || { echo "Cancelled."; exit 1; }

for mountpoint in "${mountpoints[@]}"; do
  [[ -n "$mountpoint" ]] && umount -- "$mountpoint"
done

mapfile -t final_probe < <(probe_device yes)
final_fingerprint=""
for line in "${final_probe[@]}"; do
  [[ "$line" == FINGERPRINT=* ]] && final_fingerprint="${line#FINGERPRINT=}"
done
[[ "$final_fingerprint" == "$fingerprint" ]] || {
  echo "Target identity changed after confirmation; refusing to write." >&2
  exit 1
}

dd if="$image" of="$device" bs=4M status=progress conv=fsync
sync

if $expand_root; then
  for command_name in parted partprobe e2fsck resize2fs; do
    command -v "$command_name" >/dev/null || {
      echo "Image was written, but cannot expand root: missing $command_name" >&2
      exit 1
    }
  done
  parted -s "$device" resizepart 1 100%
  partprobe "$device" || true
  if [[ "$device" =~ [0-9]$ ]]; then partition="${device}p1"; else partition="${device}1"; fi
  for _ in {1..30}; do [[ -b "$partition" ]] && break; sleep 0.2; done
  [[ -b "$partition" ]] || {
    echo "Image was written, but expanded partition device did not appear: $partition" >&2
    exit 1
  }
  set +e
  e2fsck -f -p "$partition"
  check_status=$?
  set -e
  if (( check_status > 1 )); then
    echo "Image was written and partition expanded, but filesystem check failed with $check_status." >&2
    exit 1
  fi
  resize2fs "$partition"
  sync
  echo "Root partition expanded to use the target device."
fi

echo "Image written to $device"
