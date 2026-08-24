# Shared Activity Pagination Handover — 2026-08-24

**Current status:** source correction + regressions committed; execution evidence pending  
**Blocking platform phase:** unchanged (R7 remains blocking)

## User-visible defect

In some semantic Collections, moving to the next Activity panel/page changed the visible cards but left the indicator at `1 / 2`. `Crea` exposed the problem. Other Collections appeared correct depending on their effective item count.

## Root cause

There is **not** one hardcoded display per Collection. `src/greia_launcher/presentation.py` owns the shared Activity grid/card/pagination presentation and receives Collection data from the catalogue/adaptive-discovery layers.

The shared path used `ScrollModel(capacity=page_capacity, step=page_capacity)` for discrete paging. `ScrollModel` historically clamped a final window to `total - capacity`, appropriate for a sliding list but wrong for pages. With 7 items and capacity 6 it produced start `1` instead of `6`, so the visible slice shifted while the counter (`start // capacity`) still resolved to page 1.

## Current source correction

`src/greia_platform/ui_scroll.py` now contains a separate `PaginationModel` for strict page-aligned slices. Existing launcher-style `ScrollModel(step == capacity)` calls delegate to it as a compatibility seam; true sliding `ScrollModel` behavior remains separate.

No Collection/category special case was introduced.

Regression source:

```text
tests/test_ui_pagination.py
```

Durable analysis:

```text
docs/reviews/2026-08-24_SHARED_ACTIVITY_PAGINATION_REVIEW.md
```

## Required next evidence

Run:

```bash
PYTHONPATH=src python3 -m unittest tests.test_ui_pagination -v
make verify
```

Then deploy current launcher/platform Python source to the reference Acer through the normal safe development update path and verify at least:

1. `Crea` (or any Collection currently producing a partial final page): `1/N -> 2/N`, with only remaining cards on final page;
2. a Collection whose count exactly fills its pages;
3. pointer previous/next arrows;
4. page dots;
5. PageUp/PageDown or controller-equivalent navigation;
6. switching Collections and returning resets/clamps page state;
7. an adaptive sub-Collection when present.

Do not claim physical PASS until the actual Acer display has been observed.

## Follow-up cleanup

When editing the large launcher presentation file is convenient and concurrency-safe, migrate its discrete page call sites from the historical `ScrollModel(capacity=N, step=N)` compatibility spelling to `PaginationModel(capacity=N)` explicitly. That cleanup should not change behavior and must not create Collection-specific paging implementations.
