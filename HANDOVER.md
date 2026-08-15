# Greia — Standalone Engineering Handover

**Date:** 2026-08-15  
**Version family:** `0.13.x` development  
**Repository:** `frozenpepper/Greia` (private)  
**Canonical/default/development branch:** `main`  
**Primary blocking platform phase:** **R7 — Direct graphics/session/input architecture**  
**Current cross-cutting tranche:** **ADR 0021 automatic hardware enablement — source implemented, verification pending**

## Branch policy

The repository owner requires a **single-branch workflow**. `main` is the only development/integration branch. Do not create feature, recovery, archive or work branches unless the owner explicitly changes this policy. Commit coherent work directly to `main`; GitHub remains the persistent source of truth.

Historical duplicate ref names may remain visible because the available connector does not expose ref deletion. They are not development branches and must never contain divergent current source. After substantive work, advance those aliases to the exact current `main` commit until a GitHub surface capable of deleting them is used.

## Hosted execution boundary

Do **not** use, query, trigger, rerun, inspect or download GitHub Actions runs/jobs/logs/artifacts without explicit owner authorization for that specific hosted use. Repository source operations are allowed. Verification runs locally or on an explicitly owner-approved execution environment.

## Evidence boundary

Last complete source gate genuinely executed:

```text
commit: 097f0281888a58f6f26425807ce99d9f35449313
provider-free tests: 232 / 232 PASS
project validation: PASS
bundled Activity validation: PASS
source/shell/footprint gate: PASS
```

Everything newer remains **UNPROVEN unless explicitly recorded otherwise**. In particular, the composed hardware-enablement code described below is committed but has not yet passed its current source gate, a canonical Debian installer build, a VM installation, or diverse physical-machine acceptance.

## ADR 0021 — automatic hardware enablement

Architecture owner:

```text
docs/adr/0021-automatic-hardware-enablement-and-capability-discovery.md
```

Current implementation review:

```text
docs/reviews/2026-08-15_HARDWARE_ENABLEMENT_IMPLEMENTATION_REVIEW.md
```

Current acceptance gate:

```text
docs/testing/2026-08-15_HARDWARE_ENABLEMENT_SOURCE_ACCEPTANCE.md
```

### Product/architecture rule

Greia does **not** maintain a laptop/model driver database. Linux owns kernel driver binding. Greia owns bounded discovery, trusted firmware/support-package resolution, installation policy and semantic capability classification.

```text
physical hardware
      ↓
Linux kernel / udev / kmod
      ↓
bounded Greia sysfs inventory
      ↓
bound-driver modinfo firmware declarations
+ isenkram missing-firmware signal
+ isenkram modalias advisory signal
+ x86 microcode policy
      ↓
frozen Debian firmware-provider metadata
      ↓
verified offline support repository on installer media
      ↓
fail-closed machine-specific target package plan
      ↓
read-only local APT transaction
      ↓
initramfs / GRUB regeneration
      ↓
Greia HAL / semantic capability probes
```

### Core source

```text
src/greia_platform/hardware_enablement.py
src/greia_installer/hardware_support.py
src/greia_installer/hardware_enablement.py
src/greia_installer/hardware_support_install.py
src/greia_installer/engine.py
```

Operator/build tools:

```text
tools/inspect_hardware_enablement.py
tools/build_hardware_support_pool_manifest.py
tools/finalize_hardware_support_pool.py
tools/verify_hardware_support_pool.py
build/populate-hardware-support-pool.sh
build/install-live-hardware-firmware.sh
```

### Inventory and resolution

`LinuxSysfsHardwareInventory` observes a bounded, privacy-minimized hardware inventory. A device record contains only:

```text
sysfs path
subsystem
modalias
bound driver
```

Do not add storage/DMI/device serials or human-readable product-name heuristics to automatic resolution.

`IsenkramHardwareSupportResolver` treats:

- `isenkram-autoinstall-firmware -l` as an automatic firmware signal;
- general `isenkram-lookup -l` as advisory because it may recommend user-space utilities.

A general advisory recommendation can become automatic only when the independently verified frozen pool classifies that exact package as firmware.

`BoundDriverFirmwareResolver` independently asks the actual bound driver for `modinfo -F firmware` declarations and resolves exact or wildcard firmware paths through the frozen Debian provider map. This is required because the live installer already contains broad firmware; a detector for *currently missing* firmware alone can therefore legitimately return no missing firmware even though the final target still needs a firmware package.

x86 CPU vendor policy may select `intel-microcode` or `amd64-microcode`; ARM does not use this x86 policy.

### Frozen installer support pool

The canonical installer builder now creates an offline local APT repository at:

```text
/opt/greia-hardware-support
```

Candidate firmware/provider data is derived from Debian/isnkram `Fw-Contents-*` metadata. Debian Contents entries with multiple comma-separated package providers are preserved correctly. Greia does not maintain a PCI/USB-ID-to-package table.

Pool population:

- is download-only;
- resolves candidates independently so alternative/conflicting firmware providers do not poison one giant solver transaction;
- resolves dependencies against the **exact target squashfs `dpkg` status**, not the richer live installer state;
- forbids package-removal plans;
- verifies the live installed package set did not change during download-only resolution;
- admits no vendor downloaders or direct `dpkg -i` path.

The finalizer:

- bounds package count and pool bytes;
- rejects symlinked/non-regular `.deb` payloads;
- rejects duplicate package+architecture versions;
- inspects Debian package metadata;
- hashes every `.deb` by SHA-256;
- generates flat `Packages` and reproducible `Packages.gz` indexes;
- hashes both repository indexes;
- freezes firmware/microcode classes and firmware-file provider mapping;
- records unavailable candidates.

### Broad live support versus lean installed target

The USB/live image intentionally carries a broader compatibility payload than the installed Greia target.

The frozen manifest records:

```text
provided_firmware_packages
provided_microcode_packages
broad_firmware_packages
firmware_providers
```

`broad_firmware_packages` is a deterministic **minimal broad live cover**: for each concrete firmware file, the finalizer chooses one verified provider, preferring the smaller candidate `.deb` and then package name. The union of those providers is installed into the live installer. Every verified alternative remains in the frozen repository for exact machine-specific target selection.

This avoids both bad extremes:

- a tiny live installer unable to initialize hardware because firmware is missing;
- every final low-storage Greia machine permanently carrying all firmware packages.

The canonical builder composes the pool and broad live firmware **before** final live initramfs generation and squashfs compression. Its report records support-pool package count, bytes and manifest digest.

### Runtime pool trust boundary

`VerifiedHardwareSupportPool.load()` fail-closes on:

- missing/symlinked manifest;
- suite/architecture mismatch;
- malformed/duplicate package identity;
- package size or SHA-256 mismatch;
- symlinked/missing/unmanifested `.deb` payloads;
- `Packages`/`Packages.gz` size or digest mismatch;
- invalid firmware/microcode classes;
- provider mapping to non-firmware packages;
- a broad-live cover that does not cover every mapped concrete firmware file.

Only after this verification may the temporary APT source use local `trusted=yes`; trust comes from Greia's frozen-media verification, not from the APT flag itself.

### Machine-specific target installation

`InstallerHardwareEnablementPlanner` intersects current machine evidence with the verified media pool. Automatic target package output is empty unless the plan is complete.

`InstallationEngine` now supports explicit live-service composition through:

```text
GREIA_HARDWARE_SUPPORT_POOL=/opt/greia-hardware-support
GREIA_TARGET_IMAGE_PROFILE=/etc/greia-os/target-image-profile.json
```

The production live installer service sets both. Demo/tests/off-media calls remain compatible when the variables are absent.

Before the first destructive disk operation, the engine:

1. verifies payload and disk identity;
2. loads target suite/architecture from the target image profile;
3. hashes/verifies the frozen support pool;
4. resolves the current machine;
5. stops before erase if resolution is incomplete or a required frozen package is missing.

After the target payload is copied and chroot mounts exist, the engine:

1. re-opens and re-hashes the support pool at point of use;
2. bind-mounts it read-only under target `/run`;
3. gives APT a temporary source list containing **only** that local file repository;
4. installs only the selected machine-specific firmware/microcode package names plus frozen dependencies;
5. forbids package removal;
6. removes the temporary source;
7. regenerates initramfs and GRUB afterward.

The existing reverse-order mount cleanup owns the nested hardware-support bind mount before the target `/run` bind is detached.

The ordinary install record may contain:

```text
hardware_enablement_complete
hardware_support_packages
```

It must not contain raw modaliases, sysfs paths, bound driver names, device serials or Wi-Fi credentials.

### Why persistent hotplug package installation is not implemented yet

Do **not** add a second ad-hoc hardware system. The installed-system first-boot/hotplug resolver should reuse these same inventory/resolver/pool contracts, but persistent privileged package installation expands the attack/recovery surface beyond the one-shot installer transaction.

Implement it only after the current source/build/VM installer path passes. Future likely behavior:

```text
new device hotplug
→ kernel/udev bind if possible
→ Greia re-probe
→ if already usable: done
→ if signed support package is needed: trusted installed resolver
→ local installer media or approved Debian source
→ package transaction / re-probe
→ parent-visible working/degraded/unresolved status
```

No continuously running arbitrary `apt` agent and no vendor installer path.

## Current hardware-enablement regression source

```text
tests/test_hardware_enablement.py
tests/test_hardware_support_pool_manifest.py
tests/test_hardware_support_pool_finalize.py
tests/test_hardware_support_pool_build_script.py
tests/test_live_hardware_firmware_build_script.py
tests/test_hardware_enablement_build_contract.py
tests/test_installer_builder_hardware_support.py
tests/test_installer_hardware_support_pool.py
tests/test_installer_hardware_enablement.py
tests/test_installer_hardware_support_install.py
tests/test_installer_hardware_support_service.py
tests/test_installer_engine.py
```

These are **COMMITTED BUT UNEXECUTED**.

## Exact next source gate

On an owner-controlled exact current checkout of `main`:

```bash
PYTHONPATH=src:. python3 -m unittest \
  tests.test_hardware_enablement \
  tests.test_hardware_support_pool_manifest \
  tests.test_hardware_support_pool_finalize \
  tests.test_hardware_support_pool_build_script \
  tests.test_live_hardware_firmware_build_script \
  tests.test_hardware_enablement_build_contract \
  tests.test_installer_builder_hardware_support \
  tests.test_installer_hardware_support_pool \
  tests.test_installer_hardware_enablement \
  tests.test_installer_hardware_support_install \
  tests.test_installer_hardware_support_service \
  tests.test_installer_engine \
  -v
```

Then:

```bash
PYTHONPATH=src:. python3 -m unittest \
  tests.test_installer_wifi \
  tests.test_installer_wifi_setup \
  tests.test_installer_wifi_persistence \
  tests.test_installer_wifi_build_contract \
  tests.test_installer_state \
  tests.test_build_profiles \
  -v

make verify
```

Stop at the first genuine failure. Preserve exact stdout/stderr and tested commit SHA. Do not weaken the tests or replace Debian metadata with Greia-authored device tables.

## Build/VM evidence after source PASS

1. Build at least one Bookworm/i386 installer and one Trixie/amd64 installer on an owner-controlled Debian/Ubuntu build environment.
2. Record generated support-pool package counts/bytes and inspect manifests.
3. Confirm package resolution never changes the live package set during download-only pool construction.
4. Boot/install in the existing owner-controlled VM/QEMU path.
5. Verify malformed/mismatched support media stops before disk mutation.
6. Verify local read-only package transaction, cleanup, initramfs/GRUB ordering and no visible Linux UI.
7. Only then begin broad physical-machine/peripheral acceptance.

## Broad compatibility evidence still open

Automatic firmware/package resolution does not itself prove broad hardware support. Still required:

- deliberately diverse old/new x86 physical-machine matrix;
- keyboard/mouse/touchpad/touchscreen classes;
- controller/joystick classes;
- Wi-Fi and Ethernet families;
- audio output/input;
- internal/external displays and graphics paths;
- storage/controllers/card readers/USB;
- power/battery/brightness;
- representative Bluetooth/USB peripherals;
- explicit compatible/certified/degraded/unsupported results.

Kernel support remains separate from firmware support. Very new/old hardware may require different kernel tracks. Current x86 Phase-0 boot remains BIOS-oriented; UEFI breadth is a separate compatibility tranche. R7 production graphics/session/input architecture remains independently blocking.

## Existing Wi-Fi installer state

Installation-time Wi-Fi remains optional and offline-first:

```text
Welcome
→ target disk
→ input/screen settings
→ Wi-Fi (optional)
→ final confirmation
→ installation
```

Visible Open and WPA/WPA2/WPA3-Personal are the initial cases. Enterprise/802.1X is identified/deferred; WEP unsupported; hidden/manual SSID remains follow-up. Credentials are masked, absent from argv/log/install record, and successful profiles are persisted privately. Physical Wi-Fi acceptance remains NOT RUN.

## Developer remote-control / Acer agent workflow

`tools/greia_remote.py` supports remote status/screenshot/snapshot/logs/input/Activity deployment/service restart/reboot/poweroff/shell on explicit developer images. Screenshot streams actual Greia-display PNG bytes to the operator. Physical remote-agent acceptance remains NOT RUN.

## Other active R7 state

- Production display remains provisional Xorg/xinit; no compositor selected.
- ADR 0019 trusted system Home/Back source exists; concrete production backend remains unproven.
- ADR 0020 input/controller semantic source exists; production Activity input broker and physical controller acceptance remain open.
- `ShellInputController` still needs focused source verification and minimal live composition.
- Writing/Painting remain source-implemented but current execution/hardware evidence unproven.

## Non-negotiable continuation rules

- `main` only unless the owner explicitly changes branch policy;
- no unauthorized GitHub Actions execution or inspection;
- no visible Linux UI during normal child operation;
- no per-model Greia driver database;
- no arbitrary vendor drivers/downloaders;
- no raw hardware identifiers exposed to Activities;
- broad compatibility payload belongs primarily on removable installer media, not every final C0 target;
- automatic package resolution must be bounded, signed/frozen, fail-closed and no-removal;
- source/build/VM/physical evidence boundaries remain explicit and honest;
- do not implement persistent installed-system hotplug package installation before the installer path passes its current gates;
- preserve ADR 0019/0020 R7 trusted system-chrome/input constraints while expanding hardware breadth.
