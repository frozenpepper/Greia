# Whisper Tiny versus Base — executed comparison, 2026-10-22

## Scope and method

Same 24 saved short target clips, one selected Leo voice, four languages, six
examples per language. Three pause strategies, two generations each; these are
repetitions of one translated phrase, not a diverse corpus. Both manually staged
French target cuts were included unchanged. Every source/target SHA is frozen in
comparison-plan.json. No synthesis, runtime installation or default model change.

Pinned multilingual MLX Base weights/config were downloaded with owner permission:
`mlx-community/whisper-base-mlx` revision
`1e3e249fb8d01c655324bd6841b1deadffd6d04c`; weights 143,724,204 bytes.
Tiny revision `78c52ab98ca87f570bc57ad852e15ef7060f9f76`.
Same prepared Python, explicit locale, temperature 0, no expected-text prompt,
word timestamps on, previous-text conditioning off. One fresh subprocess per
model, serial execution, one excluded warmup each. Model-specific full ASR
responses retained; audio-hash cache prevents repeated recognition of the same
input within a model block. Existing cutter v5 replayed unchanged with injected
model. Source-only measurements are not a claim about concurrent synthesis.

## Identical fixed target clips — primary comparison

| Measurement | Tiny | Base |
|---|---:|---:|
| Score >0.8 | 16/24 | 19/24 |
| Exact normalized target | 13/24 | 16/24 |
| Score >0.8 plus equal target token count | 15/24 | 19/24 |
| Median warm ASR time per target | 0.307 s | 0.408 s |
| Sum of 24 warm target ASR calls | 7.786 s | 10.275 s |
| MLX tracked peak allocation after warmup | 295 MB | 547 MB |

Base warm target ASR is approximately 33% slower here, adding about 0.10 s at
the median. MLX allocation is not total system memory or a guarantee of safe
concurrency with VoxCPM2. Subprocess peak RSS was 354/420 MB (Tiny/Base); do not
sum RSS and MLX allocation on unified memory.

| Language | Tiny score passes | Base score passes |
|---|---:|---:|
| English | 6/6 | 6/6 |
| Italian | 6/6 | 6/6 |
| Spanish | 4/6 | 5/6 |
| French | 0/6 | 2/6 |

Base recovered four score failures and introduced one score regression, for a net
three additional passes. One Spanish exact match became a non-exact score pass.
Thus it is not uniformly better on every file.

## The two troublesome French fixed targets

| Clip | Tiny transcript / score | Base transcript / score |
|---|---|---|
| ellipsis-two-seconds-fr-1 | T'as vu l'eau. / 0.2708 | T'es une chose de plus de temps. / 0.1857 |
| ellipsis-two-seconds-fr-2 | T'ouvre l'hône ! / 0.4160 | Trove Luna / 0.7940 |

Expected: `Trouve Luna.` Both remain below the unchanged >0.8 threshold.

## Automatic cutter replay — secondary comparison

Tiny produced 22/24 cuts; Base 24/24. Cut plus final target score passed 16/24
for Tiny and 18/24 for Base. Cut creation does not equal a quality pass. The
model-specific word timings change the selected cut sample, so this secondary
comparison does not use identical extracted audio between models.

Recognition is sensitive to leading quiet padding: Base transcribed the fixed
manual fr-1 cut as `T'es une chose de plus de temps.`, but its automatically
selected cut of the same raw take as `Trouve l'une.` (0.7052). Both preserve the
original source suffix and differ in quiet padding. This argues for stabilizing
ASR input preparation before assuming every failed score needs new synthesis;
it does not authorize selectively retrying recognizer settings until they pass.

## Decision and limits

Base improves this small matched sample at modest absolute latency/memory cost.
It does not resolve French verification reliably and is not a sufficient sole
fix for autonomous regeneration decisions. Keep the production default unchanged
for this comparison; Base is now cached and selectable for subsequent controlled
work. No threshold relaxation, model escalation, extra voices or human acceptance
was inferred. Benchmark scripts/results are external experimental artifacts, not
new production queue implementation.

Artifacts: comparison-plan.json, summary.json, comparison.csv, per-model
results.json/full ASR responses, extracted WAVs and progress.log in this folder.

External evidence folder: `/Volumes/Test1/Works/Greia-voice-auditions/2026-10-22-whisper-tiny-base-comparison-v1`.
