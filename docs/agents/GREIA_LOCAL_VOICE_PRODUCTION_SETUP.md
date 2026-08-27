# Greia Local Voice Production Setup for Agents

**Status:** canonical authoring-workstation setup for the Voice Production Engine  
**Reviewed:** 2026-08-28  
**Purpose:** install/probe the optional local providers used by `tools/greia_voice.py`  
**Not shipped to:** Greia child devices or Activity packages

## 1. Canonical boundary

Greia voice production is invoked through:

```text
tools/greia_voice.py
```

Do not install a TTS backend and then call it directly from an Activity, OS/shared-library or Encyclopedia script. Chatterbox, native TTS, Whisper and FFmpeg are providers/helpers behind the Greia Voice Production Engine.

Read first:

```text
AGENTS.md
SETUP.md
skills/greia-voice-production/SKILL.md
tools/greia_voice_core/README.md
docs/design/GREIA_VOICE_GENERATION_AND_CANONICAL_VOICES.md
docs/architecture/GREIA_VOICE_PRODUCTION_ENGINE.md
assets/audio/characters/canonical/v0.1/manifest.toml
```

The low-level Chatterbox field guide is maintainer/troubleshooting material only:

```text
docs/agents/GREIA_CHATTERBOX_PRODUCTION_FIELD_GUIDE.md
```

## 2. Start with `doctor`

The engine source is already in the repository. Before installing anything run:

```bash
python3 tools/greia_voice.py doctor
```

This is non-mutating. It checks:

```text
canonical reference presence/hash
FFmpeg availability
Chatterbox MLX provider imports
native/system speech provider availability
Whisper availability
```

It does not install packages or download model weights.

If the provider required for the requested work is already available, do not reinstall it.

## 3. Installation policy

The heavy cloned-character stack is optional for a general Greia development workstation, but when **actual character voice production is requested**, install/use the canonical voice profile rather than improvising another TTS setup.

Do not silently install multi-GB models merely while designing an Activity. Installation or first model download requires owner authorization.

Machine-local material stays outside Git:

```text
virtual environment
Hugging Face/model caches
scratch/rejected audio
service locks/state
```

## 4. Current full production host: Apple Silicon macOS

The current implemented full path is:

```text
character/shared cloned speech -> mlx-community/chatterbox-multilingual-v3
optional verification          -> mlx-community/whisper-tiny
pedagogical/Dani speech         -> macOS say + afconvert
packaging                       -> FFmpeg
```

Recommended environment:

```bash
export GREIA_VOICE_HOME="${HOME}/Library/Application Support/Greia/voice-production"
export GREIA_VOICE_CACHE="${HOME}/Library/Caches/Greia/voice-production"
export HF_HOME="${GREIA_VOICE_CACHE}/huggingface"
export HF_HUB_DISABLE_TELEMETRY=1

mkdir -p "${GREIA_VOICE_HOME}" "${GREIA_VOICE_CACHE}" "${HF_HOME}"
```

### 4.1 Install with `uv` (preferred)

```bash
uv venv "${GREIA_VOICE_HOME}/venv" --python 3.12
uv pip install --python "${GREIA_VOICE_HOME}/venv" \
  -r tools/greia_voice_requirements_mlx.txt
```

### 4.2 Standard `venv` / `pip` alternative

```bash
python3.12 -m venv "${GREIA_VOICE_HOME}/venv"
"${GREIA_VOICE_HOME}/venv/bin/python" -m pip install -U pip
"${GREIA_VOICE_HOME}/venv/bin/python" -m pip install \
  -r tools/greia_voice_requirements_mlx.txt
```

The tested dependency file currently pins:

```text
mlx-audio==0.5.0
mlx==0.32.1
soundfile==0.14.0
sentencepiece==0.2.2
mlx-whisper==0.4.3
```

Do not move this venv into the repository or an Activity folder.

## 5. FFmpeg

FFmpeg is the canonical authoring-time packaging/inspection dependency.

Check:

```bash
ffmpeg -version
ffprobe -version
```

On macOS, if missing and installation is owner-authorized:

```bash
brew install ffmpeg
```

Do not package FFmpeg in an Activity merely because authoring used it.

## 6. Native pedagogical/Dani provider

On macOS, `say` and `afconvert` are OS-provided. No Python model is required for deterministic pedagogical/Dani speech.

The engine currently owns the tested profiles and pronunciation workarounds. Activity scripts must not hard-code Alice/Samantha, speech rates or accent overrides.

Optional host-voice overrides are engine configuration only:

```text
GREIA_VOICE_PEDAGOGICAL_VOICE_IT
GREIA_VOICE_PEDAGOGICAL_VOICE_EN
GREIA_VOICE_DANI_VOICE_IT
GREIA_VOICE_DANI_VOICE_EN
```

Any changed profile still requires human listening.

## 7. Activate and verify

```bash
source "${GREIA_VOICE_HOME}/venv/bin/activate"
python tools/greia_voice.py doctor
```

A full Apple-Silicon character-production environment should show:

```text
canonical anchors: OK
ffmpeg: available
chatterbox-mlx-multilingual-v3: available
macos-native-say: available
mlx-whisper-tiny: available   # optional but recommended
```

A canonical reference hash mismatch is a hard stop. Do not replace/re-hash a reference locally to make `doctor` green.

## 8. Model download

`doctor` only probes imports and references. It does not intentionally load/download Chatterbox weights.

The first actual character/shared-library generation may fetch:

```text
mlx-community/chatterbox-multilingual-v3
```

The first Whisper verification may fetch:

```text
mlx-community/whisper-tiny
```

Do not trigger those downloads without owner authorization/network expectations.

## 9. Smoke tests through the engine

### Character dialogue

```bash
python tools/greia_voice.py generate \
  --speaker leo \
  --kind character_dialogue \
  --locale it \
  --text "Guardiamo con calma." \
  --cue-id smoke.leo \
  --output "${GREIA_VOICE_HOME}/smoke/leo.ogg"
```

### Pedagogical syllable

```bash
python tools/greia_voice.py generate \
  --speaker pedagogical \
  --kind pedagogical_speech \
  --locale it \
  --text "ma" \
  --cue-id smoke.phonics.ma \
  --verification off \
  --output "${GREIA_VOICE_HOME}/smoke/ma.wav"
```

### Dani

```bash
python tools/greia_voice.py generate \
  --speaker dani \
  --kind dani_system_speech \
  --locale it \
  --text "Schema completato!" \
  --cue-id smoke.dani \
  --output "${GREIA_VOICE_HOME}/smoke/dani.ogg"
```

Listen to every smoke clip. Process success is not acceptance.

## 10. Warm service / batch use

For repeated agent work:

```bash
python tools/greia_voice.py serve
```

Submit with `request`, then stop with:

```bash
python tools/greia_voice.py shutdown
```

For known queues:

```bash
python tools/greia_voice.py batch --input requests.jsonl
```

The engine owns model reuse, MLX cache clearing and the cross-process single-worker guard. Caller agents must not implement their own parallel inference loops.

## 11. Shared library production

The central Greia reaction library is also produced through the engine using:

```text
kind = shared_character_utterance
```

Lilli/Leo/Flash/Tito/Momo route to the cloned-character provider. Dani routes to native/system speech.

Normal Activities do not synthesize these at runtime; they resolve the reviewed shared family.

The exact phrase/library runbook is:

```text
docs/agents/GREIA_SHARED_CHARACTER_UTTERANCE_RECORDING.md
```

## 12. Unsupported hosts

The semantic engine can run `doctor` elsewhere, but current repository providers are intentionally honest:

```text
Apple-Silicon macOS -> full cloned-character + native system path
other macOS         -> native system path; MLX character path depends on actual provider support
Linux/Windows       -> no accepted native/character provider yet unless a new VoiceProvider is implemented
```

Do not bypass `UNAVAILABLE` by teaching Activities direct host-specific TTS commands. Add a provider behind `VoiceEngine` instead.

## 13. Review/package boundary

Successful generation writes audio + `.receipt.json` and leaves:

```text
human_review = PENDING
```

Human listening must verify exact words/locale, character identity where applicable, pronunciation, clipping/tails, delivery and small-speaker intelligibility.

Only the owning workflow may mark/package accepted audio. For example, Encyclopedia clips remain subject to `OWNER_ACCEPTED` in its ledger.

Never package:

```text
model weights
venvs
model caches
canonical reference masters
rejected/unreviewed takes
Whisper as a runtime dependency
```
