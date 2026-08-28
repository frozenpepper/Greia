"""Greia voice-studio memory probe.

Measure the real long-lived Voice Production Engine footprint on the production
workstation. Unlike the earlier probe, this reports current process RSS plus MLX
active/cache/peak memory instead of mislabeling ``ru_maxrss`` (a historical peak)
as current RSS.

By default the probe mirrors normal character production and leaves Whisper
verification enabled. Run a second process with ``--verification off`` to isolate
Chatterbox and compare the two reports.

Examples:

    python tools/measure_voice_memory_growth.py \
        --requests 8 --verification auto \
        --output "${HOME}/Library/Application Support/Greia/voice-production/memory-probe/with-whisper.md"

    python tools/measure_voice_memory_growth.py \
        --requests 8 --verification off \
        --output "${HOME}/Library/Application Support/Greia/voice-production/memory-probe/chatterbox-only.md"

The probe is authoring-time only. It uses the canonical in-process VoiceEngine,
creates review audio only under the selected machine-local report directory, and
deletes those samples after each request.
"""

from __future__ import annotations

import argparse
import csv
import os
import resource
import subprocess
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))
sys.path.insert(0, str(PROJECT_ROOT / "tools"))

from greia_voice_core import (
    SpeechKind,
    VerificationMode,
    VoiceEngine,
    VoiceRegistry,
    VoiceRequest,
)
from greia_voice_core.audio import AudioPipeline
from greia_voice_core.locking import NullGenerationLock
from greia_voice_core.providers import (
    ChatterboxMLXProvider,
    MacOSNativeSpeechProvider,
    UnsupportedNativeSpeechProvider,
)
from greia_voice_core.verification import WhisperVerifier


def _peak_rss_mib() -> float:
    """Return process peak RSS in MiB (historical high-water mark)."""
    max_rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    if sys.platform == "darwin":
        return round(max_rss / (1024.0 * 1024.0), 2)
    return round(max_rss / 1024.0, 2)


def _current_rss_mib() -> float | None:
    """Return current resident-set size in MiB without an extra dependency."""
    try:
        raw = subprocess.check_output(
            ["ps", "-o", "rss=", "-p", str(os.getpid())],
            text=True,
        ).strip()
        if not raw:
            return None
        # POSIX ps reports RSS in KiB on macOS/Linux.
        return round(int(raw.split()[0]) / 1024.0, 2)
    except (OSError, subprocess.SubprocessError, ValueError):
        return None


def _mlx_memory() -> dict[str, float | None]:
    """Return MLX allocator memory in MiB when MLX is available."""
    try:
        import mlx.core as mx

        scale = 1024.0 * 1024.0
        return {
            "mlx_active_mib": round(mx.get_active_memory() / scale, 2),
            "mlx_cache_mib": round(mx.get_cache_memory() / scale, 2),
            "mlx_peak_mib": round(mx.get_peak_memory() / scale, 2),
        }
    except Exception:
        return {
            "mlx_active_mib": None,
            "mlx_cache_mib": None,
            "mlx_peak_mib": None,
        }


def _snapshot() -> dict[str, float | None]:
    return {
        "rss_current_mib": _current_rss_mib(),
        "rss_peak_mib": _peak_rss_mib(),
        **_mlx_memory(),
    }


def _build_engine() -> VoiceEngine:
    return VoiceEngine(
        project_root=PROJECT_ROOT,
        registry=VoiceRegistry.load(PROJECT_ROOT),
        providers=(
            ChatterboxMLXProvider(),
            MacOSNativeSpeechProvider(),
            UnsupportedNativeSpeechProvider(),
        ),
        verifier=WhisperVerifier(),
        audio_pipeline=AudioPipeline(),
        generation_lock=NullGenerationLock(),
    )


def _request(
    speaker: str,
    text: str,
    output: Path,
    verification: VerificationMode,
) -> VoiceRequest:
    return VoiceRequest(
        speaker=speaker,
        kind=SpeechKind.CHARACTER_DIALOGUE,
        locale="it",
        text=text,
        cue_id=f"memory_probe.{speaker}",
        output=output,
        verification=verification,
        max_attempts=1,
    )


def _fmt(value: object) -> str:
    if value is None:
        return "n/a"
    if isinstance(value, float):
        return f"{value:.2f}"
    return str(value)


def _format_report(
    rows: list[dict],
    baseline: dict[str, float | None],
    verification: VerificationMode,
) -> str:
    lines = ["# Greia voice-studio memory probe", ""]
    lines.append(f"verification: **{verification.value}**")
    lines.append("")
    lines.append(
        "This report distinguishes current RSS, process peak RSS, MLX active memory, "
        "MLX allocator cache and MLX peak memory. `rss_peak`/`mlx_peak` are historical "
        "high-water marks and must not be interpreted as current retained memory."
    )
    lines.append("")
    lines.append("## Baseline")
    lines.append("")
    for key, value in baseline.items():
        lines.append(f"- {key}: {_fmt(value)} MiB")
    lines.append("")
    if not rows:
        lines.append("_no rows collected_")
        return "\n".join(lines) + "\n"

    lines += [
        "## Requests",
        "",
        "| # | speaker | ms | current RSS | peak RSS | MLX active | MLX cache | MLX peak | verifier | disposition |",
        "|---|---|---:|---:|---:|---:|---:|---:|---|---|",
    ]
    for row in rows:
        lines.append(
            f"| {row['index']} | {row['speaker']} | {row['duration_ms']:.0f} | "
            f"{_fmt(row['rss_current_mib'])} | {_fmt(row['rss_peak_mib'])} | "
            f"{_fmt(row['mlx_active_mib'])} | {_fmt(row['mlx_cache_mib'])} | "
            f"{_fmt(row['mlx_peak_mib'])} | {row['verification']} | "
            f"{row['disposition']} |"
        )

    final = rows[-1]
    lines += [
        "",
        "## Final retained state",
        "",
        f"- current RSS: {_fmt(final['rss_current_mib'])} MiB",
        f"- MLX active: {_fmt(final['mlx_active_mib'])} MiB",
        f"- MLX cache: {_fmt(final['mlx_cache_mib'])} MiB",
        f"- process peak RSS: {_fmt(final['rss_peak_mib'])} MiB",
        f"- MLX peak: {_fmt(final['mlx_peak_mib'])} MiB",
        "",
        "Compare this report with a fresh-process run using the opposite "
        "`--verification` setting. Large retained MLX cache after a request is a "
        "Studio allocator-lifecycle problem; large active memory means live arrays/models "
        "are still referenced and requires a different fix.",
        "",
    ]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    default_speakers = ",".join(["lilli", "leo", "flash", "tito", "momo"])
    parser.add_argument("--requests", type=int, default=8)
    parser.add_argument("--speakers", default=default_speakers)
    parser.add_argument(
        "--verification",
        choices=[VerificationMode.AUTO.value, VerificationMode.OFF.value],
        default=VerificationMode.AUTO.value,
        help="auto mirrors normal Studio verification; off isolates Chatterbox",
    )
    parser.add_argument(
        "--text-long",
        action="store_true",
        help="use a longer line instead of the default short multi-word line",
    )
    voice_home = os.environ.get(
        "GREIA_VOICE_HOME",
        str(Path.home() / "Library/Application Support/Greia/voice-production"),
    )
    parser.add_argument(
        "--output",
        default=str(Path(voice_home) / "memory-probe" / "report.md"),
    )
    parser.add_argument("--csv", default=None)
    args = parser.parse_args()

    verification = VerificationMode(args.verification)
    text = (
        "Oggi abbiamo scoperto un colore nuovo dentro il foglio!"
        if args.text_long
        else "Prova a contarle con me."
    )
    speakers = [s.strip() for s in args.speakers.split(",") if s.strip()]
    if not speakers:
        parser.error("--speakers resolved to an empty list")

    output_path = Path(args.output).resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    csv_path = Path(args.csv).resolve() if args.csv else output_path.with_suffix(".csv")
    csv_path.parent.mkdir(parents=True, exist_ok=True)

    engine = _build_engine()
    rows: list[dict] = []
    baseline = _snapshot()
    print(f"[probe] verification={verification.value} baseline={baseline}", flush=True)
    try:
        for idx in range(args.requests):
            speaker = speakers[idx % len(speakers)]
            staging = output_path.parent / f"sample-{idx:04d}-{speaker}.wav"
            req = _request(speaker, text, staging, verification)
            before = _snapshot()
            t0 = time.perf_counter()
            result = engine.generate(req)
            duration_ms = (time.perf_counter() - t0) * 1000.0
            after = _snapshot()
            row = {
                "index": idx + 1,
                "speaker": speaker,
                "duration_ms": round(duration_ms, 2),
                **after,
                "rss_before_mib": before["rss_current_mib"],
                "mlx_active_before_mib": before["mlx_active_mib"],
                "mlx_cache_before_mib": before["mlx_cache_mib"],
                "provider": result.provider_id,
                "verification": result.verification.disposition.value,
                "disposition": result.disposition.value,
                "attempts": result.attempts,
            }
            rows.append(row)
            print(
                "[probe] "
                f"{idx + 1}/{args.requests} {speaker} "
                f"rss={_fmt(after['rss_current_mib'])}MiB "
                f"mlx_active={_fmt(after['mlx_active_mib'])}MiB "
                f"mlx_cache={_fmt(after['mlx_cache_mib'])}MiB "
                f"mlx_peak={_fmt(after['mlx_peak_mib'])}MiB "
                f"verify={row['verification']}",
                flush=True,
            )
            if result.output_path is not None and result.output_path.exists():
                try:
                    result.output_path.unlink()
                except OSError:
                    pass
            if result.receipt_path is not None and result.receipt_path.exists():
                try:
                    result.receipt_path.unlink()
                except OSError:
                    pass
    finally:
        engine.close()

    output_path.write_text(
        _format_report(rows, baseline, verification),
        encoding="utf-8",
    )
    if rows:
        with csv_path.open("w", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
            writer.writeheader()
            writer.writerows(rows)
    print(f"[probe] report: {output_path}")
    print(f"[probe] csv:    {csv_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
