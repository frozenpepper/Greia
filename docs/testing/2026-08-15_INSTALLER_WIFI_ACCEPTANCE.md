# Greia Installer Wi-Fi Acceptance

**Date:** 2026-08-15  
**Status:** ACTIVE physical/source acceptance protocol  
**Applies to:** `docs/product/INSTALLER_WIFI_SETUP.md`

## Purpose

Prove that optional Wi-Fi configuration works inside the graphical Greia installer on real reference hardware and that the selected network survives into the installed system without making networking an installation prerequisite.

## Hard rules

- Do not use/query/trigger GitHub Actions for this procedure without explicit owner authorization.
- Record the exact `main` SHA and image/profile used.
- Preserve the first real failure; do not weaken installer safety or network credential handling to obtain PASS.
- Never put the test Wi-Fi password in logs, screenshots, filenames, evidence summaries, commits, or chat output.
- Do not substitute a host/VM network device for physical Acer Wi-Fi acceptance.
- The destructive installation section may run only on the intended disposable/approved target disk.

## A. Focused source verification

From the current `main` checkout:

```bash
SOURCE_SHA="$(git rev-parse HEAD)"
printf 'SOURCE_SHA=%s\n' "$SOURCE_SHA"

PYTHONPATH=src python3 -m unittest \
  tests.test_installer_wifi \
  tests.test_installer_wifi_setup \
  tests.test_installer_wifi_persistence \
  tests.test_installer_wifi_build_contract \
  tests.test_installer_state \
  tests.test_installer_engine \
  tests.test_build_profiles \
  -v

make verify
```

Stop on the first genuine failure.

## B. Safe graphical preview

Before destructive hardware work, run the demo/windowed installer on a development machine where Pygame is available:

```bash
PYTHONPATH=src python3 -m greia_installer.main \
  --root . \
  --windowed \
  --demo
```

Confirm the page order:

```text
Welcome
→ target disk
→ Input and screen
→ Wi-Fi (optional)
→ Ready to install
```

On the Wi-Fi page verify visually:

- bounded network rows fit at 1024×600;
- Personal network accepts masked text;
- Open network requires no password;
- Enterprise network is labelled for later configuration;
- Refresh is visible;
- Skip for now is obvious;
- Back works;
- connection/scanning states do not freeze rendering.

Do not treat demo PASS as hardware networking evidence.

## C. Build exact installer image

Use the exact Acer profile selected by inventory evidence. Examples are currently:

```text
acer-aspire-one-i386
acer-aspire-one-i386-nonpae
acer-aspire-one-amd64
```

Build using the canonical installer builder for that exact profile and preserve its SHA256/profile manifest.

Confirm the live filesystem contains at minimum:

```text
iwd
python3-dbus
rfkill
systemd-resolved
wireless-regdb
```

and that `greia-installer.service` orders after iwd/systemd-resolved.

## D. Non-destructive live Wi-Fi test on Acer

Boot the exact installer USB on the Acer without starting disk installation.

Record non-secret hardware identity relevant to the wireless adapter/driver/firmware. Do **not** record the network password.

Verify:

1. the graphical installer reaches the Wi-Fi page without Linux UI;
2. the physical Wi-Fi adapter is available;
3. nearby visible networks appear after scan;
4. Refresh works;
5. signal ordering/labels are plausible;
6. the UI remains responsive during scan;
7. selecting an unsupported Enterprise network does not present a misleading Personal-password path;
8. Skip for now proceeds to final confirmation without network access.

If the Acer radio is not available because its exact chipset requires firmware, STOP and record the chipset/driver/firmware fact. Add the required firmware package to the Acer build profile so both live installer and installed target receive it. Do not install ad-hoc packages manually and call that acceptance.

## E. Personal Wi-Fi connection

Using a test/home WPA/WPA2/WPA3-Personal network whose credentials the owner is authorized to use:

1. select the SSID;
2. enter the password and confirm that only masking characters appear;
3. connect;
4. confirm the UI reaches the connected state;
5. confirm the graphical installer remains responsive;
6. inspect relevant bounded logs only for credential leakage—the password must not appear;
7. return/back/re-enter as needed and ensure stale scan/connect results do not overwrite a newer parent choice.

Then deliberately try one wrong password:

- connection must fail recoverably;
- the password must not appear in the error text or logs;
- a failed newly-created iwd profile must not remain as the accepted installation profile;
- the parent must still be able to Skip for now.

## F. Destructive install with Wi-Fi configured

Only on the approved target disk:

1. connect successfully to the intended Personal network;
2. reach final confirmation and verify it shows the selected SSID but never the password;
3. perform the normal hold-to-erase installation;
4. save the parent recovery code;
5. allow Greia to power off cleanly;
6. remove the USB;
7. boot the installed system.

After first boot, verify the installed target reconnects to the same network through its normal target networking architecture.

Inspect `/etc/greia-os/install-record.json` through the approved maintenance/developer path and confirm:

```text
wifi_configured = true
```

while the SSID and password are absent from that record.

Confirm the installed iwd profile is root-only (`0600`) and its state directory is not world-readable.

## G. Destructive/offline install

On an approved repeatable target or after restoring the test baseline:

1. boot the installer with Wi-Fi unavailable or choose Skip for now;
2. complete the entire installation offline;
3. boot the installed system offline;
4. confirm normal child/profile operation does not require networking;
5. confirm the install record reports Wi-Fi not configured and no installer-created iwd profile exists.

This is a mandatory acceptance path, not a fallback of lesser quality.

## H. Reconfiguration expectation

After installation, confirm that the product design still has a typed parent-facing route for configuring/changing Wi-Fi later. If that Greia Parents implementation is not yet complete, record it as a later product implementation gap; do not expose Linux network files or `iwctl` to the parent as the supported UI.

## PASS scope

A full PASS proves optional installation-time Wi-Fi for the tested Greia SHA/profile/Acer wireless adapter/network type. It does not prove every wireless chipset, Enterprise/802.1X, WEP, hidden SSIDs, Raspberry Pi Wi-Fi, or future Web/runtime networking behavior.
