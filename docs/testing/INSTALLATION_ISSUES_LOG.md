
## 29. Microphone processing endpoint was never installed (2026-09-30)

Symptom: the Parent panel's noise cancelling controls stored correctly and
changed nothing. The API reported
`effective: mode=off, capture_device=default, fallback_reason=lightweight_unavailable`.

Chain, measured on the Acer rather than inferred:

```
/etc/asound.conf defines greia_mic_light                 present
greia-audio-endpoints.service + probe                    present
/usr/lib/i386-linux-gnu/alsa-lib/                        did not exist
arecord -D greia_mic_light                               "No such device or address"
/run/greia-audio/lightweight-ready                       never written
```

The ALSA ExtPlugin in `src/greia_platform/audio_alsa/greia_mic_light.c` was
never compiled or installed, so the PCM could not open. The probe correctly
declined to mark the endpoint ready and the service correctly fell back to
`off`; fail-closed behaviour indistinguishable from "not installed".

Three provisioning gaps, all fixed in `build/lib/compose.sh` and
`build/overlay/`:

- the plugin is now built with the target toolchain inside the root, the way
  the framebuffer renderer is, and installed as
  `libasound_module_pcm_greia_mic_light.so`; this runs before the footprint
  prune, which is what removes `cc1`;
- the probe is `chmod 0755` (it previously failed `203/EXEC`);
- `greia-audio-endpoints.service` is enabled in the target role.

Verified on the Acer after installing the module by hand:

```
backend:   lightweight_capture_device='greia_mic_light'
available: {'lightweight': True, 'advanced': False}
effective: mode='lightweight' capture_device='greia_mic_light' fallback_reason=None
arecord -D greia_mic_light: 64044 bytes at 16 kHz mono
```

Advanced reduction remains unavailable and is reported as such: there is no
`greia_mic_advanced` PCM and no plugin for it. Lightweight is Speex
preprocessing at -15 dB with AGC disabled.

## 30. Two boot loops from provisioning (2026-09-30)

**Group name that was never created.** `greia-os.conf` named the group
`greiaprofiles`; `compose.sh` creates `pipprofiles`. `systemd-tmpfiles` failed
with "Failed to resolve group" and left `/run/greia-os` as `root:root 0755`.
Xorg runs as `greiakid` and could not open `/run/greia-os/Xorg.0.log`, so
`greia-launcher.service` restart-looped on every boot.

**Child could not traverse the parent home.** The launcher runs as `greiakid`
and activity discovery stats `/var/lib/greia-os/activity-packages`, which sits
under `/var/lib/greia-os` at `0750 greiapel:greiapel`. `greiakid` got `EACCES`
instead of `ENOENT`, so a directory that nothing had ever created presented as
a permission fault:

```
PermissionError: [Errno 13] '/var/lib/greia-os/activity-packages/active'
  greia_platform/activities.py:421 discovery_token
```

`child_shell` exited 1 about 20 s into every start, the trusted-presentation
fallback also exited non-zero, and the unit looped indefinitely. Fixed by
making `/var/lib/greia-os` `0751` (traverse-only; the parent service's files
stay unreadable to the child) and creating the activity package root
explicitly. `tests/test_image_tmpfiles_identities.py` now fails the build if
`tmpfiles.d` names an identity `compose.sh` does not create.

Both loops presented as `is-active` returning healthy; only `NRestarts`
climbing showed them.

## 31. Microphone gain appeared not to respond on the reference Acer (2026-09-30)

OPEN QUESTION, no product decision taken. A parent raising the gain watched
nothing happen on this machine. Measured on the Acer:

```
amixer scontrols -> Simple mixer control 'Capture',0
Limits: Capture 0 - 31
Mono:  Capture 31 [100%] [31.50dB]
```

`_apply_audio` maps `mic_gain` to an ALSA Capture percentage as
`mic_gain / 2.0`, clamped to 100. So:

```
preset 100% (1.0) -> 50% ALSA
preset 200% (2.0) -> 100% ALSA   hardware maximum
preset 300% (3.0) -> clamped, identical to 2.0
preset 400% (4.0) -> clamped, identical to 2.0
```

On this machine the 300% and 400% presets are therefore indistinguishable from
200%, and 2.0 is the ceiling. That is an observation about one ALSA control on
one device, not a product conclusion: other hardware may expose a higher
Capture limit, a separate `Mic Boost` control (present on the Acer but not yet
characterised), or a different mapping. The 0.5-4.0 product range and the
existing presets are unchanged.

The open design question, for the owner to decide rather than an agent: whether
the achievable range should be discovered per device and surfaced, or whether
the gain control should be expressed in real hardware terms at all. Either way
a parent needs to be told what ceiling they have reached instead of watching a
control that appears inert.

A second finding from the same measurements, recorded because it is an
environment limit and not a defect: with `Capture` pinned at maximum, an internal
ALC268 mic and five fans running, the raw capture floor measured about
-30 dBFS RMS and the processed endpoint about -36 to -38 dBFS, i.e. roughly 7 dB
of attenuation. Normal speech therefore sits only a few dB above the noise
floor. The available remedies are exhausted in software: gain is at maximum,
denoise gives about 7 dB, and the internal mic has no directional response. This
needs a quieter machine or an external microphone to assess speech quality.

## 32. Shareable-device contention between the meter and Activities (2026-09-30)

Recording stopped working in every microphone-using Activity once the live
Parent meter existed. The ALSA capture device is exclusive and only one holder
wins:

```
meter holding the device continuously   Activity 0 of 6 capture attempts
meter sampling 0.4 s every 1.0 s        Activity 3 of 8
meter sampling 0.15 s every 0.15 s      Activity 7 of 8
```

The meter now samples in short bursts at the protocol's full rate (measured
19.9 lines/s against a 20 lines/s ceiling) and yields for 30 s the moment an
open fails because the device is busy, so an Activity that starts meets a meter
that gets out of the way.

This is not fully solvable by scheduling: there is one capture device and no
signal yet for "an Activity is recording". Until the platform exposes one, the
meter yields on contention rather than competing, and that is a real remaining
limitation rather than a tuning detail.

Note for anyone measuring this later: counting distinct level *values* to judge
meter responsiveness is wrong in a quiet room, because the value does not
change and the meter looks frozen while publishing happily. Measure the publish
rate off the socket.
