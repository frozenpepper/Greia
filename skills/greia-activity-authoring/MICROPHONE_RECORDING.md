# Microphone and Voice Recording in Greia Activities

**Status:** living derived Activity-authoring companion  
**Reviewed:** 2026-10-30  
**Architecture authority:** `docs/adr/0031-platform-owned-microphone-processing.md`  
**Current implementation/evidence:** `docs/architecture/GREIA_AUDIO_SERVICE.md`, `docs/testing/2026-08-23_ACER_MICROPHONE_PROCESSING_ACCEPTANCE.md`

This companion is about **child microphone input / voice recording**. It is not the custom character-voice production guide. For generated Greia character speech, use `VOICE_GENERATION.md`.

## 1. Treat microphone recording as an available Greia capability

Greia has a platform-owned microphone path. On the reference Acer, the default lightweight cleanup route has been physically accepted and is deliberately cheap/on-demand.

Activity authors should therefore **actively consider microphone/voice recording when it would make the Activity more expressive, playful or educational** instead of avoiding it merely because low-end laptop microphones are noisy.

Good candidates include:

```text
storytelling / puppet narration
pretend play and role-play
child-created voice notes or captions
language speaking/practice where playback is useful
call-and-response games
animal/environment sound imitation
creative audio diaries
record-and-replay experimentation
```

Do not add recording as decoration. It should give the child a meaningful action, creation, reflection or feedback loop.

Microphone use should normally remain optional unless the Activity's explicit product purpose fundamentally depends on it. A child who does not want to record should not be trapped in a dead end merely because the feature exists.

## 2. Default authoring assumption

For ordinary child speech/voice recording, assume:

```text
physical microphone
  -> Greia platform-owned route
  -> lightweight cleanup by default
  -> Activity with audio.basic
```

The Activity does **not** choose the denoiser, ALSA card, codec, microphone brand or physical device.

The default platform policy is:

```text
microphone processing: ON
mode: lightweight when available
advanced processing: OFF unless a parent explicitly enables an available backend
```

There is no automatic CPU/model/hardware selection policy.

## 3. Manifest contract

An Activity that needs microphone capture declares `audio.basic` through the normal capability contract.

Current first-party example:

```toml
[requirements]
required_capabilities = ["display", "pointer", "audio.basic"]
```

If microphone recording is optional to the Activity rather than required for its core experience, use the manifest's normal optional-capability semantics where appropriate and design a real no-microphone fallback.

Do not request microphone authority for an Activity that never records.

## 4. Runtime API — never pick hardware yourself

Use Greia's Activity SDK.

For capture libraries that can open the semantic endpoint directly:

```python
from greia_platform.activity_api import get_audio_capture_device

capture_device = get_audio_capture_device()
```

For SDL/Pygame capture:

```python
from greia_platform.activity_api import get_sdl_capture_device

capture_device = get_sdl_capture_device()
```

`get_sdl_capture_device()` exists because SDL cannot reliably open an arbitrary ALSA PCM name. Greia composes the Activity's ALSA view and the SDK designates the SDL-visible device carrying the selected platform route.

Rules:

- never use `get_audio_device_names(True)[0]` as production device policy;
- never hard-code `hw:0,0`, `plughw`, codec names or Acer-specific card identifiers;
- never read `/dev/snd` to choose a device;
- never instantiate Activity-local Speex/RNNoise/noise-gate processing to replace Greia's route;
- never read the `GREIA_AUDIO_*` environment variables directly when an SDK accessor exists.

`None` from the SDK means use the runtime's ordinary development/simulator fallback where documented; it is not permission to invent production hardware selection.

## 5. Processing is intentionally transparent to ordinary Activities

For normal voice capture, the Activity should not branch gameplay around whether the effective route is `lightweight`, `advanced` or `off`.

The descriptive helper exists for diagnostics/presentation only:

```python
from greia_platform.activity_api import get_audio_processing_mode
```

Do not make score, difficulty, educational truth or child progression depend on a particular DSP mode.

A backend may be unavailable. Greia then falls back honestly to raw capture rather than faking readiness. The Activity should remain usable if recording quality is less ideal.

## 6. Encourage recording where it genuinely improves the experience

During new-Activity design, explicitly ask:

```text
Would hearing their own voice make this more creative or fun?
Would recording let a pre-reader express something without typing?
Would replay help the child notice, compare, remember or tell a story?
Could a character invite the child to narrate, imitate, answer or invent?
Can the result become a child-owned creation worth saving?
```

Examples of good integration:

- a story Activity lets the child narrate a scene and replay the whole story;
- a nature Activity lets the child imitate an animal call and listen back;
- a language Activity lets the child record a phrase and compare/replay it without pretending Greia can grade pronunciation unless a real scoring system exists;
- a pretend-radio Activity lets the child record a short weather/news segment;
- a drawing Activity may optionally attach a spoken explanation to a picture if that genuinely enriches creation.

Examples of weak integration:

- requiring a spoken answer when tapping/selecting would be simpler;
- recording the child continuously without a clear child action;
- saving ambient microphone audio the child did not intentionally create;
- adding speech recognition claims when the Activity only has audio capture.

## 7. Pre-reader UX

Microphone recording can be especially valuable for children who cannot yet read or type fluently.

Use a simple visual recording grammar:

```text
large microphone button -> start
clear active recording state -> recording
large stop button -> stop
obvious play button -> hear it back
clear delete/re-record affordance -> try again
```

Prefer visual state, animation and short reviewed speech cues over textual instructions.

Do not auto-record on Activity launch. The child should perform an obvious action that starts capture.

Give immediate feedback that recording has begun, such as a simple waveform/level animation or clear recording indicator, but keep it lightweight on the Acer floor.

## 8. Child recordings are child-created data

If recordings are saved:

- store them through approved Greia profile-scoped Activity storage;
- keep them offline/local under normal Greia product behavior;
- make retention purposeful and bounded;
- provide a child/parent-appropriate way to replace/delete recordings where the Activity exposes a library;
- do not put recordings in package assets, logs, repository evidence or global platform state;
- do not upload voice recordings to a cloud service merely to implement an otherwise-local Activity.

Temporary capture buffers should be released when no longer needed.

Do not retain incidental microphone audio that is not part of an intentional child creation.

## 9. How microphone processing is disabled

### Parent/product control

Greia Parents owns the processing preference.

The normal parent-facing control is:

```text
Improve microphone sound: ON / OFF
```

Turning it OFF sets the typed audio preference equivalent to:

```text
microphone_processing_enabled = false
```

The change applies on the **next microphone open**. Close/reopen the recording session or Activity when testing the change.

Restore defaults returns to lightweight processing ON and advanced processing OFF.

### Activity code must not disable the parent's policy

An ordinary Activity **cannot and must not silently turn Greia's processing off**.

Do not bypass the platform route by opening the physical card because an author believes raw input might sound better.

If the Activity merely wants a local "microphone off" option, stop/avoid capture inside the Activity. That is different from changing Greia's denoising policy.

### If an Activity genuinely requires raw/unprocessed signal

Some future activities may have a legitimate signal-analysis requirement where noise suppression changes the phenomenon being measured, for example precise pitch/timbre/acoustic experiments.

The current Activity contract does not provide a per-Activity raw-processing override.

In that case:

1. record the requirement explicitly in the Activity design;
2. do **not** open ALSA hardware directly;
3. do **not** mutate Parent audio settings;
4. raise a platform/API design change for a typed raw-capture purpose/route if the requirement is accepted;
5. until that exists, classify the feature as unsupported rather than bypassing Greia authority.

For owner/developer A/B diagnostics, use the Parent setting/API to turn processing off and reopen the microphone. Diagnostic convenience is not an Activity permission.

## 10. Advanced processing

The advanced backend is optional.

Activity authors must never require it merely because the API can describe it.

Current reference-Acer acceptance intentionally has:

```text
available.advanced = false
```

That is a correct supported state.

If a future device exposes an advanced backend, only a parent explicitly enables it. The Activity still uses the same SDK route and does not change its code.

## 11. Recording quality and gain

Greia's microphone processing and microphone gain are separate concerns.

Do not add Activity-local AGC merely because a recording is quiet. The platform already has a bounded parent-facing microphone gain path.

If recordings clip, distort or remain too quiet on a physical device, diagnose the platform/hardware gain state rather than hiding it with Activity DSP.

The accepted reference Acer required sane capture-gain tuning during physical acceptance; that hardware fact is not a universal Activity constant.

## 12. Testing requirements for microphone Activities

Source/unit testing is not enough.

At minimum verify:

```text
Activity has the correct audio.basic capability
SDK capture route is used
no physical-device enumeration policy remains
record start/stop works
recorded data is non-empty when hardware is available
replay works if the Activity promises replay
microphone can be reacquired after stop/exit
no-microphone/fallback behavior is understandable
Activity returns cleanly to Shell
```

For Simulator acceptance, follow `LAUNCH_ACCEPTANCE.md` but do not claim physical microphone/DSP evidence from simulator results.

For a physical microphone claim, name the hardware and exact source state.

When changing the platform audio route itself, switch to `skills/greia-os-work/SKILL.md` and the ADR/audio-service/physical-acceptance authorities.

## 13. New-Activity design checklist addition

For every new Activity, explicitly record:

```text
microphone/voice-recording decision:
  useful and included / considered but unnecessary / intentionally excluded

if included:
  required or optional capability
  child action that begins recording
  playback/re-record/delete behavior
  saved-data policy
  no-microphone fallback
  why processed ordinary voice is appropriate
```

The default design question is no longer "can this cheap laptop handle voice recording?" Greia owns a lightweight cleaned microphone path precisely so Activity authors can use voice creatively when it makes sense.
