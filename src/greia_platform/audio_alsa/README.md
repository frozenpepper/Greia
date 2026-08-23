# Greia ALSA microphone endpoint plugin

Platform-owned implementation of the `greia_mic_light` logical capture
endpoint (ADR 0031). The plugin is a small ALSA ExtPlug that runs inside
whichever process opens the endpoint, so processing is strictly on-demand:
there is no audio daemon and no idle CPU cost.

## Signal path

```text
plughw capture slave (bound in Greia-owned /etc/asound.conf)
    -> fixed mono S16_LE 16 kHz voice contract
    -> SpeexDSP preprocessor denoise (-15 dB, AGC disabled)
    -> greia_mic_light
```

The surrounding ALSA plug layers convert whatever the application requested
(for example SDL 22.05 kHz mono) onto the fixed voice contract.

## Policy encoded here

- denoising on, conservative suppression; tune only from real A/B recordings;
- Speex AGC permanently off — Greia owns the separate `mic_gain` control;
- no echo cancellation / dereverberation in this tranche;
- the physical card identity lives only in `/etc/asound.conf`, never in
  Activity-visible configuration.

## Build and install (development lane)

```sh
make
sudo make install          # installs into /usr/lib/<multiarch>/alsa-lib/
```

Runtime dependency: `libspeexdsp1` (`build/package-sets/platform-shell-pygame.txt`).
Build dependencies (`gcc`, `libc6-dev`, `libasound2-dev`, `libspeexdsp-dev`)
are development-only and must never enter the child runtime image.

Image composition additionally places:

- `build/overlay/etc/asound.conf`
- `build/overlay/usr/local/lib/greia-os/greia-audio-endpoint-probe`
- `build/overlay/etc/systemd/system/greia-audio-endpoints.service`

The oneshot service probes the endpoint at boot with a real one-second
capture and creates `/run/greia-audio/lightweight-ready` only on success.
Markers live under tmpfs `/run` so they can never become stale persistent
state; a missing marker makes the AudioService fall back to raw capture with
the truthful `lightweight_unavailable` reason.
