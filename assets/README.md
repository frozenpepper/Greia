# Shared art library

Runtime code uses individual transparent files under `icons/` through the semantic catalogue under `catalog/`.

- `source/core_icons_v1_source.png` is the canonical approved source sheet.
- `source/generated_variants/` archives later experiments and is never installed.
- `source/achievements/` contains reusable vector masters for Greia medals, trophies and special achievement awards. Their current low-resource Pygame counterparts are rendered and cached by `greia_platform.pygame_achievements`; the SVG masters are not decoded at runtime.
- `catalog/core_icons_v1_contact_sheet.png` is a developer preview and is never installed.
- `tools/extract_core_icons.py` regenerates the individual PNG variants and catalogue.

See `docs/13_ART_LIBRARY_AND_ASSET_PIPELINE.md` and `assets/source/achievements/README.md`.
