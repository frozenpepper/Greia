# Greia Local Voice Production Setup for Agents

**Status:** optional local developer/Activity Designer setup procedure  
**Date:** 2026-08-23  
**Purpose:** configure local custom Greia character speech production when the owner explicitly wants it  
**Not required for:** ordinary Activity authoring, shared Greia character utterances, pedagogical/system speech, or child-runtime playback

## 1. Read first

Before custom character-voice production, read:

```text
AGENTS.md
SETUP.md
docs/design/GREIA_VOICE_GENERATION_AND_CANONICAL_VOICES.md
docs/design/GREIA_SHARED_CHARACTER_UTTERANCES.md
skills/greia-activity-authoring/SKILL.md
skills/greia-activity-authoring/VOICE_GENERATION.md
assets/audio/characters/canonical/v0.1/manifest.toml
```

## 2. Opt-in rule

**Do not install this toolchain automatically.**

A normal Activity authoring environment does not need a cloning model.

Before installing anything, determine whether the Activity can use:

```text
shared Greia character utterance
or
deterministic pedagogical/system speech
or
visual/text feedback without custom dialogue
```

Only configure Chatterbox when the owner explicitly requests custom canonical character dialogue or has already opted into the `voice` setup profile.

If the toolchain is absent and the user has not requested installation, return `UNAVAILABLE` to the authoring workflow and let the Activity skill drop optional custom character speech.

## 3. Current renderer policy

Current custom character renderer:

```text
Chatterbox Multilingual V3
upstream: Resemble AI Chatterbox
license: MIT
Italian: supported
purpose: reviewed zero-shot cloning for normal character speech
```

Rejected paths:

```text
MOSS-TTS-Nano                       REJECTED — production quality unsuitable
repeated "ma. ma. ma." generation  REJECTED — local test worsened results
Chatterbox for phonics/syllables    REJECTED — pronunciation inconsistency
```

For pronunciation-authoritative teaching audio, use the pedagogical/system path defined by the voice design document.

## 4. Canonical reference integrity

Use the manifest; do not guess filenames or replace references locally.

Current cloning IDs:

```text
greia.lilli.v1
greia.leo.v1
greia.flash.v1
greia.tito.v1
greia.momo.v1
```

Dani is not cloned:

```text
greia.dani.system-v1
```

Verify source/anchor hashes against:

```text
assets/audio/characters/canonical/v0.1/manifest.toml
```

A hash mismatch is a stop condition.

## 5. Cross-platform audio prerequisite

Use FFmpeg + ffprobe for authoring-time inspection, bounded trimming and package conversion.

Verify:

```bash
ffmpeg -version
ffprobe -version
```

These are authoring tools. Do not put FFmpeg binaries into an Activity package merely because they were used during production.

Typical host installation, only with owner approval:

### macOS

```bash
brew install ffmpeg
```

### Windows

Use an existing trusted FFmpeg install or an owner-approved package-manager install.

### Debian/Ubuntu

```bash
sudo apt-get install ffmpeg
```

## 6. Preferred Apple Silicon path: MLX Audio

On Apple Silicon, the preferred current path is the MLX conversion:

```text
mlx-community/chatterbox-multilingual-v3
```

Keep the environment and model cache outside the Greia checkout.

Example setup:

```bash
export GREIA_VOICE_HOME="${HOME}/Library/Application Support/Greia/voice-production"
export GREIA_VOICE_CACHE="${HOME}/Library/Caches/Greia/voice-production"
export HF_HOME="${GREIA_VOICE_CACHE}/huggingface"
export HF_HUB_DISABLE_TELEMETRY=1

mkdir -p "${GREIA_VOICE_HOME}" "${GREIA_VOICE_CACHE}" "${HF_HOME}"

python3 -m venv "${GREIA_VOICE_HOME}/venv"
source "${GREIA_VOICE_HOME}/venv/bin/activate"
python -m pip install -U pip mlx-audio
```

Do not create the environment inside an Activity or repository directory.

The first model use may download weights. Do not trigger that download unless the owner has opted into custom voice generation.

Example Italian smoke test:

```bash
mlx_audio.tts.generate \
  --model mlx-community/chatterbox-multilingual-v3 \
  --text "Ciao! Giochiamo insieme?" \
  --ref_audio assets/audio/characters/canonical/v0.1/lilli-reference-v1.flac \
  --lang_code it
```

Listen to the result. Process success is not audio acceptance.

## 7. Upstream/PyTorch path

On a supported non-MLX authoring machine, use the official Resemble AI Chatterbox package/repository and record the exact version/device backend.

The current upstream package exposes `chatterbox-tts`; follow the upstream version's installation instructions rather than copying an old Greia command blindly.

Keep:

```text
virtual environment
model weights/cache
generation scratch
```

outside the repository.

Do not make CUDA, PyTorch or Chatterbox an Activity dependency.

## 8. Non-mutating availability probe

Before an Activity authoring agent attempts custom dialogue, it should check the already-configured environment rather than installing one.

A successful probe should establish:

```text
configured Python/environment exists
Chatterbox implementation imports/starts
configured multilingual V3 model is known
canonical reference assets exist and hash correctly
ffmpeg/ffprobe exist when trimming is required
```

Do not treat network access or `pip` availability as a successful voice-toolchain probe.

If no configured environment is found, return `UNAVAILABLE` and let the Activity skill continue without optional custom voice.

A future `tools/greia_setup.py --profile voice --check` should own this probe centrally; do not proliferate incompatible ad-hoc probes once that tool exists.

## 9. Generation scope

Use Chatterbox for:

```text
normal character dialogue
narration spoken by a canonical character
character instructions/reactions
reviewed short character exclamations
```

Do not use it for:

```text
letters as teaching targets
syllables as teaching targets
phonics
spelling/pronunciation authority
foreign-language target pronunciation when exact sound is being taught
```

Those use the pedagogical/system speech path.

## 10. Short character clips

Ultra-short Chatterbox generation can append unwanted sounds.

For short **character dialogue**, a local production worker may use:

```text
bounded max output tokens
→ inspect generated WAV
→ ffmpeg/ffprobe analysis
→ bounded tail/edge trimming if the intended utterance itself is correct
→ human review
```

Do not use trimming to repair a wrong pronunciation or invented sound inside the intended utterance.

Do not use repeated prompt padding. The repeated-middle experiment is rejected.

## 11. Shared utterances require no local cloning setup

Generic reactions should preferably use Greia's shared character library:

```text
praise.congratulations
praise.great_work
praise.well_done
celebrate.you_did_it
encourage.try_again
ready.lets_go
```

See:

```text
docs/design/GREIA_SHARED_CHARACTER_UTTERANCES.md
```

Once those assets are implemented in Greia, Activity authors consume them through the shared semantic resolver and do not need Chatterbox locally.

## 12. Review masters and package conversion

Keep generated review masters as WAV.

For an accepted non-pronunciation-critical custom clip, OGG Vorbis is generally appropriate under current localized audio policy.

Example conversion:

```bash
ffmpeg -hide_banner -nostdin -y \
  -i build/voice-review/it/welcome.wav \
  -af "loudnorm=I=-18:LRA=7:TP=-1.5" \
  -ac 1 \
  -c:a libvorbis -q:a 5 \
  activities/<activity>/locales/it/audio/welcome.ogg
```

Listen again after conversion.

Do not normalize or overwrite canonical reference masters.

## 13. Generation receipt

For custom character speech preserve at least:

```text
Activity ID
cue ID
locale
exact text
voice ID
voice/reference manifest version
reference SHA-256
Chatterbox implementation/model ID
model/package revision
backend/device
generation parameters
max token limit if used
post-processing/trimming parameters
output SHA-256
human reviewer/disposition
```

No secrets or private absolute user paths belong in portable source metadata.

## 14. Human review gate

Every accepted custom character line must be listened to for:

```text
exact words
correct language
canonical character identity
no repeated/invented words or tail sounds
acceptable pronunciation
appropriate emotion
unclipped onset/ending
small-speaker intelligibility
no overlap with surrounding Activity speech
```

If the clip is pronunciation-authoritative, it should not have been routed through Chatterbox in the first place.

## 15. Child/package boundary

Never package:

```text
Chatterbox weights
model caches
MLX/PyTorch environment
canonical voice references
FFmpeg binaries solely for authoring
rejected generations
```

The child receives only final reviewed Activity-owned audio or resolves Greia shared/system speech through platform-owned interfaces.
