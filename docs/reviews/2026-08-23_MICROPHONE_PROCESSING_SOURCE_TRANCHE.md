# Microphone-processing source tranche review — 2026-08-23

**Disposition:** SOURCE IMPLEMENTED / PHYSICAL BACKEND UNPROVEN  
**Architecture:** `docs/adr/0031-platform-owned-microphone-processing.md`  
**Physical protocol:** `docs/testing/2026-08-23_ACER_MICROPHONE_PROCESSING_ACCEPTANCE.md`

## Owner decision captured

Greia does not automatically choose a microphone processor.

The stable product policy is:

```text
lightweight cleanup desired by default
advanced cleanup OFF by default
parent may disable cleanup
parent may explicitly enable advanced only when a real advanced endpoint exists
```

No CPU benchmark, device-model table, current-load heuristic or silent promotion is part of the contract.

## Implemented Greia source boundary

The tranche adds a typed Audio Service without turning Greia into a desktop audio stack:

```text
src/greia_platform/audio.py
runtime/audio-settings.toml
src/greia_parent/protocol.py
src/greia_parent/update_api.py
src/greia_launcher/child_shell.py
src/greia_platform/activity_api.py
```

The service separates Parent desired state from backend availability and effective routing. It uses stable semantic ALSA endpoint names:

```text
default
greia_mic_light
greia_mic_advanced
```

Readiness is fail-closed. Without a genuine current-boot processor endpoint, Greia reports raw fallback rather than claiming cleanup is active.

Only Activities granted `audio.basic` receive the selected route. The Activity SDK exposes `get_audio_capture_device()` so Activities no longer need to select host microphones themselves.

## Parent API and client

The top-level Parent API now exposes capability-gated typed resources:

```text
GET  /api/v1/settings/audio
PUT  /api/v1/settings/audio
POST /api/v1/settings/audio/reset
```

The separate Parent HTML source repository contains a newer reviewed-source candidate at:

```text
frozenpepper/Greia-Parent-App-Html@cdea281a1848d1372a18822a559dc15494e749b0
```

It adds the `Microphone cleanup` card, lightweight default control, effective status and an enhanced-processing checkbox only when the Greia API reports an advanced endpoint.

The Greia runtime pin intentionally remains at the previously verified Parent revision `7ff7e318eb246618dab26939ba086999864538ce` until the newer candidate executes its local tests/syntax/visual review and Greia regenerates the exact integrity manifest.

`tools/update_parent_client_pin.py` now provides the deterministic clean-checkout repin path and refuses dirty or revision-mismatched Parent trees.

## Tests authored in this tranche

```text
tests/test_audio_service.py
tests/test_parent_audio_api.py
tests/test_activity_audio_api.py
tests/test_parent_client_pin_tool.py
```

The Parent source repository also adds:

```text
tests/audio_processing.test.js
```

These tests are **authored but no current-head PASS is claimed from the remote GitHub-edit environment**. They must execute in the owner-controlled local checkout before source verification is promoted.

The previously recorded aggregate Greia source boundary also contained four unrelated stale boot-contract failures around the accepted `panic=5` versus old `panic=30` expectations. Preserve genuine current results and do not change unrelated tests merely to produce a green microphone tranche.

## Deliberately open physical work

No source-only claim is made that the Acer already has a real denoiser endpoint.

The local agent must physically establish:

1. the exact raw built-in microphone/capture topology;
2. a working very-low-resource `greia_mic_light` endpoint;
3. useful A/B signal improvement during speech;
4. CPU/RSS/latency/dropout cost on the reference Acer;
5. correct readiness-marker lifecycle;
6. end-to-end use by a normal `audio.basic` Activity;
7. Parent off/default/persistence behavior;
8. whether an advanced endpoint is worthwhile at all.

SpeexDSP preprocessor is the preferred first denoising candidate for the Acer because it is a small voice-oriented DSP path. AGC should initially remain disabled there because current Greia already has a separate microphone-gain behavior. A simple gate/high-pass chain may be evaluated but does not qualify as noise reduction merely because it silences quiet gaps.

Advanced processing is optional. It is a correct outcome for the Acer to advertise `advanced = false`.

## Known first-party migration seam

At review time, `activities/teatrino_fiabe/main.py` still enumerates SDL capture devices and selects the first one. The physical-finalization agent must migrate that capture-open path to `get_audio_capture_device()` and verify normal story recording through the Greia launcher.

The existing `mic_gain` behavior remains compatibility state for this tranche; do not mix a gain/AGC redesign into physical denoising acceptance without explicit measured evidence.

## Architecture status

This tranche does not close or reorder the active R7 display/session/input work. R7 remains the primary blocking architecture phase.

The microphone work is an independent typed platform service whose source contract is now present and whose physical Acer realization remains evidence-gated.
