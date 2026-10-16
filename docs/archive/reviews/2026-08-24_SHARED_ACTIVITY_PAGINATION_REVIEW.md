# Shared Activity Pagination Review — 2026-08-24

**Status:** source correction committed; focused/full execution and physical Acer acceptance still required  
**Scope:** launcher Activity grids across all semantic Collections (`create`, `play`, `learn`, `explore`, adaptive sub-Collections, and any future Collection using the shared grid)

## Finding

The inconsistent page counter was **not** caused by per-category hardcoded screens. The launcher has one shared Activity grid/card/pagination path in `src/greia_launcher/presentation.py`, fed by semantic Collections from the catalogue/adaptive-discovery layers.

The defect was in the shared navigation primitive: discrete Activity pages were modeled with `ScrollModel`, a selection-aware **sliding window** abstraction.

For a 6-card grid with 7 Activities, a discrete pager must produce:

```text
page 1 -> items [0:6]
page 2 -> items [6:7]
```

The historical sliding-window rule instead bounded the final start at:

```text
max_start = total - capacity = 7 - 6 = 1
```

so the second navigation step produced `[1:7]`. The visible cards changed, but the shared counter calculated:

```text
current_page = start // capacity = 1 // 6 = 0
label = 1 / 2
```

Categories whose item counts happened to align with page capacity could appear correct, masking the shared defect. A Collection such as `Crea` with a partial final page exposed it.

## Architecture correction

`src/greia_platform/ui_scroll.py` now distinguishes two different semantics:

- `ScrollModel` — genuine sliding/selection-aware windows;
- `PaginationModel` — strict discrete pages whose start is always `page_index * capacity`.

`PaginationModel` owns:

- page count;
- selection-to-page projection;
- exact page-aligned visible slice;
- bounded previous/next page movement.

The existing launcher convention `ScrollModel(capacity=N, step=N)` is temporarily compatibility-routed through `PaginationModel`, so the production shared launcher path receives the correction without a category-specific patch. New discrete-page call sites should use `PaginationModel` directly.

This compatibility seam should be removed in a later small cleanup when `presentation.py` is safely migrated to request `PaginationModel` explicitly; that cleanup must not recreate separate Collection-specific paging state.

## Regression lock

`tests/test_ui_pagination.py` covers:

- 7 items / capacity 6 -> second page `[6:7]`;
- counter identity -> `2 / 2` on that partial final page;
- totals 7–11 all begin their second page at index 6;
- exact full pages and third partial pages;
- empty/clamped selection;
- previous/next movement on real page boundaries;
- launcher compatibility routing;
- preservation of genuine sliding-list behavior.

No test execution is claimed by this document. Source presence is not PASS.

## Durable launcher invariant

Semantic Collections must never own independent Activity-grid pagination implementations.

For a shared Activity grid:

1. Collection/category selection supplies **data**, not a renderer implementation.
2. Visible card slice, page counter, dots and previous/next affordances must derive from one shared page-state semantic.
3. A partial final page starts at the exact page boundary and contains only remaining Activities; it must not repeat prior-page cards merely to fill the grid.
4. Keyboard, controller, wheel, page arrows and page dots must converge on the same selected page state.
5. Switching Collection resets/clamps selection/page through the same shared path.
6. Adaptive sub-Collections use the same paginator; they do not fork presentation logic.

## Required verification

Focused source gate:

```bash
PYTHONPATH=src python3 -m unittest tests.test_ui_pagination -v
```

Then run the repository gate before claiming aggregate green:

```bash
make verify
```

Physical/simulator acceptance should exercise at least:

- one Collection with a partial final page (especially `Crea` if its current effective child-visible count still exposes the case);
- one Collection with an exact page boundary;
- pointer arrows;
- page dots;
- keyboard/controller page movement;
- forward/back navigation;
- switching Collections and returning;
- an adaptive sub-Collection when present.

For each, verify the visible card slice and `N / total` indicator remain synchronized and that a short final page does not repeat cards from the prior page.
