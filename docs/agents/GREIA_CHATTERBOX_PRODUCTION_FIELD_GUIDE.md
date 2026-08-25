# Greia — Chatterbox Voice Production Field Guide for Agents

**Status:** authoritative operational and troubleshooting field guide for project agents  
**Date:** 2026-08-23  
**Target Platform:** macOS Darwin arm64 (Apple Silicon Metal)  
**Primary Model:** `mlx-community/chatterbox-multilingual-v3`  
**Purpose:** provide incoming AI agents with exact platform quirks, installation recipes, process lifecycle management, token mechanics, and troubleshooting rules to guarantee predictable, clean, and resource-safe voice production.

---

## 1. Executive Overview & Architecture Boundary

Chatterbox Multilingual V3 is Greia's approved zero-shot voice cloning engine for canonical character voices (**Lilli, Leo, Flash, Tito, Momo**).

### What Chatterbox IS used for:
- Character reactions and shared exclamations (praise, celebrate, encourage, ready).
- Activity dialogue and narrative prompts spoken by canonical characters.
- Non-authoritative conversational speech.

### What Chatterbox IS NOT used for:
- **Dani:** Dani is intentionally robotic and must use Greia system-TTS (`greia.dani.system-v1`), never a cloned natural voice.
- **Pedagogical/Teaching Truth:** Educational syllable teaching, letter sounds, phonics, and spelling authority must use deterministic native system-TTS to guarantee zero phonetic hallucination.
- **Child-runtime execution:** Chatterbox models and weights are never shipped to the child device. Only pre-generated, reviewed, and approved audio assets are packaged.

---

## 2. Platform & Environment Setup (Apple Silicon / MLX)

### 2.1 Directory Isolation Rules
Do **NOT** install virtual environments, caches, or download model weights inside the Greia git repository or inside Activity folders.

Use standard macOS user application storage:
```bash
export GREIA_VOICE_HOME="${HOME}/Library/Application Support/Greia/voice-production"
export GREIA_VOICE_CACHE="${HOME}/Library/Caches/Greia/voice-production"
export HF_HOME="${GREIA_VOICE_CACHE}/huggingface"
export HF_HUB_DISABLE_TELEMETRY=1

mkdir -p "${GREIA_VOICE_HOME}" "${GREIA_VOICE_CACHE}" "${HF_HOME}"
```

### 2.2 Environment Creation with `uv`
Using `uv` provides fast, isolated virtual environment creation without polluting global Python or Anaconda base installations:

```bash
uv venv "${GREIA_VOICE_HOME}/venv" --python 3.12
uv pip install --python "${GREIA_VOICE_HOME}/venv" \
  mlx-audio==0.5.0 \
  mlx==0.32.1 \
  soundfile==0.14.0 \
  sentencepiece==0.2.2 \
  mlx-whisper==0.4.3
```

### 2.3 Required External Prerequisite: FFmpeg & ffprobe
FFmpeg is required for signal analysis, boundary detection, and format conversion. Verify that the host has FFmpeg installed with the required filters:

```bash
ffmpeg -version
ffprobe -version
ffmpeg -hide_banner -filters | grep -E "silencedetect|atrim|astats"
```
*(On macOS, install via `brew install ffmpeg` only if authorized by the user).*

---

## 3. Critical Process & Memory Lifecycle Management

> [!CAUTION]
> **Preventing Memory and Process Leaks:**
> In autoregressive speech generation on Apple Silicon Unified Memory, a single model instance occupies **3.0–4.5 GB of Metal RAM/swap**. Launching multiple subagent processes or failing to terminate background scripts will rapidly exhaust RAM and swap, causing system-wide degradation.

### Mandatory Rules for Every Agent:

1. **Pre-flight Process Check:**
   Before launching any audio generation script or batch run, always verify that no orphaned TTS processes are active:
   ```bash
   ps aux | grep -iE "voice-production|chatterbox" | grep -v grep || echo "Clean"
   ```
   If stale processes exist from an interrupted previous run, terminate them immediately before proceeding.

2. **Single-Process Model Lifecycle (Load Once, Batch Generate):**
   - **Never** spawn a new Python subprocess per audio file. Loading model weights takes ~3–5 seconds and re-allocates GBs of Metal buffers.
   - Load the model **once** in memory, iterate over the entire phrase matrix, and cleanly shut down at the end.

3. **Explicit Metal Memory Eviction & Garbage Collection After EVERY Utterance:**
   In autoregressive loops, MLX retains intermediate Metal allocation buffers across generation steps. To prevent memory ballooning, call `mx.clear_cache()` and `gc.collect()` immediately after writing each clip:
   ```python
   import gc
   import mlx.core as mx

   # Immediately after generating & saving each utterance:
   mx.clear_cache()  # Note: replaces deprecated mx.metal.clear_cache()
   gc.collect()
   ```

4. **Idempotency & Pre-check (Skip Existing Valid Clips):**
   Always check whether the destination `.wav` already exists and is non-empty before calling `model.generate()`. Skipping already produced clips avoids redundant inference passes, eliminates wasted memory overhead, and allows seamless resumption:
   ```python
   if dest_wav.exists() and dest_wav.stat().st_size > 1000:
       print(f"Skipping {key} (already exists)", flush=True)
       continue
   ```

5. **Strict Post-Task Process Teardown:**
   Ensure your Python script calls `sys.exit(0)` at completion. After running a background generation task, verify that the process has exited with `ps aux`.

---

## 4. Chatterbox Model Mechanics & Token Budgeting

Chatterbox Multilingual V3 utilizes an **S3 speech tokenizer** with an autoregressive LLaMA-520M language model backbone.

### 4.1 Token Rate (~25 Hz / ~40 ms per token)
Speech tokens correspond to audio frames:
$$\text{Duration (seconds)} \approx \text{Tokens} \times 0.040\,\text{s}$$

### 4.2 Why Default `max_new_tokens=1000` Causes Hallucinations on Short Speech
When given a short input (e.g. 1–3 words), Chatterbox finishes speaking the requested words within 0.5s–1.5s. However, because the model frequently fails to emit an EOS (end-of-sequence) stop token on short prompts, it continues generating until `max_new_tokens` is exhausted, producing:
- Repeating token cascades (`"Ma... Ma... Ma..."`, `"M, M, M, M"`).
- Spurious foreign language tokens (e.g. Japanese graphemes like `"まーす"` or English filler `"uh"`).
- Trailing clicks, breath sounds, and vocal fry.

### 4.3 Proven Token Budget Table
Always pass explicit `max_new_tokens` according to the semantic length of the input:

| Utterance Type | Example Text | Recommended `max_new_tokens` | Max Audio Window |
| :--- | :--- | :---: | :---: |
| **Single Syllable** | `"ba."`, `"pa."`, `"ma."` | **`20 – 25`** | `~0.8s – 1.0s` |
| **Short Reaction (1–2 words)** | `"Complimenti!"`, `"Evviva!"`, `"You did it!"` | **`45`** | `~1.8s` |
| **Medium Reaction (3–4 words)** | `"Quasi! Proviamo ancora!"`, `"Almost! Let's try again!"` | **`65`** | `~2.6s` |
| **Full Sentence Dialogue** | `"Ciao bambini! Oggi esploriamo il bosco insieme."` | **`120 – 160`** | `~5.0s – 6.5s` |

> [!NOTE]
> Setting `max_new_tokens < 15` on syllables cuts off the vowel before articulation finishes. The sweet spot for single syllables is **20–25 tokens**.

---

## 5. Proven Waveform Gating vs Rejected Workarounds

### 5.1 Rejection of the Triple-Utterance Workaround (`ma. ma. ma.`)
An experimental hypothesis was tested: repeating a word three times and automatically extracting the middle segment.
- **Empirical Result:** **FAIL (19.0% segmentation success)**.
- **Why it failed:** Prompting an autoregressive model with repeated identical tokens directly triggers token repetition loops (stuttering 4 to 8 times or merging vowels into one continuous sound).
- **Rule:** Do **NOT** use repeated prompt padding.

### 5.2 Approved Production Workaround: Primary Speech Burst Extraction
Generate the single phrase directly with a bounded token limit, then apply energy-based speech island extraction:
1. Compute RMS energy in 10 ms frames.
2. Find the primary speech burst exceeding `-35 dB` relative to peak frame energy.
3. Apply `25 ms` leading pad (protects onset plosives) and `40 ms` trailing pad (protects vowel decay).
4. Terminate the extraction at the first silence gap exceeding `120 ms`.

```python
def trim_speech_island(
    audio: np.ndarray,
    sr: int,
    noise_db: float = -35.0,
    pad_leading_ms: float = 25.0,
    pad_trailing_ms: float = 40.0,
) -> np.ndarray:
    frame_len = int(0.010 * sr)
    num_frames = len(audio) // frame_len
    if num_frames == 0:
        return audio

    frames = audio[:num_frames * frame_len].reshape(num_frames, frame_len)
    frame_rms = np.sqrt(np.mean(frames**2, axis=1))
    peak_rms = np.max(frame_rms)
    if peak_rms < 1e-4:
        return audio

    threshold = max(0.010, peak_rms * (10 ** (noise_db / 20.0)))
    active = np.where(frame_rms > threshold)[0]
    if len(active) == 0:
        return audio

    island_start = active[0]
    island_end = active[0]
    for idx in active[1:]:
        if idx - island_end > 12:  # >120ms silence gap indicates end of utterance
            break
        island_end = idx

    start_s = max(0.0, (island_start * 0.010) - (pad_leading_ms / 1000.0))
    end_s = min(len(audio) / sr, ((island_end + 1) * 0.010) + (pad_trailing_ms / 1000.0))
    return audio[int(start_s * sr):int(end_s * sr)]
```

---

## 6. Language Conditioning & Whisper Verification Quirks

### 6.1 Language Parameter
- Always pass `lang_code="it"` for Italian and `lang_code="en"` for English to `model.generate()`.
- Chatterbox normalizes whitespace (`" ".join(text.split())`). Do not attempt to control timing by adding extra spaces.
- Preserve punctuation: exclamation marks (`!`) provide necessary prosodic energy for reactions.

### 6.2 Whisper Transcription Language Trap
When using `mlx_whisper` to automate take validation:
- **Default Behavior:** `mlx_whisper.transcribe(file)` defaults to English.
- **The Trap:** On short Italian phrases, Whisper attempts to phonetically force English words (e.g. `"Ben fatto!"` transcribed as `"Bem fat!"`, `"Ce l'hai fatta!"` transcribed as `"Shall I fall?"`).
- **The Fix:** Always explicitly pass `language=locale`:
  ```python
  tr = mlx_whisper.transcribe(audio_path, path_or_hf_repo="mlx-community/whisper-tiny", language="it")
  ```

---

## 7. Canonical Reference Voice Hashes

Always verify anchor references against `assets/audio/characters/canonical/v0.1/manifest.toml`:

| Character | Voice ID | File | SHA-256 (First 16 chars) |
| :--- | :--- | :--- | :--- |
| **Lilli** | `greia.lilli.v1` | `lilli-reference-v1.flac` | `a77a2380106ec64c...` |
| **Leo** | `greia.leo.v1` | `leo-reference-v1.flac` | `4fd8be1a5d9163aa...` |
| **Flash** | `greia.flash.v1` | `flash-reference-v1.flac` | `a6dc67a66b644311...` |
| **Tito** | `greia.tito.v1` | `tito-reference-v1.flac` | `e5d38bdd6dededd1...` |
| **Momo** | `greia.momo.v1` | `momo-reference-v1.flac` | `6aaf803220113856...` |

---

## 8. Standard Agent Generation Template

Incoming agents should use this template pattern for generating character voice assets:

```python
import sys
from pathlib import Path
import numpy as np
import soundfile as sf
import mlx.core as mx
from mlx_audio.tts import load

# 1. Load model once
model = load("mlx-community/chatterbox-multilingual-v3")

# 2. Configure generation
ref_path = "assets/audio/characters/canonical/v0.1/lilli-reference-v1.flac"
text = "Evviva! Che meraviglia!"
locale = "it"
word_count = len(text.split())
max_tokens = 65 if word_count >= 3 else 45

# 3. Generate
res = next(model.generate(
    text=text,
    ref_audio=ref_path,
    lang_code=locale,
    max_new_tokens=max_tokens,
    verbose=False,
))

# 4. Trim primary burst
clean_audio = trim_speech_island(np.array(res.audio), res.sample_rate)

# 5. Save output at 24kHz 16-bit mono WAV
sf.write("output.wav", clean_audio, res.sample_rate)

# 6. Clear Metal memory cache
mx.clear_cache()
```
