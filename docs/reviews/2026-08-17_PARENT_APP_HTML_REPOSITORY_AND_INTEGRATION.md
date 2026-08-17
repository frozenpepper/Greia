# Greia Parent App HTML repository and integration — 2026-08-17

## Scope

This record covers the first standalone Greia Parents client repository and the Greia-side source integration needed to consume it without turning the browser into a privileged management implementation.

Canonical client repository:

```text
frozenpepper/Greia-Parent-App-Html
```

Greia runtime client revision currently pinned:

```text
b186ba3fee3e8c946ad6b8fe4ce822cd1cb3303f
```

## Client implementation

The standalone repository now contains a dependency-free responsive HTML/CSS/ES-module application with:

- Overview, Children, Activities, Settings and Parent Devices screens;
- a typed `/api/v1` client and typed pairing-required failures;
- provisional bootstrap pairing into independent per-device credentials;
- origin-scoped credential storage;
- coherent application state separate from transport and rendering;
- profile create/delete and selected-profile progress;
- Activity inventory;
- mouse/touchpad/display settings;
- paired-device revocation;
- capability-driven unavailable-feature presentation;
- confirmation for destructive actions;
- a localhost-only `?demo=1` fixture adapter;
- no third-party runtime JavaScript, framework, analytics, remote font or CDN dependency;
- DOM text insertion rather than API-controlled `innerHTML`.

Client-side execution performed in the available environment after the runtime source change:

```text
npm test
6 / 6 PASS

node --check src/app.js
PASS
```

No browser-rendering PASS is claimed. A headless Chromium attempt hung in the container/DBus environment and was discarded as evidence.

## Greia source integration

Greia now contains:

```text
src/greia_parent/static_client.py
runtime/parent-app-client.toml
runtime/parent-app-client.manifest.json
tools/stage_parent_app.py
tests/test_parent_static_client.py
tests/test_parent_app_staging.py
docs/architecture/PARENT_APP_SOURCE_INTEGRATION.md
```

`ParentApiRequestHandler` serves a public inert application shell/static files while keeping management API resources authenticated. This is required because an unpaired browser must load the pairing UI before it can possess a device credential.

Static serving is bounded to `index.html` plus `src/`, `styles/`, and `assets/`, with explicit content types, 512 KiB file bounds, no directory listing, no traversal/hidden/symlink path acceptance, CSP, `nosniff`, no-referrer and no-cache response policy.

The runtime pin and hash manifest freeze the separate repository revision and exact runtime bytes. `tools/stage_parent_app.py` validates all byte sizes/digests and safe paths before writing any target directory; repository docs/tests/tooling are not staged.

A local smoke execution of the stager against the standalone client source passed. The new Greia unit-test files themselves have **not** been executed in a current complete Greia checkout, and no full `make verify`, image build, VM boot or physical-machine result is claimed for this tranche.

## Remaining integration boundary

The canonical image builder does not yet invoke `tools/stage_parent_app.py`. Therefore `/usr/share/greia-parent-app` is not yet populated from the external repository by the normal build, and the existing embedded Python-string client remains a transitional fallback.

Next exact implementation step:

1. add a declared owner-controlled build input for the Parent App checkout/export;
2. invoke the stager during target image composition before image closure;
3. record the pinned client revision/hash in build evidence;
4. run the focused Parent API/static/staging tests and the full owner-controlled source gate;
5. build/boot an image and verify the external client is the served root application;
6. only then remove the embedded `greia_parent.web_client` fallback.

Production pairing and transport remain separately open per ADR 0022: authenticated encryption, Greia-local short-lived challenge, explicit Allow/Deny, replay/expiry protection and device identity binding are still required.
