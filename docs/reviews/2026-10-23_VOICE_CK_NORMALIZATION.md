# Parakeet C/K/CH comparison and saved-run replay

**Scope:** versioned comparison semantics for new Parakeet verification and a
read-only replay of saved transcripts from the existing ten-request diagnostic.
No speech was generated or recognized during this review. No audio, receipt,
master, budget, registration, or historical result was modified.

## Policy

New Parakeet creation paths use
`locale-number-tokens-v3-chck-orthographic`. The comparator first recognizes the
existing locale-specific cardinal and numeric-literal tokens, preserving exact
numeric identity. For remaining lexical tokens, it applies `ch` → `k` first,
then `c` → `k`; `k` remains `k`. Thus C/K and CH/K substitutions compare as
equivalent, including `Oskar`/`Oscar`. It does not delete, add, or reorder words.
The exact submitted phrase and exact recognizer transcript remain stored and
displayed; only comparison tokens are canonicalized. Existing v2 and historical
policies are unchanged. Short candidate extraction and the final packaged-audio
check use the same new policy ID for ordinary requests. A versioned optional
request override lets a registered corpus plan carry its frozen policy
(currently v2) through extraction and final checking; an unset normal request
remains v3. The default request JSON is unchanged when the override is unset.

Hyphens were already treated as lexical separators in v2, so
`Raconte-moi` and `Raconte moi` already compare equally. The saved French result
is still rejected because its exact transcript contains both an extra leading
word and a changed lexical word; punctuation spacing is not the failure.

Focused positive and negative tests cover C/K and CH/K in both directions,
`Oscar`/`Oskar`, hyphen/space, numeric-identity retention, extra/missing words,
and unrelated letters. Historical v2 behavior is explicitly tested unchanged.

## Saved-only replay

Inputs were the ten-request registration
`/Volumes/Test1/Works/Greia-voice-auditions/2026-10-22-rejection-investigation/parakeet-v3-pipeline-10-v1/registered-scope.json`
(SHA-256 `f75db6781a0d2447bf408154901bd71df5cbb5bee90b42ec22dbce303e264266`),
the original saved run results (SHA-256
`769f698beb024e288475992255f4331a126c58546f9617bc6a72bd8df161d97d`), and
the original Takeboard source batch (SHA-256
`0ed73552401018e8ce05b294b65b686b2a599cdb51c1068aa34050a352170493`). The
replay uses saved Parakeet transcripts and saved signal metrics only; it invokes
no recognizer or synthesizer and creates no package or receipt.

| Saved request | Exact expected target | Saved exact transcript(s) | v3 replay |
|---|---|---|---|
| `09-it-tito-it` | `Trova Oskar` | attempt 1 `Trova Oscar.`; attempt 2 `Trowa Oskar!`; attempt 3 `Trova Oscar.` | Attempts 1 and 3 satisfy the text-extraction predicate. Attempt 1 is the earliest eligible candidate. The original v2 request stopped before packaging; there is no final delivered check, so this is **not** an end-to-end pass. |
| `10-fr-lilli-fr` | `Raconte-moi cette image!` | attempts 1–2 produced no candidate; attempt 3 `Là, compte-moi cette image.` | No eligible candidate. The extra `Là` and `compte` versus `raconte` remain mismatches; hyphen/space was already equivalent in v2. |
| `03-en-leo-en` | `Y as Yacht` | candidate transcript `Hasbegurdi as Yat.` (attempt 1); other attempts also lack a qualifying candidate | No eligible candidate; the new orthographic rule does not close the missing/changed words. |
| `04-es-leo-es` | `C de Casa` | saved candidate observations | No eligible candidate under the unchanged count and word constraints. |

The six requests with existing final packaged checks remain passes under the
saved transcript plus their saved signal metrics. This is a comparison replay,
not a new packaged-audio verification or human listening result. Every actual
recording remains unreviewed pending owner listening.

Replay artifact:
`/Volumes/Test1/Works/Greia-voice-auditions/2026-10-22-rejection-investigation/parakeet-v3-pipeline-10-v1/saved-comparison-replay-v3.json`
(SHA-256 `f4d374e1c4fdb6ab092b9d7cbc861a5149f7ac55ce2460ca2ae59177fbde1a3a`).

## Listening batch

A separate 51-recording batch preserves the previous batch and review state.
Its visible EXPECTED WORDS panel shows both the exact submitted synthesis phrase
and the expected retained target. The automated panel displays the exact saved
ASR transcript; raw disposable carriers are labeled `NOT_RUN` because they were
not transcribed. All review states remain unreviewed. Batch validation passed:

`/Volumes/Test1/Works/Greia-voice-auditions/2026-10-22-rejection-investigation/parakeet-v3-pipeline-10-v1/takeboard-listening-fulltext-ck-v1.json`
(SHA-256 `dba47c0bb169c920e0e6b32506b81372f7e278592386e45a0a256eeeb6502f5c`)

Listening page: <http://127.0.0.1:8817/>.

## Verification and boundary

All voice-pattern tests: **225 passed**; VoxStage doctor/provider tests: **21
passed**. `git diff --check` passed. An initial full run (5,827 tests) had 8
failures, 8 errors and 8 skips. Cause review found that the newly selected v3
policy conflicted with frozen v2 automatic/natural corpus plans, the carrier
test fake lacked the new `generate_disposable_carrier` collaborator, and the
VoxStage doctor test still patched the removed `WhisperVerifier` symbol. The
request-level policy pin and test-fixture updates fixed those voice-suite issues;
the frozen plan/receipts remain v2.

Final `make verify` completed **5,827 tests: 1 failure, 3 errors, 8 skipped**;
full gate **NOT GREEN**. Remaining failures are outside this voice change:
`test_all_repository_profiles_are_typed_toml_and_resolve_both_artifacts` (ARM64
builder support), `test_completion_button_writes_the_root_poweroff_marker` and
`test_completion_marker_failure_shows_the_manual_fallback` (macOS has no
`lsblk`), and `test_foreign_plan_non_disk_and_deferred_adapters` (MBR expectation
does not match the registered-plan guard message). Final log:
`/tmp/greia-parakeet-ck-make-verify-final.log`. No unrelated platform issue was
changed.

This policy only changes text comparison for new Parakeet creation. It does not
claim phonetic equivalence outside the stated token rewrite, listening quality,
or end-to-end success for any candidate that lacked final packaged verification.
