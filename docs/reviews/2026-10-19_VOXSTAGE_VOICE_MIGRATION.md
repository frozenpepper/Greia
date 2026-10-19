# VoxStage/VoxCPM2 voice migration — 19 October 2026

## Scope and owner acceptance

The owner selected Flash round 1 candidate 2, Leo round 1 candidate 3, Lilli round
2 candidate 3, Dani round 2 candidate 3, Tito round 2 candidate 1 and Momo round 2
candidate 3. After listening to the selected masters and 24 EN/IT/FR/ES samples,
the owner accepted the set and explicitly directed promotion and default-provider
integration. This authorizes the v0.2 identity set and new default; it does not
request regeneration of every existing accepted runtime cue.

## Implemented owner chain

`tools/greia_voice.py` and repository producers use the common `build_engine` /
`composition.build_providers` policy. The default character adapter uses the
existing VoxStage service and its serialized VoxCPM2 worker over loopback HTTP.
Provider adaptation and bounded transport are separate collaborators; model,
voice-library and job persistence remain owned by the shared tool. No second
MLX model process or child-device synthesis dependency was introduced.

The active registry is `assets/audio/characters/canonical/v0.2/manifest.toml`.
Each full selected master is preserved byte-for-byte as source and reference;
portable provenance retains source voice/job IDs, seed, transcript and design
prompt. All six canonical IDs are `greia.<character>.v2`, including Dani.
v0.1 remains historical. Existing shipping audio and receipts were not changed.

Missing saved voice IDs import exact repository references on a fresh local
VoxStage library. Existing IDs are reused only for the same reference/transcript;
they are never overwritten. Full returned text, reference identity and complete
mixed output are checked, so longer split requests cannot silently return only
the first sentence. Errors/timeouts preserve job or submission identity for
recovery; uncertain POSTs are never automatically repeated.

Chatterbox remains explicitly selectable through `--character-provider
chatterbox` or `GREIA_VOICE_CHARACTER_PROVIDER=chatterbox`; there is no automatic
backend fallback. Its noisy model diagnostics now go to stderr so CLI stdout
remains JSON. Dani's existing `dani_system_speech` kind is compatible with its
new clone; `character_dialogue` also works for Dani. Pedagogical pronunciation
keeps the separate native/system provider and semantic speaker constraints.

The warm client separates its ten-second connection timeout from its synthesis
response timeout. Canonical asset installation now validates all twelve v0.2
files. Runtime asset composition excludes every canonical reference version;
the real-rsync test also starts with a stale leaked reference and proves it is
removed while shared runtime audio remains installed.

## Verification

Source baseline was refreshed on `main` from `43045003e39c4d020647309760d19a41182b98f3`
to concurrent upstream `245ed1573221ec8fc4bb94f7848fca336cc59d82` before final
verification. No branch/worktree was created. Ignored local `.agents/skills/` copies were refreshed from the canonical voice-production, OS-work and Activity-authoring skills so future local agents see the same guidance. An untouched Git archive of the
first baseline outside the repository was used only to reproduce inherited
failures. Unrelated `final.mp4` and `launch-video/` were preserved untracked.

- Focused voice, retained-provider and real-rsync packaging run: **37 tests PASS**.
- Canonical installer `--pack-root . --check-only`: all twelve files PASS.
- Live default `generate` plus five-character `batch`: all six voices produced
  review audio and receipts using their selected v0.2 references.
- Live `serve` on port 43842 plus ordinary `request`: Spanish Dani generated
  through the default provider; server shutdown completed afterward.
- Final default Momo generation after source refinements: PASS.
- Retained Chatterbox generated Leo using cached weights with
  `HF_HUB_OFFLINE=1`; repeated after the stderr fix with clean JSON output: PASS.
- Native pedagogical Italian `ma`: generated through `macos-native-say`.
- Final `doctor`: `character_production_ready=true`, selected provider `voxstage`,
  six valid references, FFmpeg available. Optional Whisper is UNAVAILABLE due
  to this host's Anaconda/NumPy/Numba compatibility issue. Live synthesis smoke
  checks deliberately used `--verification off`.
- All new engine-integration smoke recordings remain **human review PENDING**.
  They are separate technical evidence from the previously owner-accepted 24
  comparison samples. No production runtime/image/physical playback is claimed.
- Final `make -k verify` on the refreshed source: **5,449 tests run; 1 failure, 4 errors, 8 skipped**. Only the five deterministic baseline cases below remained; launcher-memory passed in this run. The aggregate gate is **NOT GREEN**.
- Project validation also stops at the inherited ARM64 builder assumption; the same validator failure reproduced on the untouched baseline with its correct `PYTHONPATH`.
- All **45 Activity validators PASS** when run independently of that blocked project validator. Shell syntax and source footprint checks PASS. Final source-bytecode cleanup completed.
- Implementation scope is SOURCE-CLOSED for this owner-directed migration; aggregate repository/build readiness remains blocked by the existing upstream issues.

### Inherited aggregate failures

The first full `make verify` ran 5,437 tests: two failures, four errors and eight
skips. Five deterministic cases reproduced on the untouched first baseline:

1. `test_build_profiles...test_all_repository_profiles_are_typed_toml_and_resolve_both_artifacts` assumes every profile is buildable, while new ARM profiles deliberately fail closed.
2. `test_build_profiles...test_cli_manifest_is_stable_json` executes a non-executable `tools/build_profile.py` (upstream mode 100644).
3. `test_installer_state...test_completion_button_writes_the_root_poweroff_marker` invokes missing Linux `lsblk` on macOS.
4. `test_installer_state...test_completion_marker_failure_shows_the_manual_fallback` has the same host dependency.
5. `test_mbr_observed_identity...test_foreign_plan_non_disk_and_deferred_adapters` expects the old `legacy-bios-ab-v1` error wording.

The launcher-memory full-run failure (672,188 retained bytes versus the 524,288
threshold) passed when isolated on the untouched baseline; it is not claimed
fixed or deterministically reproduced. These unrelated installer/launcher
changes were not folded into this voice migration.

## Reproduce and use

```bash
voxstage start
python3 tools/greia_voice.py doctor
python3 tools/run_tests.py -v test_greia_voxstage test_greia_voice_tool test_greia_voice_provider_policy test_build_runtime_assets_contract
python3 tools/install_canonical_voice_assets.py . --pack-root . --check-only
make -k verify
# Free the shared model after generation, without removing its library/jobs.
voxstage unload
```

Normal generation uses `generate`, `batch`, or `serve`/`request` with semantic
speaker/kind/locale/text. For explicit Chatterbox, unload VoxStage first and use
the operator flag/environment setting. New recordings still require listening.

Detailed local smoke artifacts/receipts and source-file SHA-256 snapshot remain
outside Git in `/Volumes/Test1/Works/Greia-voice-auditions/2026-10-19-engine-integration/`.
Copies of the final checks, baseline reproduction, readiness and retained-backend
logs are retained under that directory’s `logs/` (original commands also wrote `/tmp/greia-voxstage-*`). The migration does not close a blocking remediation/lifecycle phase.

Audited source/reference fingerprint: `347ba39ba97d77299aeb5140c60720da4408be106139b6b71325a69847b57198` (file list retained in the external evidence directory).
