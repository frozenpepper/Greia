# Greia Audio Service

**Status:** implemented; physically accepted on the reference Acer (2026-08-24)  
**Architecture authority:** `docs/adr/0031-platform-owned-microphone-processing.md`  
**Physical acceptance:** `docs/testing/2026-08-23_ACER_MICROPHONE_PROCESSING_ACCEPTANCE.md`  
**Physical evidence review:** `2026-08-24_ACER_MICROPHONE_PHYSICAL_ACCEPTANCE.md` (archived; see git history)

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

### SDL runtime composition (implemented, Acer-accepted)

SDL 2.26 cannot open arbitrary ALSA PCM names, so for routed `audio.basic`
launches the launcher additionally injects `ALSA_CONFIG_PATH` pointing at
`runtime/alsa/greia-activity-capture.conf`. That composition (hooks:
system alsa.conf, then Greia overrides) hides raw `hw:` enumeration hints and
resolves `default`/`sysdefault` to a routed asymmetric PCM — capture through
the `greia_denoise` ExtPlug (SpeexDSP at an in-spec 24 kHz via FIR
decimation, AGC off, conservative suppression), playback through the stock
dmix chain. Processing-off launches receive no injection and keep the raw
system view. The physical slave identity lives only in Greia-owned
composition files.

## Activity contract

An Activity that needs microphone capture declares `audio.basic` through the normal manifest/capability path.

Python Activities obtain the selected endpoint through:

```python
from greia_platform.activity_api import get_audio_capture_device

capture_device = get_audio_capture_device()
```

SDL/pygame Activities must additionally obtain the SDL-openable device
designation, because SDL cannot open arbitrary ALSA PCM names:

```python
from greia_platform.activity_api import get_sdl_capture_device

sdl_device = get_sdl_capture_device()
```

`get_sdl_capture_device()` returns the platform-designated SDL-enumerated
capture device when a production route was injected, and `None` in
development/simulator contexts (where the Activity may use its normal SDL
default/enumeration fallback). Activities must never enumerate and choose
hardware themselves on Greia; the selection inside the SDK is the
platform's route decision, not an Activity choice.

For SDL/Pygame, open `get_sdl_capture_device()`; for other capture APIs,
open `get_audio_capture_device()`. Do not choose `get_audio_device_names(True)[0]`.

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
- launcher route injection for `audio.basic` (route environment plus the
  SDL ALSA composition for non-off modes);
- Activity SDK route accessors including the SDL device designation;
- Parent HTML controls in their source repository;
- focused source tests.

Physically accepted on the reference Acer (2026-08-24, see
`2026-08-24_ACER_MICROPHONE_PHYSICAL_ACCEPTANCE.md` (archived; see git history)):

- `greia_mic_light` implemented as an in-process ALSA ExtPlug
  (SpeexDSP denoise at in-spec 24 kHz, on-demand, no daemon);
- boot-probe readiness marker lifecycle (survives reboot honestly);
- live route proof during real launcher-driven Teatrino recording;
- measured −19.9 dB stationary noise-floor reduction with voice band
  preserved, ~5–10% of one core, +0.4 MB RSS, zero glitches;
- Parent controls (default/off/restore/reboot persistence) verified;
- advanced endpoint intentionally absent (`available.advanced = false`).

Still open:

- image-build integration: compiling `src/greia_platform/audio_alsa/` into
  future i686 images (dev machine currently carries a manually installed
  build; images without it honestly fall back to raw);
- advanced endpoint remains intentionally unevaluated on this hardware.

That separation is intentional: Greia reports raw fallback until a real processor endpoint exists rather than faking feature readiness.
