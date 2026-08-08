# Shared art library

Runtime code uses individual transparent files under `icons/` through the semantic catalogue under `catalog/`.

- `source/core_icons_v1_source.png` is the canonical approved source sheet.
- `source/generated_variants/` archives later experiments and is never installed.
- `catalog/core_icons_v1_contact_sheet.png` is a developer preview and is never installed.
- `tools/extract_core_icons.py` regenerates the individual PNG variants and catalogue.

See `docs/13_ART_LIBRARY_AND_ASSET_PIPELINE.md`.
