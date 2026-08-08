#!/usr/bin/env bash
set -euo pipefail

usage() {
  echo "Usage: build/verify-image-qemu.sh IMAGE [i386|amd64]" >&2
}
[[ $# -ge 1 && $# -le 2 ]] || { usage; exit 2; }
image="$(realpath "$1")"
[[ -f "$image" ]] || { echo "Image not found: $image" >&2; exit 1; }
arch="${2:-}"
report="${image%.img}-footprint.txt"
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
    echo "Cannot determine image architecture. Keep the footprint report beside the image or pass i386/amd64 explicitly." >&2
    exit 1
    ;;
esac
command -v "$qemu_binary" >/dev/null || {
  echo "Install qemu-system-x86 for $qemu_binary." >&2
  exit 1
}

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
Installed image: $image
Image architecture: $arch
CPU model: $cpu_model
The helper keeps 768 MiB RAM and one vCPU, avoids QEMU's highly capable max CPU,
and uses the architecture recorded by the builder rather than silently forcing a
32-bit emulator for amd64 images.
INFO

exec "$qemu_binary" \
  -machine pc,accel=kvm:tcg \
  -cpu "$cpu_model" \
  -m 768 \
  -smp 1 \
  -drive "file=$image,format=raw,if=ide" \
  -device e1000,netdev=net0 \
  -netdev user,id=net0,hostfwd=tcp::18766-:8766 \
  -display gtk \
  -no-reboot
