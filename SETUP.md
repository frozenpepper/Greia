# Greia Setup Index

**Status:** LIVING workstation / contributor / operator setup router  
**Reviewed:** 2026-10-30
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

Repository `skills/` files are canonical. Some workstations keep ignored installed
copies under `.agents/skills/`; refresh the affected skill directories from
`skills/` after changes (for example `rsync -a skills/greia-voice-production/ .agents/skills/greia-voice-production/`). Do not treat an older installed copy as a second authority.

For current testing/evidence routing use:

```text
docs/testing/LOCAL_AGENT_START_HERE.md
```

That file deliberately routes through `HANDOVER.md` instead of freezing one dated test session forever.

## 5. Activity creator — standard profile

The practical human overview is [Create an Activity](docs/development/CREATE_AN_ACTIVITY.md). Agent authors should still follow the current source-owned [Activity skill](skills/greia-activity-authoring/SKILL.md); this page only routes tooling installation.

Read:

```text
skills/greia-activity-authoring/SKILL.md
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

**Post-generation review:** follow `docs/agents/GREIA_AUTOMATED_VOICE_REVIEW.md`.
`tools/regenerate_voice_corpus.py review` checks installed audio/receipts and
produces external resumable reports. Optional ASR uses existing cached weights
only; disabled/unavailable ASR is incomplete screening. This does not grant
human acceptance or install anything. Generation DONE is a separate state.

Corpus regeneration/replacement (owner-requested 2026-10-19, v3 run
2026-10-21) uses `tools/regenerate_voice_corpus.py` with
`docs/agents/GREIA_VOICE_CORPUS_REGENERATION.md`: external originals and
candidates are kept, deterministic isolated letters and syllables are
preserved, and every new take is listening-pending. Character acting defaults
are in `tools/greia_voice_core/character_delivery.json`, with a
`delivery_prompt` override per recording. Short-cue carrier extraction
(`tools/voice_carrier.py`, `docs/agents/GREIA_SPOKEN_CARRIER_EXTRACTION.md`)
is technical screening only, never acceptance, and uses cached model weights
only.

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

**Owner direction (2026-10-21):** voice-defining pitch/register, timbre, age
and texture belong in master design only. Per-cue directions must be
acting/emotion/pace, not repeated persona definitions. The active v0.3 masters
are Dani v5 candidate 02, Momo v3 candidate 01 and Tito v3 candidate 01;
Lilli, Leo and Flash keep their v0.2 masters.

### 7.1 Base engine and default character production

Python 3.11+ runs the Greia CLI. The active v0.3 registry uses owner-selected
Dani, Momo and Tito masters from 2026-10-21 and retains Lilli, Leo and Flash's
exact v0.2 masters unchanged. Character production uses **VoxCPM2 through the
shared local VoxStage service** by default. No model runs on the child device.

On this workstation VoxStage is already installed. Start/reuse its single worker:

```bash
voxstage start
python3 tools/greia_voice.py doctor
```

Greia uses only standard-library HTTP to talk to VoxStage; it does not import a
second MLX model or require the Chatterbox venv for default character production.
FFmpeg remains required for engine-owned 22,050 Hz mono WAV/OGG packaging.
VoxStage owns its optional Apple-Silicon model/runtime installation; consult the
shared tools catalog and VoxStage skill before installing anything. Never copy
its weights, venv or generated job cache into this repository.

### 7.2 Configuration and retained alternative

- Default character provider: `voxstage` (`voxstage-voxcpm2` in receipts).
- Override for an engine process: `--character-provider chatterbox` on `doctor`,
  `generate`, `batch` or `serve`; repository producers can use
  `GREIA_VOICE_CHARACTER_PROVIDER=chatterbox`. An explicit CLI flag wins.
- The default service origin is `http://127.0.0.1:8791`;
  `GREIA_VOXSTAGE_URL` may select another loopback HTTP origin only.
- `GREIA_VOXSTAGE_TIMEOUT` bounds each job wait (default 1,800 seconds;
  allowed 1–7,200). A timed-out job can still run in VoxStage; inspect its
  recorded job ID before submitting more work. No automatic POST resubmission.
- Voice IDs and transcripts come from the active v0.3 registry. Missing VoxStage library
  entries are imported from the repository's exact reviewed WAV; existing IDs
  are reused without replacement. `doctor` never imports or generates.
- All six character profiles use cloned references, including the compatible
  `dani_system_speech` route. `pedagogical_speech` retains deterministic macOS
  native pronunciation through the independent native provider.

Chatterbox remains implemented. Its optional installation and requirements are
in `docs/agents/GREIA_LOCAL_VOICE_PRODUCTION_SETUP.md` and
`tools/greia_voice_requirements_mlx.txt`. Unload the shared VoxStage model before
using in-process Chatterbox on the same workstation. No silent backend fallback
occurs if the chosen character provider is unavailable.

Greia's `serve` process selects its provider at startup; `request` clients use
that server's choice. `request --timeout` controls the response wait (default
3,600 seconds), separate from the ten-second connection deadline. VoxStage
owns its warm worker: `voxstage unload` releases model memory after production;
closing a Greia client does not stop a service used by other projects.

### 7.3 Shared reactions + character introductions

The owner-accepted v0.2 baseline is 180 shared reactions plus 12 character
introductions (192 clips). Rows that the 2026-10-21 v3 replacement regenerated
for Dani, Momo and Tito are listening-pending again (see §12).

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

Still separate/pending where applicable:

- runtime shared-utterance resolver/catalogue integration;
- final product UX placement for character introductions.

Normal Activity authors do not need a cloning environment merely to consume an accepted static shared library.

### 7.4 Pedagogical/system speech

Letters, syllables, phonics and other pronunciation-authoritative material use `pedagogical_speech` through VoiceEngine. Activity/OS scripts must not call macOS `say` or encode host voice names/pronunciation hacks.

Dani-specific robotic speech uses `dani_system_speech`, now backed by Dani’s selected cloned master through VoxStage by default.

### 7.5 Current Parakeet verifier and retained historical Whisper environment

**New VoiceEngine requests (since 2026-10-23)** use offline cached
multilingual **Parakeet-TDT v3** through `tools/greia_voice_core/parakeet_asr.py`,
with pinned model `mlx-community/parakeet-tdt-0.6b-v3` at revision
`ed2b7e8c15f9aaa0b5772e2efb986255eaef7e15`.
This is **not** the same model as VoxCPM2 (speech generation). Verification
does not silently fall back to Whisper or download missing weights.

On the owner's already-prepared Apple Silicon workstation:

```bash
voice_python="$HOME/Library/Application Support/Greia/voice-production/venv/bin/python"
"$voice_python" tools/greia_voice.py doctor
```

Inspect `verifier.available` and the exact model/revision in the doctor
response. Character provider readiness and doctor exit code 0 are **not**
proof of ASR readiness. A fresh workstation must separately install a
compatible MLX/Parakeet environment and provision the exact cached snapshot;
the Greia checkout alone does not reproduce the owner's voice workstation.
See `docs/agents/GREIA_LOCAL_VOICE_PRODUCTION_SETUP.md` and the full entry
in `tools/greia_voice_core/README.md`. Language support/recognition quality
must be assessed for *new* languages before trusting machine transcripts.

**Historical frozen corpus review** retains Whisper evidence and the old
`mlx-community/whisper-base-mlx` pinned revision
`1e3e249fb8d01c655324bd6841b1deadffd6d04c`
(older records may use Tiny). The owner's prepared venv also has
`mlx-whisper==0.4.3` and cached Base/Tiny weights for those workflows.
Use `docs/agents/GREIA_AUTOMATED_VOICE_REVIEW.md` for exact historical
review commands. Do not relabel, rerun or silently reinterpret prior receipts
as Parakeet results. Neither ASR gives human listening acceptance.

### 7.6 Human review

Shared `takeboard` provides the local HTML listening desk; see the shared tools
catalog/skill and `docs/agents/GREIA_AUTOMATED_VOICE_REVIEW.md` §6. Greia supplies
only `tools/export_voice_review_batch.py`. The tool needs Python/browser only,
no model installation, and saves human states/scores/notes in external review JSON.
It does not change Greia media/receipts or grant automatic acceptance.


New generations begin with human review pending. Provider success, a valid WAV/OGG file or Whisper PASS is not acceptance.

The accepted v0.2 shared/introduction set is an example of the complete flow: generation -> review receipts -> owner listening -> versioned accepted asset promotion.

Low-level provider troubleshooting only:

```text
docs/agents/GREIA_CHATTERBOX_PRODUCTION_FIELD_GUIDE.md
```

## 8. Parent App developer

For parent-facing usage, rather than client development, use [Greia Parents](docs/user/GREIA_PARENTS.md). The on-device **S + T** shortcut and browser connection belong in that simple guide.

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

Installed Greia serves the Parent browser and API over self-signed HTTPS on LAN port 8766; the local S+T Parent panel uses loopback-only HTTP at 127.0.0.1:8767. The on-device TLS certificate is generated with OpenSSL (included in the image base package set). Browser certificate warnings on first visit are expected. See the Parent user guide and the exact transport acceptance note in docs/testing.

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

For an overview, see [Build a Greia image](docs/development/BUILD_A_GREIA_IMAGE.md); agents following a human-authorized image build should use the linked [image-building agent runbook](docs/agents/GREIA_IMAGE_BUILD_AGENT.md). The specialist manuals below remain authoritative for exact commands. For ordinary Windows/Mac USB writing and installation, use [the nontechnical guide](docs/user/INSTALL_FROM_USB.md) instead.

Not required for ordinary Activity work.

Read:

```text
skills/greia-os-work/SKILL.md
skills/greia-os-work/BOOT.md
docs/agents/GREIA_AGENT_OPERATIONS.md
docs/engineering/boot/INSTALLER_IMAGE_CREATION_AND_BOOT.md
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

The release-candidate runbook (frozen SHA, operator public key, USB identification, required PASS lines, pre-build gates G1–G11) is `docs/engineering/boot/INSTALLER_IMAGE_CREATION_AND_BOOT.md` §13. Boot console policy (`diagnostic` vs `quiet`, hidden verbose paths) is §7 there.

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
| Installer/image creation | `docs/engineering/boot/INSTALLER_IMAGE_CREATION_AND_BOOT.md` |
| Public-release gate | `docs/release/GREIA_PUBLIC_RELEASE_READINESS.md` |

## 12. Current readiness ledger

| Surface | Current state |
|---|---|
| Repository source verification | `make verify`; execute on exact current checkout before claiming PASS |
| Activity Simulator | implemented/documented; desktop development dependencies required |
| Developer remote | implemented for explicit developer images only |
| Voice Production Engine | implemented/canonical; provider readiness is workstation-specific and reported by `doctor` |
| Character production (all six) | shared local VoxStage/VoxCPM2 default behind VoiceEngine; Chatterbox explicitly selectable |
| Pedagogical production | independent macOS native provider; Dani now uses the cloned-character route |
| ASR verification | Parakeet-TDT v3 for new requests, Whisper retained for historical review; advisory only, never acceptance authority |
| Shared reactions | **180 EN/IT recordings were owner-accepted in the v0.2 baseline**; selected Dani/Momo/Tito rows included in the 2026-10-21 v3 corpus replacement are now pending fresh listening, with prior bytes/receipts backed up externally |
| Character introductions | **12 EN/IT introductions were owner-accepted in the v0.2 baseline**; selected Dani/Momo/Tito introductions included in the 2026-10-21 v3 replacement are now pending fresh listening; product placement separate |
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
