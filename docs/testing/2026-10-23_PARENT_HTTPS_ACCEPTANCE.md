# Greia Parents HTTPS — source and device acceptance (2026-10-23)

**Status:** source implementation committed; source gates and real-device/browser acceptance **not yet executed or certified**. Supersedes only the *transport* instructions in the older 2026-09-08 authentication procedure. Authentication rules remain the same: Parent password bootstrap, per-device revocable bearer, no shared token.

## Boundary

- Greia LAN: `https://<device-ip>:8766/`. Installed Greia generates a persistent self-signed cert/key at `/var/lib/greia-os/parent-tls/` on initial service start using the image-installed `openssl` package.
- Built-in S+T Parent panel: `http://127.0.0.1:8767` (HTTP bound only to loopback); shares Parent API and mutation lock with the TLS listener.
- No network plaintext HTTP fallback. If TLS certificate generation/loading fails, the LAN listener remains closed but the local on-device Parents panel stays available on HTTP 127.0.0.1:8767 and the service logs a bounded diagnostic. Certificate warning on the browser is expected and owner-approved for home use. It does not demonstrate cryptographic verification of the Greia identity.
- Parent HTML source is `parent-app/` in this repository; Greia's `runtime/parent-app-client.toml`, manifest and image overlay must all correspond to its committed state (`python3 tools/update_parent_client_pin.py --check`).
- Activity installation remains capability-gated; TLS alone must not enable it.

## Local source gate (single repository; non-destructive)

Prerequisites: a working local checkout of `frozenpepper/Greia` (it contains the browser client as `parent-app/`); Python 3.11+, OpenSSL, Node.js >= 18; no hosted Actions. Ensure any local changes are preserved; never reset, clean, overwrite, or rebase. Fetch the current `main`, record the SHA, and use a clean checkout for authoritative results.

Greia:

```sh
python3 --version
openssl version
PYTHONPATH=src python3 -m unittest discover -s tests -p 'test_parent_tls.py' -v
PYTHONPATH=src python3 -m unittest discover -s tests -p 'test_parent_production_api.py' -v
PYTHONPATH=src python3 -m unittest discover -s tests -p 'test_parent_api.py' -v
PYTHONPATH=src python3 -m unittest discover -s tests -p 'test_parent_credential_client.py' -v
PYTHONPATH=src python3 -m unittest discover -s tests -p 'test_parent_api_legacy_token_negative.py' -v
PYTHONPATH=src python3 -m greia_parent.parent_client_integrity --root build/overlay/usr/share/greia-parent-app --manifest runtime/parent-app-client.manifest.json --pin runtime/parent-app-client.toml
python3 tools/update_parent_client_pin.py --check
```

Parent HTML client (same checkout):

```sh
node --version
make parent-app-test        # node --test parent-app/tests/*.test.js
```

The pin `--check` must report no drift: the pin revision is the git tree id of the committed `parent-app/` (`git rev-parse HEAD:parent-app`), and the overlay root verified above is the exact payload the image ships. The run must not test unpinned moving browser bytes and call them installed Greia. Report actual test counts and failures, not inferred PASSes. A test unavailable in a checkout must be reported as such rather than silently skipped.

## Device smoke test — only with separate owner authorization for deployment

**Deployment compatibility warning:** Do **not** use `tools/dev_source_deploy.py` alone to test this HTTPS change on an older installed image. Its current archive/deploy contract does not update `/usr/share/greia-parent-app/`, while the new source updates the pinned Parent client revision and integrity manifest. The installed `greia-parent.service` would then fail its mandatory `ExecStartPre` integrity verification. Do not bypass this by manually copying browser files or disabling integrity checks. Test physically only on a newly composed exact-head image, or a separately reviewed/authorized deployment procedure proven to update the complete browser runtime and source in one coherent operation. Do not flash, reinstall, update, or reboot the Acer without explicit owner authorization. If such an image/deployment is not already available, stop at the source tests and report this hardware-test blocker.

If the complete new version is already installed or an independently authorized complete-image test is performed, record its exact image/source SHA and check:

1. `systemctl is-active greia-parent`; show recent `journalctl -u greia-parent` logs **without passwords/credentials**. Confirm no startup failure from OpenSSL/certificate state.
2. `ss -lnt` must show LAN HTTPS listener on port 8766 and **only** 127.0.0.1:8767 for local HTTP; neither `0.0.0.0:8767` nor a plaintext LAN API is allowed.
3. `curl -ksS --max-time 5 https://127.0.0.1:8766/api/v1/meta` returns Greia Parents metadata with `transport_security: self-signed-https`.
4. `curl -sS --max-time 5 http://127.0.0.1:8767/api/v1/meta` returns the same API identity; plaintext `http://<device-ip>:8766/api/v1/meta` must not return a valid API result.
5. The certificate and key exist only on the installed device (not inside the release image), key mode `0600`; after a permitted service restart they remain unchanged. Never print private key bytes.
6. From a phone/laptop on the same LAN, open `https://<device-ip>:8766/`, acknowledge the expected self-signed warning for the known Greia address, then test actual Parent password login, reload/reconnect, profile read and independent revocation. Test S+T on the child profile-picker (five-second hold) and on-device password login separately.
7. If normal password state or paired clients already exist, use a disposable target or coordinate with the owner before modifying them. Do not reset or revoke anyone's existing devices.

## Stop and evidence

Stop on the first genuine failing gate and return its full non-secret output with the exact Greia and Parent SHAs, commands and exit codes, host OS/tool versions, and any screenshots/observations. Save logs in one local folder; do not commit giant evidence bundles, secrets, generated certificate keys, or hardware artifacts. Never claim browser/hardware proof from source tests.
