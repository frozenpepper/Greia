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
**Status:** instructions prepared; actual recording NOT STARTED or accepted.

## 0. Hard rules for this agent

1. Always read the files above **before** operating. Never improvise new
   terminal tools to synthesize directly from an Activity. The
   **only semantic production entry point** is `tools/greia_voice.py`
   and its `greia_voice_core` provider contract. The existing engine
   currently supports macOS/MLX and native speakers; a **Modal
   `VoiceProvider` does not yet exist**. Modal is the preferred future
   authoring platform, **not an already-working integration**.
2. **Never invent lines or translate scripts yourself**. Generate only
   from reviewed four-language cue sheets produced in this plan.
   Every job must have: unique semantic `cue_id`, exact text,
   `locale`, `speaker`, speech `kind`, and path. A missing
   translation is `BLOCKED_TEXT`, never guessed into a recording.
3. **No mass generation until the owner authorizes provider/cloud
   expenditure and the provider is ready.** Do not deploy Modal,
   download multi-GB model weights, start a paid job, or install voice
   dependencies without explicit approval. A task to prepare the
   recording instructions is not approval for open-ended spending.
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

### 2026-10-13 current source stage: all 45 built-ins have ES/FR bundles; NOT 45 accepted languages

The 45 built-ins now all have staged `locales/es.json` and
`locales/fr.json` files, but they have intentionally different
coverage levels:

- **39 packages:** ES/FR bundles have **all currently declared
  English/Italian text keys**. This is source-key parity, **not**
  accepted UI, sound or gameplay translation. The latest adds
  `baia_delle_orche`, `cucciolo_mio`,
  `la_discesa_della_biglia`, `labirinto_magico`,
  `mondo_contrari`, `morbidi_mostriciattoli`,
  `posta_di_leo`, `stelle_incantate`,
  `storie_della_mia_voce`, `teatrino_fiabe`,
  `viaggio_delfino` and the 77-key
  `sottomarino_giramondo`.
- **Five literacy packages** have translated UI/instructions,
  but the actual alphabet/rhyme/phonics/syllable/word examples
  are **NOT adapted to each language**. `foresta_parole`
  deliberately leaves its 24 English-specific
  `word.*`/`phonics.*` source keys untranslated instead
  of lying about language-correct spelling puzzles.
  `alfabeto_leo`, `festa_delle_rime`,
  `officina_dei_suoni` and `sillabe_magiche` have
  source-key parity for UI strings but still need
  local-language pedagogical content/voice.
- **Encyclopedia:** ES/FR only the first 51 of 246
  source text keys (navigation plus lion, elephant,
  octopus, bee, penguin and frog). **195 keys per locale
  remain untranslated.** The source declares **200
  prerecorded audio cue keys per language**; they are
  not 200 approved English/Italian transcripts and
  must not be blindly voiced from short UI headings.

**At least 90 missing ES/FR Activity title voice candidates**
(45 titles × two languages) appear in the generated
`RECORDING_LEDGER.csv`. This is only a small subset:
`sottomarino_giramondo` alone declares 55
source audio cues per locale, including button actions,
orders and 32 marine fact scripts. ES/FR textual
marine facts are now drafted, **not recorded**; other
audio cues without authored scripts remain
`BLOCKED_TEXT`. Dolphin Journey has seven existing
EN/IT narrated cues now explicitly linked to their
caption keys in its two source locale bundles:
review those captions against each existing recording
before treating them as transcripts. Its ES/FR
dialogue/facts are still text-only.

Generate the ledger using the exact command in §2.
Its source title text, expected paths and original
asset hashes are real source facts, but every row's
`speaker`, `kind`, provider, script approval and
human audio acceptance must be filled separately.
`EXISTING_REVIEW_PENDING` does not mean approved.

**Known language and content review requirements:**
- Number Train's `prompt.load` plural item names
  are currently **dormant**: the active puzzle is
  graphical and generated target counts are at least
  two. It is *not* a reproduced 1-item gameplay bug.
  If a localized text/spoken prompt is later wired
  into runtime, author count-sensitive phrasing first.
- `casa_del_dieci`, `bosco_numeri`,
  `viaggio_delfino` and `foresta_parole`
  use literal `$target`, `$num`, `$count`,
  `$word` or `$letter` template markers.
  Never read the markers aloud or erase them during
  locale copy authoring.
- `bottega_delle_misure` must distinguish length
  from height in Spanish and French.
- Curriculum Lessons (letters, syllables, rhyme and
  phonics) require real locale-relative lesson data
  and accepted speech; a visually translated menu
  does **not** establish proper educational behavior.
- `enciclopedia_greia` and
  `sottomarino_giramondo` require narrative/science
  review and exact transcript provenance per cue,
  especially where English and Italian audio have
  richer narration than the on-screen titles.
- Existing My Time incubator EN/IT
  `VOICE_PRODUCTION_BRIEF.md` remains authoritative;
  review ES/FR scripts separately before synthesis.

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

First submit `RECORDING_LEDGER.csv` and a short gap report listing
total cues by `locale,source,state` to the authoring owner.
**This is a prerequisite to producing the large voice batch.**

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

**Local agent must STOP on Modal readiness until the GitHub
authoring owner has committed and tested the adapter and the
owner has approved a concrete cost/run budget.** A status message
`BLOCKED_MODAL_PROVIDER` is correct if this has not happened.
An approved existing MLX provider can be used only with explicit
authority for that route. Do not silently swap to macOS `say`
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
