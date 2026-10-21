from __future__ import annotations

from dataclasses import dataclass
import hashlib
import shutil
import subprocess
from pathlib import Path
import wave


@dataclass(frozen=True)
class AudioInspection:
    duration_seconds: float
    sample_rate_hz: int
    channels: int
    bytes: int
    sha256: str


class AudioPipelineError(RuntimeError):
    pass


class AudioPipeline:
    """Owns bounded authoring-time audio packaging and basic signal checks.

    OGG output defaults to Vorbis quality 5. A caller may select another bounded
    FFmpeg quality for a corpus-specific footprint constraint; that changes only
    packaging, never the frozen synthesis request or its human-review state.
    """

    def __init__(self, target_sample_rate_hz: int = 22050, ogg_quality: int = 5) -> None:
        if not 0 <= ogg_quality <= 10:
            raise ValueError("OGG quality must be between 0 and 10")
        self.target_sample_rate_hz = target_sample_rate_hz
        self.ogg_quality = ogg_quality

    @staticmethod
    def ffmpeg_available() -> bool:
        return shutil.which("ffmpeg") is not None

    def package(self, source_wav: Path, output: Path) -> Path:
        output.parent.mkdir(parents=True, exist_ok=True)
        suffix = output.suffix.lower()
        if suffix not in {".wav", ".ogg"}:
            raise AudioPipelineError("output extension must be .wav or .ogg")
        if not self.ffmpeg_available():
            raise AudioPipelineError("ffmpeg is required for Greia voice packaging")

        if suffix == ".wav":
            codec = ["-c:a", "pcm_s16le"]
        else:
            codec = ["-c:a", "libvorbis", "-q:a", str(self.ogg_quality)]

        cmd = [
            "ffmpeg", "-hide_banner", "-loglevel", "error", "-nostdin", "-y",
            "-i", str(source_wav),
            "-ar", str(self.target_sample_rate_hz),
            "-ac", "1",
            *codec,
            str(output),
        ]
        try:
            subprocess.run(cmd, check=True, capture_output=True, text=True)
        except subprocess.CalledProcessError as exc:
            raise AudioPipelineError(exc.stderr.strip() or "ffmpeg packaging failed") from exc
        return output

    def inspect_wav(self, wav_path: Path) -> AudioInspection:
        try:
            with wave.open(str(wav_path), "rb") as handle:
                frames = handle.getnframes()
                sample_rate = handle.getframerate()
                channels = handle.getnchannels()
        except (wave.Error, EOFError) as exc:
            raise AudioPipelineError(f"invalid WAV: {wav_path}") from exc
        duration = frames / sample_rate if sample_rate else 0.0
        size = wav_path.stat().st_size
        return AudioInspection(
            duration_seconds=duration,
            sample_rate_hz=sample_rate,
            channels=channels,
            bytes=size,
            sha256=hashlib.sha256(wav_path.read_bytes()).hexdigest(),
        )

    def decode_for_review(self, source: Path, output: Path) -> None:
        """Decode a bounded temporary signal for analysis without changing source audio.

        Cap decoding at 121 seconds so malformed/very long compressed inputs cannot
        fill the review workspace; the review policy rejects anything above 120s.
        """
        try:
            subprocess.run([
                "ffmpeg", "-hide_banner", "-loglevel", "error", "-nostdin", "-y",
                "-i", str(source), "-t", "121", "-ar", "22050", "-ac", "1",
                "-c:a", "pcm_s16le", str(output),
            ], check=True, capture_output=True, text=True, timeout=120)
        except (subprocess.SubprocessError, OSError) as exc:
            raise AudioPipelineError(f"review decode failed: {getattr(exc, 'stderr', '') or exc}") from exc

    def validate_review_wav(self, wav_path: Path) -> AudioInspection:
        inspection = self.inspect_wav(wav_path)
        if inspection.bytes < 1000:
            raise AudioPipelineError("generated WAV is implausibly small")
        if inspection.duration_seconds < 0.12:
            raise AudioPipelineError("generated speech is implausibly short")
        if inspection.duration_seconds > 120.0:
            raise AudioPipelineError("generated speech exceeds the bounded authoring limit")
        return inspection
