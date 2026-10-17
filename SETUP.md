# Greia Setup Index

**Status:** LIVING workstation / contributor / operator setup router  
**Reviewed:** 2026-10-16  
**Canonical repository:** `frozenpepper/Greia`

This file answers one question: **what does this workstation/operator role need to read and install?** It does not replace the narrower manuals that own exact procedures. New contributors should start with `CONTRIBUTING.md`; this file covers the heavier roles.

## 1. Read before installing anything

From the repository root:

```text
AGENTS.md
SETUP.md
docs/DOCUMENTATION.md
HANDOVER.md
docs/agents/GREIA_AGENT_OPERATIONS.md
```

Then read the task/role-specific skill below.

Do not install heavy model stacks, enable SSH, write removable media, add privileged host packages or perform destructive installation merely because a Greia tool exists.

## 2. Setup principles

1. **Use the active checkout.** Repository-local skills/docs are authoritative for that source state.
2. **Choose a role.** An Activity author does not need the raw-image build stack; an OS builder does not automatically need voice models.
3. **One voice-production boundary.** New prerecorded speech goes through `tools/greia_voice.py`; callers do not operate Chatterbox/MLX/Whisper/native TTS/FFmpeg directly.
4. **Authoring models are optional workstation tooling.** No normal narration TTS/ASR model belongs on the child device.
5. **Asset acceptance and runtime integration are separate.** A reviewed audio/image set may exist while a runtime resolver or final product placement is still pending.
6. **Keep machine-local material outside Git.** Venvs, model weights, caches, private keys, scratch audio, Simulator state and bulky evidence/build roots are local material.
7. **Do not silently auto-install privileged/heavy dependencies.** Inspect and obtain owner approval where required.
8. **Record exact SHA for retained evidence.** Source, Simulator, VM/image, provider+human and physical evidence are different lanes.
9. **Developer remote access is opt-in.** Normal/release Greia keeps SSH off.
10. **Setup success is not release evidence.** A tool starting successfully proves only its own setup scope.

## 3. Common bootstrap

```bash
git clone https://github.com/frozenpepper/Greia.git
cd Greia
python3 -m pip install -r requirements-dev.txt

git status --short
git rev-parse HEAD
python3 --version
git --version
make --version
```

When the role's host dependencies are available:

```bash
make verify
```

Run the gate on the exact checkout whose result you intend to retain; do not copy old PASS counts from documentation.

## 4. Repository-local task routers

```text
skills/greia-os-work/SKILL.md
skills/greia-activity-authoring/SKILL.md
skills/greia-visual-authoring/SKILL.md
skills/greia-voice-production/SKILL.md
```

For current testing/evidence routing use:

```text
docs/testing/LOCAL_AGENT_START_HERE.md
```

That file deliberately routes through `HANDOVER.md` instead of freezing one dated test session forever.

## 5. Activity creator — standard profile

Read:

```text
skills/greia-activity-authoring/SKILL.md
skills/greia-activity-authoring/CORE.md
docs/development/GREIA_ACTIVITY_SIMULATOR.md
docs/development/GREIA_ACTIVITY_TEXT_TYPOGRAPHY_AND_EMOJI.md
docs/product/ACTIVITY_INPUT_STANDARDS.md
docs/product/ACTIVITY_SYSTEM_NAVIGATION.md
```

Typical host needs:

```text
Python 3.11+
requirements-dev.txt (pygame, Pillow, zstandard; regex optional)
Tk support for Simulator control plane
make
```

Start the Simulator:

```bash
python3 tools/greia_simulator.py
```

Validate one Activity:

```bash
PYTHONPATH=src python3 tools/validate_activity.py activities/<activity-directory>
```

If new prerecorded speech is required, switch to the Voice Production profile rather than invoking a TTS backend directly.

## 6. Visual author — optional extension

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

Build/validate declared visual renditions:

```bash
make visual-assets
make visual-assets-check
```

Do not infer physical readability/performance from desktop rendering alone.

## 7. Voice Production Engine / authoring Voice Studio

Canonical entry point:

```text
tools/greia_voice.py
```

“Voice Studio” is shorthand for the authoring workflow around `VoiceEngine`; it is not child-runtime TTS and does not imply a GUI.

Read:

```text
skills/greia-voice-production/SKILL.md
tools/greia_voice_core/README.md
docs/architecture/GREIA_VOICE_PRODUCTION_ENGINE.md
docs/design/GREIA_VOICE_GENERATION_AND_CANONICAL_VOICES.md
```

First command on any workstation:

```bash
python3 tools/greia_voice.py doctor
```

Semantic production kinds:

```text
character_dialogue
shared_character_utterance
pedagogical_speech
dani_system_speech
```

### 7.1 Base engine

The authoring engine source is repository tooling; it is not installed into Greia OS. Python 3.11+ is required for the CLI; Python 3.12 is the current tested production version recorded by the voice tooling docs.

### 7.2 Apple-Silicon natural-character production

For Lilli/Leo/Flash/Tito/Momo production:

```text
tools/greia_voice_core/README.md
docs/agents/GREIA_LOCAL_VOICE_PRODUCTION_SETUP.md
tools/greia_voice_requirements_mlx.txt
```

Machine-local venv/cache/model data stays below the configured Voice home/cache outside Git.

Current implemented provider composition:

```text
natural canonical characters -> Chatterbox Multilingual V3 / MLX
optional transcript warning   -> mlx-whisper-tiny
pedagogical + Dani speech     -> deterministic macOS native/system provider
packaging                     -> engine-owned FFmpeg path
```

Other hosts must report unavailable provider gaps honestly until an accepted provider exists. Do not bypass VoiceEngine with direct `espeak`, Piper, Coqui, Windows Speech or arbitrary host commands.

### 7.3 Shared reactions + character introductions — authoring COMPLETE

The accepted authoring set is now:

```text
180 shared reactions
+ 12 character introductions
= 192 owner-accepted clips
```

Canonical accepted assets:

```text
assets/audio/characters/shared/v0.2/
```

The older `v0.1` set is retired historical material.

Producer/runbook:

```text
tools/record_shared_character_utterances.py
docs/agents/GREIA_SHARED_CHARACTER_UTTERANCE_RECORDING.md
```

Design/status authority:

```text
docs/design/GREIA_SHARED_CHARACTER_UTTERANCES.md
docs/design/GREIA_VOICE_GENERATION_AND_CANONICAL_VOICES.md
```

**Do not call this production/listening pending anymore.** Generation and owner listening are complete for v0.2.

Still separate/pending where applicable:

- runtime shared-utterance resolver/catalogue integration;
- final product UX placement for character introductions.

Normal Activity authors do not need a cloning environment merely to consume an accepted static shared library.

### 7.4 Pedagogical/system speech

Letters, syllables, phonics and other pronunciation-authoritative material use `pedagogical_speech` through VoiceEngine. Activity/OS scripts must not call macOS `say` or encode host voice names/pronunciation hacks.

Dani-specific robotic speech uses `dani_system_speech`.

### 7.5 Human review

New generations begin with human review pending. Provider success, a valid WAV/OGG file or Whisper PASS is not acceptance.

The accepted v0.2 shared/introduction set is an example of the complete flow: generation -> review receipts -> owner listening -> versioned accepted asset promotion.

Low-level provider troubleshooting only:

```text
docs/agents/GREIA_CHATTERBOX_PRODUCTION_FIELD_GUIDE.md
```

## 8. Parent App developer

Canonical HTML client repository:

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

The browser client must not invent an SSH/shell fallback for an unavailable semantic Parent API feature.

## 9. Developer-device operator

Use only with an explicit developer image.

Read:

```text
docs/agents/GREIA_AGENT_OPERATIONS.md
docs/testing/2026-08-09_DEVELOPER_REMOTE_CONTROL.md
docs/development/GREIA_DEVELOPER_BOOT_DIAGNOSTICS.md
```

Typical operator flow:

```bash
python3 tools/greia_remote.py wait --timeout 180
python3 tools/greia_remote.py status
python3 tools/greia_remote.py screenshot out/screen.png
```

Never commit the operator private key. Never turn developer SSH into a normal/release dependency.

For current acceptance, follow the exact test procedure selected by `HANDOVER.md`; do not run an old dated protocol merely because it exists.

## 10. OS image / installer builder

Not required for ordinary Activity work.

Read:

```text
skills/greia-os-work/SKILL.md
skills/greia-os-work/BOOT.md
docs/agents/GREIA_AGENT_OPERATIONS.md
docs/INSTALLER_IMAGE_CREATION_AND_BOOT.md
docs/engineering/BOOT_PIPELINE_AGENT_GUIDE.md
```

Raw-image/current backend evidence requires an owner-controlled compatible Linux environment with root access and the prerequisites named by the exact build/test procedure.

Developer target entry point currently includes:

```bash
sudo bash build/build-developer-image.sh out
```

Reference-Acer USB front door (diagnostic developer image, or the quiet release candidate):

```bash
sudo bash tools/build-and-flash-development-usb.sh legacy-x86-i686-dev /dev/sdX
sudo bash tools/build-and-flash-development-usb.sh legacy-x86-i686-rc /dev/sdX ./out --operator-key ~/greia-operator.pub
```

The release-candidate runbook (frozen SHA, operator public key, USB identification, required PASS lines, pre-build gates G1–G11) is `docs/INSTALLER_IMAGE_CREATION_AND_BOOT.md` §13. Boot console policy (`diagnostic` vs `quiet`, hidden verbose paths) is §7 there.

Do not add destructive disk/removable-media writes to a generic setup helper.

## 11. Setup map

| Need | Entry point |
|---|---|
| Current implementation/evidence | `HANDOVER.md` |
| Current testing route | `docs/testing/LOCAL_AGENT_START_HERE.md` |
| Repository/agent operations | `docs/agents/GREIA_AGENT_OPERATIONS.md` |
| OS/platform work | `skills/greia-os-work/SKILL.md` |
| Activity authoring | `skills/greia-activity-authoring/SKILL.md` |
| Activity Simulator | `docs/development/GREIA_ACTIVITY_SIMULATOR.md` |
| Visual authoring | `skills/greia-visual-authoring/SKILL.md` |
| Visual architecture | `docs/design/GREIA_ART_GRAPHICS_SYSTEM.md` |
| Voice production | `skills/greia-voice-production/SKILL.md` |
| Voice engine quick use | `tools/greia_voice_core/README.md` |
| Voice architecture | `docs/architecture/GREIA_VOICE_PRODUCTION_ENGINE.md` |
| Voice policy/status | `docs/design/GREIA_VOICE_GENERATION_AND_CANONICAL_VOICES.md` |
| Parent source/API | `docs/architecture/GREIA_PARENT_MANAGEMENT.md` |
| Developer remote | `docs/agents/GREIA_AGENT_OPERATIONS.md` |
| Installer/image creation | `docs/INSTALLER_IMAGE_CREATION_AND_BOOT.md` |
| Public-release gate | `docs/release/GREIA_PUBLIC_RELEASE_READINESS.md` |

## 12. Current readiness ledger

| Surface | Current state |
|---|---|
| Repository source verification | `make verify`; execute on exact current checkout before claiming PASS |
| Activity Simulator | implemented/documented; desktop development dependencies required |
| Developer remote | implemented for explicit developer images only |
| Voice Production Engine | implemented/canonical; provider readiness is workstation-specific and reported by `doctor` |
| Natural-character production | Apple-Silicon MLX provider implemented behind VoiceEngine |
| Pedagogical/Dani production | macOS deterministic provider implemented behind VoiceEngine |
| Whisper verification | optional advisory verifier; never acceptance authority |
| Shared reactions | **180 generated + owner-accepted in `shared/v0.2`** |
| Character introductions | **12 generated + owner-accepted in `shared/v0.2/_intros`**; product placement separate |
| Shared runtime resolver | separate integration task where still pending |
| Public-source legal/provenance gate | root entry points added 2026-10-16 (`LICENSE`, `NOTICE.md`, `SECURITY.md`, `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`); audit still pending, see `NOTICE.md` |

## 13. Maintenance rule

When a change materially alters a required tool, role, external repository, connection path, Simulator prerequisite, voice workflow/provider, image-build prerequisite or setup verification command:

1. update the narrower owner document;
2. update this router if setup/navigation changed;
3. update `AGENTS.md` only if repository-wide mandatory behavior changed;
4. update `HANDOVER.md` when current readiness/continuation changed;
5. preserve evidence scope honestly.

A future setup assistant may automate role bootstrap, but it must consume rather than replace these authorities and must never silently install heavy/privileged dependencies.
