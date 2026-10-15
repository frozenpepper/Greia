# Shared art library

Runtime code uses individual transparent files under `icons/` through the semantic catalogue under `catalog/`.

- `source/icons/core/v1/*.svg` are the flat-vector masters of the core semantic icons (`catalog/core_icons_v1.toml`, authored under `docs/design/GREIA_SVG_AUTHORING_RULES.md`). `make assets` (`tools/build_core_icons.py`) renders them with `rsvg-convert` to `icons/core/v1/{64,128,256}/`; `make assets-check` (`--check`) verifies the committed PNGs match a fresh render and that no master/PNG is uncatalogued. The glossy raster source sheet and `tools/extract_core_icons.py` were retired on 2026-10-15 (git history only).
- Earlier generated-variant experiments (`source/generated_variants/`) were retired on 2026-10-15; they remain in git history only.
- `source/achievements/` contains reusable vector masters for Greia medals, trophies and special achievement awards. Their current low-resource Pygame counterparts are rendered and cached by `greia_platform.pygame_achievements`; the SVG masters are not decoded at runtime.
- For a family preview use `python3 tools/visual_family_contact_sheet.py --output <scratch>/family.png` (never inside the repository).

See `docs/13_ART_LIBRARY_AND_ASSET_PIPELINE.md` and `assets/source/achievements/README.md`.
