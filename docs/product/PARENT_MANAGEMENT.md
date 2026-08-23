# Greia Parents — Product and Interaction Requirements

**Status:** accepted product direction; core local Parent API/client implementation active, with production pairing/security and some management domains still incremental  
**Date:** 2026-08-23  
**Architecture owner:** ADR 0022; microphone-processing extension ADR 0031  
**Initial implementation:** responsive HTML client served by Greia itself  
**Related child discovery policy:** `docs/product/CHILD_ACTIVITY_DISCOVERY_AND_AUDIENCE.md`

> **2026-08-18 owner policy amendment (active):** the main Parent/admin
> credential is intentionally simple and predictable. The initial login is
> `greia` / `greia`. It is stored only as a bounded password digest, is
> changeable from Greia Parents through a typed operation, and is never returned
> by any API or log. During active development, developer/test installations
> stay reachable over SSH as `greia` / `greia` (see `docs/agents/GREIA_AGENT_OPERATIONS.md`);
> root SSH login remains disabled and child-facing operation still exposes no
> shell or desktop. Old repository text describing a generated random end-install
> recovery password/code is obsolete and must not be revived.

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

### Current prototype boundary

The shared pairing-token/bootstrap mechanism is still provisional. Per-device credentials and revocation exist, but the release pairing flow above still requires short-lived challenges, device-local Allow/Deny and authenticated encrypted transport before production acceptance.

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

Each device has its own credential. Revoking one device must not sign every other parent out. No pairing secret or bearer token is shown in ordinary device lists.

The current Parent API and rebuilt HTML client list and revoke individual paired devices.

## 4. Primary management areas

### Main Parent password

The main Parent/admin credential is the human-readable Greia management login:

```text
username = greia
password = greia     (initial, changeable from Greia Parents)
```

Requirements:

- only a bounded PBKDF2 digest is persisted; no plaintext password file;
- changing it is a typed Greia-owned operation that requires the current password;
- API responses never return the stored password or its digest;
- Greia Parents exposes a clear **Change Parent password** control;
- the main Parent password is distinct from per-device bearer credentials used by paired parent clients;
- during active development/test, the main Parent password intentionally owns the development SSH login on developer images; root SSH login stays disabled.

### Children

Parents can currently:

- create child profiles;
- rename profiles;
- choose/change avatar or icon;
- set, replace, or remove the child's simple password;
- choose whether the password is masked while the child types;
- delete an inactive child profile;
- provide an optional **coarse/approximate age** from 1 through 18 for Activity discovery without supplying a date of birth;
- choose a discovery/challenge preference: **Automatic**, **Easier**, **Standard**, or **More challenging**;
- manage per-child Activity visibility policy and individual Activity overrides through the Parent API/client.

Child password material is never returned by the API after it is set.

Approximate age exists only to support appropriate Activity discovery/presentation and Parent policy. Greia does not require a date of birth merely to decide which educational Activities to emphasize.

Appearance/customization reset remains a separate Greia-owned operation and must not be conflated with profile identity or Activity policy.

### Activities

Parents can currently:

- see installed Activities and their declared metadata;
- inspect baseline challenge/difficulty and optional recommended age range;
- inspect adaptive-difficulty declarations where present;
- select one child and configure a default visibility policy;
- override an individual Activity as **Always show** or **Always hide** for that child;
- install a `.greiaactivity` only when the Greia API advertises `activities.install`.

Still incremental/future package-management work includes explicit Activity update/remove product flows and the complete R10 lifecycle. The Parent App delegates package mutation to the Greia package-management service; it must not unzip/copy packages itself or run package-manager commands.

Ordinary/release images currently keep `activities.install` unavailable while the Parent transport remains provisional HTTP. Developer/owner-enabled environments may advertise it through the typed capability.

### Per-child Activity discovery and visibility

The authoritative child discovery contract lives in `docs/product/CHILD_ACTIVITY_DISCOVERY_AND_AUDIENCE.md`.

The implemented Parent policy modes are:

```text
Show everything
Hide Activities probably too simple
Show recommended range only
Custom
```

with explicit Activity overrides:

```text
Always show this Activity to this child
Always hide this Activity from this child
```

Rules:

- an explicit per-Activity Parent override wins over automatic age/difficulty recommendation;
- age/developmental suitability and Activity difficulty are separate metadata dimensions;
- missing age metadata does not automatically hide an otherwise valid Activity;
- an open-ended creative Activity may legitimately have no upper age bound;
- Parent visibility changes affect the child's **effective catalogue projection**, not package installation/trust/permissions/saves;
- adaptive launcher depth is computed from the effective visible Activity set after Parent policy, not raw installed count;
- Activity code cannot grant itself visibility or hide competing Activities;
- filtering language remains neutral and child-positive rather than describing a child as behind, too young, too old or incapable.

Current source/API/client implementation includes profile age/challenge fields, per-profile discovery policy persistence, effective-catalogue computation, Parent policy endpoints and the integrated HTML controls. This is no longer a future-only contract.

### Input, microphone and pointing

Parents can control supported semantic hardware settings such as:

- mouse speed;
- touchpad speed;
- tap-to-click;
- natural scrolling;
- microphone input gain when the current hardware payload exposes `desired.mic_gain`;
- platform-owned microphone cleanup when `settings.audio` is advertised;
- later controller mappings/policies where the common input model permits them.

Current microphone gain remains owned by the typed hardware settings service for compatibility:

```text
minimum 0.5× / 50%
default 2.0× / 200%
maximum 4.0× / 400%
```

Microphone **processing** is now owned separately by the typed Audio Service defined in ADR 0031. Its product defaults are:

```text
Improve microphone sound = ON
Enhanced noise reduction = OFF
```

The normal path is deliberately the cheapest useful processor. Greia does not benchmark hardware or silently promote to advanced processing. A parent may turn processing off, and the stronger option appears only when the platform reports a real advanced endpoint.

The network Parent client exposes these controls through `/api/v1/settings/audio`. The exact Acer processor remains subject to the physical acceptance protocol in `docs/testing/2026-08-23_ACER_MICROPHONE_PROCESSING_ACCEPTANCE.md`; until an endpoint is truly ready the service reports fallback rather than pretending cleanup is active.

Controls appear only when Greia reports the relevant capability/data contract.

### Display

Parents can:

- use automatic/native resolution;
- choose supported resolutions;
- inspect degraded/unavailable display states without seeing Xorg/DRM implementation details.

Brightness remains future work where supported by a typed platform path.

### Sound

The implemented Audio Service currently owns the bounded **microphone-processing** surface, not general speaker administration.

Current Parent microphone controls are:

- improve microphone sound (lightweight desired default);
- disable microphone processing for raw capture/troubleshooting;
- enhanced noise reduction only when the OS advertises a proven advanced endpoint;
- effective/fallback status.

Broader intended parent audio controls remain future work:

- output volume;
- mute;
- selected output when Greia exposes more than one appropriate target.

`settings.audio` is therefore true in the concrete audio-aware Parent composition, but clients must not infer that every possible audio control exists. The resource schema defines the currently supported microphone fields.

The existing **microphone input gain** remains a narrower hardware setting. Neither the HTML client nor an Activity may invent shell-based ALSA/Pulse/PipeWire control.

### Network

Current typed Parent networking includes:

- Wi-Fi scan/status;
- Wi-Fi connection management;
- parent-suitable connection errors.

Future extensions may include forget/change-network UX, friendly device naming and richer bounded diagnostics. The API exposes semantic networking, never `iwd` command lines or raw system files.

### System and diagnostics

Parents can inspect current bounded health information including uptime, free storage, memory state and update status where the typed service advertises it.

Future product work includes broader safe restart/shutdown/recovery operations through typed services. Raw system administration is never the Parent API contract.

### Backup and restore

Portable profile backup/restore is part of the eventual Parent App, backed by `.greiabackup` / R11. The web client does not implement an independent backup format.

### SSH maintenance

Normal Greia ships with SSH **off**.

Current Parent surfaces can deliberately enable/disable SSH maintenance through the typed service. When enabled:

- the managed `greia` account is the administrative shell user;
- root login is disabled;
- a public key may be added as an additional automation path;
- passwordless privilege escalation stays behind bounded Greia-owned controls, not generic passwordless sudo/root APIs;
- host connection details may be shown after success;
- the parent can disable SSH and revoke/replace key material through supported typed operations.

During active development, developer/test images additionally provision the `greia` / `greia` login as described in `docs/agents/GREIA_AGENT_OPERATIONS.md` so the owner-controlled test agent can continue working after install and reboot. This development convenience is not a release security claim.

Developer-image remote control remains separate from this release maintenance switch.

## 5. Capability-driven client UI

The Parent API reports semantic capabilities. Clients use those facts rather than guessing from model/architecture.

Current examples include:

```text
profiles.manage
activities.read
activities.policy
activities.install
progress.read
settings.input
settings.display
settings.language
settings.audio
network.manage
maintenance.ssh
paired_devices.manage
parent.password
system.update.read
system.update.upload
system.update.activate
backup.manage
```

Per-child discovery policy is exposed through typed profile Activity-policy resources; clients do not infer support from manifest versions.

If a capability is false, production-oriented client behavior is to omit or clearly explain the unavailable control rather than build a dashboard of engineering backlog states.

For `settings.audio`, the resource remains capability/data driven inside the surface as well: `available.advanced = false` means the enhanced-processing control is omitted.

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

This keeps the HTML interface honest: if the browser cannot perform an operation through the public Parent API, a future phone app cannot either.

A legacy server-rendered troubleshooting view may remain temporarily during migration, but it is not the target product contract.

The separately maintained HTML client is source-pinned by Greia through:

```text
runtime/parent-app-client.toml
runtime/parent-app-client.manifest.json
```

The current pin is an integrity-checked build input and is still marked `source-pinned-not-yet-vendored`; runtime JavaScript must never be fetched from moving repository `main`.

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
- static HTML/CSS/JavaScript remains small;
- the server may remain single-request-at-a-time if interaction remains responsive;
- no background polling storm;
- bounded request sizes;
- bounded paired-device count;
- no expensive persistent write on every authenticated request.

The microphone-processing policy follows the same rule: lightweight is deterministic/default, advanced is explicit and optional, and no background benchmarking loop exists.

Resource behavior must be measured before adding heavyweight dependencies. Follow `docs/engineering/GREIA_PERFORMANCE_BEST_PRACTICES.md` for measured performance work.

## 11. Current implementation slice

The current local Parent foundation can:

- identify the service and expose API metadata;
- pair through the current provisional bootstrap and use per-device credentials;
- load system status;
- list/create/update/delete child profiles;
- persist optional approximate age and challenge preference;
- list installed Activities and audience/challenge metadata;
- read/update per-child Activity visibility policy and explicit overrides;
- read/update input/display hardware settings, including microphone gain where present;
- read/update/reset typed microphone-processing preferences and report effective/available mode;
- read progress summaries;
- read/change Greia language;
- scan/connect Wi-Fi;
- enable/disable SSH maintenance;
- change the main Parent password;
- list/revoke paired devices;
- read system-update status and upload only when capability permits;
- install Activity packages only when capability permits.

The separately maintained HTML client source includes the capability-gated microphone cleanup controls. The exact Greia pin/integrity manifest must always point to the reviewed Parent revision used in a build; see the physical acceptance runbook for repin verification.

This does **not** imply that production pairing/encryption, general speaker/output audio management, backups, complete Activity update/removal lifecycle, production system-update activation, or all future native-client UX is finished. It also does not claim that the Acer lightweight DSP backend is physically proven before its dedicated hardware protocol passes.

## 12. On-Device Parent Mode & Key Chord

Greia physical devices provide an on-device Parent Settings Panel directly on the machine's display:

- **Hidden activation gesture:** Holding keys `s` and `t` simultaneously for 5.0 seconds on the initial user selection screen (`_mode == "profiles"`).
- **Accidental-activation resistance:** If either key is released before 5.0 seconds have elapsed, the hold timer resets immediately without disturbing ordinary child navigation.
- **Parent authentication gate:** Opening the panel requires entering the main Parent password (`greia` by default, validated via `MainCredentialStore`).
- **On-device capabilities:**
  1. **Language:** choose the Greia system language through the typed language service.
  2. **Audio & Mic:** inspect and adjust the bounded microphone input gain through `HardwareSettingsStore`. Microphone-processing mode is currently managed through the typed Parent API/HTML client; an on-device presentation may be added later without changing the Audio Service contract.
  3. **Wi-Fi Manager:** scan nearby SSIDs, select a network, enter a passphrase with on-screen masking, and connect via the platform Wi-Fi service.
  4. **SSH Maintenance Switch:** on-demand toggle to enable or disable SSH with connection guidance.
  5. **Remote Companion Diagnostics:** display device LAN IP, mDNS status, and instructions for connecting via browser at `http://<ip>:8766` during the provisional HTTP phase.

The on-device panel and network client are two presentations over Greia-owned typed services; neither is allowed to become a parallel Linux administration surface.
