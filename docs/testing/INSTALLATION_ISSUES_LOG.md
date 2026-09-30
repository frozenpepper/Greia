
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
