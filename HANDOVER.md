# Greia — Standalone Engineering Handover

**Date:** 2026-08-19  
**Version family:** `0.13.x` development  
**Repository:** `frozenpepper/Greia` (private)  
**Canonical/default/development branch:** `main`  
**Primary blocking platform phase:** **R7 — Direct graphics/session/input architecture**  
**Current cross-cutting source tranches after the last full executed gate:** **Activity Simulator hardening + Unicode/color-emoji/Writing + R13B transactional-system-update foundation**  
**External Parent HTML revision pinned by Greia:** `frozenpepper/Greia-Parent-App-Html@ccc2355e3e9d758cdad24d73cb56371ca651a95f`

This file owns the **current continuation/evidence boundary**. Historical detail belongs in the append-only active plan and dated reviews. Exact APIs/limits remain source-owned.

---

## 1. Repository and execution rules

- `main` is the owner-required development/integration branch. Do not create branches unless the owner explicitly changes policy.
- GitHub is canonical persistence; commit coherent work as it proceeds.
- Do **not** use/query/trigger/rerun/inspect/download GitHub-hosted Actions without explicit owner authorization for that specific hosted execution.
- Never convert committed tests into PASS merely because the files exist.
- The active plan remains `docs/plans/2026-08-08_ARCHITECTURE_REMEDIATION_AND_PLATFORM_COMPLETION.md`.
- R7 remains the first incomplete blocking architecture phase. Cross-cutting product work does not close/skip R7.

---

## 2. Current evidence boundary

The latest genuinely executed complete owner-controlled source gate is the 2026-08-19 run:

```text
make verify:                         781 PASS
project & 10 activities validation:  PASS
footprint & shell check:             PASS
```

That evidence covers:
- The 2026-08-19 Activity Simulator hardening and Remote Bridge (`http://127.0.0.1:8767`, web canvas, CLI control);
- The 2026-08-19 Unicode grapheme/color-emoji typography and Writing Activity picker;
- The 2026-08-19 On-Device Parent Settings Panel, Key Chord Tracker (`s`+`t` 5.0s), Platform Wi-Fi service, and SSH Maintenance service;
- The 2026-08-19 UI rendering performance optimizations (bounded label/category/shadow caching, pure text fast-path, wallpaper stat throttling);
- The 2026-08-19 6 new first-party built-in activities (`cucciolo_mio`, `foresta_parole`, `orchestra_animali`, `pasticceria_magica`, `teatrino_fiabe`, `volo_draghetto`).

No current-head system-update activation, rollback, QEMU A/B, Pi A/B, or current-head aggregate PASS is claimed.

---

# 3. 2026-08-19 — Transactional Greia system-update foundation

# 4. 2026-08-19 — On-Device Parent Settings Panel, Key Chord & Simulator Remote Bridge

## 4.1 Product & Architecture Decisions

- Accidental-activation-resistant key chord: pressing and holding `s` + `t` simultaneously for 5.0 seconds on the initial profile selection screen triggers the on-device parent flow. Releasing either key before 5.0 seconds resets the hold timer immediately.
- Authentication gate: Entering the parent panel requires entering the main Parent password (`greia` by default, managed via `MainCredentialStore`).
- On-device Wi-Fi configuration: Scans nearby networks, allows SSID selection and masked passphrase entry, and persists connection via `iwd` D-Bus backend.
- SSH Maintenance switch: On-demand toggle to enable or disable SSH on the machine, with connection command details (`ssh greia@<ip>`).
- Remote pairing & companion info: Displays local IP and URL (`http://<ip>:8766`) for the web client.
- Shared platform services: `greia_platform.wifi` and `greia_platform.ssh_maintenance` provide unified implementations reused by the installer, launcher, and Parent API v1.
- Activity Simulator Remote Bridge: Loopback HTTP server (`http://127.0.0.1:8767`) serving an interactive HTML5 web canvas (real-time display, mouse/keyboard forwarding), REST input endpoints, and CLI utility `tools/greia_simulator_ctl.py`.

---

# 5. 2026-08-19 — Platform Unicode, color emoji and Writing

## 3.1 Selected architecture

Accepted architecture:

```text
docs/adr/0030-platform-owned-transactional-system-updates.md
docs/product/SYSTEM_UPDATES.md
docs/development/GREIA_SYSTEM_UPDATE_RELEASE_WORKFLOW.md
```

Core rule:

> **Greia updates itself. The Parents client authorizes, uploads and observes; it is not the privileged updater.**

Target release model is A/B system slots with persistent Greia child/data state outside routine system-slot replacement:

```text
Internet / Parent upload / USB-SD
              |
              v
       signed .greiaupdate
              |
    trust + compatibility preflight
              |
              v
       inactive system slot
              |
        pending reboot
              |
       boot health gate
        /          \
   confirm        rollback
```

Delivery source is intentionally independent from activation. Network download, Parent upload and removable-media delivery feed the same signed bundle/service contract.

Routine system updates must not mutate the active root in place, expose `apt`/`dpkg`/`dd`/mount/GRUB shell operations through the Parent API, or make irreversible shared-data migrations before candidate boot confirmation.

RAUC remains a serious implementation candidate below ADR 0030, **not selected yet**. Measure its package/disk/RAM/process/GRUB/Pi cost against a narrow custom backend before choosing.

## 3.2 Current `.greiaupdate` source contract

Exact source owner:

```text
src/greia_platform/system_updates.py
```

Current portable bundle shape:

```text
release.greiaupdate
├── manifest.json
├── manifest.sig
└── payload.bin
```

Implemented source includes:

- canonical schema-1 manifest;
- exact platform family / architecture / build-profile identity;
- whole-system-slot payload contract;
- signed payload SHA-256 + exact size binding;
- strict/bounded ZIP member contract;
- Ed25519 signature envelope;
- reviewed `cryptography` backend loaded only for signing/verification;
- `SystemIdentity` compatibility check;
- typed `SystemUpdateBackend` variation seam;
- fail-closed `UnavailableSystemUpdateBackend` for current single-root machines;
- `SystemUpdateService` which re-establishes signature + compatibility before backend staging;
- bounded unprivileged `SystemUpdateInbox` for Parent-delivered candidate bytes.

Current inbox properties:

- exact candidate stored under a content digest;
- identical re-upload is idempotent;
- a new candidate cannot overwrite existing content-addressed bytes;
- only one current untrusted candidate is retained;
- stale receive temporaries are cleaned;
- a free-space reserve is checked **before** a large HTTP receive starts;
- the Parent HTTP receiver streams directly into a private staging file on the update-state filesystem;
- successful publication hard-links that exact staged inode to its digest-addressed candidate name, so a Parent upload does not create a second full-size local copy;
- the receive socket has a bounded timeout rather than allowing one upload to hold the single-threaded Parent server indefinitely;
- status hides local filesystem paths;
- receipt verifies bundle structure/payload hash consistency but intentionally reports `signature_verified = false` because the HTTP receiver is not the release-trust boundary.

## 3.3 Current machine/layout boundary — critical

The current release profile:

```text
build/profiles/legacy-x86-i686.toml
```

still says:

```text
[image]
layout = "bios-single-ext4"
```

and does not select `system-update` in its package sets.

Therefore:

```text
system.update.read       = available semantic status
system.update.upload     = false by default; developer/owner lane may enable
system.update.activate   = FALSE
A/B staging              = NOT IMPLEMENTED
boot confirmation        = NOT IMPLEMENTED
rollback                 = NOT IMPLEMENTED
```

This is deliberate. No code may convert unavailable activation into in-place root mutation.

`build/package-sets/system-update.txt` currently reserves `python3-cryptography` for the future production verifier but is intentionally **not selected** by current profiles until footprint/backend evidence is accepted.

## 3.4 Simple release/operator workflow

Canonical tool:

```text
tools/greia_update.py
```

One-time development/release key generation:

```bash
python3 tools/greia_update.py keygen \
  --private-key ./local-secrets/greia-update-ed25519-private.pem \
  --public-key ./out/greia-update-ed25519-public.pem
```

Normal package creation derives compatibility identity from the canonical profile:

```bash
python3 tools/greia_update.py build \
  --payload ./out/greia-system-slot.img \
  --profile-file ./build/profiles/legacy-x86-i686.toml \
  --version 0.14.0 \
  --private-key ./local-secrets/greia-update-ed25519-private.pem
```

Defaults:

```text
release_id = greia-0.14.0
signer     = greia-release-main
output     = out/greia-0.14.0-legacy-x86-i686.greiaupdate
```

Local trust check:

```bash
python3 tools/greia_update.py inspect \
  ./out/greia-0.14.0-legacy-x86-i686.greiaupdate \
  --public-key ./out/greia-update-ed25519-public.pem
```

Push through paired Parent API:

```bash
python3 tools/greia_update.py push \
  ./out/greia-0.14.0-legacy-x86-i686.greiaupdate \
  --url http://greia.local:8766 \
  --bearer "$GREIA_PARENT_BEARER"
```

Current development bootstrap may use `--legacy-token` instead of `--bearer` where explicitly owner-enabled.

Status:

```bash
python3 tools/greia_update.py status \
  --url http://greia.local:8766 \
  --bearer "$GREIA_PARENT_BEARER"
```

**Payload warning:** today's canonical single-root builder does not yet produce a production A/B slot payload. Synthetic/test payloads can exercise format/tooling, but wrapping today's complete `bios-single-ext4` disk image does not create a valid production A/B update.

## 3.5 Parent API/client implementation

Greia OS source:

```text
src/greia_parent/protocol.py
src/greia_parent/update_api.py
build/overlay/etc/systemd/system/greia-parent.service
```

Semantic resources/capabilities now include:

```text
GET  /api/v1/system/update
POST /api/v1/system/update/bundle

system.update.read
system.update.upload
system.update.activate
```

The installed Parent daemon now runs the update-aware API composition, which is a strict superset of the existing package-aware API. It remains:

```text
User=greiapanel
NoNewPrivileges=yes
ProtectSystem=strict
CapabilityBoundingSet=
```

The HTTP process can receive a bounded candidate into its state inbox. It cannot write OS slots, alter boot selection or reboot as update authority.

Because Parent transport is still provisional plaintext HTTP, `system.update.upload` is false by default and may be enabled only on an explicit developer/owner lane. `system.update.activate` remains false regardless.

External HTML client:

```text
frozenpepper/Greia-Parent-App-Html@ccc2355e3e9d758cdad24d73cb56371ca651a95f
```

The client now:

- reads system-update status;
- honors capability negotiation;
- shows a `.greiaupdate` file picker only when upload is advertised;
- posts the original file with the Greia update media type;
- explicitly presents upload as receipt/queueing, not installation;
- has focused API client tests;
- remains dependency-light and has no shell/SSH fallback.

Greia pins that exact Parent revision plus an exact per-file SHA-256 manifest. Runtime remote JavaScript fetch remains forbidden.

## 3.6 System-update tests committed, not executed

Current focused Greia tests:

```text
tests/test_system_updates.py
tests/test_system_update_streaming.py
tests/test_parent_system_updates.py
tests/test_greia_update_tool.py
```

They cover structural/hash rejection, strict signature-envelope types, content-addressed/single-candidate inbox behavior, idempotent re-upload, **same-inode streamed publication/no second local copy**, free-space preflight, unavailable backend fail-closed behavior, compatibility identity, crypto round-trip when available, Parent capability separation, actual current `bios-single-ext4` profile activation false, unprivileged service hardening and profile-derived CLI identity.

External Parent repo adds:

```text
tests/system_update_api.test.js
```

**None of these new update tests have executed in this connector session. No PASS is claimed.**

Required owner-controlled commands:

```bash
PYTHONPATH=src python3 -m unittest \
  tests.test_system_updates \
  tests.test_system_update_streaming \
  tests.test_parent_system_updates \
  tests.test_greia_update_tool -v

make verify
```

External Parent repo:

```bash
npm test
```

## 3.7 Next R13B implementation step

Do not add more network endpoints before the real update backend exists.

Next sequence:

1. evaluate/measure **RAUC A/B versus minimal Greia backend** on the C0/Acer floor;
2. define canonical A/B disk + persistent-data layout across x86 and Pi abstractions;
3. make the canonical release builder emit the exact slot payload consumed by `.greiaupdate`;
4. provision reviewed trusted public update keys into update-enabled images;
5. implement privileged inactive-slot staging below `SystemUpdateBackend`;
6. implement bounded boot-attempt selection, health confirmation and automatic rollback;
7. prove broken/interrupted candidate recovery in VM;
8. prove physical Acer rollback before enabling `system.update.activate`;
9. then add normal device-direct online channel download and USB/SD discovery through the same bundle service.

---

# 4. Platform Unicode/color-emoji/Writing state

Emoji is a platform typography/text capability, not an Activity-local problem.

Current shared source:

```text
src/greia_platform/typography.py
src/greia_platform/emoji_palette.py
src/greia_platform/pygame_ui.py
activities/writing/main.py
```

Selected semantics:

- Nunito Sans remains normal Greia UI;
- Noto Color Emoji is the emoji fallback;
- standard Unicode/UTF-8 persistence;
- Unicode extended grapheme clusters are child-visible editing units;
- Writing has grapheme-safe movement/delete/wrapping/hit-test/truncation and a large shared-palette emoji picker;
- emoji never substitute for trusted Greia Home/Back/system icons.

Author manual:

```text
docs/development/GREIA_ACTIVITY_TEXT_TYPOGRAPHY_AND_EMOJI.md
```

Focused tests remain `tests.test_typography_emoji` and `tests.test_writing_emoji_editing`; run them at current head before claiming current emoji source PASS. Installed font footprint, color rendering, latency/RSS and physical Acer Writing acceptance remain evidence items.

---

# 5. Activity Simulator state

Normative/developer docs:

```text
docs/adr/0029-real-runtime-activity-simulator.md
docs/development/GREIA_ACTIVITY_SIMULATOR.md
```

The simulator remains a thin developer surface over canonical Greia platform services with synthetic HAL/viewport/capability facts. It is not a second platform and not an untrusted-code security sandbox.

Run current focused tests before claiming simulator PASS:

```bash
PYTHONPATH=src python3 -m unittest tests.test_greia_simulator -v
```

Simulator evidence never substitutes for R7 backend/hardware evidence.

---

# 6. R7 and physical hardware state

R7 remains the primary blocking architecture phase.

Current production path remains **provisional Xorg/xinit**; no compositor is selected. ADR 0019 trusted Home/Back and ADR 0020 platform-owned input/controller semantics remain mandatory for the final backend.

Important physical Acer facts retained from current lineage:

- reference Acer Aspire One is BIOS-only;
- its proven live USB path is **syslinux/FAT32**, not GRUB-MBR USB;
- canonical operator path uses `tools/build-live-usb.sh`;
- installed target initramfs must use target-kernel-aware storage policy (`MODULES=most` + guarded storage modules), never chroot/build-host hardware inference;
- developer/test SSH remains `greia / greia`, root SSH denied; normal/release SSH remains fail-closed;
- a fresh 2026-08-19 installer completed on Acer and installed OS reached launcher;
- later source tranches, including emoji and system updates, require a fresh rebuild before physical acceptance is extended to them.

Canonical detail:

```text
docs/INSTALLATION_ISSUES_LOG.md
docs/INSTALLATION_USB_BOOT_POSTMORTEM.md
docs/INSTALLED_OS_BOOT_POSTMORTEM.md
docs/testing/LOCAL_AGENT_START_HERE.md
```

---

# 7. Other current platform state

### Parent security

Initial Parent/admin credential remains `greia / greia` per owner policy, stored/changed through typed Greia credential operations. Parent plaintext LAN HTTP/shared bootstrap remains provisional; production local approval + authenticated encrypted transport is still required.

### Activity packages

A bounded `.greiaactivity` new-install foundation exists, but full R10 update/remove/rollback/signature/revocation/save-migration remains open.

### Awards

ADR 0025/product requirements select platform-owned Reward/Award/Celebration semantics. Award ledger/evaluator/collection/celebration scheduler remain implementation-pending.

### Responsive UI / localization / My Greia

ADR 0026/0027/0028 source families remain part of the shared platform. Current-head aggregate verification is required after later cross-cutting changes.

---

# 8. Exact verification sequence now

On an owner-controlled current Linux checkout, resolve/record the exact `main` SHA and preserve first failure.

### A. New system-update focused gate

```bash
PYTHONPATH=src python3 -m unittest \
  tests.test_system_updates \
  tests.test_system_update_streaming \
  tests.test_parent_system_updates \
  tests.test_greia_update_tool -v
```

### B. Emoji/Writing focused gate

```bash
PYTHONPATH=src python3 -m unittest \
  tests.test_typography_emoji \
  tests.test_writing_emoji_editing -v
```

### C. Simulator focused gate

```bash
PYTHONPATH=src python3 -m unittest tests.test_greia_simulator -v
```

### D. Complete source gate

```bash
make verify
```

### E. External Parent app

At pinned `ccc2355e3e9d758cdad24d73cb56371ca651a95f`:

```bash
npm test
```

Do not claim current-head PASS until these actually run at the recorded revisions.

---

# 9. Exact continuation priorities

1. Execute the new system-update focused tests and fix only genuine failures without weakening trust/activation separation.
2. Execute current emoji/Writing and simulator focused tests.
3. Execute current `make verify`; preserve first failure and record exact SHA.
4. Execute Parent HTML `npm test` at the pinned revision.
5. Continue R7 as the first blocking platform phase.
6. For R13B specifically, measure RAUC vs minimal backend before selecting or adding update runtime dependencies to current profiles.
7. Design/build the A/B + persistent-data image layout and canonical slot-payload builder; do not repurpose the current single-root disk image.
8. Implement/prove privileged staging + boot-confirmation/rollback before enabling `system.update.activate` anywhere.
9. Rebuild/physically accept later source on Acer before extending hardware claims.

---

# 10. Non-negotiable continuation rules

- `main` only unless owner changes branch policy;
- GitHub is canonical source truth;
- no unauthorized GitHub Actions use/inspection;
- no current-head PASS without current-head execution;
- no visible Linux UI during normal child operation;
- R7 remains open and production Xorg/xinit remains provisional;
- trusted Home/Back remain outside Activity authority;
- ordinary Activities do not gain raw `/dev/input` or DRM authority;
- child text remains Unicode/UTF-8 and grapheme-safe;
- system updates are Greia platform authority, not Parent-browser or Activity authority;
- Parent upload never equals signature trust or activation;
- current single-root profiles must keep `system.update.activate = false`;
- never fall back to in-place `apt`, active-root file mutation or raw disk writes to make update UI appear functional;
- private update signing keys never ship in Git, Greia images or Parent clients;
- production update activation requires trusted-key, A/B, boot-health, rollback and shared-data migration evidence;
- source/build/VM/physical evidence scopes remain explicit and honest.

Resolve the exact current `main` SHA before every owner-controlled verification/build run and record that SHA with returned evidence.
