# Parakeet v3 voice pipeline: bounded ten-request diagnostic

**Date:** 2026-10-23
**Scope:** public `VoiceEngine.generate` path; ten preregistered short cues; no
runtime installation, corpus-budget mutation, master change, model download,
model reroll outside these requests, or human acceptance.

## Result

The new-request recognizer is pinned local multilingual Parakeet-TDT v3:
`mlx-community/parakeet-tdt-0.6b-v3`, revision
`ed2b7e8c15f9aaa0b5772e2efb986255eaef7e15`. With unchanged numeric/count/score/
signal guards, the full short carrier → candidate-cut → delivered-package path
produced **6 machine-verified packages and 4 rejected requests** after **21 actual
provider jobs**. Each request stopped at first automated pass or its three-try
limit. All passing audio is still `human_review=PENDING`; Parakeet is not a human
pronunciation, identity or delivery judgment.

The previous natural-carrier recipe was supplied through an explicit diagnostic
policy injection to compare with the earlier working recipe. It is **not** a new
production prompt default. No contextual saved-source fallback, Oscar/Oskar
exception, threshold change, aliases, or alternate comparison policy was used.
The public `verification=off` remains an explicit unverified opt-out. Historical
Whisper reports/receipts remain identified as Whisper and are not reinterpreted.

## Frozen registration and evidence

External run directory:

`/Volumes/Test1/Works/Greia-voice-auditions/2026-10-22-rejection-investigation/parakeet-v3-pipeline-10-v1/`

Registration: `registered-scope.json`, SHA-256
`f75db6781a0d2447bf408154901bd71df5cbb5bee90b42ec22dbce303e264266`.
The registration pins ten distinct cues from all four released locales, selected
masters and their hashes, request text/prefix/delivery, number policy
`locale-number-tokens-v2`, model/revision, implementation/runner source hashes,
seeds, timeouts, and one-to-three attempt rule. `progress.json` reports COMPLETE,
10 requests and 21 jobs. `results.json`, per-case evidence directories, target
WAVs and sibling receipts retain job IDs/idempotency keys/raw hashes and actual
Parakeet observations.

| # | Cue | Attempts | Automated result | Evidence summary |
|---|---|---:|---|---|
| 1 | EN Tito — “Count to ten” | 1 | PASS | “Count to ten.”; delivered WAV checked |
| 2 | FR Leo — “Trouve Luna” | 1 | PASS | “Trouve Luna.”; delivered WAV checked |
| 3 | EN Leo — “Y as Yacht” | 3 | REJECT | Recognition unstable across takes; no delivered package accepted |
| 4 | ES Leo — “C de Casa” | 3 | REJECT | Candidate cutter had zero candidates once and nine (> fixed cap six) once; remaining try transcript mismatched |
| 5 | FR Leo — “D comme Dinosaure” | 2 | PASS | “D comme dinosaur”; score 0.8636, guards clear |
| 6 | IT Leo — “Dov'è la lettera K?” | 2 | PASS | Exact recognized target; guards clear |
| 7 | FR Momo — “Deux lucioles!” | 2 | PASS | “Deux lucioles.”; guards clear |
| 8 | ES Tito — “¡Llegaste al pícnic!” | 1 | PASS | “¿Llegaste al picnic?”; accents/punctuation comparison policy accepted; guards clear |
| 9 | IT Tito — “Trova Oskar” | 3 | REJECT | Recognizer alternated “Oscar”/“Oskar”; exact numeric/lexical gates unchanged, no later name exception |
| 10 | FR Lilli — “Raconte-moi cette image!” | 3 | REJECT | Two takes lacked usable candidate suffixes; final transcript substituted initial wording |

REJECT describes an automated gate result, not proof that the spoken content is
wrong. Recognition uncertainty and cutter-cap failures are not equivalent to
speech errors. Listening is required to decide whether any take is actually
suitable.

## Listening handoff

Takeboard manifest:
`/Volumes/Test1/Works/Greia-voice-auditions/2026-10-22-rejection-investigation/parakeet-v3-pipeline-10-v1/takeboard-listening.json`
SHA-256 `0ed73552401018e8ce05b294b65b686b2a599cdb51c1068aa34050a352170493`.
`takeboard check` reports 51 recordings: all 21 raw attempts, 24 materialized
candidate cuts, and 6 automated-pass final packages. Every item is unreviewed;
no decisions were imported or promoted. Local desk: <http://127.0.0.1:8816/>.

Recommended order: compare each passing final with its raw/cut siblings first,
then listen to rejected raw/candidate evidence to distinguish a bad take from ASR
or cutter uncertainty. Do not install or mark accepted from machine results.

## Source verification and limitations

The focused voice/pipeline/policy suite passed **85 tests** in the prepared voice
Python environment. Full local `make verify` ended in test stage `Abort trap: 6`;
see `/tmp/greia-parakeet-pipeline-make-verify.log`. The full repository gate is
**NOT GREEN** and no remediation phase is closed. No runtime/device/release proof
is claimed. `VoiceEngine` remains a sizable coordinator (~500 lines); this change
added focused adapter/evidence collaborators and did not attempt a broad refactor.

The frozen problematic-corpus run remains held. This ten-request experiment does
not establish corpus yield or authorize bulk continuation.
