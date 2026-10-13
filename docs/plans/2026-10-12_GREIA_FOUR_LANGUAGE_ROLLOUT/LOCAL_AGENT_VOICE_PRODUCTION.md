# Greia — Local Agent: Four-Language Audio Production and Gap Closure

**Owner request:** record *all* missing spoken content across Greia OS,
installer (if any spoken UX), launcher and Parent surfaces, every built-in
Activity, encyclopedia, shared characters and the new Spanish/French
translations. Also restore missing English/Italian audio discovered earlier.  
**Languages:** `en`, `it`, `es`, `fr`.  
**Execution:** local authorized agent only. **The GitHub authoring agent
owns exact text translations, manifests and code integration.** This file
does not authorize new system installation, hosted Actions or flashing.  
**Project authority:** `AGENTS.md`, `SETUP.md`,
`docs/agents/GREIA_LOCAL_VOICE_PRODUCTION_SETUP.md`,
`tools/greia_voice_core/README.md`, and
`docs/plans/2026-10-12_GREIA_FOUR_LANGUAGE_ROLLOUT/PLAN.md`.  
**Status:** voice-production work order **AUTHORIZED** by owner on
2026-10-14 for all missing EN/IT/ES/FR clips; generation/recording itself
has **NOT BEEN EXECUTED** in the GitHub authoring session.
Owner approval covers **every currently authored text translation**, not
unwritten full narration transcripts, missing letter-name/phoneme scripts,
unverified pronunciation or generated audio. Audio remains review-pending
until heard.

**START HERE — EXECUTION ORDER:**
[`LOCAL_AGENT_ALL_APP_VOICE_RECORDING_ORDER.md`](./LOCAL_AGENT_ALL_APP_VOICE_RECORDING_ORDER.md).
It provides the 45×4 sequential Activity pass, shared-system pass, live
CLI commands, resumable ledger and deliverables; this existing document
remains the detailed voice/script/architecture authority.

## 0. Hard rules for this agent

1. Always read the files above **before** operating. Never improvise new
   terminal tools to synthesize directly from an Activity. The
   **only semantic production entry point** is `tools/greia_voice.py`
   and its `greia_voice_core` provider contract. The existing engine
   currently supports macOS/MLX and native speakers; a **Modal
   `VoiceProvider` does not yet exist**. Modal is the preferred future
   authoring platform, **not an already-working integration**.
2. **Never invent a spoken line or translate a missing script.** The
   owner approved all *existing authored* four-language text on
   2026-10-14; a complete, semantically correct utterance in those
   catalogues can be used without another generic copy-approval pass.
   Every voice job still requires a unique semantic `cue_id`, exact
   speech text, `locale`, `speaker`, kind and destination path.
   Where an existing catalogue contains only a glyph, short heading,
   incomplete narration caption or unresolved phoneme-vs-letter-name
   choice, mark `BLOCKED_SCRIPT`; text approval did not create the
   missing required utterance.
3. **Owner's 2026-10-14 instruction authorizes proceeding with actual
   missing-voice production** through an *already available, registered,
   zero-new-spend local Greia Voice Engine provider*, in small reviewable
   batches. A priced/cloud Modal run, installing voice stacks or
   downloading multi-GB weights still requires a separate concrete
   expenditure approval. Do not let missing Modal block an independently
   working local provider, and do not silently spend. Record and
   continue unrelated apps if a speaker/provider remains blocked.
4. Never overwrite accepted WAV/OGG or their receipts. Never directly
   change canonical character anchor hashes or substitute a new
   character identity. Reuse accepted original EN/IT assets.
5. ASR/Whisper is a useful **screen**, not human acceptance;
   `PASS` in the verifier ≠ product-approved speech. Mark every
   new generation `REVIEW_PENDING` until a person listens.
   A missing or incorrect clip is BLOCKED, not made successful by
   silent English/Italian fallback.
6. Keep OS images offline-first: only static accepted audio files
   and lightweight playback/catalogue mappings go into release
   artefacts. No runtime voice generator, Modal credentials or
   cloud connection on a child's Greia machine.
7. On first ambiguity, unsafe condition, changed source SHA or
   missing approved text, **STOP that branch of work**, log the
   exact blocker and ask the GitHub authoring owner for updated
   source/mapping; continue independent non-destructive inventory
   only. No source fixes or commit unless explicitly authorized.

## 1. Sync the approved source safely

Work from the existing designated Greia checkout, never a temporary
branch. In order:

```bash
pwd
git status --short
git branch --show-current
git rev-parse HEAD
git fetch origin main
git switch main
git merge --ff-only origin/main
git status --short
git log -5 --oneline
```

**STOP** immediately if the starting tree is dirty, branch is wrong
or fetch/ff-only fails. Never reset, clean, stash, force-push or rewrite
another agent's work. The source may advance during authoring:
pin the exact `HEAD` in the recording ledger. On a later SHA, review
the changed locale JSONs before continuing queued lines.

Create one ignored evidence directory:

```bash
RUN="tmp/greia-voice-four-language-$(date +%Y%m%d-%H%M%S)"
mkdir -p "$RUN"/{logs,inventory,receipts,review}
git rev-parse HEAD > "$RUN/HEAD.txt"
git status --short > "$RUN/status-before.txt"
```

All further evidence stays under `$RUN` or the standard external
`GREIA_VOICE_HOME` cache, never scattered into the repository.

## 2. Preflight: inventory text, audio and voices without generating

Run the existing non-mutating tools and save **real** results:

```bash
PYTHONPATH=src python3 tools/audit_launcher_spoken_labels.py --locales en it --json \
  > "$RUN/inventory/launcher-en-it.json"
echo "$?" > "$RUN/inventory/launcher-en-it.exit"
python3 tools/greia_voice.py doctor \
  > "$RUN/inventory/voice-doctor.json"
echo "$?" > "$RUN/inventory/voice-doctor.exit"
python3 tools/audit_voice_receipts.py \
  > "$RUN/inventory/voice-receipts.log" 2>&1
echo "$?" > "$RUN/inventory/voice-receipts.exit"
```

When `tools/audit_greia_language_coverage.py` is available in the
current GitHub tree, run:

```bash
python3 tools/audit_greia_language_coverage.py \
  --root . \
  --output "$RUN/inventory/language-coverage.json" \
  --recording-ledger "$RUN/inventory/RECORDING_LEDGER.csv"
echo "$?" > "$RUN/inventory/language-coverage.exit"
```

**Do not interpret a nonzero coverage-audit exit as a runtime
crash**: missing es/fr is expected during rollout. Record exact
missing items; stop the generation stage for any unmapped cue.
Confirm the tool's actual `--help` on current HEAD first.

In addition to tooling, manually inspect **all** of:

- `assets/audio/system/launcher-labels/{en,it}` and their
  pending `es,fr` siblings; all collection/subcollection labels;
- `assets/audio/characters/{canonical,shared}`, their exact
  speakers and references; approved shared praise/retry/start cues;
- `activities/*/locales/{en,it,es,fr}.json`: every
  `strings` and `audio` mapping; accompanying audio path,
  caption key, file presence, and activity title;
- Activity voices in `assets/audio`, `locales/*/audio`,
  `activities/*/assets` and any generated media; also locate
  narration or facts loaded by custom audio modules;
- installer actual spoken audio requirements (if none, document
  **no spoken cues by design**, not a fake missing task);
- Shell, system settings, launcher profiles, OS/Parent panel,
  navigation labels, error prompts, achievements, discovery,
  time, creations, and encyclopedia;
- older Wave 34–37 voice-gap notes in `HANDOVER.md`,
  Activity progress ledger and existing `docs/testing/` evidence
  references. Compare *current source* to each reported gap.
  Distinguish missing files from bad ASR, bad pronunciation,
  wrong language, stale manifest, and missing text.

### Already identified EN/IT recording gaps — do not overlook

These are **verified existing obligations**, not generic search terms:

1. **My Creations launcher destination:** both
   `assets/audio/system/launcher-labels/en/my_creations.wav`
   and `assets/audio/system/launcher-labels/it/my_creations.wav`
   were absent at the latest P6 audit. Exact approved text candidates
   are **EN “My Creations”** and **IT “Le mie creazioni”**.
   See `docs/testing/GREIA_LOCAL_AGENT_TASK_QUEUE.md` GLA-010;
   do not replace with an unrelated “Create” recording.
   Check whether another agent subsequently filled them before recording.
2. **My Time (incubator, not released):**
   `activity_incubator/tempo_di_greia/VOICE_PRODUCTION_BRIEF.md`
   defines the **exact eight semantic cues per EN and IT**:
   title, welcome, clock, practice, stopwatch, timer, finished,
   real-time instruction. These are currently unrecorded
   source obligations. They require L5 reviews and full prereader
   acceptance before promoting the incubated Activity. Extend its
   reviewed cue sheet to ES and FR **only after** the GitHub
   authoring agent has translated those scripts; do not guess
   Spanish/French text or silently release the Activity early.
3. **Previously reported Momo and other presenter gaps:**
   consult the archived P7/Wave 34–37 notes and present code.
   Record the exact missing semantic cues/files, distinguish
   unavailable narration from nonverbal music, and file specific
   ledger rows. Do not mark a broad "Momo voice" task complete
   solely from an Activity title WAV.

### 2026-10-13 latest: all 45 Activities have ES/FR UI text bundles — VOICES/CURRICULUM STILL BLOCKED

The full set of 45 bundled Activities now contains ES/FR JSON
files. **45/45 have all 901 cumulative declared English/Italian
string keys represented**. The total source text
value count is now **901 per target locale, 1,802
ES+FR entries**. This is text-key completeness, not
evidence of correctly narrated lessons.
This is SOURCE-KEY parity, **NOT 45 accepted language
translations**: inline strings, curriculum-specific
logic, voice, line fit, scientific review and the
separately pinned Parent HTML client remain outstanding.

- **40 other Activities**, including
  `sottomarino_giramondo` and
  `enciclopedia_greia`, have all their
  EN/IT-declared source text keys translated to
  Spanish/French in their respective JSON bundles.
- **Four literacy Activities** also have full
  source-key parity for UI texts, but not native
  lesson/curriculum adaptation: `alfabeto_leo`,
  `festa_delle_rime`, `officina_dei_suoni`
  and `sillabe_magiche`. Audio phonemes, letter
  exemplars and rhyme pairs must be recreated in
  each actual learning language, not copied.
- **Word Forest** (`foresta_parole`) now contains
  all 34 locale text keys in ES/FR **plus 21
  source-authored letter/example-word lesson tuples per
  language**, distinct from the prior English and Italian
  lessons. Those are candidate learning words, NOT
  approved phoneme acoustics or shipped support. Its
  code owns three audio cues per lesson:
  letter `<letter>.wav`, prompt
  `find_<letter>.wav`, and spoken example
  `<word_stem>.wav`, under
  `activities/foresta_parole/assets/audio/<locale>/`.
  The provider-free voice inventory now reads the
  literal `foresta_content.PHONICS_DATA` source via
  AST and adds **252 code-owned candidates across
  EN/IT/ES/FR** (20 IT + 22 EN + 21 ES + 21 FR
  lessons, each with three distinct clips).
  **126 new ES/FR lesson audio candidates** remain
  unrecorded. The exact *word* script is present,
  but the exact spoken *letter* and
  *find-the-letter prompt* instructions are
  deliberately `BLOCKED_TEXT`: a letter glyph alone
  cannot establish whether the child should hear
  the letter name or its phoneme. Author, approve
  and translate these scripts first; the CSV must
  not be fed directly to the voice engine.

The **Encyclopedia** now has all **246 source
text keys** staged for ES/FR across six animal
chapters, the solar system, oceans/Earth, human
biology, machines/aviation and ancient history.
Its EN and IT source locale bundles independently
declare **200 audio cues per locale**, **NOT 200
verified literal narrator transcripts**. ES/FR
`audio={}` throughout. A short translated heading
is not permission to generate a long fact narration
with the same cue ID; the LLM/user must first
reconcile actual source recording scripts or
author new approved scripts. All science prose
requires native and content-factual proofreading.

**At least 90 missing ES/FR Activity titles** (45 × 2)
and **126 ES/FR Word Forest phonics clips**
are candidate ledger rows, plus Submarine's 55
source audio cue IDs per language, Dolphin's
seven caption-linked narrative cues and the many
Encyclopedia facts, platform spoken labels, My
Creations portal and legacy My Time incubator.
No scripts/audio are accepted on the basis of
source-key parity. Use `--recording-ledger` to
generate the first exact source census, then
manually reconcile ALL code-loaded/legacy cues,
speaker assignments and recordings.

**Count and template truth:** Number Train currently
generates counts >=2 and uses a graphical display.
Its plural `prompt.load` text is dormant; do NOT
report a reproduced 1-item bug. Add proper
count-sensitive grammar when enabling a spoken/text
prompt or allowing count 1. Keep literal `$num`,
`$target`, `$count`, `$letter`, `$word`
and curly named formatting variables intact.
Measurement questions must distinguish height
and length pedagogically. Dolphin EN/IT seven
narrator/curiosity audio cues now have explicit
`caption_key` links; human-check the text
against those recordings, not an automatic PASS.

Do not assume that per-locale JSON `audio` covers *every*
spoken line: some legacy Activities still select WAVs
programmatically. Those must be listed separately and converted
to semantic production/integration by the GitHub agent.

## 3. The required recording manifest

Use a single UTF-8 `$RUN/inventory/RECORDING_LEDGER.csv` with header:

```text
source,locale,speaker,kind,cue_id,exact_text,caption_key,output_path,existing_asset_sha256,state,provider,receipt_path,asr_result,human_review,notes
```

- One row per **distinct spoken message by locale, speaker and
  semantic context**, not one row per English word found in source.
- Unique `(source,locale,speaker,cue_id)`; never reuse a
  similar-sounding sentence in a different pedagogical context
  without the product owner approving semantic reuse.
- `state` is one of: `EXISTING_REVIEW_PENDING`,
  `EXISTING_ACCEPTED`, `MISSING_AUDIO`, `BLOCKED_TEXT`,
  `PATH_REVIEW_REQUIRED`, `READY_TO_GENERATE`,
  `GENERATED_REVIEW_PENDING`, `ASR_WARNING`,
  `REJECTED`, `HUMAN_ACCEPTED`, `INTEGRATED`.
  Never mark `EXISTING_ACCEPTED` based on a hash or file
  presence alone; the owner needs provenance and human review.
- Include **all four locales** per required cue, including EN/IT
  legacy gaps. Skip only a documented inherently language-neutral
  nonverbal sound; do not re-record music/SFX in a language.
- Exact expected filenames derive from the consuming
  `audio.path` in locale JSON or the canonical platform catalogue.
  Never pick arbitrary final paths in the agent workspace.
- Text, punctuation, numbers, singular/plural, names and vocal
  emotion must be approved in the relevant locale. Spanish
  peninsular/neutral and metropolitan French accent decisions are
  reviewed consistently; don't mix Spanish with Italian.
- `speaker`: use registered canonical Greia speaker IDs
  (Leo, Lilli, Momo, Flash, Tito, Dani or registered pedagogical
  voice as appropriate); don't invent a random new voice.
- `kind`: use only values in `SpeechKind` emitted by
  `python3 tools/greia_voice.py --help` and source enum.
  Treat syllables/letters/phonics as `pedagogical_speech`,
  not mascot voice cloning.

First complete the `RECORDING_LEDGER.csv` census and a gap report
listing total cues by `locale,source,state`. Preserve those in the
run evidence so the GitHub authoring owner can reconcile paths.
**A complete inventory is a prerequisite for a large batch, not a
reason to stop all immediately actionable local recordings.** Work
each app/locale in small bounded batches; hold blocked rows aside.

## 4. Provider readiness / Modal decision

The current production engine's
`tools/greia_voice_core/providers.py` has no Modal backend.
Preferred new architecture: implement a `ModalVoiceProvider`
*inside that provider interface only*, behind a secure,
bounded authoring-time connection with no Greia-OS runtime
dependence. Preserve speaker anchor identity/voice reference
contract, single active producer, timeouts/retries and verification
receipts; do not fork the voice pipeline with an Activity-specific
Modal script. Add tests for error, unavailable provider and output
validation. Credentials must remain outside Git/source/logs.

**Local agent must not use Modal until** its integrated
`VoiceProvider` is committed/tested and a concrete spend budget
is approved; record `BLOCKED_MODAL_PROVIDER` for that route.
**The owner has explicitly authorized recording on 2026-10-14:**
if `doctor` finds a ready **existing registered local provider with
no new spend**, use that engine for a small reviewed batch and continue
the 45-app recording work. Never substitute an unrelated backend or
write a direct synthesis script. Do not silently swap to macOS `say`
for character speech or use a generic accent in lieu of the
canonical character.

For source-proven existing engine environments, preflight is:

```bash
python3 tools/greia_voice.py doctor
```

The doctor's raw report, selected backend, model identifier,
speaker anchors and locale handling belong in the evidence.

## 5. Production protocol once approved

Produce **one** representative test cue for each
`locale × speaker × speech_kind` actually required, listen and
obtain approval *before* mass production. Use only ledger rows
where source texts and reviewer decisions are frozen. A verified
known-good sample for a character is not permission to clone any
other character from an unrelated anchor.

Example **using the already-existing CLI** (change only row data,
choose the approved backend, stage outside final asset tree):

```bash
python3 tools/greia_voice.py generate \
  --speaker leo \
  --kind character_dialogue \
  --locale es \
  --text "¡Vamos a descubrir algo nuevo!" \
  --cue-id example.leo.discovery \
  --output "$RUN/review/leo-es-example.wav"
```

**The example is NOT a content-approved production cue**: it merely
shows the command syntax. Never feed it into the final ledger.
Real jobs use exact approved text/semantic IDs. For a larger
authorized batch, convert only `READY_TO_GENERATE` ledger
rows into JSONL messages with the existing service schema and run:

```bash
python3 tools/greia_voice.py batch --input "$RUN/inventory/approved-requests.jsonl" \
  > "$RUN/logs/batch-output.json" 2>&1
echo "$?" > "$RUN/logs/batch.exit"
```

Every result must have an output file **and**
`<audio>.receipt.json`; no generated file auto-promotes to
`assets/`. Check names, hashes, locale, exact text, voice ID,
verified transcript/disposition, no truncation/repeats or clipping.
Maintain the canonical format already expected by Greia runtime,
prefer bounded PCM mono WAV/OGG as dictated by that cue's consumer.
Do not increase system image footprint recklessly: report bytes
per language, per Activity and total; batch small and deduplicate
truly shared semantic lines.

## 6. Quality control and staged integration

For each generated or previously suspect recording:

1. Verify expected speech is exactly audible, complete and
   correctly pronounced for an adult native speaker; check short
   child-directed intelligibility, natural prosody and identity.
   Preschool phonemes, syllables and numerals get stricter
   pedagogical reviews than casual celebration lines.
2. Listen for mixed languages, false friends, swapped speaker,
   background music, glitches, volume jumps, hallucinated tails,
   offensive/unsafe output and bad emphasis. Use actual
   low-quality speakers when possible.
3. Compare ASR result to expected script and receipt; `WARN`
   must be explicitly reviewed or rejected, not waived globally.
4. Check portable asset paths, WAV/OGG decoder, audio sample
   rate/channels/bit depth, packaging size, caption mapping, and
   unique SHA-256. Verify the same cue plays on both arm64 and
   i386 runtime constraints.
5. Keep rejected candidates and reasons in ignored evidence,
   never overwrite them. Only move accepted clips into versioned
   canonical asset paths through the owning integration workflow.
6. Re-run `tools/audit_launcher_spoken_labels.py --locales
   en it es fr --json` **after** all four locales and files
   exist; if an Activity intentionally does not support four
   languages, document that gap and block full promotion.
7. After integration, exercise every voiced flow with audio
   enabled and disabled for IT/EN/ES/FR. A missing clip may
   fail softly at runtime but must fail the completeness gate.
   Report false-language fallback especially carefully.

Human listening decision is recorded per ledger row with
`reviewer`, date, audible language, intelligibility, speaker
identity, approval status and evidence path. Audio metadata
checks and Whisper cannot certify naturalness. Human approval
is mandatory.

## 7. Required output and update policy

Deliver one evidence directory/ZIP per bounded run, with:

- `HEAD.txt`, starting/final git status and exact commands/exits;
- complete `RECORDING_LEDGER.csv` with every source/cue/locale;
- coverage audit JSON and differentiated missing text/audio list;
- `voice-doctor.json`, actual provider and explicit cost consent;
- staged candidates plus receipts, hashes, ASR reports,
  rejected samples and native-speaker listening decisions;
- manifest of approved final paths, format/size and
  remaining unresolved cues; sample capture per character/locale;
- `REPORT.md` with totals by locale/source, first blocker,
  last completed row, no claims for unexecuted steps;
- evidence ZIP and SHA-256 of archive.

**Agent may update only its task's evidence/status rows** in the
already-existing `docs/testing/GREIA_LOCAL_AGENT_TASK_QUEUE.md`
when allowed by that queue's procedure. Otherwise return the
evidence/notes to the GitHub authoring agent; do not alter
source, commits, voice anchors, installation records or
language registry as an ad-hoc workaround.

**Stop conditions:** unexpected dirty tree, incompatible HEAD,
unreviewed/incomplete text, missing or incorrect voice anchor,
unavailable Modal/MLX backend, unauthorized cloud spend,
non-unique cue, missing ASR/receipt, unacceptable audio,
invalid output format or renderer crash. Preserve negative
evidence, do not restart from zero and do not mark incomplete
languages supported. The exact next cue is the first ledger
row whose state isn't `INTEGRATED` or `EXISTING_ACCEPTED`.

### Final review checklist

- [ ] Every built-in Activity's spoken title exists in four languages
- [ ] Every spoken collection and sub-collection label exists in four
- [ ] Every OS, installer, Parent and child UI spoken prompt mapped
- [ ] Character/dialogue and educational syllable speech inventoried
- [ ] All missing EN/IT recordings corrected and individually approved
- [ ] ES/FR speech tested and approved per canonical character
- [ ] No wrong-language fallback in a promoted built-in Activity
- [ ] Source locale/caption/audio keys agree with reviewed recordings
- [ ] Full offline playthrough and actual low-end speaker acceptance
- [ ] Only reviewed, bounded audio assets included in release image

None of these boxes can be checked merely because a code
commit has been made.


### Staged Rhyme Festival and Sound Workshop curricula (2026-10-13)

The Spanish/French curriculum **source** now exists in
`activities/festa_delle_rime/rhyme_content.py` and
`activities/officina_dei_suoni/sound_content.py`. These are
candidate learning materials, not voice approvals. For
`festa_delle_rime`, every unique `RhymeItem.item_id` across both
`get_corpus(locale)` rhyme pairs and alliteration families is a
spoken-word cue; for `officina_dei_suoni`, every
`SoundUnit.audio_id` is an **isolated phoneme** cue and every
`WordItem.word_id` is a complete **spoken word** cue. Add their
per-locale expected file paths at
`activities/<activity>/assets/audio/<locale>/<cue_id>.wav` to
the full inventory, including EN/IT gaps. Check the actual runtime
loader at source HEAD; avoid duplicate cues used in multiple games.

**BLOCKED until reviewed:** exact pronunciation, stress, the
phoneme articulation (not merely the letter name), regional
variants and any accent lost in an ASCII cue filename; e.g.
`fee` → French *fée*, `bebe` → *bébé*, and `lapiz` →
Spanish *lápiz*. Review the image/word pairing and rhyme sound
with native-speaking educators before freezing each recording
script. Scene/instruction cues (`prompt_*`) need independent
full scripts. Do not presume a spoken string from a key or generate
silence for missing audio. The two manifests remain EN/IT; no
recording integration/approval is claimed here.


### Alphabet Leo and Magic Syllables new source owners (2026-10-13)

**Alphabet Leo**: `activities/alfabeto_leo/alfabeto_model.py`
owns four-language candidate example word/picture pairs and the
locale-relative alphabet. ES has **27 letters including Ñ between N
and O**; FR, IT, EN have 26. The actual playback filenames in
`assets/audio/<locale>/` are `letter_<uppercase-letter>.wav`
and `ask_<uppercase-letter>.wav`, plus `intro.wav`,
`mode_guess_intro.wav`, `try_again.wav`, `well_done.wav`.
Do **not** force ASCII approximation `N` for Spanish `Ñ`.
The <letter> and question transcripts are currently
`BLOCKED_TEXT`: the existing filename does not settle
letter name versus phonemic /sound/, region-specific pronunciation,
or a full grammatically gendered question. Spanish H and French H
are normally silent; never infer /h/ from a capital letter label.
Written examples (`EXAMPLES_ES/FR`) are only candidate display
content and need native speaker/preschool pedagogy review.
Inventory: 58 new ES cues, 56 FR cues.

**Magic Syllables**: `activities/sillabe_magiche/sillabe_content.py`
owns `get_syllable_curriculum(locale)`, two-part builder words,
consonant/vowel teaching inventory, tabs and praise IDs.
`sillabe_audio.SoundManager` owns real runtime playback stems:
`letter_<consonant>`, `syl_<syllable>`,
`find_<syllable>`, `word_<stem>`, and locale
`praise_cues`. The previous 173 ES/190 FR census relied on the Italian C+V
generator and is superseded. The current actual source
exposes 115 ES/93 FR cues (208 combined); explorer/catcher
use explicit _FAMILIES_ES (8 letter groups, 40 syllables)
and _FAMILIES_FR (5 groups, 25 syllables). Word-builder-only
segments require `syl_*` audio but **no** `find_*`
recording if never in a catcher round. Use the newly updated
`tools/audit_greia_language_coverage.py` ledger to derive
precise paths rather than inventing Italian grid combinations.
Only `word_*` has a source-backed candidate written utterance;
all phoneme, prompt, syllable decomposition and praise scripts
are `BLOCKED_TEXT` until native approval. These explicit
families are unreviewed linguistic candidates, not certified
phonemes or permission for mass voice generation.
A French visual split like `MAI-SON` does not prove the
word's acoustic syllabification. The existing file inventory
is **not** an instruction to generate all phonemic recordings
automatically.

These cues are included automatically by
`tools/audit_greia_language_coverage.py` through literal AST
source extraction. The named GLA-015 suite checks its counts
and refuses executable source fragments. The output labels are
staging candidates only. No spoken WAV is approved or included
in ES/FR, and the manifests remain restricted to EN/IT.
