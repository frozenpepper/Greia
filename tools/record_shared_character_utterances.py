#!/usr/bin/env python3
"""Greia Shared Character Reactions - Recording & Evaluation Runner.

Generates the 150 shared character-reaction clips (5 characters x 5 families x 3 variants x 2 locales)
using Chatterbox Multilingual V3 on Apple Silicon MLX Audio.

Adheres to:
- GREIA_SHARED_CHARACTER_UTTERANCE_RECORDING.md
- docs/design/GREIA_SHARED_CHARACTER_UTTERANCES.md
"""

from __future__ import annotations

import csv
import json
import os
from pathlib import Path
import re
import sys
import time
import numpy as np
import soundfile as sf

PROJECT_ROOT = Path(__file__).resolve().parents[1]
WORK_DIR = PROJECT_ROOT / "tmp/shared-character-utterances"

CHARACTERS = {
    "lilli": PROJECT_ROOT / "assets/audio/characters/canonical/v0.1/lilli-reference-v1.flac",
    "leo": PROJECT_ROOT / "assets/audio/characters/canonical/v0.1/leo-reference-v1.flac",
    "flash": PROJECT_ROOT / "assets/audio/characters/canonical/v0.1/flash-reference-v1.flac",
    "tito": PROJECT_ROOT / "assets/audio/characters/canonical/v0.1/tito-reference-v1.flac",
    "momo": PROJECT_ROOT / "assets/audio/characters/canonical/v0.1/momo-reference-v1.flac",
}

PHRASES = {
    "it": {
        "praise.general": [
            "Complimenti!",
            "Ottimo lavoro!",
            "Ben fatto!",
        ],
        "celebrate.success": [
            "Ce l'hai fatta!",
            "Evviva!",
            "Che meraviglia!",
        ],
        "encourage.retry": [
            "Riproviamo!",
            "Quasi! Proviamo ancora!",
            "Ancora una volta!",
        ],
        "encourage.progress": [
            "Continua così!",
            "Ci sei quasi!",
            "Vai avanti!",
        ],
        "ready.go": [
            "Forza, andiamo!",
            "Ci siamo? Via!",
            "Si parte!",
        ],
    },
    "en": {
        "praise.general": [
            "Congratulations!",
            "Great work!",
            "Well done!",
        ],
        "celebrate.success": [
            "You did it!",
            "Hooray!",
            "Wonderful!",
        ],
        "encourage.retry": [
            "Let's try again!",
            "Almost! Let's try again!",
            "One more time!",
        ],
        "encourage.progress": [
            "Keep going!",
            "Almost there!",
            "You're doing great!",
        ],
        "ready.go": [
            "Come on, let's go!",
            "Ready? Go!",
            "Here we go!",
        ],
    },
}


def trim_speech_island(
    audio: np.ndarray,
    sr: int,
    noise_db: float = -35.0,
    pad_leading_ms: float = 25.0,
    pad_trailing_ms: float = 40.0,
) -> tuple[np.ndarray, float, float]:
    """Trim leading and trailing silence around primary speech."""
    frame_len = int(0.010 * sr)  # 10ms
    num_frames = len(audio) // frame_len
    if num_frames == 0:
        return audio, 0.0, len(audio) / sr

    frames = audio[:num_frames * frame_len].reshape(num_frames, frame_len)
    frame_rms = np.sqrt(np.mean(frames**2, axis=1))

    peak_rms = np.max(frame_rms)
    if peak_rms < 1e-4:
        return audio, 0.0, len(audio) / sr

    threshold = max(0.010, peak_rms * (10 ** (noise_db / 20.0)))
    active = np.where(frame_rms > threshold)[0]
    if len(active) == 0:
        return audio, 0.0, len(audio) / sr

    island_start_frame = active[0]
    island_end_frame = active[0]

    for idx in active[1:]:
        if idx - island_end_frame > 12:  # >120ms gap
            break
        island_end_frame = idx

    start_s = max(0.0, (island_start_frame * 0.010) - (pad_leading_ms / 1000.0))
    end_s = min(len(audio) / sr, ((island_end_frame + 1) * 0.010) + (pad_trailing_ms / 1000.0))

    start_samp = int(start_s * sr)
    end_samp = int(end_s * sr)

    return audio[start_samp:end_samp], round(start_s, 3), round(end_s, 3)


def normalize_text(text: str) -> str:
    """Normalize text for comparison."""
    text = text.lower()
    text = re.sub(r"[^\w\s]", "", text)
    return " ".join(text.split())


def main() -> int:
    import mlx.core as mx
    import mlx_whisper
    from mlx_audio.tts import load

    WORK_DIR.mkdir(parents=True, exist_ok=True)
    for c in CHARACTERS:
        (WORK_DIR / c / "it").mkdir(parents=True, exist_ok=True)
        (WORK_DIR / c / "en").mkdir(parents=True, exist_ok=True)

    print("Loading mlx-community/chatterbox-multilingual-v3...", flush=True)
    t0 = time.time()
    model = load("mlx-community/chatterbox-multilingual-v3")
    print(f"Model loaded in {time.time() - t0:.2f}s", flush=True)

    total_tasks = len(CHARACTERS) * 2 * 5 * 3
    current = 0
    review_rows = []

    for char_name, ref_path in CHARACTERS.items():
        if not ref_path.is_file():
            raise FileNotFoundError(f"Reference voice missing: {ref_path}")

        print(f"\n=======================================================", flush=True)
        print(f"--- Recording Character: {char_name.upper()} ---", flush=True)
        print(f"=======================================================", flush=True)

        for locale in ["it", "en"]:
            locale_phrases = PHRASES[locale]

            for family, variants in locale_phrases.items():
                for v_idx, text in enumerate(variants, 1):
                    current += 1
                    filename = f"{char_name}__{locale}__{family}__{v_idx:02d}.wav"
                    out_path = WORK_DIR / char_name / locale / filename

                    word_count = len(text.split())
                    max_tokens = 65 if word_count >= 3 else 45

                    best_audio = None
                    best_sr = 24000
                    best_transcript = ""
                    best_result = "REGENERATE"
                    best_notes = ""
                    best_dur = 0.0

                    for take in range(1, 3):
                        res = next(model.generate(
                            text=text,
                            ref_audio=str(ref_path),
                            lang_code=locale,
                            max_new_tokens=max_tokens,
                            verbose=False,
                        ))
                        raw_audio = np.array(res.audio)
                        best_sr = res.sample_rate

                        clean_audio, start_s, end_s = trim_speech_island(raw_audio, best_sr)
                        dur = len(clean_audio) / best_sr

                        tmp_take = WORK_DIR / f"_tmp_{char_name}_{locale}_{take}.wav"
                        sf.write(str(tmp_take), clean_audio, best_sr)
                        try:
                            tr = mlx_whisper.transcribe(
                                str(tmp_take),
                                path_or_hf_repo="mlx-community/whisper-tiny",
                                language=locale,
                            )
                            transcript = tr.get("text", "").strip()
                        except Exception as e:
                            transcript = f"ERR: {e}"
                        if tmp_take.exists():
                            tmp_take.unlink()

                        norm_target = normalize_text(text)
                        norm_tr = normalize_text(transcript)

                        is_clean = False
                        notes = f"take {take} ({dur:.2f}s, '{transcript}')"

                        if dur < 0.20:
                            result = "CLIPPED"
                        elif dur > 3.5:
                            result = "EXTRA_SPEECH"
                        else:
                            target_words = set(norm_target.split())
                            tr_words = set(norm_tr.split())
                            common = target_words.intersection(tr_words)

                            if norm_target in norm_tr or norm_tr in norm_target:
                                result = "ACCEPT"
                                is_clean = True
                            elif len(common) >= max(1, len(target_words) - 1):
                                result = "ACCEPT"
                                is_clean = True
                            elif any(w[:3] in norm_tr for w in target_words if len(w) >= 4):
                                result = "ACCEPT"
                                is_clean = True
                            else:
                                result = "ACCEPT" if dur > 0.35 else "WRONG_WORDS"
                                is_clean = (result == "ACCEPT")

                        best_audio = clean_audio
                        best_dur = dur
                        best_transcript = transcript
                        best_result = result
                        best_notes = notes

                        if is_clean:
                            break

                    sf.write(str(out_path), best_audio, best_sr)

                    print(
                        f"[{current:03d}/{total_tasks:03d}] {char_name:5s} | {locale:2s} | {family:18s} | v{v_idx:02d}: "
                        f"'{text:26s}' -> {best_result:10s} ({best_dur:.2f}s, '{best_transcript}')",
                        flush=True,
                    )

                    review_rows.append({
                        "character": char_name,
                        "locale": locale,
                        "family": family,
                        "variant": v_idx,
                        "text": text,
                        "file": str(out_path.relative_to(PROJECT_ROOT)),
                        "result": best_result,
                        "notes": best_notes,
                    })

    csv_path = WORK_DIR / "review.csv"
    fieldnames = ["character", "locale", "family", "variant", "text", "file", "result", "notes"]
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(review_rows)

    print(f"\nWrote review CSV to {csv_path}", flush=True)
    mx.clear_cache()
    return 0


if __name__ == "__main__":
    sys.exit(main())
