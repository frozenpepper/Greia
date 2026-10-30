# Acer microphone-processing physical acceptance and final integration

**Status:** required physical follow-up for ADR 0031  
**Date:** 2026-08-23  
**Target:** first-generation Acer Aspire One Greia developer machine  
**Evidence class:** PHYSICAL  
**Automation rule:** do not use GitHub Actions; execute on the owner-controlled checkout/Acer only

## 1. Mission

Complete, review and physically prove the platform-owned microphone-processing tranche introduced by ADR 0031.

The source architecture and Parent API/UI are intentionally designed so they can land before the exact Acer ALSA processor is proven. Your job is to close that hardware-specific gap without weakening the architecture.

The required product behavior is:

```text
raw physical microphone
        ↓
Greia-owned logical capture endpoint
        ↓
lightweight denoising by default
        ↓
Activity granted audio.basic
```

A parent may disable processing. A stronger advanced endpoint may be exposed only if it is deliberately installed and proves useful on the Acer. **There is no automatic benchmark-based or load-based processor choice.**

## 2. Mandatory reading before editing

In the Greia checkout read, in order:

```text
AGENTS.md
README.md
docs/DOCUMENTATION.md
docs/engineering/ENGINEERING_FOUNDATIONS.md
docs/adr/0031-platform-owned-microphone-processing.md
docs/agents/GREIA_AGENT_OPERATIONS.md
HANDOVER.md
src/greia_platform/audio.py
src/greia_platform/activity_api.py
src/greia_launcher/child_shell.py
src/greia_parent/update_api.py
runtime/audio-settings.toml
activities/teatrino_fiabe/main.py
```

Also inspect the exact current build profile/package set used on the Acer before adding any package.

For Parent client work (`parent-app/`, same repository), read `parent-app/README.md` and `parent-app/AGENTS.md` before editing it.

## 3. Hard invariants

Do not violate any of these to obtain a passing demo:

1. Do **not** add PipeWire/PulseAudio merely to solve this microphone tranche.
2. Do **not** implement noise suppression separately inside each Activity.
3. Do **not** allow Activities to choose physical card numbers, `/dev/snd` nodes or “first microphone”.
4. Do **not** automatically choose advanced processing from CPU benchmarks, machine model, current load or heuristics.
5. Do **not** create `/run/greia-audio/*-ready` markers unless the corresponding logical capture endpoint is genuinely usable.
6. Do **not** call a simple silence gate “noise reduction” if noise remains materially unchanged while a child is speaking.
7. Do **not** weaken sandbox/device authority or grant microphone access to an Activity that lacks `audio.basic`.
8. Do **not** leave a continuously running high-CPU audio daemon just to keep a virtual microphone alive if an on-demand/in-process design can satisfy the contract.
9. Do **not** retain child voice recordings as product state. Test recordings are temporary physical evidence only and must stay outside Git.
10. Do **not** use GitHub Actions for tests/evidence.
11. Do **not** rewrite the active architecture remediation phase order or claim R7 is closed because microphone work passes.
12. Preserve the existing `mic_gain` behavior unless a measured replacement is implemented and all consumers are migrated in the same reviewed change.

## 4. Establish exact source state

From the Greia checkout:

```bash
git status --short
git branch --show-current
git rev-parse HEAD
git log -1 --oneline
```

Record the exact SHA in the evidence report.

From the Parent HTML checkout:

```bash
git status --short
git branch --show-current
git rev-parse HEAD
git log -1 --oneline
```

If either checkout is dirty, determine why before modifying it. Do not destroy owner work.

## 5. Run source-level focused tests first

On the normal development machine/checkout, run at least:

```bash
python3 -m unittest tests.test_audio_service tests.test_parent_audio_api
python3 -m py_compile \
  src/greia_platform/audio.py \
  src/greia_platform/activity_api.py \
  src/greia_launcher/child_shell.py \
  src/greia_parent/update_api.py
```

Then run the repository's normal local verification command defined by current repo docs/Makefile.

Important: the handover at the time this protocol was written recorded pre-existing aggregate verification failures around the previously accepted `panic=5` / stale `panic=30` expectations. If they are still present and unchanged, classify them as pre-existing; do not “fix” unrelated assertions to turn this microphone tranche green. If the current handover has superseded that fact, follow the current handover.

In the Parent HTML checkout run:

```bash
npm test
node --check src/api.js
node --check src/state.js
node --check src/views_device.js
node --check src/demo_api.js
```

Do not proceed to hardware integration if the new microphone-focused tests fail.

## 6. Verify Parent client pin before Acer deployment

The Greia repository pins the exact committed state of `parent-app/` (the Git tree id) and an integrity manifest:

```text
runtime/parent-app-client.toml
runtime/parent-app-client.manifest.json
```

The microphone UI changes are in `parent-app/`. Before building/deploying, ensure the pin and image overlay correspond to a commit of `parent-app/` containing:

```text
GET/PUT audio client methods
capability-gated state fetch
Microphone cleanup card
Improve microphone sound control
Enhanced noise reduction opt-in
Demo behavior + tests
```

Check with `python3 tools/update_parent_client_pin.py --check`. If it reports drift or the pin is older:

1. finish/rerun the client tests (`make parent-app-test`);
2. commit `parent-app/`;
3. run `python3 tools/update_parent_client_pin.py`, which rewrites the pin, manifest and image overlay from the committed bytes;
4. verify every pinned file byte count and SHA-256 (the tool and `tests/test_parent_client_image_integration.py` do this);
5. commit the repin as a distinct Greia commit.

Never hand-edit hashes from memory.

## 7. Connect to the Acer using the existing developer lane

Use the current remote-development procedure in:

```text
docs/agents/GREIA_AGENT_OPERATIONS.md
```

Prefer the existing `tools/greia_remote.py`/documented SSH path. Do not invent another remote-control service.

Before changing audio, capture:

```bash
uname -a
cat /etc/os-release
cat /proc/cpuinfo
cat /proc/meminfo | head -20
lspci -nnk | grep -A4 -Ei 'audio|multimedia'
lsmod | grep '^snd' || true
aplay -l || true
arecord -l || true
aplay -L || true
arecord -L || true
```

Also record:

```bash
systemctl --no-pager --full status greia-parent.service || true
systemctl --no-pager --full status greia-launcher.service || true
```

Use the actual launcher unit name if the checkout/image uses a different documented name.

## 8. Establish the raw microphone baseline

Identify the real built-in capture path by inspection and short recordings. Do not assume `hw:0,0`.

Capture at least:

1. 10 seconds of ordinary room silence/noise;
2. 15–20 seconds of speech from the child's normal seating position;
3. speech while the laptop fan/background noise is representative;
4. if practical, speech while Greia plays normal audio through its speakers, but do not treat echo cancellation as part of this tranche.

Use mono S16 at a voice-appropriate rate supported without unstable conversion. Prefer 16 kHz or 48 kHz based on actual device support; do not force a rate that causes ALSA errors merely because a document guessed it.

Keep recordings outside the repository, for example under an operator-owned evidence directory. Delete them after review if they contain a child's voice; retain metrics/logs, not voice content.

Record raw CPU/RSS/latency context before adding processing.

## 9. Implement the lightweight endpoint

### Required semantic result

After implementation, this must be a real working ALSA capture endpoint:

```text
greia_mic_light
```

It must perform actual useful microphone cleanup with very low incremental resource use.

### Preferred first implementation: SpeexDSP preprocessor

Evaluate a minimal on-demand ALSA-compatible realization using the SpeexDSP preprocessor. Debian's i386 `libspeexdsp1` is tiny and the preprocessor provides voice-oriented denoising/AGC/VAD primitives; for the first pass:

- enable denoise;
- keep AGC disabled initially because Greia already has a separate `mic_gain` control and double-gain policy would be confusing;
- use conservative noise attenuation first (for example around -10 to -20 dB) and tune only from recordings;
- process small fixed speech frames;
- avoid dereverb/echo processing unless independently justified;
- prefer an ALSA plugin/on-demand endpoint over a permanently running proxy daemon.

If an existing Debian/ALSA plugin can provide a clean on-demand SpeexDSP capture path, use it rather than creating a large framework.

If a tiny Greia-owned ALSA PCM plugin is required, keep it narrow:

```text
physical/slave capture PCM
    ↓
mono S16 frame adapter
    ↓
SpeexDSP preprocess
    ↓
greia_mic_light
```

Its configuration must identify the physical/slave capture endpoint below a Greia-owned config boundary; Activities must never receive that physical identifier.

### Simpler fallback evaluation

A very small ALSA LADSPA high-pass/noise-gate chain may be evaluated because it is cheap. It is acceptable as the default only if A/B recordings demonstrate a meaningful improvement for the actual Acer use case **while the child is speaking**, without clipping syllable starts or pumping. If it merely makes silent gaps quieter, record that fact and move to a real denoiser rather than mislabeling it.

### Packaging

Only after the implementation is proven:

- add the minimum runtime package(s) to the correct Greia package set/profile;
- do not install development headers/compilers in the runtime image unless the current image architecture explicitly requires them;
- place Greia-owned ALSA configuration under an appropriate immutable `/etc` or `/opt/greia-os` source-controlled path according to existing image conventions;
- make creation/health of the endpoint deterministic at boot or endpoint open;
- create `/run/greia-audio/lightweight-ready` only after a real probe of `greia_mic_light` succeeds.

## 10. Make first-party microphone Activities consume Greia's route

Inspect every first-party Activity that opens a capture device.

The Python contract is:

```python
from greia_platform.activity_api import get_audio_capture_device

capture_device = get_audio_capture_device()
```

For SDL/Pygame, pass that selected logical device when the API accepts a device name. Do not enumerate and choose `names[0]`.

`activities/teatrino_fiabe/main.py` was known at protocol creation time to enumerate capture devices and select the first entry. If current source still does that, migrate it.

Development behavior may fall back to SDL's default when `get_audio_capture_device()` returns `None`.

Do not add `os` imports to Activities simply to read Greia's environment; use the platform API.

## 11. Activate the lightweight marker only after a probe

Once the real endpoint exists, test directly:

```bash
arecord -D greia_mic_light --dump-hw-params -d 1 /dev/null
```

Adapt format/rate options only if required by the actual endpoint.

Then perform a real short capture through `greia_mic_light`.

Only when that succeeds should the platform/backend lifecycle expose:

```text
/run/greia-audio/lightweight-ready
```

The marker must be recreated from current boot/runtime health; it must not be a stale persistent file under `/var`.

After marker creation, verify the Parent endpoint reports:

```text
desired.microphone_processing_enabled = true
desired.advanced_noise_reduction = false
available.lightweight = true
effective.microphone_processing_mode = lightweight
effective.capture_device = greia_mic_light
```

## 12. Verify launch routing end-to-end

Launch a real `audio.basic` Activity through the normal Greia launcher, not directly from a shell.

Verify that its sanitized launch environment contains:

```text
GREIA_AUDIO_PROCESSING_MODE=lightweight
GREIA_AUDIO_CAPTURE_DEVICE=greia_mic_light
```

Do not expose those variables to an Activity that lacks `audio.basic`.

Record a narration in Teatrino or another actual microphone Activity and play it back through the normal product flow.

Pass conditions:

- microphone opens reliably;
- recording starts/stops cleanly repeatedly;
- no first-device enumeration bypass remains in the tested first-party Activity;
- cleanup is audibly useful or measurably reduces stationary noise;
- child speech beginnings/endings are not clipped;
- there are no obvious dropouts, repeated buffers, feedback loops or severe latency;
- playback and unrelated Greia audio remain functional.

## 13. Measure resource cost

Measure the lightweight path while idle and while continuously capturing speech.

At minimum collect:

```bash
pidstat -u -r -p ALL 1 20  # if installed; otherwise use top/ps/proc equivalents
cat /proc/meminfo
```

For an in-process ALSA plugin, measure the Activity process versus the same Activity on raw capture. For a helper process, measure both Activity and helper.

The acceptance principle is not a magical single percentage. It is:

- no sustained CPU saturation or scheduler starvation on the Acer;
- no visible degradation of Greia child UI responsiveness;
- no capture underruns/overruns/dropouts in repeated recordings;
- incremental resident memory small enough to remain comfortable on the C0 floor;
- materially useful cleanup relative to raw.

If the implementation consumes a noticeable fraction of the machine merely while no microphone Activity is using it, redesign it toward on-demand ownership.

Report actual numbers rather than only PASS/FAIL adjectives.

## 14. Parent controls physical acceptance

From the real Parent HTML client against the Acer:

### Default

Confirm:

```text
Improve microphone sound: ON
Enhanced noise reduction: absent unless advanced endpoint is really available
Effective status: Lightweight cleanup active
```

### Off

Turn “Improve microphone sound” off.

Close/reopen the microphone Activity or otherwise cause a new microphone open. Confirm effective route becomes raw/default and the recording uses the raw path.

### Persistence

Reboot the Acer. Confirm the selected setting persists.

Restore defaults. Confirm lightweight is desired again and advanced is off.

## 15. Advanced processing is optional, explicit and second

Do **not** begin advanced work until the lightweight path is stable.

If the owner wants it evaluated on this Acer, a reasonable candidate is RNNoise or another stronger denoiser. The public Greia route must be:

```text
greia_mic_advanced
```

Rules:

- it must not replace the lightweight default;
- it must not be enabled by benchmark/autodetection;
- the Parent switch appears only after real endpoint readiness;
- measure actual incremental CPU/RSS/latency and A/B audio;
- if quality improvement is too small or cost is too high, leave `advanced-ready` absent and document `advanced = false` as the correct result.

There is no requirement that the Acer support advanced processing.

## 16. Failure handling

Stop and preserve evidence before broad refactoring if any of these occur:

- ALSA device deadlock or capture prevents normal playback;
- microphone cannot be reopened after an Activity exits;
- Greia launcher loses audio permissions or sandboxing must be weakened;
- processor requires a large always-on desktop audio stack;
- substantial CPU saturation or UI stutter;
- speech is less intelligible after processing;
- Parent API says lightweight/advanced is active when the endpoint does not work;
- tests reveal an architecture regression outside the audio tranche.

Fix the root cause, not the test.

## 17. Required final evidence report

Return one concise report containing:

```text
Greia SHA:
Parent HTML SHA:
Acer model:
CPU/RAM:
ALSA codec/card/capture device:
Raw capture endpoint:
Lightweight implementation/library/version:
Lightweight logical endpoint:
Lightweight availability marker owner/lifecycle:
Advanced implementation/status (or NOT INSTALLED):

Focused Greia tests: PASS/FAIL
Parent npm tests: PASS/FAIL
Aggregate local verification: PASS/FAIL + unrelated known failures separated
Raw capture: PASS/FAIL
Lightweight direct capture: PASS/FAIL
Activity end-to-end capture: PASS/FAIL
Parent default/off/persistence: PASS/FAIL
Reboot persistence: PASS/FAIL

Raw CPU/RSS observations:
Lightweight CPU/RSS observations:
Advanced CPU/RSS observations if tested:
Latency/dropout observations:
A/B speech/noise assessment:

Files changed:
Commits created:
Remaining risks/unproven claims:
```

If implementation changes were necessary, commit them to the appropriate repository in coherent commits after tests, update Greia's Parent pin/integrity manifest if the Parent SHA changed, and update `HANDOVER.md` with the exact evidence classification.

Do not mark the physical audio tranche complete if only source/simulator evidence exists.
