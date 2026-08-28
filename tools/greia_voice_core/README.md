# Greia Voice Production Engine — Quick Start

Greia uses one authoring-time voice tool for prerecorded speech:

```text
tools/greia_voice.py
```

Use it for new Activity, OS/shared-library and Encyclopedia voice production. Do **not** call Chatterbox, MLX, Whisper, macOS `say`, `afconvert` or FFmpeg directly from content-authoring scripts. Those are provider details owned by this engine.

The engine is authoring-only. It is **not installed on the child device** and does not add runtime TTS, speech recognition or model dependencies to Greia OS.

## Features

- semantic routing by `speaker + kind + locale + exact text`;
- canonical Lilli/Leo/Flash/Tito/Momo voice references with SHA-256 verification;
- deterministic native/system speech for pedagogical pronunciation and Dani;
- shared-character-library production through the same engine;
- optional Whisper verification for suitable generated dialogue;
- automatic bounded regeneration after likely ASR mismatch;
- model loaded once for batch/service runs;
- cross-process single-worker guard to avoid multiple multi-GB Chatterbox instances;
- WAV/OGG packaging and generation receipts;
- localhost warm service for repeated agent requests;
- provider-neutral design so future TTS engines can be added without changing Activity code.

Every generated clip remains `human_review = PENDING`. Whisper can reject or warn about suspicious output, but it never accepts audio.

## Speech kinds

| Kind | Use | Current route |
|---|---|---|
| `character_dialogue` | presenter dialogue, narration, hints, facts | canonical character provider |
| `shared_character_utterance` | producing Greia's central praise/retry/start library | canonical character provider; Dani uses system speech |
| `pedagogical_speech` | letters, syllables, phonics, pronunciation targets | deterministic native/system speech |
| `dani_system_speech` | Activity-specific Dani dialogue | deterministic native/system speech |

For normal Activity playback of a **shared** utterance, request the reviewed shared family from Greia at runtime; do not synthesize it on the child device. `shared_character_utterance` here is for producing/extending that shared library during authoring.

---

# Installation

## 1. Base tool

The engine source is already part of the Greia repository. There is no package to install into Greia OS.

Requirements for the CLI itself:

- Python **3.11+** (`tomllib` is used; Python 3.12 is the tested production version);
- the Greia repository checkout;
- canonical voice assets when character cloning is requested.

From the repository root:

```bash
python3 tools/greia_voice.py doctor
```

`doctor` is non-mutating: it checks what is already available and does not download model weights.

## 2. Full Apple-Silicon production setup

The currently implemented full character-production provider is the tested macOS/Apple-Silicon MLX path.

Keep the environment and model cache outside the repository:

```bash
export GREIA_VOICE_HOME="${HOME}/Library/Application Support/Greia/voice-production"
export GREIA_VOICE_CACHE="${HOME}/Library/Caches/Greia/voice-production"
export HF_HOME="${GREIA_VOICE_CACHE}/huggingface"
export HF_HUB_DISABLE_TELEMETRY=1

mkdir -p "${GREIA_VOICE_HOME}" "${GREIA_VOICE_CACHE}" "${HF_HOME}"
```

### Recommended install with `uv`

```bash
uv venv "${GREIA_VOICE_HOME}/venv" --python 3.12
uv pip install --python "${GREIA_VOICE_HOME}/venv" \
  -r tools/greia_voice_requirements_mlx.txt
```

### Standard `venv` / `pip` alternative

```bash
python3.12 -m venv "${GREIA_VOICE_HOME}/venv"
"${GREIA_VOICE_HOME}/venv/bin/python" -m pip install -U pip
"${GREIA_VOICE_HOME}/venv/bin/python" -m pip install \
  -r tools/greia_voice_requirements_mlx.txt
```

FFmpeg is required for canonical WAV/OGG packaging. On macOS, when installation is owner-authorized:

```bash
brew install ffmpeg
```

macOS `say` and `afconvert` are supplied by the OS and are used by the deterministic pedagogical/Dani provider.

Activate the voice environment before using the full MLX stack:

```bash
source "${GREIA_VOICE_HOME}/venv/bin/activate"
python tools/greia_voice.py doctor
```

A healthy full Apple-Silicon setup should report:

- canonical cloning anchors present and hash-valid;
- `ffmpeg` available;
- `chatterbox-mlx-multilingual-v3` available;
- `macos-native-say` available;
- `mlx-whisper-tiny` available when optional ASR verification is installed.

The first actual Chatterbox generation may download `mlx-community/chatterbox-multilingual-v3` weights if they are not already cached. Do not trigger that network download without owner authorization.

## 3. Per-host install

Pick the section that matches your machine. The semantic engine and `doctor` are portable, but each provider is OS-specific.

### macOS on Apple Silicon (M1/M2/M3/M4, arm64) — full cloned-character production

Same as §2 above. This is the **only** configuration with a complete provider stack today.

### Intel macOS — pedagogical/Dani only

The MLX provider requires Apple Silicon, so `chatterbox-mlx-multilingual-v3` and `mlx-whisper-tiny` are `UNAVAILABLE`. Install only `soundfile` and `sentencepiece` and keep `macos-native-say` for `pedagogical_speech` and `dani_system_speech`.

### Linux — system speech only (no cloned character yet)

No `VoiceProvider` for `pedagogical_speech`/`dani_system_speech` ships for Linux; the engine reports `UNAVAILABLE` honestly. Install `ffmpeg` and `espeak-ng` via your package manager so they are present whenever a Linux provider lands. Do not synthesize speech through `subprocess`/`espeak`/`piper` directly from Activity or skill code.

### Windows — no providers yet

The engine source and `doctor` work; every provider reports `UNAVAILABLE` until a Windows-native `VoiceProvider` is implemented. Install `ffmpeg` (e.g. `winget install Gyan.FFmpeg`) but do not route speech through `System.Speech`/`Add-Type` to make providers appear available.

Add future backends behind the `VoiceProvider` interface in `tools/greia_voice_core/providers.py`. Do not teach Activities, OS, shared-library or Encyclopedia scripts a new host-specific backend command.

For detailed installation/troubleshooting, see:

```text
docs/agents/GREIA_LOCAL_VOICE_PRODUCTION_SETUP.md
```

The Chatterbox field guide is for **engine maintainers/troubleshooting only**:

```text
docs/agents/GREIA_CHATTERBOX_PRODUCTION_FIELD_GUIDE.md
```

---

# Usage

## Check readiness

```bash
python tools/greia_voice.py doctor
```

## Generate one character line

```bash
python tools/greia_voice.py generate \
  --speaker leo \
  --kind character_dialogue \
  --locale it \
  --text "Guardiamo con calma." \
  --cue-id presenter.hint \
  --output ./tmp/voice-review/presenter-hint.ogg
```

## Generate a syllable deterministically

```bash
python tools/greia_voice.py generate \
  --speaker pedagogical \
  --kind pedagogical_speech \
  --locale it \
  --text "ma" \
  --cue-id phonics.ma \
  --verification off \
  --output ./tmp/voice-review/phonics-ma.wav
```

Do not ask a canonical character to speak a pronunciation-authoritative teaching target merely to preserve mascot identity.

## Generate Dani

```bash
python tools/greia_voice.py generate \
  --speaker dani \
  --kind dani_system_speech \
  --locale it \
  --text "Schema completato!" \
  --cue-id dani.complete \
  --output ./tmp/voice-review/dani-complete.ogg
```

## Batch generation

Create newline-delimited JSON (`.jsonl`), one semantic request per line:

```json
{"speaker":"tito","kind":"character_dialogue","locale":"it","text":"Guarda cosa abbiamo scoperto!","cue_id":"curiosity.discovery","output":"./tmp/voice-review/discovery.ogg"}
{"speaker":"pedagogical","kind":"pedagogical_speech","locale":"it","text":"to","cue_id":"phonics.to","output":"./tmp/voice-review/to.wav","verification":"off"}
```

Run:

```bash
python tools/greia_voice.py batch --input requests.jsonl
```

The model is kept warm for the batch and generation stays single-worker.

## Warm service for agents

When an agent will request many clips over time:

```bash
python tools/greia_voice.py serve
```

Then from another shell:

```bash
python tools/greia_voice.py request \
  --speaker lilli \
  --kind character_dialogue \
  --locale en \
  --text "Let's try something new!" \
  --cue-id presenter.try-new \
  --output ./tmp/voice-review/try-new.ogg
```

Stop cleanly:

```bash
python tools/greia_voice.py shutdown
```

The service binds only to localhost. Do not expose it on the LAN.

---

# Output and review

Every successful generation produces:

```text
<requested audio file>
<requested audio file>.receipt.json
```

The receipt records the semantic request, provider, voice/reference identity, generation parameters, optional ASR result, attempts and output hash.

Machine success is not acceptance. Before integrating audio, a human must listen for:

- exact words and correct locale;
- correct character identity when applicable;
- correct pronunciation/stress;
- no repeated or invented sounds;
- no clipped start/end or unwanted tail;
- appropriate delivery and small-speaker intelligibility.

For pedagogical speech, exact educational pronunciation is the primary gate.

Existing owner-accepted audio does **not** need to be regenerated just because its historical script predates this engine.

---

# Rule for new Greia work

For new voice production:

```text
Activity / OS / Encyclopedia author
    -> semantic request
    -> tools/greia_voice.py
    -> provider chosen by VoiceEngine
    -> review asset + receipt
    -> human listening
    -> owning workflow integrates only accepted audio
```

Do not add another Activity-specific Chatterbox/system-TTS/Whisper implementation. Legacy `generate_*_audio.py` scripts are historical compatibility/evidence unless and until converted into thin semantic request producers.