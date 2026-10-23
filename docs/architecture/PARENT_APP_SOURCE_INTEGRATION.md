# Greia Parent App source integration

**Status:** production runtime integration implemented; exact-current local/image and physical Acer acceptance pending  
**Updated:** 2026-09-08  
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
5518a9eed8ba61503249a1c827b7ef4fef5dab36
```

This revision uses Greia Parent password bootstrap (`greia` by default, changeable by parents) to issue a revocable per-device browser credential. The retired household-wide pairing token is not a production browser credential.

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

## Source-to-Greia trust boundary

The canonical developer repin entrypoint is:

```bash
python3 tools/update_parent_client_pin.py \
  --parent-root /path/to/Greia-Parent-App-Html \
  --revision <exact-reviewed-parent-sha>
```

The command requires a clean Parent checkout at exactly the supplied SHA. It discovers the transitive runtime closure from `index.html`, captures those runtime bytes once, derives the manifest from those same bytes, then stages all four Greia-owned artifacts before replacing any current artifact:

```text
runtime/parent-app-client.toml
runtime/parent-app-client.manifest.json
vendor/parent-app/
build/overlay/usr/share/greia-parent-app/
```

The replacement step keeps sibling backups until every staged artifact has been installed and restores the previous checkout state if a multi-path swap fails. Both runtime trees are rebuilt from the manifest-owned closure, so stale files from an older Parent revision disappear instead of surviving a repin.

This single operation is intentional. Pin/manifest advancement, vendored provenance, and image-overlay payload must not be performed as separate manual synchronization steps; that can produce an internally inconsistent Greia commit.

`tools/stage_parent_app.py` remains the lower-level exact-byte verifier/stager used by focused tests and other bounded staging work. It verifies repository/revision pin and manifest bytes, rejects symlinks/traversal/unexpected runtime locations, and stages only frozen runtime files. It is not a replacement for the canonical four-artifact repin command above.

`vendor/parent-app/` is provenance, not a second editable Parent application. Changes originate in `Greia-Parent-App-Html`, are accepted there, then the exact accepted bytes and manifest are advanced together in Greia.

## Canonical image integration

The same frozen runtime bytes are committed directly into the canonical image overlay:

```text
build/overlay/usr/share/greia-parent-app/
```

For the current integration the vendor tree and image-overlay tree use the same accepted runtime bytes. The normal image builder already installs `build/overlay/` into the target root with root ownership:

```text
rsync -a --chown=root:root "$PROJECT_ROOT/build/overlay/" "$ROOTFS/"
```

Therefore the Parent browser bundle is a deterministic, offline image input. A release/developer image does not fetch Parent JavaScript from GitHub or any other network location during build, boot or runtime, and operators must not manually copy a browser bundle into `/usr/share/greia-parent-app`.

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
revision = "01301d285c6ba2a9a1f2948a9768b821d2536729"
integration_state = "vendored-image-integrity-enforced"
```

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

The source/image integration is structurally represented by the exact pin, manifest, vendored runtime and image-overlay runtime. `tests/test_parent_client_image_integration.py` verifies the pin/manifest relationship without hard-coding a particular future revision, so a legitimate repin does not require changing test policy merely to name a new SHA.

`tests/test_update_parent_client_pin.py` additionally owns the repin transaction itself. It verifies transitive HTML/JS/CSS/asset discovery, exact manifest/runtime byte equality, removal of stale runtime files from both copies, refusal of dirty Parent source before Greia mutation, and rollback when a later path replacement fails after an earlier one has already been installed.

Source-level owners include:

```text
tools/update_parent_client_pin.py
tests/test_update_parent_client_pin.py
tools/stage_parent_app.py
tests/test_parent_app_staging.py
tests/test_parent_client_image_integration.py
greia_parent.parent_client_integrity
tests/test_parent_password_auth.py
```

The current `01301d...` runtime itself is unchanged by the repin-tool hardening. The new updater/test descendant still requires exact-current local execution. A committed test is not a PASS.

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

1. implement/review/test the browser change in `Greia-Parent-App-Html`;
2. freeze the exact accepted Parent commit and ensure its checkout is clean;
3. run `tools/update_parent_client_pin.py --parent-root ... --revision <exact-sha>` once; this derives the manifest and synchronizes the pin, vendor, and image overlay from the same captured runtime bytes;
4. inspect the resulting Greia diff: the two runtime trees must contain exactly the manifest closure and no unrelated Greia source should move merely because of the repin;
5. run `tests/test_update_parent_client_pin.py`, Parent staging/image-integrity/password-auth focused tests, and full `make verify` locally;
6. repeat any browser/image/physical acceptance made stale by the runtime change.

Never hand-edit the manifest, vendored runtime, or image copy as independent Parent implementations.
