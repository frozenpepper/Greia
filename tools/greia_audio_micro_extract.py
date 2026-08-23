#!/usr/bin/env python3
"""Greia Micro-Utterance Audio Extractor.

Extracts a specific speech segment (e.g. the middle rendition from a triple repetition)
using FFmpeg silencedetect and atrim filters without external Python DSP dependencies.

Adheres to:
- GREIA_CHATTERBOX_MICRO_UTTERANCE_TRIPLE_TEST.md
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
from typing import Any


def check_ffmpeg_available() -> tuple[str, str]:
    """Verify that ffmpeg and ffprobe are installed and available."""
    ffmpeg = shutil.which("ffmpeg")
    ffprobe = shutil.which("ffprobe")
    if not ffmpeg or not ffprobe:
        raise RuntimeError(
            f"Missing audio prerequisite: ffmpeg={ffmpeg}, ffprobe={ffprobe}. "
            "Please ensure both ffmpeg and ffprobe are installed and in PATH."
        )
    return ffmpeg, ffprobe


def probe_audio(input_path: Path, ffprobe_bin: str = "ffprobe") -> dict[str, Any]:
    """Probe audio file for format and stream properties using ffprobe."""
    cmd = [
        ffprobe_bin,
        "-v",
        "error",
        "-show_entries",
        "format=duration,size,bit_rate:stream=codec_name,sample_rate,channels,sample_fmt",
        "-of",
        "json",
        str(input_path),
    ]
    res = subprocess.run(cmd, capture_output=True, text=True, check=True)
    data = json.loads(res.stdout)

    stream = data.get("streams", [{}])[0] if data.get("streams") else {}
    fmt = data.get("format", {})

    duration = float(fmt.get("duration") or stream.get("duration") or 0.0)
    sample_rate = int(stream.get("sample_rate") or 0)
    channels = int(stream.get("channels") or 1)
    codec = stream.get("codec_name") or "unknown"
    sample_fmt = stream.get("sample_fmt") or "unknown"

    return {
        "duration_seconds": round(duration, 6),
        "sample_rate_hz": sample_rate,
        "channels": channels,
        "codec": codec,
        "sample_fmt": sample_fmt,
        "size_bytes": int(fmt.get("size") or input_path.stat().st_size),
    }


def detect_silence(
    input_path: Path,
    noise_db: float = -40.0,
    min_silence_s: float = 0.100,
    ffmpeg_bin: str = "ffmpeg",
) -> tuple[list[tuple[float, float]], str]:
    """Run FFmpeg silencedetect and return list of (silence_start, silence_end) intervals."""
    filter_str = f"silencedetect=noise={noise_db}dB:d={min_silence_s:.4f}"
    cmd = [
        ffmpeg_bin,
        "-hide_banner",
        "-nostats",
        "-i",
        str(input_path),
        "-af",
        filter_str,
        "-f",
        "null",
        "-",
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)
    log = res.stderr

    # Parse silencedetect events from stderr
    # [silencedetect @ 0x...] silence_start: 0.456
    # [silencedetect @ 0x...] silence_end: 0.891 | silence_duration: 0.435
    silence_intervals: list[tuple[float, float]] = []
    current_start: float | None = None

    for line in log.splitlines():
        if "silence_start:" in line:
            m = re.search(r"silence_start:\s*([0-9.]+)", line)
            if m:
                current_start = float(m.group(1))
        elif "silence_end:" in line:
            m = re.search(r"silence_end:\s*([0-9.]+)", line)
            if m and current_start is not None:
                end = float(m.group(1))
                silence_intervals.append((current_start, end))
                current_start = None

    return silence_intervals, log


def derive_speech_segments(
    total_duration: float,
    silence_intervals: list[tuple[float, float]],
    min_speech_duration_s: float = 0.030,
) -> list[tuple[float, float]]:
    """Derive non-silent speech segments from silence intervals and total duration."""
    if not silence_intervals:
        if total_duration > min_speech_duration_s:
            return [(0.0, total_duration)]
        return []

    speech_segments: list[tuple[float, float]] = []
    cursor = 0.0

    for s_start, s_end in silence_intervals:
        if s_start > cursor + min_speech_duration_s:
            speech_segments.append((round(cursor, 6), round(s_start, 6)))
        cursor = max(cursor, s_end)

    if cursor + min_speech_duration_s < total_duration:
        speech_segments.append((round(cursor, 6), round(total_duration, 6)))

    return speech_segments


def extract_segment(
    input_path: Path,
    output_path: Path,
    start_s: float,
    end_s: float,
    ffmpeg_bin: str = "ffmpeg",
) -> None:
    """Extract segment with atrim and write pcm_s16le WAV."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    atrim_filter = f"atrim=start={start_s:.6f}:end={end_s:.6f},asetpts=PTS-STARTPTS"
    cmd = [
        ffmpeg_bin,
        "-y",
        "-hide_banner",
        "-nostats",
        "-i",
        str(input_path),
        "-af",
        atrim_filter,
        "-c:a",
        "pcm_s16le",
        str(output_path),
    ]
    subprocess.run(cmd, capture_output=True, text=True, check=True)


def analyze_audio_astats(input_path: Path, ffmpeg_bin: str = "ffmpeg") -> tuple[dict[str, Any], str]:
    """Run FFmpeg astats filter and extract signal metrics."""
    cmd = [
        ffmpeg_bin,
        "-hide_banner",
        "-nostats",
        "-i",
        str(input_path),
        "-af",
        "astats=metadata=0:reset=0",
        "-f",
        "null",
        "-",
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)
    log = res.stderr

    metrics: dict[str, Any] = {}
    for line in log.splitlines():
        line = line.strip()
        if "Peak level dB:" in line:
            m = re.search(r"Peak level dB:\s*([-\d.]+)", line)
            if m:
                metrics["peak_level_db"] = float(m.group(1))
        elif "RMS level dB:" in line:
            m = re.search(r"RMS level dB:\s*([-\d.]+)", line)
            if m:
                metrics["rms_level_db"] = float(m.group(1))
        elif "DC offset:" in line:
            m = re.search(r"DC offset:\s*([-\d.]+)", line)
            if m:
                metrics["dc_offset"] = float(m.group(1))

    return metrics, log


def run_extraction(
    input_wav: Path,
    output_wav: Path | None = None,
    noise_db: float = -40.0,
    min_silence_ms: float = 100.0,
    leading_pad_ms: float = 30.0,
    trailing_pad_ms: float = 50.0,
    expected_segments: int = 3,
    segment_index: int = 2,
    report_json_path: Path | None = None,
    analysis_log_path: Path | None = None,
) -> tuple[bool, dict[str, Any]]:
    """Execute the full extraction pipeline and return (success, report_dict)."""
    ffmpeg_bin, ffprobe_bin = check_ffmpeg_available()

    if not input_wav.is_file():
        raise FileNotFoundError(f"Input file does not exist: {input_wav}")

    probe = probe_audio(input_wav, ffprobe_bin)
    total_duration = probe["duration_seconds"]

    min_silence_s = min_silence_ms / 1000.0
    leading_pad_s = leading_pad_ms / 1000.0
    trailing_pad_s = trailing_pad_ms / 1000.0

    silence_intervals, silence_log = detect_silence(
        input_wav, noise_db=noise_db, min_silence_s=min_silence_s, ffmpeg_bin=ffmpeg_bin
    )
    speech_segments = derive_speech_segments(total_duration, silence_intervals)

    num_segments = len(speech_segments)
    is_expected_count = (num_segments == expected_segments)
    valid_index = (1 <= segment_index <= num_segments)

    report: dict[str, Any] = {
        "input_path": str(input_wav),
        "output_path": str(output_wav) if output_wav else None,
        "input_metadata": probe,
        "parameters": {
            "noise_db": noise_db,
            "min_silence_ms": min_silence_ms,
            "leading_pad_ms": leading_pad_ms,
            "trailing_pad_ms": trailing_pad_ms,
            "expected_segments": expected_segments,
            "segment_index": segment_index,
        },
        "silence_intervals": silence_intervals,
        "detected_speech_segments": speech_segments,
        "detected_segment_count": num_segments,
        "segmentation_success": is_expected_count and valid_index,
        "extracted_clip": None,
        "astats": None,
        "error": None,
    }

    if not is_expected_count:
        report["error"] = f"Expected {expected_segments} speech segments, but found {num_segments}."
        if report_json_path:
            report_json_path.parent.mkdir(parents=True, exist_ok=True)
            report_json_path.write_text(json.dumps(report, indent=2))
        return False, report

    if not valid_index:
        report["error"] = f"Requested segment index {segment_index} is out of range (1..{num_segments})."
        if report_json_path:
            report_json_path.parent.mkdir(parents=True, exist_ok=True)
            report_json_path.write_text(json.dumps(report, indent=2))
        return False, report

    # Bounded padding around chosen segment
    idx = segment_index - 1
    raw_start, raw_end = speech_segments[idx]

    # Preceding boundary
    prev_boundary = speech_segments[idx - 1][1] if idx > 0 else 0.0
    gap_before = raw_start - prev_boundary
    max_lead_pad = max(0.0, gap_before / 2.0)
    actual_lead_pad = min(leading_pad_s, max_lead_pad)
    padded_start = max(0.0, round(raw_start - actual_lead_pad, 6))

    # Following boundary
    next_boundary = speech_segments[idx + 1][0] if idx < num_segments - 1 else total_duration
    gap_after = next_boundary - raw_end
    max_trail_pad = max(0.0, gap_after / 2.0)
    actual_trail_pad = min(trailing_pad_s, max_trail_pad)
    padded_end = min(total_duration, round(raw_end + actual_trail_pad, 6))

    if output_wav is not None:
        extract_segment(input_wav, output_wav, padded_start, padded_end, ffmpeg_bin=ffmpeg_bin)
        out_probe = probe_audio(output_wav, ffprobe_bin)
        astats_metrics, astats_log = analyze_audio_astats(output_wav, ffmpeg_bin=ffmpeg_bin)

        report["extracted_clip"] = {
            "raw_start_s": raw_start,
            "raw_end_s": raw_end,
            "padded_start_s": padded_start,
            "padded_end_s": padded_end,
            "duration_seconds": out_probe["duration_seconds"],
            "sample_rate_hz": out_probe["sample_rate_hz"],
        }
        report["astats"] = astats_metrics

        if analysis_log_path:
            analysis_log_path.parent.mkdir(parents=True, exist_ok=True)
            analysis_log_path.write_text(f"=== SILENCEDETECT ===\n{silence_log}\n\n=== ASTATS ===\n{astats_log}\n")

    if report_json_path:
        report_json_path.parent.mkdir(parents=True, exist_ok=True)
        report_json_path.write_text(json.dumps(report, indent=2))

    return True, report


def main() -> int:
    parser = argparse.ArgumentParser(description="Greia Micro-Utterance Audio Extractor.")
    parser.add_argument("input_wav", type=Path, help="Input triple-repetition WAV audio file")
    parser.add_argument("output_wav", type=Path, nargs="?", default=None, help="Output extracted WAV file")
    parser.add_argument("--noise-db", type=float, default=-40.0, help="Noise threshold in dB for silence detection (default: -40.0)")
    parser.add_argument("--min-silence-ms", type=float, default=100.0, help="Minimum silence duration in ms (default: 100.0)")
    parser.add_argument("--leading-pad-ms", type=float, default=30.0, help="Leading silence padding in ms (default: 30.0)")
    parser.add_argument("--trailing-pad-ms", type=float, default=50.0, help="Trailing silence padding in ms (default: 50.0)")
    parser.add_argument("--expected-segments", type=int, default=3, help="Expected number of speech segments (default: 3)")
    parser.add_argument("--segment-index", type=int, default=2, help="1-based segment index to extract (default: 2)")
    parser.add_argument("--report-json", type=Path, default=None, help="Path to write structured JSON report")
    parser.add_argument("--analysis-log", type=Path, default=None, help="Path to write raw analysis log")
    parser.add_argument("--check-only", action="store_true", help="Perform segmentation check without writing output audio")

    args = parser.parse_args()

    if not args.check_only and args.output_wav is None:
        parser.error("output_wav positional argument is required unless --check-only is specified.")

    target_out = None if args.check_only else args.output_wav

    try:
        success, report = run_extraction(
            input_wav=args.input_wav,
            output_wav=target_out,
            noise_db=args.noise_db,
            min_silence_ms=args.min_silence_ms,
            leading_pad_ms=args.leading_pad_ms,
            trailing_pad_ms=args.trailing_pad_ms,
            expected_segments=args.expected_segments,
            segment_index=args.segment_index,
            report_json_path=args.report_json,
            analysis_log_path=args.analysis_log,
        )
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    if not success:
        print(f"FAIL: {report.get('error')}", file=sys.stderr)
        return 1

    clip_info = report.get("extracted_clip")
    if clip_info:
        print(
            f"PASS: extracted segment {args.segment_index}/{args.expected_segments} "
            f"({clip_info['padded_start_s']}s -> {clip_info['padded_end_s']}s, "
            f"dur={clip_info['duration_seconds']}s) -> {args.output_wav}"
        )
    else:
        print(f"PASS: verified {report['detected_segment_count']} segments")

    return 0


if __name__ == "__main__":
    sys.exit(main())
