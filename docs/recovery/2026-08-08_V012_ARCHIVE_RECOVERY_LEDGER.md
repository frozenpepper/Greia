# Greia v0.12 archive recovery ledger

**Date:** 2026-08-08
**Active branch at recovery start:** `r6-runtime-integration-recovery`
**Recovery-start head:** `73a75374ffca6e617a12f1560af24341168fe3cc`
**Uploaded archive:** `pip-kids-os-phase0-v0.12(2).zip`
**Archive SHA-256:** `7afb5028aa9f70930de1df8df4aa5a1fe00321fbfdeb94a4316cb234c332b124`

## Purpose

This ledger records the exact archive supplied again by the project owner after the R0 repository-continuity failure was discovered. The archive is the same byte-identical v0.12 source package whose checksum was recorded during the original verification session.

This file exists so archive provenance survives another execution-environment reset. It does **not** claim that the current GitHub tree already contains every archive byte.

## Archive integrity and inventory

The uploaded ZIP was read directly from the mounted upload and verified before recovery work.

```text
SHA-256  7afb5028aa9f70930de1df8df4aa5a1fe00321fbfdeb94a4316cb234c332b124
files     318
dirs       91
text      195 files, 1,145,394 bytes (about 1.09 MiB)
PNG       123 files, 12,529,585 bytes (about 11.95 MiB)
Python     46 files
```

The complete archive expands to about 13.04 MiB of file content.

The checksum matches the historical `pip-kids-os-phase0-v0.12.zip.sha256` record. The historical source-verification transcript for this archive reports `140 / 140` provider-free tests passing before the later Greia/R1-R6 work.

## Binary inventory

The 123 PNG files consist of:

```text
39 × assets/icons/core/v1/64/*.png       250,639 bytes
39 × assets/icons/core/v1/128/*.png      797,372 bytes
39 × assets/icons/core/v1/256/*.png    2,565,601 bytes
assets/source/core_icons_v1_source.png 2,907,186 bytes
assets/source/generated_variants/
  transparent_atlas_experiment.png     2,999,095 bytes
  labeled_catalog_experiment.png       2,119,549 bytes
assets/catalog/core_icons_v1_contact_sheet.png
                                         695,703 bytes
2 × Plymouth boot-mark.png                97,017 bytes each
```

The two boot-mark files are byte-identical.

`tools/extract_core_icons.py` was exercised locally against the recovered approved source sheet. It regenerated all 117 64/128/256 icon PNGs, the contact sheet, and the catalogue byte-for-byte. Independently, Pillow LANCZOS resizing from the 39 256px icons regenerated all 78 64/128px icons byte-for-byte. These observations are recovery evidence only; they do not authorize silently replacing the approved source sheet or experimental historical PNGs.

## Text/source recovery scope

The v0.12 archive includes important material that was absent from GitHub during R6 recovery, including the original:

- `docs/adr/0012-platform-architecture-constitution.md`;
- `src/pip_launcher/main.py` launcher composition baseline;
- build/installer/system-overlay source;
- asset pipeline source and catalogue;
- the complete v0.12 tests and tools;
- the complete historical documentation set.

The archive predates the Greia technical-identity migration and therefore uses Pip-era module/path identifiers. It must **not** be copied blindly over newer Greia/R1-R6 code.

The archive also necessarily predates R4/R5/R6 source created on 2026-08-08. It therefore does **not** contain the later verified `src/greia_platform/history.py`, `tests/test_history.py`, or the final post-R5 installed Greia launcher composition. Those files must be recovered from a later trustworthy copy if available; security/storage/history authority must not be reconstructed merely from prose.

## Secondary durable archive copy

The exact uploaded ZIP was copied, without modification, into the project owner's private Google Drive using the connected Drive account:

```text
Drive file ID: 17O0gelYptjQkQPTItpS636YN29pkuqy4
Name: Greia-recovery-pip-kids-os-phase0-v0.12.zip
Size: 12,921,890 bytes
```

This is a disaster-recovery copy, not the canonical repository. GitHub remains the intended source of truth.

A temporary encrypted-copy sharing experiment was attempted only with ciphertext. The Drive account does not support the connector's domain-wide share mode; the experiment failed without exposing source and the temporary encrypted Drive object was deleted.

## GitHub connector limitation discovered during recovery

The available GitHub Git-data API can create binary blobs when the complete base64 payload is supplied, but the action does not accept a mounted-file/file-URI parameter. A disposable probe proved that passing a local pathname with `encoding=base64` causes the pathname text itself to be decoded; it does not read the local file.

The current execution container also has no GitHub credential helper, no `gh`/authenticated Git path, no connector socket/CLI, and no outbound DNS/networking. Cross-connector Drive `sediment://` file references are internal authenticated references and cannot be consumed by GitHub Actions.

Therefore binary transfer must not be falsely reported complete until the actual PNG blobs are present in Git history or an accepted repository-managed asset mechanism is implemented.

## Recovery branches/probes

The following recovery-only refs were created from the R6.2 head while testing safe binary transport:

```text
archive/pip-kids-os-v0.12-exact
recovery/base64-tree-probe
```

The base64-tree probe demonstrated that `create_tree` does not honor a per-entry base64 encoding hint. The archive branch currently contains only isolated recovery staging and must not be merged as project source until its recovery payload is deliberately finalized/cleaned.

## Non-negotiable recovery rule

Do not repeat the original continuity failure by committing selected source fragments and calling the repository complete.

R0 closes only when:

1. the complete intended Greia source/build/test tree is represented by GitHub;
2. all required binary assets are Git-managed (or an accepted, repository-managed reproducible mechanism exists);
3. missing post-v0.12 R4/R5/R6 authority is reconciled from trustworthy source, not prose guesses;
4. a **fresh clean clone** runs the complete project `make verify` successfully;
5. the resulting commit SHA, test count and source footprint are recorded.

Until then, R0 remains OPEN and R6 must not be promoted to source-closed merely because focused R6.2 tests pass.
