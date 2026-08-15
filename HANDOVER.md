# Greia — Standalone Engineering Handover

**Date:** 2026-08-15  
**Version family:** `0.13.x` development  
**Repository:** `frozenpepper/Greia` (private)  
**Canonical/default/development branch:** `main`  
**Blocking phase:** **R7 — Direct graphics/session/input architecture**

## Branch policy

The repository owner has explicitly requested a **single-branch workflow**. `main` is the only development/integration branch. Do not create feature, recovery, archive or work branches unless the owner explicitly changes this policy. Commit coherent work directly to `main` as work proceeds. GitHub remains the persistent source of truth.

PR #4 (`r7-direct-graphics`) was merged into `main` with merge commit `6019eb06134478861010cdcfae649a921f1ffc7d`. Historical duplicate ref names may remain visible because the available connector does not expose ref deletion; they must not be used for development and should be kept aligned to `main` until they can be physically deleted.

## Resume order

Read `AGENTS.md`, `README.md`, `docs/DOCUMENTATION.md`, `docs/architecture/GREIA_ARCHITECTURE.md`, accepted ADRs through ADR 0020, `docs/engineering/ENGINEERING_FOUNDATIONS.md`, applicable product requirements including `docs/product/INSTALLER_WIFI_SETUP.md`, the active implementation plan, this handover, applicable testing/review docs, agent operations, and the Activity skill when relevant.

Always resolve the current **`main` HEAD** before editing or testing.

## Hosted execution boundary

Do **not** use, query, trigger, rerun, inspect or download GitHub Actions runs/jobs/logs/artifacts without explicit owner authorization for that specific hosted use. Repository source operations are allowed. Verification runs locally or on an explicitly owner-approved execution environment.

## Verification boundary

Last complete source gate genuinely executed:

```text
commit: 097f0281888a58f6f26425807ce99d9f35449313
provider-free tests: 232 / 232 PASS
project validation: PASS
bundled Activity validation: PASS
source/shell/footprint gate: PASS
```

Everything newer remains **UNPROVEN unless explicitly recorded otherwise**. Do not promote source presence to runtime or hardware PASS.

## Installation-time Wi-Fi — source implemented, physical acceptance pending

Product requirement:

```text
docs/product/INSTALLER_WIFI_SETUP.md
```

Physical/source acceptance protocol:

```text
docs/testing/2026-08-15_INSTALLER_WIFI_ACCEPTANCE.md
```

The graphical installer now has this intended flow:

```text
Welcome
→ target disk
→ input/screen settings
→ Wi-Fi (optional)
→ final confirmation
→ installation
```

Permanent product semantics:

- Wi-Fi setup is optional; **Skip for now** must always preserve a complete offline installation path.
- Internet reachability is never required to install or first-boot Greia.
- Phase-0 installer supports visible open and WPA/WPA2/WPA3-Personal networks through iwd's `open`/`psk` model.
- Enterprise/802.1X is identified but deliberately deferred to a later typed Greia Parents configuration flow; WEP is unsupported; hidden/manual SSID remains follow-up scope.
- credentials must not appear in command-line arguments, ordinary logs or `install-record.json`.
- password UI is masked and transient credentials are suppressed from ordinary object repr/debug output and cleared after successful connection, failed connection, or skip.
- successful configuration persists the exact tested iwd profile to the installed target under `/var/lib/iwd` with private permissions.
- the installation record stores only `wifi_configured: true/false`, never SSID/password.
- slow scan/connection/DHCP work runs outside the Pygame event/render loop.
- stale async scan/connect results are invalidated by generation and cannot overwrite a newer parent choice.

Relevant source:

```text
src/greia_installer/wifi.py
src/greia_installer/wifi_setup.py
src/greia_installer/main.py
src/greia_installer/engine.py
```

Live installer networking additions:

```text
build/package-sets/installer-base.txt
build/installer-overlay/etc/iwd/main.conf
build/installer-overlay/etc/systemd/system/greia-installer.service
```

Every live installer now declares the small wireless stack in `installer-base`:

```text
iwd
python3-dbus
rfkill
systemd-resolved
wireless-regdb
```

Live iwd temporarily owns address/DNS configuration (`EnableNetworkConfiguration=true`) so the installation environment does not need a second live network manager. Debian's `systemd-resolved` package owns normal live `/etc/resolv.conf` integration; Greia deliberately does not overlay a competing regular file. The installed target retains the existing platform architecture where iwd owns Wi-Fi authentication and systemd-networkd owns address configuration.

The build-profile resolver also applies the selected profile's kernel, video packages and `extra_packages` to installer artifacts. Therefore any firmware package required by the exact Acer/Pi radio after physical inventory should be added to the hardware profile so both live installer and installed target receive it; do not add a separate ad-hoc installer firmware path.

Focused regression source added:

```text
tests/test_installer_wifi.py
tests/test_installer_wifi_setup.py
tests/test_installer_wifi_persistence.py
tests/test_installer_wifi_build_contract.py
```

These tests are **COMMITTED BUT UNEXECUTED**. No real Acer Wi-Fi scan, Personal connection, wrong-password recovery, target profile persistence or first-boot reconnect PASS is currently claimed.

Important physical acceptance still required:

1. boot exact Acer installer USB;
2. prove the real radio/driver/firmware is present;
3. scan visible networks;
4. connect to a supported Personal network without password leakage;
5. prove wrong-password recovery;
6. install using that network;
7. remove USB and prove first-boot reconnect;
8. separately prove a complete offline install using Skip for now.

## Phase-0 UI / system-navigation state

ADR 0018 owns the lightweight Greia UI foundation in `src/greia_platform/ui_core.py`. ADR 0019 requires immutable Greia-owned Activity Home/Back outside Activity rendering/input authority; current source lives in `src/greia_platform/system_chrome.py` and `src/greia_launcher/system_chrome.py`. No concrete production trusted `SystemChromeBackend` has yet passed real hardware acceptance.

## Phase-0 input/controller state — ADR 0020

Controller/joystick support is a Phase-0 platform requirement. Current runtime-neutral source is in `src/greia_platform/input_core.py`, `src/greia_platform/pygame_input.py`, and `src/greia_launcher/shell_input.py`.

Important boundaries remain: ordinary Activities do not receive broad `/dev/input`; Guide/system input is platform-reserved where supported; Shell controller composition still needs focused verification; production Activity controller delivery still requires the trusted R7 input broker; generic unmapped joystick policy still needs explicit evidence-backed closure.

Physical acceptance procedure:

```text
docs/testing/2026-08-15_PHASE0_INPUT_CONTROLLER_ACCEPTANCE.md
```

## First-party Phase-0 creative Activities

Source exists for `org.greia.writing` (`text`) and `org.greia.painting` (`pointer`). Both remain source-implemented but current execution/hardware evidence is unproven.

## Developer remote-control / Acer agent workflow

The installed developer-image architecture is designed so an agent on the operator computer can remotely test and monitor Greia. `tools/greia_remote.py` supports wait/status/screenshot/snapshot/logs/key/mouse/text/Activity deploy/remove/restore/service restart/reboot/poweroff/shell operations. Screenshot streams actual Greia-display PNG bytes to the operator; snapshot collects `screen.png`, `status.json`, `logs.txt`, and `snapshot.json`.

Acer developer profiles exist for the current i386/non-PAE/amd64 candidates. Matching normal profiles remain remote-disabled. Physical Acer remote-agent acceptance is defined by `docs/testing/2026-08-15_ACER_REMOTE_AGENT_ACCEPTANCE.md` and remains **NOT RUN**.

## R7 production state

```text
installed display path:       Xorg + xinit compatibility
status:                       PROVISIONAL
production compositor:        none selected
trusted system chrome:        source contract/coordinator implemented; backend unproven
controller semantic core:     source implemented; unproven
production Activity input broker: NOT IMPLEMENTED
physical controller evidence: NOT RUN
Acer remote-agent physical evidence: NOT RUN
installer Wi-Fi physical evidence: NOT RUN
```

## Exact next source verification

On an owner-controlled current checkout of `main`, run:

```bash
PYTHONPATH=src python3 -m unittest \
  tests.test_installer_wifi \
  tests.test_installer_wifi_setup \
  tests.test_installer_wifi_persistence \
  tests.test_installer_wifi_build_contract \
  tests.test_installer_state \
  tests.test_installer_engine \
  tests.test_build_profiles \
  -v

PYTHONPATH=src python3 -m unittest \
  tests.test_input_core \
  tests.test_pygame_input \
  tests.test_activity_input_contract \
  tests.test_activity_input_api \
  tests.test_hal_legacy_x \
  tests.test_shell_input \
  tests.test_system_chrome \
  tests.test_ui_core \
  tests.test_ui_core_lifecycle \
  tests.test_activity_ui \
  tests.test_core_creation_activities \
  tests.test_activity_theme_access \
  -v

PYTHONPATH=src python3 tools/validate_activity.py activities/writing
PYTHONPATH=src python3 tools/validate_activity.py activities/painting
PYTHONPATH=src python3 -m unittest discover -s tests -p 'test_developer_remote.py' -v
make verify
```

Stop on first real failure and preserve exact stdout/stderr. Do not weaken tests to manufacture PASS.

## Next implementation/evidence after source PASS

1. Run the installer Wi-Fi demo/windowed visual acceptance at 1024×600.
2. Build the exact Acer installer image and execute `docs/testing/2026-08-15_INSTALLER_WIFI_ACCEPTANCE.md`, initially non-destructively through the Wi-Fi page.
3. If exact radio firmware is missing, add it to the Acer hardware profile and rebuild rather than installing it manually on the live target.
4. Continue the open R7 system-chrome/input/controller integration and physical evidence sequence.
5. Execute Acer remote-agent acceptance once the exact developer profile is installed.

## Invariants

- `main` is the sole development branch unless the owner explicitly changes policy;
- no visible Linux UI in normal child operation;
- installation-time Wi-Fi is available when wanted but never required;
- Wi-Fi credentials never enter normal install records/logs/argv;
- complete offline installation and first boot remain mandatory;
- Activity remains runtime-neutral;
- every child-facing Activity retains Greia-owned Home outside Activity authority;
- controller/joystick support is a platform concern, not per-Activity raw hardware code;
- progression/rewards remain platform-owned;
- Acer remains the extreme resource floor and ARM remains co-equal;
- no unauthorized hosted execution;
- no desktop/window-manager architecture;
- source/VM/physical evidence boundaries remain explicit and honest.
