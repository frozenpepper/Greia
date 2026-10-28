#!/usr/bin/env bash
# Shared artifact checks for a composed Greia root (read-only).
#
# Sourced by tools/verify-development-target-image.sh (mounted target image)
# and tools/verify-development-installer.sh (paths extracted from the target
# payload and live squashfs). Each check reads files below ROOT only; nothing
# is executed from the image.
#
#   greia_verify_composed_root ROOT ROLE LABEL PROJECT_ROOT
#     ROLE: target | live-installer
#
# Covers the release-candidate contracts added on 2026-10-17: boot console
# policy, quiet/diagnostic GRUB rendering, microphone ALSA module, HDA power
# save, bytecode prefix, Wi-Fi netdev grants, iwd state directory, persistent
# developer journal, installer SDL hint, and the optional operator key.

_greia_root_fail() {
  echo "$1: $2" >&2
  exit 1
}

# Expected console policy: the image's own declared manifest; manifests that
# predate the key mean "developer -> diagnostic, else quiet".
_greia_expected_console_policy() {
  local root="$1" developer="$2"
  python3 -I - "$root/etc/greia-os/image-profile.json" "$developer" <<'PY'
import json
import sys

path, developer = sys.argv[1], sys.argv[2] == "1"
try:
    with open(path, encoding="utf-8") as handle:
        manifest = json.load(handle)
except FileNotFoundError:
    manifest = {}
default = "diagnostic" if developer else "quiet"
print((manifest.get("boot") or {}).get("console_policy", default))
PY
}

greia_verify_composed_root() {
  local root="$1" role="$2" label="$3" project_root="$4"
  local developer=0
  [[ -s "$root/etc/greia-os/developer-remote" ]] && developer=1

  # Boot console policy recorded in the root matches the declared profile.
  local policy expected
  [[ -s "$root/etc/greia-os/boot-console-policy" ]] || _greia_root_fail "$label" "boot console policy file is missing"
  policy="$(tr -d ' \t\r\n' < "$root/etc/greia-os/boot-console-policy")"
  expected="$(_greia_expected_console_policy "$root" "$developer")"
  [[ "$policy" == "$expected" ]] || _greia_root_fail "$label" "boot console policy $policy does not match declared $expected"
  case "$policy" in
    quiet|diagnostic) ;;
    *) _greia_root_fail "$label" "unknown boot console policy $policy" ;;
  esac
  BOOT_CONSOLE_POLICY_FOUND="$policy"

  # Microphone noise filter: exactly one module, plus HDA power save off.
  local module_count=0 module="" found
  while IFS= read -r found; do
    module_count=$((module_count + 1))
    module="$found"
  done < <(find "$root/usr/lib" -mindepth 3 -maxdepth 3 -type f \
    -path '*/alsa-lib/libasound_module_pcm_greia_mic_light.so' 2>/dev/null)
  (( module_count == 1 )) && [[ -s "$module" ]] || \
    _greia_root_fail "$label" "greia_mic_light ALSA module missing (found $module_count)"
  grep -Eq '^options snd_hda_intel .*power_save=0' "$root/etc/modprobe.d/greia-audio.conf" 2>/dev/null || \
    _greia_root_fail "$label" "snd_hda_intel power_save=0 is missing"

  # Read-only bytecode prefix built with the image's interpreter.
  compgen -G "$root/usr/lib/greia/pycache/opt/greia-os/src/greia_platform/*.pyc" >/dev/null || \
    _greia_root_fail "$label" "Greia bytecode prefix /usr/lib/greia/pycache is missing"

  # SSH bootstrap: password login always, key login when a key is present.
  if (( developer )); then
    local helper="$root/usr/local/lib/greia-os/prepare-developer-ssh"
    for required in 'methods=password' 'methods="publickey password"' \
      'AuthorizedKeysFile /etc/ssh/greia-operator-keys/%u' 'AuthenticationMethods $methods'; do
      grep -Fq -- "$required" "$helper" || _greia_root_fail "$label" "SSH key/password policy missing: $required"
    done
  fi
  if [[ -n "${GREIA_OPERATOR_AUTHORIZED_KEY_FILE:-}" ]]; then
    local installed="$root/etc/ssh/greia-operator-keys/greia" expected_keys
    [[ -s "$installed" ]] || _greia_root_fail "$label" "operator key was requested but is not installed"
    expected_keys="$(mktemp "${TMPDIR:-/tmp}/greia-operator-key.XXXXXX")"
    python3 -I "$project_root/build/lib/operator_key.py" \
      "$GREIA_OPERATOR_AUTHORIZED_KEY_FILE" "$expected_keys" >/dev/null || {
      rm -f "$expected_keys"; _greia_root_fail "$label" "operator key input no longer validates"; }
    cmp -s "$expected_keys" "$installed" || {
      rm -f "$expected_keys"; _greia_root_fail "$label" "installed operator key differs from the input"; }
    rm -f "$expected_keys"
  fi

  if [[ "$role" == "live-installer" ]]; then
    local unit="$root/etc/systemd/system/greia-installer.service"
    # systemd resolves User/Group/SupplementaryGroups before ExecStartPre.
    # A missing netdev (or any other requested group) prevents the *entire*
    # graphical installer from starting: status=216/GROUP and endless cover.
    # Verify the real composed image database, not just the service text.
    grep -q '^nobody:' "$root/etc/passwd" || \
      _greia_root_fail "$label" "installer service user nobody is missing"
    local installer_group
    for installer_group in $(sed -n -e 's/^Group=//p' -e 's/^SupplementaryGroups=//p' "$unit"); do
      [[ "$installer_group" =~ ^[a-z_][a-z0-9_-]*$ ]] || \
        _greia_root_fail "$label" "invalid installer group declaration: $installer_group"
      grep -q "^$installer_group:" "$root/etc/group" || \
        _greia_root_fail "$label" "installer group $installer_group missing from live /etc/group (216/GROUP)"
    done
    grep -Fqx 'Environment=SDL_FRAMEBUFFER_ACCELERATION=0' "$unit" || \
      _greia_root_fail "$label" "installer unit lacks SDL_FRAMEBUFFER_ACCELERATION=0"
    grep -Fqx 'Environment=PYTHONPYCACHEPREFIX=/usr/lib/greia/pycache' "$unit" || \
      _greia_root_fail "$label" "installer unit does not use the bytecode prefix"
    grep -Eq '^SupplementaryGroups=(.*[[:space:]])?audio([[:space:]]|$)' "$unit" || \
      _greia_root_fail "$label" "installer UI cannot open ALSA for the boot chime (no audio group)"
    # xinit exits 0 even when the installer Python crashes, so only
    # Restart=always restarts it; ExecStopPost keeps VT1 on the Greia cover.
    grep -Fqx 'Restart=always' "$unit" || \
      _greia_root_fail "$label" "installer unit does not restart after a crash (xinit exits 0)"
    grep -Fqx 'ExecStopPost=+/usr/local/lib/greia-os/installer-exit-cover' "$unit" && \
      [[ -x "$root/usr/local/lib/greia-os/installer-exit-cover" ]] || \
      _greia_root_fail "$label" "installer unit does not repaint the cover after it stops"
    # Completion power-off: the unprivileged UI writes the marker it owns and
    # the root path unit performs the single systemctl poweroff (2026-10-18;
    # the UI's own unprivileged poweroff call is denied by logind/polkit).
    grep -Fqx 'PathExists=/run/greia-installer/finish-request' \
      "$root/etc/systemd/system/greia-installer-finish.path" || \
      _greia_root_fail "$label" "installer finish path unit is missing or wrong"
    grep -Fqx 'ExecStart=/usr/local/lib/greia-os/greia-installer-finish' \
      "$root/etc/systemd/system/greia-installer-finish.service" || \
      _greia_root_fail "$label" "installer finish service is missing or wrong"
    [[ -x "$root/usr/local/lib/greia-os/greia-installer-finish" ]] || \
      _greia_root_fail "$label" "installer finish helper is missing"
    grep -Fq '/usr/bin/systemctl poweroff' "$root/usr/local/lib/greia-os/greia-installer-finish" || \
      _greia_root_fail "$label" "installer finish helper does not power off"
    # Shutdown stays silent: raising show-status/kernel loglevel here printed
    # terminal text over the Greia cover. Instead the helper lowers PID1's log
    # level to emergency for the final power-off (2026-10-18).
    grep -Fq 'LogLevel s emerg' "$root/usr/local/lib/greia-os/greia-installer-finish" || \
      _greia_root_fail "$label" "installer finish helper does not silence the shutdown phase"
    if grep -Eq 'SetShowStatus|/proc/sys/kernel/printk' \
      "$root/usr/local/lib/greia-os/greia-installer-finish"; then
      _greia_root_fail "$label" "installer finish helper reintroduces shutdown console text"
    fi
    [[ -L "$root/etc/systemd/system/multi-user.target.wants/greia-installer-finish.path" ]] || \
      _greia_root_fail "$label" "installer finish path unit is not enabled"
    # Installer look + boot intro assets (src/greia_installer/presentation.py,
    # boot_intro.py). The catalogue must load strictly or the UI silently
    # falls back to procedural art.
    local assets="$root/opt/greia-os/assets"
    [[ -s "$assets/boot/frames/frame_0000.png" && -s "$assets/boot/frames/frame_0051.png" ]] || \
      _greia_root_fail "$label" "boot animation frames are missing from the live root"
    [[ -s "$assets/audio/system/greia-boot-chime.wav" ]] || \
      _greia_root_fail "$label" "boot chime is missing from the live root"
    [[ -x "$root/usr/bin/aplay" ]] || _greia_root_fail "$label" "aplay (alsa-utils) is missing for the boot chime"
    PYTHONPATH="$project_root/src" PYTHONDONTWRITEBYTECODE=1 python3 -I -c '
import sys
sys.path.insert(0, sys.argv[2])
from pathlib import Path
from greia_platform.assets import AssetCatalogue
catalogue = AssetCatalogue.load(Path(sys.argv[1]) / "catalog/shared_visuals_v1.toml")
for asset_id in ("bg.meadow_day.home", "character.leo"):
    for _name, path in catalogue.get_visual(asset_id).variants:
        if not path.is_file() or path.stat().st_size == 0:
            raise SystemExit(f"missing {asset_id} rendition {path}")
' "$assets" "$project_root/src" || _greia_root_fail "$label" "shared visual catalogue/renditions for the installer do not load"
    return 0
  fi

  # The installed application is one atomically switched generation. The
  # index alias follows that same pointer, and the stable recovery driver
  # remains outside the replaceable application tree.
  [[ -L "$root/opt/greia-os" ]] || \
    _greia_root_fail "$label" "installed /opt/greia-os is not the application-generation symlink"
  [[ "$(readlink "$root/opt/greia-os")" == "greia-software/generations/base" ]] || \
    _greia_root_fail "$label" "base application-generation pointer has the wrong target"
  [[ -s "$root/opt/greia-software/generations/base/activity-index-v1.json" ]] || \
    _greia_root_fail "$label" "base application generation has no built-in Activity index"
  [[ -L "$root/usr/share/greia/activity-index-v1.json" ]] && \
    [[ "$(readlink "$root/usr/share/greia/activity-index-v1.json")" == "../../../opt/greia-os/activity-index-v1.json" ]] || \
    _greia_root_fail "$label" "built-in Activity index alias does not follow the app generation"
  [[ -x "$root/usr/local/lib/greia-os/software-update-bootstrap.py" ]] || \
    _greia_root_fail "$label" "stable software-update bootstrap helper is missing"
  python3 -I - "$root/etc/greia-os/software-update-bootstrap.json" <<'PY' || \
    _greia_root_fail "$label" "software-update bootstrap marker is invalid"
import json, sys
with open(sys.argv[1], encoding="utf-8") as handle:
    if json.load(handle) != {"schema_version": 1}:
        raise SystemExit(1)
PY
  local recover_unit="$root/etc/systemd/system/greia-software-update-recover.service"
  local apply_unit="$root/etc/systemd/system/greia-software-update-apply.service"
  local timer_unit="$root/etc/systemd/system/greia-software-update-apply.timer"
  grep -Fq 'ConditionPathExists=/etc/greia-os/software-update-bootstrap.json' "$recover_unit" || \
    _greia_root_fail "$label" "software-update recovery service lacks its bootstrap condition"
  grep -Fq -- '--recover' "$recover_unit" || \
    _greia_root_fail "$label" "software-update recovery service does not run the stable recovery path"
  grep -Fq 'ConditionPathExists=/var/lib/greia-os/software-updates/pending' "$apply_unit" || \
    _greia_root_fail "$label" "software-update service is not conditional on the durable pending marker"
  grep -Fq -- '--apply' "$apply_unit" || \
    _greia_root_fail "$label" "software-update service does not run the stable apply path"
  grep -Fq 'OnUnitActiveSec=15s' "$timer_unit" || \
    _greia_root_fail "$label" "software-update retry timer is not bounded to 15-second intervals"
  [[ -L "$root/etc/systemd/system/timers.target.wants/greia-software-update-apply.timer" ]] || \
    _greia_root_fail "$label" "software-update retry timer is not enabled"
  if [[ -L "$root/etc/systemd/system/multi-user.target.wants/greia-boot-observer.service" ]]; then
    [[ -L "$root/etc/systemd/system/timers.target.wants/greia-candidate-recovery.timer" ]] || \
      _greia_root_fail "$label" "A/B candidate health-deadline timer is not enabled"
  fi

  # Wi-Fi: iwd's bus policy admits root and netdev only.
  grep -Eq '^SupplementaryGroups=(.*[[:space:]])?netdev([[:space:]]|$)' \
    "$root/etc/systemd/system/greia-launcher.service" || \
    _greia_root_fail "$label" "launcher lacks the netdev group"
  grep -Eq '^SupplementaryGroups=(.*[[:space:]])?tty([[:space:]]|$)' \
    "$root/etc/systemd/system/greia-launcher.service" || \
    _greia_root_fail "$label" "launcher lost the tty group"
  grep -Eq '^SupplementaryGroups=(.*[[:space:]])?netdev([[:space:]]|$)' \
    "$root/etc/systemd/system/greia-parent.service" || \
    _greia_root_fail "$label" "Parent service lacks the netdev group"
  local members
  members="$(awk -F: '$1 == "netdev" {print $4}' "$root/etc/group")"
  for account in greiakid greiapanel; do
    [[ ",$members," == *",$account,"* ]] || _greia_root_fail "$label" "$account is not in group netdev"
  done
  # GREIA_VERIFY_ROOT_UID exists only so the source tests can run this on an
  # unprivileged fixture; real verification always expects uid 0.
  [[ -d "$root/var/lib/iwd" && "$(python3 -I -c 'import os, sys; s = os.stat(sys.argv[1]); print("%o %d" % (s.st_mode & 0o7777, s.st_uid))' "$root/var/lib/iwd")" == "700 ${GREIA_VERIFY_ROOT_UID:-0}" ]] || \
    _greia_root_fail "$label" "/var/lib/iwd must exist root-owned 0700 for Wi-Fi credentials"

  if (( developer )); then
    grep -Fqx 'Storage=persistent' "$root/etc/systemd/journald.conf.d/20-greia-developer-persistent.conf" 2>/dev/null || \
      _greia_root_fail "$label" "developer image lacks the bounded persistent journal"
    grep -Eq '^SystemMaxUse=[0-9]+M$' "$root/etc/systemd/journald.conf.d/20-greia-developer-persistent.conf" || \
      _greia_root_fail "$label" "persistent journal is not bounded"
  fi

  # Installed GRUB generator carries both policies; the rendered config (made
  # by build-image.sh with the build root UUID) must pass the boot contract in
  # exactly the declared policy.
  local generator="$root/etc/grub.d/10_greia_appliance"
  for required in 'boot-console-policy' 'console_arg="console=tty1"' \
    'panic_arg="panic=0"' 'greia-os-diagnostics' 'keystatus --shift'; do
    grep -Fq -- "$required" "$generator" || _greia_root_fail "$label" "GRUB generator lacks: $required"
  done
  # console=null means "no console" on the Debian 686 kernel (no ttynull):
  # PID 1 then cannot open /dev/console and the boot panics silently.
  if grep -Fq 'console_arg="console=null"' "$generator"; then
    _greia_root_fail "$label" "GRUB generator uses console=null (fatal: no ttynull in this kernel)"
  fi
  if grep -Eq 'panic=[1-9]' "$generator"; then
    _greia_root_fail "$label" "GRUB generator reintroduces a timed panic reboot"
  fi
  if [[ -s "$root/boot/grub/grub.cfg" ]]; then
    local contract_args=(--console-policy "$policy")
    (( developer )) && contract_args+=(--developer)
    PYTHONPATH="$project_root/src" PYTHONDONTWRITEBYTECODE=1 python3 -m greia_platform.boot_contract \
      "${contract_args[@]}" "$root/boot/grub/grub.cfg" >/dev/null || \
      _greia_root_fail "$label" "rendered grub.cfg violates the $policy boot contract"
  fi
}
