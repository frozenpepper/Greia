# T-BAG skill defect report — OpenCode 2 host detection (installer cannot reach the v2 adapter set)

**To:** agent working on the T-BAG skill (`/Users/taio84/.config/opencode/skills/t-bag`, HEAD `57a0de3` "RC56: support OpenCode 2 server plugins")
**From:** T-BAG parent run R2, project `/Users/taio84/Works/Bimbe_GIOCHI/Greia OS/Greia`
**Date:** 2026-09-17
**Severity:** installer cannot produce the correct adapter set on an OpenCode 2 parent host; no workaround exists within the installer's contract.

## 1. Environment (observed fact)

- Parent host is **OpenCode 2**: binary `/usr/local/bin/opencode2` → `../lib/node_modules/@opencode/cli/bin/opencode2.exe`, `--version` prints exactly `opencode2 v0.0.0-beta-19289`.
- PATH `opencode` is still the 1.x line: `/usr/local/bin/opencode` → `../lib/node_modules/opencode-ai/bin/opencode.exe`, `--version` prints `1.18.31`.
- Project state before report: `.opencode/plugins/tbag.js` (v1 transport) + `.opencode/plugins/tbag-status-tui-v1.tsx` + `.opencode/tui.json` registering the v1 companion — i.e. the major-1 set, installed while detection saw 1.18.31. Correct per the old host, wrong for the current one.

## 2. Reproduction

```bash
# What the installer sees (PATH opencode):
python3 -c "
import sys; sys.path.insert(0,'<skill>/scripts')
from opencode_tui_compat import detect_opencode_version
print(detect_opencode_version())"
# -> ('1.18.31', 1)

# What the real parent host reports (via a temporary PATH shim
# mapping `opencode` -> /usr/local/bin/opencode2; shim removed afterwards):
# -> ('0.0.0-beta-19289', 0)
```

Detection source: `scripts/opencode_tui_compat.py::detect_opencode_version` runs `["opencode", "--version"]` and takes the first numeric token. For `opencode2 v0.0.0-beta-19289` the tokens are `opencode2` (non-numeric) and `v0.0.0-beta-19289` → major **0**.

## 3. Consequence in the installer

`scripts/install_harness_adapter.py::install_opencode` branches on `major`:

- `major == 1` → `tbag.js` (V1 hooks) + `tbag-status-tui-v1.tsx` + `tui.json` entry.
- `major == 2` → `tbag-v2.js` (native `id` + `setup(ctx)`) + `tbag-ui/{index.ts,tui.ts,tui.tsx}`, removes stale v1 tsx and its `tui.json` entry.
- else → stable `tbag.js` transport only, no UI guess.

So on this host the installer can only produce the v1 set (wrong generation — RC56 notes the two transports are not interchangeable) or the unsupported-major set (v1 transport, no UI). **The correct v2 set is unreachable.** `OPENCODE.md`'s contract ("the installer detects the local host generation with `opencode --version`") does not hold when the parent runs under the `opencode2` beta binary.

## 4. Suggested fix directions (skill agent decides)

- Teach `detect_opencode_version` about the beta: e.g. treat binary basename `opencode2`, or a `0.0.0-beta` version string from it, as major 2. Consider probing `opencode2 --version` as a fallback/override when `opencode` resolves to 1.x, since both binaries coexist here.
- Optional: explicit installer override (e.g. `--generation 2`) for hosts whose version strings carry no usable major. Must not become a silent default: unknown stays transport-only per current policy.
- Keep invariants: installer proves file on disk only; never guess a TUI API; keep the major-1 path byte-identical; keep backup behavior for overwritten files.
- Existing coverage to extend, not replace: `tests/test_rc56_opencode2_server.py`, `tests/opencode_v2_plugin_runtime.mjs`, `tests/test_components.py`.

## 5. Acceptance for the fix (verifiable in this project)

1. With the parent host running under `opencode2`, re-run `scripts/install_harness_adapter.py --harness opencode --project-root <Greia project>` and observe `opencode_major: 2`, `transport_generation: v2`, `tui_generation: v2`; `.opencode/plugins/tbag.js` becomes the v2 adapter; `.opencode/plugins/tbag-ui/{index.ts,tui.ts,tui.tsx}` installed; stale `tbag-status-tui-v1.tsx` removed; its `tui.json` entry removed.
2. Re-run with only a 1.x host visible and observe the v1 set unchanged.
3. Skill test suite green.

## 7. RC57 verification (2026-09-17, skill HEAD `de3935b`)

RC57 ("detect active OpenCode host generation") implements the right mechanism —
prefer the active parent via `OPENCODE_PID`, identity-hint `opencode2` /
`/@opencode/cli/` as generation 2 — but it receives **no signal** in this
session, so detection still yields `('1.18.31', 1)`:

- `OPENCODE_PID` is **unset** in the tool subprocess environment
  (`echo $OPENCODE_PID` → empty; only `OPENCODE_EXPERIMENTAL_OUTPUT_TOKEN_MAX`
  and `OPENCODE_TERMINAL` are present).
- Direct host proof (one-time bounded diagnostic, not a scan): the tool
  shell's parent PID 37966 is
  `/usr/local/lib/node_modules/@opencode/cli/bin/opencode2.exe serve --service`
  (now reparented to PID 1; still alive). The parent host therefore **is**
  OpenCode 2, and `_generation_hint` would return 2 had the PID been available.
- So either this beta (`v0.0.0-beta-19289`, running as `serve --service`)
  does not export `OPENCODE_PID` to tool subprocesses at all, or the tool
  runner strips it. Suggested direction: when `OPENCODE_PID` is unset, fall
  back to a **bounded ancestry walk** (own PID upward, a handful of levels,
  `ps -o command=` per level — no global scan) applying the existing
  `_generation_hint` to each ancestor command. That resolves exactly this
  case with no dual-install ambiguity. Keep the current refusal to prefer
  `opencode2` by mere installation presence.
- The installer was deliberately **not** re-run: with major still 1 it would
  reinstall the v1 set on a v2 host.

## 6. Explicit non-goals / constraints (unchanged)

- Do not hand-install v2 files into the project outside the installer to "unblock" this run; the next installer run would flip-flop the generation. The parent run (R2) proceeds on manual ticks meanwhile and is not blocked on this fix.
- No credentials, mounts, or privileged operations are involved. No temp files were left behind (the PATH shim was removed after the probe).

## 9. tbag-ui failure (skill source defects — first diagnosis SUPERSEDED, see §11)

After the §8 install, the host showed a `Plugin failed: tbag-ui` dialog (owner
quoted a keymap-provider message). The first code-read diagnosis recorded here
(render-time `usePlugin`/`keymap.layer` in `Dashboard` as the thrower, setup
layer as the safe pattern) was INVERTED and is retracted. Live pty repro
against beta-19289 proved the opposite (details §11):

- `context.keymap.layer()` in `setup()` fails plugin load (no component
  owner/provider at setup time). The SDK's own doc agrees: layer creates "a
  reactive keymap layer owned by the calling component".
- The same call inside a rendered footer-slot component works (visible probe
  text, no dialog); built-in storybook uses the identical render-time pattern.
- Separately, `index.ts`'s value import of bare `"@opencode/plugin"` fails
  server load (`Die(ResolveMessage)`): the server loader has no such mapping
  (it exists only in the TUI runtime-module pipeline).

Coverage gap stands, inverted: no skill test executes setup/render paths, so
neither the setup-time throw nor the unresolvable bare import was caught.
`tests/test_rc46_supervision.py` asserts only string presence.

## 10. Project-local full fix (2026-09-17, pending skill-side port)

Final shipped state in `Greia/.opencode/plugins/tbag-ui/` (skill source
untouched). Three stacked defects fixed:

1. `index.ts` value-imported bare `"@opencode/plugin"` → server
   `Die(ResolveMessage)`, whole plugin failed to load. Now `import type
   { Plugin }` + `Plugin.Plugin` annotation (erased at runtime; typecheck
   clean). Server loads.
2. Setup-time `context.keymap.layer()` → plugin load failure ("Keymap
   provider is missing": layers are component-owned; setup has no
   provider). The global palette/slash command is now layered from the
   footer-slot render, which runs under a provider on every screen
   (verified live with a visible probe).
3. `import path from "node:path"` without `esModuleInterop` → `.default`
   undefined at runtime, crashing snapshot loads. Template string now.

Kept deliberately conservative: `Dashboard` stays presentational (per-panel
`f`/`escape` not restored — panel-subtree provider coverage is unmapped),
footer no longer advertises those keys.

Verification (all executed):
- Live pty repro (`opencode2 --standalone` in a scratch project): tbag-ui
  loads with zero failure dialogs (only the pre-existing global
  `opencode-cmd-provider` env failure: broken npm cache EACCES, unrelated);
  footer probe text rendered.
- `tsc --noEmit --strict` on `tui.tsx` + `index.ts` vs real beta-19507 SDK
  types: zero errors.
- Mock-host smoke suite: fixed file `TBAG_UI_SMOKE_PASS` (setup clean, all
  slots render null + full snapshots, slash opens panel); setup-layer
  variant fails with the production-identical `setup threw: Error: Keymap
  provider is missing`. Fixture identity guarded.
- Handoff pack (80K, self-contained): `sdk/smoke/` = `README.md`,
  `run-smoke.js`, 3 mocks, `tui-under-test.tsx` (fixed copy),
  `tui-variant-setup-layer.tsx` (must-fail fixture),
  `tbag-ui-fix.diff` (unified diff vs skill source, incl. `index.ts`),
  `compiled/`. Needs only global `tsc` + `node`.

DIVERGENCE NOTE: project copy differs from skill source. The next installer
run overwrites it (fix lost, crash back) unless the skill ports this first.
Port order: `index.ts` type-only import, footer-render layering, path fix.

## 12. Transport supervision plane dead: wrong tool name (2026-09-17)

Symptom: parent kept stopping; heartbeat never enrolled (no
`TBag/runs/<id>/.transport/opencode.json` ever appeared); launches never
auto-armed observers; only owner turns moved the run.

Root cause: `adapters/opencode/tbag-v2.js` gates both `tool.execute`
hooks on `event.tool !== "bash"`. The v2 host has no `bash` tool — its
inventory (proven from the host binary's tool dispatch table) is `shell`,
`glob`, `read`, `grep`, `webfetch`, `websearch`, `write`, `edit`,
`subagent`, `execute`, `patch`, `question`, `skill`. Every hook invocation
returned early, so enrollment, auto-arm, observer repair and the
follow-guard were all silently dead. (Also cleared along the way: the
`failed to load plugin … tbag.js … Expected object at ["default"]` log
lines are Sep-16 v1-era (v1 file has no default export); the v2 module
shape imports cleanly under node. Later "12:05 failures"greps were
self-matches — the server logs our own grep command lines.)

Verification of the probe: `echo "dsd_attempt.py follow"` (matches the
follow-guard regex) executed WITHOUT the expected guard error → hooks
provably blind to our calls.

Fix (project-local `Greia/.opencode/plugins/tbag.js`, skill must port):
both hooks now match `"shell"`. Next tick enrolled immediately:
`.transport/opencode.json` created with `adapter_pid` = live host,
`parent_sessions` = current session, `last_arm_error: null`. Project-local
divergence noted for the skill agent (v1 file keeps `"bash"`).

## 11. Visual upgrade (2026-09-17, same handoff pack)

Owner missed the v1 progress bar (v2 footer/sidebar had text only) and asked
for color + motion. Shipped in the same project files:

- Footer: spinner (`⠋…⠏` while workers live, `●` idle) + 8-wide mini bar.
- Sidebar: spinner + 14-wide bar + phase/gate + red attention line.
- Panel: 30-wide wave bars (bright pulse head travels with the frame),
  bouncing `▁…█…▁` pulse header, colored status (green/yellow/blue/gray),
  red attention, blue ◆ analysts / green ● grunts, numbered workers,
  objectives truncated at 76 chars.
- 500ms frame signal, cleared on dispose; motion advances on host
  re-renders (proven: distinct `probe0`…`probe10` frames across captures).

Two empirically settled rules (live pty probes, beta-19289):

- Colors ONLY via `<span style={{ fg }}>` — `fg=` props render white
  (ignored). Both forms typecheck; only span-style paints.
- Slot renders tick on our signals (frames advanced), so the interval
  animation is live, not decorative.

Same evidence bar (typecheck zero errors incl. colors, smoke PASS incl.
bar/index/attention/spinner assertions, setup-layer variant fails
identically, live pty load clean). `tbag-ui-fix.diff` regenerated
(268 lines).

## 8. RC58 verification and new ancestry-matching defect (2026-09-17, skill HEAD `85f16ef`)

RC58 added the requested bounded-ancestry fallback. Standalone detection then
returned `('0.0.0-beta-19289', 2)` when the installer/tool process was a direct
child of PID 37966 (`opencode2.exe serve --service`).

However, the installer still returned major 1 when invoked through a wrapper
shell. Root cause found by direct probing:

- Ancestor command matching examines the complete command line, including a
  transient `/bin/zsh -c '...'` wrapper.
- The installer’s own required argument, `--harness opencode`, contains a bare
  `opencode` token. `_generation_hint()` therefore classifies the wrapper as
  generation 1 at hop 0 and stops before reaching PID 37966.
- It then probes PATH `opencode` (`1.18.31`) and installs the v1 adapter set on
  a v2 host. The ancestry result is nondeterministic because it depends on
  whether a wrapper shell is present.

The same hazard applies to other bare-`opencode` CLI/model tokens. Suggested
correction: match generation identity against `argv[0]`/executable basename or
known install-path identity, not against arbitrary command-line tokens.

Workaround used for this one-time install only: verified PID 37966 was alive as
`opencode2.exe serve --service`, exported `OPENCODE_PID=37966` for that
installer invocation, and obtained major 2. The installer then installed
`tbag-v2.js` as `.opencode/plugins/tbag.js`, installed
`.opencode/plugins/tbag-ui/{index.ts,tui.ts,tui.tsx}`, removed stale
`tbag-status-tui-v1.tsx`, and removed its `tui.json` entry. Restart/reload is
still required for live activation.
