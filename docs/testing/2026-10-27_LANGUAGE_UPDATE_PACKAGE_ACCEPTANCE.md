# Language-resource application update acceptance

**Status (2026-10-27):** current-source Python/combined package acceptance procedure,
subordinate to the [single consolidated update release campaign](GREIA_UPDATE_RELEASE_ACCEPTANCE.md).
**Pre-release policy:** there is no backward-compatibility obligation. Only
freshly installed current-release candidates should be update targets. The
legacy receiver bridge and its test have been removed from source.

## Historical source verification (not a current installed PASS)

On October 27 an earlier source snapshot passed 121 focused tests including
five now-retired legacy-bridge tests, package-builder tests, generation tests,
and localization suites. EN/IT/ES/FR language checks reported zero problems.
The overall `make verify` was RED: 5,990 tests, six failures, three errors and
nine skips. Preserve those exact historical observations in Git history; do
**not** cite the deleted bridge tests as current executable coverage or as
proof of Linux installed update acceptance.

## Current source requirements

Normal Python/combined `.greia_update` packages contain complete managed
language resources alongside code. Every offered locale contains paired
`src/greia_platform/languages/<locale>/manifest.json` and `ui.json` files;
English is mandatory, and the runtime allows at most 32 offered locales.
Unmanifested language authoring folders are not offered or packaged.

The receiver validates the staged language manifests, ordering, English UI
key coverage, schema and interpolation placeholders before activating a new
application generation. It must preserve the prior healthy generation and
profiles/saves/Activities on rejection or failed health. The current four
offered locales are EN/IT/ES/FR.

Run current focused source tests before the installed trial:

```bash
set -euo pipefail
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m unittest discover -s tests -p 'test_software_update_package.py' -v
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m unittest discover -s tests -p 'test_software_update_generation.py' -v
for locale in en it es fr; do
    PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -B tools/check_greia_language.py "$locale"
done
```

These are source checks, not substitutes for the installed update.

## Installed acceptance on a fresh current image

Use the current disposable Linux/QEMU installation selected for the
consolidated acceptance campaign. It must have been composed from current
source with the working application-update receiver; **do not** try to update
`1275` or other historical development images.

1. Build and inspect one normal current Python `.greia_update` package from
   the current source using `tools/greia_software_update.py build-python`
   with its current CLI arguments (see the
   [package operator guide](../development/GREIA_SOFTWARE_UPDATE_PACKAGES.md)).
2. Send it through the ordinary authenticated Parent **Upload & install**
   route. After durable acknowledgement, close/disconnect Parent.
3. Confirm the device continues independently until terminal job state
   `applied`, including fresh launcher/Parent health acceptance.
4. Reconnect and verify the installed Python version and locale roster
   `en,it,es,fr`; confirm actual manifest/UI resource imports.
5. On a disposable clone, deliver one rejected/broken candidate and establish
   that the previous healthy generation and user data survive. Record the
   concrete error and job result.
6. Include current combined Python/Activity packaging in the wider
   consolidated campaign. No special migration or legacy compatibility
   step belongs in this sequence.

Record package hash, current installed base identity, source SHA, job state,
health, language roster and Parent-disconnect continuation in the **single**
consolidated update result. Only installed Linux behavior may be marked
installed PASS. No complete-system image or physical hardware certification
is implied by an application-generation PASS.
