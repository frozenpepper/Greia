"""Greia voice-service memory-growth probe.

Authors can run this script to measure whether the Greia Voice Production Engine
keeps its RSS footprint bounded across many generations on the same warm
worker. It is an authoring-time measurement tool: it does not change engine
behavior and does not package audio.

The script starts one in-process voice engine (the same path a `serve` worker
takes), submits N bounded character_dialogue requests against canonical
references, samples the resident-set size (RSS) of the current process before
and after each request, and writes both a CSV row stream and a Markdown report.

It is intentionally opt-in:

- no `--commit` flag exists;
- no output audio file is created under the project tree (staging lives in
  $GREIA_VOICE_HOME/memory-probe by default);
- the engine is the single source of truth — provider selection, model
  caching, cross-process lock and cleanup all flow through the canonical
  VoiceEngine instance, just as a real `serve` worker would.

Run:

    python tools/measure_voice_memory_growth.py \
        --requests 8 --speakers lilli,leo,flash,tito,momo \
        --output "${HOME}/Library/Application Support/Greia/voice-production/memory-probe/report.md"

The default behavior is a no-network, local-only probe of the current engine.
Sub-second character lines are used to keep generation cost low; widen
--text-syllables or --text-long only when measuring long-form growth.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import resource
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


def _rss_mib() -> float:
    """Return the current process resident-set size in MiB.

    Uses the high-resolution `ru_maxrss` from `resource.getrusage` (macOS:
    bytes; Linux: kilobytes). The platform-specific unit is handled here.
    """
    ru = resource.getrusage(resource.RUSAGE_SELF)
    max_rss = ru.ru_maxrss
    if sys.platform == "darwin":
        # macOS reports bytes in ru_maxrss on modern Python.
        return round(max_rss / (1024.0 * 1024.0), 2)
    return round(max_rss / 1024.0, 2)


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
        # In-process single-worker; no interprocess lock needed.
        generation_lock=NullGenerationLock(),
    )


def _request(speaker: str, text: str, output: Path) -> VoiceRequest:
    return VoiceRequest(
        speaker=speaker,
        kind=SpeechKind.CHARACTER_DIALOGUE,
        locale="it",
        text=text,
        cue_id=f"memory_probe.{speaker}",
        output=output,
        # Skip verifier: it loads a second multi-GB model on first call and
        # would dominate the footprint signal we are trying to measure.
        verification=VerificationMode.OFF,
        max_attempts=1,
    )


def _format_report(rows: list[dict], output_path: Path) -> str:
    lines = ["# Greia voice-service memory-growth probe", ""]
    if not rows:
        return "\n".join(lines) + "\n_no rows collected_\n"
    baseline_rss = rows[0]["rss_before_mib"]
    final_rss = rows[-1]["rss_after_mib"]
    peak_rss = max(row["rss_after_mib"] for row in rows)
    growth_mib = round(final_rss - baseline_rss, 2)
    peak_growth_mib = round(peak_rss - baseline_rss, 2)
    lines += [
        f"_requests: {len(rows)}; baseline RSS: {baseline_rss} MiB; "
        f"final RSS: {final_rss} MiB; peak RSS: {peak_rss} MiB._",
        "",
        f"_total growth (final - baseline): **{growth_mib:+.2f} MiB**; "
        f"peak growth (peak - baseline): **{peak_growth_mib:+.2f} MiB**._",
        "",
        "| # | speaker | duration_ms | rss_before (MiB) | rss_after (MiB) | delta (MiB) | provider |",
        "|---|---------|-------------|------------------|-----------------|-------------|----------|",
    ]
    for row in rows:
        lines.append(
            f"| {row['index']} | {row['speaker']} | {row['duration_ms']:.0f} | "
            f"{row['rss_before_mib']:.2f} | {row['rss_after_mib']:.2f} | "
            f"{row['rss_delta_mib']:+.2f} | {row.get('provider', '?')} |"
        )
    lines.append("")
    lines.append(
        "_A well-behaved warm worker should show small, bounded growth after "
        "the first request loads the model weights. Growth > 200 MiB / request "
        "after the first call usually indicates a leaked intermediate buffer._"
    )
    lines.append("")
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    default_speakers = ",".join(["lilli", "leo", "flash", "tito", "momo"])
    parser.add_argument(
        "--requests",
        type=int,
        default=8,
        help="total number of generations to submit (default: 8)",
    )
    parser.add_argument(
        "--speakers",
        default=default_speakers,
        help=(
            "comma-separated character speakers to round-robin through "
            "(default: lilli,leo,flash,tito,momo)"
        ),
    )
    parser.add_argument(
        "--text-syllables",
        action="store_true",
        help="use a tiny one-syllable line per generation (cheapest probe)",
    )
    parser.add_argument(
        "--text-long",
        action="store_true",
        help="use a longer line per generation (worst-case growth probe)",
    )
    voice_home = os.environ.get(
        "GREIA_VOICE_HOME",
        str(Path.home() / "Library/Application Support/Greia/voice-production"),
    )
    parser.add_argument(
        "--output",
        default=str(Path(voice_home) / "memory-probe" / "report.md"),
        help="Markdown report path (default: under GREIA_VOICE_HOME/memory-probe)",
    )
    parser.add_argument(
        "--csv",
        default=None,
        help="optional CSV row stream for spreadsheet/diff",
    )
    args = parser.parse_args()

    if args.text_long:
        text = (
            "Oggi abbiamo scoperto un colore nuovo dentro il foglio!"
        )
    elif args.text_syllables:
        text = "Vai!"
    else:
        text = "Prova a contarle con me."

    speakers = [s.strip() for s in args.speakers.split(",") if s.strip()]
    if not speakers:
        parser.error("--speakers resolved to an empty list")

    output_path = Path(args.output).resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    csv_path = Path(args.csv).resolve() if args.csv else output_path.with_suffix(".csv")
    csv_path.parent.mkdir(parents=True, exist_ok=True)

    print(f"[probe] starting in-process engine against {len(speakers)} speaker(s)", flush=True)
    engine = _build_engine()
    rows: list[dict] = []
    try:
        baseline_rss = _rss_mib()
        print(f"[probe] baseline RSS: {baseline_rss} MiB", flush=True)
        for idx in range(args.requests):
            speaker = speakers[idx % len(speakers)]
            staging = output_path.parent / f"sample-{idx:04d}-{speaker}.wav"
            req = _request(speaker, text, staging)
            rss_before = _rss_mib()
            t0 = time.perf_counter()
            result = engine.generate(req)
            duration_ms = (time.perf_counter() - t0) * 1000.0
            rss_after = _rss_mib()
            rss_delta = round(rss_after - rss_before, 2)
            row = {
                "index": idx,
                "speaker": speaker,
                "duration_ms": duration_ms,
                "rss_before_mib": rss_before,
                "rss_after_mib": rss_after,
                "rss_delta_mib": rss_delta,
                "provider": result.provider_id,
                "output_path": str(result.output_path) if result.output_path else None,
                "disposition": str(result.disposition),
                "attempts": result.attempts,
            }
            rows.append(row)
            print(
                f"[probe] {idx + 1:>3}/{args.requests} speaker={speaker:<6} "
                f"rss_before={rss_before:>7.2f} MiB "
                f"rss_after={rss_after:>7.2f} MiB "
                f"delta={rss_delta:+6.2f} MiB "
                f"took={duration_ms:>6.0f} ms"
                f" disp={row['disposition']}",
                flush=True,
            )
            # Keep staging tidy so the probe does not fill the disk.
            if result.output_path is not None and result.output_path.exists():
                try:
                    result.output_path.unlink()
                except OSError:
                    pass
    finally:
        engine.close()

    report = _format_report(rows, output_path)
    output_path.write_text(report, encoding="utf-8")
    with csv_path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    print(f"[probe] report written: {output_path}")
    print(f"[probe] csv written:    {csv_path}")
    # Print the headline once more for the caller's log.
    if rows:
        growth = round(rows[-1]["rss_after_mib"] - rows[0]["rss_before_mib"], 2)
        peak_growth = round(
            max(r["rss_after_mib"] for r in rows) - rows[0]["rss_before_mib"], 2
        )
        print(
            f"[probe] headline: total growth {growth:+.2f} MiB, "
            f"peak growth {peak_growth:+.2f} MiB across {len(rows)} request(s)"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
