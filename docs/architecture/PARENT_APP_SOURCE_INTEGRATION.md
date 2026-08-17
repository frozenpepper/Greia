# Greia Parent App source integration

**Status:** implementation foundation in progress  
**Date:** 2026-08-17  
**Normative parent architecture:** ADR 0022

## Separate client repository

The canonical HTML client source now lives in:

```text
frozenpepper/Greia-Parent-App-Html
```

Greia OS remains authoritative for the Parent API, authentication, platform services, privileged operations and release integration. The client repository owns only the HTML/CSS/JavaScript client.

`runtime/parent-app-client.toml` pins the reviewed client revision expected by this Greia source tree.

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

## Current integration state

The server-side loader and source pin exist. The release image does **not yet vendor the pinned client files** into `/usr/share/greia-parent-app`; until that build step lands, the old embedded prototype remains a transitional root fallback.

The next build integration must be deterministic and integrity checked. It must not fetch mutable GitHub content at Greia boot/runtime. A build may consume a locally supplied checkout/archive of the exact pinned revision or another repository-managed immutable input mechanism.

Do not maintain two independently edited Parent Apps. Once the external client is vendored and source-verified, the embedded prototype should be removed.
