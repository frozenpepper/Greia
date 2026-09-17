# How the T-BAG status plugin was made to work on OpenCode 2 — full account

Date: 2026-09-17. Host: `opencode2 v0.0.0-beta-19289`
(`/usr/local/lib/node_modules/@opencode/cli/bin/opencode2.exe`, running as
`serve --service`, PID 37966). Project:
`/Users/taio84/Works/Bimbe_GIOCHI/Greia OS/Greia`.
Skill repo HEADs touched along the way: RC56 → RC57 → RC58.

## 0. Starting position

The project carried the OpenCode 1 adapter set: `.opencode/plugins/tbag.js`
(V1 hooks transport) + `tbag-status-tui-v1.tsx` + a `tui.json` entry, installed
while PATH `opencode` was 1.18.31. The owner moved daily driving to the
OpenCode 2 beta (`/usr/local/bin/opencode2`, coexisting with the 1.x binary),
which needs the v2 set: native `setup()` transport (`tbag-v2.js`) +
`tbag-ui/{index.ts,tui.ts,tui.tsx}`. Nothing in the installer could produce it
(see §1).

## 1. Installer could not see the v2 host (three rounds)

**Round 1 — wrong binary.** `detect_opencode_version()` runs
`opencode --version` from PATH → `1.18.31`, major 1 → installs the v1 set on
a v2 host. (RC56 stated the transports are not interchangeable.)

**Round 2 — beta version string.** Pointing PATH at `opencode2` gives
`opencode2 v0.0.0-beta-19289`, which the parser reads as major **0** →
"unsupported" branch (v1 transport, no UI). Skill fix RC57: prefer the active
parent via `OPENCODE_PID`, recognize `opencode2`/`/@opencode/cli/` identity
as generation 2.

**Round 3 — no signal.** `OPENCODE_PID` is unset in tool subprocess
environments, so RC57 still yielded major 1. Host proof (bounded, one PID,
not a scan): the tool shell's parent was PID 37966 =
`.../@opencode/cli/bin/opencode2.exe serve --service`. Skill fix RC58:
bounded ancestry walk. That worked for direct children — but through a
wrapper shell the walk matched the wrapper's own command line, and the
installer's required argument `--harness opencode` contains a bare
`opencode` token, so `_generation_hint()` returned 1 at hop 0 and stopped
before reaching the host (nondeterministic by invocation shape). Reported
with reproduction; suggested correction: match identity against
`argv[0]`/executable rather than arbitrary command-line tokens.

**What finally installed the v2 set:** verified PID 37966 alive as the
opencode2 server, exported `OPENCODE_PID=37966` for one installer run →
major 2, `tbag-v2.js` transport, `tbag-ui/` installed, stale v1 companion
and its `tui.json` entry removed. Restart/reload still required for
activation (installer proves disk, host proves live).

## 2. Plugin failed to load: unresolvable bare import (server side)

First TUI start showed `Plugin failed: tbag-ui`. Server log
(`--standalone --print-logs`) gave the cause verbatim:

```text
failed to load plugin .../tbag-ui ... Cause([Die(ResolveMessage:
Cannot find package '@opencode/plugin' imported from .../tbag-ui/index.ts)])
```

`index.ts` value-imported bare `"@opencode/plugin"`. The host maps
`@opencode/plugin/tui` (and `solid-js`, `@opentui/*`) only inside the TUI
runtime-module pipeline (proven from the binary's module table); the server
loader resolves with plain Bun resolution, where the bare specifier does not
exist (project `.opencode/node_modules` holds only the v1
`@opencode-ai/plugin`). Removing `index.ts` entirely makes the directory
invisible to discovery, so the entry must stay — but dependency-free.

**Fix:** `import type { Plugin }` + `const plugin: Plugin.Plugin`
(server-side `Plugin` namespace per SDK types). Type-only imports are erased
before execution, so the loader never resolves anything; `Plugin.define` is
the identity function at runtime anyway. Verified: server loads, dialog
clears. (First attempt used a non-existent `Definition` root export —
caught by the type gate; corrected to `Plugin.Plugin`.)

## 3. "Keymap provider is missing": setup-time layering (retracted first diagnosis)

With loading fixed, the host still reported a keymap-provider failure. The
first code-read diagnosis (render-time `usePlugin`/`layer()` in `Dashboard`
as the thrower) was **wrong** — removing it changed nothing. A pty-driven
repro matrix (`opencode2 --standalone` in a scratch project under
`script(1)`, 45s captures, success = no `Plugin failed` dialog) isolated it:

- Full file with setup-time `context.keymap.layer(...)` → failure dialog.
- Same file with that block commented out → dialog clear.
- Minimal footer probe calling `context.keymap.layer(...)` **inside the
  footer render** → renders visibly, no dialog.

SDK doc agrees: layer creates "a reactive keymap layer owned by the calling
component" — setup has no owner/provider; a rendered component does
(built-in storybook layers in render too). **Final shape:** the global
palette/slash command is layered from the footer-slot render (renders on
every screen, keeping the command available); `Dashboard` stays
presentational. Per-panel `f`/`escape` was deliberately not restored —
panel-subtree provider coverage is unmapped, and an unverified shortcut is
worse than none.

## 4. Two more genuine defects found by testing, both fixed

- `import path from "node:path"` without `esModuleInterop` compiles to
  `.default.join` (undefined) and crashes snapshot loading at runtime.
  Template string now. (Caught because the pristine file failed the smoke
  test's footer assertion.)
- `timer.unref?.()` assumes Bun's Timer type; narrowed with a cast so the
  file typechecks without host globals (`declare const Bun: any` likewise).

## 5. Visual upgrade (same files)

- Colors ONLY via `<span style={{ fg }}>` — live probe proved `fg=` props
  render white (ignored) while `style.fg` paints green in the pty escapes.
  Status header, attention, worker glyphs, phase checks.
- Motion: 500ms frame signal read by footer/sidebar/panel renders —
  spinner (`⠋…⠏`, green live / gray idle), traveling pulse head on 30-wide
  wave bars, bouncing `▁…█…▁` header pulse. Probe showed distinct frames
  across captures, so the host re-renders on our signal. One interval,
  cleared on dispose.
- Bars everywhere (footer mini-bar answers the original "no progress bar":
  the old v2 footer/sidebar were text-only), numbered workers, truncated
  objectives, per-worker health/CPU/log lines.

## 6. Verification battery (all executed, none claimed)

- **Live pty matrix** (scratch `--standalone` TUI, dialog presence as the
  signal): bare-import index → fail; plain/type-only index → load; minimal
  probe → renders; setup-layer file → fail; footer-layer file → clean;
  final visual file → clean. (TUI keystrokes via pty stdin proved
  unreliable, so panel-open is covered by the smoke test, not live.)
- **Strict typecheck, zero errors**, `tui.tsx` + `index.ts`, against the
  real `@opencode/plugin@0.0.0-beta-19507` + `solid-js@1.9.15` +
  `@opentui/solid@0.5.11` + `@opencode/client@2.0.5` +
  `@opencode/theme@2.0.5` types. Also confirmed `LocationRef.directory`
  (project-root line was already correct) and `fg?: string | RGBA`.
- **Mock-host smoke suite**: setup completes with zero setup-time layers;
  footer/sidebar/panel render under null AND populated snapshots (bars,
  indices, spinner/pulse, attention asserted); slash command opens the
  panel. Must-fail fixture (setup-time layer) dies with the
  production-identical `setup threw: Error: Keymap provider is missing`.
  Fixture identity guarded (`grep -c usePlugin`).

## 7. Handoff pack for the skill agent

`/private/var/folders/hm/ctvd76zd7qndz1t0cchm9yc80000gn/T/opencode/sdk/smoke/`
(~100K, needs only global `tsc` + `node`): `README.md`, `run-smoke.js`, 3
mocks, `tui-under-test.tsx` (fixed copy), `tui-variant-setup-layer.tsx`
(must-fail fixture), `tbag-ui-fix.diff` (268-line unified diff vs skill
source, incl. `index.ts`), `compiled/`. SDK tarballs were removed after the
gate (recreate via the `npm pack` line in the README). Working log with
section detail:
`/private/var/folders/hm/ctvd76zd7qndz1t0cchm9yc80000gn/T/opencode/TBAG-skill-opencode2-detection-report.md`
(§§1–11).

## 8. Caveats and remaining notes

- Project copy diverges from skill source: the next installer run
  overwrites it (fix lost, crash back) until the skill ports §§2–5, in the
  order: `index.ts` type-only import, footer-render layering, path fix,
  span-style colors.
- `opencode-cmd-provider` also shows as failed in `/plugins`: pre-existing
  environment issue (npm cache `EACCES` on a foreign cache path),
  unrelated to this work.
- Panel-open was verified via mocks, not live (pty input unreliable).
- Per-panel `f`/`escape` intentionally unrestored (unmapped provider
  coverage); restore only with proof.
- No credentials, mounts, or privileged operations anywhere. Scratch
  projects, SDK tarballs, tarballs extracts, and shim dirs were removed;
  only the 100K handoff pack and the report remain, both outside the repo.
  The Greia working tree is clean (plugin files are gitignored).
