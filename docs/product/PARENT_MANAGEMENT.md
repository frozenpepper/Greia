# Greia Parents — Product and Interaction Requirements

**Status:** accepted product direction; implementation incremental  
**Date:** 2026-08-17  
**Architecture owner:** ADR 0022  
**Initial implementation:** responsive HTML client served by Greia itself

## 1. Product purpose

Greia Parents is the parent-facing management experience for a Greia OS computer.

The first version is intentionally a small local HTML application. This is not a disposable throwaway admin page: it is the first client of the same Greia Parent API that a later iPhone/Android/desktop application would use.

The early web client exists for two reasons:

1. make real parent control useful immediately without requiring an app-store release;
2. force the project to discover and stabilize the correct parent-management capabilities before investing in native applications.

Greia Parents is offline/local-first. A cloud account is not required for core management.

## 2. First connection

### Target experience

A parent should not need to discover IP addresses or Linux hostnames manually.

Normal intended flow:

1. Greia is connected to Ethernet or configured Wi-Fi.
2. The parent chooses **Add a Greia** in a client, or opens the locally advertised Greia Parents page.
3. The client discovers `_greia-parent._tcp` services on the LAN.
4. On the Greia screen, the parent opens **Parent setup → Pair a device**.
5. Greia displays:
   - a QR code containing a short-lived pairing challenge and local connection information;
   - a short numeric fallback code.
6. The parent scans/enters the challenge.
7. Greia shows the requesting device name and asks **Allow this parent device?**
8. The parent explicitly chooses Allow or Deny on Greia.
9. The approved client receives its own revocable credential.
10. Future connections are automatic when the client can find the same Greia.

mDNS is convenience only. Pairing/QR data must allow a client to reach the Greia if multicast discovery is unavailable.

### Prototype allowance

The current shared pairing-token mechanism may be used temporarily to bootstrap the early HTML/API work. It must be visibly treated as provisional and replaced by short-lived, locally confirmed pairing before production release.

## 3. Parent devices

Greia presents paired clients as individual devices, for example:

```text
Paired devices

Dad's browser          paired today
Mum's phone            paired yesterday
Family tablet          paired Sunday

[ Pair another device ]

[ Revoke ]
```

Each device has its own credential.

Revoking one device must not sign every other parent out.

No pairing secret or bearer token is shown in ordinary device lists.

## 4. Primary management areas

### Children

Parents can:

- create child profiles;
- rename profiles;
- choose/change avatar or icon;
- set, replace, or remove the child's simple password;
- choose whether the password is masked while the child types;
- delete an inactive child profile;
- reset child appearance/customization;
- later manage per-child Activity availability and policy.

Child password material is never returned by the API after it is set.

### Activities

Parents can eventually:

- see installed Activities and versions;
- install a `.greiaactivity`;
- update an Activity;
- remove an Activity while preserving child data by default;
- see invalid/incompatible packages clearly;
- later enable/disable Activities for specific children.

The Parent App delegates installation/update/removal to the R10 package-management service. It must not unzip/copy packages itself or run package-manager commands.

The initial API foundation may expose installed Activity inventory while `activities.install` remains unavailable.

### Input and pointing

Parents can control supported semantic settings such as:

- mouse speed;
- touchpad speed;
- tap-to-click;
- natural scrolling;
- later controller mappings/policies where the common input model permits them.

Controls appear only when Greia reports the relevant capability.

### Display

Parents can:

- use automatic/native resolution;
- choose supported resolutions;
- later manage brightness where supported;
- inspect degraded/unavailable display states without seeing Xorg/DRM implementation details.

### Sound

The intended parent surface includes:

- output volume;
- mute;
- selected output when Greia exposes more than one appropriate target;
- microphone/input policy where product requirements need it.

This functionality remains unavailable until the typed Audio Service path exists. The HTML client must not invent ALSA/Pulse/PipeWire shell control.

### Network

The intended parent surface includes:

- current network status;
- Wi-Fi connection management;
- forget/change network;
- hostname/friendly device name where supported;
- diagnostics suitable for a parent.

The API exposes semantic networking, never `iwd` command lines or raw system files.

### System and diagnostics

Parents can inspect:

- Greia OS version;
- uptime/health;
- free disk space;
- memory status where useful;
- installed Activity health;
- update availability later;
- bounded diagnostic/recovery information.

Parents can eventually request safe restart/shutdown/recovery actions through typed services.

### Backup and restore

Portable profile backup/restore is part of the eventual Parent App, backed by `.greiabackup` / R11.

The web client does not implement an independent backup format.

### SSH maintenance

Normal Greia ships with SSH **off**.

A parent can eventually deliberately enable it from Maintenance:

```text
SSH maintenance                  OFF

Allows administrative shell access from another computer on
this local network. Greia Parents does not require SSH.

Authentication
  SSH public key: [ Add / replace key ]

Root login                       Disabled
Password login                   Disabled
Remote user                      greiaadmin

[ Enable SSH ]
```

When disabled, the SSH service is not listening.

When enabled:

- key authentication only;
- no root login;
- no password authentication;
- no generic web-to-shell endpoint;
- host connection details are shown after success;
- parent can disable SSH and revoke/replace key material.

Developer-image remote control remains separate from this release maintenance switch.

## 5. Capability-driven client UI

The Parent API reports semantic capabilities. Clients must use those facts rather than guessing from model/architecture.

Examples:

```text
profiles.manage
activities.read
activities.install
progress.read
settings.input
settings.display
settings.audio
network.manage
backup.manage
maintenance.ssh
paired_devices.manage
```

If a capability is false, the initial HTML interface may show **Not implemented yet** during development. A production client should normally hide or explain unavailable functionality appropriately.

## 6. Common client protocol

The HTML client and future native client share:

- discovery;
- pairing;
- device credentials;
- API versions;
- resource identifiers;
- capability discovery;
- typed errors;
- long-operation status;
- revocation behavior.

A native app must not gain a private SSH path or hidden root endpoint.

## 7. API-first web client rule

The Greia-served HTML application communicates through `/api/v1`.

It must not call Python objects directly, depend on filesystem locations, or encode Linux-specific system commands.

This rule keeps the HTML interface honest: if the browser cannot perform an operation through the public Parent API, a future phone app cannot either.

A legacy server-rendered troubleshooting view may remain temporarily during migration, but it is not the target product contract.

## 8. Privilege and safety

Parent authority is stronger than child authority, but it is still bounded.

The network-facing Parent API remains unprivileged. Root effects go through typed Greia-owned services/brokers with explicit operation schemas.

Never expose:

- arbitrary shell command execution;
- arbitrary `sudo`;
- arbitrary filesystem reads/writes;
- direct package-manager commands;
- raw device access;
- a generic root RPC method.

Destructive or recovery-sensitive operations require explicit confirmation appropriate to their risk.

## 9. Transport security

The early development HTTP endpoint is provisional.

Production paired-device credentials require authenticated encryption. Pairing must bind the client to the intended Greia device rather than trusting a hostname or LAN address alone.

No secret belongs in mDNS TXT records.

## 10. Low-resource behavior

The parent service is present on the low-resource Acer class, so:

- no large web framework is required for the first implementation;
- static HTML/CSS/JavaScript should remain small;
- the server may remain single-request-at-a-time if interaction remains responsive;
- no background polling storm;
- bounded request sizes;
- bounded paired-device count;
- no expensive persistent write on every authenticated request.

Resource behavior must be measured before adding heavyweight dependencies.

## 11. Initial implementation slice

The first API/client slice is considered useful when it can:

- discover/identify the service;
- pair through the current provisional bootstrap;
- use a per-device credential;
- load system status;
- list/create/update/delete child profiles;
- list installed Activities;
- read/update current input/display settings;
- read progress summaries;
- list/revoke paired devices;
- clearly report future capabilities as unavailable.

It does **not** imply that Activity installation, audio/network management, backups, updates, SSH control, or production pairing security are finished.
