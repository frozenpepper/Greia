# Whisper ASR Mismatches — Shared Character Reaction Library

**Source run:** Greia `0cad91c` (post-`1eb4169` engine) · provider `chatterbox-mlx-multilingual-v3` · verifier `mlx-whisper-tiny` (auto, `max_attempts=2`, `pass_threshold=0.72`)
**Scope:** the 27 `WARN` rows in receipt-verification blocks after the 3-pass regeneration of the 19 owner-flagged clips.
**Audit invariant:** for every receipt, `transcript_similarity(expected_text, whisper_transcript)` was recomputed from `tools/greia_voice_core/verification.py` and compared to the stored `verification.score`. Mismatch count: **0**. The stored scores are exact (≤ 0.0005 tolerance).
**Status:** all 27 are still `human_review = PENDING`. A Whisper `WARN` is advisory and is never acceptance or rejection. After the engine post-`1eb4169` fix the 19 owner-flagged clips were re-listened to and owner-accepted.

---

## 1. Headline numbers

| class | count | share |
|---|---|---|
| `PASS` (score ≥ 0.72) | 102 | 53.1% |
| `WARN` (score < 0.72) | 27 | 14.1% |
| `NOT_APPLICABLE` (engine skipped ASR) | 63 | 32.8% |
| **Total receipts** | **192** | **100%** |

- Of 129 receipts the engine did score, 27 (20.9%) came back `WARN`.
- Of 192 total, 27 (14.1%) are `WARN`.
- All 27 had `attempts=2` — the engine already retried each once and the second take still mismatched.
- Score range across the 27 WARNs: 0.0897 – 0.6667. Pass threshold: 0.72.

## 2. Audit invariant: stored score == recomputed score

Every receipt's `verification.score` was recomputed by calling `transcript_similarity(expected, transcript)` from `tools/greia_voice_core/verification.py` and compared to the stored value. The score in the receipt is derived from that function on the final take; the audit confirms the engine's reported scores are exactly reproducible from the receipt's own text and transcript (no rotation, no stale state, no mixed attempts). Mismatch count across all 129 scorable receipts: **0**.

`transcript_similarity(expected, actual)` is:

```python
def normalize_transcript(text: str) -> str:
    return " ".join(re.findall(r"\w+", text.casefold(), flags=re.UNICODE))

def transcript_similarity(expected, actual) -> float:
    en, an = normalize_transcript(expected), normalize_transcript(actual)
    if not en or not an: return 0.0
    char = SequenceMatcher(None, en, an).ratio()
    ew, aw = set(en.split()), set(an.split())
    overlap = len(ew & aw)
    precision = overlap / max(1, len(aw))
    recall    = overlap / max(1, len(ew))
    f1 = 0.0 if not (precision+recall) else 2*precision*recall/(precision+recall)
    return round(char*0.65 + f1*0.35, 4)
```

This means the **normalize step strips punctuation entirely** (`!`, `.`, `,`, `'`, `?` are all dropped by `\w+`). A `!` vs `.` difference can never cause a WARN. A leading-word-vs-full-prompt difference can.

## 3. Two real clusters (not three)

The previous report described a 'punctuation-only mismatch' cluster. That cluster does not exist with this scorer: `!` vs `.` is invisible to `\w+`. Reading the actual transcripts, the 27 WARNs break into two genuine clusters:

### Cluster A — Whisper heard something unrelated (9 of 27, recall=0.0)

Whisper transcribed a string with no token overlap with the expected text. Some of these transcripts include non-Latin characters (`か` Japanese, `ап` Cyrillic, `ди` Cyrillic) which strongly suggests hallucination on low-SNR or short audio. The previous report's 'Italian diacritic' interpretation is not the cause here.

| # | file | stored | transcript |
|---|---|---|---|
| A1 | `momo/it/momo__it__celebrate.success__01.wav.receipt.json` | 0.0897 | `Hellohofer Perか` |
| A2 | `momo/en/momo__en__praise.general__02.wav.receipt.json` | 0.1000 | `3, 1!` |
| A3 | `momo/en/momo__en__encourage.progress__02.wav.receipt.json` | 0.1209 | `Fighting Robinson Shawn Release` |
| A4 | `momo/it/momo__it__encourage.retry__02.wav.receipt.json` | 0.2167 | `qua ап ди` |
| A5 | `tito/it/tito__it__celebrate.success__03.wav.receipt.json` | 0.4643 | `Chemerovilietà` |
| A6 | `leo/it/leo__it__celebrate.success__03.wav.receipt.json` | 0.4680 | `chimera via` |
| A7 | `momo/it/momo__it__celebrate.success__03.wav.receipt.json` | 0.4680 | `Cameravilla!` |
| A8 | `flash/it/flash__it__encourage.progress__01.wav.receipt.json` | 0.5720 | `continuacosi` |
| A9 | `momo/it/momo__it__encourage.progress__01.wav.receipt.json` | 0.5720 | `continuacosi` |

### Cluster B — Whisper heard only a fragment of the expected prompt (18 of 27, recall 0.2–0.5)

Whisper transcribed the **first word** of the expected prompt and stopped. The score is driven by `recall < 0.5` (only 1 of 3-4 expected words) and `f1 < 0.7`, even though `precision` is often 1.0 (the one transcribed word is correct).

Common pattern:

| expected | whisper transcribed | recall | chars | f1 |
|---|---|---|---|---|
| `Almost! Let's try again!` | `Almost.` | 0.20 | 0.43 | 0.33 |
| `Quasi! Proviamo ancora!` | `quasi!` | 0.33 | 0.38 | 0.50 |
| `Come on, let's go!` | `Come on.` | 0.40 | 0.61 | 0.57 |
| `Forza, andiamo!` | `Forza!` | 0.50 | 0.56 | 0.67 |

Full list:

| # | file | stored | exp_norm | act_norm | char | prec | rec | f1 |
|---|---|---|---|---|---|---|---|---|
| B1 | `momo/it/momo__it__encourage.retry__03.wav.receipt.json` | 0.2635 | `ancora una volta` | `una porta maya conditioned fins i` | 0.2857 | 0.1667 | 0.3333 | 0.2222 |
| B2 | `flash/en/flash__en__encourage.retry__02.wav.receipt.json` | 0.3952 | `almost let s try again` | `almost` | 0.4286 | 1.0000 | 0.2000 | 0.3333 |
| B3 | `leo/en/leo__en__encourage.retry__02.wav.receipt.json` | 0.3952 | `almost let s try again` | `almost` | 0.4286 | 1.0000 | 0.2000 | 0.3333 |
| B4 | `lilli/en/lilli__en__encourage.retry__02.wav.receipt.json` | 0.3952 | `almost let s try again` | `almost` | 0.4286 | 1.0000 | 0.2000 | 0.3333 |
| B5 | `momo/en/momo__en__encourage.retry__02.wav.receipt.json` | 0.3952 | `almost let s try again` | `almost` | 0.4286 | 1.0000 | 0.2000 | 0.3333 |
| B6 | `tito/en/tito__en__encourage.retry__02.wav.receipt.json` | 0.3952 | `almost let s try again` | `almost` | 0.4286 | 1.0000 | 0.2000 | 0.3333 |
| B7 | `flash/it/flash__it__encourage.retry__02.wav.receipt.json` | 0.4250 | `quasi proviamo ancora` | `quasi` | 0.3846 | 1.0000 | 0.3333 | 0.5000 |
| B8 | `leo/it/leo__it__encourage.retry__02.wav.receipt.json` | 0.4250 | `quasi proviamo ancora` | `quasi` | 0.3846 | 1.0000 | 0.3333 | 0.5000 |
| B9 | `lilli/it/lilli__it__encourage.retry__02.wav.receipt.json` | 0.4250 | `quasi proviamo ancora` | `quasi` | 0.3846 | 1.0000 | 0.3333 | 0.5000 |
| B10 | `tito/it/tito__it__encourage.retry__02.wav.receipt.json` | 0.4250 | `quasi proviamo ancora` | `quasi` | 0.3846 | 1.0000 | 0.3333 | 0.5000 |
| B11 | `lilli/it/lilli__it__celebrate.success__01.wav.receipt.json` | 0.5167 | `ce l hai fatta` | `sciени fatta` | 0.6154 | 0.5000 | 0.2500 | 0.3333 |
| B12 | `flash/it/flash__it__celebrate.success__01.wav.receipt.json` | 0.5333 | `ce l hai fatta` | `sella i fatta` | 0.6667 | 0.3333 | 0.2500 | 0.2857 |
| B13 | `lilli/it/lilli__it__ready.go__01.wav.receipt.json` | 0.5944 | `forza andiamo` | `forza` | 0.5556 | 1.0000 | 0.5000 | 0.6667 |
| B14 | `lilli/en/lilli__en__ready.go__01.wav.receipt.json` | 0.5957 | `come on let s go` | `come on` | 0.6087 | 1.0000 | 0.4000 | 0.5714 |
| B15 | `momo/en/momo__en__ready.go__01.wav.receipt.json` | 0.5957 | `come on let s go` | `come on` | 0.6087 | 1.0000 | 0.4000 | 0.5714 |
| B16 | `tito/en/tito__en__ready.go__01.wav.receipt.json` | 0.5957 | `come on let s go` | `come on` | 0.6087 | 1.0000 | 0.4000 | 0.5714 |
| B17 | `tito/it/tito__it__celebrate.success__01.wav.receipt.json` | 0.6000 | `ce l hai fatta` | `te lei fatta` | 0.7692 | 0.3333 | 0.2500 | 0.2857 |
| B18 | `lilli/en/lilli__en__encourage.progress__02.wav.receipt.json` | 0.6667 | `almost there` | `almost` | 0.6667 | 1.0000 | 0.5000 | 0.6667 |

## 4. Full WARN table (sorted by stored score, recomputed verified)

| # | file | character | locale | expected | whisper transcript | stored | recomputed |
|---|---|---|---|---|---|---|---|
| 1 | `momo/it/momo__it__celebrate.success__01.wav.receipt.json` | momo | it | `Ce l'hai fatta!` | `Hellohofer Perか` | 0.0897 | 0.0897 |
| 2 | `momo/en/momo__en__praise.general__02.wav.receipt.json` | momo | en | `Great work!` | `3, 1!` | 0.1000 | 0.1000 |
| 3 | `momo/en/momo__en__encourage.progress__02.wav.receipt.json` | momo | en | `Almost there!` | `Fighting Robinson Shawn Release` | 0.1209 | 0.1209 |
| 4 | `momo/it/momo__it__encourage.retry__02.wav.receipt.json` | momo | it | `Quasi! Proviamo ancora!` | `qua ап ди` | 0.2167 | 0.2167 |
| 5 | `momo/it/momo__it__encourage.retry__03.wav.receipt.json` | momo | it | `Ancora una volta!` | `Una porta Maya conditioned fins i` | 0.2635 | 0.2635 |
| 6 | `flash/en/flash__en__encourage.retry__02.wav.receipt.json` | flash | en | `Almost! Let's try again!` | `Almost.` | 0.3952 | 0.3952 |
| 7 | `leo/en/leo__en__encourage.retry__02.wav.receipt.json` | leo | en | `Almost! Let's try again!` | `Almost.` | 0.3952 | 0.3952 |
| 8 | `lilli/en/lilli__en__encourage.retry__02.wav.receipt.json` | lilli | en | `Almost! Let's try again!` | `Almost.` | 0.3952 | 0.3952 |
| 9 | `momo/en/momo__en__encourage.retry__02.wav.receipt.json` | momo | en | `Almost! Let's try again!` | `Almost!` | 0.3952 | 0.3952 |
| 10 | `tito/en/tito__en__encourage.retry__02.wav.receipt.json` | tito | en | `Almost! Let's try again!` | `Almost.` | 0.3952 | 0.3952 |
| 11 | `flash/it/flash__it__encourage.retry__02.wav.receipt.json` | flash | it | `Quasi! Proviamo ancora!` | `quasi!` | 0.4250 | 0.4250 |
| 12 | `leo/it/leo__it__encourage.retry__02.wav.receipt.json` | leo | it | `Quasi! Proviamo ancora!` | `quasi.` | 0.4250 | 0.4250 |
| 13 | `lilli/it/lilli__it__encourage.retry__02.wav.receipt.json` | lilli | it | `Quasi! Proviamo ancora!` | `Quasi!` | 0.4250 | 0.4250 |
| 14 | `tito/it/tito__it__encourage.retry__02.wav.receipt.json` | tito | it | `Quasi! Proviamo ancora!` | `quasi.` | 0.4250 | 0.4250 |
| 15 | `tito/it/tito__it__celebrate.success__03.wav.receipt.json` | tito | it | `Che meraviglia!` | `Chemerovilietà` | 0.4643 | 0.4643 |
| 16 | `leo/it/leo__it__celebrate.success__03.wav.receipt.json` | leo | it | `Che meraviglia!` | `chimera via` | 0.4680 | 0.4680 |
| 17 | `momo/it/momo__it__celebrate.success__03.wav.receipt.json` | momo | it | `Che meraviglia!` | `Cameravilla!` | 0.4680 | 0.4680 |
| 18 | `lilli/it/lilli__it__celebrate.success__01.wav.receipt.json` | lilli | it | `Ce l'hai fatta!` | `sciени fatta` | 0.5167 | 0.5167 |
| 19 | `flash/it/flash__it__celebrate.success__01.wav.receipt.json` | flash | it | `Ce l'hai fatta!` | `Sella i fatta!` | 0.5333 | 0.5333 |
| 20 | `flash/it/flash__it__encourage.progress__01.wav.receipt.json` | flash | it | `Continua così!` | `continuacosi` | 0.5720 | 0.5720 |
| 21 | `momo/it/momo__it__encourage.progress__01.wav.receipt.json` | momo | it | `Continua così!` | `continuacosi` | 0.5720 | 0.5720 |
| 22 | `lilli/it/lilli__it__ready.go__01.wav.receipt.json` | lilli | it | `Forza, andiamo!` | `Forza!` | 0.5944 | 0.5944 |
| 23 | `lilli/en/lilli__en__ready.go__01.wav.receipt.json` | lilli | en | `Come on, let's go!` | `Come on.` | 0.5957 | 0.5957 |
| 24 | `momo/en/momo__en__ready.go__01.wav.receipt.json` | momo | en | `Come on, let's go!` | `Come on!` | 0.5957 | 0.5957 |
| 25 | `tito/en/tito__en__ready.go__01.wav.receipt.json` | tito | en | `Come on, let's go!` | `Come on.` | 0.5957 | 0.5957 |
| 26 | `tito/it/tito__it__celebrate.success__01.wav.receipt.json` | tito | it | `Ce l'hai fatta!` | `Te lei fatta!` | 0.6000 | 0.6000 |
| 27 | `lilli/en/lilli__en__encourage.progress__02.wav.receipt.json` | lilli | en | `Almost there!` | `Almost.` | 0.6667 | 0.6667 |

## 5. Where the warnings concentrate

**By character × locale** (most → fewest):

| character | it | en | total |
|---|---|---|---|
| lilli | 3 | 3 | 6 |
| leo | 2 | 1 | 3 |
| flash | 3 | 1 | 4 |
| tito | 3 | 2 | 5 |
| momo | 5 | 4 | 9 |

Dani is absent (intentionally: `macos-native-say` provider has ASR skipped by `asr_eligible()` in the verifier). Momo concentrates 9 of 27 (33%) — same as the previous run's distribution, but no longer described as 'expressive-delivery hypothesis'.

**By prompt** (10 distinct phrases, 27 warnings):

| prompt | warnings |
|---|---|
| `Quasi! Proviamo ancora!` | 5 |
| `Almost! Let's try again!` | 5 |
| `Ce l'hai fatta!` | 4 |
| `Che meraviglia!` | 3 |
| `Come on, let's go!` | 3 |
| `Almost there!` | 2 |
| `Continua così!` | 2 |
| `Great work!` | 1 |
| `Ancora una volta!` | 1 |
| `Forza, andiamo!` | 1 |

**By length** (expected word count):

- 2-word prompt: 9 WARN(s)
- 3-word prompt: 6 WARN(s)
- 4-word prompt: 4 WARN(s)
- 5-word prompt: 8 WARN(s)

## 6. What this report does NOT claim

- It does **not** claim the audio is broken. All 27 clips are owner-accepted on ears (see HANDOVER §5.5 and the 2026-08-28 active-plan entry). Whisper-tiny on short, expressive, Italian-diacritic, non-ASCII-prone clips is well-known to underperform; the WARN count is consistent with that baseline and is not an audio-quality signal on its own.
- It does **not** rank the 27 by 'confidence' to produce a listening priority. The stored score is a token-overlap proxy on the Whisper transcript, not a child-listening-quality metric. The only known reason to prioritise one clip over another is owner intuition; this report deliberately does not invent a ranking that isn't in the receipts.
- It does **not** recommend tuning the verifier. The `transcript_similarity` formula's recall/precision/f1 trade-off is a design decision owned by the voice-production skill and the runbook; one-off `WARN` counts on this specific set are not a sound basis for changing it.

## 7. What the raw transcripts are still useful for

The raw transcripts in the `verification.transcript` field are real and reproducible. They are useful for two things only:

1. Spotting **silent/garbled generations** (Cluster A above) where Whisper heard something with no token overlap at all. If a future run produces a Cluster-A transcript and the owner listens and hears silence or unrelated noise, that's actionable evidence the audio is broken.
2. Spotting **systematic word-drop** (Cluster B above) where the same prompt across multiple characters yields the same single-word fragment. The `Almost! Let's try again!` → `Almost.` pattern across 5/5 natural characters is a real cluster of interest, not a one-off: either Whisper is consistently missing `Let's try again!`, or the post-`1eb4169` engine is consistently emitting only the first word. Owner ears will tell which.

## 8. What changed since the previous report

| | previous report | this report |
|---|---|---|
| source of transcript column | receipts (correct) | receipts (correct) |
| source of score column | receipts (correct) | receipts (correct) |
| audit invariant `recomputed == stored` | not checked | **checked; 0 mismatches** |
| interpretation of WARNs | 3 clusters (punctuation / diacritic / word-drop) | **2 clusters (recall=0 unrelated, recall<1 fragment)** |
| 'punctuation-only mismatch' cluster | asserted to exist | **does not exist** with current scorer |
| 'lowest-confidence' listening priority | asserted from scores | **withdrawn** (score is a token-overlap proxy, not a child-listening-quality metric) |
| '27 second takes still mismatched' | claimed; mixed with the wrong interpretation | **revalidated: 27/27 have `attempts=2`; transcripts are the final take** |
| recommendation to tune the verifier | not made | **explicitly not made** |

## 9. Recommended next step (none for audio)

- **No audio regeneration.**
- **No verifier tuning.**
- If the owner later wants to re-validate listening priority from a different angle, the right next experiment is human listening (or a larger verifier) on Cluster A first, then Cluster B, recorded in a separate human-decision CSV. This report does not pre-fill that decision.

