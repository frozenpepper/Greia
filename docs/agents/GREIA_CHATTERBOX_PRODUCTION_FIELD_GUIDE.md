# Greia — Chatterbox Provider Field Guide

**Retained alternative (2026-10-21):** VoxStage/VoxCPM2 is the default character provider. This guide applies only when explicitly selecting `--character-provider chatterbox` or its environment equivalent. The active reference set is v0.3: Dani/Momo/Tito use their selected v3 references and Lilli/Leo/Flash retain their exact v2 references. Keep the Chatterbox mechanisms below; unload VoxStage before loading this alternative model on the same host.

**Status:** Voice Production Engine maintainer/troubleshooting reference  
**Reviewed:** 2026-08-28  
**Target provider:** Apple-Silicon MLX `mlx-community/chatterbox-multilingual-v3`

## Important boundary

Ordinary Activity, OS/shared-library and Encyclopedia agents should **not use this document as their production runbook**.

Canonical production is:

```text
skills/greia-voice-production/SKILL.md
tools/greia_voice_core/README.md
tools/greia_voice.py
```

This file preserves low-level provider lessons for maintainers of:

```text
tools/greia_voice_core/providers.py
```

If a caller-facing document says to invoke `mlx_audio`, Chatterbox, `mlx_whisper`, FFmpeg trimming or canonical reference files directly, that operational instruction is obsolete. Fix the caller to use `VoiceEngine` instead.

## 1. Provider role

When explicitly selected, Chatterbox implements canonical cloned-character speech:

```text
Lilli
Leo
Flash
Tito
Momo
Dani
```

It is not pronunciation authority for letters/syllables/phonics; those retain the independent native/system provider. Dani now has a reviewed v0.3 cloned reference and can use this explicit alternative.

No Chatterbox model or dependency is shipped to the child device.

## 2. Tested Apple-Silicon dependency set

Canonical declaration:

```text
tools/greia_voice_requirements_mlx.txt
```

Current tested pins:

```text
mlx-audio==0.5.0
mlx==0.32.1
soundfile==0.14.0
sentencepiece==0.2.2
mlx-whisper==0.4.3
```

Installation belongs to:

```text
tools/greia_voice_core/README.md
docs/agents/GREIA_LOCAL_VOICE_PRODUCTION_SETUP.md
```

Do not duplicate install recipes into Activity runbooks.

## 3. Resource lifecycle

A single model can consume several GB of Apple-Silicon unified memory. The engine therefore owns these mandatory invariants:

```text
one local inference worker
lazy model load
model reuse for batch/service requests
cross-process generation lock
mx.clear_cache() after each take
gc.collect() after each take
explicit close/cleanup
```

Do not add per-clip subprocess generation or parallel Chatterbox workers.

The daemon/batch path holds the global lock for its lifetime so a second process cannot load another model while the first remains warm.

## 4. Canonical reference integrity

Voice identity is source-controlled by:

```text
assets/audio/characters/canonical/v0.3/manifest.toml
```

`VoiceRegistry.verify_anchor()` validates the reference SHA-256 before cloned generation.

Never bypass or rewrite a hash locally to make production continue.

## 5. Chatterbox output-length policy

**Do not derive Chatterbox acoustic-token limits from source word count.**

An earlier workaround used small `max_new_tokens` values for very short prompts because Chatterbox had been explored for isolated letters/syllables. That workaround was later inherited by ordinary character/shared speech and caused real words and phrases to be cut off mid-word.

That policy is retired.

Current Greia rule:

```text
character_dialogue / shared_character_utterance
    -> do not pass a Greia word-count-derived max_new_tokens override
    -> let the Chatterbox backend use its normal generation stopping policy

pedagogical letters / syllables / phonics
    -> do not use Chatterbox
    -> route through pedagogical_speech / deterministic native-system provider
```

Do not replace the removed 45/65-token table with a different guessed table. If Chatterbox output-length behavior needs future tuning, diagnose the backend behavior directly and justify the change with real generated evidence.

The rejected triple-prompt workaround (`ma. ma. ma.` followed by middle extraction) remains rejected.

## 6. Waveform trimming lesson

The provider may trim **outer leading/trailing inactivity only**. It must preserve every internal pause and low-energy region between the first and last detected speech activity.

A previous special path for lines of four words or fewer stopped at the first inactive gap of roughly 120 ms. That was incorrect: normal pauses, breaths and low-energy consonants could be interpreted as the end of the utterance, deterministically cutting otherwise complete Chatterbox output. That internal-island truncation is retired.

Trimming may remove unwanted material outside the intended utterance. It may not repair:

```text
wrong pronunciation
invented/repeated word inside the phrase
voice identity drift
wrong language
```

Those require regeneration/rejection.

## 7. Historical Whisper verifier (not the current default)

This section describes historical Chatterbox/Whisper receipts, **not** the
current `VoiceEngine` verifier. New generation requests now use the pinned
multilingual Parakeet-TDT v3 provider behind `SpeechVerifier` as documented
in `tools/greia_voice_core/asr_policy.py`. Old Whisper Tiny/Base evidence
must remain attributed to its actual model rather than relabeled Parakeet.

When deliberately replaying an old Whisper task, the requested language is
passed explicitly.

Suitable multi-word character/shared-library lines may be checked. Tiny one-word reactions and pedagogical speech normally skip ASR.

Whisper PASS is never human acceptance.

A Whisper `WARN` is nevertheless actionable production evidence: the engine retries within the request's bounded attempt count. If the final attempt still warns, the audio and receipt are preserved for inspection, but shared-library production treats that row as unresolved rather than counting it as a clean candidate.

## 8. Troubleshooting sequence

Always start through the public probe:

```bash
python3 tools/greia_voice.py doctor
```

Only descend into provider internals if `doctor` reports a Chatterbox-specific failure.

Useful maintainer checks:

```bash
python -c 'import mlx; import mlx_audio; import soundfile; print("MLX stack imports")'
python -c 'import mlx_whisper; print("Whisper imports")'
ffmpeg -version
ffprobe -version
```

Check for a live Greia voice service before launching direct diagnostic code. Do not contend with the engine's generation lock or keep a second model resident.

## 9. Acceptance boundary

Even when a provider bug is fixed and generation succeeds, output remains:

```text
human_review = PENDING
```

Provider diagnostics can prove transport/model mechanics, not character-quality acceptance.

Human review remains responsible for exact words, language, voice identity, pronunciation, clipping/tails, delivery and small-speaker suitability.

## 10. Extension rule

If Chatterbox is replaced or complemented, implement another `VoiceProvider` behind `VoiceEngine`.

Do not require Activity/Encyclopedia/shared-library callers to learn a new model name, Python package or lifecycle rule.
