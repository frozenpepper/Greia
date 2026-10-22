# Paired voice-method tests and number-comparison correction — 2026-10-22

## Authority and scope

The owner stopped bulk generation, then explicitly requested new prompt/code
experiments on a couple of repeatedly rejected targets and word/digit number
recognition across the four languages. Bulk remains **OWNER STOPPED**; its
heartbeat is deleted. No experiment installs audio, resets production budgets,
changes masters, or authorizes a new corpus traversal.

Chosen hard cases: Tito EN **Count to ten**, Leo FR **Trouve Luna**, both rejected
on all three earlier diagnostic takes. Two fixed seeds42/314159 per target and
four recipes produced16 distinct completed diagnostic jobs. Provider job/key,
seed, exact script, actual direction, selected master hash and output hashes
were reconciled; no uncertain job was resubmitted. These are two difficult
examples, not a representative corpus success-rate estimate.

## Experiment and results

First preregistered experiment: identical existing localized intro/target/master
and paired seeds, comparing the old imperative direction against a shorter
warm/calm/clear description with no pause command. Neither wins with corrected
native-source verification. A second preregistered experiment compares direct
speech against a natural, target-relevant carrier, with localized descriptions.
Every run is one take; failures are reported, not retried until they look good.

| Recipe | Native PCM: final machine passes | Canonical22,050Hz replay |
|---|---:|---:|
| Existing language-label intro + imperative pause direction | 0/4 | 1/4 |
| Same intro + concise description | 0/4 | 0/4 |
| Direct target, no carrier | 1/4 | Not an extraction experiment |
| Natural relevant carrier + concise description | 3/4 | 3/4 |

All comparisons above use corrected number policy v2. The first experiment's
original v1 receipt had one machine PASS, recognized as `Client to 10` for
`Count to ten`; corrected scoring rejects it. Its original receipt remains
unchanged; it is not presented as a valid new-policy target pass.

Natural EN script:

```text
Let's practise counting together.

Count to ten
```

EN description: `Warm, calm, clear speech. Careful, natural pronunciation.`
Both seeds pass, recognized as `Count to ten` / `Count to 10`, score1.0,
no signal flags. Measured selected pauses910ms/800ms.

Natural FR script:

```text
Nous cherchons notre amie.

Trouve Luna
```

FR description: `Lecture chaleureuse et calme. Diction claire et naturelle.`
Seed42 passes (score1.0, no flags), measured pause1,620ms. Seed314159 rejects,
recognized as `Trouve le na...`; that rejection remains visible. The experiment
cannot distinguish a pronunciation error from a recognition error by ASR alone.
The FR natural recipe changes both carrier and description language relative to
the first experiment, so do not attribute its improvement solely to either one.
Within the second experiment, direct/natural use the same localized description.

Direct FR seed314159 has an exact transcript but still warns for leading silence;
we did not weaken the existing signal gate. Direct Tito seed42 is unintelligible
to Base. These controls argue against treating direct short generation as a
universal replacement. No new prompt is adopted as the production default yet.
No ellipsis or imperative two-second pause was added to the natural recipes.

## Code correction: number recognition and scoring

`number_lexicon.py` supplies a bounded standard cardinal inventory0–100 for
EN/IT/FR/ES, including French compounds and Italian/Spanish accented forms.
Grammar was cross-checked against the primary num2words language implementations:
[French](https://raw.githubusercontent.com/savoirfairelinux/num2words/master/num2words/lang_FR.py),
[Italian](https://raw.githubusercontent.com/savoirfairelinux/num2words/master/num2words/lang_IT.py),
[Spanish](https://raw.githubusercontent.com/savoirfairelinux/num2words/master/num2words/lang_ES.py).
No third-party package or model was installed; the runtime image is unaffected.

Current comparison policy **locale-number-tokens-v2**:

- Exact cardinal word/digit equivalence, with locale supplied by the request:
  `twenty-six ↔26`, `trentatré ↔33`, `quatre-vingt-onze ↔91`, `treinta y uno ↔31`.
- Digit literals beyond the spelling range retain exact numeric identity too.
  Leading-zero codes, signed/decimal/fraction notation are literal and distinct.
  No homophone correction, fuzzy number spelling or arbitrary joined-word split.
- Accents remain ignored by default, with the existing strict override.
- Comparison-unit count and numeric sequence guards remain; no threshold change.
- Similarity scores use ordinary digits, not verbose internal `<num:...>` labels.
  The old marker increased unrelated text's shared-character score: `Client to
  10` scored.8077 against `Count to ten`; corrected score.742 rejects it.
- V1 interpretation retains its0–25 inventory and old scoring. New target checks
  dispatch by extraction comparison policy; old receipts/reports are not rewritten.

The ordinary WhisperVerifier previously used plain lexical scoring, bypassing
short-route number equivalence. It now uses the shared comparator and hard
numeric identity guard. Live review and saved reassessment likewise share it
under **greia-audio-screen-v4**. Corpus reassessment passes the actual request
locale; old ad-hoc reports without locale are marked `legacy-text-no-locale`
rather than guessing English. The ASR model and prompts are unchanged.

## Saved-audio code experiment and negative controls

`CarrierSourcePreparation` is a focused experimental collaborator over existing
AudioPipeline. It preserves native source bytes and records native/prepared
hashes while preparing22,050Hz mono PCM. It is NOT wired as the default source
recipe. The same12 fresh carrier sources were compared native/canonical, plus
24 older saved sources, for48 extraction evaluations. No further synthesis.

All72 wrong-content/extra-word controls reject. The older saved24 yield23PASS,
1rejection under v2. The held case is `Due lucciole` recognized as `due luciole`;
the corrected scorer no longer gets artificial credit from its numeric marker.
This remains an unresolved possible ASR false rejection, not an accepted audio
label. Do not hide it or call this a fully calibrated verifier.

A separate17-source saved number experiment spans all four languages (EN5,IT3,
ES6,FR3): all17 deliberately wrong-number targets reject;15 actual expected
number targets match,2hold. These are extraction matches, not human acceptance
or proof that every packaged rendition passes. No extra takes were spent.

## Listening comparison and artifact provenance

[Takeboard comparison](http://127.0.0.1:8810/) contains37 rows for16 unique jobs:
complete carrier raws, direct controls, native rejected cuts and final passing
native/canonical renditions. Every row shows exact expected text, actual direction
in generation metadata, seed, actor/locale, ASR transcript/score and the immutable
selected master. Failed cuts are playable; an uncut raw is never labeled target
PASS. Search `natural-carrier` for the promising recipe, clear search to compare.
All human states remain unreviewed. Existing listening pages/saves are unchanged.

Browser verification observed37rows, filtering to11natural-carrier rows, displayed
rejected `Client to10` with score.742, and successful `Count to ten` with score1.
Generated and master players are present; the generated player's control changed
to pause after Play. This proves UI/playback interaction, not listening acceptance.

External evidence root:
`/Volumes/Test1/Works/Greia-voice-auditions/2026-10-22-rejection-investigation/`

- `method-paired-prompts-v1/` and `method-context-v2/`: registered scopes, actual
  results, retained raw receipts, histories, source/cut evidence, provider jobs.
- `method-code-replay-v2/`: fixed source scope, source-preparation hashes, native/
  canonical extraction/checks and negative controls. `number-v2-saved-controls/`:
  actual/wrong-number controls and complete observations.
- `method-comparison.json`, matching independent reviewed output, export script.
- `method-runtime-provenance-audit.json`:16exact jobs; all667 runtime pairs still
  match the stopped production journal's seven pre-stop installations; cumulative
  production reservations remain60 as at stop. No diagnostic runtime installation.

## Verification and continuation boundary

Focused voice148PASS, related Greia voice/corpus53PASS. These include v1 history,
four-language digit/spelling equivalence, wrong values in long sentences,
accent overrides, marker-inflation regression, live verifier and saved review
routing, native/prepared source identity, and cut/transaction tests.

Full `make verify` first aborted with segmentation fault11; the diagnostic rerun
completed5,749tests in263.793s:2failures/3errors/8skips, **NOT GREEN**. Three errors
are ARM64 profile support and two unavailable macOS lsblk cases; the MBR diagnostic
expectation failure remains. A shell retained-surface memory test also failed
(574,308B vs524,288B limit), separately rerun rather than attributed to this voice
change. The memory test passes its isolated rerun (1 test,5.463s); the full-suite
failure remains recorded and is not declared resolved. Full log
`method-make-verify-diagnostic.log`; isolated evidence and final
focused logs remain external. A final one-line change retained historical
Unicode decimal digit handling; focused source tests were rerun after it.

Next: listen to these exact two difficult targets and keep their judgments
separate from ASR findings. Natural carrier is a candidate, not a universal
production solution. Broader hard-case calibration must include number/letter
phrases and the retained `Due lucciole` discrepancy before default adoption or
any bulk restart. No further synthesis/automatic continuation is running.
