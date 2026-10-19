# Greia — Local Agent: Record All Missing Voices in Every App (EN / IT / ES / FR)

**Subsequent replacement request (2026-10-19):** execute
`docs/agents/GREIA_VOICE_CORPUS_REGENERATION.md` with
`tools/regenerate_voice_corpus.py` for the newly authorized existing-corpus
replacement, per-recording performance prompts and deterministic isolated
letter/syllable preservation. Older add-only/no-overwrite instructions below
describe the previous missing-voice programme and do not prevent this explicitly
requested replacement. New takes remain pending listening; the full replacement
run has not been launched by the tool-preparation session.

**Current routing override — owner decision 2026-10-19:** new character production uses the six accepted v0.2 masters through shared local VoxStage/VoxCPM2 by default, including Dani. Chatterbox is explicitly selectable; pedagogical pronunciation retains its native route. Any older provider/reference descriptions below describe the earlier recording programme and do not select the current backend. Use `tools/greia_voice.py` and current `SETUP.md` §7; existing accepted audio remains unchanged.

**Owner instruction:** 2026-10-14. The owner has approved all *currently authored text translations* in English, Italian, Spanish and French for voice-production use. **Do the work, app by app; do not stop after an inventory.** Missing spoken scripts, pronunciation distinctions, and as-yet-untranslated inline runtime text are *not* magically filled by this approval.

**Canonical repository:** frozenpepper/Greia, branch main. **Scope:** all 45 built-in Activities; every system/launcher/Creations/Parent spoken cue; the Encyclopedia; the My Time incubator; all canonical character/shared voice packs. Repair missing EN/IT recordings as well as creating ES/FR recordings. **Voice path:** only the existing tools/greia_voice.py semantic engine. **Authoring platform:** prefer Modal if an approved provider exists; at this checkpoint it does not, so an already-working, registered, zero-new-spend local provider is authorized for actual production. Do not wait for Modal if the local engine can complete a cue. No unapproved provider installations, model downloads, paid/cloud jobs, or new spend limits. Ask separately for a priced Modal implementation or expenditure if necessary.

## Greia Voice Studio — the existing authoring workflow, not a new recorder

**Use Greia's existing Voice Studio as the owner of all speech production.**
The normative design (`docs/design/GREIA_VOICE_GENERATION_AND_CANONICAL_VOICES.md`,
section 1) calls **Voice Studio** the authoring workflow around
`tools/greia_voice.py` / `VoiceEngine`. `SETUP.md`, section 7, explicitly
states that this name does **not** imply a graphical UI. The authoritative
GitHub `main` source exposes a semantic **CLI, one warm localhost service
and a batch interface**, not a separate voice-recording GUI. If a newer
Voice Studio desktop/web GUI is present *only on this workstation*,
**document its exact executable path, version, source repo/commit, and
whether it routes through VoiceEngine before use**; do not assume
unverified buttons automatically integrate assets or mark them accepted.
Never invent a second TTS/Voice Studio backend or run raw providers outside
the canonical engine.

Trace the **complete** existing Voice Studio path for each job:

```text
approved, exact text + cue_id + locale + semantic speaker/speech kind
    -> tools/greia_voice.py (generate / batch / serve+request)
    -> greia_voice_core.engine.VoiceEngine
    -> greia_voice_core.registry.VoiceRegistry
       (canonical speaker and anchor SHA-256)
    -> registered greia_voice_core.providers.VoiceProvider
       (VoxStage/VoxCPM2 default for all six v0.2 cloned characters;
        Chatterbox explicitly selectable; native pedagogical route;
        doctor is authoritative about workstation readiness)
    -> one locked worker -> SpeechVerifier (advisory Whisper where suitable)
    -> AudioPipeline (WAV/OGG package and format checks)
    -> candidate audio + adjacent .receipt.json (human_review = PENDING)
    -> native-speaker listening, source/caption/path/identity verification
    -> owner acceptance and **separate** versioned asset/integration commit
```

Do not mistake a successful `batch` exit, successful Whisper transcript,
or a candidate receipt for fully accepted, installed audio. The local agent
owns *recording candidates and review evidence*, not changing the release
selector or silently claiming a Voice Studio GUI has performed integration.

**Existing owner-accepted shared audio, do not re-record:**
`assets/audio/characters/shared/v0.2/` already contains the **192
owner-accepted EN/IT recordings: 180 shared reactions and 12 character
introductions** (2026-08-28). The authority is
`docs/design/GREIA_SHARED_CHARACTER_UTTERANCES.md`, plus
`docs/agents/GREIA_SHARED_CHARACTER_UTTERANCE_RECORDING.md`, and its
`manifest.toml` / `review.csv` / receipts. Verify the exact bytes, mapped
semantic family, locale and existing approval; classify valid rows
`EXISTING_ACCEPTED`. Never regenerate this complete set or its historic
retired v0.1 library. Separately note if an Activity's runtime
**fails to resolve** an already-accepted shared cue: that is an
`INTEGRATION_BLOCKED` wiring defect, not missing speech. New ES/FR
shared utterances and genuinely new lines still need the Voice Studio
review path, but never replace established EN/IT assets.

## 0. Read and respect these exact sources

Read AGENTS.md, SETUP.md **section 7 (Voice Studio)**, HANDOVER.md, skills/greia-voice-production/SKILL.md, docs/design/GREIA_VOICE_GENERATION_AND_CANONICAL_VOICES.md **section 1**, docs/design/GREIA_SHARED_CHARACTER_UTTERANCES.md, docs/agents/GREIA_SHARED_CHARACTER_UTTERANCE_RECORDING.md, docs/agents/GREIA_LOCAL_VOICE_PRODUCTION_SETUP.md, tools/greia_voice_core/README.md, and docs/plans/2026-10-12_GREIA_FOUR_LANGUAGE_ROLLOUT/LOCAL_AGENT_VOICE_PRODUCTION.md. The last file is the detailed source/phonics/voice-identity authority; this work order gives the execution sequence. Use docs/testing/GREIA_LOCAL_AGENT_TASK_QUEUE.md as the *only* task queue (GLA-014/015 and GLA-010), not a new competing status system.

Never change the system's supported-language registry, the Activity manifests, the installer, the pinned Parent browser client, release statuses, canonical voice reference hashes, or the child-device image. English/Italian remain the only selectable languages pending separate L6 release acceptance. Spanish/French may be generated **offline** without enabling them.

## 1. Sync safely; make one persistent evidence directory

From the authorized existing Greia checkout:

~~~bash
pwd
git status --short
git branch --show-current
git rev-parse HEAD
~~~

**STOP** if the tree is unexpectedly dirty or not on main; never reset, stash, clean, switch branches or discard unrelated work. On clean main:

~~~bash
git fetch origin main
git merge --ff-only origin/main
git status --short
RUN="tmp/greia-all-app-voices-$(date +%Y%m%d-%H%M%S)"
mkdir -p "$RUN"/{logs,inventory,review,receipts,accepted,blocked}
git rev-parse HEAD > "$RUN/HEAD.txt"
git status --short > "$RUN/status-before.txt"
python3 tools/greia_voice.py --help > "$RUN/logs/voice-help.txt" 2>&1
python3 tools/greia_voice.py doctor > "$RUN/logs/doctor.json" 2>&1
echo "$?" > "$RUN/logs/doctor.exit"
~~~

Do not assume doctor succeeded: read provider availability, speaker anchor SHA checks, exact model and locale support. No generating from a mismatched canonical anchor. The source HEAD is pinned for this run; if source advances, reconcile only changed relevant copy and cue IDs before further generation.

## 2. Build the real four-language gap ledger (no synthesis yet)

~~~bash
python3 tools/audit_greia_language_coverage.py --root . --output "$RUN/inventory/language-coverage.json" --recording-ledger "$RUN/inventory/RECORDING_LEDGER.csv" > "$RUN/logs/language-audit.log" 2>&1
echo "$?" > "$RUN/logs/language-audit.exit"
PYTHONPATH=src python3 tools/audit_launcher_spoken_labels.py --locales en it --json > "$RUN/inventory/launcher-en-it.json" 2> "$RUN/logs/launcher-audit.err"
echo "$?" > "$RUN/logs/launcher-audit.exit"
python3 tools/audit_voice_receipts.py > "$RUN/logs/existing-receipts.log" 2>&1
echo "$?" > "$RUN/logs/existing-receipts.exit"
~~~

The inventory may exit nonzero because speech is missing: save that result; do not confuse it with code failing to run. If a required tool is absent or crashes, capture its traceback and continue **manual read-only** inventory. Confirm the initial ledger's columns:

    source,locale,speaker,kind,cue_id,exact_text,caption_key,output_path,existing_asset_sha256,state,provider,receipt_path,asr_result,human_review,notes

These rows are a **seed**, not complete truth: legacy Python Activities load additional voice files by filename. Do not regenerate accepted recordings merely because they do not appear in the locale JSON's audio section.

List all actual built-in Activities, not a hand-picked subset:

~~~bash
python3 - "$RUN" <<'PY'
from pathlib import Path
import sys
run=Path(sys.argv[1])
apps=sorted(p.parent for p in Path("activities").glob("*/activity.toml"))
(run/"inventory"/"apps-order.txt").write_text("".join(str(p)+"\n" for p in apps),encoding="utf-8")
print("Built-in Activities:",len(apps))
print("\n".join(map(str,apps)))
if len(apps)!=45:
    raise SystemExit("STOP: expected 45 built-ins; reconcile HEAD before working")
PY
~~~

Make one resumable checklist in $RUN/inventory/app-progress.csv with each Activity × locale (180 rows, not just the ones with missing audio). Track NOT_STARTED, AUDITED, RECORDING, READY_FOR_REVIEW, AUDIO_ACCEPTED, BLOCKED, NO_SPEECH_REQUIRED; totals and last completed source/cue. A silent Activity is NO_SPEECH_REQUIRED **only after inspecting its live render/audio behavior**, not because its locale audio map is empty.

## 3. Mandatory app-by-app procedure — process every listed folder in order

For each line of $RUN/inventory/apps-order.txt, process EN, IT, ES and FR in that order, then advance to the next app. At each app:

1. Read activity.toml, main.py, its renderer/app/model/audio modules and all four locales/{lang}.json files; identify the actual profile UI locale and the actual lesson/content language. Cross-check all files under assets/audio/, locales/*/audio/, and custom player loaders. A text label is not necessarily a spoken cue.
2. Walk **all game modes** and narration states from the real source, not only the title. Include launch/welcome, instructions, questions, retries/errors, answer/praise, progress, achievements, completion/replay, scenes/chapters, saved creations and short accessibility descriptions where spoken. If runtime is available, exercise those flows with sound on and off; preserve screenshots/logs separately.
3. Add to RECORDING_LEDGER.csv every actual required spoken cue per locale, including code-derived WAV/OGG path references, exact stable semantic cue ID, real full spoken words, canonical speaker, SpeechKind, consumer path, missing/existing hash, and runtime trigger. Use source-equivalent scripts already approved by the owner. Never infer a long encyclopedia narration from its short screen heading.
4. Compare each candidate with the expected canonical path, existing sound bytes, receipt, locale, transcript and real playback. Check the already accepted `v0.2` Voice Studio shared library before marking a reusable shared cue missing. Classify PRESENT_REVIEW_NEEDED, EXISTING_ACCEPTED, MISSING_AUDIO, BLOCKED_SCRIPT, BAD_AUDIO, BAD_PATH, INTEGRATION_BLOCKED (existing accepted sound not correctly wired), or READY_TO_GENERATE. Preserve accepted-source hashes and review manifests. Do not overwrite any existing accepted clip.
5. For every genuinely missing row with a complete approved transcript, a verified speaker and a ready local provider: generate a *small* review batch into $RUN/review/... via section 5. Do this **now**, without pausing merely because other unrelated apps are blocked. Record its output file, receipt, SHA-256 and generation result. If a clip fails, preserve the failure, retry only within the engine's bounded policy and continue unrelated rows.
6. Have the reviewer listen for the exact **native language**, natural age-appropriate prosody, correct character identity, pronunciation/stress and complete phrase. Especially test letter *name versus phoneme*, numbers, spelling, accent marks, silent H, syllables and scientific claims. ASR PASS is not human approval. Track NEEDS_HUMAN_REVIEW when no human is available; keep producing independent permitted clips but never silently label them accepted.
7. Update that app's four rows in app-progress.csv, list remaining blockers and exact cue IDs. Commit **no source edits** on this voice-production pass; preserve reviewed candidate assets, receipts and evidence for the GitHub integration agent.

**Special coverage which MUST NOT be missed:**

- All 45 Activity title cues, plus individual modes/feedback; missing ES/FR activity-title clips do not prove the rest of the Activity is silent.
- **Enciclopedia Greia:** EN/IT bundles declare ~200 narrator audio entries per language; ES/FR audio maps were empty. Map all distinct long-form narration to **real full scripts**, chapters and speakers. Block only genuinely missing narration texts; continue accepted short cues and other work.
- **Submarine Around the World:** ~55 declared cue IDs per source language; follow the actual caption/audio lookup.
- **Dolphin Journey:** seven narrated welcome/fact cues, existing EN/IT recordings and staged ES/FR captions; preserve the caption-to-audio semantic mapping.
- **Word Forest:** model owns native locale-specific phonics; record full lesson letter cue, find prompt and spoken example for each actual lesson. Letter glyph alone is *not* a reviewed letter-name/phoneme transcript.
- **Alphabet Leo:** locale-specific examples; Spanish Ñ is an independent letter. Inspect letter_*, ask_* plus intro, mode switch, praise and retry. Silent H and phoneme/name accuracy require explicit spoken scripts.
- **Magic Syllables:** derive each locale's actual consonant and syllable families, word parts, find prompts, whole words and praise cues from code; French accented MÉ must not be replaced with ME. No invented generic Italian C+V grid. Recheck current tool inventory counts.
- **Rhyme Festival and Sound Workshop:** per-locale rhyme words, isolated phonemes, complete words and instructional prompts; validate actual accent, sound/rhyme pedagogy.
- **Little Greenhouse, Labyrinth, Memory, Number Train, Opposites, Painting:** inspect recently fixed real display copy; do **not** assume every visual label should produce speech or that the presence of a translation proves an audio clip exists.
- **My Time incubator:** read activity_incubator/tempo_di_greia/VOICE_PRODUCTION_BRIEF.md; eight known IT/EN semantic prompts plus source-required ES/FR equivalents. Keep this incubated app unpublished.
- **Characters / already accepted Voice Studio work:** Leo, Lilli, Momo, Flash, Tito, Dani and the approved pedagogical voice. The **180 EN/IT shared reactions and 12 EN/IT character introductions were owner-accepted in v0.2**; verify/reuse these 192 actual assets, **do not re-record them**. Inspect v0.2 `manifest.toml`, `review.csv` and receipts. Report missing runtime resolver integration separately. Record genuinely absent ES/FR shared audio and new approved utterances only. Never clone from a different speaker's reference.

If an Activity requires no speech, document how you determined that (source function and user path). **Do not fabricate prompts solely to fill a language quota.**

## 4. After the 45 apps: shared OS / launcher / other surfaces

Audit all **four** languages in system/launcher/collection/subcollection voice labels, child Home/categories, My Creations portal, Creations library and preview accessibility, profiles, child settings/errors, Shell alerts, shared presenters, Parent audio-guidance (only where actually spoken) and installer voice (if designed). Specifically re-check previously missing assets/audio/system/launcher-labels/{en,it}/my_creations.wav. EN "My Creations" and IT "Le mie creazioni" have been identified as the exact copy. Record ES/FR equivalents from the source language catalogues.

The installer may be text-only: document NO_SPOKEN_UX if so. Don't synthesize every Parent settings label without a genuine voice playback/a11y consumer. Keep a separate row for any spoken runtime text not yet localized; the owner approves authored text, **not nonexistent new scripts**.

## 5. Produce actual audio with the canonical engine

A Voice Studio / VoiceEngine request is READY_TO_GENERATE only when all of: owner-approved **exact utterance** (not an arbitrary caption fragment), locale, canonical speaker, SpeechKind, unique cue ID, approved destination path, available provider, and no accepted existing clip are established. Valid kinds: character_dialogue, shared_character_utterance, pedagogical_speech, dani_system_speech. The engine accepts exact text via tools/greia_voice.py generate or an approved per-app JSONL via batch. Use its --help/README for details.

**First** generate one representative cue for each required locale × speaker × kind; listen and record the sample decision before a large batch. Use real rows, not placeholder sample text. Example JSONL request structure (replace every value from an actual ledger row):

~~~json
{"speaker":"pedagogical","kind":"pedagogical_speech","locale":"es","text":"<EXACT APPROVED UTTERANCE>","cue_id":"<EXACT SEMANTIC ID>","output":"tmp/<RUN>/review/<APP>/<LOCALE>/<CUE>.wav","verification":"off"}
~~~

Do not paste that example literally or invent audio text. Write output inside the real absolute $RUN/review folder, **not canonical assets**. Create a bounded batch (one Activity/locale/speaker at a time), then:

~~~bash
python3 tools/greia_voice.py batch --input "$RUN/inventory/ready-current-batch.jsonl" > "$RUN/logs/batch-current.log" 2>&1
echo "$?" > "$RUN/logs/batch-current.exit"
~~~

Keep the engine single-worker. Each successful request must have audio and a .receipt.json; check its disposition and never accept output solely from exit code. Native pedagogical phoneme/word audio needs native-language listening (ASR can be disabled where inappropriate). Compare original full text, verify output duration/format, clipping and speaker continuity. Estimate bytes per app and per locale. Reuse truly semantic shared cues without corrupting stable speaker identity.

This instruction authorizes producing missing recordings on an **already configured available local Greia voice provider without new spend**. It does not authorize paid Modal/cloud runs, credential entry in files, downloading enormous models, or installing new synthesis stacks. If a modality requires that, mark BLOCKED_PROVIDER_COST, provide a concrete one-off proposed budget/setup and continue the other no-cost sources. Do not bypass tools/greia_voice.py by calling macOS say, MLX, Modal or FFmpeg directly.

## 6. Deliver, preserve progress, and stop correctly

Every run produces these artifacts under $RUN:

- Voice Studio ownership/readiness note: canonical engine CLI version/source SHA, doctor report, provider/anchor verification and any separate workstation-only GUI discovery; explicit reuse count for the **192 accepted v0.2 EN/IT assets** and `INTEGRATION_BLOCKED` count for already-recorded-but-unwired runtime cues;

- HEAD.txt, status-before.txt/status-after.txt, exact command logs/exits, doctor results and provider details;
- inventory/apps-order.txt (45 entries), inventory/app-progress.csv (45×4 rows), complete enriched RECORDING_LEDGER.csv and language-coverage.json;
- every produced WAV/OGG, matching receipt, SHA-256, sample review, ASR result if applicable, rejected-take reason and human-review status;
- inventory/remaining-gaps.csv with *exact* Activity, locale, speaker, cue, path, and BLOCKED_SCRIPT/BLOCKED_PROVIDER_COST/BAD_AUDIO reasons;
- REPORT.md reporting counts by app and locale: already accepted, newly generated, awaiting human hearing, blocked scripts, missing providers, integrated by owner, and truly no-spoken-cues; last completed app and next actionable row;
- one resumable evidence archive with SHA-256, excluding credentials, ephemeral model caches and unrelated system artefacts.

Save progress after **each app**, not only at the end; never delete unfinished or rejected work. You may update **only** the relevant GLA-014/015/010 status/evidence rows in the canonical local-agent task queue as allowed by its instructions. Do **not** commit source code, binaries, translated strings, new voice references or system-language changes yourself. Return the accepted/staged audio paths, receipts and a complete handover; the GitHub integration agent will commit reviewed assets and mapping repairs to main through its normal authoring workflow.

**Stop the affected cue/provider immediately** on mismatched voice-anchor hash, missing exact script, incompatible path, paid-spend request without approval, real output corruption or unreviewed speaker mapping. Do not stop other independent apps unnecessarily. **Stop the entire run** on unexpected dirty worktree, branch mismatch, unsafe source drift or secret exposure. Report actual failure and evidence; never claim 45/45 completion before every app/locale is resolved.

**Acceptance definition:** all 45 built-ins plus shared and incubated spoken surfaces accounted for in EN/IT/ES/FR, each genuinely required cue either an existing *human-accepted* asset or a newly recorded *human-accepted* asset, correct path/codec/caption and offline playback, no language-mismatched fallback. Generated but unreviewed clips are *not* complete. Text-source owner approval does not itself certify speech, pedagogy, rendered layouts, or ES/FR selectable OS support.
