# ADR 0031 — Platform-owned microphone processing

**Status:** Accepted  
**Date:** 2026-08-23  
**Decision scope:** microphone capture routing, lightweight/advanced processing policy, Parent control, Activity contract

## Context

Greia deliberately targets machines as constrained as the first-generation Acer Aspire One. Its built-in microphone is a useful reminder that microphone quality cannot be treated as an Activity-specific problem: recording, speech recognition, storytelling and future voice-driven Activities all need one predictable capture path.

The current reference Linux stack is intentionally small and presently uses direct ALSA/SDL rather than PipeWire. At least one first-party Activity historically enumerated host capture devices and chose the first one. That makes platform-wide cleanup impossible to guarantee and leaks hardware/backend details into child software.

Greia already has a typed `audio.basic` capability and a Parent-controlled microphone gain. A broader audio setting had deliberately remained unimplemented pending a proper platform service.

The product requirement is modest:

- use the cheapest useful microphone cleanup by default;
- permit a parent to disable processing entirely;
- optionally expose a stronger processor where a concrete build/hardware path provides it;
- **never benchmark the machine and silently choose/promote processing modes**;
- keep processor selection, hardware card names and backend wiring out of Activities;
- preserve the extreme low-resource floor.

## Decision

### 1. Greia owns the capture route

An Activity granted `audio.basic` receives a Greia-selected logical capture route. It must not select a physical card by index, brand, `/dev/snd` node or host enumeration order.

The current Python SDK exposes:

```python
from greia_platform.activity_api import get_audio_capture_device

device = get_audio_capture_device()
```

`None` means the runtime/default capture endpoint in a development environment where Greia did not inject a production route. It does **not** authorize the Activity to invent a platform policy.

The current installed launcher mirrors the trusted resolved route into bounded launch context:

```text
GREIA_AUDIO_CAPTURE_DEVICE
GREIA_AUDIO_PROCESSING_MODE = off | lightweight | advanced
```

Those variables are descriptive runtime transport. The trusted `AudioService` and launch authority remain the owners of the decision.

### 2. One typed Audio Service owns policy

`src/greia_platform/audio.py` owns:

- persistent microphone-processing preferences;
- processor availability facts supplied by a backend adapter;
- resolution of desired Parent policy into an effective route;
- honest fallback reporting;
- Activity launch-environment projection.

The first Linux adapter uses stable logical ALSA endpoint names rather than card numbers:

```text
raw:         default
lightweight: greia_mic_light
advanced:    greia_mic_advanced
```

Concrete backend installation/provisioning remains below this semantic boundary and may change without changing Parent or Activity contracts.

### 3. Lightweight is the default; there is no automatic processor chooser

Canonical defaults are declared in `runtime/audio-settings.toml`:

```toml
microphone_processing_enabled = true
advanced_noise_reduction = false
```

If the lightweight endpoint exists, it is used. The existence of an advanced endpoint does **not** change the mode.

Greia must not:

- benchmark CPU at boot to choose a mode;
- promote to advanced because spare CPU appears available;
- change processor mode based on current Activity load;
- silently turn advanced processing on after an update.

This deliberately favors predictable behavior, battery/thermal stability and debuggability over adaptive cleverness.

### 4. Advanced processing is explicit Parent opt-in

The Parent API provides:

```text
GET  /api/v1/settings/audio
PUT  /api/v1/settings/audio
POST /api/v1/settings/audio/reset
```

The concrete top-level Parent service advertises `settings.audio = true`.

The desired state contains independent booleans:

```text
microphone_processing_enabled
advanced_noise_reduction
```

The Parent UI exposes a normal “Improve microphone sound” control and, only when the OS reports an advanced endpoint available, an “Enhanced noise reduction” option. Advanced remains off by default and the UI explicitly states that it costs more processor time and is never enabled automatically.

If advanced is requested but the concrete endpoint disappears later, Greia falls back to lightweight when available and reports `advanced_unavailable`. It does not pretend advanced processing is active.

A Parent request to enable advanced processing while the endpoint is currently unavailable is rejected.

### 5. Processing may be disabled

A parent may disable microphone processing. The effective route then uses the raw/default capture endpoint. This is important for troubleshooting, unusually good USB microphones and future external audio interfaces.

Disabling processing does not delete the backend or rewrite Activity manifests.

### 6. Backend choice is a measured implementation detail

The architecture does not hard-code a specific DSP library into the Activity/Parent contract.

For the first Acer hardware acceptance, the preferred lightweight candidate is **SpeexDSP preprocessor denoising** because it is a tiny, mature voice-oriented DSP library and is available for Debian i386. A simpler ALSA/LADSPA gate/high-pass chain may be evaluated as an even cheaper baseline, but it must not be called “noise reduction” if it only mutes silence and leaves speech-band noise unchanged.

An advanced endpoint may use RNNoise or another substantially stronger processor only after physical measurement shows acceptable behavior on the intended build. It is optional; a machine may legitimately report `advanced = false` forever.

No dependency is promoted into the reference image merely because it exists upstream. Package cost, resident memory, steady CPU, latency, speech quality and failure behavior must be measured on the Acer path first.

### 7. Availability is explicit, not guessed

The provisional ALSA backend consumes small readiness markers under:

```text
/run/greia-audio/lightweight-ready
/run/greia-audio/advanced-ready
```

A future concrete audio backend may replace this mechanism. A marker is valid only when the corresponding endpoint is actually installed and its startup/health contract has been satisfied.

Do not create a marker merely to make the Parent UI show a feature.

### 8. Microphone gain remains compatible but separate

The existing `mic_gain` hardware setting remains supported for compatibility. It is not used to smuggle DSP mode into `HardwareSettings`.

Longer term, gain/AGC ownership should be reconciled with the Audio Service so multiple Activities do not independently amplify samples. That migration requires measured physical behavior and is not implied to be complete by this ADR.

### 9. Calibration is a later typed extension

Calibration is desirable but is not required for the first processor tranche. When implemented it must:

- remain Parent initiated;
- store small derived values such as noise floor/target level, not retained raw child recordings;
- be bound to a concrete capture-device identity where possible;
- never calibrate the phone/browser microphone accidentally when the Parent client is remote;
- remain processor/backend neutral at the public contract.

### 10. Evidence boundary

Source tests can prove preference validation, no-auto-promotion policy, capability-gated Parent semantics and route resolution.

Only physical Acer evidence can establish:

- which capture device is correct;
- that the logical ALSA endpoint opens through SDL/Pygame;
- actual denoising quality;
- incremental CPU/RAM/latency;
- lack of underruns/xruns/dropouts;
- whether advanced processing is usable;
- acceptable child-speech intelligibility.

The dedicated physical protocol is:

```text
docs/testing/2026-08-23_ACER_MICROPHONE_PROCESSING_ACCEPTANCE.md
```

Until that procedure passes, the concrete lightweight/advanced backend is **UNPROVEN on the Acer** even though the platform/API architecture is implemented.

**Evidence status (2026-10-17).** On 2026-08-24 a hand-installed lightweight module passed the protocol on the previous Acer image (PHYSICAL; `2026-08-24_ACER_MICROPHONE_PHYSICAL_ACCEPTANCE.md` (archived; see git history)). The **image-built** endpoint has not passed. The 2026-10-06 `legacy-x86-i686-dev` image ships no `greia_mic_light` module, because the composition build step failed without stopping the build. The probe therefore correctly reports `lightweight_unavailable`, and Activities record raw while the Parent setting still says enabled. On real Acer captures, the configured SpeexDSP chain run offline gives about 14–15 dB of stationary-noise suppression, keeps voice-band levels within 0.5 dB, and leaves AGC off. That result is offline DSP, not the plugin. Details, the proposed build fix, and a separate start-of-recording transient caused by HDA codec power saving are in `2026-10-17_ACER_MIC_NOISE_FILTER.md` (archived; see git history). The lightweight backend stays **UNPROVEN on the Acer for images** until a fixed image boots with the module and the protocol is re-run. The advanced backend remains not provisioned.

`/etc/asound.conf` names the module by bare file name, which alsa-lib resolves in its own plugin directory, and binds the capture slave to ALSA's default card. No multiarch path or card index is hard-coded in Greia ALSA configuration.

## Consequences

### Positive

- Activities share one microphone policy instead of accumulating incompatible DSP implementations.
- The cheapest path stays deterministic and default.
- Parents retain an explicit troubleshooting/off switch.
- A stronger processor can be added without Activity changes.
- The Parent UI cannot imply advanced support on a build that lacks it.
- The architecture remains compatible with future Web/native runtimes and future non-ALSA audio backends.

### Costs

- Current microphone Activities must migrate away from physical-device enumeration.
- The exact Acer backend needs physical integration work before it can be marked ready.
- Supporting advanced processing means carrying and maintaining a second backend only where it has real value.

## Rejected alternatives

### Automatic benchmark/processor selection

Rejected. It adds hidden variability and can produce different behavior as load changes or hardware ages. The user explicitly selected predictable lightweight defaults plus Parent opt-in.

### Per-Activity noise suppression

Rejected. It duplicates CPU work, configuration and bugs, and prevents consistent Parent control.

### PipeWire as a new baseline dependency solely for denoising

Rejected for the current extreme-low-resource tranche. Greia's current path is direct ALSA/SDL. A future audio/session architecture may adopt PipeWire for broader reasons, but microphone cleanup alone does not justify imposing it on the Acer floor.

### Always-on advanced neural denoising

Rejected. The stronger path is optional and must earn its place through physical evidence.
