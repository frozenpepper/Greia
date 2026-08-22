# Greia Setup Index

**Status:** living workstation, agent and operator setup entry point  
**Last reviewed:** 2026-08-22  
**Canonical repository:** `frozenpepper/Greia`

This is the first file a human contributor or software agent should use when preparing a machine to work on Greia.

It does not replace the narrower manuals. It selects the correct setup path, points to the authoritative procedure for each role, and makes incomplete setup surfaces visible instead of allowing agents to improvise.

## 1. Read before installing anything

From the Greia repository root, read in this order:

```text
AGENTS.md
SETUP.md
docs/DOCUMENTATION.md
HANDOVER.md
docs/agents/GREIA_AGENT_OPERATIONS.md
```

Then read the skill and manuals for the role being configured.

Do not install packages, create virtual environments, download model weights, enable SSH, write removable media, or perform a destructive OS installation merely because a tool exists in the repository. Use the narrow role profile below and preserve the security/evidence boundaries in `AGENTS.md`.

## 2. Setup principles

1. **The repository copy is canonical.** Skills and setup documentation must be read from the checked-out Greia revision, not from a stale global copy or chat transcript.
2. **Choose a role profile.** An Activity author does not need the raw-image build stack; an OS builder does not automatically need local voice models.
3. **Keep machine-local material outside Git.** Virtual environments, model weights, caches, private keys, generated scratch audio, simulator state and build work roots stay outside the repository.
4. **Do not silently auto-install privileged dependencies.** Inspect the host, report missing prerequisites, and obtain owner approval before broad package-manager or root changes.
5. **Verify the exact checkout.** Record the source SHA for retained simulator, image or physical evidence.
6. **Developer remote access is opt-in.** It belongs only to explicit developer images. Normal/release Greia keeps SSH off.
7. **A setup command succeeding is not product evidence.** Source, simulator, VM/image and physical evidence remain distinct.

## 3. Common repository bootstrap

Every role starts with:

```bash
git clone <authorized Greia repository URL>
cd Greia

git status --short
git rev-parse HEAD

python3 --version
git --version
make --version
```

Read the files in section 1 before making changes.

Run the provider-free repository gate when the host has the required project Python dependencies:

```bash
make verify
```

A failed gate must be investigated. Do not weaken validation or delete failing tests to call the workstation ready.

## 4. Canonical repository skills

Greia currently owns these repository-local skills:

```text
skills/greia-activity-authoring/SKILL.md
skills/greia-visual-authoring/SKILL.md
```

The Activity skill also delegates to:

```text
skills/greia-activity-authoring/CORE.md
skills/greia-activity-authoring/VOICE_GENERATION.md
```

### Agent integration rule

An agent must load the skill directly from the active Greia checkout whenever its platform supports repository-local instructions.

When an agent platform requires skills in a separate user directory, create a symlink or an explicitly managed copy only if that platform cannot consume the repository path. Record the source checkout and refresh the installed copy after Greia updates. Never edit the detached copy as the authority.

There is not yet a cross-agent automatic skill installer. Until one exists, successful setup means the agent can identify and read the repository skill files above before performing the governed work.

## 5. Role profiles

### 5.1 Activity creator — standard profile

Use this for creating, modifying, validating and testing Python/Pygame Activities.

Read:

```text
skills/greia-activity-authoring/SKILL.md
skills/greia-activity-authoring/CORE.md
docs/development/GREIA_ACTIVITY_SIMULATOR.md
docs/development/GREIA_ACTIVITY_TEXT_TYPOGRAPHY_AND_EMOJI.md
docs/product/ACTIVITY_INPUT_STANDARDS.md
docs/product/ACTIVITY_SYSTEM_NAVIGATION.md
```

Host needs:

```text
Python 3
Pygame and the current Greia Python dependencies
Tk support for the simulator control plane
make
```

Start the real-runtime desktop simulator:

```bash
python3 tools/greia_simulator.py
```

Optional isolated state:

```bash
python3 tools/greia_simulator.py \
  --state-dir ~/.greia-simulator-my-project
```

Validate one Activity:

```bash
PYTHONPATH=src python3 tools/validate_activity.py activities/<activity-directory>
```

Run the focused simulator contract gate:

```bash
PYTHONPATH=src python3 -m unittest tests.test_greia_simulator -v
```

Then run `make verify` before claiming the source tranche is complete.

### 5.2 Visual author — optional extension

Use this in addition to the Activity profile when creating or integrating Greia visual assets.

Read:

```text
skills/greia-visual-authoring/SKILL.md
docs/design/GREIA_ART_GRAPHICS_SYSTEM.md
docs/design/GREIA_VISUAL_STYLE_GUIDE.md
docs/design/GREIA_VISUAL_ART_AND_CORE_ASSET_REQUIREMENTS.md
docs/design/GREIA_VISUAL_AUTHORING_ARCHITECTURE.md
docs/design/GREIA_SCENE_COMPOSITION_RUNTIME.md
docs/plans/2026-08-20_GREIA_VISUAL_FOUNDATION_AND_ASSET_SYSTEM.md
docs/handovers/GREIA_VISUAL_SYSTEM_RESUME.md
```

Build and validate declared runtime renditions with:

```bash
make visual-assets
make visual-assets-check
```

Visual evidence must retain its correct label: source, desktop review, simulator review or physical review.

### 5.3 Local voice production — optional extension

Use this only on an owner-approved authoring machine when producing Activity playback audio from reviewed Greia character voices.

Read:

```text
docs/design/GREIA_VOICE_GENERATION_AND_CANONICAL_VOICES.md
docs/agents/GREIA_LOCAL_VOICE_PRODUCTION_SETUP.md
skills/greia-activity-authoring/VOICE_GENERATION.md
assets/audio/characters/canonical/v0.1/README.md
assets/audio/characters/canonical/v0.1/manifest.toml
```

The voice-production virtual environment, model cache and generated scratch output stay outside the repository. The narrow setup procedure in `GREIA_LOCAL_VOICE_PRODUCTION_SETUP.md` owns the Apple-Silicon MLX and portable ONNX paths.

#### Current repository readiness warning

The voice registry documentation and integrity manifest are committed, but current GitHub `main` does **not** contain the registered binary source masters or FLAC production anchors. The missing paths are:

```text
assets/source/audio/character-voice-masters/v0.1/*.wav
assets/audio/characters/canonical/v0.1/*-reference-v1.flac
```

Do not call a fresh clone voice-production ready until those exact files are present and match `manifest.toml`.

The files are small enough for ordinary GitHub storage. Their absence is not a GitHub-size limitation. They must be committed from an authorized working copy containing the real audio bytes; hashes in the manifest cannot reconstruct them.

### 5.4 Parent App developer — separate client repository

The canonical HTML client is not edited independently inside this repository. It lives in:

```text
frozenpepper/Greia-Parent-App-Html
```

Read in Greia OS:

```text
docs/architecture/PARENT_APP_SOURCE_INTEGRATION.md
docs/architecture/GREIA_PARENT_MANAGEMENT.md
docs/product/PARENT_MANAGEMENT.md
docs/adr/0022-parent-management-api-client-pairing-and-privilege-boundary.md
runtime/parent-app-client.toml
runtime/parent-app-client.manifest.json
```

Then clone the separate Parent App repository and use its own `README.md` and `AGENTS.md` when present.

Local dependency-free UI review from the Parent App checkout:

```bash
python3 -m http.server 8080
```

Open:

```text
http://127.0.0.1:8080/?demo=1
```

Run its tests at the exact pinned revision:

```bash
npm test
```

Normal mode talks to same-origin `/api/v1`; the browser client must not invent an SSH or shell fallback.

Greia OS stages a reviewed exported client through:

```text
tools/stage_parent_app.py
```

The canonical OS image builder does not yet complete that staging automatically. Read `docs/architecture/PARENT_APP_SOURCE_INTEGRATION.md` before changing this boundary.

### 5.5 Developer-device operator — connect to a child/test computer

Use only with an explicitly provisioned Greia **developer image**.

Read:

```text
docs/agents/GREIA_AGENT_OPERATIONS.md
docs/testing/2026-08-09_DEVELOPER_REMOTE_CONTROL.md
docs/development/GREIA_DEVELOPER_BOOT_DIAGNOSTICS.md
```

Operator host needs:

```text
Python 3
OpenSSH ssh/scp/ssh-keygen
an authorized Greia checkout
the private operator key produced by the developer-image build, when using key mode
```

Never commit the private key.

Typical connection flow:

```bash
python3 tools/greia_remote.py wait --timeout 180
python3 tools/greia_remote.py status
python3 tools/greia_remote.py screenshot out/screen.png
```

The default development target identity is currently:

```text
greia-dev.local
```

Use `--host` for an explicitly identified DHCP address when mDNS is unavailable. Do not hard-code target addresses or credentials into Greia source.

Use the stable `tools/greia_remote.py` commands for deployment, logs, screenshots, bounded input and lifecycle control. Do not script current Xorg/systemd internals as the public operator contract.

### 5.6 OS image / installer builder — privileged specialist profile

This profile is not required for ordinary Activity work.

Read:

```text
docs/agents/GREIA_AGENT_OPERATIONS.md
docs/INSTALLER_IMAGE_CREATION_AND_BOOT.md
docs/INSTALLATION_USB_BOOT_POSTMORTEM.md
docs/INSTALLED_OS_BOOT_POSTMORTEM.md
docs/development/GREIA_DEVELOPER_BOOT_DIAGNOSTICS.md
docs/testing/HARDWARE_COMPATIBILITY_MATRIX.md
```

Raw image and current QEMU/backend evidence require an owner-controlled compatible Linux environment with root access and the prerequisites named by the exact build/test procedure.

An explicit modern developer target is built with:

```bash
sudo bash build/build-developer-image.sh out
```

Do not run destructive disk or removable-media writes from a generic bootstrap script. Device identity, capacity and removable/internal status must be shown and confirmed at the dedicated procedure boundary.

## 6. Setup document map

| Need | Canonical practical entry point |
|---|---|
| Repository/agent operating rules | `docs/agents/GREIA_AGENT_OPERATIONS.md` |
| Activity authoring | `skills/greia-activity-authoring/SKILL.md` |
| Activity implementation details | `skills/greia-activity-authoring/CORE.md` |
| Desktop simulator | `docs/development/GREIA_ACTIVITY_SIMULATOR.md` |
| Text, typography and emoji | `docs/development/GREIA_ACTIVITY_TEXT_TYPOGRAPHY_AND_EMOJI.md` |
| Visual authoring | `skills/greia-visual-authoring/SKILL.md` |
| Visual-system architecture | `docs/design/GREIA_ART_GRAPHICS_SYSTEM.md` |
| Local character voice generation | `docs/agents/GREIA_LOCAL_VOICE_PRODUCTION_SETUP.md` |
| Parent App source and staging | `docs/architecture/PARENT_APP_SOURCE_INTEGRATION.md` |
| Parent management/API | `docs/architecture/GREIA_PARENT_MANAGEMENT.md` |
| Developer-device remote control | `docs/agents/GREIA_AGENT_OPERATIONS.md` and `docs/testing/2026-08-09_DEVELOPER_REMOTE_CONTROL.md` |
| Developer boot diagnosis | `docs/development/GREIA_DEVELOPER_BOOT_DIAGNOSTICS.md` |
| System-update release production | `docs/development/GREIA_SYSTEM_UPDATE_RELEASE_WORKFLOW.md` |
| Installer/image creation | `docs/INSTALLER_IMAGE_CREATION_AND_BOOT.md` |
| Hardware compatibility/evidence | `docs/testing/HARDWARE_COMPATIBILITY_MATRIX.md` and the named acceptance procedure |

## 7. Current readiness ledger

| Surface | Current state |
|---|---|
| Repository source verification | Available through `make verify`; host dependencies are not yet installed by one Greia command |
| Repository-local Activity and visual skills | Present; automatic cross-agent registration is not yet implemented |
| Activity Simulator | Implemented and documented; requires desktop Python/Pygame/Tk dependencies |
| Parent App local demo | Dependency-light and documented in the separate client repository |
| Parent App image staging | Integrity-checked stager exists; canonical image-build invocation remains incomplete |
| Developer remote control | Implemented for explicit developer images; forbidden as an implicit release feature |
| Local voice production procedure | Documented; canonical binary voice files are currently missing from GitHub `main` |
| One-command role-based workstation bootstrap | **Not implemented yet** |
| One-command setup verification report | **Not implemented yet** |

## 8. Next setup-system implementation tranche

The natural next implementation is a repository-owned, non-destructive setup assistant rather than more disconnected shell snippets.

Proposed entry point:

```text
tools/greia_setup.py
```

It should:

1. inspect OS, architecture and available commands;
2. accept an explicit profile such as `activity`, `visual`, `voice`, `parent`, `remote` or `builder`;
3. print the exact missing prerequisites before changing the host;
4. install nothing privileged without explicit approval;
5. keep venvs/caches/state outside the checkout;
6. verify repository skills are discoverable from the active checkout;
7. verify optional canonical assets by manifest/hash;
8. run bounded smoke checks appropriate to the selected profile;
9. emit a machine-readable and human-readable setup report;
10. never enable SSH, write disks, download mutable runtime code at Greia boot, or blur simulator/source/physical evidence.

Until that tool exists, this file is the canonical setup router and readiness ledger.

## 9. Maintenance rule

Whenever a change adds, removes or materially changes a required tool, skill, external repository, developer connection path, Parent App launch path, simulator prerequisite, voice backend, image-build prerequisite or setup verification command:

1. update the narrower owner document;
2. update this index in the same tranche;
3. update `AGENTS.md` if the mandatory read/setup rule changes;
4. update `HANDOVER.md` when current readiness or the next exact setup step changes;
5. commit the coherent documentation/source change to the canonical GitHub repository.
