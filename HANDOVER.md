# Greia — Standalone Engineering Handover

**Date:** 2026-08-15  
**Version family:** `0.13.x` development  
**Repository:** `frozenpepper/Greia` (private)  
**Canonical/default/development branch:** `main`  
**Blocking phase:** **R7 — Direct graphics/session/input architecture**

## Branch policy

The repository owner requires a **single-branch workflow**. `main` is the only development/integration branch. Do not create feature, recovery, archive or work branches unless the owner explicitly changes this policy. Commit coherent work directly to `main`; GitHub remains the persistent source of truth.

Historical duplicate ref names may remain visible because the available connector does not expose ref deletion. They are not development branches and must not contain divergent current source.

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

Everything newer remains **UNPROVEN unless explicitly recorded otherwise**.

## ADR 0021 — automatic hardware enablement

Greia's hardware-support strategy is now general rather than machine-list driven:

```text
hardware
  ↓
Linux kernel + udev driver binding
  ↓
Greia bounded hardware inventory
  ↓
Hardware Support Resolver
  ├─ modalias → support package
  ├─ missing firmware → firmware package
  ├─ CPU microcode
  └─ approved generic hardware metadata
  ↓
trusted signed local-media / approved Debian package source
  ↓
install only required support packages
  ↓
re-probe actual working hardware
  ↓
Greia semantic HAL capabilities
```

Normative owner:

```text
docs/adr/0021-automatic-hardware-enablement-and-capability-discovery.md
```

Permanent direction:

- do **not** maintain a Greia PCI/USB-ID-to-driver table;
- Linux kernel/udev/kmod owns normal driver matching and module loading;
- Greia observes bound drivers and working capabilities;
- installer media should carry a broad architecture/suite-appropriate compressed **Hardware Support Pool** with signed firmware/support packages and resolution metadata;
- the final installed target should receive only the support packages it actually needs wherever practical;
- resolver inputs should use Debian modalias/AppStream/isenkram/firmware-Contents metadata rather than Greia keyword/vendor lists;
- missing support must be re-probed after package installation; package presence alone is not success;
- automatic hardware installation may use only pre-approved signed package sources, never arbitrary vendor installers/downloads;
- generic hardware compatibility and Greia hardware **certification** are distinct;
- named machine profiles remain for architecture/boot families, extreme floors, board-specific exceptions and physical certification, not as the general driver database;
- per-machine firmware `extra_packages` are now the exception path. A normal newly encountered Wi-Fi/GPU/audio firmware need should be solved by the generic Hardware Support Resolver/Pool first;
- the resolver must also exist in lightweight idempotent form after installation so replaced/added hardware can be enabled automatically where trusted packages are available;
- when offline after installation and newly added hardware requires firmware that is not cached locally, Greia may ask the parent to insert compatible Greia installation/recovery media containing the support pool.

Kernel-family policy remains below the Greia platform contract. Modern amd64 currently uses Debian 13/Trixie, while true legacy i386 remains on Debian 12/Bookworm because Debian 13 no longer provides a regular i386 kernel/installer. Modern profiles may later use an explicitly approved newer/backports kernel when required for new hardware; firmware cannot compensate for an absent kernel driver.

Implementation still required before broad hardware-support claims:

1. bounded sysfs/udev hardware inventory;
2. generic package/firmware resolver abstraction;
3. build-time Hardware Support Pool and compact resolution metadata on installer media;
4. offline installer resolution before Wi-Fi/input/audio/display capability decisions where relevant;
5. trusted target package persistence;
6. post-install first-boot/hardware-change resolver;
7. post-enable semantic HAL re-probe/classification;
8. diagnostics distinguishing absent vs present-but-unresolved vs working hardware;
9. resource/installer-media measurements and multi-machine acceptance corpus.

No source implementation of the ADR 0021 resolver/pool is claimed yet.

## Installation-time Wi-Fi — source implemented, physical acceptance pending

Owners:

```text
docs/product/INSTALLER_WIFI_SETUP.md
docs/testing/2026-08-15_INSTALLER_WIFI_ACCEPTANCE.md
```

Graphical flow:

```text
Welcome
→ target disk
→ input/screen settings
→ Wi-Fi (optional)
→ final confirmation
→ installation
```

Current contract:

- **Skip for now** preserves full offline installation/first boot.
- Visible Open and WPA/WPA2/WPA3-Personal networks are the initial supported installer cases.
- Enterprise/802.1X is identified and deferred; WEP unsupported; hidden/manual SSID is follow-up scope.
- Credentials never belong in argv, ordinary logs or `install-record.json`.
- Password is masked, hidden from ordinary repr/debug output, and cleared after success/failure/skip.
- Successful connection persists the exact tested iwd profile under target `/var/lib/iwd` with private permissions.
- Install record contains only `wifi_configured: true/false`, not SSID/password.
- Scan/connect/DHCP work is asynchronous and generation-bound so stale results cannot replace newer parent choices.
- Back from final confirmation allows reselecting Wi-Fi rather than trapping the accepted choice.

Source owners:

```text
src/greia_installer/wifi.py
src/greia_installer/wifi_setup.py
src/greia_installer/main.py
src/greia_installer/engine.py
```

Live installer networking:

```text
build/package-sets/installer-base.txt
build/installer-overlay/etc/iwd/main.conf
build/installer-overlay/etc/systemd/system/greia-installer.service
```

Live package set includes `iwd`, `python3-dbus`, `rfkill`, `systemd-resolved`, and `wireless-regdb`. Live iwd owns temporary address/DNS configuration. `systemd-resolved` owns normal live `/etc/resolv.conf`; Greia deliberately does not overlay a competing file. Installed Greia retains iwd authentication plus systemd-networkd address configuration.

The Wi-Fi page currently assumes a usable kernel network device exists. Under ADR 0021 the generic Hardware Support Resolver must ultimately run before the Wi-Fi decision so a radio that requires packaged firmware can become usable from offline installer media without a model-specific patch.

Regression source:

```text
tests/test_installer_wifi.py
tests/test_installer_wifi_setup.py
tests/test_installer_wifi_persistence.py
tests/test_installer_wifi_build_contract.py
tests/test_installer_state.py
```

These tests are **COMMITTED BUT UNEXECUTED**. Physical Wi-Fi evidence is **NOT RUN**.

## Other active R7 state

- Production display remains provisional Xorg/xinit; no compositor selected.
- ADR 0019 trusted system Home/Back source exists, concrete production backend remains unproven.
- ADR 0020 input/controller semantic source exists; production Activity input broker and physical controller acceptance remain open.
- `ShellInputController` still needs focused source verification and minimal live composition.
- Writing/Painting remain source-implemented but current execution/hardware evidence unproven.

## Developer remote-control / Acer agent workflow

`tools/greia_remote.py` supports remote wait/status/screenshot/snapshot/logs/input/Activity deployment/service restart/reboot/poweroff/shell on explicit developer images. Screenshot streams actual Greia-display PNG bytes to the operator. Physical Acer remote-agent acceptance remains NOT RUN.

## Exact next source verification

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

Stop on first genuine failure and preserve exact stdout/stderr. Do not weaken tests to manufacture PASS.

## Next implementation/evidence after source PASS

1. Implement ADR 0021 bounded hardware inventory and resolver contracts before adding more model-specific firmware packages.
2. Prototype/build the installer Hardware Support Pool and measure installer-media size/RAM impact; do not install the whole pool into the final target.
3. Integrate offline support resolution ahead of installer Wi-Fi capability selection and prove on multiple unlike Wi-Fi adapters.
4. Run the Wi-Fi installer demo at 1024×600 and physical installer acceptance.
5. Continue R7 trusted system-chrome/input/controller integration and physical evidence.
6. Execute Acer remote-agent acceptance on the installed developer profile.
7. Expand hardware acceptance beyond the Acer into a deliberately diverse old/new PC corpus plus Pi references.
