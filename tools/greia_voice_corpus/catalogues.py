"""Refresh existing derived audio metadata in the same replacement transaction."""
import csv
import io
import json
from pathlib import Path
import re
import tomllib

from .store import atomic_bytes


def _toml_fields(block: str, values: dict) -> str:
    for key, value in values.items():
        literal = json.dumps(value, ensure_ascii=False)
        pattern = rf"(?m)^{re.escape(key)} = .*?$"
        if re.search(pattern, block):
            block = re.sub(pattern, lambda _: f"{key} = {literal}", block)
        else:
            block = block.rstrip() + f"\n{key} = {literal}\n\n"
    return block


def derived_replacements(root: Path, relative: str, receipt: dict, staging: Path) -> dict[str, Path]:
    """Only touch catalogue rows describing this exact replaced recording."""
    replacements = {}

    def add(path: Path, text: str) -> None:
        destination = staging / path.relative_to(root)
        atomic_bytes(destination, text.encode("utf-8"))
        replacements[str(path.relative_to(root))] = destination

    shared = root / "assets/audio/characters/shared/v0.2"
    if relative.startswith(str(shared.relative_to(root)) + "/"):
        manifest = shared / "manifest.toml"
        filename = str((root / relative).relative_to(shared))
        sections = manifest.read_text(encoding="utf-8").split("[[utterance]]")
        found = False
        for index in range(1, len(sections)):
            block = tomllib.loads(sections[index])
            if block.get("file") != filename:
                continue
            verification = receipt["verification"]
            sections[index] = _toml_fields(sections[index], {
                "sha256": receipt["output"]["sha256"], "bytes": receipt["output"]["bytes"],
                "speaker": receipt["request"]["speaker"], "kind": receipt["request"]["kind"],
                "provider_id": receipt["provider_id"], "voice_id": receipt["voice_id"],
                "voice_registry_version": receipt["voice_registry_version"], "human_review": "PENDING",
                "delivery_prompt": receipt["request"]["delivery_prompt"],
                "verification_disposition": verification["disposition"],
                "verification_score": verification.get("score") if verification.get("score") is not None else "",
                "whisper_transcript": verification.get("transcript") or "", "attempts": receipt["attempts"],
            })
            found = True
        if not found:
            raise ValueError(f"shared recording missing from manifest: {relative}")
        sections[0] = _toml_fields(sections[0], {
            "status": "corpus regeneration in progress; replaced cues require human review",
            "character_renderer_family": "mixed corpus; exact renderer and acceptance are recorded per cue",
            "dani_provider": "mixed corpus; consult per-cue receipts",
            "verifier": "per-cue receipt; no automatic acceptance",
            "total_clips": len(sections) - 1,
            "total_shared_utterances": sum(tomllib.loads(s).get("family") != "character.intro" for s in sections[1:]),
            "total_character_introductions": sum(tomllib.loads(s).get("family") == "character.intro" for s in sections[1:]),
            "verifier_warn_count": sum(tomllib.loads(s).get("verification_disposition") == "WARN" for s in sections[1:]),
            "human_review_pending_count": sum(tomllib.loads(s).get("human_review") == "PENDING" for s in sections[1:]),
        })
        text = "[[utterance]]".join(sections)
        tomllib.loads(text)
        add(manifest, text)
        review = shared / "review.csv"
        if review.exists():
            reader = csv.DictReader(io.StringIO(review.read_text(encoding="utf-8")))
            fields, rows = reader.fieldnames, list(reader)
            if not any(row.get("file") == filename for row in rows):
                declaration = next(tomllib.loads(s) for s in sections[1:] if tomllib.loads(s).get("file") == filename)
                rows.append({"scope": "intro" if declaration.get("family") == "character.intro" else "shared",
                             "character": receipt["request"]["speaker"], "locale": receipt["request"]["locale"],
                             "family": declaration.get("family", ""), "variant": declaration.get("variant", ""),
                             "text": receipt["request"]["text"], "file": filename})
            for row in rows:
                if row.get("file") == filename:
                    row.update(result="REVIEW_PENDING", note="New VoxStage/master generation; listening required.",
                               verification_disposition=receipt["verification"]["disposition"],
                               verification_score=receipt["verification"].get("score") or "")
            output = io.StringIO(newline="")
            writer = csv.DictWriter(output, fieldnames=fields)
            writer.writeheader()
            writer.writerows(rows)
            add(review, output.getvalue())
    target = root / relative
    for parent in target.parents:
        if parent == root:
            break
        manifest = parent / "audio_manifest.sha256"
        if manifest.is_file():
            name = str(target.relative_to(parent))
            lines = manifest.read_text(encoding="utf-8").splitlines()
            updated = [f"{receipt['output']['sha256']}  {name}" if line.split(maxsplit=1)[-1].lstrip("*") == name else line for line in lines if line.strip()]
            if updated != lines:
                add(manifest, "\n".join(updated) + "\n")
    return replacements
