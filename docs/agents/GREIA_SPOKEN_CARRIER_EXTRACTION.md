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
`mlx-community/whisper-tiny` model in offline mode; it does not download models
or pass the expected wording as a transcription prompt.

Extraction succeeds only when all of these hold:

1. `--remove-first-words` equals the exact Unicode-aware word count in
   `--prefix`.
2. Raw ASR word timestamps are finite, ordered, complete and within clip
   duration. The known prefix must match exactly and there must be a recognized
   suffix after it. Repeated prefix words in the suffix reject.
3. Inside the timestamped gap between final prefix word and first target word,
   one unique PCM run of at least 200 ms is at or below the versioned −42 dBFS
   frame RMS and −30 dBFS frame peak thresholds. The run must have 50 ms guards
   from both Whisper word boundaries. Missing or multiple runs reject.
4. A deterministic sample cut is made at the midpoint of that quiet run,
   leaving at least 100 ms low-energy padding on both sides. The cut is first written to a temporary
   file; the final path changes only after extracted audio has valid word
   timestamps and at least 80 ms of cumulative 10 ms frames whose RMS exceeds
   the −42 dBFS voiced-signal floor. A single noise spike or ASR hallucination
   cannot satisfy this guard.
5. A source/output alias, malformed timestamps, merged words without a clear
   gap, unexpected speech, or any extraction error rejects without replacing an
   existing output. There is no guessed boundary or automatic retry.

`--target-verification required` is the default for the standalone CLI and
requires exact raw and extracted target transcripts. Explicit
`--target-verification warn` keeps the exact prefix, timing, unique-gap and
voiced-duration gates, but records target-text mismatches as
`EXTRACTED_TARGET_WARN_PENDING_LISTENING`; it never turns them into a machine
pass. The receipt retains raw and extracted transcripts, target tokens,
confidence fields when available, policy and exact-match flags. Use warn mode
only through an explicit frozen corpus plan.

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

## v4: coincident ASR boundaries

Whisper may assign a real pause to the first target-word span while prefix-end
and target-start coincide. Version 4 distinguishes this from an out-of-WAV
timestamp. For this case only, it searches from prefix-end through the first
target span's end using the same unique 200 ms quiet-run and padding guards.
Both removed audio and retained audio must independently transcribe to exactly
the known prefix and target; `warn` cannot waive these recovery checks. Evidence
records the search strategy, search extent, removed transcript and word spans.
No new synthesis is needed to test captured raw recordings. Matching ASR is
technical evidence, not pronunciation or human listening acceptance.
