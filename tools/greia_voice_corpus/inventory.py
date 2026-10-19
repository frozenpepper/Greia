"""Resolve existing speech from receipts and source catalogues without guessing text."""
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import tomllib

from audit_greia_language_coverage import build_inventory
from encyclopedia.voice_ledger import parse_ledger_rows
from greia_platform.system_language import SUPPORTED_SYSTEM_LOCALES
from greia_voice_core.direction import character_delivery
from greia_voice_core.registry import CANONICAL_MANIFEST, VoiceRegistry
from greia_voice_core.models import SpeechKind, VoiceRequest

ROOTS = ("activities", "assets/audio", "activity_incubator")


def digest(path: Path) -> str | None:
    if not path.exists():
        return None
    with path.open("rb") as stream:
        result = hashlib.file_digest(stream, "sha256").hexdigest()
    return result


def receipt_path(path: Path) -> Path:
    return path.with_name(path.name + ".receipt.json")


def safe_target(root: Path, relative: str) -> Path:
    """Limit replacement authority to corpus roots, excluding masters and history."""
    root = root.resolve()
    rel = Path(relative)
    if rel.is_absolute() or ".." in rel.parts or "\\" in relative:
        raise ValueError(f"unsafe corpus path: {relative}")
    if not any(relative.startswith(prefix + "/") for prefix in ROOTS):
        raise ValueError(f"outside corpus roots: {relative}")
    if relative.startswith("assets/audio/characters/canonical/") or relative.startswith("assets/audio/characters/shared/v0.1/"):
        raise ValueError(f"master/historical path is protected: {relative}")
    result = root / rel
    if not result.resolve().is_relative_to(root) or any(p.is_symlink() for p in (result, *result.parents) if p.is_relative_to(root)):
        raise ValueError(f"symlink corpus path: {relative}")
    return result


def _locale_key(path: Path) -> str:
    return "/".join("{locale}" if p in SUPPORTED_SYSTEM_LOCALES else p for p in path.parts)


def preserved_reason(relative: str, request: dict) -> str:
    path = Path(relative)
    if relative.startswith("assets/audio/characters/canonical/"):
        return "canonical cloning master (never a runtime cue)"
    if relative.startswith("assets/audio/characters/shared/v0.1/"):
        return "historical shared library"
    if relative == "assets/audio/system/greia-boot-chime.wav":
        return "non-speech boot chime"
    # These stems belong to the source-owned syllable curriculum. A find_*
    # instruction and an alphabet example phrase are deliberately NOT excluded.
    if relative.startswith("activities/sillabe_magiche/") and path.stem.startswith(("syl_", "letter_")):
        return "deterministic isolated syllable/letter"
    text = str(request.get("text", "")).strip().strip(".!? ")
    if request.get("kind") == "pedagogical_speech" and len(text) == 1 and text.isalpha():
        return "deterministic isolated letter"
    if relative.startswith("activities/foresta_parole/") and len(path.stem) == 1 and path.stem.isalpha():
        return "source-owned isolated phonics letter"
    return ""


class CorpusInventory:
    """Join exact local scripts to existing files and emit explicit unresolved rows."""

    def __init__(self, root: Path, delivery_file: Path, overrides: dict | None = None) -> None:
        self.root = root.resolve()
        self.prompts = character_delivery(delivery_file)
        self.overrides = overrides or {}

    def build(self) -> dict:
        registry = VoiceRegistry.load(self.root)
        source = build_inventory(self.root)
        ledger = self.root / "encyclopedia/VOICE_RECORDING_REQUESTS.md"
        narration = parse_ledger_rows(ledger.read_text(encoding="utf-8")) if ledger.exists() else {}
        scripts = {}
        for item in source["spoken_resources"]:
            entry = narration.get((item["cue_id"], item["locale"])) if item["source"] == "activities/enciclopedia_greia" else None
            if item.get("path") and (entry or item.get("text")):
                relative = str(Path(item["source"]) / item["path"]) if item["source"].startswith("activities/") else item["path"]
                scripts[relative] = {"text": entry.exact_text if entry else item["text"], "locale": item["locale"], "cue_id": item["cue_id"]}
                if entry:
                    scripts[relative].update(speaker=entry.speaker, kind=entry.kind)
        # These existing Activity producers own exact bilingual narration.
        from generate_stelle_incantate_audio import FACTS
        from generate_viaggio_delfino_audio import CLIPS
        for activity, table, speaker in (("stelle_incantate", FACTS, "leo"), ("viaggio_delfino", CLIPS, "tito")):
            for locale, lines in table.items():
                for cue, text in lines:
                    scripts[f"activities/{activity}/assets/audio/{locale}/{cue}.ogg"] = {
                        "text": text, "locale": locale, "cue_id": f"{activity}.{cue}", "speaker": speaker, "kind": "character_dialogue"}
        shared = self.root / "assets/audio/characters/shared/v0.2/manifest.toml"
        if shared.exists():
            for row in tomllib.loads(shared.read_text(encoding="utf-8")).get("utterance", []):
                scripts[str(shared.parent.relative_to(self.root) / row["file"])] = {
                    "speaker": row["speaker"], "kind": row["kind"], "locale": row["locale"],
                    "text": row["text"], "cue_id": row["cue_id"],
                }
        files = sorted(p for prefix in ROOTS for p in (self.root / prefix).rglob("*")
                       if p.is_file() and p.suffix.lower() in {".wav", ".ogg", ".mp3"})
        requests, errors, siblings = {}, {}, defaultdict(list)
        for path in files:
            relative = str(path.relative_to(self.root))
            receipt = receipt_path(path)
            if receipt.exists():
                try:
                    request = json.loads(receipt.read_text(encoding="utf-8"))["request"]
                    if not isinstance(request, dict):
                        raise ValueError("request is not an object")
                    requests[relative] = request
                    siblings[_locale_key(Path(relative))].append(request)
                except (ValueError, KeyError, TypeError) as exc:
                    errors[relative] = f"invalid receipt: {exc}"
        rows = []
        for path in files:
            relative = str(path.relative_to(self.root))
            request = dict(scripts.get(relative, {}))
            request.update(requests.get(relative, {}))
            path_locales = set(Path(relative).parts) & set(SUPPORTED_SYSTEM_LOCALES)
            if not request.get("locale") and len(path_locales) == 1:
                request["locale"] = next(iter(path_locales))
            original_kind = request.get("kind", "")
            original_speaker = request.get("speaker", "")
            reason = preserved_reason(relative, request)
            row = {"path": relative, "state": "PRESERVED" if reason else "READY", "reason": reason}
            if not reason:
                safe_target(self.root, relative)
                # The same cue in another language can establish speaker/purpose,
                # never its transcript. Conflicting identities stay unresolved.
                peers = siblings[_locale_key(Path(relative))]
                for key in ("speaker", "kind"):
                    values = {q[key] for q in peers if q.get(key)}
                    if not request.get(key) and len(values) == 1:
                        request[key] = values.pop()
                override = self.overrides.get(relative, {})
                if not isinstance(override, dict):
                    raise ValueError(f"override for {relative} must be an object")
                if override.get("preserve_reason"):
                    row.update(state="PRESERVED", reason=override["preserve_reason"])
                else:
                    request.update(override)
                    if isinstance(request.get("speaker"), str):
                        request["speaker"] = request["speaker"].strip().lower()
                    if request.get("kind") == "pedagogical_speech":
                        # Owner explicitly requested numbers/words be revoiced too.
                        # Most literacy/counting hosts are Leo; Number Woods is Tito.
                        request["speaker"] = "tito" if relative.startswith("activities/bosco_numeri/") else "leo"
                        request["kind"] = "character_dialogue"
                        # A per-cue explicit character override wins this mapping.
                        request.update(override)
                        request["speaker"] = str(request.get("speaker", "")).strip().lower()
                    missing = [key for key in ("speaker", "kind", "locale", "text") if not request.get(key)]
                    if relative in errors:
                        missing.append(errors[relative])
                    if path.suffix.lower() not in {".wav", ".ogg"}:
                        missing.append("unsupported format (engine packages WAV/OGG)")
                    speaker = request.get("speaker")
                    if speaker not in registry.profiles:
                        missing.append("canonical character unassigned")
                    if request.get("locale") not in SUPPORTED_SYSTEM_LOCALES:
                        missing.append("locale is outside the released registry")
                    if path_locales and request.get("locale") not in path_locales:
                        missing.append("receipt/script locale disagrees with destination")
                    if request.get("kind") not in {"character_dialogue", "shared_character_utterance", "dani_system_speech"}:
                        missing.append("unsupported speech kind")
                    if request.get("kind") == "dani_system_speech" and speaker != "dani":
                        missing.append("Dani speech requires speaker dani")
                    prompt = override.get("delivery_prompt") or self.prompts.get(speaker, "")
                    if not isinstance(prompt, str) or not prompt.strip() or len(prompt) > 2000:
                        missing.append("missing/invalid delivery prompt")
                    row["request"] = {key: request.get(key) for key in ("speaker", "kind", "locale", "text", "cue_id")}
                    row["request"].update(cue_id=request.get("cue_id") or relative, delivery_prompt=prompt.strip() if isinstance(prompt, str) else prompt)
                    if not missing:
                        try:
                            normalized = VoiceRequest(**{k: v for k, v in row["request"].items() if k != "kind"}, kind=SpeechKind(request["kind"]))
                            row["request"]["text"] = normalized.text
                        except (ValueError, TypeError, AttributeError) as exc:
                            missing.append(f"invalid semantic request: {exc}")
                    if missing:
                        row.update(state="BLOCKED_METADATA", reason="; ".join(missing))
            row.update(original_kind=original_kind, original_speaker=original_speaker,
                       original_sha256=digest(path), original_receipt_sha256=digest(receipt_path(path)))
            rows.append(row)
        unknown = set(self.overrides) - {row["path"] for row in rows}
        if unknown:
            raise ValueError(f"override paths do not exist in corpus: {sorted(unknown)}")
        return {"schema_version": 1, "root": str(self.root), "provider": "voxstage",
                "registry_manifest_sha256": digest(self.root / CANONICAL_MANIFEST),
                "delivery_prompts": self.prompts, "source_inventory_errors": source["structural_errors"],
                "summary": dict(Counter(row["state"] for row in rows)), "rows": rows}
