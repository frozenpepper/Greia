# Language update package acceptance — 2026-10-27

> **Current execution route:** [one consolidated update release acceptance guide](GREIA_UPDATE_RELEASE_ACCEPTANCE.md). This document remains the specialized source and exact-legacy-bridge reference; it does not require a separate single-use agent handoff. The one-time receiver bridge applies **only** to an installed test image verified to match the specific `1275` source base.

**Scope:** source proof for language JSON delivery through Python application
updates, plus the bounded installed follow-up. This is not Linux image,
A/B-slot, current-language image, or physical-device acceptance.

**Source review boundary:** implementation worktree based on `d1d6b60ad`,
Python 3.12.7 at `/opt/anaconda3/bin/python3` on macOS; SDL video/audio dummy,
bytecode disabled. No production manifests, translations or audio changed.
Fresh Luna read-only review found no correctness/data-loss blocker. Real-source
CLI builds of the current Python package and the source-matched bridge passed;
their temporary outputs were not installed or committed.

Executed focused result: **121 tests PASS**, including package 18, generation
10 and bridge 5, plus jobs/bootstrap/CLI and all five localization suites.
EN/IT/ES/FR source checks each report zero problems. Documentation audit:
427 Markdown files, zero unresolved links; four auditor tests PASS.
`make verify` is RED: 5,990 tests, six failures, three errors, nine skips.
These are the previously recorded three Foresta voice-review subtest failures,
one MBR error-message assertion, two Parent JavaScript assertions, the ARM64
builder-support error and two installer tests requiring unavailable `lsblk` on
macOS. No unrelated repairs were made. The final focused run was sequential;
an initial parallel invocation raced `make`'s bytecode cleanup and was rerun.
Logs are local at `/tmp/greia-language-update-20261027/`.

## Source checks

Run these focused suites first from the repository root. They use temporary
source trees and package files; they do not build or install an OS image.

```bash
set -euo pipefail
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m unittest discover -s tests -p 'test_software_update_package.py' -v
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m unittest discover -s tests -p 'test_software_update_generation.py' -v
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m unittest discover -s tests -p 'test_software_update_bridge.py' -v
```

The bridge suite starts from the exact legacy source commit
`1275e0be1a9e0cda724ce18151ae65a25f03c98c`, builds the code-only receiver
bridge, stages it through that real legacy package reader/generation builder,
then stages a normal current Python package and imports the candidate's real
language registry in a fresh process. It checks that the current package can
introduce additional offered language JSON after the bridge. This is source
proof only; it does not execute the installed service, Parent API, or target
hardware.

The normal Python/combined package is a complete managed language-resource
snapshot: each offered canonical locale includes paired `manifest.json` and
`ui.json` files, English is required, and the runtime limit is 32 offered
locales. Manifest-less language staging folders are ignored. The receiver
validates JSON schema, runtime ordering, English UI key coverage and
interpolation placeholders before pointer activation. Stale managed locale
JSON is removed only from the staged generation. Profiles, saves, Activities,
and the active generation remain preserved on a rejected candidate.

## Bounded installed follow-up

Only use an existing supported test device or disposable clone that is idle at
the real profile picker and not running another install/update or test session.
If those conditions are not true, stop without starting an install. Do not
build/reimage an OS for this acceptance and do not use hosted Actions.

1. Confirm the installed application matches source
   `1275e0be1a9e0cda724ce18151ae65a25f03c98c`. Build and inspect the one-time
   bridge using the exact command in [the package operator
   guide](../development/GREIA_SOFTWARE_UPDATE_PACKAGES.md). It uses that base,
   `--git-root .`, and `--python-root .`. The package replaces the complete
   declared Python/runtime snapshot with the frozen base snapshot and overlays
   only the receiver package and generation modules. Never use it on an
   arbitrary supported image or a newer application generation.
2. Upload the bridge through the normal authenticated Parent **Upload &
   install** route. Wait for job state `applied`, which includes fresh launcher
   and Parent health acceptance. Do not send the current language package
   before this state.
3. After bridge acceptance, build and inspect a normal current Python package
   from `--source-root .`. Upload it through the same route and wait for
   `applied`. Record package hashes, job states, and the offered locale order
   reported by the installed runtime.
4. Stop after these two application updates. Do not arm or boot A/B slot B as
   part of this language-data check.

After either upload is acknowledged, close the Parent app; reconnect only to
read the job result. If the result is `failed` or `rolled_back`, save the first
error and stop without retrying or rebuilding. On an already provisioned
developer target, the existing maintenance shell can read the installed roster:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/opt/greia-os/src python3 -B -c \
  'from greia_platform.system_language import SUPPORTED_SYSTEM_LOCALES; print(SUPPORTED_SYSTEM_LOCALES)'
```

Do not enable SSH or add a maintenance API for this check. Record one concise
report with repository/Python identity, installed base identity, both package
hashes, final job states/errors, roster order and whether processing completed
after the Parent disconnected. Stop if the installed base is unknown or differs
from the bridge base; do not downgrade it to make this recipe fit.

An `applied` result on the selected disposable target proves that target's
application-generation path and startup acceptance only. It does not certify
an OS image rebuild, a different device family, a fifth locale's rendered UI,
Parent browser chrome localization, audio/listening, or physical-device
acceptance beyond the target used.
