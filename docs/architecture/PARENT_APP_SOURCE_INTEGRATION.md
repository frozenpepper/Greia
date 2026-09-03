# Greia Parent App source integration

**Status:** production runtime integration implemented; physical Acer acceptance pending  
**Updated:** 2026-09-03  
**Normative parent architecture:** ADR 0022

## Separate client repository

The canonical HTML/CSS/JavaScript client source lives in:

```text
frozenpepper/Greia-Parent-App-Html
```

Greia OS remains authoritative for the Parent API, authentication, platform services, privileged operations, image composition and release integration. The client repository owns only the browser client.

Greia never serves moving Parent `main`. `runtime/parent-app-client.toml` pins one reviewed Parent commit, and `runtime/parent-app-client.manifest.json` freezes the exact production runtime files, byte counts and SHA-256 digests for that commit.

The currently integrated Parent revision is:

```text
75ee275771c495dc187efb5275732ea10c10af4b
```

## Production runtime shape

The installed Parent client is served from:

```text
/usr/share/greia-parent-app
```

by the same Greia Parent HTTP service that owns `/api/v1`.

```text
GET /                  public static client shell
GET /src/*             public static client code
GET /styles/*          public static client styles
GET /assets/*          public static client assets when present in the manifest

GET /api/v1/meta       public discovery metadata
/api/v1/*              authenticated management API except explicit pairing endpoints
```

The static shell contains no management state or credential. It is public so an unpaired browser can render the pairing flow; authorization remains on management API resources.

## Production files are not demo files

The production manifest contains only assets reachable by the Acer production client. Localhost demo adapters are source/test fixtures in the Parent repository and are deliberately excluded from the Greia production manifest and image payload.

`?demo=1` is therefore not a production feature. The Parent source only lazy-loads the demo adapter on loopback hosts, and a normal Acer-served client does not ship the demo modules at all.

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

## Source-to-Greia trust boundary

`tools/stage_parent_app.py` remains the review/update tool for importing an accepted Parent source export. It verifies the repository/revision pin and exact manifest bytes, rejects symlinks/traversal/unexpected runtime locations, and stages only frozen runtime files.

After a Parent revision is accepted, the verified production bytes are committed under:

```text
vendor/parent-app/
```

That directory is provenance, not a second editable Parent application. Changes originate in `Greia-Parent-App-Html`, are accepted there, then the exact accepted bytes and manifest are advanced together in Greia.

## Canonical image integration

The same frozen runtime bytes are committed directly into the canonical image overlay:

```text
build/overlay/usr/share/greia-parent-app/
```

For the current integration the vendor tree and image-overlay tree use the same Git blobs. The normal image builder already installs `build/overlay/` into the target root with root ownership:

```text
rsync -a --chown=root:root "$PROJECT_ROOT/build/overlay/" "$ROOTFS/"
```

Therefore the Parent browser bundle is now a deterministic, offline image input. A release/developer image does not fetch Parent JavaScript from GitHub or any other network location during build, boot or runtime, and operators must not manually copy a browser bundle into `/usr/share/greia-parent-app`.

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

Current pin state is:

```text
integration_state = "vendored-image-integrity-enforced"
```

## Parent/API truthfulness

The browser is capability-driven and the installed API remains authoritative. Unsupported features are shown as unavailable; they are not emulated.

In particular, installed production Wi-Fi composition uses the real iwd backend only. `network.manage` is false when the unprivileged Parent service cannot genuinely manage iwd state, scan/connect is fail-closed, and a connection request must name a network returned by a real scan. No production path may synthesize demo SSIDs or manufacture a network object for an unscanned SSID.

System output controls keep their existing privilege separation: Parent mutates typed desired state; the child hardware session owns ALSA/backlight/media-key application. Do not grant the HTTP process direct mixer/backlight authority to make browser controls appear functional.

## Verification and remaining evidence

Source-level authority is covered by the Parent pin/manifest, `tools/stage_parent_app.py`, `tests/test_parent_app_staging.py`, `greia_parent.parent_client_integrity`, and `tests/test_parent_client_image_integration.py`.

This does **not** prove the physical Acer path. Final real-runtime acceptance is defined in:

```text
docs/testing/2026-09-02_PARENT_REAL_RUNTIME_FINAL_ACCEPTANCE.md
```

That gate must use an officially built image and a normal paired production URL. It forbids demo mode, manual runtime copying, fabricated state and visual-only mutation acceptance. In particular it must prove browser volume/mute changes reach actual Acer ALSA state and converge with hardware-key changes.

## Updating the Parent client later

Use this order:

1. implement/review/test the browser change in `Greia-Parent-App-Html`;
2. freeze the exact accepted Parent commit;
3. generate/obtain its production manifest with demo fixtures excluded;
4. advance Greia's pin and manifest together;
5. stage the exact accepted bytes into `vendor/parent-app/`;
6. replace the image-overlay runtime with those same exact bytes;
7. run Parent staging/image-integrity focused tests and full `make verify` locally;
8. repeat any browser/image/physical acceptance made stale by the runtime change.

Never hand-edit the vendored or image copy as an independent Parent implementation.
