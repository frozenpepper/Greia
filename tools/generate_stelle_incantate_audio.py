#!/usr/bin/env python3
"""Generate Leo curiosity-fact voice clips for Stelle Incantate.

Clones the canonical Leo voice (greia.leo.v1) with Chatterbox Multilingual V3
on Apple Silicon (mlx-community conversion), following the mandatory batch
rules in skills/greia-activity-authoring/VOICE_GENERATION.md section 12.2:

- model loaded exactly once per run;
- mx.clear_cache() + gc.collect() immediately after each clip;
- idempotent: existing non-empty outputs are skipped;
- one worker, never concurrent inference;
- failures are loud (no silent stubs).

Masters (WAV) are written to the review directory outside the checkout; the
packaged artifacts are mono OGG files under the Activity's assets/audio tree.
"""

from __future__ import annotations

import argparse
from pathlib import Path
import subprocess
import sys
import tempfile
import time

PROJECT_ROOT = Path(__file__).resolve().parents[1]
LEO_REF = (
    PROJECT_ROOT / "assets" / "audio" / "characters" / "canonical" / "v0.1" / "leo-reference-v1.flac"
)
PACKAGE = PROJECT_ROOT / "activities" / "stelle_incantate"

#: Exact reviewed locale wording; must stay aligned with locales/<lang>.json.
FACTS: dict[str, list[tuple[str, str]]] = {
    "it": [
        (
            "curiosity-triangolo",
            "Nel cielo ci sono 88 costellazioni ufficiali, decise dagli astronomi di tutto il mondo!",
        ),
        (
            "curiosity-cassiopea",
            "Cassiopea era una regina delle storie antiche: la sua W di stelle brilla ancora ogni notte.",
        ),
        (
            "curiosity-cigno",
            "Il Cigno vola nel cielo estivo con le sue stelle a forma di grande croce.",
        ),
        (
            "curiosity-carro",
            "Le due stelle del bordo del Grande Carro indicano la strada verso la Stella Polare!",
        ),
        (
            "curiosity-leone",
            "Il Leone è una costellazione antichissima: la guardiamo da migliaia di anni.",
        ),
        (
            "curiosity-orione",
            "Le stelle di una costellazione sembrano vicine, ma in realtà molte sono lontanissime tra loro!",
        ),
    ],
    "en": [
        (
            "curiosity-triangolo",
            "There are 88 official constellations, chosen by astronomers all over the world!",
        ),
        (
            "curiosity-cassiopea",
            "Cassiopeia was a queen from ancient stories: her W of stars still shines every night.",
        ),
        (
            "curiosity-cigno",
            "The Swan flies across the summer sky with its stars shaped like a big cross.",
        ),
        (
            "curiosity-carro",
            "The two stars on the edge of the Big Dipper point the way to the North Star!",
        ),
        (
            "curiosity-leone",
            "The Lion is a very ancient constellation: people have watched it for thousands of years.",
        ),
        (
            "curiosity-orione",
            "The stars of a constellation look close together, but many are really far, far apart!",
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

    if not LEO_REF.is_file():
        print(f"Leo reference missing: {LEO_REF}", file=sys.stderr)
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

    for locale, items in FACTS.items():
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
                        ref_audio=str(LEO_REF),
                        lang_code=locale,
                        max_new_tokens=max_tokens,
                        verbose=False,
                    )
                )
                audio = trim_speech_ends(np.array(result.audio), result.sample_rate)
                master = review_dir / f"leo_{locale}_{cue}.wav"
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

    print(
        f"Done. generated={generated} skipped={skipped} failures={len(failures)}",
        flush=True,
    )
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
