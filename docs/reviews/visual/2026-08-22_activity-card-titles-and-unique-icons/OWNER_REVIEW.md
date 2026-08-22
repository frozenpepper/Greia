# Greia OS Owner Review
## Activity Card Titles and Unique Icons
**Review Date:** 2026-08-22  
**Status:** ACCEPTED / PASS

## Decision

This tranche is accepted.

The launcher title/icon contract now clears the earlier product blockers:

- Activity names are no longer trapped in the previous one-line unreadable presentation.
- Package-owned icon identity is now the normal first-party rule rather than an exception.
- Contain-fit icon treatment fixes the earlier clipping/crowding problem.
- The fail-soft fallback path is explicitly evidenced.
- The authoring/runtime contract is now much healthier for future Activities.

## Owner evidence review

The submitted bundle demonstrates the intended contract well enough to accept the tranche:

- `10-long-localized-title.png` clearly proves the long-title handling path and the full-title disclosure pill.
- `11-non-square-package-icon.png` proves ratio-preserving contain-fit behavior for both wide and tall package icons.
- `12-icon-fallback.png` proves corrupt/missing package icons fall back safely to the standard robot icon.
- The core launcher captures show first-party Activities now have distinct package-owned icon identities instead of recycling the same tiny set.

Accepted implementation direction:

- two-line centered titles;
- grapheme-safe defensive truncation;
- hover/selection disclosure;
- separate bounded caches;
- package-owned first-party icon migration.

## Non-blocking review note

For future evidence rounds, captures intended to prove hover/focus disclosure should make the disclosure pill visually unmistakable in the screenshot itself, as in `10-long-localized-title.png`.

## Outcome

**Accepted.**

This closes the launcher title-legibility + unique-icon tranche and establishes the baseline for launcher-shell productization.
