"""Durable cue states and recoverable multi-file replacement transactions."""
import json
import os
from pathlib import Path
import sqlite3
import tempfile

from .inventory import digest, safe_target


def write_json(path: Path, value: object) -> None:
    atomic_bytes(path, (json.dumps(value, indent=2, ensure_ascii=False) + "\n").encode())


def atomic_bytes(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=".greia-corpus-", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(name, path.stat().st_mode & 0o777 if path.exists() else 0o644)
        os.replace(name, path)
    finally:
        Path(name).unlink(missing_ok=True)


class RunStore:
    """Single-writer SQLite journal. A status reader needs no generation lock."""

    def __init__(self, work: Path) -> None:
        self.work = work.resolve()
        self.plan = json.loads((self.work / "plan.json").read_text(encoding="utf-8"))
        self.root = Path(self.plan["root"])
        self.db = sqlite3.connect(self.work / "state.sqlite3", timeout=30)
        self.db.execute("PRAGMA synchronous=FULL")

    @classmethod
    def create(cls, work: Path, plan: dict) -> "RunStore":
        work.mkdir(parents=True, exist_ok=False)
        write_json(work / "plan.json", plan)
        db = sqlite3.connect(work / "state.sqlite3")
        with db:
            db.execute("CREATE TABLE cues(path TEXT PRIMARY KEY, state TEXT, detail TEXT)")
            db.execute("CREATE TABLE transactions(id INTEGER PRIMARY KEY AUTOINCREMENT, path TEXT, state TEXT, files TEXT)")
            db.executemany("INSERT INTO cues VALUES(?,?,?)", [(r["path"], r["state"], r["reason"]) for r in plan["rows"]])
        db.close()
        return cls(work)

    def close(self) -> None:
        self.db.close()

    def state(self, path: str) -> str:
        return self.db.execute("SELECT state FROM cues WHERE path=?", (path,)).fetchone()[0]

    def set_state(self, path: str, state: str, detail: str = "") -> None:
        with self.db:
            self.db.execute("UPDATE cues SET state=?,detail=? WHERE path=?", (state, detail, path))

    def summary(self) -> dict:
        return dict(self.db.execute("SELECT state,count(*) FROM cues GROUP BY state"))

    def problems(self) -> list[dict]:
        return [{"path": p, "state": s, "detail": d} for p, s, d in self.db.execute(
            "SELECT path,state,detail FROM cues WHERE state NOT IN ('DONE','READY','PRESERVED') ORDER BY path")]

    def prepare(self, path: str, replacements: dict[str, Path]) -> int:
        files = []
        for relative, candidate in replacements.items():
            target = safe_target(self.root, relative)
            files.append({"path": relative, "before": digest(target), "after": digest(candidate),
                          "candidate": str(candidate.relative_to(self.work))})
            if files[-1]["after"] is None:
                raise ValueError(f"missing candidate: {candidate}")
        with self.db:
            cursor = self.db.execute("INSERT INTO transactions(path,state,files) VALUES(?, 'INSTALLING', ?)", (path, json.dumps(files)))
            transaction = cursor.lastrowid
            self.db.execute("UPDATE cues SET state='INSTALLING',detail='' WHERE path=?", (path,))
        return transaction

    def install(self, transaction: int) -> None:
        path, state, raw = self.db.execute("SELECT path,state,files FROM transactions WHERE id=?", (transaction,)).fetchone()
        if state != "INSTALLING":
            return
        files = json.loads(raw)
        # Check the entire pair/catalogue bundle before touching any file.
        for item in files:
            target = safe_target(self.root, item["path"])
            if digest(target) not in {item["before"], item["after"]}:
                raise ValueError(f"destination changed during run: {item['path']}")
            candidate = self.work / item["candidate"]
            if digest(candidate) != item["after"]:
                raise ValueError(f"candidate changed: {candidate}")
        for item in files:
            target = safe_target(self.root, item["path"])
            if digest(target) not in {item["before"], item["after"]}:
                raise ValueError(f"destination changed during installation: {target}")
            backup = self.work / "backups" / str(transaction) / item["path"]
            if item["before"] is not None:
                if not backup.exists():
                    if digest(target) != item["before"]:
                        raise ValueError(f"original backup missing after replacement: {target}")
                    atomic_bytes(backup, target.read_bytes())
                if digest(backup) != item["before"]:
                    raise ValueError(f"backup changed: {backup}")
            if digest(target) != item["after"]:
                atomic_bytes(target, (self.work / item["candidate"]).read_bytes())
        with self.db:
            self.db.execute("UPDATE transactions SET state='DONE' WHERE id=?", (transaction,))
            self.db.execute("UPDATE cues SET state='DONE',detail='human_review=PENDING' WHERE path=?", (path,))

    def recover(self) -> None:
        for (transaction,) in self.db.execute("SELECT id FROM transactions WHERE state='INSTALLING' ORDER BY id").fetchall():
            self.install(transaction)

    def restore(self) -> None:
        """Undo newest transactions first, including an interrupted file pair."""
        for transaction, path, raw in self.db.execute(
            "SELECT id,path,files FROM transactions WHERE state!='RESTORED' ORDER BY id DESC").fetchall():
            files = json.loads(raw)
            for item in files:
                if digest(safe_target(self.root, item["path"])) not in {item["before"], item["after"]}:
                    raise ValueError(f"refusing to erase a later edit: {item['path']}")
                backup = self.work / "backups" / str(transaction) / item["path"]
                if item["before"] is not None and digest(backup) != item["before"]:
                    # A transaction interrupted before backup needs no undo for
                    # a file that is still its original version.
                    if digest(safe_target(self.root, item["path"])) != item["before"]:
                        raise ValueError(f"cannot restore without original backup: {backup}")
            for item in reversed(files):
                target = safe_target(self.root, item["path"])
                if digest(target) == item["before"]:
                    continue
                if item["before"] is None:
                    target.unlink(missing_ok=True)
                else:
                    atomic_bytes(target, (self.work / "backups" / str(transaction) / item["path"]).read_bytes())
            with self.db:
                self.db.execute("UPDATE transactions SET state='RESTORED' WHERE id=?", (transaction,))
                self.db.execute("UPDATE cues SET state='RESTORED',detail='' WHERE path=?", (path,))
