# Acer Aspire One microphone noise filter: installation, capture and DSP check (2026-10-17)

**Evidence class:** mixed, labelled per row.

- **PHYSICAL**: real captures from the Acer internal microphone and the Acer's own speakers, made over SSH.
- **PHYSICAL CAPTURE + OFFLINE DSP**: those real captures were run, on the Acer, through a re-implementation of the `greia_mic_light.c` chain. It uses the same FIR taps, the same 48→24 kHz decimation, SpeexDSP denoise at −15 dB with AGC off and 20 ms frames, and the device's installed `libspeexdsp.so.1` (1.2.1) through `ctypes`. **This is not the ALSA plugin.** The plugin is not installed on the device (§1), so it could not be measured.
- **SOURCE**: read from source or checked by tests only.

**Remote-only caveat:** all of this was done remotely. Nobody spoke into the microphone. The stimuli were synthetic: pink noise and a harmonic "speech-like" signal with formants and syllable gating, generated into device `/tmp`. They were played through the Acer speakers at the existing mixer settings. The room around the device was not controlled. Its noise was not stationary (§3). No child or owner judged intelligibility. All recordings were deleted from the device after analysis and were never copied off it.

**Device:** Acer Aspire One, Atom N270, Debian 12 i686, kernel 6.1.0-53-686, alsa-lib 1.2.8, HDA Intel ALC268. The image is `legacy-x86-i686-dev`, `build-info` dated 2026-10-06 04:47 UTC, installed 2026-10-06. Source is deployed in place at `/opt/greia-os/.deployed-sha` = `3f3cff7b`. The repository was at `38f068f9` while this was written.

## 0. Headline

1. **The noise filter is not running on the Acer.** The ExtPlug module `libasound_module_pcm_greia_mic_light.so` is missing from the image, so `greia_mic_light` fails to open ("Cannot open shared library"). The boot probe correctly writes no marker, and the AudioService routes `effective.mode = off` with `fallback_reason = lightweight_unavailable`. The Parent "noise cancelling" toggle is stored as on, but no Activity gets a filtered path. (PHYSICAL)
2. **Correction to the parity audit: the image does not predate the plugin build step.** It was built from campaign source `64103e48`, which contains `e859fb4b`. The build step ran and failed without stopping the build. Evidence: an empty, package-unowned directory `/usr/lib/alsa-lib/` with mtime 2026-10-06 05:00:58 UTC, 50 s after the early-framebuffer helper (05:00:08). That is exactly what `install -d "$rootfs/usr/lib/$multiarch/alsa-lib"` produces when `$multiarch` is empty. The audit (`2026-10-17_ACER_REPO_PARITY_AUDIT.md`, class "(c)") said otherwise. Root causes are in §2. The fix lives in `build/lib/compose.sh` and is outside this worker's scope, so it is given as an exact proposal in §2.
3. **The DSP itself works as intended on real Acer audio.** This is the offline chain, not the plugin:
   - steady noise drops about 14–15 dB (p10 block level);
   - voice-band (300–3000 Hz) levels of the speech-like stimulus stay within 0.5 dB;
   - AGC reads back off;
   - SpeexDSP costs about 3.9% of one Atom core.
4. **New PHYSICAL defect: start-of-recording thump.** HDA codec power saving is on (`snd_hda_intel power_save=1`). After about 1 s of audio idle, every capture open makes the mic channel rail at full scale for about 1 s (raw left channel −1.5 dBFS RMS, DC swinging +18 700 … −30 600). The denoiser passes it unchanged. It disappears when the codec is kept awake. This affects raw and filtered recordings alike.
5. The internal mic is **mono on the left channel only**; the right channel is digital zero. Every mono capture through `plughw` averages the two channels, so it is 6 dB quieter than the mic signal. SNR is unaffected. This is probably why `mic_gain` 2.0 sounds right on this device.

## 1. Installation state on the device (PHYSICAL)

| Check | Result |
| --- | --- |
| Module `/usr/lib/i386-linux-gnu/alsa-lib/libasound_module_pcm_greia_mic_light.so` | **absent**. The directory `/usr/lib/i386-linux-gnu/alsa-lib/` does not exist. `/usr/lib/alsa-lib/` exists, is empty and is owned by no package. |
| `libspeexdsp1` | 1.2.1-1 i386 installed (`/usr/lib/i386-linux-gnu/libspeexdsp.so.1.5.2`) |
| `/etc/asound.conf` | matches the repository at the time (absolute i386 module path, `plughw:CARD=0,DEV=0`) |
| `greia-audio-endpoints.service` | enabled, `active (exited)`, status 0/SUCCESS at boot. The journal has no entries because the old probe logged nothing. |
| `/run/greia-audio/` | empty: no `lightweight-ready`, no `advanced-ready` (correct, fail-closed) |
| `arecord -l` (root) | card 0 `Intel [HDA Intel]`, device 0 `ALC268 Analog`. This is the only card. As user `greia` the list is empty because `greia` is not in `audio`; this is expected. |
| `arecord -D greia_mic_light` | `Cannot open shared library …greia_mic_light.so` → `No such device or address` |
| Parent desired state | no `audio-settings.json` in `/var/lib/greia-system-settings` (`greiapanel:pipsettings 2770`), so defaults apply: processing enabled, advanced off |
| AudioService payload, run as `greiakid` against the deployed source | `effective: {mode: off, capture_device: default, fallback_reason: lightweight_unavailable}`, `available: {lightweight: false, advanced: false}` |
| What Activities open today | `GREIA_AUDIO_PROCESSING_MODE=off`, `GREIA_AUDIO_CAPTURE_DEVICE=default`, no `ALSA_CONFIG_PATH`. SDL enumerates `['HDA Intel, ALC268 Analog']`, so `storie_della_mia_voce` and `teatrino_fiabe` record **raw**. |
| Mixer | Capture 31/31 (+31.5 dB), Mic Boost 0, `Inverted` capture off. There is no hardware AGC control. |
| Nothing holding the mic during the tests | checked with `/proc/*/fd` (no `fuser` on the image). The Shell stayed on Home throughout. |

## 2. Why the image has no module (SOURCE + PHYSICAL evidence)

`compose_build_audio_endpoint_plugin` (`build/lib/compose.sh`) has three defects:

1. **`set -e` is off inside it.** It is called as `compose_build_audio_endpoint_plugin "$rootfs" || return 1`. Bash suppresses errexit for the whole body of a function invoked in a `||` context, so only the last command's status (the apt purge) counts. A failed compile or install is ignored. The parity audit's D2 also notes this.
2. **`dpkg-architecture` is not in the toolchain.** It belongs to `dpkg-dev`, which `apt-get install --no-install-recommends gcc libasound2-dev libspeexdsp-dev` does not pull in. `multiarch` became empty, and the module directory became `/usr/lib//alsa-lib`. That is the empty directory found on the device.
3. **`libc6-dev` is not requested.** `gcc` only *recommends* it, and the ALSA headers include `<stdio.h>`, `<stdlib.h>` and `<string.h>`. This is very probably why no `.so` was produced at all: the directory exists but stays empty. This is INFERRED. The build log is gone (`/var/log` is truncated by footprint hygiene), and compiling on the Acer is impossible because `cc1` was pruned.

The `tests/test_image_staging_contract.py` string checks (`"greia_mic_light.so" in compose.sh`) passed throughout. They cannot detect a build that fails without stopping.

**Proposed `compose.sh` change (for the build-owning worker):**

```bash
compose_build_audio_endpoint_plugin() {
  local rootfs="$1"
  local project_root="${COMPOSE_PROJECT_ROOT:-$_COMPOSE_PROJECT_ROOT_DEFAULT}"
  local build_packages=(gcc libc6-dev libasound2-dev libspeexdsp-dev)
  compose_apt_options
  chroot "$rootfs" /usr/bin/env DEBIAN_FRONTEND=noninteractive \
    apt-get "${APT_ACQUIRE_OPTIONS[@]}" update || return 1
  chroot "$rootfs" /usr/bin/env DEBIAN_FRONTEND=noninteractive \
    apt-get "${APT_ACQUIRE_OPTIONS[@]}" -o Dpkg::Options::=--force-confold \
    install -y --no-install-recommends "${build_packages[@]}" >/dev/null || return 1
  install -d -m 0755 "$rootfs/usr/src/greia-audio" || return 1
  cp "$project_root/src/greia_platform/audio_alsa/greia_mic_light.c" \
    "$rootfs/usr/src/greia-audio/greia_mic_light.c" || return 1
  local multiarch
  multiarch="$(chroot "$rootfs" gcc -print-multiarch)" || return 1
  [[ -n "$multiarch" ]] || { echo "cannot determine target multiarch" >&2; return 1; }
  chroot "$rootfs" /bin/sh -c 'cd /usr/src/greia-audio && gcc -O2 -Wall -fPIC -shared -o greia_mic_light.so greia_mic_light.c -lasound -lspeexdsp -lm' || return 1
  local module="$rootfs/usr/lib/$multiarch/alsa-lib/libasound_module_pcm_greia_mic_light.so"
  install -D -m 0755 "$rootfs/usr/src/greia-audio/greia_mic_light.so" "$module" || return 1
  rm -rf "$rootfs/usr/src/greia-audio"
  chroot "$rootfs" /usr/bin/env DEBIAN_FRONTEND=noninteractive \
    apt-get "${APT_ACQUIRE_OPTIONS[@]}" -y remove --purge "${build_packages[@]}" >/dev/null || return 1
  chroot "$rootfs" apt-get -y autoremove >/dev/null 2>&1 || true
  [[ -s "$module" ]] || { echo "greia_mic_light module missing after build" >&2; return 1; }
}
```

Also recommended:

- an ELF-machine check like the one `build_early_framebuffer` does;
- an artifact-verifier assertion that the module exists under `/usr/lib/<multiarch>/alsa-lib/`;
- a behavioural test that runs the function with a fake `chroot`/`gcc` that fails, and asserts that `compose_root` stops.

**First-boot check on the next image:**

```sh
arecord -D greia_mic_light -d 1 -f S16_LE -r 16000 -c 1 /dev/null
ls /run/greia-audio/
journalctl -b -u greia-audio-endpoints
```

## 3. Measurements

**Method.** Captures were 48 kHz mono S16_LE through `plughw:CARD=0,DEV=0` (raw, which `default` also resolves to here). They were made as root with `arecord`. Stimuli were played concurrently with `aplay -D default` (dmix) at the existing Master 70%.

| Recording | Content |
| --- | --- |
| `quiet` | room only, 6 s |
| `pink` | pink noise −18 dBFS, 6 s |
| `speech` | speech-like stimulus −16 dBFS, 6 s |
| `mix` | 0–2 s pink −24 dBFS only, then 2–6 s pink + speech-like |

The first 0.5 s of each capture is skipped. "p10 block" is the 10th percentile of 10 ms RMS blocks, which is the stationary floor. Levels are dBFS of the mono downmix.

**PHYSICAL CAPTURE + OFFLINE DSP** (re-implemented `greia_mic_light` chain):

| Capture | Raw RMS | Filtered RMS | Raw p10 block | Filtered p10 block | Notes |
| --- | --- | --- | --- | --- | --- |
| room, codec awake (`quiet_default`) | −30.5 | −34.8 | −36.8 | −50.5 | room noise not stationary (−28 … −33 per 0.5 s) |
| room, steady stretch after start-up (`idle1`, 1.5–3 s) | −28 … −31 | −43 … −46 | | | **≈ −15 dB** stationary suppression |
| pink noise through speaker | −35.3 | −41.2 | −39.3 | −53.3 | bands: 100–300 Hz −7.2, 300–1k −8.5, 1–3k −5.1, 3–6k −9.2, 6–11k −10.4 dB |
| speech-like through speaker | −32.2 | −33.4 | −41.6 | −51.0 | 300–1k **−0.3**, 1–3k **−0.5** dB; 100–300 Hz −7.5 dB |
| mix: noise-only segment | −36.4 | −38.6 | | | |
| mix: speech + noise segment | −31.0 | −32.3 | | | SNR **3.9 → 5.1 dB** (+1.2 dB) |

Other results, by evidence class:

| Item | Result | Evidence class |
| --- | --- | --- |
| Spectral sanity | Content above about 12 kHz is removed (13–20 kHz band 71 → 21 dB re 1 LSB). This is the expected 24 kHz DSP band limit, already accepted in 2026-08. No tonal artefacts in the band table. | offline DSP |
| Clipping (steady captures) | 0 samples at full scale in all steady captures. Peaks −10 … −15 dBFS. | PHYSICAL |
| Clipping (start-up) | yes, see §4 | PHYSICAL |
| AGC | `SPEEX_PREPROCESS_GET_AGC` = 0 after the plugin's exact `ctl` sequence (denoise 1, AGC 0, suppress −15). The source never enables AGC. The ALC268 has no hardware AGC control. | offline DSP + SOURCE |
| CPU, SpeexDSP | 0.038–0.040 s per audio second on the Atom (≈ 3.9% of one core) | offline DSP |
| CPU, whole plugin | The FIRs and ALSA plumbing come on top; this could not be measured. The archived 2026-08-24 measurement of the hand-installed plugin was 5–10% of one core. | not measured |
| Latency | About 65–70 ms constant: the primed FIFO (2209 transport samples, ≈ 46 ms) plus the SpeexDSP one-frame internal lag (measured 991-sample offline offset ≈ 20.6 ms, which includes both FIRs). Not measured on the plugin. Irrelevant for record-then-replay. | SOURCE + offline DSP |

**Reading.** The denoiser does what it is configured to do. It removes stationary noise by 14–15 dB at the floor and leaves voice-band energy intact. It cannot remove the non-stationary part of this room's noise, so the broadband SNR gain on the mix is modest (+1.2 dB). That is consistent with a conservative −15 dB Speex setting. Real child-speech intelligibility is still unjudged.

## 4. Start-of-recording transient (PHYSICAL, new)

`/sys/module/snd_hda_intel/parameters/power_save` is `1` and `power_save_controller` is `Y`.

| Capture (raw stereo `hw:0,0`, left channel, 0.5 s blocks) | RMS dBFS | Mean (DC) |
| --- | --- | --- |
| after 12 s audio idle | −1.5, −0.6, −9.1, −25.5, −22.4, −25.1 | 18 706, −30 529, −10 006, 717, 2 350, 1 523 (min/max −32768/32767) |
| same, codec held awake by a silent `aplay` into dmix | −21.5, −27.7, −30.4, −28.9, −27.7, −29.0 | 2 070, 256, −163, 185, −117, 76 |
| second capture right after a capture | −34.8 … −37.9 | ≤ 383 |

The offline filter passes the transient (−7.7 dBFS in the first 0.5 s of the mono downmix), so filtered recordings would start with it too. Activities then apply `mic_gain`. Two options, for the owner and build worker:

- `options snd_hda_intel power_save=0` via a Greia-owned `modprobe.d` file. This is the cleanest fix, at a small idle power cost.
- A DC-blocking high-pass plus about 0.6–1 s of start-up mute inside the plugin. Offline, a 40 Hz one-pole DC blocker alone brings the first 0.5 s from −7.5 to −29 dBFS, so the mute is still needed. This needs a compile and a physical re-check, which was not possible here.

The right channel is digital zero on every capture: the internal mic is mono on the left channel.

## 5. Parent toggle → Activity path (SOURCE, plus PHYSICAL config resolution)

1. The Parent API writes `/var/lib/greia-system-settings/audio-settings.json` through `AudioSettingsStore` (0664, group `pipsettings`).
2. On every launch, the launcher (`child_shell.py`) calls `AudioService.route()`. It re-reads the settings file and the `/run/greia-audio` markers each time (`apply_scope: next_microphone_open`).
3. For an `audio.basic` Activity:
   - **mode `lightweight`**: it gets `GREIA_AUDIO_PROCESSING_MODE`, `GREIA_AUDIO_CAPTURE_DEVICE=greia_mic_light` and `ALSA_CONFIG_PATH=/opt/greia-os/runtime/alsa/greia-activity-capture.conf`;
   - **mode `off`** (toggle off, or plugin missing): it gets `default` and no ALSA view.
4. `storie_della_mia_voce/voice_microphone.py` and `teatrino_fiabe/teatrino_audio.py` open `get_sdl_capture_device()`, which is SDL's first enumerated capture device.
5. **PHYSICAL**, routed view built from the revised config files in device `/tmp`, run as `greiakid`:
   - SDL enumerates exactly `['Greia routed audio']`;
   - `default` and `sysdefault` capture both resolve to the denoise module (the open stops only at the missing `.so`);
   - routed playback through dmix opens.
   - Raw view: SDL enumerates `['HDA Intel, ALC268 Analog']`.

    So with the module installed, `storie_della_mia_voce` would record through the filter when the toggle is on. **Today it records raw** because the module is missing.
6. Gap (outside this worker's files): `microphone_level_service.ArecordMicrophoneCapture` picks `greia_mic_light` whenever the marker exists and ignores the Parent toggle. With processing switched off, the Parent meter would show the filtered level while Activities record raw.

## 6. Changes made in this tranche (SOURCE; config resolution PHYSICAL)

| File | Change | Verified |
| --- | --- | --- |
| `build/overlay/etc/asound.conf` | Module named by bare file name, not an absolute i386 path. The capture slave follows `defaults.pcm.card`/`defaults.pcm.device`, the same card the raw `default` route uses, instead of a hard-coded `CARD=0`. | On the Acer: alsa-lib expands the bare name to `/usr/lib/i386-linux-gnu/alsa-lib/…`. A nested `@func concat` slave at the same depth captured correctly (32 000 bytes per 1 s at 16 kHz). |
| `runtime/alsa/greia-activity-overrides.conf` | The routed `default`/`sysdefault` capture now references the single `greia_mic_light` definition instead of two copies of the chain with `CARD=0`. Playback dmix follows `defaults.pcm.card`. | On the Acer: hints, SDL enumeration, capture resolution and playback, as in §5. |
| `greia-audio-endpoint-probe` | Capture bounded by `timeout` (10 s; the oneshot unit has no start timeout). Every outcome is logged to stderr/journal with arecord's reason. The run directory can be overridden for tests. | On the Acer (dash): logs the missing-module reason and leaves no marker. Against a working stand-in endpoint it writes the marker. |
| `src/greia_platform/audio_alsa/Makefile` | Install dir from `$(CC) -print-multiarch`. The silent `i386-linux-gnu` fallback is gone, an empty triplet now fails, and `-lm` is added. | SOURCE |
| `greia_mic_light.c` | Frees the FIFO when `snd_pcm_extplug_create` fails (leak). Comment points at the right config owner. | SOURCE only; it cannot be compiled here (no ALSA headers on the Mac, no `cc1` on the Acer) |
| `README.md` (plugin) | Signal path corrected (it still described a 16 kHz contract). Build dependencies now include `libc6-dev`. | SOURCE |
| `tests/test_alsa_mic_endpoint_contract.py` | New. Config contracts, plus behavioural probe tests with fake `arecord`/`timeout`: success, missing module with stale-marker removal, timeout. | ran locally, with the focused audio suites: OK |

## 7. Not done / still UNPROVEN

- The real plugin was neither measured nor deployed to the device. Building it needs Debian i386 headers, which means a download or the fixed image build. The image-built endpoint is still **UNPROVEN on the Acer**. The archived 2026-08-24 PHYSICAL acceptance covered a hand-installed module on the previous image.
- Whole-plugin CPU, latency and xruns, the SDL open through the routed device, and child-speech intelligibility all need the module and, for intelligibility, a person at the device.
- The revised config files were checked in device `/tmp` only. The live `/etc/asound.conf` and `/opt/greia-os` were not changed.
