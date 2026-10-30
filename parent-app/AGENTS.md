# AGENTS.md — Parent browser client (`parent-app/`)

This directory is the single editable source of the browser Parent client. The
repository-root [`AGENTS.md`](../AGENTS.md) governs everything here (branch
policy, validation, evidence labels, documentation duties); this file adds only
the rules specific to the client. The Parent API, authorization, platform
services, privileged brokers and image integration live under `src/` and
`build/` at the repository root.

## Client rules

- All management state and mutations use the versioned Greia Parent `/api/v1`
  API. Do not invent a second management protocol.
- Never execute shell commands, SSH commands, package-manager commands, or host
  paths from browser JavaScript.
- Treat Greia capability discovery as authoritative. If a capability is
  unavailable, show it as unavailable; never emulate it.
- Never render API-provided text with `innerHTML`.
- No third-party JavaScript, trackers, analytics, remote icons/fonts, build
  step, heavyweight SPA framework, or runtime package dependency without an
  explicit architecture decision. The client is plain ES modules, CSS and
  static assets served as-is under a strict Content-Security-Policy.
- Credentials (pairing tokens) stay in the credential store scoped to the
  selected Greia origin; never log them, put them in URLs, or send them to any
  other origin.
- Preserve low-resource operation: bounded DOM, bounded discovery, no
  background polling loop by default, no background animation.
- Keep discovery/bootstrap, API transport, state, and rendering separated.
- Destructive actions require clear Parent confirmation; server enforcement
  remains authoritative.
- The production browser runtime has **no demo mode**. Fake APIs may exist only
  under `tests/support/` and must never be browser-reachable or part of the
  runtime manifest.

## Device discovery and connection

The standalone dev host (`tools/dev_server.mjs`) starts unbound and must find
real Greia computers before management begins:
discover → choose or restore one validated device → normal pairing → HTTPS
proxy to that device's real `/api/v1`.

- Browser JavaScript does not scan the LAN; `tools/greia_discovery.mjs` owns
  bounded host-side discovery (at most 512 IPv4 candidates, local network only).
- A candidate is accepted only when `GET https://<candidate>:8766/api/v1/meta`
  returns the exact Greia Parent identity (`product=Greia`,
  `service=Greia Parents`, `api_version=v1`, non-empty `device_name`).
- The dev host proxies `/api/v1` only to a device in its recent validated
  discovery set; it must never become an arbitrary URL/LAN proxy. Its
  `/__greia/*` routes are bootstrap plumbing, not management APIs.
- Installed Greia serves a device-generated self-signed certificate; the dev
  bridge accepts those local certificates and does not establish public CA
  trust.
- A remembered device reconnects automatically only if it is rediscovered and
  validated on the current network; several devices need an explicit chooser.
  Never manufacture a fallback device.
- Do not review the product with a static server, a fake adapter, fabricated API
  state or an authentication bypass.

## Runtime closure and the image pin

The installed image ships only the runtime closure reachable from `index.html`
(`index.html`, `src/`, `styles/`, `assets/` that it actually references). Tests,
tools, docs and `tests/support/` demo fixtures are never shipped.

After changing any runtime file, commit `parent-app/` and run
`python3 tools/update_parent_client_pin.py` from the repository root, then commit
the resulting `runtime/parent-app-client.*` and
`build/overlay/usr/share/greia-parent-app/` changes. A drift test fails
otherwise. Never hand-edit the overlay or the pin/manifest files.

## Verification

```bash
node --test parent-app/tests/*.test.js     # or: make parent-app-test
```

Discovery changes must cover bounded candidate enumeration, exact Greia meta
validation, rejection of unrelated hosts, discovered-only selection and
per-device credential isolation. Browser-source tests do not substitute for
image or physical-device evidence; production acceptance uses the normal Greia
Parent service and normal pairing.
