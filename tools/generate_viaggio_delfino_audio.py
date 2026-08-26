#!/usr/bin/env python3
"""Generate Tito voice clips for Il Viaggio del Delfino.

Clones the canonical Tito voice (greia.tito.v1) with Chatterbox Multilingual V3
on Apple Silicon (mlx-community conversion), following the mandatory batch
rules in skills/greia-activity-authoring/VOICE_GENERATION.md section 12.2:

- model loaded exactly once per run;
- mx.clear_cache() + gc.collect() immediately after each clip;
- idempotent: existing non-empty outputs are skipped;
- one worker, never concurrent inference;
- failures are loud (no silent stubs).

Masters (WAV) are written to the review directory outside the checkout; the
packaged artifacts are mono OGG files under the Activity's assets/audio tree.
Clip wording must stay aligned with locales/it.json and locales/en.json.
"""

from __future__ import annotations

import argparse
from pathlib import Path
import subprocess
import sys
import tempfile
import time

PROJECT_ROOT = Path(__file__).resolve().parents[1]
TITO_REF = (
    PROJECT_ROOT / "assets" / "audio" / "characters" / "canonical" / "v0.1" / "tito-reference-v1.flac"
)
PACKAGE = PROJECT_ROOT / "activities" / "viaggio_delfino"

#: Exact reviewed locale wording; must stay aligned with locales/<lang>.json.
CLIPS: dict[str, list[tuple[str, str]]] = {
    "it": [
        (
            "presenter-welcome",
            "Ciao! Io sono Tito! Muovi il mouse o usa le frecce per nuotare, e premi la barra per saltare fuori dall'acqua! Raccogli tutte le perle!",
        ),
        (
            "curiosity-breaching",
            "I delfini saltano fuori dall'acqua, finanche a quattro metri! Lo fanno per giocare e per farsi vedere dagli amici lontani.",
        ),
        (
            "curiosity-echolocation",
            "Il delfino emette piccoli click: ascoltando l'eco trova i pesci perfino dove non si vede!",
        ),
        (
            "curiosity-blowhole",
            "Il delfino non è un pesce: è un mammifero! Respira l'aria dal foro sulla testa, il sfiatatoio.",
        ),
        (
            "curiosity-pods",
            "I delfini vivono in famiglie chiamate branchi: insieme cacciano i pesci e si proteggono.",
        ),
        (
            "curiosity-teeth",
            "Il delfino ha tanti dentini, ma non mastica mai: afferra il pesce e lo ingoia tutto intero!",
        ),
        (
            "curiosity-whistle",
            "Ogni delfino ha un fischietto speciale, quasi un nome: così gli amici lo riconoscono!",
        ),
    ],
    "en": [
        (
            "presenter-welcome",
            "Hi! I'm Tito! Move the mouse or use the arrow keys to swim, and press the space bar to leap out of the water! Collect all the pearls!",
        ),
        (
            "curiosity-breaching",
            "Dolphins leap out of the water, up to four metres high! They do it to play and to show faraway friends where they are.",
        ),
        (
            "curiosity-echolocation",
            "The dolphin makes little clicks: listening to the echoes, it finds fish even where it cannot see!",
        ),
        (
            "curiosity-blowhole",
            "A dolphin is not a fish: it is a mammal! It breathes air through the hole on top of its head, the blowhole.",
        ),
        (
            "curiosity-pods",
            "Dolphins live in families called pods: together they herd fish and keep each other safe.",
        ),
        (
            "curiosity-teeth",
            "A dolphin has many tiny teeth, but it never chews: it grabs the fish and swallows it whole!",
        ),
        (
            "curiosity-whistle",
            "Every dolphin has its own special whistle, almost like a name: that is how friends recognise it!",
        ),
    ],
}


def trim_speech_ends(audio, sr: int, noise_db: float = -38.0,
                     pad_leading_ms: float = 60.0, pad_trailing_ms: float = 200.0):
    """Trim leading/trailing silence only, preserving internal pauses."""
    import numpy as np

    frame_len = int(0.010 * sr)
    num_frames = len(audio) // frame_len
    if num_frames == 0:
        return audio
    frames = audio[: num_frames * frame_len].reshape(num_frames, frame_len)
    frame_rms = np.sqrt(np.mean(frames**2, axis=1))
    peak_rms = float(np.max(frame_rms))
    if peak_rms < 1e-4:
        return audio
    threshold = max(0.005, peak_rms * (10 ** (noise_db / 20.0)))
    active = np.where(frame_rms > threshold)[0]
    if len(active) == 0:
        return audio
    start_s = max(0.0, (active[0] * 0.010) - (pad_leading_ms / 1000.0))
    end_s = min(len(audio) / sr, ((active[-1] + 1) * 0.010) + (pad_trailing_ms / 1000.0))
    return audio[int(start_s * sr):int(end_s * sr)]


def to_packaged_ogg(master_wav: Path, dest_ogg: Path) -> bool:
    dest_ogg.parent.mkdir(parents=True, exist_ok=True)
    result = subprocess.run(
        [
            "ffmpeg", "-y", "-i", str(master_wav),
            "-ar", "22050", "-ac", "1", "-c:a", "libvorbis", "-q:a", "4",
            str(dest_ogg),
        ],
        capture_output=True,
    )
    return result.returncode == 0 and dest_ogg.is_file() and dest_ogg.stat().st_size > 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--review-dir",
        type=Path,
        required=True,
        help="Directory for WAV masters (keep outside the checkout).",
    )
    args = parser.parse_args()
    review_dir = args.review_dir.resolve()
    review_dir.mkdir(parents=True, exist_ok=True)

    if not TITO_REF.is_file():
        print(f"Tito reference missing: {TITO_REF}", file=sys.stderr)
        return 2

    try:
        import gc

        import mlx.core as mx
        import numpy as np
        import soundfile as sf
        from mlx_audio.tts import load
    except ImportError as err:
        print(f"Voice production environment not importable: {err}", file=sys.stderr)
        return 2

    print("Loading mlx-community/chatterbox-multilingual-v3 (once)...", flush=True)
    t0 = time.time()
    model = load("mlx-community/chatterbox-multilingual-v3")
    print(f"Model loaded in {time.time() - t0:.1f}s", flush=True)

    generated = 0
    skipped = 0
    failures: list[str] = []

    for locale, items in CLIPS.items():
        for cue, text in items:
            dest_ogg = PACKAGE / "assets" / "audio" / locale / f"{cue}.ogg"
            if dest_ogg.is_file() and dest_ogg.stat().st_size > 0:
                skipped += 1
                print(f"skip existing [{locale}] {cue}", flush=True)
                continue

            word_count = len(text.split())
            max_tokens = max(500, word_count * 28)
            print(f"Generating [{locale}] {cue}...", flush=True)
            try:
                result = next(
                    model.generate(
                        text=text,
                        ref_audio=str(TITO_REF),
                        lang_code=locale,
                        max_new_tokens=max_tokens,
                        verbose=False,
                    )
                )
                audio = trim_speech_ends(np.array(result.audio), result.sample_rate)
                master = review_dir / f"tito_{locale}_{cue}.wav"
                sf.write(str(master), audio, result.sample_rate)
                if not to_packaged_ogg(master, dest_ogg):
                    raise RuntimeError("ffmpeg OGG packaging failed")
                duration = len(audio) / result.sample_rate
                print(
                    f"  ok [{locale}] {cue}: {duration:.2f}s, "
                    f"{dest_ogg.stat().st_size} bytes",
                    flush=True,
                )
                generated += 1
            except Exception as err:  # loud failure: no silent stubs
                failures.append(f"{locale}/{cue}: {err}")
                print(f"  FAILED [{locale}] {cue}: {err}", file=sys.stderr, flush=True)
            finally:
                # Mandatory per-clip Metal memory release (VOICE_GENERATION 12.2).
                mx.clear_cache()
                gc.collect()

    print(f"done: generated={generated} skipped={skipped} failures={len(failures)}", flush=True)
    for failure in failures:
        print(f"FAILURE {failure}", file=sys.stderr, flush=True)
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
