# Ubuntu legacy-x86 source-gate failure and repair

**Date:** 2026-08-15  
**Repository:** `frozenpepper/Greia`  
**Failed source SHA:** `5182ba487dba562c9670b0bd87eadd32700fd357`  
**Execution host:** Intel Mac mini, Ubuntu 24.04.4 LTS x86_64  
**Physical-media status:** **NOT WRITTEN**

## Preserved failure

The owner-controlled Ubuntu run of:

```bash
bash tools/run_hardware_enablement_source_gate.sh
```

stopped before image build or SD mutation as required. The two focused hardware-enablement suites passed, then the full source gate failed after 520 tests with `failures=4, errors=6`.

The uploaded evidence bundle records the exact host, clean `origin/main` SHA, package versions, profile, disk-space state, source-gate exit, and full stdout/stderr.

## Root-cause classification

The failures were not evidence that Greia required a larger build VM or a different Acer-specific image. They exposed cross-project source/test drift plus one distro-Pygame portability defect.

### Real implementation defects repaired

1. `tools/greia_remote.py` stored the SSH key path in `self.key`, shadowing the existing `key()` remote-input method. The path state is now `self.key_path`.
2. `src/greia_platform/pygame_input.py` assumed every Pygame `_sdl2.controller` build re-exported SDL2 `CONTROLLER_BUTTON_*` and `CONTROLLER_AXIS_*` enum constants. Ubuntu's packaged Pygame exposes the controller module/API but omits those attributes. Greia now uses named compatibility constants with SDL2's stable enum values as fallbacks while preserving the same semantic input mapping.
3. The common overlay was missing the explicit SSH hardening drop-in already required by the developer-remote security contract. `build/overlay/etc/ssh/sshd_config.d/20-greia-parent.conf` now explicitly permits public-key authentication, disables password and keyboard-interactive authentication, disables root login, and limits SSH login to `greiaadmin`. This policy does not itself enable SSH on normal images.

### Stale regression expectations repaired

1. Activity theme access now intentionally falls back to the canonical default resolved theme when no profile customization path is granted; the test no longer expects an exception for ordinary read-only theme access.
2. Built-in Activity discovery now includes the required Writing and Painting Activities and assertions no longer depend on obsolete list positions.
3. Painting repository tests now provide the required initial PNG payload to `PaintingRepository.create()`.
4. Text-buffer line-end navigation now expects the logical end of the current line/document after the inserted newline sequence.
5. Invalid runtime lifecycle environment bindings are rejected by `RuntimeManager` before display acquisition. The supervisor regression now expects `LAUNCH_FAILURE`, no process launch, and no display-backend calls rather than an unreachable post-display `PLATFORM_FAILURE` path.
6. Pygame input tests use Greia's compatibility constants rather than reaching back into optional third-party enum exports.

## Evidence status after source repair

The repair is source-reviewed but **UNPROVEN on the owner-controlled Ubuntu host until the exact current `main` SHA reruns the canonical source gate**.

Do not build or write the SD merely because the code changes are committed. The next authoritative action remains:

```bash
git pull --ff-only origin main
bash tools/run_hardware_enablement_source_gate.sh
```

Only after that command exits zero may the Ubuntu SD runbook continue to:

```bash
sudo bash build/build-legacy-x86-sd-installer.sh out
```

and then the physical SD identification/write/read-back procedure.

## Non-regression constraints

- Do not replace the generic `legacy-x86-i686` profile with an Acer model-specific build.
- Do not weaken `tools/run_hardware_enablement_source_gate.sh` to hide unrelated regressions.
- Do not treat Pygame packaging differences as permission to expose raw controller devices directly to Activities.
- Do not rely on distro SSH defaults for Greia developer-image authentication policy.
- Preserve the failed Ubuntu evidence; do not rewrite it as a pass after the repair.
