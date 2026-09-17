# tbag-ui keymap fix — handoff test pack for the skill agent

Source under test: `adapters/opencode/tbag-ui/tui.tsx` + `index.ts` (fixed
versions are the live project copies at
`Greia/.opencode/plugins/tbag-ui/`; the diff from skill source is
`tbag-ui-fix.diff` in this directory).

## Host rule (proven by live pty repro against beta-19289, not just types)

`context.keymap.layer()` is owned by the calling component:

- Calling it in `setup()` fails plugin load — reproduced live as the
  `Plugin failed: tbag-ui` dialog, and the setup context has no Keymap
  provider ("Keymap provider is missing").
- Calling it inside a rendered component (footer slot verified live) works.
  Built-in storybook uses the same render-time pattern.
- Separate, also-fixed defect: `index.ts` used a value import of bare
  `"@opencode/plugin"`, which the server loader cannot resolve
  (`Die(ResolveMessage)` in server log). Fixed with a type-only import
  (`import type { Plugin }` + `Plugin.Plugin` annotation — erased at
  runtime). A second genuine defect caught by this suite: `import path from
  "node:path"` without `esModuleInterop` compiles to `.default.join`
  (undefined) and crashes snapshot loading; replaced with a template string.

Per-panel `f`/`escape` bindings were deliberately NOT restored: the panel
subtree's provider coverage is unmapped, so `Dashboard` stays
presentational. The global palette/slash command is layered from the footer
render (renders on every screen, verified live).

## How to run the smoke test

Requires global `tsc` and `node` (no installs; no network):

```bash
cd <this-dir>
cp <fixed-tui.tsx> ./tui-under-test.tsx
rm -rf compiled
tsc tui-under-test.tsx tui-variant-setup-layer.tsx \
  --jsx react-jsx --jsxImportSource mock-jsx \
  --target es2022 --module commonjs --outDir compiled --skipLibCheck 2>/dev/null
node run-smoke.js            # expect TBAG_UI_SMOKE_PASS
SMOKE_COMPILED=./compiled/tui-variant-setup-layer.js node run-smoke.js
                             # expect: setup threw "Keymap provider is missing"
```

(`TS2307 cannot find module` lines during compile are expected: host modules
are mocked at runtime via the require hook in `run-smoke.js`. Any other
diagnostic is a real failure. Guard against stale fixtures: `grep -c
usePlugin compiled/tui-under-test.js` must print `0`.)

`tui-variant-setup-layer.tsx` is the pre-fix shape (setup-time layer)
regenerated from the fixed file; it must FAIL with the production-identical
error (proves the test is sensitive).

## What the test proves

- `setup()` completes WITHOUT layering (the mock throws there, faithful to
  the host rule proven by live repro: layers are component-owned).
- Footer/sidebar/panel slots render with null AND populated snapshots,
  including bars, colors, worker indices, truncation, attention.
- The global command is layered during footer render and opens the
  `tbag.status` panel via slash/palette.

## Visual layer (bars, span colors, animation)

- Footer: spinner + mini bar. Sidebar: bar + phase/gate + attention.
  Panel: 30-wide wave bars, bouncing `▁▂▃▄▅▆▇█` pulse header, colored
  status/attention/workers, numbered workers, truncated objectives.
- Colors use `<span style={{ fg }}>` ONLY: live probe against beta-19289
  proved `fg=` props render white (ignored) while `style.fg` renders
  (green `#4ade80` observed in pty escapes). Both typecheck.
- Animation: 500ms frame signal read by footer/sidebar/panel renders; live
  probe showed distinct frames (`probe0`…`probe10`) across captures, so the
  host re-renders on our signal. One interval, cleared on dispose.
- Smoke assertions cover bars, worker indices, attention, spinner/pulse
  characters.

## Typecheck (separately verified, not bundled)

`tui.tsx` + `index.ts` typecheck with ZERO errors (`--strict`) against the
real `@opencode/plugin@0.0.0-beta-19507` + `solid-js@1.9.15` +
`@opentui/solid@0.5.11` + `@opencode/client@2.0.5` +
`@opencode/theme@2.0.5` types (`--jsx react-jsx --jsxImportSource
@opentui/solid --moduleResolution bundler --skipLibCheck`). Recreate with:
`npm pack @opencode/plugin@0.0.0-beta-19507 solid-js @opentui/solid@0.5.11
@opentui/core@0.5.11 @opencode/client @opencode/theme`.

## Live repro (how the rule was proven)

Scratch project + `opencode2 --standalone` under `script(1)` pty:
bare-import `index.ts` → server `Die(ResolveMessage)` + `Plugin failed`
dialog; plain-object/`import type` `index.ts` → server loads; minimal footer
probe → renders; full file with setup layer → failure dialog; without setup
layer → dialog names only the pre-existing broken `opencode-cmd-provider`
(global env issue: npm cache EACCES, unrelated); footer-render layer →
clean. TUI keystrokes via pty stdin proved unreliable, so panel-open was
verified via the smoke test, not live.
