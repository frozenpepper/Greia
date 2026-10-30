# Greia Parent App HTML — Architecture

**Status:** current management-app architecture  
**Date:** 2026-09-02

## 1. Purpose

This repository is the canonical browser-based Greia Parent application used from a parent computer, phone, or tablet. Greia OS serves the reviewed static client and owns the API, authorization, privileged services, package management, image integration, and security decisions.

The stable dependency direction is:

```text
Views / interaction controller
          ↓
     ParentAppState
          ↓
 Parent API client contract
      ├── HTTP implementation
      └── test-only implementation (tests/support; never served)
          ↓
      Greia /api/v1
```

The browser never talks directly to Linux services or host filesystem paths.

## 2. Runtime model

The client deliberately remains build-light and dependency-free at runtime:

- semantic HTML;
- CSS;
- native ES modules;
- native Fetch API;
- no framework runtime;
- no remote JavaScript, fonts, icons, trackers, or CDN assets;
- no background polling loop by default.

This keeps the client cheap to serve from low-resource Greia hardware while remaining straightforward to audit.

## 3. Main components

### `ParentApiClient`

Owns same-origin API-v1 URL construction, bearer authentication, JSON/raw package transport, typed errors, and semantic Parent operations. It validates browser-supported system-control mutations and does not own DOM state.

### `BrowserCredentialStore`

Owns provisional per-origin browser credential persistence. It does not know API semantics.

### `ParentAppState`

Owns the coherent server snapshot and publish/subscribe boundary used by rendering. Capability discovery remains authoritative; unsupported features are not emulated in the browser. System output controls are loaded only when `settings.system_controls` is advertised.

### `GreiaParentApp`

Owns navigation, confirmation flows, shell rendering, dialogs, and view orchestration. View handlers call state/API objects rather than issuing arbitrary HTTP requests.

### Device view composition

`src/views_device.js` owns the established device cards and shared range-field helpers. `src/views_system_controls.js` owns only the speaker volume/mute card. `src/views_device_layout.js` composes it into the `Input, display & sound` group.

This separation is intentional: output volume, microphone processing, pointer/display preferences, and platform brightness are distinct domains.

### Test fixtures

Fake APIs exist only under `tests/support/` for local unit tests. Production has
no demo mode. Browser review uses host-side real-device discovery and normal
per-device pairing, as specified by `AGENTS.md`.

## 4. Product information architecture

The current Parent app has four parent jobs:

```text
Home
Children
Activities
This Greia
```

Desktop uses a persistent left management rail and focused workspace. Narrow/mobile layouts use a compact bottom navigation.

### Home

Operational summary for the selected child, recent use, Activity counts, rewards, and concise device state.

### Children

Profile management, including create/edit/delete, avatar, approximate-age guidance, challenge preference, child password controls, Activity-time limits, Activity shortcut, and capability-gated Style & wording presentation.

### Activities

Installed-Activity management rather than a dashboard card wall:

- search and Create / Play / Learn / Explore filters;
- built-in versus Parent-installed origin;
- per-child effective visibility and overrides;
- age and difficulty discovery policy;
- `.greiaactivity` installation when advertised;
- removal of Parent-installed packages when advertised;
- built-in Activities remain non-removable;
- Greia remains authoritative for package validation and trust.

### This Greia

Settings are grouped semantically rather than presented as an unrelated card mosaic:

```text
System
Network & language
Input, display & sound
Security & access
```

The typed Wi-Fi, language, hardware, speaker output, microphone, Parent password, SSH, paired-device, and system-update controls live within those groups.

The speaker-output card is capability-gated by `settings.system_controls` and exposes only:

```text
speaker volume 0..100%
mute on/off
```

Brightness is intentionally not a Parent browser control in this tranche. The Greia platform may expose current brightness in the read model for coherence with hardware keys, but browser mutations remain limited to volume/mute.

## 5. Shared state and hardware-key coexistence

Physical Greia volume keys and the Parent browser operate on the same platform-owned state. A Parent form may therefore become stale while it is open.

The browser mitigates this by sending **partial mutations only for fields the parent actually changed**. Changing only mute sends only `muted`; changing only volume sends only `volume_percent`. This prevents a stale untouched value from rolling back a more recent hardware-key change.

The no-change submit path performs a one-shot refresh inside the same guarded async error boundary as actual mutations, so a temporary API failure cannot escape as an unhandled event rejection.

The browser is not the source of truth for hardware application and does not poll continuously. After a successful mutation it refreshes the system-control resource once.

## 6. Pairing and security boundary

Normal startup reads public metadata and then attempts authenticated API discovery. A `pairing_required` response enters the pairing screen.

The current LAN HTTP/bootstrap credential flow remains development/provisional infrastructure. Production pairing and encrypted transport are Greia OS responsibilities and can change without changing this client’s authority boundary.

## 7. Activity package boundary

The normal Parent file picker accepts the Greia Activity product format:

```text
.greiaactivity
application/vnd.greia.activity+zip
```

Filename/MIME are UX routing hints only. Greia validates the archive, manifest, trust source, collisions, and activation. Removal deletes only Parent-installed package code; profile-scoped child saves/progress remain outside that package transaction.

## 8. Release integration

This directory is the canonical, only editable source of the browser client in
the Greia repository. The installed image ships a frozen, integrity-checked copy
of the runtime closure (`build/overlay/usr/share/greia-parent-app/`), pinned by
`runtime/parent-app-client.toml` and `runtime/parent-app-client.manifest.json`.
The pin `revision` is the Git tree id of the committed `parent-app/` directory;
`python3 tools/update_parent_client_pin.py` (repository root) regenerates the
pin, manifest and overlay from that committed tree. Do not advance the pin until
the browser source passes `node --test tests/*.test.js` plus
desktop/1024x600/mobile review against a real Greia through normal pairing.

## 9. Parent visual system — 2026-09-08

The owner-selected direction is colourful and playful. `styles/app.css` owns
shared tokens, the blue navigation rail, cream workspace, peach profile header,
lilac/blue/yellow summary metrics, child cards, Activity rows, fields, dialogs,
connection screens, keyboard focus and responsive bottom navigation.
`styles/management.css` owns device settings groups and their responsive cards.
System fonts, the existing inline SVG icon vocabulary and one local OS artwork
keep the runtime dependency-free. No background animation or polling was added.

Home's profile header and summary metrics are separate semantic sections.
Children use a two-column card collection on wide screens and a single column
below 1150px. Activity filters expose pressed state; settings remain grouped by
existing API domains. Native fields have programmatically associated labels.
Mobile navigation and sticky save controls reserve separate bottom space.

`assets/greia-constellation.png` is the unchanged owner-selected OS frame; see
`assets/README.md` for provenance and the runtime-manifest integration boundary.
These Parent changes do not advance the OS runtime pin or constitute device
acceptance. Authenticated browser review is still required before integration.
