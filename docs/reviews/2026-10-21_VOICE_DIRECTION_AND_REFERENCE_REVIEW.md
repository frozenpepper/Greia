# Voice direction, reference guidance and new auditions · 2026-10-21

## Owner feedback and diagnosed prompt mismatch

The owner reports excessive pitch/excitement for Dani/Momo/Tito, inconsistent Momo,
and an old/hyperactive quality for Tito. Audible assessment is the owner's report;
this investigation traces prompt inputs, not an agent listening judgment.

Both layers repeated character acting:

- Master design: Dani "buzzy, nasal, bell-like", staccato and stepped pitch;
  Tito "pointed nasal", nimble and husky; Momo "honking nasal", wobbly musical bounce.
- Recurring defaults repeated robot/woodland/comic acting; the external v2
  `build_overrides.py` additionally prefixed every explicit cue with PERSONA.
- Generic praise asked for delighted brightness and a bounce; celebration and
  welcomes also systematically boosted excitement. These are plausible contributors,
  not proof that prompt wording alone caused all acoustic defects.

**Correct ownership:** fixed pitch/register, timbre, vocal age/texture and character
identity belong to master design. Per-cue prompts contain only acting appropriate
to that line. All six current defaults are now `Clear, natural conversational
delivery at an easy, unhurried pace.` Intentional teaching emotions may still be
performed on their specific cues; ordinary narration/praise should stay restrained.
Explicit historical prompts are not silently rewritten in engine requests.
The actual runtime boundary was traced: Greia sends only `Speak in <language>.`
plus the effective delivery prompt; VoxStage's planner composes script direction,
segment emotion/delivery/pace. The clone path does not reinsert the saved voice
library description. The duplicate persona was in Greia's old defaults/overrides,
not an unavoidable requirement of reference cloning.

## Primary source guidance (accessed 2026-10-21)

- [VoxCPM usage guide, Reference Audio](https://voxcpm.readthedocs.io/en/latest/usage_guide.html#reference-audio): practical duration range 5–30 seconds; clean audio helps preserve timbre; reusing the same reference supports consistency.
- [OpenBMB VoxCPM repository](https://github.com/OpenBMB/VoxCPM): reference cloning conditions timbre while optional instructions steer performance; continuation additionally uses the exact transcript and carries vocal detail.
- [OpenBMB VoxCPM2 model card](https://huggingface.co/openbmb/VoxCPM2): separates voice design, controllable reference cloning and transcript-conditioned cloning.

The installed MLX/VoxStage implementation is distinct from the upstream PyTorch
API: it exposes reference/continuation/combined modes, passes `ref_audio` and
`instruct`, and currently imports references of 2–30 seconds. Do not copy upstream
parameter names into Greia callers. A longer reference is an experiment within
the guidance, not a guarantee of better cloning or proof that 8 seconds was invalid.

Current v0.2 reference durations: Dani 8.00s, Momo 6.88s, Tito 9.76s (other cast
7.36–8.00s). The saved original design settings use max_tokens=180; the installed
backend's 160ms/patch cap would be around 28.8s. Thus their 7–10s lengths are not
explained by reaching that token cap. No claim of exact transcript completeness
has been established by this inspection.

## Executed bounded new auditions

Shared VoxStage queue was idle before submitting three jobs with two seeds each.
New immutable IDs, description only at master design, common 46-word natural
reference script, 10 steps / CFG 2 / cap 240. No canonical reference replacement.
The aim was more grounded middle/low registers and restrained conversational
acting. These are requested attributes, not listening-verified properties.

| Character | Job | Durations | Seeds |
|---|---|---|---|
| Dani | `20261021-062707-daebe616` | 16.00s / 14.88s | 63000 / 63001 |
| Momo | `20261021-062708-2e6a6186` | 14.24s / 14.88s | 63100 / 63101 |
| Tito | `20261021-062709-40733336` | 11.84s / 12.32s | 63200 / 63201 |

Generation finished; clean registration/valid files are not human acceptance.
Tito remains shorter than the 15–25s target; listen for pace and completeness
rather than padding a clip or assuming longer automatically sounds better.
Takeboard at http://127.0.0.1:8795/ compares each candidate to its old master.
External sources, submission/job provenance and copied WAVs:
`/Volumes/Test1/Works/Greia-voice-auditions/2026-10-21-calm-masters-v3/`.
Shared worker was unloaded after its queue emptied; it remains available for other
projects. No runtime recording or canonical master was changed.

The next replacement draft targets 1,340 DONE files (392 Dani / 284 Momo / 664 Tito)
with stripped persona prefixes and restrained performance prompts. It is not
planned or launched. Owner master selection and representative multilingual clone
listening are the next steps before replacement. Frozen v2 metadata and originals
remain intact; no old human acceptance is inferred for new outputs.
