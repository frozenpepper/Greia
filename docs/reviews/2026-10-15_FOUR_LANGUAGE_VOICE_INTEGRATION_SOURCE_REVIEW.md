# Greia four-language voice integration — source review (2026-10-15)

## Owner correction — accepted audio is final; use conventional filename fallback

The owner explicitly confirmed on 2026-10-15 that **every committed recording was personally reviewed and APPROVED**. This is the product acceptance authority and supersedes this report's earlier uncertainty about per-clip listening evidence. **Do not recertify, regenerate, reject, relabel or replace already committed audio**. The integration script's permissive behavior remains a **future destructive-replacement safeguard defect**, not evidence that the present recordings are wrong.

The owner proposes a simpler playback policy: obtain a canonical filename from the semantic cue, use the requested locale's file if present, otherwise use the English counterpart, otherwise fail softly. This **is appropriate for ordinary narration, interface labels and shared character speech**. Greia launcher collection labels already do exactly this via `src/greia_launcher/spoken_labels.py:collection_title_audio`. The difficulty exposed by this review is a current *code implementation* constraint: `LocalizedResources.audio_cue()` returns a path only for an explicit per-locale JSON audio-map key; recorded ES/FR voice files cannot be discovered through that method while their `audio` dictionaries are empty. A minimal owner-facing fix is to use existing **English** key→relative-filename mappings as the canonical base, then safely substitute the target language directory and check that file, with an optional explicit exception mapping for truly irregular filenames. This avoids copying hundreds of equivalent locale maps. Keep a strict selected-language/no-English-phoneme policy for letter-name, spelling, rhyme and syllable teaching where fallback would be pedagogically false. Preserve the existing child-language release gate until actual playback behavior is verified.

**Narrow new-recording task:** `docs/testing/2026-10-15_GREIA_TARGETED_MISSING_VOICES_LOCAL_AGENT.md`. It stages **35 candidate slots**: four ES/FR titles in Bottega/Casa; 14 currently absent Submarine audio stems for each ES/FR (28); and three EN/ES/FR alarm-cue recordings required by the real `voice.btn.alarm` gameplay request (IT already recorded). Only missing filenames are generated; existing approved clips are always skipped. Proposed new Submarine scripts must be heard/approved before integrating; no permission to rerun the unsafe integrator or overwrite existing audio.


**Scope:** `frozenpepper/Greia` `main`, baseline `b3edfa6760d91c15d7616440a9e08e81d1eb76b9`, reviewed head `e1ab2426cf1623ce46b000c2e92973033cdf3f64`. Four intervening commits: `69cc834f` (record task results), `a4a81b67` (1,359-cue checkpoint), `6129289e` (native ES/FR pedagogical voices), `e1ab2426` (canonical asset integration).

**Review type:** GitHub source/diff/tree readback; **no** workstation playback, Pygame, hardware, ASR rechecks, unit-test reexecution or owner-listening evidence independently inspected. Do not reinterpret the user's reported blanket audio approval as proof of per-cue validation. Preserve all existing candidate WAV/OGG assets and user decisions.

## What succeeded

- The existing `VoiceEngine` / semantic `VoiceProvider` routing was retained. The native macOS speech profiles now include `es` and `fr`; char-dialogue remains under cloned Chatterbox where used.
- The local-agent log claims 2,329 new generated candidates: 1,277 pedagogical/Dani and 1,052 character/narrator, and reports 192 prior approved v0.2 shared clips reused.
- At reviewed HEAD, an exhaustive nontruncated GitHub tree read returned 11,123 entries; comparison to baseline showed **3,923 added blob paths**, **665 modified blob paths**, no removals. Of these, 1,643 newly added audio paths, **609 *modified existing* audio paths**, 2,279 newly added receipt paths, 52 modified receipts, plus implementation/docs. The integration agent reports 2,331 processed audio/receipt pairs (distinct changed audio paths can be fewer due to byte-identical preexisting paths). The committed repository contains 3,718 total WAV/OGG assets and 2,658 receipt files, including older legacy assets without new receipts. No physically impossible zero/under-200-byte audio files appeared in tree metadata.
- The OS/Activity manifests remain restricted to EN/IT; ES/FR were not prematurely released.

## Findings, in priority order

### P0 — Asset promotion bypasses individual receipt approval and overwrites existing assets

**Source:** `tools/integrate_reviewed_voices.py`, `integrate`.

- Reads all WAV/OGG in review directory with `glob('**/*')`, independent of the authoritative approved ledger.
- Copies every candidate with `shutil.copy2(af, dest)` **unconditionally**. This commit actually changed the blob SHA of **609 existing canonical WAV/OGG paths**. No collision manifest, existing accepted asset hash guard, explicit replacement allowance or rollback journal.
- Rewrites every parseable receipt as `human_review='APPROVED'`, appending one generic owner acceptance note. No comparison to per-row listening decision, expected locale/speaker/cue/script, receipt's recorded output SHA or canonical identity.
- Missing/invalid receipt merely warns, yet audio still installs; return value is always zero. If ledger/progress don't exist it silently skips them; if present, it blindly updates rows with generic `REVIEW_PENDING` state independently of whether an output was copied.
- `compute_destination` derives target from arbitrary `review_dir` components without verifying actual Activity manifest membership, reserved file prefixes, final project confinement or that the file is expected by the runtime.

**Impact:** the promoted tree isn't independently auditable as a set of individually accepted, correct cues. Rerunning the tool could silently replace approved originals. **Recommended:** do not rerun existing integrator. Refactor to manifest/ledger-driven promotion, strict path allowlist/confinement and canonical audio key checks, exact text/speaker/locale and receipt/hash validation, required per-cue acceptance provenance, fail-closed mismatches, collision report and explicit replacement allowlist, dry-run before writes, then a minimal integration test with positive/negative fixture cases. Do **not** regenerate audio by default.

### P1 — ES/FR narrator recordings exist but are unreachable through semantic audio catalogues

**Sources:** `activities/enciclopedia_greia/locales/{es,fr}.json`, `activities/enciclopedia_greia/enciclopedia_audio.py`, `activities/viaggio_delfino/locales/{es,fr}.json`, `activities/viaggio_delfino/delfino_audio.py`, `src/greia_platform/localization.py`.

- The full Git tree contains **199 .ogg/.wav narration assets per ES and FR** under `activities/enciclopedia_greia/assets/audio/{es,fr}/`. However both ES/FR bundles declare `audio={}`, and `EncyclopediaAudio.play` requires `LocalizedResources.audio_cue(cue_id)` to return a registered mapping. Consequently **no ES/FR encyclopedia fact narration can play through the intended path**.
- Dolphin likewise has **seven ES and seven FR narrated voice files**, but both `viaggio_delfino/locales/{es,fr}.json` audio maps are empty; `PygameDelfinoAudio` resolves only by semantic keys.
- `LocalizedResources.audio_cue` defaults to `allow_fallback=True`. Once these locales are enabled, a missing local mapping may result in **wrong-language fallback** to the default source language; selected-locale speech needs an explicit policy.
- The latest integration commit did **not modify any ES/FR locales JSON**. The voice asset import is therefore only an import, not language integration.

**Recommended:** derive/verify maps from existing authoritative EN/IT semantic cue IDs, confirmed ES/FR assets and exact spoken content; add appropriate per-locale `audio` entries for each supported Activity; enforce correct-language/no-cross-locale fallback for pedagogical speech; add tests that load each locale and resolve/decode each expected narrated cue. Keep ES/FR selector disabled until this works.

### P1 — Incomplete speech coverage despite “all 45 Activities” claim

**Source:** exhaustive `main` Git tree plus `activities/*/activity.toml` (exactly **45** direct Activity packages).

- `activities/bottega_delle_misure/locales/{es,fr}/audio/activity-title.wav` and `activities/casa_del_dieci/locales/{es,fr}/audio/activity-title.wav` **do not exist** (four missing expected language/title combinations). Both ES/FR source bundles contain `activity.title` translations.
- Submarine title uses a pre-existing alternative canonical path `activities/sottomarino_giramondo/audio/{en,it}/sub_title.wav` and was verified present. Missing *standard* EN/IT title files there are not themselves proof of an actual missing runtime cue.
- Submarine has 55 English and 56 Italian recordings in `activities/sottomarino_giramondo/audio/`, but only **41** each for ES and FR. Fourteen ES/FR stems absent relative to EN: `btn_action`, `btn_bubbles`, `btn_horn`, `btn_light`, `btn_sonar`, `creature_angler`, `creature_clownfish`, `creature_dolphin`, `creature_manta`, `creature_turtle`, `creature_whale`, `enc_octopus`, `enc_shark`, `enc_solved`. Italian also has a `btn_alarm` cue not in ES/FR. The Submarine `sub_app.py` queues semantic IDs via `resources.audio_cue`; ES/FR audio maps remain empty.
- Completeness of other narration code-owned cues, phonemic correctness and actual runtime trigger/playback remains to be independently tested.

**Recommended:** enumerate exactly 45 direct Activity manifests; enumerate real code-owned or catalogue cue IDs per locale; make a missing-cues table classified missing **script**, missing **file**, existing **unmapped**, existing **accepted**, or intentionally nonverbal. Fill only real gaps and repair wiring before claiming full four-language readiness.

### P2 — Committed receipts expose workstation paths and are not clean release metadata

**Source:** representative new `activities/acquario_magico/locales/es/audio/activity-title.wav.receipt.json` and amended `activities/alfabeto_leo/assets/audio/en/letter_A.wav.receipt.json`.

- The integrator fixes top-level `output.path` but keeps `request.output` as the **absolute local authoring-workstation path**, including username and worktree path.
- 2,331 generated receipts are reported as committed alongside package audio. That duplication should be deliberate, private-path-free and packaged only where allowed; it is not automatically required by runtime.

**Recommended:** move machine-specific paths/evidence to ignored review material, preserve auditable *portable* relative paths, schema-version canonical receipts, and clarify whether receipts are included in installed Activity distribution.

### P2 — Test and queue claims need scoped cleanup

- `HANDOVER.md` reports **29 voice, seven syllable and ten source-localization unit tests** passing, but review could not inspect those original command logs in this connector session or rerun them.
- `docs/testing/GREIA_LOCAL_AGENT_TASK_QUEUE.md` marks GLA-014 PASS and GLA-015 “AUDIO INTEGRATED”, but still retains old “third stage — preparation, NOT actual generation” instructions, old `audio={}` limitations, and GLA-015 “SOURCE COMMITTED, UNEXECUTED” at current HEAD. Preserve the execution history but append a clear split: **candidates produced**, **assets imported**, **per-cue semantic mapping incomplete**, **native listening/visual runtime unverified**. Don't conflate the recording stage with full language release.

## Minimal next work

1. Freeze current audio bytes; run no bulk regeneration or second unsafe promotion.
2. Repair the promotion script and add a small deterministic source test for receipt and destination conflicts.
3. Cross-check source keys ↔ expected path ↔ existing audio for all 45 apps × four locales; add missing ES/FR semantic mappings to all catalogue-driven players (first Encyclopedia, Dolphin, Submarine). Use strict correct-locale playback where appropriate.
4. Close confirmed four missing titles and Submarine's missing/unmapped ES/FR cues with a targeted recording order only when truly necessary.
5. Reconcile the task queue and collect focused headless/playback source tests. Keep language selector staged until the real L6 gate.

**Conclusion:** valuable substantial speech production and assets preserved, but **“all audio integrated and ready in four languages” is not supported by current runtime source**. This review describes source findings rather than rejecting the owner's content approval.
