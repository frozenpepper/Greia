# Greia Parents — Product and Interaction Requirements

**Status:** accepted product direction; core local Parent API/client authentication implemented, with self-signed HTTPS source integration and some management domains still incremental  
**Date:** 2026-08-23  
**Authentication review:** 2026-09-08  
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

## 1A. Parent entry on the child's profile-selection screen (release UX requirement)

Greia's **profile-selection screen** is also the on-device entry to Parent settings. The implemented shortcut is **hold the physical S and T keys together for five continuous seconds**. It works only while profiles are being selected, opens the on-device password-protected Parents panel, and is unrelated to a child's optional profile password. The Parent credential remains authoritative.

For an ordinary-family release, the screen must be **immediately understandable**: the child's picture/name choices are large and obvious, and a small but legible adult-facing hint explains the actual shortcut without cluttering or frightening the child. An example meaning is *“For parents: hold S + T for 5 seconds.”* The hint must be translated through the supported EN/IT/ES/FR localization system and legible at the low-resource 1024×600 and 800×480 targets; do not add a second secret gesture, a Linux login or a visible control that bypasses the Parent password.

A family must also be able to return to profile selection from the child's Home/profile switcher and understand the difference between on-device settings and the browser Parents App. Do not treat documentation of an invisible shortcut as a substitute for reviewing the **actual rendered and physically operated** screen. This is an accepted product/UI requirement; the source shortcut exists, while discoverability and exact-rendered-device acceptance remain open until tested.

## 2. First connection and authentication

A parent should not need to discover IP addresses, Linux hostnames, filesystem secrets, pairing tokens, or shell commands manually.

The accepted normal flow is:

1. Greia is connected to Ethernet or configured Wi-Fi.
2. The parent chooses a Greia in a Parent client, or opens the Greia-served Parent page.
3. The client discovers Greia Parent API endpoints on the local network. Discovery is convenience only and grants no authority.
4. If the browser already has a valid credential for that Greia, it reconnects automatically.
5. Otherwise the client asks for the **Greia Parent password**. New systems start with `greia`; parents may change it from Greia Parents.
6. The client submits only the password and a friendly client/device label to the API-v1 bootstrap resource. It does not persist the password.
7. Greia verifies the password through the canonical `MainCredential` authority and issues a fresh high-entropy per-device credential.
8. The browser persists only that Greia-scoped device credential and uses it for normal management requests.
9. Future connections are automatic while that device credential remains valid; parents can revoke clients independently.

The established API-v1 wire path remains:

```text
POST /api/v1/pairing/bootstrap
{
  "password": "<Parent password>",
  "device_name": "<client label>"
}
```

The word `pairing` in this versioned wire path means creation of a paired device identity. It does **not** mean a separate pairing-token secret exists. The retired `parent-pairing-token`, token query URLs, shared-token cookies, `X-Pip-Token`, QR/PIN challenge ceremony and shell token-retrieval helper are not part of the accepted ordinary Parent authentication flow and must not be revived as compatibility mechanisms.

mDNS or bounded LAN probing may help find Greia, but discovery data contains no secret and does not authorize management.

### Release security boundary

Owner-approved network transport is now HTTPS with a persistent Greia-generated self-signed certificate. Browser users accept a first-visit trust warning for their own local Greia; this does not supply public-CA endpoint authentication. Unencrypted HTTP is available only to the built-in panel over loopback. Physical browser and image acceptance remain open.

That transport work must preserve the simple Parent-password experience. It must not add a second human secret, hidden filesystem token, mandatory QR/PIN/Allow ritual, or Linux-administration ceremony merely to compensate for transport design.

## 3. Parent devices

Greia presents authenticated clients as individual devices, for example:

```text
Parent devices

Dad's browser          connected today
Mum's phone            connected yesterday
Family tablet          connected Sunday

[ Connect another device ]

[ Revoke ]
```

Each device has its own credential. Revoking one device must not sign every other parent out. No Parent password, pairing secret, or bearer token is shown in ordinary device lists.

The current Parent API and rebuilt HTML client list and revoke individual Parent devices.

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
- the main Parent password is distinct from per-device bearer credentials used by authenticated Parent clients;
- the password is used to bootstrap a device identity, not as the bearer credential for every management request;
- repeated failed password authentication is bounded/rate-limited;
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

Owner direction 2026-10-30 enables new Activity package installation when the Parent-owned package store is writable; an explicit operator off override is supported. Install and removal require Greia to be at the profile picker. Package validation, separate Parent trust and child-save preservation remain mandatory. Source and local HTTP coverage exist; installed Linux and physical acceptance remain pending.

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

The implemented Audio Service currently owns the bounded **microphone-processing** surface, while the shared system-controls service owns currently supported speaker volume/mute state.

Current Parent microphone controls are:

- improve microphone sound (lightweight desired default);
- disable microphone processing for raw capture/troubleshooting;
- enhanced noise reduction only when the OS advertises a proven advanced endpoint;
- effective/fallback status.

Current Parent speaker controls, when the system-controls capability is advertised, include:

- output volume;
- mute.

Selected-output management remains future work if Greia exposes more than one appropriate target.

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
- owner decision 2026-10-30: explicitly enabling the Parent switch permits the simple `greia` / `greia` login on normal images;
- passwordless privilege escalation stays behind bounded Greia-owned controls, not generic passwordless sudo/root APIs;
- host connection details may be shown after success;
- the parent can disable SSH through the same switch.

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
settings.system_controls
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

The HTML client and future native clients share:

- discovery;
- Parent-password authentication;
- per-device credentials;
- API versions;
- resource identifiers;
- capability discovery;
- typed errors;
- long-operation status;
- revocation behavior.

A native app must not gain a private SSH path, hidden root endpoint, or alternate token credential.

## 7. API-first web client rule

The Greia-served HTML application communicates through `/api/v1`.

It must not call Python objects directly, depend on filesystem locations, or encode Linux-specific system commands.

This keeps the HTML interface honest: if the browser cannot perform an operation through the public Parent API, a future phone app cannot either.

A legacy server-rendered troubleshooting view may remain temporarily during migration, but it is not the target product contract and must not restore legacy shared-token authorization through the installed production service.

The HTML client source lives in this repository under `parent-app/` and is pinned for the image by Greia through:

```text
runtime/parent-app-client.toml
runtime/parent-app-client.manifest.json
```

The production browser runtime is frozen into the image overlay by `tools/update_parent_client_pin.py` from the committed `parent-app/` and integrity checked against the exact pin. Runtime JavaScript/assets must never be fetched from a network or served from the editable source tree. The runtime manifest must describe the actual transitive browser dependency closure rather than rely on a hand-maintained file list.

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

Network Greia Parents runs on HTTPS port 8766 using a self-signed on-device certificate. First-time browser warnings are expected; the parent proceeds only for their own Greia. The built-in panel uses HTTP bound to 127.0.0.1:8767.

Parent-password authentication and per-device bearer credentials require authenticated encryption for ordinary-family release. The transport must bind the client to the intended Greia device rather than trusting a hostname or LAN address alone.

No secret belongs in mDNS TXT records. Transport closure must not reintroduce a hidden shared pairing token or second human secret.

## 10. Low-resource behavior

The parent service is present on the low-resource Acer class, so:

- no large web framework is required for the first implementation;
- static HTML/CSS/JavaScript remains small;
- the server may remain single-request-at-a-time if interaction remains responsive;
- no background polling storm;
- bounded request sizes;
- bounded Parent-device count;
- bounded failed-password tracking;
- no expensive persistent write on every authenticated request.

The microphone-processing policy follows the same rule: lightweight is deterministic/default, advanced is explicit and optional, and no background benchmarking loop exists.

Resource behavior must be measured before adding heavyweight dependencies. Follow `docs/engineering/GREIA_PERFORMANCE_BEST_PRACTICES.md` for measured performance work.

## 11. Current implementation slice

The current local Parent foundation can:

- identify the service and expose API metadata;
- authenticate a new Parent client with the Greia Parent password and issue a per-device credential;
- reconnect with and independently revoke per-device credentials;
- reject the retired shared-token authorization model in installed production composition;
- load system status;
- list/create/update/delete child profiles;
- persist optional approximate age and challenge preference;
- list installed Activities and audience/challenge metadata;
- read/update per-child Activity visibility policy and explicit overrides;
- read/update input/display hardware settings, including microphone gain where present;
- read/update/reset typed microphone-processing preferences and report effective/available mode;
- read/update speaker volume/mute through shared system controls where advertised;
- read progress summaries;
- read/change Greia language;
- scan/connect Wi-Fi when the installed service can actually complete the operation;
- enable/disable SSH maintenance;
- change the main Parent password;
- list/revoke Parent devices;
- read system-update status and upload only when capability permits;
- install/remove Activity packages only when capability permits.

The HTML client (`parent-app/`) is frozen as an exact integrity-checked Greia runtime input. The Greia pin/integrity manifest and image overlay must always correspond to the committed `parent-app/` used in a build (`python3 tools/update_parent_client_pin.py --check`).

This does **not** mean that the new HTTPS implementation has passed physical/browser acceptance, or that backups, complete Activity update lifecycle, production system-update activation, every privileged network/package operation, or all future native-client UX are finished. It also does not claim that hardware-specific behavior is physically proven before its dedicated acceptance protocol passes.

## 12. On-Device Parent Mode & Key Chord

Greia physical devices provide an on-device Parent Settings Panel directly on the machine's display:

- **Hidden activation gesture:** Holding keys `s` and `t` simultaneously for 5.0 seconds on the initial user selection screen (`_mode == "profiles"`).
- **Accidental-activation resistance:** If either key is released before 5.0 seconds have elapsed, the hold timer resets immediately without disturbing ordinary child navigation.
- **Parent authentication gate:** Opening the panel requires entering the main Parent password (`greia` by default). The password is checked by the Parent service (`ParentCredentialClient.authenticate`, rate limited); the panel never reads the credential. A wrong password reads "Incorrect password", a spent attempt budget "Too many attempts", and only an unreachable service "Cannot check the password right now". Access is refused in every non-success case.
- **On-device capabilities** (a section rail on the left; every privileged write goes through the Parent service):
  1. **Language:** choose the Greia device language (each language under its own name) through the typed language service; offers exactly the languages in `SUPPORTED_SYSTEM_LANGUAGES`.
  2. **Audio & Mic:** live microphone input meter, noise cancelling (standard filter / advanced reduction when available) and the bounded microphone gain (presets flanked by −25%/+25% steps).
  3. **Kids:** add, rename and remove child accounts (removal needs the explicit red confirmation; paged when more children exist than fit).
  4. **Password:** change the Parent password.
  5. **Wi-Fi:** scan nearby SSIDs, select a network, enter a passphrase with on-screen masking, and connect via the platform Wi-Fi service.
  6. **SSH:** on-demand maintenance switch with connection guidance and the security warning first.
  7. **Remote access:** device LAN IP, mDNS service and instructions for the browser client at `https://<ip>:8766` (first-visit self-signed certificate warning expected).
  8. **Pointer:** touchpad/mouse speed presets, tap-to-click, natural scrolling, off-while-typing, reset and a test area.
- **Keyboard and controller:** Tab moves to the next section (walking a form's fields first); arrows and Enter/Space act inside the current section; Backspace edits the focused field; Esc (controller cancel) leaves an open form or confirmation first and otherwise closes the panel. Focus rings appear only after keyboard/controller input. The Shell maps controllers to arrows/activate/cancel only, so a controller cannot change section yet.
- **Layout evidence:** `tools/panel_screenshots.py` renders every section and state at 1024×600 and 800×480 in EN/IT/ES/FR and reports overlapping or clipped controls; `tests/test_parent_panel_polish.py` repeats the 800×480 check in the suite.

The on-device panel and network client are two presentations over Greia-owned typed services; neither is allowed to become a parallel Linux administration surface.
