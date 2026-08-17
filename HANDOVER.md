# Greia — Standalone Engineering Handover

**Date:** 2026-08-17  
**Version family:** `0.13.x` development  
**Repository:** `frozenpepper/Greia` (private)  
**Canonical/default/development branch:** `main`  
**Primary blocking platform phase:** **R7 — Direct graphics/session/input architecture**  
**Current cross-cutting tranche:** **Greia Parents API/client foundation — non-closing R12 preparation; production pairing and privileged parent operations remain open**

## Branch policy

The repository owner requires a **single-branch workflow**. `main` is the only development/integration branch. Do not create feature, recovery, archive or work branches unless the owner explicitly changes this policy. Commit coherent work directly to `main`; GitHub is the persistent source of truth.

Historical duplicate ref names may remain because the available connector cannot delete refs. They are not development branches and must not diverge from current `main`. A temporary historical ref named `agent/ubuntu-source-gate-repair` was created during an earlier connector safety repair; keep it at the exact current `main` commit until it can be deleted.

## Hosted execution boundary

Do **not** use, query, trigger, rerun, inspect or download GitHub Actions runs/jobs/logs/artifacts without explicit owner authorization for that specific hosted use. Repository source operations are allowed. Verification runs locally or on an explicitly owner-approved execution environment.

## Current evidence boundary

The latest genuinely executed complete owner-controlled aggregate source gate recorded in this repository is the Ubuntu rerun after the Activity-bytecode validation fix:

```text
host: Intel Mac mini / Ubuntu 24.04.4 LTS / x86_64
repair baseline: f305aed838104cd26b8330eea776a78525e88956 + bytecode-validation fix
profile intended: legacy-x86-i686
focused hardware-enablement suite 1: 77 PASS
focused hardware-enablement suite 2: 32 PASS
full source suite / make verify: 530 tests PASS
project validation: PASS (4 Activities)
source/shell/footprint gate: PASS
aggregate gate exit: 0
```

Evidence documents:

```text
docs/reviews/2026-08-16_UBUNTU_SOURCE_GATE_8D05FBB_SHELL_INPUT_REPAIR.md
docs/reviews/2026-08-16_UBUNTU_ACTIVITY_BYTECODE_VALIDATION_FIX.md
```

Everything committed after that exact executed boundary is **UNPROVEN unless a later section explicitly records an executed result**. In particular, the current Greia Parents foundation added on 2026-08-17 has source tests but those tests have **not executed in the current GitHub-connector environment**. Do not infer a PASS from committed test files or syntax checks.

The user has also reported that a more recent local test attempt encountered failures. Treat the current head as requiring a fresh owner-controlled source-gate run before using it as a release/build acceptance baseline. Preserve the first genuine failure instead of weakening tests.

## 2026-08-17 — Greia Parents API/client foundation

Architecture/product authority:

```text
docs/adr/0022-parent-management-api-client-pairing-and-privilege-boundary.md
docs/product/PARENT_MANAGEMENT.md
docs/architecture/GREIA_PARENT_MANAGEMENT.md
```

Documentation map and README were updated to make these first-class project contracts. The active implementation plan now explicitly permits this as a **non-closing R12 preparatory foundation** without bypassing the R10/R11/package/backup prerequisites of full R12.

### Core product decision

The first parent client is a small responsive HTML application served directly by Greia, but the durable product boundary is the **Greia Parent API**. A later iOS/Android/desktop client must use the same discovery, pairing, authentication, resource IDs, capability negotiation and semantic operations.

```text
Greia Parents HTML client
future native parent client
            │
            │ same versioned protocol
            ▼
      Greia Parent API
      (unprivileged)
            │
            ├── profiles
            ├── Activity inventory / future package operations
            ├── progress/status
            ├── hardware/settings
            ├── paired devices
            └── future maintenance operations
                    │
                    ▼
         typed Greia services/brokers
                    │
                    ▼
             Linux adapters
```

The Parent API must not become a generic root RPC, arbitrary shell bridge, package-manager frontend or filesystem-management API.

### Implemented source

New/changed source:

```text
src/greia_parent/protocol.py
src/greia_parent/credentials.py
src/greia_parent/api_server.py
src/greia_parent/web_client.py
src/greia_parent/server.py                  # retained legacy/domain compatibility surface
build/overlay/etc/avahi/services/greia-parent.service
build/overlay/etc/systemd/system/greia-parent.service
tests/test_parent_api.py
```

`greia-parent.service` remains unprivileged as `greiapanel`, retains the existing strict systemd sandbox, and now starts:

```text
python3 -m greia_parent.api_server --bind 0.0.0.0 --port 8766
```

The HTML client is served at `/` after authentication and performs management through `/api/v1`. The previous server-rendered parent page remains available at `/legacy` during migration/troubleshooting.

### Initial API-v1 foundation

Current namespace:

```text
/api/v1
```

Implemented routes include:

```text
GET    /api/v1/meta
GET    /api/v1
GET    /api/v1/system
GET    /api/v1/profiles
POST   /api/v1/profiles
PATCH  /api/v1/profiles/{id}
DELETE /api/v1/profiles/{id}
GET    /api/v1/activities
GET    /api/v1/settings/hardware
PUT    /api/v1/settings/hardware
POST   /api/v1/settings/hardware/reset
GET    /api/v1/progress
GET    /api/v1/devices
DELETE /api/v1/devices/{id}
POST   /api/v1/pairing/bootstrap             # PROVISIONAL bootstrap only
```

Requests are bounded JSON objects. API errors use a typed JSON error envelope. Activity inventory exposes semantic Activity metadata but deliberately does not expose package filesystem roots or runtime entrypoints.

### Capability negotiation

The API reports what is actually implemented instead of letting clients guess from architecture/model.

Currently advertised as available:

```text
profiles.manage
activities.read
progress.read
settings.input
settings.display
paired_devices.manage
```

Currently advertised as unavailable:

```text
activities.install
backup.manage
settings.audio
network.manage
maintenance.ssh
```

A false capability is never permission for the HTML client to emulate the operation with shell commands.

### Parent-device credentials

`ParentDeviceCredentialStore` introduces independently revocable parent-client credentials:

- bounded to 16 paired devices;
- each client receives its own high-entropy bearer token;
- the raw token is returned only when issued;
- persistent state stores only a SHA-256 verifier/digest plus bounded non-secret device metadata;
- one device can be revoked without rotating every other parent's credential;
- state is bounded, validated, atomically replaced and mode `0600`;
- malformed/symlinked/oversized credential state fails closed.

Bearer credentials can authenticate through `Authorization: Bearer ...`; a dedicated browser cookie name is also understood by the API layer.

The old single shared `parent-pairing-token` remains temporarily available only as a **transitional bootstrap mechanism** so the new API can be exercised before the Greia-local pairing UI exists.

### Discovery

Normal network-capable images now ship an Avahi service declaration:

```text
_greia-parent._tcp
port: 8766
TXT: api=1
TXT: path=/api/v1
TXT: product=greia
```

No secret is placed in mDNS. Discovery is convenience only; mDNS is not authentication.

### Production pairing still required

The accepted target first-pairing flow is not yet implemented:

```text
parent chooses Add a Greia
→ client discovers nearby Greia or uses explicit connection information
→ parent opens Pair a device on the Greia screen
→ Greia displays a short-lived QR challenge + numeric fallback
→ requesting client presents challenge
→ Greia shows requesting device and asks Allow / Deny locally
→ approved client receives its own revocable credential
```

Required production properties still open:

- bounded short-lived challenge lifetime;
- replay/attempt protection;
- explicit local Greia-screen approval;
- QR + numeric fallback presentation;
- device identity binding;
- authenticated encrypted transport;
- browser/native reconnect behavior;
- resource measurements on the C0/Acer floor.

The current `http://<device>:8766` transport is explicitly **PROVISIONAL**. Do not claim production credential security merely because traffic is on a home LAN.

### SSH policy

Normal/release Greia still keeps SSH **disabled by default**. `first-boot` intentionally leaves SSH host keys absent until a parent explicitly enables SSH.

Greia Parents does **not** use SSH as its management protocol.

The eventual Parent App SSH maintenance control must cross a narrow typed privileged service/broker and enforce at least:

```text
SSH off by default
key authentication only
root SSH login disabled
password SSH authentication disabled
dedicated greiaadmin identity
parent can enable/disable and replace/revoke key material
```

No release SSH enable/disable implementation has landed in this Parent foundation yet. The existing `developer-remote` profile/package path remains separate and development-only.

### Parent-management functionality represented in product design

The accepted parent-management product scope now includes:

- create/rename/delete child profiles;
- select/change avatars/icons;
- set/replace/remove simple child passwords and masking preference;
- installed Activity inventory;
- future Activity install/update/remove via R10 package service;
- mouse/touchpad/tap/natural-scroll settings;
- display resolution and future brightness where supported;
- future audio volume/mute/output through Audio Service;
- future Wi-Fi/network management through Network Service;
- system health/storage/diagnostics;
- future backup/restore through R11;
- future parent-controlled SSH maintenance;
- paired-device listing/revocation;
- later OS/runtime update/recovery through the typed platform services.

The HTML UI must remain a client of those services through the Parent API. It must not contain Linux-specific management knowledge such as `xinput`, `xrandr`, ALSA/PipeWire commands, `iwd` command lines, direct `apt`, arbitrary `sudo`, or host filesystem edits.

### Tests/evidence for Parent foundation

`tests/test_parent_api.py` was added for:

- raw-token non-persistence;
- independent device authentication/revocation;
- device-count/name bounds;
- capability truthfulness;
- bootstrap/Bearer behavior;
- Activity metadata path non-disclosure;
- HTML use of `/api/v1` rather than legacy form mutation paths;
- `_greia-parent._tcp` advertisement;
- normal-image separation from `developer-remote`/SSH.

The authored Python source was syntax-checked during implementation. **No current repository test run or `make verify` was executed here; no PASS is claimed.**

Foundation implementation/documentation commits include:

```text
50591969e11278bb1e767cf3e2da80cdb0b7e192  parent: establish API-first Greia Parents foundation
10fc96dba2387f3fe7a6641eccec5cf79d07a05e  docs: define Greia Parents API-first product surface
e04aa162ee78c0e42b7b353975ad957f4f631776  docs: map Greia Parents protocol and product authority
469fb590d175ad81c3b67cedbac1479338e3edc8  plan: record Greia Parents API foundation
```

Resolve current `origin/main` before starting any new work; this handover update itself advances `main` once more.

## 2026-08-17 — Boot animation state

The direct Greia Plymouth animation remains integrated:

- one canonical source at `build/overlay/etc/plymouth/themes/greia/`;
- 52 direct RGB PNG frames, each 222x600;
- 7 fps via `Plymouth.SetRefreshRate(7)`;
- no Base85/XOR/delta/build-time frame reconstruction;
- live installer stages the same canonical theme rather than a duplicate source copy;
- experimental `runtime/boot-animation`, `build/boot-animation` and reconstruction hooks were removed;
- physical Acer playback remains unproven until actual boot evidence exists.

Do not restore the discarded generator/chunk approach.

## ADR 0021 — automatic hardware enablement

Architecture owner:

```text
docs/adr/0021-automatic-hardware-enablement-and-capability-discovery.md
```

Current implementation review / source acceptance material:

```text
docs/reviews/2026-08-15_HARDWARE_ENABLEMENT_IMPLEMENTATION_REVIEW.md
docs/testing/2026-08-15_HARDWARE_ENABLEMENT_SOURCE_ACCEPTANCE.md
```

### Product/architecture rule

Greia does **not** maintain a laptop/model driver database. Linux owns kernel driver binding. Greia owns bounded discovery, trusted firmware/support-package resolution, installation policy and semantic capability classification.

```text
physical hardware
      ↓
Linux kernel / udev / kmod
      ↓
bounded Greia sysfs inventory
      ↓
bound-driver firmware declarations
+ isenkram signals
+ x86 microcode policy
      ↓
frozen Debian firmware-provider metadata
      ↓
verified offline support repository on installer media
      ↓
fail-closed machine-specific target package plan
      ↓
read-only local APT transaction
      ↓
initramfs / GRUB regeneration
      ↓
Greia HAL / semantic capabilities
```

Core source:

```text
src/greia_platform/hardware_enablement.py
src/greia_installer/hardware_support.py
src/greia_installer/hardware_enablement.py
src/greia_installer/hardware_support_install.py
src/greia_installer/engine.py
```

Operator/build tools:

```text
tools/inspect_hardware_enablement.py
tools/build_hardware_support_pool_manifest.py
tools/finalize_hardware_support_pool.py
tools/verify_hardware_support_pool.py
build/populate-hardware-support-pool.sh
build/install-live-hardware-firmware.sh
```

The live installer carries broad verified firmware support while the final installed target receives only the machine-specific support package plan where possible. Resolution is based on Linux/device metadata and frozen Debian provider metadata, not Greia-authored per-model tables.

The hardware support pool is bounded, integrity-checked, read-only at point of target installation, and used through a temporary local APT source. Package-removal plans are forbidden. Raw modalias/sysfs/driver evidence is not persisted in ordinary install records.

Persistent installed-system hotplug package installation remains deferred until the installer path passes its source/build/VM gates. Do not add a continuously running arbitrary `apt` agent or vendor installer path.

## Current installer / SD route

Canonical legacy SD installer build:

```bash
sudo bash build/build-legacy-x86-sd-installer.sh out
```

The generic `legacy-x86-i686` profile is architecture/family based; do not tailor the OS image to one Acer model.

Current no-USB Acer bootstrap remains:

```text
Acer BIOS
→ internal antiX
→ antiX GRUB entry prepared from Greia SD helper
→ Greia kernel/initrd/live system on SD
→ graphical fail-closed installer
→ final Greia on internal disk
```

`tools/prepare-antix-sd-boot.sh` lives on the installer media and infers the SD from its own mounted path. The helper is for the current antiX bootstrap only; installed Greia still needs a Greia-owned reinstall/update-from-media path in a later recovery tranche.

Before any SD/raw-media operation:

- use a genuinely passing current source gate;
- build on the owner-controlled compatible Linux host;
- verify generated image SHA-256;
- positively identify the intended whole SD device;
- raw-write only that device;
- perform physical read-back SHA verification.

## Existing Wi-Fi installer state

Installation-time Wi-Fi remains optional and offline-first:

```text
Welcome
→ target disk
→ input/screen settings
→ Wi-Fi (optional)
→ final confirmation
→ installation
```

Visible Open and WPA/WPA2/WPA3-Personal are the initial cases. Enterprise/802.1X remains deferred; WEP unsupported; hidden/manual SSID is follow-up. Credentials must remain absent from argv/log/install records. Physical Wi-Fi acceptance remains open.

## Developer remote-control path

`tools/greia_remote.py` and explicit development profiles provide SSH-based remote engineering controls for test images. This is not the release Parent API and must stay separate.

Development remote controls include bounded status/screenshot/log/input/Activity deployment/service restart/reboot/poweroff/shell capabilities. Normal/release profiles do not include `developer-remote` merely because these tools exist.

## Other active R7 state

- Production display remains provisional Xorg/xinit; no compositor selected.
- ADR 0019 trusted system Home/Back source exists; concrete production backend remains unproven.
- ADR 0020 runtime-neutral input/controller semantic source exists.
- `ShellInputController` contains the exact-deadline floating-point repair recorded in the Ubuntu source-gate review.
- Production Activity input broker and physical controller acceptance remain open.
- Writing/Painting remain source-implemented; current hardware/runtime evidence remains incomplete.
- Direct KMSDRM/compositor/session work remains evidence-gated and must not be bypassed by deepening X11.

## Exact continuation priorities

The Parent API foundation is now persisted, but **R7 remains the primary blocking architecture phase**. Do not reinterpret the parent work as closing or skipping R7/R10/R11/R12.

Immediate legitimate work sequence:

1. Resolve exact current `origin/main` and run the current source gate on the owner-controlled Linux checkout. Include `tests/test_parent_api.py`. Preserve the first real failure; do not weaken tests.
2. Continue the already defined installer/SD/hardware path only after the source gate genuinely passes at that exact head.
3. Continue R7 direct graphics/session/input evidence and architecture work according to the active plan.
4. For the next Greia Parents slice, implement the **local short-lived pairing challenge + Greia-screen Allow/Deny flow** and complete the encrypted transport/device-identity design before calling pairing production-safe.
5. Define/implement a narrow typed parent privileged broker before enabling SSH, Activity package installation, audio/network administration, backup/restore or update controls. Reuse R10/R11/HAL services; no shell shortcuts.

## Non-negotiable continuation rules

- `main` only unless the owner explicitly changes branch policy;
- GitHub is canonical source truth;
- no unauthorized GitHub Actions execution or inspection;
- no visible Linux UI during normal child operation;
- no per-model Greia driver database;
- no arbitrary vendor drivers/downloaders;
- no raw hardware identifiers exposed to Activities;
- broad compatibility payload belongs primarily on installer media, not every C0 target;
- automatic package resolution remains bounded, frozen/signed, fail-closed and no-removal;
- source/build/VM/physical evidence boundaries remain explicit and honest;
- normal/release SSH stays disabled unless a parent deliberately enables the future typed maintenance capability;
- Greia Parents and future native clients use the same semantic Parent API; no client receives a private shell/root path;
- current plaintext Parent transport/shared-token bootstrap are provisional and must not be described as production security;
- preserve ADR 0019/0020 trusted system-chrome/input constraints while expanding hardware support;
- do not claim current source PASS until a current checkout actually runs the gate successfully.
