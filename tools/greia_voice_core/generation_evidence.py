"""Durable, external per-request evidence for bounded normal generation attempts."""
from __future__ import annotations

import json
import os
from pathlib import Path
import uuid

from .paths import voice_home


def save_json(path: Path, value: dict) -> None:
    """Atomically persist one small evidence record beside its owner directory."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    with temporary.open("w", encoding="utf-8") as stream:
        json.dump(value, stream, indent=2, ensure_ascii=False)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    temporary.replace(path)


class GenerationEvidence:
    """Own one request's non-reused attempt directories outside the repository."""

    def __init__(self, request: dict, *, root: Path | None = None) -> None:
        self.path = Path(root or voice_home() / "generation-evidence") / uuid.uuid4().hex
        self.path.mkdir(parents=True, exist_ok=False)
        self.history: list[dict] = []
        self.request = request
        self.write_state("GENERATING")

    def attempt(self, number: int) -> Path:
        path = self.path / f"attempt-{number:02}"
        path.mkdir(parents=True, exist_ok=False)
        return path

    def append(self, row: dict) -> None:
        self.history.append(row)
        save_json(self.path / "history.json", {"request": self.request, "attempts": self.history})

    def write_state(self, status: str, **extra) -> None:
        save_json(self.path / "state.json", {
            "status": status, "request": self.request, "history": self.history, **extra,
        })
