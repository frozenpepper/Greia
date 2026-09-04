"""Audit-tool tests.

The audit tool recomputes ``transcript_similarity`` from
``tools/greia_voice_core.verification`` for every receipt under a review
workspace and hard-fails if the stored score is not reproducible. These
tests construct synthetic receipt workspaces, run the audit, and assert
the expected exit code + summary counts.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
AUDIT = PROJECT_ROOT / "tools" / "audit_voice_receipts.py"


def _write_receipt(workspace: Path, rel: str, *, expected: str, transcript, score, disposition: str) -> None:
    target = workspace / rel
    target.parent.mkdir(parents=True, exist_ok=True)
    body = {
        "schema_version": 1,
        "request": {
            "speaker": "lilli",
            "kind": "shared_character_utterance",
            "locale": "it",
            "text": expected,
            "cue_id": "shared.test",
            "verification": "auto",
        },
        "verification": {
            "disposition": disposition,
            "verifier_id": "mlx-whisper-tiny",
            "transcript": transcript,
            "score": score,
        },
        "attempts": 2,
        "human_review": "PENDING",
    }
    target.write_text(json.dumps(body), encoding="utf-8")


def _run_audit(shared: Path, intro: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        [
            sys.executable,
            str(AUDIT),
            "--shared-root", str(shared),
            "--intro-root", str(intro),
        ],
        check=False,
        capture_output=True,
        text=True,
    )


def test_audit_passes_on_reproducible_scores(tmp_path):
    shared = tmp_path / "shared"
    intro = tmp_path / "intro"
    intro.mkdir()
    expected = "Complimenti!"
    transcript = "Complimenti."
    # Score the auditor would compute for this exact pair.
    from greia_voice_core.verification import transcript_similarity
    score = transcript_similarity(expected, transcript)
    _write_receipt(shared, "lilli/it/lilli__it__praise.general__01.wav.receipt.json",
                   expected=expected, transcript=transcript, score=score, disposition="PASS")
    _write_receipt(shared, "lilli/en/lilli__en__praise.general__01.wav.receipt.json",
                   expected=expected, transcript=transcript, score=score, disposition="PASS")

    proc = _run_audit(shared, intro)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "Score mismatches" in proc.stdout
    assert "  Score mismatches (|stored - recomputed| > 0.0005): 0" in proc.stdout
    assert "PASS: 2" in proc.stdout


def test_audit_hard_fails_on_score_mismatch(tmp_path):
    shared = tmp_path / "shared"
    intro = tmp_path / "intro"
    intro.mkdir()
    _write_receipt(shared, "lilli/it/lilli__it__praise.general__01.wav.receipt.json",
                   expected="Complimenti!", transcript="Complimenti.", score=0.999, disposition="PASS")

    proc = _run_audit(shared, intro)
    assert proc.returncode == 2, proc.stdout
    assert "SCORE MISMATCHES" in proc.stdout


def test_audit_hard_fails_on_disposition_mismatch(tmp_path):
    shared = tmp_path / "shared"
    intro = tmp_path / "intro"
    intro.mkdir()
    # Score is reproducible but disposition lies: 0.95 should be PASS, not WARN.
    from greia_voice_core.verification import transcript_similarity
    expected, transcript = "Complimenti!", "Complimenti."
    _write_receipt(shared, "lilli/it/lilli__it__praise.general__01.wav.receipt.json",
                   expected=expected, transcript=transcript,
                   score=transcript_similarity(expected, transcript),
                   disposition="WARN")

    proc = _run_audit(shared, intro)
    assert proc.returncode == 2, proc.stdout
    assert "DISPOSITION MISMATCHES" in proc.stdout


def test_audit_counts_warn_rows_correctly(tmp_path):
    shared = tmp_path / "shared"
    intro = tmp_path / "intro"
    intro.mkdir()
    expected, transcript = "Quasi! Proviamo ancora!", "quasi"
    from greia_voice_core.verification import transcript_similarity
    s = transcript_similarity(expected, transcript)
    _write_receipt(shared, "lilli/it/lilli__it__encourage.retry__02.wav.receipt.json",
                   expected=expected, transcript=transcript, score=s, disposition="WARN")
    s_pass = transcript_similarity("Great work!", "Great work.")
    _write_receipt(shared, "lilli/en/lilli__en__praise.general__01.wav.receipt.json",
                   expected="Great work!", transcript="Great work.", score=s_pass, disposition="PASS")
    _write_receipt(shared, "lilli/it/lilli__it__ready.go__01.wav.receipt.json",
                   expected="Forza, andiamo!", transcript=None, score=None, disposition="NOT_APPLICABLE")

    proc = _run_audit(shared, intro)
    assert proc.returncode == 0, proc.stdout
    assert "PASS: 1" in proc.stdout
    assert "WARN: 1" in proc.stdout
    assert "Audited receipts: 3 total" in proc.stdout
