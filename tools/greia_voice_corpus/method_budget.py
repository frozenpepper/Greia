"""Durable per-provider-call budgets for a separately authorized recording method."""
import json
from pathlib import Path
from .store import write_json


class MethodAttemptBudget:
    """Own actual new-method reservations while preserving lifetime historical totals.

    The ledger is authoritative. The old-format cumulative file is a derived
    mirror for existing history tools; it never resets historical attempts.
    """

    def __init__(self, store):
        self.store = store
        self.path = store.work / "method-reservations.json"
        self.rows = {r["path"]: r for r in store.plan["rows"]}

    def _read(self):
        ledger = json.loads(self.path.read_text())
        if set(ledger["entries"]) != set(self.rows):
            raise ValueError("method budget scope differs from frozen plan")
        for relative, entry in ledger["entries"].items():
            if (entry["prior_count"] != self.rows[relative]["historical_attempts"]
                    or len(entry["attempts"]) > 3
                    or [a["number"] for a in entry["attempts"]] != list(range(1,len(entry["attempts"])+1))):
                raise ValueError("method budget history or reservation sequence differs")
        return ledger

    def reconcile_mirror(self):
        """Repair only the known ledger-then-mirror crash window, without a new call."""
        ledger = self._read()
        expected = {p:e["prior_count"]+len(e["attempts"]) for p,e in ledger["entries"].items()}
        mirror_path = self.store.work / "carrier-attempt-counts.json"
        actual = json.loads(mirror_path.read_text())
        if set(actual) != set(expected) or any(actual[p] not in {n,max(ledger['entries'][p]['prior_count'],n-1)} for p,n in expected.items()):
            raise ValueError("cumulative history mirror differs from method ledger")
        if actual != expected:
            write_json(mirror_path, expected)

    def assert_unstarted(self, relative):
        if self._read()["entries"][relative]["attempts"]:
            raise ValueError("method has reserved takes: recover exact job before any new engine call")

    def snapshot(self):
        """Return validated durable reservations for progress and final provenance checks."""
        return self._read()

    def reserve(self, request, attempt: int, evidence: Path):
        """Persist immediately before provider submission; uncertainty consumes a reservation."""
        candidate = Path(request.output).resolve()
        relative = str(candidate.relative_to((self.store.work/"candidates").resolve()))
        row = self.rows[relative]
        if any(request.to_dict().get(k) != row['request'].get(k) for k in ('speaker','kind','locale','text','cue_id','delivery_prompt')):
            raise ValueError("provider reservation differs from frozen semantic request")
        ledger = self._read()
        entry = ledger["entries"][relative]
        if attempt != len(entry["attempts"])+1 or attempt > 3:
            raise ValueError("new-method provider-call allowance exhausted or repeated")
        if entry["attempts"] and entry["attempts"][0]["evidence_dir"] != str(evidence):
            raise ValueError("cannot start a second lifecycle for an uncertain cue")
        entry["attempts"].append({"number":attempt,"evidence_dir":str(evidence),"request":request.to_dict()})
        write_json(self.path, ledger)
        write_json(self.store.work/"carrier-attempt-counts.json",
                   {p:e['prior_count']+len(e['attempts']) for p,e in ledger['entries'].items()})
