# Greia — Standalone Engineering Handover

**Date:** 2026-08-17  
**Version family:** `0.13.x` development  
**Repository:** `frozenpepper/Greia` (private)  
**Canonical/default/development branch:** `main`  
**Primary blocking platform phase:** **R7 — Direct graphics/session/input architecture**  
**Current cross-cutting state:** **ADR 0025 Awards/badges/celebrations architecture and the Greia visual-style/Nunito Sans direction are accepted/documented but unimplemented; Greia Parents API/client foundation remains the latest substantive code tranche**

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

## 2026-08-17 — Open Activity ecosystem, catalogue and licensing policy

This is a **documentation/architecture policy tranche only**. It does not implement R10 package distribution, a store, payments, entitlements, signing, a native mobile app or new Activity manifest fields, and it does not advance/close R7.

New authority:

```text
docs/adr/0023-open-activity-ecosystem-and-official-catalogue-boundary.md
docs/adr/0024-project-licensing-and-trademark-boundary.md
docs/product/ACTIVITY_ECOSYSTEM_AND_DISTRIBUTION.md
docs/governance/LICENSING_AND_TRADEMARK.md
```

README and `docs/DOCUMENTATION.md` were updated to surface those decisions and their authority boundaries.

### Ecosystem decision

Greia is now explicitly an **open platform, not an open-core product**.

Permanent architectural/product constraints:

- the OS, Activity interfaces, authoring knowledge and supported independent installation path remain available without payment;
- human and agent Activity authoring are public first-class interfaces, not hidden project knowledge;
- a future Official Greia Catalogue is optional curated distribution infrastructure, not the only technically supported install source;
- parents retain an explicit supported non-catalogue/sideload path once R10 `.greiaactivity` installation exists;
- independent installation still passes normal package validation, sandbox, compatibility and parent approval — no autorun/bypass interpretation;
- package provenance/trust, compatibility, price/entitlement and source-code license remain separate concepts;
- free and paid Activities may coexist, including paid open-source Activities;
- third-party Activity authors choose licenses for their independent work subject to incorporated dependencies and voluntary catalogue terms;
- child-facing advertising, behavioral tracking and purchase-pressure mechanics are rejected for the official ecosystem direction;
- purchases/entitlements belong to authenticated parent-facing UI;
- a future native Greia Parents phone/desktop app may be paid, but essential management must remain available through a free Greia-controlled path and all clients use the same ADR-0022 Parent API;
- core installed Activity use/local saves/progression/parent management remain local/offline-first; catalogue/cloud outages must not disable the child's installed computer.

R10 package/signing/catalogue implementation must preserve these boundaries.

### Licensing decision

ADR 0024 selects the following policy:

```text
Greia-owned software                  MPL-2.0 default
Greia-owned SDK implementation       MPL-2.0 default
copyable future scaffolds/templates  Apache-2.0 when explicitly marked
Greia-owned documentation            CC BY 4.0 default
confirmed Greia-owned reusable media intended CC BY 4.0 default unless marked otherwise
third-party code/media                retain original applicable rights/licenses
independent Activities                author/publisher chooses
Greia names/logos/trust marks         separate trademark/use policy; not granted by code/content licenses
```

This is intentionally **file-level/platform reciprocity without forcing unrelated Activities into Greia's license**.

MPL was chosen over MIT/Apache as the platform default because Greia wants distributed modifications to covered Greia source files to remain open, while avoiding a stronger whole-work GPL/AGPL boundary around independently licensed Activities/integrations.

Copyable boilerplate may be Apache-2.0 so generated/copied starter code does not accidentally impose MPL on an Activity author's own new files.

### Licensing state is selected, not mechanically complete

Do **not** claim that every existing repository byte is already MPL/CC BY licensed.

Before the repository or an official distribution is made public, the project must complete a licensing/provenance gate including:

- verify rights/provenance for existing Greia-authored source;
- inventory third-party source/snippets;
- inventory distributable icons/images/audio/fonts and their rights;
- add canonical full license texts;
- add a clear top-level licensing notice plus directory/file exceptions;
- add SPDX identifiers where practical;
- preserve upstream/third-party notices and source obligations in OS images;
- explicitly mark permissive copyable templates/scaffolds;
- create/review the public trademark/use policy for the actual legal entity/jurisdictions;
- separately review marketplace/payment/privacy/tax obligations before operating a paid catalogue.

Current correct wording is:

> **license policy selected; public-release licensing/provenance audit pending**

not “the entire tree is already relicensed”.

### Tests/evidence for this policy tranche

No implementation changed. No source/VM/hardware test was run or required for the documentation-only policy decisions. Repository paths/authority were reviewed through the GitHub connector. Existing post-Ubuntu implementation remains UNPROVEN until the owner-controlled source gate runs at current head.

Policy commits in this tranche include:

```text
6db7d1656691f17b10b5f2ebb58b7bb731b56b71  docs: define open Activity ecosystem and catalogue boundary
6409576d0fe57cea8cfb115dfc4bc9cff58e9e13  docs: select Greia licensing and trademark boundary
44adad5d309bd9dd7395a69adccf3276c6a3e859  docs: define Activity ecosystem product policy
b43720f2306fa92b8cc4ba344e110c6bb6ffa0fd  docs: add licensing and trademark policy
d113ff7a9f87e60911b96fc10b113a355fc23e39  docs: surface ecosystem and licensing decisions
2726d1ff789e24d215ae5276a1b5f8f58c9bae0e  docs: map ecosystem and governance authority
```

## 2026-08-17 — Platform-owned Awards, badges and celebrations

This is a **documentation/architecture/product tranche only**. It does not implement an Award ledger, Award manifest schema, celebration scheduler/overlay, Shell badge collection, Parent API achievement resource, or new tests. It does not advance or close R7.

New authority:

```text
docs/adr/0025-platform-owned-awards-badges-and-celebrations.md
docs/product/AWARDS_BADGES_AND_CELEBRATIONS.md
```

The following main documents were updated to surface and synthesize the decision:

```text
README.md
docs/DOCUMENTATION.md
docs/architecture/GREIA_ARCHITECTURE.md
HANDOVER.md
```

### Core Award model

Greia now explicitly distinguishes:

```text
Reward      = quantity/balance such as stars
Award       = durable named achievement; badge is the initial presentation form
Celebration = transient Greia presentation such as badge reveal or NEW BEST
Collection  = child-facing Greia place where earned Awards are revisited
```

ADR 0017 remains the progression foundation: Activities emit declared factual events/scores; Greia owns sessions, best-score comparison, progression policy and global reward economics. ADR 0025 extends the same authority boundary to durable Awards.

Permanent selected constraints:

- Activity runtime code does **not** receive direct `grant_badge()` / Award-ledger write authority;
- arbitrary event payload fields such as `badge_id` or `award_id` do not authorize a grant;
- Greia evaluates trusted progression evidence and grants Awards transactionally/idempotently;
- personal-best detection stays Greia-owned using the existing higher/lower-better semantics;
- a personal-best improvement normally creates a celebration, not endless permanent badge spam;
- Activity-specific Award definitions may eventually be declarative package metadata bound only to that Activity's validated evidence;
- Greia-wide/cross-Activity Awards are platform policy and cannot be defined/granted by one Activity;
- earned Awards are profile-scoped, offline-first and not revoked by ordinary Activity content;
- earned Awards survive Activity uninstall and logical backup/restore even if the originating Activity is absent;
- backup/storage must preserve enough stable portable presentation information or a stable fallback so the collection does not depend on a removed package path;
- core Award design rejects streak-loss anxiety, expiring badges, advertising-for-awards, purchasable achievement badges, artificial FOMO, public leaderboards by default and screen-time-maximizing reward loops.

### Grant and presentation are deliberately separate

A valid Award must be committed immediately from trusted evidence, while its visual ceremony is scheduled separately:

```text
validated event / score
      ↓
progression/Award transaction commits
      ↓
bounded celebration request
      ↓
Greia presentation scheduler chooses safe moment
      ↓
short visual/audio/spoken celebration
```

This prevents a badge popup from causing a child to fail a timed puzzle, interrupting a drawing gesture, stealing input during text entry, or otherwise sabotaging the task.

A crash/reboot after the grant but before presentation must not lose the Award. Conversely, recovery must not replay an unbounded backlog of stale ceremonies.

### R7 impact

ADR 0025 is now a **mandatory architecture constraint on the selected R7 display/session design**:

- the backend must not give Activities authority over the official Greia Award celebration;
- Greia must have a bounded transient-presentation capability above Activity content **or** an equivalent safe Greia-controlled deferred presentation path;
- mandatory Home/Back remains visible/authoritative and cannot be obscured/disabled by a celebration;
- this requirement does **not** justify a desktop notification center, arbitrary windows, unbounded z-order or general compositor/window-manager features;
- resource cost must remain acceptable on the Acer/C0 floor.

The active plan remains the ordering authority. The Awards feature itself must not be used as an excuse to jump ahead of the current R7 blocking phase; rather, R7 must select a display/session architecture that does not foreclose ADR 0025.

### Future R10/R11/Activity-author implications

When those tranches are implemented:

- R10 package work must define bounded/validated Activity-scoped Award metadata/assets if that capability is introduced; do not invent current `activity.toml` fields before source owns them;
- R11 `.greiabackup` must include logical Award state and sufficient presentation/fallback state for source-Activity-absent restore;
- Activity authoring remains fact-first: `level.completed`, `painting.saved`, `perfect_run.completed`, `score.submitted`, etc.; not `give_child_10_stars`, `set_badge_earned`, or `unlock_global_hat`;
- the authoritative badge ceremony and collection remain Greia-owned across Python/Web/future runtimes.

### Tests/evidence for this tranche

No implementation changed and no source/VM/hardware test was run. **Do not describe Awards/badges/celebrations as an implemented Greia runtime feature.** Current correct wording is:

> **Award/badge/celebration architecture selected and product requirements accepted; implementation/evidence pending.**

Documentation commits include:

```text
651dd72c20f84fc6bb773622bb850fa050f0c558  docs: define platform-owned awards and celebrations
a670ae43f56e171996d35f907dc0866fdc6406ce  docs: define child awards and badge collection experience
24bb49024983fd533575746e24ff20b0e9296c01  docs: surface Greia awards architecture
5ef29fdb574ceb009b3fca237e62a4c1aa48c41e  docs: map awards product and architecture authority
35894e4499045e79e602cb55f98af292a76319c1  docs: integrate awards into living architecture
```

## 2026-08-17 — Visual style and typography direction

This is a **documentation/design-selection tranche only**. It does not vendor fonts, alter runtime theme/source code, implement typography tokens, change an Activity API, or advance/close R7.

New design authority:

```text
docs/design/GREIA_VISUAL_STYLE_GUIDE.md
```

The existing production-art inventory remains complementary:

```text
docs/design/GREIA_VISUAL_ART_AND_CORE_ASSET_REQUIREMENTS.md
```

The style guide now owns reusable visual-language and typography direction; the asset document owns the inventory of concrete logos, characters, icons, backgrounds, effects, and state artwork.

### Selected typography

The default Greia interface family is **Nunito Sans**.

Selected direction:

```text
body         Nunito Sans Regular
controls     Nunito Sans SemiBold
titles       Nunito Sans Bold
celebration  Nunito Sans ExtraBold
```

The initial deployment direction is to use a small set of **static weights**, not make variable-font support a C0/Acer requirement.

The visual goal remains **warm and playful without looking like baby software**. Greia should obtain personality primarily from hierarchy, illustration, shape, motion, sound and celebration rather than novelty fonts or a different typeface for every surface.

### Licensing/provenance boundary

Nunito Sans is third-party font software under **SIL Open Font License 1.1 (OFL-1.1)**. When it is actually bundled, Greia must pin a traceable upstream version/source, preserve the upstream copyright/OFL notice, record whether files are modified, and list the font in the third-party provenance inventory required by ADR 0024.

Do not treat Nunito Sans as Greia-owned MPL software or CC BY artwork.

### What is not implemented yet

Do **not** infer any of the following from the design selection:

- Nunito font files are already present in the repository/image;
- `runtime/theme-defaults.toml` already contains typography roles;
- a shared font cache/loader already exists;
- first-party Activities already consume a semantic typography API;
- proposed pixel-size targets have passed physical Acer/800×600/1024×600 readability testing;
- an accessibility alternate font has already been selected.

Those are future source/provenance/evidence steps.

### Implementation direction when scheduled

When typography integration is actually implemented:

1. pin a specific upstream Nunito Sans version/source;
2. vendor only the justified static weights/glyph coverage;
3. preserve OFL-1.1 copyright/license material;
4. add the font to ADR-0024 provenance/third-party notices;
5. expose semantic platform typography roles rather than arbitrary hard-coded font paths;
6. use one bounded shared cache/load path rather than per-consumer/per-frame font loading;
7. validate English/Italian accents and young-reader ambiguous glyphs;
8. validate real layouts at 800×600 and 1024×600, including physical Acer-class evidence;
9. update the Activity authoring skill only when an actual Activity-facing typography contract exists.

Current correct wording is:

> **Nunito Sans selected as the default Greia interface typeface; font bundling/typography API/readability evidence pending.**

Documentation commits in this tranche include:

```text
48d59f4950c28823887b4176dc849364b7bf232f  docs: establish Greia visual style and typography guide
2e486225ba2d14e4c66cb4c8f094bac65516988c  docs: surface visual style and Nunito Sans choice
5fe192fd3668559e2be4c3a92bae0d0f4a90d6a0  docs: link asset requirements to visual style authority
1b72fcd4301837af0764f28e851d74bb1180b417  docs: register visual design authority and typography ownership
```

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
- **ADR 0025 now additionally requires the selected display/session design to preserve a bounded Greia-owned Award/celebration presentation path or safe Greia-controlled deferred equivalent without weakening Home/Back; this requirement is architecture-selected but unimplemented/unproven.**
- `ShellInputController` contains the exact-deadline floating-point repair recorded in the Ubuntu source-gate review.
- Production Activity input broker and physical controller acceptance remain open.
- Writing/Painting remain source-implemented; current hardware/runtime evidence remains incomplete.
- Direct KMSDRM/compositor/session work remains evidence-gated and must not be bypassed by deepening X11 or by introducing a desktop notification/window layer for Awards.

## Exact continuation priorities

The Parent API foundation, ecosystem/licensing policy, Awards architecture and visual-style/Nunito Sans direction are now persisted, but **R7 remains the primary blocking architecture phase**. Do not reinterpret any documentation tranche as closing or skipping R7/R10/R11/R12.

Immediate legitimate work sequence:

1. Resolve exact current `origin/main` and run the current source gate on the owner-controlled Linux checkout. Include `tests/test_parent_api.py`. Preserve the first real failure; do not weaken tests.
2. Continue the already defined installer/SD/hardware path only after the source gate genuinely passes at that exact head.
3. Continue R7 direct graphics/session/input evidence and architecture work according to the active plan, **while treating ADR 0025 as a mandatory selection constraint: the backend must not foreclose bounded Greia-owned celebration presentation or safe deferred presentation, and Home/Back must remain authoritative.**
4. For the next Greia Parents slice, implement the **local short-lived pairing challenge + Greia-screen Allow/Deny flow** and complete the encrypted transport/device-identity design before calling pairing production-safe.
5. Define/implement a narrow typed parent privileged broker before enabling SSH, Activity package installation, audio/network administration, backup/restore or update controls. Reuse R10/R11/HAL services; no shell shortcuts.
6. When R10 package/distribution work begins, treat ADR 0023/0024/0025 as mandatory design constraints: keep independent parent-authorized installation, keep provenance/license/price separate, do not invent child commerce, do not claim public-release licensing complete before the provenance/license audit, and define Activity-scoped Award metadata only through a bounded validated source-owned schema if/when that feature is implemented.
7. When R11 backup work begins, include logical Award state/presentation fallback required by ADR 0025 so earned badges survive cross-architecture restore with the source Activity absent.
8. **Do not jump ahead to implementing the full Awards subsystem merely because ADR 0025 now exists.** When implementation is scheduled, build it on ADR 0017 progression evidence and the selected R7 presentation seam, preserving current active-plan ordering.
9. When visual/typography integration is scheduled, treat `docs/design/GREIA_VISUAL_STYLE_GUIDE.md` as the design authority: use Nunito Sans as the default family, preserve its OFL-1.1 provenance, prefer the selected static weight subset initially, and introduce a shared semantic/bounded typography path rather than hard-coded font copies in each consumer. Do not claim font integration or physical readability before it is actually implemented/tested.

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
- **preserve ADR 0025 Award authority: Activities report facts/scores and do not directly mutate durable Awards or the official Greia collection; official celebration is Greia-owned; grant and presentation remain separate; earned Awards survive uninstall/backup; core achievement design avoids manipulative streak/FOMO/advertising/purchase mechanics;**
- **do not describe Awards/badges/celebrations as implemented until the ledger/evaluation/presentation/collection source and required evidence actually exist;**
- **preserve the visual-style authority in `docs/design/GREIA_VISUAL_STYLE_GUIDE.md`: default interface family is Nunito Sans; the font remains OFL-1.1 third-party material; do not describe it as bundled or the typography API as implemented until source/provenance/evidence actually exists;**
- the official catalogue must remain optional distribution infrastructure rather than the only supported Activity installation path;
- child-facing advertising/purchase-pressure mechanics remain outside the official Greia ecosystem direction;
- Activity provenance/trust, compatibility, license and price/entitlement remain distinct concepts;
- third-party Activity authors are not forced into Greia's platform license merely by using public Activity APIs;
- license policy is selected but existing repository/public-distribution licensing must not be described as mechanically complete until the audit/license-text/SPDX/provenance gate is done;
- do not claim current source PASS until a current checkout actually runs the gate successfully.
