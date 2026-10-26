# Historical Greia website design studies (23 September 2026)

**Status:** HISTORICAL / SUPERSEDED — not part of the maintained website or
ordinary-family release. This is a brief design-decision record, not a live
HTML preview or an acceptance report.

Three interactive prototypes were compared:

- **Greia for parents:** long-form night-landscape editorial story, Greia
  boot-frame replay, inspected Activity captures and family explanations.
  The owner selected this direction for the maintained `website/` project.
- **The Wonder Map:** draggable/zoomable illustrated world atlas.
- **The Scribble Machine:** a drawing-led, playful full-page exploration.

Their `docs/design/website_mocks_2026-09-23/` HTML/CSS/JS files and 3.5 MB of
preview imagery were retired from the active repository tree during the
release-hygiene pass on 2026-10-26. They are recoverable at the
**exact pre-cleanup commit** `c192c45d5efdf595d00d8c311853d40c53284ca7`:

```bash
git show c192c45d5:docs/design/website_mocks_2026-09-23/README.md
git ls-tree -r --name-only c192c45d5 docs/design/website_mocks_2026-09-23/
```

The authoritative current website is `website/index.html` with its separate
`website/README.md` provenance and disabled/unverified downloads policy.
Do not revive a September mockup as a current OS screenshot, source asset or
release acceptance result without its own review.
