# Character and Pedagogical Speech — Local Evaluation Findings

**Date:** 2026-08-23  
**Evidence class:** owner-reported local manual audio evaluation; qualitative, not a benchmark scorecard  
**Disposition:** informs current Greia speech-authoring policy

## 1. Purpose

Preserve the practical findings that changed Greia's voice architecture so future contributors do not repeatedly reopen failed approaches without new evidence.

This record does not invent measurements that were not captured. It records the observed qualitative outcomes reported from local authoring tests.

## 2. MOSS-TTS-Nano

Observed:

- overall synthesis quality was judged unusable for Greia character speech;
- quality was worse than older non-cloning TTS alternatives and, in practical listening, could be worse than native/system TTS;
- small model size and architectural convenience did not compensate for unacceptable output quality.

Disposition:

```text
REJECTED as Greia production character-speech renderer
```

Do not keep MOSS as a silent fallback merely because it is lightweight.

## 3. Chatterbox Multilingual V3 — normal character speech

Observed:

- much higher subjective quality than MOSS-TTS-Nano;
- good enough to remain useful for reviewed canonical character dialogue;
- voice-cloning behavior is materially more suitable for Lilli/Leo/Flash/Tito/Momo normal speech.

Disposition:

```text
ACCEPTED DIRECTION for optional authoring-time character dialogue,
subject to per-line human review
```

## 4. Chatterbox — ultra-short inputs

Problem observed:

- individual letters/syllables and similarly tiny inputs can produce extra sounds/tails;
- output-token limiting plus audio analysis/cutting can successfully remove some unwanted trailing material;
- even after that transport-level problem is controlled, individual syllables remain inconsistent: some are excellent while others are plainly mispronounced or otherwise unsuitable as teaching examples.

Important distinction:

```text
tail/extra generated material = sometimes post-processable
wrong pronunciation itself    = semantic/content failure; not safely post-processable
```

Disposition:

```text
NOT ACCEPTED for pronunciation-authoritative letters/syllables/phonics
```

## 5. Triple-repetition workaround

Tested concept:

```text
ma. ma. ma.
→ detect/cut middle rendition
```

Observed:

- made results materially worse rather than stabilizing them.

Disposition:

```text
REJECTED
```

Do not resurrect this as a standard Greia workaround without genuinely new evidence.

## 6. Architectural conclusion

Greia speech must be separated by semantic job:

```text
character speech
→ Chatterbox, optional authoring-time cloning, human reviewed

pedagogical pronunciation
→ deterministic/native/system TTS where correctness and repeatability outrank character identity

shared generic character feedback
→ small OS-owned prerecorded utterance library

Dani
→ Greia system-TTS robotic profile
```

The governing design rule is:

> If the sound itself is the educational truth being taught, use pedagogical/system speech. If speech communicates content through a character, use character speech.

## 7. Preserved useful tooling result

The audio-analysis/cutting work remains useful even though the triple-repetition experiment failed.

Useful scope:

```text
inspect generated WAV metadata
identify excessive tails/silence
bounded trim of otherwise-correct short character speech
clipping/loudness inspection
package conversion
```

It must not be used to hide or mechanically repair an incorrect pronunciation inside the intended utterance.

FFmpeg/ffprobe remain the preferred cross-platform authoring primitives for this work.

## 8. Documents updated from these findings

```text
docs/design/GREIA_VOICE_GENERATION_AND_CANONICAL_VOICES.md
docs/design/GREIA_SHARED_CHARACTER_UTTERANCES.md
docs/agents/GREIA_LOCAL_VOICE_PRODUCTION_SETUP.md
skills/greia-activity-authoring/SKILL.md
skills/greia-activity-authoring/VOICE_GENERATION.md
SETUP.md
assets/audio/characters/canonical/v0.1/manifest.toml
```
