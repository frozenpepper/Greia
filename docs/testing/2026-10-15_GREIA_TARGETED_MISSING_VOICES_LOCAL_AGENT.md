# Greia — Local Agent: Record Only the Missing Four-Language Clips (Targeted Repair)

**Date:** 2026-10-15  
**Canonical GitHub repository/branch:** `frozenpepper/Greia`, `main`  
**Voice Studio authority:** `SETUP.md` §7, `skills/greia-voice-production/SKILL.md`, `tools/greia_voice_core/README.md`, `docs/design/GREIA_VOICE_GENERATION_AND_CANONICAL_VOICES.md`  
**Source baseline audited:** `e1ab2426cf1623ce46b000c2e92973033cdf3f64` and subsequent documentation-only reviews `813266a2`, `77bdbd36`.

## Owner decisions: read carefully

1. The owner **has personally reviewed and APPROVED all recordings already committed**. Those recordings are correct and FINAL. **Do not challenge, re-record, overwrite, replace, re-listen for approval, or reset their receipt status.** The past review's concern about evidence for owner approval is superseded by the owner's explicit confirmation. For any available existing audio, mark `EXISTING_OWNER_APPROVED` and move on.
2. **Record only real missing files.** Do not regenerate 2,331 previously imported clips or the earlier owner-accepted 192 v0.2 shared reactions/introductions.
3. The intended eventual playback policy for normal speech is *file exists in selected language → use it; else try English counterpart → otherwise quiet*. That will be implemented in the Greia platform/Activity playback resolver **by the GitHub engineering agent**, not by this recording run. Phoneme/pronunciation learning should not pretend English fallback is native-language teaching.
4. Record **new** candidate clips through **the existing Voice Studio / VoiceEngine** (`tools/greia_voice.py`). They are NEW, not among the recordings already approved by the owner; prepare them for the owner's next listening acceptance. Do not mark new recordings `APPROVED` until the owner actually approves them.
5. **Do not run `tools/integrate_reviewed_voices.py`**. Its current version can overwrite committed audio unconditionally. Stage new, missing clips and receipts in one ignored evidence run directory. No source edits, installer images, model downloads or cloud/Modal spending. Existing configured, zero-new-spend local Greia providers are approved for this task.

## Exact verified missing work: 35 potential new clips

At the audited baseline, **32 definite absences** and **three newly identified missing alarm-route clips** need to be checked. The three alarm clips are real source-code speech requests, but EN lacks an `audio` mapping and only IT has a dedicated `sub_btn_alarm.wav`. The proposed scripts below make them **35 recording candidates** in total. At a newer HEAD, **if a target exists, skip it**.

**A. Missing Spanish/French Activity titles — four files, script from approved ES/FR bundles:**

| App | Locale | Expected canonical file | Script owner |
|---|---|---|---|
| `bottega_delle_misure` | es | `activities/bottega_delle_misure/locales/es/audio/activity-title.wav` | `locales/es.json → strings.activity.title` |
| `bottega_delle_misure` | fr | `activities/bottega_delle_misure/locales/fr/audio/activity-title.wav` | `locales/fr.json → strings.activity.title` |
| `casa_del_dieci` | es | `activities/casa_del_dieci/locales/es/audio/activity-title.wav` | `locales/es.json → strings.activity.title` |
| `casa_del_dieci` | fr | `activities/casa_del_dieci/locales/fr/audio/activity-title.wav` | `locales/fr.json → strings.activity.title` |

**B. Submarine missing voice stems — fourteen each in Spanish/French, 28 files:**

`activities/sottomarino_giramondo/audio/<locale>/<filename>`, with canonical **Leo** voice, `character_dialogue` kind. EN existing receipts provide the reference intent and speaker. Proposed scripts are authored equivalents for **new review candidates**; existing ES/FR text translations and EN reference scripts should be consulted for meaning. **Do not relabel these as pre-approved recordings.**

| Filename | Spanish candidate script | French candidate script |
|---|---|---|
| `sub_btn_light.wav` | ¡Enciende las luces! | Allume les projecteurs ! |
| `sub_btn_sonar.wav` | ¡Activa el sonar! | Active le sonar ! |
| `sub_btn_bubbles.wav` | ¡Un montón de burbujas de aire! | Plein de bulles d'air ! |
| `sub_btn_horn.wav` | ¡Haz sonar la sirena! | Fais sonner la sirène ! |
| `sub_btn_action.wav` | ¡Botón de acción! | Bouton d'action ! |
| `sub_creature_clownfish.wav` | ¡Pez payaso! | Poisson-clown ! |
| `sub_creature_turtle.wav` | ¡Tortuga marina! | Tortue de mer ! |
| `sub_creature_dolphin.wav` | ¡Delfín curioso! | Dauphin curieux ! |
| `sub_creature_manta.wav` | ¡Manta gigante! | Raie manta géante ! |
| `sub_creature_angler.wav` | ¡Pez linterna! | Poisson-lanterne ! |
| `sub_creature_whale.wav` | ¡Ballena tranquila! | Gentille baleine ! |
| `sub_enc_octopus.wav` | ¡El pulpo hace cosquillas en el cristal! ¡Haz sonar la sirena o suelta burbujas! | La pieuvre chatouille la vitre ! Fais sonner la sirène ou libère des bulles ! |
| `sub_enc_shark.wav` | ¡El tiburón saluda con la aleta! ¡Enciende las luces! | Le requin fait coucou avec sa nageoire ! Allume les projecteurs ! |
| `sub_enc_solved.wav` | ¡Hurra! ¡Qué divertido! | Hourra ! C'était amusant ! |

**C. Previously unmapped alarm cue, currently requested by real gameplay — three files (EN/ES/FR):**

`sub_app.py` requests `voice.btn.alarm`; `locales/it.json` maps it to the existing approved `audio/it/sub_btn_alarm.wav`. English currently has no corresponding `voice.btn.alarm` mapping/file, so this is distinct from the 28 translated gaps. **Do not touch the approved Italian recording.** These are proposed NEW scripts.

| Locale | File | Proposed script |
|---|---|---|
| en | `activities/sottomarino_giramondo/audio/en/sub_btn_alarm.wav` | General submarine alarm! Attention, crew! |
| es | `activities/sottomarino_giramondo/audio/es/sub_btn_alarm.wav` | ¡Alarma general del submarino! ¡Atención, tripulación! |
| fr | `activities/sottomarino_giramondo/audio/fr/sub_btn_alarm.wav` | Alerte générale à bord du sous-marin ! Attention, équipage ! |

**Not missing:** Submarine EN/IT launcher titles already use `audio/{en,it}/sub_title.wav`. Do NOT create redundant `locales/{en,it}/audio/activity-title.wav` solely for filename uniformity. Likewise `sub_creature_coral.wav`, `sub_creature_kelp.wav` and `sub_creature_krill.wav` already exist in several language folders; any `voice.creature.coral/kelp/krill` versus `voice.creature_coral/kelp/krill` mismatch is **an alias/lookup issue**, not a request to make duplicate recordings.

## Step 1 — sync, confirm no competing work, create evidence

Run from the **existing authorized project checkout**, not a fresh duplicate clone:

```bash
pwd
git branch --show-current
git status --short
git rev-parse HEAD
```

If not on `main` or if `git status --short` is unexpectedly nonempty, **STOP and report**. Do not stash, reset, `clean`, force, create a branch, or discard source. On clean `main`:

```bash
git fetch origin main
git merge --ff-only origin/main
RUN="tmp/greia-targeted-missing-voices-$(date +%Y%m%d-%H%M%S)"
mkdir -p "$RUN"/{inventory,jobs,review,logs}
git rev-parse HEAD > "$RUN/HEAD.txt"
git status --short > "$RUN/status-before.txt"
python3 tools/greia_voice.py doctor > "$RUN/logs/doctor.json" 2>&1
echo "$?" > "$RUN/logs/doctor.exit"
python3 tools/greia_voice.py batch --help > "$RUN/logs/batch-help.txt" 2>&1
```

Review `doctor.json`: canonical Leo anchor must match, compatible local `VoiceProvider` must be available, and FFmpeg packaging ready. If provider unavailable, deliver the complete inventory and **BLOCKED_PROVIDER** rather than installing new multi-GB dependencies or spending money. Keep the stage directory even on failure.

## Step 2 — generate exact missing-target manifest and per-locale jobs

Paste and run this ONE script; it uses approved locale bundle text for title cues and the explicit **new candidate scripts** above. It checks for already-existing canonical audio **before** scheduling each candidate. It does **not** change or overwrite any source/shipping asset.

```bash
python3 - "$RUN" <<'PY'
from pathlib import Path
import csv
import json
import sys

root = Path.cwd().resolve()
run = Path(sys.argv[1]).resolve()
review = run / "review"
jobs = run / "jobs"
inventory = run / "inventory"
for p in (review, jobs, inventory):
    p.mkdir(parents=True, exist_ok=True)

# Each tuple is: exact expected filename, Spanish, French new-candidate scripts.
SUB = [
    ("sub_btn_light.wav", "¡Enciende las luces!", "Allume les projecteurs !"),
    ("sub_btn_sonar.wav", "¡Activa el sonar!", "Active le sonar !"),
    ("sub_btn_bubbles.wav", "¡Un montón de burbujas de aire!", "Plein de bulles d'air !"),
    ("sub_btn_horn.wav", "¡Haz sonar la sirena!", "Fais sonner la sirène !"),
    ("sub_btn_action.wav", "¡Botón de acción!", "Bouton d'action !"),
    ("sub_creature_clownfish.wav", "¡Pez payaso!", "Poisson-clown !"),
    ("sub_creature_turtle.wav", "¡Tortuga marina!", "Tortue de mer !"),
    ("sub_creature_dolphin.wav", "¡Delfín curioso!", "Dauphin curieux !"),
    ("sub_creature_manta.wav", "¡Manta gigante!", "Raie manta géante !"),
    ("sub_creature_angler.wav", "¡Pez linterna!", "Poisson-lanterne !"),
    ("sub_creature_whale.wav", "¡Ballena tranquila!", "Gentille baleine !"),
    ("sub_enc_octopus.wav", "¡El pulpo hace cosquillas en el cristal! ¡Haz sonar la sirena o suelta burbujas!", "La pieuvre chatouille la vitre ! Fais sonner la sirène ou libère des bulles !"),
    ("sub_enc_shark.wav", "¡El tiburón saluda con la aleta! ¡Enciende las luces!", "Le requin fait coucou avec sa nageoire ! Allume les projecteurs !"),
    ("sub_enc_solved.wav", "¡Hurra! ¡Qué divertido!", "Hourra ! C'était amusant !"),
]
ALARM = {
    "en": "General submarine alarm! Attention, crew!",
    "es": "¡Alarma general del submarino! ¡Atención, tripulación!",
    "fr": "Alerte générale à bord du sous-marin ! Attention, équipage !",
}
targets = []
for app in ("bottega_delle_misure", "casa_del_dieci"):
    for loc in ("es", "fr"):
        catalogue = json.loads((root/"activities"/app/"locales"/f"{loc}.json").read_text(encoding="utf-8"))
        assert catalogue["locale"] == loc
        script = catalogue["strings"]["activity.title"]
        path = root/"activities"/app/"locales"/loc/"audio"/"activity-title.wav"
        targets.append((app, loc, "activity.title", path, script, "APPROVED_EXISTING_TEXT"))

for loc in ("es", "fr"):
    for filename, spanish, french in SUB:
        path = root/"activities"/"sottomarino_giramondo"/"audio"/loc/filename
        targets.append(("sottomarino_giramondo", loc, filename.removesuffix(".wav"), path,
                        spanish if loc=="es" else french, "NEW_SCRIPT_TO_REVIEW"))

for loc, script in ALARM.items():
    path = root/"activities"/"sottomarino_giramondo"/"audio"/loc/"sub_btn_alarm.wav"
    targets.append(("sottomarino_giramondo", loc, "voice.btn.alarm", path, script, "NEW_SCRIPT_TO_REVIEW"))

assert len(targets)==35, f"Expected 35 targeted candidate locations, got {len(targets)}"
rows = []
requests = {}
for app, loc, cue, final, script, script_state in targets:
    if not final.is_relative_to(root):
        raise SystemExit(f"Unsafe target path: {final}")
    if not script.strip():
        raise SystemExit(f"Missing source script: {app}/{loc}/{cue}")
    is_existing = final.is_file()
    output = review/app/loc/final.name
    row = {
        "activity":app, "locale":loc, "cue_id":cue, "script":script,
        "script_state":script_state, "canonical_path":str(final.relative_to(root)),
        "review_path":str(output), "status":"EXISTING_OWNER_APPROVED" if is_existing else "MISSING_NEEDS_RECORDING",
    }
    rows.append(row)
    if is_existing:
        continue
    job_key = (app,loc)
    requests.setdefault(job_key,[]).append({
        "speaker":"leo", "kind":"character_dialogue", "locale":loc,
        "text":script, "cue_id":f"{app}.{cue}.{loc}",
        "output":str(output), "verification":"auto", "max_attempts":2,
    })
ledger = inventory/"targeted-gaps.csv"
with ledger.open("w", encoding="utf-8", newline="") as stream:
    writer=csv.DictWriter(stream,fieldnames=list(rows[0]))
    writer.writeheader()
    writer.writerows(rows)
for (app,loc),items in requests.items():
    dest = jobs/f"{app}-{loc}.jsonl"
    dest.write_text("".join(json.dumps(item,ensure_ascii=False)+"\n" for item in items),encoding="utf-8")
print(f"Target paths audited: {len(rows)}; already present: {sum(r['status']=='EXISTING_OWNER_APPROVED' for r in rows)}; missing jobs: {sum(map(len,requests.values()))}")
print(f"Review ledger: {ledger}")
print(f"Batch files: {len(requests)}")
PY
```

**Verify the produced `$RUN/inventory/targeted-gaps.csv` before generation.** If any target file has appeared since the reviewed commit, its status must be `EXISTING_OWNER_APPROVED` and it should not appear in any job. A source/title/script mismatch is a **stop for that job only**; continue independently valid ones. Do not use old automated promotion logic.

## Step 3 — record only generated missing jobs using Voice Studio

Run **one worker at a time**; don't launch 35 parallel model instances. Use the existing Voice Studio engine, not direct Chatterbox/macOS commands.

```bash
for job in "$RUN"/jobs/*.jsonl; do
  [ -f "$job" ] || continue
  label=$(basename "$job" .jsonl)
  echo "Recording $label"
  python3 tools/greia_voice.py batch --input "$job" > "$RUN/logs/$label.json" 2> "$RUN/logs/$label.err"
  rc=$?
  printf '%s\n' "$rc" > "$RUN/logs/$label.exit"
  if [ "$rc" -ne 0 ]; then
    echo "Batch $label failed. Preserve evidence and STOP before continuing synthesis."
    break
  fi
done
```

If the script above attempts an unexpectedly high number of rows, compare `targeted-gaps.csv` to the current branch before running. New files must appear under `$RUN/review`, each with its own `<filename>.receipt.json`. If another agent already staged the exact same verified candidate, **reuse their staged candidate rather than regenerate**.

## Step 4 — verify outputs without rejecting already-approved recordings

Check each new review file with basic file integrity and source-consistency verification (do not judge existing approved files again):

```bash
python3 - "$RUN" <<'PY'
from pathlib import Path
import csv, hashlib, json, sys
run=Path(sys.argv[1]).resolve()
ledger=run/"inventory"/"targeted-gaps.csv"
rows=list(csv.DictReader(ledger.open(encoding="utf-8")))
summary=[]
bad=[]
for row in rows:
    if row["status"]=="EXISTING_OWNER_APPROVED":
        summary.append((row,"ALREADY_COMMITTED_OWNER_APPROVED"))
        continue
    p=Path(row["review_path"])
    receipt=p.with_name(p.name+".receipt.json")
    if not p.is_file() or p.stat().st_size < 1024 or not receipt.is_file():
        summary.append((row,"BLOCKED_MISSING_FILE_OR_RECEIPT"))
        bad.append(row["canonical_path"]); continue
    try:
        r=json.loads(receipt.read_text(encoding="utf-8"))
        request=r["request"]
        assert request["locale"]==row["locale"]
        assert request["text"]==row["script"]
        assert request["speaker"]=="leo"
        assert r.get("human_review")!="APPROVED", "New recording incorrectly marked owner approved"
        assert r["output"]["sha256"]==hashlib.sha256(p.read_bytes()).hexdigest()
    except (KeyError,AssertionError,ValueError,UnicodeError) as exc:
        summary.append((row,"BLOCKED_INVALID_RECEIPT"))
        bad.append(f"{row['canonical_path']}: {exc}"); continue
    summary.append((row,"RECORDED_NEW_AWAITING_OWNER_APPROVAL"))
with (run/"inventory"/"recording-results.csv").open("w",encoding="utf-8",newline="") as stream:
    writer=csv.DictWriter(stream,fieldnames=[*rows[0].keys(),"result"])
    writer.writeheader()
    for row,status in summary:
        writer.writerow({**row,"result":status})
print("Results:",{s:sum(state==s for _,state in summary) for _,s in summary})
if bad:
    print("Failures:",*bad,sep="\n- ")
    sys.exit(1)
PY
```

For every **new** take, sample by speaker/locale and check correct words, natural pronunciation, no extra speech, absence of truncation, balanced loudness, and correct cue identity. **All previously committed audio is accepted; skip its listening entirely.** Avoid automatic `APPROVED` rewriting for the newly generated set. If a new text sounds wrong or has a semantic mismatch, keep the candidate evidence and record its exact filename; the original approved assets remain untouched.

## Step 5 — verify real outstanding gaps and deliver one handover

A file check is not enough to prove cue routing. Re-read `sub_app.py`, ES/FR source bundles and the filename list, and record three kinds of issues **separately**:

- **MISSING_AUDIO:** requested semantic cue has no matching ES/FR physical file (the 35 targeted candidates above cover known examples).
- **FILE_PRESENT_UNMAPPED:** physical file exists, but `LocalizedResources.audio_cue` cannot reach it because the ES/FR JSON `audio` map is empty (especially Encyclopedia: **199 narration assets per ES/FR**, Dolphin: **7 narrated assets per ES/FR**, Submarine: voice maps). **Do not record again**; GitHub engineering must implement filename-first resolution and English fallback for ordinary narration.
- **SEMANTIC_ALIAS:** `voice.creature.coral` versus `voice.creature_coral` or `voice.btn.action` vs `voice.btn.alarm` are not proof of missing audio when an existing clip is semantically equivalent. Note the key mapping for the GitHub authoring agent.
- **EDUCATIONAL_FALLBACK_POLICY:** phoneme/spelling/syllable cues require an explicit locale-native policy; do not silently call English pronunciation “Spanish/French complete”.

Also manually inspect the existing official voice inventory under `tools/audit_greia_language_coverage.py` for **newly uncovered genuinely missing scripts/files**, not just these targeted targets. List additional gaps in `inventory/additional-gaps.csv` with exact source paths; do not generate an unbounded extra batch or invent pedagogical scripts. The user has only asked for the identified missing voices now.

Provide:
- `HEAD.txt`, clean git status, doctor, per-batch commands/exits;
- `inventory/targeted-gaps.csv` (35 known target slots), `recording-results.csv`, and any newly discovered gaps;
- **only NEW** staged WAV/OGG, receipts, expected canonical paths and SHA-256, never existing owner-approved recordings duplicated into ZIP;
- `REPORT.md` with counts recorded/already-existed/blocked, precise remaining scripts and recommended integration aliases. State clearly **new review candidates are not yet owner-approved**;
- one ZIP of this `$RUN` directory and its SHA-256, excluding any credentials and model caches.

```bash
git status --short > "$RUN/status-after.txt"
python3 - "$RUN" <<'PY'
from pathlib import Path
import sys
run=Path(sys.argv[1])
report=run/"REPORT.md"
if not report.exists():
    report.write_text("# Targeted missing Greia voice run\n\nSee inventory/*.csv, logs/, review/ and HEAD.txt. New candidate audio awaits owner listening approval.\n",encoding="utf-8")
print(report)
PY
zip -qr "$RUN.zip" "$RUN"
shasum -a 256 "$RUN.zip" > "$RUN.zip.sha256"
printf 'Evidence: %s\nSHA256: %s\n' "$RUN.zip" "$RUN.zip.sha256"
```

Send the resulting ZIP, summary and first unresolved cue back to the GitHub authoring agent. **Do not directly commit/push fresh review candidates, rewrite approved receipt metadata or enable four-language selection**. The GitHub engineering agent will implement the simpler file-first fallback, map/alias exceptions where needed, and integrate only newly approved assets without overwriting any existing sound.
