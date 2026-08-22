# Greia Local Voice Production Setup for Agents

**Status:** local developer/Activity Designer setup procedure  
**Date:** 2026-08-22  
**Purpose:** install only the lightweight local production renderer used to turn approved Greia reference voices into Activity audio  
**Does not install:** Qwen VoiceDesign, MOSS-VoiceGenerator, cloud voice tools, or any child-device runtime model

## 1. Read first

Before doing voice-production work, read:

```text
AGENTS.md
docs/DOCUMENTATION.md
docs/design/GREIA_VOICE_GENERATION_AND_CANONICAL_VOICES.md
skills/greia-activity-authoring/SKILL.md
assets/audio/characters/canonical/v0.1/README.md
assets/audio/characters/canonical/v0.1/manifest.toml
```

The canonical character references are repository assets. Model weights, virtual environments, caches and generated review output are **not** repository assets.

## 2. Scope and stop conditions

This procedure is for a developer Mac or other owner-approved authoring machine.

Stop and report instead of improvising when:

- the machine architecture is not known;
- the reference file hash differs from `manifest.toml`;
- the requested voice ID is not registered;
- generation would require uploading project references or child data to a cloud service;
- the model/backend version cannot be identified;
- a dependency asks for broad system privileges;
- output contains repeated/omitted text, wrong language, corruption or obvious voice-identity drift.

Do not install any package into the Greia OS image or an Activity package.

## 3. Preferred Apple Silicon path: MLX Audio

Use this on an `arm64` M1/M2/M3/M4/M5-class Mac. It is the preferred path because MLX uses Apple Silicon and unified memory directly.

### 3.1 Verify host

```bash
uname -s
uname -m
python3 --version
```

Expected:

```text
Darwin
arm64
Python 3.10 or newer
```

If `uname -m` is `x86_64`, skip to the ONNX fallback section.

### 3.2 Install small host prerequisites

Use Homebrew only for tools that are genuinely missing:

```bash
command -v brew >/dev/null 2>&1 || {
  echo "Homebrew is required by this procedure for ffmpeg/uv. Ask the owner before installing it."
  exit 1
}

brew list uv >/dev/null 2>&1 || brew install uv
brew list ffmpeg >/dev/null 2>&1 || brew install ffmpeg
```

`ffmpeg` is used for final OGG/WAV conversion and inspection. It is not required to preserve the canonical source masters or production anchors.

### 3.3 Create one shared authoring environment outside the repository

```bash
export GREIA_VOICE_HOME="${HOME}/Library/Application Support/Greia/voice-production"
export GREIA_VOICE_CACHE="${HOME}/Library/Caches/Greia/voice-production"
export HF_HOME="${GREIA_VOICE_CACHE}/huggingface"
export HF_HUB_DISABLE_TELEMETRY=1

mkdir -p "${GREIA_VOICE_HOME}" "${GREIA_VOICE_CACHE}" "${HF_HOME}"

uv venv "${GREIA_VOICE_HOME}/venv" --python 3.12
source "${GREIA_VOICE_HOME}/venv/bin/activate"

uv pip install --upgrade pip
uv pip install "mlx-audio"
```

Do not create `.venv` inside an Activity, `assets/`, or the Greia repository.

Record installed versions:

```bash
python - <<'PY'
import importlib.metadata
for package in ("mlx", "mlx-audio"):
    try:
        print(package, importlib.metadata.version(package))
    except importlib.metadata.PackageNotFoundError:
        print(package, "NOT INSTALLED")
PY
```

### 3.4 Pre-warm the model cache

From the Greia repository root:

```bash
source "${GREIA_VOICE_HOME}/venv/bin/activate"

python -m mlx_audio.tts.generate \
  --model mlx-community/MOSS-TTS-Nano-100M \
  --text "Hello from Greia." \
  --ref_audio assets/audio/characters/canonical/v0.1/lilli-reference-v1.flac \
  --output_path "${GREIA_VOICE_CACHE}/smoke-output"
```

The first run downloads model/tokenizer assets into `HF_HOME`. Do not move that cache into Git.

Confirm that an audio file was created and is readable:

```bash
find "${GREIA_VOICE_CACHE}/smoke-output" -type f -print
for file in "${GREIA_VOICE_CACHE}/smoke-output/"*.wav; do
  [ -e "${file}" ] || continue
  ffprobe -v error -show_entries stream=codec_name,sample_rate,channels \
    -of default=noprint_wrappers=1 \
    "${file}"
done
```

Listen to the output. A successful process exit is not sufficient quality evidence.

## 4. Efficient batch production

For one or two smoke clips, the CLI is acceptable. For an Activity voice set, do not reload the model once per cue.

Activity Designer or a local batch script should keep one Python process alive:

```python
from pathlib import Path

from mlx_audio.audio_io import write as audio_write
from mlx_audio.tts import load

model = load("mlx-community/MOSS-TTS-Nano-100M")

jobs = [
    {
        "text": "Ciao! Giochiamo insieme?",
        "reference": Path(
            "assets/audio/characters/canonical/v0.1/lilli-reference-v1.flac"
        ),
        "output": Path("build/voice-review/it/welcome.wav"),
    },
]

for job in jobs:
    result = next(
        model.generate(
            text=job["text"],
            ref_audio=str(job["reference"]),
        )
    )
    job["output"].parent.mkdir(parents=True, exist_ok=True)
    audio_write(str(job["output"]), result.audio, result.sample_rate)
```

This code is illustrative until a Greia-owned compiler/worker is implemented. Do not duplicate it across Activities as a runtime dependency.

Recommended grouping:

```text
one model load
→ one voice/reference at a time
→ all cues for that voice/locale
→ next voice/locale
```

Use a content-addressed cache. Never infer cache identity only from `welcome.wav`.

## 5. Portable fallback: upstream ONNX CPU

Use this only when MLX is unavailable or the owner needs parity with a non-Apple authoring machine.

The upstream project provides an ONNX CPU backend:

```bash
moss-tts-nano generate \
  --backend onnx \
  --prompt-speech <reference.flac> \
  --text "<text>" \
  --output <output.wav>
```

Current upstream packaging may install more dependencies than the pure inference path needs. Follow the upstream repository's pinned instructions rather than deleting imports or inventing an unreviewed “minimal” dependency set.

Keep it isolated outside the Greia repository:

```bash
export GREIA_VOICE_HOME="${HOME}/.local/share/greia/voice-production"
export GREIA_VOICE_CACHE="${HOME}/.cache/greia/voice-production"
mkdir -p "${GREIA_VOICE_HOME}" "${GREIA_VOICE_CACHE}"
```

Clone/pin the upstream source under `${GREIA_VOICE_HOME}/sources/`, create a dedicated environment, record the exact commit, and keep model downloads in `${GREIA_VOICE_CACHE}`.

The ONNX backend is a production fallback, not a reason to add PyTorch or model weights to an Activity package.

## 6. Canonical voice lookup

Use the manifest; do not guess filenames.

Current mapping:

```text
greia.lilli.v1 → lilli-reference-v1.flac
greia.leo.v1   → leo-reference-v1.flac
greia.flash.v1 → flash-reference-v1.flac
greia.tito.v1  → tito-reference-v1.flac
greia.momo.v1  → momo-reference-v1.flac
```

Dani has no reference file:

```text
greia.dani.system-v1 → Greia OS TTS policy
```

Do not generate Dani through another character reference. Do not use arbitrary macOS `say` voices as the canonical policy unless the platform implementation explicitly adopts one.

## 7. Verify reference integrity before a batch

From the repository root:

```bash
shasum -a 256 assets/audio/characters/canonical/v0.1/*-reference-v1.flac
```

Compare each result with `manifest.toml`.

Also inspect:

```bash
for file in assets/audio/characters/canonical/v0.1/*-reference-v1.flac; do
  echo "== ${file}"
  ffprobe -v error \
    -show_entries format=duration:stream=codec_name,sample_rate,channels,bits_per_raw_sample \
    -of default=noprint_wrappers=1 \
    "${file}"
done
```

Expected production anchors are mono, 24 kHz, 16-bit lossless FLAC, each exactly 12 seconds and derived from the source master recorded in `manifest.toml`. Do not “repair” them in place.

## 8. Work and output directories

Use ignored/rebuildable directories, for example:

```text
build/voice-review/
build/voice-cache/
```

or the external cache configured above.

Final accepted Activity assets go to:

```text
activities/<activity>/locales/<locale>/audio/
```

Only after human review and post-processing.

Do not commit:

```text
model weights
Hugging Face cache
venv/site-packages
raw generation scratch
rejected variants
temporary service logs
```

The five full source masters and five lossless production anchors are deliberate shared source assets under `assets/source/audio/character-voice-masters/v0.1/` and `assets/audio/characters/canonical/v0.1/`; they are never copied into Activity packages.

## 9. Post-process accepted WAV masters

Keep generation masters as WAV during review. Convert only accepted clips.

Example OGG Vorbis package output:

```bash
ffmpeg -hide_banner -nostdin -y \
  -i build/voice-review/it/welcome.wav \
  -af "loudnorm=I=-18:LRA=7:TP=-1.5" \
  -ac 1 \
  -c:a libvorbis -q:a 5 \
  activities/<activity>/locales/it/audio/welcome.ogg
```

For pronunciation-critical or extremely short clips, retaining WAV may be preferable.

Always listen after conversion. Verify:

```bash
ffprobe -v error \
  -show_entries format=duration:stream=codec_name,sample_rate,channels \
  -of default=noprint_wrappers=1 \
  activities/<activity>/locales/it/audio/welcome.ogg
```

Do not normalize the canonical source masters or production anchors. Post-processing applies to generated Activity playback assets.

## 10. Required generation receipt

Until Greia implements a receipt schema, preserve at least this information in local build evidence:

```text
Activity ID
cue ID
locale
exact text
voice ID
voice-manifest version
reference SHA-256
renderer/model ID
model revision when available
mlx-audio or upstream version
backend
generation parameters
post-processing profile
output SHA-256
human reviewer/disposition
```

Do not put secrets, machine usernames or absolute private paths into portable Activity source.

## 11. Human review gate

For every accepted cue:

1. listen from beginning to end;
2. confirm exact words and locale;
3. confirm the intended character;
4. check repeated/omitted words;
5. check pronunciation and pacing;
6. check clipping, noise and excessive silence;
7. play through laptop/small-speaker output;
8. play it in the actual Activity sequence;
9. confirm no speech overlap;
10. confirm caption/string parity.

For literacy, phoneme, spelling or foreign-language teaching audio, require a fluent human/educator review.

## 12. Cleanup and upgrades

The shared environment and model cache are intentionally reusable.

To remove only generated review output:

```bash
rm -rf "${GREIA_VOICE_CACHE}/smoke-output"
rm -rf build/voice-review build/voice-cache
```

Do not wipe the shared model cache at the end of every task; that wastes bandwidth and time.

Before upgrading `mlx-audio`, the model revision, or the post-processing profile:

- record the previous versions;
- generate a small fixed regression set for all five voices;
- compare identity, pronunciation, speed and artifacts;
- do not invalidate accepted audio merely because a newer package exists;
- update the Greia voice documentation/manifest policy if output authority changes.

## 13. Source references

Primary implementation references:

- OpenMOSS MOSS-TTS-Nano repository: `https://github.com/OpenMOSS/MOSS-TTS-Nano`
- upstream model: `OpenMOSS-Team/MOSS-TTS-Nano-100M`
- MLX Audio: `https://github.com/Blaizzy/mlx-audio`
- MLX model: `mlx-community/MOSS-TTS-Nano-100M`

These are development dependencies, not child-runtime dependencies.
