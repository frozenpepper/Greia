# ADR 0021 — Automatic Hardware Enablement and Capability Discovery

**Status:** ACCEPTED  
**Date:** 2026-08-15

## Context

Greia is intended to run on a broad range of old and new hardware. Per-model package lists do not scale and would turn hardware compatibility into a manually maintained collection of laptop-specific exceptions.

Linux already supplies the primary hardware-driver matching mechanisms. Kernel devices expose modalias/device metadata; udev consumes kernel device events; kernel modules and their dependencies are loaded through the normal module stack; input, display, audio and network subsystems expose normalized device interfaces above individual vendors.

The Greia problem is therefore not to invent a second driver system. Greia needs to:

1. ensure that the selected kernel family contains an appropriate breadth of drivers for the machine generation;
2. make distributable firmware and hardware-support packages available before networking exists;
3. determine which support packages the current machine actually needs;
4. install only those packages into the final target where practical;
5. re-probe the machine after enablement;
6. translate the resulting working devices into Greia semantic capabilities;
7. preserve a recovery path for later-added or replaced hardware.

Debian 12 and later separate redistributable non-free firmware into `non-free-firmware`. Debian's own installer uses kernel-log and modalias information plus firmware metadata to locate relevant firmware packages. Debian also ships `isenkram-cli`, whose purpose is to map current-machine modalias values and hardware metadata to useful installable hardware-support packages.

Greia's custom installer is not Debian Installer, so those behaviors do not happen automatically merely because the archive component is enabled. Greia must deliberately provide an equivalent product-level hardware-enablement flow.

## Decision

Greia adopts a **platform-owned Automatic Hardware Enablement pipeline**.

```text
physical hardware
      ↓
Linux kernel device discovery
      ↓
udev / kernel driver binding
      ↓
Greia Hardware Inventory
      ↓
Hardware Support Resolver
  ├─ modalias → package mapping
  ├─ missing firmware → package mapping
  ├─ CPU microcode selection
  └─ approved hardware-support metadata
      ↓
trusted signed package source
  ├─ local installer-media support pool
  └─ approved Debian repository when online
      ↓
install only required support packages
      ↓
re-probe devices
      ↓
Greia semantic HAL capabilities
```

Activities never see this machinery. They continue to consume semantic Greia capabilities and input contracts.

## 1. Kernel driver matching remains Linux-owned

Greia must not maintain a PCI/USB-ID-to-kernel-module table.

Normal driver discovery, module dependency resolution and hotplug/coldplug stay with the Linux kernel, udev and kmod/modprobe stack.

Greia may observe which driver is bound and whether a device is usable, but it does not replace Linux driver matching with application code.

## 2. Hardware Inventory is vendor-neutral

Greia shall maintain a bounded immutable hardware inventory derived from trusted host state such as sysfs/udev.

The inventory may contain:

- device/subsystem identity;
- modalias;
- currently bound driver/module;
- parent/seat relationship where relevant;
- firmware-missing state when it can be established reliably;
- normalized subsystem/capability observations;
- enough stable information to compare hardware across boots without storing unnecessary serial numbers.

The inventory is diagnostic/platform state, not Activity authority.

## 3. Installer media carries broad hardware support; installed targets stay lean

The live installer should have access to a broad, architecture/suite-appropriate **Hardware Support Pool** containing distributable firmware/support packages and the metadata needed to resolve them offline.

The pool should preferably live as compressed package payload on the installer medium rather than installing every firmware package into the live root or final Greia target.

At installation time Greia resolves the current machine's needs and installs only the matching packages into the target wherever practical.

Consequences:

- Wi-Fi firmware can be resolved before Wi-Fi itself works;
- old C0 machines do not pay the installed-disk cost for unrelated modern GPU/Wi-Fi firmware;
- the USB installer may be larger than the installed system by design;
- package provenance remains Debian/Greia-trusted rather than downloading arbitrary vendor executables.

## 4. Resolution sources

The Hardware Support Resolver should use general package metadata, not Greia-authored device keyword lists.

Accepted resolution sources include:

- Debian modalias/AppStream hardware-support metadata;
- Debian `isenkram` mappings or equivalent data derived from them;
- Debian firmware Contents metadata mapping requested firmware filenames to packages;
- explicit architecture-level microcode policy;
- small Greia exception/quirk metadata only when generic upstream mechanisms cannot represent a known issue.

A Greia quirk must document the upstream/kernel/libinput/driver limitation that requires it. Hardware exceptions must not become the normal path.

## 5. Signed package boundary

Automatic hardware enablement may install only packages from sources approved by Greia build/policy configuration and verified through the normal package trust chain.

A detected PCI/USB device is never authority to execute a vendor installer, arbitrary script, downloaded binary or unsigned package.

Automatic installation is therefore acceptable as a platform operation because both the package source and allowed package class are pre-authorized.

## 6. Offline-first resolution

Initial-machine hardware enablement must work without Internet access.

The local installer Hardware Support Pool is authoritative for the release's supported offline hardware envelope.

When Internet access exists, Greia may additionally resolve newer signed packages from the approved suite/update/backports policy, but installation cannot depend on reaching the network.

If a required package is neither on media nor available from an approved configured source, Greia reports the capability as unavailable/degraded rather than executing an unsafe fallback.

## 7. Modern and legacy kernel families may differ beneath one Greia platform

Greia does not force all machines onto one Debian/kernel generation.

For example, Debian 13/Trixie is appropriate for modern amd64/arm64 hardware and provides a modern kernel/hardware stack, while true 32-bit x86 hardware cannot use Debian 13 as a regular installation architecture and therefore remains on a supported legacy base such as Debian 12/Bookworm while that support window remains valid.

This is an implementation/image-profile distinction below the Greia platform contract.

Hardware-support policy should therefore be expressed by architecture/platform family, not by named laptop models.

## 8. Newer hardware may use an approved newer kernel track

Firmware cannot compensate for a kernel that predates the device driver.

Modern hardware profiles may select the current stable kernel or an explicitly approved backports kernel when newer hardware support is required and resource/security evidence is acceptable.

Legacy C0 profiles may remain on an older supported kernel where that is necessary for architecture compatibility.

Kernel selection is a profile/family policy, not an Activity concern.

## 9. Input discovery

For ordinary input devices Greia relies on the kernel evdev/udev/libinput ecosystem to normalize device differences.

Greia should consume capability-oriented input facts such as:

- keyboard;
- pointer/mouse;
- touchpad;
- touchscreen;
- tablet;
- switches;
- controller/joystick through the dedicated ADR 0020 path.

Device-specific touchpad quirks should stay in libinput/upstream data where possible. Greia's parent settings control semantic options such as tap-to-click, acceleration or scrolling only when the device reports that the option is supported.

## 10. Display discovery

Display hardware is discovered through the kernel DRM/KMS subsystem.

Greia should consume connector state and advertised modes/EDID rather than maintain per-monitor resolution lists.

The display/session backend selected by R7 remains responsible for presentation, trusted system chrome and recovery. Hardware enablement is responsible for determining whether an appropriate GPU driver/firmware path exists and for exposing the resulting display capabilities.

Safe/fallback display modes remain necessary for broken or incomplete GPU paths.

## 11. Audio discovery

Kernel audio-driver binding remains ALSA-owned.

Greia's Audio Service should discover usable output/input endpoints through the selected audio backend rather than by sound-card vendor/model.

A richer user-space broker such as PipeWire may enumerate ALSA devices and hotplug on hardware classes where its measured resource cost is acceptable. A lower-resource backend may be used below the same Greia Audio Service contract when required by C0 evidence.

The Greia API does not fragment by backend.

## 12. Network discovery

Wi-Fi/Ethernet capability is exposed only after a usable kernel network device exists.

The installation-time Wi-Fi page consumes that capability through iwd. If the Wi-Fi device exists physically but cannot become usable because firmware is missing, the Hardware Support Resolver runs before the Wi-Fi setup decision and may install the required signed firmware from local media.

## 13. First boot and later hardware changes

The resolver is not installer-only.

After installation Greia should maintain a lightweight idempotent hardware-enablement service that:

1. compares current hardware with the last accepted hardware inventory;
2. lets Linux bind drivers normally;
3. resolves newly required approved support packages;
4. re-probes Greia capabilities;
5. reports degraded/unresolved hardware to Greia Parents/diagnostics.

It must not run heavy package resolution continuously. Hotplug events are coalesced/bounded and normal already-supported USB input/storage devices should require no package transaction.

If new hardware requires firmware that is unavailable locally and no working network path exists, Greia may ask the parent to insert compatible Greia installation/recovery media containing the Hardware Support Pool.

## 14. Capability validation is distinct from package installation

A package being installed does not prove a device works.

After enablement Greia re-probes the actual system and records semantic facts such as:

```text
display usable
keyboard available
pointer available
touch available
controller available
audio output available
audio input available
Wi-Fi available
Ethernet available
removable media service available
battery/power capability available
```

Only observed working capability feeds Activity compatibility and parent UI.

## 15. Essential versus optional hardware

Installation should fail closed only when the machine cannot provide the minimum interaction/storage/display path required to install/use Greia safely.

Missing optional devices such as Wi-Fi, microphone, camera, Bluetooth or game controller do not block installation; Greia records them as unavailable.

A device that is physically present but unresolved should be reported distinctly from a device that is simply absent.

## 16. Certification versus generic compatibility

Greia distinguishes:

- **generic compatible:** automatically discovered/enabled through standard Linux/Debian mechanisms;
- **certified:** exercised by Greia's hardware acceptance suite with recorded evidence;
- **degraded:** core Greia works but one or more expected hardware capabilities are unavailable;
- **unsupported:** Greia cannot establish the required safe minimum environment.

Greia does not need a named profile for every laptop model to support it generically.

Named reference profiles remain useful for extreme floors, board-specific boot architectures and regression certification.

## 17. Hardware acceptance inventory

Reference/certification evidence should include at least:

- CPU/architecture and selected kernel family;
- storage/controller;
- DRM GPU driver, connectors and modes;
- keyboards/mice/touchpads/touchscreens;
- controller/joystick where relevant;
- ALSA/audio endpoints;
- Ethernet/Wi-Fi interfaces and bound drivers;
- firmware requests and resolved packages;
- Bluetooth where supported;
- battery/AC/power/suspend behavior where applicable;
- USB/removable media;
- any Greia-specific exception applied.

## Rejected alternatives

### Per-model driver lists

Rejected because they do not scale, duplicate Linux's hardware database and quickly become stale.

### Install every firmware/support package on every target

Rejected because it wastes significant disk on the C0 floor and does not solve missing-kernel-driver problems.

### Download vendor drivers automatically

Rejected because it creates an unacceptable trust, maintenance and reproducibility boundary.

### Treat `lspci`/USB product names as the primary resolver

Rejected. Human-readable device names are diagnostic presentation; machine resolution should use modalias, subsystem metadata and trusted package mappings.

### Consider package installation a successful hardware test

Rejected. Actual post-enable capability probing is required.

## Consequences

Greia gains a scalable hardware model: generic supported Linux hardware should normally work automatically, while Greia retains explicit evidence and exception paths for troublesome devices.

The installer becomes somewhat larger because it carries a broad hardware-support pool, but installed systems can remain lean.

The project must implement the resolver, support-pool build step, re-probe/capability classification and first-boot/hotplug service before broad hardware-support claims are made.

Existing per-reference profiles remain valid as certification/build-family inputs but are no longer interpreted as the complete universe of supported machines.
