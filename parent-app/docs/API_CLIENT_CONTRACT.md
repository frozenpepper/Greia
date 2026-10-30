# API v1 client contract

The server implementation and ADRs in `frozenpepper/Greia` are normative. This document records what this browser client consumes.

Base path:

```text
/api/v1
```

Public discovery:

```text
GET /api/v1/meta
```

Authenticated foundation resources include:

```text
GET    /api/v1
GET    /api/v1/system
GET    /api/v1/profiles
POST   /api/v1/profiles
PATCH  /api/v1/profiles/{id}
DELETE /api/v1/profiles/{id}
GET    /api/v1/activities
GET    /api/v1/settings/hardware
PUT    /api/v1/settings/hardware
POST   /api/v1/settings/hardware/reset
GET    /api/v1/settings/system-controls
PUT    /api/v1/settings/system-controls
GET    /api/v1/progress?profile_id={id}
GET    /api/v1/devices
DELETE /api/v1/devices/{id}
GET    /api/v1/system/update
POST   /api/v1/system/update/check
POST   /api/v1/system/update/prepare
POST   /api/v1/system/update/restart
```

## Device-owned Greia OS updates

The API index capabilities and `GET /api/v1/system/update` availability fields
remain authoritative. Online delivery uses only the device-owned operations:

```json
POST /api/v1/system/update/check    {}
POST /api/v1/system/update/prepare  {"release_id":"<release returned by Greia>"}
POST /api/v1/system/update/restart  {}
```

Each accepted operation returns `202 {"job": ...}`. The browser re-reads the
cached status and polls only while the persisted job is active. Progress and
terminal failure/rollback states come from `delivery.job`; readiness and the
device-filtered release choices come from `delivery.readiness` and
`delivery.catalog`. The browser never submits an artifact URL or downloads the
OS bundle. Restart is a separate, explicit Parent action shown only when the
device advertises `system.update.restart` and reports `restart_available`.
Single-root devices remain unavailable when Greia reports update readiness as
false; the client displays the server's activation reason. Manual bundle upload
continues to use the existing developer-only upload capability and route.

## Parent-password authentication

A browser that does not yet hold a device credential authenticates with the Parent password configured on that Greia:

```text
POST /api/v1/pairing/bootstrap
```

```json
{
  "password": "<parent password>",
  "device_name": "Parent phone"
}
```

`/pairing/bootstrap` is the established API-v1 wire name for creating a paired device identity. It does **not** mean that a separate pairing token still exists. The only human credential accepted by this endpoint is the Greia Parent password.

The password is used only for this request. The browser does not persist it.

On success Greia returns a new random per-device credential and device metadata. The browser stores that credential scoped to the selected Greia and uses it for subsequent requests:

```text
Authorization: Bearer <device credential>
```

The device credential is independently revocable through the paired-device resource. A revoked browser must authenticate again with the Parent password to obtain a new device credential.

There is deliberately no compatibility path for the retired shared pairing token, `X-Pip-Token`, token URL, or shared-token cookie. A server/client combination that still requires such a token is stale and must be upgraded rather than worked around.

Failed password authentication is server-rate-limited. HTTP 429 therefore means the client must stop retrying and let the server's bounded failure window expire.

## System output controls

The browser exposes this resource only when the API index advertises:

```text
settings.system_controls = true
```

The read payload may include platform-owned fields such as:

```json
{
  "schema_version": 1,
  "volume_percent": 70,
  "muted": false,
  "brightness_percent": 100
}
```

The Parent browser deliberately exposes only speaker volume and mute. It must not invent a browser brightness control merely because `brightness_percent` is present in the read payload.

Supported Parent mutations are partial:

```json
{ "volume_percent": 35 }
```

```json
{ "muted": true }
```

or both together. `volume_percent` is an integer from `0` through `100`; `muted` is boolean. Unknown fields are rejected by the browser client before network access.

Partial updates are important because physical Greia hardware keys and the Parent browser share the same platform state. The browser must submit only values the parent actually changed so a stale form cannot overwrite an unrelated hardware-key change.

The browser never executes mixer/backlight commands and never receives direct host-device authority. Greia OS owns persistence, ALSA/backlight application, hardware-key capture, and any compatibility backend.

## Error shape

The client expects server errors to use the typed envelope:

```json
{
  "error": {
    "code": "pairing_required",
    "message": "Greia password required"
  }
}
```

`pairing_required` is retained as the API-v1 wire error name for compatibility. The browser maps any such 401 to its internal **authentication required** state and presents password-login language to the parent.

Known password-authentication failures use the same typed error envelope, including `authentication_rejected` and `authentication_rate_limited`. Unknown or malformed bodies still produce a generic HTTP error in the client.

## Runtime integrity

The production runtime manifest is derived from the actual transitive browser dependency graph rooted at `index.html`. It is not a hand-maintained source list. Local scripts, stylesheets, modules, images, fonts, and CSS assets referenced by the runtime therefore enter the integrity closure automatically; tests, documentation, and development tooling remain outside it unless the browser actually references them.

## Capability policy

The API index exposes a `capabilities` map. Client availability must follow this map.

A false capability means **not available**. It must not trigger a browser-side workaround using Linux implementation details.
