#!/usr/bin/env python3
"""Generate Tito character voice clips for Baia delle Orche using Chatterbox Multilingual V3.

Clones against canonical voice reference:
assets/audio/characters/canonical/v0.1/tito-reference-v1.flac
Outputs 22050Hz LEI16 mono WAV files to activities/baia_delle_orche/assets/audio/
"""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
import subprocess
import sys
import tempfile
import time

try:
    import numpy as np
except ImportError:
    np = None

PROJECT_ROOT = Path(__file__).resolve().parents[1]
TITO_REF = PROJECT_ROOT / "assets" / "audio" / "characters" / "canonical" / "v0.1" / "tito-reference-v1.flac"
OUTPUT_DIR = PROJECT_ROOT / "activities" / "baia_delle_orche" / "assets" / "audio"

FACTS = {
    "it": [
        (
            "fact_breach",
            "I grandi salti fuori dall'acqua si chiamano breaching. Quando l'orca ricade fa un gran rumore, che può aiutare a mandare un segnale alle altre orche anche da lontano!",
        ),
        (
            "fact_swallow",
            "Le orche non masticano il cibo: usano i denti per afferrare i pesciolini e poi li inghiottono tutti interi!",
        ),
        (
            "fact_sleep",
            "Le orche dormono con un occhio aperto e metà cervello sveglio per ricordarsi di salire a respirare l'aria!",
        ),
        (
            "fact_song",
            "Ogni famiglia di orche ha fischi speciali e una propria canzone unica, diversa da tutte le altre!",
        ),
        (
            "fact_pod",
            "I cuccioli di orca restano sempre vicini alla loro mamma e al loro branco per tutta la vita!",
        ),
        (
            "fact_fin",
            "La grande pinna sulla schiena dell'orca si chiama pinna dorsale e aiuta a nuotare dritti come frecce nell'acqua!",
        ),
    ],
    "en": [
        (
            "fact_breach",
            "Big jumps out of the water are called breaching. When the orca splashes down it makes a huge sound, which helps send a signal to other orcas far away!",
        ),
        (
            "fact_swallow",
            "Orcas don't chew their food: they use their teeth to catch fish and then swallow them whole!",
        ),
        (
            "fact_sleep",
            "Orcas sleep with one eye open and half their brain awake so they remember to surface and breathe air!",
        ),
        (
            "fact_song",
            "Every orca family has special whistles and its own unique song, different from all the others!",
        ),
        (
            "fact_pod",
            "Orca calves stay close to their mother and their pod for their entire lives!",
        ),
        (
            "fact_fin",
            "The big fin on an orca's back is called the dorsal fin, and it helps them swim straight like arrows in the water!",
        ),
    ],
}


def _write_wav_stub(dest_wav: Path) -> None:
    """Create a minimal valid 22050Hz LEI16 mono WAV stub."""
    import wave
    dest_wav.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(dest_wav), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(22050)
        w.writeframes(b"\x00\x00" * 4410)


def trim_speech_ends(
    audio: np.ndarray,
    sr: int,
    noise_db: float = -38.0,
    pad_leading_ms: float = 40.0,
    pad_trailing_ms: float = 180.0,
) -> np.ndarray:
    """Trim silence only from the beginning and end of the audio, preserving all internal pauses between sentences."""
    frame_len = int(0.010 * sr)  # 10ms
    num_frames = len(audio) // frame_len
    if num_frames == 0:
        return audio

    frames = audio[: num_frames * frame_len].reshape(num_frames, frame_len)
    frame_rms = np.sqrt(np.mean(frames**2, axis=1))
    peak_rms = np.max(frame_rms)
    if peak_rms < 1e-4:
        return audio

    threshold = max(0.005, peak_rms * (10 ** (noise_db / 20.0)))
    active = np.where(frame_rms > threshold)[0]
    if len(active) == 0:
        return audio

    first_frame = active[0]
    last_frame = active[-1]

    start_s = max(0.0, (first_frame * 0.010) - (pad_leading_ms / 1000.0))
    end_s = min(len(audio) / sr, ((last_frame + 1) * 0.010) + (pad_trailing_ms / 1000.0))

    start_samp = int(start_s * sr)
    end_samp = int(end_s * sr)
    return audio[start_samp:end_samp]


def generate_with_chatterbox(dest_dir: Path) -> bool:
    try:
        import soundfile as sf
        from mlx_audio.tts import load
    except ImportError as err:
        print(f"MLX Chatterbox not importable: {err}", file=sys.stderr)
        return False

    if not TITO_REF.is_file():
        print(f"Tito reference voice missing: {TITO_REF}", file=sys.stderr)
        return False

    print("Loading mlx-community/chatterbox-multilingual-v3...", flush=True)
    t0 = time.time()
    try:
        model = load("mlx-community/chatterbox-multilingual-v3")
    except Exception as err:
        print(f"Failed to load model: {err}", file=sys.stderr)
        return False
    print(f"Model loaded in {time.time() - t0:.2f}s", flush=True)

    dest_dir.mkdir(parents=True, exist_ok=True)

    for locale, items in FACTS.items():
        loc_dir = dest_dir / locale
        loc_dir.mkdir(parents=True, exist_ok=True)
        for key, text in items:
            dest_wav = loc_dir / f"tito_{key}.wav"
            print(f"Generating [{locale}] {key}...", flush=True)

            word_count = len(text.split())
            # Headroom: 25 tokens/s + buffer
            max_tokens = max(500, word_count * 28)

            try:
                res = next(model.generate(
                    text=text,
                    ref_audio=str(TITO_REF),
                    lang_code=locale,
                    max_new_tokens=max_tokens,
                    verbose=False,
                ))
                raw_audio = np.array(res.audio)
                sr = res.sample_rate

                clean_audio = trim_speech_ends(raw_audio, sr)

                with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_f:
                    tmp_wav = Path(tmp_f.name)
                sf.write(str(tmp_wav), clean_audio, sr)

                converted = False
                for cmd in [
                    ["afconvert", "-f", "WAVE", "-d", "LEI16@22050", "-c", "1", str(tmp_wav), str(dest_wav)],
                    ["ffmpeg", "-y", "-i", str(tmp_wav), "-ar", "22050", "-ac", "1", "-c:a", "pcm_s16le", str(dest_wav)],
                ]:
                    try:
                        subprocess.run(cmd, check=True, capture_output=True)
                        converted = True
                        break
                    except Exception:
                        continue

                if not converted:
                    sf.write(str(dest_wav), clean_audio, sr)

                if tmp_wav.exists():
                    tmp_wav.unlink()

            except Exception as err:
                print(f"Error generating {key}: {err}, creating stub", file=sys.stderr)
                _write_wav_stub(dest_wav)

    return True


def generate_stubs(dest_dir: Path) -> None:
    for locale, items in FACTS.items():
        loc_dir = dest_dir / locale
        loc_dir.mkdir(parents=True, exist_ok=True)
        for key, _ in items:
            dest_wav = loc_dir / f"tito_{key}.wav"
            if not dest_wav.exists():
                _write_wav_stub(dest_wav)


def create_manifest(dest_dir: Path) -> None:
    manifest_path = dest_dir / "audio_manifest.sha256"
    lines = []
    for p in sorted(dest_dir.rglob("*.wav")):
        rel = p.relative_to(dest_dir)
        sha = hashlib.sha256(p.read_bytes()).hexdigest()
        lines.append(f"{sha}  {rel}")
    manifest_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote manifest: {manifest_path} ({len(lines)} files)")


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate Baia delle Orche Tito voice clips.")
    parser.add_argument("--output", type=Path, default=OUTPUT_DIR, help="Destination directory")
    parser.add_argument("--stubs-only", action="store_true", help="Generate silent stubs only")
    args = parser.parse_args()

    if args.stubs_only:
        generate_stubs(args.output)
    else:
        success = generate_with_chatterbox(args.output)
        if not success:
            print("Chatterbox generation failed; writing valid stubs.", file=sys.stderr)
            generate_stubs(args.output)

    create_manifest(args.output)
    print("Done!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
