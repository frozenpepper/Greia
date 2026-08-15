# Greia Hardware Enablement — Source Acceptance

**Date:** 2026-08-15  
**Status:** source gate definition; not yet executed on the current `main`

This gate covers ADR 0021's first implementation tranche: bounded sysfs inventory,
Debian isenkram resolution policy, x86 microcode policy, offline firmware-pool
candidate manifest generation, and live-installer resolver prerequisites.

It does **not** certify broad physical hardware support and does not authorize
automatic package installation into a target yet.

## Invariants

The gate must preserve all of the following:

- no Greia-authored PCI/USB product-to-driver database;
- inventory is bounded and does not collect storage/DMI/device serial numbers;
- kernel driver binding remains Linux/udev/kmod owned;
- `isenkram-autoinstall-firmware -l` may produce automatic firmware candidates;
- general `isenkram-lookup -l` results are advisory only;
- incomplete automatic resolution exposes zero automatic packages;
- commands are fixed argument arrays with `shell=False`;
- installer contains `isenkram-cli`, while target installation of detected
  support packages is still a separate later authority boundary;
- pool candidates are derived from Debian firmware Contents metadata, not
  product-name keyword lists;
- x86 microcode is architecture-level policy only;
- no GitHub Actions execution is part of this gate.

## Focused source gate

From the repository root of the exact current `main` commit:

```bash
PYTHONPATH=src:. python3 -m unittest \
  tests.test_hardware_enablement \
  tests.test_hardware_support_pool_manifest \
  tests.test_hardware_enablement_build_contract \
  -v
```

Stop at the first genuine failure. Preserve exact stdout/stderr and the tested
commit SHA. Do not weaken tests or replace Debian metadata with hand-maintained
device mappings to manufacture a PASS.

## Machine observation check

On a Linux machine with `isenkram-cli` installed:

```bash
PYTHONPATH=src python3 tools/inspect_hardware_enablement.py --pretty > hardware-enablement.json
```

Acceptance properties:

1. output is valid JSON;
2. `inventory.device_count` is bounded;
3. device records contain only sysfs path, subsystem, modalias and bound driver;
4. no serial numbers are present;
5. firmware/microcode candidates appear under `support.automatic_packages` only
   when `support.complete` is true;
6. general hardware-tool suggestions may appear only as advisory packages;
7. the command changes no packages or device state.

## Offline-pool manifest check

On a built/live installer root containing Debian `isenkram-cli` metadata:

```bash
python3 tools/build_hardware_support_pool_manifest.py \
  --isenkram-dir <LIVE_ROOT>/usr/share/isenkram \
  --suite <SUITE> \
  --architecture <ARCH> \
  --output hardware-support-candidates.json
```

The manifest must contain only safe Debian package basenames derived from
`Fw-Contents-*` firmware metadata plus the architecture-level x86 microcode
candidates where applicable. Package availability still must be checked by APT
before a later pool-population step downloads anything.

## Explicitly not yet accepted

The following remain future gates:

- downloading/populating the broad `.deb` pool during installer-image build;
- a local verified APT repository/index on the installer;
- applying selected auto-eligible packages into the target;
- post-install re-probe and capability classification;
- first-boot/hotplug enablement service;
- broad physical old/new hardware certification.
