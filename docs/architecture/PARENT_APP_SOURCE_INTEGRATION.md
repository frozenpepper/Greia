# Greia Parent App source integration

**Status:** implementation foundation in progress  
**Date:** 2026-08-17  
**Normative parent architecture:** ADR 0022

## Separate client repository

The canonical HTML client source lives in:

```text
frozenpepper/Greia-Parent-App-Html
```

Greia OS remains authoritative for the Parent API, authentication, platform services, privileged operations and release integration. The client repository owns only the HTML/CSS/JavaScript client.

`runtime/parent-app-client.toml` pins the reviewed client revision expected by this Greia source tree. `runtime/parent-app-client.manifest.json` independently freezes the exact runtime-file sizes and SHA-256 digests for that revision.

## Runtime shape

Release images will serve the pinned static client from:

```text
/usr/share/greia-parent-app
```

through the same Greia Parent HTTP service that owns `/api/v1`.

This same-origin shape is deliberate:

```text
GET /                  public static client shell
GET /src/*             public static client code
GET /styles/*          public static client styles
GET /assets/*          public static client assets

GET /api/v1/meta       public discovery metadata
/api/v1/*              authenticated management API except explicit pairing endpoints
```

The public static shell contains no management data or credential. It must be reachable before pairing so an unpaired browser can display the pairing flow. Authentication remains on the API resources, not on the inert application shell.

## Static serving boundary

`greia_parent.static_client.ParentStaticClient` provides a bounded read-only loader:

- only `index.html` and assets beneath `src/`, `styles/`, or `assets/`;
- no directory listing;
- no `docs/`, tests, package metadata or arbitrary repository files;
- no traversal, hidden files or symlink escape;
- explicit content-type allowlist;
- 512 KiB per-file ceiling;
- no runtime network fetch.

The API server adds CSP, `nosniff`, no-referrer and no-cache response policy for served client assets.

## Build-time source verification

`tools/stage_parent_app.py` is the source-to-image trust boundary. A build supplies a checkout/export of the separately maintained Parent App; the stager:

1. loads the repository/revision pin;
2. requires the hash manifest to name that exact pin;
3. accepts only bounded static runtime paths/types;
4. verifies every runtime file's byte count and SHA-256 before creating the target;
5. rejects symlink assets, traversal and unexpected runtime locations;
6. stages only the frozen runtime files, not repository docs/tests/tooling;
7. writes through a fresh temporary directory before publishing the target directory.

The content manifest, rather than mutable Git metadata on the build host, is sufficient to validate an exported source tree. The revision remains recorded for provenance and review.

## Current integration state

The standalone client is implemented and its current reviewed revision is pinned. The server-side static loader, API shell/public-pairing boundary, frozen runtime manifest and integrity-checked stager exist.

The canonical image builder does **not yet invoke the stager**, so the release image does not yet populate `/usr/share/greia-parent-app` from the separate repository. Until that final build wiring lands, the old embedded prototype remains a transitional root fallback.

The remaining build integration must not fetch mutable GitHub content at Greia boot/runtime. The owner-controlled image build should receive a local checkout/export of the exact Parent App revision (for example through a declared `GREIA_PARENT_APP_SOURCE` build input), invoke the stager before image closure, and record the pinned revision/digest in build evidence.

Do not maintain two independently edited Parent Apps. Once the external client is staged by the canonical image build and source-verified, remove the embedded prototype.
