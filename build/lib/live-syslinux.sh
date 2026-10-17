#!/usr/bin/env bash
# Shared Syslinux template selection for the Acer live USB writer and its
# read-only verifier (tools/build-live-usb.sh, tools/verify-live-usb.sh).
#
# The installer image declares its console policy in
# .disk/installer-image-profile.json (boot.console_policy, written by
# tools/build_profile.py). Images without the key predate the policy and keep
# the diagnostic template, so existing developer media behave as before.

# Print "quiet" or "diagnostic" for a mounted installer image partition.
greia_live_console_policy() {
  local image_mount="$1"
  local manifest="$image_mount/.disk/installer-image-profile.json"
  [[ -r "$manifest" ]] || { echo "diagnostic"; return 0; }
  python3 -I - "$manifest" <<'PY'
import json
import sys

with open(sys.argv[1], encoding="utf-8") as handle:
    manifest = json.load(handle)
policy = (manifest.get("boot") or {}).get("console_policy", "diagnostic")
if policy not in ("quiet", "diagnostic"):
    raise SystemExit(f"unknown boot.console_policy in installer manifest: {policy!r}")
print(policy)
PY
}

# Print the template path for a console policy.
greia_live_syslinux_template() {
  local project_root="$1"
  local policy="$2"
  case "$policy" in
    diagnostic) printf '%s\n' "$project_root/build/live-syslinux/syslinux.cfg.in" ;;
    quiet) printf '%s\n' "$project_root/build/live-syslinux/syslinux-quiet.cfg.in" ;;
    *) echo "Unknown live console policy: $policy" >&2; return 1 ;;
  esac
}
