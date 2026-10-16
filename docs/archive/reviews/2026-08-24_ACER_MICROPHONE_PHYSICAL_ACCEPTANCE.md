# Acer microphone processing — physical acceptance review

**Date:** 2026-08-24
**Scope:** PHYSICAL — first-generation Acer Aspire One Greia developer machine
**Greia SHA at physical completion:** `2972127` (tranche commits `51ad24e`..`2972127`; Parent client pin unchanged at `f64067b`)
**Protocol:** `docs/testing/2026-08-23_ACER_MICROPHONE_PROCESSING_ACCEPTANCE.md`
**Verdict:** lightweight route ACCEPTED by the owner after A/B; advanced endpoint NOT INSTALLED (correct per ADR 0031)

## Machine identity

```text
Acer Aspire One, Intel Atom N270 @ 1.60 GHz (2 threads), 1 GiB RAM
Debian 12 bookworm i686, kernel 6.1.0-52-686
ALSA HDA Intel, codec ALC268 Analog (hw:0,0; capture stereo-only, 44.1–96 kHz)
Developer image, greia/greia SSH lane, password sudo (devctl NOPASSWD not provisioned on this image)
```

## What was implemented physically

```text
raw ALC268 capture (plughw)
  → Greia ALSA ExtPlug "greia_denoise" (in-process, on-demand)
      FIR decimate 48 kHz → 24 kHz (in-spec SpeexDSP range)
      SpeexDSP preprocessor denoise −15 dB, AGC off
      FIR interpolate back to 48 kHz
      primed delay-line FIFO (constant latency, glitch-free)
  → logical endpoint greia_mic_light
```

- `libasound_module_pcm_greia_mic_light.so` built from
  `src/greia_platform/audio_alsa/` (libspeexdsp1 1.2.1, Debian i386).
- `/etc/asound.conf` registers the plugin type and the `greia_mic_light` PCM
  (physical slave hidden below Greia configuration).
- `systemd greia-audio-endpoints.service` probes the endpoint with a real
  one-second capture at boot and maintains `/run/greia-audio/lightweight-ready`
  (tmpfs; verified recreated automatically after a real reboot).
- Runtime composition `runtime/alsa/greia-activity-capture.conf` +
  `greia-activity-overrides.conf` is injected per-launch through
  `ALSA_CONFIG_PATH` for `audio.basic` launches whose effective mode is not
  `off`. It hides raw `hw:` hints from SDL and resolves `default`/`sysdefault`
  to the routed asymmetric PCM (capture → denoise, playback → stock dmix).

## Why the SDL composition exists (integration finding)

SDL 2.26.5 (Debian pygame 2.1.2) enumerates only hint names matching the
`hw:`/`sysdefault:`/`default:` prefixes and opens them through its own device
table; arbitrary ALSA PCM names (including `greia_mic_light` and even literal
`hw:CARD=...` strings) are rejected with "No such device". The ADR's
"pass the route name to the capture-open call" is therefore realized for
SDL runtimes as: the launcher injects the composed ALSA view, and the SDK
function `get_sdl_capture_device()` designates the SDL-enumerated device that
carries the route. Activities still never choose hardware themselves.
`get_audio_capture_device()` keeps its semantic meaning for non-SDL capture.

## Physical verification results

```text
Focused Greia microphone tests (audio service, parent API, activity API,
  pin tool, teatrino):            PASS (31 tests)
Parent HTML client at pinned f64067b
  (runtime bytes identical to locally tested ce8ef76):
  npm 45/45 PASS, node --check PASS,
  desktop + mobile visual review PASS (demo mode)
Raw capture baseline:             PASS (mono 16k/48k via plug, no xruns)
greia_mic_light direct probe:     PASS (arecord + in-sandbox SDL probe)
Launch-context injection:         PASS — real launcher launch of Teatrino
  carried GREIA_AUDIO_PROCESSING_MODE=lightweight,
  GREIA_AUDIO_CAPTURE_DEVICE=greia_mic_light, ALSA_CONFIG_PATH
Live route proof:                 PASS — during Teatrino recording,
  /proc/asound hw_params showed rate 48000 with owner_pid = Teatrino pid
Teatrino record/replay/save:      PASS (multiple narrations saved through
  the normal product flow; mic re-acquired after Activity exit)
Negative capability check:        PASS — painting (no audio.basic) launch
  carried zero audio-route environment variables
Parent API state:                 PASS — desired/effective/available exactly
  per protocol §13; OFF control, restore, and reboot persistence PASS
Reboot persistence:               PASS — Parent setting persisted; boot probe
  recreated lightweight-ready on its own
Advanced endpoint:                NOT INSTALLED (available.advanced = false)
```

## Measured quality and cost

```text
Stationary noise floor (room noise, 22050 Hz mono, p10 block RMS):
  raw capture                582
  routed (final build)        59     −19.9 dB broadband
  per-band suppression        −1.6 … −8.9 dB across 0.25–10.5 kHz
Speech preservation (speaker stimulus A/B):
  voice-band levels within ~1.5 dB of raw; SNR improvement ≈ +4.5 dB
Glitches:                       0 discontinuities >3000 LSB in 12 s takes
Latency:                        one 20 ms DSP frame + FIR delay (~45 ms),
  constant, inaudible for narration
CPU (arecord through route):    ~5–10% of one core (~3–5% of the Atom)
RSS:                            +0.4 MB versus raw arecord
Idle cost:                      zero — no process exists when no capture open
```

Owner A/B verdicts (recorded in-session): raw noise vs routed noise played
twice through the Acer speakers → "B clearly better"; in-Teatrino narration
→ "denoising is clearly there and effective". Voice level tuned with the
existing Parent `mic_gain` control (raised 2.0 → 3.0 on this device).

## Defects found and fixed during acceptance

1. SpeexDSP ran out of spec at 48 kHz (−6 dB suppression) → in-spec 24 kHz
   decimated pipeline (−19.9 dB).
2. In-place transfer transform duplicated/glitched samples at transfer
   boundaries ("clipfest") → primed delay-line FIFO.
3. SDL silently fell back to the raw `default:CARD=Intel` chain because the
   routed definition's hint name did not match SDL's prefix matcher →
   `default`/`sysdefault` now resolve to the routed PCM inside routed
   Activity processes.

## Remaining risks / unproven

- The compiled plugin is installed on the Acer dev machine only; image build
  integration (compiling `src/greia_platform/audio_alsa/` for i686 during
  image composition) is a required follow-up before release images ship the
  route. Until then, images without the plugin honestly report
  `lightweight_unavailable` and fall back to raw.
- The 24 kHz DSP band-limits capture to 12 kHz; narration quality accepted by
  the owner, but a future stronger in-spec DSP could widen it.
- `nascondino_bosco` was observed saturating one core (100% main-thread CPU)
  while open — pre-existing Activity render-loop behavior, unrelated to this
  tranche, worth its own performance pass.
- Child-voice test recordings were deleted after review; only measurements
  and logs are retained.
