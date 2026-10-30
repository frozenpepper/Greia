# Greia Parent browser client

The browser client for managing a Greia computer from a parent's phone or
computer: pairing, children, Activities, usage limits, language, device
settings and software updates, all through the device's versioned
`/api/v1` Parent API. It is plain ES modules, CSS and static assets with no
build step and no runtime dependencies.

- `index.html`, `src/`, `styles/`, `assets/` — the client itself.
- `tools/` — the local development host (`dev_server.mjs`), LAN discovery and
  the runtime-closure helper.
- `tests/` — Node unit tests (`tests/support/` holds demo/fake APIs for tests
  only, never shipped).
- `docs/` — API client contract, architecture and security notes.

## Tests (Node 22)

```bash
node --test parent-app/tests/*.test.js     # from the repository root
make parent-app-test                        # same, skipped when Node < 18 is absent
```

## Development server

```bash
node tools/dev_server.mjs                   # from this directory
```

Then open <http://127.0.0.1:8080/>. The host discovers real Greia devices on
the local network; see [AGENTS.md](AGENTS.md) for the discovery rules.

## Shipping changes to the image

The installed Parent service serves a frozen, integrity-checked copy of the
runtime files, not this directory. After changing runtime files, commit
`parent-app/` and run the repin tool from the repository root:

```bash
python3 tools/update_parent_client_pin.py          # rewrite pin, manifest and overlay
python3 tools/update_parent_client_pin.py --check  # verify they are in sync
```

Then commit the result. The pin `revision` is the Git tree id of the committed
`parent-app/` directory.
