# Greia Installer Wi-Fi Setup

**Status:** ACCEPTED product requirement  
**Date:** 2026-08-15  
**Applies to:** every user-facing Greia installation image

## Product requirement

A parent installing Greia must be able to configure ordinary home Wi-Fi during the graphical installation if desired, without using a Linux shell, terminal, network configuration file, or post-install maintenance procedure.

Wi-Fi is **optional**. Greia remains offline-first and installation must always be able to continue without network access.

The normal flow is:

```text
Welcome
→ target disk
→ input/screen settings
→ Wi-Fi (optional)
→ final confirmation
→ installation
```

## Wi-Fi page behavior

The Wi-Fi page must:

- scan for visible wireless networks when a compatible adapter is available;
- show a bounded list ordered by the platform backend;
- identify approximate signal quality;
- identify whether the network is open, password-protected Personal Wi-Fi, or an unsupported enterprise configuration;
- let the parent select a network;
- accept a masked password for supported Personal Wi-Fi;
- provide Refresh;
- provide an obvious **Skip for now** / continue-offline path;
- keep the graphical installer responsive while scanning, associating, or obtaining network configuration;
- show a clear success or failure state;
- never require Internet reachability in order to install Greia.

If no compatible wireless adapter is available, the installer explains that Wi-Fi can be configured later and continues offline.

## Initial supported authentication

The Phase-0 installation UI supports the common household cases:

- open Wi-Fi;
- WPA/WPA2/WPA3 Personal networks represented by iwd's `psk` network type.

Enterprise / 802.1X Wi-Fi requires materially different identity/certificate/EAP configuration and is not represented as a fake single-password network. The installer identifies it as unsupported during Phase 0 and directs the parent to configure it later through Greia Parents once the typed parent network service supports it.

WEP is not a supported Greia installation configuration.

Hidden-network/manual-SSID support is a follow-up compatibility feature. It must use the same typed Wi-Fi backend and credential rules rather than shelling out to arbitrary network commands.

## Offline-first rule

Wi-Fi configuration is never a prerequisite for:

- validating the installation payload;
- selecting or erasing the target disk;
- copying Greia;
- creating the bootloader;
- completing installation;
- first normal child boot.

A failed scan, unavailable radio, incorrect password, unavailable DHCP service, or unavailable Internet connection must not force the parent to abandon installation. The parent may correct the problem or continue offline.

## Credential handling

Wi-Fi credentials are sensitive parent configuration.

Greia must therefore ensure that:

- the password is visually masked;
- the password is never placed in command-line arguments;
- the password is never written into ordinary installer logs;
- the password is never written into `install-record.json`;
- the password is not included in diagnostics/screenshots as clear text;
- transient UI state clears the password after a successful connection or explicit skip;
- persisted iwd profiles are root-only (`0600`) under a root-only state directory;
- an unsuccessful attempt does not leave a newly created credential profile behind;
- if an existing live profile was temporarily replaced for testing, a failed attempt restores it.

The install record may record only a non-secret fact such as `wifi_configured: true/false`.

## Persistence into the installed system

The live installer tests the selected connection before treating it as configured.

When installation later copies/configures the target, Greia persists the exact successfully tested iwd network profile into the installed system's `/var/lib/iwd` state directory with private permissions. The target then uses its normal platform networking architecture to reconnect after first boot.

The live installer may use a different bounded networking implementation from the installed system when doing so keeps the installer simpler. In the current Phase-0 implementation, live iwd owns temporary DHCP/DNS configuration, while the installed target retains iwd authentication plus systemd-networkd address configuration.

## Hardware/profile rule

A graphical Wi-Fi page is not sufficient evidence of hardware support.

The live installer must contain the same profile-specific kernel and required firmware packages needed to recognize the target machine's wireless hardware. Greia's build-profile resolver applies the selected profile's kernel and `extra_packages` to both target and installer artifacts, so any firmware discovered by physical Acer/Pi acceptance belongs in the hardware profile rather than in a separate installer-only hack.

## Failure and concurrency behavior

Scanning and connection work must not block the Pygame rendering/event loop.

Late results from an abandoned scan or connection attempt must not overwrite a newer parent choice. The Wi-Fi setup controller therefore treats each asynchronous operation as a generation and ignores results from superseded generations.

## Acceptance criteria

For every reference installer family, eventually prove on appropriate physical hardware that:

1. the Wi-Fi page can be skipped and installation completes fully offline;
2. a supported adapter is detected without showing Linux UI;
3. visible networks can be scanned and selected;
4. an open network can be configured;
5. a WPA/WPA2/WPA3 Personal network can be configured with a masked password;
6. a wrong password produces a recoverable error and does not leak the password;
7. successful configuration survives installation and reconnects after first boot;
8. install records/logs/screenshots do not reveal the password;
9. no adapter / radio unavailable remains a nonfatal offline path;
10. enterprise/WEP networks are not misrepresented as supported Personal Wi-Fi;
11. the UI remains responsive during slow scan/DHCP behavior;
12. the live installer has the driver/firmware required by the actual reference wireless adapter;
13. the feature remains usable at 1024×600 and within the Acer resource floor.

Exact physical execution instructions belong in `docs/testing/` and evidence claims belong in `HANDOVER.md`.
