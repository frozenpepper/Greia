"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
const jsx_runtime_1 = require("mock-jsx/jsx-runtime");
const tui_1 = require("@opencode/plugin/tui");
const solid_js_1 = require("solid-js");
const REFRESH_MS = 5000;
function clampPercent(value) {
    const n = Number(value ?? 0);
    return Number.isFinite(n) ? Math.max(0, Math.min(100, n)) : 0;
}
function progressBar(value, width = 16) {
    const pct = clampPercent(value);
    const filled = Math.round((pct / 100) * width);
    return `${"█".repeat(filled)}${"░".repeat(Math.max(0, width - filled))}`;
}
function truncate(text, max = 76) {
    const s = String(text ?? "");
    return s.length > max ? `${s.slice(0, max - 1)}…` : s;
}
function statusColor(status) {
    const s = String(status ?? "").toLowerCase();
    if (s === "active")
        return "#4ade80";
    if (s === "completed")
        return "#38bdf8";
    if (s === "human-blocked" || s === "paused-by-user")
        return "#facc15";
    return "#9ca3af";
}
const SPINNER = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"];
const PULSE = ["▁", "▂", "▃", "▄", "▅", "▆", "▇", "█", "▇", "▆", "▅", "▄", "▃", "▂"];
function waveBar(pct, width, frame) {
    const filled = Math.round((clampPercent(pct) / 100) * width);
    const head = ((frame % width) + width) % width;
    return Array.from({ length: width }, (_, i) => {
        const ch = i < filled ? "█" : "░";
        return (0, jsx_runtime_1.jsx)("span", { style: i === head ? { fg: "#a7f3d0" } : undefined, children: ch });
    });
}
function shortSession(value) {
    const text = String(value ?? "");
    return text ? (text.length > 12 ? `${text.slice(0, 9)}…` : text) : "no-session";
}
function duration(seconds) {
    const raw = Number(seconds ?? 0);
    if (!Number.isFinite(raw) || raw < 0)
        return "?";
    const whole = Math.floor(raw);
    const h = Math.floor(whole / 3600);
    const m = Math.floor((whole % 3600) / 60);
    const s = whole % 60;
    return h ? `${h}h ${String(m).padStart(2, "0")}m` : m ? `${m}m ${String(s).padStart(2, "0")}s` : `${s}s`;
}
function workerHealth(worker) {
    const processAlive = Boolean(worker?.process?.worker?.alive ?? worker?.process_alive ?? worker?.state === "running");
    const observer = worker?.observer?.healthy;
    const attention = worker?.attention;
    if (attention)
        return `⚠ ${attention}`;
    if (!processAlive)
        return "○ process down";
    if (worker?.observer?.known === false)
        return "● process alive";
    if (!observer)
        return "◐ observer missing";
    return "● healthy";
}
function Worker(props) {
    const w = () => props.worker;
    const glyph = w().tier === "analyst" ? "◆" : "●";
    const glyphColor = w().tier === "analyst" ? "#38bdf8" : "#4ade80";
    return ((0, jsx_runtime_1.jsxs)("box", { flexDirection: "column", marginBottom: 1, children: [(0, jsx_runtime_1.jsxs)("text", { children: [`[${props.index + 1}] `, (0, jsx_runtime_1.jsx)("span", { style: { fg: glyphColor }, children: glyph }), ` ${w().authority ?? "Worker"} · ${w().role ?? "?"} · ${duration(w().elapsed_seconds)}`] }), (0, jsx_runtime_1.jsx)("text", { children: `    ${w().task_id ?? "?"} · ${truncate(w().objective, 72)}` }), (0, jsx_runtime_1.jsx)("text", { children: `    ${String(w().model ?? "unknown model")} · ${shortSession(w().session?.id)} · ${workerHealth(w())}` }), (0, jsx_runtime_1.jsx)("text", { children: `    CPU ${w().process?.worker?.cpu_percent ?? "?"}% / ${duration(w().process?.worker?.cpu_seconds)} · log ${duration(w().log_age_seconds)} ago · report ${duration(w().report_age_seconds)} ago` }), (0, jsx_runtime_1.jsx)(solid_js_1.Show, { when: w().deadline?.exceeded || w().deadline_exceeded, children: (0, jsx_runtime_1.jsx)("text", { children: (0, jsx_runtime_1.jsx)("span", { style: { fg: "#f87171" }, children: `    ⚠ role deadline exceeded${w().deadline?.overrun_seconds ? ` by ${duration(w().deadline.overrun_seconds)}` : ""}` }) }) })] }));
}
function Dashboard(props) {
    // Presentational only. Keymap layers are setup-time API: the setup-level
    // context.keymap.layer below owns the global T-BAG bindings. Layering a
    // keymap during panel render throws "Keymap provider is missing" on hosts
    // whose session.panel subtree carries no Keymap provider, so per-panel
    // f/escape bindings are deliberately not registered here.
    const s = () => props.snapshot;
    return ((0, jsx_runtime_1.jsx)("box", { flexDirection: "column", padding: 1, children: (0, jsx_runtime_1.jsxs)(solid_js_1.Show, { when: s(), fallback: (0, jsx_runtime_1.jsx)("text", { children: "T-BAG status unavailable for this session." }), children: [(0, jsx_runtime_1.jsxs)("text", { children: [(0, jsx_runtime_1.jsx)("span", { style: { fg: "#4ade80" }, children: PULSE[props.frame % PULSE.length] }), ` T-BAG · ${s()?.run?.id ?? "run"} · `, (0, jsx_runtime_1.jsx)("span", { style: { fg: statusColor(s()?.run?.status) }, children: String(s()?.run?.status ?? "unknown").toUpperCase() })] }), (0, jsx_runtime_1.jsxs)("text", { children: [waveBar(s()?.progress?.registered_percent ?? 0, 30, props.frame), ` ${s()?.progress?.registered_percent ?? 0}% (${s()?.progress?.registered_done ?? 0}/${s()?.progress?.registered_total ?? 0})`] }), (0, jsx_runtime_1.jsx)("text", { children: `Phases ${s()?.progress?.phases_done ?? 0}/${s()?.progress?.phases_total ?? 0} · slots ${s()?.worker_budget?.live ?? 0}/${s()?.worker_budget?.max ?? 0} · ${s()?.run?.parent_loop ?? "no tick yet"}` }), (0, jsx_runtime_1.jsxs)(solid_js_1.Show, { when: s()?.current_phase, children: [(0, jsx_runtime_1.jsx)("text", { children: `Current: ${s()?.current_phase?.phase_id} · ${s()?.current_phase?.percent ?? 0}% · gate ${s()?.current_phase?.gate?.result ?? "pending"}` }), (0, jsx_runtime_1.jsxs)("text", { children: [waveBar(s()?.current_phase?.percent ?? 0, 30, props.frame), ` ${s()?.current_phase?.percent ?? 0}%`] })] }), (0, jsx_runtime_1.jsx)("text", { children: " " }), (0, jsx_runtime_1.jsx)("text", { children: `ACTIVE SESSIONS · Analysts ${s()?.analysts_active?.length ?? 0} · Grunts ${s()?.grunts_active?.length ?? 0}` }), (0, jsx_runtime_1.jsx)(solid_js_1.Show, { when: (s()?.workers?.length ?? 0) > 0, fallback: (0, jsx_runtime_1.jsx)("text", { children: "  No active workers." }), children: (0, jsx_runtime_1.jsx)(solid_js_1.For, { each: s()?.workers ?? [], children: (worker, index) => (0, jsx_runtime_1.jsx)(Worker, { worker: worker, index: index() }) }) }), (0, jsx_runtime_1.jsxs)(solid_js_1.Show, { when: (s()?.attention?.length ?? 0) > 0, children: [(0, jsx_runtime_1.jsx)("text", { children: (0, jsx_runtime_1.jsx)("span", { style: { fg: "#f87171" }, children: `ATTENTION · ${s()?.attention?.length ?? 0}` }) }), (0, jsx_runtime_1.jsx)(solid_js_1.For, { each: (s()?.attention ?? []).slice(0, 8), children: (item) => (0, jsx_runtime_1.jsx)("text", { children: (0, jsx_runtime_1.jsx)("span", { style: { fg: "#f87171" }, children: `⚠ ${item.phase_id ?? ""}/${item.task_id ?? ""} · ${item.status ?? "attention"} · ${truncate(item.objective, 64)}` }) }) })] }), (0, jsx_runtime_1.jsx)("text", { children: " " }), (0, jsx_runtime_1.jsx)("text", { children: "PHASES" }), (0, jsx_runtime_1.jsx)(solid_js_1.For, { each: s()?.phases ?? [], children: (phase) => (0, jsx_runtime_1.jsxs)("text", { children: [phase.complete ? (0, jsx_runtime_1.jsx)("span", { style: { fg: "#4ade80" }, children: "✓" }) : "○", ` ${phase.phase_id}  ${progressBar(phase.percent, 12)} ${phase.percent}%  gate:${phase.gate?.result ?? "—"}`] }) }), (0, jsx_runtime_1.jsx)("text", { children: " " }), (0, jsx_runtime_1.jsx)("text", { children: "reopen via palette or /tbag" })] }) }));
}
exports.default = tui_1.Plugin.define({
    id: "tbag.status.tui",
    setup(context) {
        const [snapshots, setSnapshots] = (0, solid_js_1.createSignal)({});
        const refreshing = new Set();
        const projectRoot = (context.location ?? context.data.location.default())?.directory;
        function currentSessionID() {
            const route = context.ui.router.current();
            return route?.type === "session" ? route.sessionID : undefined;
        }
        function readSnapshot(sessionID) {
            if (!projectRoot || !sessionID || refreshing.has(sessionID))
                return;
            refreshing.add(sessionID);
            try {
                const tool = `${projectRoot}/TBag/tools/tbag_status.py`;
                const result = Bun.spawnSync([
                    "python3", tool,
                    "--project-root", projectRoot,
                    "--parent-session-id", sessionID,
                ], { stdout: "pipe", stderr: "pipe" });
                if (result.exitCode !== 0)
                    return;
                const text = new TextDecoder().decode(result.stdout || new Uint8Array()).trim();
                if (!text)
                    return;
                const value = JSON.parse(text);
                if (value?.format !== "tbag-status-v1")
                    return;
                setSnapshots((prior) => ({ ...prior, [sessionID]: value }));
            }
            catch (_) {
                // Presentation must never disturb the OpenCode session or T-BAG control plane.
            }
            finally {
                refreshing.delete(sessionID);
            }
        }
        function snapshot(sessionID) {
            if (!sessionID)
                return null;
            const current = snapshots()[sessionID] ?? null;
            if (!current)
                queueMicrotask(() => readSnapshot(sessionID));
            return current;
        }
        function refreshCurrent() {
            const sessionID = currentSessionID();
            if (sessionID)
                readSnapshot(sessionID);
        }
        const timer = setInterval(refreshCurrent, REFRESH_MS);
        timer.unref?.();
        queueMicrotask(refreshCurrent);
        // Animation clock. Slot renders read frame() (footer spinner, panel wave
        // bar and pulse), so every host re-render advances the motion. Cheap:
        // one tiny signal, cleared with everything else on dispose.
        const [frame, setFrame] = (0, solid_js_1.createSignal)(0);
        const clock = setInterval(() => setFrame((f) => (f + 1) % 100000), 500);
        clock.unref?.();
        const stopEvents = context.data.listen(() => {
            // Server/session events are cheap hints. The Python snapshot remains the only
            // interpretation of T-BAG task state.
            const sessionID = currentSessionID();
            if (sessionID)
                queueMicrotask(() => readSnapshot(sessionID));
        });
        const disposers = [];
        const keep = (value) => { if (typeof value === "function")
            disposers.push(value); };
        keep(context.ui.slot({
            append: "prompt.footer.status",
            render: () => {
                // Keymap layers are owned by the calling component: this render runs
                // under the host's Keymap provider, while setup() does not, so the
                // global command must be layered here. Calling context.keymap.layer
                // in setup() fails plugin load with "Keymap provider is missing".
                // The footer renders on every screen, keeping the command available.
                context.keymap.layer(() => ({
                    mode: "global",
                    priority: 10,
                    commands: [
                        {
                            id: "tbag.status",
                            title: "T-BAG orchestration status",
                            group: "T-BAG",
                            palette: true,
                            slash: { name: "tbag", aliases: ["tbag-status"] },
                            enabled: () => Boolean(currentSessionID()),
                            run: () => {
                                const sessionID = currentSessionID();
                                if (!sessionID)
                                    return;
                                readSnapshot(sessionID);
                                context.ui.panel.open("tbag.status");
                            },
                        },
                    ],
                }));
                const sessionID = currentSessionID();
                const s = snapshot(sessionID);
                if (!s)
                    return null;
                const f = frame();
                const live = (s.worker_budget?.live ?? 0) > 0;
                const spin = live ? SPINNER[f % SPINNER.length] : "●";
                const warn = s.attention?.length ? ` · ⚠${s.attention.length}` : "";
                return (0, jsx_runtime_1.jsxs)("text", { children: [(0, jsx_runtime_1.jsx)("span", { style: { fg: live ? "#4ade80" : "#9ca3af" }, children: spin }), ` T-BAG ${String(s.run?.status ?? "?").toUpperCase()} · ${s.current_phase?.phase_id ?? "—"} · ${progressBar(s.progress?.registered_percent, 8)} ${s.progress?.registered_percent ?? 0}% · A${s.analysts_active?.length ?? 0}/G${s.grunts_active?.length ?? 0}${warn}`] });
            },
        }));
        keep(context.ui.slot({
            append: "sidebar.content",
            render: ({ sessionID }) => {
                const s = snapshot(sessionID);
                if (!s)
                    return null;
                const f = frame();
                const live = (s.worker_budget?.live ?? 0) > 0;
                const spin = live ? SPINNER[f % SPINNER.length] : "●";
                return ((0, jsx_runtime_1.jsxs)("box", { flexDirection: "column", marginTop: 1, children: [(0, jsx_runtime_1.jsxs)("text", { children: [(0, jsx_runtime_1.jsx)("span", { style: { fg: live ? "#4ade80" : "#9ca3af" }, children: spin }), ` T-BAG · ${s.progress?.registered_percent ?? 0}% · ${s.worker_budget?.live ?? 0}/${s.worker_budget?.max ?? 0} workers`] }), (0, jsx_runtime_1.jsx)("text", { children: `${progressBar(s.progress?.registered_percent, 14)} ${s.progress?.registered_percent ?? 0}%` }), (0, jsx_runtime_1.jsx)("text", { children: `${s.current_phase?.phase_id ?? "—"} · gate ${s.current_phase?.gate?.result ?? "—"}` }), (0, jsx_runtime_1.jsx)(solid_js_1.For, { each: (s.workers ?? []).slice(0, 4), children: (worker) => (0, jsx_runtime_1.jsx)("text", { children: `${worker.tier === "analyst" ? "◆" : "●"} ${worker.task_id} ${worker.role} ${duration(worker.elapsed_seconds)}` }) }), (0, jsx_runtime_1.jsx)(solid_js_1.Show, { when: (s.attention?.length ?? 0) > 0, children: (0, jsx_runtime_1.jsx)("text", { children: (0, jsx_runtime_1.jsx)("span", { style: { fg: "#f87171" }, children: `⚠ ${s.attention.length} item${s.attention.length === 1 ? "" : "s"} need attention` }) }) }), (0, jsx_runtime_1.jsx)("text", { children: "/tbag for details" })] }));
            },
        }));
        keep(context.ui.slot({
            append: "session.panel",
            render: (panel) => ((0, jsx_runtime_1.jsx)(solid_js_1.Show, { when: panel.name === "tbag.status", children: (0, jsx_runtime_1.jsx)(Dashboard, { snapshot: snapshot(panel.sessionID), panel: panel, frame: frame() }) })),
        }));
        return () => {
            clearInterval(timer);
            clearInterval(clock);
            stopEvents?.();
            for (const dispose of disposers.reverse())
                dispose();
        };
    },
});
