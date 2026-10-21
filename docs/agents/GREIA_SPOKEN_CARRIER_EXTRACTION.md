# Greia spoken-carrier extraction

**Status:** bounded local authoring experiment; output remains listening-pending.
**Implementation:** `tools/voice_carrier.py`.

This tool extracts a short target from one VoiceEngine recording that begins
with a native-language carrier sentence. The carrier and target are synthesized
together through VoiceEngine, preserving one natural performance and one exact
voice master. It is not a second speech generator and does not directly call
VoxStage. The raw carrier WAV and its original VoiceEngine provider receipt must
be retained beside the extracted clip.

## Carrier text and target selection

Use a short, child-natural sentence in the target language, a clear sentence
boundary, then the exact target after a brief pause. Frozen `spoken-short-v1`
starters:

| Locale | Spoken carrier prefix | Words removed |
|---|---|---:|
| en | `Listen to this phrase in English.` | 6 |
| it | `Ascolta questa frase in italiano.` | 5 |
| fr | `Cette phrase est en français.` | 5 |
| es | `Escucha esta frase en español.` | 5 |

These are versioned technical prefixes. Keep the exact target spelling,
accents, punctuation and cue identity in
the corpus plan and target receipt. Prompt only for neutral acting/performance
such as a brief pause; the selected master carries voice identity. Do not use
the v2 persona prompts.

Default corpus selection policy covers all six canonical actors and is
configurable by speaker through `--carrier-speakers`:
`max_words=3 OR (max_words=4 AND max_unicode_alnum=28)`. Count orthographic
words with Unicode letters/digits and internal apostrophes; count
letters/digits, excluding spaces and punctuation. Exclude pronunciation-
authoritative isolated letters and syllables, which remain untouched. Use a
speaker subset for a deliberately disjoint plan; the frozen plan records it.
The inventory is a candidate list only: inspect exact cue meaning and cue kind
before planning a generation. Never stretch or paraphrase the original target
to fit the threshold.

## Extraction contract

The command accepts mono PCM16 WAV only. Other formats must be converted through
the existing Greia `AudioPipeline` first. Inputs are bounded to 120 seconds and
192 kHz. It uses installed `mlx-whisper` with the already-cached
pinned `mlx-community/whisper-base-mlx` model in offline mode; it does not download models
or pass the expected wording as a transcription prompt.

Extraction v6 locates the target from the **end of the recording**. Introductory
words are disposable: their spelling, recognized length and full-transcript
agreement are never acceptance gates. `--prefix` and `--remove-first-words`
retain the intended script/count for provenance and compatibility; the count
must agree with the supplied prefix, but does not choose the cut boundary.

1. Parse finite, ordered word timings within the WAV duration. Find the final
   target suffix, preferring exact normalized target tokens. Explicit `warn`
   mode allows suffix character similarity at least 0.8 for targets of at least
   four characters, considering target word count plus/minus one. Unidentifiable or
   ambiguous suffixes reject; the intro need not transcribe correctly.
2. Search for the existing unique guarded PCM quiet run before that target.
   Keep the 200 ms minimum, 50 ms guards, −42 dBFS RMS / −30 dBFS peak ceilings
   and 100 ms cut padding. If the inter-word interval fails, search the adjacent
   last-intro/first-target timing spans. This handles pauses attributed to words.
3. Cut the exact PCM suffix at the quiet run midpoint. Independently transcribe
   the retained phrase. Expanded boundary searches require the **exact target**
   even in warn mode; discarded introductory speech is never transcribed again.
   Ordinary boundary searches retain the explicit required/warn target policy.
4. Require at least 80 ms voiced signal; preserve sources/existing outputs on
   any error. No fallback to a guessed timestamp, automatic regeneration or
   replacement of runtime files occurs in the standalone cutter.

Receipts identify v6, target-suffix boundary strategy, recognized intro length,
raw/extracted transcripts, target checks, PCM metrics and the actual cut sample.
Intro exact-match is diagnostic only. An extraction result does not establish
speech correctness or human acceptance. Frozen v4 corpus plans cannot run under
v6; prepare an explicitly reviewed new plan before any bulk restart.

ASR text and word alignment are probabilistic evidence. The PCM gap measurement
and sample-index calculation are separate technical checks; neither establishes
correct pronunciation, language recognition, voice identity, naturalness or
human acceptance. Listen to the raw and extracted pair before considering any
runtime replacement. Keep every result `human_review=PENDING` until the owner
reviews it.

## Example

Generate the full native-language carrier plus target as one semantic request
through `tools/greia_voice.py` into external review staging. The resulting WAV
has a sibling `<raw.wav>.receipt.json` provider receipt. Then run the extractor
with the prepared authoring Python:

```bash
voice_python="$HOME/Library/Application Support/Greia/voice-production/venv/bin/python"
"$voice_python" tools/voice_carrier.py \
  /absolute/review/raw.wav /absolute/review/target.wav \
  --locale fr \
  --prefix 'Cette phrase est en français.' \
  --target 'Trouve Luna.' \
  --remove-first-words 5
```

The tool writes `<target.wav>.receipt.json` by default. It records exact prefix
and target, any adjacent VoiceEngine receipt path/hash, source/output hashes,
Whisper package/model/revision, full raw and extracted word alignments, transcript
comparisons, gap RMS/peak/quiet fraction, padding, cut time/sample and the
evidence boundary. If the raw provider receipt has a nonstandard path, provide
it with `--source-receipt`. Standalone user WAVs may be used without a provider
receipt; the extraction receipt will not invent one.

The corpus planner does not select carriers by default. Enable the policy
explicitly with `tools/regenerate_voice_corpus.py plan --carrier-mode
spoken-short-v1`; the plan records the exact prefix, target, word counts,
target-verification mode and algorithm thresholds. The runner sends one
composite request through VoiceEngine, preserves the raw WAV and its true
provider receipt in the external work directory, extracts PCM to a separate
WAV, then packages the target using the existing AudioPipeline for the corpus
format. Its candidate receipt describes the original target and links both
raw-provider and extraction evidence. Nonselected READY rows become
PRESERVED in that explicit plan. A rejected cue remains FAILED until the
existing provider-idle retry process archives the entire attempt. The runner
continues after safe boundary rejection only when invoked with
`--continue-after-carrier-rejection`; uncertain provider failures stop. Fresh
provider attempts are capped at three per cue, and every retry requires
`--acknowledge-provider-idle`. Scope expansions must use a new external run
folder and disjoint `--carrier-speakers` selection.

## Tests and gate

Focused tests:

```bash
voice_python="$HOME/Library/Application Support/Greia/voice-production/venv/bin/python"
PYTHONPATH=src:tools "$voice_python" -m unittest \
  tests.test_voice_carrier tests.test_voice_carrier_policy \
  tests.test_voice_carrier_generation tests.test_greia_voice_corpus -v
```

Before packaging or committing implementation changes, run `make verify` and
record inherited failures without conflating source tests with provider
generation or listening evidence. The parent performs the independent
technical boundary review does not accept speech; every generated or extracted
clip remains listening-pending for owner review.

## Historical v4 behavior (superseded by v5)

Version 4 required exact introductory transcription and, for coincident
boundaries, exact removed-intro transcription. The owner corrected this on
2026-10-22: the intro exists to absorb synthesis instability, so errors in it
must not prevent extraction of a good final target. Version 5 replaces both
intro checks with target-suffix location and retained-target verification.
Historical v4 receipts and experiments remain unchanged.

## Base and diacritic policy (2026-10-22)

Version 6 retains target-suffix selection and PCM safety from v5. Recognition
uses cached multilingual Base revision `1e3e249fb8d01c655324bd6841b1deadffd6d04c`.
Comparison ignores combining diacritics by default, including exact retained-target
checks after expanded boundary search. `extract(..., ignore_accents=False)` or
`--strict-accents` restores accent sensitivity. The original prefix/target and
recognized text remain unchanged in receipts. This does not waive missing/extra
words or unrelated spelling differences. Frozen carrier plans include
ignore_accents, asr_model and asr_revision; v5 experiments remain historical.
