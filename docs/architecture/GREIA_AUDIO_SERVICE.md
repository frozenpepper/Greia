# Greia Audio Service

**Status:** implemented semantic service; Acer DSP backend pending physical acceptance  
**Architecture authority:** `docs/adr/0031-platform-owned-microphone-processing.md`  
**Physical acceptance:** `docs/testing/2026-08-23_ACER_MICROPHONE_PROCESSING_ACCEPTANCE.md`

## Purpose

Greia owns microphone routing so every Activity receives the same Parent-controlled capture policy without learning Linux card names or reimplementing denoising.

The current contract is deliberately narrow. It does not attempt to become a desktop sound server.

## Runtime flow

```text
physical capture device
        │
        ├──────── raw/default ───────────────────────────────┐
        │                                                    │
        └─ Greia backend ── greia_mic_light                  │
                          └─ greia_mic_advanced (optional)   │
                                                             │
Parent desired state ──> AudioService ──> effective route ───┘
                                      │
                                      └─ launch context for audio.basic Activity
```

The semantic service never benchmarks the machine and never promotes processing automatically.

## Source ownership

```text
src/greia_platform/audio.py
    AudioSettingsStore
    AudioService
    AudioProcessingBackend protocol
    AlsaAudioProcessingBackend
    effective route + truthful fallback

runtime/audio-settings.toml
    canonical defaults

src/greia_launcher/child_shell.py
    injects the resolved route only for a launch granted audio.basic

src/greia_platform/activity_api.py
    get_audio_capture_device()
    get_audio_processing_mode()

src/greia_parent/update_api.py
    authenticated Parent GET/PUT/reset settings surface

src/greia_parent/protocol.py
    versioned audio settings resources/capability

runtime/parent-app-client.toml
runtime/parent-app-client.manifest.json
    exact external Parent HTML client pin/integrity boundary
```

## Settings model

Canonical defaults:

```text
microphone_processing_enabled = true
advanced_noise_reduction = false
```

The two values are independent. A parent can therefore preserve the advanced preference while temporarily disabling all processing; when processing is re-enabled, the effective route is resolved again against current backend availability.

`AudioService.payload()` intentionally separates:

```text
desired   what the parent selected
effective what Greia can actually route right now
available which concrete endpoints currently exist
backend   implementation family
```

This prevents the Parent client from equating a stored preference with hardware truth.

## Effective-route rules

```text
processing OFF
    -> raw/default

processing ON, advanced OFF, lightweight available
    -> lightweight

processing ON, advanced OFF, lightweight unavailable
    -> raw/default + lightweight_unavailable

processing ON, advanced ON, advanced available
    -> advanced

stored advanced ON, advanced disappears, lightweight available
    -> lightweight + advanced_unavailable
```

A new Parent PUT that tries to enable advanced while it is unavailable is rejected.

## ALSA adapter boundary

The initial Linux adapter uses stable logical names:

```text
default
greia_mic_light
greia_mic_advanced
```

Readiness is provisionally signaled under `/run/greia-audio/`. This is deliberately a small adapter seam: the public API does not care whether a later backend uses an ALSA plugin, another native audio API or a different service.

Do not persist readiness markers. They must represent current boot/runtime truth.

## Activity contract

An Activity that needs microphone capture declares `audio.basic` through the normal manifest/capability path.

Python Activities obtain the selected endpoint through:

```python
from greia_platform.activity_api import get_audio_capture_device

capture_device = get_audio_capture_device()
```

For SDL/Pygame, pass `capture_device` to the capture-device opening API. When `None`, use SDL's default capture endpoint. Do not choose `get_audio_device_names(True)[0]`.

`get_audio_processing_mode()` exists for narrow presentation/diagnostics only. Activities must not branch educational/game behavior around a particular DSP implementation.

## Parent contract

```text
GET  /api/v1/settings/audio
PUT  /api/v1/settings/audio
POST /api/v1/settings/audio/reset
```

The Parent HTML UI presents:

- **Improve microphone sound** — normal default, lightweight path;
- **Enhanced noise reduction** — only when `available.advanced` is true;
- effective status/fallback information;
- restore defaults.

Advanced processing remains explicit Parent opt-in. The UI must never imply it was automatically chosen.

## Resource policy

The first Acer path should prefer a real voice denoiser with extremely small runtime cost. SpeexDSP preprocessor is the preferred first physical candidate because it is voice-specific and tiny on Debian i386. A cheaper gate/high-pass chain may be measured, but only qualifies as the default if it produces useful in-speech cleanup rather than merely muting silent gaps.

The advanced endpoint is optional and may remain absent on C0/Acer hardware.

No DSP package becomes part of the reference image until the physical protocol measures its cost and quality.

## Current evidence status

Implemented/source-visible:

- typed service and settings store;
- lightweight-default/no-auto-promotion policy;
- advanced availability and explicit Parent selection;
- Parent API resources;
- launcher route injection for `audio.basic`;
- Activity SDK route accessors;
- Parent HTML controls in its source repository;
- focused source tests.

Still requires physical proof before being called complete on Acer:

- exact built-in capture device;
- implementation of `greia_mic_light`;
- readiness-marker lifecycle;
- first-party Activity migration where raw enumeration remains;
- A/B denoising quality;
- CPU/RAM/latency/dropout measurements;
- optional advanced endpoint decision;
- Parent HTML exact-revision repin/integrity update if not already current at test time.

That separation is intentional: Greia reports raw fallback until a real processor endpoint exists rather than faking feature readiness.
