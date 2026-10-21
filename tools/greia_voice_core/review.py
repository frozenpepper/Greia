"""Read-only audio screening. Machine findings never grant listening acceptance."""
from array import array
from dataclasses import replace
import math
import os
from pathlib import Path
import sys
import tempfile
import wave

from .audio import AudioPipeline
from .models import VerificationMode
from .verification import asr_eligible, normalize_transcript

from .review_policy import POLICY_VERSION, MAX_TRAILING_SILENCE, MAX_INTERNAL_PAUSE, reassess_result


def probe_cached_asr(verifier) -> tuple[bool, str]:
    """Require already installed code AND cached weights; never download for review."""
    available, detail = verifier.probe()
    if not available:
        return False, detail
    try:
        from huggingface_hub import snapshot_download
        snapshot_download(verifier.model_id, local_files_only=True)
        return True, f"cached {verifier.model_id}"
    except Exception as exc:
        return False, f"ASR weights are not locally ready: {exc}"


def signal_metrics(path: Path) -> tuple[dict, list[str]]:
    """Measure normalized PCM using 20ms RMS windows; thresholds are screening heuristics."""
    with wave.open(str(path), "rb") as handle:
        if (handle.getnchannels(), handle.getsampwidth(), handle.getframerate()) != (1, 2, 22050):
            raise ValueError("review decoder did not return mono PCM16/22050")
        duration = handle.getnframes() / 22050
        if not 0.12 <= duration <= 120:
            raise ValueError(f"speech duration outside 0.12–120 seconds: {duration:.3f}")
        samples = array("h", handle.readframes(handle.getnframes()))
    if sys.byteorder != "little":
        samples.byteswap()
    if not samples:
        raise ValueError("empty decoded signal")
    rms = math.sqrt(sum(float(x) ** 2 for x in samples) / len(samples)) / 32768
    peak = max(abs(x) for x in samples) / 32768
    dbfs = 20 * math.log10(max(rms, 1e-12))
    if dbfs <= -65:
        raise ValueError(f"effectively silent signal: RMS {dbfs:.1f} dBFS")
    frame = 441
    active = [math.sqrt(sum(float(x) ** 2 for x in samples[i:i + frame]) / len(samples[i:i + frame])) / 32768 >= 0.0031623
              for i in range(0, len(samples), frame)]
    indices = [i for i, value in enumerate(active) if value]
    first, last = (indices[0], indices[-1]) if indices else (len(active), -1)
    leading = min(duration, first * .02)
    trailing = min(duration, (len(active) - 1 - last) * .02)
    longest = current = 0
    for value in active[first:last + 1]:
        current = 0 if value else current + 1
        longest = max(longest, current)
    clipped = sum(abs(x) >= 32760 for x in samples) / len(samples)
    flags = []
    for predicate, label in ((dbfs < -40, "LOW_LEVEL"), (clipped >= .001, "POSSIBLE_CLIPPING"),
                             (leading >= .4, "LONG_LEADING_SILENCE"), (trailing >= MAX_TRAILING_SILENCE, "LONG_TRAILING_SILENCE"),
                             (longest * .02 >= MAX_INTERNAL_PAUSE, "LONG_INTERNAL_PAUSE")):
        if predicate:
            flags.append(label)
    return {"duration_seconds": duration, "rms_dbfs": round(dbfs, 2), "peak": round(peak, 5),
            "clipped_fraction": round(clipped, 6), "leading_silence_seconds": round(leading, 3),
            "trailing_silence_seconds": round(trailing, 3), "longest_internal_pause_seconds": round(longest * .02, 3)}, flags


class AudioReviewer:
    """Compose bounded signal analysis and the existing semantic SpeechVerifier."""

    def __init__(self, verifier, *, asr: bool, asr_ready: tuple[bool, str], pipeline=None) -> None:
        self.verifier, self.asr, self.asr_ready = verifier, asr, asr_ready
        self.pipeline = pipeline or AudioPipeline()

    def review(self, request, audio: Path) -> dict:
        with tempfile.TemporaryDirectory(prefix="greia-audio-review-") as temporary:
            decoded = Path(temporary) / "decoded.wav"
            self.pipeline.decode_for_review(audio, decoded)
            metrics, flags = signal_metrics(decoded)
            result = {"metrics": metrics, "flags": flags, "asr": {"status": "DISABLED"}, "status": "WARN" if flags else "PASS"}
            screening_request = replace(request, verification=VerificationMode.REQUIRED)
            if not self.asr:
                return reassess_result(result)
            if not asr_eligible(screening_request):
                result["asr"] = {"status": "NOT_APPLICABLE_POLICY", "detail": "Existing verifier eligibility excludes Dani, short teaching targets/utterances and scripts over 500 characters"}
            elif not self.asr_ready[0]:
                result.update(status="BLOCKED", asr={"status": "UNAVAILABLE", "detail": self.asr_ready[1]})
            else:
                # Guard dependency/model resolution even when the operator's shell
                # allows online Hugging Face access. Restore process environment.
                previous = os.environ.get("HF_HUB_OFFLINE")
                os.environ["HF_HUB_OFFLINE"] = "1"
                try:
                    verification = self.verifier.verify(screening_request, decoded)
                finally:
                    if previous is None:
                        os.environ.pop("HF_HUB_OFFLINE", None)
                    else:
                        os.environ["HF_HUB_OFFLINE"] = previous
                result["asr"] = {"status": verification.disposition.value, **verification.to_dict()}
                if verification.disposition.value != "PASS":
                    result["status"] = "WARN"
                    result["flags"].append("ASR_MISMATCH_OR_ERROR")
                if verification.disposition.value == "WARN" and verification.score is None:
                    result.update(status="BLOCKED")
                    result["asr"]["status"] = "ERROR"
                expected = set(normalize_transcript(request.text).split())
                extra = sorted(set(normalize_transcript(verification.transcript or "").split()) - expected)
                result["asr"]["unexpected_tokens"] = extra
                direction_words = set(normalize_transcript(request.delivery_prompt).split())
                if len({w for w in extra if len(w) >= 5} & direction_words) >= 2:
                    result["flags"].append("POSSIBLE_PROMPT_LEAKAGE")
                    result["status"] = "WARN"
            return reassess_result(result)
