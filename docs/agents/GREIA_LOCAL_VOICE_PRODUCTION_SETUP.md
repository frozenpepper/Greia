# Greia Local Voice Production Setup for Agents

**Status:** canonical authoring-workstation setup for the Greia Voice Production Engine / authoring “Voice Studio” workflow  
**Reviewed:** 2026-08-28  
**Not shipped to:** Greia child devices or Activity packages

## 1. Canonical boundary

All Greia prerecorded speech production goes through:

```text
tools/greia_voice.py
```

Do not install a provider and then call it directly from an Activity, OS/shared-library or Encyclopedia script. Chatterbox, native TTS, Whisper and FFmpeg are provider/helper details behind `VoiceEngine`.

Read first:

```text
AGENTS.md
SETUP.md
skills/greia-voice-production/SKILL.md
tools/greia_voice_core/README.md
docs/design/GREIA_VOICE_GENERATION_AND_CANONICAL_VOICES.md
docs/architecture/GREIA_VOICE_PRODUCTION_ENGINE.md
```

The Chatterbox field guide is maintainer/troubleshooting material only:

```text
docs/agents/GREIA_CHATTERBOX_PRODUCTION_FIELD_GUIDE.md
```

## 2. Start with `doctor`

Before installing anything:

```bash
python3 tools/greia_voice.py doctor
```

This is non-mutating. It reports:

```text
canonical cloning-reference presence/hash
FFmpeg availability
registered synthesis-provider readiness
Whisper readiness
```

If the required provider is already available, do not reinstall it.

A canonical reference hash mismatch is a hard stop. Never replace/re-hash a reference locally to make the probe green.

## 3. Installation policy

The engine source ships in the repository. The heavy cloned-character environment is optional on a general Greia workstation and needed only for actual natural-character production.

Do not silently install/download multi-GB model stacks. Installation and first model download require owner authorization.

Keep machine-local material outside Git:

```text
virtual environments
model/Hugging Face caches
review/rejected audio
service locks/state
```

Recommended machine-local roots on macOS:

```bash
export GREIA_VOICE_HOME="${HOME}/Library/Application Support/Greia/voice-production"
export GREIA_VOICE_CACHE="${HOME}/Library/Caches/Greia/voice-production"
export HF_HOME="${GREIA_VOICE_CACHE}/huggingface"
export HF_HUB_DISABLE_TELEMETRY=1
mkdir -p "${GREIA_VOICE_HOME}" "${GREIA_VOICE_CACHE}" "${HF_HOME}"
```

## 4. Full current production host: Apple-Silicon macOS

Current implemented route:

```text
Lilli/Leo/Flash/Tito/Momo -> mlx-community/chatterbox-multilingual-v3
optional ASR warning       -> mlx-community/whisper-tiny
pedagogical speech         -> macOS say + afconvert behind VoiceEngine
Dani speech                -> macOS say + afconvert behind VoiceEngine
packaging                  -> FFmpeg
```

### Preferred install with `uv`

```bash
uv venv "${GREIA_VOICE_HOME}/venv" --python 3.12
uv pip install --python "${GREIA_VOICE_HOME}/venv/bin/python" \
  -r tools/greia_voice_requirements_mlx.txt
```

### Standard venv/pip alternative

```bash
python3.12 -m venv "${GREIA_VOICE_HOME}/venv"
"${GREIA_VOICE_HOME}/venv/bin/python" -m pip install -U pip
"${GREIA_VOICE_HOME}/venv/bin/python" -m pip install \
  -r tools/greia_voice_requirements_mlx.txt
```

Install FFmpeg if missing and owner-authorized:

```bash
brew install ffmpeg
```

Activate and probe:

```bash
source "${GREIA_VOICE_HOME}/venv/bin/activate"
python3 tools/greia_voice.py doctor
```

For full natural-character production, expect the cloning references, FFmpeg, Chatterbox provider and native macOS provider to be available. Whisper is optional but recommended.

The first actual natural-character generation may download the Chatterbox model; the first eligible verification may download Whisper. `doctor` itself should not be treated as permission to trigger those downloads.

## 5. Other hosts

The semantic CLI can run on other hosts, but the current accepted provider implementation is not feature-equivalent there.

### Intel macOS

Natural-character MLX generation is unavailable. Native macOS pedagogical/Dani generation may still be available. Do not invent a direct non-engine character path.

### Linux

Current repository source does **not** provide an accepted Linux cloned-character or native/system provider. `doctor` must report unavailable providers truthfully. Installing `espeak`, Piper, Coqui or another engine does not authorize Activity scripts to bypass `VoiceEngine`.

### Windows

Current repository source does **not** provide an accepted Windows cloned-character or native/system provider. `doctor` must report unavailable providers truthfully.

Provider gaps are solved by implementing/reviewing a `VoiceProvider` behind the engine, not by teaching Activities host-specific shell commands.

## 6. Native pedagogical/Dani policy

On macOS the engine owns native voice choice, rates and pronunciation workarounds.

Activity scripts must not hard-code:

```text
Alice
Samantha
say
afconvert
accent/phonetic overrides
```

Optional host voice overrides are engine configuration only:

```text
GREIA_VOICE_PEDAGOGICAL_VOICE_IT
GREIA_VOICE_PEDAGOGICAL_VOICE_EN
GREIA_VOICE_DANI_VOICE_IT
GREIA_VOICE_DANI_VOICE_EN
```

Any changed profile still requires human listening.

## 7. Smoke tests

### Natural-character dialogue

```bash
python3 tools/greia_voice.py generate \
  --speaker leo \
  --kind character_dialogue \
  --locale it \
  --text "Guardiamo con calma." \
  --cue-id smoke.leo \
  --output "${GREIA_VOICE_HOME}/smoke/leo.ogg"
```

### Pedagogical target

```bash
python3 tools/greia_voice.py generate \
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
python3 tools/greia_voice.py generate \
  --speaker dani \
  --kind dani_system_speech \
  --locale it \
  --text "Schema completato!" \
  --cue-id smoke.dani \
  --output "${GREIA_VOICE_HOME}/smoke/dani.ogg"
```

Listen to every smoke clip. Process success is not acceptance.

## 8. Warm service / batch

Repeated work should reuse one engine/model:

```bash
python3 tools/greia_voice.py serve
```

Submit requests with `request` and stop with:

```bash
python3 tools/greia_voice.py shutdown
```

Known queues may use:

```bash
python3 tools/greia_voice.py batch --input requests.jsonl
```

The engine owns the cross-process generation lock and model reuse. Do not launch parallel Chatterbox workers.

## 9. Immediate pending production jobs

The authoring infrastructure exists, but two shared OS content tranches still need actual production and owner listening.

### 9.1 Shared reaction library — 180 candidates

```text
6 characters × 5 families × 3 variants × 2 locales = 180
```

Generate through:

```bash
python3 tools/record_shared_character_utterances.py
```

Exact runbook:

```text
docs/agents/GREIA_SHARED_CHARACTER_UTTERANCE_RECORDING.md
```

Do not call the shared library complete until generation, listening, accepted-set promotion and runtime resolver evidence exist.

### 9.2 Character introduction pack — 12 candidates

```text
6 characters × 2 locales = 12
```

The scripts/cue IDs are defined in:

```text
docs/design/GREIA_VOICE_GENERATION_AND_CANONICAL_VOICES.md
```

Generate them through `tools/greia_voice.py batch` using the requests in the shared recording runbook. They remain review-only until listened to and promoted by the later OS integration tranche.

Their final UI placement is intentionally open: first-run meet-the-cast, tappable characters on Home, a character gallery, or another non-blocking OS presentation.

## 10. Review/package boundary

Every successful generation produces audio + receipt and remains:

```text
human_review = PENDING
```

Human listening verifies:

- exact words/locale;
- character identity where applicable;
- pronunciation/stress;
- clipping/tails/noise;
- delivery;
- small-speaker intelligibility.

Whisper PASS never substitutes for listening.

Only the owning workflow may promote accepted audio into source/runtime assets.

Never package or commit as runtime content:

```text
model weights
venvs
model caches
canonical cloning masters
rejected/unreviewed takes
Whisper runtime dependencies
```

## 11. Evidence to report after production

For any retained production run return:

```text
exact source SHA
doctor result
command/input queue used
review directory
candidate count
UNAVAILABLE/REJECTED/ASR-warning count
representative receipts
human accepted/rejected count
remaining missing variants
Dani voice-quality assessment
```

Do not convert setup success into an audio-acceptance claim.
