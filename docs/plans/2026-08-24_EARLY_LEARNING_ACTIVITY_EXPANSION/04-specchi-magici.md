# Session 04 — Specchi Magici: geometry and symmetry

**Provider calls:** forbidden; repository art plus local SVG work only
**Prerequisite:** Sessions 00–03 accepted and committed
**Commit:** `feat(activity): add Specchi Magici symmetry puzzles`

## Outcome

`org.greia.specchi-magici` delivers six deterministic mirrored mosaics using shape composition, orientation, and exact vertical reflection, distinct from Shape Garden.

## Implementation checkpoint — 2026-08-24

The source implementation is complete, verified, and accepted:

Current source shape:

```text
activities/specchi_magici/
  activity.toml
  main.py
  mirror_model.py
  mirror_services.py
  mirror_audio.py
  mirror_art.py
  mirror_renderer.py
  mirror_app.py
  locales/{it,en}.json
  assets/source/icon.svg
  assets/icon.png
tests/test_activity_specchi_magici.py
```

Evidence:
- 12/12 focused unit and integration tests passing (`tests/test_activity_specchi_magici.py`).
- Cumulative test suite passing: 103 tests green across early learning and platform contracts.
- Repository-wide `make verify` completely passing: 1,231 unit tests green, all 24 activities valid, footprint and shell checks green.
- Package validation digest: `sha256 97ad0c0171209b908b4423a6ab3632f68cffa183c5eb0c3de5e3b532f1ebd374`.
- Visual review executed for Italian and English locales and multiple game modes (Level 1 circles/squares, Level 2 triangles, Level 3 mixed rotations, Level 5 two-sided symmetry, Shining Gallery completion). Exact vertical axis reflection and piece tray selection ring.
- Audio: Prepared procedural tones (`place`, `correct`, `retry`, `complete`).
- Simulator integration: Supervisor launch and lifecycle tested cleanly.

## Preconditions

- Pull current `main`; verify prior cumulative gate.
- Read the same specialist documents required by Session 01.

## Allowed files

```text
activities/specchi_magici/**
tests/test_activity_specchi_magici.py
docs/plans/2026-08-08_ARCHITECTURE_REMEDIATION_AND_PLATFORM_COMPLETION.md
docs/plans/2026-08-20_GREIA_VISUAL_FOUNDATION_AND_ASSET_SYSTEM.md
docs/handovers/GREIA_VISUAL_SYSTEM_RESUME.md
HANDOVER.md
```

## Forbidden changes

- No free drawing, continuous rotation, diagonal symmetry, framebuffer comparison, duplicate Shape Garden loop, or platform edit.

## Evidence and source decisions

Head Start includes shape recognition across orientation and composition from components. A discrete 8×6 board makes reflection correctness exact/testable and keeps rendering bounded.

## Exact implementation

1. Manifest: `org.greia.specchi-magici`, key `activity.specchi_magici.title`; `it,en`; collections `learn,create`; tags `puzzles,making`; education `geometry,spatial_reasoning,symmetry`; difficulty 3, age 5–7, adaptive 2–5; pointer; required `display,pointer`, optional `touch`; milestone `mirror.mosaic_completed`, completion `mirror.gallery_completed`; storage 1.
2. Create thin `main.py` and `mirror_model/content/services/art/renderer/app.py`. Define `ShapeKind(CIRCLE,SQUARE,TRIANGLE,SEMICIRCLE)`, `Piece(kind,color,rotation_quarters)`, `CellPiece(row,col,piece)`, `MosaicPuzzle(rows,columns,axis_col,givens,required)`, `MirrorSession`.
3. Board is 8×6 with axis between columns 3/4. Reflection is `mirror_col = 7 - col`; a total shape-specific table maps rotation. Circle/square normalize to zero; triangle/semicircle map explicitly.
4. L1 circles/squares no rotation; L2 add triangles; L3 mixed rotation; L4 compose butterfly/flower/rocket silhouettes; L5 one missing piece on each side. Six deterministic puzzles/set.
5. Drops snap to cells. Occupied/wrong/outside drops return to tray, wobble gently, and highlight source-to-mirror path. Correct pieces lock; Activity-owned undo reverses one placement before completion.
6. Completion compares semantic pieces, never pixels. After puzzle, shimmer axis/pairs; after six use `PygameCompletionScreen`.
7. Persist `specchi_magici.progress.v1` with level/≤8 summaries. Emit exact milestone/completion once.
8. Reuse `character.lilli`; adapt block material/shadows. Create mirror, pieces, silhouettes, icon, opaque background. Cache `(shape,color,rotation,size)` ≤64; clear on viewport recreation.

## Tests

- Reflection/rotation covers every shape/orientation and mirroring twice returns normalized original.
- Generator yields solvable unique sets and no piece on axis gap.
- Wrong/occupied/outside drop preserves inventory; undo restores one placement.
- Semantic completion/events once; cache ≤64; idle/terminal/safe geometry.

## Local gate

```bash
find activities/specchi_magici -type d -name __pycache__ -prune -exec rm -rf {} +
PYTHONPATH=src:tests:. python3 -m unittest tests.test_activity_specchi_magici -v
PYTHONPATH=src:tools python3 tools/validate_activity.py activities/specchi_magici
```

Expected: tests/validation exit 0; no cached bytecode remains.

## Cumulative gate

```bash
PYTHONPATH=src:tests:. python3 -m unittest tests.test_activity_luci_di_momo tests.test_activity_casa_del_dieci tests.test_activity_bottega_delle_misure tests.test_activity_specchi_magici tests.test_activity_contract tests.test_activity_audience_manifest tests.test_first_party_activity_audience_metadata tests.test_first_party_activity_readiness tests.test_core_activity_system_safe_ui tests.test_activity_ui tests.test_activity_viewport tests.test_localization tests.test_typography_emoji -v
```

Expected: exit 0 with four math suites and named contracts green.

## Stop conditions

- Any puzzle relies on pixels, unbounded surfaces, or ambiguous mirror rules.
- Interaction is materially the same as Shape Garden free placement.

## Handoff

Return standard packet plus mirror table, seeded puzzle summaries, cache/event proof, asset hashes, and SOURCE label.
