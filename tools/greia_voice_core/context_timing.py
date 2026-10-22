"""Validate complete recognizer word coverage before a fixed PCM boundary slice."""
from dataclasses import dataclass
import math
from numbers import Real
from .verification import normalize_transcript


@dataclass(frozen=True)
class TimedTargetSlice:
    """All words after a physical prefix, retaining any boundary conflict."""

    transcript: str
    words: tuple[dict, ...]
    straddling: tuple[dict, ...]
    full_transcript: str

    @classmethod
    def from_result(cls, result: dict, *, prefix_seconds: float, duration_seconds: float):
        """Reject incomplete/malformed timing instead of silently dropping words.

        Whisper's timestamp grid may end up to one 20 ms frame beyond decoded PCM.
        This permits quantization only, never a shifted candidate boundary.
        """
        if (not isinstance(prefix_seconds, Real) or isinstance(prefix_seconds, bool)
                or not isinstance(duration_seconds, Real) or isinstance(duration_seconds, bool)
                or not math.isfinite(prefix_seconds) or not math.isfinite(duration_seconds)
                or not 0 < prefix_seconds < duration_seconds <= 120):
            raise ValueError('context boundary outside PCM')
        if not isinstance(result, dict) or not isinstance(result.get('text'), str):
            raise ValueError('malformed contextual transcript')
        segments = result.get('segments')
        if not isinstance(segments, list) or len(segments) > 1000:
            raise ValueError('missing or unbounded contextual segments')
        words = []
        for segment in segments:
            if not isinstance(segment, dict) or not isinstance(segment.get('words'), list):
                raise ValueError('context segment lacks word timestamps')
            words.extend(segment['words'])
            if len(words) > 2000:
                raise ValueError('unbounded contextual word timestamps')
        # mlx-whisper emits NumPy real scalars. Preserve the same numeric
        # bounds while accepting real-valued timestamp representations.
        previous = 0.
        for word in words:
            if not isinstance(word, dict) or not isinstance(word.get('word'), str):
                raise ValueError('malformed contextual word')
            start, end = word.get('start'), word.get('end')
            if (not isinstance(start, Real) or isinstance(start, bool)
                    or not isinstance(end, Real) or isinstance(end, bool)
                    or not math.isfinite(start) or not math.isfinite(end)
                    or not 0 <= start < end <= duration_seconds + .02 or start < previous):
                raise ValueError('invalid contextual word timestamps')
            previous = end
        joined = ''.join(word['word'] for word in words)
        if normalize_transcript(joined) != normalize_transcript(result['text']):
            raise ValueError('context text is not fully covered by word timestamps')
        kept = tuple(word for word in words if word['start'] >= prefix_seconds)
        crossing = tuple(word for word in words if word['start'] < prefix_seconds < word['end'])
        return cls(''.join(word['word'] for word in kept).strip(), kept, crossing, result['text'])
