"""Remove only the residual, already-proven carrier gap from delivery PCM."""
import hashlib
import math
from pathlib import Path
import wave


def prepare_delivery(source: Path, destination: Path, extraction: dict) -> dict:
    """Retain 100 ms of the measured quiet run; never search inside target speech.

    Extractor v6 keeps its original midpoint cut and evidence. This optional
    delivery step advances only within that same proven silence interval.
    """
    boundary = extraction["boundary"]
    rate = extraction["sample_rate"]
    end = boundary["verified_silence_end_seconds"]
    start = boundary["verified_silence_start_seconds"]
    cut = boundary["cut_sample"]
    if not (math.isfinite(start) and math.isfinite(end) and start <= cut/rate <= end):
        raise ValueError("invalid verified carrier gap metadata")
    padding = .1
    offset = max(0, round((end-padding)*rate)-cut)
    with wave.open(str(source),'rb') as wav:
        if wav.getframerate() != rate or not 0 <= offset < wav.getnframes():
            raise ValueError("delivery offset is outside the verified extraction")
        params=wav.getparams()
        wav.setpos(offset)
        frames=wav.readframes(wav.getnframes()-offset)
    with wave.open(str(destination),'wb') as wav:
        wav.setparams(params);wav.writeframes(frames)
    return {"policy":"verified-carrier-gap-delivery-v1", "removed_frames":offset,
            "removed_seconds":offset/rate,"retained_verified_quiet_seconds":padding,
            "raw_delivery_start_sample":cut+offset,"path":str(destination),
            "sha256":hashlib.sha256(destination.read_bytes()).hexdigest()}
