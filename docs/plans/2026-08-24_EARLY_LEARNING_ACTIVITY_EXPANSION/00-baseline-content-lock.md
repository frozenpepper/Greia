# Session 00 — Baseline, catalogue gap, and bilingual content lock

**Provider calls:** forbidden; local deterministic inspection only
**Prerequisite:** current `main`, worktree state recorded, and this README reviewed in full
**Production edits:** prohibited; commit evidence and continuation documents only
**Commit:** `docs(activity): lock early-learning portfolio content baseline`

## Outcome

A hash-bound evidence packet confirms the current 19-Activity catalogue, the ten non-duplicative concepts, and fluent-review disposition for every Italian/English rhyme, sound family, story caption, and pedagogical recording requirement.

## Preconditions

- Run `git pull --ff-only origin main`; record SHA and `git status --short`.
- Read `README.md`, `docs/DOCUMENTATION.md`, `HANDOVER.md`, the active remediation plan, and every specialist route named by the Activity skill.
- Obtain one named fluent Italian reviewer and one named fluent English reviewer with early-literacy competence; one bilingual reviewer may fill both roles.

## Allowed files

```text
docs/plans/2026-08-24_EARLY_LEARNING_ACTIVITY_EXPANSION/evidence/content-lock.json
docs/reviews/2026-08-24_EARLY_LEARNING_ACTIVITY_CONTENT_LOCK.md
docs/plans/2026-08-24_EARLY_LEARNING_ACTIVITY_EXPANSION/README.md
HANDOVER.md
```

## Forbidden changes

- No `activities/`, `src/`, `tests/`, `runtime/`, asset, audio, policy, or build edit.
- No replacement word, rhyme, phoneme, translation, difficulty rule, Activity ID, or title invented by the executing agent.
- No audio generation before the cue corpus receives accepted reviewer disposition.

## Evidence and source decisions

Repository manifests own current catalogue facts. The README owns the draft portfolio/corpora. Rhymes, phoneme examples, and decodable words are language-specific pedagogical truth, so this is a human content-acceptance gate rather than an implementation session.

## Exact implementation

1. Parse every `activities/*/activity.toml` with `tomllib`. Write `content-lock.json` with `schema_version = 1`, `source_sha`, and sorted records containing directory, ID, title key, languages, presentation categories/tags, education fields, input profile, events, and Python file/line counts.
2. Copy the ten planned IDs/titles and README corpora into the JSON. Each localized item contains `semantic_id`, `locale`, `display_text`, `spoken_text`, `picture_id`, `reviewer`, `review_date`, and `disposition` (`accepted` or `rejected`).
3. Review every rhyme for ordinary pronunciation, familiar vocabulary, pictureability, and absence of dialect-only dependence. Review every initial-sound word for an unambiguous first phoneme in the named locale.
4. Supply complete Italian and English story captions in the JSON: exactly three semantic picture IDs per story, each caption no more than 48 grapheme clusters, with no art-baked text.
5. If both locales receive an accepted final-phoneme/multi-phoneme corpus, record it. Otherwise record `omitted_v1` and lock Officina to initial-sound levels with `difficulty_max = 3`.
6. Write the review Markdown with SHA, reviewers, every disposition, content hash, and exact impact of rejections. Amend this README only for reviewer-approved corrections.
7. Update `HANDOVER.md` with SOURCE-only readiness and Session 01 as next step; R7 remains unchanged.

## Tests

- Exactly 19 baseline manifests and ten collision-free planned IDs.
- Every accepted rhyme has two distinct picture IDs; every sound word begins with the reviewed phoneme.
- Every story has three ordered cards, both locales, and no missing review field.
- No item remains without reviewer, date, and accepted/rejected disposition.

## Local gate

```bash
python3 -m json.tool docs/plans/2026-08-24_EARLY_LEARNING_ACTIVITY_EXPANSION/evidence/content-lock.json >/dev/null
python3 -c "import hashlib,json,pathlib; p=pathlib.Path('docs/plans/2026-08-24_EARLY_LEARNING_ACTIVITY_EXPANSION/evidence/content-lock.json'); d=json.loads(p.read_text()); assert d['schema_version']==1 and len(d['baseline_activities'])==19 and len(d['planned_activities'])==10; print(hashlib.sha256(p.read_bytes()).hexdigest())"
```

Expected: both commands exit 0 and the printed SHA-256 is recorded in the review and handover.

## Cumulative gate

```bash
git diff --check
git status --short
```

Expected: diff check exits 0; status lists only allowed documentation/evidence paths.

## Stop conditions

- A reviewer rejects an item and no exact corrected item is approved in the same packet.
- The baseline count/IDs differ or either locale lacks an accountable fluent reviewer.
- Current source invalidates a README contract.

## Handoff

Return the standard packet plus reviewer roles, disposition counts per locale/content type, content SHA-256, exact Officina maximum difficulty, and confirmation that production code/audio/assets were untouched.
