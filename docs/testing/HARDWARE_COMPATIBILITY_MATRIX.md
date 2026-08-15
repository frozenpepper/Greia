# Greia Hardware Compatibility Matrix

This document defines how Greia scales hardware support evidence without becoming a per-model driver database.

## Status vocabulary

- **Generic-compatible** — Linux binds the required drivers and Greia's automatic enablement/capability probes work, but this exact device/model has not completed the physical certification suite.
- **Certified** — exact hardware completed the applicable physical Greia suite with evidence.
- **Degraded** — Greia boots/operates safely but one or more declared hardware capabilities are unavailable or reduced.
- **Unsupported** — no safe usable Greia configuration exists for a mandatory capability such as boot, display, primary input or durable storage.
- **Unknown** — no sufficient evidence yet.

A package being installed is never enough to mark a capability working or a machine certified.

## Evidence dimensions

Each physical machine run records applicable dimensions without storing hardware serial numbers:

| Dimension | Minimum evidence |
|---|---|
| Boot | installer boot, installed boot, clean shutdown/reboot, no visible Linux shell |
| CPU/platform | architecture, kernel track, microcode selection where applicable, idle/resource evidence |
| Graphics/display | bound DRM/display driver, native/safe modes, real rendered Shell, resolution change where supported |
| Keyboard | navigation, text entry, modifier/basic special keys |
| Pointer | motion, primary/secondary click, wheel where present |
| Touchpad | pointer/buttons plus supported Greia parent settings such as tap/speed |
| Touchscreen | touch capability and coordinate correctness where present |
| Controller | normalized navigation/game inputs and disconnect/reconnect where present |
| Wi-Fi | interface creation, scan, supported-network connection, reconnect, firmware persistence |
| Ethernet | link/interface, DHCP/address configuration where present |
| Audio output | usable default output, volume/mute, no crash when absent |
| Audio input | usable capture where declared/supported |
| Storage | install target, filesystem/boot reliability, realistic capacity handling |
| USB | representative HID/storage/controller hotplug and removal |
| Card reader | media discovery/mount policy where present |
| Bluetooth | representative supported peripheral path where enabled in the product |
| Power | AC/battery reporting, controlled shutdown; suspend only if Greia declares it supported |
| Brightness | bounded display brightness control where hardware exposes it |
| Camera | only when/if Greia exposes a camera capability |
| Remote development | developer-image status/screenshot/input/log/reboot path where applicable |

## Matrix strategy

Physical certification should deliberately sample hardware families rather than chase model counts:

### Legacy x86 floor

- first-generation Atom/netbook class;
- 32-bit PAE and non-PAE candidates where still supported;
- Intel integrated graphics from the legacy era;
- old SATA/PATA/USB storage paths;
- PS/2 and USB input;
- representative Atheros/Realtek/Broadcom/Intel wireless families as available.

### Mid-generation x86

- Core 2 / early Core i generations;
- Intel/AMD integrated graphics;
- common HDA audio;
- mixed BIOS/UEFI-era machines once the applicable Greia boot adapter exists;
- common laptop touchpads and function keys.

### Modern x86-64

- current Intel and AMD integrated platforms;
- high-DPI and external displays;
- current Intel/Realtek/MediaTek wireless examples;
- USB-C/modern USB where supported by the kernel track;
- modern Bluetooth/controller/peripheral samples.

### ARM reference platforms

Raspberry Pi 400 and Pi 500 remain first-class reference targets, but board-specific boot/display adapters are separate from the generic PC firmware resolver.

### Peripheral diversity

Across the machine matrix, deliberately rotate:

- wired/wireless keyboards and mice;
- multiple controller families plus a generic unmapped joystick case;
- USB audio;
- external HDMI/DisplayPort screens where available;
- USB storage and SD/card readers;
- optional touchscreens/tablets where product support is intended.

## Automatic enablement evidence

For each machine, record separately:

```text
inventory complete?       yes/no
resolver complete?        yes/no
frozen packages selected  names only
missing pool packages     names only
broad live firmware used  yes/no
installed target packages names only
post-install capability   working/degraded/unresolved
```

Do not persist raw serial numbers in ordinary compatibility records. PCI/USB IDs and modaliases may be captured in an explicit engineering evidence bundle when needed to diagnose compatibility, but they are not product-facing Greia identifiers and do not become deterministic product-name rules.

## Acceptance philosophy

The goal is not "every peripheral Linux has ever supported." The goal is:

1. broad zero-configuration success for standard hardware already supported by the selected Linux kernel track;
2. automatic trusted firmware/microcode enablement without network dependence during installation;
3. graceful degradation when optional hardware is unavailable;
4. clear evidence boundaries between generic compatibility and physical certification;
5. no desktop/Linux maintenance workflow exposed to children or parents merely because hardware is unusual.

## Current evidence state

ADR 0021's composed source implementation is newer than the last complete verified Greia source gate. Therefore the compatibility matrix currently contains **no new certified claims from this implementation tranche**. Populate it only from owner-controlled source/build/VM/physical evidence after the current hardware-enablement gate passes.
