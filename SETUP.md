# Greia Setup Index

**Status:** living workstation, agent and operator setup entry point  
**Last reviewed:** 2026-08-28  
**Canonical repository:** `frozenpepper/Greia`

This is the first file a human contributor or software agent should use when preparing a machine to work on Greia. It selects the correct setup path; narrower manuals remain authoritative for exact procedures.

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
3. **Voice production has one Greia entry point.** New prerecorded character/shared/pedagogical/Dani speech is produced through `tools/greia_voice.py`; caller scripts do not operate TTS/ASR backends directly.
4. **The heavy character-production profile is optional on a general workstation.** The Voice Engine source/semantic contract is repository-standard; Chatterbox/Whisper model installation is required only when the requested production route needs it.
5. **Keep machine-local material outside Git.** Venvs, model weights, caches, private keys, scratch audio, simulator state and build work roots stay outside the repository.
6. **Do not silently auto-install privileged/heavy dependencies.** Inspect first and obtain owner approval.
7. **Verify the exact checkout.** Record source SHA for retained simulator/image/physical evidence.
8. **Developer remote access is opt-in.** Normal/release Greia keeps SSH off.
9. **Setup success is not product evidence.** Source, simulator, VM/image, provider/audio-listening and physical evidence remain distinct.

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

When host dependencies are available:

```bash
make verify
```

Do not weaken validation to make a workstation look ready.

## 4. Repository-local skills

Greia currently owns task routers/skills including:

```text
skills/greia-os-work/SKILL.md
skills/greia-activity-authoring/SKILL.md
skills/greia-visual-authoring/SKILL.md
skills/greia-voice-production/SKILL.md
```

Activity authoring delegates to focused companions such as:

```text
skills/greia-activity-authoring/CORE.md
skills/greia-activity-authoring/DISCOVERY.md
skills/greia-activity-authoring/VOICE_GENERATION.md
```

`VOICE_GENERATION.md` delegates actual speech production to `skills/greia-voice-production/SKILL.md` and the Voice Engine. Agents should consume repository skills directly from the active checkout whenever possible.

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

If the Activity requires new prerecorded speech, switch to the Voice Production profile below rather than invoking a backend directly.

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

### 5.3 Voice Production Engine — canonical authoring profile

All new Greia prerecorded speech production uses:

```text
tools/greia_voice.py
```

Read:

```text
skills/greia-voice-production/SKILL.md
tools/greia_voice_core/README.md
docs/design/GREIA_VOICE_GENERATION_AND_CANONICAL_VOICES.md
docs/architecture/GREIA_VOICE_PRODUCTION_ENGINE.md
```

The first command on any workstation is the non-mutating probe:

```bash
python3 tools/greia_voice.py doctor
```

The engine handles four semantic production classes:

```text
character_dialogue
shared_character_utterance
pedagogical_speech
dani_system_speech
```

#### Base engine

The source is part of the repository; no engine package is installed into Greia OS. Python 3.11+ is required for the authoring CLI (`3.12` is the current tested production version).

#### Full Apple-Silicon character-production profile

When actual Lilli/Leo/Flash/Tito/Momo generation is requested and owner-authorized, follow:

```text
tools/greia_voice_core/README.md
docs/agents/GREIA_LOCAL_VOICE_PRODUCTION_SETUP.md
```

The tested dependency declaration is:

```text
tools/greia_voice_requirements_mlx.txt
```

Machine-local venv/cache/model data stays below `GREIA_VOICE_HOME` / `GREIA_VOICE_CACHE`, outside Git.

Current provider composition:

```text
canonical cloned characters -> Chatterbox Multilingual V3 / MLX
optional transcript check    -> mlx-whisper-tiny
pedagogical + Dani speech    -> macOS native/system speech
packaging                    -> FFmpeg
```

The Activity/OS/Encyclopedia skills do not call those pieces directly.

#### Shared Greia character utterances

Normal Activities consume semantic families such as:

```text
praise.general
celebrate.success
encourage.retry
encourage.progress
ready.go
```

They do not need a local cloning model merely to play the reviewed shared library.

When producing/extending the **central library itself**, use:

```bash
python3 tools/record_shared_character_utterances.py
```

This script is a thin Voice Engine client and covers Lilli/Leo/Flash/Tito/Momo plus Dani through the proper provider routes.

#### Pedagogical/system speech

Letters, syllables, phonics and pronunciation-authoritative audio use `pedagogical_speech` through the Voice Engine. Activity scripts do not call macOS `say` or hard-code host voice names/pronunciation overrides.

#### Human review

Every successful engine generation writes a receipt with:

```text
human_review = PENDING
```

Whisper PASS, process success or a valid audio file is never acceptance. Human listening remains mandatory before the owning workflow packages/promotes audio.

The low-level Chatterbox field guide is now for **Voice Engine maintainers/troubleshooting only**:

```text
docs/agents/GREIA_CHATTERBOX_PRODUCTION_FIELD_GUIDE.md
```

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

Open `http://127.0.0.1:8080/?demo=1` and run its tests with `npm test`.

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
| Voice production skill | `skills/greia-voice-production/SKILL.md` |
| Voice engine quick install/use | `tools/greia_voice_core/README.md` |
| Voice architecture | `docs/architecture/GREIA_VOICE_PRODUCTION_ENGINE.md` |
| Voice policy/canonical identities | `docs/design/GREIA_VOICE_GENERATION_AND_CANONICAL_VOICES.md` |
| Voice workstation setup | `docs/agents/GREIA_LOCAL_VOICE_PRODUCTION_SETUP.md` |
| Chatterbox internals/troubleshooting | `docs/agents/GREIA_CHATTERBOX_PRODUCTION_FIELD_GUIDE.md` |
| Shared character utterances | `docs/design/GREIA_SHARED_CHARACTER_UTTERANCES.md` |
| Shared utterance production | `docs/agents/GREIA_SHARED_CHARACTER_UTTERANCE_RECORDING.md` |
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
| Repository source verification | `make verify`; execute locally on the exact current source before claiming PASS |
| Repository-local skills | OS, Activity, visual and voice skills present; universal cross-agent registration not implemented |
| Activity Simulator | Implemented/documented; requires desktop Python/Pygame/Tk dependencies |
| Parent App local demo | Dependency-light in separate client repository |
| Developer remote control | Implemented for explicit developer images only |
| Voice Production Engine | Implemented and canonical for new authoring production; real provider readiness is workstation-specific and reported by `doctor` |
| Pedagogical/system speech | macOS adapter implemented behind Voice Engine; other hosts require future providers |
| Chatterbox character production | Apple-Silicon MLX provider implemented behind Voice Engine; optional heavy workstation profile |
| Whisper verification | Optional advisory verifier implemented behind Voice Engine; never acceptance authority |
| Shared-library producer | Engine-based producer implemented; human-reviewed runtime catalogue completeness remains separately evidence-owned |
| One-command role-based workstation bootstrap | Not implemented; voice profile has explicit install guide + `doctor` |

## 8. Future setup assistant

A future `tools/greia_setup.py` may unify role bootstrap, but it must consume rather than replace the current Voice Engine provider probe and never silently install heavy/privileged dependencies.

Desired profiles may include:

```text
activity
visual
voice
parent
remote
builder
```

Until then, this file is the setup router/readiness ledger and `tools/greia_voice.py doctor` is the canonical voice readiness probe.

## 9. Maintenance rule

Whenever a change adds/removes/materially changes a required tool, skill, external repository, connection path, Parent App launch path, simulator prerequisite, voice backend, image-build prerequisite or setup verification command:

1. update the narrower owner document;
2. update this index in the same tranche;
3. update `AGENTS.md` if the mandatory setup/read rule changes;
4. update `HANDOVER.md` when current readiness/next setup step changes materially;
5. commit the coherent documentation/source change to the canonical repository.
