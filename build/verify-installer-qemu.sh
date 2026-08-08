#!/usr/bin/env bash
set -euo pipefail

usage() {
  echo "Usage: build/verify-installer-qemu.sh INSTALLER_IMAGE [WORK_DIR] [i386|amd64]" >&2
}
[[ $# -ge 1 && $# -le 3 ]] || { usage; exit 2; }
installer_image="$(realpath "$1")"
[[ -f "$installer_image" ]] || { echo "Installer image not found: $installer_image" >&2; exit 1; }
work_dir="${2:-$(dirname "$installer_image")/qemu-installer-test}"
mkdir -p "$work_dir"
work_dir="$(realpath "$work_dir")"

arch="${3:-}"
report="${installer_image%.img}-report.txt"
if [[ -z "$arch" && -r "$report" ]]; then
  arch="$(sed -n 's/^architecture=//p' "$report" | head -n1)"
fi
case "$arch" in
  i386)
    qemu_binary=qemu-system-i386
    fallback_cpu=qemu32
    ;;
  amd64)
    qemu_binary=qemu-system-x86_64
    fallback_cpu=qemu64
    ;;
  *)
    echo "Cannot determine installer architecture. Keep the builder report beside the image or pass i386/amd64 explicitly." >&2
    exit 1
    ;;
esac
command -v "$qemu_binary" >/dev/null || {
  echo "Install qemu-system-x86 for $qemu_binary." >&2
  exit 1
}

target_image="$work_dir/blank-acer-target.img"
[[ -e "$target_image" ]] || truncate -s 7G "$target_image"
cpu_help="$($qemu_binary -cpu help 2>/dev/null || true)"
if [[ -n "${PIP_QEMU_CPU_MODEL:-}" ]]; then
  cpu_model="$PIP_QEMU_CPU_MODEL"
elif [[ "$arch" == i386 ]] && grep -Eq '(^|[[:space:]])n270([[:space:]]|$)' <<<"$cpu_help"; then
  cpu_model=n270
elif [[ "$arch" == i386 ]] && grep -Eq '(^|[[:space:]])pentium3([[:space:]]|$)' <<<"$cpu_help"; then
  cpu_model=pentium3
else
  cpu_model="$fallback_cpu"
fi

cat <<INFO
Installer media: $installer_image
Installer architecture: $arch
Disposable target: $target_image
CPU model: $cpu_model
The installer image is presented as a read-only USB mass-storage device, while
only the 7 GiB IDE disk is writable. Device bootindex values select the USB
installer first without mixing firmware -boot order with bootindex.
INFO

exec "$qemu_binary" \
  -machine pc,accel=kvm:tcg \
  -cpu "$cpu_model" \
  -m 768 \
  -smp 1 \
  -usb \
  -drive "if=none,id=installer,file=$installer_image,format=raw,readonly=on" \
  -device "usb-storage,drive=installer,bootindex=1" \
  -drive "if=none,id=target,file=$target_image,format=raw" \
  -device "ide-hd,drive=target,bootindex=2" \
  -device e1000,netdev=net0 \
  -netdev user,id=net0 \
  -display gtk \
  -no-reboot
