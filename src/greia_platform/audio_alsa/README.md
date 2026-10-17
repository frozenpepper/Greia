# Greia ALSA microphone endpoint plugin

Platform-owned implementation of the `greia_mic_light` logical capture
endpoint (ADR 0031). The plugin is a small ALSA ExtPlug that runs inside
whichever process opens the endpoint, so processing is strictly on-demand:
there is no audio daemon and no idle CPU cost.

## Signal path

```text
plughw capture slave of ALSA's default card (bound in Greia-owned /etc/asound.conf)
    -> outer plug pins the 48 kHz mono S16_LE transport contract
    -> greia_denoise ExtPlug: FIR decimate 48 -> 24 kHz (in-spec SpeexDSP rate)
       -> SpeexDSP preprocessor denoise (-15 dB, AGC disabled, 20 ms frames)
       -> FIR interpolate back to 48 kHz through a primed delay line
    -> greia_mic_light
```

The outer ALSA plug converts whatever the application requested (16 kHz
probe, SDL 22.05 kHz mono, ...) onto the transport contract. The capture is
band-limited to about 11 kHz by the 24 kHz DSP stage. Constant latency is one
DSP frame plus the primed FIFO (about 45 ms).

## Policy encoded here

- denoising on, conservative suppression; tune only from real A/B recordings;
- Speex AGC permanently off — Greia owns the separate `mic_gain` control;
- no echo cancellation / dereverberation in this tranche;
- the physical card identity lives only in `/etc/asound.conf`, never in
  Activity-visible configuration.

## Build and install (development lane)

```sh
make
sudo make install          # installs into /usr/lib/<gcc -print-multiarch>/alsa-lib/
```

Runtime dependency: `libspeexdsp1` (`build/package-sets/platform-shell-pygame.txt`).
Build dependencies (`gcc`, `libc6-dev`, `libasound2-dev`, `libspeexdsp-dev`)
are development-only and must never enter the child runtime image. `libc6-dev`
must be named explicitly: `gcc` only recommends it, so an
`--no-install-recommends` toolchain can lack the C library headers that the
ALSA headers include.

`/etc/asound.conf` names the module by bare file name, which alsa-lib expands
to its compiled plugin directory, so the configuration is architecture
neutral. The module file must therefore sit in exactly that directory.

Image composition additionally places:

- `build/overlay/etc/asound.conf`
- `build/overlay/usr/local/lib/greia-os/greia-audio-endpoint-probe`
- `build/overlay/etc/systemd/system/greia-audio-endpoints.service`

The oneshot service probes the endpoint at boot with a real one-second
capture (bounded by `timeout`, outcome logged to the journal) and creates
`/run/greia-audio/lightweight-ready` only on success.
Markers live under tmpfs `/run` so they can never become stale persistent
state; a missing marker makes the AudioService fall back to raw capture with
the truthful `lightweight_unavailable` reason.
