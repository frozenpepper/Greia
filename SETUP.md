# Greia Setup Index

**Status:** living workstation, agent and operator setup entry point  
**Last reviewed:** 2026-08-23  
**Canonical repository:** `frozenpepper/Greia`

This is the first file a human contributor or software agent should use when preparing a machine to work on Greia.

It does not replace narrower manuals. It selects the correct setup path, points to the authoritative procedure for each role, and makes incomplete/optional setup surfaces visible instead of allowing agents to improvise.

## 1. Read before installing anything

From the Greia repository root, read:

```text
AGENTS.md
SETUP.md
docs/DOCUMENTATION.md
HANDOVER.md
docs/agents/GREIA_AGENT_OPERATIONS.md
```

Then read the skill/manual for the role being configured.

Do not install packages, create model environments, download weights, enable SSH, write removable media, or perform destructive OS installation merely because a tool exists in the repository.

## 2. Setup principles

1. **The repository copy is canonical.** Read skills/setup docs from the active checkout.
2. **Choose a role profile.** An Activity creator does not need the raw-image build stack; an OS builder does not automatically need local voice models.
3. **Optional means optional.** Custom Chatterbox character-voice production is not required to create a valid Greia Activity.
4. **Keep machine-local material outside Git.** Venvs, model weights, caches, private keys, scratch audio, simulator state and build work roots stay outside the repository.
5. **Do not silently auto-install privileged/heavy dependencies.** Inspect first and obtain owner approval.
6. **Verify the exact checkout.** Record source SHA for retained simulator/image/physical evidence.
7. **Developer remote access is opt-in.** Normal/release Greia keeps SSH off.
8. **Setup success is not product evidence.** Source, simulator, VM/image and physical evidence remain distinct.

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

When host dependencies are available, run:

```bash
make verify
```

Do not weaken validation to make a workstation look ready.

## 4. Repository-local skills

Greia currently owns:

```text
skills/greia-activity-authoring/SKILL.md
skills/greia-visual-authoring/SKILL.md
```

The Activity skill delegates to:

```text
skills/greia-activity-authoring/CORE.md
skills/greia-activity-authoring/DISCOVERY.md
skills/greia-activity-authoring/VOICE_GENERATION.md
```

Agents should consume these directly from the active checkout when possible. If an agent platform requires separately installed skills, use a symlink or explicitly managed copy and keep the repository version authoritative.

There is not yet a universal cross-agent skill installer.

## 5. Role profiles

### 5.1 Activity creator — standard profile

Use for creating/modifying/validating Activities.

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
current Greia/Pygame dependencies
Tk support for simulator control plane
make
```

Start simulator:

```bash
python3 tools/greia_simulator.py
```

Validate one Activity:

```bash
PYTHONPATH=src python3 tools/validate_activity.py activities/<activity-directory>
```

Focused simulator gate:

```bash
PYTHONPATH=src python3 -m unittest tests.test_greia_simulator -v
```

Then run `make verify` before claiming a substantive source tranche complete.

### 5.2 Visual author — optional extension

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

Build/validate declared renditions:

```bash
make visual-assets
make visual-assets-check
```

### 5.3 Speech support — standard versus optional

Speech has separate setup surfaces.

#### A. Shared Greia character utterances

No local cloning model is required for an ordinary Activity author once shared runtime assets are implemented.

Read:

```text
docs/design/GREIA_SHARED_CHARACTER_UTTERANCES.md
skills/greia-activity-authoring/VOICE_GENERATION.md
```

Activities request semantic families such as:

```text
praise.general
celebrate.success
encourage.retry
encourage.progress
ready.go
```

They do not select concrete phrases or files. A resolved family owns a reviewed file array: one file is always used; multiple files are randomly selected by Greia for presentation variety.

#### B. Pedagogical/system speech

Letters, syllables, phonics and pronunciation-authoritative audio use a deterministic native/system speech path. This must not require Chatterbox merely to author the Activity.

Read:

```text
docs/design/GREIA_VOICE_GENERATION_AND_CANONICAL_VOICES.md
skills/greia-activity-authoring/VOICE_GENERATION.md
```

Native/system provider adapters are not yet standardized into one Greia setup command; use only the platform/authoring path explicitly supported by the current implementation.

#### C. Custom canonical character dialogue — optional `voice` profile

Use only when the owner wants new Lilli/Leo/Flash/Tito/Momo dialogue beyond the shared utterance library.

Read:

```text
docs/design/GREIA_VOICE_GENERATION_AND_CANONICAL_VOICES.md
docs/agents/GREIA_LOCAL_VOICE_PRODUCTION_SETUP.md
skills/greia-activity-authoring/VOICE_GENERATION.md
assets/audio/characters/canonical/v0.1/manifest.toml
```

Current optional renderer:

```text
Chatterbox Multilingual V3
```

Preferred Apple-Silicon path is currently the MLX Audio conversion documented by the local voice setup guide. Other supported authoring hosts may use the official upstream Chatterbox path.

**The Activity skill must not install this profile automatically.** It first checks for shared utterances/pedagogical speech, then probes an already configured Chatterbox environment. If unavailable and not explicitly requested, optional custom character dialogue is dropped while the Activity remains fully functional.

FFmpeg/ffprobe are the preferred cross-platform audio inspection/trim/conversion tools for this optional production profile.

Current canonical binary voice references may still be absent from a fresh GitHub checkout until the reviewed WAV/FLAC asset commit is materialized. A manifest alone is not voice-production readiness; verify actual files and hashes before use.

#### D. Shared utterance library producer — optional `voice` profile

Use this only when producing/extending Greia's OS-owned shared reaction library itself.

Read and follow:

```text
docs/agents/GREIA_SHARED_CHARACTER_UTTERANCE_RECORDING.md
```

The complete v0.1 target is 180 reviewed clips: 150 Chatterbox clips for Lilli/Leo/Flash/Tito/Momo plus 30 future Dani system-TTS clips. A family does not require all three planned variants to function: one reviewed file is already a valid non-empty array; additional reviewed files add variety.

### 5.4 Parent App developer — separate client repository

Canonical HTML client:

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

Then use the separate repository's own README/AGENTS.

Local dependency-light demo:

```bash
python3 -m http.server 8080
```

Open:

```text
http://127.0.0.1:8080/?demo=1
```

Run its tests:

```bash
npm test
```

The browser client must not invent an SSH/shell fallback for unavailable API features.

### 5.5 Developer-device operator

Use only with an explicit Greia developer image.

Read:

```text
docs/agents/GREIA_AGENT_OPERATIONS.md
docs/testing/2026-08-09_DEVELOPER_REMOTE_CONTROL.md
docs/development/GREIA_DEVELOPER_BOOT_DIAGNOSTICS.md
```

Operator host needs Python 3, OpenSSH tools, an authorized checkout and the developer-image operator key when key mode is used. Never commit that key.

Typical flow:

```bash
python3 tools/greia_remote.py wait --timeout 180
python3 tools/greia_remote.py status
python3 tools/greia_remote.py screenshot out/screen.png
```

Default development target identity is currently `greia-dev.local`. Use explicit `--host` when required; do not hard-code addresses/credentials into source.

### 5.6 OS image / installer builder — privileged specialist profile

Not required for ordinary Activity work.

Read:

```text
docs/agents/GREIA_AGENT_OPERATIONS.md
docs/INSTALLER_IMAGE_CREATION_AND_BOOT.md
docs/INSTALLATION_USB_BOOT_POSTMORTEM.md
docs/INSTALLED_OS_BOOT_POSTMORTEM.md
docs/development/GREIA_DEVELOPER_BOOT_DIAGNOSTICS.md
docs/testing/HARDWARE_COMPATIBILITY_MATRIX.md
```

Raw-image/current backend evidence requires an owner-controlled compatible Linux environment with root access and the prerequisites named by the exact build/test procedure.

Developer target:

```bash
sudo bash build/build-developer-image.sh out
```

Do not put destructive disk/removable-media writes into a generic setup helper.

## 6. Setup document map

| Need | Entry point |
|---|---|
| Repository/agent operations | `docs/agents/GREIA_AGENT_OPERATIONS.md` |
| Activity authoring | `skills/greia-activity-authoring/SKILL.md` |
| Activity implementation | `skills/greia-activity-authoring/CORE.md` |
| Desktop simulator | `docs/development/GREIA_ACTIVITY_SIMULATOR.md` |
| Text/typography/emoji | `docs/development/GREIA_ACTIVITY_TEXT_TYPOGRAPHY_AND_EMOJI.md` |
| Visual authoring | `skills/greia-visual-authoring/SKILL.md` |
| Visual architecture | `docs/design/GREIA_ART_GRAPHICS_SYSTEM.md` |
| Speech/voice policy | `docs/design/GREIA_VOICE_GENERATION_AND_CANONICAL_VOICES.md` |
| Shared character utterances | `docs/design/GREIA_SHARED_CHARACTER_UTTERANCES.md` |
| Shared utterance recording | `docs/agents/GREIA_SHARED_CHARACTER_UTTERANCE_RECORDING.md` |
| Optional custom character-voice setup | `docs/agents/GREIA_LOCAL_VOICE_PRODUCTION_SETUP.md` |
| Parent App source/staging | `docs/architecture/PARENT_APP_SOURCE_INTEGRATION.md` |
| Parent management/API | `docs/architecture/GREIA_PARENT_MANAGEMENT.md` |
| Developer remote control | `docs/agents/GREIA_AGENT_OPERATIONS.md`, `docs/testing/2026-08-09_DEVELOPER_REMOTE_CONTROL.md` |
| Developer boot diagnosis | `docs/development/GREIA_DEVELOPER_BOOT_DIAGNOSTICS.md` |
| Update release production | `docs/development/GREIA_SYSTEM_UPDATE_RELEASE_WORKFLOW.md` |
| Installer/image creation | `docs/INSTALLER_IMAGE_CREATION_AND_BOOT.md` |
| Hardware compatibility/evidence | `docs/testing/HARDWARE_COMPATIBILITY_MATRIX.md` + named acceptance procedure |

## 7. Current readiness ledger

| Surface | Current state |
|---|---|
| Repository source verification | `make verify`; host dependencies not yet installed by one Greia command |
| Repository-local skills | Present; universal cross-agent registration not yet implemented |
| Activity Simulator | Implemented/documented; requires desktop Python/Pygame/Tk dependencies |
| Parent App local demo | Dependency-light in separate client repository |
| Parent App image staging | Integrity-checked stager exists; full canonical image-build wiring remains implementation-owned |
| Developer remote control | Implemented for explicit developer images only |
| Pedagogical/system speech abstraction | Policy accepted; unified provider implementation pending |
| Shared character utterance library | Five variant-aware families accepted; 180-clip audio/runtime resolver still pending |
| Custom Chatterbox character production | **Optional**; setup documented; never required for ordinary Activity authoring |
| One-command role-based workstation bootstrap | **Not implemented yet** |
| One-command setup verification report | **Not implemented yet** |

## 8. Future setup assistant

Natural future entry point:

```text
tools/greia_setup.py
```

It should:

1. inspect OS/architecture/available commands;
2. accept explicit profiles such as `activity`, `visual`, `voice`, `parent`, `remote`, `builder`;
3. install nothing privileged/heavy without explicit approval;
4. keep machine-local state outside the checkout;
5. verify repository skills from the active checkout;
6. verify optional canonical assets by manifest/hash;
7. run bounded profile-specific smoke checks;
8. emit human/machine-readable setup reports;
9. allow `--profile voice --check` to probe custom character generation without installing it;
10. never enable SSH/write disks/download runtime code implicitly.

Until then, this file is the setup router/readiness ledger.

## 9. Maintenance rule

Whenever a change adds/removes/materially changes a required tool, skill, external repository, connection path, Parent App launch path, simulator prerequisite, voice backend, image-build prerequisite or setup verification command:

1. update the narrower owner document;
2. update this index in the same tranche;
3. update `AGENTS.md` if the mandatory setup/read rule changes;
4. update `HANDOVER.md` when current readiness/next setup step changes materially;
5. commit the coherent documentation/source change to the canonical repository.
