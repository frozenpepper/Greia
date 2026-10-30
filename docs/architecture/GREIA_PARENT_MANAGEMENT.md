# Greia Parent Management Architecture

**Status:** living design synthesis subordinate to ADR 0012 and ADR 0022  
**Date:** 2026-08-17  
**Reviewed:** 2026-09-08  
**Implementation phase:** API/client foundation in progress; full privileged management remains R12

## 1. Architectural intent

Greia Parents is a client/server subsystem, not a privileged webpage.

The stable boundary is the Greia Parent API. The dependency-light HTML application and any future native Parent application consume the same semantic protocol.

```text
                    same API contract
        ┌──────────────────┴──────────────────┐
        │                                     │
Greia-served HTML                       native Parent app
        │                                     │
        └───────────────┬─────────────────────┘
                        ▼
                 Greia Parent API
                 (unprivileged)
                        │
       ┌────────────────┼────────────────┐
       ▼                ▼                ▼
 Profile/Progress   HAL/settings    Package/Backup/
 platform services  services        Update services
       │                │                │
       └──────────────┬─┴────────────────┘
                      ▼
          typed privileged broker
            only where required
                      │
                      ▼
               Linux adapters
```

The network API must never become a parallel implementation of profiles, package installation, backup, networking, audio, or update logic.

## 2. Process and authority boundary

`greia-parent.service` runs as `greiapanel` with a strict systemd sandbox. The installed composition is `src/greia_parent/production_api.py`.

The service owns protocol parsing, Parent-device identity, read-only status assembly, calls into existing unprivileged Greia stores/services, static Parent-client serving, and typed requests to future privileged services. It does not own generic root authority.

A capability is true only when the installed process can safely complete the semantic operation under its actual authority. Detecting a lower-level Linux service is not enough.

Future privileged work crosses a narrow semantic broker. Good requests are `enable_ssh(public_key)`, `install_activity(staged_package_handle)`, `set_audio_volume(0.5)`, and `reboot()`. Generic commands, arbitrary argv, client-selected filesystem writes, `sudo`, and raw package-manager calls are rejected boundaries.

## 3. Authentication and Parent-device identity

Greia has two deliberately different credential classes.

### Human bootstrap authority

The canonical Parent password is owned by `MainCredential`. The initial owner-approved credential is `greia` / `greia`, and parents can change it through the Parent management surface.

An unpaired browser submits the password once to:

```text
POST /api/v1/pairing/bootstrap
{
  "password": "<Parent password>",
  "device_name": "<client label>"
}
```

Greia verifies the password locally. The browser does not persist it. Failed attempts are rate-limited per client address with bounded in-memory state.

The main credential store persists only bounded PBKDF2 digest material, uses restrictive file permissions, atomic replacement, and rejects final-path symlink substitution.

### Persistent Parent-device identity

Successful password bootstrap issues a fresh random per-device credential. Normal management requests use:

```text
Authorization: Bearer <device credential>
```

Stored device state contains non-secret metadata plus verifier/hash material rather than the raw issued bearer secret. A credential is returned only when created. Devices can be listed and revoked independently.

This separation keeps the human password out of ordinary API traffic while avoiding one household-wide shared bearer token.

### Retired shared-token model

The old `parent-pairing-token` model is retired from API v1 rather than retained for compatibility there. `ParentApiApplication` owns that rule for every API-v1 composition: its inherited initialization removes stale `parent-pairing-token` state and does not create or retain a shared token. Installed production inherits this API-v1 behavior; it does not carry a separate production-only token-suppression override.

API v1 must not authorize `X-Pip-Token`, token query URLs, shared-token cookies, or any equivalent global fallback, and release images do not install the old token-retrieval helper.

The older `ParentStatusApplication` still owns a compatibility token for the standalone legacy status server only. That legacy server is not an alternate API-v1 authentication model and is not the installed Parent API authority. If the legacy server is removed later, its compatibility token should disappear with it rather than migrate back into API v1.

The API-v1 route name `pairing/bootstrap` remains a wire-compatibility name for enrolling a Parent device. It does not imply that the retired shared token remains valid input.

## 4. Discovery

Greia Parent discovery is convenience, not authorization.

The protocol reserves `_greia-parent._tcp.local` on port 8766 with API metadata and no secret payload. Standalone Parent tooling may also use bounded LAN probing of the public metadata endpoint when multicast discovery is unavailable.

Unauthenticated discovery metadata is intentionally small:

```text
GET /api/v1/meta
```

No Parent password, device credential, child/profile data, machine serial, or other secret belongs in discovery output.

## 5. Protocol layering

The versioned API exposes semantic resources for system/health, profiles, Activities, hardware/settings, progress, Parent devices, and later operations.

After bootstrap the client reads the capability map and renders only supported controls:

```text
client discovers API v1
→ if needed, bootstraps device identity with Parent password
→ authenticates with device bearer credential
→ reads capability map
→ renders only supported controls
```

No architecture/model-specific client branching is required.

## 6. HTML client boundary

The web application is static/dependency-light HTML/CSS/JavaScript. It performs management through `/api/v1` and contains no Linux-specific management implementation.

This remains an architectural test: if a feature cannot be represented cleanly in the Parent API, it is not ready to become a native-app feature either.

The old server-rendered Parent implementation is legacy-only and is not an alternate authentication architecture. It must not expose a shared-token route through the installed production service.

## 7. Long-running operations

Simple profile/settings mutations are synchronous. Operations with meaningful validation, progress, failure, or rollback phases must use explicit operation resources owned by their platform service.

This applies to Activity install/update, backup/restore, OS/runtime update, and other mutations where disconnect/recovery is expected.

## 8. Activity and package boundary

The Parent source lists Activities through the trusted Activity Registry and advertises install/remove only when its real Parent package store is writable and no operator off override is set. New installations and removals hold the shared profile-session lock and require the profile picker, preventing deletion of files under an active Activity. The Shell follows changes to the atomic active-generation pointer on its bounded rescan and rebuilds launch authority before publishing the catalogue.

Package validation and activation remain platform-package responsibilities. The Parent HTTP server does not unpack arbitrary archives directly into the Activity installation root.

## 9. Settings and hardware boundary

The Parent API speaks in semantics such as mouse/touchpad behavior, resolution, volume/mute, and network identity. HAL/platform adapters determine how those settings reach the machine.

Clients do not see `xinput`, `xrandr`, ALSA, iwd, sysfs, or future direct-graphics implementation details.

## 10. SSH boundary

SSH is optional maintenance, not a dependency of Greia Parents. Normal images keep it off unless deliberately enabled through the typed maintenance boundary. Owner decision 2026-10-30 selects `greia` / `greia` for the explicitly enabled service, including normal images. Root login remains disabled. The installed socket-activated `greia-parent-ssh` service accepts only status/enable/disable from the Parent identity; it owns the systemd and account operations. Source implementation requires Linux and physical acceptance.

Greia Parents itself continues to use the Parent API, never SSH.

## 11. Transport security

Owner-approved home-use transport (2026-10-23): the **installed** Greia Parent server now serves HTTPS on LAN port `8766` using a device-generated, persistent self-signed certificate. Direct browsers show the expected self-signed certificate warning, which parents may acknowledge for their own Greia. The on-device Parent panel uses HTTP **only** on `127.0.0.1:8767`; failure to generate/load TLS disables network HTTPS but does not disable local Parent settings. There is no plaintext HTTP fallback on the LAN.

TLS protects traffic from passive observation but a self-signed certificate is not automatically validated against a public CA. This is the explicit owner-accepted practical home-LAN tradeoff. Existing password bootstrap, per-device credentials, revocation, privilege boundaries and capability rules stay unchanged. Do not add QR/Allow challenges, cloud accounts or public PKI as an implicit requirement.

Source implementation and packaging are committed. Exact-head automated, browser, fresh-image and physical hardware acceptance are **not yet recorded as passing**; see `docs/testing/2026-10-23_PARENT_HTTPS_ACCEPTANCE.md`.

## 12. Resource budget

The Parent service runs on the C0 floor. The current architecture therefore favors:

- stdlib bounded HTTP + TLS server composition;
- single-process bounded state;
- bounded JSON requests and credential stores;
- no database solely for authentication;
- no persistent write on every authenticated request;
- bounded rate-limit state;
- small static web client;
- no frontend framework dependency.

These are implementation choices, not excuses to weaken the protocol or security boundaries.

## 13. Current foundation and remaining closure

Implemented/source-owned foundation includes:

```text
protocol constants/resource index
canonical Parent password authority
password bootstrap -> per-device credential
independent Parent-device revocation
bounded failed-password limiter
API-v1-owned legacy shared-token rejection/removal
legacy standalone status token isolated to its compatibility server
API-v1 facade over profile/hardware/package/update/settings services
explicit installed production composition with fail-closed capabilities
real-IWD backend with management advertised only when usable
bounded Activity package path behind capability policy
SSH maintenance API surface through platform service boundaries
Activity inventory
Parent HTML API client
standalone bounded LAN discovery/proxy tooling
exact Parent runtime revision/integrity pin in Greia
vendored runtime and image overlay synchronized to the accepted Parent revision
installed-runtime integrity preflight
```

Current integrated Parent client revision:

```text
frozenpepper/Greia-Parent-App-Html
5518a9eed8ba61503249a1c827b7ef4fef5dab36
```

Still required before ordinary-family Parent authentication is release-complete:

```text
exact-head local automated verification across Greia + Parent client
physical discovery -> password bootstrap -> reconnect -> password-change -> revoke -> rebootstrap test
upgrade proof that obsolete token helper/state are absent and not recreated
source HTTPS + persistent device certificate (physical acceptance pending)
remaining typed privileged broker work for operations requiring root authority
full package/update/backup/network release acceptance owned by their phases
resource measurements on the C0 floor
```

The shared-token initialization ownership debt is closed at the source boundary: API v1 owns retirement, production inherits it, and the legacy standalone server retains compatibility behavior only within its own class. The API-v1 and legacy sides have dedicated regression tests, but those tests still require exact-head local execution before this descendant can claim a source PASS.

This foundation does not falsely close R12 or any later platform/release obligation.

## 14. Client-facing catalogue and identity fields (2026-10-16)

- `GET /api/v1/activities` entries carry `titles`: `{locale: display title}` for
  every language the Activity declares, read through `LocalizationBundle` from
  the same `locales/<locale>.json` the child Shell uses (`activity.title`, else
  the manifest `title_key` string). Clients choose a locale and fall back to
  their own humanised id when a title is missing. Owner:
  `greia_platform.localization.activity_titles`.
- `GET /api/v1/system` carries `os`: `{version, profile, platform_family,
  architecture, build_phase}` from `/etc/greia-os/build-info` and
  `image-profile.json`, so Parent clients can compare the installed release
  with a published update channel. Owner: `greia_platform.health.installed_os_identity`.
- Activity discovery memoises tree validation and package digests per package
  stat fingerprint (`ActivityRegistry._validated_tree_digest`); on the Atom
  reference floor the Parent catalogue calls dropped from ~20 s to ~0.65 s.
