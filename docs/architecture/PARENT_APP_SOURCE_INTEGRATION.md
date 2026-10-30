# Greia Parent App source integration

**Status:** production runtime integration implemented; source merged into this repository (2026-10-30); exact-current image and physical Acer acceptance pending  
**Updated:** 2026-10-30  
**Normative parent architecture:** ADR 0022 (see its Amendment 2026-10-30)

## Source lives in this repository

The HTML/CSS/JavaScript browser client is edited in one place, the `parent-app/` directory of this repository (`frozenpepper/Greia`). It was previously the separate private repository `frozenpepper/Greia-Parent-App-Html`, pinned by commit SHA and copied into `vendor/parent-app/`; that repository has been merged here and neither the separate pin nor `vendor/parent-app/` exists any more. Start with `parent-app/README.md` and `parent-app/AGENTS.md`; the root `AGENTS.md` governs everything in the directory.

Greia OS remains authoritative for the Parent API, authentication, platform services, privileged operations, image composition and release integration. `parent-app/` owns only the browser client (plus its tests, local development host and client-side docs, none of which ship).

Greia never serves the working tree of `parent-app/`. `runtime/parent-app-client.toml` pins one committed state of it, and `runtime/parent-app-client.manifest.json` freezes the exact production runtime files, byte counts and SHA-256 digests for that state. The pin fields are:

```text
repository = "frozenpepper/Greia:parent-app"
revision   = <40-hex Git tree id of the committed parent-app/ directory>
```

The `revision` is `git rev-parse HEAD:parent-app` at pin time (a tree id, not a commit id), so it names the exact reviewed source without a second repository while keeping the 40-hex format the integrity verifier and the pin/manifest equality check rely on. The current value is whatever `runtime/parent-app-client.toml` says; do not copy it into documentation.

The browser authenticates with the Greia Parent password (`greia` by default, changeable by parents) to obtain a revocable per-device credential. The retired household-wide pairing token is not a production browser credential.

## Production runtime shape

The installed Parent client is served from:

```text
/usr/share/greia-parent-app
```

by the same Greia Parent HTTPS service that owns `/api/v1` on LAN port 8766. The on-device settings panel communicates with the same application on loopback-only HTTP port 8767. The network certificate is generated on the installed device, not included in this pinned HTML bundle.

```text
GET /                  public static client shell
GET /src/*             public static client code
GET /styles/*          public static client styles
GET /assets/*          public static client assets when present in the manifest

GET /api/v1/meta       public discovery metadata
/api/v1/*              authenticated management API except explicit password-bootstrap endpoint
```

The static shell contains no management state or credential. It is public so an unpaired browser can render the connection flow; authorization remains on management API resources.

## Production files are not demo files

The production manifest contains only runtime files reachable by the accepted Greia-served client. Demo adapters and source/test fixtures are excluded from the Greia production manifest and image payload.

`?demo=1` is not a production feature and is never acceptance evidence. A normal Greia-served client does not ship demo modules.

## Static serving boundary

`greia_parent.static_client.ParentStaticClient` is a bounded read-only loader:

- only `index.html` and assets beneath `src/`, `styles/`, or `assets/`;
- no directory listing;
- no repository docs, tests, package metadata or arbitrary files;
- no traversal, hidden files or symlink escape;
- explicit content-type allowlist;
- 512 KiB per-file ceiling;
- no runtime network fetch.

The HTTP layer adds the Parent static response security policy. If a lower-level development server cannot load `/`, `greia_parent.web_client` renders only an explicit installation-error page: it contains no management controls and no sample state. The installed production service normally never reaches that path because its integrity preflight fails first.

## Source-to-image trust boundary

The only supported way to move browser changes into the image is:

1. edit `parent-app/` (never the overlay, pin or manifest);
2. `make parent-app-test` (`node --test parent-app/tests/*.test.js`; skipped when Node >= 18 is absent);
3. commit `parent-app/`;
4. run `python3 tools/update_parent_client_pin.py` from the repository root;
5. commit the resulting pin, manifest and overlay.

`python3 tools/update_parent_client_pin.py --check` reports drift without writing, and `tests/test_parent_client_image_integration.py` fails when `parent-app/` runtime files, the manifest, the pin or the overlay disagree.

The tool refuses to run while `parent-app/` has uncommitted or untracked changes. It reads the runtime closure reachable from `index.html` from Git objects at `HEAD:parent-app` (never the working tree), exactly once, and derives all three Greia-owned artifacts from those same bytes:

```text
runtime/parent-app-client.toml
runtime/parent-app-client.manifest.json
build/overlay/usr/share/greia-parent-app/
```

All replacements are staged before any current artifact is moved, and sibling backups restore the previous checkout state if a multi-path swap fails. The overlay is rebuilt from the manifest-owned closure, so files removed from the runtime closure disappear instead of surviving a repin.

Pin, manifest and overlay must never be advanced by separate manual steps or hand-edited; that can produce an internally inconsistent Greia commit.

## Canonical image integration

The frozen runtime bytes are committed directly into the canonical image overlay:

```text
build/overlay/usr/share/greia-parent-app/
```

The normal image builder already installs `build/overlay/` into the target root with root ownership:

```text
rsync -a --chown=root:root "$PROJECT_ROOT/build/overlay/" "$ROOTFS/"
```

Therefore the Parent browser bundle is a deterministic, offline image input. A release/developer image does not fetch Parent JavaScript from GitHub or any other network location during build, boot or runtime, and operators must not manually copy a browser bundle into `/usr/share/greia-parent-app`.

Because the Parent client lives under the frozen system image root (not under `/opt/greia-os/src`), a Python application update cannot change it; only a full-system image (A/B update or reinstall) delivers a new Parent client.

## Installed-runtime integrity enforcement

`greia_parent.parent_client_integrity` verifies an installed runtime against both Greia authorities:

```text
runtime/parent-app-client.toml
runtime/parent-app-client.manifest.json
```

It rejects:

- missing runtime root;
- symlinked root or assets;
- missing manifest files;
- unexpected/unmanifested files;
- demo files in the production manifest;
- byte-count mismatch;
- SHA-256 mismatch;
- pin/manifest repository or revision mismatch.

`greia-parent.service` runs this verifier as an unprivileged `ExecStartPre` before the Parent API starts. A corrupt, incomplete or substituted browser bundle therefore makes the installed Parent service fail closed instead of serving a second UI or fabricated state.

The pin also records `integration_state = "vendored-image-integrity-enforced"`: the runtime bytes are carried in the image and enforced at service start.

## Authentication contract

The browser connection flow is intentionally two-stage:

```text
human Parent password
  -> POST /api/v1/pairing/bootstrap
  -> fresh per-device bearer credential
  -> ordinary authenticated /api/v1 requests
```

The bootstrap route name remains `pairing/bootstrap` for API-v1 compatibility, but the request body contains `password`, not the retired shared `pairing_token`. The browser persists only its issued device credential; it does not persist the Parent password.

Changing the Parent password does not silently convert existing browser credentials into a household-wide shared credential. Parent devices remain independently revocable.

## Parent/API truthfulness

The browser is capability-driven and the installed API remains authoritative. Unsupported features are shown as unavailable; they are not emulated.

In particular, installed production Wi-Fi composition uses the real iwd backend only. `network.manage` is false when the unprivileged Parent service cannot genuinely manage iwd state, scan/connect is fail-closed, and a connection request must name a network returned by a real scan. No production path may synthesize demo SSIDs or manufacture a network object for an unscanned SSID.

System output controls keep their existing privilege separation: Parent mutates typed desired state; the child hardware session owns ALSA/backlight/media-key application. Do not grant the HTTP process direct mixer/backlight authority to make browser controls appear functional.

## Verification and remaining evidence

The source/image integration is structurally represented by `parent-app/`, the exact pin, the manifest and the image-overlay runtime. `tests/test_parent_client_image_integration.py` verifies that relationship without hard-coding a particular revision, so a legitimate repin does not require changing test policy. It fails on drift between `parent-app/` and the pin/manifest/overlay.

`tests/test_update_parent_client_pin.py` and `tests/test_parent_client_pin_tool.py` own the repin transaction itself: transitive HTML/JS/CSS/asset discovery, exact manifest/runtime byte equality, removal of stale runtime files from the overlay, refusal of uncommitted `parent-app/` source before Greia mutation, and rollback when a later path replacement fails after an earlier one has already been installed. Browser unit tests live in `parent-app/tests/` and run through `make parent-app-test` (also part of `make verify`).

Source-level owners include:

```text
parent-app/
tools/update_parent_client_pin.py
tests/test_update_parent_client_pin.py
tests/test_parent_client_pin_tool.py
tests/test_parent_client_image_integration.py
greia_parent.parent_client_integrity
tests/test_parent_password_auth.py
```

A committed test is not a PASS; exact-current local execution is still required for any claim.

This also does **not** prove the physical Acer path. Final real-runtime acceptance must use an officially built image and a real browser against the Greia-served production URL. It must prove:

- the initial `greia` password works on an unchanged fresh credential store;
- successful bootstrap issues and persists a browser device credential;
- browser reload/reconnect does not require re-entering the password while that device credential remains valid;
- changing the Parent password rejects the old password and accepts the new one for future bootstrap;
- revoking the current browser device removes that browser's API access;
- the revoked browser can bootstrap again only with the current Parent password;
- no obsolete shared-token helper/state is installed or recreated;
- browser system-control mutations reach real hardware state where the capability is advertised.

The exact-current procedure is owned under `docs/testing/` and must supersede the obsolete token instructions in the older 2026-09-02 Parent runtime gate.

## Updating the Parent client later

Use this order:

1. implement and test the browser change in `parent-app/` (`make parent-app-test`);
2. commit `parent-app/`;
3. run `python3 tools/update_parent_client_pin.py` once; it derives the manifest and synchronizes the pin and image overlay from the same committed bytes (`--check` reports drift);
4. inspect the resulting diff: the overlay must contain exactly the manifest closure and no unrelated Greia source should move merely because of the repin;
5. run `tests/test_update_parent_client_pin.py`, `tests/test_parent_client_image_integration.py`, the Parent password-auth tests and full `make verify` locally;
6. repeat any browser/image/physical acceptance made stale by the runtime change.

Never hand-edit the manifest, pin or image copy as independent Parent implementations.
