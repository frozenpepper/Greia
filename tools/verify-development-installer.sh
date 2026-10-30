#!/usr/bin/env bash
set -Eeuo pipefail

PROJECT_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
# shellcheck source=../build/lib/safe-cleanup.sh
source "$PROJECT_ROOT/build/lib/safe-cleanup.sh"
# shellcheck source=../build/lib/verify-composed-root.sh
source "$PROJECT_ROOT/build/lib/verify-composed-root.sh"
# shellcheck source=../build/lib/installer-image-root.sh
source "$PROJECT_ROOT/build/lib/installer-image-root.sh"

usage() {
  echo "Usage: sudo bash tools/verify-development-installer.sh INSTALLER_IMAGE" >&2
}

[[ $# -eq 1 ]] || { usage; exit 2; }
[[ ${EUID:-$(id -u)} -eq 0 ]] || { echo "Run as root." >&2; exit 1; }
IMAGE="$(realpath "$1")"
[[ -f "$IMAGE" ]] || { echo "Installer image not found: $IMAGE" >&2; exit 1; }

for command_name in losetup partx blockdev blkid udevadm findmnt mount umount mountpoint unsquashfs awk grep realpath cmp python3; do
  command -v "$command_name" >/dev/null || {
    echo "Missing verifier dependency: $command_name" >&2
    exit 1
  }
done
python3 - <<'PY'
try:
    from PIL import Image  # noqa: F401
except ImportError as exc:
    raise SystemExit("Installer verification requires python3-pil on the build host") from exc
PY

WORK="$(mktemp -d -p "${TMPDIR:-/tmp}" greia-dev-installer-verify.XXXXXX)"
MOUNT="$WORK/media"
LOOP=""
mkdir -p "$MOUNT"
cleanup() {
  local original_status=$?
  trap - EXIT INT TERM
  set +e
  local cleanup_failed=0
  safe_unmount_paths "$MOUNT" || cleanup_failed=1
  safe_detach_loop "$LOOP" || cleanup_failed=1
  if (( cleanup_failed == 0 )); then
    rm -rf "$WORK"
  fi
  safe_cleanup_exit "$original_status" "$cleanup_failed" "Development-installer verification cleanup was incomplete; preserving work data for inspection."
}
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

LOOP="$(losetup --find --show --partscan --read-only "$IMAGE")"
PART="$(greia_installer_root_partition "$LOOP")" || {
  echo "Installer ext4 root partition did not appear." >&2
  exit 1
}
mount -o ro,noload "$PART" "$MOUNT"

LIVE="$MOUNT/live/filesystem.squashfs"
TARGET="$MOUNT/payload/greia-rootfs.squashfs"
[[ -r "$LIVE" ]] || { echo "Live installer squashfs is missing." >&2; exit 1; }
[[ -r "$TARGET" ]] || { echo "Installed-system payload squashfs is missing." >&2; exit 1; }

sqcat() {
  unsquashfs -cat "$1" "$2" 2>/dev/null
}

sqhas() {
  unsquashfs -ll "$1" "$2" 2>/dev/null | grep -Fq -- "$2"
}

check_account() {
  local squash="$1" label="$2" shadow hash
  shadow="$(sqcat "$squash" etc/shadow)" || {
    echo "$label: cannot read /etc/shadow from artifact." >&2
    exit 1
  }
  hash="$(printf '%s\n' "$shadow" | awk -F: '$1=="greia" {print $2; exit}')"
  [[ -n "$hash" && "$hash" != '!'* && "$hash" != '*'* ]] || {
    echo "$label: greia account is missing, locked, or passwordless." >&2
    exit 1
  }
}

check_ssh_runtime() {
  local squash="$1" label="$2" helper unit
  helper="$(sqcat "$squash" usr/local/lib/greia-os/prepare-developer-ssh)" || {
    echo "$label: developer SSH bootstrap helper is missing." >&2
    exit 1
  }
  unit="$(sqcat "$squash" etc/systemd/system/ssh.service.d/10-greia-developer-bootstrap.conf)" || {
    echo "$label: ssh.service developer bootstrap drop-in is missing." >&2
    exit 1
  }
  for required in \
    'methods=password' \
    'PasswordAuthentication yes' \
    'KbdInteractiveAuthentication no' \
    'PermitRootLogin no' \
    'AllowUsers greia' \
    'ssh_host_ed25519_key' \
    'sshd -T'
  do
    printf '%s\n' "$helper" | grep -Fq "$required" || {
      echo "$label: SSH runtime contract is missing: $required" >&2
      exit 1
    }
  done
  printf '%s\n' "$unit" | grep -Fq 'prepare-developer-ssh' || {
    echo "$label: sshd does not run Greia bootstrap before validation." >&2
    exit 1
  }
  printf '%s\n' "$unit" | grep -Fq 'ExecStartPre=/usr/sbin/sshd -t' || {
    echo "$label: sshd syntax validation is missing." >&2
    exit 1
  }
  sqhas "$squash" etc/systemd/system/multi-user.target.wants/ssh.service || {
    echo "$label: ssh.service is not enabled in the artifact." >&2
    exit 1
  }
}

check_network() {
  local squash="$1" label="$2" expected_l3_owner="$3" path content iwd_conf

  # Wired recovery networking is systemd-networkd's job and must keep DHCP.
  path="etc/systemd/network/20-greia-wired.network"
  content="$(sqcat "$squash" "$path")" || {
    echo "$label: missing recovery network policy $path" >&2
    exit 1
  }
  printf '%s\n' "$content" | grep -Fq 'DHCP=yes' || {
    echo "$label: $path does not enable DHCP." >&2
    exit 1
  }

  path="etc/iwd/main.conf"
  iwd_conf="$(sqcat "$squash" "$path")" || {
    echo "$label: missing iwd role policy $path" >&2
    exit 1
  }
  path="etc/systemd/network/25-greia-wireless.network"
  content="$(sqcat "$squash" "$path")" || {
    echo "$label: missing wireless network policy $path" >&2
    exit 1
  }

  case "$expected_l3_owner" in
    iwd)
      printf '%s\n' "$iwd_conf" | grep -Fq 'EnableNetworkConfiguration=true' || {
        echo "$label: iwd must own live wireless L3 configuration." >&2
        exit 1
      }
      printf '%s\n' "$content" | awk '
        BEGIN { in_link = 0; found = 0 }
        /^[[:space:]]*\[Link\][[:space:]]*$/ { in_link = 1; next }
        /^[[:space:]]*\[/ { in_link = 0 }
        in_link && /^[[:space:]]*Unmanaged=yes[[:space:]]*$/ { found = 1 }
        END { exit(found ? 0 : 1) }
      ' || {
        echo "$label: networkd must leave live Wi-Fi unmanaged while iwd owns L3." >&2
        exit 1
      }
      if printf '%s\n' "$content" | grep -Eq '^[[:space:]]*DHCP(v4|v6)?[[:space:]]*='; then
        echo "$label: wireless networkd policy must not run DHCP while iwd owns L3." >&2
        exit 1
      fi
      ;;
    networkd)
      printf '%s\n' "$iwd_conf" | grep -Fq 'EnableNetworkConfiguration=false' || {
        echo "$label: installed target must leave wireless L3 to networkd." >&2
        exit 1
      }
      printf '%s\n' "$content" | awk '
        BEGIN { in_network = 0; found = 0 }
        /^[[:space:]]*\[Network\][[:space:]]*$/ { in_network = 1; next }
        /^[[:space:]]*\[/ { in_network = 0 }
        in_network && /^[[:space:]]*DHCP=yes[[:space:]]*$/ { found = 1 }
        END { exit(found ? 0 : 1) }
      ' || {
        echo "$label: target Wi-Fi must retain networkd DHCP behind iwd authentication." >&2
        exit 1
      }
      if printf '%s\n' "$content" | awk '
        BEGIN { in_link = 0; bad = 0 }
        /^[[:space:]]*\[Link\][[:space:]]*$/ { in_link = 1; next }
        /^[[:space:]]*\[/ { in_link = 0 }
        in_link && /^[[:space:]]*Unmanaged=yes[[:space:]]*$/ { bad = 1 }
        END { exit(bad ? 0 : 1) }
      '; then
        echo "$label: target Wi-Fi cannot be Unmanaged while networkd owns DHCP." >&2
        exit 1
      fi
      ;;
    *)
      echo "Internal verifier error: unknown wireless L3 owner $expected_l3_owner" >&2
      exit 2
      ;;
  esac
}

check_installed_dev_boot_diagnostics() {
  local squash="$1" grub
  grub="$(sqcat "$squash" etc/grub.d/10_greia_appliance)" || {
    echo "installed-system payload: Greia GRUB policy is missing." >&2
    exit 1
  }
  # The generator must keep the diagnostic branch for -dev profiles (selected
  # by /etc/greia-os/boot-console-policy, checked in check_composed_roots).
  for required in \
    'developer-remote' \
    'console_arg="console=tty1"' \
    'panic_arg="panic=0"' \
    'loglevel=4' \
    'systemd.show_status=true' \
    'rd.systemd.show_status=true'
  do
    printf '%s\n' "$grub" | grep -Fq "$required" || {
      echo "installed-system payload: developer boot diagnostics are missing: $required" >&2
      exit 1
    }
  done
}

# Extract the small set of paths the shared root contract reads (no code from
# the image runs) and apply it to both artifacts.
extract_for_contract() {
  local squash="$1" dest="$2" role="$3" path
  local paths=(etc boot/grub/grub.cfg var/lib/iwd usr/local/lib/greia-os usr/bin/aplay
    usr/lib/greia/pycache/opt/greia-os/src/greia_platform)
  if [[ "$role" == "target" ]]; then
    # The target's application root and built-in index are symlinks into the
    # one base generation. Extract the links themselves plus the generation
    # index so the installed-generation contract sees the real layout.
    paths+=(opt/greia-os opt/greia-software/generations/base/activity-index-v1.json
      usr/share/greia/activity-index-v1.json)
  else
    paths+=(opt/greia-os/assets)
  fi
  while IFS= read -r path; do
    paths+=("$path")
  done < <(unsquashfs -ll "$squash" 2>/dev/null \
    | awk '{print $NF}' | sed -n 's|^squashfs-root/||p' \
    | grep -E '^usr/lib/[^/]+/alsa-lib/libasound_module_pcm_greia_mic_light\.so$' || true)
  unsquashfs -q -n -d "$dest" "$squash" "${paths[@]}" >/dev/null 2>&1 || true
  [[ -d "$dest/etc" ]] || {
    echo "Cannot extract contract paths from $squash" >&2
    exit 1
  }
}

check_composed_roots() {
  extract_for_contract "$TARGET" "$WORK/target-root" target
  greia_verify_composed_root "$WORK/target-root" target "installed-system payload" "$PROJECT_ROOT"
  TARGET_CONSOLE_POLICY="$BOOT_CONSOLE_POLICY_FOUND"
  extract_for_contract "$LIVE" "$WORK/live-root" live-installer
  greia_verify_composed_root "$WORK/live-root" live-installer "live installer" "$PROJECT_ROOT"
  [[ "$BOOT_CONSOLE_POLICY_FOUND" == "$TARGET_CONSOLE_POLICY" ]] || {
    echo "live installer and installed payload declare different console policies." >&2
    exit 1
  }
}

check_runtime_directory_contract() {
  local tmpfiles launcher parent first_boot prepare
  tmpfiles="$(sqcat "$TARGET" etc/tmpfiles.d/greia-runtime.conf)" || {
    echo "installed-system payload: recurring Greia tmpfiles policy is missing." >&2
    exit 1
  }
  launcher="$(sqcat "$TARGET" etc/systemd/system/greia-launcher.service)" || exit 1
  parent="$(sqcat "$TARGET" etc/systemd/system/greia-parent.service)" || exit 1
  first_boot="$(sqcat "$TARGET" usr/local/lib/greia-os/first-boot)" || exit 1
  prepare="$(sqcat "$TARGET" usr/local/lib/greia-os/prepare-launcher-vt)" || exit 1

  for required in \
    'd /run/greia-os       0770 greiakid greiaprofiles' \
    'd /run/greia-hardware 2750 greiakid greiapanel'
  do
    printf '%s\n' "$tmpfiles" | grep -Fq "$required" || {
      echo "installed-system payload: tmpfiles runtime contract missing: $required" >&2
      exit 1
    }
  done
  for unit_text in "$launcher" "$parent"; do
    printf '%s\n' "$unit_text" | grep -Fq 'systemd-tmpfiles-setup.service' || {
      echo "installed-system payload: Greia service is not ordered after recurring tmpfiles setup." >&2
      exit 1
    }
  done
  if printf '%s\n' "$launcher" | grep -Fq 'RuntimeDirectory=greia-os'; then
    echo "installed-system payload: launcher still races shared /run ownership via RuntimeDirectory." >&2
    exit 1
  fi
  if printf '%s\n' "$first_boot" | grep -Fq '/run/greia-hardware'; then
    echo "installed-system payload: one-time first boot still owns volatile /run/greia-hardware." >&2
    exit 1
  fi
  for required in \
    'profile_data_root=/var/lib/greia-profiles/data' \
    'if [ -L "$profile_data_root" ]' \
    'install -d -m 2770 -o greiakid -g greiaprofiles "$profile_data_root"' \
    'b4-profile-child-roots-v1.done' \
    'chown -h -- greiakid:greiaprofiles'
  do
    printf '%s\n' "$first_boot" | grep -Fq -- "$required" || {
      echo "installed-system payload: bounded profile ownership contract missing: $required" >&2
      exit 1
    }
  done
  if printf '%s\n' "$first_boot" | grep -Fq 'find /var/lib/greia-profiles/data -depth -print0'; then
    echo "installed-system payload: unsafe whole-profile recursive ownership sweep returned." >&2
    exit 1
  fi
  for required in \
    'AssertPathIsDirectory=/run/greia-os' \
    'AssertPathIsDirectory=/run/greia-hardware'
  do
    printf '%s\n' "$launcher" | grep -Fq "$required" || {
      echo "installed-system payload: launcher runtime-root assertion missing: $required" >&2
      exit 1
    }
  done
  if printf '%s\n' "$prepare" | grep -Fq 'chown greiakid:greiaprofiles /run/greia-os'; then
    echo "installed-system payload: launcher preflight regained shared /run ownership." >&2
    exit 1
  fi
}

check_installed_first_boot_contract() {
  local launcher xsession xwrapper input supervisor
  launcher="$(sqcat "$TARGET" etc/systemd/system/greia-launcher.service)" || {
    echo "installed-system payload: launcher service is missing." >&2
    exit 1
  }
  xsession="$(sqcat "$TARGET" usr/local/lib/greia-os/greia-x-session)" || {
    echo "installed-system payload: X client session is missing." >&2
    exit 1
  }
  xwrapper="$(sqcat "$TARGET" etc/X11/Xwrapper.config)" || {
    echo "installed-system payload: Xwrapper policy is missing." >&2
    exit 1
  }
  input="$(sqcat "$TARGET" etc/X11/xorg.conf.d/90-greia-input-defaults.conf)" || {
    echo "installed-system payload: X input defaults are missing." >&2
    exit 1
  }
  supervisor="$(sqcat "$TARGET" opt/greia-os/src/greia_launcher/supervisor.py)" || {
    echo "installed-system payload: Activity supervisor is missing." >&2
    exit 1
  }

  for required in \
    "User=greiakid" \
    "TTYPath=/dev/tty1" \
    "StandardInput=tty-fail" \
    "-logfile /run/greia-os/Xorg.0.log"
  do
    printf '%s\n' "$launcher" | grep -Fq -- "$required" || {
      echo "installed-system payload: launcher first-boot contract missing: $required" >&2
      exit 1
    }
  done
  printf '%s\n' "$launcher" | grep -Eq '^SupplementaryGroups=.*(^|[[:space:]])tty([[:space:]]|$)' || {
    echo "installed-system payload: launcher does not receive tty group." >&2
    exit 1
  }
  printf '%s\n' "$xsession" | grep -Fq 'exec </dev/null' || {
    echo "installed-system payload: launcher client does not detach VT stdin." >&2
    exit 1
  }
  printf '%s\n' "$xsession" | grep -Fq -- '-m greia_launcher.child_shell' || {
    echo "installed-system payload: launcher child-shell entrypoint is missing." >&2
    exit 1
  }
  printf '%s\n' "$xwrapper" | grep -Fq 'allowed_users=anybody' || {
    echo "installed-system payload: accepted Xwrapper user policy is missing." >&2
    exit 1
  }
  printf '%s\n' "$xwrapper" | grep -Fq 'needs_root_rights=yes' || {
    echo "installed-system payload: accepted Xwrapper rights policy is missing." >&2
    exit 1
  }
  printf '%s\n' "$input" | grep -Fq 'MatchDevicePath "/dev/input/mouse*"' || {
    echo "installed-system payload: legacy mouse compatibility nodes are not ignored." >&2
    exit 1
  }
  printf '%s\n' "$input" | grep -Fq 'Option "Ignore" "true"' || {
    echo "installed-system payload: legacy mouse ignore policy is incomplete." >&2
    exit 1
  }
  printf '%s\n' "$supervisor" | grep -Fq '"--tmpfs",' || {
    echo "installed-system payload: Activity sandbox private /run setup is missing." >&2
    exit 1
  }
  printf '%s\n' "$supervisor" | grep -Fq '"/run"' || {
    echo "installed-system payload: Activity sandbox /run target is missing." >&2
    exit 1
  }
  if printf '%s\n' "$supervisor" | grep -Fq '"--unshare-user"'; then
    echo "installed-system payload: broken Activity user-namespace mode returned." >&2
    exit 1
  fi
}

check_boot_progress_contract() {
  local stage path text first_boot prepare intro
  for stage in 'init-top:15' 'local-premount:30' 'init-bottom:45'; do
    path="${stage%%:*}"
    value="${stage##*:}"
    text="$(sqcat "$TARGET" "etc/initramfs-tools/scripts/$path/greia-early-framebuffer")" || {
      echo "installed-system payload: boot progress script missing at $path." >&2
      exit 1
    }
    printf '%s\n' "$text" | grep -Fq -- "--progress $value" || {
      echo "installed-system payload: boot progress milestone $path=$value is missing." >&2
      exit 1
    }
  done
  first_boot="$(sqcat "$TARGET" usr/local/lib/greia-os/first-boot)" || exit 1
  for value in 55 65; do
    printf '%s\n' "$first_boot" | grep -Fq "boot_progress $value" || {
      echo "installed-system payload: first-boot progress milestone $value is missing." >&2
      exit 1
    }
  done
  prepare="$(sqcat "$TARGET" usr/local/lib/greia-os/prepare-launcher-vt)" || exit 1
  printf '%s\n' "$prepare" | grep -Fq -- '--progress 78' || {
    echo "installed-system payload: final pre-X 78% progress milestone is missing." >&2
    exit 1
  }
  intro="$(sqcat "$TARGET" opt/greia-os/src/greia_launcher/boot_intro.py)" || exit 1
  printf '%s\n' "$intro" | grep -Fq 'draw_boot_handoff_frame(screen, pygame, progress=92)' || {
    echo "installed-system payload: launcher 92% X-handoff frame is missing." >&2
    exit 1
  }
}

check_boot_artwork() {
  local live_ppm="$WORK/live-boot.ppm"
  local target_ppm="$WORK/target-boot.ppm"
  local grub_png="$WORK/target-grub-boot.png"
  local launcher_png="$WORK/target-launcher-boot.png"
  local theme grub

  sqcat "$LIVE" etc/greia-boot/boot-logo.ppm > "$live_ppm" || {
    echo "live installer: embedded early-boot PPM is missing." >&2
    exit 1
  }
  sqcat "$TARGET" etc/greia-boot/boot-logo.ppm > "$target_ppm" || {
    echo "installed-system payload: embedded early-boot PPM is missing." >&2
    exit 1
  }
  cmp -s "$live_ppm" "$target_ppm" || {
    echo "boot artwork mismatch: live and installed PPM canvases differ." >&2
    exit 1
  }

  sqcat "$TARGET" boot/grub/greia-boot-logo.png > "$grub_png" || {
    echo "installed-system payload: GRUB splash PNG is missing." >&2
    exit 1
  }
  sqcat "$TARGET" opt/greia-os/assets/boot/static/greia-boot-logo.png > "$launcher_png" || {
    echo "installed-system payload: launcher boot PNG is missing." >&2
    exit 1
  }

  python3 - "$target_ppm" "$grub_png" "$launcher_png" <<'PY'
from pathlib import Path
import sys
from PIL import Image

ppm_path, grub_path, launcher_path = map(Path, sys.argv[1:])
data = ppm_path.read_bytes()
header = b"P6\n1024 600\n255\n"
if not data.startswith(header):
    raise SystemExit("embedded boot PPM is not the required 1024x600 P6 canvas")
pixels = data[len(header):]
if len(pixels) != 1024 * 600 * 3:
    raise SystemExit("embedded boot PPM raster length is invalid")

sampled = {
    tuple(pixels[index:index + 3])
    for index in range(0, len(pixels) - 2, 3 * 97)
}
if len(sampled) < 64:
    raise SystemExit(f"embedded boot artwork lacks full-colour detail ({len(sampled)} sampled colours)")
old_duotone = {(255, 255, 255), (62, 70, 130)}
if sampled.issubset(old_duotone):
    raise SystemExit("embedded boot artwork is still the rejected white/indigo derivative")

for label, path in (("GRUB", grub_path), ("launcher", launcher_path)):
    image = Image.open(path).convert("RGB")
    if image.size != (1024, 600):
        raise SystemExit(f"{label} splash PNG has wrong geometry: {image.size}")
    if image.tobytes() != pixels:
        raise SystemExit(f"{label} splash PNG does not match the embedded PPM canvas")
PY

  theme="$(sqcat "$TARGET" boot/grub/greia-theme.txt)" || {
    echo "installed-system payload: proportional GRUB theme is missing." >&2
    exit 1
  }
  for required in \
    'desktop-image: "greia-boot-logo.png"' \
    'desktop-image-scale-method: "padding"' \
    'desktop-image-h-align: "center"' \
    'desktop-image-v-align: "center"'
  do
    printf '%s\n' "$theme" | grep -Fq "$required" || {
      echo "installed-system payload: GRUB theme missing splash contract: $required" >&2
      exit 1
    }
  done

  grub="$(sqcat "$TARGET" etc/grub.d/10_greia_appliance)" || exit 1
  printf '%s\n' "$grub" | grep -Fq 'set theme=$theme' || {
    echo "installed-system payload: GRUB script does not activate the proportional theme." >&2
    exit 1
  }
  if printf '%s\n' "$grub" | grep -Eq '^[[:space:]]*background_image[[:space:]]'; then
    echo "installed-system payload: raw GRUB background_image stretch path is still active." >&2
    exit 1
  fi
}

check_account "$LIVE" "live installer"
check_ssh_runtime "$LIVE" "live installer"
check_network "$LIVE" "live installer" "iwd"

check_account "$TARGET" "installed-system payload"
check_ssh_runtime "$TARGET" "installed-system payload"
check_network "$TARGET" "installed-system payload" "networkd"
check_installed_dev_boot_diagnostics "$TARGET"
check_composed_roots
check_runtime_directory_contract
check_installed_first_boot_contract
check_boot_progress_contract
check_boot_artwork

TARGET_MARKER="$(sqcat "$TARGET" etc/greia-os/developer-remote)" || {
  echo "installed-system payload: developer marker is missing." >&2
  exit 1
}
[[ -n "$TARGET_MARKER" ]] || {
  echo "installed-system payload: developer marker is empty." >&2
  exit 1
}

LIVE_BUILD_INFO="$(sqcat "$LIVE" etc/greia-os/build-info)"
TARGET_BUILD_INFO="$(sqcat "$TARGET" etc/greia-os/build-info)"
printf '%s\n' "$LIVE_BUILD_INFO" | grep -Fq 'PIP_BUILD_PROFILE=' || exit 1
printf '%s\n' "$TARGET_BUILD_INFO" | grep -Fq 'PIP_BUILD_PROFILE=' || exit 1

printf '%s\n' "Developer installer artifact verification: PASS"
printf '%s\n' "- live installer: password-enabled greia account, sshd bootstrap, DHCP policy"
printf '%s\n' "- installed payload: password-enabled greia account, sshd bootstrap, DHCP policy"
if [[ "$TARGET_CONSOLE_POLICY" == quiet ]]; then
  printf '%s\n' "- boot console: quiet (installer + installed), panic=0; hidden Syslinux 'verbose' + owner-only GRUB diagnostics"
else
  printf '%s\n' "- installed dev boot: tty1 diagnostics, panic=0 (no timed reboot)"
fi
printf '%s\n' "- both roots: mic ALSA module, HDA power_save=0, bytecode prefix; target: netdev, /var/lib/iwd, persistent journal"
printf '%s\n' "- runtime roots: recurring tmpfiles ownership verified; one-time/launcher ownership race rejected"
printf '%s\n' "- first boot: launcher VT/client split, Xwrapper/input and Activity sandbox contracts verified"
printf '%s\n' "- boot progress: truthful milestones 15/30/45/55/65/78 + launcher 92 handoff verified"
printf '%s\n' "- splash: full-colour 1024x600 canvas verified in live PPM, target PPM, GRUB PNG and launcher PNG"
printf '%s\n' "- GRUB splash: proportional padding + centred; raw stretch path rejected"
printf '%s\n' "- root SSH remains denied; password login always; operator key login when built with --operator-key"
